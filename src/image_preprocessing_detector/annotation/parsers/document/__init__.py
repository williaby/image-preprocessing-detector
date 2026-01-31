# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Document type parsers for the annotation system.

This package contains parsers for document classification datasets:
- RVL-CDIP: Document classification (16 classes)
- MIDV-500: ID documents (50 countries)
- OHR-Bench: OCR hallucination benchmark (16 categories)
- OmniDocBench: Arrow format comprehensive benchmark
- Tobacco800: Degraded scanned documents
- RealDAE: Camera-captured documents with degradations
- Multimodal Textbook: Educational textbook images
- FinanceBench: SEC filings benchmark (10K, 10Q, 8K, Earnings)

Datasets covered:
    - rvl_cdip
    - midv500
    - ohr-bench / ohr_bench
    - omnidocbench
    - tobacco800
    - realdae
    - multimodal_textbook / multimodal-textbook
    - financebench / finance-bench
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_document_parsers(registry: ParserRegistry) -> None:
    """Register all document parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    from .financebench import FinanceBenchParser
    from .midv500 import Midv500Parser
    from .multimodal_textbook import MultimodalTextbookParser
    from .ohr_bench import OhrBenchParser
    from .omnidocbench import OmnidocbenchParser
    from .realdae import RealdaeParser
    from .rvl_cdip import RvlCdipParser
    from .tobacco800 import Tobacco800Parser

    registry.register(RvlCdipParser())
    registry.register(Midv500Parser())
    registry.register(OhrBenchParser())
    registry.register(OmnidocbenchParser())
    registry.register(Tobacco800Parser())
    registry.register(RealdaeParser())
    registry.register(MultimodalTextbookParser())
    registry.register(FinanceBenchParser())


__all__ = [
    "register_document_parsers",
]
