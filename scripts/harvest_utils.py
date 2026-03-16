"""Shared utilities for harvest scripts.

Provides common functions used across harvest_john11_manuscripts.py,
harvest_john11_printed_editions.py, and harvest_thousand_character_classic.py
to eliminate code duplication.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Lowercase hex string of the SHA256 digest.
    """
    hasher = hashlib.sha256()
    with filepath.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_registry(registry_path: Path) -> tuple[set[str], list[dict[str, Any]]]:
    """Load existing registry entries, returning (sha256_set, entries_list).

    Args:
        registry_path: Path to the JSONL registry file.

    Returns:
        Tuple of (set of SHA256 hashes, list of parsed entries).
    """
    sha_set: set[str] = set()
    entries: list[dict[str, Any]] = []
    if registry_path.exists():
        with registry_path.open("r") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                sha_set.add(entry["sha256"])
                entries.append(entry)
    return sha_set, entries


def append_entry(entry: dict[str, Any], registry_path: Path) -> None:
    """Append a single JSONL entry to the registry.

    Args:
        entry: Dictionary to serialize as a single JSONL line.
        registry_path: Path to the JSONL registry file.
    """
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
