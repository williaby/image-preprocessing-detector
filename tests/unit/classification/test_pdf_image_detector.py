"""
Unit tests for PDF image detection.

Tests the detect_embedded_images function with various PDF types.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import fitz  # PyMuPDF
import pytest
from PIL import Image

from image_preprocessing_detector.classification.pdf_image_detector import (
    PDFImageDetectionError,
    detect_embedded_images,
)


class TestDetectEmbeddedImages:
    """Tests for detect_embedded_images function."""

    def test_detect_images_in_pdf_with_single_image(self, tmp_path: Path) -> None:
        """Test detecting a single embedded image in a PDF."""
        pdf_path = tmp_path / "with_image.pdf"

        # Create a simple image
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "test_image.jpg"
        img.save(str(img_path))

        # Create PDF with embedded image
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(100, 100, 300, 300), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify
        assert len(images) == 1
        assert images[0]["page_number"] == 0
        assert images[0]["image_index"] == 0
        assert images[0]["width"] == 100
        assert images[0]["height"] == 100
        assert "xref" in images[0]

    def test_detect_multiple_images_on_same_page(self, tmp_path: Path) -> None:
        """Test detecting multiple images on the same page."""
        pdf_path = tmp_path / "multiple_images.pdf"

        # Create two different images
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_path = tmp_path / "img1.jpg"
        img1.save(str(img1_path))

        img2 = Image.new("RGB", (150, 150), color="blue")
        img2_path = tmp_path / "img2.jpg"
        img2.save(str(img2_path))

        # Create PDF with both images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(50, 50, 150, 150), filename=str(img1_path))
        page.insert_image(fitz.Rect(200, 200, 350, 350), filename=str(img2_path))
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify both images detected
        assert len(images) == 2
        assert all(img["page_number"] == 0 for img in images)
        assert images[0]["image_index"] == 0
        assert images[1]["image_index"] == 1

    def test_detect_images_across_multiple_pages(self, tmp_path: Path) -> None:
        """Test detecting images across multiple pages."""
        pdf_path = tmp_path / "multipage_images.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="green")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create PDF with images on different pages
        doc = fitz.open()
        for _i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_image(fitz.Rect(100, 100, 200, 200), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify images on all pages
        assert len(images) == 3
        assert images[0]["page_number"] == 0
        assert images[1]["page_number"] == 1
        assert images[2]["page_number"] == 2

    def test_detect_no_images_in_text_only_pdf(self, tmp_path: Path) -> None:
        """Test detecting images in a PDF with no images."""
        pdf_path = tmp_path / "text_only.pdf"

        # Create text-only PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "This is text only, no images")
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify no images found
        assert len(images) == 0

    def test_detect_images_with_different_formats(self, tmp_path: Path) -> None:
        """Test detecting images with different colorspaces."""
        pdf_path = tmp_path / "different_formats.pdf"

        # Create RGB image
        rgb_img = Image.new("RGB", (100, 100), color="red")
        rgb_path = tmp_path / "rgb.jpg"
        rgb_img.save(str(rgb_path))

        # Create grayscale image
        gray_img = Image.new("L", (100, 100), color=128)
        gray_path = tmp_path / "gray.jpg"
        gray_img.save(str(gray_path))

        # Create PDF with both images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(50, 50, 150, 150), filename=str(rgb_path))
        page.insert_image(fitz.Rect(200, 200, 300, 300), filename=str(gray_path))
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify both images detected with metadata
        assert len(images) == 2
        assert all("colorspace" in img for img in images)
        assert all("bits_per_component" in img for img in images)

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        """Test error handling when PDF file doesn't exist."""
        pdf_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            detect_embedded_images(pdf_path)

        assert "not found" in str(exc_info.value)

    def test_path_is_not_a_file(self, tmp_path: Path) -> None:
        """Test error handling when path is a directory, not a file."""
        dir_path = tmp_path / "directory"
        dir_path.mkdir()

        with pytest.raises(PDFImageDetectionError) as exc_info:
            detect_embedded_images(dir_path)

        assert "not a file" in str(exc_info.value)

    def test_corrupted_pdf_error(self, tmp_path: Path) -> None:
        """Test error handling for corrupted PDF files."""
        pdf_path = tmp_path / "corrupted.pdf"
        pdf_path.write_text("This is not a valid PDF file")

        with pytest.raises(PDFImageDetectionError) as exc_info:
            detect_embedded_images(pdf_path)

        assert "Invalid or corrupted" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_image_detector.fitz.open")
    def test_password_protected_pdf_error(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for password-protected PDFs."""
        pdf_path = tmp_path / "protected.pdf"
        pdf_path.touch()

        mock_fitz_open.side_effect = RuntimeError("Password required")

        with pytest.raises(PDFImageDetectionError) as exc_info:
            detect_embedded_images(pdf_path)

        assert "Password-protected" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_image_detector.fitz.open")
    def test_generic_runtime_error(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for generic runtime errors."""
        pdf_path = tmp_path / "error.pdf"
        pdf_path.touch()

        mock_fitz_open.side_effect = RuntimeError("Some other error")

        with pytest.raises(PDFImageDetectionError) as exc_info:
            detect_embedded_images(pdf_path)

        assert "Error opening PDF" in str(exc_info.value)

    @patch("image_preprocessing_detector.classification.pdf_image_detector.fitz.open")
    def test_unexpected_exception(
        self, mock_fitz_open: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling for unexpected exceptions."""
        pdf_path = tmp_path / "unexpected.pdf"
        pdf_path.touch()

        mock_fitz_open.side_effect = ValueError("Unexpected error")

        with pytest.raises(PDFImageDetectionError) as exc_info:
            detect_embedded_images(pdf_path)

        assert "Error opening PDF" in str(exc_info.value)

    def test_page_processing_error_continues(self, tmp_path: Path) -> None:
        """Test that page processing errors don't stop processing other pages."""
        pdf_path = tmp_path / "partial_error.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create PDF with multiple pages
        doc = fitz.open()
        for _i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_image(fitz.Rect(100, 100, 200, 200), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Mock to simulate error on page 2
        with patch(
            "image_preprocessing_detector.classification.pdf_image_detector.fitz.open"
        ) as mock_open:
            mock_doc = MagicMock()
            mock_doc.__len__ = MagicMock(return_value=3)

            # Page 1: success
            mock_page1 = Mock()
            mock_page1.get_images.return_value = [(1, 0, 100, 100, 8, None, None)]

            # Page 2: error
            mock_page2 = Mock()
            mock_page2.get_images.side_effect = Exception("Page error")

            # Page 3: success
            mock_page3 = Mock()
            mock_page3.get_images.return_value = [(2, 0, 100, 100, 8, None, None)]

            mock_doc.__getitem__.side_effect = [mock_page1, mock_page2, mock_page3]
            mock_doc.extract_image.return_value = {
                "width": 100,
                "height": 100,
                "colorspace": "RGB",
                "bpc": 8,
            }
            mock_doc.close = Mock()
            mock_open.return_value = mock_doc

            # Detect images - should continue despite page 2 error
            images = detect_embedded_images(pdf_path)

            # Verify pages 1 and 3 processed, page 2 skipped
            assert len(images) == 2

    def test_image_extraction_error_continues(self, tmp_path: Path) -> None:
        """Test that image extraction errors don't stop processing other images."""
        pdf_path = tmp_path / "image_error.pdf"

        # Create PDF
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(50, 50, 150, 150), filename=str(img_path))
        page.insert_image(fitz.Rect(200, 200, 300, 300), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Mock to simulate error on second image
        with patch(
            "image_preprocessing_detector.classification.pdf_image_detector.fitz.open"
        ) as mock_open:
            mock_doc = MagicMock()
            mock_doc.__len__ = MagicMock(return_value=1)

            mock_page = Mock()
            mock_page.get_images.return_value = [
                (1, 0, 100, 100, 8, None, None),
                (2, 0, 100, 100, 8, None, None),
            ]

            # First image: success, second image: error
            mock_doc.extract_image.side_effect = [
                {"width": 100, "height": 100, "colorspace": "RGB", "bpc": 8},
                Exception("Image extraction error"),
            ]

            mock_doc.__getitem__.return_value = mock_page
            mock_doc.close = Mock()
            mock_open.return_value = mock_doc

            # Detect images - should get first image, skip second
            images = detect_embedded_images(pdf_path)

            # Verify first image processed
            assert len(images) == 1

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test that function accepts string paths."""
        pdf_path = tmp_path / "string_path.pdf"

        # Create PDF without images
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(str(pdf_path))
        doc.close()

        # Pass as string
        images = detect_embedded_images(str(pdf_path))

        assert isinstance(images, list)
        assert len(images) == 0

    def test_returns_correct_metadata_structure(self, tmp_path: Path) -> None:
        """Test that returned metadata has correct structure."""
        pdf_path = tmp_path / "metadata_test.pdf"

        # Create image and PDF
        img = Image.new("RGB", (200, 150), color="blue")
        img_path = tmp_path / "test.jpg"
        img.save(str(img_path))

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(100, 100, 300, 250), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Detect images
        images = detect_embedded_images(pdf_path)

        # Verify structure
        assert len(images) == 1
        img_metadata = images[0]
        assert "page_number" in img_metadata
        assert "image_index" in img_metadata
        assert "width" in img_metadata
        assert "height" in img_metadata
        assert "colorspace" in img_metadata
        assert "bits_per_component" in img_metadata
        assert "xref" in img_metadata

        # Verify types
        assert isinstance(img_metadata["page_number"], int)
        assert isinstance(img_metadata["image_index"], int)
        assert isinstance(img_metadata["width"], int)
        assert isinstance(img_metadata["height"], int)
