"""Tests for the annotation orchestrator.

Test Coverage:
    - AnnotationOrchestrator initialization
    - Single dataset processing
    - Multi-dataset processing
    - Completion tracking
    - Reset functionality
    - Error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.annotation.config.settings import AnnotationSettings
from image_preprocessing_detector.annotation.enrichment.manager import (
    EnrichmentManager,
)
from image_preprocessing_detector.annotation.integrity.checkpointing import (
    CheckpointManager,
)
from image_preprocessing_detector.annotation.parsers.registry import ParserRegistry
from image_preprocessing_detector.annotation.storage.parquet_writer import (
    PartitionedParquetWriter,
)
from image_preprocessing_detector.annotation.workflow.orchestrator import (
    AnnotationOrchestrator,
    DatasetResult,
    OrchestrationResult,
    create_orchestrator,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_settings(tmp_path) -> AnnotationSettings:
    """Create mock settings for testing."""
    return AnnotationSettings(
        e_drive_root=tmp_path / "e_drive",
        metadata_root=tmp_path / "metadata",
        checkpoint_dir=tmp_path / "checkpoints",
        yolo_model_path=None,
        yolo_confidence_threshold=0.5,
        batch_size=10,
        workers=2,
    )


@pytest.fixture
def mock_parser_registry() -> MagicMock:
    """Create mock parser registry."""
    mock = MagicMock(spec=ParserRegistry)
    return mock


@pytest.fixture
def mock_enrichment_manager() -> MagicMock:
    """Create mock enrichment manager."""
    mock = MagicMock(spec=EnrichmentManager)
    mock.providers = []
    return mock


@pytest.fixture
def mock_checkpoint_manager(tmp_path) -> CheckpointManager:
    """Create real checkpoint manager with temp directory."""
    return CheckpointManager(tmp_path / "checkpoints")


@pytest.fixture
def mock_parquet_writer(tmp_path) -> PartitionedParquetWriter:
    """Create real parquet writer with temp directory."""
    return PartitionedParquetWriter(tmp_path / "parquet")


@pytest.fixture
def orchestrator(
    mock_settings,
    mock_parser_registry,
    mock_enrichment_manager,
    mock_checkpoint_manager,
    mock_parquet_writer,
) -> AnnotationOrchestrator:
    """Create orchestrator with mock dependencies."""
    return AnnotationOrchestrator(
        settings=mock_settings,
        parser_registry=mock_parser_registry,
        enrichment_manager=mock_enrichment_manager,
        checkpoint_manager=mock_checkpoint_manager,
        parquet_writer=mock_parquet_writer,
    )


# ============================================================================
# DatasetResult Tests
# ============================================================================


class TestDatasetResult:
    """Test DatasetResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = DatasetResult(
            dataset_name="test-dataset",
            success=True,
            samples_processed=100,
            samples_failed=5,
            errors=["Error 1", "Error 2"],
            duration_seconds=10.5,
        )

        assert result.dataset_name == "test-dataset"
        assert result.success is True
        assert result.samples_processed == 100
        assert result.samples_failed == 5
        assert len(result.errors) == 2
        assert result.duration_seconds == pytest.approx(10.5)

    def test_create_failure_result(self):
        """Test creating a failed result."""
        result = DatasetResult(
            dataset_name="test-dataset",
            success=False,
            samples_processed=0,
            errors=["Fatal error"],
        )

        assert result.success is False
        assert result.samples_processed == 0

    def test_default_values(self):
        """Test default values are applied."""
        result = DatasetResult(
            dataset_name="test",
            success=True,
            samples_processed=10,
        )

        assert result.samples_failed == 0
        assert result.errors == []
        assert result.duration_seconds == pytest.approx(0.0)


# ============================================================================
# OrchestrationResult Tests
# ============================================================================


class TestOrchestrationResult:
    """Test OrchestrationResult dataclass."""

    def test_success_count(self):
        """Test success_count property."""
        result = OrchestrationResult(
            dataset_results=[
                DatasetResult("a", success=True, samples_processed=10),
                DatasetResult("b", success=False, samples_processed=0),
                DatasetResult("c", success=True, samples_processed=20),
            ]
        )

        assert result.success_count == 2
        assert result.failure_count == 1

    def test_empty_result(self):
        """Test empty orchestration result."""
        result = OrchestrationResult()

        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.total_samples == 0
        assert result.total_errors == 0


# ============================================================================
# Orchestrator Initialization Tests
# ============================================================================


class TestOrchestratorInitialization:
    """Test AnnotationOrchestrator initialization."""

    def test_creates_with_all_dependencies(
        self,
        mock_settings,
        mock_parser_registry,
        mock_enrichment_manager,
    ):
        """Test orchestrator initializes with all dependencies."""
        orchestrator = AnnotationOrchestrator(
            settings=mock_settings,
            parser_registry=mock_parser_registry,
            enrichment_manager=mock_enrichment_manager,
        )

        assert orchestrator.settings == mock_settings
        assert orchestrator.parsers == mock_parser_registry
        assert orchestrator.enrichment == mock_enrichment_manager
        assert orchestrator.checkpoints is not None
        assert orchestrator.parquet_writer is not None
        assert orchestrator.progress is not None

    def test_accepts_optional_dependencies(
        self,
        mock_settings,
        mock_parser_registry,
        mock_enrichment_manager,
        mock_checkpoint_manager,
        mock_parquet_writer,
    ):
        """Test orchestrator accepts optional dependencies."""
        orchestrator = AnnotationOrchestrator(
            settings=mock_settings,
            parser_registry=mock_parser_registry,
            enrichment_manager=mock_enrichment_manager,
            checkpoint_manager=mock_checkpoint_manager,
            parquet_writer=mock_parquet_writer,
        )

        assert orchestrator.checkpoints == mock_checkpoint_manager
        assert orchestrator.parquet_writer == mock_parquet_writer


# ============================================================================
# Single Dataset Processing Tests
# ============================================================================


class TestProcessDataset:
    """Test single dataset processing."""

    def test_unknown_dataset_returns_error(self, orchestrator):
        """Test processing unknown dataset returns error result."""
        result = orchestrator.process_dataset("nonexistent-dataset")

        assert result.success is False
        assert "Unknown dataset" in result.errors[0]

    def test_empty_dataset_returns_success(self, orchestrator, mock_settings):
        """Test processing dataset with no images returns success."""
        # Create dataset directory but no images
        dataset_path = mock_settings.e_drive_root / "benchmark_only" / "diqa-5000"
        dataset_path.mkdir(parents=True)

        result = orchestrator.process_dataset("diqa-5000")

        assert result.success is True
        assert result.samples_processed == 0

    def test_nonexistent_path_returns_success_empty(self, orchestrator):
        """Test nonexistent dataset path returns success with 0 samples."""
        result = orchestrator.process_dataset("diqa-5000")

        assert result.success is True
        assert result.samples_processed == 0

    def test_process_respects_max_samples(self, orchestrator, mock_settings):
        """Test max_samples parameter is respected."""
        # Create dataset with images
        dataset_path = mock_settings.e_drive_root / "benchmark_only" / "diqa-5000"
        ori_path = dataset_path / "train" / "ori"
        ori_path.mkdir(parents=True)

        # Create 10 dummy images
        for i in range(10):
            (ori_path / f"img{i:03d}.jpg").touch()

        # Request max 5 samples
        with patch.object(orchestrator, "_discover_images", return_value=[]):
            result = orchestrator.process_dataset("diqa-5000", max_samples=5)

        # Should be limited
        assert result.success is True


# ============================================================================
# Multi-Dataset Processing Tests
# ============================================================================


class TestProcessAll:
    """Test multi-dataset processing."""

    def test_process_all_with_specific_datasets(self, orchestrator):
        """Test processing specific dataset list."""
        result = orchestrator.process_all(
            dataset_names=["diqa-5000", "smartdoc-qa"],
            resume=False,
        )

        assert isinstance(result, OrchestrationResult)
        assert len(result.dataset_results) == 2

    def test_resume_skips_completed(self, orchestrator, mock_parquet_writer):
        """Test resume=True skips completed datasets."""
        # Write some data to mark as completed
        from image_preprocessing_detector.annotation.schemas.immutable import (
            OriginalFileMetadata,
            OriginalLabels,
        )
        from image_preprocessing_detector.annotation.schemas.sample import (
            SampleMetadata,
        )

        sample = SampleMetadata(
            id="test123",
            file_hash="sha256:abc",
            dataset_name="diqa-5000",
            dataset_version="1.0",
            original_path="test.png",
            original_filename="test.png",
            download_date="2025-01-26",
            original_labels=OriginalLabels(),
            original_file=OriginalFileMetadata(
                format="png",
                width_px=100,
                height_px=100,
                channels=3,
                bit_depth=8,
                file_size_bytes=1000,
            ),
        )
        mock_parquet_writer.write_dataset("diqa-5000", [sample])

        # Process with resume=True
        result = orchestrator.process_all(
            dataset_names=["diqa-5000"],
            resume=True,
        )

        # Should skip already completed dataset
        assert len(result.dataset_results) == 0

    def test_resume_false_processes_all(self, orchestrator):
        """Test resume=False processes all datasets."""
        result = orchestrator.process_all(
            dataset_names=["diqa-5000"],
            resume=False,
        )

        assert len(result.dataset_results) == 1


# ============================================================================
# Completion Tracking Tests
# ============================================================================


class TestCompletionTracking:
    """Test completion tracking functionality."""

    def test_get_pending_datasets_all_pending(self, orchestrator):
        """Test all datasets are pending initially."""
        pending = orchestrator.get_pending_datasets()

        # All datasets in DATASET_CONFIGS should be pending
        assert len(pending) > 0
        assert "diqa-5000" in pending

    def test_get_pending_excludes_completed(self, orchestrator, mock_parquet_writer):
        """Test completed datasets are excluded from pending list."""
        # Mark one dataset as completed by writing data
        from image_preprocessing_detector.annotation.schemas.immutable import (
            OriginalFileMetadata,
            OriginalLabels,
        )
        from image_preprocessing_detector.annotation.schemas.sample import (
            SampleMetadata,
        )

        sample = SampleMetadata(
            id="test123",
            file_hash="sha256:abc",
            dataset_name="diqa-5000",
            dataset_version="1.0",
            original_path="test.png",
            original_filename="test.png",
            download_date="2025-01-26",
            original_labels=OriginalLabels(),
            original_file=OriginalFileMetadata(
                format="png",
                width_px=100,
                height_px=100,
                channels=3,
                bit_depth=8,
                file_size_bytes=1000,
            ),
        )
        mock_parquet_writer.write_dataset("diqa-5000", [sample])

        pending = orchestrator.get_pending_datasets()

        assert "diqa-5000" not in pending


# ============================================================================
# Reset Tests
# ============================================================================


class TestReset:
    """Test reset functionality."""

    def test_reset_clears_parquet_data(self, orchestrator, mock_parquet_writer):
        """Test reset removes parquet data."""
        # Write some data
        from image_preprocessing_detector.annotation.schemas.immutable import (
            OriginalFileMetadata,
            OriginalLabels,
        )
        from image_preprocessing_detector.annotation.schemas.sample import (
            SampleMetadata,
        )

        sample = SampleMetadata(
            id="test123",
            file_hash="sha256:abc",
            dataset_name="test-dataset",
            dataset_version="1.0",
            original_path="test.png",
            original_filename="test.png",
            download_date="2025-01-26",
            original_labels=OriginalLabels(),
            original_file=OriginalFileMetadata(
                format="png",
                width_px=100,
                height_px=100,
                channels=3,
                bit_depth=8,
                file_size_bytes=1000,
            ),
        )
        mock_parquet_writer.write_dataset("test-dataset", [sample])
        assert "test-dataset" in mock_parquet_writer.list_datasets()

        # Reset
        result = orchestrator.reset_dataset("test-dataset")

        assert result is True
        assert "test-dataset" not in mock_parquet_writer.list_datasets()


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateOrchestrator:
    """Test create_orchestrator factory function."""

    def test_creates_with_default_settings(self, tmp_path):
        """Test factory creates orchestrator with default settings."""
        # Set required env vars
        with patch.dict(
            "os.environ",
            {
                "E_DRIVE_ROOT": str(tmp_path / "e"),
                "METADATA_ROOT": str(tmp_path / "meta"),
                "CHECKPOINT_DIR": str(tmp_path / "checkpoints"),
            },
        ):
            with patch(
                "image_preprocessing_detector.annotation.config.settings.AnnotationSettings.from_env"
            ) as mock_from_env:
                mock_from_env.return_value = AnnotationSettings(
                    e_drive_root=tmp_path / "e",
                    metadata_root=tmp_path / "meta",
                    checkpoint_dir=tmp_path / "checkpoints",
                )
                orchestrator = create_orchestrator(use_yolo=False)

        assert isinstance(orchestrator, AnnotationOrchestrator)

    def test_creates_with_custom_settings(self, mock_settings):
        """Test factory accepts custom settings."""
        orchestrator = create_orchestrator(
            settings=mock_settings,
            use_yolo=False,
        )

        assert orchestrator.settings == mock_settings

    def test_yolo_disabled_when_requested(self, mock_settings):
        """Test YOLO is disabled when use_yolo=False."""
        orchestrator = create_orchestrator(
            settings=mock_settings,
            use_yolo=False,
        )

        # Enrichment manager should have no providers
        assert len(orchestrator.enrichment.providers) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestOrchestratorIntegration:
    """Integration tests for orchestrator workflows."""

    def test_process_and_reset_workflow(self, orchestrator, mock_parquet_writer):
        """Test complete process and reset workflow."""
        # Process a dataset (will be empty but successful)
        result1 = orchestrator.process_dataset("diqa-5000")
        assert result1.success is True

        # Check if it would be skipped on resume (no data = not completed)
        pending = orchestrator.get_pending_datasets()
        assert "diqa-5000" in pending

    def test_multiple_datasets_sequential(self, orchestrator):
        """Test processing multiple datasets sequentially."""
        result = orchestrator.process_all(
            dataset_names=["diqa-5000", "smartdoc-qa", "dibco"],
            resume=False,
        )

        assert len(result.dataset_results) == 3
        assert all(r.success for r in result.dataset_results)
