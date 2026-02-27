"""Progress tracking for annotation pipeline.

This module provides progress tracking and reporting capabilities
for long-running annotation operations.

Features:
    - Callback-based progress updates
    - ETA calculation
    - Rate tracking (images/second)
    - Multi-dataset progress

Example:
    >>> from image_preprocessing_detector.annotation.workflow.progress import (
    ...     ProgressTracker,
    ...     ProgressCallback,
    ... )
    >>>
    >>> def my_callback(current: int, total: int, rate: float) -> None:
    ...     print(f"Progress: {current}/{total} ({rate:.1f} img/s)")
    >>>
    >>> tracker = ProgressTracker(callback=my_callback)
    >>> tracker.start("diqa-5000", total=1000)
    >>> for i in range(1000):
    ...     tracker.update(1)
    >>> tracker.finish()
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for progress callback functions.

    Callbacks receive progress updates during processing.
    """

    def __call__(
        self,
        current: int,
        total: int,
        rate: float,
        dataset_name: str | None = None,
    ) -> None:
        """Handle progress update.

        Args:
            current: Current number of items processed
            total: Total number of items to process
            rate: Current processing rate (items/second)
            dataset_name: Name of dataset being processed (optional)
        """


@dataclass
class ProgressState:
    """State for tracking progress of a single dataset.

    Attributes:
        dataset_name: Name of the dataset
        total: Total items to process
        current: Current items processed
        start_time: When processing started
        last_update: Last update timestamp
        errors: Number of errors encountered
    """

    dataset_name: str
    total: int
    current: int = 0
    start_time: float = field(default_factory=time.perf_counter)
    last_update: float = field(default_factory=time.perf_counter)
    errors: int = 0

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time since start."""
        return time.perf_counter() - self.start_time

    @property
    def rate(self) -> float:
        """Processing rate (items/second)."""
        elapsed = self.elapsed_seconds
        if elapsed > 0:
            return self.current / elapsed
        return 0.0

    @property
    def eta_seconds(self) -> float | None:
        """Estimated time remaining (seconds)."""
        if self.rate > 0 and self.current < self.total:
            remaining = self.total - self.current
            return remaining / self.rate
        return None

    @property
    def percent_complete(self) -> float:
        """Percentage complete (0-100)."""
        if self.total > 0:
            return (self.current / self.total) * 100
        return 0.0


class ProgressTracker:
    """Track progress across multiple datasets.

    Provides progress tracking with optional callback for UI updates.
    Supports multi-dataset processing with per-dataset stats.

    Attributes:
        callback: Optional callback for progress updates
        update_interval: Minimum seconds between callback invocations
    """

    def __init__(
        self,
        callback: Callable[[int, int, float, str | None], None] | None = None,
        update_interval: float = 0.5,
    ):
        """Initialize progress tracker.

        Args:
            callback: Optional callback function for progress updates
            update_interval: Minimum interval between updates (seconds)
        """
        self.callback = callback
        self.update_interval = update_interval

        # Per-dataset progress state
        self._states: dict[str, ProgressState] = {}
        self._current_dataset: str | None = None
        self._last_callback_time: float = 0.0

    def start(self, dataset_name: str, total: int) -> None:
        """Start tracking a new dataset.

        Args:
            dataset_name: Name of the dataset
            total: Total items to process
        """
        self._states[dataset_name] = ProgressState(
            dataset_name=dataset_name,
            total=total,
        )
        self._current_dataset = dataset_name

        logger.info(f"Starting progress tracking for {dataset_name}: {total} items")

        # Initial callback
        self._maybe_callback()

    def update(self, increment: int = 1, errors: int = 0) -> None:
        """Update progress for current dataset.

        Args:
            increment: Number of items completed
            errors: Number of errors in this batch
        """
        if self._current_dataset is None:
            return

        state = self._states.get(self._current_dataset)
        if state is None:
            return

        state.current += increment
        state.errors += errors
        state.last_update = time.perf_counter()

        self._maybe_callback()

    def finish(self, dataset_name: str | None = None) -> ProgressState | None:
        """Finish tracking for a dataset.

        Args:
            dataset_name: Dataset to finish (default: current dataset)

        Returns:
            Final ProgressState for the dataset
        """
        name = dataset_name or self._current_dataset
        if name is None:
            return None

        state = self._states.get(name)
        if state is None:
            return None

        logger.info(
            f"Finished {name}: {state.current}/{state.total} items, "
            f"{state.errors} errors, {state.rate:.1f} items/s"
        )

        # Force final callback
        self._last_callback_time = 0
        self._maybe_callback()

        # Clear current if finishing current dataset
        if name == self._current_dataset:
            self._current_dataset = None

        return state

    def get_state(self, dataset_name: str | None = None) -> ProgressState | None:
        """Get progress state for a dataset.

        Args:
            dataset_name: Dataset name (default: current dataset)

        Returns:
            ProgressState or None if not tracking
        """
        name = dataset_name or self._current_dataset
        if name is None:
            return None
        return self._states.get(name)

    def get_all_states(self) -> dict[str, ProgressState]:
        """Get all progress states.

        Returns:
            Dictionary mapping dataset names to ProgressState
        """
        return dict(self._states)

    def get_summary(self) -> dict[str, int | float]:
        """Get summary statistics across all datasets.

        Returns:
            Dictionary with aggregate statistics
        """
        total_items = sum(s.total for s in self._states.values())
        total_processed = sum(s.current for s in self._states.values())
        total_errors = sum(s.errors for s in self._states.values())

        return {
            "datasets_count": len(self._states),
            "total_items": total_items,
            "total_processed": total_processed,
            "total_errors": total_errors,
            "percent_complete": (
                (total_processed / total_items * 100) if total_items > 0 else 0.0
            ),
        }

    def _maybe_callback(self) -> None:
        """Invoke callback if interval has elapsed."""
        if self.callback is None:
            return

        now = time.perf_counter()
        if now - self._last_callback_time < self.update_interval:
            return

        state = self.get_state()
        if state is None:
            return

        self._last_callback_time = now

        try:
            self.callback(
                state.current,
                state.total,
                state.rate,
                state.dataset_name,
            )
        except Exception as e:
            logger.warning(f"Progress callback failed: {e}")


def format_eta(eta_seconds: float | None) -> str:
    """Format ETA as human-readable string.

    Args:
        eta_seconds: Estimated seconds remaining (or None)

    Returns:
        Human-readable string like "2h 30m" or "unknown"
    """
    if eta_seconds is None:
        return "unknown"

    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    if eta_seconds < 3600:
        minutes = int(eta_seconds / 60)
        seconds = int(eta_seconds % 60)
        return f"{minutes}m {seconds}s"

    hours = int(eta_seconds / 3600)
    minutes = int((eta_seconds % 3600) / 60)
    return f"{hours}h {minutes}m"


__all__ = [
    "ProgressCallback",
    "ProgressState",
    "ProgressTracker",
    "format_eta",
]
