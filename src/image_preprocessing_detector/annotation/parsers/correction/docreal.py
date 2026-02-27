"""Parser for DocReal document dewarping benchmark dataset.

DocReal provides real-world distorted document images alongside scanned
ground truth for dewarping evaluation. The distorted set contains 201
images and the scanned ground truth set contains 50 images.

Dataset Structure:
    DocReal/
        distorted/        # 201 distorted document photos
            {doc_id}_{variant}.png
        scanned/          # 50 scanned ground truth images
            {doc_id}.png

Filename Patterns:
    - Distorted: {doc_id}_{variant}.png (e.g., 001_1.png, 001_2.png)
    - Scanned: {doc_id}.png (e.g., 001.png)

    Multiple distorted variants may exist for each scanned ground truth.

Example:
    >>> parser = DocrealParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/DocReal"),
    ...     image_path=Path("/data/DocReal/distorted/042_1.png"),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "docreal"
__l4_workstream__ = "WS3"
__l4_task__ = "correction"
__l4_l2_file__ = "docreal_metadata.json"
__l4_integrate__ = "scripts/integrate_docreal_enrichments.py"


import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

# Pattern for distorted filenames: {doc_id}_{variant}
_DISTORTED_PATTERN = re.compile(r"^(.+?)_(\d+)$")


class DocrealParser(BaseParser):
    """Parser for DocReal document dewarping benchmark.

    Extracts image type (distorted vs scanned), document ID, and
    variant information from filename patterns and directory structure.
    Scanned images serve as ground truth for distorted variants.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["docreal"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DocReal labels from directory structure and filenames.

        Args:
            dataset_path: Root path of the DocReal dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with dewarping benchmark metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "docreal"
        labels.raw_labels["correction_task"] = "dewarping"

        # Determine image type from parent directory
        parent_name = image_path.parent.name.lower()
        filename = image_path.stem

        if parent_name == "distorted":
            labels.raw_labels["image_type"] = "distorted"
            labels.raw_labels["capture_method"] = "camera_smartphone"
            labels.raw_labels["is_degraded"] = True

            # Extract doc_id and variant from filename pattern
            match = _DISTORTED_PATTERN.match(filename)
            if match:
                doc_id = match.group(1)
                variant = match.group(2)
                labels.raw_labels["doc_id"] = doc_id
                labels.raw_labels["variant"] = int(variant)

                # Check for paired scanned ground truth
                scanned_path = dataset_path / "scanned" / f"{doc_id}.png"
                if scanned_path.exists():
                    labels.raw_labels["has_ground_truth"] = True
                    labels.raw_labels["ground_truth_path"] = str(scanned_path)
                else:
                    labels.raw_labels["has_ground_truth"] = False
            else:
                # Filename doesn't match expected pattern
                labels.raw_labels["doc_id"] = filename
                labels.raw_labels["has_ground_truth"] = False

            labels.raw_labels["expected_degradations"] = [
                "perspective_distortion",
                "warping",
                "lighting_variation",
            ]

        elif parent_name == "scanned":
            labels.raw_labels["image_type"] = "ground_truth"
            labels.raw_labels["capture_method"] = "scanner_flatbed"
            labels.raw_labels["is_degraded"] = False
            labels.raw_labels["doc_id"] = filename
            labels.raw_labels["has_ground_truth"] = False

        else:
            # Unknown directory structure
            labels.raw_labels["image_type"] = "unknown"
            labels.raw_labels["capture_method"] = "unknown"
            labels.raw_labels["is_degraded"] = True

        labels.raw_labels["base_filename"] = filename

        return labels


__all__ = ["DocrealParser"]
