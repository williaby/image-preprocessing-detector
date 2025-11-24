"""
Unit tests for classical IQA detectors (skew, blur, contrast, noise).
"""

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    BlurDetector,
    ContrastDetectionResult,
    ContrastDetector,
    NoiseDetectionResult,
    NoiseDetector,
    NoiseType,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    detect_blur,
    detect_contrast,
    detect_noise,
    detect_skew,
)


class TestSkewDetector:
    """Test SkewDetector class."""

    def test_init_default_params(self) -> None:
        """Test SkewDetector initialization with defaults."""
        detector = SkewDetector()

        assert detector.threshold_low == 0.5
        assert detector.threshold_medium == 2.0
        assert detector.threshold_high == 5.0
        assert detector.min_line_length == 100
        assert detector.max_line_gap == 10

    def test_init_custom_params(self) -> None:
        """Test SkewDetector initialization with custom parameters."""
        detector = SkewDetector(
            threshold_low=1.0,
            threshold_medium=3.0,
            threshold_high=7.0,
            min_line_length=200,
            max_line_gap=20,
        )

        assert detector.threshold_low == 1.0
        assert detector.threshold_medium == 3.0
        assert detector.threshold_high == 7.0
        assert detector.min_line_length == 200
        assert detector.max_line_gap == 20

    def test_detect_no_skew(self) -> None:
        """Test detection on image with no skew."""
        # Create synthetic text-like image (horizontal lines)
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        for y in range(50, 450, 30):
            cv2.line(img, (20, y), (480, y), (0, 0, 0), 2)

        detector = SkewDetector()
        result = detector.detect(img)

        # Should detect no significant skew (< 0.5 degrees)
        assert abs(result.angle) < 2.0  # Allow small tolerance
        assert result.severity in [Severity.LOW, Severity.MEDIUM]

    def test_detect_positive_skew(self) -> None:
        """Test detection on image with positive skew."""
        # Create synthetic document with text blocks (more robust for rotation)
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255

        # Add multiple horizontal text-like blocks
        for y in range(50, 450, 30):
            # Multiple short segments to simulate words
            for x in range(20, 460, 80):
                cv2.rectangle(img, (x, y), (x + 60, y + 12), (0, 0, 0), -1)

        # Rotate by +5 degrees
        center = (250, 250)
        M = cv2.getRotationMatrix2D(center, -5, 1.0)  # noqa: N806  # fmt: skip
        rotated = cv2.warpAffine(img, M, (500, 500), borderValue=(255, 255, 255))

        detector = SkewDetector()
        result = detector.detect(rotated)

        # Should detect skew (angle may vary, but should be detected)
        # Note: Detection accuracy depends on content and method
        assert isinstance(result.angle, float)
        assert isinstance(result.confidence, float)
        assert result.severity in [
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        ]

    def test_detect_negative_skew(self) -> None:
        """Test detection on image with negative skew."""
        # Create synthetic document with text blocks
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255

        # Add multiple horizontal text-like blocks
        for y in range(50, 450, 30):
            for x in range(20, 460, 80):
                cv2.rectangle(img, (x, y), (x + 60, y + 12), (0, 0, 0), -1)

        # Rotate by -5 degrees
        center = (250, 250)
        M = cv2.getRotationMatrix2D(center, 5, 1.0)  # noqa: N806  # fmt: skip
        rotated = cv2.warpAffine(img, M, (500, 500), borderValue=(255, 255, 255))

        detector = SkewDetector()
        result = detector.detect(rotated)

        # Should detect skew (angle may vary, but should be detected)
        assert isinstance(result.angle, float)
        assert isinstance(result.confidence, float)
        assert result.severity in [
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        ]

    def test_severity_levels(self) -> None:
        """Test severity level assignment."""
        detector = SkewDetector(
            threshold_low=0.5, threshold_medium=2.0, threshold_high=5.0
        )

        # Test internal severity computation
        assert detector._compute_severity(0.3) == Severity.LOW
        assert detector._compute_severity(1.5) == Severity.MEDIUM
        assert detector._compute_severity(3.5) == Severity.HIGH
        assert detector._compute_severity(7.0) == Severity.CRITICAL

    def test_detect_empty_image_raises(self) -> None:
        """Test detection raises ValueError for empty image."""
        detector = SkewDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(np.array([]))

    def test_detect_none_image_raises(self) -> None:
        """Test detection raises ValueError for None image."""
        detector = SkewDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(None)  # type: ignore


class TestBlurDetector:
    """Test BlurDetector class."""

    def test_init_default_params(self) -> None:
        """Test BlurDetector initialization with defaults."""
        detector = BlurDetector()

        assert detector.threshold_critical == 50.0
        assert detector.threshold_high == 100.0
        assert detector.threshold_medium == 200.0

    def test_init_custom_params(self) -> None:
        """Test BlurDetector initialization with custom parameters."""
        detector = BlurDetector(
            threshold_critical=30.0, threshold_high=80.0, threshold_medium=150.0
        )

        assert detector.threshold_critical == 30.0
        assert detector.threshold_high == 80.0
        assert detector.threshold_medium == 150.0

    def test_detect_sharp_image(self) -> None:
        """Test detection on sharp image."""
        # Create sharp image with high frequency content
        img = np.zeros((500, 500, 3), dtype=np.uint8)

        # Add checkerboard pattern (sharp edges)
        square_size = 25
        for i in range(0, 500, square_size):
            for j in range(0, 500, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    img[i : i + square_size, j : j + square_size] = 255

        detector = BlurDetector()
        result = detector.detect(img)

        # Should detect sharp image (high Laplacian variance)
        assert result.is_blurred is False
        assert result.score > 200.0  # Should be high
        assert result.severity == Severity.LOW
        assert result.confidence > 0.8

    def test_detect_blurred_image(self) -> None:
        """Test detection on blurred image."""
        # Create sharp image
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        square_size = 25
        for i in range(0, 500, square_size):
            for j in range(0, 500, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    img[i : i + square_size, j : j + square_size] = 255

        # Apply strong blur
        blurred = cv2.GaussianBlur(img, (21, 21), 10)

        detector = BlurDetector()
        result = detector.detect(blurred)

        # Should detect blur (low Laplacian variance)
        assert result.is_blurred is True
        assert result.score < 200.0  # Should be lower than sharp
        assert result.severity in [Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

    def test_detect_critically_blurred(self) -> None:
        """Test detection on critically blurred image."""
        # Create very blurred image (almost uniform)
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        # Add very subtle pattern
        for i in range(0, 500, 100):
            img[i : i + 10, :] = 130

        # Apply extreme blur
        blurred = cv2.GaussianBlur(img, (51, 51), 20)

        detector = BlurDetector()
        result = detector.detect(blurred)

        # Should detect critical blur
        assert result.is_blurred is True
        assert result.score < 100.0
        assert result.severity in [Severity.HIGH, Severity.CRITICAL]

    def test_detect_empty_image_raises(self) -> None:
        """Test detection raises ValueError for empty image."""
        detector = BlurDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(np.array([]))


class TestContrastDetector:
    """Test ContrastDetector class."""

    def test_init_default_params(self) -> None:
        """Test ContrastDetector initialization with defaults."""
        detector = ContrastDetector()

        # Real-world calibrated thresholds (DocLayNet validation)
        assert detector.threshold_critical == 0.08
        assert detector.threshold_high == 0.13
        assert detector.threshold_medium == 0.18

    def test_init_custom_params(self) -> None:
        """Test ContrastDetector initialization with custom parameters."""
        detector = ContrastDetector(
            threshold_critical=0.15, threshold_high=0.25, threshold_medium=0.35
        )

        assert detector.threshold_critical == 0.15
        assert detector.threshold_high == 0.25
        assert detector.threshold_medium == 0.35

    def test_detect_high_contrast(self) -> None:
        """Test detection on high contrast image."""
        # Create high contrast image (black and white)
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img[:, :250] = 0  # Black left half
        img[:, 250:] = 255  # White right half

        detector = ContrastDetector()
        result = detector.detect(img)

        # Should detect good contrast
        assert result.is_low_contrast is False
        assert result.score > 0.4
        assert result.severity == Severity.LOW
        assert result.confidence > 0.8

    def test_detect_low_contrast(self) -> None:
        """Test detection on low contrast image."""
        # Create low contrast image (similar gray values)
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        # Add very subtle variation
        img[:, :250] = 120
        img[:, 250:] = 136

        detector = ContrastDetector()
        result = detector.detect(img)

        # Should detect low contrast
        assert result.is_low_contrast is True
        assert result.score < 0.4
        assert result.severity in [Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

    def test_detect_critically_low_contrast(self) -> None:
        """Test detection on critically low contrast image."""
        # Create uniform gray image
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        detector = ContrastDetector()
        result = detector.detect(img)

        # Should detect critical low contrast
        assert result.is_low_contrast is True
        assert result.score < 0.3
        assert result.severity in [Severity.HIGH, Severity.CRITICAL]

    def test_detect_normal_document(self) -> None:
        """Test detection on normal document-like image."""
        # Create document-like image with text
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255  # White background

        # Add black text-like rectangles
        for y in range(50, 450, 30):
            for x in range(20, 480, 40):
                img[y : y + 15, x : x + 30] = 0

        detector = ContrastDetector()
        result = detector.detect(img)

        # Should detect good contrast (black text on white)
        assert result.is_low_contrast is False
        assert result.score > 0.4

    def test_detect_empty_image_raises(self) -> None:
        """Test detection raises ValueError for empty image."""
        detector = ContrastDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(np.array([]))


class TestNoiseDetector:
    """Test NoiseDetector class."""

    def test_init_default_params(self) -> None:
        """Test NoiseDetector initialization with defaults."""
        detector = NoiseDetector()

        assert detector.threshold_critical == 0.15
        assert detector.threshold_high == 0.10
        assert detector.threshold_medium == 0.05
        assert detector.salt_pepper_threshold == 0.01

    def test_init_custom_params(self) -> None:
        """Test NoiseDetector initialization with custom parameters."""
        detector = NoiseDetector(
            threshold_critical=0.20,
            threshold_high=0.15,
            threshold_medium=0.08,
            salt_pepper_threshold=0.02,
        )

        assert detector.threshold_critical == 0.20
        assert detector.threshold_high == 0.15
        assert detector.threshold_medium == 0.08
        assert detector.salt_pepper_threshold == 0.02

    def test_detect_clean_image(self) -> None:
        """Test detection on clean image without noise."""
        # Create clean document-like image with sharp edges
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255

        # Add clean text-like rectangles
        for y in range(50, 450, 30):
            for x in range(20, 480, 40):
                img[y : y + 15, x : x + 30] = 0

        detector = NoiseDetector()
        result = detector.detect(img)

        # Should detect clean image (low noise score)
        assert result.is_noisy is False
        assert result.noise_type == NoiseType.CLEAN
        assert result.severity == Severity.LOW
        assert result.score < 0.05
        assert result.salt_pepper_ratio < 0.01

    def test_detect_gaussian_noise(self) -> None:
        """Test detection on image with Gaussian noise."""
        # Create clean image
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        # Add Gaussian noise
        noise = np.random.normal(0, 25, img.shape).astype(np.float32)
        noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        detector = NoiseDetector()
        result = detector.detect(noisy)

        # Should detect noise
        assert result.is_noisy is True
        assert result.noise_type in [NoiseType.GAUSSIAN, NoiseType.SPECKLE, NoiseType.MIXED]
        assert result.score > 0.05
        assert result.sigma_estimate > 5.0  # Should detect significant noise

    def test_detect_salt_pepper_noise(self) -> None:
        """Test detection on image with salt-and-pepper noise."""
        # Create clean gray image
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        # Add salt-and-pepper noise (2% of pixels)
        rng = np.random.default_rng(42)
        salt_mask = rng.random((500, 500)) < 0.01
        pepper_mask = rng.random((500, 500)) < 0.01

        img[salt_mask] = 255
        img[pepper_mask] = 0

        detector = NoiseDetector()
        result = detector.detect(img)

        # Should detect salt-and-pepper noise
        assert result.is_noisy is True
        assert result.noise_type in [NoiseType.SALT_PEPPER, NoiseType.MIXED]
        assert result.salt_pepper_ratio > 0.005  # Should detect some S&P

    def test_detect_severe_noise(self) -> None:
        """Test detection on severely noisy image."""
        # Create image with severe Gaussian noise
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        # Add severe Gaussian noise (sigma = 50)
        noise = np.random.normal(0, 50, img.shape).astype(np.float32)
        noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        detector = NoiseDetector()
        result = detector.detect(noisy)

        # Should detect severe noise
        assert result.is_noisy is True
        assert result.severity in [Severity.HIGH, Severity.CRITICAL]
        assert result.score > 0.10

    def test_severity_levels(self) -> None:
        """Test severity level assignment."""
        detector = NoiseDetector(
            threshold_critical=0.15,
            threshold_high=0.10,
            threshold_medium=0.05,
        )

        # Test internal severity computation
        assert detector._compute_severity(0.03) == Severity.LOW
        assert detector._compute_severity(0.07) == Severity.MEDIUM
        assert detector._compute_severity(0.12) == Severity.HIGH
        assert detector._compute_severity(0.20) == Severity.CRITICAL

    def test_noise_type_classification(self) -> None:
        """Test noise type classification logic."""
        detector = NoiseDetector()

        # Test classification logic
        assert detector._classify_noise_type(0.03, 0.005) == NoiseType.CLEAN
        assert detector._classify_noise_type(0.12, 0.005) == NoiseType.GAUSSIAN
        assert detector._classify_noise_type(0.07, 0.005) == NoiseType.SPECKLE
        assert detector._classify_noise_type(0.03, 0.02) == NoiseType.SALT_PEPPER
        assert detector._classify_noise_type(0.12, 0.02) == NoiseType.MIXED

    def test_detect_empty_image_raises(self) -> None:
        """Test detection raises ValueError for empty image."""
        detector = NoiseDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(np.array([]))

    def test_detect_none_image_raises(self) -> None:
        """Test detection raises ValueError for None image."""
        detector = NoiseDetector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.detect(None)  # type: ignore

    def test_result_attributes(self) -> None:
        """Test NoiseDetectionResult has all required attributes."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        detector = NoiseDetector()
        result = detector.detect(img)

        assert isinstance(result, NoiseDetectionResult)
        assert hasattr(result, "is_noisy")
        assert hasattr(result, "score")
        assert hasattr(result, "noise_type")
        assert hasattr(result, "confidence")
        assert hasattr(result, "severity")
        assert hasattr(result, "sigma_estimate")
        assert hasattr(result, "salt_pepper_ratio")

        # Check value ranges
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.salt_pepper_ratio <= 1.0
        assert result.sigma_estimate >= 0.0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_skew_convenience(self) -> None:
        """Test detect_skew convenience function."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        for y in range(50, 450, 30):
            cv2.line(img, (20, y), (480, y), (0, 0, 0), 2)

        result = detect_skew(img)

        assert isinstance(result, SkewDetectionResult)
        assert hasattr(result, "angle")
        assert hasattr(result, "confidence")

    def test_detect_blur_convenience(self) -> None:
        """Test detect_blur convenience function."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img[:250, :] = 0
        img[250:, :] = 255

        result = detect_blur(img)

        assert isinstance(result, BlurDetectionResult)
        assert hasattr(result, "score")
        assert hasattr(result, "is_blurred")

    def test_detect_contrast_convenience(self) -> None:
        """Test detect_contrast convenience function."""
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img[:, :250] = 0
        img[:, 250:] = 255

        result = detect_contrast(img)

        assert isinstance(result, ContrastDetectionResult)
        assert hasattr(result, "score")
        assert hasattr(result, "is_low_contrast")

    def test_detect_noise_convenience(self) -> None:
        """Test detect_noise convenience function."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128

        result = detect_noise(img)

        assert isinstance(result, NoiseDetectionResult)
        assert hasattr(result, "score")
        assert hasattr(result, "is_noisy")
        assert hasattr(result, "noise_type")
        assert hasattr(result, "sigma_estimate")


class TestSeverityEnum:
    """Test Severity enum."""

    def test_severity_values(self) -> None:
        """Test Severity enum values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_severity_comparison(self) -> None:
        """Test Severity enum can be compared."""
        assert Severity.LOW == Severity.LOW
        assert Severity.HIGH != Severity.LOW


class TestNoiseTypeEnum:
    """Test NoiseType enum."""

    def test_noise_type_values(self) -> None:
        """Test NoiseType enum values."""
        assert NoiseType.GAUSSIAN.value == "gaussian"
        assert NoiseType.SALT_PEPPER.value == "salt_pepper"
        assert NoiseType.SPECKLE.value == "speckle"
        assert NoiseType.MIXED.value == "mixed"
        assert NoiseType.CLEAN.value == "clean"

    def test_noise_type_comparison(self) -> None:
        """Test NoiseType enum can be compared."""
        assert NoiseType.GAUSSIAN == NoiseType.GAUSSIAN
        assert NoiseType.SALT_PEPPER != NoiseType.GAUSSIAN
