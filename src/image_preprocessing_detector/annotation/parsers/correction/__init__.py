# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Correction parsers for shadow removal and dewarping datasets.

Datasets covered:
    - anyphotodoc6300 (dewarping benchmark, 6,300 images)
    - docalign12k (document alignment, 12,000 images)
    - wsrd (shadow removal, NTIRE 2023/2024)
    - warpdoc (document dewarping, 1,020 images)
    - docreal (document dewarping benchmark)
    - sd7k (shadow removal, ~7,000 images)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ParserRegistry


def register_correction_parsers(registry: ParserRegistry) -> None:
    """Register all correction parsers with the registry.

    Args:
        registry: ParserRegistry instance to register parsers with
    """
    from .anyphotodoc6300 import Anyphotodoc6300Parser
    from .docalign12k import Docalign12KParser
    from .docreal import DocrealParser
    from .sd7k import Sd7KParser
    from .warpdoc import WarpdocParser
    from .wsrd import WsrdParser

    registry.register(Anyphotodoc6300Parser())
    registry.register(Docalign12KParser())
    registry.register(WsrdParser())
    registry.register(WarpdocParser())
    registry.register(DocrealParser())
    registry.register(Sd7KParser())


__all__ = ["register_correction_parsers"]
