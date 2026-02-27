"""Parser for VJRODa (Vertical Japanese Receipt OCR Dataset) dataset.

VJRODa contains vertical Japanese text images of receipts and administrative
documents. All text in the dataset is vertical orientation. The dataset
includes transcriptions in rw_data_texts.jsonl and URL metadata in
url_list.jsonl.

Dataset Structure:
    vjroda/
        images/                     # PNG images
            00000.png
            00001.png
            ...
        url_list.jsonl              # URL metadata per image ID
        rw_data_texts.jsonl         # Text transcriptions per image ID

url_list.jsonl Format (one JSON object per line):
    {"id": "00000", "url": "https://...", "page": 1, ...}

rw_data_texts.jsonl Format (one JSON object per line):
    {"id": "00000", "text": "...", ...}

Labels:
    - language_code: ja (Japanese)
    - script_name: Japanese
    - iso15924_script_code: Jpan (Japanese)
    - raw_labels: is_vertical, text_orientation, text, page, source_url

Example:
    >>> parser = VjrodaParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/multilingual_scripts/vjroda/images"),
    ...     image_path=Path("/data/multilingual_scripts/vjroda/images/00000.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ja'
    >>> print(labels.raw_labels["is_vertical"])
    True
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "vjroda"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "vjroda_metadata.json"
__l4_integrate__ = "scripts/integrate_vjroda_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class VjrodaParser(BaseParser):
    """Parser for VJRODa (Vertical Japanese Receipt OCR Dataset).

    Extracts text transcriptions and URL metadata from JSONL files.
    All images in the dataset contain vertical Japanese text.
    """

    def __init__(self) -> None:
        """Initialize parser with manifest caches."""
        super().__init__()
        self._url_cache: dict[Path, dict[str, dict[str, Any]]] = {}
        self._text_cache: dict[Path, dict[str, str]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["vjroda", "vj-roda"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse VJRODa labels from JSONL metadata files.

        Args:
            dataset_path: Root path of the VJRODa dataset (images/ dir)
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script codes, and vertical
            text orientation metadata including transcription
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Japanese
        labels.language_code = "ja"
        labels.script_name = "Japanese"
        labels.iso15924_script_code = "Jpan"

        # All VJRODa images are vertical text
        labels.raw_labels["is_vertical"] = True
        labels.raw_labels["text_orientation"] = "vertical"

        # The dataset root (parent of images/) contains the JSONL files
        dataset_root = dataset_path.parent
        image_id = image_path.stem

        # Load URL metadata
        url_data = self._load_url_list(dataset_root)
        if image_id in url_data:
            record = url_data[image_id]
            labels.raw_labels["page"] = record.get("page")
            labels.raw_labels["source_url"] = record.get("url", "")
        else:
            logger.debug("No URL record found for %s in url_list.jsonl", image_id)

        # Load text transcriptions
        text_data = self._load_texts(dataset_root)
        if image_id in text_data:
            transcription = text_data[image_id]
            labels.raw_labels["text"] = transcription
            labels.transcription = transcription
        else:
            logger.debug("No text record found for %s in rw_data_texts.jsonl", image_id)

        return labels

    def _load_url_list(self, dataset_root: Path) -> dict[str, dict[str, Any]]:
        """Load and cache url_list.jsonl, indexed by image ID.

        Args:
            dataset_root: Root path of the VJRODa dataset (parent of images/)

        Returns:
            Dictionary mapping image ID to URL record data
        """
        if dataset_root in self._url_cache:
            return self._url_cache[dataset_root]

        url_data: dict[str, dict[str, Any]] = {}
        url_path = dataset_root / "url_list.jsonl"

        if url_path.exists():
            try:
                with open(url_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        record_id = str(record.get("id", ""))
                        if record_id:
                            url_data[record_id] = record

                logger.debug("Loaded %d records from %s", len(url_data), url_path)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to load url_list.jsonl at %s: %s", url_path, exc)

        self._url_cache[dataset_root] = url_data
        return url_data

    def _load_texts(self, dataset_root: Path) -> dict[str, str]:
        """Load and cache rw_data_texts.jsonl, indexed by image ID.

        Args:
            dataset_root: Root path of the VJRODa dataset (parent of images/)

        Returns:
            Dictionary mapping image ID to transcription text
        """
        if dataset_root in self._text_cache:
            return self._text_cache[dataset_root]

        text_data: dict[str, str] = {}
        text_path = dataset_root / "rw_data_texts.jsonl"

        if text_path.exists():
            try:
                with open(text_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        record_id = str(record.get("id", ""))
                        text = record.get("text", "")
                        if record_id and text:
                            text_data[record_id] = text

                logger.debug(
                    "Loaded %d text records from %s", len(text_data), text_path
                )
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to load rw_data_texts.jsonl at %s: %s",
                    text_path,
                    exc,
                )

        self._text_cache[dataset_root] = text_data
        return text_data

    def supports_batch(self) -> bool:
        """Batch parsing is optimized - JSONL files are loaded once."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads JSONL files once and extracts labels for all images.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        # Pre-load JSONL files
        dataset_root = dataset_path.parent
        self._load_url_list(dataset_root)
        self._load_texts(dataset_root)

        # Parse each image (JSONL data is now cached)
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["VjrodaParser"]
