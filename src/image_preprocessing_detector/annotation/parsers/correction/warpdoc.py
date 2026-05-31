"""Parser for WarpDoc document dewarping dataset.

WarpDoc contains 1,020 camera-captured document images with 6 distinct
distortion types. Designed for evaluating document dewarping algorithms.

Dataset Structure:
    warpdoc/
        Fold/             # Folded document pages
            *.jpg
        Curved/           # Curved/bent documents
            *.jpg
        Incomplete/       # Partially visible documents
            *.jpg
        Random/           # Random deformation patterns
            *.jpg
        Rotating/         # Rotational distortion
            *.jpg
        Perspective/      # Perspective distortion
            *.jpg

Distortion Types:
    - Fold: Physical folds in paper
    - Curved: Curved/bent page surfaces (book spines, etc.)
    - Incomplete: Partially captured documents
    - Random: Random deformation patterns
    - Rotating: Rotational distortion from capture angle
    - Perspective: Perspective distortion from oblique capture

Example:
    >>> parser = WarpdocParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/warpdoc"),
    ...     image_path=Path("/data/warpdoc/Curved/img_042.jpg"),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "warpdoc"
__l4_workstream__ = "WS3"
__l4_task__ = "correction"
__l4_l2_file__ = "warpdoc_metadata.json"
__l4_integrate__ = "scripts/integrate_warpdoc_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

# Known distortion types and their canonical names
_DISTORTION_TYPES: dict[str, str] = {
    "fold": "fold",
    "curved": "curved",
    "incomplete": "incomplete",
    "random": "random",
    "rotating": "rotating",
    "perspective": "perspective",
}

# Map distortion types to expected degradation labels
_DISTORTION_DEGRADATIONS: dict[str, list[str]] = {
    "fold": ["fold", "warping"],
    "curved": ["curved", "warping"],
    "incomplete": ["incomplete_capture", "perspective_distortion"],
    "random": ["warping", "random_deformation"],
    "rotating": ["rotation", "perspective_distortion"],
    "perspective": ["perspective_distortion"],
}


class WarpdocParser(BaseParser):
    """Parser for WarpDoc document dewarping dataset.

    Extracts distortion type from directory structure. Each subdirectory
    corresponds to one of 6 distortion categories. All images are
    camera-captured documents.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["warpdoc"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse WarpDoc labels from directory structure.

        Args:
            dataset_path (Path): Root path of the WarpDoc dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with dewarping metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "warpdoc"
        labels.raw_labels["capture_method"] = "camera_smartphone"
        labels.raw_labels["correction_task"] = "dewarping"
        labels.raw_labels["is_degraded"] = True

        # Extract distortion type from parent directory
        parent_name = image_path.parent.name.lower()
        canonical_distortion = _DISTORTION_TYPES.get(parent_name)

        if canonical_distortion is not None:
            labels.raw_labels["distortion_type"] = canonical_distortion
            labels.raw_labels["distortion_type_original"] = image_path.parent.name

            # Set degradation labels specific to this distortion type
            degradations = _DISTORTION_DEGRADATIONS.get(
                canonical_distortion, ["warping"]
            )
            labels.raw_labels["expected_degradations"] = degradations
        else:
            # Unknown directory - still mark as warped document
            labels.raw_labels["distortion_type"] = "unknown"
            labels.raw_labels["expected_degradations"] = [
                "perspective_distortion",
                "warping",
            ]

        labels.raw_labels["base_filename"] = image_path.stem

        return labels


__all__ = ["WarpdocParser"]
