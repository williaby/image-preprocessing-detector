"""Parser for RealDAE camera-captured document dataset.

RealDAE (Real Document image Attribute Estimation) provides camera-captured
document images with various degradations including perspective distortion,
lighting variations, shadows, and blur.

Dataset Structure:
    realdae/
        {subset}/
            *_in.jpg        # Input degraded images
            *_gt.jpg        # Ground truth clean images (if available)

Degradation Types:
    - Perspective distortion (camera angle)
    - Uneven lighting
    - Shadows
    - Motion/defocus blur
    - Low resolution
    - Compression artifacts

Note: Only process *_in.jpg files (input images), not ground truth.

Example:
    >>> parser = RealdaeParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/realdae"),
    ...     image_path=Path("/data/realdae/train/doc_001_in.jpg"),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "realdae"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "realdae_metadata.json"
__l4_integrate__ = "scripts/integrate_realdae_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class RealdaeParser(BaseParser):
    """Parser for RealDAE camera-captured document dataset.

    Extracts metadata from filename patterns and provides pairing information
    between degraded input images and ground truth (if available).
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["realdae"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse RealDAE labels from filename patterns.

        Args:
            dataset_path (Path): Root path of the RealDAE dataset.
            image_path (Path): Absolute path to the image file being processed.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with degradation metadata in raw_labels.
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Store source and capture method
        labels.raw_labels["source"] = "realdae"
        labels.raw_labels["capture_method"] = "camera_smartphone"
        labels.raw_labels["is_degraded"] = True

        filename = image_path.stem

        # Check if this is an input image (_in suffix)
        if filename.endswith("_in"):
            labels.raw_labels["image_type"] = "input_degraded"
            base_name = filename[:-3]  # Remove "_in" suffix
            labels.raw_labels["base_name"] = base_name

            # Check for paired ground truth image
            gt_path = image_path.parent / f"{base_name}_gt.jpg"
            if gt_path.exists():
                labels.raw_labels["has_ground_truth"] = True
                labels.raw_labels["ground_truth_path"] = str(gt_path)
            else:
                labels.raw_labels["has_ground_truth"] = False

        elif filename.endswith("_gt"):
            # Ground truth image - typically not processed directly
            labels.raw_labels["image_type"] = "ground_truth"
            base_name = filename[:-3]  # Remove "_gt" suffix
            labels.raw_labels["base_name"] = base_name

        # Extract subset from parent directory (train/val/test)
        parent = image_path.parent.name
        if parent.lower() in ("train", "val", "test", "validation"):
            labels.raw_labels["subset"] = parent.lower()

        # Document is camera-captured, likely has these degradations
        labels.raw_labels["expected_degradations"] = [
            "perspective_distortion",
            "lighting_variation",
            "shadow",
            "blur",
        ]

        return labels


__all__ = ["RealdaeParser"]
