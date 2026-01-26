# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for OHR-Bench dataset.

OHR-Bench (OCR Hallucination Recognition Benchmark) provides document images
across 16 categories for evaluating OCR hallucination detection.

Dataset Structure:
    ohr_bench/
        {category}/
            *.jpg

16 Document Categories:
    - academic: Research papers and academic documents
    - book: Book pages and chapters
    - exam: Examination papers and tests
    - finance: Financial reports and statements
    - form: Forms and questionnaires
    - handwritten: Handwritten notes and documents
    - legal: Legal documents and contracts
    - magazine: Magazine articles and layouts
    - medical: Medical records and prescriptions
    - newspaper: Newspaper articles and pages
    - note: Notes and memos
    - poster: Posters and flyers
    - receipt: Receipts and invoices
    - research: Research papers and publications
    - resume: Resumes and CVs
    - slide: Presentation slides

Note: Arrow format dataset - labels may come from extraction metadata.

Example:
    >>> parser = OhrBenchParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/ohr_bench"),
    ...     image_path=Path("/data/ohr_bench/finance/report_001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["category"])
    "finance"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class OhrBenchParser(BaseParser):
    """Parser for OHR-Bench OCR hallucination benchmark dataset.

    Extracts document category from filename or parent directory structure.
    """

    # OHR-Bench document categories (16 categories)
    OHR_CATEGORIES = {
        "academic",
        "book",
        "exam",
        "finance",
        "form",
        "handwritten",
        "legal",
        "magazine",
        "medical",
        "newspaper",
        "note",
        "poster",
        "receipt",
        "research",
        "resume",
        "slide",
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["ohr-bench", "ohr_bench"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse OHR-Bench labels from filename or directory structure.

        Args:
            dataset_path: Root path of the OHR-Bench dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with category in raw_labels and document_type set
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Try to extract category from filename or parent directory
        filename = image_path.stem
        parent = image_path.parent.name

        for cat in self.OHR_CATEGORIES:
            if cat in filename.lower() or cat in parent.lower():
                labels.raw_labels["category"] = cat
                # Set document_type for downstream compatibility
                labels.raw_labels["document_type"] = cat.title()
                break

        return labels


__all__ = ["OhrBenchParser"]
