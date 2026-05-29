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


def _validate_positive_int(value: int | None, name: str, default: int) -> int:
    """Return a validated positive int, applying ``default`` when ``value`` is None.

    Rejects ``bool`` (which ``isinstance(_, int)`` accepts) and non-int
    types so a misconfigured caller fails fast at construction rather
    than deep inside ``range(...)`` or arithmetic later.

    Args:
        value: Caller-supplied value, or None to use the default.
        name: Parameter name, used in error messages.
        default: Value to use when ``value`` is None.

    Returns:
        The validated positive integer.

    Raises:
        TypeError: If the resolved value is a bool or not an int.
        ValueError: If the resolved value is not greater than zero.
    """
    resolved = default if value is None else value
    if isinstance(resolved, bool) or not isinstance(resolved, int):
        msg = f"{name} must be a positive int, got {resolved!r}"
        raise TypeError(msg)
    if resolved <= 0:
        msg = f"{name} must be > 0, got {resolved}"
        raise ValueError(msg)
    return resolved


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
        """Record the offending page count, cap, and source path."""
        self.page_count = page_count
        self.max_pages = max_pages
        self.pdf_path = pdf_path
        super().__init__(
            f"PDF has {page_count} pages, exceeds max_pages={max_pages}: {pdf_path}"
        )


class PDFPageTooLargeError(ValueError):
    """Raised when a single page would rasterize beyond `max_pixels`.

    Defends against pixel-dimension bombs: a PDF with a tiny byte size
    but a huge MediaBox renders, at the target DPI, into a pixmap large
    enough to exhaust memory at ``page.get_pixmap()``. The projected
    output size is checked *before* rasterization so the allocation
    never happens.
    """

    def __init__(self, page_num: int, projected_pixels: int, max_pixels: int) -> None:
        """Record the offending page index, projected pixel count, and cap."""
        self.page_num = page_num
        self.projected_pixels = projected_pixels
        self.max_pixels = max_pixels
        super().__init__(
            f"PDF page {page_num} would rasterize to {projected_pixels} pixels, "
            f"exceeds max_pixels={max_pixels}"
        )


class PDFLoader:
    """Loads PDF files and converts pages to images.

    Uses PyMuPDF (fitz) for efficient PDF parsing and rendering.

    .. warning::
        Not safe for concurrent use. ``last_total_pages`` and
        ``last_pages_truncated`` are mutable per-call state on the
        instance; two threads/tasks calling ``load()`` on the same
        loader will clobber each other's truncation bookkeeping.
        Construct one ``PDFLoader`` per request instead of sharing
        a singleton.
    """

    # Hard upper bound on page count to prevent CPU/memory exhaustion
    # from adversarial PDFs (e.g. thousands of pages or pages with huge
    # rendered dimensions). Override via the constructor when a legitimate
    # use case requires it.
    DEFAULT_MAX_PAGES: int = 500

    # Hard upper bound on the rasterized pixel count of a single page.
    # Defends against pixel-dimension bombs (a small PDF whose MediaBox
    # is enormous renders into a multi-gigabyte pixmap at target DPI).
    # 200 MP blocks the billions-of-pixels bombs (65535x65535 ~= 4.29e9)
    # while still allowing large legitimate pages. Tune down for
    # stricter tenants.
    DEFAULT_MAX_PIXELS: int = 200_000_000

    def __init__(
        self,
        target_dpi: int = 300,
        color_space: str = "RGB",
        alpha: bool = False,
        max_pages: int | None = None,
        allow_truncation: bool = False,
        max_pixels: int | None = None,
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
                a partial page sequence - and read
                `last_pages_truncated` after iteration to detect it.
            max_pixels: Maximum rasterized pixel count for a single
                page. Pages whose projected output (MediaBox scaled to
                target DPI) exceeds this raise PDFPageTooLargeError
                *before* the pixmap is allocated. Defaults to
                DEFAULT_MAX_PIXELS.
        """
        self.target_dpi = target_dpi
        self.color_space = color_space
        self.alpha = alpha
        self.max_pages = _validate_positive_int(
            max_pages, "max_pages", self.DEFAULT_MAX_PAGES
        )
        self.max_pixels = _validate_positive_int(
            max_pixels, "max_pixels", self.DEFAULT_MAX_PIXELS
        )
        self.allow_truncation = allow_truncation
        # Truncation state from the most recent `load()` call. Reset on
        # each call. Callers in `allow_truncation=True` mode should
        # check this after iterating to detect partial results.
        self.last_total_pages: int = 0
        self.last_pages_truncated: int = 0

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

        # Reset truncation state for this call.
        self.last_total_pages = 0
        self.last_pages_truncated = 0

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info("Loading PDF", path=str(pdf_path))

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {pdf_path}") from e

        # Single try/finally enclosing ALL post-open logic so the
        # fitz.Document is released even if page-count inspection,
        # the max_pages check, or the render loop raises.
        try:
            page_count = len(doc)
            self.last_total_pages = page_count
            logger.info("PDF loaded", pages=page_count, path=str(pdf_path))

            if page_count > self.max_pages:
                if not self.allow_truncation:
                    raise PDFTooManyPagesError(
                        page_count, self.max_pages, str(pdf_path)
                    )
                self.last_pages_truncated = page_count - self.max_pages
                logger.warning(
                    "pdf_page_limit_exceeded_truncating",
                    path=str(pdf_path),
                    page_count=page_count,
                    max_pages=self.max_pages,
                    pages_truncated=self.last_pages_truncated,
                )

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

        # Pixel-bomb guard: project the rasterized output size from the
        # page MediaBox scaled by zoom and reject before allocating the
        # pixmap. A tiny PDF with a huge MediaBox would otherwise OOM
        # the worker inside page.get_pixmap().
        projected_w = int(page.rect.width * zoom)
        projected_h = int(page.rect.height * zoom)
        projected_pixels = projected_w * projected_h
        if projected_pixels > self.max_pixels:
            raise PDFPageTooLargeError(page_num, projected_pixels, self.max_pixels)

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
