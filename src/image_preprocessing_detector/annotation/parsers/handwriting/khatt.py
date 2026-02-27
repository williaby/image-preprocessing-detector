"""Parser for KHATT Arabic Handwritten Text dataset.

KHATT (KFUPM Handwritten Arabic TexT) contains paragraph-level scans
of Arabic handwriting from 1,000 writers. Images are TIFF (converted
to JPEG), with per-image .txt companion files containing Arabic Unicode
transcriptions.

Dataset Structure (after extraction from HuggingFace ZIPs):
    khatt/
        train/
            *.jpg                   # ~1,400 JPEG paragraph images (converted from TIF)
            *.txt                   # NOT present after extraction (text in TSV only)
        validation/
            *.jpg                   # ~233 JPEG paragraph images
        khatt_groundtruth.tsv       # TSV: image_path, split, image_stem, arabic_text
        Groundtruth-Unicode.xlsx    # Original Excel ground truth

Filename Convention:
    {writerID}_Para{paraNum}_{segment}.jpg
    e.g.: AHTD3A0001_Para2_3.jpg
          ^^^^^^^^^  writer ID (first 9 chars, unique per writer)
                      ^^^^^^ paragraph number
                               ^ segment within paragraph

Labels Extracted:
    - language_code: "ar" (Arabic)
    - script_name: "Arabic"
    - iso15924_script_code: "Arab"
    - transcription: Arabic text from TSV ground truth
    - writer_id: extracted from filename
    - text_direction: right-to-left

Conversion Notes:
    - Original TIFF images converted to JPEG quality 90 on extraction
    - Transcriptions sourced from khatt_groundtruth.tsv (per-image TSV)
    - Falls back to companion .txt file if present (original ZIP structure)

Example:
    >>> parser = KHATTParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/image_detection/01_base_data/handwriting/khatt"),
    ...     image_path=Path(".../khatt/train/AHTD3A0001_Para2_3.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ar'
    >>> print(labels.transcription[:30])
    'من العذاب في الآخرة، وأفضل ما'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "khatt"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "khatt_metadata.json"
__l4_integrate__ = "scripts/integrate_khatt_enrichments.py"


import csv
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Filename pattern: AHTD3A0001_Para2_3  (writer_Para_segment)
_KHATT_STEM_RE = re.compile(
    r"^(?P<writer_id>[A-Z0-9]+)_Para(?P<para_num>\d+)_(?P<segment>\d+)$",
    re.IGNORECASE,
)


class KHATTParser(BaseParser):
    """Parser for KHATT Arabic Handwritten Text dataset.

    Extracts annotations from:
    1. ``khatt_groundtruth.tsv`` — TSV with Arabic Unicode transcriptions per image
    2. Companion ``.txt`` file (fallback, only present in original ZIP structure)
    3. Filename parsing for writer_id and paragraph metadata
    """

    def __init__(self) -> None:
        super().__init__()
        # Lazy-loaded TSV index: {stem -> arabic_text}
        self._tsv_cache: dict[str, dict[str, dict[str, str]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["khatt", "khatt-arabic"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse KHATT labels from TSV ground truth and filename metadata.

        Args:
            dataset_path: Root path of the KHATT dataset
            image_path: Absolute path to the JPEG image being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with Arabic text, language/script metadata,
            writer identity, and paragraph coordinates
        """
        labels = OriginalLabels()

        # Set language/script for Arabic handwriting
        labels.language_code = "ar"
        labels.script_name = "Arabic"
        labels.iso15924_script_code = "Arab"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "khatt"
        labels.raw_labels["production"] = "handwritten-cursive"
        labels.raw_labels["reading_direction"] = "right-to-left"
        labels.raw_labels["capture_method"] = "scanner_flatbed"

        # Parse filename metadata
        stem = image_path.stem
        m = _KHATT_STEM_RE.match(stem)
        if m:
            writer_id = m.group("writer_id")
            para_num = int(m.group("para_num"))
            segment = int(m.group("segment"))
            labels.raw_labels["writer_id"] = writer_id
            labels.raw_labels["para_num"] = para_num
            labels.raw_labels["segment"] = segment
        else:
            logger.debug("KHATT filename does not match expected pattern: %s", stem)

        # Load transcription from TSV
        tsv_data = self._load_tsv(dataset_path)
        if stem in tsv_data:
            transcription = tsv_data[stem].get("arabic_text", "")
            if transcription:
                labels.transcription = transcription
                labels.raw_labels["text_content"] = {
                    "full_text": transcription,
                    "source_type": "dataset_provided",
                    "source_format": "tsv_groundtruth",
                    "extraction_method": "KHATTParser.parse",
                    "extraction_timestamp": None,
                    "is_complete": True,
                    "encoding": "utf-8",
                }
        else:
            # Fallback: companion .txt file (if present — original ZIP structure)
            fallback_text = self._load_companion_txt(dataset_path, image_path)
            if fallback_text:
                labels.transcription = fallback_text
                labels.raw_labels["text_content"] = {
                    "full_text": fallback_text,
                    "source_type": "dataset_provided",
                    "source_format": "companion_txt",
                    "extraction_method": "KHATTParser._load_companion_txt",
                    "extraction_timestamp": None,
                    "is_complete": True,
                    "encoding": "utf-8",
                }
            else:
                logger.debug("No transcription found for KHATT image: %s", stem)

        return labels

    def _load_tsv(self, dataset_path: Path) -> dict[str, dict[str, str]]:
        """Load and cache the khatt_groundtruth.tsv index.

        Args:
            dataset_path: Root path of KHATT dataset

        Returns:
            Dict mapping image_stem -> {"arabic_text": "...", "split": "..."}
        """
        cache_key = str(dataset_path)
        if cache_key in self._tsv_cache:
            return self._tsv_cache[cache_key]

        tsv_path = dataset_path / "khatt_groundtruth.tsv"
        if not tsv_path.exists():
            logger.warning("KHATT ground truth TSV not found: %s", tsv_path)
            empty: dict[str, dict[str, str]] = {}
            self._tsv_cache[cache_key] = empty
            return empty

        index: dict[str, dict[str, str]] = {}
        try:
            with open(tsv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    stem = Path(row.get("image_path", "")).stem
                    if stem:
                        index[stem] = {
                            "arabic_text": row.get("arabic_text", ""),
                            "split": row.get("split", ""),
                        }
        except (OSError, csv.Error) as exc:
            logger.warning("Failed to load KHATT TSV %s: %s", tsv_path, exc)

        self._tsv_cache[cache_key] = index
        logger.debug("Loaded %d KHATT TSV entries from %s", len(index), tsv_path)
        return index

    def _load_companion_txt(
        self,
        dataset_path: Path,
        image_path: Path,
    ) -> str | None:
        """Load Arabic transcription from companion .txt file (fallback).

        Args:
            dataset_path: Root path of KHATT dataset
            image_path: Path to the JPEG image

        Returns:
            Arabic text string, or None if not found
        """
        # Try .txt sibling of the .jpg
        txt_path: Path = image_path.with_suffix(".txt")
        if txt_path.exists():
            try:
                return txt_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.debug("Failed to read companion txt %s: %s", txt_path, exc)
                return None

        # Try searching relative to dataset_path
        found = self._find_annotation_file(
            dataset_path,
            [f"**/{image_path.stem}.txt"],
        )
        if found and found.exists():
            try:
                return found.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.debug("Failed to read companion txt %s: %s", found, exc)

        return None


__all__ = ["KHATTParser"]
