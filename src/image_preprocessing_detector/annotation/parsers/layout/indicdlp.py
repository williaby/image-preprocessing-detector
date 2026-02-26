# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for IndicDLP layout annotation dataset.

IndicDLP is a 12-language Indic document layout dataset with 42 layout classes
in COCO annotation format. Covers Assamese, Bengali, Gujarati, Hindi, Kannada,
Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu, and Urdu documents.

Dataset Structure:
    indicdlp/
        annotations/
            train.json       # COCO-format layout annotations
            val.json
            test.json
        images/
            {image_id}.jpg

COCO Format:
    - images: List of image metadata with id and file_name
    - annotations: List of bbox annotations with image_id, category_id, bbox
    - categories: List of category definitions (42 classes)

Example:
    >>> parser = IndicdlpParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/indicdlp"),
    ...     image_path=Path("/data/indicdlp/images/hindi_001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["source"])
    "indicdlp"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "indicdlp"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "indicdlp_metadata.json"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Module-level cache for COCO annotations (load once per file)
_COCO_CACHE: dict[str, dict[str, Any]] = {}


def _load_coco_annotations(coco_path: Path) -> dict[str, Any] | None:
    """Load and cache COCO annotations file.

    Args:
        coco_path: Path to COCO JSON file

    Returns:
        Cached annotations dict or None if loading fails
    """
    cache_key = str(coco_path)
    if cache_key in _COCO_CACHE:
        return _COCO_CACHE[cache_key]

    if not coco_path.exists():
        return None

    try:
        with open(coco_path) as f:
            coco_data = json.load(f)

        # Build filename -> image_id mapping
        filename_to_id: dict[str, int] = {}
        for img in coco_data.get("images", []):
            filename_to_id[img["file_name"]] = img["id"]

        # Build image_id -> annotations mapping
        id_to_annotations: dict[int, list[dict]] = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            if img_id not in id_to_annotations:
                id_to_annotations[img_id] = []
            id_to_annotations[img_id].append(ann)

        # Build category_id -> category_name mapping
        categories: dict[int, str] = {}
        for cat in coco_data.get("categories", []):
            categories[cat["id"]] = cat["name"]

        # Create final mapping: filename -> annotations with category names
        result: dict[str, Any] = {"annotations": {}, "categories": categories}
        for filename, img_id in filename_to_id.items():
            annotations = id_to_annotations.get(img_id, [])
            for ann in annotations:
                cat_id = ann.get("category_id")
                ann["category_name"] = (
                    categories.get(int(cat_id), "unknown")
                    if cat_id is not None
                    else "unknown"
                )
            result["annotations"][filename] = annotations

        _COCO_CACHE[cache_key] = result
        logger.debug(
            f"Loaded COCO annotations from {coco_path}: {len(filename_to_id)} images"
        )
        return result
    except Exception as e:
        logger.warning(f"Failed to load COCO annotations from {coco_path}: {e}")
        return None


class IndicdlpParser(BaseParser):
    """Parser for IndicDLP Indic document layout dataset.

    Extracts COCO-format layout annotations with 42 layout classes
    across 12 Indic languages from JSON annotation files.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["indicdlp"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse IndicDLP COCO annotations.

        Args:
            dataset_path: Root path of the IndicDLP dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with layout annotations in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "indicdlp"
        labels.raw_labels["annotation_format"] = "coco"

        # Look for COCO annotations in various locations
        coco_paths = [
            dataset_path / "annotations" / "train.json",
            dataset_path / "annotations" / "val.json",
            dataset_path / "annotations" / "test.json",
            dataset_path / "train.json",
            dataset_path / "val.json",
            dataset_path / "test.json",
        ]

        # Also search for any JSON files in annotations/ directory
        annotations_dir = dataset_path / "annotations"
        if annotations_dir.exists():
            for json_file in annotations_dir.glob("*.json"):
                if json_file not in coco_paths:
                    coco_paths.append(json_file)

        coco_data = None
        for coco_path in coco_paths:
            coco_data = _load_coco_annotations(coco_path)
            if coco_data:
                break

        if not coco_data:
            return labels

        # Get annotations for this image
        filename = image_path.name
        annotations = coco_data["annotations"].get(filename, [])

        if annotations:
            # Extract category IDs, bboxes, and class names
            category_ids = [ann.get("category_id") for ann in annotations]
            bboxes = [ann.get("bbox") for ann in annotations]
            class_names = [ann.get("category_name", "unknown") for ann in annotations]

            labels.raw_labels["category_ids"] = category_ids
            labels.raw_labels["bboxes"] = bboxes
            labels.raw_labels["class_names"] = class_names
            labels.raw_labels["num_annotations"] = len(annotations)
            labels.raw_labels["indicdlp_annotations"] = annotations

        return labels


__all__ = ["IndicdlpParser"]
