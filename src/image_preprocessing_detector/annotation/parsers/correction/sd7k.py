"""Parser for SD7K shadow removal dataset.

SD7K provides paired shadow/shadow-free document images for shadow removal
training and evaluation. The dataset contains approximately 7,000 images
split into training and test sets.

Dataset Structure:
    sd7k/
        train/
            input/        # 6,479 shadow images
                IMG_{number}.png
            target/       # 6,478 shadow-free ground truth
                IMG_{number}.png
        test/
            input/        # 760 shadow images
                IMG_{number}.png
            target/       # 760 shadow-free ground truth
                IMG_{number}.png

Known Issue:
    The training set has a count mismatch: 6,479 input images but only
    6,478 target images. One input image lacks a ground truth pair.

Filename Pattern:
    IMG_{number}.png (e.g., IMG_0001.png, IMG_6479.png)

Example:
    >>> parser = Sd7KParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/sd7k"),
    ...     image_path=Path("/data/sd7k/train/input/IMG_0042.png"),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "sd7k"
__l4_workstream__ = "WS3"
__l4_task__ = "correction"
__l4_l2_file__ = "sd7k_metadata.json"
__l4_integrate__ = "scripts/integrate_sd7k_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

_VALID_SPLITS = frozenset({"train", "test"})


class Sd7KParser(BaseParser):
    """Parser for SD7K shadow removal dataset.

    Extracts split, image type (shadow/shadow-free), and pairing
    information from the directory structure. Flags the known
    train target count mismatch (6,479 input vs 6,478 target).
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["sd7k"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SD7K labels from directory structure.

        Args:
            dataset_path: Root path of the SD7K dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with shadow removal metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "sd7k"
        labels.raw_labels["capture_method"] = "camera_smartphone"
        labels.raw_labels["correction_task"] = "shadow_removal"

        # Parse directory structure: sd7k/{split}/{type}/{filename}
        try:
            relative = image_path.relative_to(dataset_path)
            parts = relative.parts
        except ValueError:
            parts = ()

        split = None
        image_type = None

        if len(parts) >= 3:
            split = parts[0].lower()
            image_type = parts[1].lower()
        elif len(parts) >= 2:
            potential_split = parts[0].lower()
            if potential_split in _VALID_SPLITS:
                split = potential_split

        if split in _VALID_SPLITS:
            labels.raw_labels["subset"] = split

        # Determine image type from subdirectory
        if image_type == "input":
            labels.raw_labels["image_type"] = "shadow"
            labels.raw_labels["is_degraded"] = True

            # Check for paired shadow-free target
            target_path = image_path.parent.parent / "target" / image_path.name
            if target_path.exists():
                labels.raw_labels["has_ground_truth"] = True
                labels.raw_labels["ground_truth_path"] = str(target_path)
            else:
                labels.raw_labels["has_ground_truth"] = False

                # Flag known train mismatch issue
                if split == "train":
                    labels.raw_labels["known_issue"] = (
                        "train_target_count_mismatch: 6479 input vs 6478 target"
                    )

        elif image_type == "target":
            labels.raw_labels["image_type"] = "shadow_free"
            labels.raw_labels["is_degraded"] = False
            labels.raw_labels["has_ground_truth"] = False
        else:
            labels.raw_labels["image_type"] = "unknown"
            labels.raw_labels["is_degraded"] = True

        labels.raw_labels["base_filename"] = image_path.stem

        labels.raw_labels["expected_degradations"] = [
            "shadow",
            "uneven_lighting",
        ]

        return labels


__all__ = ["Sd7KParser"]
