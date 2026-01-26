# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for RVL-CDIP document classification dataset.

RVL-CDIP (Ryerson Vision Lab Complex Document Information Processing) provides
16-class document classification labels encoded in filenames.

Dataset Structure:
    rvl_cdip/
        images/
            rvl_{class}_{number}.jpg

16 Document Classes:
    - advertisement, budget, email, file_folder
    - form, handwritten, invoice, letter
    - memo, news_article, presentation, questionnaire
    - resume, scientific_publication, scientific_report, specification

Filename Format:
    rvl_{class}_{number}.jpg
    Example: rvl_advertisement_0000.jpg

Example:
    >>> parser = RvlCdipParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/rvl_cdip"),
    ...     image_path=Path("/data/rvl_cdip/images/rvl_advertisement_0000.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["document_class"])
    "advertisement"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class RvlCdipParser(BaseParser):
    """Parser for RVL-CDIP document classification dataset.

    Extracts document class from filename pattern (rvl_{class}_{number}.jpg).
    Maps class names to numeric IDs and sets document_type field for
    downstream compatibility.
    """

    # RVL-CDIP class definitions (16 classes)
    RVL_CLASSES = {
        "advertisement": 0,
        "budget": 1,
        "email": 2,
        "file_folder": 3,
        "form": 4,
        "handwritten": 5,
        "invoice": 6,
        "letter": 7,
        "memo": 8,
        "news_article": 9,
        "presentation": 10,
        "questionnaire": 11,
        "resume": 12,
        "scientific_publication": 13,
        "scientific_report": 14,
        "specification": 15,
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["rvl_cdip"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse RVL-CDIP labels from filename.

        Args:
            dataset_path: Root path of the RVL-CDIP dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with document_class, document_class_id, and
            document_type populated in raw_labels
        """
        labels = OriginalLabels()

        # Parse class from filename: rvl_{class}_{number}.jpg
        filename = image_path.stem  # e.g., "rvl_advertisement_0000"

        if labels.raw_labels is None:
            labels.raw_labels = {}

        if filename.startswith("rvl_"):
            # Remove 'rvl_' prefix and split by underscore
            # Split from right to handle multi-word classes like "scientific_publication"
            parts = filename[4:].rsplit("_", 1)
            if len(parts) == 2:
                class_name = parts[
                    0
                ]  # e.g., "advertisement" or "scientific_publication"
                image_number = parts[1]  # e.g., "0000"

                if class_name in self.RVL_CLASSES:
                    labels.raw_labels["document_class"] = class_name
                    labels.raw_labels["document_class_id"] = self.RVL_CLASSES[
                        class_name
                    ]
                    labels.raw_labels["image_number"] = image_number

                    # Map to document type for downstream compatibility
                    # Convert snake_case to Title Case
                    labels.raw_labels["document_type"] = class_name.replace(
                        "_", " "
                    ).title()

        return labels


__all__ = ["RvlCdipParser"]
