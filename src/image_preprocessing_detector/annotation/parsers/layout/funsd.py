# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for FUNSD form understanding dataset.

FUNSD (Form Understanding in Noisy Scanned Documents) provides form annotations
with entity boxes, text, labels, and linking information.

Dataset Structure:
    FUNSD/
        training_data/
            annotations/
                *.json
            images/
                *.png
        testing_data/
            annotations/
                *.json
            images/
                *.png
        or
        annotations/
            *.json
        images/
            *.png

FUNSD Annotation Format (dict/object, NOT list - P0-4 fix):
    {
        "form": [
            {
                "text": "Entity text",
                "box": [x1, y1, x2, y2],
                "label": "question|answer|header|other",
                "linking": [[entity_id1, entity_id2], ...],
                "words": [
                    {"text": "word", "box": [x1, y1, x2, y2]}
                ]
            }
        ]
    }

Labels:
    - question: Form field questions
    - answer: Form field answers
    - header: Form headers
    - other: Other text elements

Example:
    >>> parser = FunsdParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/funsd"),
    ...     image_path=Path("/data/funsd/training_data/images/form001.png"),
    ...     config={},
    ... )
    >>> print(labels.funsd_annotations["form"][0]["label"])
    question
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class FunsdParser(BaseParser):
    """Parser for FUNSD form understanding dataset.

    Extracts form entity annotations with text, bounding boxes, labels,
    and linking information from JSON files in training/testing splits.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["funsd"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse FUNSD form annotations.

        Args:
            dataset_path: Root path of the FUNSD dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with funsd_annotations (dict) and raw_labels populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Try multiple possible annotation locations
        json_paths = [
            # Alongside image
            image_path.with_suffix(".json"),
            # Standard FUNSD training structure
            dataset_path / "training_data" / "annotations" / f"{image_path.stem}.json",
            # Standard FUNSD testing structure
            dataset_path / "testing_data" / "annotations" / f"{image_path.stem}.json",
            # Alternative annotation folder
            dataset_path / "annotations" / f"{image_path.stem}.json",
        ]

        for json_path in json_paths:
            if json_path.exists():
                try:
                    with open(json_path) as f:
                        labels.funsd_annotations = json.load(f)
                    break  # Found annotations, stop searching
                except Exception as e:
                    logger.debug(
                        f"Failed to parse FUNSD annotations from {json_path}: {e}"
                    )

        # Even without annotations, we know it's a form dataset (Tier 0)
        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["document_type"] = "form"
        labels.raw_labels["is_scanned"] = True

        # FUNSD is English forms - populate language_code (Layer 1 field)
        labels.language_code = "en"

        # Aggregate text transcription from form entities if available
        if labels.funsd_annotations and "form" in labels.funsd_annotations:
            form_entities = labels.funsd_annotations["form"]
            full_text = " ".join(
                entity.get("text", "") for entity in form_entities if entity.get("text")
            )
            if full_text.strip():
                labels.transcription = full_text.strip()

                # Populate Layer 2 text_content schema fields
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["text_content"] = {
                    "full_text": full_text.strip(),
                    "source_type": "dataset_provided",
                    "source_format": "json_entity_text",
                    "extraction_method": "FunsdParser.parse",
                    "extraction_timestamp": None,
                    "is_complete": True,
                    "encoding": "utf-8",
                }

        return labels


__all__ = ["FunsdParser"]
