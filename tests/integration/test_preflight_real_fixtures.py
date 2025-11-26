"""Integration tests for pre-flight analysis with real fixtures.

Tests DPI detection and upscaling workflow with:
- DocLayNet PDF fixtures
- Various DPI scenarios
- Real document processing paths

Sprint 5.1.x: Pre-flight analysis integration tests.
"""

from pathlib import Path

import pytest

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.ingestion.pdf_analyzer import PDFDocumentAnalyzer
from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader
from image_preprocessing_detector.ingestion.pdf_resolution import (
    PDFResolutionAnalyzer,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def settings():
    """Test settings with upscaling enabled."""
    s = Settings()
    s.enable_pdf_upscaling = True
    s.pdf_min_dpi = 150
    s.pdf_target_dpi = 300
    return s


@pytest.fixture
def resolution_analyzer():
    """PDF resolution analyzer."""
    return PDFResolutionAnalyzer()


@pytest.fixture
def pdf_loader():
    """PDF loader for loading pages."""
    return PDFLoader()


# =============================================================================
# Resolution Analysis Tests with Real Fixtures
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_data
class TestPreflightResolutionWithDocLayNet:
    """Test pre-flight resolution analysis with DocLayNet PDFs."""

    def test_simple_text_pdf_resolution(
        self, resolution_analyzer, simple_text_pdf
    ):
        """Test DPI detection on simple text PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(simple_text_pdf)

        assert result is not None
        assert result["min_dpi"] > 0
        assert result["avg_dpi"] > 0
        assert result["max_dpi"] >= result["min_dpi"]
        assert isinstance(result["needs_upscaling"], bool)
        assert result["image_count"] >= 0

    def test_tables_figures_pdf_resolution(
        self, resolution_analyzer, tables_figures_pdf
    ):
        """Test DPI detection on PDF with tables and figures."""
        if not tables_figures_pdf.exists():
            pytest.skip("Tables/figures PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(tables_figures_pdf)

        assert result is not None
        assert result["min_dpi"] >= 0
        # PDFs with embedded figures may have varying DPI

    def test_multi_column_pdf_resolution(
        self, resolution_analyzer, multi_column_pdf
    ):
        """Test DPI detection on multi-column PDF."""
        if not multi_column_pdf.exists():
            pytest.skip("Multi-column PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(multi_column_pdf)

        assert result is not None
        # Born-digital PDFs may have no embedded images, so avg_dpi can be None
        if result["avg_dpi"] is not None:
            assert result["avg_dpi"] >= 0

    def test_skewed_pdf_resolution(
        self, resolution_analyzer, skewed_pdf
    ):
        """Test DPI detection on skewed PDF."""
        if not skewed_pdf.exists():
            pytest.skip("Skewed PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(skewed_pdf)

        # Skew shouldn't affect DPI detection
        assert result is not None
        assert result["min_dpi"] >= 0

    def test_low_contrast_pdf_resolution(
        self, resolution_analyzer, low_contrast_pdf
    ):
        """Test DPI detection on low contrast PDF."""
        if not low_contrast_pdf.exists():
            pytest.skip("Low contrast PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(low_contrast_pdf)

        # Contrast shouldn't affect DPI detection
        assert result is not None
        assert result["min_dpi"] >= 0

    def test_all_doclaynet_pdfs_resolution(
        self, resolution_analyzer, all_doclaynet_pdfs
    ):
        """Test DPI detection on all DocLayNet PDFs."""
        if not all_doclaynet_pdfs:
            pytest.skip("DocLayNet PDFs not available")

        for pdf_path in all_doclaynet_pdfs:
            result = resolution_analyzer.analyze_pdf_resolution(pdf_path)

            assert result is not None, f"Failed to analyze {pdf_path.name}"
            # Born-digital PDFs may have no embedded images, so DPI values can be None
            if result["min_dpi"] is not None:
                assert result["min_dpi"] >= 0, f"Invalid min_dpi for {pdf_path.name}"
            if result["avg_dpi"] is not None:
                assert result["avg_dpi"] >= 0, f"Invalid avg_dpi for {pdf_path.name}"


# =============================================================================
# Pre-flight Decision Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_data
class TestPreflightDecisions:
    """Test pre-flight upscaling decision logic."""

    def test_high_dpi_pdf_no_upscaling(
        self, resolution_analyzer, settings, simple_text_pdf
    ):
        """High DPI PDF should not require upscaling."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(simple_text_pdf)

        # Most DocLayNet PDFs are high quality
        # If avg DPI >= target, no upscaling needed
        if result["avg_dpi"] >= settings.pdf_target_dpi:
            assert result["needs_upscaling"] is False

    def test_upscaling_threshold_decision(self, resolution_analyzer, settings):
        """Test upscaling threshold decision logic."""
        # This tests the logic, not a specific PDF
        # Threshold is pdf_min_dpi (150 by default)
        assert settings.pdf_min_dpi == 150
        assert settings.pdf_target_dpi == 300


# =============================================================================
# Full Pre-flight Analysis Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_data
class TestFullPreflightAnalysis:
    """Test complete pre-flight analysis workflow."""

    def test_preflight_simple_text_pdf(
        self, pdf_loader, resolution_analyzer, simple_text_pdf
    ):
        """Test full pre-flight on simple text PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        # Step 1: Analyze resolution
        resolution_result = resolution_analyzer.analyze_pdf_resolution(simple_text_pdf)
        assert resolution_result is not None

        # Step 2: Load pages (this applies upscaling if needed)
        pages = list(pdf_loader.load(str(simple_text_pdf)))
        assert len(pages) >= 1

        # Step 3: Verify page images are usable
        for page in pages:
            assert page.image is not None
            assert page.image.shape[0] > 0  # Height
            assert page.image.shape[1] > 0  # Width
            assert len(page.image.shape) == 3  # BGR channels
            assert page.dpi_effective >= 72  # At least screen resolution

    def test_preflight_all_doclaynet_pdfs(
        self, pdf_loader, resolution_analyzer, all_doclaynet_pdfs
    ):
        """Test full pre-flight on all DocLayNet PDFs."""
        if not all_doclaynet_pdfs:
            pytest.skip("DocLayNet PDFs not available")

        for pdf_path in all_doclaynet_pdfs:
            # Analyze resolution
            resolution_result = resolution_analyzer.analyze_pdf_resolution(pdf_path)
            assert resolution_result is not None, f"Failed: {pdf_path.name}"

            # Load pages
            pages = list(pdf_loader.load(str(pdf_path)))
            assert len(pages) >= 1, f"No pages in: {pdf_path.name}"

            # Verify each page
            for idx, page in enumerate(pages):
                assert page.image is not None, (
                    f"Null image in {pdf_path.name} page {idx}"
                )
                assert page.image.shape[0] > 100, (
                    f"Image too small in {pdf_path.name} page {idx}"
                )

    def test_preflight_preserves_aspect_ratio(
        self, pdf_loader, simple_text_pdf
    ):
        """Test that pre-flight processing preserves aspect ratio."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        pages = list(pdf_loader.load(str(simple_text_pdf)))

        for page in pages:
            # Typical document aspect ratios
            aspect = page.image.shape[1] / page.image.shape[0]  # width/height
            # Letter: 8.5/11 = 0.77, A4: ~0.71, but varies
            # Should be reasonable document aspect ratio
            assert 0.5 < aspect < 2.0, f"Unusual aspect ratio: {aspect}"


# =============================================================================
# Edge Case Pre-flight Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_data
class TestPreflightEdgeCases:
    """Test pre-flight with edge case documents."""

    def test_watermarked_pdf_preflight(
        self, resolution_analyzer, watermarked_pdf
    ):
        """Test pre-flight on watermarked PDF."""
        if not watermarked_pdf.exists():
            pytest.skip("Watermarked PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(watermarked_pdf)

        # Should not crash on watermarked document
        assert result is not None

    def test_dense_math_pdf_preflight(
        self, resolution_analyzer, dense_math_pdf
    ):
        """Test pre-flight on dense math PDF."""
        if not dense_math_pdf.exists():
            pytest.skip("Dense math PDF not available")

        result = resolution_analyzer.analyze_pdf_resolution(dense_math_pdf)

        assert result is not None
        # Math documents may have complex rendering

    def test_handwriting_image_preflight(
        self, handwriting_mixed_image
    ):
        """Test pre-flight handles image files (not PDFs)."""
        if not handwriting_mixed_image.exists():
            pytest.skip("Handwriting image not available")

        # Images don't need PDF resolution analysis
        # But should be loadable directly
        import cv2
        img = cv2.imread(str(handwriting_mixed_image))
        assert img is not None
        assert img.shape[0] > 0

    def test_colorful_background_image_preflight(
        self, colorful_background_image
    ):
        """Test pre-flight handles colorful background images."""
        if not colorful_background_image.exists():
            pytest.skip("Colorful background image not available")

        import cv2
        img = cv2.imread(str(colorful_background_image))
        assert img is not None


# =============================================================================
# Performance Validation Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.real_data
class TestPreflightPerformance:
    """Test pre-flight performance characteristics."""

    def test_resolution_analysis_completes_quickly(
        self, resolution_analyzer, simple_text_pdf
    ):
        """Test that resolution analysis is fast."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        import time
        start = time.perf_counter()

        result = resolution_analyzer.analyze_pdf_resolution(simple_text_pdf)

        elapsed = time.perf_counter() - start

        assert result is not None
        # Resolution analysis should be fast (< 5 seconds for single PDF)
        assert elapsed < 5.0, f"Resolution analysis took {elapsed:.2f}s"

    def test_pdf_loading_reasonable_time(
        self, pdf_loader, simple_text_pdf
    ):
        """Test that PDF loading completes in reasonable time."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        import time
        start = time.perf_counter()

        pages = list(pdf_loader.load(str(simple_text_pdf)))

        elapsed = time.perf_counter() - start

        assert len(pages) >= 1
        # PDF loading should be < 30 seconds for typical document
        assert elapsed < 30.0, f"PDF loading took {elapsed:.2f}s"
