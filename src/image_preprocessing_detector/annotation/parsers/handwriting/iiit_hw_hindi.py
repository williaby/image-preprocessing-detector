"""Parser for IIIT-HW-Hindi (IIIT Handwritten Hindi Words) dataset.

IIIT-HW-Hindi provides 95,430 word-level images of Hindi handwriting
in Devanagari script, from CVIT (Centre for Visual Information Technology)
at IIIT Hyderabad.

The full dataset is hosted on HuggingFace as Parquet files
(c3rl/IIIT-INDIC-HW-WORDS-Hindi). Locally, images are extracted from
Parquet and saved as JPEG with a companion TSV ground truth file.

Dataset Structure (locally extracted):
    iiit-hw-hindi/
        iiit_hw_hindi_test_00000.jpg    # ~300 test images
        iiit_hw_hindi_test_00001.jpg
        ...
        iiit_hw_hindi_train_00000.jpg   # ~100 train images
        iiit_hw_hindi_train_00001.jpg
        ...
        iiit_hw_hindi_groundtruth.tsv   # TSV: image_path, split, filename, hindi_text

Full dataset (HuggingFace streaming):
    c3rl/IIIT-INDIC-HW-WORDS-Hindi
    Splits: train (69,900) / validation (12,700) / test (12,900)
    Format: Parquet with 'image' (PIL.Image) and 'text' (str) fields

Filename Convention (locally extracted):
    iiit_hw_hindi_{split}_{index:05d}.jpg
    e.g.: iiit_hw_hindi_test_00042.jpg

Labels Extracted:
    - language_code: "hi" (Hindi)
    - script_name: "Devanagari"
    - iso15924_script_code: "Deva"
    - transcription: Devanagari Unicode word text
    - split: "train" / "validation" / "test"

Example:
    >>> parser = IIITHWHindiParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path(
    ...         "/mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi"
    ...     ),
    ...     image_path=Path(".../iiit_hw_hindi_test_00000.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'hi'
    >>> print(labels.transcription)
    'अनाथों'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "iiit-hw-hindi"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "iiit-hw-hindi_metadata.json"
__l4_integrate__ = "scripts/integrate_iiit_hw_hindi_enrichments.py"


import csv
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Filename pattern: iiit_hw_hindi_{split}_{index:05d}.jpg
_IIIT_STEM_RE = re.compile(
    r"^iiit_hw_hindi_(?P<split>train|validation|test)_(?P<index>\d+)$",
    re.IGNORECASE,
)


class IIITHWHindiParser(BaseParser):
    """Parser for IIIT-HW-Hindi word-level Devanagari handwriting dataset.

    Extracts annotations from:
    1. ``iiit_hw_hindi_groundtruth.tsv`` — TSV with Hindi Unicode transcriptions
    2. Filename parsing for split assignment and index

    The full dataset is available via HuggingFace streaming; only a subset
    is typically extracted locally. The parser handles both the locally-extracted
    JPEG files and gracefully degrades if the TSV is unavailable.
    """

    def __init__(self) -> None:
        super().__init__()
        # Lazy-loaded TSV index: {filename -> {"hindi_text": ..., "split": ...}}
        self._tsv_cache: dict[str, dict[str, dict[str, str]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["iiit-hw-hindi", "iiit_hw_hindi", "iiit-indic-hw-hindi"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse IIIT-HW-Hindi labels from TSV ground truth and filename metadata.

        Args:
            dataset_path: Root path of the locally-extracted IIIT-HW-Hindi dataset
            image_path: Absolute path to the JPEG image being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with Hindi text, language/script metadata, and split info
        """
        labels = OriginalLabels()

        # Set language/script for Hindi/Devanagari handwriting
        labels.language_code = "hi"
        labels.script_name = "Devanagari"
        labels.iso15924_script_code = "Deva"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "iiit-hw-hindi"
        labels.raw_labels["production"] = "handwritten-cursive"
        labels.raw_labels["reading_direction"] = "left-to-right"
        labels.raw_labels["granularity"] = "word-level"

        # Parse filename for split and index
        stem = image_path.stem
        m = _IIIT_STEM_RE.match(stem)
        if m:
            split = m.group("split")
            index = int(m.group("index"))
            labels.raw_labels["split"] = split
            labels.raw_labels["index"] = index
        else:
            logger.debug(
                "IIIT-HW-Hindi filename does not match expected pattern: %s", stem
            )

        # Load transcription from TSV
        tsv_data = self._load_tsv(dataset_path)
        fname = image_path.name
        if fname in tsv_data:
            hindi_text = tsv_data[fname].get("hindi_text", "")
            if hindi_text:
                labels.transcription = hindi_text
                labels.raw_labels["text_content"] = {
                    "full_text": hindi_text,
                    "source_type": "dataset_provided",
                    "source_format": "tsv_groundtruth",
                    "extraction_method": "IIITHWHindiParser.parse",
                    "extraction_timestamp": None,
                    "is_complete": True,
                    "encoding": "utf-8",
                }
        else:
            logger.debug(
                "No transcription found in TSV for IIIT-HW-Hindi image: %s", fname
            )

        return labels

    def _load_tsv(self, dataset_path: Path) -> dict[str, dict[str, str]]:
        """Load and cache the iiit_hw_hindi_groundtruth.tsv index.

        Args:
            dataset_path: Root path of locally-extracted IIIT-HW-Hindi data

        Returns:
            Dict mapping filename -> {"hindi_text": "...", "split": "..."}
        """
        cache_key = str(dataset_path)
        if cache_key in self._tsv_cache:
            return self._tsv_cache[cache_key]

        tsv_path = dataset_path / "iiit_hw_hindi_groundtruth.tsv"
        if not tsv_path.exists():
            logger.warning("IIIT-HW-Hindi ground truth TSV not found: %s", tsv_path)
            self._tsv_cache[cache_key] = {}
            return {}

        index: dict[str, dict[str, str]] = {}
        try:
            with open(tsv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    filename = row.get("filename", "")
                    if filename:
                        index[filename] = {
                            "hindi_text": row.get("hindi_text", ""),
                            "split": row.get("split", ""),
                        }
        except (OSError, csv.Error) as exc:
            logger.warning("Failed to load IIIT-HW-Hindi TSV %s: %s", tsv_path, exc)

        self._tsv_cache[cache_key] = index
        logger.debug(
            "Loaded %d IIIT-HW-Hindi TSV entries from %s", len(index), tsv_path
        )
        return index


__all__ = ["IIITHWHindiParser"]
