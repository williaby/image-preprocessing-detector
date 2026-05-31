"""PDF embedded image detection utility using PyMuPDF (fitz).

Detects and extracts metadata about embedded images in PDF files.
"""

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class PDFImageDetectionError(Exception):
    """Raised when PDF image detection fails."""


def _open_pdf_document(pdf_path: Path) -> fitz.Document:
    """Open a PDF document with proper error handling.

    Args:
        pdf_path (Path): Path to the PDF file

    Returns:
        fitz.Document: Opened fitz.Document

    Raises:
        PDFImageDetectionError: If PDF cannot be opened
    """
    try:
        return fitz.open(str(pdf_path))
    except fitz.FileDataError as e:
        logger.exception("Invalid or corrupted PDF file", path=str(pdf_path))
        raise PDFImageDetectionError(f"Invalid or corrupted PDF: {pdf_path}") from e
    except RuntimeError as e:
        if "password" in str(e).lower():
            logger.exception("Password-protected PDF", path=str(pdf_path))
            raise PDFImageDetectionError(
                f"Password-protected PDF cannot be processed: {pdf_path}"
            ) from e
        raise PDFImageDetectionError(f"Error opening PDF: {pdf_path}") from e
    except Exception as e:
        logger.exception("Unexpected error opening PDF", path=str(pdf_path))
        raise PDFImageDetectionError(f"Error opening PDF: {pdf_path}") from e


def _extract_image_metadata(
    doc: fitz.Document, page_num: int, img_index: int, xref: int
) -> dict[str, Any] | None:
    """Extract metadata for a single image.

    Args:
        doc (fitz.Document): PDF document
        page_num (int): Page number (zero-based)
        img_index (int): Image index on the page
        xref (int): Image cross-reference number

    Returns:
        dict[str, Any] | None: Image metadata dictionary or None if extraction fails
    """
    try:
        img_dict = doc.extract_image(xref)
        if img_dict:
            return {
                "page_number": page_num,
                "image_index": img_index,
                "width": img_dict.get("width", 0),
                "height": img_dict.get("height", 0),
                "colorspace": img_dict.get("colorspace", "Unknown"),
                "bits_per_component": img_dict.get("bpc", 0),
                "xref": xref,
            }
    except Exception as e:
        logger.warning(
            "Failed to extract image metadata",
            page_num=page_num,
            img_index=img_index,
            error=str(e),
        )
    return None


def _extract_page_images(doc: fitz.Document, page_num: int) -> list[dict[str, Any]]:
    """Extract all images from a single page.

    Args:
        doc (fitz.Document): PDF document
        page_num (int): Page number (zero-based)

    Returns:
        list[dict[str, Any]]: List of image metadata dictionaries
    """
    images: list[dict[str, Any]] = []
    try:
        page = doc[page_num]
        page_images = page.get_images()

        for img_index, img_info in enumerate(page_images):
            xref = img_info[0]
            metadata = _extract_image_metadata(doc, page_num, img_index, xref)
            if metadata:
                images.append(metadata)
    except Exception as e:
        logger.warning(
            "Failed to process page for images",
            page_num=page_num,
            error=str(e),
        )
    return images


def detect_embedded_images(pdf_path: Path | str) -> list[dict[str, Any]]:
    """Detect embedded images in a PDF file.

    Uses PyMuPDF (fitz) to detect embedded images and extract metadata.
    Returns information about each embedded image including dimensions,
    format, and page location.

    Args:
        pdf_path (Path | str): Path to the PDF file

    Returns:
        list[dict[str, Any]]: List of dictionaries containing image metadata:
        - page_number: Page index (zero-based)
        - image_index: Index of image on the page
        - width: Image width in pixels
        - height: Image height in pixels
        - colorspace: Colorspace of the image (e.g., "RGB", "Gray")
        - bits_per_component: Bits per color component
        - xref: Cross-reference number in PDF (unique ID)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        PDFImageDetectionError: If PDF is corrupted, password-protected, or invalid

    Example:
        >>> images = detect_embedded_images("document.pdf")
        >>> print(f"Found {len(images)} images")
        >>> for img in images:
        ...     print(f"Page {img['page_number']}: {img['width']}x{img['height']}")
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        logger.error("PDF file not found", path=str(pdf_path))
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.is_file():
        logger.error("Path is not a file", path=str(pdf_path))
        raise PDFImageDetectionError(f"Path is not a file: {pdf_path}")

    logger.info("Detecting embedded images in PDF", path=str(pdf_path))

    doc = _open_pdf_document(pdf_path)
    try:
        images: list[dict[str, Any]] = []
        for page_num in range(len(doc)):
            images.extend(_extract_page_images(doc, page_num))

        logger.info(
            "Image detection complete",
            path=str(pdf_path),
            pages=len(doc),
            total_images=len(images),
        )
        return images
    finally:
        doc.close()


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_image_detector.py <pdf_path>")
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    pdf_path = sys.argv[1]
    images = detect_embedded_images(pdf_path)

    print(f"\nDetected {len(images)} embedded images in {pdf_path}:")
    for img in images:
        print(
            f"  Page {img['page_number'] + 1}, Image {img['image_index']}: "
            f"{img['width']}x{img['height']} ({img['colorspace']}, "
            f"{img['bits_per_component']} bpc)"
        )
