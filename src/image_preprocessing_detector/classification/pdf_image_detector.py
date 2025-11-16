"""
PDF embedded image detection utility using PyMuPDF (fitz).

Detects and extracts metadata about embedded images in PDF files.
"""

from pathlib import Path

import fitz  # PyMuPDF

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class PDFImageDetectionError(Exception):
    """Raised when PDF image detection fails."""


def detect_embedded_images(pdf_path: Path | str) -> list[dict]:
    """
    Detect embedded images in a PDF file.

    Uses PyMuPDF (fitz) to detect embedded images and extract metadata.
    Returns information about each embedded image including dimensions,
    format, and page location.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dictionaries containing image metadata:
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

    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as e:
        logger.exception("Invalid or corrupted PDF file", path=str(pdf_path))
        raise PDFImageDetectionError(f"Invalid or corrupted PDF: {pdf_path}") from e
    except RuntimeError as e:
        # Handle password-protected PDFs
        if "password" in str(e).lower():
            logger.exception("Password-protected PDF", path=str(pdf_path))
            raise PDFImageDetectionError(
                f"Password-protected PDF cannot be processed: {pdf_path}"
            ) from e
        raise PDFImageDetectionError(f"Error opening PDF: {pdf_path}") from e
    except Exception as e:
        logger.exception("Unexpected error opening PDF", path=str(pdf_path))
        raise PDFImageDetectionError(f"Error opening PDF: {pdf_path}") from e

    try:
        images = []
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                page_images = page.get_images()

                for img_index, img_info in enumerate(page_images):
                    try:
                        # Extract image metadata
                        xref = img_info[0]
                        img_dict = doc.extract_image(xref)

                        if img_dict:
                            images.append(
                                {
                                    "page_number": page_num,
                                    "image_index": img_index,
                                    "width": img_dict.get("width", 0),
                                    "height": img_dict.get("height", 0),
                                    "colorspace": img_dict.get("colorspace", "Unknown"),
                                    "bits_per_component": img_dict.get("bpc", 0),
                                    "xref": xref,
                                }
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to extract image metadata",
                            page_num=page_num,
                            img_index=img_index,
                            error=str(e),
                        )
                        # Continue processing other images

            except Exception as e:
                logger.warning(
                    "Failed to process page for images",
                    page_num=page_num,
                    error=str(e),
                )
                # Continue processing other pages

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
        print("Usage: python pdf_image_detector.py <pdf_path>")  # noqa: T201
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    pdf_path = sys.argv[1]
    images = detect_embedded_images(pdf_path)

    print(f"\nDetected {len(images)} embedded images in {pdf_path}:")  # noqa: T201
    for img in images:
        print(  # noqa: T201
            f"  Page {img['page_number'] + 1}, Image {img['image_index']}: "
            f"{img['width']}x{img['height']} ({img['colorspace']}, "
            f"{img['bits_per_component']} bpc)"
        )
