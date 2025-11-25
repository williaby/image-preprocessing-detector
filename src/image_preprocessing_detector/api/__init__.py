"""FastAPI service for image preprocessing detection.

This module provides a REST API for:
- Single document processing (/process)
- Batch document processing (/batch)
- Job status tracking (/status, /result)
"""

from image_preprocessing_detector.api.app import create_app

__all__ = ["create_app"]
