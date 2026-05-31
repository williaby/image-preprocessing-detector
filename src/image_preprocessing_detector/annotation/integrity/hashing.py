"""Data integrity hashing utilities.

This module provides full-file SHA256 hashing and deterministic sample ID
generation, fixing critical data integrity issues:

- P0-1: Full-file SHA256 (was 64KB partial) - BREAKING CHANGE
- P1-3: Deterministic sample IDs (was random UUIDs)

BREAKING CHANGE NOTICE:
    The fix for P0-1 changes ALL existing sample IDs. A full re-processing
    of all datasets is REQUIRED upon migration. Incremental updates against
    pre-migration data are NOT supported.

Example:
    >>> from pathlib import Path
    >>> from image_preprocessing_detector.annotation.integrity.hashing import (
    ...     compute_full_sha256,
    ...     compute_sample_id,
    ... )
    >>>
    >>> file_hash = compute_full_sha256(Path("image.png"))
    >>> sample_id = compute_sample_id("diqa-5000", "train/img001.png", file_hash)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Default chunk size for streaming hash (64KB - optimal for most filesystems)
DEFAULT_CHUNK_SIZE = 65536


def compute_full_sha256(
    file_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Compute SHA256 hash of ENTIRE file content.

    BREAKING CHANGE: This replaces partial 64KB hashing.
    All existing sample IDs will change.

    Streams the file in chunks to handle large files efficiently
    without loading the entire file into memory.

    Args:
        file_path (Path): Path to the file to hash.
        chunk_size (int): Size of chunks to read (default 64KB).

    Returns:
        str: Lowercase hexadecimal SHA256 hash string (64 characters).
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_sample_id(
    dataset_name: str,
    relative_path: str,
    file_hash: str,
) -> str:
    """Generate deterministic sample ID for deduplication.

    Creates a stable, reproducible ID from dataset name, file path,
    and content hash. This enables:
    - Deduplication across datasets
    - Incremental updates (same file = same ID)
    - Reproducible processing runs

    The ID is a truncated SHA256 hash of the combined inputs,
    providing collision resistance while keeping IDs manageable.

    Args:
        dataset_name (str): Name of the source dataset (e.g., "diqa-5000").
        relative_path (str): Path relative to dataset root (e.g., "train/img001.png").
        file_hash (str): Full SHA256 hash of file content.

    Returns:
        str: 32-character lowercase hexadecimal ID.

    Example:
        >>> sample_id = compute_sample_id(
        ...     "diqa-5000", "train/img001.png", "abc123def456..."
        ... )
        >>> len(sample_id)
        32
    """
    # Combine inputs with separator to prevent collisions
    # e.g., "dataset:path" vs "dataset:" + "path" would collide without separator
    content = f"{dataset_name}:{relative_path}:{file_hash}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def compute_content_hash(data: bytes) -> str:
    """Compute SHA256 hash of in-memory content.

    Useful for hashing configuration, computed values, or other
    non-file data for provenance tracking.

    Args:
        data (bytes): Bytes to hash.

    Returns:
        str: Lowercase hexadecimal SHA256 hash string.
    """
    return hashlib.sha256(data).hexdigest()


def compute_string_hash(text: str, encoding: str = "utf-8") -> str:
    """Compute SHA256 hash of string content.

    Convenience wrapper for hashing text data like configuration
    or JSON serializations.

    Args:
        text (str): String to hash.
        encoding (str): Text encoding (default UTF-8).

    Returns:
        str: Lowercase hexadecimal SHA256 hash string.
    """
    return hashlib.sha256(text.encode(encoding)).hexdigest()


def verify_file_hash(file_path: Path, expected_hash: str) -> bool:
    """Verify file content matches expected hash.

    Args:
        file_path (Path): Path to file to verify.
        expected_hash (str): Expected SHA256 hash (lowercase hex).

    Returns:
        bool: True if hash matches, False otherwise.
    """
    actual_hash = compute_full_sha256(file_path)
    return actual_hash.lower() == expected_hash.lower()


__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "compute_content_hash",
    "compute_full_sha256",
    "compute_sample_id",
    "compute_string_hash",
    "verify_file_hash",
]
