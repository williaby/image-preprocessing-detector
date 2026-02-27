"""Tests for checkpoint management including edge cases.

Tests CheckpointManager, BatchCheckpointManager, and validation features
for resumable processing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.integrity.checkpointing import (
    BatchCheckpointInfo,
    BatchCheckpointManager,
    CheckpointInfo,
    CheckpointManager,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    """Create checkpoint directory."""
    return tmp_path / "checkpoints"


@pytest.fixture
def manager(checkpoint_dir: Path) -> CheckpointManager:
    """Create CheckpointManager instance."""
    return CheckpointManager(checkpoint_dir)


@pytest.fixture
def batch_manager(checkpoint_dir: Path) -> BatchCheckpointManager:
    """Create BatchCheckpointManager instance."""
    return BatchCheckpointManager(
        checkpoint_dir=checkpoint_dir,
        batch_size=32,
        checkpoint_interval=10,
    )


@pytest.fixture
def sample_images(tmp_path: Path) -> list[Path]:
    """Create sample image files for testing."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    paths = []
    for i in range(100):
        img_path = images_dir / f"img_{i:04d}.jpg"
        img_path.write_bytes(f"image_content_{i}".encode())
        paths.append(img_path)

    return paths


def compute_test_hash(path: Path) -> str:
    """Compute SHA256 hash for test files."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# =============================================================================
# Unit Tests - CheckpointInfo
# =============================================================================


class TestCheckpointInfo:
    """Tests for CheckpointInfo dataclass."""

    def test_create_checkpoint(self) -> None:
        """Test creating checkpoint info."""
        info = CheckpointInfo(
            dataset_name="test",
            processed_count=100,
            last_path="train/img100.jpg",
            last_hash="abc123",
        )

        assert info.dataset_name == "test"
        assert info.processed_count == 100
        assert info.last_path == "train/img100.jpg"
        assert info.last_hash == "abc123"
        assert info.version == 1

    def test_timestamp_auto_generated(self) -> None:
        """Test timestamp is auto-generated."""
        info = CheckpointInfo(
            dataset_name="test",
            processed_count=0,
            last_path="",
            last_hash="",
        )

        # Should be valid ISO timestamp
        assert info.timestamp
        datetime.fromisoformat(info.timestamp)

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        info = CheckpointInfo(
            dataset_name="test",
            processed_count=50,
            last_path="path.jpg",
            last_hash="hash",
            timestamp="2025-01-01T00:00:00+00:00",
            version=1,
        )

        d = info.to_dict()

        assert d["dataset_name"] == "test"
        assert d["processed_count"] == 50
        assert d["version"] == 1

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "dataset_name": "test",
            "processed_count": 75,
            "last_path": "path.jpg",
            "last_hash": "hash123",
            "timestamp": "2025-01-01T00:00:00+00:00",
            "version": 1,
        }

        info = CheckpointInfo.from_dict(d)

        assert info.dataset_name == "test"
        assert info.processed_count == 75
        assert info.last_hash == "hash123"

    def test_from_dict_missing_optional(self) -> None:
        """Test from_dict with missing optional fields."""
        d = {
            "dataset_name": "test",
            "processed_count": 0,
            "last_path": "path.jpg",
            "last_hash": "hash",
        }

        info = CheckpointInfo.from_dict(d)

        assert info.version == 1  # Default


# =============================================================================
# Unit Tests - CheckpointManager
# =============================================================================


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    def test_creates_checkpoint_dir(self, tmp_path: Path) -> None:
        """Test checkpoint directory is created."""
        dir_path = tmp_path / "nested" / "checkpoints"
        CheckpointManager(dir_path)

        assert dir_path.exists()
        assert dir_path.is_dir()

    def test_save_and_get_checkpoint(self, manager: CheckpointManager) -> None:
        """Test saving and retrieving checkpoint."""
        manager.save_checkpoint(
            dataset_name="test-dataset",
            processed_count=500,
            last_path="train/img500.jpg",
            last_hash="abc123def456",
        )

        checkpoint = manager.get_resume_point("test-dataset")

        assert checkpoint is not None
        assert checkpoint.dataset_name == "test-dataset"
        assert checkpoint.processed_count == 500
        assert checkpoint.last_hash == "abc123def456"

    def test_get_checkpoint_not_exists(self, manager: CheckpointManager) -> None:
        """Test getting non-existent checkpoint returns None."""
        result = manager.get_resume_point("nonexistent")

        assert result is None

    def test_clear_checkpoint(self, manager: CheckpointManager) -> None:
        """Test clearing checkpoint."""
        manager.save_checkpoint("test", 100, "path.jpg", "hash")

        assert manager.get_resume_point("test") is not None

        cleared = manager.clear_checkpoint("test")

        assert cleared is True
        assert manager.get_resume_point("test") is None

    def test_clear_nonexistent_checkpoint(self, manager: CheckpointManager) -> None:
        """Test clearing non-existent checkpoint returns False."""
        result = manager.clear_checkpoint("nonexistent")

        assert result is False

    def test_list_checkpoints(self, manager: CheckpointManager) -> None:
        """Test listing all checkpoints."""
        manager.save_checkpoint("dataset1", 100, "path1.jpg", "hash1")
        manager.save_checkpoint("dataset2", 200, "path2.jpg", "hash2")
        manager.save_checkpoint("dataset3", 300, "path3.jpg", "hash3")

        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 3
        names = [c.dataset_name for c in checkpoints]
        assert "dataset1" in names
        assert "dataset2" in names
        assert "dataset3" in names

    def test_get_stats(self, manager: CheckpointManager) -> None:
        """Test getting checkpoint statistics."""
        manager.save_checkpoint("test", 100, "path.jpg", "hash")

        stats = manager.get_stats()

        assert stats["total_checkpoints"] == 1
        assert "test" in stats["datasets"]

    def test_checkpoint_path_sanitized(self, manager: CheckpointManager) -> None:
        """Test checkpoint path handles special characters."""
        # Names with special characters
        manager.save_checkpoint("test/with/slashes", 100, "path.jpg", "hash")
        manager.save_checkpoint("test\\with\\backslashes", 100, "path.jpg", "hash")

        assert manager.get_resume_point("test/with/slashes") is not None
        assert manager.get_resume_point("test\\with\\backslashes") is not None

    def test_atomic_write_corruption_protection(
        self, manager: CheckpointManager, checkpoint_dir: Path
    ) -> None:
        """Test checkpoint survives interrupted writes."""
        # Save initial checkpoint
        manager.save_checkpoint("test", 100, "path1.jpg", "hash1")

        # Get checkpoint file path
        checkpoint_file = checkpoint_dir / "test.checkpoint.json"
        checkpoint_file.read_text()

        # Save second checkpoint
        manager.save_checkpoint("test", 200, "path2.jpg", "hash2")

        # Verify update
        checkpoint = manager.get_resume_point("test")
        assert checkpoint is not None
        assert checkpoint.processed_count == 200


# =============================================================================
# Unit Tests - Validated Resume
# =============================================================================


class TestValidatedResume:
    """Tests for hash-based checkpoint validation."""

    def test_no_checkpoint_returns_valid(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test no checkpoint returns valid with index 0."""
        result = manager.get_validated_resume_point("test", sample_images)

        assert result.is_valid
        assert result.resume_index == 0
        assert result.checkpoint is None

    def test_valid_checkpoint_by_path(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test checkpoint validation by path match."""
        # Save checkpoint at index 50
        manager.save_checkpoint(
            "test",
            50,
            str(sample_images[49]),
            compute_test_hash(sample_images[49]),
        )

        result = manager.get_validated_resume_point("test", sample_images)

        assert result.is_valid
        assert result.resume_index == 50  # Resume from next

    def test_valid_checkpoint_by_filename(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test checkpoint validation by filename match."""
        # Save checkpoint with just filename
        manager.save_checkpoint(
            "test",
            50,
            sample_images[49].name,  # Just filename
            compute_test_hash(sample_images[49]),
        )

        result = manager.get_validated_resume_point("test", sample_images)

        assert result.is_valid
        assert result.resume_index == 50

    def test_invalid_checkpoint_file_not_found(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test checkpoint invalid when file not in list."""
        manager.save_checkpoint(
            "test",
            50,
            "nonexistent_file.jpg",
            "somehash",
        )

        result = manager.get_validated_resume_point("test", sample_images)

        assert not result.is_valid
        assert result.resume_index == 0
        assert "not found" in result.reason

    def test_invalid_checkpoint_hash_mismatch(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test checkpoint invalid when hash doesn't match."""
        manager.save_checkpoint(
            "test",
            50,
            str(sample_images[49]),
            "wrong_hash_value",
        )

        result = manager.get_validated_resume_point(
            "test",
            sample_images,
            compute_hash=compute_test_hash,
        )

        assert not result.is_valid
        assert "Hash mismatch" in result.reason

    def test_valid_with_hash_verification(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test valid checkpoint with hash verification."""
        idx = 25
        manager.save_checkpoint(
            "test",
            idx,
            str(sample_images[idx - 1]),
            compute_test_hash(sample_images[idx - 1]),
        )

        result = manager.get_validated_resume_point(
            "test",
            sample_images,
            compute_hash=compute_test_hash,
        )

        assert result.is_valid
        assert result.resume_index == idx


# =============================================================================
# Unit Tests - BatchCheckpointManager
# =============================================================================


class TestBatchCheckpointManager:
    """Tests for BatchCheckpointManager class."""

    def test_update_defers_save(self, batch_manager: BatchCheckpointManager) -> None:
        """Test updates are deferred until interval."""
        # Update less than checkpoint_interval times
        for i in range(5):
            saved = batch_manager.update(
                "test", batch_idx=i, last_path=f"img{i}.jpg", last_hash=f"hash{i}"
            )
            assert not saved  # Should defer

    def test_update_saves_at_interval(
        self, batch_manager: BatchCheckpointManager
    ) -> None:
        """Test checkpoint saved at interval."""
        saved_count = 0

        for i in range(15):
            if batch_manager.update(
                "test", batch_idx=i, last_path=f"img{i}.jpg", last_hash=f"hash{i}"
            ):
                saved_count += 1

        # Should have saved once at interval 10
        assert saved_count == 1

    def test_update_with_force(self, batch_manager: BatchCheckpointManager) -> None:
        """Test force flag triggers immediate save."""
        saved = batch_manager.update(
            "test",
            batch_idx=1,
            last_path="img1.jpg",
            last_hash="hash1",
            force=True,
        )

        assert saved

    def test_flush_saves_pending(self, batch_manager: BatchCheckpointManager) -> None:
        """Test flush saves pending checkpoints."""
        # Update without reaching interval
        batch_manager.update("test1", 1, "img1.jpg", "hash1")
        batch_manager.update("test2", 1, "img2.jpg", "hash2")

        saved = batch_manager.flush()

        assert saved == 2

    def test_flush_specific_dataset(
        self, batch_manager: BatchCheckpointManager
    ) -> None:
        """Test flush specific dataset only."""
        batch_manager.update("test1", 1, "img1.jpg", "hash1")
        batch_manager.update("test2", 1, "img2.jpg", "hash2")

        saved = batch_manager.flush("test1")

        assert saved == 1

    def test_get_batch_resume_point(
        self, batch_manager: BatchCheckpointManager
    ) -> None:
        """Test getting batch-aware resume point."""
        batch_manager.update("test", 5, "img5.jpg", "hash5", force=True)

        checkpoint = batch_manager.get_batch_resume_point("test")

        assert checkpoint is not None
        assert isinstance(checkpoint, BatchCheckpointInfo)
        assert checkpoint.batch_idx == 5
        assert checkpoint.batch_size == 32

    def test_get_progress(self, batch_manager: BatchCheckpointManager) -> None:
        """Test getting progress info."""
        batch_manager.update(
            "test",
            batch_idx=5,
            last_path="img5.jpg",
            last_hash="hash5",
            total_batches=10,
            force=True,
        )

        progress = batch_manager.get_progress("test")

        assert progress["has_checkpoint"]
        assert progress["batch_idx"] == 5
        assert progress["total_batches"] == 10
        assert progress["percentage"] == pytest.approx(50.0)

    def test_get_progress_no_checkpoint(
        self, batch_manager: BatchCheckpointManager
    ) -> None:
        """Test progress with no checkpoint."""
        progress = batch_manager.get_progress("nonexistent")

        assert not progress["has_checkpoint"]
        assert progress["batch_idx"] == 0

    def test_legacy_checkpoint_conversion(
        self, batch_manager: BatchCheckpointManager, checkpoint_dir: Path
    ) -> None:
        """Test legacy checkpoint is converted to batch format."""
        # Create legacy checkpoint (version 1)
        legacy_data = {
            "dataset_name": "test",
            "processed_count": 160,
            "last_path": "img160.jpg",
            "last_hash": "hash160",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": 1,
        }
        checkpoint_file = checkpoint_dir / "test.checkpoint.json"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, "w") as f:
            json.dump(legacy_data, f)

        checkpoint = batch_manager.get_batch_resume_point("test")

        assert checkpoint is not None
        assert checkpoint.version == 2
        # 160 items / 32 batch_size = 5 batches
        assert checkpoint.batch_idx == 5


# =============================================================================
# Unit Tests - BatchCheckpointInfo
# =============================================================================


class TestBatchCheckpointInfo:
    """Tests for BatchCheckpointInfo dataclass."""

    def test_create_batch_checkpoint(self) -> None:
        """Test creating batch checkpoint info."""
        info = BatchCheckpointInfo(
            dataset_name="test",
            processed_count=320,
            last_path="img320.jpg",
            last_hash="hash",
            batch_idx=10,
            batch_size=32,
            total_batches=100,
        )

        assert info.batch_idx == 10
        assert info.batch_size == 32
        assert info.total_batches == 100
        assert info.version == 2  # Batch checkpoints default to version 2

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        d = {
            "dataset_name": "test",
            "processed_count": 320,
            "last_path": "img320.jpg",
            "last_hash": "hash",
            "timestamp": "2025-01-01T00:00:00+00:00",
            "version": 2,
            "batch_idx": 10,
            "batch_size": 32,
            "total_batches": 100,
            "items_in_current_batch": 32,
        }

        info = BatchCheckpointInfo.from_dict(d)

        assert info.batch_idx == 10
        assert info.total_batches == 100


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestCheckpointEdgeCases:
    """Edge case tests for checkpoint system."""

    def test_empty_image_list_validation(self, manager: CheckpointManager) -> None:
        """Test validation with empty image list."""
        manager.save_checkpoint("test", 50, "img.jpg", "hash")

        result = manager.get_validated_resume_point("test", [])

        assert not result.is_valid
        assert "not found" in result.reason

    def test_checkpoint_at_last_image(
        self, manager: CheckpointManager, sample_images: list[Path]
    ) -> None:
        """Test checkpoint at last image in list."""
        last_idx = len(sample_images) - 1
        manager.save_checkpoint(
            "test",
            last_idx + 1,
            str(sample_images[last_idx]),
            compute_test_hash(sample_images[last_idx]),
        )

        result = manager.get_validated_resume_point(
            "test", sample_images, compute_test_hash
        )

        assert result.is_valid
        # Resume index should be past the end
        assert result.resume_index == len(sample_images)

    def test_corrupted_checkpoint_file(
        self, manager: CheckpointManager, checkpoint_dir: Path
    ) -> None:
        """Test handling of corrupted checkpoint file."""
        # Create corrupted file
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        bad_file = checkpoint_dir / "test.checkpoint.json"
        bad_file.write_text("not valid json {")

        result = manager.get_resume_point("test")

        assert result is None  # Should handle gracefully

    def test_missing_fields_in_checkpoint(
        self, manager: CheckpointManager, checkpoint_dir: Path
    ) -> None:
        """Test handling of checkpoint with missing fields."""
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        bad_file = checkpoint_dir / "test.checkpoint.json"
        bad_file.write_text('{"dataset_name": "test"}')  # Missing required fields

        result = manager.get_resume_point("test")

        assert result is None

    def test_concurrent_updates_same_dataset(
        self, batch_manager: BatchCheckpointManager
    ) -> None:
        """Test rapid updates to same dataset don't corrupt."""
        # Rapid updates
        for i in range(100):
            batch_manager.update(
                "test",
                batch_idx=i,
                last_path=f"img{i}.jpg",
                last_hash=f"hash{i}",
            )

        batch_manager.flush("test")
        checkpoint = batch_manager.get_batch_resume_point("test")

        assert checkpoint is not None
        assert checkpoint.batch_idx == 99

    def test_unicode_in_paths(self, manager: CheckpointManager) -> None:
        """Test checkpoint with unicode characters in paths."""
        manager.save_checkpoint(
            "test",
            50,
            "données/图片/画像.jpg",  # French, Chinese, Japanese
            "hash",
        )

        checkpoint = manager.get_resume_point("test")

        assert checkpoint is not None
        assert "画像.jpg" in checkpoint.last_path

    def test_very_long_hash(self, manager: CheckpointManager) -> None:
        """Test checkpoint with very long hash."""
        long_hash = "a" * 1000

        manager.save_checkpoint("test", 50, "img.jpg", long_hash)

        checkpoint = manager.get_resume_point("test")
        assert checkpoint is not None
        assert checkpoint.last_hash == long_hash

    def test_zero_processed_count(self, manager: CheckpointManager) -> None:
        """Test checkpoint with zero processed count."""
        manager.save_checkpoint("test", 0, "", "")

        checkpoint = manager.get_resume_point("test")

        assert checkpoint is not None
        assert checkpoint.processed_count == 0

    def test_fsync_mode(self, checkpoint_dir: Path) -> None:
        """Test checkpoint manager with fsync enabled."""
        manager = CheckpointManager(checkpoint_dir, fsync=True)

        manager.save_checkpoint("test", 100, "img.jpg", "hash")

        checkpoint = manager.get_resume_point("test")
        assert checkpoint is not None

    def test_batch_interval_one(self, checkpoint_dir: Path) -> None:
        """Test batch manager with interval of 1 (save every batch)."""
        manager = BatchCheckpointManager(
            checkpoint_dir, batch_size=10, checkpoint_interval=1
        )

        saved_count = 0
        for i in range(5):
            if manager.update("test", i, f"img{i}.jpg", f"hash{i}"):
                saved_count += 1

        assert saved_count == 5  # Every update should save
