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
- IIIT-HW-Hindi: Hindi word-level handwriting in Devanagari script (95K images)
- KHATT: Arabic paragraph-level handwriting (1,633 images from 1,000 writers)
- CASIA-HWDB2: Chinese full-page handwriting (5,091 pages, DGRL binary format)
- CASIA-HWDB2-line: Chinese line-level handwriting (52,160 lines, Teklia HF edition)
- Egyptian Handwriting: Arabic cursive word-level (11,216 images, 89 writers)
- SALAMI: Legibility assessment with 20-expert consensus (250 manuscript images)
- GNHK: English handwriting with word-level polygons (687 pages, legibility tags)

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
    - iiit-hw-hindi
    - khatt
    - casia-hwdb2
    - casia-hwdb2-line
    - egyptian-handwriting
    - salami
    - gnhk
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .casia_hwdb2 import CasiaHwdb2Parser
from .casia_hwdb2_line import CasiaHwdb2LineParser
from .egyptian_handwriting import EgyptianHandwritingParser
from .gnhk import GNHKParser
from .hasyv2 import HASYv2Parser
from .iam import IAMParser
from .iiit_hw_hindi import IIITHWHindiParser
from .khatt import KHATTParser
from .maths_handwriting import MathsHandwritingParser
from .muharaf import MuharafParser
from .ndl_minhon import NdlMinhonParser
from .nist_db2 import NistDb2Parser
from .nist_sd6 import NistSd6Parser
from .nist_sd19 import NistSd19Parser
from .pucit_ohul import PucitOhulParser
from .salami import SalamiParser
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
    registry.register(IIITHWHindiParser())
    registry.register(KHATTParser())
    registry.register(CasiaHwdb2Parser())
    registry.register(CasiaHwdb2LineParser())
    registry.register(EgyptianHandwritingParser())
    registry.register(GNHKParser())
    registry.register(NdlMinhonParser())
    registry.register(SalamiParser())


__all__ = [
    "CasiaHwdb2LineParser",
    "CasiaHwdb2Parser",
    "EgyptianHandwritingParser",
    "GNHKParser",
    "HASYv2Parser",
    "IAMParser",
    "IIITHWHindiParser",
    "KHATTParser",
    "MathsHandwritingParser",
    "MuharafParser",
    "NdlMinhonParser",
    "NistDb2Parser",
    "NistSd6Parser",
    "NistSd19Parser",
    "PucitOhulParser",
    "SalamiParser",
    "SignaTRParser",
    "register_handwriting_parsers",
]
