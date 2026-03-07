"""Parser for SignverOD (Signature Verification Object Detection) dataset.

SignverOD contains 2,765 scanned document images with bounding box annotations
for signatures, initials, redactions, and dates. Documents sourced from NIST
government forms and GSA contract documents.

Dataset Structure:
    signverod/
        images/
            X_000.jpeg              # 2,765 document images
            nist_r0392_01.png
            gsa_LAR17002-SLA-1-_Z-01.png
        train.csv                   # 7,549 bounding box annotations
        test.csv                    # 1,666 bounding box annotations
        image_ids.csv               # Image metadata (height, width, id, file_name)
        categories.csv              # Category definitions

Annotation Format (CSV):
    area: Normalized bounding box area (fraction of image)
    bbox: [x, y, width, height] normalized to [0,1]
    category_id: 1=signature, 2=initials, 3=redaction, 4=date
    id: Annotation ID
    image_id: References image_ids.csv

Labels Extracted:
    - language_code: "en" (English)
    - script_name: "Latin"
    - iso15924_script_code: "Latn"
    - has_signature: True if category_id=1 annotations present
    - has_initials: True if category_id=2 annotations present
    - has_redaction: True if category_id=3 annotations present
    - has_date: True if category_id=4 annotations present
    - annotation_count: Total bounding boxes for this image
    - source_type: nist/gsa/other (from filename prefix)

Example:
    >>> parser = SignverODParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../handwriting/signverod"),
    ...     image_path=Path(".../signverod/images/nist_r0392_01.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["has_signature"])
    True
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "signverod"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "signverod_metadata.json"
__l4_integrate__ = "scripts/integrate_signverod_enrichments.py"


import csv
from pathlib import Path
from typing import Any

from ....utils.log_config import get_logger
from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = get_logger(__name__)

# Category mapping from categories.csv
_CATEGORY_NAMES = {1: "signature", 2: "initials", 3: "redaction", 4: "date"}


class SignverODParser(BaseParser):
    """Parser for SignverOD signature detection dataset.

    Extracts per-image annotation statistics from train/test CSV files,
    including signature/initials/redaction/date counts and document source.
    """

    def __init__(self) -> None:
        super().__init__()
        # Lazy-loaded annotation index: {filename -> [{category_id, bbox, ...}]}
        self._annotation_cache: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self._image_id_cache: dict[str, dict[str, str]] = {}
        self._split_ids_cache: dict[str, set[str]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["signverod"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SignverOD labels from CSV annotation files.

        Args:
            dataset_path: Root path of the SignverOD dataset
            image_path: Absolute path to the image being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with signature/handwriting presence,
            annotation counts, and document source metadata
        """
        labels = OriginalLabels()

        # Set language/script for English documents
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.iso15924_script_code = "Latn"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "signverod"
        labels.raw_labels["capture_method"] = "scanner_flatbed"

        # Determine source from filename
        stem = image_path.stem
        if stem.startswith("nist_"):
            labels.raw_labels["source_type"] = "nist"
        elif stem.startswith("gsa_"):
            labels.raw_labels["source_type"] = "gsa"
        else:
            labels.raw_labels["source_type"] = "other"

        # Load annotation index
        image_id_map = self._load_image_ids(dataset_path)
        annotations = self._load_annotations(dataset_path)

        # Set stable default schema for all parse paths
        labels.raw_labels["annotation_count"] = 0
        labels.raw_labels["has_signature"] = False
        labels.raw_labels["has_initials"] = False
        labels.raw_labels["has_redaction"] = False
        labels.raw_labels["has_date"] = False
        labels.raw_labels["has_handwriting"] = False
        labels.raw_labels["category_counts"] = {}

        # Find image_id for this file
        filename = image_path.name
        image_id = image_id_map.get(filename)
        if image_id is None:
            logger.debug("No image_id found for %s", filename)
            return labels

        # Get annotations for this image
        img_annotations = annotations.get(image_id, [])
        if not img_annotations:
            return labels

        # Count by category
        category_counts: dict[str, int] = {}
        for ann in img_annotations:
            cat_id = int(ann.get("category_id", 0))
            cat_name = _CATEGORY_NAMES.get(cat_id, "unknown")
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        labels.raw_labels["annotation_count"] = len(img_annotations)
        labels.raw_labels["has_signature"] = category_counts.get("signature", 0) > 0
        labels.raw_labels["has_initials"] = category_counts.get("initials", 0) > 0
        labels.raw_labels["has_redaction"] = category_counts.get("redaction", 0) > 0
        labels.raw_labels["has_date"] = category_counts.get("date", 0) > 0
        labels.raw_labels["has_handwriting"] = (
            category_counts.get("signature", 0) > 0
            or category_counts.get("initials", 0) > 0
        )
        labels.raw_labels["category_counts"] = category_counts

        # Determine split
        if image_id in self._get_split_ids(dataset_path, "train"):
            labels.raw_labels["split"] = "train"
        elif image_id in self._get_split_ids(dataset_path, "test"):
            labels.raw_labels["split"] = "test"

        return labels

    def _load_image_ids(self, dataset_path: Path) -> dict[str, str]:
        """Load image_ids.csv mapping filename -> image_id.

        Args:
            dataset_path: Root path of SignverOD dataset

        Returns:
            Dict mapping file_name -> id
        """
        cache_key = str(dataset_path)
        if cache_key in self._image_id_cache:
            return self._image_id_cache[cache_key]

        csv_path = dataset_path / "image_ids.csv"
        if not csv_path.exists():
            logger.warning("image_ids.csv not found: %s", csv_path)
            empty: dict[str, str] = {}
            self._image_id_cache[cache_key] = empty
            return empty

        mapping: dict[str, str] = {}
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mapping[row["file_name"]] = row["id"]

        self._image_id_cache[cache_key] = mapping
        return mapping

    def _load_annotations(self, dataset_path: Path) -> dict[str, list[dict[str, Any]]]:
        """Load and merge train.csv + test.csv annotations by image_id.

        Args:
            dataset_path: Root path of SignverOD dataset

        Returns:
            Dict mapping image_id -> list of annotation dicts
        """
        cache_key = str(dataset_path)
        if cache_key in self._annotation_cache:
            return self._annotation_cache[cache_key]

        index: dict[str, list[dict[str, Any]]] = {}
        for csv_name in ("train.csv", "test.csv"):
            csv_path = dataset_path / csv_name
            if not csv_path.exists():
                continue
            with open(csv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    img_id = row["image_id"]
                    if img_id not in index:
                        index[img_id] = []
                    index[img_id].append(dict(row))

        self._annotation_cache[cache_key] = index
        logger.debug(
            "Loaded %d annotation entries for %d images",
            sum(len(v) for v in index.values()),
            len(index),
        )
        return index

    def _get_split_ids(self, dataset_path: Path, split: str) -> set[str]:
        """Get image IDs belonging to a specific split.

        Args:
            dataset_path: Root path of SignverOD dataset
            split: "train" or "test"

        Returns:
            Set of image_id strings for the given split
        """
        cache_key = f"{dataset_path}:{split}"
        if cache_key in self._split_ids_cache:
            return self._split_ids_cache[cache_key]

        csv_path = dataset_path / f"{split}.csv"
        if not csv_path.exists():
            return set()
        ids: set[str] = set()
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row["image_id"])

        self._split_ids_cache[cache_key] = ids
        return ids


__all__ = ["SignverODParser"]
