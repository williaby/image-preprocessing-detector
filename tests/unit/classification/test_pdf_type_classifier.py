"""
Unit tests for PDF type classification.

Tests the classify_pdf_type function with various PDF types.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import fitz  # PyMuPDF
from PIL import Image

from image_preprocessing_detector.classification.pdf_type_classifier import (
    classify_pdf_type,
)
from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.schema import PDFType


class TestClassifyPDFType:
    """Tests for classify_pdf_type function."""

    def test_classify_born_digital_pdf(self, tmp_path: Path) -> None:
        """Test classification of text-only PDF as born_digital."""
        pdf_path = tmp_path / "born_digital.pdf"

        # Create text-only PDF with >50 characters
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "This is a text-based document created digitally.")
        page.insert_text((100, 150), "It contains no images, only extractable text.")
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Verify
        assert pdf_type == PDFType.BORN_DIGITAL

    def test_classify_image_only_pdf(self, tmp_path: Path) -> None:
        """Test classification of image-only PDF as image_only."""
        pdf_path = tmp_path / "image_only.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create PDF with image only (minimal/no text)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(100, 100, 300, 300), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Verify
        assert pdf_type == PDFType.IMAGE_ONLY

    def test_classify_hybrid_pdf_text_and_images(self, tmp_path: Path) -> None:
        """Test classification of PDF with both text and images as hybrid."""
        pdf_path = tmp_path / "hybrid.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="blue")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create PDF with both text and images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "This document has both text and images.")
        page.insert_image(fitz.Rect(100, 200, 300, 400), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Verify
        assert pdf_type == PDFType.HYBRID

    def test_classify_hybrid_pdf_minimal_text_no_images(self, tmp_path: Path) -> None:
        """Test classification as hybrid when text is between thresholds and no images."""
        pdf_path = tmp_path / "hybrid_minimal_text.pdf"

        # Create PDF with text between 10-50 characters, no images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Some text content")  # ~17 characters
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Verify - should be hybrid (text > 10, but <= 50, and no images)
        assert pdf_type == PDFType.HYBRID

    def test_classify_hybrid_pdf_long_text_with_images(self, tmp_path: Path) -> None:
        """Test classification as hybrid when text >50 chars but has images."""
        pdf_path = tmp_path / "hybrid_long_text.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="green")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create PDF with long text + images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            (100, 100),
            "This is a long text document with more than fifty characters of content.",
        )
        page.insert_image(fitz.Rect(100, 200, 300, 400), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Verify - should be hybrid (text > 50 but has images)
        assert pdf_type == PDFType.HYBRID

    def test_custom_thresholds_via_parameters(self, tmp_path: Path) -> None:
        """Test classification with custom thresholds passed as parameters."""
        pdf_path = tmp_path / "custom_threshold.pdf"

        # Create PDF with 25 characters of text, no images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Exactly 25 characters!!")  # 23-25 chars
        doc.save(str(pdf_path))
        doc.close()

        # With default thresholds (10, 50): should be hybrid
        pdf_type_default = classify_pdf_type(pdf_path)
        assert pdf_type_default == PDFType.HYBRID

        # With custom thresholds (20, 30): text < 30, so should be hybrid
        # But with (5, 20): text > 20, so should be born_digital
        pdf_type_custom = classify_pdf_type(
            pdf_path, text_min_threshold=5, text_max_threshold=20
        )
        assert pdf_type_custom == PDFType.BORN_DIGITAL

    def test_custom_thresholds_via_settings(self, tmp_path: Path) -> None:
        """Test classification with custom thresholds via Settings object."""
        pdf_path = tmp_path / "settings_threshold.pdf"

        # Create PDF with 30 characters of text, no images
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "This has thirty characters!!!")
        doc.save(str(pdf_path))
        doc.close()

        # Custom settings
        settings = Settings(pdf_text_min_threshold=25, pdf_text_max_threshold=35)

        # Classify with custom settings
        pdf_type = classify_pdf_type(pdf_path, settings=settings)

        # 30 chars is between 25-35, no images → hybrid
        assert pdf_type == PDFType.HYBRID

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test that function accepts string paths."""
        pdf_path = tmp_path / "string_path.pdf"

        # Create simple text PDF with >50 characters
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            (100, 100),
            "This is a text document with sufficient content for classification.",
        )
        doc.save(str(pdf_path))
        doc.close()

        # Pass as string
        pdf_type = classify_pdf_type(str(pdf_path))

        assert pdf_type == PDFType.BORN_DIGITAL

    def test_empty_pdf_classified_as_hybrid(self, tmp_path: Path) -> None:
        """Test that empty PDF is classified as hybrid."""
        pdf_path = tmp_path / "empty.pdf"

        # Create empty PDF
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # 0 chars text, 0 images → should be hybrid (edge case)
        assert pdf_type == PDFType.HYBRID

    def test_multipage_text_pdf_born_digital(self, tmp_path: Path) -> None:
        """Test classification of multi-page text PDF as born_digital."""
        pdf_path = tmp_path / "multipage_text.pdf"

        # Create multi-page text PDF
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((100, 100), f"Page {i + 1} content with sufficient text.")
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Should be born_digital (lots of text, no images)
        assert pdf_type == PDFType.BORN_DIGITAL

    def test_multipage_image_pdf_image_only(self, tmp_path: Path) -> None:
        """Test classification of multi-page image PDF as image_only."""
        pdf_path = tmp_path / "multipage_images.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create multi-page image PDF
        doc = fitz.open()
        for _i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_image(fitz.Rect(100, 100, 300, 300), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Should be image_only (minimal text, has images)
        assert pdf_type == PDFType.IMAGE_ONLY

    def test_multipage_hybrid_pdf(self, tmp_path: Path) -> None:
        """Test classification of multi-page hybrid PDF."""
        pdf_path = tmp_path / "multipage_hybrid.pdf"

        # Create image
        img = Image.new("RGB", (100, 100), color="blue")
        img_path = tmp_path / "image.jpg"
        img.save(str(img_path))

        # Create multi-page hybrid PDF
        doc = fitz.open()
        # Page 1: Text only
        page1 = doc.new_page(width=595, height=842)
        page1.insert_text((100, 100), "First page with text content.")
        # Page 2: Image only
        page2 = doc.new_page(width=595, height=842)
        page2.insert_image(fitz.Rect(100, 100, 300, 300), filename=str(img_path))
        # Page 3: Both
        page3 = doc.new_page(width=595, height=842)
        page3.insert_text((100, 100), "Third page with text.")
        page3.insert_image(fitz.Rect(100, 200, 300, 400), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        # Should be hybrid (has both text and images across pages)
        assert pdf_type == PDFType.HYBRID

    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.extract_text_from_pdf"
    )
    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.detect_embedded_images"
    )
    def test_classification_logic_born_digital(
        self,
        mock_detect_images: Mock,
        mock_extract_text: Mock,
        tmp_path: Path,
    ) -> None:
        """Test classification logic: text > 50, images = 0 → born_digital."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        # Mock returns
        mock_extract_text.return_value = "A" * 100  # 100 characters
        mock_detect_images.return_value = []  # No images

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        assert pdf_type == PDFType.BORN_DIGITAL

    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.extract_text_from_pdf"
    )
    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.detect_embedded_images"
    )
    def test_classification_logic_image_only(
        self,
        mock_detect_images: Mock,
        mock_extract_text: Mock,
        tmp_path: Path,
    ) -> None:
        """Test classification logic: text < 10, images > 0 → image_only."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        # Mock returns
        mock_extract_text.return_value = "AB"  # 2 characters
        mock_detect_images.return_value = [{"xref": 1}]  # Has images

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        assert pdf_type == PDFType.IMAGE_ONLY

    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.extract_text_from_pdf"
    )
    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.detect_embedded_images"
    )
    def test_classification_logic_hybrid_case_1(
        self,
        mock_detect_images: Mock,
        mock_extract_text: Mock,
        tmp_path: Path,
    ) -> None:
        """Test classification logic: text between thresholds → hybrid."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        # Mock returns: text = 30 (between 10-50), no images
        mock_extract_text.return_value = "A" * 30
        mock_detect_images.return_value = []

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        assert pdf_type == PDFType.HYBRID

    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.extract_text_from_pdf"
    )
    @patch(
        "image_preprocessing_detector.classification.pdf_type_classifier.detect_embedded_images"
    )
    def test_classification_logic_hybrid_case_2(
        self,
        mock_detect_images: Mock,
        mock_extract_text: Mock,
        tmp_path: Path,
    ) -> None:
        """Test classification logic: text > 50 but has images → hybrid."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        # Mock returns: text = 100, has images
        mock_extract_text.return_value = "A" * 100
        mock_detect_images.return_value = [{"xref": 1}]

        # Classify
        pdf_type = classify_pdf_type(pdf_path)

        assert pdf_type == PDFType.HYBRID
