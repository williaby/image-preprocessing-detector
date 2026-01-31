# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for PUCIT-OHUL Urdu handwriting dataset.

PUCIT-OHUL (Punjab University Center for IT - Offline Handwritten Urdu Lines)
is an Urdu line-level handwriting dataset with ground truth transcriptions
stored in Excel files.

Dataset Structure:
    Pucit/
        train_labels_v2.xlsx    - Training labels with transcriptions
        test_labels_v2.xlsx     - Testing labels with transcriptions
        train_lines/            - Training line images
            *.png
        test_lines/             - Testing line images
            *.png

Excel Format:
    Columns: [image_name, transcription, writer_id (optional)]

Language:
    - Language: Urdu (ISO 639: ur)
    - Script: Arabic (Urdu uses Arabic script with additional letters)

Note:
    Excel parsing requires openpyxl. Falls back to path-based inference
    if Excel reading fails.

Example:
    >>> parser = PucitOhulParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/Pucit"),
    ...     image_path=Path("/data/Pucit/train_lines/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ur'
    >>> print(labels.script_name)
    'Arabic'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class PucitOhulParser(BaseParser):
    """Parser for PUCIT-OHUL Urdu handwriting dataset.

    Extracts Urdu line transcriptions from Excel files and metadata
    from directory structure:
    - Language/script identification (Urdu/Arabic)
    - Split (train/test)
    - Transcription text
    - Writer ID (if available)
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["pucit-ohul", "pucit_ohul", "pucit"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse PUCIT-OHUL labels from Excel files.

        Args:
            dataset_path: Root path of the PUCIT-OHUL dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, transcription,
            writer_id, and raw_labels containing split
        """
        labels = OriginalLabels()

        # Set language/script based on dataset (known from dataset metadata)
        labels.language_code = "ur"  # Urdu
        labels.script_name = "Arabic"  # Human-readable name
        labels.iso15924_script_code = "Arab"  # ISO 15924 (Urdu uses Arabic script)

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Determine split from path
        path_str = str(image_path)
        split = None
        if "train_lines" in path_str or "/train/" in path_str:
            split = "train"
        elif "test_lines" in path_str or "/test/" in path_str:
            split = "test"

        if split:
            labels.raw_labels["split"] = split

        # Try to find and parse Excel labels
        # Look for Pucit subdirectory
        pucit_path = None
        for parent in image_path.parents:
            if (parent / "train_labels_v2.xlsx").exists():
                pucit_path = parent
                break
            if (parent / "Pucit" / "train_labels_v2.xlsx").exists():
                pucit_path = parent / "Pucit"
                break

        if pucit_path:
            excel_file = pucit_path / f"{split}_labels_v2.xlsx" if split else None
            if excel_file and excel_file.exists():
                try:
                    import openpyxl

                    wb = openpyxl.load_workbook(excel_file, read_only=True)
                    ws = wb.active

                    # Find row matching image filename
                    image_name = image_path.stem
                    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
                        if row and len(row) >= 2:
                            # Format: [image_name, transcription, ...]
                            if (
                                str(row[0]) == image_name
                                or str(row[0]) == image_path.name
                            ):
                                if row[1]:
                                    labels.transcription = str(row[1])
                                if len(row) >= 3 and row[2]:
                                    labels.writer_id = str(row[2])
                                break
                    wb.close()
                except ImportError:
                    logger.debug("openpyxl not available for PUCIT-OHUL label parsing")
                except Exception as e:
                    logger.debug(
                        f"Failed to parse PUCIT-OHUL labels from {excel_file}: {e}"
                    )

        return labels


__all__ = ["PucitOhulParser"]
