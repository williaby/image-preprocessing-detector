"""Parser for POPP-line (French Census Handwriting) dataset.

POPP-line contains 4,794 line-level handwritten text images from French
census records with text transcriptions. From the Teklia/POPP project
for historical demography.

Dataset Structure (after extraction from HuggingFace Arrow):
    popp-datasets/
        extracted_images/
            train/
                00000.png - 03834.png  (3,835 line images)
            validation/
                00000.png - 00479.png  (480 line images)
            test/
                00000.png - 00478.png  (479 line images)
        hf_cache/
            train/data-00000-of-00001.arrow
            validation/data-00000-of-00001.arrow
            test/data-00000-of-00001.arrow

Labels Extracted:
    - language_code: "fr" (French)
    - script_name: "Latin"
    - iso15924_script_code: "Latn"
    - split: train/validation/test (from path)
    - text_scope: "line"

Example:
    >>> parser = PoppLineParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../forms/popp-datasets"),
    ...     image_path=Path(".../extracted_images/train/00001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'fr'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "popp-line"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "popp-line_metadata.json"
__l4_integrate__ = "scripts/integrate_popp_line_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class PoppLineParser(BaseParser):
    """Parser for POPP-line French census handwriting dataset.

    Extracts language/script metadata and split information from
    materialized line images.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["popp-line", "popp_line"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse POPP-line labels from image path metadata.

        Args:
            dataset_path (Path): Root path of the POPP dataset
            image_path (Path): Absolute path to the PNG image being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with French language/script metadata
            and split information
        """
        labels = OriginalLabels()

        # Set language/script for French handwriting
        labels.language_code = "fr"
        labels.script_name = "Latin"
        labels.iso15924_script_code = "Latn"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "popp-line"
        labels.raw_labels["production"] = "handwritten"
        labels.raw_labels["capture_method"] = "scanner_flatbed"
        labels.raw_labels["has_handwriting"] = True
        labels.raw_labels["text_scope"] = "line"

        # Determine split from path
        for split in ("train", "validation", "test"):
            if split in image_path.parts:
                labels.raw_labels["split"] = split
                break

        return labels


__all__ = ["PoppLineParser"]
