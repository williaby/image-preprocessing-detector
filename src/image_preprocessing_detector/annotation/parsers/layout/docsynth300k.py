# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for DocSynth300K synthetic document layout dataset.

DocSynth300K is a large-scale synthetic document layout analysis dataset
from the DocLayout-YOLO project. Contains 300K synthetic document images
with YOLO-format layout annotations.

Dataset Structure:
    docsynth300k/
        part0.parquet
        part1.parquet
        ...
        part29.parquet
        README.md

Parquet Schema:
    - filename: str - Image filename (e.g., "1720629091_634364.jpg")
    - image_data: bytes - JPEG image data (base64 in HuggingFace, raw bytes locally)
    - anno_string: list[str] - YOLO-format annotations
    - split: str - Split identifier ("train")

YOLO Annotation Format:
    Each annotation string: "class_id x_center y_center width height"
    - class_id: int - DocLayNet-compatible class index
    - x_center, y_center, width, height: float - Normalized [0,1] coordinates

DocSynth300K Categories (aligned with DocLayNet 11 classes):
    The dataset uses the same category structure as DocLayNet for
    training models that transfer to DocLayNet evaluation.

Source:
    - Paper: DocLayout-YOLO (arXiv:2410.12628)
    - GitHub: https://github.com/opendatalab/DocLayout-YOLO
    - HuggingFace: https://huggingface.co/datasets/juliozhao/DocSynth300K
    - License: Apache-2.0

Example:
    >>> parser = DocSynth300KParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/docsynth300k"),
    ...     image_path=Path("/data/docsynth300k/extracted/1720629091_634364.jpg"),
    ...     config={},
    ... )
    >>> print(len(labels.raw_labels["docsynth300k_annotations"]))
    5
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Module-level cache for parquet index (filename -> annotations mapping)
_PARQUET_INDEX: dict[str, dict[str, list[dict[str, Any]]]] = {}


def _parse_yolo_annotation(anno_str: str) -> dict[str, Any]:
    """Parse a single YOLO-format annotation string.

    Args:
        anno_str: YOLO annotation string "class_id x_center y_center width height ..."

    Returns:
        Dict with parsed annotation fields
    """
    parts = anno_str.strip().split()
    if len(parts) < 5:
        return {}

    try:
        class_id = int(parts[0])
        # YOLO format: normalized x_center, y_center, width, height
        x_center = float(parts[1])
        y_center = float(parts[2])
        width = float(parts[3])
        height = float(parts[4])

        # Convert to COCO-style bbox [x, y, width, height] (top-left corner)
        x = x_center - width / 2
        y = y_center - height / 2

        return {
            "category_id": class_id,
            "bbox_normalized": [x, y, width, height],
            "bbox_yolo": [x_center, y_center, width, height],
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse YOLO annotation '{anno_str}': {e}")
        return {}


def _build_parquet_index(dataset_path: Path) -> dict[str, list[dict[str, Any]]] | None:
    """Build filename to annotations index from parquet files.

    This is an expensive operation that reads all parquet files.
    Results are cached at module level.

    Args:
        dataset_path: Root path of the DocSynth300K dataset

    Returns:
        Mapping of filename -> list of parsed annotations, or None if loading fails
    """
    cache_key = str(dataset_path)
    if cache_key in _PARQUET_INDEX:
        return _PARQUET_INDEX[cache_key]

    try:
        import pyarrow.parquet as pq
    except ImportError:
        logger.warning("pyarrow not installed - cannot read parquet files")
        return None

    # Find all parquet files
    parquet_files = sorted(dataset_path.glob("*.parquet"))
    if not parquet_files:
        logger.warning(f"No parquet files found in {dataset_path}")
        return None

    index: dict[str, list[dict[str, Any]]] = {}

    for parquet_path in parquet_files:
        try:
            # Read only filename and anno_string columns
            table = pq.read_table(
                parquet_path,
                columns=["filename", "anno_string"],
            )

            for i in range(len(table)):
                filename = table["filename"][i].as_py()
                anno_strings = table["anno_string"][i].as_py()

                if filename and anno_strings:
                    annotations = []
                    for anno_str in anno_strings:
                        parsed = _parse_yolo_annotation(anno_str)
                        if parsed:
                            annotations.append(parsed)
                    if annotations:
                        index[filename] = annotations

            logger.debug(f"Indexed {len(table)} records from {parquet_path.name}")

        except Exception as e:
            logger.warning(f"Failed to read parquet file {parquet_path}: {e}")
            continue

    if index:
        _PARQUET_INDEX[cache_key] = index
        logger.info(f"Built parquet index for {dataset_path}: {len(index)} images")

    return index if index else None


class DocSynth300KParser(BaseParser):
    """Parser for DocSynth300K synthetic document layout dataset.

    Extracts YOLO-format layout annotations from parquet files and converts
    them to a standardized format compatible with DocLayNet annotations.

    Note:
        For performance, this parser builds an index of all annotations
        on first access. For very large datasets, consider using batch
        parsing or pre-extracting annotations.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["docsynth300k"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DocSynth300K YOLO annotations.

        Args:
            dataset_path: Root path of the DocSynth300K dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels["docsynth300k_annotations"] populated

        Note:
            First call builds an index from parquet files, which may take time.
            Subsequent calls use the cached index.
        """
        labels = OriginalLabels()

        # Build or retrieve parquet index
        index = _build_parquet_index(dataset_path)
        if not index:
            return labels

        # Get annotations for this image
        filename = image_path.name
        annotations = index.get(filename, [])

        if annotations:
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["docsynth300k_annotations"] = annotations

        return labels

    def supports_batch(self) -> bool:
        """DocSynth300K benefits from batch parsing due to parquet format."""
        return True


__all__ = ["DocSynth300KParser"]
