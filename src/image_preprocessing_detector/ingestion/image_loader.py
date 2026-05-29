"""Direct image loading for JPG, PNG, TIFF, and other formats.

Handles DPI extraction, color space conversion, and metadata detection.
"""

from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np
from PIL import Image

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class ImageMetadata:
    """Metadata extracted from an image file.

    Attributes:
        width: Image width in pixels
        height: Image height in pixels
        dpi_x: Horizontal DPI (dots per inch), None if not available
        dpi_y: Vertical DPI (dots per inch), None if not available
        color_mode: PIL color mode (RGB, RGBA, L, etc.)
        format: Image format (JPEG, PNG, TIFF, etc.)
        has_exif: Whether EXIF data is present
    """

    def __init__(
        self,
        width: int,
        height: int,
        dpi_x: float | None = None,
        dpi_y: float | None = None,
        color_mode: str = "RGB",
        format: str = "UNKNOWN",
        has_exif: bool = False,
    ) -> None:
        """Initialize image metadata."""
        self.width = width
        self.height = height
        self.dpi_x = dpi_x
        self.dpi_y = dpi_y
        self.color_mode = color_mode
        self.format = format
        self.has_exif = has_exif

    @property
    def dpi(self) -> float | None:
        """Return average DPI if available."""
        if self.dpi_x is not None and self.dpi_y is not None:
            return (self.dpi_x + self.dpi_y) / 2.0
        return self.dpi_x or self.dpi_y

    @property
    def needs_upscaling(self) -> bool:
        """Check if image needs DPI upscaling (< 300 DPI)."""
        if self.dpi is None:
            return False  # Unknown DPI, assume no upscaling needed
        return self.dpi < 300.0


class ImageLoader:
    """Loads images from various formats (JPG, PNG, TIFF, etc.).

    Uses PIL for metadata extraction and OpenCV for image loading.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
        ".bmp",
        ".webp",
    }

    # Hard upper bound on the decoded pixel count. Defends against
    # pixel-dimension bombs: a PNG/TIFF header can declare enormous
    # dimensions (e.g. 65535x65535) in a tiny file that OOMs the worker
    # at cv2.imread. PIL reports the declared size cheaply (without
    # decoding), so we check it before handing the file to OpenCV.
    DEFAULT_MAX_PIXELS: int = 200_000_000

    def __init__(
        self,
        target_dpi: int = 300,
        ensure_bgr: bool = True,
        max_pixels: int | None = None,
    ) -> None:
        """Initialize image loader.

        Args:
            target_dpi: Target DPI for quality assessment (default: 300)
            ensure_bgr: Convert images to BGR format for OpenCV (default: True)
            max_pixels: Maximum decoded pixel count. Images whose
                declared dimensions exceed this raise ValueError before
                cv2.imread allocates the buffer. Defaults to
                DEFAULT_MAX_PIXELS.
        """
        self.target_dpi = target_dpi
        self.ensure_bgr = ensure_bgr
        self.max_pixels = self.DEFAULT_MAX_PIXELS if max_pixels is None else max_pixels

        logger.info("Image loader initialized", target_dpi=target_dpi)

    def load(self, image_path: str | Path) -> tuple[np.ndarray, ImageMetadata]:
        """Load image and extract metadata.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (image_array, metadata)
            - image_array: NumPy array in BGR format (H, W, C)
            - metadata: ImageMetadata object with DPI and format info

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If file format is not supported, the declared
                dimensions exceed `max_pixels`, or the image is invalid.
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if image_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported image format: {image_path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        logger.info("Loading image", path=str(image_path))

        # Extract metadata using PIL
        metadata = self._extract_metadata(image_path)

        # Pixel-bomb guard: PIL reports declared dimensions without
        # decoding pixel data, so reject oversize images before
        # cv2.imread allocates a potentially multi-gigabyte buffer.
        declared_pixels = metadata.width * metadata.height
        if declared_pixels > self.max_pixels:
            raise ValueError(
                f"Image dimensions {metadata.width}x{metadata.height} "
                f"({declared_pixels} pixels) exceed max_pixels={self.max_pixels}"
            )

        # Load image using OpenCV
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # Verify image is in BGR format (OpenCV default)
        if img.ndim != 3 or img.shape[2] != 3:
            logger.warning(
                "Image is not 3-channel BGR, attempting conversion",
                shape=img.shape,
                path=str(image_path),
            )
            if img.ndim == 2:  # Grayscale
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif img.shape[2] == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        logger.debug(
            "Image loaded",
            path=str(image_path),
            shape=img.shape,
            dpi=metadata.dpi,
            needs_upscaling=metadata.needs_upscaling,
        )

        return img, metadata

    def _extract_metadata(self, image_path: Path) -> ImageMetadata:
        """Extract metadata from image using PIL.

        Args:
            image_path: Path to image file

        Returns:
            ImageMetadata object
        """
        try:
            with Image.open(image_path) as pil_img:
                width, height = pil_img.size
                color_mode = pil_img.mode
                img_format = pil_img.format or "UNKNOWN"

                # Extract DPI from EXIF or info dict
                dpi_x, dpi_y = None, None
                has_exif = False

                # Try EXIF data first (more reliable for JPEG)
                exif = pil_img.getexif()
                if exif:
                    has_exif = True
                    # EXIF tag 282 = XResolution, 283 = YResolution
                    if 282 in exif and 283 in exif:
                        dpi_x = float(exif[282])
                        dpi_y = float(exif[283])

                # Fall back to info dict if EXIF not available
                if dpi_x is None and "dpi" in pil_img.info:
                    dpi_info = pil_img.info["dpi"]
                    if isinstance(dpi_info, tuple) and len(dpi_info) == 2:
                        dpi_x, dpi_y = float(dpi_info[0]), float(dpi_info[1])
                    elif isinstance(dpi_info, int | float):
                        dpi_x = dpi_y = float(dpi_info)

                metadata = ImageMetadata(
                    width=width,
                    height=height,
                    dpi_x=dpi_x,
                    dpi_y=dpi_y,
                    color_mode=color_mode,
                    format=img_format,
                    has_exif=has_exif,
                )

                logger.debug(
                    "Metadata extracted",
                    width=width,
                    height=height,
                    dpi=metadata.dpi,
                    format=img_format,
                    has_exif=has_exif,
                )

                return metadata

        except Exception as e:
            raise ValueError(f"Failed to extract metadata from {image_path}") from e

    @classmethod
    def is_supported(cls, file_path: str | Path) -> bool:
        """Check if file format is supported.

        Args:
            file_path: Path to check

        Returns:
            True if format is supported, False otherwise
        """
        return Path(file_path).suffix.lower() in cls.SUPPORTED_FORMATS


def load_image(
    image_path: str | Path, target_dpi: int = 300
) -> tuple[np.ndarray, ImageMetadata]:
    """Convenience function to load an image.

    Args:
        image_path: Path to image file
        target_dpi: Target DPI for quality assessment (default: 300)

    Returns:
        Tuple of (image_array, metadata)

    Example:
        >>> img, metadata = load_image("document.jpg")
        >>> print(f"Image: {metadata.width}x{metadata.height} @ {metadata.dpi} DPI")
        >>> if metadata.needs_upscaling:
        ...     print("Image needs upscaling")
    """
    loader = ImageLoader(target_dpi=target_dpi)
    return loader.load(image_path)


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_loader.py <image_path>")
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    image_path = sys.argv[1]

    if not ImageLoader.is_supported(image_path):
        logger.error("Unsupported image format", path=image_path)
        sys.exit(1)

    loader = ImageLoader()
    img, metadata = loader.load(image_path)

    print(f"\n{'=' * 60}")
    print(f"Image Metadata for: {image_path}")
    print(f"{'=' * 60}")
    print(f"Dimensions:  {metadata.width}x{metadata.height} pixels")
    print(f"Format:      {metadata.format}")
    print(f"Color Mode:  {metadata.color_mode}")
    print(f"DPI:         {metadata.dpi or 'Unknown'}")
    if metadata.dpi:
        print(f"  X: {metadata.dpi_x}, Y: {metadata.dpi_y}")
    print(f"EXIF Data:   {'Yes' if metadata.has_exif else 'No'}")
    print(f"Upscaling:   {'Needed' if metadata.needs_upscaling else 'Not needed'}")
    print(f"Array Shape: {img.shape}")
    print(f"{'=' * 60}\n")
