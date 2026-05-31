"""Quality score parsers for the annotation system.

This package contains parsers for datasets with human quality scores:
- DIQA-5000: Document image quality assessment (MOS 1-5)
- SmartDoc-QA: Camera-captured document quality
- OCR-Quality: OCR readability scores (1-4, inverted)
- DIBCO: Binarization benchmark
- Q-Doc: Document quality assessment benchmark

Datasets covered:
    - diqa-5000
    - smartdoc-qa
    - ocr_quality
    - dibco
    - q-doc
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .dibco import DibcoParser
from .diqa import DIQAParser
from .ocr_quality import OcrQualityParser
from .q_doc import QDocParser
from .smartdoc import SmartDocParser

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_quality_parsers(registry: ParserRegistry) -> None:
    """Register all quality parsers with the registry.

    Args:
        registry (ParserRegistry): ParserRegistry instance to register parsers with.
    """
    registry.register(DIQAParser())
    registry.register(SmartDocParser())
    registry.register(OcrQualityParser())
    registry.register(DibcoParser())
    registry.register(QDocParser())


__all__ = [
    "DIQAParser",
    "DibcoParser",
    "OcrQualityParser",
    "QDocParser",
    "SmartDocParser",
    "register_quality_parsers",
]
