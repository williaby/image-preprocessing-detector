# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Checkpoint management for resumable annotation processing.

This module provides checkpointing capabilities for the annotation pipeline,
enabling resumable processing after interruption or failure.

Features:
    - Intra-dataset checkpointing (resume within a dataset)
    - Cross-session persistence via JSON files
    - Atomic checkpoint writes for consistency
    - Configurable checkpoint intervals
    - Batch-aware checkpointing (Phase 3.3.2)
    - Hash-based validation on resume (Phase 3.3.3)

Basic Usage:
    >>> from image_preprocessing_detector.annotation.integrity.checkpointing import (
    ...     CheckpointManager,
    ...     CheckpointInfo,
    ... )
    >>>
    >>> manager = CheckpointManager(checkpoint_dir=Path(".checkpoints"))
    >>>
    >>> # Check for existing checkpoint
    >>> resume = manager.get_resume_point("diqa-5000")
    >>> if resume:
    ...     print(f"Resuming from {resume.last_path}")
    >>>
    >>> # Save checkpoint during processing
    >>> manager.save_checkpoint(
    ...     dataset_name="diqa-5000",
    ...     processed_count=500,
    ...     last_path="train/img500.png",
    ...     last_hash="abc123...",
    ... )

Batch-Aware Checkpointing:
    >>> # Create batch-aware manager (saves every 100 batches)
    >>> batch_manager = BatchCheckpointManager(
    ...     checkpoint_dir=Path(".checkpoints"),
    ...     batch_size=32,
    ...     checkpoint_interval=100,  # Save every 100 batches
    ... )
    >>>
    >>> # Process batches
    >>> for batch_idx, batch in enumerate(data_loader):
    ...     process_batch(batch)
    ...     batch_manager.update(
    ...         dataset_name="diqa-5000",
    ...         batch_idx=batch_idx,
    ...         last_path=batch[-1].path,
    ...         last_hash=batch[-1].hash,
    ...     )

Validated Resume:
    >>> # Resume with hash validation
    >>> result = manager.get_validated_resume_point(
    ...     dataset_name="diqa-5000",
    ...     image_paths=all_image_paths,
    ...     compute_hash=lambda p: hashlib.sha256(p.read_bytes()).hexdigest(),
    ... )
    >>> if result.is_valid:
    ...     start_idx = result.resume_index
    ... else:
    ...     print(f"Checkpoint invalid: {result.reason}")
    ...     start_idx = 0
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .atomic import atomic_write

logger = logging.getLogger(__name__)


@dataclass
class CheckpointInfo:
    """Information about a processing checkpoint.

    Attributes:
        dataset_name: Name of the dataset being processed
        processed_count: Number of items processed so far
        last_path: Path to the last successfully processed image
        last_hash: SHA256 hash of the last processed image
        timestamp: When checkpoint was created (ISO 8601)
        version: Checkpoint format version
    """

    dataset_name: str
    processed_count: int
    last_path: str
    last_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointInfo:
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with checkpoint fields

        Returns:
            CheckpointInfo instance

        Raises:
            KeyError: If required field is missing
            TypeError: If field has wrong type
        """
        return cls(
            dataset_name=data["dataset_name"],
            processed_count=data["processed_count"],
            last_path=data["last_path"],
            last_hash=data["last_hash"],
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            version=data.get("version", 1),
        )


class CheckpointManager:
    """Manages checkpoints for resumable processing.

    Checkpoints are stored as JSON files in the checkpoint directory,
    one per dataset. Files are written atomically to prevent corruption.

    Attributes:
        checkpoint_dir: Directory for checkpoint files
        fsync: Whether to call fsync for durability
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        fsync: bool = False,
    ):
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
            fsync: Enable fsync for durability (slower but safer)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.fsync = fsync

        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _checkpoint_path(self, dataset_name: str) -> Path:
        """Get checkpoint file path for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Path to checkpoint JSON file
        """
        # Sanitize dataset name for filesystem
        safe_name = dataset_name.replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{safe_name}.checkpoint.json"

    def get_resume_point(self, dataset_name: str) -> CheckpointInfo | None:
        """Get resume point for a dataset.

        Args:
            dataset_name: Name of the dataset to check

        Returns:
            CheckpointInfo if checkpoint exists, None otherwise
        """
        checkpoint_path = self._checkpoint_path(dataset_name)

        if not checkpoint_path.exists():
            logger.debug(f"No checkpoint found for {dataset_name}")
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)
            checkpoint = CheckpointInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                f"Invalid checkpoint file for {dataset_name}: {e}. Starting fresh."
            )
            return None
        else:
            logger.info(
                f"Found checkpoint for {dataset_name}: "
                f"processed={checkpoint.processed_count}, last={checkpoint.last_path}"
            )
            return checkpoint

    def save_checkpoint(
        self,
        dataset_name: str,
        processed_count: int,
        last_path: str,
        last_hash: str,
    ) -> None:
        """Save a checkpoint for a dataset.

        The checkpoint is written atomically to prevent corruption.

        Args:
            dataset_name: Name of the dataset
            processed_count: Number of items processed so far
            last_path: Relative path to last processed image
            last_hash: SHA256 hash of last processed image
        """
        checkpoint = CheckpointInfo(
            dataset_name=dataset_name,
            processed_count=processed_count,
            last_path=last_path,
            last_hash=last_hash,
        )

        checkpoint_path = self._checkpoint_path(dataset_name)

        # Write atomically
        with (
            atomic_write(checkpoint_path, fsync=self.fsync) as temp_path,
            open(temp_path, "w") as f,
        ):
            json.dump(checkpoint.to_dict(), f, indent=2)

        logger.debug(f"Saved checkpoint for {dataset_name}: count={processed_count}")

    def clear_checkpoint(self, dataset_name: str) -> bool:
        """Clear checkpoint for a dataset.

        Call this when processing completes successfully.

        Args:
            dataset_name: Name of the dataset

        Returns:
            True if checkpoint was removed, False if it didn't exist
        """
        checkpoint_path = self._checkpoint_path(dataset_name)

        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info(f"Cleared checkpoint for {dataset_name}")
            return True
        return False

    def list_checkpoints(self) -> list[CheckpointInfo]:
        """List all existing checkpoints.

        Returns:
            List of CheckpointInfo for all datasets with checkpoints
        """
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.checkpoint.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                checkpoints.append(CheckpointInfo.from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Skipping invalid checkpoint {path}: {e}")

        return sorted(checkpoints, key=lambda c: c.timestamp, reverse=True)

    def get_stats(self) -> dict[str, Any]:
        """Get checkpoint statistics.

        Returns:
            Dictionary with checkpoint stats
        """
        checkpoints = self.list_checkpoints()
        return {
            "checkpoint_dir": str(self.checkpoint_dir),
            "total_checkpoints": len(checkpoints),
            "datasets": [c.dataset_name for c in checkpoints],
            "fsync_enabled": self.fsync,
        }

    def get_validated_resume_point(
        self,
        dataset_name: str,
        image_paths: list[Path],
        compute_hash: Callable[[Path], str] | None = None,
        strict_matching: bool = True,
        strict_hash: bool = False,
    ) -> CheckpointValidationResult:
        """Get resume point with hash-based validation.

        Validates that the checkpoint file still exists in the image list
        and optionally verifies its hash matches.

        Args:
            dataset_name: Name of the dataset
            image_paths: List of all image paths in processing order
            compute_hash: Optional function to compute file hash for validation
                         Signature: (Path) -> str
            strict_matching: If True (default), only match by full path or
                           normalized relative path. If False, also allow
                           filename-only matching (less safe for datasets
                           with duplicate filenames across directories).
            strict_hash: If True, hash validation errors fail the resume.
                        If False (default), log warning and continue.

        Returns:
            ValidationResult with validation status and resume index

        Example:
            >>> result = manager.get_validated_resume_point(
            ...     "diqa-5000",
            ...     image_paths,
            ...     compute_hash=lambda p: hashlib.sha256(p.read_bytes()).hexdigest(),
            ...     strict_matching=True,
            ... )
            >>> if result.is_valid:
            ...     start_idx = result.resume_index
        """
        checkpoint = self.get_resume_point(dataset_name)

        if checkpoint is None:
            return CheckpointValidationResult(
                is_valid=True,
                resume_index=0,
                checkpoint=None,
                reason="No checkpoint found - starting fresh",
            )

        # Find checkpoint file in image list
        checkpoint_path = checkpoint.last_path
        checkpoint_path_obj = Path(checkpoint_path)
        found_idx = None
        match_method = None

        for idx, path in enumerate(image_paths):
            # Try full path match first
            if str(path) == checkpoint_path:
                found_idx = idx
                match_method = "full_path"
                break

            # Try normalized POSIX path match (handles relative vs absolute)
            if path.as_posix().endswith(checkpoint_path_obj.as_posix()):
                found_idx = idx
                match_method = "normalized_path"
                break

            # Filename-only matching (less safe, requires strict_matching=False)
            if not strict_matching and path.name == checkpoint_path_obj.name:
                found_idx = idx
                match_method = "filename_only"
                logger.warning(
                    f"Checkpoint matched by filename only: {checkpoint_path}. "
                    f"This may be incorrect if multiple files share this name."
                )
                break

        if found_idx is None:
            return CheckpointValidationResult(
                is_valid=False,
                resume_index=0,
                checkpoint=checkpoint,
                reason=f"Checkpoint file '{checkpoint_path}' not found in image list",
            )

        # Validate hash if compute_hash provided
        if compute_hash is not None:
            try:
                actual_hash = compute_hash(image_paths[found_idx])
                if actual_hash != checkpoint.last_hash:
                    return CheckpointValidationResult(
                        is_valid=False,
                        resume_index=0,
                        checkpoint=checkpoint,
                        reason=(
                            f"Hash mismatch for '{checkpoint_path}': "
                            f"expected {checkpoint.last_hash[:16]}..., "
                            f"got {actual_hash[:16]}..."
                        ),
                    )
            except Exception as e:
                msg = f"Could not validate hash for {checkpoint_path}: {e}"
                if strict_hash:
                    return CheckpointValidationResult(
                        is_valid=False,
                        resume_index=0,
                        checkpoint=checkpoint,
                        reason=msg,
                    )
                logger.warning(msg)
                # Continue without hash validation in non-strict mode

        # Valid checkpoint - resume from next file
        resume_idx = found_idx + 1
        return ValidationResult(
            is_valid=True,
            resume_index=resume_idx,
            checkpoint=checkpoint,
            reason=f"Valid checkpoint (matched by {match_method}), resuming from index {resume_idx}",
        )


@dataclass
class CheckpointValidationResult:
    """Result of checkpoint validation.

    Note: Named CheckpointValidationResult to distinguish from
    config.validators.ValidationResult which serves a different purpose.

    Attributes:
        is_valid: Whether checkpoint is valid for resume
        resume_index: Index to resume from (0 if starting fresh)
        checkpoint: Original checkpoint info (if found)
        reason: Human-readable explanation
    """

    is_valid: bool
    resume_index: int
    checkpoint: CheckpointInfo | None
    reason: str


# Backward compatibility alias (deprecated)
ValidationResult = CheckpointValidationResult


@dataclass
class BatchCheckpointInfo(CheckpointInfo):
    """Extended checkpoint info with batch metadata.

    Attributes:
        batch_idx: Current batch index
        batch_size: Number of items per batch
        total_batches: Total number of batches (if known)
        items_in_current_batch: Items processed in current batch
    """

    batch_idx: int = 0
    batch_size: int = 32
    total_batches: int | None = None
    items_in_current_batch: int = 0
    version: int = 2  # Override: batch checkpoints are version 2

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchCheckpointInfo:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            dataset_name=data["dataset_name"],
            processed_count=data["processed_count"],
            last_path=data["last_path"],
            last_hash=data["last_hash"],
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            version=data.get("version", 2),  # Version 2 for batch checkpoints
            batch_idx=data.get("batch_idx", 0),
            batch_size=data.get("batch_size", 32),
            total_batches=data.get("total_batches"),
            items_in_current_batch=data.get("items_in_current_batch", 0),
        )


class BatchCheckpointManager(CheckpointManager):
    """Batch-aware checkpoint manager.

    Automatically saves checkpoints at configurable batch intervals,
    providing efficient checkpointing for large-scale processing.

    Attributes:
        batch_size: Number of items per batch
        checkpoint_interval: Save checkpoint every N batches
        pending_updates: Counter for batches since last checkpoint
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        batch_size: int = 32,
        checkpoint_interval: int = 100,
        fsync: bool = False,
    ):
        """Initialize batch checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
            batch_size: Number of items per processing batch
            checkpoint_interval: Save checkpoint every N batches
            fsync: Enable fsync for durability
        """
        super().__init__(checkpoint_dir, fsync)
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        self._pending_updates: dict[str, int] = {}
        self._last_checkpoint: dict[str, BatchCheckpointInfo] = {}

    def update(
        self,
        dataset_name: str,
        batch_idx: int,
        last_path: str,
        last_hash: str,
        items_in_batch: int | None = None,
        total_batches: int | None = None,
        force: bool = False,
    ) -> bool:
        """Update checkpoint state after batch processing.

        Checkpoints are saved automatically every checkpoint_interval batches,
        or immediately if force=True.

        Args:
            dataset_name: Name of the dataset
            batch_idx: Current batch index
            last_path: Path to last processed image
            last_hash: Hash of last processed image
            items_in_batch: Number of items in this batch (default: batch_size)
            total_batches: Total batches if known (for progress tracking)
            force: Force checkpoint save regardless of interval

        Returns:
            True if checkpoint was saved, False if deferred
        """
        items = items_in_batch or self.batch_size
        processed_count = (batch_idx * self.batch_size) + items

        # Track pending updates
        if dataset_name not in self._pending_updates:
            self._pending_updates[dataset_name] = 0
        self._pending_updates[dataset_name] += 1

        # Update in-memory state
        checkpoint = BatchCheckpointInfo(
            dataset_name=dataset_name,
            processed_count=processed_count,
            last_path=last_path,
            last_hash=last_hash,
            batch_idx=batch_idx,
            batch_size=self.batch_size,
            total_batches=total_batches,
            items_in_current_batch=items,
        )
        self._last_checkpoint[dataset_name] = checkpoint

        # Check if we should save
        should_save = force or (
            self._pending_updates[dataset_name] >= self.checkpoint_interval
        )

        if should_save:
            self._save_batch_checkpoint(dataset_name, checkpoint)
            self._pending_updates[dataset_name] = 0
            return True

        return False

    def flush(self, dataset_name: str | None = None) -> int:
        """Force save all pending checkpoints.

        Args:
            dataset_name: Specific dataset to flush, or None for all

        Returns:
            Number of checkpoints saved
        """
        saved = 0

        if dataset_name:
            datasets = [dataset_name]
        else:
            datasets = list(self._last_checkpoint.keys())

        for name in datasets:
            if name in self._last_checkpoint and self._pending_updates.get(name, 0) > 0:
                self._save_batch_checkpoint(name, self._last_checkpoint[name])
                self._pending_updates[name] = 0
                saved += 1

        return saved

    def get_batch_resume_point(self, dataset_name: str) -> BatchCheckpointInfo | None:
        """Get batch-aware resume point.

        Args:
            dataset_name: Name of the dataset

        Returns:
            BatchCheckpointInfo if checkpoint exists, None otherwise
        """
        checkpoint_path = self._checkpoint_path(dataset_name)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path) as f:
                data = json.load(f)

            # Check if this is a batch checkpoint (version 2+)
            if data.get("version", 1) >= 2:
                return BatchCheckpointInfo.from_dict(data)
            # Convert legacy checkpoint to batch checkpoint
            legacy = CheckpointInfo.from_dict(data)
            return BatchCheckpointInfo(
                dataset_name=legacy.dataset_name,
                processed_count=legacy.processed_count,
                last_path=legacy.last_path,
                last_hash=legacy.last_hash,
                timestamp=legacy.timestamp,
                version=2,
                batch_idx=legacy.processed_count // self.batch_size,
                batch_size=self.batch_size,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Invalid checkpoint file for {dataset_name}: {e}")
            return None

    def get_progress(self, dataset_name: str) -> dict[str, Any]:
        """Get progress information from checkpoint.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dictionary with progress info (batches, items, percentage)
        """
        checkpoint = self.get_batch_resume_point(dataset_name)

        if checkpoint is None:
            return {
                "has_checkpoint": False,
                "batch_idx": 0,
                "processed_count": 0,
                "percentage": 0.0,
            }

        percentage = 0.0
        if checkpoint.total_batches:
            percentage = (checkpoint.batch_idx / checkpoint.total_batches) * 100

        return {
            "has_checkpoint": True,
            "batch_idx": checkpoint.batch_idx,
            "processed_count": checkpoint.processed_count,
            "total_batches": checkpoint.total_batches,
            "percentage": percentage,
            "last_path": checkpoint.last_path,
            "timestamp": checkpoint.timestamp,
        }

    def _save_batch_checkpoint(
        self, dataset_name: str, checkpoint: BatchCheckpointInfo
    ) -> None:
        """Save batch checkpoint atomically.

        Args:
            dataset_name: Name of the dataset
            checkpoint: Checkpoint info to save
        """
        checkpoint_path = self._checkpoint_path(dataset_name)

        with (
            atomic_write(checkpoint_path, fsync=self.fsync) as temp_path,
            open(temp_path, "w") as f,
        ):
            json.dump(checkpoint.to_dict(), f, indent=2)

        logger.debug(
            f"Saved batch checkpoint for {dataset_name}: "
            f"batch={checkpoint.batch_idx}, count={checkpoint.processed_count}"
        )


__all__ = [
    "BatchCheckpointInfo",
    "BatchCheckpointManager",
    "CheckpointInfo",
    "CheckpointManager",
    "CheckpointValidationResult",
    "ValidationResult",  # Backward compatibility alias
]
