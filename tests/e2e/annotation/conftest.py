"""Pytest fixtures for E2E annotation tests.

Provides:
- Real sample image fixtures (actual PNG/JPEG files)
- Real dataset directory structures
- Settings configured for testing
- Orchestrator and pipeline factories

Key Design Principles:
- Minimal mocking - use real components wherever possible
- Real image files - not fake bytes with image extensions
- Temp directories - isolated test environments
- Reproducible - seeded random generation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.annotation.config.settings import AnnotationSettings
from image_preprocessing_detector.annotation.enrichment.manager import EnrichmentManager
from image_preprocessing_detector.annotation.enrichment.providers import (
    SimulatedInferenceProvider,
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
)
from image_preprocessing_detector.annotation.workflow.pipeline import AnnotationPipeline

# Use seeded RNG for reproducibility
_rng = np.random.default_rng(seed=12345)


# =============================================================================
# Real Image Generation
# =============================================================================


def _create_document_image(
    width: int = 640,
    height: int = 480,
    has_text_blocks: bool = True,
    has_table: bool = False,
    noise_level: float = 0.0,
) -> np.ndarray:
    """Create a realistic synthetic document image.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        has_text_blocks: Whether to include simulated text lines
        has_table: Whether to include a table-like structure
        noise_level: Amount of Gaussian noise (0.0-1.0)

    Returns:
        BGR numpy array representing a document image
    """
    # White background
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    if has_text_blocks:
        # Add header (black bar simulating title)
        header_height = height // 10
        cv2.rectangle(
            img,
            (int(width * 0.1), int(height * 0.05)),
            (int(width * 0.9), int(height * 0.05) + header_height),
            (30, 30, 30),
            -1,
        )

        # Add text lines (gray bars of varying lengths)
        line_height = height // 40
        line_spacing = height // 25
        start_y = int(height * 0.2)

        for i in range(15):
            y = start_y + i * line_spacing
            if y + line_height > height - 50:
                break
            # Vary line lengths
            line_width = _rng.uniform(0.5, 0.85)
            cv2.rectangle(
                img,
                (int(width * 0.1), y),
                (int(width * line_width), y + line_height),
                (60, 60, 60),
                -1,
            )

    if has_table:
        # Add table structure
        table_left = int(width * 0.15)
        table_right = int(width * 0.85)
        table_top = int(height * 0.6)
        table_bottom = int(height * 0.9)

        # Draw table border
        cv2.rectangle(
            img,
            (table_left, table_top),
            (table_right, table_bottom),
            (0, 0, 0),
            2,
        )

        # Draw horizontal lines
        num_rows = 5
        row_height = (table_bottom - table_top) // num_rows
        for i in range(1, num_rows):
            y = table_top + i * row_height
            cv2.line(img, (table_left, y), (table_right, y), (0, 0, 0), 1)

        # Draw vertical lines
        num_cols = 4
        col_width = (table_right - table_left) // num_cols
        for i in range(1, num_cols):
            x = table_left + i * col_width
            cv2.line(img, (x, table_top), (x, table_bottom), (0, 0, 0), 1)

    if noise_level > 0:
        noise = _rng.normal(0, noise_level * 30, img.shape).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return img


def _create_form_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a synthetic form image with labeled fields."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Form title
    cv2.rectangle(
        img,
        (int(width * 0.3), 20),
        (int(width * 0.7), 50),
        (0, 0, 0),
        -1,
    )

    # Form fields (label + input box pairs)
    field_y_positions = [100, 160, 220, 280, 340]
    for y in field_y_positions:
        # Label (small gray block)
        cv2.rectangle(
            img,
            (50, y),
            (150, y + 20),
            (80, 80, 80),
            -1,
        )
        # Input box (white with border)
        cv2.rectangle(
            img,
            (170, y - 5),
            (width - 50, y + 30),
            (0, 0, 0),
            1,
        )

    return img


# =============================================================================
# Image File Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def sample_document_png() -> bytes:
    """Create a real PNG-encoded document image.

    Module-scoped for efficiency - same image reused across tests.
    """
    img = _create_document_image(has_text_blocks=True, has_table=False)
    success, buffer = cv2.imencode(".png", img)
    assert success, "Failed to encode PNG"
    return bytes(buffer)


@pytest.fixture(scope="module")
def sample_table_jpeg() -> bytes:
    """Create a real JPEG-encoded table document image."""
    img = _create_document_image(has_text_blocks=True, has_table=True)
    success, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    assert success, "Failed to encode JPEG"
    return bytes(buffer)


@pytest.fixture(scope="module")
def sample_form_png() -> bytes:
    """Create a real PNG-encoded form image."""
    img = _create_form_image()
    success, buffer = cv2.imencode(".png", img)
    assert success, "Failed to encode PNG"
    return bytes(buffer)


@pytest.fixture
def sample_images_collection(
    tmp_path: Path,
    sample_document_png: bytes,
    sample_table_jpeg: bytes,
    sample_form_png: bytes,
) -> list[Path]:
    """Create a collection of 10 real sample images.

    Returns list of paths to created image files.
    """
    images_dir = tmp_path / "sample_images"
    images_dir.mkdir()

    paths = []

    # Create document images (6 PNGs)
    for i in range(6):
        path = images_dir / f"document_{i:03d}.png"
        path.write_bytes(sample_document_png)
        paths.append(path)

    # Create table images (2 JPEGs)
    for i in range(2):
        path = images_dir / f"table_{i:03d}.jpg"
        path.write_bytes(sample_table_jpeg)
        paths.append(path)

    # Create form images (2 PNGs)
    for i in range(2):
        path = images_dir / f"form_{i:03d}.png"
        path.write_bytes(sample_form_png)
        paths.append(path)

    return paths


# =============================================================================
# Dataset Directory Fixtures
# =============================================================================


@pytest.fixture
def mock_dataset_structure(
    tmp_path: Path,
    sample_document_png: bytes,
    sample_table_jpeg: bytes,
) -> Path:
    """Create a realistic dataset directory structure.

    Structure:
        e_drive/
        └── base_data/
            └── test-dataset/
                ├── train/
                │   ├── document_000.png
                │   └── ...
                ├── val/
                │   └── ...
                └── annotations/
                    └── labels.json
    """
    e_drive = tmp_path / "e_drive"
    dataset_dir = e_drive / "base_data" / "test-dataset"

    # Create train split (8 images)
    train_dir = dataset_dir / "train"
    train_dir.mkdir(parents=True)
    for i in range(6):
        (train_dir / f"document_{i:03d}.png").write_bytes(sample_document_png)
    for i in range(2):
        (train_dir / f"table_{i:03d}.jpg").write_bytes(sample_table_jpeg)

    # Create val split (4 images)
    val_dir = dataset_dir / "val"
    val_dir.mkdir()
    for i in range(3):
        (val_dir / f"document_{i:03d}.png").write_bytes(sample_document_png)
    (val_dir / "table_000.jpg").write_bytes(sample_table_jpeg)

    # Create annotations
    annotations_dir = dataset_dir / "annotations"
    annotations_dir.mkdir()

    labels = {
        "version": "1.0",
        "created": datetime.now(UTC).isoformat(),
        "images": [
            {
                "id": i,
                "file_name": f"train/document_{i:03d}.png",
                "category": "document",
            }
            for i in range(6)
        ]
        + [
            {"id": i + 6, "file_name": f"train/table_{i:03d}.jpg", "category": "table"}
            for i in range(2)
        ]
        + [
            {
                "id": i + 8,
                "file_name": f"val/document_{i:03d}.png",
                "category": "document",
            }
            for i in range(3)
        ]
        + [{"id": 11, "file_name": "val/table_000.jpg", "category": "table"}],
    }
    (annotations_dir / "labels.json").write_text(json.dumps(labels, indent=2))

    return e_drive


@pytest.fixture
def multi_dataset_structure(
    tmp_path: Path,
    sample_document_png: bytes,
) -> Path:
    """Create structure with multiple datasets for orchestration tests.

    Structure:
        e_drive/
        └── base_data/
            ├── dataset-alpha/
            │   └── images/
            ├── dataset-beta/
            │   └── images/
            └── dataset-gamma/
                └── images/
    """
    e_drive = tmp_path / "e_drive"

    for dataset_name in ["dataset-alpha", "dataset-beta", "dataset-gamma"]:
        images_dir = e_drive / "base_data" / dataset_name / "images"
        images_dir.mkdir(parents=True)

        # Each dataset has 5 images
        for i in range(5):
            (images_dir / f"img_{i:03d}.png").write_bytes(sample_document_png)

    return e_drive


# =============================================================================
# Settings and Configuration Fixtures
# =============================================================================


@pytest.fixture
def real_settings(tmp_path: Path, mock_dataset_structure: Path) -> AnnotationSettings:
    """Create real AnnotationSettings for E2E testing.

    Uses actual temp directories for all outputs.
    Configures for CPU-only operation (no GPU inference).
    """
    metadata_root = tmp_path / "metadata_registry"
    metadata_root.mkdir(parents=True, exist_ok=True)

    return AnnotationSettings(
        e_drive_root=mock_dataset_structure,
        metadata_root=metadata_root,
        checkpoint_dir=tmp_path / "checkpoints",
        workers=2,  # Limited workers for test stability
        batch_size=4,  # Small batches for faster tests
        checkpoint_interval=3,  # Frequent checkpoints for testing
        yolo_model_path=None,  # No GPU inference for CI
        siglip_model_path=None,  # No GPU inference for CI
    )


@pytest.fixture
def multi_dataset_settings(
    tmp_path: Path, multi_dataset_structure: Path
) -> AnnotationSettings:
    """Settings configured for multi-dataset testing."""
    metadata_root = tmp_path / "metadata_registry"
    metadata_root.mkdir(parents=True, exist_ok=True)

    return AnnotationSettings(
        e_drive_root=multi_dataset_structure,
        metadata_root=metadata_root,
        checkpoint_dir=tmp_path / "checkpoints",
        workers=2,
        batch_size=3,
        checkpoint_interval=2,
        yolo_model_path=None,
        siglip_model_path=None,
    )


# =============================================================================
# Real Component Fixtures
# =============================================================================


@pytest.fixture
def real_checkpoint_manager(tmp_path: Path) -> CheckpointManager:
    """Create a real CheckpointManager with temp directory."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return CheckpointManager(checkpoint_dir=checkpoint_dir)


@pytest.fixture
def real_parquet_writer(tmp_path: Path) -> PartitionedParquetWriter:
    """Create a real PartitionedParquetWriter."""
    parquet_root = tmp_path / "parquet"
    return PartitionedParquetWriter(parquet_root=parquet_root)


@pytest.fixture
def real_parser_registry() -> ParserRegistry:
    """Create a real ParserRegistry with default parsers.

    Note: This loads the actual parser implementations.
    """
    return ParserRegistry()


@pytest.fixture
def real_enrichment_manager() -> EnrichmentManager:
    """Create a real EnrichmentManager with simulated provider.

    For E2E tests in CI, we use SimulatedInferenceProvider to
    generate realistic enrichment data without GPU requirements.
    """
    simulated_provider = SimulatedInferenceProvider(
        failure_rate=0.0,  # No failures for normal E2E tests
        seed=42,  # Reproducible results
    )
    return EnrichmentManager(
        providers=[simulated_provider],
        validate=True,
        max_retries=1,
    )


@pytest.fixture
def enrichment_manager_with_failures() -> EnrichmentManager:
    """Create EnrichmentManager with simulated failures for error testing.

    Uses 20% failure rate to test error handling paths.
    """
    simulated_provider = SimulatedInferenceProvider(
        failure_rate=0.2,  # 20% failure rate
        seed=42,
    )
    return EnrichmentManager(
        providers=[simulated_provider],
        validate=True,
        max_retries=1,
    )


# =============================================================================
# Pipeline and Orchestrator Factories
# =============================================================================


@pytest.fixture
def create_pipeline(
    real_settings: AnnotationSettings,
    real_checkpoint_manager: CheckpointManager,
    real_parser_registry: ParserRegistry,
    real_enrichment_manager: EnrichmentManager,
):
    """Factory fixture for creating AnnotationPipeline with real components.

    Returns a function that creates pipelines with optional overrides.

    Note: AnnotationPipeline constructor takes:
        settings, parser_registry, enrichment_manager, checkpoint_manager
    """

    def _create(
        settings: AnnotationSettings | None = None,
        parser_registry: ParserRegistry | None = None,
        enrichment_manager: EnrichmentManager | None = None,
        checkpoint_manager: CheckpointManager | None = None,
    ) -> AnnotationPipeline:
        return AnnotationPipeline(
            settings=settings or real_settings,
            parser_registry=parser_registry or real_parser_registry,
            enrichment_manager=enrichment_manager or real_enrichment_manager,
            checkpoint_manager=checkpoint_manager or real_checkpoint_manager,
        )

    return _create


@pytest.fixture
def create_orchestrator(
    real_settings: AnnotationSettings,
    real_checkpoint_manager: CheckpointManager,
    real_parquet_writer: PartitionedParquetWriter,
    real_parser_registry: ParserRegistry,
    real_enrichment_manager: EnrichmentManager,
):
    """Factory fixture for creating AnnotationOrchestrator with real components.

    Note: AnnotationOrchestrator constructor takes:
        settings, parser_registry, enrichment_manager,
        checkpoint_manager=None, parquet_writer=None, progress_tracker=None
    """

    def _create(
        settings: AnnotationSettings | None = None,
        parser_registry: ParserRegistry | None = None,
        enrichment_manager: EnrichmentManager | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        parquet_writer: PartitionedParquetWriter | None = None,
    ) -> AnnotationOrchestrator:
        return AnnotationOrchestrator(
            settings=settings or real_settings,
            parser_registry=parser_registry or real_parser_registry,
            enrichment_manager=enrichment_manager or real_enrichment_manager,
            checkpoint_manager=checkpoint_manager or real_checkpoint_manager,
            parquet_writer=parquet_writer or real_parquet_writer,
        )

    return _create


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end tests (may be slow)",
    )
    config.addinivalue_line(
        "markers",
        "e2e_annotation: marks tests as annotation E2E tests",
    )
