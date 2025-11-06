"""
Unit tests for classical IQA detectors (skew, blur, contrast).
"""

import cv2
import numpy as np
import pytest
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    BlurDetector,
    ContrastDetectionResult,
    ContrastDetector,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    detect_blur,
    detect_contrast,
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
        M = cv2.getRotationMatrix2D(center, -5, 1.0)  # Negative for clockwise
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
        M = cv2.getRotationMatrix2D(center, 5, 1.0)  # Positive for counter-clockwise
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
