# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for AnyPhotoDoc6300 dewarping benchmark dataset.

AnyPhotoDoc6300 provides paired distorted/rectified document images for
dewarping evaluation. The dataset contains multiple distortion variants
(init_1 through init_7) plus ground truth flat images.

Dataset Structure:
    anyphotodoc6300/
        init_1/           # Distortion variant 1
            *.png
        init_2/           # Distortion variant 2
            *.png
        ...
        init_7/           # Distortion variant 7
            *.png
        flat/             # Ground truth (rectified) images
            *.png

Distortion Variants:
    - init_1 through init_7: Different perspective/warping distortions
    - flat: Rectified ground truth (scan-quality)

Note: Multiple zip files contain the init directories plus flat.zip.

Example:
    >>> parser = Anyphotodoc6300Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/anyphotodoc6300"),
    ...     image_path=Path("/data/anyphotodoc6300/init_3/doc_042.png"),
    ...     config={},
    ... )
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class Anyphotodoc6300Parser(BaseParser):
    """Parser for AnyPhotoDoc6300 dewarping benchmark dataset.

    Extracts distortion variant and pairing information from the
    directory structure. Images under init_X directories are distorted;
    images under flat/ are ground truth rectified versions.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["anyphotodoc6300"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse AnyPhotoDoc6300 labels from directory structure.

        Args:
            dataset_path: Root path of the AnyPhotoDoc6300 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with dewarping metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "anyphotodoc6300"
        labels.raw_labels["capture_method"] = "camera_smartphone"
        labels.raw_labels["correction_task"] = "dewarping"

        # Determine image type from parent directory name
        parent_name = image_path.parent.name.lower()

        if parent_name == "flat":
            labels.raw_labels["image_type"] = "ground_truth"
            labels.raw_labels["is_degraded"] = False
        else:
            labels.raw_labels["image_type"] = "distorted"
            labels.raw_labels["is_degraded"] = True

            # Extract distortion variant number from init_X pattern
            variant_match = re.match(r"init_(\d+)", parent_name)
            if variant_match:
                variant_number = int(variant_match.group(1))
                labels.raw_labels["distortion_variant"] = variant_number
                labels.raw_labels["distortion_variant_name"] = parent_name

        # Store filename for pairing across variants
        labels.raw_labels["base_filename"] = image_path.stem

        # Check for paired ground truth
        flat_path = dataset_path / "flat" / image_path.name
        if flat_path.exists():
            labels.raw_labels["has_ground_truth"] = True
            labels.raw_labels["ground_truth_path"] = str(flat_path)
        else:
            labels.raw_labels["has_ground_truth"] = False

        labels.raw_labels["expected_degradations"] = [
            "perspective_distortion",
            "warping",
        ]

        return labels


__all__ = ["Anyphotodoc6300Parser"]
