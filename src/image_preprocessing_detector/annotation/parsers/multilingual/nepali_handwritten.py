# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Nepali Handwritten dataset.

Nepali Handwritten contains handwritten Nepali text images
in Devanagari script, split into training and test sets.

Dataset Structure:
    nepali_handwritten/
        train/
            *.jpg
        test/
            *.jpg

Extracts:
    - language_code: Fixed "ne" (Nepali)
    - script_name: Fixed "Devanagari"
    - raw_labels: split, iso15924_script

Example:
    >>> parser = NepaliHandwrittenParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/nepali_handwritten"),
    ...     image_path=Path("/data/nepali_handwritten/train/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    ne
    >>> print(labels.script_name)
    Devanagari
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class NepaliHandwrittenParser(BaseParser):
    """Parser for Nepali Handwritten dataset.

    Extracts split information from directory structure.
    Fixed Nepali language/Devanagari script.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nepali_handwritten"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Nepali Handwritten labels from directory structure.

        Args:
            dataset_path: Root path of the nepali_handwritten dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code="ne", script_name="Devanagari",
            and split information
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Devanagari script (ISO 15924: Deva, ISO 639: ne)
        labels.language_code = "ne"
        labels.script_name = "Devanagari"
        labels.iso15924_script_code = "Deva"

        # Extract split from parent directory
        parent = image_path.parent.name
        if parent in ("train", "test", "val"):
            labels.raw_labels["split"] = parent

        return labels


__all__ = ["NepaliHandwrittenParser"]
