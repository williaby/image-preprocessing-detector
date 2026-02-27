"""Parser for Hindi OCR Synthetic dataset.

Hindi OCR Synthetic is a synthetically generated dataset of Hindi text images
using various fonts and font sizes. Contains 80K images with ground truth
text stored in a CSV file.

Dataset Structure:
    hindi_ocr_synthetic/
        data_80k/
            data.csv
            output_images/
                1.png
                2.png
                ...
            TestSamples/
                ...

CSV Format:
    image_file,text,font_size,font_file,word_count

Example:
    1.png,गर्भनिरोध के लिए महिलाएं...,51,Lohit-Devanagari.ttf,8

Labels:
    - language_code: hi (Hindi)
    - script_name: Deva (Devanagari)
    - transcription: Ground truth text
    - raw_labels: font_file, font_size, word_count, is_synthetic

Example:
    >>> parser = HindiOcrSyntheticParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/hindi_ocr_synthetic"),
    ...     image_path=Path("/data/hindi_ocr_synthetic/data_80k/output_images/1.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'hi'
    >>> print(labels.raw_labels["font_file"])
    'Lohit-Devanagari.ttf'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "hindi-synth"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "hindi_synth_metadata.json"
__l4_integrate__ = "scripts/integrate_hindi_synth_enrichments.py"


import csv
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class HindiOcrSyntheticParser(BaseParser):
    """Parser for Hindi OCR Synthetic dataset.

    Extracts text and font metadata from CSV annotations for
    synthetically generated Hindi text images.
    """

    def __init__(self) -> None:
        """Initialize parser with CSV cache."""
        super().__init__()
        self._csv_cache: dict[Path, dict[str, dict[str, Any]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["hindi_ocr_synthetic", "hindi-ocr-synthetic"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Hindi OCR Synthetic labels from CSV.

        Args:
            dataset_path: Root path of the dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, transcription,
            and raw_labels containing font and generation metadata
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Hindi/Devanagari
        labels.language_code = "hi"
        labels.script_name = "Devanagari"  # Human-readable name
        labels.iso15924_script_code = "Deva"  # ISO 15924
        labels.raw_labels["is_synthetic"] = True
        labels.raw_labels["content_type"] = "text_line"

        # Load CSV data
        csv_data = self._load_csv(dataset_path)

        # Look up image in CSV
        image_name = image_path.name
        if image_name in csv_data:
            record = csv_data[image_name]
            labels.transcription = record.get("text", "")
            labels.raw_labels["font_file"] = record.get("font_file", "")
            labels.raw_labels["font_size"] = record.get("font_size", 0)
            labels.raw_labels["word_count"] = record.get("word_count", 0)
        else:
            logger.debug(f"No CSV record found for {image_name}")

        return labels

    def _load_csv(self, dataset_path: Path) -> dict[str, dict[str, Any]]:
        """Load and cache CSV data for the dataset.

        Args:
            dataset_path: Root path of the dataset

        Returns:
            Dictionary mapping image filename to record data
        """
        if dataset_path in self._csv_cache:
            return self._csv_cache[dataset_path]

        csv_data: dict[str, dict[str, Any]] = {}

        # Find CSV file
        csv_path = dataset_path / "data_80k" / "data.csv"
        if not csv_path.exists():
            # Try alternative locations
            csv_path = dataset_path / "data.csv"

        if csv_path.exists():
            try:
                with open(csv_path, encoding="utf-8", errors="ignore", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        image_file = row.get("image_file", "")
                        if image_file:
                            csv_data[image_file] = {
                                "text": row.get("text", ""),
                                "font_size": int(row.get("font_size", 0) or 0),
                                "font_file": row.get("font_file", ""),
                                "word_count": int(row.get("word_count", 0) or 0),
                            }
                logger.debug(f"Loaded {len(csv_data)} records from {csv_path}")
            except Exception as e:
                logger.warning(f"Failed to load CSV at {csv_path}: {e}")

        self._csv_cache[dataset_path] = csv_data
        return csv_data


__all__ = ["HindiOcrSyntheticParser"]
