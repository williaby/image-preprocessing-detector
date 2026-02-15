# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for StainDoc document stain removal dataset.

StainDoc provides paired stained and clean document images for evaluating
stain removal algorithms. Images contain various types of stains
(ink, coffee, water damage, discoloration) on document pages.

Dataset Structure:
    staindoc/
        stained/           # Stained document images
            {doc_id}.png
        clean/             # Clean ground truth images
            {doc_id}.png
        ground_truth/      # Alternative GT directory name
            {doc_id}.png

Filename Patterns:
    - Stained and clean images share the same base filename
    - Ground truth may be in clean/ or ground_truth/ directory

Example:
    >>> parser = StaindocParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/staindoc"),
    ...     image_path=Path("/data/staindoc/stained/doc_042.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["correction_task"])
    "stain_removal"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

# Directories that indicate stained/degraded images
_STAINED_DIRS = {"stained", "stain", "degraded", "input", "src"}

# Directories that indicate clean/ground truth images
_CLEAN_DIRS = {"clean", "ground_truth", "gt", "target", "ref", "reference"}


class StaindocParser(BaseParser):
    """Parser for StainDoc stain removal benchmark.

    Extracts image type (stained vs clean) and document ID from
    directory structure and filenames. Clean images serve as
    ground truth for stained variants.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["staindoc"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse StainDoc labels from directory structure.

        Args:
            dataset_path: Root path of the StainDoc dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with stain removal metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "staindoc"
        labels.raw_labels["correction_task"] = "stain_removal"

        # Determine image type from parent directory
        parent_name = image_path.parent.name.lower()
        filename = image_path.stem

        if parent_name in _STAINED_DIRS:
            labels.raw_labels["image_type"] = "stained"
            labels.raw_labels["capture_method"] = "scanner_flatbed"
            labels.raw_labels["is_degraded"] = True
            labels.raw_labels["expected_degradations"] = [
                "stain",
                "discoloration",
            ]

            # Check for paired ground truth in clean directories
            has_ground_truth = False
            for clean_dir_name in _CLEAN_DIRS:
                clean_path = dataset_path / clean_dir_name / image_path.name
                if clean_path.exists():
                    labels.raw_labels["has_ground_truth"] = True
                    labels.raw_labels["ground_truth_path"] = str(clean_path)
                    has_ground_truth = True
                    break

            if not has_ground_truth:
                labels.raw_labels["has_ground_truth"] = False

        elif parent_name in _CLEAN_DIRS:
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


__all__ = ["StaindocParser"]
