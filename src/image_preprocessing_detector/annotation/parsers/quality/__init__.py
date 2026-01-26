# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Quality score parsers for the annotation system.

This package contains parsers for datasets with human quality scores:
- DIQA-5000: Document image quality assessment (MOS 1-5)
- SmartDoc-QA: Camera-captured document quality
- OCR-Quality: OCR readability scores (1-4, inverted)
- DIBCO: Binarization benchmark

Datasets covered:
    - diqa-5000
    - smartdoc-qa
    - ocr_quality
    - dibco
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .dibco import DibcoParser
from .diqa import DIQAParser
from .ocr_quality import OcrQualityParser
from .smartdoc import SmartDocParser

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_quality_parsers(registry: ParserRegistry) -> None:
    """Register all quality parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    registry.register(DIQAParser())
    registry.register(SmartDocParser())
    registry.register(OcrQualityParser())
    registry.register(DibcoParser())


__all__ = [
    "DIQAParser",
    "SmartDocParser",
    "OcrQualityParser",
    "DibcoParser",
    "register_quality_parsers",
]
