"""Tests for streaming VLM labeling pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit.vlm_streaming_service import (
    BatchResult,
    LabelingTask,
    TaskStatus,
    create_task,
    generate_queue_status,
    list_tasks,
    load_checkpoints,
    load_task,
    save_checkpoint,
)


class TestLabelingTask:
    """Tests for LabelingTask dataclass."""

    def test_create(self) -> None:
        task = LabelingTask(
            task_id="test_field_001",
            dataset="test",
            target_field="domain_level1",
            total_images=100,
        )
        assert task.status == TaskStatus.PENDING
        assert task.progress_pct == 0.0
        assert task.remaining_batches == 10

    def test_progress(self) -> None:
        task = LabelingTask(
            task_id="t1",
            dataset="ds",
            target_field="f",
            total_images=50,
            completed_images=25,
        )
        assert task.progress_pct == 50.0

    def test_remaining_batches(self) -> None:
        task = LabelingTask(
            task_id="t1",
            dataset="ds",
            target_field="f",
            total_images=25,
            completed_images=10,
            batch_size=10,
        )
        assert task.remaining_batches == 2  # 15 remaining / 10 batch

    def test_to_dict(self) -> None:
        task = LabelingTask(
            task_id="t1",
            dataset="ds",
            target_field="f",
        )
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "pending"
        # Must be JSON-serializable
        json.dumps(d)


class TestCreateTask:
    """Tests for create_task."""

    def test_creates_and_persists(self, tmp_path: Path) -> None:
        task = create_task(
            "test-ds",
            "capture_method",
            total_images=50,
            queue_dir=tmp_path,
        )
        assert task.dataset == "test-ds"
        assert task.target_field == "capture_method"
        # File should exist
        path = tmp_path / f"{task.task_id}.json"
        assert path.exists()

    def test_unique_task_ids(self, tmp_path: Path) -> None:
        t1 = create_task("ds", "f1", queue_dir=tmp_path)
        t2 = create_task("ds", "f2", queue_dir=tmp_path)
        assert t1.task_id != t2.task_id


class TestLoadTask:
    """Tests for load_task."""

    def test_loads_persisted_task(self, tmp_path: Path) -> None:
        original = create_task(
            "test-ds",
            "domain_level1",
            total_images=100,
            batch_size=20,
            queue_dir=tmp_path,
        )
        loaded = load_task(original.task_id, queue_dir=tmp_path)
        assert loaded is not None
        assert loaded.dataset == "test-ds"
        assert loaded.total_images == 100
        assert loaded.batch_size == 20

    def test_returns_none_for_missing(self, tmp_path: Path) -> None:
        assert load_task("nonexistent", queue_dir=tmp_path) is None


class TestListTasks:
    """Tests for list_tasks."""

    def test_lists_all(self, tmp_path: Path) -> None:
        create_task("ds1", "f1", queue_dir=tmp_path)
        create_task("ds2", "f2", queue_dir=tmp_path)
        tasks = list_tasks(queue_dir=tmp_path)
        assert len(tasks) == 2

    def test_status_filter(self, tmp_path: Path) -> None:
        t1 = create_task("ds1", "f1", queue_dir=tmp_path)
        create_task("ds2", "f2", queue_dir=tmp_path)
        # Mark first task as completed
        t1.status = TaskStatus.COMPLETED
        t1.completed_images = t1.total_images
        from scripts.audit.vlm_streaming_service import _save_task

        _save_task(t1, queue_dir=tmp_path)

        pending = list_tasks(queue_dir=tmp_path, status_filter=TaskStatus.PENDING)
        completed = list_tasks(queue_dir=tmp_path, status_filter=TaskStatus.COMPLETED)
        assert len(pending) == 1
        assert len(completed) == 1

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list_tasks(queue_dir=tmp_path) == []


class TestCheckpoints:
    """Tests for checkpoint management."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        task = create_task(
            "ds",
            "field",
            total_images=30,
            batch_size=10,
            queue_dir=tmp_path,
        )
        batch = BatchResult(
            batch_index=0,
            image_ids=["img1", "img2", "img3"],
            labels={"img1": "scan", "img2": "photo", "img3": "scan"},
            processing_time_s=1.5,
        )
        save_checkpoint(task, batch, queue_dir=tmp_path)

        checkpoints = load_checkpoints(task.task_id, queue_dir=tmp_path)
        assert len(checkpoints) == 1
        assert checkpoints[0].batch_index == 0
        assert len(checkpoints[0].image_ids) == 3

    def test_updates_progress(self, tmp_path: Path) -> None:
        task = create_task(
            "ds",
            "field",
            total_images=20,
            batch_size=10,
            queue_dir=tmp_path,
        )
        batch = BatchResult(
            batch_index=0,
            image_ids=[f"img{i}" for i in range(10)],
        )
        save_checkpoint(task, batch, queue_dir=tmp_path)
        assert task.completed_images == 10
        assert task.status == TaskStatus.IN_PROGRESS

    def test_completes_when_done(self, tmp_path: Path) -> None:
        task = create_task(
            "ds",
            "field",
            total_images=5,
            batch_size=5,
            queue_dir=tmp_path,
        )
        batch = BatchResult(
            batch_index=0,
            image_ids=[f"img{i}" for i in range(5)],
        )
        save_checkpoint(task, batch, queue_dir=tmp_path)
        assert task.status == TaskStatus.COMPLETED

    def test_multiple_checkpoints(self, tmp_path: Path) -> None:
        task = create_task(
            "ds",
            "field",
            total_images=20,
            batch_size=10,
            queue_dir=tmp_path,
        )
        for i in range(2):
            batch = BatchResult(
                batch_index=i,
                image_ids=[f"img{i}_{j}" for j in range(10)],
            )
            save_checkpoint(task, batch, queue_dir=tmp_path)

        checkpoints = load_checkpoints(task.task_id, queue_dir=tmp_path)
        assert len(checkpoints) == 2
        assert task.completed_images == 20
        assert task.status == TaskStatus.COMPLETED


class TestGenerateQueueStatus:
    """Tests for generate_queue_status."""

    def test_empty_queue(self, tmp_path: Path) -> None:
        status = generate_queue_status(queue_dir=tmp_path)
        assert status["total_tasks"] == 0
        assert status["overall_progress_pct"] == 0.0

    def test_with_tasks(self, tmp_path: Path) -> None:
        create_task("ds1", "f1", total_images=100, queue_dir=tmp_path)
        create_task("ds2", "f2", total_images=50, queue_dir=tmp_path)
        status = generate_queue_status(queue_dir=tmp_path)
        assert status["total_tasks"] == 2
        assert status["total_images"] == 150
        assert status["completed_images"] == 0
