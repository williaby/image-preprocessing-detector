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
    - language_code: "en" (English) - dataset-level assignment
    - script_name: "Latin" with ISO 15924 code "Latn" - dataset-level assignment

Language Assignment Rationale:
    PubTabNet is sourced from PubMed Central scientific literature. All papers
    are peer-reviewed English scientific publications. Text-based analysis of
    a 1% sample (5,685 tables) confirmed 98% Latin script with 89% English
    language detection (75% English + 14.1% Latin scientific terminology).

Phase 5 Fix: Uses StreamingJSONLReader instead of loading entire 500K+ entries
into memory. See storage.cache module for memory management details.

Example:
    >>> parser = PubTabNetParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/pubtabnet"),
    ...     image_path=Path("/data/pubtabnet/train/PMC1234_table_0.png"),
    ...     config={},
    ... )
    >>> print(labels.table_html[:50])
    <thead><tr><td>...
    >>> print(labels.language_code)
    en
    >>> print(labels.script_name)
    Latin
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ...storage.cache import StreamingJSONLReader
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Phase 5: Use streaming readers instead of loading entire JSONL into memory
# Key: jsonl_path -> StreamingJSONLReader (bounded cache of 10K entries)
_PUBTABNET_READERS: dict[str, StreamingJSONLReader] = {}


class PubTabNetParser(BaseParser):
    """Parser for PubTabNet table structure dataset.

    Extracts table HTML structure and cell annotations from JSONL files.

    Phase 5: Uses StreamingJSONLReader for memory-efficient access to 500K+
    entries without loading entire file into memory.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["pubtabnet"]

    def _get_reader(self, jsonl_path: Path) -> StreamingJSONLReader:
        """Get or create a StreamingJSONLReader for the JSONL file.

        Args:
            jsonl_path: Path to the JSONL annotation file

        Returns:
            StreamingJSONLReader instance (cached per file path)
        """
        cache_key = str(jsonl_path)
        if cache_key not in _PUBTABNET_READERS:
            logger.debug(f"Creating StreamingJSONLReader for {jsonl_path}")
            _PUBTABNET_READERS[cache_key] = StreamingJSONLReader(
                file_path=jsonl_path,
                cache_size=10_000,  # Cache 10K entries for repeated access
                filename_key="filename",
            )
        return _PUBTABNET_READERS[cache_key]

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

        # Dataset-level language assignment: All PubTabNet samples are English
        # Source: PubMed Central scientific literature (peer-reviewed English papers)
        # Validation: 1% sample (5,685 tables) showed 98% Latin, 89% English detection
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.raw_labels = {
            "iso15924_script": "Latn",
            "language_source": "dataset_provenance",
            "language_confidence": 0.98,
        }

        # Try multiple possible JSONL locations
        jsonl_paths = [
            dataset_path / "PubTabNet_2.0.0.jsonl",
            dataset_path / "pubtabnet.jsonl",
            dataset_path / "annotations.jsonl",
            dataset_path.parent / "PubTabNet_2.0.0.jsonl",
        ]

        # Find JSONL file
        jsonl_path = None
        for path in jsonl_paths:
            if path.exists():
                jsonl_path = path
                break

        if not jsonl_path:
            return labels

        # Phase 5: Use StreamingJSONLReader for memory-efficient access
        try:
            reader = self._get_reader(jsonl_path)
            filename = image_path.name
            entry = reader.get(filename)
        except Exception as e:
            logger.warning(f"Failed to read PubTabNet annotation for {image_path}: {e}")
            return labels

        if entry and "html" in entry:
            html_data = entry["html"]

            # Extract HTML structure as string
            if "structure" in html_data and "tokens" in html_data["structure"]:
                labels.table_html = "".join(html_data["structure"]["tokens"])

            # Extract cell annotations
            if "cells" in html_data:
                labels.cell_annotations = html_data["cells"]

            # Store split information if available (preserve existing raw_labels)
            if "split" in entry:
                labels.raw_labels["split"] = entry["split"]

        return labels


__all__ = ["PubTabNetParser"]
