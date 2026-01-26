# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Atomic file operations for data integrity.

This module provides atomic file writing to prevent data corruption
on crashes or interruptions, fixing issue P2-2.

The key insight is that `os.replace()` is atomic on all platforms
(POSIX and Windows), so we write to a temp file first, then atomically
rename to the target path.

Example:
    >>> from pathlib import Path
    >>> import json
    >>> from image_preprocessing_detector.annotation.integrity.atomic import (
    ...     atomic_write,
    ... )
    >>>
    >>> # Write JSON atomically
    >>> with atomic_write(Path("data.json"), fsync=True) as temp_path:
    ...     temp_path.write_text(json.dumps({"key": "value"}))
    >>>
    >>> # If an exception occurs, the original file is preserved
    >>> with atomic_write(Path("data.json")) as temp_path:
    ...     temp_path.write_text("partial data")
    ...     raise ValueError("Something went wrong")  # Original preserved
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def atomic_write(
    path: Path,
    fsync: bool = False,
    suffix: str = ".tmp",
) -> Iterator[Path]:
    """Context manager for atomic file writes.

    Writes to a temporary file, then atomically renames to the target
    path using `os.replace()`. This ensures that:

    1. The target file is never in a partial/corrupt state
    2. Readers always see either the old or new complete content
    3. Crashes during write don't corrupt existing data

    Args:
        path: Target file path for the final output
        fsync: If True, call fsync before rename for durability guarantee.
            Use for critical data that must survive power loss.
            Has performance cost (~10-100ms depending on storage).
        suffix: Suffix for temporary file (default ".tmp")

    Yields:
        Temporary file Path to write to. The context manager handles
        the atomic rename on successful exit.

    Raises:
        Original exception if write fails. Temp file is cleaned up
        automatically on failure.

    Example:
        >>> with atomic_write(Path("output.json"), fsync=True) as temp:
        ...     temp.write_text('{"status": "complete"}')
        >>> # File is atomically replaced only after write succeeds

    Note:
        The yielded path should be written to using Path methods
        (write_text, write_bytes) or by opening it normally.
        Do NOT write directly to `path` - write to `temp_path`.
    """
    # Create temp file in same directory for atomic rename
    temp_path = path.with_suffix(path.suffix + suffix)

    try:
        yield temp_path

        if fsync:
            # Ensure data is on disk before rename
            _fsync_file(temp_path)

        # Atomic rename - this is the critical operation
        temp_path.replace(path)

    except Exception:
        # Clean up temp file on failure
        temp_path.unlink(missing_ok=True)
        raise


def _fsync_file(path: Path) -> None:
    """Fsync a file to ensure data is on disk.

    Opens the file read-only and calls fsync on the file descriptor.
    This is more efficient than opening read-write.

    Args:
        path: Path to file to fsync
    """
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def safe_write_text(
    path: Path,
    content: str,
    encoding: str = "utf-8",
    fsync: bool = False,
) -> None:
    """Write text to file atomically.

    Convenience function for simple text file writes.

    Args:
        path: Target file path
        content: Text content to write
        encoding: Text encoding (default UTF-8)
        fsync: If True, fsync before rename
    """
    with atomic_write(path, fsync=fsync) as temp_path:
        temp_path.write_text(content, encoding=encoding)


def safe_write_bytes(
    path: Path,
    content: bytes,
    fsync: bool = False,
) -> None:
    """Write bytes to file atomically.

    Convenience function for simple binary file writes.

    Args:
        path: Target file path
        content: Binary content to write
        fsync: If True, fsync before rename
    """
    with atomic_write(path, fsync=fsync) as temp_path:
        temp_path.write_bytes(content)


def atomic_json_write(
    path: Path,
    data: dict[str, Any] | list[Any],
    indent: int | None = 2,
    fsync: bool = False,
) -> None:
    """Write JSON data to file atomically.

    Convenience function for JSON output with atomic safety.

    Args:
        path: Target file path
        data: JSON-serializable data
        indent: JSON indentation (None for compact, 2 for readable)
        fsync: If True, fsync before rename
    """
    import json

    content = json.dumps(data, indent=indent, ensure_ascii=False)
    safe_write_text(path, content, fsync=fsync)


__all__ = [
    "atomic_json_write",
    "atomic_write",
    "safe_write_bytes",
    "safe_write_text",
]
