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

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "mathverse"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "mathverse_metadata.json"
__l4_integrate__ = "scripts/integrate_mathverse_enrichments.py"


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
            dataset_path (Path): Root path of the dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with raw_labels containing split and basic metadata
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
