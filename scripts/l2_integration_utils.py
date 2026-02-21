#!/usr/bin/env python3
"""Shared utilities for Layer 2 metadata integration scripts.

Provides common helpers used across integrate_*.py scripts that write
enrichment data into L2 metadata JSON files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def get_sample_filename(sample: dict[str, Any]) -> str | None:
    """Extract the original filename from a L2 metadata sample.

    Handles multiple field locations used across datasets.

    Args:
        sample: A single sample dict from the L2 metadata.

    Returns:
        The original filename string, or None if not found.
    """
    # Try source.original_filename first (standard L2 field)
    source = sample.get("source", {})
    filename = source.get("original_filename")
    if filename:
        return str(Path(filename).name)

    # Fallback: sample_id may contain the filename
    sample_id = sample.get("sample_id", "")
    if sample_id and "." in sample_id:
        return sample_id

    return None


def next_version_number(enrichments: dict[str, Any]) -> int:
    """Compute the next version number from the enrichments structure.

    Args:
        enrichments: The enrichments dict for a sample (contains
            ``current_version`` and ``versions`` keys).

    Returns:
        Integer version number to use for the new enrichment entry.
    """
    current_ver = enrichments.get("current_version")
    if isinstance(current_ver, int):
        return current_ver + 1
    if isinstance(current_ver, str):
        if current_ver.startswith("v"):
            try:
                return int(current_ver[1:]) + 1
            except ValueError:
                return len(enrichments.get("versions", [])) + 1
        if current_ver.isdigit():
            return int(current_ver) + 1
    return len(enrichments.get("versions", [])) + 1
