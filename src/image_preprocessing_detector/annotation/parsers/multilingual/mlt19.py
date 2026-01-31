# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for ICDAR 2019 MLT (Multi-Lingual Text) dataset.

MLT19 is a multi-lingual scene text dataset covering 10 languages:
Arabic, Bangla, Chinese, Japanese, Korean, Latin (English, French, German),
Hindi, and mixed scripts.

Dataset Structure:
    mlt19/
        TrainImages/
            tr_img_00001.jpg
            tr_img_00002.jpg
            ...
        TrainGT/
            TrainGT/
                tr_img_00001.txt
                tr_img_00002.txt
                ...
        TestImages/
            ts_img_00001.jpg
            ...

Ground Truth Format (per line):
    x1,y1,x2,y2,x3,y3,x4,y4,language,transcription

    Where:
    - x1-y4: Quadrilateral bounding box coordinates (4 corners)
    - language: Script/language identifier (Arabic, Bangla, Chinese, etc.)
    - transcription: Ground truth text (### for illegible)

Labels:
    - language_code: Primary language from annotations
    - script_name: Primary script detected
    - raw_labels: word_count, languages_found, has_mixed_scripts, sample_texts

Example:
    >>> parser = Mlt19Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/mlt19"),
    ...     image_path=Path("/data/mlt19/TrainImages/tr_img_00001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["languages_found"])
    ['Arabic', 'Latin']
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Map MLT19 language labels to ISO 639-1 codes
LANGUAGE_TO_ISO = {
    "Arabic": "ar",
    "Bangla": "bn",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Latin": "en",  # Default Latin to English
    "Hindi": "hi",
    "Devanagari": "hi",  # Hindi uses Devanagari script
}

# Map MLT19 language labels to ISO 15924 script codes
LANGUAGE_TO_SCRIPT = {
    "Arabic": "Arab",
    "Bangla": "Beng",
    "Chinese": "Hans",
    "Japanese": "Jpan",
    "Korean": "Kore",
    "Latin": "Latn",
    "Hindi": "Deva",
    "Devanagari": "Deva",
}


class Mlt19Parser(BaseParser):
    """Parser for ICDAR 2019 MLT multi-lingual scene text dataset.

    Extracts text annotations including language labels and transcriptions
    from ground truth .txt files with quadrilateral bounding boxes.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["mlt19", "mlt-2019", "icdar2019-mlt"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MLT19 labels from ground truth files.

        Args:
            dataset_path: Root path of the MLT19 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, and raw_labels
            containing word annotations and language statistics
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Find corresponding ground truth file
        gt_path = self._find_gt_path(dataset_path, image_path)

        languages_found: list[str] = []
        transcriptions: list[str] = []
        word_count = 0

        if gt_path and gt_path.exists():
            try:
                with open(gt_path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        # Parse CSV format: x1,y1,...,x4,y4,language,transcription
                        parts = line.split(",")
                        if len(parts) >= 10:
                            # First 8 values are coordinates
                            language = parts[8]
                            transcription = ",".join(parts[9:])  # Handle commas in text

                            if language and language not in languages_found:
                                languages_found.append(language)

                            # Count words (skip illegible markers)
                            if transcription and transcription != "###":
                                transcriptions.append(transcription)
                                word_count += 1

            except Exception as e:
                logger.debug(f"Failed to parse MLT19 ground truth at {gt_path}: {e}")

        # Determine primary language
        if languages_found:
            primary_lang = languages_found[0]
            labels.language_code = LANGUAGE_TO_ISO.get(primary_lang, "und")
            labels.script_name = primary_lang  # Store original name (e.g., "Arabic")
            labels.iso15924_script_code = LANGUAGE_TO_SCRIPT.get(
                primary_lang
            )  # ISO 15924
        else:
            labels.language_code = "und"  # Undetermined
            labels.iso15924_script_code = "Zzzz"  # Unknown script

        # Store raw labels
        labels.raw_labels["word_count"] = word_count
        labels.raw_labels["languages_found"] = languages_found
        labels.raw_labels["has_mixed_scripts"] = len(languages_found) > 1
        labels.raw_labels["content_type"] = "scene_text"

        # Store sample transcriptions (first 5)
        if transcriptions:
            labels.raw_labels["sample_texts"] = transcriptions[:5]

        return labels

    def _find_gt_path(self, dataset_path: Path, image_path: Path) -> Path | None:
        """Find the ground truth file for an image.

        Args:
            dataset_path: Root dataset path
            image_path: Path to the image file

        Returns:
            Path to ground truth file or None if not found
        """
        stem = image_path.stem

        # For train images: tr_img_XXXXX.jpg -> TrainGT/TrainGT/tr_img_XXXXX.txt
        if stem.startswith("tr_img"):
            gt_path = dataset_path / "TrainGT" / "TrainGT" / f"{stem}.txt"
            if gt_path.exists():
                return gt_path

        # Try relative to image path
        gt_path = image_path.with_suffix(".txt")
        if gt_path.exists():
            return gt_path

        # Try in parent's GT directory
        gt_path = image_path.parent.parent / "TrainGT" / "TrainGT" / f"{stem}.txt"
        if gt_path.exists():
            return gt_path

        return None


__all__ = ["Mlt19Parser"]
