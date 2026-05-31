"""Parser for PDM OCR (Pre-modern Digital Manuscripts OCR) dataset.

PDM OCR contains scanned Japanese historical documents from the National
Diet Library digitization project. The dataset is split into two parts
(pdmocr-part1 and pdmocr-part2) sharing the same format. Metadata is
provided in info.csv with bibliographic details per PID.

Dataset Structure:
    pdmocr-part1/                   (or pdmocr-part2/)
        images/                     # PNG page images
            PID_page.png
            ...
        info.csv                    # Bibliographic metadata per PID

info.csv Format (header row):
    PID,DatasetID,Title,Publisher,PublicationYear,NDCClassification,...

DatasetID Convention:
    tosho_{decade}_{category}  (e.g., "tosho_1870_bunkei")

Labels:
    - language_code: ja (Japanese)
    - script_name: Japanese
    - iso15924_script_code: Jpan (Japanese)
    - raw_labels: pid, decade, dataset_id, title, publisher,
                  publication_year, ndc_classification

Example:
    >>> parser = PdmocrParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/pdmocr-part1/images"),
    ...     image_path=Path("/data/pdmocr-part1/images/12345_001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ja'
    >>> print(labels.raw_labels["decade"])
    '1870'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "pdmocr-part1"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "pdmocr-part1_metadata.json"
__l4_integrate__ = "scripts/integrate_pdmocr_enrichments.py"


import csv
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Pattern to extract decade from DatasetID (e.g., "tosho_1870_bunkei" -> "1870")
_DECADE_RE = re.compile(r"(\d{4})")


class PdmocrParser(BaseParser):
    """Parser for PDM OCR (Pre-modern Digital Manuscripts OCR) dataset.

    Extracts bibliographic metadata from info.csv. Shared by both
    pdmocr-part1 and pdmocr-part2 datasets.
    """

    def __init__(self) -> None:
        super().__init__()
        self._csv_cache: dict[Path, dict[str, dict[str, str]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["pdmocr-part1", "pdmocr-part2", "pdmocr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse PDM OCR labels from info.csv metadata.

        Args:
            dataset_path (Path): Root path of the PDM OCR images directory
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with language/script metadata and bibliographic
            information from info.csv
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Japanese
        labels.language_code = "ja"
        labels.script_name = "Japanese"
        labels.iso15924_script_code = "Jpan"

        # Extract PID from filename (format: PID_page.png or just PID.png)
        pid = self._extract_pid(image_path)
        labels.raw_labels["pid"] = pid

        # Load CSV metadata from dataset root parent
        dataset_root = dataset_path.parent
        csv_data = self._load_info_csv(dataset_root)

        if pid and pid in csv_data:
            record = csv_data[pid]
            dataset_id = record.get("DatasetID", "")
            labels.raw_labels["dataset_id"] = dataset_id
            labels.raw_labels["title"] = record.get("Title", "")
            labels.raw_labels["publisher"] = record.get("Publisher", "")
            labels.raw_labels["publication_year"] = record.get("PublicationYear", "")
            labels.raw_labels["ndc_classification"] = record.get(
                "NDCClassification", ""
            )

            # Extract decade from DatasetID
            decade = self._extract_decade(dataset_id)
            labels.raw_labels["decade"] = decade
        else:
            logger.debug(
                "No info.csv record found for PID '%s' (image: %s)",
                pid,
                image_path.name,
            )

        return labels

    def _extract_pid(self, image_path: Path) -> str:
        """Extract PID from image filename.

        Handles formats like "PID_page.png" by taking the first
        underscore-delimited segment, or the full stem if no underscore.

        Args:
            image_path (Path): Path to the image file

        Returns:
            str: PID string extracted from filename
        """
        stem = image_path.stem
        # PID is typically the first part before underscore
        parts = stem.split("_")
        if len(parts) >= 2:
            return parts[0]
        return stem

    def _extract_decade(self, dataset_id: str) -> str:
        """Extract decade from DatasetID field.

        Args:
            dataset_id (str): DatasetID string (e.g., "tosho_1870_bunkei")

        Returns:
            str: Decade string (e.g., "1870") or empty string if not found
        """
        match = _DECADE_RE.search(dataset_id)
        if match:
            return match.group(1)
        return ""

    def _load_info_csv(self, dataset_root: Path) -> dict[str, dict[str, str]]:
        """Load and cache info.csv, indexed by PID.

        Args:
            dataset_root (Path): Root path of the PDM OCR dataset (parent of images/)

        Returns:
            dict[str, dict[str, str]]: Dictionary mapping PID to row data
        """
        if dataset_root in self._csv_cache:
            return self._csv_cache[dataset_root]

        csv_data: dict[str, dict[str, str]] = {}
        csv_path = dataset_root / "info.csv"

        if csv_path.exists():
            try:
                with open(csv_path, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pid = row.get("PID", "")
                        if pid:
                            csv_data[pid] = dict(row)

                logger.debug("Loaded %d records from %s", len(csv_data), csv_path)
            except (OSError, csv.Error) as exc:
                logger.warning("Failed to load info.csv at %s: %s", csv_path, exc)

        self._csv_cache[dataset_root] = csv_data
        return csv_data

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

        Loads info.csv once and extracts labels for all images.

        Args:
            dataset_path (Path): Root path of the dataset
            image_paths (list[Path]): List of absolute paths to image files
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            list[OriginalLabels]: List of OriginalLabels in same order as image_paths
        """
        # Pre-load CSV
        dataset_root = dataset_path.parent
        self._load_info_csv(dataset_root)

        # Parse each image (CSV is now cached)
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["PdmocrParser"]
