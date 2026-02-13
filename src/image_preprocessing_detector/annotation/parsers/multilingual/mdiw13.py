# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for MDIW-13 multi-script dataset.

MDIW-13 (Multi-lingual Database for Script Identification) contains
13 scripts used in India and neighboring regions. Images are segmented
at document, line, and word levels.

Dataset Structure:
    mdiw13/
        SIW_MultiscriptDatabase/
            {script_name}/
                Document/
                    *.png
                Line/
                    *.png
                Word/
                    *.png
        ICDAR_SIW_Competition/
            TestCompetition_WITHOUTGroundTruth/
                sample000001.png  (uses TestCompetitionGroundtruth.txt)
            TrainCompetition_WITHGroundTruth/
                {script_name}/
                    *.png

13 Scripts:
    Arabic, Bengali, Gujarati, Gurmukhi, Devanagari, Japanese,
    Kannada, Malayalam, Oriya, Roman (Latin), Tamil, Telugu, Thai

Extracts:
    - script_name: Script class from directory or ground truth file
    - language_code: ISO 639 code derived from script
    - raw_labels: iso15924_script, segmentation_level (Document/Line/Word),
                  data_source (competition_test/competition_train/main)

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
import re
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Mdiw13Parser(BaseParser):
    """Parser for MDIW-13 multi-script dataset.

    Extracts script classification and segmentation level from directory
    structure or ground truth file (for test competition samples).

    Supports three data sources:
    - main: SIW_MultiscriptDatabase with script directories
    - competition_train: TrainCompetition_WITHGroundTruth with script directories
    - competition_test: TestCompetition_WITHOUTGroundTruth using ground truth file
    """

    # Script name to ISO 15924 and ISO 639 mappings
    SCRIPT_MAPPINGS: ClassVar[dict[str, tuple[str, str]]] = {
        "Arabic": ("Arab", "ar"),
        "Bengali": ("Beng", "bn"),
        "Bangla": ("Beng", "bn"),  # Alternate name
        "Gujarati": ("Gujr", "gu"),
        "Gurmukhi": ("Guru", "pa"),
        "Devanagari": ("Deva", "hi"),
        "Hindi": ("Deva", "hi"),  # Ground truth uses "Hindi"
        "Japanese": ("Jpan", "ja"),
        "Kannada": ("Knda", "kn"),
        "Malayalam": ("Mlym", "ml"),
        "Oriya": ("Orya", "or"),
        "Roman": ("Latn", "en"),
        "Tamil": ("Taml", "ta"),
        "Telugu": ("Telu", "te"),
        "Thai": ("Thai", "th"),
    }

    # Numeric label to script name mapping (from TestCompetitionGroundtruth.txt)
    NUMERIC_TO_SCRIPT: ClassVar[dict[int, str]] = {
        0: "Arabic",
        1: "Bengali",
        2: "Gujarati",
        3: "Gurmukhi",
        4: "Hindi",
        5: "Japanese",
        6: "Kannada",
        7: "Malayalam",
        8: "Oriya",
        9: "Roman",
        10: "Tamil",
        11: "Telugu",
        12: "Thai",
    }

    # Class-level cache for ground truth labels
    _gt_labels: ClassVar[dict[int, int] | None] = None
    _gt_path: ClassVar[Path | None] = None

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["mdiw13"]

    @classmethod
    def _load_ground_truth(cls, dataset_path: Path) -> dict[int, int]:
        """Load ground truth labels from file (cached).

        Args:
            dataset_path: Root path of the MDIW-13 dataset

        Returns:
            Dict mapping sample number to numeric label
        """
        gt_path = (
            dataset_path
            / "SIW_Database"
            / "ICDAR_SIW_Competition"
            / "TestCompetitionGroundtruth.txt"
        )

        # Return cached if already loaded for this path
        if cls._gt_labels is not None and cls._gt_path == gt_path:
            return cls._gt_labels

        if not gt_path.exists():
            logger.warning(f"Ground truth file not found: {gt_path}")
            cls._gt_labels = {}
            cls._gt_path = gt_path
            return cls._gt_labels

        labels: dict[int, int] = {}
        with open(gt_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    try:
                        numeric_label = int(line)
                        if 0 <= numeric_label <= 12:
                            labels[line_num] = numeric_label
                    except ValueError:
                        pass  # Skip non-numeric lines in ground truth file

        cls._gt_labels = labels
        cls._gt_path = gt_path
        logger.info(f"Loaded {len(labels)} ground truth labels from {gt_path}")
        return cls._gt_labels

    @staticmethod
    def _extract_sample_number(filename: str) -> int | None:
        """Extract sample number from filename (e.g., 'sample000001.png' -> 1)."""
        match = re.match(r"sample(\d+)\.\w+", filename)
        if match:
            return int(match.group(1))
        return None

    def _parse_from_ground_truth(
        self, image_path: Path, dataset_path: Path
    ) -> OriginalLabels | None:
        """Try to parse labels from ground truth file for test competition.

        Args:
            image_path: Path to the image
            dataset_path: Root path of the dataset

        Returns:
            OriginalLabels if found in ground truth, None otherwise
        """
        sample_num = self._extract_sample_number(image_path.name)
        if sample_num is None:
            return None

        gt_labels = self._load_ground_truth(dataset_path)
        numeric_label = gt_labels.get(sample_num)
        if numeric_label is None:
            return None

        script_name = self.NUMERIC_TO_SCRIPT.get(numeric_label)
        if script_name is None:
            return None

        iso15924, iso639 = self.SCRIPT_MAPPINGS[script_name]

        labels = OriginalLabels()
        labels.script_name = script_name  # Human-readable name
        labels.iso15924_script_code = iso15924  # ISO 15924
        labels.language_code = iso639
        labels.raw_labels = {
            "data_source": "competition_test",
            "numeric_label": numeric_label,
        }
        return labels

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MDIW-13 labels from directory structure or ground truth.

        Tries multiple strategies in order:
        1. Check for script directory in path (main dataset or competition train)
        2. Check ground truth file for test competition samples

        Args:
            dataset_path: Root path of the MDIW-13 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with script_name, language_code, and metadata
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        path_parts = image_path.parts
        path_str = str(image_path)

        # Determine data source from path
        data_source = "main"
        if "TestCompetition_WITHOUTGroundTruth" in path_str:
            data_source = "competition_test"
        elif "TrainCompetition_WITHGroundTruth" in path_str:
            data_source = "competition_train"

        # Strategy 1: Parse script from directory structure
        for part in path_parts:
            if part in self.SCRIPT_MAPPINGS:
                iso15924, iso639 = self.SCRIPT_MAPPINGS[part]
                labels.script_name = part  # Human-readable name
                labels.iso15924_script_code = iso15924  # ISO 15924
                labels.language_code = iso639
                labels.raw_labels["data_source"] = data_source
                break

        # Strategy 2: Use ground truth for test competition samples
        if not labels.script_name and data_source == "competition_test":
            gt_labels = self._parse_from_ground_truth(image_path, dataset_path)
            if gt_labels:
                return gt_labels

        # Determine segmentation level (for main dataset)
        for part in path_parts:
            if part in ("Document", "Line", "Word"):
                labels.raw_labels["segmentation_level"] = part.lower()
                break

        # Set data source if not already set
        if "data_source" not in labels.raw_labels:
            labels.raw_labels["data_source"] = data_source

        return labels


__all__ = ["Mdiw13Parser"]
