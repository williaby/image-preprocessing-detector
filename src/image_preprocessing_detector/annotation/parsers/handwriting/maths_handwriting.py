# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for mathematical handwriting datasets.

This is a stub parser for mathematical handwriting datasets that may
be added in the future. Currently extracts minimal metadata from
directory structure.

Dataset Structure:
    maths_handwriting/
        {split}/
            *.png

Labels:
    - split: train/test/validation (if available)
    - Basic metadata from path structure

Note:
    This is a placeholder parser. Extend with specific parsing logic
    when actual mathematical handwriting datasets are integrated.

Example:
    >>> parser = MathsHandwritingParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/maths_handwriting"),
    ...     image_path=Path("/data/maths_handwriting/train/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["split"])
    'train'
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class MathsHandwritingParser(BaseParser):
    """Parser for mathematical handwriting datasets.

    Stub parser that extracts basic metadata from path structure.
    Extend with specific parsing logic when datasets are integrated.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["maths-handwriting", "maths_handwriting", "math_handwriting"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse basic metadata from directory structure.

        Args:
            dataset_path: Root path of the dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels containing split and basic metadata
        """
        labels = OriginalLabels()

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Extract split from path if available
        path_parts = image_path.parts
        for part in path_parts:
            if part in ("train", "test", "validation", "val"):
                labels.raw_labels["split"] = part
                break

        # Mark as mathematical content
        labels.raw_labels["content_type"] = "mathematical"

        return labels


__all__ = ["MathsHandwritingParser"]
