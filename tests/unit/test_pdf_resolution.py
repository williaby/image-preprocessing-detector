# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

"""Unit tests for PDF resolution detection."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from image_preprocessing_detector.ingestion.pdf_resolution import (
    PDFResolutionAnalyzer,
    quick_resolution_check,
)


class TestPDFResolutionAnalyzer:
    """Test cases for PDFResolutionAnalyzer."""

    def test_init(self) -> None:
        """Test analyzer initialization."""
        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=200)
        assert analyzer.min_dpi_threshold == 200

    def test_init_default(self) -> None:
        """Test analyzer initialization with default values."""
        analyzer = PDFResolutionAnalyzer()
        assert analyzer.min_dpi_threshold == 300

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_no_images(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test analysis of PDF with no images."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True

        # Mock PyMuPDF document with no images
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_images.return_value = []  # No images
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution("/fake/path.pdf")

        assert result["needs_upscaling"] is False
        assert result["min_dpi"] is None
        assert result["avg_dpi"] is None
        assert result["max_dpi"] is None
        assert result["image_count"] == 0
        assert result["low_res_image_count"] == 0

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_high_res(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test analysis of high-resolution PDF."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True
        # Mock PyMuPDF document with high-res image
        mock_doc = MagicMock()
        mock_page = MagicMock()

        # Mock image list (XREF=1)
        mock_page.get_images.return_value = [[1, 0, 0, 0, 0, 0, 0, 0]]

        # Mock pixmap with 300 DPI image
        mock_pix = MagicMock()
        mock_pix.width = 3000  # 3000 pixels width
        mock_pix.height = 2000  # 2000 pixels height

        # Mock bbox (10 inches x 6.67 inches at 72 DPI = 3000px / 10in = 300 DPI)
        mock_bbox = MagicMock()
        mock_bbox.x0 = 0
        mock_bbox.y0 = 0
        mock_bbox.x1 = 720  # 10 inches * 72 points/inch
        mock_bbox.y1 = 480  # 6.67 inches * 72 points/inch

        mock_page.get_image_bbox.return_value = mock_bbox

        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Pixmap.return_value = mock_pix

        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution("/fake/path.pdf")

        assert result["needs_upscaling"] is False  # 300 DPI meets threshold
        assert result["min_dpi"] == 300.0
        assert result["image_count"] == 1
        assert result["low_res_image_count"] == 0

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_low_res(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test analysis of low-resolution PDF."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True
        # Mock PyMuPDF document with low-res image
        mock_doc = MagicMock()
        mock_page = MagicMock()

        # Mock image list
        mock_page.get_images.return_value = [[1, 0, 0, 0, 0, 0, 0, 0]]

        # Mock pixmap with 150 DPI image
        mock_pix = MagicMock()
        mock_pix.width = 1500  # 1500 pixels width
        mock_pix.height = 1000  # 1000 pixels height

        # Mock bbox (10 inches x 6.67 inches at 72 DPI = 1500px / 10in = 150 DPI)
        mock_bbox = MagicMock()
        mock_bbox.x0 = 0
        mock_bbox.y0 = 0
        mock_bbox.x1 = 720  # 10 inches * 72 points/inch
        mock_bbox.y1 = 480  # 6.67 inches * 72 points/inch

        mock_page.get_image_bbox.return_value = mock_bbox

        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Pixmap.return_value = mock_pix

        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution("/fake/path.pdf")

        assert result["needs_upscaling"] is True  # 150 DPI below threshold
        assert result["min_dpi"] == 150.0
        assert result["image_count"] == 1
        assert result["low_res_image_count"] == 1

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_multiple_pages(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test analysis of multi-page PDF with mixed resolutions."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True
        # Mock PyMuPDF document with 2 pages
        mock_doc = MagicMock()

        # Page 1: High res (300 DPI)
        mock_page1 = MagicMock()
        mock_page1.get_images.return_value = [[1, 0, 0, 0, 0, 0, 0, 0]]
        mock_pix1 = MagicMock()
        mock_pix1.width = 3000
        mock_pix1.height = 2000
        mock_bbox1 = MagicMock()
        mock_bbox1.x0, mock_bbox1.y0, mock_bbox1.x1, mock_bbox1.y1 = 0, 0, 720, 480
        mock_page1.get_image_bbox.return_value = mock_bbox1

        # Page 2: Low res (150 DPI)
        mock_page2 = MagicMock()
        mock_page2.get_images.return_value = [[2, 0, 0, 0, 0, 0, 0, 0]]
        mock_pix2 = MagicMock()
        mock_pix2.width = 1500
        mock_pix2.height = 1000
        mock_bbox2 = MagicMock()
        mock_bbox2.x0, mock_bbox2.y0, mock_bbox2.x1, mock_bbox2.y1 = 0, 0, 720, 480
        mock_page2.get_image_bbox.return_value = mock_bbox2

        mock_doc.__len__.return_value = 2
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Pixmap.side_effect = [mock_pix1, mock_pix2]

        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution("/fake/path.pdf")

        assert result["needs_upscaling"] is True  # Min is 150 DPI
        assert result["min_dpi"] == 150.0  # Lowest DPI across all pages
        assert result["max_dpi"] == 300.0  # Highest DPI
        assert result["image_count"] == 2
        assert result["low_res_image_count"] == 1  # One image below threshold
        assert len(result["details"]) == 2  # Two pages analyzed

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_zero_bbox(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test handling of images with zero-sized bounding boxes."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True
        # Mock PyMuPDF document with zero-sized bbox
        mock_doc = MagicMock()
        mock_page = MagicMock()

        mock_page.get_images.return_value = [[1, 0, 0, 0, 0, 0, 0, 0]]

        mock_pix = MagicMock()
        mock_pix.width = 3000
        mock_pix.height = 2000

        # Zero-sized bbox (edge case)
        mock_bbox = MagicMock()
        mock_bbox.x0 = 0
        mock_bbox.y0 = 0
        mock_bbox.x1 = 0  # Zero width
        mock_bbox.y1 = 0  # Zero height

        mock_page.get_image_bbox.return_value = mock_bbox

        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Pixmap.return_value = mock_pix

        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution("/fake/path.pdf")

        # Should skip image with zero bbox
        assert result["needs_upscaling"] is False
        assert result["image_count"] == 0

    def test_analyze_pdf_file_not_found(self) -> None:
        """Test handling of non-existent PDF file."""
        analyzer = PDFResolutionAnalyzer()

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            analyzer.analyze_pdf_resolution("/nonexistent/path.pdf")

    @patch("image_preprocessing_detector.ingestion.pdf_resolution.Path")
    @patch("image_preprocessing_detector.ingestion.pdf_resolution.fitz")
    def test_analyze_pdf_resolution_error(
        self, mock_fitz: Mock, mock_path: Mock
    ) -> None:
        """Test handling of PDF analysis errors."""
        # Mock Path.exists() to return True
        mock_path.return_value.exists.return_value = True

        mock_fitz.open.side_effect = Exception("PDF corrupted")

        analyzer = PDFResolutionAnalyzer()

        with pytest.raises(Exception, match="PDF corrupted"):
            analyzer.analyze_pdf_resolution("/fake/path.pdf")


class TestQuickResolutionCheck:
    """Test cases for quick_resolution_check function."""

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.PDFResolutionAnalyzer"
    )
    def test_quick_check_needs_upscaling(self, mock_analyzer_class: Mock) -> None:
        """Test quick check when upscaling is needed."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": True,
            "min_dpi": 150.0,
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = quick_resolution_check("/fake/path.pdf", min_dpi=300)

        assert result is True
        mock_analyzer_class.assert_called_once_with(min_dpi_threshold=300)

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.PDFResolutionAnalyzer"
    )
    def test_quick_check_no_upscaling_needed(self, mock_analyzer_class: Mock) -> None:
        """Test quick check when upscaling is not needed."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": False,
            "min_dpi": 350.0,
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = quick_resolution_check("/fake/path.pdf", min_dpi=300)

        assert result is False

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.PDFResolutionAnalyzer"
    )
    def test_quick_check_error_handling(self, mock_analyzer_class: Mock) -> None:
        """Test quick check error handling."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_pdf_resolution.side_effect = Exception("Analysis failed")
        mock_analyzer_class.return_value = mock_analyzer

        result = quick_resolution_check("/fake/path.pdf")

        assert result is False  # Returns False on error
