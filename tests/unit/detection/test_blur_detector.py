"""
Comprehensive unit tests for enhanced BlurDetector (Sprint 4.1.1).

Tests cover:
- Core blur detection with Laplacian variance
- Normalized blur_score (0-1)
- ROI-based blur detection
- Block-based spatial analysis
- Detailed metrics computation
- Edge cases and error handling
"""

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    BlurDetector,
    BlurMetrics,
    Severity,
    compute_laplacian_variance,
    normalize_blur_score,
)


class TestNormalizeBlurScore:
    """Test normalize_blur_score function."""

    def test_minimum_variance(self) -> None:
        """Test score at minimum variance threshold."""
        score = normalize_blur_score(10.0, min_variance=10.0, max_variance=500.0)
        assert score == 0.0

    def test_below_minimum_variance(self) -> None:
        """Test score below minimum variance returns 0."""
        score = normalize_blur_score(5.0, min_variance=10.0, max_variance=500.0)
        assert score == 0.0

    def test_maximum_variance(self) -> None:
        """Test score at maximum variance threshold."""
        score = normalize_blur_score(500.0, min_variance=10.0, max_variance=500.0)
        assert score == 1.0

    def test_above_maximum_variance(self) -> None:
        """Test score above maximum variance returns 1."""
        score = normalize_blur_score(1000.0, min_variance=10.0, max_variance=500.0)
        assert score == 1.0

    def test_midpoint_variance(self) -> None:
        """Test score at midpoint."""
        # Midpoint between 10 and 500 is 255
        score = normalize_blur_score(255.0, min_variance=10.0, max_variance=500.0)
        assert 0.4 < score < 0.6  # Should be around 0.5

    def test_linear_interpolation(self) -> None:
        """Test linear interpolation."""
        # 25% of the way from 10 to 500 should give ~0.25
        variance = 10.0 + 0.25 * (500.0 - 10.0)  # 132.5
        score = normalize_blur_score(variance, min_variance=10.0, max_variance=500.0)
        assert pytest.approx(score, abs=0.05) == 0.25

    def test_default_parameters(self) -> None:
        """Test with default min/max parameters."""
        # Default is 10.0 to 500.0
        assert normalize_blur_score(10.0) == 0.0
        assert normalize_blur_score(500.0) == 1.0


class TestComputeLaplacianVariance:
    """Test compute_laplacian_variance function."""

    def test_uniform_image_low_variance(self) -> None:
        """Test uniform image has low variance."""
        img = np.ones((100, 100), dtype=np.uint8) * 128
        variance = compute_laplacian_variance(img)
        assert variance < 1.0  # Should be very low

    def test_checkerboard_high_variance(self) -> None:
        """Test checkerboard pattern has high variance."""
        img = np.zeros((100, 100), dtype=np.uint8)
        # Create checkerboard
        for i in range(0, 100, 10):
            for j in range(0, 100, 10):
                if (i // 10 + j // 10) % 2 == 0:
                    img[i : i + 10, j : j + 10] = 255
        variance = compute_laplacian_variance(img)
        assert variance > 100.0  # Should be high

    def test_blurred_image_lower_variance(self) -> None:
        """Test blurred image has lower variance than sharp."""
        # Create sharp image
        sharp = np.zeros((100, 100), dtype=np.uint8)
        for i in range(0, 100, 10):
            for j in range(0, 100, 10):
                if (i // 10 + j // 10) % 2 == 0:
                    sharp[i : i + 10, j : j + 10] = 255

        # Blur it
        blurred = cv2.GaussianBlur(sharp, (11, 11), 5)

        var_sharp = compute_laplacian_variance(sharp)
        var_blurred = compute_laplacian_variance(blurred)

        assert var_blurred < var_sharp


class TestBlurDetectorInit:
    """Test BlurDetector initialization."""

    def test_default_parameters(self) -> None:
        """Test default parameter values."""
        detector = BlurDetector()

        assert detector.threshold_critical == 50.0
        assert detector.threshold_high == 100.0
        assert detector.threshold_medium == 200.0
        assert detector.min_variance == 10.0
        assert detector.max_variance == 500.0
        assert detector.block_size == 64

    def test_custom_parameters(self) -> None:
        """Test custom parameter initialization."""
        detector = BlurDetector(
            threshold_critical=30.0,
            threshold_high=80.0,
            threshold_medium=150.0,
            min_variance=5.0,
            max_variance=1000.0,
            block_size=32,
        )

        assert detector.threshold_critical == 30.0
        assert detector.threshold_high == 80.0
        assert detector.threshold_medium == 150.0
        assert detector.min_variance == 5.0
        assert detector.max_variance == 1000.0
        assert detector.block_size == 32


class TestBlurDetectorDetect:
    """Test BlurDetector.detect() method."""

    def test_detect_sharp_image(self) -> None:
        """Test detection on sharp image with edges."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        # Create checkerboard
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        detector = BlurDetector()
        result = detector.detect(img)

        assert isinstance(result, BlurDetectionResult)
        assert result.is_blurred is False
        assert result.score > 200.0  # High variance
        assert 0.0 <= result.blur_score <= 1.0
        assert result.blur_score > 0.5  # Should be on the sharp side
        assert result.severity == Severity.LOW
        assert result.confidence > 0.8
        assert result.metrics is None  # Not requested

    def test_detect_blurred_image(self) -> None:
        """Test detection on blurred image."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        # Apply heavy blur
        blurred = cv2.GaussianBlur(img, (21, 21), 10)

        detector = BlurDetector()
        result = detector.detect(blurred)

        assert result.is_blurred is True
        assert result.score < 200.0  # Lower variance
        assert result.blur_score < 0.5  # Should be on the blurry side
        assert result.severity in [Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

    def test_detect_with_detailed_metrics(self) -> None:
        """Test detection with detailed metrics enabled."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        detector = BlurDetector()
        result = detector.detect(img, compute_detailed_metrics=True)

        assert result.metrics is not None
        assert isinstance(result.metrics, BlurMetrics)
        assert result.metrics.laplacian_variance == result.score
        assert result.metrics.blur_score == result.blur_score
        assert result.metrics.local_variance_mean > 0
        assert result.metrics.local_variance_std >= 0
        assert 0.0 <= result.metrics.edge_density <= 1.0

    def test_detect_grayscale_input(self) -> None:
        """Test detection with grayscale input."""
        gray = np.zeros((500, 500), dtype=np.uint8)
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    gray[i : i + 25, j : j + 25] = 255

        detector = BlurDetector()
        result = detector.detect(gray)

        assert isinstance(result, BlurDetectionResult)
        assert result.is_blurred is False

    def test_detect_rgba_input(self) -> None:
        """Test detection with RGBA input."""
        rgba = np.zeros((500, 500, 4), dtype=np.uint8)
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    rgba[i : i + 25, j : j + 25] = [255, 255, 255, 255]

        detector = BlurDetector()
        result = detector.detect(rgba)

        assert isinstance(result, BlurDetectionResult)

    def test_detect_empty_image_raises(self) -> None:
        """Test ValueError for empty image."""
        detector = BlurDetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(np.array([]))

    def test_detect_none_image_raises(self) -> None:
        """Test ValueError for None image."""
        detector = BlurDetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(None)  # type: ignore

    def test_blur_score_range(self) -> None:
        """Test that blur_score is always in [0, 1] range."""
        detector = BlurDetector()

        # Test with various images
        test_images = [
            np.ones((100, 100, 3), dtype=np.uint8) * 128,  # Uniform
            np.zeros((100, 100, 3), dtype=np.uint8),  # Black
            np.ones((100, 100, 3), dtype=np.uint8) * 255,  # White
        ]

        for img in test_images:
            result = detector.detect(img)
            assert 0.0 <= result.blur_score <= 1.0


class TestBlurDetectorDetectROI:
    """Test BlurDetector.detect_roi() method."""

    def test_detect_roi_basic(self) -> None:
        """Test basic ROI detection."""
        # Create image with sharp region and blurry region
        img = np.zeros((500, 500, 3), dtype=np.uint8)

        # Sharp left half (checkerboard)
        for i in range(0, 500, 25):
            for j in range(0, 250, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        # Blurry right half
        for i in range(0, 500, 25):
            for j in range(250, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255
        img[:, 250:] = cv2.GaussianBlur(img[:, 250:], (21, 21), 10)

        detector = BlurDetector()

        # Test sharp region
        sharp_result = detector.detect_roi(img, bbox=(0, 0, 200, 500))
        # Test blurry region
        blurry_result = detector.detect_roi(img, bbox=(300, 0, 200, 500))

        # Sharp region should have higher score
        assert sharp_result.score > blurry_result.score

    def test_detect_roi_coco_format(self) -> None:
        """Test ROI detection uses COCO format (x, y, w, h)."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        for i in range(100, 300):
            for j in range(100, 300):
                img[i, j] = [255, 255, 255]

        detector = BlurDetector()
        # COCO format: x=100, y=100, width=200, height=200
        result = detector.detect_roi(img, bbox=(100, 100, 200, 200))

        assert isinstance(result, BlurDetectionResult)

    def test_detect_roi_invalid_bbox(self) -> None:
        """Test ValueError for invalid bbox."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        detector = BlurDetector()

        with pytest.raises(ValueError, match="Invalid bbox"):
            detector.detect_roi(img, bbox=(0, 0, 0, 0))

        with pytest.raises(ValueError, match="Invalid bbox"):
            detector.detect_roi(img, bbox=(0, 0, -10, 100))

    def test_detect_roi_empty_image_raises(self) -> None:
        """Test ValueError for empty image."""
        detector = BlurDetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect_roi(np.array([]), bbox=(0, 0, 10, 10))


class TestBlurDetectorDetectBlocks:
    """Test BlurDetector.detect_blocks() method."""

    def test_detect_blocks_basic(self) -> None:
        """Test basic block detection."""
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        for i in range(0, 256, 25):
            for j in range(0, 256, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        detector = BlurDetector(block_size=64)
        results = detector.detect_blocks(img)

        # Should have (256/64)^2 = 16 blocks
        assert len(results) == 16

        for bbox, result in results:
            assert len(bbox) == 4
            assert bbox[2] == 64  # width
            assert bbox[3] == 64  # height
            assert isinstance(result, BlurDetectionResult)
            assert 0.0 <= result.blur_score <= 1.0

    def test_detect_blocks_custom_size(self) -> None:
        """Test block detection with custom block size."""
        img = np.zeros((256, 256, 3), dtype=np.uint8)

        detector = BlurDetector(block_size=64)
        results = detector.detect_blocks(img, block_size=128)

        # Should have (256/128)^2 = 4 blocks
        assert len(results) == 4

    def test_detect_blocks_non_divisible_size(self) -> None:
        """Test block detection when image size is not divisible."""
        img = np.zeros((300, 300, 3), dtype=np.uint8)

        detector = BlurDetector(block_size=64)
        results = detector.detect_blocks(img)

        # Should have floor(300/64) * floor(300/64) = 4*4 = 16 blocks
        assert len(results) == 16

    def test_detect_blocks_empty_image_raises(self) -> None:
        """Test ValueError for empty image."""
        detector = BlurDetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect_blocks(np.array([]))


class TestBlurDetectorGrayscaleConversion:
    """Test BlurDetector grayscale conversion."""

    def test_bgr_to_grayscale(self) -> None:
        """Test BGR image is correctly converted."""
        bgr = np.zeros((100, 100, 3), dtype=np.uint8)
        bgr[:, :, 0] = 50  # Blue
        bgr[:, :, 1] = 100  # Green
        bgr[:, :, 2] = 150  # Red

        detector = BlurDetector()
        gray = detector._to_grayscale(bgr)

        assert gray.shape == (100, 100)
        assert gray.dtype == np.uint8

    def test_grayscale_passthrough(self) -> None:
        """Test grayscale image is passed through."""
        gray_input = np.ones((100, 100), dtype=np.uint8) * 128

        detector = BlurDetector()
        gray = detector._to_grayscale(gray_input)

        assert gray.shape == (100, 100)
        np.testing.assert_array_equal(gray, gray_input)

    def test_single_channel_extraction(self) -> None:
        """Test single channel image is extracted correctly."""
        single_channel = np.ones((100, 100, 1), dtype=np.uint8) * 128

        detector = BlurDetector()
        gray = detector._to_grayscale(single_channel)

        assert gray.shape == (100, 100)

    def test_bgra_to_grayscale(self) -> None:
        """Test BGRA image is correctly converted."""
        bgra = np.zeros((100, 100, 4), dtype=np.uint8)
        bgra[:, :, 0] = 50  # Blue
        bgra[:, :, 1] = 100  # Green
        bgra[:, :, 2] = 150  # Red
        bgra[:, :, 3] = 255  # Alpha

        detector = BlurDetector()
        gray = detector._to_grayscale(bgra)

        assert gray.shape == (100, 100)


class TestBlurDetectorSeverity:
    """Test BlurDetector severity computation."""

    def test_severity_critical(self) -> None:
        """Test CRITICAL severity for very low variance."""
        detector = BlurDetector()
        severity = detector._compute_severity(30.0)
        assert severity == Severity.CRITICAL

    def test_severity_high(self) -> None:
        """Test HIGH severity for low variance."""
        detector = BlurDetector()
        severity = detector._compute_severity(75.0)
        assert severity == Severity.HIGH

    def test_severity_medium(self) -> None:
        """Test MEDIUM severity for medium variance."""
        detector = BlurDetector()
        severity = detector._compute_severity(150.0)
        assert severity == Severity.MEDIUM

    def test_severity_low(self) -> None:
        """Test LOW severity for high variance."""
        detector = BlurDetector()
        severity = detector._compute_severity(300.0)
        assert severity == Severity.LOW

    def test_severity_at_thresholds(self) -> None:
        """Test severity at exact threshold values."""
        detector = BlurDetector(
            threshold_critical=50.0,
            threshold_high=100.0,
            threshold_medium=200.0,
        )

        # Below critical
        assert detector._compute_severity(49.9) == Severity.CRITICAL
        # At critical threshold, still critical
        assert detector._compute_severity(50.0) == Severity.HIGH
        # At high threshold
        assert detector._compute_severity(100.0) == Severity.MEDIUM
        # At medium threshold
        assert detector._compute_severity(200.0) == Severity.LOW


class TestBlurMetrics:
    """Test BlurMetrics dataclass."""

    def test_blur_metrics_creation(self) -> None:
        """Test BlurMetrics can be created."""
        metrics = BlurMetrics(
            laplacian_variance=100.0,
            blur_score=0.5,
            local_variance_mean=90.0,
            local_variance_std=20.0,
            edge_density=0.15,
        )

        assert metrics.laplacian_variance == 100.0
        assert metrics.blur_score == 0.5
        assert metrics.local_variance_mean == 90.0
        assert metrics.local_variance_std == 20.0
        assert metrics.edge_density == 0.15

    def test_blur_metrics_from_detection(self) -> None:
        """Test BlurMetrics from actual detection."""
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        for i in range(0, 256, 25):
            for j in range(0, 256, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        detector = BlurDetector()
        result = detector.detect(img, compute_detailed_metrics=True)

        assert result.metrics is not None
        # Local variance should be close to global for uniform pattern
        assert abs(result.metrics.local_variance_mean - result.metrics.laplacian_variance) < result.metrics.laplacian_variance
        # Edge density should be positive for checkerboard
        assert result.metrics.edge_density > 0


class TestBlurDetectorConfidence:
    """Test BlurDetector confidence computation."""

    def test_confidence_normal_image(self) -> None:
        """Test confidence for normal-sized image."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        for i in range(0, 500, 25):
            for j in range(0, 500, 25):
                if (i // 25 + j // 25) % 2 == 0:
                    img[i : i + 25, j : j + 25] = 255

        detector = BlurDetector()
        result = detector.detect(img)

        assert result.confidence >= 0.8

    def test_confidence_small_image(self) -> None:
        """Test reduced confidence for small image."""
        small_img = np.zeros((50, 50, 3), dtype=np.uint8)
        for i in range(0, 50, 10):
            for j in range(0, 50, 10):
                if (i // 10 + j // 10) % 2 == 0:
                    small_img[i : i + 10, j : j + 10] = 255

        detector = BlurDetector()
        result = detector.detect(small_img)

        # Confidence should be reduced for small images
        assert result.confidence < 0.9

    def test_confidence_uniform_image(self) -> None:
        """Test reduced confidence for uniform image."""
        uniform_img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        detector = BlurDetector()
        result = detector.detect(uniform_img)

        # Confidence should be reduced for uniform images
        assert result.confidence < 0.8


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_black_image(self) -> None:
        """Test detection on all-black image."""
        black = np.zeros((500, 500, 3), dtype=np.uint8)

        detector = BlurDetector()
        result = detector.detect(black)

        assert isinstance(result, BlurDetectionResult)
        assert result.score < 1.0  # Very low variance
        assert result.blur_score == 0.0  # Normalized to 0
        assert result.severity == Severity.CRITICAL

    def test_all_white_image(self) -> None:
        """Test detection on all-white image."""
        white = np.ones((500, 500, 3), dtype=np.uint8) * 255

        detector = BlurDetector()
        result = detector.detect(white)

        assert isinstance(result, BlurDetectionResult)
        assert result.score < 1.0  # Very low variance
        assert result.blur_score == 0.0

    def test_high_frequency_noise(self) -> None:
        """Test detection on high-frequency noise."""
        noise = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)

        detector = BlurDetector()
        result = detector.detect(noise)

        # Random noise has very high variance
        assert result.is_blurred is False
        assert result.score > 500.0
        assert result.blur_score == 1.0

    def test_very_small_image(self) -> None:
        """Test detection on very small image."""
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        tiny[3:7, 3:7] = 255

        detector = BlurDetector()
        result = detector.detect(tiny)

        assert isinstance(result, BlurDetectionResult)
        assert result.confidence < 0.9  # Reduced for small images

    def test_large_image(self) -> None:
        """Test detection on large image."""
        large = np.zeros((2000, 2000, 3), dtype=np.uint8)
        for i in range(0, 2000, 50):
            for j in range(0, 2000, 50):
                if (i // 50 + j // 50) % 2 == 0:
                    large[i : i + 50, j : j + 50] = 255

        detector = BlurDetector()
        result = detector.detect(large)

        assert isinstance(result, BlurDetectionResult)
        assert result.is_blurred is False
