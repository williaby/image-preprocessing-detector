# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for PubTabNet table structure dataset.

PubTabNet provides table structure annotations with HTML tokens and cell
bounding boxes for table recognition from PubMed Central papers.

Dataset Structure:
    pubtabnet/
        train/
            PMC*.png
        val/
            PMC*.png
        PubTabNet_2.0.0.jsonl  - Annotations for all images

JSONL Format (one entry per line):
    {
        "filename": "PMC1234_table_0.png",
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
    - split: Dataset split (train/val/test)

Example:
    >>> parser = PubTabNetParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/pubtabnet"),
    ...     image_path=Path("/data/pubtabnet/train/PMC1234_table_0.png"),
    ...     config={},
    ... )
    >>> print(labels.table_html[:50])
    <thead><tr><td>...
    >>> print(len(labels.cell_annotations))
    24
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)

# Module-level cache for PubTabNet JSONL annotations (loaded once per file)
_PUBTABNET_CACHE: dict[str, dict[str, dict]] = {}


class PubTabNetParser(BaseParser):
    """Parser for PubTabNet table structure dataset.

    Extracts table HTML structure and cell annotations from JSONL files.
    Uses module-level caching to load JSONL only once per file.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["pubtabnet"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse PubTabNet table annotations from JSONL file.

        Args:
            dataset_path: Root path of the PubTabNet dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with table_html, cell_annotations, and raw_labels populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Try multiple possible JSONL locations
        jsonl_paths = [
            dataset_path / "PubTabNet_2.0.0.jsonl",
            dataset_path / "pubtabnet.jsonl",
            dataset_path / "annotations.jsonl",
            dataset_path.parent / "PubTabNet_2.0.0.jsonl",
        ]

        # Find and load JSONL if not cached
        jsonl_path = None
        for path in jsonl_paths:
            if path.exists():
                jsonl_path = path
                break

        if not jsonl_path:
            return labels

        # Load annotations into cache if not already done
        cache_key = str(jsonl_path)
        if cache_key not in _PUBTABNET_CACHE:
            try:
                annotations_by_filename: dict[str, dict] = {}
                with open(jsonl_path) as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            if "filename" in entry:
                                annotations_by_filename[entry["filename"]] = entry
                _PUBTABNET_CACHE[cache_key] = annotations_by_filename
                logger.debug(
                    f"Loaded {len(annotations_by_filename)} PubTabNet annotations from {jsonl_path}"
                )
            except Exception as e:
                logger.warning(f"Failed to load PubTabNet JSONL from {jsonl_path}: {e}")
                _PUBTABNET_CACHE[cache_key] = {}

        # Look up annotation for this image
        filename = image_path.name
        annotations = _PUBTABNET_CACHE.get(cache_key, {})
        entry = annotations.get(filename)

        if entry and "html" in entry:
            html_data = entry["html"]

            # Extract HTML structure as string
            if "structure" in html_data and "tokens" in html_data["structure"]:
                labels.table_html = "".join(html_data["structure"]["tokens"])

            # Extract cell annotations
            if "cells" in html_data:
                labels.cell_annotations = html_data["cells"]

            # Store split information if available
            if labels.raw_labels is None:
                labels.raw_labels = {}
            if "split" in entry:
                labels.raw_labels["split"] = entry["split"]

        return labels


__all__ = ["PubTabNetParser"]
