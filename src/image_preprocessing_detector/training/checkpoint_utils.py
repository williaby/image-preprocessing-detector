"""Checkpoint utilities for training pipelines.

Provides shared utilities for saving, loading, and managing model checkpoints
with security best practices.
"""

# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch

logger = logging.getLogger(__name__)


def load_checkpoint_safe(
    checkpoint_path: str | Path,
    device: torch.device | str | None = None,
) -> dict[str, Any]:
    """Load a checkpoint file with security best practices.

    Uses weights_only=True to prevent arbitrary code execution from
    untrusted checkpoint files.

    Args:
        checkpoint_path: Path to the checkpoint file
        device: Device to map tensors to (default: current device)

    Returns:
        Dictionary containing checkpoint data

    Raises:
        FileNotFoundError: If checkpoint file doesn't exist
    """
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    logger.info(f"Loading checkpoint: {checkpoint_path}")

    # Security: Use weights_only=True to prevent arbitrary code execution
    # Only loads tensors, dicts, lists, and primitive types
    checkpoint: dict[str, Any] = torch.load(
        checkpoint_path, map_location=device, weights_only=True
    )

    return checkpoint


def cleanup_old_checkpoints(
    checkpoint_dir: Path,
    pattern: str,
    keep_last_n: int = 3,
) -> None:
    """Remove old checkpoints, keeping only the most recent N.

    Args:
        checkpoint_dir: Directory containing checkpoints
        pattern: Glob pattern to match checkpoint files (e.g., "checkpoint_epoch_*.pt")
        keep_last_n: Number of most recent checkpoints to keep
    """
    checkpoints = sorted(
        checkpoint_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
    )

    if len(checkpoints) > keep_last_n:
        for checkpoint in checkpoints[:-keep_last_n]:
            checkpoint.unlink()
            logger.debug(f"Removed old checkpoint: {checkpoint}")
