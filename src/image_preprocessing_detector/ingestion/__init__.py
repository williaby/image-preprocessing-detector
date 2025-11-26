"""PDF, image, and office document ingestion modules.

Handles loading documents from various formats (PDF, images, Office documents)
and converting them to standardized numpy arrays for processing.

Phase 8: Added Office document support (.docx, .xlsx, .pptx)
"""

# NOTE: DocumentProcessor temporarily commented out due to missing dependencies
# (calculate_dqs, calculate_pre_ocr_risk functions). Will be re-enabled in Phase 8/9.
from image_preprocessing_detector.ingestion.image_loader import (
    ImageLoader,
    ImageMetadata,
    load_image,
)
from image_preprocessing_detector.ingestion.office_processor import (
    EmbeddedImage,
    OfficeDocumentInfo,
    OfficeProcessor,
    detect_office_type,
    extract_office_images,
)
from image_preprocessing_detector.ingestion.pdf_loader import (
    PageImage,
    PDFLoader,
    load_pdf,
)

__all__ = [
    # "DocumentProcessor",  # Commented out - see note above
    # Image loading
    "ImageLoader",
    "ImageMetadata",
    "load_image",
    # PDF loading
    "PDFLoader",
    "PageImage",
    "load_pdf",
    # Office document processing (Phase 8)
    "EmbeddedImage",
    "OfficeDocumentInfo",
    "OfficeProcessor",
    "detect_office_type",
    "extract_office_images",
]
