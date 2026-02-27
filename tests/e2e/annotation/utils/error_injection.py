"""Error injection utilities for testing failure scenarios.

These utilities allow controlled injection of errors into various parts
of the annotation pipeline for testing error handling and recovery.

Usage:
    with inject_enrichment_failure(after_n_samples=3):
        result = pipeline.process(...)
    assert result.samples_failed >= 1
"""

from __future__ import annotations

import contextlib
import errno
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from image_preprocessing_detector.annotation.enrichment.manager import (
        EnrichmentManager,
        EnrichmentResult,
    )


@contextlib.contextmanager
def inject_enrichment_failure(
    after_n_samples: int = 5,
    error_type: type[Exception] = RuntimeError,
    error_message: str = "Injected enrichment failure for testing",
) -> Iterator[dict[str, int]]:
    """Inject failure into enrichment after N samples.

    Patches EnrichmentManager.enrich to fail after processing N samples.
    Tracks the number of successful and failed enrichments.

    Args:
        after_n_samples: Number of successful samples before failure
        error_type: Type of exception to raise
        error_message: Error message for the exception

    Yields:
        Dictionary with 'successful' and 'failed' counts

    Example:
        with inject_enrichment_failure(after_n_samples=3) as stats:
            result = pipeline.process(...)
        assert stats['successful'] == 3
        assert stats['failed'] >= 1
    """
    from image_preprocessing_detector.annotation.enrichment.manager import (
        EnrichmentManager,
    )

    stats = {"successful": 0, "failed": 0}
    original_enrich = EnrichmentManager.enrich

    def failing_enrich(self: EnrichmentManager, image_path: Path) -> EnrichmentResult:
        if stats["successful"] >= after_n_samples:
            stats["failed"] += 1
            raise error_type(error_message)
        result = original_enrich(self, image_path)
        stats["successful"] += 1
        return result

    with patch.object(EnrichmentManager, "enrich", failing_enrich):
        yield stats


@contextlib.contextmanager
def inject_disk_full(
    target_path: Path,
    error_code: int = errno.ENOSPC,
) -> Iterator[None]:
    """Simulate disk full when writing to target path.

    Patches builtins.open to raise OSError when attempting to write
    to files under the target path.

    Args:
        target_path: Path prefix that triggers the error
        error_code: errno value (default: ENOSPC - No space left on device)

    Yields:
        None

    Example:
        with inject_disk_full(tmp_path / "output"):
            result = pipeline.process(...)
        assert "No space left" in str(result.errors[0])
    """
    import builtins

    original_open = builtins.open

    def failing_open(
        file: str | Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ) -> object:
        file_path = Path(file) if isinstance(file, str) else file
        try:
            is_under_target = file_path.resolve().is_relative_to(target_path.resolve())
        except (ValueError, OSError):
            is_under_target = False

        if "w" in mode and is_under_target:
            raise OSError(error_code, "No space left on device", str(file))
        return original_open(file, mode, *args, **kwargs)

    with patch.object(builtins, "open", failing_open):
        yield


@contextlib.contextmanager
def inject_permission_denied(
    target_path: Path,
    error_code: int = errno.EACCES,
) -> Iterator[None]:
    """Simulate permission denied when accessing target path.

    Patches builtins.open to raise PermissionError when attempting to
    access files under the target path.

    Args:
        target_path: Path prefix that triggers the error
        error_code: errno value (default: EACCES - Permission denied)

    Yields:
        None

    Example:
        with inject_permission_denied(tmp_path / "checkpoints"):
            result = pipeline.process(...)
        assert "Permission denied" in str(result.errors[0])
    """
    import builtins

    original_open = builtins.open

    def failing_open(
        file: str | Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ) -> object:
        file_path = Path(file) if isinstance(file, str) else file
        try:
            is_under_target = file_path.resolve().is_relative_to(target_path.resolve())
        except (ValueError, OSError):
            is_under_target = False

        if is_under_target:
            raise PermissionError(error_code, "Permission denied", str(file))
        return original_open(file, mode, *args, **kwargs)

    with patch.object(builtins, "open", failing_open):
        yield


@contextlib.contextmanager
def inject_checkpoint_corruption(checkpoint_dir: Path) -> Iterator[None]:
    """Inject corrupted checkpoint files.

    Creates invalid JSON in checkpoint files when the CheckpointManager
    attempts to save, simulating file corruption.

    Args:
        checkpoint_dir: Directory where checkpoints are stored

    Yields:
        None
    """
    import json

    original_dump = json.dump

    def corrupting_dump(
        obj: object,
        fp: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        # Check if we're writing to checkpoint directory
        if hasattr(fp, "name"):
            fp_path = Path(fp.name)
            try:
                is_checkpoint = fp_path.resolve().is_relative_to(
                    checkpoint_dir.resolve()
                )
            except (ValueError, OSError):
                is_checkpoint = False

            if is_checkpoint:
                # Write corrupted JSON
                if hasattr(fp, "write"):
                    fp.write("{corrupted: invalid json without quotes}")  # type: ignore[union-attr]
                    return

        original_dump(obj, fp, *args, **kwargs)

    with patch.object(json, "dump", corrupting_dump):
        yield
