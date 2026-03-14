"""Pytest fixtures for annotation module tests.

This module provides:
- Mock parsers and parser registry fixtures
- Sample image generation for unit tests
- SampleMetadata and enrichment data fixtures
- Pipeline component fixtures
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
from image_preprocessing_detector.annotation.parsers.base import BaseParser
from image_preprocessing_detector.annotation.parsers.registry import ParserRegistry
from image_preprocessing_detector.annotation.schemas.enrichment import (
    EnrichmentData,
    LayoutDetection,
)
from image_preprocessing_detector.annotation.schemas.immutable import (
    OriginalFileMetadata,
    OriginalLabels,
)
from image_preprocessing_detector.annotation.schemas.sample import SampleMetadata
from image_preprocessing_detector.annotation.workflow.pipeline import (
    EnrichedSample,
    ParsedSample,
)

# ============================================================================
# Sample Image Generation
# ============================================================================


@pytest.fixture
def sample_rgb_bytes() -> bytes:
    """Return minimal RGB image bytes (1x1 pixel PNG).

    This is a valid PNG with a single white pixel.
    """
    # Minimal 1x1 white pixel PNG (valid PNG structure)
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,  # PNG signature
            0x00,
            0x00,
            0x00,
            0x0D,  # IHDR length
            0x49,
            0x48,
            0x44,
            0x52,  # IHDR
            0x00,
            0x00,
            0x00,
            0x01,  # width: 1 pixel
            0x00,
            0x00,
            0x00,
            0x01,  # height: 1 pixel
            0x08,
            0x02,  # bit depth = 8, color type = 2 (RGB)
            0x00,
            0x00,
            0x00,  # compression, filter, interlace
            0x90,
            0x77,
            0x53,
            0xDE,  # CRC
            0x00,
            0x00,
            0x00,
            0x0C,  # IDAT length
            0x49,
            0x44,
            0x41,
            0x54,  # IDAT
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
            0xFE,  # compressed data
            0xA3,
            0x6C,
            0xEC,
            0x61,  # CRC
            0x00,
            0x00,
            0x00,
            0x00,  # IEND length
            0x49,
            0x45,
            0x4E,
            0x44,  # IEND
            0xAE,
            0x42,
            0x60,
            0x82,  # CRC
        ]
    )


@pytest.fixture
def sample_image_file(tmp_path: Path, sample_rgb_bytes: bytes) -> Path:
    """Create a sample image file for testing.

    Args:
        tmp_path: Pytest temporary path fixture
        sample_rgb_bytes: Minimal PNG bytes

    Returns:
        Path to the created sample image
    """
    img_path = tmp_path / "sample_image.png"
    img_path.write_bytes(sample_rgb_bytes)
    return img_path


@pytest.fixture
def sample_image_dir(tmp_path: Path, sample_rgb_bytes: bytes) -> Path:
    """Create a directory with multiple sample images.

    Args:
        tmp_path: Pytest temporary path fixture
        sample_rgb_bytes: Minimal PNG bytes

    Returns:
        Path to directory containing sample images
    """
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    for i in range(10):
        img_path = img_dir / f"image_{i:03d}.png"
        img_path.write_bytes(sample_rgb_bytes)

    return img_dir


@pytest.fixture
def sample_dataset_dir(tmp_path: Path, sample_rgb_bytes: bytes) -> Path:
    """Create a mock dataset directory with structure.

    Creates:
        dataset/
        ├── train/
        │   ├── image_000.png
        │   ├── image_001.png
        │   └── ...
        ├── val/
        │   └── ...
        └── annotations.json

    Args:
        tmp_path: Pytest temporary path fixture
        sample_rgb_bytes: Minimal PNG bytes

    Returns:
        Path to the mock dataset directory
    """
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()

    # Create train and val directories
    for split in ["train", "val"]:
        split_dir = dataset_dir / split
        split_dir.mkdir()
        for i in range(5):
            img_path = split_dir / f"image_{i:03d}.png"
            img_path.write_bytes(sample_rgb_bytes)

    # Create annotations file
    annotations = {
        "images": [
            {"id": i, "file_name": f"train/image_{i:03d}.png", "width": 1, "height": 1}
            for i in range(5)
        ]
        + [
            {
                "id": i + 5,
                "file_name": f"val/image_{i:03d}.png",
                "width": 1,
                "height": 1,
            }
            for i in range(5)
        ],
        "annotations": [],
        "categories": [{"id": 1, "name": "document"}],
    }
    annotations_path = dataset_dir / "annotations.json"
    annotations_path.write_text(json.dumps(annotations))

    return dataset_dir


# ============================================================================
# Mock Parser Fixtures
# ============================================================================


class MockParser(BaseParser):
    """Mock parser for testing.

    Implements the BaseParser interface with configurable dataset names.
    """

    def __init__(self, dataset_name: str = "mock-dataset"):
        """Initialize mock parser.

        Args:
            dataset_name: Primary dataset name this parser handles.
        """
        super().__init__()
        self._dataset_name = dataset_name
        self.parse_calls: list[Path] = []

    @property
    def dataset_names(self) -> list[str]:
        """Return list of dataset names this parser handles."""
        return [self._dataset_name]

    @property
    def supported_extensions(self) -> set[str]:
        """Return supported extensions."""
        return {".png", ".jpg", ".jpeg"}

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse image and return mock labels.

        Records the parse call for verification.
        Uses raw_labels for generic label storage.
        """
        self.parse_calls.append(image_path)
        return OriginalLabels(
            raw_labels={"category": "document", "tags": ["mock", "test"]},
        )


@pytest.fixture
def mock_parser() -> MockParser:
    """Return a mock parser instance."""
    return MockParser()


@pytest.fixture
def mock_parser_factory():
    """Factory fixture for creating mock parsers with custom names."""

    def _create_parser(dataset_name: str = "mock-dataset") -> MockParser:
        return MockParser(dataset_name)

    return _create_parser


@pytest.fixture
def parser_registry_with_mock(mock_parser: MockParser) -> ParserRegistry:
    """Return parser registry with mock parser registered."""
    registry = ParserRegistry()
    registry.register(mock_parser)
    return registry


# ============================================================================
# Enrichment Fixtures
# ============================================================================


@pytest.fixture
def sample_layout_detection() -> LayoutDetection:
    """Return sample layout detection."""
    return LayoutDetection(
        class_name="document",
        confidence=0.95,
        bbox=[0.0, 0.0, 100.0, 100.0],
        source="mock-detector",
    )


@pytest.fixture
def sample_enrichment_data(
    sample_layout_detection: LayoutDetection,
) -> EnrichmentData:
    """Return sample enrichment data with quality and layout."""
    return EnrichmentData(
        quality_overall=0.85,
        layout_detections=[sample_layout_detection],
    )


@pytest.fixture
def mock_enrichment_manager(sample_enrichment_data: EnrichmentData):
    """Return mock enrichment manager that returns sample data.

    DEPRECATED: Prefer real_enrichment_manager for new tests.
    """
    manager = MagicMock(spec=EnrichmentManager)

    def mock_enrich_batch(image_paths: list[Path]) -> list[EnrichmentResult]:
        return [
            EnrichmentResult(
                data=sample_enrichment_data,
                errors=[],
            )
            for _ in image_paths
        ]

    manager.enrich_batch.side_effect = mock_enrich_batch
    return manager


@pytest.fixture
def real_enrichment_manager() -> EnrichmentManager:
    """Return real EnrichmentManager with SimulatedInferenceProvider.

    Uses SimulatedInferenceProvider for GPU-less testing with deterministic,
    reproducible enrichment results. Preferred over mock_enrichment_manager.
    """
    from image_preprocessing_detector.annotation.enrichment.providers import (
        SimulatedInferenceProvider,
    )

    simulated_provider = SimulatedInferenceProvider(
        failure_rate=0.0,  # No failures for normal unit tests
        seed=42,  # Reproducible results
    )
    return EnrichmentManager(
        providers=[simulated_provider],
        validate=True,
        max_retries=1,
    )


# ============================================================================
# Schema Fixtures
# ============================================================================


@pytest.fixture
def sample_original_labels() -> OriginalLabels:
    """Return sample original labels using raw_labels fallback."""
    return OriginalLabels(
        raw_labels={"category": "document", "tags": ["text", "table"]},
    )


@pytest.fixture
def sample_original_file_metadata() -> OriginalFileMetadata:
    """Return sample original file metadata."""
    return OriginalFileMetadata(
        format="png",
        width_px=1920,
        height_px=1080,
        channels=3,
        bit_depth=8,
        file_size_bytes=1024,
        dpi=300,
    )


@pytest.fixture
def sample_metadata(
    sample_original_labels: OriginalLabels,
    sample_original_file_metadata: OriginalFileMetadata,
) -> SampleMetadata:
    """Return sample SampleMetadata instance."""
    return SampleMetadata(
        id="test-sample-001",
        file_hash="abc123def456",
        dataset_name="test-dataset",
        dataset_version="1.0",
        original_path="train/image_001.png",
        original_filename="image_001.png",
        download_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        original_labels=sample_original_labels,
        original_file=sample_original_file_metadata,
    )


@pytest.fixture
def sample_parsed_sample(sample_image_file: Path) -> ParsedSample:
    """Return sample ParsedSample instance."""
    return ParsedSample(
        image_path=sample_image_file,
        relative_path="train/sample_image.png",
        file_hash="abc123def456",
        original_labels=OriginalLabels(raw_labels={"category": "document"}),
        dataset_name="test-dataset",
    )


@pytest.fixture
def sample_enriched_sample(
    sample_parsed_sample: ParsedSample,
    sample_enrichment_data: EnrichmentData,
) -> EnrichedSample:
    """Return sample EnrichedSample instance."""
    return EnrichedSample(
        parsed=sample_parsed_sample,
        enrichment=sample_enrichment_data,
        enrichment_errors=[],
    )


# ============================================================================
# Pipeline Fixtures
# ============================================================================


@pytest.fixture
def sample_settings(tmp_path: Path) -> AnnotationSettings:
    """Return sample annotation settings with real paths.

    Uses tmp_path to create isolated test directories.
    """
    metadata_root = tmp_path / "metadata_registry"
    metadata_root.mkdir(parents=True, exist_ok=True)

    return AnnotationSettings(
        e_drive_root=tmp_path,
        metadata_root=metadata_root,
        checkpoint_dir=tmp_path / "checkpoints",
        workers=2,
        batch_size=10,
        checkpoint_interval=5,
        yolo_model_path=None,  # No GPU inference for unit tests
        siglip_model_path=None,
    )


@pytest.fixture
def mock_checkpoint_manager(tmp_path: Path) -> CheckpointManager:
    """Return checkpoint manager with temp directory."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return CheckpointManager(checkpoint_dir=checkpoint_dir)


# ============================================================================
# Data Generation Fixtures
# ============================================================================


@pytest.fixture
def sample_batch_factory(sample_rgb_bytes: bytes):
    """Factory for creating batches of sample images.

    Returns:
        Factory function that creates a directory with N images
    """

    def _create_batch(tmp_path: Path, batch_size: int = 10) -> list[Path]:
        paths = []
        for i in range(batch_size):
            img_path = tmp_path / f"batch_image_{i:04d}.png"
            img_path.write_bytes(sample_rgb_bytes)
            paths.append(img_path)
        return paths

    return _create_batch


@pytest.fixture
def sample_coco_annotations() -> dict[str, Any]:
    """Return sample COCO-format annotations."""
    return {
        "images": [
            {"id": 1, "file_name": "image_001.png", "width": 1920, "height": 1080},
            {"id": 2, "file_name": "image_002.png", "width": 1920, "height": 1080},
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [100, 100, 200, 150],
                "area": 30000,
                "iscrowd": 0,
            },
            {
                "id": 2,
                "image_id": 2,
                "category_id": 2,
                "bbox": [50, 50, 300, 200],
                "area": 60000,
                "iscrowd": 0,
            },
        ],
        "categories": [
            {"id": 1, "name": "text"},
            {"id": 2, "name": "table"},
        ],
    }


@pytest.fixture
def sample_coco_file(tmp_path: Path, sample_coco_annotations: dict) -> Path:
    """Create sample COCO annotation file."""
    coco_path = tmp_path / "annotations.json"
    coco_path.write_text(json.dumps(sample_coco_annotations))
    return coco_path
