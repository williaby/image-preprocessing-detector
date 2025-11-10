# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: F841
"""Unit tests for PDF upscaling."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from image_preprocessing_detector.ingestion.pdf_upscaler import (
    PDFUpscaler,
    UpscaleAlgorithm,
    upscale_if_needed,
)


class TestUpscaleAlgorithm:
    """Test cases for UpscaleAlgorithm enum."""

    def test_algorithm_values(self) -> None:
        """Test algorithm enum values."""
        assert UpscaleAlgorithm.BICUBIC.value == "bicubic"
        assert UpscaleAlgorithm.LANCZOS.value == "lanczos"
        assert UpscaleAlgorithm.INTER_CUBIC.value == "inter_cubic"
        assert UpscaleAlgorithm.INTER_LINEAR.value == "inter_linear"
        assert UpscaleAlgorithm.INTER_AREA.value == "inter_area"


class TestPDFUpscaler:
    """Test cases for PDFUpscaler."""

    def test_init(self) -> None:
        """Test upscaler initialization."""
        upscaler = PDFUpscaler(
            target_dpi=600,
            algorithm=UpscaleAlgorithm.BICUBIC,
            preserve_original=False,
        )

        assert upscaler.target_dpi == 600
        assert upscaler.algorithm == UpscaleAlgorithm.BICUBIC
        assert upscaler.preserve_original is False

    def test_init_defaults(self) -> None:
        """Test upscaler initialization with defaults."""
        upscaler = PDFUpscaler()

        assert upscaler.target_dpi == 300
        assert upscaler.algorithm == UpscaleAlgorithm.LANCZOS
        assert upscaler.preserve_original is True

    def test_upscale_pdf_file_not_found(self) -> None:
        """Test upscaling with non-existent file."""
        upscaler = PDFUpscaler()

        with pytest.raises(FileNotFoundError, match="Input PDF not found"):
            upscaler.upscale_pdf("/nonexistent/path.pdf")

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.fitz")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.Image")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.Path")
    @patch(
        "image_preprocessing_detector.ingestion.pdf_upscaler.tempfile.NamedTemporaryFile"
    )
    def test_upscale_pdf_success(
        self,
        mock_tempfile: Mock,
        mock_path_class: Mock,
        mock_image: Mock,
        mock_cv2: Mock,
        mock_fitz: Mock,
    ) -> None:
        """Test successful PDF upscaling."""
        # Mock input file
        mock_input_path = MagicMock(spec=Path)
        mock_input_path.exists.return_value = True
        mock_input_path.stat.return_value.st_size = 1000
        mock_input_path.parent = Path("/fake")
        mock_input_path.stem = "test"
        mock_input_path.name = "test.pdf"

        # Mock output file
        mock_output_path = MagicMock(spec=Path)
        mock_output_path.stat.return_value.st_size = 2000
        mock_output_path.name = "test_upscaled.pdf"

        # Mock Path class to return our mocks
        mock_path_class.side_effect = [mock_input_path, mock_output_path]

        # Mock PyMuPDF document
        mock_doc = MagicMock()
        mock_new_doc = MagicMock()
        mock_page = MagicMock()

        mock_page.rect.width = 612  # 8.5 inches * 72
        mock_page.rect.height = 792  # 11 inches * 72

        # Mock pixmap
        mock_pix = MagicMock()
        mock_pix.width = 2550  # 8.5 * 300 DPI
        mock_pix.height = 3300  # 11 * 300 DPI
        mock_pix.n = 3  # RGB
        mock_pix.samples = np.zeros((3300, 2550, 3), dtype=np.uint8).tobytes()

        mock_page.get_pixmap.return_value = mock_pix

        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.side_effect = [mock_doc, mock_new_doc]
        mock_fitz.Matrix.return_value = MagicMock()

        # Mock new page
        mock_new_page = MagicMock()
        mock_new_page.rect = MagicMock()
        mock_new_doc.new_page.return_value = mock_new_page

        # Mock image processing
        mock_img_array = np.zeros((3300, 2550, 3), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = mock_img_array
        mock_cv2.resize.return_value = mock_img_array

        mock_pil_img = MagicMock()
        mock_pil_img.tobytes.return_value = b"fake_image_data"
        mock_image.fromarray.return_value = mock_pil_img

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/fake.png"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        upscaler = PDFUpscaler(target_dpi=300)
        result = upscaler.upscale_pdf(
            input_path=str(mock_input_path),
            output_path=str(mock_output_path),
        )

        assert result["success"] is True
        assert result["pages_processed"] == 1
        assert result["before_size"] == 1000
        assert result["after_size"] == 2000
        assert "processing_time" in result

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.fitz")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.Path")
    def test_upscale_pdf_error_handling(
        self,
        mock_path_class: Mock,
        mock_fitz: Mock,
    ) -> None:
        """Test PDF upscaling error handling."""
        # Mock input file
        mock_input_path = MagicMock(spec=Path)
        mock_input_path.exists.return_value = True
        mock_input_path.stat.return_value.st_size = 1000
        mock_input_path.name = "test.pdf"

        mock_path_class.return_value = mock_input_path

        # Mock PDF opening failure
        mock_fitz.open.side_effect = Exception("PDF corrupted")

        upscaler = PDFUpscaler()
        result = upscaler.upscale_pdf(str(mock_input_path))

        assert result["success"] is False
        assert "PDF corrupted" in result["error_message"]
        assert result["pages_processed"] == 0

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    def test_apply_upscaling_bicubic(self, mock_cv2: Mock) -> None:
        """Test bicubic upscaling algorithm."""
        upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.BICUBIC)

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        result = upscaler._apply_upscaling(img, 200, 200)

        mock_cv2.resize.assert_called_once()
        call_args = mock_cv2.resize.call_args
        assert call_args[0][1] == (200, 200)  # Target dimensions

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.np.array")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.Image")
    def test_apply_upscaling_lanczos(
        self, mock_image: Mock, mock_cv2: Mock, mock_np_array: Mock
    ) -> None:
        """Test Lanczos upscaling algorithm."""
        upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.LANCZOS)

        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock PIL operations
        mock_pil_img = MagicMock()
        mock_pil_img.resize.return_value = mock_pil_img
        mock_image.fromarray.return_value = mock_pil_img
        mock_cv2.cvtColor.return_value = img
        mock_np_array.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        result = upscaler._apply_upscaling(img, 200, 200)

        # Verify PIL resize was called with Lanczos
        mock_pil_img.resize.assert_called_once()

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    def test_apply_upscaling_inter_cubic(self, mock_cv2: Mock) -> None:
        """Test inter_cubic upscaling algorithm."""
        upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.INTER_CUBIC)

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        result = upscaler._apply_upscaling(img, 200, 200)

        mock_cv2.resize.assert_called_once()

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    def test_apply_upscaling_inter_linear(self, mock_cv2: Mock) -> None:
        """Test inter_linear upscaling algorithm."""
        upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.INTER_LINEAR)

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        result = upscaler._apply_upscaling(img, 200, 200)

        mock_cv2.resize.assert_called_once()

    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.cv2")
    def test_apply_upscaling_inter_area(self, mock_cv2: Mock) -> None:
        """Test inter_area upscaling algorithm."""
        upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.INTER_AREA)

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.resize.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        result = upscaler._apply_upscaling(img, 200, 200)

        mock_cv2.resize.assert_called_once()


class TestUpscaleIfNeeded:
    """Test cases for upscale_if_needed function."""

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.quick_resolution_check"
    )
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.PDFUpscaler")
    def test_upscale_if_needed_upscaling_needed(
        self,
        mock_upscaler_class: Mock,
        mock_quick_check: Mock,
    ) -> None:
        """Test upscale_if_needed when upscaling is needed."""
        mock_quick_check.return_value = True

        mock_upscaler = MagicMock()
        mock_upscaler.upscale_pdf.return_value = {
            "success": True,
            "output_path": "/fake/upscaled.pdf",
            "processing_time": 1.5,
        }
        mock_upscaler_class.return_value = mock_upscaler

        result = upscale_if_needed("/fake/input.pdf", min_dpi=300, target_dpi=300)

        assert result["success"] is True
        assert result["output_path"] == "/fake/upscaled.pdf"
        mock_quick_check.assert_called_once_with("/fake/input.pdf", 300)
        mock_upscaler.upscale_pdf.assert_called_once()

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.quick_resolution_check"
    )
    def test_upscale_if_needed_skipped(self, mock_quick_check: Mock) -> None:
        """Test upscale_if_needed when upscaling is not needed."""
        mock_quick_check.return_value = False

        result = upscale_if_needed("/fake/input.pdf")

        assert result["success"] is True
        assert result["upscaling_skipped"] is True
        assert result["output_path"] == "/fake/input.pdf"
        assert result["processing_time"] == 0

    @patch(
        "image_preprocessing_detector.ingestion.pdf_resolution.quick_resolution_check"
    )
    @patch("image_preprocessing_detector.ingestion.pdf_upscaler.PDFUpscaler")
    def test_upscale_if_needed_with_output_path(
        self,
        mock_upscaler_class: Mock,
        mock_quick_check: Mock,
    ) -> None:
        """Test upscale_if_needed with custom output path."""
        mock_quick_check.return_value = True

        mock_upscaler = MagicMock()
        mock_upscaler.upscale_pdf.return_value = {
            "success": True,
            "output_path": "/custom/output.pdf",
        }
        mock_upscaler_class.return_value = mock_upscaler

        result = upscale_if_needed(
            "/fake/input.pdf",
            output_path="/custom/output.pdf",
        )

        assert result["success"] is True
        mock_upscaler.upscale_pdf.assert_called_once_with(
            "/fake/input.pdf",
            "/custom/output.pdf",
        )
