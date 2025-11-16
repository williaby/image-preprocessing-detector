"""PDF type classifier using text extraction and image detection.

Classifies PDFs into three types:
- born_digital: Text-based PDFs with extractable text, no embedded images
- image_only: Scanned PDFs with embedded images only, minimal text
- hybrid: PDFs with both extractable text and embedded images
"""

from pathlib import Path

from image_preprocessing_detector.classification.pdf_image_detector import (
    detect_embedded_images,
)
from image_preprocessing_detector.classification.pdf_text_extractor import (
    extract_text_from_pdf,
)
from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.schema import PDFType
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def classify_pdf_type(
    pdf_path: Path | str,
    text_min_threshold: int | None = None,
    text_max_threshold: int | None = None,
    settings: Settings | None = None,
) -> PDFType:
    """Classify a PDF into one of three types based on content.

    Classification logic:
    - If text length > text_max_threshold AND image count == 0 → born_digital
    - If text length < text_min_threshold AND image count > 0 → image_only
    - Otherwise → hybrid

    Args:
        pdf_path: Path to the PDF file
        text_min_threshold: Minimum characters for text detection (default from config: 10)
        text_max_threshold: Minimum characters for born_digital classification (default from config: 50)
        settings: Configuration settings (uses defaults if None)

    Returns:
        PDFType enum value (BORN_DIGITAL, IMAGE_ONLY, or HYBRID)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        PDFTextExtractionError: If PDF cannot be processed for text extraction
        PDFImageDetectionError: If PDF cannot be processed for image detection

    Example:
        >>> pdf_type = classify_pdf_type("document.pdf")
        >>> if pdf_type == PDFType.BORN_DIGITAL:
        ...     print("Text-based document")
        >>> elif pdf_type == PDFType.IMAGE_ONLY:
        ...     print("Scanned document")
        >>> else:
        ...     print("Hybrid document")
    """
    pdf_path = Path(pdf_path)

    # Get settings
    if settings is None:
        settings = Settings()

    # Use provided thresholds or fall back to settings
    min_threshold = (
        text_min_threshold
        if text_min_threshold is not None
        else settings.pdf_text_min_threshold
    )
    max_threshold = (
        text_max_threshold
        if text_max_threshold is not None
        else settings.pdf_text_max_threshold
    )

    logger.info(
        "Classifying PDF type",
        path=str(pdf_path),
        text_min_threshold=min_threshold,
        text_max_threshold=max_threshold,
    )

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    text_length = len(text)

    # Detect embedded images
    images = detect_embedded_images(pdf_path)
    image_count = len(images)

    # Classification logic
    if text_length > max_threshold and image_count == 0:
        pdf_type = PDFType.BORN_DIGITAL
    elif text_length < min_threshold and image_count > 0:
        pdf_type = PDFType.IMAGE_ONLY
    else:
        pdf_type = PDFType.HYBRID

    logger.info(
        "PDF classification complete",
        path=str(pdf_path),
        pdf_type=pdf_type.value,
        text_length=text_length,
        image_count=image_count,
    )

    return pdf_type


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_type_classifier.py <pdf_path>")  # noqa: T201
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    pdf_path = sys.argv[1]
    pdf_type = classify_pdf_type(pdf_path)

    print(f"\nPDF Classification for {pdf_path}:")  # noqa: T201
    print(f"  Type: {pdf_type.value}")  # noqa: T201

    if pdf_type == PDFType.BORN_DIGITAL:
        print("  → Text-based document (born digital)")  # noqa: T201
    elif pdf_type == PDFType.IMAGE_ONLY:
        print("  → Scanned document (image only)")  # noqa: T201
    else:
        print("  → Hybrid document (text + images)")  # noqa: T201
