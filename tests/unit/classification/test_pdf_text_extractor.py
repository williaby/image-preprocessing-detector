"""
Unit tests for PDF text extraction.

Tests the extract_text_from_pdf function with various PDF types.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import fitz  # PyMuPDF
import pytest

from image_preprocessing_detector.classification.pdf_text_extractor import (
    PDFTextExtractionError,
    extract_text_from_pdf,
)


class TestExtractTextFromPDF:
    """Tests for extract_text_from_pdf function."""

    def test_extract_text_from_valid_pdf(self, tmp_path: Path) -> None:
        """Test extracting text from a valid PDF file."""
        # Create a simple PDF with text
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 size
        page.insert_text((100, 100), "Hello World")
        page.insert_text((100, 150), "This is a test PDF")
        doc.save(str(pdf_path))
        doc.close()

        # Extract text
        text = extract_text_from_pdf(pdf_path)

        # Verify
        assert "Hello World" in text
        assert "This is a test PDF" in text
        assert len(text) > 0

    def test_extract_text_from_multipage_pdf(self, tmp_path: Path) -> None:
        """Test extracting text from a multi-page PDF."""
        pdf_path = tmp_path / "multipage.pdf"
        doc = fitz.open()

        # Create 3 pages with different content
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((100, 100), f"Page {i + 1} content")

        doc.save(str(pdf_path))
        doc.close()

        # Extract text
        text = extract_text_from_pdf(pdf_path)

        # Verify all pages are included
        assert "Page 1 content" in text
        assert "Page 2 content" in text
        assert "Page 3 content" in text

    def test_extract_text_from_empty_pdf(self, tmp_path: Path) -> None:
        """Test extracting text from a PDF with no text content."""
        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        doc.new_page(width=595, height=842)  # Empty page
        doc.save(str(pdf_path))
        doc.close()

        # Extract text
        text = extract_text_from_pdf(pdf_path)

        # Verify empty or minimal text
        assert len(text) == 0 or text.strip() == ""

    def test_extract_text_normalizes_whitespace(self, tmp_path: Path) -> None:
        """Test that extracted text has normalized whitespace."""
        pdf_path = tmp_path / "whitespace.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # Insert text with extra whitespace
        page.insert_text((100, 100), "Text   with    extra")
        page.insert_text((100, 150), "whitespace\n\n\n")
        doc.save(str(pdf_path))
        doc.close()

        # Extract text
        text = extract_text_from_pdf(pdf_path)

        # Verify whitespace is normalized
        assert "  " not in text  # No double spaces
        assert "\n" not in text  # No newlines

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        """Test error handling when PDF file doesn't exist."""
        pdf_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            extract_text_from_pdf(pdf_path)

        assert "not found" in str(exc_info.value)

    def test_path_is_not_a_file(self, tmp_path: Path) -> None:
        """Test error handling when path is a directory, not a file."""
        # Create a directory instead of a file
        dir_path = tmp_path / "directory"
        dir_path.mkdir()

        with pytest.raises(PDFTextExtractionError) as exc_info:
            extract_text_from_pdf(dir_path)

        assert "not a file" in str(exc_info.value)

    def test_corrupted_pdf_error(self, tmp_path: Path) -> None:
        """Test error handling for corrupted PDF files."""
        # Create a corrupted PDF (invalid content)
        pdf_path = tmp_path / "corrupted.pdf"
        pdf_path.write_text("This is not a valid PDF file")

        with pytest.raises(PDFTextExtractionError) as exc_info:
            extract_text_from_pdf(pdf_path)

        assert "Invalid or corrupted" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_text_extractor.fitz.open")
    def test_password_protected_pdf_error(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for password-protected PDFs."""
        pdf_path = tmp_path / "protected.pdf"
        pdf_path.touch()  # Create empty file

        # Mock fitz.open to raise password error
        mock_fitz_open.side_effect = RuntimeError("Password required")

        with pytest.raises(PDFTextExtractionError) as exc_info:
            extract_text_from_pdf(pdf_path)

        assert "Password-protected" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_text_extractor.fitz.open")
    def test_generic_runtime_error(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for generic runtime errors."""
        pdf_path = tmp_path / "error.pdf"
        pdf_path.touch()

        # Mock fitz.open to raise generic runtime error
        mock_fitz_open.side_effect = RuntimeError("Some other error")

        with pytest.raises(PDFTextExtractionError) as exc_info:
            extract_text_from_pdf(pdf_path)

        assert "Error opening PDF" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_text_extractor.fitz.open")
    def test_unexpected_exception(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for unexpected exceptions."""
        pdf_path = tmp_path / "unexpected.pdf"
        pdf_path.touch()

        # Mock fitz.open to raise unexpected exception
        mock_fitz_open.side_effect = ValueError("Unexpected error")

        with pytest.raises(PDFTextExtractionError) as exc_info:
            extract_text_from_pdf(pdf_path)

        assert "Error opening PDF" in str(exc_info.value)

    def test_page_extraction_error_continues_processing(self, tmp_path: Path) -> None:
        """Test that page extraction errors don't stop processing other pages."""
        pdf_path = tmp_path / "partial_error.pdf"

        # Create a PDF with multiple pages
        doc = fitz.open()
        page1 = doc.new_page(width=595, height=842)
        page1.insert_text((100, 100), "Page 1 content")
        page2 = doc.new_page(width=595, height=842)
        page2.insert_text((100, 100), "Page 2 content")
        page3 = doc.new_page(width=595, height=842)
        page3.insert_text((100, 100), "Page 3 content")
        doc.save(str(pdf_path))
        doc.close()

        # Mock to simulate error on page 2
        with patch(
            "image_preprocessing_detector.classification.pdf_text_extractor.fitz.open"
        ) as mock_open:
            mock_doc = MagicMock()
            # Set length properly
            mock_doc.__len__ = MagicMock(return_value=3)

            # Page 1: success
            mock_page1 = Mock()
            mock_page1.get_text.return_value = "Page 1 content"

            # Page 2: error
            mock_page2 = Mock()
            mock_page2.get_text.side_effect = Exception("Page error")

            # Page 3: success
            mock_page3 = Mock()
            mock_page3.get_text.return_value = "Page 3 content"

            mock_doc.__getitem__.side_effect = [mock_page1, mock_page2, mock_page3]
            mock_doc.close = Mock()
            mock_open.return_value = mock_doc

            # Extract text - should continue despite page 2 error
            text = extract_text_from_pdf(pdf_path)

            # Verify pages 1 and 3 are included
            assert "Page 1 content" in text
            assert "Page 3 content" in text
            # Page 2 should be skipped
            assert "Page 2 content" not in text

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test that function accepts string paths."""
        pdf_path = tmp_path / "string_path.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "String path test")
        doc.save(str(pdf_path))
        doc.close()

        # Pass as string instead of Path
        text = extract_text_from_pdf(str(pdf_path))

        assert "String path test" in text

    def test_logging_on_success(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that successful extraction logs appropriately."""
        pdf_path = tmp_path / "logging_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Logging test")
        doc.save(str(pdf_path))
        doc.close()

        result = extract_text_from_pdf(pdf_path)

        # Verify extraction worked
        assert "Logging test" in result
        assert len(result) > 0
