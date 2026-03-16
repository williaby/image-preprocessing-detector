"""Text extraction via Docling REST API.

Provides a client for the deployed Docling server that accepts documents
and returns structured text, markdown, and layout information.
"""

from image_preprocessing_detector.text_extraction.docling_client import (
    DoclingClient,
    DoclingResult,
    DoclingServerError,
)

__all__ = [
    "DoclingClient",
    "DoclingResult",
    "DoclingServerError",
]
