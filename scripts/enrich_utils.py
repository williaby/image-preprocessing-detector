"""Shared utilities for enrich scripts.

Provides common functions used across enrich_john11_manuscripts.py,
enrich_john11_printed_editions.py, and enrich_thousand_character_classic.py
to eliminate code duplication.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_jsonl_registry(registry_path: Path) -> list[dict[str, Any]]:
    """Load registry JSONL entries.

    Args:
        registry_path: Path to the JSONL registry file.

    Returns:
        List of parsed dictionary entries.
    """
    entries: list[dict[str, Any]] = []
    if registry_path.exists():
        with registry_path.open("r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    return entries


def now_iso() -> str:
    """Return current UTC time in ISO 8601 format.

    Returns:
        ISO-formatted timestamp string with UTC timezone.
    """
    return datetime.now(timezone.utc).isoformat()


def get_image_properties(image_path: Path) -> dict[str, Any]:
    """Extract image properties via Pillow.

    Args:
        image_path: Path to the image file.

    Returns:
        Dictionary with keys: width, height, color_mode, dpi (or empty on error).
    """
    from PIL import Image

    props: dict[str, Any] = {}
    try:
        with Image.open(image_path) as img:
            props["width"] = img.width
            props["height"] = img.height
            props["color_mode"] = img.mode

            dpi_info = img.info.get("dpi")
            if dpi_info and isinstance(dpi_info, tuple) and dpi_info[0] > 0:
                props["dpi"] = int(dpi_info[0])
            else:
                props["dpi"] = None
    except Exception as exc:
        logger.warning("Failed to read image %s: %s", image_path, exc)
    return props


def dpi_to_category(dpi: int | None) -> str:
    """Categorize DPI into resolution bands.

    Args:
        dpi: DPI value or None if unknown.

    Returns:
        String category: low_<150, medium_150-299, standard_300, or high_>300.
    """
    if dpi is None:
        return "medium_150-299"
    if dpi < 150:
        return "low_<150"
    if dpi < 300:
        return "medium_150-299"
    if dpi == 300:
        return "standard_300"
    return "high_>300"


def normalize_license(raw: str) -> str:
    """Normalize license strings to SPDX-like identifiers.

    Args:
        raw: Raw license string from registry entry.

    Returns:
        Normalized SPDX-like license identifier.
    """
    mapping = {
        "CC0": "CC0-1.0",
        "CC-BY-4.0": "CC-BY-4.0",
        "CC-BY-SA": "CC-BY-SA-4.0",
        "public_domain": "PD",
        "per-image": "mixed-open",
    }
    return mapping.get(raw, raw)
