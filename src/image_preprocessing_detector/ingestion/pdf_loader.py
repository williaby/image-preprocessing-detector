"""PDF loading and conversion to images using PyMuPDF (fitz).

Handles PDF to image conversion, DPI detection, and multi-page documents.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass
class PageImage:
    """Represents a single page converted to an image.

    Attributes:
        page_number: Zero-based page index
        image: Image as numpy array (H, W, C) in BGR format
        width: Image width in pixels
        height: Image height in pixels
        dpi_input: Original DPI of the PDF page
        dpi_effective: Effective DPI after rendering
        needs_upscaling: Whether the page needs DPI upscaling
    """

    page_number: int
    image: np.ndarray
    width: int
    height: int
    dpi_input: float
    dpi_effective: float
    needs_upscaling: bool


class PDFTooManyPagesError(ValueError):
    """Raised when a PDF exceeds the configured `max_pages` limit.

    Carries `page_count` and `max_pages` so callers can either propagate
    a structured error to the client or fall back to opening the loader
    with `allow_truncation=True`.
    """

    def __init__(self, page_count: int, max_pages: int, pdf_path: str) -> None:
        self.page_count = page_count
        self.max_pages = max_pages
        self.pdf_path = pdf_path
        super().__init__(
            f"PDF has {page_count} pages, exceeds max_pages={max_pages}: {pdf_path}"
        )


class PDFLoader:
    """Loads PDF files and converts pages to images.

    Uses PyMuPDF (fitz) for efficient PDF parsing and rendering.
    """

    # Hard upper bound on page count to prevent CPU/memory exhaustion
    # from adversarial PDFs (e.g. thousands of pages or pages with huge
    # rendered dimensions). Override via the constructor when a legitimate
    # use case requires it.
    DEFAULT_MAX_PAGES: int = 500

    def __init__(
        self,
        target_dpi: int = 300,
        color_space: str = "RGB",
        alpha: bool = False,
        max_pages: int | None = None,
        allow_truncation: bool = False,
    ) -> None:
        """Initialize PDF loader.

        Args:
            target_dpi: Target DPI for rendering (default: 300)
            color_space: Color space for rendering (RGB or GRAY)
            alpha: Whether to include alpha channel
            max_pages: Maximum number of pages to render. Defaults to
                DEFAULT_MAX_PAGES; pass a smaller value for stricter
                tenants or untrusted uploads.
            allow_truncation: If True, silently truncate documents that
                exceed `max_pages` (the previous behavior). If False
                (the default) the loader raises PDFTooManyPagesError so
                callers cannot accidentally analyse a partial document
                and surface incomplete results to users. Set True only
                when downstream code is explicitly designed to handle
                a partial page sequence.
        """
        self.target_dpi = target_dpi
        self.color_space = color_space
        self.alpha = alpha
        self.max_pages = max_pages if max_pages is not None else self.DEFAULT_MAX_PAGES
        self.allow_truncation = allow_truncation

        logger.info(
            "PDF loader initialized",
            target_dpi=target_dpi,
            color_space=color_space,
            max_pages=self.max_pages,
            allow_truncation=self.allow_truncation,
        )

    def load(self, pdf_path: str | Path) -> Iterator[PageImage]:
        """Load PDF and yield pages as images.

        Args:
            pdf_path: Path to PDF file

        Yields:
            PageImage objects for each page

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a valid PDF
            PDFTooManyPagesError: If page count exceeds `max_pages` and
                `allow_truncation=False` (the default).
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info("Loading PDF", path=str(pdf_path))

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {pdf_path}") from e

        page_count = len(doc)
        logger.info("PDF loaded", pages=page_count, path=str(pdf_path))

        if page_count > self.max_pages:
            if not self.allow_truncation:
                doc.close()
                raise PDFTooManyPagesError(page_count, self.max_pages, str(pdf_path))
            logger.warning(
                "pdf_page_limit_exceeded_truncating",
                path=str(pdf_path),
                page_count=page_count,
                max_pages=self.max_pages,
            )

        try:
            for page_num in range(min(page_count, self.max_pages)):
                yield self._render_page(doc, page_num)
        finally:
            doc.close()

    def _render_page(self, doc: fitz.Document, page_num: int) -> PageImage:
        """Render a single PDF page to an image.

        Args:
            doc: PyMuPDF document object
            page_num: Zero-based page index

        Returns:
            PageImage object with rendered image and metadata
        """
        page = doc[page_num]

        # Detect original DPI from page dimensions
        dpi_input = self._detect_page_dpi(page)

        # Calculate zoom factor to achieve target DPI
        zoom = self.target_dpi / 72.0  # PDF default is 72 DPI

        # Render page to pixmap
        mat = fitz.Matrix(zoom, zoom)
        # Convert color space string to fitz.Colorspace
        colorspace = fitz.csRGB if self.color_space == "RGB" else fitz.csGRAY
        pix = page.get_pixmap(
            matrix=mat,
            colorspace=colorspace,
            alpha=self.alpha,
        )

        # Convert pixmap to numpy array
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )

        # Convert RGB to BGR for OpenCV compatibility
        if pix.n == 3:  # RGB
            img_array = img_array[:, :, [2, 1, 0]]  # type: ignore[assignment]  # RGB → BGR
        elif pix.n == 4:  # RGBA
            img_array = img_array[:, :, [2, 1, 0, 3]]  # type: ignore[assignment]  # RGBA → BGRA

        # Determine if upscaling is needed
        needs_upscaling = dpi_input < self.target_dpi

        logger.debug(
            "Page rendered",
            page_number=page_num,
            width=pix.width,
            height=pix.height,
            dpi_input=dpi_input,
            dpi_effective=self.target_dpi,
            needs_upscaling=needs_upscaling,
        )

        return PageImage(
            page_number=page_num,
            image=img_array,
            width=pix.width,
            height=pix.height,
            dpi_input=dpi_input,
            dpi_effective=self.target_dpi,
            needs_upscaling=needs_upscaling,
        )

    def _detect_page_dpi(self, page: fitz.Page) -> float:
        """Detect the effective DPI of a PDF page.

        Args:
            page: PyMuPDF page object

        Returns:
            Estimated DPI based on page dimensions
        """
        # Get page dimensions in points (1/72 inch)
        rect = page.rect
        width_pt = rect.width
        height_pt = rect.height

        # Standard page sizes (in inches) for DPI estimation
        common_sizes = [
            (8.5, 11.0),  # Letter
            (8.27, 11.69),  # A4
            (11.0, 17.0),  # Tabloid
        ]

        # Estimate DPI based on closest standard size
        width_inches = width_pt / 72.0
        height_inches = height_pt / 72.0

        # Find closest standard size
        min_diff = float("inf")
        estimated_dpi = 72.0  # Default

        for std_w, std_h in common_sizes:
            diff = abs(width_inches - std_w) + abs(height_inches - std_h)
            if diff < min_diff:
                min_diff = diff
                # Estimate DPI from actual pixel dimensions if available
                # For now, use default PDF DPI
                estimated_dpi = 72.0

        # Try to get actual DPI from images in the page
        try:
            images = page.get_images()
            if images and page.parent is not None:
                # Get the first image's DPI
                xref = images[0][0]
                img_dict = page.parent.extract_image(xref)
                if img_dict and "width" in img_dict and "height" in img_dict:
                    img_width = img_dict["width"]
                    # Calculate DPI from image resolution vs page size
                    estimated_dpi = (
                        (img_width / width_inches) if width_inches > 0 else 72.0
                    )
        except Exception:  # nosec B110
            # Legitimate fallback: DPI estimation is optional, defaults to 72.0 if metadata extraction fails
            pass

        return estimated_dpi


def load_pdf(
    pdf_path: str | Path,
    target_dpi: int = 300,
) -> list[PageImage]:
    """Convenience function to load a PDF and return all pages as a list.

    Args:
        pdf_path: Path to PDF file
        target_dpi: Target DPI for rendering (default: 300)

    Returns:
        List of PageImage objects, one per page

    Example:
        >>> pages = load_pdf("document.pdf", target_dpi=300)
        >>> for page in pages:
        ...     print(f"Page {page.page_number}: {page.width}x{page.height}")
    """
    loader = PDFLoader(target_dpi=target_dpi)
    return list(loader.load(pdf_path))


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_loader.py <pdf_path>")
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    pdf_path = sys.argv[1]
    pages = load_pdf(pdf_path, target_dpi=300)

    print(f"\nLoaded {len(pages)} pages from {pdf_path}")
    for page in pages:
        print(
            f"  Page {page.page_number + 1}: {page.width}×{page.height}px @ {page.dpi_effective} DPI"
        )
        if page.needs_upscaling:
            print(f"    ⚠️  Upscaling needed (input: {page.dpi_input} DPI)")
