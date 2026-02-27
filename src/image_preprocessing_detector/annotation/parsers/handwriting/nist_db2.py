"""Parser for NIST Special Database 2 (Tax Form) dataset.

NIST SD2 contains handwritten IRS 1040 tax forms with field annotations
stored in companion .fmt files.

Dataset Structure:
    NIST_SD2/
        *.png           - Page images
        *.fmt           - Field annotation files

.fmt File Format:
    Line 1: Form ID
    Line 2+: field_id value
    Special token: _ICON_ indicates non-text content

Labels:
    - form_type: IRS form type (1040)
    - document_type: tax_form
    - form_id: Unique form identifier
    - field_count: Number of fields in form
    - has_handwritten_content: Whether form contains handwritten text
    - sample_fields: Sample field values (first 5)

Example:
    >>> parser = NistDb2Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/NIST_SD2"),
    ...     image_path=Path("/data/NIST_SD2/form_0001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'en'
    >>> print(labels.raw_labels["form_type"])
    '1040'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "nist-sd2"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "nist_sd2_metadata.json"
__l4_integrate__ = "scripts/integrate_nist_sd2_enrichments.py"


import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class NistDb2Parser(BaseParser):
    """Parser for NIST Special Database 2 (Tax Form) dataset.

    Extracts tax form metadata and field annotations from .fmt files:
    - Form type (IRS 1040)
    - Form ID
    - Field count and sample values
    - Handwritten content detection
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nist-db2", "nist-sd2", "sd2"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse NIST DB2 labels from .fmt files.

        Args:
            dataset_path: Root path of the NIST DB2 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, and raw_labels
            containing form metadata and field annotations
        """
        labels = OriginalLabels()

        # Set language/script for US tax forms
        labels.language_code = "en"
        labels.script_name = "Latin"

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["form_type"] = "1040"
        labels.raw_labels["document_type"] = "tax_form"

        # Try to find and parse companion .fmt file
        fmt_path = image_path.with_suffix(".fmt")
        if fmt_path.exists():
            try:
                with open(fmt_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    if lines:
                        # First line is form ID
                        labels.raw_labels["form_id"] = lines[0].strip()

                        # Extract field count and sample values
                        field_values = []
                        for line in lines[1:]:
                            line = line.strip()
                            if line and " " in line:
                                parts = line.split(" ", 1)
                                if len(parts) == 2:
                                    _, value = parts
                                    if value and value != "_ICON_":
                                        field_values.append(value)

                        labels.raw_labels["field_count"] = len(lines) - 1
                        if field_values:
                            labels.raw_labels["has_handwritten_content"] = True
                            # Store first few field values as sample
                            labels.raw_labels["sample_fields"] = field_values[:5]

                            # Populate Layer 2 text_content schema fields
                            full_text = " ".join(field_values)
                            labels.raw_labels["text_content"] = {
                                "full_text": full_text,
                                "source_type": "dataset_provided",
                                "source_format": "fmt_field_values",
                                "extraction_method": "NistDb2Parser.parse",
                                "extraction_timestamp": None,
                                "is_complete": True,
                                "encoding": "utf-8",
                            }
                        else:
                            labels.raw_labels["has_handwritten_content"] = False
            except Exception as e:
                logger.debug(f"Failed to parse NIST DB2 .fmt file: {e}")

        return labels


__all__ = ["NistDb2Parser"]
