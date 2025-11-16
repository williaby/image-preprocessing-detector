# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

# ruff: noqa: T201
"""Integration tests for PDF resolution detection and upscaling (Phase 1c).

This module tests the end-to-end workflow of:
1. Detecting low-resolution PDFs
2. Upscaling them to 300 DPI
3. Verifying the upscaling was successful
4. Integration with DocumentRouter
"""

import logging
import tempfile
from collections.abc import Generator
from pathlib import Path

import fitz  # PyMuPDF
import pytest
from PIL import Image

from image_preprocessing_detector.ingestion.pdf_analyzer import PDFDocumentAnalyzer
from image_preprocessing_detector.ingestion.pdf_resolution import (
    PDFResolutionAnalyzer,
)

logger = logging.getLogger(__name__)

# DocumentRouter not yet implemented in this project - commenting out for Phase 1B
# from image_preprocessing_detector.ingestion.router import DocumentRouter


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def low_res_pdf(temp_dir: Path) -> Path:
    """Create a low-resolution test PDF (150 DPI)."""
    pdf_path = temp_dir / "low_res_test.pdf"

    # Create a simple image at 150 DPI
    # 8.5 x 11 inches at 150 DPI = 1275 x 1650 pixels
    img = Image.new("RGB", (1275, 1650), color="white")

    # Draw some simple content
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)

    # Draw text (font size scaled for 150 DPI)
    try:
        # Try to use a default font
        draw.text((50, 50), "Low Resolution Test PDF (150 DPI)", fill="black")
        draw.text((50, 100), "This PDF should be upscaled to 300 DPI", fill="black")
    except Exception:
        # Fallback if font not available - test PDF can still be created without text
        logger.warning("Font unavailable, creating PDF without text")

    # Save as JPEG with proper DPI metadata (more compatible than PNG)
    temp_img_path = temp_dir / "temp_img.jpg"
    img.save(temp_img_path, format="JPEG", dpi=(150, 150), quality=95)

    # Create PDF and properly embed the image
    doc = fitz.open()
    # Page size: 8.5 x 11 inches = 612 x 792 points
    page = doc.new_page(width=612, height=792)

    # Insert image - use stream parameter for better embedding
    with open(temp_img_path, "rb") as f:
        img_bytes = f.read()

    # Insert image using bytes stream (ensures proper embedding)
    page.insert_image(page.rect, stream=img_bytes)

    # Save with proper compression
    doc.save(str(pdf_path), deflate=True)
    doc.close()

    # Cleanup temp image
    temp_img_path.unlink()

    return pdf_path


@pytest.fixture
def high_res_pdf(temp_dir: Path) -> Path:
    """Create a high-resolution test PDF (300 DPI)."""
    pdf_path = temp_dir / "high_res_test.pdf"

    # Create a simple image at 300 DPI
    # 8.5 x 11 inches at 300 DPI = 2550 x 3300 pixels
    img = Image.new("RGB", (2550, 3300), color="white")

    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)

    try:
        draw.text((100, 100), "High Resolution Test PDF (300 DPI)", fill="black")
        draw.text((100, 200), "This PDF should NOT be upscaled", fill="black")
    except Exception:
        # Fallback if font not available - test PDF can still be created without text
        logger.warning("Font unavailable, creating PDF without text")

    # Save as JPEG with proper DPI metadata
    temp_img_path = temp_dir / "temp_img.jpg"
    img.save(temp_img_path, format="JPEG", dpi=(300, 300), quality=95)

    # Create PDF and properly embed the image
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Insert image using bytes stream
    with open(temp_img_path, "rb") as f:
        img_bytes = f.read()

    page.insert_image(page.rect, stream=img_bytes)

    doc.save(str(pdf_path), deflate=True)
    doc.close()

    temp_img_path.unlink()

    return pdf_path


class TestPDFResolutionDetection:
    """Test PDF resolution detection accuracy."""

    def test_detect_low_resolution_pdf(self, low_res_pdf: Path) -> None:
        """Test detection of low-resolution PDF."""
        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution(low_res_pdf)

        # Verify detection
        assert result["needs_upscaling"] is True, "Should detect low-res PDF"
        assert result["min_dpi"] is not None, "Should calculate min DPI"
        assert result["min_dpi"] < 300, (
            f"Min DPI should be < 300, got {result['min_dpi']}"
        )
        assert result["image_count"] > 0, "Should detect images in PDF"
        assert result["low_res_image_count"] > 0, "Should count low-res images"

        print("\n✓ Low-res PDF detection:")
        print(f"  Min DPI: {result['min_dpi']}")
        print(f"  Avg DPI: {result['avg_dpi']}")
        print(f"  Max DPI: {result['max_dpi']}")
        print(
            f"  Low-res images: {result['low_res_image_count']}/{result['image_count']}"
        )

    def test_detect_high_resolution_pdf(self, high_res_pdf: Path) -> None:
        """Test detection of high-resolution PDF."""
        analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        result = analyzer.analyze_pdf_resolution(high_res_pdf)

        # Verify detection
        assert result["needs_upscaling"] is False, (
            "Should NOT detect high-res PDF as needing upscaling"
        )
        assert result["min_dpi"] is not None, "Should calculate min DPI"
        assert result["min_dpi"] >= 300, (
            f"Min DPI should be >= 300, got {result['min_dpi']}"
        )
        assert result["low_res_image_count"] == 0, "Should have no low-res images"

        print("\n✓ High-res PDF detection:")
        print(f"  Min DPI: {result['min_dpi']}")
        print(f"  Avg DPI: {result['avg_dpi']}")
        print(
            f"  Low-res images: {result['low_res_image_count']}/{result['image_count']}"
        )


class TestPDFUpscaling:
    """Test PDF upscaling functionality."""

    def test_upscale_low_resolution_pdf(
        self, low_res_pdf: Path, temp_dir: Path
    ) -> None:
        """Test upscaling of low-resolution PDF."""
        analyzer = PDFDocumentAnalyzer()

        # Perform analysis and upscaling
        result = analyzer.analyze(low_res_pdf, perform_upscaling=True)

        # Verify upscaling was performed
        assert result.needs_upscaling is True, "Should identify need for upscaling"
        assert result.should_use_upscaled is True, "Should recommend upscaled version"
        assert result.upscaled_path is not None, "Should create upscaled PDF"
        assert Path(result.upscaled_path).exists(), "Upscaled PDF should exist"

        # Verify upscaling result
        upscaling_result = result.upscaling_result
        assert upscaling_result.get("success") is True, "Upscaling should succeed"
        assert upscaling_result.get("pages_processed", 0) > 0, "Should process pages"

        print("\n✓ PDF upscaling:")
        print(f"  Original size: {upscaling_result.get('before_size', 0):,} bytes")
        print(f"  Upscaled size: {upscaling_result.get('after_size', 0):,} bytes")
        print(f"  Processing time: {upscaling_result.get('processing_time', 0):.2f}s")
        print(f"  Pages processed: {upscaling_result.get('pages_processed', 0)}")

        # Verify upscaled PDF has higher resolution
        upscaled_analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
        upscaled_analysis = upscaled_analyzer.analyze_pdf_resolution(
            result.upscaled_path
        )

        original_min_dpi = result.resolution_analysis.get("min_dpi", 0)
        upscaled_min_dpi = upscaled_analysis.get("min_dpi", 0)

        assert upscaled_min_dpi > original_min_dpi, (
            f"Upscaled DPI ({upscaled_min_dpi}) should be > original ({original_min_dpi})"
        )
        assert upscaled_min_dpi >= 300, (
            f"Upscaled DPI should be >= 300, got {upscaled_min_dpi}"
        )

        print("\n✓ DPI improvement:")
        print(f"  Original min DPI: {original_min_dpi}")
        print(f"  Upscaled min DPI: {upscaled_min_dpi}")
        print(f"  Improvement: {upscaled_min_dpi - original_min_dpi:.1f} DPI")

        # Cleanup
        Path(result.upscaled_path).unlink()

    def test_skip_upscaling_high_resolution_pdf(self, high_res_pdf: Path) -> None:
        """Test that high-resolution PDFs are not upscaled."""
        analyzer = PDFDocumentAnalyzer()

        # Perform analysis - use None to let it auto-detect (don't force upscaling)
        result = analyzer.analyze(high_res_pdf, perform_upscaling=None)

        # Verify upscaling was not performed
        assert result.needs_upscaling is False, "Should NOT need upscaling"
        assert result.should_use_upscaled is False, (
            "Should NOT recommend upscaled version"
        )
        assert result.upscaled_path is None, "Should NOT create upscaled PDF"

        print("\n✓ High-res PDF correctly skipped upscaling")


# Phase 1B: DocumentRouter not yet implemented - tests commented out
# TODO: Uncomment when DocumentRouter is implemented in Phase 1C
# class TestDocumentRouterIntegration:
#     """Test integration with DocumentRouter."""
#
#     def test_router_automatically_upscales_low_res_pdf(self, low_res_pdf: Path) -> None:
#         """Test that DocumentRouter automatically upscales low-res PDFs."""
#         # #CRITICAL: Parser Registration: Router needs registered parsers to work
#         # #VERIFY: This test may fail if no parsers are registered
#
#         # Create router with upscaling enabled
#         settings = Settings(
#             enable_pdf_upscaling=True,
#             pdf_min_dpi=300,
#             pdf_target_dpi=300,
#         )
#         router = DocumentRouter(settings=settings)
#
#         # Create document
#         document = router.create_document(source_path=low_res_pdf)
#
#         # Verify metadata will be added (we can't fully test without parsers)
#         assert document.format.value == "pdf", "Should detect PDF format"
#
#         print("\n✓ DocumentRouter integration:")
#         print(f"  Document format: {document.format.value}")
#         print(f"  Source path: {document.source_path}")
#
#     def test_router_respects_upscaling_config(self, low_res_pdf: Path) -> None:
#         """Test that DocumentRouter respects upscaling configuration."""
#         # Test with upscaling disabled
#         settings = Settings(enable_pdf_upscaling=False)
#         router = DocumentRouter(settings=settings)
#
#         analyzer = router.pdf_analyzer
#         result = analyzer.analyze(low_res_pdf)
#
#         # Should still detect need for upscaling
#         assert result.needs_upscaling is True, "Should detect low resolution"
#
#         # But should not create upscaled version
#         assert result.upscaled_path is None, "Should NOT upscale when disabled"
#
#         print("\n✓ Router respects upscaling config (disabled)")


class TestValidationMetrics:
    """Test validation metrics and metadata."""

    def test_upscaling_metadata_accuracy(self, low_res_pdf: Path) -> None:
        """Test that upscaling metadata is accurate."""
        analyzer = PDFDocumentAnalyzer()
        result = analyzer.analyze(low_res_pdf, perform_upscaling=True)

        # Verify metadata structure
        assert "needs_upscaling" in result.resolution_analysis
        assert "min_dpi" in result.resolution_analysis
        assert "avg_dpi" in result.resolution_analysis
        assert "image_count" in result.resolution_analysis
        assert "details" in result.resolution_analysis

        if result.upscaling_result:
            assert "success" in result.upscaling_result
            assert "processing_time" in result.upscaling_result
            assert "before_size" in result.upscaling_result
            assert "after_size" in result.upscaling_result

            # Verify size increase is reasonable (upscaled should be larger)
            before_size = result.upscaling_result.get("before_size", 0)
            after_size = result.upscaling_result.get("after_size", 0)

            if before_size > 0 and after_size > 0:
                size_ratio = after_size / before_size
                assert size_ratio > 1.0, "Upscaled PDF should be larger"
                # Note: Upscaling can create very large files (100x+) due to uncompressed images
                # This is expected - we're increasing resolution significantly
                assert size_ratio < 1000.0, (
                    "Size increase should be reasonable (< 1000x)"
                )

                print("\n✓ Metadata validation:")
                print(f"  Size increase: {size_ratio:.2f}x")

        # Cleanup
        if result.upscaled_path:
            Path(result.upscaled_path).unlink()

    def test_processing_time_reasonable(self, low_res_pdf: Path) -> None:
        """Test that processing time is reasonable."""
        analyzer = PDFDocumentAnalyzer()
        result = analyzer.analyze(low_res_pdf, perform_upscaling=True)

        # Processing should complete in reasonable time
        assert result.processing_time > 0, "Should record processing time"
        assert result.processing_time < 30, "Should complete in < 30s for test PDF"

        print(f"\n✓ Processing time: {result.processing_time:.2f}s")

        # Cleanup
        if result.upscaled_path:
            Path(result.upscaled_path).unlink()


if __name__ == "__main__":
    """Allow running tests directly for manual validation."""
    pytest.main([__file__, "-v", "-s"])
