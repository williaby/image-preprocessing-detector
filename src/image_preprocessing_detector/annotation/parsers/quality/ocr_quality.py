# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for OCR-Quality dataset.

OCR-Quality provides human quality scores (1-4 scale, where 1=best - inverted!)
for OCR readability assessment. Labels can be stored in either Parquet or JSON
format with OCR text snippets and source information.

Dataset Structure:
    OCR-Quality/
        OCR-Quality.parquet    (preferred)
        OCR-Quality.json       (fallback)

Parquet/JSON Schema:
    - image_path: Path to the image file
    - human_score: Quality score (1-4, where 1=best - INVERTED!)
    - source: Source of the quality annotation
    - ocr_text: Associated OCR text content

Note:
    The human_score scale is INVERTED: 1 is the best quality, 4 is the worst.
    This is different from DIQA/SmartDoc where higher scores mean better quality.

Example:
    >>> parser = OcrQualityParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/ocr-quality"),
    ...     image_path=Path("/data/ocr-quality/images/doc001.png"),
    ...     config={},
    ... )
    >>> print(labels.ocr_quality_score)
    1  # Best quality
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "ocr-quality"
__l4_workstream__ = "WS3"
__l4_task__ = "quality"
__l4_l2_file__ = "ocr_quality_metadata.json"
__l4_integrate__ = "scripts/integrate_ocr_quality_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class OcrQualityParser(BaseParser):
    """Parser for OCR-Quality dataset.

    Extracts human quality scores (1-4 scale, inverted) from Parquet or JSON
    files. Truncates OCR text to 500 characters to save storage.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["ocr_quality"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse OCR-Quality labels from Parquet or JSON file.

        Args:
            dataset_path: Root path of the OCR-Quality dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with ocr_quality_score, ocr_quality_source,
            and ocr_quality_text populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Load from JSON or Parquet (prefer Parquet)
        json_path = dataset_path / "OCR-Quality.json"
        parquet_path = dataset_path / "OCR-Quality.parquet"

        # Try Parquet first (more efficient)
        if parquet_path.exists():
            try:
                import pyarrow.parquet as pq

                table = pq.read_table(parquet_path)
                df = table.to_pandas()
                # Find matching row by image name
                img_name = image_path.stem
                match = df[df["image_path"].str.contains(img_name, na=False)]
                if not match.empty:
                    row = match.iloc[0]
                    labels.ocr_quality_score = int(row.get("human_score", 0))
                    labels.ocr_quality_source = str(row.get("source", ""))
                    labels.ocr_quality_text = str(row.get("ocr_text", ""))[
                        :500
                    ]  # Truncate
            except Exception as e:
                logger.debug(f"Failed to parse OCR-Quality labels from Parquet: {e}")

        # Fallback to JSON if Parquet not available
        elif json_path.exists():
            try:
                with open(json_path) as f:
                    data = json.load(f)
                    img_name = image_path.stem
                    for record in data:
                        if img_name in record.get("image_path", ""):
                            labels.ocr_quality_score = int(record.get("human_score", 0))
                            labels.ocr_quality_source = str(record.get("source", ""))
                            labels.ocr_quality_text = str(record.get("ocr_text", ""))[
                                :500
                            ]
                            break
            except Exception as e:
                logger.debug(f"Failed to parse OCR-Quality labels from JSON: {e}")

        return labels


__all__ = ["OcrQualityParser"]
