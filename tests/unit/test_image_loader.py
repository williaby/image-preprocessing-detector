"""
Unit tests for direct image loading.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from image_preprocessing_detector.ingestion.image_loader import (
    ImageLoader,
    ImageMetadata,
    load_image,
)


class TestImageMetadata:
    """Test ImageMetadata class."""

    def test_metadata_creation(self) -> None:
        """Test creating an ImageMetadata instance."""
        metadata = ImageMetadata(
            width=1920,
            height=1080,
            dpi_x=300.0,
            dpi_y=300.0,
            color_mode="RGB",
            format="JPEG",
            has_exif=True,
        )

        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.dpi_x == pytest.approx(300.0)
        assert metadata.dpi_y == pytest.approx(300.0)
        assert metadata.color_mode == "RGB"
        assert metadata.format == "JPEG"
        assert metadata.has_exif is True

    def test_dpi_property(self) -> None:
        """Test DPI property returns average."""
        metadata = ImageMetadata(width=100, height=100, dpi_x=300.0, dpi_y=400.0)

        assert metadata.dpi == pytest.approx(350.0)  # Average of 300 and 400

    def test_dpi_property_with_none(self) -> None:
        """Test DPI property with missing values."""
        # Both None
        metadata1 = ImageMetadata(width=100, height=100)
        assert metadata1.dpi is None

        # Only X
        metadata2 = ImageMetadata(width=100, height=100, dpi_x=300.0)
        assert metadata2.dpi == pytest.approx(300.0)

        # Only Y
        metadata3 = ImageMetadata(width=100, height=100, dpi_y=300.0)
        assert metadata3.dpi == pytest.approx(300.0)

    def test_needs_upscaling(self) -> None:
        """Test needs_upscaling property."""
        # High DPI - no upscaling needed
        metadata_high = ImageMetadata(width=100, height=100, dpi_x=300.0, dpi_y=300.0)
        assert metadata_high.needs_upscaling is False

        # Low DPI - upscaling needed
        metadata_low = ImageMetadata(width=100, height=100, dpi_x=150.0, dpi_y=150.0)
        assert metadata_low.needs_upscaling is True

        # Unknown DPI - no upscaling
        metadata_unknown = ImageMetadata(width=100, height=100)
        assert metadata_unknown.needs_upscaling is False


class TestImageLoader:
    """Test ImageLoader class."""

    def test_init_default_params(self) -> None:
        """Test ImageLoader initialization with defaults."""
        loader = ImageLoader()

        assert loader.target_dpi == 300
        assert loader.ensure_bgr is True

    def test_init_custom_params(self) -> None:
        """Test ImageLoader initialization with custom parameters."""
        loader = ImageLoader(target_dpi=600, ensure_bgr=False)

        assert loader.target_dpi == 600
        assert loader.ensure_bgr is False

    def test_is_supported(self) -> None:
        """Test is_supported class method."""
        # Supported formats
        assert ImageLoader.is_supported("image.jpg") is True
        assert ImageLoader.is_supported("image.jpeg") is True
        assert ImageLoader.is_supported("image.png") is True
        assert ImageLoader.is_supported("image.tiff") is True
        assert ImageLoader.is_supported("image.tif") is True
        assert ImageLoader.is_supported("image.bmp") is True
        assert ImageLoader.is_supported("image.webp") is True

        # Case insensitive
        assert ImageLoader.is_supported("image.JPG") is True
        assert ImageLoader.is_supported("image.PNG") is True

        # Unsupported formats
        assert ImageLoader.is_supported("document.pdf") is False
        assert ImageLoader.is_supported("file.txt") is False
        assert ImageLoader.is_supported("archive.zip") is False

    def test_load_file_not_found(self) -> None:
        """Test loading non-existent file raises FileNotFoundError."""
        loader = ImageLoader()

        with pytest.raises(FileNotFoundError, match="Image file not found"):
            loader.load("/nonexistent/image.jpg")

    def test_load_unsupported_format(self) -> None:
        """Test loading unsupported format raises ValueError."""
        loader = ImageLoader()

        # Create a temporary file with unsupported extension
        with (
            tempfile.NamedTemporaryFile(suffix=".txt") as tmp,
            pytest.raises(ValueError, match="Unsupported image format"),
        ):
            loader.load(tmp.name)

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_valid_jpeg(self, mock_pil_open: Mock, mock_cv2_imread: Mock) -> None:
        """Test loading valid JPEG image."""
        # Mock PIL Image
        mock_pil_img = MagicMock()
        mock_pil_img.size = (1920, 1080)
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "JPEG"
        mock_pil_img.getexif.return_value = {282: 300.0, 283: 300.0}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV imread
        mock_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_cv2_imread.return_value = mock_img

        loader = ImageLoader()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            img, metadata = loader.load(tmp.name)

        assert img.shape == (1080, 1920, 3)
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.dpi == pytest.approx(300.0)
        assert metadata.format == "JPEG"
        assert metadata.has_exif is True

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_png_without_dpi(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """Test loading PNG without DPI metadata."""
        # Mock PIL Image without DPI
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV imread
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_cv2_imread.return_value = mock_img

        loader = ImageLoader()

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            _img, metadata = loader.load(tmp.name)

        assert metadata.dpi is None
        assert metadata.needs_upscaling is False  # Unknown DPI

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_with_info_dict_dpi(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """Test loading image with DPI in info dict (fallback)."""
        # Mock PIL Image with DPI in info dict
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {"dpi": (150.0, 150.0)}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV imread
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_cv2_imread.return_value = mock_img

        loader = ImageLoader()

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            _img, metadata = loader.load(tmp.name)

        assert metadata.dpi == pytest.approx(150.0)
        assert metadata.needs_upscaling is True

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_grayscale_conversion(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """Test automatic conversion of grayscale to BGR."""
        # Mock PIL Image
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "L"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV imread - grayscale image (2D)
        mock_gray = np.zeros((600, 800), dtype=np.uint8)
        mock_cv2_imread.return_value = mock_gray

        loader = ImageLoader()

        with (
            tempfile.NamedTemporaryFile(suffix=".png") as tmp,
            patch(
                "image_preprocessing_detector.ingestion.image_loader.cv2.cvtColor"
            ) as mock_cvt,
        ):
            mock_bgr = np.zeros((600, 800, 3), dtype=np.uint8)
            mock_cvt.return_value = mock_bgr

            img, _metadata = loader.load(tmp.name)

            # Should have called cvtColor to convert grayscale to BGR
            mock_cvt.assert_called_once()
            assert img.shape == (600, 800, 3)

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_rgba_conversion(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """Test automatic conversion of RGBA to BGR."""
        # Mock PIL Image
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "RGBA"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV imread - RGBA image (4 channels)
        mock_rgba = np.zeros((600, 800, 4), dtype=np.uint8)
        mock_cv2_imread.return_value = mock_rgba

        loader = ImageLoader()

        with (
            tempfile.NamedTemporaryFile(suffix=".png") as tmp,
            patch(
                "image_preprocessing_detector.ingestion.image_loader.cv2.cvtColor"
            ) as mock_cvt,
        ):
            mock_bgr = np.zeros((600, 800, 3), dtype=np.uint8)
            mock_cvt.return_value = mock_bgr

            img, _metadata = loader.load(tmp.name)

            # Should have called cvtColor to convert RGBA to BGR
            mock_cvt.assert_called_once()
            assert img.shape == (600, 800, 3)

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_load_invalid_image(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """Test loading invalid image raises ValueError."""
        # Mock PIL to succeed (file exists)
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "JPEG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        # Mock OpenCV to fail (corrupted image)
        mock_cv2_imread.return_value = None

        loader = ImageLoader()

        with (
            tempfile.NamedTemporaryFile(suffix=".jpg") as tmp,
            pytest.raises(ValueError, match="Failed to load image"),
        ):
            loader.load(tmp.name)

    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_extract_metadata_failure(self, mock_pil_open: Mock) -> None:
        """Test metadata extraction failure raises ValueError."""
        # Mock PIL to raise exception
        mock_pil_open.side_effect = Exception("Corrupted file")

        loader = ImageLoader()

        with (
            tempfile.NamedTemporaryFile(suffix=".jpg") as tmp,
            pytest.raises(ValueError, match="Failed to extract metadata"),
        ):
            loader.load(tmp.name)


class TestLoadImageConvenience:
    """Test load_image convenience function."""

    @patch("image_preprocessing_detector.ingestion.image_loader.ImageLoader")
    def test_load_image_convenience(self, mock_loader_class: Mock) -> None:
        """Test load_image convenience function."""
        # Mock loader instance
        mock_loader = MagicMock()
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_metadata = ImageMetadata(
            width=800,
            height=600,
            dpi_x=300.0,
            dpi_y=300.0,
            format="JPEG",
        )
        mock_loader.load.return_value = (mock_img, mock_metadata)
        mock_loader_class.return_value = mock_loader

        img, metadata = load_image("test.jpg", target_dpi=600)

        # Verify loader was created with correct DPI
        mock_loader_class.assert_called_once_with(target_dpi=600)

        # Verify load was called
        assert img.shape == (600, 800, 3)
        assert metadata.width == 800
        assert metadata.height == 600


class TestImageLoaderRealOperations:
    """Test ImageLoader with real image operations (minimal mocking)."""

    def test_load_rgba_image_real_conversion(self) -> None:
        """Test RGBA to BGR conversion with real cv2 operations."""
        from PIL import Image

        # Create a real RGBA image in memory
        rgba_img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            rgba_img.save(tmp.name)
            tmp_path = tmp.name

        try:
            loader = ImageLoader()
            img, metadata = loader.load(tmp_path)

            # Image should be loaded as BGR (3 channels)
            assert img.shape == (100, 100, 3)
            assert img.ndim == 3
            assert metadata.color_mode == "RGBA"
            assert metadata.format == "PNG"
        finally:
            Path(tmp_path).unlink()

    def test_load_image_with_exif_dpi(self) -> None:
        """Test loading image with EXIF DPI tags."""
        from PIL import Image

        # Create an image with EXIF DPI
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))

        # Create EXIF data with DPI tags (282=XResolution, 283=YResolution)
        from PIL import Image as PILImage

        exif = PILImage.Exif()
        exif[282] = 300.0  # XResolution
        exif[283] = 300.0  # YResolution

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img.save(tmp.name, exif=exif)
            tmp_path = tmp.name

        try:
            loader = ImageLoader()
            _loaded_img, metadata = loader.load(tmp_path)

            # Should extract DPI from EXIF
            assert metadata.dpi_x == pytest.approx(300.0)
            assert metadata.dpi_y == pytest.approx(300.0)
            assert metadata.has_exif is True
        finally:
            Path(tmp_path).unlink()

    def test_load_image_with_dpi_as_single_value(self) -> None:
        """Test loading image with DPI as single int/float value."""
        from PIL import Image

        # Create an image
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Save with DPI as single value (will be stored in info dict)
            img.save(tmp.name, dpi=(150, 150))
            tmp_path = tmp.name

        try:
            # Now mock the info dict to return a single int instead of tuple
            from unittest.mock import patch

            loader = ImageLoader()

            with patch("PIL.Image.open") as mock_open:
                # Create a mock PIL image with DPI as single int
                mock_img = Image.new("RGB", (100, 100))
                mock_img.info = {"dpi": 150}  # Single value, not tuple

                # Use context manager properly
                mock_open.return_value.__enter__.return_value = mock_img
                mock_open.return_value.__exit__.return_value = None

                _loaded_img, metadata = loader.load(tmp_path)

                # Should handle DPI as single value
                assert metadata.dpi_x == pytest.approx(150.0)
                assert metadata.dpi_y == pytest.approx(150.0)
        finally:
            Path(tmp_path).unlink()


class TestImageLoaderPixelBomb:
    """Verify the pixel-dimension-bomb guard in ImageLoader.load."""

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_rejects_pixel_bomb_before_imread(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """An image whose PIL-declared dimensions exceed max_pixels is
        rejected before cv2.imread is ever called."""
        mock_pil_img = MagicMock()
        mock_pil_img.size = (65535, 65535)  # ~4.29e9 pixels
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img

        loader = ImageLoader(max_pixels=200_000_000)

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ValueError, match="exceed max_pixels"):
                loader.load("huge.png")

        # cv2.imread must NOT have been called - the guard fires first.
        mock_cv2_imread.assert_not_called()

    @patch("image_preprocessing_detector.ingestion.image_loader.cv2.imread")
    @patch("image_preprocessing_detector.ingestion.image_loader.Image.open")
    def test_under_pixel_limit_loads(
        self, mock_pil_open: Mock, mock_cv2_imread: Mock
    ) -> None:
        """A normal image under max_pixels loads without raising."""
        mock_pil_img = MagicMock()
        mock_pil_img.size = (800, 600)
        mock_pil_img.mode = "RGB"
        mock_pil_img.format = "PNG"
        mock_pil_img.getexif.return_value = {}
        mock_pil_img.info = {}
        mock_pil_open.return_value.__enter__.return_value = mock_pil_img
        mock_cv2_imread.return_value = np.zeros((600, 800, 3), dtype=np.uint8)

        loader = ImageLoader(max_pixels=200_000_000)

        with patch("pathlib.Path.exists", return_value=True):
            img, metadata = loader.load("ok.png")

        assert img is not None
        assert metadata.width == 800
        assert metadata.height == 600
        mock_cv2_imread.assert_called_once()
