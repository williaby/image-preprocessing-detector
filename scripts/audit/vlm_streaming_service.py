"""Streaming VLM labeling pipeline for async audit operations.

Provides a task queue for VLM labeling outside of interactive Claude
sessions, with checkpoint/resume support and configurable batch size.

This module defines the data structures and queue management logic.
Actual VLM API calls are delegated to model-specific adapters.

Usage::

    # Create a labeling task
    python scripts/audit/vlm_streaming_service.py --create \\
        --dataset jssoda --field capture_method --batch-size 10

    # Resume processing
    python scripts/audit/vlm_streaming_service.py --resume \\
        --task-id jssoda_capture_method_20260214

    # Show queue status
    python scripts/audit/vlm_streaming_service.py --status
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"
VLM_QUEUE_DIR = AUDIT_RESULTS_DIR / "vlm_queue"


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    """VLM labeling task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class LabelingTask:
    """A VLM labeling task for a dataset field.

    Attributes:
        task_id: Unique task identifier.
        dataset: Target dataset name.
        target_field: Field being labeled.
        model: VLM model identifier.
        batch_size: Images per batch.
        total_images: Total images to label.
        completed_images: Images labeled so far.
        status: Current task status.
        created_at: Task creation timestamp.
        updated_at: Last update timestamp.
        checkpoint_path: Path to last checkpoint.
        error_message: Last error (if failed).
    """

    task_id: str
    dataset: str
    target_field: str
    model: str = "claude-opus-4-6"
    batch_size: int = 10
    total_images: int = 0
    completed_images: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    updated_at: str = ""
    checkpoint_path: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    @property
    def progress_pct(self) -> float:
        """Completion percentage."""
        if self.total_images == 0:
            return 0.0
        return 100.0 * self.completed_images / self.total_images

    @property
    def remaining_batches(self) -> int:
        """Number of batches remaining."""
        remaining = self.total_images - self.completed_images
        if remaining <= 0:
            return 0
        return (remaining + self.batch_size - 1) // self.batch_size

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = asdict(self)
        d["status"] = self.status.value
        d["progress_pct"] = self.progress_pct
        d["remaining_batches"] = self.remaining_batches
        return d


@dataclass
class BatchResult:
    """Result of processing a single batch.

    Attributes:
        batch_index: 0-based batch number.
        image_ids: Image identifiers in this batch.
        labels: Model-assigned labels.
        confidences: Per-label confidence scores.
        processing_time_s: Wall-clock time for this batch.
    """

    batch_index: int
    image_ids: list[str]
    labels: dict[str, Any] = field(default_factory=dict)
    confidences: dict[str, float] = field(default_factory=dict)
    processing_time_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Queue management
# ---------------------------------------------------------------------------
def _queue_dir(base: Path | None = None) -> Path:
    """Get the VLM queue directory."""
    return base or VLM_QUEUE_DIR


def create_task(
    dataset: str,
    target_field: str,
    *,
    model: str = "claude-opus-4-6",
    batch_size: int = 10,
    total_images: int = 0,
    queue_dir: Path | None = None,
) -> LabelingTask:
    """Create a new labeling task and persist to queue.

    Args:
        dataset: Target dataset name.
        target_field: Field to label.
        model: VLM model to use.
        batch_size: Images per batch.
        total_images: Total images to process.
        queue_dir: Override queue directory.

    Returns:
        The created LabelingTask.
    """
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    task_id = f"{dataset}_{target_field}_{ts}"

    task = LabelingTask(
        task_id=task_id,
        dataset=dataset,
        target_field=target_field,
        model=model,
        batch_size=batch_size,
        total_images=total_images,
    )

    _save_task(task, queue_dir=queue_dir)
    log.info("Created task %s", task_id)
    return task


def _save_task(
    task: LabelingTask,
    *,
    queue_dir: Path | None = None,
) -> Path:
    """Persist task state to disk."""
    qdir = _queue_dir(queue_dir)
    qdir.mkdir(parents=True, exist_ok=True)
    path = qdir / f"{task.task_id}.json"

    task.updated_at = datetime.now(UTC).isoformat()
    with path.open("w", encoding="utf-8") as f:
        json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)

    return path


def load_task(
    task_id: str,
    *,
    queue_dir: Path | None = None,
) -> LabelingTask | None:
    """Load a task from the queue.

    Args:
        task_id: Task identifier.
        queue_dir: Override queue directory.

    Returns:
        LabelingTask or None if not found.
    """
    qdir = _queue_dir(queue_dir)
    path = qdir / f"{task_id}.json"
    if not path.exists():
        return None

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    return LabelingTask(
        task_id=data["task_id"],
        dataset=data["dataset"],
        target_field=data["target_field"],
        model=data.get("model", "claude-opus-4-6"),
        batch_size=data.get("batch_size", 10),
        total_images=data.get("total_images", 0),
        completed_images=data.get("completed_images", 0),
        status=TaskStatus(data.get("status", "pending")),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        checkpoint_path=data.get("checkpoint_path"),
        error_message=data.get("error_message"),
    )


def list_tasks(
    *,
    queue_dir: Path | None = None,
    status_filter: TaskStatus | None = None,
) -> list[LabelingTask]:
    """List all tasks in the queue.

    Args:
        queue_dir: Override queue directory.
        status_filter: Only return tasks with this status.

    Returns:
        List of LabelingTask objects.
    """
    qdir = _queue_dir(queue_dir)
    if not qdir.is_dir():
        return []

    tasks: list[LabelingTask] = []
    for path in sorted(qdir.glob("*.json")):
        task = load_task(path.stem, queue_dir=queue_dir)
        if task is None:
            continue
        if status_filter is not None and task.status != status_filter:
            continue
        tasks.append(task)

    return tasks


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------
def save_checkpoint(
    task: LabelingTask,
    batch_result: BatchResult,
    *,
    queue_dir: Path | None = None,
) -> Path:
    """Save a batch checkpoint and update task progress.

    Args:
        task: The labeling task.
        batch_result: Result of the completed batch.
        queue_dir: Override queue directory.

    Returns:
        Path to the checkpoint file.
    """
    qdir = _queue_dir(queue_dir)
    checkpoint_dir = qdir / task.task_id / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    cp_path = checkpoint_dir / f"batch_{batch_result.batch_index:04d}.json"
    with cp_path.open("w", encoding="utf-8") as f:
        json.dump(batch_result.to_dict(), f, indent=2, ensure_ascii=False)

    # Update task progress
    task.completed_images += len(batch_result.image_ids)
    task.checkpoint_path = str(cp_path)
    task.status = TaskStatus.IN_PROGRESS

    if task.completed_images >= task.total_images:
        task.status = TaskStatus.COMPLETED

    _save_task(task, queue_dir=queue_dir)
    log.info(
        "Checkpoint saved for %s: batch %d (%d/%d images)",
        task.task_id,
        batch_result.batch_index,
        task.completed_images,
        task.total_images,
    )
    return cp_path


def load_checkpoints(
    task_id: str,
    *,
    queue_dir: Path | None = None,
) -> list[BatchResult]:
    """Load all checkpoints for a task.

    Args:
        task_id: Task identifier.
        queue_dir: Override queue directory.

    Returns:
        List of BatchResult in order.
    """
    qdir = _queue_dir(queue_dir)
    checkpoint_dir = qdir / task_id / "checkpoints"
    if not checkpoint_dir.is_dir():
        return []

    results: list[BatchResult] = []
    for path in sorted(checkpoint_dir.glob("batch_*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        results.append(
            BatchResult(
                batch_index=data["batch_index"],
                image_ids=data.get("image_ids", []),
                labels=data.get("labels", {}),
                confidences=data.get("confidences", {}),
                processing_time_s=data.get("processing_time_s", 0.0),
            )
        )

    return results


# ---------------------------------------------------------------------------
# Queue status
# ---------------------------------------------------------------------------
def generate_queue_status(
    *,
    queue_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate queue status summary.

    Args:
        queue_dir: Override queue directory.

    Returns:
        Status summary dict.
    """
    tasks = list_tasks(queue_dir=queue_dir)

    status_counts: dict[str, int] = {}
    total_images = 0
    completed_images = 0

    for task in tasks:
        status = task.status.value
        status_counts[status] = status_counts.get(status, 0) + 1
        total_images += task.total_images
        completed_images += task.completed_images

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_tasks": len(tasks),
        "status_counts": status_counts,
        "total_images": total_images,
        "completed_images": completed_images,
        "overall_progress_pct": (
            100.0 * completed_images / total_images if total_images else 0.0
        ),
        "tasks": [t.to_dict() for t in tasks],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Streaming VLM labeling pipeline.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true", help="Create new task.")
    mode.add_argument("--resume", action="store_true", help="Resume task.")
    mode.add_argument("--status", action="store_true", help="Show queue status.")

    parser.add_argument("--dataset", type=str, help="Dataset name.")
    parser.add_argument("--field", type=str, help="Target field.")
    parser.add_argument("--model", type=str, default="claude-opus-4-6")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--total-images", type=int, default=0)
    parser.add_argument("--task-id", type=str, help="Task ID for resume.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.create:
        if not args.dataset or not args.field:
            parser.error("--dataset and --field required for --create")
        task = create_task(
            args.dataset,
            args.field,
            model=args.model,
            batch_size=args.batch_size,
            total_images=args.total_images,
        )
        print(f"Created task: {task.task_id}")

    elif args.resume:
        if not args.task_id:
            parser.error("--task-id required for --resume")
        task = load_task(args.task_id)
        if task is None:
            print(f"Task not found: {args.task_id}")
            return
        print(f"Task {task.task_id}: {task.status.value}")
        print(
            f"  Progress: {task.completed_images}/{task.total_images}"
            f" ({task.progress_pct:.1f}%)"
        )
        print(f"  Remaining batches: {task.remaining_batches}")

    elif args.status:
        status = generate_queue_status()
        print(f"\nVLM Queue Status ({status['total_tasks']} tasks)")
        print(f"  Total images: {status['total_images']}")
        print(f"  Completed: {status['completed_images']}")
        print(f"  Progress: {status['overall_progress_pct']:.1f}%")
        for task_data in status["tasks"]:
            print(
                f"  {task_data['task_id']}: {task_data['status']}"
                f" ({task_data['progress_pct']:.1f}%)"
            )


if __name__ == "__main__":
    main()
