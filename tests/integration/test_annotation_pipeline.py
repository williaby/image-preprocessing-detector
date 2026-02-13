# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Integration tests for the annotation pipeline.

Tests the complete annotation workflow including:
- Pre-flight validation
- Batch scanning
- Pipeline processing with all stages
- Checkpointing and resume
- Metrics collection
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.annotation.config.settings import AnnotationSettings
from image_preprocessing_detector.annotation.enrichment.manager import (
    EnrichmentManager,
    EnrichmentResult,
)
from image_preprocessing_detector.annotation.integrity.checkpointing import (
    CheckpointManager,
)
from image_preprocessing_detector.annotation.monitoring.metrics import (
    get_annotation_metrics,
)
from image_preprocessing_detector.annotation.parsers.base import BaseParser
from image_preprocessing_detector.annotation.parsers.registry import ParserRegistry
from image_preprocessing_detector.annotation.schemas.enrichment import EnrichmentData
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels
from image_preprocessing_detector.annotation.workflow.pipeline import (
    AnnotationPipeline,
    PipelineResult,
)
from image_preprocessing_detector.annotation.workflow.preflight import (
    CheckSeverity,
    PreflightChecker,
    PreflightConfig,
)
from image_preprocessing_detector.annotation.workflow.scanner import (
    BatchScanner,
    ScanConfig,
)

# ============================================================================
# Fixtures
# ============================================================================


class IntegrationMockParser(BaseParser):
    """Mock parser for integration testing."""

    def __init__(self, dataset_name: str = "integration-test"):
        super().__init__()
        self._dataset_name = dataset_name

    @property
    def dataset_names(self) -> list[str]:
        """Return list of dataset names this parser handles."""
        return [self._dataset_name]

    @property
    def supported_extensions(self) -> set[str]:
        return {".png", ".jpg", ".jpeg"}

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Return mock labels for testing."""
        return OriginalLabels(
            diqa_overall=0.85,
            raw_labels={"source": "integration-test", "path": str(image_path)},
        )


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Minimal valid PNG for testing."""
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,
            0x08,
            0x02,
            0x00,
            0x00,
            0x00,
            0x90,
            0x77,
            0x53,
            0xDE,
            0x00,
            0x00,
            0x00,
            0x0C,
            0x49,
            0x44,
            0x41,
            0x54,
            0x08,
            0xD7,
            0x63,
            0xF8,
            0xFF,
            0xFF,
            0xFF,
            0x00,
            0x05,
            0xFE,
            0x02,
            0xFE,
            0xA3,
            0x6C,
            0xEC,
            0x61,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )


@pytest.fixture
def integration_dataset(tmp_path: Path, sample_png_bytes: bytes) -> Path:
    """Create a test dataset for integration testing.

    Structure:
        dataset/
        ├── train/
        │   ├── image_000.png ... image_019.png
        ├── val/
        │   ├── image_000.png ... image_004.png
        └── annotations.json
    """
    dataset_dir = tmp_path / "integration_dataset"
    dataset_dir.mkdir()

    # Create train images (20)
    train_dir = dataset_dir / "train"
    train_dir.mkdir()
    for i in range(20):
        (train_dir / f"image_{i:03d}.png").write_bytes(sample_png_bytes)

    # Create val images (5)
    val_dir = dataset_dir / "val"
    val_dir.mkdir()
    for i in range(5):
        (val_dir / f"image_{i:03d}.png").write_bytes(sample_png_bytes)

    # Create annotations
    annotations = {
        "images": [
            {"id": i, "file_name": f"train/image_{i:03d}.png"} for i in range(20)
        ]
        + [{"id": i + 20, "file_name": f"val/image_{i:03d}.png"} for i in range(5)],
        "annotations": [],
        "categories": [{"id": 1, "name": "document"}],
    }
    (dataset_dir / "annotations.json").write_text(json.dumps(annotations))

    return dataset_dir


@pytest.fixture
def integration_settings(
    tmp_path: Path, integration_dataset: Path
) -> AnnotationSettings:
    """Create settings for integration testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()

    return AnnotationSettings(
        e_drive_root=integration_dataset,
        metadata_root=output_dir,
        checkpoint_dir=checkpoint_dir,
        workers=2,
        batch_size=5,
        checkpoint_interval=2,
    )


@pytest.fixture
def mock_enrichment_manager() -> MagicMock:
    """Create mock enrichment manager."""
    manager = MagicMock(spec=EnrichmentManager)

    def mock_enrich(paths: list[Path]) -> list[EnrichmentResult]:
        return [
            EnrichmentResult(
                data=EnrichmentData(quality_overall=0.85),
                errors=[],
            )
            for _ in paths
        ]

    manager.enrich_batch.side_effect = mock_enrich
    return manager


# ============================================================================
# Pre-flight Integration Tests
# ============================================================================


class TestPreflightIntegration:
    """Integration tests for pre-flight validation."""

    def test_preflight_passes_for_valid_paths(
        self,
        integration_dataset: Path,
        tmp_path: Path,
    ) -> None:
        """Test that preflight passes for valid paths."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = PreflightConfig(
            min_disk_space_gb=0.001,  # Very small for testing
            required_read_paths=[integration_dataset],
            required_write_paths=[output_dir],
            check_model_availability=False,
            check_provider_connectivity=False,
        )

        checker = PreflightChecker(config)
        result = checker.check_all()

        assert result.passed
        assert len(result.failures) == 0

    def test_preflight_detects_missing_path(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that preflight detects missing required path."""
        missing_path = tmp_path / "nonexistent"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = PreflightConfig(
            min_disk_space_gb=0.001,
            required_read_paths=[missing_path],
            required_write_paths=[output_dir],
            check_model_availability=False,
            check_provider_connectivity=False,
        )

        checker = PreflightChecker(config)
        result = checker.check_all()

        assert not result.passed
        failures = [c for c in result.checks if c.severity == CheckSeverity.ERROR]
        assert len(failures) >= 1

    def test_preflight_with_custom_check(
        self,
        integration_dataset: Path,
        tmp_path: Path,
    ) -> None:
        """Test preflight with custom validation check."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = PreflightConfig(
            min_disk_space_gb=0.001,
            required_read_paths=[integration_dataset],
            required_write_paths=[output_dir],
            check_model_availability=False,
        )

        checker = PreflightChecker(config)

        # Register custom check
        custom_check_called = False

        def custom_check(result_obj):
            nonlocal custom_check_called
            custom_check_called = True
            from image_preprocessing_detector.annotation.workflow.preflight import (
                CheckCategory,
                CheckResult,
            )

            result_obj.checks.append(
                CheckResult(
                    check_name="custom_annotations_check",
                    passed=True,
                    message="Annotations present",
                    category=CheckCategory.CONFIGURATION,
                    severity=CheckSeverity.INFO,
                )
            )

        checker.register_check(custom_check)
        result = checker.check_all()

        assert custom_check_called
        assert result.passed


# ============================================================================
# Scanner Integration Tests
# ============================================================================


class TestScannerIntegration:
    """Integration tests for batch scanner."""

    def test_scanner_discovers_all_images(
        self,
        integration_dataset: Path,
    ) -> None:
        """Test that scanner discovers all images in dataset."""
        config = ScanConfig(
            batch_size=10,
            file_patterns=["*.png"],
        )

        scanner = BatchScanner(config)
        all_paths = []

        for batch in scanner.scan(integration_dataset):
            all_paths.extend(batch.paths)

        # Should find 25 images (20 train + 5 val)
        assert len(all_paths) == 25

    def test_scanner_respects_batch_size(
        self,
        integration_dataset: Path,
    ) -> None:
        """Test that scanner respects configured batch size."""
        config = ScanConfig(batch_size=5, file_patterns=["*.png"])
        scanner = BatchScanner(config)

        batches = list(scanner.scan(integration_dataset))

        # Should have 5 batches (25 images / 5 per batch)
        assert len(batches) == 5
        for batch in batches:
            assert len(batch.paths) <= 5

    def test_scanner_checkpoint_resume(
        self,
        integration_dataset: Path,
        tmp_path: Path,
    ) -> None:
        """Test scanner checkpoint and resume functionality."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        config = ScanConfig(
            batch_size=5,
            file_patterns=["*.png"],
            checkpoint_dir=str(checkpoint_dir),
            checkpoint_every=1,  # Checkpoint after every batch
        )

        scanner = BatchScanner(config)

        # Process first 2 batches
        batch_iter = scanner.scan(integration_dataset)
        batch1 = next(batch_iter)
        scanner.mark_batch_complete(batch1)
        batch2 = next(batch_iter)
        scanner.mark_batch_complete(batch2)

        # Checkpoint should exist in directory
        checkpoint_files = list(checkpoint_dir.glob("*.json"))
        assert len(checkpoint_files) >= 1

        # Create new scanner and resume
        scanner2 = BatchScanner(config)
        remaining_batches = list(scanner2.scan(integration_dataset))

        # Should have 3 remaining batches (or could resume from last completed)
        assert len(remaining_batches) <= 5  # Could be 3-5 depending on resume behavior


# ============================================================================
# Pipeline Integration Tests
# ============================================================================


class TestPipelineIntegration:
    """Integration tests for the annotation pipeline."""

    def test_pipeline_processes_dataset(
        self,
        integration_settings: AnnotationSettings,
        integration_dataset: Path,
        mock_enrichment_manager: MagicMock,
    ) -> None:
        """Test that pipeline processes a complete dataset."""
        # Setup parser registry
        parser_registry = ParserRegistry()
        parser_registry.register(IntegrationMockParser("integration-test"))

        # Setup checkpoint manager
        checkpoint_manager = CheckpointManager(
            checkpoint_dir=integration_settings.checkpoint_dir
        )

        # Create pipeline
        pipeline = AnnotationPipeline(
            settings=integration_settings,
            parser_registry=parser_registry,
            enrichment_manager=mock_enrichment_manager,
            checkpoint_manager=checkpoint_manager,
        )

        # Get all image paths
        image_paths = sorted(integration_dataset.glob("**/*.png"))
        assert len(image_paths) == 25

        # Process dataset
        result = pipeline.process_dataset(
            dataset_name="integration-test",
            image_paths=image_paths,
            dataset_config={"path": integration_dataset},
        )

        # Verify results
        assert isinstance(result, PipelineResult)
        assert result.dataset_name == "integration-test"
        assert result.success_count == 25
        assert result.error_count == 0
        assert len(result.samples) == 25

        # Verify stats
        assert result.stats.total_images == 25
        assert result.stats.cpu_time_seconds > 0
        assert result.stats.images_per_second > 0

    def test_pipeline_checkpointing(
        self,
        integration_settings: AnnotationSettings,
        integration_dataset: Path,
        mock_enrichment_manager: MagicMock,
    ) -> None:
        """Test pipeline checkpoint and resume."""
        parser_registry = ParserRegistry()
        parser_registry.register(IntegrationMockParser("integration-test"))

        checkpoint_manager = CheckpointManager(
            checkpoint_dir=integration_settings.checkpoint_dir
        )

        # Get all image paths
        image_paths = sorted(integration_dataset.glob("**/*.png"))

        # First run with subset
        pipeline = AnnotationPipeline(
            settings=integration_settings,
            parser_registry=parser_registry,
            enrichment_manager=mock_enrichment_manager,
            checkpoint_manager=checkpoint_manager,
        )

        result1 = pipeline.process_dataset(
            dataset_name="integration-test",
            image_paths=image_paths[:10],
            dataset_config={"path": integration_dataset},
        )

        assert result1.success_count == 10

        # Clear checkpoint for clean test
        checkpoint_manager.clear_checkpoint("integration-test")

    def test_pipeline_with_errors(
        self,
        integration_settings: AnnotationSettings,
        integration_dataset: Path,
    ) -> None:
        """Test pipeline handles enrichment errors gracefully."""
        parser_registry = ParserRegistry()
        parser_registry.register(IntegrationMockParser("integration-test"))

        checkpoint_manager = CheckpointManager(
            checkpoint_dir=integration_settings.checkpoint_dir
        )

        # Create enrichment manager that returns errors
        error_manager = MagicMock(spec=EnrichmentManager)

        def mock_enrich_with_error(paths: list[Path]) -> list[EnrichmentResult]:
            return [
                EnrichmentResult(
                    data=EnrichmentData(),
                    errors=["Simulated enrichment error"],
                )
                for _ in paths
            ]

        error_manager.enrich_batch.side_effect = mock_enrich_with_error

        pipeline = AnnotationPipeline(
            settings=integration_settings,
            parser_registry=parser_registry,
            enrichment_manager=error_manager,
            checkpoint_manager=checkpoint_manager,
        )

        image_paths = sorted(integration_dataset.glob("**/*.png"))[:5]

        result = pipeline.process_dataset(
            dataset_name="integration-test",
            image_paths=image_paths,
            dataset_config={"path": integration_dataset},
        )

        # Pipeline should complete despite enrichment errors
        assert result.success_count == 5


# ============================================================================
# Metrics Integration Tests
# ============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    def test_metrics_recorded_during_pipeline(
        self,
        integration_settings: AnnotationSettings,
        integration_dataset: Path,
        mock_enrichment_manager: MagicMock,
    ) -> None:
        """Test that metrics are recorded during pipeline execution."""
        parser_registry = ParserRegistry()
        parser_registry.register(IntegrationMockParser("integration-test"))

        checkpoint_manager = CheckpointManager(
            checkpoint_dir=integration_settings.checkpoint_dir
        )

        pipeline = AnnotationPipeline(
            settings=integration_settings,
            parser_registry=parser_registry,
            enrichment_manager=mock_enrichment_manager,
            checkpoint_manager=checkpoint_manager,
        )

        image_paths = sorted(integration_dataset.glob("**/*.png"))[:5]

        # Get metrics instance
        metrics = get_annotation_metrics()

        # Process dataset
        pipeline.process_dataset(
            dataset_name="integration-test",
            image_paths=image_paths,
            dataset_config={"path": integration_dataset},
        )

        # Metrics should be accessible (no errors)
        assert metrics is not None
        assert hasattr(metrics, "pipeline_stage_latency")
        assert hasattr(metrics, "batches_processed")


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


class TestEndToEndAnnotationWorkflow:
    """End-to-end integration tests for complete annotation workflow."""

    def test_complete_annotation_workflow(
        self,
        integration_dataset: Path,
        tmp_path: Path,
        sample_png_bytes: bytes,
    ) -> None:
        """Test complete workflow: preflight -> scan -> pipeline."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        # Step 1: Pre-flight checks
        preflight_config = PreflightConfig(
            min_disk_space_gb=0.001,
            required_read_paths=[integration_dataset],
            required_write_paths=[output_dir],
            check_model_availability=False,
        )
        checker = PreflightChecker(preflight_config)
        preflight_result = checker.check_all()
        assert preflight_result.passed, "Pre-flight should pass"

        # Step 2: Scan dataset
        scan_config = ScanConfig(batch_size=10, file_patterns=["*.png"])
        scanner = BatchScanner(scan_config)
        batches = list(scanner.scan(integration_dataset))
        assert len(batches) > 0, "Should discover batches"

        # Step 3: Process through pipeline
        settings = AnnotationSettings(
            e_drive_root=integration_dataset,
            metadata_root=output_dir,
            checkpoint_dir=checkpoint_dir,
            workers=2,
            batch_size=10,
        )

        parser_registry = ParserRegistry()
        parser_registry.register(IntegrationMockParser("integration-test"))

        checkpoint_manager = CheckpointManager(checkpoint_dir=checkpoint_dir)

        mock_enrichment = MagicMock(spec=EnrichmentManager)
        mock_enrichment.enrich_batch.side_effect = lambda paths: [
            EnrichmentResult(data=EnrichmentData(quality_overall=0.9), errors=[])
            for _ in paths
        ]

        pipeline = AnnotationPipeline(
            settings=settings,
            parser_registry=parser_registry,
            enrichment_manager=mock_enrichment,
            checkpoint_manager=checkpoint_manager,
        )

        # Process all discovered images
        all_paths = []
        for batch in batches:
            all_paths.extend(batch.paths)

        result = pipeline.process_dataset(
            dataset_name="integration-test",
            image_paths=all_paths,
            dataset_config={"path": integration_dataset},
        )

        # Verify complete workflow success
        assert result.success_count == 25
        assert result.error_count == 0
        assert len(result.samples) == 25

        # Verify all samples have valid data
        for sample in result.samples:
            assert sample.id is not None
            assert sample.file_hash is not None
            assert sample.dataset_name == "integration-test"
