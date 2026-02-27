"""Correction parsers for shadow removal and dewarping datasets.

Datasets covered:
    - anyphotodoc6300 (dewarping benchmark, 6,300 images)
    - docalign12k (document alignment, 12,000 images)
    - wsrd (shadow removal, NTIRE 2023/2024)
    - warpdoc (document dewarping, 1,020 images)
    - docreal (document dewarping benchmark)
    - sd7k (shadow removal, ~7,000 images)
    - staindoc (stain removal, WACV 2025, ~5,000 pairs)
    - drccbi (camera dewarping benchmark)
    - doc3d (synthetic document dewarping, 102,064 images, BlenderProc)
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
    from .doc3d import Doc3DParser
    from .docalign12k import Docalign12KParser
    from .docreal import DocrealParser
    from .drccbi import DrccbiParser
    from .sd7k import Sd7KParser
    from .staindoc import StaindocParser
    from .warpdoc import WarpdocParser
    from .wsrd import WsrdParser

    registry.register(Anyphotodoc6300Parser())
    registry.register(Docalign12KParser())
    registry.register(Doc3DParser())
    registry.register(WsrdParser())
    registry.register(WarpdocParser())
    registry.register(DocrealParser())
    registry.register(Sd7KParser())
    registry.register(StaindocParser())
    registry.register(DrccbiParser())


__all__ = ["register_correction_parsers"]
