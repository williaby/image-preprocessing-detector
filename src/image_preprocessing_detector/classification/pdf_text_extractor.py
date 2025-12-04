"""PDF text extraction utility using PyMuPDF (fitz).

Extracts all text content from PDF files for classification purposes.
"""

from pathlib import Path

import fitz  # PyMuPDF

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class PDFTextExtractionError(Exception):
    """Raised when PDF text extraction fails."""


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """Extract all text content from a PDF file.

    Uses PyMuPDF (fitz) to extract text from all pages of the PDF.
    Handles errors gracefully for corrupted or password-protected PDFs.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text as a single string (whitespace normalized)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        PDFTextExtractionError: If PDF is corrupted, password-protected, or invalid

    Example:
        >>> text = extract_text_from_pdf("document.pdf")
        >>> print(f"Extracted {len(text)} characters")
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        logger.error("PDF file not found", path=str(pdf_path))
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.is_file():
        logger.error("Path is not a file", path=str(pdf_path))
        raise PDFTextExtractionError(f"Path is not a file: {pdf_path}")

    logger.info("Extracting text from PDF", path=str(pdf_path))

    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as e:
        logger.exception("Invalid or corrupted PDF file", path=str(pdf_path))
        raise PDFTextExtractionError(f"Invalid or corrupted PDF: {pdf_path}") from e
    except RuntimeError as e:
        # Handle password-protected PDFs
        if "password" in str(e).lower():
            logger.exception("Password-protected PDF", path=str(pdf_path))
            raise PDFTextExtractionError(
                f"Password-protected PDF cannot be processed: {pdf_path}"
            ) from e
        raise PDFTextExtractionError(f"Error opening PDF: {pdf_path}") from e
    except Exception as e:
        logger.exception("Unexpected error opening PDF", path=str(pdf_path))
        raise PDFTextExtractionError(f"Error opening PDF: {pdf_path}") from e

    try:
        # Extract text from all pages
        text_parts = []
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                text = page.get_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                logger.warning(
                    "Failed to extract text from page",
                    page_num=page_num,
                    error=str(e),
                )
                # Continue processing other pages

        # Combine all text
        full_text = "\n".join(text_parts)

        # Normalize whitespace
        full_text = " ".join(full_text.split())

        logger.info(
            "Text extraction complete",
            path=str(pdf_path),
            pages=len(doc),
            text_length=len(full_text),
        )

        return full_text

    finally:
        doc.close()


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_text_extractor.py <pdf_path>")
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)

    print(f"\nExtracted text from {pdf_path}:")
    print(f"Length: {len(text)} characters")
    print("\nFirst 500 characters:")
    print(text[:500])
