"""
Unit tests for PDF loading and image conversion.
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from image_preprocessing_detector.ingestion.pdf_loader import (
    PageImage,
    PDFLoader,
    PDFPageTooLargeError,
    PDFTooManyPagesError,
    load_pdf,
)


class TestPageImage:
    """Test PageImage dataclass."""

    def test_page_image_creation(self) -> None:
        """Test creating a PageImage instance."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        page = PageImage(
            page_number=0,
            image=image,
            width=100,
            height=100,
            dpi_input=150.0,
            dpi_effective=300.0,
            needs_upscaling=True,
        )

        assert page.page_number == 0
        assert page.width == 100
        assert page.height == 100
        assert page.dpi_input == pytest.approx(150.0)
        assert page.dpi_effective == pytest.approx(300.0)
        assert page.needs_upscaling is True
        assert page.image.shape == (100, 100, 3)


class TestPDFLoader:
    """Test PDFLoader class."""

    def test_init_default_params(self) -> None:
        """Test PDFLoader initialization with defaults."""
        loader = PDFLoader()

        assert loader.target_dpi == 300
        assert loader.color_space == "RGB"
        assert loader.alpha is False

    def test_init_custom_params(self) -> None:
        """Test PDFLoader initialization with custom parameters."""
        loader = PDFLoader(target_dpi=600, color_space="GRAY", alpha=True)

        assert loader.target_dpi == 600
        assert loader.color_space == "GRAY"
        assert loader.alpha is True

    def test_load_file_not_found(self) -> None:
        """Test loading non-existent file raises FileNotFoundError."""
        loader = PDFLoader()

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            list(loader.load("/nonexistent/file.pdf"))

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_load_invalid_pdf(self, mock_fitz: Mock) -> None:
        """Test loading invalid PDF raises ValueError."""
        # Mock fitz.open to raise exception
        mock_fitz.open.side_effect = Exception("Invalid PDF")

        loader = PDFLoader()

        # Create a temporary file to pass existence check
        import tempfile

        with (
            tempfile.NamedTemporaryFile(suffix=".pdf") as tmp,
            pytest.raises(ValueError, match="Invalid PDF file"),
        ):
            list(loader.load(tmp.name))

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_load_single_page_pdf(self, mock_fitz: Mock) -> None:
        """Test loading a single-page PDF."""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        # Mock page
        mock_page = MagicMock()
        mock_page.rect.width = 612.0  # 8.5 inches * 72 DPI
        mock_page.rect.height = 792.0  # 11 inches * 72 DPI
        mock_page.get_images.return_value = []

        # Mock pixmap
        mock_pix = MagicMock()
        mock_pix.width = 2550  # 8.5 inches * 300 DPI
        mock_pix.height = 3300  # 11 inches * 300 DPI
        mock_pix.n = 3  # RGB
        mock_pix.samples = (np.zeros((3300, 2550, 3), dtype=np.uint8)).tobytes()

        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(target_dpi=300)

        # Create a temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 1
        page = pages[0]
        assert page.page_number == 0
        assert page.width == 2550
        assert page.height == 3300
        assert page.dpi_effective == pytest.approx(300.0)

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_load_multi_page_pdf(self, mock_fitz: Mock) -> None:
        """Test loading a multi-page PDF."""
        # Mock 3-page PDF document
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3

        # Mock page
        mock_page = MagicMock()
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_page.get_images.return_value = []

        # Mock pixmap
        mock_pix = MagicMock()
        mock_pix.width = 2550
        mock_pix.height = 3300
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((3300, 2550, 3), dtype=np.uint8)).tobytes()

        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(target_dpi=300)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 3
        for i, page in enumerate(pages):
            assert page.page_number == i

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_upscaling_detection_low_dpi(self, mock_fitz: Mock) -> None:
        """Test upscaling flag is set for low DPI pages."""
        # Mock PDF with low DPI images
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0

        # Mock low DPI image (150 DPI)
        mock_page.get_images.return_value = [(1,)]  # single image reference
        mock_doc.extract_image.return_value = {
            "width": 1275,  # 8.5 inches * 150 DPI
            "height": 1650,  # 11 inches * 150 DPI
        }
        mock_page.parent = mock_doc

        mock_pix = MagicMock()
        mock_pix.width = 2550
        mock_pix.height = 3300
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((3300, 2550, 3), dtype=np.uint8)).tobytes()

        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(target_dpi=300)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        page = pages[0]
        assert page.needs_upscaling is True
        assert page.dpi_input == pytest.approx(150.0)

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_upscaling_not_needed_high_dpi(self, mock_fitz: Mock) -> None:
        """Test upscaling flag is not set for high DPI pages."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0

        # Mock high DPI image (400 DPI)
        mock_page.get_images.return_value = [(1,)]
        mock_doc.extract_image.return_value = {
            "width": 3400,  # 8.5 inches * 400 DPI
            "height": 4400,  # 11 inches * 400 DPI
        }
        mock_page.parent = mock_doc

        mock_pix = MagicMock()
        mock_pix.width = 2550
        mock_pix.height = 3300
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((3300, 2550, 3), dtype=np.uint8)).tobytes()

        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(target_dpi=300)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        page = pages[0]
        assert page.needs_upscaling is False
        assert page.dpi_input == pytest.approx(400.0)

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_rgb_to_bgr_conversion(self, mock_fitz: Mock) -> None:
        """Test RGB to BGR conversion for OpenCV compatibility."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_page.get_images.return_value = []

        # Create RGB image with distinct colors
        rgb_image = np.zeros((10, 10, 3), dtype=np.uint8)
        rgb_image[:, :, 0] = 255  # Red channel
        rgb_image[:, :, 1] = 128  # Green channel
        rgb_image[:, :, 2] = 64  # Blue channel

        mock_pix = MagicMock()
        mock_pix.width = 10
        mock_pix.height = 10
        mock_pix.n = 3
        mock_pix.samples = rgb_image.tobytes()

        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader()

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        page = pages[0]
        # Check BGR order (RGB → BGR means [R,G,B] → [B,G,R])
        assert page.image[0, 0, 0] == 64  # Blue
        assert page.image[0, 0, 1] == 128  # Green
        assert page.image[0, 0, 2] == 255  # Red


class TestLoadPDFConvenience:
    """Test load_pdf convenience function."""

    @patch("image_preprocessing_detector.ingestion.pdf_loader.PDFLoader")
    def test_load_pdf_convenience(self, mock_loader_class: Mock) -> None:
        """Test load_pdf convenience function."""
        # Mock loader instance
        mock_loader = MagicMock()
        mock_page = PageImage(
            page_number=0,
            image=np.zeros((100, 100, 3), dtype=np.uint8),
            width=100,
            height=100,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        mock_loader.load.return_value = iter([mock_page])
        mock_loader_class.return_value = mock_loader

        # Mock file existence
        with patch("pathlib.Path.exists", return_value=True):
            pages = load_pdf("test.pdf", target_dpi=600)

        # Verify loader was created with correct DPI
        mock_loader_class.assert_called_once_with(target_dpi=600)

        # Verify load was called
        assert len(pages) == 1
        assert pages[0].page_number == 0


class TestPDFTooManyPages:
    """Verify the max_pages safety guard behaviour."""

    def _build_mock_doc(self, page_count: int) -> MagicMock:
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = page_count
        mock_page = MagicMock()
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_page.get_images.return_value = []
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 100
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((100, 100, 3), dtype=np.uint8)).tobytes()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        return mock_doc

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_raises_when_page_count_exceeds_limit(self, mock_fitz: Mock) -> None:
        """By default, exceeding max_pages raises PDFTooManyPagesError."""
        mock_fitz.open.return_value = self._build_mock_doc(page_count=10)
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pages=5)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            with pytest.raises(PDFTooManyPagesError) as exc_info:
                list(loader.load(tmp.name))

        assert exc_info.value.page_count == 10
        assert exc_info.value.max_pages == 5

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_truncates_when_allow_truncation_true(self, mock_fitz: Mock) -> None:
        """allow_truncation=True restores the previous silent-truncate behavior."""
        mock_fitz.open.return_value = self._build_mock_doc(page_count=10)
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pages=5, allow_truncation=True)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 5
        # last_pages_truncated / last_total_pages let callers detect the
        # partial result without re-opening the PDF.
        assert loader.last_total_pages == 10
        assert loader.last_pages_truncated == 5

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_under_limit_loads_normally(self, mock_fitz: Mock) -> None:
        """Documents under max_pages load all pages without raising."""
        mock_fitz.open.return_value = self._build_mock_doc(page_count=3)
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pages=5)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 3

    @pytest.mark.parametrize("bad_value", [0, -1, -1000])
    def test_invalid_max_pages_raises_value_error(self, bad_value: int) -> None:
        """Non-positive max_pages must be rejected at construction time."""
        with pytest.raises(ValueError, match="max_pages must be > 0"):
            PDFLoader(max_pages=bad_value)

    @pytest.mark.parametrize(
        "bad_value",
        [10.5, "100", True, False, [100], object()],
    )
    def test_non_int_max_pages_raises_type_error(self, bad_value: object) -> None:
        """Non-int (or bool) max_pages must be rejected with TypeError.

        Note: `None` itself is NOT tested here because the constructor
        treats `None` as a sentinel for "use DEFAULT_MAX_PAGES" - that
        path is exercised by `test_init_default_params`.
        """
        with pytest.raises(TypeError, match="max_pages must be a positive int"):
            PDFLoader(max_pages=bad_value)  # type: ignore[arg-type]

    def test_none_max_pages_uses_default(self) -> None:
        """`None` is treated as a sentinel for DEFAULT_MAX_PAGES."""
        loader = PDFLoader(max_pages=None)
        assert loader.max_pages == PDFLoader.DEFAULT_MAX_PAGES


class TestPDFPixelBomb:
    """Verify the per-page pixel-bomb guard."""

    def _build_mock_doc(self, width: int, height: int) -> MagicMock:
        # `width`/`height` set the page MediaBox, which drives the
        # pixel-bomb projection guard. The rendered pixmap is kept small
        # (16x16) with a matching `samples` buffer so _render_page's
        # reshape succeeds when the page is under the limit (the
        # projection math is independent of the returned pixmap size).
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_page = MagicMock()
        mock_page.rect.width = float(width)
        mock_page.rect.height = float(height)
        mock_page.get_images.return_value = []
        mock_pix = MagicMock()
        pix_w, pix_h = 16, 16
        mock_pix.width = pix_w
        mock_pix.height = pix_h
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((pix_h, pix_w, 3), dtype=np.uint8)).tobytes()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        return mock_doc

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_raises_when_projected_pixels_exceed_limit(self, mock_fitz: Mock) -> None:
        """A page whose MediaBox*zoom exceeds max_pixels is rejected
        before get_pixmap allocates the buffer."""
        # 10000pt x 10000pt at 300 DPI -> zoom ~4.17 -> ~41667^2 pixels.
        mock_doc = self._build_mock_doc(width=10000, height=10000)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pixels=1_000_000)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            with pytest.raises(PDFPageTooLargeError):
                list(loader.load(tmp.name))

        # get_pixmap must NOT have been called - the guard fires first.
        mock_doc.__getitem__.return_value.get_pixmap.assert_not_called()

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_normal_page_under_pixel_limit_renders(self, mock_fitz: Mock) -> None:
        """A normal page well under the limit renders without raising."""
        mock_doc = self._build_mock_doc(width=612, height=792)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pixels=200_000_000)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 1

    @pytest.mark.parametrize("bad_value", [0, -1])
    def test_invalid_max_pixels_raises_value_error(self, bad_value: int) -> None:
        with pytest.raises(ValueError, match="max_pixels must be > 0"):
            PDFLoader(max_pixels=bad_value)

    @pytest.mark.parametrize("bad_value", [10.5, "100", True])
    def test_non_int_max_pixels_raises_type_error(self, bad_value: object) -> None:
        with pytest.raises(TypeError, match="max_pixels must be a positive int"):
            PDFLoader(max_pixels=bad_value)  # type: ignore[arg-type]


class TestPDFPixelBomb:
    """Verify the per-page pixel-bomb guard."""

    def _build_mock_doc(self, width: int, height: int) -> MagicMock:
        # `width`/`height` set the page MediaBox, which drives the
        # pixel-bomb projection guard. The rendered pixmap is kept small
        # (16x16) with a matching `samples` buffer so _render_page's
        # reshape succeeds when the page is under the limit (the
        # projection math is independent of the returned pixmap size).
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_page = MagicMock()
        mock_page.rect.width = float(width)
        mock_page.rect.height = float(height)
        mock_page.get_images.return_value = []
        mock_pix = MagicMock()
        pix_w, pix_h = 16, 16
        mock_pix.width = pix_w
        mock_pix.height = pix_h
        mock_pix.n = 3
        mock_pix.samples = (np.zeros((pix_h, pix_w, 3), dtype=np.uint8)).tobytes()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        return mock_doc

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_raises_when_projected_pixels_exceed_limit(self, mock_fitz: Mock) -> None:
        """A page whose MediaBox*zoom exceeds max_pixels is rejected
        before get_pixmap allocates the buffer."""
        # 10000pt x 10000pt at 300 DPI -> zoom ~4.17 -> ~41667^2 pixels.
        mock_doc = self._build_mock_doc(width=10000, height=10000)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pixels=1_000_000)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            with pytest.raises(PDFPageTooLargeError):
                list(loader.load(tmp.name))

        # get_pixmap must NOT have been called - the guard fires first.
        mock_doc.__getitem__.return_value.get_pixmap.assert_not_called()

    @patch("image_preprocessing_detector.ingestion.pdf_loader.fitz")
    def test_normal_page_under_pixel_limit_renders(self, mock_fitz: Mock) -> None:
        """A normal page well under the limit renders without raising."""
        mock_doc = self._build_mock_doc(width=612, height=792)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = lambda x, y: MagicMock()

        loader = PDFLoader(max_pixels=200_000_000)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            pages = list(loader.load(tmp.name))

        assert len(pages) == 1

    @pytest.mark.parametrize("bad_value", [0, -1])
    def test_invalid_max_pixels_raises_value_error(self, bad_value: int) -> None:
        with pytest.raises(ValueError, match="max_pixels must be > 0"):
            PDFLoader(max_pixels=bad_value)

    @pytest.mark.parametrize("bad_value", [10.5, "100", True])
    def test_non_int_max_pixels_raises_type_error(self, bad_value: object) -> None:
        with pytest.raises(TypeError, match="max_pixels must be a positive int"):
            PDFLoader(max_pixels=bad_value)  # type: ignore[arg-type]
