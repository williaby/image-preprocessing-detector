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
    - language_code: "en" (English) - dataset-level assignment
    - script_name: "Latin" with ISO 15924 code "Latn" - dataset-level assignment

Language Assignment Rationale:
    FinTabNet is sourced from SEC EDGAR filings (US Securities & Exchange
    Commission). All documents are official US financial filings which are
    legally required to be in English. Text-based analysis of 97,475 samples
    confirmed 99.4% English detection with 99.9% Latin script.

Phase 5 Fix: Uses StreamingJSONLReader for memory-efficient access.

Example:
    >>> parser = FinTabNetParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/fintabnet"),
    ...     image_path=Path("/data/fintabnet/images/table_001.png"),
    ...     config={},
    ... )
    >>> print(labels.table_html[:50])
    <thead><tr><td>...
    >>> print(labels.language_code)
    en
    >>> print(labels.script_name)
    Latin
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "fintabnet"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "fintabnet_metadata.json"
__l4_integrate__ = "scripts/integrate_fintabnet_enrichments.py"


import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ...storage.cache import StreamingJSONLReader
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Phase 5: Use streaming readers instead of loading entire JSONL into memory
_FINTABNET_READERS: dict[str, StreamingJSONLReader] = {}


class FinTabNetParser(BaseParser):
    """Parser for FinTabNet financial table structure dataset.

    Extracts table HTML structure and cell annotations from JSONL files.
    Uses the same format as PubTabNet for consistency.

    Phase 5: Uses StreamingJSONLReader for memory-efficient access.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["fintabnet"]

    def _get_reader(self, jsonl_path: Path) -> StreamingJSONLReader:
        """Get or create a StreamingJSONLReader for the JSONL file.

        Args:
            jsonl_path: Path to the JSONL annotation file

        Returns:
            StreamingJSONLReader instance (cached per file path)
        """
        cache_key = str(jsonl_path)
        if cache_key not in _FINTABNET_READERS:
            logger.debug(f"Creating StreamingJSONLReader for {jsonl_path}")
            _FINTABNET_READERS[cache_key] = StreamingJSONLReader(
                file_path=jsonl_path,
                cache_size=5_000,  # Cache 5K entries for repeated access
                filename_key="filename",
            )
        return _FINTABNET_READERS[cache_key]

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
            OriginalLabels with table_html, cell_annotations, and language/script

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Dataset-level language assignment: All FinTabNet samples are English
        # Source: SEC EDGAR filings (US financial documents, legally required English)
        # Validation: Text analysis of 97,475 samples showed 99.4% English, 99.9% Latin
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.raw_labels = {
            "iso15924_script": "Latn",
            "language_source": "dataset_provenance",
            "language_confidence": 0.99,
        }

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

        # Phase 5: Use StreamingJSONLReader for memory-efficient access
        try:
            reader = self._get_reader(jsonl_path)
            filename = image_path.name
            entry = reader.get(filename)
        except Exception as e:
            logger.warning(f"Failed to read FinTabNet annotation for {image_path}: {e}")
            return labels

        if entry and "html" in entry:
            html_data = entry["html"]

            # Extract HTML structure as string
            if "structure" in html_data and "tokens" in html_data["structure"]:
                labels.table_html = "".join(html_data["structure"]["tokens"])

            # Extract cell annotations
            if "cells" in html_data:
                labels.cell_annotations = html_data["cells"]

                # R2: Aggregate cell text tokens into full_text
                all_text = []
                layout_detections = []

                for cell in html_data["cells"]:
                    # Aggregate text content
                    if "tokens" in cell:
                        cell_text = " ".join(cell["tokens"])
                        all_text.append(cell_text)

                    # R3: Convert cell boxes (XYXY) to COCO format (XYWH) for layout_detections
                    if "bbox" in cell:
                        x1, y1, x2, y2 = cell["bbox"]
                        x, y, w, h = x1, y1, x2 - x1, y2 - y1

                        detection = {
                            "class_name": "Text",  # Cell content is text
                            "bbox": [x, y, w, h],  # COCO XYWH format
                            "bbox_original": cell["bbox"],  # Preserve XYXY for audit
                            "bbox_source_format": "xyxy",
                            "confidence": 1.0,  # Ground truth data
                            "source": "fintabnet_gt",
                        }
                        layout_detections.append(detection)

                # Set text_content if any text was found
                if all_text:
                    labels.raw_labels["text_content"] = {
                        "full_text": " ".join(all_text),
                        "source_type": "dataset_provided",
                        "source_format": "jsonl_cell_tokens",
                        "extraction_method": "FinTabNetParser.parse",
                        "extraction_timestamp": None,
                        "is_complete": True,
                        "encoding": "utf-8",
                    }

                # Set layout_detections if any boxes were converted
                if layout_detections:
                    labels.raw_labels["layout_detections"] = layout_detections

        # R4: Set dataset-level metadata
        labels.raw_labels["capture_method"] = {
            "method": "born_digital",
            "confidence": 1.0,
            "detection_method": "dataset_config",
        }

        labels.raw_labels["domain"] = {
            "level1": "FIN",
            "confidence": 0.99,
        }

        labels.raw_labels["content_flags"] = {
            "has_table": True,
            "tier": "tier_0_exact",
            "source": "tier_0_exact_by_construction",
        }

        return labels


__all__ = ["FinTabNetParser"]
