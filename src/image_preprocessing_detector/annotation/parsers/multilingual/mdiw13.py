# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for MDIW-13 multi-script dataset.

MDIW-13 (Multi-lingual Database for Script Identification) contains
13 scripts used in India and neighboring regions. Images are segmented
at document, line, and word levels.

Dataset Structure:
    mdiw13/
        {script_name}/
            Document/
                *.png
            Line/
                *.png
            Word/
                *.png

13 Scripts:
    Arabic, Bengali, Gujarati, Gurmukhi, Devanagari, Japanese,
    Kannada, Malayalam, Oriya, Roman (Latin), Tamil, Telugu, Thai

Extracts:
    - script_name: Script class from directory
    - language_code: ISO 639 code derived from script
    - raw_labels: iso15924_script, segmentation_level (Document/Line/Word)

Example:
    >>> parser = Mdiw13Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/mdiw13"),
    ...     image_path=Path("/data/mdiw13/Devanagari/Line/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.script_name)
    Devanagari
    >>> print(labels.language_code)
    hi
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Mdiw13Parser(BaseParser):
    """Parser for MDIW-13 multi-script dataset.

    Extracts script classification and segmentation level from
    directory structure.
    """

    # Script name to ISO 15924 and ISO 639 mappings
    SCRIPT_MAPPINGS = {
        "Arabic": ("Arab", "ar"),
        "Bengali": ("Beng", "bn"),
        "Gujarati": ("Gujr", "gu"),
        "Gurmukhi": ("Guru", "pa"),
        "Devanagari": ("Deva", "hi"),
        "Japanese": ("Jpan", "ja"),
        "Kannada": ("Knda", "kn"),
        "Malayalam": ("Mlym", "ml"),
        "Oriya": ("Orya", "or"),
        "Roman": ("Latn", "en"),
        "Tamil": ("Taml", "ta"),
        "Telugu": ("Telu", "te"),
        "Thai": ("Thai", "th"),
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["mdiw13"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MDIW-13 labels from directory structure.

        Args:
            dataset_path: Root path of the MDIW-13 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with script_name, language_code, and segmentation
            level populated
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Parse script from directory structure
        path_parts = image_path.parts

        for part in path_parts:
            if part in self.SCRIPT_MAPPINGS:
                iso15924, iso639 = self.SCRIPT_MAPPINGS[part]
                labels.script_name = part
                labels.raw_labels["iso15924_script"] = iso15924
                labels.language_code = iso639
                break

        # Determine segmentation level
        for part in path_parts:
            if part in ("Document", "Line", "Word"):
                labels.raw_labels["segmentation_level"] = part.lower()
                break

        return labels


__all__ = ["Mdiw13Parser"]
