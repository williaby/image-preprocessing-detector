# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DIBCO (Document Image Binarization Contest) dataset.

DIBCO provides binary ground truth images for document binarization evaluation.
The dataset is organized by competition year (2009-2017) and document type
(handwritten or printed). This parser extracts metadata from directory structure
rather than quality scores.

Dataset Structure:
    DIBCO/
        {year}/
            DIBCO{year}_Test_images-handwritten/
            DIBCO{year}_Test_images-printed/
            DIBCO{year}-GT-Test-images_handwritten/  (ground truth)
            DIBCO{year}-GT-Test-images_printed/      (ground truth)

Labels Extracted:
    - Competition year (2009-2017)
    - Document type (handwritten or printed)
    - Has paired GT (binary binarization ground truth)
    - Ground truth path (if available)

Note:
    DIBCO provides binary ground truth images for document binarization
    evaluation, not quality scores. The GT images are pixel-aligned masks
    used for binarization algorithm evaluation.

Example:
    >>> parser = DibcoParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/dibco"),
    ...     image_path=Path(
    ...         "/data/dibco/2013/DIBCO2013_Test_images-handwritten/H01.png"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["dibco_year"])
    2013
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class DibcoParser(BaseParser):
    """Parser for DIBCO (Document Image Binarization Contest) dataset.

    Extracts year, document type (handwritten/printed), and ground truth
    availability from directory structure. Does not provide quality scores
    as DIBCO is a binarization benchmark dataset.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["dibco"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DIBCO metadata from directory structure.

        Args:
            dataset_path: Root path of the DIBCO dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels containing dibco_year, document_type,
            has_handwriting, is_ground_truth, has_ground_truth, and ground_truth_path

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Extract year and document type from path structure
        path_parts = image_path.parts

        for part in path_parts:
            # Match year folders: "2009", "2010", etc.
            if re.match(r"^20\d{2}$", part):
                year = part
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["dibco_year"] = int(year)

            # Match folder names to determine document type
            lower_part = part.lower()
            if "handwritten" in lower_part or "handwriting" in lower_part:
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["document_type"] = "handwritten"
                # This is a handwriting dataset
                labels.raw_labels["has_handwriting"] = True
            elif "printed" in lower_part:
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["document_type"] = "printed"
                labels.raw_labels["has_handwriting"] = False

            # Check if this is a ground truth image
            if "gt" in lower_part or "ground" in lower_part:
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["is_ground_truth"] = True

        # Look for corresponding GT image
        # GT images are typically in parallel folder structure
        # DIBCO naming is inconsistent:
        #   Test: DIBCO{year}_Test_images-handwritten
        #   GT:   DIBCO{year}-GT-Test-images_handwritten
        str_path = str(image_path)
        if "Test_images" in str_path and "-GT-" not in str_path:
            # This is a test image, look for GT
            # First, replace _Test_images with -GT-Test-images
            gt_path_str = str_path.replace("_Test_images", "-GT-Test-images")
            # Then handle the handwritten/printed suffix difference
            # Test uses hyphen (e.g., -handwritten), GT uses underscore (e.g., _handwritten)
            gt_path_str = gt_path_str.replace(
                "-GT-Test-images-handwritten", "-GT-Test-images_handwritten"
            )
            gt_path_str = gt_path_str.replace(
                "-GT-Test-images-printed", "-GT-Test-images_printed"
            )
            gt_path = Path(gt_path_str)
            if gt_path.exists():
                if labels.raw_labels is None:
                    labels.raw_labels = {}
                labels.raw_labels["has_ground_truth"] = True
                labels.raw_labels["ground_truth_path"] = str(gt_path)

        return labels


__all__ = ["DibcoParser"]
