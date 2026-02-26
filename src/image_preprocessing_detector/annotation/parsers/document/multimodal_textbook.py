# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Multimodal Textbook dataset.

Multimodal Textbook provides textbook page images with diverse content including
text, figures, diagrams, formulas, and tables. Designed for multimodal document
understanding tasks.

Dataset Structure:
    multimodal_textbook/
        example_data/
            sample_100_images/
                *.jpg

Content Types:
    - Text (paragraphs, headers)
    - Figures (diagrams, charts, photos)
    - Mathematical formulas
    - Tables
    - Captions and annotations

Domain:
    Educational content (textbooks, educational materials)

Example:
    >>> parser = MultimodalTextbookParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/multimodal_textbook"),
    ...     image_path=Path(
    ...         "/data/multimodal_textbook/example_data/sample_100_images/page_001.jpg"
    ...     ),
    ...     config={},
    ... )
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "multimodal-textbook"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "multimodal_textbook_metadata.json"
__l4_integrate__ = "scripts/integrate_multimodal_textbook_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class MultimodalTextbookParser(BaseParser):
    """Parser for Multimodal Textbook dataset.

    Extracts basic metadata from textbook images. Full content analysis
    (text/figure/formula detection) is handled by downstream enrichment.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["multimodal_textbook", "multimodal-textbook"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Multimodal Textbook labels from directory structure.

        Args:
            dataset_path: Root path of the Multimodal Textbook dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with basic metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Store source and domain information
        labels.raw_labels["source"] = "multimodal_textbook"
        labels.raw_labels["domain"] = "educational"
        labels.raw_labels["capture_method"] = "born_digital"
        labels.raw_labels["document_type"] = "textbook"

        # Extract page information from filename if present
        # Common patterns: page_001.jpg, ch1_p5.jpg, etc.
        filename = image_path.stem

        # Try to extract page number
        import re

        page_match = re.search(r"(?:page|p)_?(\d+)", filename, re.IGNORECASE)
        if page_match:
            labels.raw_labels["page_number"] = int(page_match.group(1))

        # Try to extract chapter information
        chapter_match = re.search(r"(?:ch|chapter)_?(\d+)", filename, re.IGNORECASE)
        if chapter_match:
            labels.raw_labels["chapter"] = int(chapter_match.group(1))

        # Textbook pages typically contain mixed content
        labels.raw_labels["expected_content"] = [
            "text",
            "figures",
            "formulas",
            "tables",
            "captions",
        ]

        # Language metadata (hardcoded for English STEM textbooks)
        labels.raw_labels["language_code"] = "en"  # English
        labels.raw_labels["script_code"] = "Latn"  # Latin script
        labels.raw_labels["script_family"] = "latin"

        return labels


__all__ = ["MultimodalTextbookParser"]
