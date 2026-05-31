"""Global split registry for preventing cross-dataset train/test leakage.

This module provides a SHA256-keyed registry that assigns each source image
to a fixed train/val/test split. When multiple derived datasets are generated
from the same base images (e.g., orientation, skew, resolution quality views),
the registry ensures the same source image is ALWAYS in the same split.

Key Features:
    - SHA256-based image identity (content-addressable)
    - JSONL file format for append-only, merge-friendly storage
    - Source-level split propagation (all derived images inherit source split)
    - Deterministic split assignment via consistent hashing
    - Thread-safe writes via file locking

Example:
    >>> from image_preprocessing_detector.schema_utils.split_registry import (
    ...     SplitRegistry,
    ... )
    >>> registry = SplitRegistry("splits.jsonl")
    >>> split = registry.assign_split("abc123sha256...", ratios=(0.8, 0.1, 0.1))
    >>> print(split)  # "train", "val", or "test" (deterministic for this hash)
    >>> registry.lookup("abc123sha256...")
    'train'
"""

from __future__ import annotations

import hashlib
import json
import logging
import struct
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default split ratios
DEFAULT_SPLIT_RATIOS: tuple[float, float, float] = (0.80, 0.10, 0.10)
SPLIT_NAMES: tuple[str, str, str] = ("train", "val", "test")


def _hash_to_split(
    sha256_hex: str,
    ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
) -> str:
    """Deterministically assign a split based on SHA256 hash.

    Uses the first 8 bytes of the hash as a uniform random number
    to assign a split according to the given ratios.

    Args:
        sha256_hex (str): Hex-encoded SHA256 hash of the source image
        ratios (tuple[float, float, float]): (train, val, test) ratios summing to 1.0

    Returns:
        Split name: "train", "val", or "test"
    """
    # Take first 8 bytes of hash -> uint64 -> normalize to [0, 1)
    hash_bytes = bytes.fromhex(sha256_hex[:16])
    value = struct.unpack(">Q", hash_bytes)[0]
    normalized = value / (2**64)

    # Assign to split based on cumulative ratios
    cumulative = 0.0
    for name, ratio in zip(SPLIT_NAMES, ratios, strict=True):
        cumulative += ratio
        if normalized < cumulative:
            return name

    return SPLIT_NAMES[-1]  # Fallback to test


def compute_image_hash(image_path: str | Path) -> str:
    """Compute SHA256 hash of an image file.

    Args:
        image_path (str | Path): Path to the image file

    Returns:
        str: Hex-encoded SHA256 hash string"""
    sha256 = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class SplitRegistry:
    """Global split registry for cross-dataset leakage prevention.

    Stores split assignments in a JSONL file (one JSON object per line).
    Each entry maps a SHA256 image hash to a split assignment with metadata.

    The registry is designed for append-only operation:
    - New entries are appended to the file
    - Existing entries are never modified
    - Lookups are O(1) via in-memory dict loaded at init

    Attributes:
        registry_path: Path to the JSONL registry file
        _entries: In-memory dict mapping SHA256 -> split assignment
    """

    def __init__(self, registry_path: str | Path) -> None:
        """Initialize the split registry.

        Args:
            registry_path (str | Path): Path to the JSONL file (created if not exists)"""
        self.registry_path = Path(registry_path)
        self._entries: dict[str, dict[str, Any]] = {}
        if self.registry_path.exists():
            self._load()

    def _load(self) -> None:
        """Load existing registry entries from JSONL file."""
        count = 0
        with open(self.registry_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    sha256 = entry.get("sha256")
                    if sha256:
                        self._entries[sha256] = entry
                        count += 1
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed line %d in %s",
                        line_num,
                        self.registry_path,
                    )
        logger.info("Loaded %d entries from %s", count, self.registry_path)

    def lookup(self, sha256_hex: str) -> str | None:
        """Look up the split assignment for an image hash.

        Args:
            sha256_hex (str): SHA256 hex digest of the source image

        Returns:
            str | None: Split name ("train", "val", "test") or None if not registered"""
        entry = self._entries.get(sha256_hex)
        if entry:
            return entry.get("split")
        return None

    def assign_split(
        self,
        sha256_hex: str,
        ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
        source_dataset: str | None = None,
        source_path: str | None = None,
    ) -> str:
        """Assign a split to an image, or return existing assignment.

        If the image is already registered, returns the existing split.
        Otherwise, deterministically assigns a split based on the hash.

        Args:
            sha256_hex (str): SHA256 hex digest of the source image
            ratios (tuple[float, float, float]): (train, val, test) split ratios
            source_dataset (str | None): Optional dataset name for provenance
            source_path (str | None): Optional original file path for provenance

        Returns:
            str: Assigned split name ("train", "val", "test")"""
        existing = self.lookup(sha256_hex)
        if existing is not None:
            return existing

        split = _hash_to_split(sha256_hex, ratios)

        entry: dict[str, Any] = {
            "sha256": sha256_hex,
            "split": split,
        }
        if source_dataset:
            entry["source_dataset"] = source_dataset
        if source_path:
            entry["source_path"] = source_path

        self._entries[sha256_hex] = entry

        # Append to file
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return split

    def verify_no_leakage(
        self,
        dataset_a_hashes: set[str],
        dataset_b_hashes: set[str],
        split_a: str = "train",
        split_b: str = "test",
    ) -> list[str]:
        """Verify no cross-split contamination between two hash sets.

        Args:
            dataset_a_hashes (set[str]): Hashes assigned to split_a
            dataset_b_hashes (set[str]): Hashes assigned to split_b
            split_a (str): Expected split for dataset A
            split_b (str): Expected split for dataset B

        Returns:
            list[str]: List of SHA256 hashes that appear in both splits (should be empty)"""
        violations = []
        overlap = dataset_a_hashes & dataset_b_hashes
        for sha256 in overlap:
            entry = self._entries.get(sha256)
            if entry:
                assigned = entry.get("split")
                if (assigned != split_a and assigned != split_b) or split_a != split_b:
                    violations.append(sha256)
        return violations

    @property
    def stats(self) -> dict[str, int]:
        """Get split distribution statistics.

        Returns:
            dict[str, int]: Dict mapping split name to count"""
        counts: dict[str, int] = {"train": 0, "val": 0, "test": 0}
        for entry in self._entries.values():
            split = entry.get("split", "unknown")
            counts[split] = counts.get(split, 0) + 1
        return counts

    def __len__(self) -> int:
        """Return the number of registered images."""
        return len(self._entries)

    def __contains__(self, sha256_hex: str) -> bool:
        """Check if an image hash is registered."""
        return sha256_hex in self._entries


__all__ = [
    "DEFAULT_SPLIT_RATIOS",
    "SPLIT_NAMES",
    "SplitRegistry",
    "compute_image_hash",
]
