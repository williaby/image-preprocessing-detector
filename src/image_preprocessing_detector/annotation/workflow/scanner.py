# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Batch-aware file scanner for annotation pipeline.

Phase 5 Task 5.2: Implements batch accumulation, batch-level checkpointing,
and progress reporting for long-running annotation scans.

Key Features:
    - **Batch Accumulation**: Groups images into configurable batches
    - **Batch Checkpointing**: Saves progress every N batches for resumability
    - **Progress Reporting**: Rich/tqdm integration for long-running scans
    - **Memory Efficiency**: Yields batches instead of loading all paths

Example:
    >>> from image_preprocessing_detector.annotation.workflow.scanner import (
    ...     BatchScanner,
    ...     ScanConfig,
    ... )
    >>>
    >>> scanner = BatchScanner(ScanConfig(batch_size=100, checkpoint_every=10))
    >>> for batch in scanner.scan(dataset_path, patterns=["*.png", "*.jpg"]):
    ...     print(f"Processing batch {batch.batch_num} with {len(batch.paths)} images")
    ...     process_batch(batch)
    ...     scanner.checkpoint(batch)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime  # type: ignore[attr-defined]
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class ScanConfig:
    """Configuration for batch scanning.

    Attributes:
        batch_size: Number of images per batch (default 100)
        checkpoint_every: Checkpoint after N batches (default 10)
        file_patterns: Glob patterns to match (default ["*.png", "*.jpg", "*.jpeg"])
        recursive: Scan subdirectories recursively (default True)
        skip_hidden: Skip hidden files/directories (default True)
        max_batches: Maximum batches to process (None for unlimited)
        resume_from_checkpoint: Resume from existing checkpoint (default True)
        checkpoint_dir: Directory for checkpoint files (default ".annotation_checkpoints")
    """

    batch_size: int = 100
    checkpoint_every: int = 10
    file_patterns: list[str] = field(
        default_factory=lambda: ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.tif", "*.bmp"]
    )
    recursive: bool = True
    skip_hidden: bool = True
    max_batches: int | None = None
    resume_from_checkpoint: bool = True
    checkpoint_dir: str = ".annotation_checkpoints"


@dataclass
class ScanBatch:
    """A batch of image paths for processing.

    Attributes:
        batch_num: Batch number (0-indexed)
        paths: List of image paths in this batch
        dataset_name: Name of the dataset being scanned
        start_index: Index of first image in overall scan
        checkpoint_hash: Hash for checkpoint identification
    """

    batch_num: int
    paths: list[Path]
    dataset_name: str
    start_index: int
    checkpoint_hash: str = ""

    def __post_init__(self) -> None:
        """Generate checkpoint hash after initialization."""
        if not self.checkpoint_hash:
            # Hash based on batch number and first/last paths for identity
            content = f"{self.batch_num}:{self.dataset_name}:{len(self.paths)}"
            if self.paths:
                content += f":{self.paths[0].name}:{self.paths[-1].name}"
            self.checkpoint_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def __len__(self) -> int:
        """Return number of paths in batch."""
        return len(self.paths)


@dataclass
class ScanProgress:
    """Progress information for scan operations.

    Attributes:
        total_files: Total files discovered
        files_processed: Files processed so far
        batches_completed: Batches completed
        batches_total: Total batches (if known)
        current_batch: Current batch number
        elapsed_seconds: Time elapsed since start
        estimated_remaining: Estimated time remaining
        throughput: Files per second
    """

    total_files: int = 0
    files_processed: int = 0
    batches_completed: int = 0
    batches_total: int | None = None
    current_batch: int = 0
    elapsed_seconds: float = 0.0
    estimated_remaining: float | None = None
    throughput: float = 0.0

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.files_processed / self.total_files) * 100.0


@dataclass
class ScanCheckpoint:
    """Checkpoint state for resumable scanning.

    Attributes:
        dataset_name: Name of the dataset
        dataset_path: Path to the dataset
        last_batch_completed: Last successfully completed batch number
        total_batches: Total number of batches
        files_processed: Total files processed
        timestamp: When checkpoint was created
        scan_hash: Hash of scan parameters for validation
    """

    dataset_name: str
    dataset_path: str
    last_batch_completed: int
    total_batches: int
    files_processed: int
    timestamp: str
    scan_hash: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "dataset_name": self.dataset_name,
            "dataset_path": self.dataset_path,
            "last_batch_completed": self.last_batch_completed,
            "total_batches": self.total_batches,
            "files_processed": self.files_processed,
            "timestamp": self.timestamp,
            "scan_hash": self.scan_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScanCheckpoint:
        """Create from dictionary."""
        return cls(
            dataset_name=data["dataset_name"],
            dataset_path=data["dataset_path"],
            last_batch_completed=data["last_batch_completed"],
            total_batches=data["total_batches"],
            files_processed=data["files_processed"],
            timestamp=data["timestamp"],
            scan_hash=data["scan_hash"],
        )


# ============================================================================
# Progress Callback Protocol
# ============================================================================


class ProgressCallback:
    """Callback interface for progress reporting.

    Subclass this to integrate with tqdm, rich, or custom progress display.
    """

    def on_scan_start(self, dataset_name: str, total_files: int) -> None:
        """Called when scan starts.

        Args:
            dataset_name: Name of the dataset
            total_files: Total files to process
        """

    def on_batch_start(self, batch: ScanBatch) -> None:
        """Called when a batch starts processing.

        Args:
            batch: The batch starting
        """

    def on_batch_complete(self, batch: ScanBatch, progress: ScanProgress) -> None:
        """Called when a batch completes.

        Args:
            batch: The completed batch
            progress: Current progress information
        """

    def on_checkpoint(self, checkpoint: ScanCheckpoint) -> None:
        """Called when a checkpoint is saved.

        Args:
            checkpoint: The saved checkpoint
        """

    def on_scan_complete(self, progress: ScanProgress) -> None:
        """Called when scan completes.

        Args:
            progress: Final progress information
        """


class LoggingProgressCallback(ProgressCallback):
    """Progress callback that logs to Python logging."""

    def on_scan_start(self, dataset_name: str, total_files: int) -> None:
        """Log scan start."""
        logger.info(
            "scan_started",
            extra={"dataset": dataset_name, "total_files": total_files},
        )

    def on_batch_complete(self, batch: ScanBatch, progress: ScanProgress) -> None:
        """Log batch completion."""
        logger.info(
            "batch_completed",
            extra={
                "batch_num": batch.batch_num,
                "files_processed": progress.files_processed,
                "percent_complete": f"{progress.percent_complete:.1f}%",
                "throughput": f"{progress.throughput:.1f} files/sec",
            },
        )

    def on_checkpoint(self, checkpoint: ScanCheckpoint) -> None:
        """Log checkpoint save."""
        logger.info(
            "checkpoint_saved",
            extra={
                "batch": checkpoint.last_batch_completed,
                "files": checkpoint.files_processed,
            },
        )

    def on_scan_complete(self, progress: ScanProgress) -> None:
        """Log scan completion."""
        logger.info(
            "scan_completed",
            extra={
                "total_files": progress.files_processed,
                "batches": progress.batches_completed,
                "elapsed_seconds": f"{progress.elapsed_seconds:.1f}",
            },
        )


# ============================================================================
# Batch Scanner Implementation
# ============================================================================


class BatchScanner:
    """Batch-aware file scanner for annotation datasets.

    Scans directories for image files, groups them into batches, and
    provides checkpointing for resumable long-running scans.

    Example:
        >>> scanner = BatchScanner(ScanConfig(batch_size=100))
        >>> for batch in scanner.scan(Path("/data/dataset")):
        ...     process_batch(batch)
        ...     scanner.mark_batch_complete(batch)
    """

    def __init__(
        self,
        config: ScanConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Initialize batch scanner.

        Args:
            config: Scan configuration (defaults to ScanConfig())
            progress_callback: Callback for progress reporting
        """
        self.config = config or ScanConfig()
        self.progress_callback = progress_callback or LoggingProgressCallback()

        # State tracking
        self._current_checkpoint: ScanCheckpoint | None = None
        self._start_time: float = 0.0
        self._files_processed: int = 0
        self._batches_completed: int = 0

    def scan(
        self,
        dataset_path: Path,
        dataset_name: str | None = None,
    ) -> Iterator[ScanBatch]:
        """Scan a dataset directory and yield batches.

        Args:
            dataset_path: Path to dataset root directory
            dataset_name: Name of the dataset (defaults to directory name)

        Yields:
            ScanBatch objects containing paths to process
        """
        dataset_path = Path(dataset_path)
        dataset_name = dataset_name or dataset_path.name

        # Compute scan hash for checkpoint validation
        scan_hash = self._compute_scan_hash(dataset_path, dataset_name)

        # Check for existing checkpoint
        resume_from = 0
        if self.config.resume_from_checkpoint:
            checkpoint = self._load_checkpoint(dataset_name, scan_hash)
            if checkpoint:
                resume_from = checkpoint.last_batch_completed + 1
                self._files_processed = checkpoint.files_processed
                self._batches_completed = checkpoint.last_batch_completed
                logger.info(
                    "resuming_from_checkpoint",
                    extra={
                        "batch": resume_from,
                        "files_already_processed": checkpoint.files_processed,
                    },
                )

        # Discover all files
        all_paths = list(self._discover_files(dataset_path))
        total_files = len(all_paths)
        total_batches = (
            total_files + self.config.batch_size - 1
        ) // self.config.batch_size

        # Notify start
        self._start_time = time.time()
        self.progress_callback.on_scan_start(dataset_name, total_files)

        # Yield batches
        batch_num = 0
        for i in range(0, total_files, self.config.batch_size):
            # Skip already processed batches
            if batch_num < resume_from:
                batch_num += 1
                continue

            # Check max batches limit
            if self.config.max_batches and batch_num >= self.config.max_batches:
                break

            batch_paths = all_paths[i : i + self.config.batch_size]
            batch = ScanBatch(
                batch_num=batch_num,
                paths=batch_paths,
                dataset_name=dataset_name,
                start_index=i,
            )

            self.progress_callback.on_batch_start(batch)
            yield batch

            batch_num += 1

        # Final progress update
        final_progress = self._get_progress(total_files, total_batches)
        self.progress_callback.on_scan_complete(final_progress)

    def mark_batch_complete(
        self,
        batch: ScanBatch,
        total_files: int | None = None,
        total_batches: int | None = None,
    ) -> None:
        """Mark a batch as complete and optionally checkpoint.

        Call this after successfully processing a batch.

        Args:
            batch: The completed batch
            total_files: Total files in scan (for progress calculation)
            total_batches: Total batches in scan (for progress calculation)
        """
        self._files_processed += len(batch)
        self._batches_completed += 1

        # Calculate progress
        progress = self._get_progress(
            total_files or self._files_processed,
            total_batches,
        )

        self.progress_callback.on_batch_complete(batch, progress)

        # Checkpoint if needed
        if self._batches_completed % self.config.checkpoint_every == 0:
            self._save_checkpoint(batch, total_batches or batch.batch_num + 1)

    def checkpoint(
        self,
        batch: ScanBatch,
        total_batches: int | None = None,
    ) -> ScanCheckpoint:
        """Explicitly save a checkpoint.

        Args:
            batch: The batch to checkpoint at
            total_batches: Total number of batches

        Returns:
            The saved checkpoint
        """
        return self._save_checkpoint(batch, total_batches or batch.batch_num + 1)

    def clear_checkpoint(self, dataset_name: str) -> bool:
        """Clear checkpoint for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            True if checkpoint was cleared
        """
        checkpoint_path = self._get_checkpoint_path(dataset_name)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("checkpoint_cleared", extra={"dataset": dataset_name})
            return True
        return False

    def _discover_files(self, dataset_path: Path) -> Iterator[Path]:
        """Discover image files in a directory.

        Args:
            dataset_path: Directory to scan

        Yields:
            Paths to image files
        """
        for pattern in self.config.file_patterns:
            glob_pattern = f"**/{pattern}" if self.config.recursive else pattern

            for path in dataset_path.glob(glob_pattern):
                if path.is_file():
                    # Skip hidden files
                    if self.config.skip_hidden:
                        parts = path.relative_to(dataset_path).parts
                        if any(part.startswith(".") for part in parts):
                            continue
                    yield path

    def _compute_scan_hash(self, dataset_path: Path, dataset_name: str) -> str:
        """Compute hash of scan parameters for checkpoint validation.

        Args:
            dataset_path: Path to dataset
            dataset_name: Dataset name

        Returns:
            Hash string
        """
        content = (
            f"{dataset_path.resolve()}:{dataset_name}:"
            f"{self.config.batch_size}:{','.join(sorted(self.config.file_patterns))}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_checkpoint_path(self, dataset_name: str) -> Path:
        """Get checkpoint file path for a dataset.

        Args:
            dataset_name: Dataset name

        Returns:
            Path to checkpoint file
        """
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        safe_name = dataset_name.replace("/", "_").replace("\\", "_")
        return checkpoint_dir / f"scan_{safe_name}.checkpoint.json"

    def _load_checkpoint(
        self,
        dataset_name: str,
        scan_hash: str,
    ) -> ScanCheckpoint | None:
        """Load checkpoint if valid.

        Args:
            dataset_name: Dataset name
            scan_hash: Expected scan hash

        Returns:
            Checkpoint if valid, None otherwise
        """
        checkpoint_path = self._get_checkpoint_path(dataset_name)
        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)
            checkpoint = ScanCheckpoint.from_dict(data)

            # Validate scan hash matches
            if checkpoint.scan_hash != scan_hash:
                logger.warning(
                    "checkpoint_invalid_scan_hash",
                    extra={"expected": scan_hash, "got": checkpoint.scan_hash},
                )
                return None

            return checkpoint  # noqa: TRY300
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("checkpoint_load_error", extra={"error": str(e)})
            return None

    def _save_checkpoint(
        self,
        batch: ScanBatch,
        total_batches: int,
    ) -> ScanCheckpoint:
        """Save checkpoint to disk.

        Args:
            batch: Current batch
            total_batches: Total number of batches

        Returns:
            Saved checkpoint
        """
        checkpoint = ScanCheckpoint(
            dataset_name=batch.dataset_name,
            dataset_path=str(batch.paths[0].parent) if batch.paths else "",
            last_batch_completed=batch.batch_num,
            total_batches=total_batches,
            files_processed=self._files_processed,
            timestamp=datetime.now(UTC).isoformat(),
            scan_hash=self._compute_scan_hash(
                Path(batch.paths[0]).parent.parent if batch.paths else Path(),
                batch.dataset_name,
            ),
        )

        checkpoint_path = self._get_checkpoint_path(batch.dataset_name)
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        self.progress_callback.on_checkpoint(checkpoint)
        self._current_checkpoint = checkpoint

        return checkpoint

    def _get_progress(
        self,
        total_files: int,
        total_batches: int | None,
    ) -> ScanProgress:
        """Calculate current progress.

        Args:
            total_files: Total files in scan
            total_batches: Total batches in scan

        Returns:
            Current progress
        """
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        throughput = self._files_processed / elapsed if elapsed > 0 else 0.0

        remaining = None
        if throughput > 0 and total_files > self._files_processed:
            remaining = (total_files - self._files_processed) / throughput

        return ScanProgress(
            total_files=total_files,
            files_processed=self._files_processed,
            batches_completed=self._batches_completed,
            batches_total=total_batches,
            current_batch=self._batches_completed,
            elapsed_seconds=elapsed,
            estimated_remaining=remaining,
            throughput=throughput,
        )


__all__ = [
    "BatchScanner",
    "LoggingProgressCallback",
    "ProgressCallback",
    "ScanBatch",
    "ScanCheckpoint",
    "ScanConfig",
    "ScanProgress",
]
