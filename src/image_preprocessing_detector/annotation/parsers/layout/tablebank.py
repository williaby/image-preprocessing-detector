# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for TableBank table detection dataset.

TableBank provides COCO-format bounding boxes for table detection in
documents from both LaTeX and Word sources.

Dataset Structure:
    TableBank/
        Detection/
            annotations/
                tablebank_latex_train.json
                tablebank_word_train.json
            images/
                latex/
                    *.png
                word/
                    *.png
        or
        Detection/
            annotations/
                train.json
        or
        annotations/
            train.json

COCO Format:
    - images: List of image metadata with id and file_name
    - annotations: List of bbox annotations with image_id, category_id (table)
    - categories: Single category for "table"

Example:
    >>> parser = TableBankParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/tablebank"),
    ...     image_path=Path("/data/tablebank/Detection/images/latex/table001.png"),
    ...     config={},
    ... )
    >>> print(len(labels.raw_labels["tablebank_annotations"]))
    3
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


class TableBankParser(BaseParser):
    """Parser for TableBank table detection dataset.

    Extracts COCO-format table bounding boxes from JSON annotation files.
    Supports both LaTeX and Word document sources.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["tablebank"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse TableBank COCO-format table annotations.

        Args:
            dataset_path: Root path of the TableBank dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels["tablebank_annotations"] populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # TableBank structure: Detection/images/ and Detection/annotations/
        coco_paths = [
            dataset_path
            / "TableBank"
            / "Detection"
            / "annotations"
            / "tablebank_latex_train.json",
            dataset_path
            / "TableBank"
            / "Detection"
            / "annotations"
            / "tablebank_word_train.json",
            dataset_path / "Detection" / "annotations" / "train.json",
            dataset_path / "annotations" / "train.json",
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
            labels.raw_labels["tablebank_annotations"] = annotations

        return labels


__all__ = ["TableBankParser"]
