# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for MIDV-500 ID document dataset.

MIDV-500 (Mobile Identity Document Video) provides images of identity documents
from 50 countries with various document types (ID cards, passports, driver's licenses).

Dataset Structure:
    midv500/
        {country_code}/
            {doc_type}/
                {id}.tif

Document Types:
    - ID card
    - Passport
    - Driver's license (driving_licence, driverlicense, dl)

Country Coverage:
    50 countries with 2-3 letter country codes (e.g., RU, USA, DEU)
    Includes Cyrillic script countries (RU, UA, BY, BG, RS, KZ)

Example:
    >>> parser = Midv500Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/midv500"),
    ...     image_path=Path("/data/midv500/RU/id/card_001.tif"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["country_code"])
    "RU"
    >>> print(labels.script_name)
    "Cyrillic"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class Midv500Parser(BaseParser):
    """Parser for MIDV-500 ID document dataset.

    Extracts country code and document type from directory structure.
    Sets script_name for Cyrillic countries.
    """

    # Cyrillic countries (for script detection)
    CYRILLIC_COUNTRIES = {"RU", "UA", "BY", "BG", "RS", "KZ"}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["midv500"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MIDV-500 labels from path structure.

        Args:
            dataset_path: Root path of the MIDV-500 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with country_code, document_type in raw_labels,
            and script_name set for Cyrillic countries
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        path_parts = image_path.parts

        # Try to extract country code and document type from path
        # MIDV structure varies but usually has country codes
        for part in path_parts:
            # Country codes are usually 2-3 letter codes in uppercase
            if len(part) in (2, 3) and part.isupper():
                labels.raw_labels["country_code"] = part

            # Document types
            doc_type_lower = part.lower()
            if doc_type_lower in (
                "id",
                "passport",
                "driverlicense",
                "driving_licence",
                "dl",
            ):
                labels.raw_labels["document_type"] = part
                # Store normalized document type for downstream use
                if doc_type_lower in ("driverlicense", "driving_licence", "dl"):
                    labels.raw_labels["document_type_normalized"] = "driver_license"
                else:
                    labels.raw_labels["document_type_normalized"] = doc_type_lower

        # Set script name for Cyrillic countries
        country_code = labels.raw_labels.get("country_code")
        if country_code in self.CYRILLIC_COUNTRIES:
            labels.script_name = "Cyrillic"

        return labels


__all__ = ["Midv500Parser"]
