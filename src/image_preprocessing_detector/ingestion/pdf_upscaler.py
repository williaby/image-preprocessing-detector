# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""PDF upscaling utilities using OpenCV."""

import logging
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class UpscaleAlgorithm(str, Enum):
    """Supported upscaling algorithms."""

    BICUBIC = "bicubic"
    LANCZOS = "lanczos"
    INTER_CUBIC = "inter_cubic"
    INTER_LINEAR = "inter_linear"
    INTER_AREA = "inter_area"


class PDFUpscaler:
    """Upscales low-resolution PDFs to improve OCR quality."""

    def __init__(
        self,
        target_dpi: int = 300,
        algorithm: UpscaleAlgorithm = UpscaleAlgorithm.LANCZOS,
        preserve_original: bool = True,
    ) -> None:
        """Initialize PDF upscaler.

        # #CRITICAL: Target DPI: 300 DPI is standard for OCR, 600 for high-quality scans
        # #VERIFY: Higher DPI increases file size and processing time

        Args:
            target_dpi: Target DPI for upscaling (default: 300)
            algorithm: Upscaling algorithm to use
            preserve_original: Keep original file if upscaling fails
        """
        self.target_dpi = target_dpi
        self.algorithm = algorithm
        self.preserve_original = preserve_original

    def upscale_pdf(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Upscale a PDF file to target DPI.

        # #CRITICAL: Memory Management: Large PDFs can exhaust memory during upscaling
        # #VERIFY: Process page-by-page and monitor memory usage

        # #CRITICAL: File Operations: Race condition if file is deleted during processing
        # #VERIFY: Use file locking or copy to temp location

        Args:
            input_path: Path to input PDF file
            output_path: Path for output file (default: creates temp file)

        Returns:
            Dictionary containing:
                - success: bool indicating if upscaling succeeded
                - output_path: Path to upscaled PDF
                - processing_time: Time taken in seconds
                - before_size: Original file size in bytes
                - after_size: Upscaled file size in bytes
                - pages_processed: Number of pages processed
                - error_message: Error message if failed

        Raises:
            FileNotFoundError: If input PDF doesn't exist
        """
        input_path = Path(input_path)

        if not input_path.exists():
            msg = f"Input PDF not found: {input_path}"
            raise FileNotFoundError(msg)

        start_time = time.time()
        before_size = input_path.stat().st_size

        try:
            # Create output path if not provided
            if output_path is None:
                # Create temp file in same directory as input
                output_path = input_path.parent / f"{input_path.stem}_upscaled.pdf"
            else:
                output_path = Path(output_path)

            logger.info(
                f"Starting PDF upscaling: {input_path.name} -> {output_path.name}"
            )

            # #CRITICAL: PDF Operations: Document may be corrupted or password-protected
            # #VERIFY: Handle encryption and corruption gracefully
            doc = fitz.open(input_path)
            new_doc = fitz.open()  # Create new PDF

            try:
                pages_processed = 0

                for page_num in range(len(doc)):
                    try:
                        page = doc[page_num]

                        # Render page to high-resolution pixmap
                        # #ASSUME: Scaling Factor: Calculate from target DPI
                        # #VERIFY: May need adjustment for very large or small pages
                        mat = fitz.Matrix(self.target_dpi / 72, self.target_dpi / 72)
                        pix = page.get_pixmap(matrix=mat)

                        # Convert to numpy array for OpenCV processing
                        img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            pix.height, pix.width, pix.n
                        )

                        # PyMuPDF's matrix transform already rendered at target DPI,
                        # so no additional upscaling needed. The img_data is already
                        # at the correct resolution.
                        upscaled_img = img_data

                        # Create new page with upscaled image
                        # #CRITICAL: Page Dimensions: Must match original page size
                        # #VERIFY: Preserve aspect ratio and page dimensions
                        img_pil = Image.fromarray(upscaled_img)

                        # Calculate page dimensions in points (72 points = 1 inch)
                        page_width = page.rect.width
                        page_height = page.rect.height

                        # Create new page with same dimensions
                        new_page = new_doc.new_page(
                            width=page_width, height=page_height
                        )

                        # Insert upscaled image
                        # Create a temporary PNG to insert
                        with tempfile.NamedTemporaryFile(
                            suffix=".png", delete=False
                        ) as tmp_img:
                            tmp_img_path = tmp_img.name
                            img_pil.save(tmp_img_path, format="PNG")

                        # Insert image after context manager exits to avoid race condition
                        try:
                            new_page.insert_image(
                                new_page.rect,
                                filename=tmp_img_path,
                            )
                        finally:
                            # Clean up temp file
                            Path(tmp_img_path).unlink(missing_ok=True)

                        pages_processed += 1
                        logger.debug(f"Upscaled page {page_num + 1}/{len(doc)}")

                        # #CRITICAL: Memory Management: Release pixmap memory
                        # #VERIFY: Monitor memory usage for large PDFs
                        pix = None

                    except Exception as e:
                        logger.error(f"Error upscaling page {page_num + 1}: {e}")
                        # Copy original page if upscaling fails
                        if self.preserve_original:
                            new_page = new_doc.new_page(
                                width=page.rect.width, height=page.rect.height
                            )
                            new_page.show_pdf_page(new_page.rect, doc, page_num)
                            pages_processed += 1

                # Save upscaled PDF
                new_doc.save(output_path)
            finally:
                # Ensure documents are always closed, even on exception
                new_doc.close()
                doc.close()

            after_size = output_path.stat().st_size
            processing_time = time.time() - start_time

            result = {
                "success": True,
                "output_path": str(output_path),
                "processing_time": round(processing_time, 2),
                "before_size": before_size,
                "after_size": after_size,
                "size_increase_ratio": round(after_size / before_size, 2),
                "pages_processed": pages_processed,
                "error_message": None,
            }

            logger.info(
                f"PDF upscaling complete: {input_path.name} -> {output_path.name} "
                f"({pages_processed} pages, {processing_time:.2f}s, "
                f"{before_size / 1024:.1f}KB -> {after_size / 1024:.1f}KB)"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"PDF upscaling failed: {e}"
            logger.error(error_msg)

            return {
                "success": False,
                "output_path": None,
                "processing_time": round(processing_time, 2),
                "before_size": before_size,
                "after_size": 0,
                "size_increase_ratio": 0,
                "pages_processed": 0,
                "error_message": error_msg,
            }

    def _apply_upscaling(
        self, img: np.ndarray, target_width: int, target_height: int
    ) -> np.ndarray:
        """Apply upscaling algorithm to image.

        NOTE: This method is currently unused for PDF upscaling because PyMuPDF's
        matrix transform (line 121) already renders at target DPI. However, this
        method will be needed in Phase 2+ for standalone image upscaling (PNG,
        JPEG, TIFF), where OpenCV/PIL interpolation is required for raster images.

        Future refactoring: Extract to shared upscaling_algorithms.py utility
        for use by both pdf_upscaler.py and image_upscaler.py.

        Args:
            img: Input image as numpy array
            target_width: Target width in pixels
            target_height: Target height in pixels

        Returns:
            Upscaled image as numpy array
        """
        # Map algorithm to OpenCV/PIL methods
        if self.algorithm == UpscaleAlgorithm.BICUBIC:
            return cv2.resize(
                img, (target_width, target_height), interpolation=cv2.INTER_CUBIC
            )

        if self.algorithm == UpscaleAlgorithm.LANCZOS:
            # Use PIL for Lanczos (generally better quality)
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            img_pil = img_pil.resize(
                (target_width, target_height), Image.Resampling.LANCZOS
            )
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        if self.algorithm == UpscaleAlgorithm.INTER_CUBIC:
            return cv2.resize(
                img, (target_width, target_height), interpolation=cv2.INTER_CUBIC
            )

        if self.algorithm == UpscaleAlgorithm.INTER_LINEAR:
            return cv2.resize(
                img, (target_width, target_height), interpolation=cv2.INTER_LINEAR
            )

        if self.algorithm == UpscaleAlgorithm.INTER_AREA:
            return cv2.resize(
                img, (target_width, target_height), interpolation=cv2.INTER_AREA
            )

        # Default to Lanczos
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        img_pil = img_pil.resize(
            (target_width, target_height), Image.Resampling.LANCZOS
        )
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def upscale_if_needed(
    pdf_path: str | Path,
    min_dpi: int = 300,
    target_dpi: int = 300,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Analyze PDF and upscale if resolution is below threshold.

    Convenience function that combines resolution analysis and upscaling.

    Args:
        pdf_path: Path to PDF file
        min_dpi: Minimum acceptable DPI (default: 300)
        target_dpi: Target DPI for upscaling (default: 300)
        output_path: Optional output path (default: creates temp file)

    Returns:
        Dictionary with upscaling results (or skipped if not needed)
    """
    from image_preprocessing_detector.ingestion.pdf_resolution import (
        quick_resolution_check,
    )

    needs_upscaling = quick_resolution_check(pdf_path, min_dpi)

    if not needs_upscaling:
        logger.info(
            f"PDF resolution is acceptable, skipping upscaling: {Path(pdf_path).name}"
        )
        return {
            "success": True,
            "upscaling_skipped": True,
            "output_path": str(pdf_path),
            "processing_time": 0,
        }

    logger.info(f"PDF resolution below {min_dpi} DPI, upscaling to {target_dpi} DPI")
    upscaler = PDFUpscaler(target_dpi=target_dpi)
    return upscaler.upscale_pdf(pdf_path, output_path)
