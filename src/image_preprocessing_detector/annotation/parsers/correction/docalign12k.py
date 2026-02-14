# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DocAlign12K document alignment/dewarping dataset.

DocAlign12K provides paired synthetically distorted and flat (rectified)
document images for training document alignment and dewarping models.

Dataset Structure:
    docalign12k/
        distorted_hard/       # Distorted document images (input)
            1/
                000101_00028.jpg
                ...
            2/
            ...
            14/
        flat/                 # Rectified ground truth
            1/
                000101_00028.jpg  (same filename = paired GT)
            ...
            14/
        shadows/              # Shadow overlay images (543)
            *.jpg
        forwardmap_hard/      # Forward displacement maps (NPY, skipped)
            ...

Pairing:
    distorted_hard/{N}/{filename} <-> flat/{N}/{filename}
    Same filename in matching numbered subdirectory = paired ground truth.

Example:
    >>> parser = Docalign12KParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/docalign12k"),
    ...     image_path=Path("/data/docalign12k/distorted_hard/1/000101_00028.jpg"),
    ...     config={},
    ... )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class Docalign12KParser(BaseParser):
    """Parser for DocAlign12K document alignment dataset.

    Extracts distortion group, image type (distorted/flat/shadow), and
    pairing information from the directory structure.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["docalign12k"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DocAlign12K labels from directory structure.

        Args:
            dataset_path: Root path of the DocAlign12K dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with alignment metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "docalign12k"
        labels.raw_labels["capture_method"] = "synthetic"
        labels.raw_labels["correction_task"] = "alignment"

        # Navigate up from file to determine directory structure
        # Expected: docalign12k/{category}/{group_num}/{filename}
        try:
            relative = image_path.relative_to(dataset_path)
            parts = relative.parts
        except ValueError:
            parts = ()

        # Extract category and group from directory hierarchy
        category = None
        group_num = None

        if len(parts) >= 3:
            category = parts[0].lower()
            group_num = parts[1]
        elif len(parts) >= 2:
            category = parts[0].lower()

        # Determine image type from top-level directory
        if category == "distorted_hard":
            labels.raw_labels["image_type"] = "input_distorted"
            labels.raw_labels["is_degraded"] = True
            labels.raw_labels["distortion_type"] = "hard"

            # Check for paired flat ground truth
            if group_num is not None:
                gt_path = dataset_path / "flat" / group_num / image_path.name
                if gt_path.exists():
                    labels.raw_labels["has_ground_truth"] = True
                    labels.raw_labels["ground_truth_path"] = str(gt_path)
                else:
                    labels.raw_labels["has_ground_truth"] = False
            else:
                labels.raw_labels["has_ground_truth"] = False

        elif category == "flat":
            labels.raw_labels["image_type"] = "ground_truth"
            labels.raw_labels["is_degraded"] = False
            labels.raw_labels["has_ground_truth"] = False

        elif category == "shadows":
            labels.raw_labels["image_type"] = "shadow_overlay"
            labels.raw_labels["is_degraded"] = False
            labels.raw_labels["has_ground_truth"] = False

        else:
            labels.raw_labels["image_type"] = "unknown"
            labels.raw_labels["is_degraded"] = True

        if group_num is not None:
            labels.raw_labels["distortion_group"] = group_num

        labels.raw_labels["base_filename"] = image_path.stem

        labels.raw_labels["expected_degradations"] = [
            "perspective_distortion",
            "misalignment",
            "warping",
        ]

        return labels


__all__ = ["Docalign12KParser"]
