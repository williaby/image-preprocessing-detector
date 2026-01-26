# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DIQA-5000 quality assessment dataset.

DIQA-5000 provides 3-dimension quality scores (overall, sharpness, color_fidelity)
from CSV files organized in train/val/test splits. Each CSV contains restored/original
image pairs with Mean Opinion Score (MOS) values on a 1-5 scale (higher is better).

Dataset Structure:
    DIQA-5000/
        train/
            train.csv
            ori/           (original images)
            res/           (restored images)
        val/
            val.csv
            ori/
            res/
        test/
            test.csv
            ori/
            res/

CSV Format:
    - res: restored/enhanced image filename (what we match against)
    - ori: original image filename (reference)
    - overall: overall quality MOS (1-5 scale, higher is better)
    - sharpness: sharpness quality MOS (1-5 scale)
    - color_fidelity: color fidelity MOS (1-5 scale)

Example:
    >>> parser = DIQAParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/diqa-5000"),
    ...     image_path=Path("/data/diqa-5000/train/ori/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.diqa_overall)
    4.2
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class DIQAParser(BaseParser):
    """Parser for DIQA-5000 quality assessment dataset.

    Extracts 3-dimension MOS scores (overall, sharpness, color_fidelity)
    from CSV files in train/val/test splits. Maintains backward compatibility
    by setting both diqa_overall and diqa_mos to the same value.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["diqa-5000"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DIQA labels from CSV files.

        Args:
            dataset_path: Root path of the DIQA-5000 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with diqa_overall, diqa_sharpness, diqa_color_fidelity,
            diqa_original_image, and diqa_mos (backward compat) populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Determine which split based on image path
        # Images are in train/ori/, val/ori/, test/ori/ subdirectories
        image_name = image_path.name
        split = None
        for s in ["train", "val", "test"]:
            if f"/{s}/" in str(image_path):
                split = s
                break

        # Try to find and parse the appropriate CSV file
        csv_files = ["train/train.csv", "val/val.csv", "test/test.csv"]
        if split:
            # Prioritize the matching split
            csv_files = [f"{split}/{split}.csv"] + [
                f for f in csv_files if split not in f
            ]

        for csv_file in csv_files:
            csv_path = dataset_path / csv_file
            if csv_path.exists():
                try:
                    with open(csv_path, newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Match by 'res' (restored image) filename
                            # DIQA-5000 uses res/ori pairs
                            if row.get("res") == image_name:
                                # 3-dimension quality scores
                                if "overall" in row:
                                    labels.diqa_overall = float(row["overall"])
                                    labels.diqa_mos = float(
                                        row["overall"]
                                    )  # Backward compat
                                if "sharpness" in row:
                                    labels.diqa_sharpness = float(row["sharpness"])
                                if "color_fidelity" in row:
                                    labels.diqa_color_fidelity = float(
                                        row["color_fidelity"]
                                    )
                                if "ori" in row:
                                    labels.diqa_original_image = row["ori"]
                                return labels  # Found match, return early
                except Exception as e:
                    logger.debug(f"Failed to parse DIQA labels from {csv_path}: {e}")

        return labels


__all__ = ["DIQAParser"]
