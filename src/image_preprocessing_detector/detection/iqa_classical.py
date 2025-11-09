"""
Classical image quality assessment (IQA) detectors.

Implements fast classical computer vision methods for detecting image quality issues:
- Skew detection (Hough Transform + Projection Profile)
- Blur detection (Laplacian variance)
- Low contrast detection (Histogram analysis)
"""

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SkewDetectionResult:
    """
    Result of skew detection analysis.

    Attributes:
        is_skewed: Whether significant skew is detected
        angle: Detected skew angle in degrees (-45 to +45)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        method: Detection method used (hough, projection, ensemble)
    """

    is_skewed: bool
    angle: float
    confidence: float
    severity: Severity
    method: str


class SkewDetector:
    """
    Detects page skew using Hough Transform and projection profile analysis.

    Optimized for document images with text or structured content.
    """

    def __init__(
        self,
        threshold_low: float = 0.5,
        threshold_medium: float = 2.0,
        threshold_high: float = 5.0,
        min_line_length: int = 100,
        max_line_gap: int = 10,
    ) -> None:
        """
        Initialize skew detector.

        Args:
            threshold_low: Low severity threshold in degrees (default: 0.5°)
            threshold_medium: Medium severity threshold in degrees (default: 2.0°)
            threshold_high: High severity threshold in degrees (default: 5.0°)
            min_line_length: Minimum line length for Hough detection (default: 100)
            max_line_gap: Maximum gap between line segments (default: 10)
        """
        self.threshold_low = threshold_low
        self.threshold_medium = threshold_medium
        self.threshold_high = threshold_high
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

        logger.info(
            "Skew detector initialized",
            threshold_low=threshold_low,
            threshold_medium=threshold_medium,
            threshold_high=threshold_high,
        )

    def detect(self, image: np.ndarray) -> SkewDetectionResult:
        """
        Detect skew in an image using ensemble of methods.

        Args:
            image: Input image (BGR format, from OpenCV)

        Returns:
            SkewDetectionResult with angle and confidence

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Running skew detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Try Hough Transform method first (more accurate for text documents)
        angle_hough, confidence_hough = self._detect_hough(gray)

        # Try projection profile method as fallback
        angle_proj, confidence_proj = self._detect_projection(gray)

        # Ensemble: use method with higher confidence
        if confidence_hough >= confidence_proj:
            angle = angle_hough
            confidence = confidence_hough
            method = "hough"
        else:
            angle = angle_proj
            confidence = confidence_proj
            method = "projection"

        # If both methods have low confidence, average them
        if confidence_hough > 0.3 and confidence_proj > 0.3:
            angle = (angle_hough + angle_proj) / 2.0
            confidence = max(confidence_hough, confidence_proj)
            method = "ensemble"

        # Determine severity
        severity = self._compute_severity(abs(angle))

        # Determine if correction is needed (> 0.5 degrees)
        is_skewed = abs(angle) > self.threshold_low

        logger.debug(
            "Skew detection complete",
            angle=angle,
            confidence=confidence,
            severity=severity.value,
            method=method,
            is_skewed=is_skewed,
        )

        return SkewDetectionResult(
            is_skewed=is_skewed,
            angle=angle,
            confidence=confidence,
            severity=severity,
            method=method,
        )

    def _detect_hough(self, gray: np.ndarray) -> tuple[float, float]:
        """
        Detect skew using Hough Line Transform.

        Args:
            gray: Grayscale image

        Returns:
            Tuple of (angle, confidence)
        """
        try:
            # Edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Hough Line Transform
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=self.min_line_length,
                maxLineGap=self.max_line_gap,
            )

            if lines is None or len(lines) == 0:
                return 0.0, 0.0

            # Calculate angles for all lines
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Skip vertical lines (infinite slope)
                if x2 - x1 == 0:
                    continue
                # Calculate angle in degrees
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Normalize to -45 to +45 range
                if angle > 45:
                    angle -= 90
                elif angle < -45:
                    angle += 90
                angles.append(angle)

            if not angles:
                return 0.0, 0.0

            # Use median angle (more robust than mean)
            angle = float(np.median(angles))

            # Confidence based on consistency of detected lines
            std = np.std(angles)
            confidence = 1.0 / (1.0 + std / 10.0)  # High std = low confidence

            return angle, float(confidence)

        except Exception as e:
            logger.warning("Hough detection failed", error=str(e))
            return 0.0, 0.0

    def _detect_projection(self, gray: np.ndarray) -> tuple[float, float]:
        """
        Detect skew using horizontal projection profile.

        Args:
            gray: Grayscale image

        Returns:
            Tuple of (angle, confidence)
        """
        try:
            # Binarize image
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # Try multiple angles and find the one with maximum projection variance
            angles_to_test = np.arange(-10, 10, 0.5)  # Test -10 to +10 degrees
            max_variance = 0.0
            best_angle = 0.0

            h, w = binary.shape
            center = (w // 2, h // 2)

            for angle in angles_to_test:
                # Rotate image
                M = cv2.getRotationMatrix2D(center, angle, 1.0)  # noqa: N806  # fmt: skip
                rotated = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC)

                # Calculate horizontal projection
                projection = np.sum(rotated, axis=1)

                # Calculate variance of projection
                variance = np.var(projection)

                if variance > max_variance:
                    max_variance = variance
                    best_angle = angle

            # Normalize confidence based on variance magnitude
            # Higher variance = more text-like structure = higher confidence
            confidence = min(1.0, max_variance / (h * 255 * 10))  # Normalize

            return float(-best_angle), float(confidence)  # Negate for correction

        except Exception as e:
            logger.warning("Projection detection failed", error=str(e))
            return 0.0, 0.0

    def _compute_severity(self, abs_angle: float) -> Severity:
        """
        Compute severity based on absolute skew angle.

        Args:
            abs_angle: Absolute value of skew angle

        Returns:
            Severity level
        """
        if abs_angle >= self.threshold_high:
            return Severity.CRITICAL
        if abs_angle >= self.threshold_medium:
            return Severity.HIGH
        if abs_angle >= self.threshold_low:
            return Severity.MEDIUM
        return Severity.LOW


@dataclass
class BlurDetectionResult:
    """
    Result of blur detection analysis.

    Attributes:
        is_blurred: Whether significant blur is detected
        score: Laplacian variance score (higher = sharper)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
    """

    is_blurred: bool
    score: float
    confidence: float
    severity: Severity


class BlurDetector:
    """
    Detects image blur using Laplacian variance.

    Higher variance indicates sharper images (more high-frequency content).
    """

    def __init__(
        self,
        threshold_critical: float = 50.0,
        threshold_high: float = 100.0,
        threshold_medium: float = 200.0,
    ) -> None:
        """
        Initialize blur detector.

        Args:
            threshold_critical: Critical blur threshold (< 50 = severe blur)
            threshold_high: High blur threshold (< 100 = noticeable blur)
            threshold_medium: Medium blur threshold (< 200 = slight blur)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium

        logger.info(
            "Blur detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

    def detect(self, image: np.ndarray) -> BlurDetectionResult:
        """
        Detect blur using Laplacian variance.

        Args:
            image: Input image (BGR format)

        Returns:
            BlurDetectionResult with score and severity

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Running blur detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(laplacian.var())

        # Determine severity
        if variance < self.threshold_critical:
            severity = Severity.CRITICAL
        elif variance < self.threshold_high:
            severity = Severity.HIGH
        elif variance < self.threshold_medium:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        # Is blurred if below medium threshold
        is_blurred = variance < self.threshold_medium

        # Confidence is always high for Laplacian variance (reliable metric)
        confidence = 0.9

        logger.debug(
            "Blur detection complete",
            variance=variance,
            is_blurred=is_blurred,
            severity=severity.value,
        )

        return BlurDetectionResult(
            is_blurred=is_blurred,
            score=variance,
            confidence=confidence,
            severity=severity,
        )


@dataclass
class ContrastDetectionResult:
    """
    Result of contrast detection analysis.

    Attributes:
        is_low_contrast: Whether low contrast is detected
        score: Contrast score (0.0-1.0, higher = better contrast)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
    """

    is_low_contrast: bool
    score: float
    confidence: float
    severity: Severity


class ContrastDetector:
    """
    Detects low contrast using histogram analysis.

    Analyzes distribution of pixel intensities to determine contrast quality.
    """

    def __init__(
        self,
        threshold_critical: float = 0.08,
        threshold_high: float = 0.13,
        threshold_medium: float = 0.18,
    ) -> None:
        """
        Initialize contrast detector.

        Thresholds calibrated on real-world DocLayNet documents:
        - Mean contrast: 0.18, Median: 0.18, Std: 0.047
        - Synthetic images have higher contrast (~0.50) than real-world

        Args:
            threshold_critical: Critical contrast threshold (< 0.08 = very low, mean - 2sigma)
            threshold_high: High severity threshold (< 0.13 = low, mean - 1sigma)
            threshold_medium: Medium severity threshold (< 0.18 = slightly low, median)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium

        logger.info(
            "Contrast detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

    def detect(self, image: np.ndarray) -> ContrastDetectionResult:
        """
        Detect low contrast using histogram analysis.

        Args:
            image: Input image (BGR format)

        Returns:
            ContrastDetectionResult with score and severity

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Running contrast detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()  # Normalize

        # Calculate RMS contrast (root mean square)
        mean_intensity = np.sum(np.arange(256) * hist)
        variance = np.sum(((np.arange(256) - mean_intensity) ** 2) * hist)
        rms_contrast = np.sqrt(variance) / 255.0  # Normalize to 0-1

        # Alternative: Use standard deviation of histogram
        std_dev = gray.std() / 255.0  # Normalize to 0-1

        # Use average of both metrics
        score = float((rms_contrast + std_dev) / 2.0)

        # Determine severity
        if score < self.threshold_critical:
            severity = Severity.CRITICAL
        elif score < self.threshold_high:
            severity = Severity.HIGH
        elif score < self.threshold_medium:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        # Low contrast if below medium threshold
        is_low_contrast = score < self.threshold_medium

        # Confidence is high for histogram-based metrics
        confidence = 0.85

        logger.debug(
            "Contrast detection complete",
            score=score,
            is_low_contrast=is_low_contrast,
            severity=severity.value,
        )

        return ContrastDetectionResult(
            is_low_contrast=is_low_contrast,
            score=score,
            confidence=confidence,
            severity=severity,
        )


# Convenience functions
def detect_skew(image: np.ndarray) -> SkewDetectionResult:
    """
    Convenience function for skew detection.

    Args:
        image: Input image (BGR format)

    Returns:
        SkewDetectionResult

    Example:
        >>> img = cv2.imread("document.jpg")
        >>> result = detect_skew(img)
        >>> if result.is_skewed:
        ...     print(f"Skew detected: {result.angle:.2f}° ({result.severity.value})")
    """
    detector = SkewDetector()
    return detector.detect(image)


def detect_blur(image: np.ndarray) -> BlurDetectionResult:
    """
    Convenience function for blur detection.

    Args:
        image: Input image (BGR format)

    Returns:
        BlurDetectionResult

    Example:
        >>> img = cv2.imread("photo.jpg")
        >>> result = detect_blur(img)
        >>> if result.is_blurred:
        ...     print(
        ...         f"Blur detected: score={result.score:.1f} ({result.severity.value})"
        ...     )
    """
    detector = BlurDetector()
    return detector.detect(image)


def detect_contrast(image: np.ndarray) -> ContrastDetectionResult:
    """
    Convenience function for contrast detection.

    Args:
        image: Input image (BGR format)

    Returns:
        ContrastDetectionResult

    Example:
        >>> img = cv2.imread("scan.jpg")
        >>> result = detect_contrast(img)
        >>> if result.is_low_contrast:
        ...     print(
        ...         f"Low contrast: score={result.score:.2f} ({result.severity.value})"
        ...     )
    """
    detector = ContrastDetector()
    return detector.detect(image)
