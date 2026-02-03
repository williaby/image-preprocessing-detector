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

Extracts (Layer 1 - Basic Annotations):
    - raw_labels["tablebank_annotations"]: COCO-format table bounding boxes
    - language_code: "en" (English) - dataset-level assignment
    - script_name: "Latin" with ISO 15924 code "Latn" - dataset-level assignment

Extracts (Layer 2 - Enhanced Metadata):
    - raw_labels["split"]: train/validation/test split from annotation filename
    - raw_labels["dataset_subset"]: latex or word source subset
    - raw_labels["capture_method"]: "born_digital" (LaTeX rendered, Word extracted)
    - raw_labels["domain_level1"]: "SCI" (scientific publications)
    - raw_labels["has_table"]: True if table annotations present

Language Assignment Rationale:
    TableBank is sourced from arXiv papers (LaTeX subset) and academic Word
    documents, curated by MSRA NLC Group. The LaTeX subset uses arXiv paper
    IDs in filenames (e.g., "1312.1234_5.png"), confirming English scientific
    content. The Word subset contains academic documents from the same domain.
    Domain provenance confirms English/Latin for the entire dataset.

Example:
    >>> parser = TableBankParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/tablebank"),
    ...     image_path=Path("/data/tablebank/Detection/images/latex/table001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    en
    >>> print(labels.script_name)
    Latin
    >>> print(labels.raw_labels.get("capture_method"))
    born_digital
    >>> print(labels.raw_labels.get("domain_level1"))
    SCI
"""

from __future__ import annotations

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
                cat_id = ann.get("category_id")
                if cat_id is not None:
                    ann["category_name"] = categories.get(cat_id, "unknown")
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

        # Dataset-level language assignment: All TableBank samples are English
        # Source: arXiv papers (LaTeX) and academic Word documents (MSRA NLC Group)
        # Validation: arXiv IDs in LaTeX filenames confirm English scientific content
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.raw_labels = {
            "iso15924_script": "Latn",
            "language_source": "dataset_provenance",
            "language_confidence": 0.95,
        }

        # R2: Add capture method metadata (born_digital)
        labels.raw_labels.update(
            {
                "capture_method": "born_digital",
                "capture_confidence": 1.0,
                "capture_detection_method": "dataset_provenance",
                "capture_method_rationale": "LaTeX rendered and Word extracted tables (no scanning)",
            }
        )

        # R3: Add domain classification (SCI)
        labels.raw_labels.update(
            {
                "domain_level1": "SCI",
                "domain_confidence": 0.95,
                "domain_source": "dataset_provenance",
                "domain_rationale": "arXiv papers (LaTeX) and academic documents (Word)",
            }
        )

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
        matched_coco_path = None
        for coco_path in coco_paths:
            coco_data = _load_coco_annotations(coco_path)
            if coco_data:
                matched_coco_path = coco_path
                break

        if not coco_data:
            return labels

        # R1: Extract provenance fields (split, subset) from COCO filename
        if matched_coco_path:
            split_map = {
                "train": "train",
                "val": "validation",
                "test": "test",
            }
            subset_map = {
                "latex": "latex",
                "word": "word",
            }

            # Extract from coco_path filename (e.g., "tablebank_latex_train.json")
            filename_stem = matched_coco_path.stem  # "tablebank_latex_train"
            parts = filename_stem.split("_")

            if len(parts) >= 3:
                # Format: tablebank_<subset>_<split>
                subset = parts[1]  # "latex" or "word"
                split = parts[2]  # "train", "val", "test"

                labels.raw_labels["dataset_subset"] = subset_map.get(subset, subset)
                labels.raw_labels["split"] = split_map.get(split, split)
            elif len(parts) == 1:
                # Format: train.json (no subset, only split)
                split = parts[0]
                labels.raw_labels["split"] = split_map.get(split, split)

        # Get annotations for this image
        filename = image_path.name
        annotations = coco_data["annotations"].get(filename, [])

        # Add annotations to raw_labels (preserve existing language metadata)
        if annotations:
            labels.raw_labels["tablebank_annotations"] = annotations

        # R4: Add content_flags (has_table) based on annotation presence
        if annotations:
            labels.raw_labels.update(
                {
                    "has_table": True,
                    "content_flags_tier": "tier_1_annotation",
                    "content_flags_source": "coco_annotation",
                }
            )
        else:
            labels.raw_labels.update(
                {
                    "has_table": False,
                    "content_flags_tier": "tier_3_heuristic",
                    "content_flags_source": "parser_inference",
                }
            )

        return labels


__all__ = ["TableBankParser"]
