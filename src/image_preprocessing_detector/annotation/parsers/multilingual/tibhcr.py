# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for TibHCR Tibetan handwriting dataset.

TibHCR (Tibetan Handwritten Character Recognition) contains
Tibetan handwritten characters from 235 writers, organized by
character class and split (train/test).

Dataset Structure:
    TibHCR/
        train/
            {character_class}/
                *.png
        test/
            {character_class}/
                *.png

Contains 47 character classes.

Extracts:
    - script_name: Fixed "Tibetan"
    - language_code: Fixed "bo" (Tibetan)
    - transcription: Character class (ground truth)
    - raw_labels: split, character_class, iso15924_script

Example:
    >>> parser = TibhcrParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/tibhcr"),
    ...     image_path=Path("/data/tibhcr/train/ka/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.script_name)
    Tibetan
    >>> print(labels.transcription)
    ka
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class TibhcrParser(BaseParser):
    """Parser for TibHCR Tibetan handwriting dataset.

    Extracts character class and split information from directory
    structure. Fixed Tibetan script/language.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["tibhcr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse TibHCR labels from directory structure.

        Args:
            dataset_path: Root path of the TibHCR dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with script_name="Tibetan", language_code="bo",
            and character class as transcription
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Tibetan script (ISO 15924: Tibt, ISO 639: bo)
        labels.script_name = "Tibetan"
        labels.language_code = "bo"
        labels.raw_labels["iso15924_script"] = "Tibt"

        path_parts = image_path.parts

        # Determine split
        for part in path_parts:
            if part in ("train", "test", "val", "validation"):
                labels.raw_labels["split"] = part
                break

        # Character class is typically the parent directory name
        parent_dir = image_path.parent.name
        if parent_dir not in ("train", "test", "val", "validation", "images"):
            labels.raw_labels["character_class"] = parent_dir
            labels.transcription = parent_dir

        return labels


__all__ = ["TibhcrParser"]
