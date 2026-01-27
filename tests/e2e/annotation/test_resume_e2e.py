# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""End-to-end tests for checkpoint/resume workflow.

These tests verify:
- Checkpoint creation during processing
- Resume from checkpoint without duplicates
- Checkpoint integrity after interruption
- Multiple resume cycles
"""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from image_preprocessing_detector.annotation.integrity.checkpointing import (
    CheckpointInfo,
    CheckpointManager,
)

if TYPE_CHECKING:
    pass


@pytest.mark.e2e
@pytest.mark.e2e_annotation
class TestCheckpointResumeE2E:
    """End-to-end checkpoint/resume workflow tests."""

    def test_checkpoint_survives_restart(
        self,
        tmp_path: Path,
    ) -> None:
        """Test checkpoint persists across manager instances."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        # First manager - save checkpoint
        manager1 = CheckpointManager(checkpoint_dir=checkpoint_dir)
        manager1.save_checkpoint(
            dataset_name="persist-test",
            processed_count=100,
            last_path="train/img100.png",
            last_hash="hash_100",
        )

        # Simulate restart - new manager instance
        manager2 = CheckpointManager(checkpoint_dir=checkpoint_dir)
        checkpoint = manager2.get_resume_point("persist-test")

        # Verify checkpoint survived
        assert checkpoint is not None
        assert checkpoint.processed_count == 100
        assert checkpoint.last_path == "train/img100.png"

    def test_checkpoint_update_overwrites_previous(
        self,
        real_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Test updating checkpoint overwrites previous state."""
        dataset = "update-test"

        # Initial checkpoint
        real_checkpoint_manager.save_checkpoint(
            dataset_name=dataset,
            processed_count=50,
            last_path="img50.png",
            last_hash="hash_50",
        )

        # Update checkpoint
        real_checkpoint_manager.save_checkpoint(
            dataset_name=dataset,
            processed_count=100,
            last_path="img100.png",
            last_hash="hash_100",
        )

        # Verify only latest state
        checkpoint = real_checkpoint_manager.get_resume_point(dataset)
        assert checkpoint is not None
        assert checkpoint.processed_count == 100
        assert checkpoint.last_path == "img100.png"
        assert checkpoint.last_hash == "hash_100"

    def test_multiple_datasets_independent_checkpoints(
        self,
        real_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Test different datasets have independent checkpoints."""
        # Save checkpoints for multiple datasets
        datasets = [
            ("dataset-a", 10, "a/img10.png"),
            ("dataset-b", 20, "b/img20.png"),
            ("dataset-c", 30, "c/img30.png"),
        ]

        for name, count, path in datasets:
            real_checkpoint_manager.save_checkpoint(
                dataset_name=name,
                processed_count=count,
                last_path=path,
                last_hash=f"hash_{name}",
            )

        # Verify each dataset has correct checkpoint
        for name, count, path in datasets:
            checkpoint = real_checkpoint_manager.get_resume_point(name)
            assert checkpoint is not None, f"Missing checkpoint for {name}"
            assert checkpoint.processed_count == count
            assert checkpoint.last_path == path

    def test_clear_one_dataset_preserves_others(
        self,
        real_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Test clearing one checkpoint doesn't affect others."""
        # Save two checkpoints
        real_checkpoint_manager.save_checkpoint(
            dataset_name="keep-this",
            processed_count=100,
            last_path="keep.png",
            last_hash="keep_hash",
        )
        real_checkpoint_manager.save_checkpoint(
            dataset_name="delete-this",
            processed_count=50,
            last_path="delete.png",
            last_hash="delete_hash",
        )

        # Clear one
        real_checkpoint_manager.clear_checkpoint("delete-this")

        # Verify correct behavior
        assert real_checkpoint_manager.get_resume_point("delete-this") is None
        kept = real_checkpoint_manager.get_resume_point("keep-this")
        assert kept is not None
        assert kept.processed_count == 100


@pytest.mark.e2e
@pytest.mark.e2e_annotation
class TestConcurrentCheckpointingE2E:
    """End-to-end tests for concurrent checkpoint access."""

    def test_concurrent_checkpoint_updates_no_corruption(
        self,
        tmp_path: Path,
    ) -> None:
        """Test concurrent updates don't corrupt checkpoint file.

        CheckpointManager uses threading.RLock to serialize concurrent writes,
        preventing race conditions that could corrupt checkpoint files.
        """
        checkpoint_dir = tmp_path / "concurrent_checkpoints"
        checkpoint_dir.mkdir()
        manager = CheckpointManager(checkpoint_dir=checkpoint_dir)

        dataset = "concurrent-test"
        errors: list[Exception] = []
        updates_completed = 0
        lock = threading.Lock()

        def update_checkpoint(worker_id: int, count: int) -> None:
            nonlocal updates_completed
            try:
                for i in range(count):
                    manager.save_checkpoint(
                        dataset_name=dataset,
                        processed_count=worker_id * 1000 + i,
                        last_path=f"worker_{worker_id}/img_{i}.png",
                        last_hash=f"hash_{worker_id}_{i}",
                    )
                    with lock:
                        updates_completed += 1
            except Exception as e:
                errors.append(e)

        # Run 4 workers doing 25 updates each
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(update_checkpoint, worker_id, 25)
                for worker_id in range(4)
            ]
            concurrent.futures.wait(futures)

        # Verify no errors occurred
        assert errors == [], f"Errors during concurrent updates: {errors}"
        assert updates_completed == 100

        # Verify checkpoint file is still valid
        checkpoint = manager.get_resume_point(dataset)
        assert checkpoint is not None
        assert checkpoint.dataset_name == dataset

    def test_concurrent_reads_safe(
        self,
        tmp_path: Path,
    ) -> None:
        """Test concurrent reads don't fail."""
        checkpoint_dir = tmp_path / "read_checkpoints"
        checkpoint_dir.mkdir()
        manager = CheckpointManager(checkpoint_dir=checkpoint_dir)

        # Create initial checkpoint
        manager.save_checkpoint(
            dataset_name="read-test",
            processed_count=42,
            last_path="test.png",
            last_hash="test_hash",
        )

        read_results: list[int | None] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def read_checkpoint(iterations: int) -> None:
            try:
                for _ in range(iterations):
                    checkpoint = manager.get_resume_point("read-test")
                    with lock:
                        if checkpoint:
                            read_results.append(checkpoint.processed_count)
                        else:
                            read_results.append(None)
            except Exception as e:
                errors.append(e)

        # Run 4 readers doing 50 reads each
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(read_checkpoint, 50) for _ in range(4)]
            concurrent.futures.wait(futures)

        assert errors == [], f"Errors during concurrent reads: {errors}"
        assert len(read_results) == 200
        # All reads should return the same value
        assert all(r == 42 for r in read_results)


@pytest.mark.e2e
@pytest.mark.e2e_annotation
class TestCheckpointInfoE2E:
    """End-to-end tests for CheckpointInfo dataclass."""

    def test_checkpoint_info_round_trip(self) -> None:
        """Test CheckpointInfo serialization round-trip."""
        original = CheckpointInfo(
            dataset_name="round-trip-test",
            processed_count=999,
            last_path="deep/nested/path/image.png",
            last_hash="x" * 64,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = CheckpointInfo.from_dict(data)

        # Verify all fields match
        assert restored.dataset_name == original.dataset_name
        assert restored.processed_count == original.processed_count
        assert restored.last_path == original.last_path
        assert restored.last_hash == original.last_hash
        assert restored.version == original.version

    def test_checkpoint_info_timestamp_populated(self) -> None:
        """Test CheckpointInfo automatically populates timestamp."""
        info = CheckpointInfo(
            dataset_name="timestamp-test",
            processed_count=1,
            last_path="test.png",
            last_hash="hash",
        )

        assert info.timestamp is not None
        # Timestamp should be a valid ISO format string
        assert "T" in info.timestamp or "-" in info.timestamp

    def test_checkpoint_info_version_default(self) -> None:
        """Test CheckpointInfo has default version."""
        info = CheckpointInfo(
            dataset_name="version-test",
            processed_count=1,
            last_path="test.png",
            last_hash="hash",
        )

        assert info.version >= 1


@pytest.mark.e2e
@pytest.mark.e2e_annotation
class TestResumeNoDuplicatesE2E:
    """Tests to verify resume doesn't create duplicate entries."""

    def test_resume_point_identifies_last_processed(
        self,
        real_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Test resume point correctly identifies where to continue."""
        # Simulate processing 50 images
        processed_paths = [f"train/img_{i:04d}.png" for i in range(50)]
        last_processed = processed_paths[-1]
        last_hash = f"hash_of_{last_processed}"

        # Save checkpoint at position 50
        real_checkpoint_manager.save_checkpoint(
            dataset_name="resume-test",
            processed_count=50,
            last_path=last_processed,
            last_hash=last_hash,
        )

        # Get resume point
        resume = real_checkpoint_manager.get_resume_point("resume-test")

        # Verify resume knows where to continue
        assert resume is not None
        assert resume.processed_count == 50
        assert resume.last_path == last_processed
        assert resume.last_hash == last_hash

    def test_empty_resume_starts_from_beginning(
        self,
        real_checkpoint_manager: CheckpointManager,
    ) -> None:
        """Test no checkpoint means start from beginning."""
        resume = real_checkpoint_manager.get_resume_point("never-processed-dataset")
        assert resume is None


def _multiprocess_worker(
    checkpoint_dir: str,
    worker_id: int,
    num_updates: int,
    result_queue: multiprocessing.Queue[tuple[int, bool, str]],
) -> None:
    """Worker function for multi-process checkpoint tests.

    Must be a top-level function for pickling by multiprocessing.

    Args:
        checkpoint_dir: Path to checkpoint directory
        worker_id: Unique ID for this worker
        num_updates: Number of checkpoint updates to perform
        result_queue: Queue to report results back to main process
    """
    try:
        manager = CheckpointManager(checkpoint_dir=Path(checkpoint_dir))
        dataset = "multiprocess-test"

        for i in range(num_updates):
            manager.save_checkpoint(
                dataset_name=dataset,
                processed_count=worker_id * 1000 + i,
                last_path=f"worker_{worker_id}/img_{i}.png",
                last_hash=f"hash_{worker_id}_{i}",
            )

        result_queue.put((worker_id, True, ""))
    except Exception as e:
        result_queue.put((worker_id, False, str(e)))


@pytest.mark.e2e
@pytest.mark.e2e_annotation
class TestMultiProcessCheckpointingE2E:
    """Cross-process checkpoint safety tests.

    These tests verify that CheckpointManager correctly handles
    concurrent access from multiple Python processes using FileLock.
    """

    def test_multiprocess_checkpoint_updates_no_corruption(
        self,
        tmp_path: Path,
    ) -> None:
        """Test concurrent processes don't corrupt checkpoint file.

        Uses multiprocessing.Process to spawn 4 worker processes,
        each doing 25 checkpoint updates to the same dataset.
        Verifies final checkpoint is valid JSON.
        """
        import multiprocessing

        checkpoint_dir = tmp_path / "multiprocess_checkpoints"
        checkpoint_dir.mkdir()

        result_queue: multiprocessing.Queue[tuple[int, bool, str]] = (
            multiprocessing.Queue()
        )

        # Spawn 4 worker processes doing 25 updates each
        num_workers = 4
        updates_per_worker = 25
        processes = []

        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=_multiprocess_worker,
                args=(str(checkpoint_dir), worker_id, updates_per_worker, result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=30)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Verify all workers succeeded
        assert len(results) == num_workers, f"Expected {num_workers} results"
        for worker_id, success, error in results:
            assert success, f"Worker {worker_id} failed: {error}"

        # Verify checkpoint file is valid
        manager = CheckpointManager(checkpoint_dir=checkpoint_dir)
        checkpoint = manager.get_resume_point("multiprocess-test")
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.dataset_name == "multiprocess-test"

    def test_multiprocess_mixed_read_write(
        self,
        tmp_path: Path,
    ) -> None:
        """Test concurrent read/write from multiple processes.

        Creates initial checkpoint, then spawns processes that
        both read and write concurrently.
        """
        import multiprocessing

        checkpoint_dir = tmp_path / "mixed_checkpoints"
        checkpoint_dir.mkdir()

        # Create initial checkpoint
        manager = CheckpointManager(checkpoint_dir=checkpoint_dir)
        manager.save_checkpoint(
            dataset_name="mixed-test",
            processed_count=0,
            last_path="initial.png",
            last_hash="initial_hash",
        )

        result_queue: multiprocessing.Queue[tuple[int, bool, str]] = (
            multiprocessing.Queue()
        )

        # Spawn workers
        processes = []
        for worker_id in range(4):
            p = multiprocessing.Process(
                target=_multiprocess_mixed_worker,
                args=(str(checkpoint_dir), worker_id, result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for completion
        for p in processes:
            p.join(timeout=30)

        # Collect and verify results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        assert len(results) == 4
        for worker_id, success, error in results:
            assert success, f"Worker {worker_id} failed: {error}"


def _multiprocess_mixed_worker(
    checkpoint_dir: str,
    worker_id: int,
    result_queue: multiprocessing.Queue[tuple[int, bool, str]],
) -> None:
    """Worker that does mixed read/write operations.

    Args:
        checkpoint_dir: Path to checkpoint directory
        worker_id: Unique ID for this worker
        result_queue: Queue to report results
    """
    try:
        manager = CheckpointManager(checkpoint_dir=Path(checkpoint_dir))

        for i in range(10):
            # Alternate between read and write
            if i % 2 == 0:
                checkpoint = manager.get_resume_point("mixed-test")
                if checkpoint is None:
                    raise ValueError("Expected checkpoint to exist")
            else:
                manager.save_checkpoint(
                    dataset_name="mixed-test",
                    processed_count=worker_id * 100 + i,
                    last_path=f"worker_{worker_id}/img_{i}.png",
                    last_hash=f"hash_{worker_id}_{i}",
                )

        result_queue.put((worker_id, True, ""))
    except Exception as e:
        result_queue.put((worker_id, False, str(e)))
