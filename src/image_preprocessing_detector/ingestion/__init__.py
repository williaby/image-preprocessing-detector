"""
PDF and image ingestion modules.

Handles loading documents from various formats (PDF, images) and converting
them to standardized numpy arrays for processing.
"""

from image_preprocessing_detector.ingestion.document_processor import (
    DocumentProcessor,
)
from image_preprocessing_detector.ingestion.image_loader import (
    ImageLoader,
    ImageMetadata,
    load_image,
)
from image_preprocessing_detector.ingestion.pdf_loader import (
    PageImage,
    PDFLoader,
    load_pdf,
)

__all__ = [
    "DocumentProcessor",
    "ImageLoader",
    "ImageMetadata",
    "PDFLoader",
    "PageImage",
    "load_image",
    "load_pdf",
]
