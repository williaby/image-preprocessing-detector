# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for FinTabNet financial table structure dataset.

FinTabNet provides table structure annotations for financial documents
with HTML tokens and cell bounding boxes, using the same format as PubTabNet.

Dataset Structure:
    fintabnet/
        images/
            *.png
        annotations.jsonl or fintabnet.jsonl

JSONL Format (one entry per line, same as PubTabNet):
    {
        "filename": "table_001.png",
        "split": "train",
        "html": {
            "structure": {
                "tokens": ["<thead>", "<tr>", "<td>", ...]
            },
            "cells": [
                {
                    "tokens": ["text", "content"],
                    "bbox": [x1, y1, x2, y2]
                }
            ]
        }
    }

Extracts:
    - table_html: HTML structure tokens joined as string
    - cell_annotations: List of cell dicts with tokens and bboxes

Example:
    >>> parser = FinTabNetParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/fintabnet"),
    ...     image_path=Path("/data/fintabnet/images/table_001.png"),
    ...     config={},
    ... )
    >>> print(labels.table_html[:50])
    <thead><tr><td>...
    >>> print(len(labels.cell_annotations))
    18
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Module-level cache for FinTabNet JSONL annotations (loaded once per file)
# Reuse PubTabNet cache mechanism since format is identical
_FINTABNET_CACHE: dict[str, dict[str, dict]] = {}


class FinTabNetParser(BaseParser):
    """Parser for FinTabNet financial table structure dataset.

    Extracts table HTML structure and cell annotations from JSONL files.
    Uses the same format as PubTabNet for consistency.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["fintabnet"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse FinTabNet table annotations from JSONL file.

        Args:
            dataset_path: Root path of the FinTabNet dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with table_html and cell_annotations populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Try multiple possible JSONL locations
        jsonl_paths = [
            dataset_path / "fintabnet.jsonl",
            dataset_path / "annotations.jsonl",
            dataset_path / "FinTabNet.jsonl",
            dataset_path.parent / "fintabnet.jsonl",
        ]

        jsonl_path = None
        for path in jsonl_paths:
            if path.exists():
                jsonl_path = path
                break

        if not jsonl_path:
            return labels

        # Load annotations into cache if not already done
        cache_key = str(jsonl_path)
        if cache_key not in _FINTABNET_CACHE:
            try:
                annotations_by_filename: dict[str, dict] = {}
                with open(jsonl_path) as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            if "filename" in entry:
                                annotations_by_filename[entry["filename"]] = entry
                _FINTABNET_CACHE[cache_key] = annotations_by_filename
                logger.debug(
                    f"Loaded {len(annotations_by_filename)} FinTabNet annotations from {jsonl_path}"
                )
            except Exception as e:
                logger.warning(f"Failed to load FinTabNet JSONL from {jsonl_path}: {e}")
                _FINTABNET_CACHE[cache_key] = {}

        # Look up annotation for this image
        filename = image_path.name
        annotations = _FINTABNET_CACHE.get(cache_key, {})
        entry = annotations.get(filename)

        if entry and "html" in entry:
            html_data = entry["html"]

            # Extract HTML structure as string
            if "structure" in html_data and "tokens" in html_data["structure"]:
                labels.table_html = "".join(html_data["structure"]["tokens"])

            # Extract cell annotations
            if "cells" in html_data:
                labels.cell_annotations = html_data["cells"]

        return labels


__all__ = ["FinTabNetParser"]
