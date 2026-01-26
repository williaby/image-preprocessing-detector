# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Handwriting and signature parsers for the annotation system.

This package contains parsers for handwriting/signature datasets:
- SignaTR6K: Signature segmentation dataset
- PUCIT-OHUL: Urdu handwriting lines
- NIST-SD19: Handwritten characters and digits
- NIST-DB2: Handwritten tax forms
- Maths Handwriting: Mathematical expressions (stub)

Datasets covered:
    - signatr6k
    - nist_sd19
    - pucit_ohul
    - nist_db2
    - maths_handwriting
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maths_handwriting import MathsHandwritingParser
from .nist_db2 import NistDb2Parser
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
    registry.register(MathsHandwritingParser())


__all__ = [
    "MathsHandwritingParser",
    "NistDb2Parser",
    "NistSd19Parser",
    "PucitOhulParser",
    "SignaTRParser",
    "register_handwriting_parsers",
]
