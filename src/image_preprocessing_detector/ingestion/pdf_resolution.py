# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

"""PDF resolution detection utilities."""

import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def _analyze_single_image(
    doc: Any, page: Any, img: tuple, img_index: int, page_num: int
) -> tuple[float, float] | None:
    """Analyze a single image to extract DPI values.

    Args:
        doc: PyMuPDF document
        page: Page containing the image
        img: Image info tuple from get_images
        img_index: Image index on page
        page_num: Page number (0-indexed)

    Returns:
        Tuple of (width_dpi, height_dpi) or None if analysis fails
    """
    try:
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        img_width = pix.width
        img_height = pix.height

        img_bbox_result = page.get_image_bbox(img, transform=False)
        img_bbox: fitz.Rect = img_bbox_result  # pyright: ignore[reportAssignmentType]

        bbox_width_inches = (img_bbox.x1 - img_bbox.x0) / 72.0
        bbox_height_inches = (img_bbox.y1 - img_bbox.y0) / 72.0

        pix = None  # Release memory

    except Exception as e:
        logger.warning(f"Error analyzing image {img_index} on page {page_num + 1}: {e}")
        return None
    else:
        if bbox_width_inches <= 0 or bbox_height_inches <= 0:
            return None
        dpi_width = img_width / bbox_width_inches
        dpi_height = img_height / bbox_height_inches
        return (dpi_width, dpi_height)


def _build_empty_result() -> dict[str, Any]:
    """Build result for PDFs with no images.

    Returns:
        Empty result dictionary
    """
    return {
        "needs_upscaling": False,
        "min_dpi": None,
        "avg_dpi": None,
        "max_dpi": None,
        "image_count": 0,
        "low_res_image_count": 0,
        "details": [],
    }


def _calculate_page_stats(
    page_dpi_values: list[tuple[float, float]], page_num: int
) -> dict[str, Any] | None:
    """Calculate statistics for a single page.

    Args:
        page_dpi_values: List of (width_dpi, height_dpi) tuples for page
        page_num: Page number (0-indexed)

    Returns:
        Page statistics dict or None if no images
    """
    if not page_dpi_values:
        return None

    page_min_dpi = min(min(dpi) for dpi in page_dpi_values)
    page_avg_dpi = sum(sum(dpi) for dpi in page_dpi_values) / (len(page_dpi_values) * 2)
    page_max_dpi = max(max(dpi) for dpi in page_dpi_values)

    return {
        "page_number": page_num + 1,
        "image_count": len(page_dpi_values),
        "min_dpi": round(page_min_dpi, 2),
        "avg_dpi": round(page_avg_dpi, 2),
        "max_dpi": round(page_max_dpi, 2),
    }


def _process_page_images(
    doc: Any,
    page: Any,
    page_num: int,
    image_list: list,
    min_dpi_threshold: int,
) -> tuple[list[tuple[float, float]], int]:
    """Process all images on a single page.

    Args:
        doc: PyMuPDF document
        page: Page object
        page_num: Page number (0-indexed)
        image_list: List of images on the page
        min_dpi_threshold: Minimum DPI threshold for low-res detection

    Returns:
        Tuple of (dpi_values list, low_res_count)
    """
    page_dpi_values: list[tuple[float, float]] = []
    low_res_count = 0

    for img_index, img in enumerate(image_list):
        dpi_result = _analyze_single_image(doc, page, img, img_index, page_num)
        if dpi_result:
            page_dpi_values.append(dpi_result)
            min_img_dpi = min(dpi_result)
            if min_img_dpi < min_dpi_threshold:
                low_res_count += 1

    return page_dpi_values, low_res_count


class PDFResolutionAnalyzer:
    """Analyzes PDF resolution to determine if upscaling is needed."""

    def __init__(self, min_dpi_threshold: int = 300) -> None:
        """Initialize PDF resolution analyzer.

        # #CRITICAL: DPI Threshold: 300 DPI is standard for high-quality OCR
        # #VERIFY: Threshold may need adjustment based on OCR engine requirements

        Args:
            min_dpi_threshold: Minimum DPI for acceptable quality (default: 300)
        """
        self.min_dpi_threshold = min_dpi_threshold

    def analyze_pdf_resolution(self, pdf_path: str | Path) -> dict[str, Any]:
        """Analyze PDF to determine image resolutions.

        # #CRITICAL: External Resources: PDF may be corrupted or password-protected
        # #VERIFY: Handle encryption and corruption gracefully

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary containing:
                - needs_upscaling: bool indicating if upscaling is recommended
                - min_dpi: Minimum DPI found across all images
                - avg_dpi: Average DPI across all images
                - max_dpi: Maximum DPI found
                - image_count: Total number of images analyzed
                - low_res_image_count: Number of images below threshold
                - details: List of per-page resolution info

        Raises:
            Exception: If PDF cannot be opened or analyzed
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            msg = f"PDF file not found: {pdf_path}"
            raise FileNotFoundError(msg)

        try:
            # #CRITICAL: Memory Management: Large PDFs can exhaust memory
            # #VERIFY: Process page-by-page to limit memory usage
            doc = fitz.open(pdf_path)

            dpi_values: list[tuple[float, float]] = []  # (width_dpi, height_dpi)
            page_details: list[dict[str, Any]] = []
            low_res_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get all images on the page
                # #CRITICAL: PyMuPDF API: get_images(full=True) required for complete image info
                # #VERIFY: Without full=True, get_image_bbox may fail
                image_list = page.get_images(full=True)

                # Process all images on this page using helper
                page_dpi_values, page_low_res = _process_page_images(
                    doc, page, page_num, image_list, self.min_dpi_threshold
                )
                dpi_values.extend(page_dpi_values)
                low_res_count += page_low_res

                # Store page-level details using helper
                page_stats = _calculate_page_stats(page_dpi_values, page_num)
                if page_stats:
                    page_details.append(page_stats)

            doc.close()

            # Calculate overall statistics
            if not dpi_values:
                logger.warning(f"No images found in PDF: {pdf_path}")
                return _build_empty_result()

            # Flatten DPI values (width and height)
            all_dpi_flat = [dpi for pair in dpi_values for dpi in pair]

            min_dpi = min(all_dpi_flat)
            avg_dpi = sum(all_dpi_flat) / len(all_dpi_flat)
            max_dpi = max(all_dpi_flat)

            # Determine if upscaling is needed
            # #ASSUME: Upscaling Decision: Use minimum DPI as threshold
            # #VERIFY: May want to use average or weighted threshold
            needs_upscaling = min_dpi < self.min_dpi_threshold

            result = {
                "needs_upscaling": needs_upscaling,
                "min_dpi": round(min_dpi, 2),
                "avg_dpi": round(avg_dpi, 2),
                "max_dpi": round(max_dpi, 2),
                "image_count": len(dpi_values),
                "low_res_image_count": low_res_count,
                "details": page_details,
            }

            logger.info(
                f"PDF resolution analysis complete: {pdf_path.name} - "
                f"Min DPI: {result['min_dpi']}, Avg DPI: {result['avg_dpi']}, "
                f"Needs upscaling: {needs_upscaling}"
            )

        except Exception as e:
            error_msg = f"Error analyzing PDF resolution: {e}"
            logger.exception(error_msg)
            raise
        else:
            return result


def quick_resolution_check(pdf_path: str | Path, min_dpi: int = 300) -> bool:
    """Quick check if PDF needs upscaling.

    Args:
        pdf_path: Path to PDF file
        min_dpi: Minimum acceptable DPI (default: 300)

    Returns:
        True if upscaling is recommended, False otherwise
    """
    analyzer = PDFResolutionAnalyzer(min_dpi_threshold=min_dpi)
    try:
        result = analyzer.analyze_pdf_resolution(pdf_path)
        return bool(result["needs_upscaling"])
    except Exception:
        logger.exception("Quick resolution check failed")
        return False
