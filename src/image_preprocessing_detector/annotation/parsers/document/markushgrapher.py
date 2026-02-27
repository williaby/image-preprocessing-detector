"""Parser for MarkushGrapher chemical structure dataset.

MarkushGrapher is a HuggingFace dataset containing Markush chemical structure
diagrams from patent documents. The dataset may contain parquet files with
image data and metadata, or a standard image directory structure.

Dataset Structure (Local):
    markushgrapher/
        images/
            {structure_id}.png
        data/
            *.parquet          # HuggingFace parquet files
        metadata.json          # Optional metadata file
        dataset_info.json      # HuggingFace dataset info

HuggingFace Dataset:
    Parquet format with metadata fields including chemical structure
    annotations and patent references.

Example:
    >>> parser = MarkushgrapherParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/markushgrapher"),
    ...     image_path=Path("/data/markushgrapher/images/struct_001.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["source"])
    "markushgrapher"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "markushgrapher"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "markushgrapher_metadata.json"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class MarkushgrapherParser(BaseParser):
    """Parser for MarkushGrapher chemical structure dataset.

    Extracts metadata from parquet files, JSON configs, or directory
    structure. Primarily tracks source identity and domain classification
    for chemical structure images from patent documents.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["markushgrapher"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MarkushGrapher metadata.

        Args:
            dataset_path: Root path of the MarkushGrapher dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with chemical structure metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "markushgrapher"
        labels.raw_labels["domain"] = "chemical_structure"
        labels.raw_labels["content_type"] = "markush_structure"

        # Try to find metadata from JSON config files
        metadata_paths = [
            dataset_path / "metadata.json",
            dataset_path / "dataset_info.json",
        ]

        for metadata_path in metadata_paths:
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)

                    labels.raw_labels["dataset_metadata"] = metadata
                    labels.raw_labels["metadata_file"] = str(
                        metadata_path.relative_to(dataset_path)
                    )
                    break
                except Exception as e:
                    logger.debug(f"Failed to parse metadata from {metadata_path}: {e}")

        # Check for parquet files (HuggingFace format)
        parquet_files = list(dataset_path.glob("**/*.parquet"))
        if parquet_files:
            labels.raw_labels["has_parquet"] = True
            labels.raw_labels["num_parquet_files"] = len(parquet_files)
        else:
            labels.raw_labels["has_parquet"] = False

        # Determine relative path within dataset
        try:
            relative_path = str(image_path.relative_to(dataset_path))
            labels.raw_labels["relative_path"] = relative_path
        except ValueError:
            labels.raw_labels["relative_path"] = image_path.name

        return labels


__all__ = ["MarkushgrapherParser"]
