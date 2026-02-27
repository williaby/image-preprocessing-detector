"""Parser for Egyptian Handwriting Dataset.

Egyptian handwriting dataset with 11,216 word-level images from 89 writers
(ages 6-73). All images are individual Arabic word crops with corresponding
Arabic text labels. Data is in HuggingFace parquet format.

Dataset Structure:
    egyptian-handwriting/
        data/
            egy_handwriting_dataset_set1.parquet   # 11,216 rows: {image, label}
        README.md

Parquet Schema:
    - image: binary (JPEG/PNG word crop)
    - label: string (Arabic Unicode word, 1-11 chars)

Labels Extracted:
    - language_code: "ar" (Arabic)
    - script_name: "Arabic"
    - iso15924_script_code: "Arab"
    - transcription: Arabic word label
    - scope: word-level

Note:
    This dataset stores images inside parquet columns (not as files on disk).
    The parser extracts labels from the parquet metadata only. Actual image
    extraction for training is handled separately during dataset preparation.

Example:
    >>> parser = EgyptianHandwritingParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path(".../egyptian-handwriting"),
    ...     image_path=Path(".../egyptian-handwriting/data/row_0.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ar'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "egyptian-handwriting"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "egyptian-handwriting_metadata.json"
__l4_integrate__ = "scripts/integrate_egyptian_handwriting_enrichments.py"

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class EgyptianHandwritingParser(BaseParser):
    """Parser for Egyptian Handwriting Dataset.

    Extracts annotations from parquet metadata. Since images are stored
    as binary blobs within the parquet file, this parser provides label
    information for image rows referenced by index.
    """

    def __init__(self) -> None:
        super().__init__()
        self._parquet_cache: dict[str, list[str]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["egyptian-handwriting", "egyptian_handwriting"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Egyptian Handwriting labels for a single image.

        Args:
            dataset_path: Root path of the Egyptian Handwriting dataset
            image_path: Path to the extracted image (expected: row_{idx}.png)
            config: Dataset configuration dictionary

        Returns:
            OriginalLabels with Arabic word label and script metadata
        """
        labels = OriginalLabels()

        # Set language/script for Arabic handwriting
        labels.language_code = "ar"
        labels.script_name = "Arabic"
        labels.iso15924_script_code = "Arab"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "egyptian-handwriting"
        labels.raw_labels["production"] = "handwritten-cursive"
        labels.raw_labels["reading_direction"] = "right-to-left"
        labels.raw_labels["capture_method"] = "scanner_flatbed"
        labels.raw_labels["scope"] = "word"
        labels.raw_labels["writer_count"] = 89
        labels.raw_labels["writer_age_range"] = "6-73"

        # Extract row index from filename (e.g., row_0.png -> 0)
        stem = image_path.stem
        row_idx = self._extract_row_index(stem)

        if row_idx is not None:
            parquet_labels = self._load_parquet_labels(dataset_path)
            if 0 <= row_idx < len(parquet_labels):
                transcription = parquet_labels[row_idx]
                labels.transcription = transcription
                labels.raw_labels["text_content"] = {
                    "full_text": transcription,
                    "source_type": "dataset_provided",
                    "source_format": "parquet_label_column",
                    "extraction_method": "EgyptianHandwritingParser.parse",
                    "extraction_timestamp": None,
                    "is_complete": True,
                    "encoding": "utf-8",
                }
            else:
                logger.debug(
                    "Row index %d out of range for Egyptian HW (%d total)",
                    row_idx,
                    len(parquet_labels),
                )
        else:
            logger.debug("Cannot extract row index from filename: %s", stem)

        return labels

    def _extract_row_index(self, stem: str) -> int | None:
        """Extract numeric row index from image filename.

        Supports patterns: row_0, row_00042, 0, 42, img_0, etc.

        Args:
            stem: Image filename stem (without extension)

        Returns:
            Integer row index, or None if not extractable
        """
        # Try "row_{idx}" pattern
        if stem.startswith("row_"):
            try:
                return int(stem[4:])
            except ValueError:
                pass

        # Try pure numeric
        try:
            return int(stem)
        except ValueError:
            pass

        # Try extracting trailing number after any prefix
        parts = stem.rsplit("_", 1)
        if len(parts) == 2:
            try:
                return int(parts[1])
            except ValueError:
                pass

        return None

    def _load_parquet_labels(self, dataset_path: Path) -> list[str]:
        """Load and cache label column from parquet file.

        Args:
            dataset_path: Root path of the dataset

        Returns:
            List of label strings indexed by row number
        """
        cache_key = str(dataset_path)
        if cache_key in self._parquet_cache:
            return self._parquet_cache[cache_key]

        parquet_path = dataset_path / "data" / "egy_handwriting_dataset_set1.parquet"
        result: list[str] = []

        if not parquet_path.exists():
            logger.warning("Egyptian HW parquet not found: %s", parquet_path)
            self._parquet_cache[cache_key] = result
            return result

        try:
            import pyarrow.parquet as pq

            table = pq.read_table(parquet_path, columns=["label"])
            result = [
                str(v) if v is not None else ""
                for v in table.column("label").to_pylist()
            ]
        except (ImportError, OSError) as exc:
            logger.warning(
                "Failed to load Egyptian HW parquet %s: %s",
                parquet_path,
                exc,
            )

        # Cache even on failure to avoid repeated import/IO errors
        self._parquet_cache[cache_key] = result
        logger.debug("Loaded %d Egyptian HW labels from %s", len(result), parquet_path)
        return result


__all__ = ["EgyptianHandwritingParser"]
