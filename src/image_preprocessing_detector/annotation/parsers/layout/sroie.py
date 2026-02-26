# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for SROIE receipt OCR and information extraction dataset.

SROIE (Scanned Receipt OCR and Information Extraction) provides receipt
images with text annotations and key entity extraction.

Dataset Structure:
    SROIE/
        train/
            {id}.jpg
            {id}.txt  - OCR text with bounding boxes
        test/
            {id}.jpg
            {id}.txt

Text Annotation Format (one box per line):
    x1,y1,x2,y2,x3,y3,x4,y4,text

Where:
    - (x1,y1), (x2,y2), (x3,y3), (x4,y4): Four corners of the text box (quad)
    - text: OCR transcription of the text region

Extracts:
    - text_instances: List of text boxes with coordinates and transcriptions
    - split: Dataset split (train/test)
    - document_type: "receipt"

Example:
    >>> parser = SroieParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/sroie"),
    ...     image_path=Path("/data/sroie/train/X00001.jpg"),
    ...     config={},
    ... )
    >>> print(len(labels.text_instances))
    45
    >>> print(labels.text_instances[0]["text"])
    COMPANY NAME
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "sroie"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "sroie_metadata.json"
__l4_integrate__ = "scripts/integrate_sroie_enrichments.py"


import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class SroieParser(BaseParser):
    """Parser for SROIE receipt OCR and IE dataset.

    Extracts text boxes with 8-point polygon coordinates and transcriptions
    from paired .txt annotation files.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["sroie"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SROIE receipt labels from annotation files.

        Args:
            dataset_path: Root path of the SROIE dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with text_instances and raw_labels populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Try to find transcription file
        txt_path = image_path.with_suffix(".txt")
        if txt_path.exists():
            try:
                with open(txt_path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    # SROIE format: x1,y1,x2,y2,x3,y3,x4,y4,text
                    text_instances = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(",", 8)
                        if len(parts) >= 9:
                            try:
                                coords = [int(x) for x in parts[:8]]
                                text = parts[8]
                                text_instances.append(
                                    {
                                        "bbox": coords,
                                        "text": text,
                                    }
                                )
                            except ValueError:
                                continue
                    if text_instances:
                        labels.text_instances = text_instances

                        # Populate Layer 2 text_content schema fields
                        full_text = " ".join(
                            str(instance["text"]) for instance in text_instances
                        )
                        if labels.raw_labels is None:
                            labels.raw_labels = {}
                        labels.raw_labels["text_content"] = {
                            "full_text": full_text,
                            "source_type": "dataset_provided",
                            "source_format": "txt_quad_text",
                            "extraction_method": "SroieParser.parse",
                            "extraction_timestamp": None,
                            "is_complete": True,
                            "encoding": "utf-8",
                        }
            except Exception as e:
                logger.debug(f"Failed to parse SROIE annotations: {e}")

        # Extract split from path
        path_str = str(image_path).lower()
        if "train" in path_str:
            labels.raw_labels["split"] = "train"
        elif "test" in path_str:
            labels.raw_labels["split"] = "test"

        labels.raw_labels["document_type"] = "receipt"

        return labels


__all__ = ["SroieParser"]
