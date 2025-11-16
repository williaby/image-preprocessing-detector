"""PDF and image ingestion modules.

Handles loading documents from various formats (PDF, images) and converting
them to standardized numpy arrays for processing.
"""

# NOTE: DocumentProcessor temporarily commented out due to missing dependencies
# (calculate_dqs, calculate_pre_ocr_risk functions). Will be re-enabled in Phase 8/9.
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
    # "DocumentProcessor",  # Commented out - see note above
    "ImageLoader",
    "ImageMetadata",
    "PDFLoader",
    "PageImage",
    "load_image",
    "load_pdf",
]
