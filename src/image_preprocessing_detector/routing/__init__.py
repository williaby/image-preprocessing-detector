"""OCR routing recommendation engine for RAG Pipeline.

Analyzes document characteristics and recommends optimal OCR engine routing.

Stream 1 additions:
- ScriptRouter: Three-tier script-to-OCR-engine routing
- get_default_router: Convenience singleton factory
"""

from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.routing.script_router import (
    ScriptRouter,
    get_default_router,
    reset_default_router,
)

__all__ = [
    "ScriptRouter",
    "get_default_router",
    "recommend_ocr_routing",
    "reset_default_router",
]
