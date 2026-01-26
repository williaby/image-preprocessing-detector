# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Arabic Documents OCR dataset.

Arabic Documents OCR contains scanned Arabic documents across
12 different categories/document types.

Dataset Structure:
    arabic_docs_ocr/
        Documents/
            {category}/
                *.jpg

12 Categories:
    Various document types (invoices, forms, letters, etc.)

Extracts:
    - language_code: Fixed "ar" (Arabic)
    - script_name: Fixed "Arabic"
    - document_type: Category from directory
    - raw_labels: category, iso15924_script

Example:
    >>> parser = ArabicDocsParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/arabic_docs_ocr"),
    ...     image_path=Path("/data/arabic_docs_ocr/Documents/invoice/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    ar
    >>> print(labels.document_type)
    Invoice
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class ArabicDocsParser(BaseParser):
    """Parser for Arabic Documents OCR dataset.

    Extracts document category from directory structure.
    Fixed Arabic language/script.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["arabic_docs_ocr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Arabic Documents labels from directory structure.

        Args:
            dataset_path: Root path of the arabic_docs_ocr dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code="ar", script_name="Arabic",
            and document category
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Arabic script (ISO 15924: Arab, ISO 639: ar)
        labels.language_code = "ar"
        labels.script_name = "Arabic"
        labels.raw_labels["iso15924_script"] = "Arab"

        # Extract category from parent directory
        path_parts = image_path.parts
        for i, part in enumerate(path_parts):
            if part == "Documents" and i + 1 < len(path_parts):
                category = path_parts[i + 1]
                labels.raw_labels["category"] = category
                labels.raw_labels["document_type"] = category
                break

        return labels


__all__ = ["ArabicDocsParser"]
