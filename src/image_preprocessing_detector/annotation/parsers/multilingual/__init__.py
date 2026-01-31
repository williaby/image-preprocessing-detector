# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Multilingual and script detection parsers for the annotation system.

This package contains parsers for multilingual/script datasets covering
15+ datasets across multiple languages and scripts.

Parsers:
    - MultilingualScriptsParser: Collection of subdatasets (arabic_ocr,
      dzongkha_digits, jssoda, nepal_devanagari)
    - Mdiw13Parser: 13 Indic scripts (Arabic, Bengali, Gujarati, etc.)
    - CcOcrParser: Chinese Character OCR benchmark
    - TibhcrParser: Tibetan handwritten characters
    - ArabicDocsParser: Arabic document OCR (12 categories)
    - NepaliHandwrittenParser: Nepali handwritten text
    - YarmoukParser: Yarmouk Arabic OCR dataset
    - CvsiParser: Video script identification (10 scripts)
    - Siw13Parser: Scene script identification (13 scripts)
    - Mle2eParser: Multi-language end-to-end (4 scripts)
    - Mlt19Parser: ICDAR 2019 MLT multi-lingual scene text (10 languages)
    - HindiOcrSyntheticParser: Synthetic Hindi text (80K images)

Datasets covered:
    - multilingual_scripts (arabic_ocr, dzongkha_digits, jssoda, nepal_devanagari)
    - mdiw13 (13 Indic scripts)
    - cc_ocr (Chinese)
    - tibhcr (Tibetan)
    - arabic_docs_ocr (Arabic documents)
    - nepali_handwritten (Nepali)
    - yarmouk_ocr (Arabic)
    - cvsi (10 scripts)
    - siw13 (13 scripts)
    - mle2e (4 scripts)
    - mlt19 (10 languages scene text)
    - hindi_ocr_synthetic (Hindi synthetic)

Example:
    >>> from image_preprocessing_detector.annotation.parsers.multilingual import (
    ...     register_multilingual_parsers,
    ... )
    >>> from image_preprocessing_detector.annotation.parsers.registry import (
    ...     ParserRegistry,
    ... )
    >>>
    >>> registry = ParserRegistry()
    >>> register_multilingual_parsers(registry)
    >>> parser = registry.get_parser("mdiw13")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ParserRegistry

from .arabic_docs import ArabicDocsParser
from .cc_ocr import CcOcrParser
from .cvsi import CvsiParser
from .hindi_ocr_synthetic import HindiOcrSyntheticParser
from .mdiw13 import Mdiw13Parser
from .mle2e import Mle2eParser
from .mlt19 import Mlt19Parser
from .multilingual_scripts import MultilingualScriptsParser
from .nepali_handwritten import NepaliHandwrittenParser
from .siw13 import Siw13Parser
from .tibhcr import TibhcrParser
from .yarmouk import YarmoukParser


def register_multilingual_parsers(registry: ParserRegistry) -> None:
    """Register all multilingual parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    registry.register(MultilingualScriptsParser())
    registry.register(Mdiw13Parser())
    registry.register(CcOcrParser())
    registry.register(TibhcrParser())
    registry.register(ArabicDocsParser())
    registry.register(NepaliHandwrittenParser())
    registry.register(YarmoukParser())
    registry.register(CvsiParser())
    registry.register(Siw13Parser())
    registry.register(Mle2eParser())
    registry.register(Mlt19Parser())
    registry.register(HindiOcrSyntheticParser())


__all__ = [
    "ArabicDocsParser",
    "CcOcrParser",
    "CvsiParser",
    "HindiOcrSyntheticParser",
    "Mdiw13Parser",
    "Mle2eParser",
    "Mlt19Parser",
    "MultilingualScriptsParser",
    "NepaliHandwrittenParser",
    "Siw13Parser",
    "TibhcrParser",
    "YarmoukParser",
    "register_multilingual_parsers",
]
