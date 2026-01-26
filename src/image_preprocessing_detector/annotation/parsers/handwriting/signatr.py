# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for SignaTR6K signature dataset.

SignaTR6K provides signature images with binary segmentation masks for
signature extraction tasks. The dataset contains cropped signature images
and paired label masks in train/test/validation splits.

Dataset Structure:
    SignaTR6K/
        train/
            crop/           - Cropped signature images
                {id}.png
            label/          - Binary mask labels
                {id}.png
        test/
            crop/
            label/
        validation/
            crop/
            label/

Label Format:
    - Split: train/test/validation
    - Image ID: numeric identifier from filename
    - Has paired mask: whether label image exists
    - Image type: signature (crop) or mask (label)

Note:
    SignaTR6K provides signature images with binary segmentation masks
    for signature localization. There are no writer IDs or genuine/forgery
    labels in this dataset structure.

Example:
    >>> parser = SignaTRParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/SignaTR6K"),
    ...     image_path=Path("/data/SignaTR6K/train/crop/12345.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["split"])
    'train'
    >>> print(labels.raw_labels["signature_id"])
    12345
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class SignaTRParser(BaseParser):
    """Parser for SignaTR6K signature dataset.

    Extracts signature metadata from directory structure and filename:
    - Split (train/test/validation)
    - Image type (signature/mask)
    - Signature ID
    - Paired mask availability
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["signatr6k", "signatr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SignaTR6K labels from directory structure.

        Args:
            dataset_path: Root path of the SignaTR6K dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels containing split, image_type,
            signature_id, has_mask, and optional mask_path
        """
        labels = OriginalLabels()

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Extract split and image info from path structure
        path_parts = image_path.parts

        for i, part in enumerate(path_parts):
            # Identify split
            if part in ("train", "test", "validation"):
                labels.raw_labels["split"] = part

            # Identify if this is crop or label
            if part == "crop":
                labels.raw_labels["image_type"] = "signature"
                # Check for corresponding mask
                label_path = image_path.parent.parent / "label" / image_path.name
                if label_path.exists():
                    labels.raw_labels["has_mask"] = True
                    labels.raw_labels["mask_path"] = str(label_path)
                else:
                    labels.raw_labels["has_mask"] = False
            elif part == "label":
                labels.raw_labels["image_type"] = "mask"

        # Extract numeric ID from filename
        try:
            image_id = int(image_path.stem)
            labels.raw_labels["signature_id"] = image_id
        except ValueError:
            # If not numeric, store as string
            labels.raw_labels["signature_id"] = image_path.stem

        return labels


__all__ = ["SignaTRParser"]
