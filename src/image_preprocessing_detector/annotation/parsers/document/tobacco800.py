# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Tobacco800 degraded document dataset.

Tobacco800 contains degraded scanned document images from the tobacco industry
litigation document collection. These documents exhibit various degradation
patterns typical of real-world scanned documents.

Dataset Structure:
    tobacco800/
        images/
            *.png

Characteristics:
    - Degraded scanned documents
    - Administrative/legal domain
    - Scanner ADF capture method
    - Various quality degradations (blur, skew, noise, artifacts)

Note: Labels are typically extracted from directory structure or filename patterns.

Example:
    >>> parser = Tobacco800Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/tobacco800"),
    ...     image_path=Path("/data/tobacco800/images/doc_001.png"),
    ...     config={},
    ... )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class Tobacco800Parser(BaseParser):
    """Parser for Tobacco800 degraded scanned document dataset.

    Extracts basic metadata from file structure. Document class information
    may be available in some dataset variants through filename patterns.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["tobacco800"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Tobacco800 labels from directory structure.

        Args:
            dataset_path: Root path of the Tobacco800 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with basic metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Store source and domain information
        labels.raw_labels["source"] = "tobacco800"
        labels.raw_labels["domain"] = "administrative"
        labels.raw_labels["capture_method"] = "scanner_adf"
        labels.raw_labels["is_degraded"] = True

        # Try to extract document class from filename if present
        # Some variants use patterns like: {class}_{id}.png
        filename = image_path.stem
        if "_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2:
                # First part might be document class
                potential_class = parts[0]
                labels.raw_labels["potential_class"] = potential_class

        return labels


__all__ = ["Tobacco800Parser"]
