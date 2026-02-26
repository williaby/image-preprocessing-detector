# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for WSRD shadow removal dataset (NTIRE 2023/2024).

WSRD (Wide-angle Shadow Removal Dataset) provides paired shadow/shadow-free
document images used in the NTIRE 2023 and 2024 shadow removal challenges.

Dataset Structure:
    wsrd/
        train/
            input/        # Images with shadows
                *.png
            target/       # Shadow-free ground truth
                *.png
        validation/
            input/
                *.png
            target/
                *.png
        test/
            input/
                *.png
            target/
                *.png

Pairing:
    Input (shadow) and target (shadow-free) images share the same filename
    within their respective split/type directories.

Note: File format may be PNG or JPG depending on dataset version.

Example:
    >>> parser = WsrdParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/wsrd"),
    ...     image_path=Path("/data/wsrd/train/input/img_001.png"),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "wsrd"
__l4_workstream__ = "WS3"
__l4_task__ = "correction"
__l4_l2_file__ = "wsrd_metadata.json"
__l4_integrate__ = "scripts/integrate_wsrd_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

_VALID_SPLITS = frozenset({"train", "val", "validation", "test"})


class WsrdParser(BaseParser):
    """Parser for WSRD shadow removal dataset.

    Extracts split, image type (shadow/shadow-free), and pairing
    information from the directory structure.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["wsrd"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse WSRD labels from directory structure.

        Args:
            dataset_path: Root path of the WSRD dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with shadow removal metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "wsrd"
        labels.raw_labels["capture_method"] = "camera_smartphone"
        labels.raw_labels["correction_task"] = "shadow_removal"

        # Parse directory structure: wsrd/{split}/{type}/{filename}
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

        # Normalize validation split name
        if split == "validation":
            split = "val"

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
                # Try alternate extension (PNG <-> JPG)
                alt_ext = ".jpg" if image_path.suffix.lower() == ".png" else ".png"
                alt_target = (
                    image_path.parent.parent / "target" / (image_path.stem + alt_ext)
                )
                if alt_target.exists():
                    labels.raw_labels["has_ground_truth"] = True
                    labels.raw_labels["ground_truth_path"] = str(alt_target)
                else:
                    labels.raw_labels["has_ground_truth"] = False

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


__all__ = ["WsrdParser"]
