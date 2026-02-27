"""Parser for Document Haystack benchmark dataset.

Document Haystack is a document retrieval benchmark with query-relevance
pairs for evaluating document search and retrieval systems. Images represent
document pages that serve as retrieval candidates.

Dataset Structure:
    document-haystack/
        images/
            {document_id}.png
        metadata/
            queries.json          # Query-document relevance pairs
            documents.json        # Document metadata
            documents.csv         # Alternative metadata format

Example:
    >>> parser = DocumentHaystackParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/document-haystack"),
    ...     image_path=Path("/data/document-haystack/images/doc_042.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["source"])
    "document-haystack"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "document-haystack"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "document_haystack_metadata.json"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class DocumentHaystackParser(BaseParser):
    """Parser for Document Haystack retrieval benchmark.

    Extracts document metadata and retrieval task information from
    the benchmark's metadata files. Primarily tracks document identity
    and benchmark membership for downstream evaluation.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["document-haystack"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Document Haystack benchmark metadata.

        Args:
            dataset_path: Root path of the Document Haystack dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with benchmark metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "document-haystack"
        labels.raw_labels["task"] = "document_retrieval"
        labels.raw_labels["is_benchmark"] = True

        # Determine relative path of image within dataset
        try:
            relative_path = str(image_path.relative_to(dataset_path))
            labels.raw_labels["relative_path"] = relative_path
        except ValueError:
            labels.raw_labels["relative_path"] = image_path.name

        # Try to find metadata files with document info
        metadata_paths = [
            dataset_path / "metadata" / "documents.json",
            dataset_path / "documents.json",
            dataset_path / "metadata.json",
        ]

        for metadata_path in metadata_paths:
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)

                    # Look up document by filename
                    filename = image_path.stem
                    if isinstance(metadata, dict) and filename in metadata:
                        doc_meta = metadata[filename]
                        labels.raw_labels["document_metadata"] = doc_meta
                    elif isinstance(metadata, list):
                        for entry in metadata:
                            if (
                                entry.get("id") == filename
                                or entry.get("file_name") == image_path.name
                            ):
                                labels.raw_labels["document_metadata"] = entry
                                break

                    labels.raw_labels["metadata_file"] = str(
                        metadata_path.relative_to(dataset_path)
                    )
                    break
                except Exception as e:
                    logger.debug(f"Failed to parse metadata from {metadata_path}: {e}")

        return labels


__all__ = ["DocumentHaystackParser"]
