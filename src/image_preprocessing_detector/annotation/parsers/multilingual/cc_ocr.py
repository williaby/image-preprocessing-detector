"""Parser for CC-OCR benchmark dataset.

CC-OCR (Comprehensive OCR Benchmark) is a large-scale OCR benchmark
covering multiple tracks including multi-scene text, multilingual text,
document parsing, and key information extraction.

Dataset Structure:
    CC-OCR/
        {track}/
            {subset}/
                images/
                    *.png
                annotations/
                    *.json

Tracks:
    - Multi-Scene Text: Scene text recognition
    - Multilingual Text: Chinese character OCR
    - Document Parsing: Document structure analysis
    - Key Info Extraction: Form/invoice data extraction

Extracts:
    - language_code: Language from JSON annotations
    - transcription: Ground truth text
    - raw_labels: track, subset, scene_type, full annotation

Example:
    >>> parser = CcOcrParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/cc-ocr"),
    ...     image_path=Path("/data/cc-ocr/multilingual_text/subset1/images/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    zh
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "cc-ocr"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "cc_ocr_metadata.json"
__l4_integrate__ = "scripts/integrate_cc_ocr_enrichments.py"


import csv
import logging
import sys
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class CcOcrParser(BaseParser):
    """Parser for CC-OCR benchmark dataset.

    Extracts track, subset, and language/text annotations from
    directory structure and JSON annotation files.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["cc_ocr"]

    def _resolve_tsv_path(self, dataset_path: Path, image_path: Path) -> Path | None:
        """Resolve TSV file path from extracted image path.

        Path mapping:
            Image: .../extracted_images/doc_parsing/doc/doc_scan_chn_75/0.jpg
            TSV:   .../doc_parsing/doc/doc_scan_chn_75.tsv

        The dataset_path points to extracted_images/, so we go up one level
        to find the TSV files in the sibling track directories.

        Args:
            dataset_path (Path): Root path of the CC-OCR extracted_images directory
            image_path (Path): Absolute path to the image file being processed

        Returns:
            Path | None: Path to TSV file, or None if not found
        """
        # Extract path components
        parts = image_path.parts

        # Find 'extracted_images' in path
        try:
            extracted_idx = parts.index("extracted_images")
        except ValueError:
            logger.debug(f"'extracted_images' not in path: {image_path}")
            return None

        # Get track, category, subset from path after 'extracted_images'
        # Example: extracted_images/doc_parsing/doc/doc_scan_chn_75/0.jpg
        if extracted_idx + 3 >= len(parts):
            logger.debug(f"Path too short after extracted_images: {image_path}")
            return None

        track = parts[extracted_idx + 1]  # "doc_parsing"
        category = parts[extracted_idx + 2]  # "doc"
        subset = parts[extracted_idx + 3]  # "doc_scan_chn_75"

        # Build TSV path - go up from extracted_images to CC-OCR root
        # dataset_path = .../CC-OCR/extracted_images
        # TSV is at .../CC-OCR/doc_parsing/doc/doc_scan_chn_75.tsv
        cc_ocr_root = dataset_path.parent  # Go up from extracted_images to CC-OCR
        tsv_path = cc_ocr_root / track / category / f"{subset}.tsv"

        if not tsv_path.exists():
            logger.debug(f"TSV not found at: {tsv_path}")
            return None

        return tsv_path

    def _load_tsv_annotations(self, tsv_path: Path) -> dict[str, dict[str, str]]:
        """Load TSV file and index by image_name.

        Args:
            tsv_path (Path): Path to TSV file

        Returns:
            dict[str, dict[str, str]]: Dict mapping image_name to row dict

        Note:
            Sets csv.field_size_limit to handle base64-encoded images
        """
        # Increase field size limit for base64 image column
        csv.field_size_limit(sys.maxsize)

        annotations = {}

        try:
            with open(tsv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t", quotechar='"')
                for row in reader:
                    image_name = row.get("image_name")
                    if image_name:
                        annotations[image_name] = row
        except Exception:
            logger.exception(f"Failed to load TSV {tsv_path}")
            return {}

        return annotations

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse CC-OCR labels from directory and JSON annotations.

        Args:
            dataset_path (Path): Root path of the CC-OCR dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with language_code, transcription, and track
            information populated
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Default to Chinese for CC-OCR (Simplified Chinese)
        labels.language_code = "zh"
        labels.script_name = "Chinese"  # Human-readable name
        labels.iso15924_script_code = "Hans"  # ISO 15924

        # Parse track and subset from path
        path_parts = image_path.parts

        for part in path_parts:
            # Look for track patterns
            if (
                "scene" in part.lower()
                or "multilingual" in part.lower()
                or "document" in part.lower()
                or "parsing" in part.lower()
                or "extraction" in part.lower()
                or "key" in part.lower()
            ):
                labels.raw_labels["track"] = part

        # Load TSV annotations
        tsv_path = self._resolve_tsv_path(dataset_path, image_path)
        if tsv_path:
            annotations = self._load_tsv_annotations(tsv_path)
            image_name = image_path.name

            if image_name in annotations:
                row = annotations[image_name]

                # Extract ground truth text from 'answer' column
                if row.get("answer"):
                    labels.transcription = row["answer"]

                # Store additional TSV fields in raw_labels
                # TSV is in CC-OCR root (parent of extracted_images)
                cc_ocr_root = dataset_path.parent
                labels.raw_labels.update(
                    {
                        "tsv_file": str(tsv_path.relative_to(cc_ocr_root)),
                        "category": row.get("category", ""),
                        "l2_category": row.get("l2-category", ""),
                        "split": row.get("split", ""),
                        "question": row.get("question", ""),
                    }
                )

                # Detect language from subset name (eng vs chn)
                subset_name = tsv_path.stem  # "doc_scan_chn_75"
                if "eng" in subset_name.lower():
                    labels.language_code = "en"
                    labels.script_name = "English"
                    labels.iso15924_script_code = "Latn"
                elif "chn" in subset_name.lower() or "chi" in subset_name.lower():
                    labels.language_code = "zh"
                    labels.script_name = "Chinese"
                    labels.iso15924_script_code = "Hans"
                # else: keep default 'zh' from lines 85-88
            else:
                logger.warning(f"Image {image_name} not found in TSV {tsv_path}")
        else:
            logger.debug(f"No TSV file found for image {image_path}")

        return labels


__all__ = ["CcOcrParser"]
