# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DRCCBI document dewarping/correction dataset.

DRCCBI (Document Rectification and Character-level Correction Benchmark Images)
contains distorted and corrected document image pairs for evaluating document
dewarping and rectification algorithms.

Dataset Structure:
    drccbi/
        src/              # Distorted/source document images
            {doc_id}.png
        public/           # Corrected/reference document images
            {doc_id}.png

    Alternative structures:
        drccbi/
            distorted/
                {doc_id}.png
            corrected/
                {doc_id}.png

Filename Patterns:
    - Distorted and corrected images share the same base filename
    - src/ contains input distorted images
    - public/ contains corrected reference images

Example:
    >>> parser = DrccbiParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/drccbi"),
    ...     image_path=Path("/data/drccbi/src/page_042.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["correction_task"])
    "dewarping"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

# Directories that indicate distorted/source images
_DISTORTED_DIRS = {"src", "source", "distorted", "input", "warped"}

# Directories that indicate corrected/reference images
_CORRECTED_DIRS = {"public", "corrected", "target", "gt", "ground_truth", "ref"}


class DrccbiParser(BaseParser):
    """Parser for DRCCBI document dewarping benchmark.

    Extracts image type (distorted vs corrected) and document ID from
    directory structure and filenames. Corrected images serve as
    ground truth for distorted variants.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["drccbi"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DRCCBI labels from directory structure.

        Args:
            dataset_path: Root path of the DRCCBI dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with dewarping metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "drccbi"
        labels.raw_labels["correction_task"] = "dewarping"

        # Determine image type from parent directory
        parent_name = image_path.parent.name.lower()
        filename = image_path.stem

        if parent_name in _DISTORTED_DIRS:
            labels.raw_labels["image_type"] = "distorted"
            labels.raw_labels["capture_method"] = "camera_smartphone"
            labels.raw_labels["is_degraded"] = True
            labels.raw_labels["expected_degradations"] = [
                "perspective_distortion",
                "warping",
            ]

            # Check for paired corrected ground truth
            has_ground_truth = False
            for corrected_dir_name in _CORRECTED_DIRS:
                corrected_path = dataset_path / corrected_dir_name / image_path.name
                if corrected_path.exists():
                    labels.raw_labels["has_ground_truth"] = True
                    labels.raw_labels["ground_truth_path"] = str(corrected_path)
                    has_ground_truth = True
                    break

            if not has_ground_truth:
                labels.raw_labels["has_ground_truth"] = False

        elif parent_name in _CORRECTED_DIRS:
            labels.raw_labels["image_type"] = "ground_truth"
            labels.raw_labels["capture_method"] = "scanner_flatbed"
            labels.raw_labels["is_degraded"] = False
            labels.raw_labels["has_ground_truth"] = False

        else:
            # Unknown directory structure
            labels.raw_labels["image_type"] = "unknown"
            labels.raw_labels["capture_method"] = "unknown"
            labels.raw_labels["is_degraded"] = True

        labels.raw_labels["base_filename"] = filename

        return labels


__all__ = ["DrccbiParser"]
