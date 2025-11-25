"""API routes package.

Contains route modules for:
- Health and readiness checks
- Document processing
- Batch processing
"""

from image_preprocessing_detector.api.routes.health import router as health_router
from image_preprocessing_detector.api.routes.process import router as process_router

__all__ = ["health_router", "process_router"]
