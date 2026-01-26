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

Example:
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
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
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
            timestamp=data.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
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
            logger.info(
                f"Found checkpoint for {dataset_name}: "
                f"processed={checkpoint.processed_count}, last={checkpoint.last_path}"
            )
            return checkpoint
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                f"Invalid checkpoint file for {dataset_name}: {e}. "
                f"Starting fresh."
            )
            return None

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
        with atomic_write(checkpoint_path, fsync=self.fsync) as temp_path:
            with open(temp_path, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

        logger.debug(
            f"Saved checkpoint for {dataset_name}: count={processed_count}"
        )

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


__all__ = [
    "CheckpointInfo",
    "CheckpointManager",
]
