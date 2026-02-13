# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for annotation workflow scanner module.

Phase 5 Task 5.2: Batch-aware scanner tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.annotation.workflow.scanner import (
    BatchScanner,
    LoggingProgressCallback,
    ProgressCallback,
    ScanBatch,
    ScanCheckpoint,
    ScanConfig,
    ScanProgress,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    """Create a sample dataset directory with images."""
    dataset_path = tmp_path / "test_dataset"
    dataset_path.mkdir()

    # Create subdirectories
    (dataset_path / "train").mkdir()
    (dataset_path / "val").mkdir()

    # Create sample image files
    for i in range(25):
        (dataset_path / "train" / f"image_{i:03d}.png").touch()
    for i in range(10):
        (dataset_path / "val" / f"image_{i:03d}.jpg").touch()

    return dataset_path


@pytest.fixture
def small_dataset(tmp_path: Path) -> Path:
    """Create a small dataset for quick tests."""
    dataset_path = tmp_path / "small_dataset"
    dataset_path.mkdir()

    for i in range(5):
        (dataset_path / f"img_{i}.png").touch()

    return dataset_path


# ============================================================================
# ScanConfig Tests
# ============================================================================


class TestScanConfig:
    """Tests for ScanConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ScanConfig()
        assert config.batch_size == 100
        assert config.checkpoint_every == 10
        assert config.recursive is True
        assert config.skip_hidden is True
        assert config.resume_from_checkpoint is True
        assert "*.png" in config.file_patterns
        assert "*.jpg" in config.file_patterns

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ScanConfig(
            batch_size=50,
            checkpoint_every=5,
            file_patterns=["*.tiff"],
            recursive=False,
            max_batches=10,
        )
        assert config.batch_size == 50
        assert config.checkpoint_every == 5
        assert config.file_patterns == ["*.tiff"]
        assert config.recursive is False
        assert config.max_batches == 10


# ============================================================================
# ScanBatch Tests
# ============================================================================


class TestScanBatch:
    """Tests for ScanBatch dataclass."""

    def test_creation(self, tmp_path: Path) -> None:
        """Test batch creation."""
        paths = [tmp_path / "a.png", tmp_path / "b.png"]
        batch = ScanBatch(
            batch_num=0,
            paths=paths,
            dataset_name="test",
            start_index=0,
        )
        assert batch.batch_num == 0
        assert batch.paths == paths
        assert batch.dataset_name == "test"
        assert len(batch) == 2
        assert batch.checkpoint_hash != ""

    def test_checkpoint_hash_consistency(self, tmp_path: Path) -> None:
        """Test that same batch produces same hash."""
        paths = [tmp_path / "a.png", tmp_path / "b.png"]

        batch1 = ScanBatch(batch_num=0, paths=paths, dataset_name="test", start_index=0)
        batch2 = ScanBatch(batch_num=0, paths=paths, dataset_name="test", start_index=0)

        assert batch1.checkpoint_hash == batch2.checkpoint_hash

    def test_different_batches_different_hash(self, tmp_path: Path) -> None:
        """Test that different batches produce different hashes."""
        paths1 = [tmp_path / "a.png"]
        paths2 = [tmp_path / "b.png"]

        batch1 = ScanBatch(
            batch_num=0, paths=paths1, dataset_name="test", start_index=0
        )
        batch2 = ScanBatch(
            batch_num=1, paths=paths2, dataset_name="test", start_index=1
        )

        assert batch1.checkpoint_hash != batch2.checkpoint_hash


# ============================================================================
# ScanProgress Tests
# ============================================================================


class TestScanProgress:
    """Tests for ScanProgress dataclass."""

    def test_percent_complete(self) -> None:
        """Test percent completion calculation."""
        progress = ScanProgress(total_files=100, files_processed=50)
        assert progress.percent_complete == pytest.approx(50.0)

        progress = ScanProgress(total_files=100, files_processed=0)
        assert progress.percent_complete == pytest.approx(0.0)

        progress = ScanProgress(total_files=0, files_processed=0)
        assert progress.percent_complete == pytest.approx(0.0)

    def test_all_fields(self) -> None:
        """Test all progress fields."""
        progress = ScanProgress(
            total_files=100,
            files_processed=75,
            batches_completed=7,
            batches_total=10,
            current_batch=7,
            elapsed_seconds=30.5,
            estimated_remaining=10.2,
            throughput=2.5,
        )
        assert progress.percent_complete == pytest.approx(75.0)
        assert progress.throughput == pytest.approx(2.5)


# ============================================================================
# ScanCheckpoint Tests
# ============================================================================


class TestScanCheckpoint:
    """Tests for ScanCheckpoint dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        checkpoint = ScanCheckpoint(
            dataset_name="test",
            dataset_path="/data/test",
            last_batch_completed=5,
            total_batches=10,
            files_processed=500,
            timestamp="2025-01-26T12:00:00",
            scan_hash="abc123",
        )
        result = checkpoint.to_dict()

        assert result["dataset_name"] == "test"
        assert result["last_batch_completed"] == 5
        assert result["files_processed"] == 500
        assert result["scan_hash"] == "abc123"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "dataset_name": "test",
            "dataset_path": "/data/test",
            "last_batch_completed": 5,
            "total_batches": 10,
            "files_processed": 500,
            "timestamp": "2025-01-26T12:00:00",
            "scan_hash": "abc123",
        }
        checkpoint = ScanCheckpoint.from_dict(data)

        assert checkpoint.dataset_name == "test"
        assert checkpoint.last_batch_completed == 5
        assert checkpoint.files_processed == 500

    def test_roundtrip(self) -> None:
        """Test to_dict -> from_dict roundtrip."""
        original = ScanCheckpoint(
            dataset_name="test",
            dataset_path="/data/test",
            last_batch_completed=5,
            total_batches=10,
            files_processed=500,
            timestamp="2025-01-26T12:00:00",
            scan_hash="abc123",
        )
        restored = ScanCheckpoint.from_dict(original.to_dict())

        assert restored.dataset_name == original.dataset_name
        assert restored.last_batch_completed == original.last_batch_completed
        assert restored.scan_hash == original.scan_hash


# ============================================================================
# BatchScanner Tests
# ============================================================================


class TestBatchScanner:
    """Tests for BatchScanner class."""

    def test_init_default_config(self) -> None:
        """Test scanner initialization with default config."""
        scanner = BatchScanner()
        assert scanner.config.batch_size == 100
        assert isinstance(scanner.progress_callback, LoggingProgressCallback)

    def test_init_custom_config(self) -> None:
        """Test scanner initialization with custom config."""
        config = ScanConfig(batch_size=50, checkpoint_every=5)
        scanner = BatchScanner(config=config)
        assert scanner.config.batch_size == 50
        assert scanner.config.checkpoint_every == 5

    def test_scan_yields_batches(self, sample_dataset: Path) -> None:
        """Test that scan yields batches of correct size."""
        config = ScanConfig(batch_size=10, checkpoint_every=100)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))

        # 35 total files, batch_size=10 → 4 batches (10+10+10+5)
        assert len(batches) == 4
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 10
        assert len(batches[3]) == 5

    def test_scan_batch_numbering(self, sample_dataset: Path) -> None:
        """Test that batches are numbered correctly."""
        config = ScanConfig(batch_size=10, checkpoint_every=100)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))

        for i, batch in enumerate(batches):
            assert batch.batch_num == i

    def test_scan_max_batches(self, sample_dataset: Path) -> None:
        """Test max_batches limit."""
        config = ScanConfig(batch_size=10, max_batches=2)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))

        assert len(batches) == 2

    def test_scan_non_recursive(self, sample_dataset: Path) -> None:
        """Test non-recursive scanning."""
        # Add file to root
        (sample_dataset / "root_image.png").touch()

        config = ScanConfig(batch_size=100, recursive=False)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))

        # Should only find root_image.png
        assert len(batches) == 1
        assert len(batches[0]) == 1

    def test_scan_skips_hidden(self, sample_dataset: Path) -> None:
        """Test that hidden files are skipped."""
        # Create hidden directory with images
        hidden_dir = sample_dataset / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.png").touch()

        config = ScanConfig(batch_size=100, skip_hidden=True)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))
        all_paths = [p for batch in batches for p in batch.paths]

        # No hidden files should be included
        assert not any(".hidden" in str(p) for p in all_paths)

    def test_scan_includes_hidden_when_disabled(self, sample_dataset: Path) -> None:
        """Test that hidden files are included when skip_hidden=False."""
        hidden_dir = sample_dataset / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.png").touch()

        config = ScanConfig(batch_size=100, skip_hidden=False)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(sample_dataset))
        all_paths = [p for batch in batches for p in batch.paths]

        # Hidden files should be included
        assert any(".hidden" in str(p) for p in all_paths)

    def test_mark_batch_complete(self, small_dataset: Path) -> None:
        """Test marking batches complete."""
        config = ScanConfig(batch_size=2, checkpoint_every=10)
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(small_dataset))
        scanner.mark_batch_complete(batches[0], total_files=5, total_batches=3)

        assert scanner._files_processed == 2
        assert scanner._batches_completed == 1

    def test_checkpoint_creation(self, small_dataset: Path, tmp_path: Path) -> None:
        """Test checkpoint file creation."""
        config = ScanConfig(
            batch_size=2,
            checkpoint_every=1,  # Checkpoint every batch
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(small_dataset))
        scanner.mark_batch_complete(batches[0], total_files=5, total_batches=3)

        # Check checkpoint file exists
        checkpoint_path = (
            tmp_path / "checkpoints" / "scan_small_dataset.checkpoint.json"
        )
        assert checkpoint_path.exists()

        # Verify content
        with open(checkpoint_path) as f:
            data = json.load(f)
        assert data["last_batch_completed"] == 0
        assert data["dataset_name"] == "small_dataset"

    def test_resume_from_checkpoint(self, small_dataset: Path, tmp_path: Path) -> None:
        """Test resuming from checkpoint."""
        checkpoint_dir = tmp_path / "checkpoints"
        config = ScanConfig(
            batch_size=2,
            checkpoint_every=1,
            checkpoint_dir=str(checkpoint_dir),
        )

        # First scan - process batches
        scanner1 = BatchScanner(config=config)
        batches1 = list(scanner1.scan(small_dataset))
        total_batches = len(batches1)

        # Mark first two batches complete
        scanner1.mark_batch_complete(
            batches1[0], total_files=5, total_batches=total_batches
        )
        scanner1.mark_batch_complete(
            batches1[1], total_files=5, total_batches=total_batches
        )

        # Manually update checkpoint with correct scan_hash for second scanner
        checkpoint_path = checkpoint_dir / "scan_small_dataset.checkpoint.json"
        assert checkpoint_path.exists(), "Checkpoint should exist"

        # Create new scanner with same config
        scanner2 = BatchScanner(config=config)

        # Compute the expected scan_hash for second scanner
        expected_hash = scanner2._compute_scan_hash(small_dataset, "small_dataset")

        # Update checkpoint with correct hash
        with open(checkpoint_path) as f:
            checkpoint_data = json.load(f)
        checkpoint_data["scan_hash"] = expected_hash
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f)

        # Second scan - should resume from batch 2
        batches2 = list(scanner2.scan(small_dataset))

        # Should skip first 2 batches (batch 0 and batch 1)
        assert len(batches2) == 1
        assert batches2[0].batch_num == 2

    def test_clear_checkpoint(self, small_dataset: Path, tmp_path: Path) -> None:
        """Test clearing checkpoint."""
        checkpoint_dir = tmp_path / "checkpoints"
        config = ScanConfig(
            batch_size=2,
            checkpoint_every=1,
            checkpoint_dir=str(checkpoint_dir),
        )

        scanner = BatchScanner(config=config)
        batches = list(scanner.scan(small_dataset))
        scanner.mark_batch_complete(batches[0], total_files=5, total_batches=3)

        # Clear checkpoint
        result = scanner.clear_checkpoint("small_dataset")
        assert result is True

        # Verify file is gone
        checkpoint_path = checkpoint_dir / "scan_small_dataset.checkpoint.json"
        assert not checkpoint_path.exists()

        # Clear again should return False
        result = scanner.clear_checkpoint("small_dataset")
        assert result is False

    def test_progress_callback_called(self, small_dataset: Path) -> None:
        """Test that progress callback methods are called."""
        mock_callback = MagicMock(spec=ProgressCallback)
        config = ScanConfig(batch_size=2)
        scanner = BatchScanner(config=config, progress_callback=mock_callback)

        batches = list(scanner.scan(small_dataset))
        for batch in batches:
            scanner.mark_batch_complete(batch, total_files=5, total_batches=3)

        # Verify callbacks
        mock_callback.on_scan_start.assert_called_once()
        assert mock_callback.on_batch_start.call_count == len(batches)
        assert mock_callback.on_batch_complete.call_count == len(batches)
        mock_callback.on_scan_complete.assert_called_once()

    def test_custom_file_patterns(self, tmp_path: Path) -> None:
        """Test custom file patterns."""
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "image.png").touch()
        (dataset / "image.tiff").touch()
        (dataset / "document.pdf").touch()

        config = ScanConfig(batch_size=100, file_patterns=["*.tiff"])
        scanner = BatchScanner(config=config)

        batches = list(scanner.scan(dataset))
        all_paths = [p for batch in batches for p in batch.paths]

        assert len(all_paths) == 1
        assert all_paths[0].suffix == ".tiff"


class TestLoggingProgressCallback:
    """Tests for LoggingProgressCallback class."""

    def test_on_scan_start(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test scan start logging."""
        callback = LoggingProgressCallback()

        with caplog.at_level("INFO"):
            callback.on_scan_start("test_dataset", 100)

        assert "scan_started" in caplog.text

    def test_on_batch_complete(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test batch complete logging."""
        callback = LoggingProgressCallback()
        batch = ScanBatch(
            batch_num=0,
            paths=[],
            dataset_name="test",
            start_index=0,
        )
        progress = ScanProgress(
            total_files=100,
            files_processed=10,
            throughput=2.5,
        )

        with caplog.at_level("INFO"):
            callback.on_batch_complete(batch, progress)

        assert "batch_completed" in caplog.text

    def test_on_scan_complete(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test scan complete logging."""
        callback = LoggingProgressCallback()
        progress = ScanProgress(
            total_files=100,
            files_processed=100,
            batches_completed=10,
            elapsed_seconds=30.5,
        )

        with caplog.at_level("INFO"):
            callback.on_scan_complete(progress)

        assert "scan_completed" in caplog.text
