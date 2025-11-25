"""
Unit tests for PDF analyzer module.

Tests the PDFDocumentAnalyzer class and PDFPreflightResult model.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.ingestion.pdf_analyzer import (
    PDFDocumentAnalyzer,
    PDFPreflightResult,
)


class TestPDFPreflightResult:
    """Tests for PDFPreflightResult dataclass."""

    def test_to_dict(self) -> None:
        """Test to_dict() method converts all fields correctly."""
        result = PDFPreflightResult(
            needs_upscaling=True,
            resolution_analysis={"min_dpi": 150, "needs_upscaling": True},
            upscaled_path="/tmp/upscaled.pdf",  # nosec B108 - test fixture path
            upscaling_result={"success": True},
            processing_time=1.23,
        )

        result_dict = result.to_dict()

        assert result_dict["needs_upscaling"] is True
        assert result_dict["resolution_analysis"]["min_dpi"] == 150
        assert result_dict["upscaled_path"] == "/tmp/upscaled.pdf"  # nosec B108
        assert result_dict["upscaling_result"]["success"] is True
        assert result_dict["processing_time"] == pytest.approx(1.23)
        assert result_dict["should_use_upscaled"] is True
        assert result_dict["recommended_path"] == "/tmp/upscaled.pdf"  # nosec B108

    def test_should_use_upscaled_false_when_no_upscaling(self) -> None:
        """Test should_use_upscaled is False when upscaling wasn't performed."""
        result = PDFPreflightResult(
            needs_upscaling=False,
            resolution_analysis={"min_dpi": 300, "needs_upscaling": False},
            processing_time=0.5,
        )

        assert result.should_use_upscaled is False
        assert result.recommended_path is None

    def test_should_use_upscaled_false_when_upscaling_failed(self) -> None:
        """Test should_use_upscaled is False when upscaling failed."""
        result = PDFPreflightResult(
            needs_upscaling=True,
            resolution_analysis={"min_dpi": 150, "needs_upscaling": True},
            upscaling_result={"success": False, "error_message": "Failed"},
            processing_time=1.0,
        )

        assert result.should_use_upscaled is False
        assert result.recommended_path is None


class TestPDFDocumentAnalyzer:
    """Tests for PDFDocumentAnalyzer class."""

    def test_init_with_default_settings(self) -> None:
        """Test initialization with default settings."""
        analyzer = PDFDocumentAnalyzer()

        assert analyzer.settings is not None
        assert analyzer.settings.enable_pdf_upscaling is True

    def test_init_with_custom_settings(self) -> None:
        """Test initialization with custom settings."""
        settings = Settings(enable_pdf_upscaling=False)
        analyzer = PDFDocumentAnalyzer(settings=settings)

        assert analyzer.settings.enable_pdf_upscaling is False

    def test_analyze_file_not_found(self) -> None:
        """Test analyze() raises FileNotFoundError for missing PDF."""
        analyzer = PDFDocumentAnalyzer()

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            analyzer.analyze(Path("/nonexistent/file.pdf"))

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    def test_analyze_resolution_analysis_failure(
        self, mock_analyzer_class: Mock, tmp_path: Path
    ) -> None:
        """Test analyze() handles resolution analysis exceptions gracefully."""
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        # Mock resolution analyzer to raise exception
        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.side_effect = RuntimeError(
            "Analysis failed"
        )
        mock_analyzer_class.return_value = mock_resolution_analyzer

        analyzer = PDFDocumentAnalyzer()

        result = analyzer.analyze(pdf_path)

        # Should return a result indicating failure, not raise exception
        assert result.needs_upscaling is False
        assert "error" in result.resolution_analysis
        assert "Analysis failed" in str(result.resolution_analysis["error"])
        assert result.processing_time > 0

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFUpscaler")
    def test_analyze_upscaling_failure(
        self,
        mock_upscaler_class: Mock,
        mock_analyzer_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Test analyze() handles upscaling failure gracefully."""
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        # Mock resolution analyzer to indicate upscaling needed
        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": True,
            "min_dpi": 150,
        }
        mock_analyzer_class.return_value = mock_resolution_analyzer

        # Mock upscaler to return failure
        mock_upscaler = Mock()
        mock_upscaler.upscale_pdf.return_value = {
            "success": False,
            "error_message": "Upscaling error",
        }
        mock_upscaler_class.return_value = mock_upscaler

        analyzer = PDFDocumentAnalyzer()

        result = analyzer.analyze(pdf_path, perform_upscaling=True)

        # Should handle failure gracefully
        assert result.needs_upscaling is True
        assert result.upscaled_path is None
        assert result.upscaling_result["success"] is False
        assert result.should_use_upscaled is False

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFUpscaler")
    def test_analyze_upscaling_exception(
        self,
        mock_upscaler_class: Mock,
        mock_analyzer_class: Mock,
        tmp_path: Path,
    ) -> None:
        """Test analyze() handles upscaling exceptions gracefully."""
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        # Mock resolution analyzer to indicate upscaling needed
        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": True,
            "min_dpi": 150,
        }
        mock_analyzer_class.return_value = mock_resolution_analyzer

        # Mock upscaler to raise exception
        mock_upscaler = Mock()
        mock_upscaler.upscale_pdf.side_effect = RuntimeError("Upscaler crashed")
        mock_upscaler_class.return_value = mock_upscaler

        analyzer = PDFDocumentAnalyzer()

        result = analyzer.analyze(pdf_path, perform_upscaling=True)

        # Should handle exception gracefully
        assert result.needs_upscaling is True
        assert result.upscaled_path is None
        assert result.upscaling_result["success"] is False
        assert "Upscaler crashed" in result.upscaling_result["error_message"]
        assert result.should_use_upscaled is False

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    def test_quick_check_success(
        self, mock_analyzer_class: Mock, tmp_path: Path
    ) -> None:
        """Test quick_check() returns True when upscaling needed."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": True
        }
        mock_analyzer_class.return_value = mock_resolution_analyzer

        analyzer = PDFDocumentAnalyzer()

        assert analyzer.quick_check(pdf_path) is True

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    def test_quick_check_no_upscaling_needed(
        self, mock_analyzer_class: Mock, tmp_path: Path
    ) -> None:
        """Test quick_check() returns False when upscaling not needed."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.return_value = {
            "needs_upscaling": False
        }
        mock_analyzer_class.return_value = mock_resolution_analyzer

        analyzer = PDFDocumentAnalyzer()

        assert analyzer.quick_check(pdf_path) is False

    @patch("image_preprocessing_detector.ingestion.pdf_analyzer.PDFResolutionAnalyzer")
    def test_quick_check_exception_handling(
        self, mock_analyzer_class: Mock, tmp_path: Path
    ) -> None:
        """Test quick_check() returns False on exception."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")

        mock_resolution_analyzer = Mock()
        mock_resolution_analyzer.analyze_pdf_resolution.side_effect = RuntimeError(
            "Check failed"
        )
        mock_analyzer_class.return_value = mock_resolution_analyzer

        analyzer = PDFDocumentAnalyzer()

        # Should return False on error, not raise exception
        assert analyzer.quick_check(pdf_path) is False
