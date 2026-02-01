# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for NIST Special Database 6 (Census Form) dataset.

NIST SD6 contains synthesized 1988 Census forms with handwritten field entries.
Field annotations are stored in companion .fmt files (same format as NIST SD2).

IMPORTANT: This dataset contains CENSUS forms, NOT tax forms (unlike NIST SD2).
- SD2: IRS 1040 tax forms (12 form types)
- SD6: 1988 Census forms (20 unique form faces)

Dataset Structure:
    nist_sd6/
        sd06/
            data/
                sfrs2_0/
                    r0000/
                        r0000_00.png  - Page images (5,595 total)
                        r0000_00.fmt  - Field annotations
                    r0001/
                        ...

.fmt File Format:
    Line 1: Form ID (e.g., "census_001")
    Line 2+: field_id value
    Fields follow 1988 Census form structure
    Special token: _ICON_ for checkboxes/logos

Labels Extracted:
    - form_type: "census" (1988 Census forms)
    - document_type: "census_form"
    - form_id: Unique form identifier from .fmt
    - field_count: Number of fields in form
    - has_handwritten_content: Whether form contains handwritten text
    - sample_fields: Sample field values (first 5)
    - field_mapping: Full field_id→value mapping (optional)

Dataset Characteristics:
    - 5,595 page images (synthesized, not real scans)
    - 20 unique Census form faces
    - Binary B&W images (2560 x 3300 px)
    - Public domain license
    - Handwritten field entries on printed forms

Example:
    >>> parser = NistSd6Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/nist_sd6"),
    ...     image_path=Path("/data/nist_sd6/sd06/data/sfrs2_0/r0000/r0000_00.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'en'
    >>> print(labels.raw_labels["form_type"])
    'census'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class NistSd6Parser(BaseParser):
    """Parser for NIST Special Database 6 (Census Form) dataset.

    Extracts census form metadata and field annotations from .fmt files:
    - Form type (1988 Census forms - NOT tax forms like SD2)
    - Form ID
    - Field count and sample values
    - Full field mapping (field_id → value)
    - Handwritten content detection

    IMPORTANT: SD6 contains Census forms, NOT IRS 1040 tax forms.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nist-sd6", "nist_sd6", "sd6"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse NIST SD6 labels from .fmt files.

        Args:
            dataset_path: Root path of the NIST SD6 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, and raw_labels
            containing form metadata and field annotations
        """
        labels = OriginalLabels()

        # Set language/script for US Census forms
        labels.language_code = "en"
        labels.script_name = "Latin"

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # CRITICAL FIX: SD6 contains Census forms, NOT tax forms
        labels.raw_labels["form_type"] = "census"
        labels.raw_labels["document_type"] = "census_form"

        # Try to find and parse companion .fmt file
        fmt_path = image_path.with_suffix(".fmt")
        if fmt_path.exists():
            try:
                with open(fmt_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    if lines:
                        # First line is form ID
                        labels.raw_labels["form_id"] = lines[0].strip()

                        # Extract full field mapping and sample values
                        field_mapping: dict[str, str] = {}
                        field_values: list[str] = []
                        for line in lines[1:]:
                            line = line.strip()
                            if line and " " in line:
                                parts = line.split(" ", 1)
                                if len(parts) == 2:
                                    field_id, value = parts
                                    if value and value != "_ICON_":
                                        field_mapping[field_id] = value
                                        field_values.append(value)

                        labels.raw_labels["field_count"] = len(lines) - 1
                        labels.raw_labels["field_mapping"] = field_mapping
                        if field_values:
                            labels.raw_labels["has_handwritten_content"] = True
                            # Store first few field values as sample
                            labels.raw_labels["sample_fields"] = field_values[:5]
                        else:
                            labels.raw_labels["has_handwritten_content"] = False
            except Exception as e:
                logger.debug(f"Failed to parse NIST SD6 .fmt file: {e}")

        return labels


__all__ = ["NistSd6Parser"]
