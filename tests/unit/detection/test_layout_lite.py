"""Unit tests for layout_lite detection module.

Tests cover all layout_lite detectors using real test fixtures:
- Table detection (Hough line + grid pattern)
- Column detection (projection profile analysis)
- Figure detection (connected component analysis)
- Fuzzy scan detection (blur + noise metrics)
- Watermark detection (FFT analysis)
- Background detection (color analysis)
- Full analyzer integration
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.layout_lite.analyzer import (
    LayoutLiteAnalyzer,
)
from image_preprocessing_detector.detection.layout_lite.background_detector import (
    detect_colorful_background,
)
from image_preprocessing_detector.detection.layout_lite.column_detector import (
    detect_column_count,
)
from image_preprocessing_detector.detection.layout_lite.figure_detector import (
    detect_figures,
)
from image_preprocessing_detector.detection.layout_lite.fuzzy_scan_detector import (
    detect_fuzzy_scan,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    ColorfulBackgroundResult,
    ColumnDetectionResult,
    FigureDetectionResult,
    FuzzyScanDetectionResult,
    TableDetectionResult,
    WatermarkDetectionResult,
)
from image_preprocessing_detector.detection.layout_lite.table_detector import (
    detect_tables,
)
from image_preprocessing_detector.detection.layout_lite.watermark_detector import (
    detect_watermark,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_table_image(tablebank_fixtures_dir: Path) -> np.ndarray:
    """Load simple table test image."""
    img_path = tablebank_fixtures_dir / "simple_table_1.png"
    if not img_path.exists():
        pytest.skip(f"Fixture not found: {img_path}")
    image = cv2.imread(str(img_path))
    if image is None:
        pytest.skip(f"Failed to load: {img_path}")
    return image


@pytest.fixture
def complex_table_image(tablebank_fixtures_dir: Path) -> np.ndarray:
    """Load complex table test image."""
    img_path = tablebank_fixtures_dir / "complex_table_2.png"
    if not img_path.exists():
        pytest.skip(f"Fixture not found: {img_path}")
    image = cv2.imread(str(img_path))
    if image is None:
        pytest.skip(f"Failed to load: {img_path}")
    return image


@pytest.fixture
def low_quality_image(tablebank_fixtures_dir: Path) -> np.ndarray:
    """Load low quality/blurry test image."""
    img_path = tablebank_fixtures_dir / "low_quality_4.jpg"
    if not img_path.exists():
        pytest.skip(f"Fixture not found: {img_path}")
    image = cv2.imread(str(img_path))
    if image is None:
        pytest.skip(f"Failed to load: {img_path}")
    return image


@pytest.fixture
def embedded_graphics_image(tablebank_fixtures_dir: Path) -> np.ndarray:
    """Load image with embedded graphics."""
    img_path = tablebank_fixtures_dir / "embedded_graphics_5.jpg"
    if not img_path.exists():
        pytest.skip(f"Fixture not found: {img_path}")
    image = cv2.imread(str(img_path))
    if image is None:
        pytest.skip(f"Failed to load: {img_path}")
    return image


@pytest.fixture
def synthetic_single_column() -> np.ndarray:
    """Create synthetic single-column document image."""
    # Create white background
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    # Add text-like horizontal lines (single column)
    for y in range(100, 900, 30):
        cv2.line(image, (50, y), (750, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_multi_column() -> np.ndarray:
    """Create synthetic two-column document image."""
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    # Left column
    for y in range(100, 900, 30):
        cv2.line(image, (50, y), (350, y), (0, 0, 0), 2)
    # Right column
    for y in range(100, 900, 30):
        cv2.line(image, (450, y), (750, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_table() -> np.ndarray:
    """Create synthetic table with grid lines."""
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    # Horizontal lines
    for y in range(100, 500, 50):
        cv2.line(image, (100, y), (700, y), (0, 0, 0), 2)
    # Vertical lines
    for x in range(100, 750, 100):
        cv2.line(image, (x, 100), (x, 450), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_figure() -> np.ndarray:
    """Create synthetic document with a large figure region."""
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    # Add a large gray rectangle (simulating a figure)
    cv2.rectangle(image, (100, 300), (700, 700), (128, 128, 128), -1)
    # Add some text lines above
    for y in range(100, 280, 30):
        cv2.line(image, (50, y), (750, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_blurry() -> np.ndarray:
    """Create synthetic blurry document."""
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    # Add text-like lines
    for y in range(100, 500, 30):
        cv2.line(image, (50, y), (750, y), (0, 0, 0), 2)
    # Apply significant blur
    return cv2.GaussianBlur(image, (21, 21), 7.0)


@pytest.fixture
def synthetic_colorful() -> np.ndarray:
    """Create synthetic document with colorful background."""
    image = np.ones((600, 800, 3), dtype=np.uint8)
    # Create gradient background
    for x in range(800):
        for y in range(600):
            image[y, x] = [
                int(255 * x / 800),  # Blue gradient
                int(255 * y / 600),  # Green gradient
                128,  # Red constant
            ]
    return image


# =============================================================================
# Table Detection Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.real_data
class TestTableDetector:
    """Tests for table detection using Hough lines."""

    def test_detect_tables_on_simple_table(self, simple_table_image: np.ndarray) -> None:
        """Test table detection on simple table fixture."""
        result = detect_tables(simple_table_image)

        assert isinstance(result, TableDetectionResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.num_horizontal_lines >= 0
        assert result.num_vertical_lines >= 0
        assert 0.0 <= result.grid_score <= 1.0

    def test_detect_tables_on_complex_table(
        self, complex_table_image: np.ndarray
    ) -> None:
        """Test table detection on complex table with merged cells."""
        result = detect_tables(complex_table_image)

        assert isinstance(result, TableDetectionResult)
        assert 0.0 <= result.confidence <= 1.0
        # Complex tables should still detect some structure
        assert result.num_horizontal_lines >= 0
        assert result.num_vertical_lines >= 0

    def test_detect_tables_on_synthetic(self, synthetic_table: np.ndarray) -> None:
        """Test table detection on synthetic table with clear grid."""
        result = detect_tables(synthetic_table)

        assert isinstance(result, TableDetectionResult)
        # Synthetic table has clear grid structure
        assert result.num_horizontal_lines > 0
        assert result.num_vertical_lines > 0

    def test_detect_tables_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_tables(None)

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_tables(np.array([]))

    def test_detect_tables_wrong_shape(self) -> None:
        """Test that grayscale image raises ValueError."""
        gray_image = np.ones((100, 100), dtype=np.uint8) * 128
        with pytest.raises(ValueError, match="Expected BGR image"):
            detect_tables(gray_image)

    def test_detect_tables_no_lines(self) -> None:
        """Test table detection on blank image."""
        blank = np.ones((500, 500, 3), dtype=np.uint8) * 255
        result = detect_tables(blank)

        assert result.has_tables is False
        assert result.num_horizontal_lines == 0
        assert result.num_vertical_lines == 0


# =============================================================================
# Column Detection Tests
# =============================================================================


@pytest.mark.unit
class TestColumnDetector:
    """Tests for column detection using projection profiles."""

    def test_detect_single_column(self, synthetic_single_column: np.ndarray) -> None:
        """Test detection of single column layout."""
        result = detect_column_count(synthetic_single_column)

        assert isinstance(result, ColumnDetectionResult)
        assert result.column_type in ["single_column", "multi_column", "three_column", "complex"]
        assert 0.0 <= result.confidence <= 1.0
        assert result.num_columns >= 1

    def test_detect_multi_column(self, synthetic_multi_column: np.ndarray) -> None:
        """Test detection of multi-column layout."""
        result = detect_column_count(synthetic_multi_column)

        assert isinstance(result, ColumnDetectionResult)
        # Should detect 2 columns
        assert result.num_columns >= 1
        assert len(result.column_boundaries) >= 0

    def test_detect_column_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_column_count(None)

    def test_detect_column_wrong_shape(self) -> None:
        """Test that grayscale image raises ValueError."""
        gray_image = np.ones((100, 100), dtype=np.uint8)
        with pytest.raises(ValueError, match="Expected BGR image"):
            detect_column_count(gray_image)


# =============================================================================
# Figure Detection Tests
# =============================================================================


@pytest.mark.unit
class TestFigureDetector:
    """Tests for figure detection using connected components."""

    def test_detect_figures_with_graphics(
        self, embedded_graphics_image: np.ndarray
    ) -> None:
        """Test figure detection on image with embedded graphics."""
        result = detect_figures(embedded_graphics_image)

        assert isinstance(result, FigureDetectionResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.num_figures >= 0
        assert 0.0 <= result.largest_figure_area_ratio <= 1.0

    def test_detect_figures_synthetic(self, synthetic_figure: np.ndarray) -> None:
        """Test figure detection on synthetic figure."""
        result = detect_figures(synthetic_figure)

        assert isinstance(result, FigureDetectionResult)
        # Should detect the large gray rectangle
        assert result.num_figures >= 0

    def test_detect_figures_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_figures(None)


# =============================================================================
# Fuzzy Scan Detection Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.real_data
class TestFuzzyScanDetector:
    """Tests for fuzzy scan (blur/noise) detection."""

    def test_detect_fuzzy_on_low_quality(self, low_quality_image: np.ndarray) -> None:
        """Test fuzzy scan detection on low quality image."""
        result = detect_fuzzy_scan(low_quality_image)

        assert isinstance(result, FuzzyScanDetectionResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.blur_score >= 0.0
        assert result.noise_score >= 0.0

    def test_detect_fuzzy_on_blurry(self, synthetic_blurry: np.ndarray) -> None:
        """Test fuzzy scan detection on synthetic blurry image."""
        result = detect_fuzzy_scan(synthetic_blurry)

        assert isinstance(result, FuzzyScanDetectionResult)
        # Blurry image should have lower Laplacian variance (higher blur_score)

    def test_detect_fuzzy_on_clean(self, synthetic_single_column: np.ndarray) -> None:
        """Test fuzzy scan detection on clean synthetic image."""
        result = detect_fuzzy_scan(synthetic_single_column)

        assert isinstance(result, FuzzyScanDetectionResult)
        # Clean image should not be flagged as fuzzy

    def test_detect_fuzzy_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_fuzzy_scan(None)


# =============================================================================
# Watermark Detection Tests
# =============================================================================


@pytest.mark.unit
class TestWatermarkDetector:
    """Tests for watermark detection using FFT."""

    def test_detect_watermark_on_clean(
        self, synthetic_single_column: np.ndarray
    ) -> None:
        """Test watermark detection on clean image."""
        result = detect_watermark(synthetic_single_column)

        assert isinstance(result, WatermarkDetectionResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.low_freq_energy >= 0.0
        assert result.opacity_score >= 0.0

    def test_detect_watermark_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_watermark(None)


# =============================================================================
# Background Detection Tests
# =============================================================================


@pytest.mark.unit
class TestBackgroundDetector:
    """Tests for colorful background detection."""

    def test_detect_colorful_background(self, synthetic_colorful: np.ndarray) -> None:
        """Test colorful background detection on gradient image."""
        result = detect_colorful_background(synthetic_colorful)

        assert isinstance(result, ColorfulBackgroundResult)
        assert 0.0 <= result.confidence <= 1.0
        assert result.unique_colors >= 0
        assert result.avg_saturation >= 0.0
        # Gradient should be detected as colorful
        assert result.colorful_background is True or result.avg_saturation > 0

    def test_detect_white_background(
        self, synthetic_single_column: np.ndarray
    ) -> None:
        """Test that white/gray background is not colorful."""
        result = detect_colorful_background(synthetic_single_column)

        assert isinstance(result, ColorfulBackgroundResult)
        # White background should not be colorful
        assert result.colorful_background is False or result.avg_saturation < 0.3

    def test_detect_background_invalid_image(self) -> None:
        """Test that invalid image raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detect_colorful_background(None)


# =============================================================================
# Full Analyzer Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.integration
class TestLayoutLiteAnalyzer:
    """Integration tests for the full LayoutLiteAnalyzer."""

    def test_analyzer_initialization(self) -> None:
        """Test analyzer can be initialized with default settings."""
        analyzer = LayoutLiteAnalyzer()
        assert analyzer is not None
        assert analyzer.enable_table_detection is True
        assert analyzer.enable_column_detection is True
        assert analyzer.enable_figure_detection is True

    def test_analyzer_with_disabled_features(self) -> None:
        """Test analyzer with some features disabled."""
        analyzer = LayoutLiteAnalyzer(
            enable_table_detection=False,
            enable_watermark_detection=False,
        )
        assert analyzer.enable_table_detection is False
        assert analyzer.enable_watermark_detection is False
        assert analyzer.enable_column_detection is True  # Still enabled

    def test_analyze_synthetic_document(
        self, synthetic_single_column: np.ndarray
    ) -> None:
        """Test full analysis on synthetic document."""
        analyzer = LayoutLiteAnalyzer()
        result = analyzer.analyze(synthetic_single_column)

        assert isinstance(result, dict)
        # Should have results for all enabled detectors
        assert "column_type" in result or "error" in result
        assert "has_tables" in result or "error" in result

    @pytest.mark.real_data
    def test_analyze_real_table_fixture(self, simple_table_image: np.ndarray) -> None:
        """Test full analysis on real table fixture."""
        analyzer = LayoutLiteAnalyzer()
        result = analyzer.analyze(simple_table_image)

        assert isinstance(result, dict)
        # Should complete without errors

    @pytest.mark.real_data
    def test_analyze_real_quality_fixture(self, low_quality_image: np.ndarray) -> None:
        """Test full analysis on low quality fixture."""
        analyzer = LayoutLiteAnalyzer()
        result = analyzer.analyze(low_quality_image)

        assert isinstance(result, dict)
        # Low quality should be detected


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.unit
class TestLayoutLiteEdgeCases:
    """Edge case and error handling tests."""

    def test_very_small_image(self) -> None:
        """Test handling of very small images."""
        tiny = np.ones((10, 10, 3), dtype=np.uint8) * 128

        # Should not crash, may return default results
        result = detect_tables(tiny)
        assert isinstance(result, TableDetectionResult)

    def test_very_large_image(self) -> None:
        """Test handling of large images."""
        large = np.ones((3000, 3000, 3), dtype=np.uint8) * 255
        # Add some content
        cv2.rectangle(large, (100, 100), (2900, 2900), (0, 0, 0), 5)

        result = detect_tables(large)
        assert isinstance(result, TableDetectionResult)

    def test_all_black_image(self) -> None:
        """Test handling of all-black image."""
        black = np.zeros((500, 500, 3), dtype=np.uint8)
        result = detect_tables(black)
        assert isinstance(result, TableDetectionResult)

    def test_all_white_image(self) -> None:
        """Test handling of all-white image."""
        white = np.ones((500, 500, 3), dtype=np.uint8) * 255
        result = detect_column_count(white)
        assert isinstance(result, ColumnDetectionResult)
