# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DocLayNet layout annotation dataset.

DocLayNet provides COCO-format annotations for document layout analysis
with 11 semantic classes covering various document elements.

Dataset Structure:
    DocLayNet/
        COCO/
            train.json
            val.json
            test.json
        PNG/
            {document_id}_{page_num}.png
        or
        annotations/
            train.json
            instances_train.json

COCO Format:
    - images: List of image metadata with id and file_name
    - annotations: List of bbox annotations with image_id, category_id, bbox
    - categories: List of category definitions

DocLayNet Categories (11 classes):
    - Caption
    - Footnote
    - Formula
    - List-Item
    - Page-Footer
    - Page-Header
    - Picture
    - Section-Header
    - Table
    - Text
    - Title

Example:
    >>> parser = DocLayNetParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/doclaynet"),
    ...     image_path=Path("/data/doclaynet/PNG/doc1234_0.png"),
    ...     config={},
    ... )
    >>> print(len(labels.raw_labels["doclaynet_annotations"]))
    15
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)

# Module-level cache for COCO annotations (load once per file)
_COCO_CACHE: dict[str, dict[str, Any]] = {}


def _load_coco_annotations(coco_path: Path) -> dict[str, Any] | None:
    """Load and cache COCO annotations file.

    Returns dict with:
        - annotations: Mapping of filename -> list of annotations
        - categories: Mapping of category_id -> category_name

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
            # Add category names to annotations
            for ann in annotations:
                ann["category_name"] = categories.get(ann.get("category_id"), "unknown")
            result["annotations"][filename] = annotations

        _COCO_CACHE[cache_key] = result
        logger.debug(
            f"Loaded COCO annotations from {coco_path}: {len(filename_to_id)} images"
        )
        return result
    except Exception as e:
        logger.warning(f"Failed to load COCO annotations from {coco_path}: {e}")
        return None


class DocLayNetParser(BaseParser):
    """Parser for DocLayNet document layout dataset.

    Extracts COCO-format layout annotations with 11 semantic classes
    from JSON files in train/val/test splits.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["doclaynet"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DocLayNet COCO annotations.

        Args:
            dataset_path: Root path of the DocLayNet dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels["doclaynet_annotations"] populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Look for COCO annotations in various locations
        coco_paths = [
            dataset_path / "COCO" / "train.json",
            dataset_path / "COCO" / "val.json",
            dataset_path / "COCO" / "test.json",
            dataset_path / "annotations" / "train.json",
            dataset_path / "annotations" / "instances_train.json",
        ]

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
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["doclaynet_annotations"] = annotations

        return labels


__all__ = ["DocLayNetParser"]
