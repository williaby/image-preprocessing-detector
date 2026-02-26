# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
r"""Parser for NDL-Minhon (National Diet Library Minhon) dataset.

NDL-Minhon contains line-level images of historical Japanese handwriting
(kuzushiji / classical cursive script) from the National Diet Library's
crowd-transcription project. Metadata is provided in v2_metadata.csv
(tab-separated) with book-level bibliographic information.

Dataset Structure:
    ndl-minhon/
        images/                     # PNG line-level images
            {project_id}/
                {book_id}/
                    *.png
        v2_metadata.csv             # Tab-separated book metadata
        annotations/                # Optional JSON annotation files
            {book_id}.json          # Per-book transcription annotations

v2_metadata.csv Format (tab-separated):
    project_id\tbook_id\tbook_name\tattribution\t...

Labels:
    - language_code: ja (Japanese)
    - script_name: Japanese
    - iso15924_script_code: Jpan (Japanese)
    - raw_labels: project_id, book_id, book_name, attribution,
                  is_vertical, is_kuzushiji, handwriting_script

Example:
    >>> parser = NdlMinhonParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/handwriting/ndl-minhon/images"),
    ...     image_path=Path(
    ...         "/data/handwriting/ndl-minhon/images/proj01/book01/line001.png"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ja'
    >>> print(labels.raw_labels["is_kuzushiji"])
    True
    >>> print(labels.raw_labels["handwriting_script"])
    'kuzushiji'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "ndl-minhon"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "ndl-minhon_metadata.json"
__l4_integrate__ = "scripts/integrate_ndl_minhon_enrichments.py"


import csv
import json
import logging
from pathlib import Path
from typing import Any, cast

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class NdlMinhonParser(BaseParser):
    """Parser for NDL-Minhon (National Diet Library Minhon) dataset.

    Extracts book-level metadata from v2_metadata.csv and optional
    transcription annotations from per-book JSON files. All images
    contain historical Japanese kuzushiji handwriting.
    """

    def __init__(self) -> None:
        """Initialize parser with metadata cache."""
        super().__init__()
        self._metadata_cache: dict[Path, dict[str, dict[str, str]]] = {}
        self._annotation_cache: dict[str, dict[str, Any]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["ndl-minhon", "ndl_minhon", "minhon"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse NDL-Minhon labels from metadata CSV and annotations.

        Args:
            dataset_path: Root path of the NDL-Minhon images directory
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language/script metadata, kuzushiji flag,
            and book-level bibliographic information
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Japanese
        labels.language_code = "ja"
        labels.script_name = "Japanese"
        labels.iso15924_script_code = "Jpan"

        # All NDL-Minhon images are kuzushiji handwriting
        labels.raw_labels["is_kuzushiji"] = True
        labels.raw_labels["handwriting_script"] = "kuzushiji"
        labels.raw_labels["is_vertical"] = True  # Classical Japanese is vertical

        # Extract project_id and book_id from path structure
        project_id, book_id = self._extract_ids_from_path(dataset_path, image_path)
        labels.raw_labels["project_id"] = project_id
        labels.raw_labels["book_id"] = book_id

        # Load book-level metadata from CSV
        dataset_root = dataset_path.parent  # ndl-minhon/ root
        metadata = self._load_metadata_csv(dataset_root)

        if book_id and book_id in metadata:
            record = metadata[book_id]
            labels.raw_labels["book_name"] = record.get("book_name", "")
            labels.raw_labels["attribution"] = record.get("attribution", "")
        elif project_id and project_id in metadata:
            # Fallback: try matching by project_id
            record = metadata[project_id]
            labels.raw_labels["book_name"] = record.get("book_name", "")
            labels.raw_labels["attribution"] = record.get("attribution", "")
        else:
            logger.debug(
                "No metadata record found for book_id='%s' (image: %s)",
                book_id,
                image_path.name,
            )

        # Try to load transcription from annotation JSON
        transcription = self._load_annotation(dataset_root, book_id)
        if transcription:
            labels.transcription = transcription

        return labels

    def _extract_ids_from_path(
        self,
        dataset_path: Path,
        image_path: Path,
    ) -> tuple[str, str]:
        """Extract project_id and book_id from image path structure.

        Expected path: images/{project_id}/{book_id}/image.png

        Args:
            dataset_path: Root images directory
            image_path: Absolute path to image

        Returns:
            Tuple of (project_id, book_id)
        """
        try:
            rel = image_path.relative_to(dataset_path)
            parts = rel.parts
            if len(parts) >= 3:
                return parts[0], parts[1]
            if len(parts) >= 2:
                return parts[0], ""
        except ValueError:
            pass  # image_path not under dataset_path; return default ("", "")
        return "", ""

    def _load_metadata_csv(self, dataset_root: Path) -> dict[str, dict[str, str]]:
        """Load and cache v2_metadata.csv, indexed by book_id.

        The CSV is tab-separated with columns: project_id, book_id,
        book_name, attribution, ...

        Args:
            dataset_root: Root path of NDL-Minhon dataset (parent of images/)

        Returns:
            Dictionary mapping book_id to row data
        """
        if dataset_root in self._metadata_cache:
            return self._metadata_cache[dataset_root]

        metadata: dict[str, dict[str, str]] = {}
        csv_path = dataset_root / "v2_metadata.csv"

        if csv_path.exists():
            try:
                with open(csv_path, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for row in reader:
                        book_id = row.get("book_id", "")
                        if book_id:
                            metadata[book_id] = dict(row)

                logger.debug(
                    "Loaded %d metadata records from %s",
                    len(metadata),
                    csv_path,
                )
            except (OSError, csv.Error) as exc:
                logger.warning(
                    "Failed to load v2_metadata.csv at %s: %s", csv_path, exc
                )

        self._metadata_cache[dataset_root] = metadata
        return metadata

    def _load_annotation(
        self,
        dataset_root: Path,
        book_id: str,
    ) -> str | None:
        """Load transcription from per-book JSON annotation file.

        Args:
            dataset_root: Root path of NDL-Minhon dataset
            book_id: Book identifier

        Returns:
            Transcription text if available, None otherwise
        """
        if not book_id:
            return None

        cache_key = f"{dataset_root}:{book_id}"
        if cache_key in self._annotation_cache:
            cached = self._annotation_cache[cache_key]
            return cast("str | None", cached.get("transcription"))

        annotation_path = dataset_root / "annotations" / f"{book_id}.json"
        if not annotation_path.exists():
            self._annotation_cache[cache_key] = {}
            return None

        try:
            with open(annotation_path, encoding="utf-8") as f:
                data = json.load(f)

            self._annotation_cache[cache_key] = data
            return cast("str | None", data.get("transcription"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Failed to load annotation %s: %s", annotation_path, exc)
            self._annotation_cache[cache_key] = {}
            return None

    def supports_batch(self) -> bool:
        """Batch parsing is optimized - CSV is loaded once."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads v2_metadata.csv once and extracts labels for all images.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        # Pre-load metadata CSV
        dataset_root = dataset_path.parent
        self._load_metadata_csv(dataset_root)

        # Parse each image (CSV is now cached)
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["NdlMinhonParser"]
