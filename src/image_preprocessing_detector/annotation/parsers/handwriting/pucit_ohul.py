"""Parser for PUCIT-OHUL Urdu handwriting dataset.

PUCIT-OHUL (Punjab University Center for IT - Offline Handwritten Urdu Lines)
is an Urdu line-level handwriting dataset with ground truth transcriptions
stored in Excel files.

Dataset Structure:
    Pucit/
        train_labels_v2.xlsx    - Training labels with transcriptions
        test_labels_v2.xlsx     - Testing labels with transcriptions
        train_lines/            - Training line images
            *.png
        test_lines/             - Testing line images
            *.png

Excel Format:
    Columns: [image_name, transcription, writer_id (optional)]

Language:
    - Language: Urdu (ISO 639: ur)
    - Script: Arabic (Urdu uses Arabic script with additional letters)

Note:
    Excel parsing requires openpyxl. Falls back to path-based inference
    if Excel reading fails.

Example:
    >>> parser = PucitOhulParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/Pucit"),
    ...     image_path=Path("/data/Pucit/train_lines/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ur'
    >>> print(labels.script_name)
    'Arabic'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "pucit-ohul"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "pucit_ohul_metadata.json"
__l4_integrate__ = "scripts/integrate_pucit_ohul_enrichments.py"


import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class PucitOhulParser(BaseParser):
    """Parser for PUCIT-OHUL Urdu handwriting dataset.

    Extracts Urdu line transcriptions from Excel files and metadata
    from directory structure:
    - Language/script identification (Urdu/Arabic)
    - Split (train/test)
    - Transcription text
    - Writer ID (if available)

    Excel data is cached on first access per file to avoid reopening
    the XLSX for every image (O(1) lookup instead of O(n) per image).
    """

    def __init__(self) -> None:
        """Initialize parser with Excel label cache."""
        super().__init__()
        # Cache: excel_path -> {image_stem: (transcription, writer_id)}
        self._label_cache: dict[Path, dict[str, tuple[str | None, str | None]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["pucit-ohul", "pucit_ohul", "pucit"]

    def _load_excel_labels(
        self, excel_file: Path
    ) -> dict[str, tuple[str | None, str | None]]:
        """Load and cache all labels from an Excel file.

        Args:
            excel_file: Path to the XLSX label file.

        Returns:
            Dict mapping image stem to (transcription, writer_id) tuple.
        """
        if excel_file in self._label_cache:
            return self._label_cache[excel_file]

        label_map: dict[str, tuple[str | None, str | None]] = {}
        try:
            import openpyxl

            wb = openpyxl.load_workbook(excel_file, read_only=True)
            ws = wb.active

            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 2 and row[0] is not None:
                    image_key = str(row[0])
                    transcription = str(row[1]) if row[1] else None
                    writer_id = str(row[2]) if len(row) >= 3 and row[2] else None
                    label_map[image_key] = (transcription, writer_id)

            wb.close()
            logger.debug("Loaded %d labels from %s", len(label_map), excel_file.name)
        except ImportError:
            logger.debug("openpyxl not available for PUCIT-OHUL label parsing")
        except Exception:
            logger.debug("Failed to parse PUCIT-OHUL labels from %s", excel_file)

        self._label_cache[excel_file] = label_map
        return label_map

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse PUCIT-OHUL labels from cached Excel data.

        Args:
            dataset_path: Root path of the PUCIT-OHUL dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, transcription,
            writer_id, and raw_labels containing split
        """
        labels = OriginalLabels()

        # Set language/script based on dataset (known from dataset metadata)
        labels.language_code = "ur"  # Urdu
        labels.script_name = "Arabic"  # Human-readable name
        labels.iso15924_script_code = "Arab"  # ISO 15924 (Urdu uses Arabic script)

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Determine split from path
        path_str = str(image_path)
        split = None
        if "train_lines" in path_str or "/train/" in path_str:
            split = "train"
        elif "test_lines" in path_str or "/test/" in path_str:
            split = "test"

        if split:
            labels.raw_labels["split"] = split

        # Find Pucit directory with Excel files
        pucit_path = None
        for parent in image_path.parents:
            if (parent / "train_labels_v2.xlsx").exists():
                pucit_path = parent
                break
            if (parent / "Pucit" / "train_labels_v2.xlsx").exists():
                pucit_path = parent / "Pucit"
                break

        if pucit_path and split:
            excel_file = pucit_path / f"{split}_labels_v2.xlsx"
            if excel_file.exists():
                label_map = self._load_excel_labels(excel_file)
                image_stem = image_path.stem
                image_name = image_path.name

                # O(1) dict lookup instead of iterating all rows
                match = label_map.get(image_stem) or label_map.get(image_name)
                if match:
                    transcription, writer_id = match
                    if transcription:
                        labels.transcription = transcription
                    if writer_id:
                        labels.writer_id = writer_id

        return labels


__all__ = ["PucitOhulParser"]
