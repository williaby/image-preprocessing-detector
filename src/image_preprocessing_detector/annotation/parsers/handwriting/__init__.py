# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Handwriting and signature parsers for the annotation system.

This package contains parsers for handwriting/signature datasets:
- SignaTR6K: Signature segmentation dataset
- PUCIT-OHUL: Urdu handwriting lines
- NIST-SD19: Handwritten characters and digits
- NIST-DB2: Handwritten tax forms
- NIST-SD6: Handwritten tax forms (Special Database 6)
- Maths Handwriting: Mathematical expressions (stub)
- HASYv2: Handwritten mathematical symbols (369 classes)
- Muharaf: Arabic historical manuscripts with PAGE XML annotations
- IAM: English handwriting database (forms/lines/words)

Datasets covered:
    - signatr6k
    - nist_sd19
    - pucit_ohul
    - nist-sd2
    - nist_sd6
    - maths_handwriting
    - hasyv2
    - muharaf
    - iam
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .hasyv2 import HASYv2Parser
from .iam import IAMParser
from .maths_handwriting import MathsHandwritingParser
from .muharaf import MuharafParser
from .nist_db2 import NistDb2Parser
from .nist_sd6 import NistSd6Parser
from .nist_sd19 import NistSd19Parser
from .pucit_ohul import PucitOhulParser
from .signatr import SignaTRParser

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_handwriting_parsers(registry: ParserRegistry) -> None:
    """Register all handwriting parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    registry.register(SignaTRParser())
    registry.register(PucitOhulParser())
    registry.register(NistSd19Parser())
    registry.register(NistDb2Parser())
    registry.register(NistSd6Parser())
    registry.register(MathsHandwritingParser())
    registry.register(HASYv2Parser())
    registry.register(MuharafParser())
    registry.register(IAMParser())


__all__ = [
    "HASYv2Parser",
    "IAMParser",
    "MathsHandwritingParser",
    "MuharafParser",
    "NistDb2Parser",
    "NistSd6Parser",
    "NistSd19Parser",
    "PucitOhulParser",
    "SignaTRParser",
    "register_handwriting_parsers",
]
