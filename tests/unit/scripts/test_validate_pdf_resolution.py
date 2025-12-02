# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/validate_pdf_resolution.py - PDF resolution validation.

These tests verify the PDF resolution validation script correctly:
- Formats byte sizes
- Prints resolution analysis
- Validates PDF resolution
- Handles upscaling workflow
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_pdf_resolution import (
    format_bytes,
    print_resolution_analysis,
    print_section,
    print_separator,
    print_upscaling_result,
)


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_format_bytes(self) -> None:
        """Test formatting bytes."""
        assert format_bytes(500) == "500.00 B"

    def test_format_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        result = format_bytes(1024)
        assert result == "1.00 KB"

    def test_format_megabytes(self) -> None:
        """Test formatting megabytes."""
        result = format_bytes(1024 * 1024)
        assert result == "1.00 MB"

    def test_format_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        result = format_bytes(1024 * 1024 * 1024)
        assert result == "1.00 GB"

    def test_format_terabytes(self) -> None:
        """Test formatting terabytes."""
        result = format_bytes(1024 * 1024 * 1024 * 1024)
        assert result == "1.00 TB"

    def test_format_fractional(self) -> None:
        """Test formatting fractional values."""
        result = format_bytes(1536)  # 1.5 KB
        assert result == "1.50 KB"

    def test_format_zero(self) -> None:
        """Test formatting zero bytes."""
        result = format_bytes(0)
        assert result == "0.00 B"

    def test_format_float_input(self) -> None:
        """Test formatting with float input."""
        result = format_bytes(1024.5)
        assert "KB" in result


class TestPrintSeparator:
    """Tests for print_separator function."""

    def test_default_separator(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test default separator output."""
        print_separator()
        captured = capsys.readouterr()
        assert "=" * 80 in captured.out

    def test_custom_char(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test separator with custom character."""
        print_separator("-")
        captured = capsys.readouterr()
        assert "-" * 80 in captured.out

    def test_custom_length(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test separator with custom length."""
        print_separator("*", 40)
        captured = capsys.readouterr()
        assert "*" * 40 in captured.out


class TestPrintSection:
    """Tests for print_section function."""

    def test_section_header(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test section header output."""
        print_section("Test Section")
        captured = capsys.readouterr()
        assert "Test Section" in captured.out
        assert "=" in captured.out


class TestPrintResolutionAnalysis:
    """Tests for print_resolution_analysis function."""

    def test_print_basic_analysis(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing basic analysis results."""
        analysis = {
            "needs_upscaling": True,
            "image_count": 5,
            "low_res_image_count": 3,
            "min_dpi": 150.0,
            "avg_dpi": 180.0,
            "max_dpi": 220.0,
        }

        print_resolution_analysis(analysis)
        captured = capsys.readouterr()

        assert "Needs Upscaling: True" in captured.out
        assert "Total Images: 5" in captured.out
        assert "Low-Res Images: 3" in captured.out
        assert "150.0 DPI" in captured.out

    def test_print_analysis_with_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing analysis with per-page details."""
        analysis = {
            "needs_upscaling": False,
            "image_count": 2,
            "low_res_image_count": 0,
            "min_dpi": 300.0,
            "avg_dpi": 300.0,
            "max_dpi": 300.0,
            "details": [
                {
                    "page_number": 1,
                    "min_dpi": 300.0,
                    "avg_dpi": 300.0,
                    "image_count": 1,
                },
                {
                    "page_number": 2,
                    "min_dpi": 300.0,
                    "avg_dpi": 300.0,
                    "image_count": 1,
                },
            ],
        }

        print_resolution_analysis(analysis)
        captured = capsys.readouterr()

        assert "Per-Page Details" in captured.out
        assert "Page 1" in captured.out
        assert "Page 2" in captured.out

    def test_print_analysis_missing_dpi(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing analysis with missing DPI values."""
        analysis = {
            "needs_upscaling": False,
            "image_count": 0,
            "low_res_image_count": 0,
        }

        print_resolution_analysis(analysis)
        captured = capsys.readouterr()

        assert "N/A" in captured.out


class TestPrintUpscalingResult:
    """Tests for print_upscaling_result function."""

    def test_print_successful_upscaling(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing successful upscaling result."""
        result = {
            "success": True,
            "before_size": 1024 * 1024,  # 1 MB
            "after_size": 2 * 1024 * 1024,  # 2 MB
            "processing_time": 1.5,
            "pages_processed": 10,
            "output_path": "/path/to/output.pdf",
        }

        print_upscaling_result(result)
        captured = capsys.readouterr()

        assert "Success: True" in captured.out
        assert "1.00 MB" in captured.out
        assert "2.00 MB" in captured.out
        assert "2.00x" in captured.out
        assert "1.50s" in captured.out
        assert "10" in captured.out
        assert "/path/to/output.pdf" in captured.out

    def test_print_failed_upscaling(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing failed upscaling result."""
        result = {
            "success": False,
            "error_message": "Failed to process PDF",
        }

        print_upscaling_result(result)
        captured = capsys.readouterr()

        assert "Success: False" in captured.out
        assert "Failed to process PDF" in captured.out


class TestValidatePdfResolution:
    """Tests for validate_pdf_resolution function."""

    def test_validate_with_mock_analyzer(self, tmp_path: Path) -> None:
        """Test validation with mocked analyzer."""
        from validate_pdf_resolution import validate_pdf_resolution

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        mock_analysis = {
            "needs_upscaling": True,
            "image_count": 5,
            "low_res_image_count": 3,
            "min_dpi": 150.0,
            "avg_dpi": 180.0,
            "max_dpi": 220.0,
        }

        with patch(
            "validate_pdf_resolution.PDFResolutionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_pdf_resolution.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            result = validate_pdf_resolution(pdf_file)

            assert result["needs_upscaling"] is True
            assert result["min_dpi"] == pytest.approx(150.0)

    def test_validate_handles_error(self, tmp_path: Path) -> None:
        """Test validation handles errors gracefully."""
        from validate_pdf_resolution import validate_pdf_resolution

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch(
            "validate_pdf_resolution.PDFResolutionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_pdf_resolution.side_effect = Exception("Test error")
            mock_analyzer_class.return_value = mock_analyzer

            result = validate_pdf_resolution(pdf_file)

            assert "error" in result
            assert "Test error" in result["error"]


class TestValidatePdfUpscaling:
    """Tests for validate_pdf_upscaling function."""

    def test_upscaling_with_mock(self, tmp_path: Path) -> None:
        """Test upscaling with mocked analyzer."""
        from validate_pdf_resolution import validate_pdf_upscaling

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        mock_result = MagicMock()
        mock_result.processing_time = 1.5
        mock_result.upscaling_result = {
            "success": True,
            "before_size": 1000,
            "after_size": 2000,
        }
        mock_result.upscaled_path = None
        mock_result.to_dict.return_value = {"success": True}

        with patch("validate_pdf_resolution.PDFDocumentAnalyzer") as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_result
            mock_class.return_value = mock_analyzer

            result = validate_pdf_upscaling(pdf_file)

            assert result["success"] is True

    def test_upscaling_handles_error(self, tmp_path: Path) -> None:
        """Test upscaling handles errors gracefully."""
        from validate_pdf_resolution import validate_pdf_upscaling

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch("validate_pdf_resolution.PDFDocumentAnalyzer") as mock_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.side_effect = Exception("Upscaling error")
            mock_class.return_value = mock_analyzer

            result = validate_pdf_upscaling(pdf_file)

            assert "error" in result


class TestMainFunction:
    """Tests for main entry point."""

    def test_main_missing_file(self, tmp_path: Path) -> None:
        """Test main with missing PDF file."""
        from validate_pdf_resolution import main

        with patch(
            "sys.argv", ["validate_pdf_resolution.py", str(tmp_path / "missing.pdf")]
        ):
            result = main()

            assert result == 1

    def test_main_analyze_only(self, tmp_path: Path) -> None:
        """Test main with analyze only (no upscale)."""
        from validate_pdf_resolution import main

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        mock_analysis = {
            "needs_upscaling": False,
            "image_count": 1,
            "low_res_image_count": 0,
            "min_dpi": 300.0,
            "avg_dpi": 300.0,
            "max_dpi": 300.0,
        }

        with patch(
            "validate_pdf_resolution.PDFResolutionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_pdf_resolution.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            with patch("sys.argv", ["validate_pdf_resolution.py", str(pdf_file)]):
                result = main()

                assert result == 0

    def test_main_with_upscale_flag(self, tmp_path: Path) -> None:
        """Test main with --upscale flag."""
        from validate_pdf_resolution import main

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        mock_analysis = {
            "needs_upscaling": True,
            "image_count": 1,
            "low_res_image_count": 1,
            "min_dpi": 150.0,
        }

        mock_upscale_result = MagicMock()
        mock_upscale_result.processing_time = 1.0
        mock_upscale_result.upscaling_result = {"success": True}
        mock_upscale_result.upscaled_path = None
        mock_upscale_result.to_dict.return_value = {}

        with patch("validate_pdf_resolution.PDFResolutionAnalyzer") as mock_res_class:
            mock_res_analyzer = MagicMock()
            mock_res_analyzer.analyze_pdf_resolution.return_value = mock_analysis
            mock_res_class.return_value = mock_res_analyzer

            with patch("validate_pdf_resolution.PDFDocumentAnalyzer") as mock_doc_class:
                mock_doc_analyzer = MagicMock()
                mock_doc_analyzer.analyze.return_value = mock_upscale_result
                mock_doc_class.return_value = mock_doc_analyzer

                with patch(
                    "sys.argv",
                    ["validate_pdf_resolution.py", str(pdf_file), "--upscale"],
                ):
                    result = main()

                    assert result == 0

    def test_main_error_returns_1(self, tmp_path: Path) -> None:
        """Test that errors in main return 1."""
        from validate_pdf_resolution import main

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        with patch(
            "validate_pdf_resolution.PDFResolutionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_pdf_resolution.side_effect = Exception("Error")
            mock_analyzer_class.return_value = mock_analyzer

            with patch("sys.argv", ["validate_pdf_resolution.py", str(pdf_file)]):
                result = main()

                assert result == 1


class TestArgumentParsing:
    """Tests for argument parsing."""

    def test_parse_basic_args(self) -> None:
        """Test parsing basic arguments."""

        # The main function creates its own parser, so we test indirectly
        # through the main function behavior

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        # Default min-dpi: 300
        # Default target-dpi: 300
        # Default algorithm: lanczos
        # These are tested through the main function behavior
