# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Layout annotation parsers for the annotation system.

This package contains parsers for datasets with layout/structure annotations:
- DocLayNet: Document layout analysis (COCO format)
- DocSynth300K: Synthetic document layout (YOLO format in parquet)
- TableBank: Table detection (COCO format)
- PubTabNet: Table structure (HTML + COCO)
- FinTabNet: Financial table structure
- FUNSD: Form understanding (dict format - P0-4 fix)
- FUNSD+: Extended FUNSD
- SROIE: Receipt OCR and IE
- Invoices-KG: Kaggle High-Quality Invoice Images (JSON manifest)

Datasets covered:
    - doclaynet
    - docsynth300k
    - tablebank
    - pubtabnet
    - fintabnet
    - funsd
    - funsd_plus
    - sroie
    - invoices-kg / invoices_kaggle
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_layout_parsers(registry: ParserRegistry) -> None:
    """Register all layout parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    from .doclaynet import DocLayNetParser
    from .docsynth300k import DocSynth300KParser
    from .fintabnet import FinTabNetParser
    from .funsd import FunsdParser
    from .funsd_plus import FunsdPlusParser
    from .invoices_kg import InvoicesKgParser
    from .pubtabnet import PubTabNetParser
    from .sroie import SroieParser
    from .tablebank import TableBankParser

    registry.register(DocLayNetParser())
    registry.register(DocSynth300KParser())
    registry.register(TableBankParser())
    registry.register(PubTabNetParser())
    registry.register(FinTabNetParser())
    registry.register(FunsdParser())
    registry.register(FunsdPlusParser())
    registry.register(SroieParser())
    registry.register(InvoicesKgParser())


__all__ = [
    "register_layout_parsers",
]
