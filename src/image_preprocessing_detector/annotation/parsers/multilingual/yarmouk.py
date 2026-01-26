# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Yarmouk OCR dataset.

Yarmouk OCR is an Arabic OCR dataset with training, testing,
and sample sets. Contains scanned Arabic document images.

Dataset Structure:
    yarmouk_ocr/
        Training/
            *.jpg
        Testing/
            *.jpg
        Samples/
            *.jpg

Extracts:
    - language_code: Fixed "ar" (Arabic)
    - script_name: Fixed "Arabic"
    - raw_labels: split, iso15924_script

Example:
    >>> parser = YarmoukParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/yarmouk_ocr"),
    ...     image_path=Path("/data/yarmouk_ocr/Training/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    ar
    >>> print(labels.raw_labels["split"])
    train
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class YarmoukParser(BaseParser):
    """Parser for Yarmouk OCR dataset.

    Extracts split information from directory structure.
    Fixed Arabic language/script.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["yarmouk_ocr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Yarmouk OCR labels from directory structure.

        Args:
            dataset_path: Root path of the yarmouk_ocr dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code="ar", script_name="Arabic",
            and split information (Training/Testing/Samples)
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Arabic script (ISO 15924: Arab, ISO 639: ar)
        labels.language_code = "ar"
        labels.script_name = "Arabic"
        labels.raw_labels["iso15924_script"] = "Arab"

        # Extract split from parent directory
        path_parts = image_path.parts
        for part in path_parts:
            if part == "Training":
                labels.raw_labels["split"] = "train"
                break
            elif part == "Testing":
                labels.raw_labels["split"] = "test"
                break
            elif part == "Samples":
                labels.raw_labels["split"] = "sample"
                break

        return labels


__all__ = ["YarmoukParser"]
