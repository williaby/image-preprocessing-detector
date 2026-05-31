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

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "doclaynet"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "doclaynet_metadata.json"
__l4_integrate__ = "scripts/integrate_doclaynet_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Common file name constants (S1192: avoid duplicate string literals)
TRAIN_JSON = "train.json"

# Module-level cache for COCO annotations (load once per file)
_COCO_CACHE: dict[str, dict[str, Any]] = {}


def _load_coco_annotations(coco_path: Path) -> dict[str, Any] | None:
    """Load and cache COCO annotations file.

    Returns dict with:
        - annotations: Mapping of filename -> list of annotations
        - categories: Mapping of category_id -> category_name

    Args:
        coco_path (Path): Path to COCO JSON file

    Returns:
        dict[str, Any] | None: Cached annotations dict or None if loading fails
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
            dataset_path (Path): Root path of the DocLayNet dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with raw_labels["doclaynet_annotations"] populated

        """
        labels = OriginalLabels()

        # Look for COCO annotations in various locations
        coco_paths = [
            dataset_path / "ground_truth" / "coco" / TRAIN_JSON,
            dataset_path / "ground_truth" / "coco" / "val.json",
            dataset_path / "ground_truth" / "coco" / "test.json",
            dataset_path / "COCO" / TRAIN_JSON,
            dataset_path / "COCO" / "val.json",
            dataset_path / "COCO" / "test.json",
            dataset_path / "annotations" / TRAIN_JSON,
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

        # Extract text content from ground_truth/json/ files
        text_json_path = (
            dataset_path / "ground_truth" / "json" / f"{image_path.stem}.json"
        )
        if text_json_path.exists():
            try:
                with open(text_json_path) as f:
                    text_data = json.load(f)

                # Extract all cell text
                cells = text_data.get("cells", [])
                if cells:
                    # Sort cells by position (top-to-bottom, left-to-right)
                    sorted_cells = sorted(
                        cells, key=lambda c: (c["bbox"][1], c["bbox"][0])
                    )
                    full_text = " ".join(
                        cell["text"] for cell in sorted_cells if cell.get("text")
                    )

                    if full_text.strip():
                        if labels.raw_labels is None:
                            labels.raw_labels = {}
                        labels.raw_labels["text_content"] = {
                            "full_text": full_text,
                            "source_type": "ground_truth",
                            "source_file": str(
                                text_json_path.relative_to(dataset_path)
                            ),
                            "source_format": "doclaynet_json_cells",
                            "extraction_method": "parse_doclaynet_labels",
                            "is_complete": True,
                            "segments": [
                                {
                                    "text": cell["text"],
                                    "segment_type": "cell",
                                    "bbox": cell["bbox"],
                                    "sequence_index": idx,
                                }
                                for idx, cell in enumerate(sorted_cells)
                                if cell.get("text")
                            ],
                        }
            except Exception as e:
                logger.warning(f"Failed to extract text from {text_json_path}: {e}")

        return labels


__all__ = ["DocLayNetParser"]
