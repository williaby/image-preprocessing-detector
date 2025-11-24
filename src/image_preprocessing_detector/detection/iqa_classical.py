"""Classical image quality assessment (IQA) detectors.

Implements fast classical computer vision methods for detecting image quality issues:
- Skew detection (Hough Transform + Projection Profile)
- Blur detection (Laplacian variance)
- Low contrast detection (Histogram analysis)
- Noise detection (Wavelet-based estimation)
"""

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from scipy import ndimage

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
    """Result of skew detection analysis.

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
    """Detects page skew using Hough Transform and projection profile analysis.

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
        """Initialize skew detector.

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
        """Detect skew in an image using ensemble of methods.

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
        """Detect skew using Hough Line Transform.

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
        """Detect skew using horizontal projection profile.

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
                M = cv2.getRotationMatrix2D(center, float(angle), 1.0)  # noqa: N806  # fmt: skip
                rotated = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC)

                # Calculate horizontal projection
                projection = np.sum(rotated, axis=1)

                # Calculate variance of projection
                variance = np.var(projection)

                if variance > max_variance:
                    max_variance = variance
                    best_angle = float(angle)  # Convert numpy.floating to Python float

            # Normalize confidence based on variance magnitude
            # Higher variance = more text-like structure = higher confidence
            confidence = min(1.0, max_variance / (h * 255 * 10))  # Normalize

            return float(-best_angle), float(confidence)  # Negate for correction

        except Exception as e:
            logger.warning("Projection detection failed", error=str(e))
            return 0.0, 0.0

    def _compute_severity(self, abs_angle: float) -> Severity:
        """Compute severity based on absolute skew angle.

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
    """Result of blur detection analysis.

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
    """Detects image blur using Laplacian variance.

    Higher variance indicates sharper images (more high-frequency content).
    """

    def __init__(
        self,
        threshold_critical: float = 50.0,
        threshold_high: float = 100.0,
        threshold_medium: float = 200.0,
    ) -> None:
        """Initialize blur detector.

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
        """Detect blur using Laplacian variance.

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
    """Result of contrast detection analysis.

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
    """Detects low contrast using histogram analysis.

    Analyzes distribution of pixel intensities to determine contrast quality.
    """

    def __init__(
        self,
        threshold_critical: float = 0.08,
        threshold_high: float = 0.13,
        threshold_medium: float = 0.18,
    ) -> None:
        """Initialize contrast detector.

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
        """Detect low contrast using histogram analysis.

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


class NoiseType(str, Enum):
    """Types of image noise."""

    GAUSSIAN = "gaussian"
    SALT_PEPPER = "salt_pepper"
    SPECKLE = "speckle"
    MIXED = "mixed"
    CLEAN = "clean"


@dataclass
class NoiseDetectionResult:
    """Result of noise detection analysis.

    Attributes:
        is_noisy: Whether significant noise is detected
        score: Noise level score (0.0-1.0, higher = more noise)
        noise_type: Classified type of noise
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        sigma_estimate: Estimated noise standard deviation
        salt_pepper_ratio: Ratio of salt-and-pepper pixels (0.0-1.0)
    """

    is_noisy: bool
    score: float
    noise_type: NoiseType
    confidence: float
    severity: Severity
    sigma_estimate: float
    salt_pepper_ratio: float


class NoiseDetector:
    """Detects image noise using wavelet-based estimation.

    Uses Median Absolute Deviation (MAD) of high-frequency coefficients
    to estimate noise level. Also detects salt-and-pepper noise patterns.

    The wavelet-based approach is robust and works well for document images
    where text edges should not be confused with noise.
    """

    # MAD normalization constant for Gaussian noise
    MAD_CONSTANT = 0.6745

    def __init__(
        self,
        threshold_critical: float = 0.15,
        threshold_high: float = 0.10,
        threshold_medium: float = 0.05,
        salt_pepper_threshold: float = 0.01,
    ) -> None:
        """Initialize noise detector.

        Args:
            threshold_critical: Critical noise threshold (> 0.15 = severe noise)
            threshold_high: High noise threshold (> 0.10 = noticeable noise)
            threshold_medium: Medium noise threshold (> 0.05 = slight noise)
            salt_pepper_threshold: Threshold for salt-and-pepper detection (> 1% pixels)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.salt_pepper_threshold = salt_pepper_threshold

        logger.info(
            "Noise detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            salt_pepper_threshold=salt_pepper_threshold,
        )

    def detect(self, image: np.ndarray) -> NoiseDetectionResult:
        """Detect noise using wavelet-based estimation.

        Args:
            image: Input image (BGR format)

        Returns:
            NoiseDetectionResult with noise level and type

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Running noise detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)

        # Estimate Gaussian noise using wavelet-based MAD
        sigma_estimate = self._estimate_noise_sigma(gray)

        # Normalize sigma to 0-1 score (assuming max reasonable sigma is ~50)
        noise_score = min(1.0, sigma_estimate / 50.0)

        # Detect salt-and-pepper noise
        salt_pepper_ratio = self._detect_salt_pepper(gray)

        # Classify noise type
        noise_type = self._classify_noise_type(noise_score, salt_pepper_ratio)

        # Determine severity based on noise score
        severity = self._compute_severity(noise_score)

        # Determine if noisy based on thresholds
        is_noisy = noise_score > self.threshold_medium or salt_pepper_ratio > self.salt_pepper_threshold

        # Confidence based on image size and detection consistency
        confidence = self._compute_confidence(gray, noise_score, salt_pepper_ratio)

        logger.debug(
            "Noise detection complete",
            noise_score=noise_score,
            sigma_estimate=sigma_estimate,
            salt_pepper_ratio=salt_pepper_ratio,
            noise_type=noise_type.value,
            severity=severity.value,
            is_noisy=is_noisy,
        )

        return NoiseDetectionResult(
            is_noisy=is_noisy,
            score=noise_score,
            noise_type=noise_type,
            confidence=confidence,
            severity=severity,
            sigma_estimate=sigma_estimate,
            salt_pepper_ratio=salt_pepper_ratio,
        )

    def _estimate_noise_sigma(self, gray: np.ndarray) -> float:
        """Estimate noise standard deviation using wavelet-based MAD.

        Uses a simple high-pass filter (approximating HH wavelet subband)
        and computes the Median Absolute Deviation for robust estimation.

        The formula is: sigma = median(|coefficients|) / 0.6745

        Args:
            gray: Grayscale image as float64

        Returns:
            Estimated noise standard deviation
        """
        # For large images, subsample to improve performance
        # Noise estimation is statistical, so subsampling is acceptable
        h, w = gray.shape
        max_dim = 500
        if h > max_dim or w > max_dim:
            scale = min(max_dim / h, max_dim / w)
            new_h, new_w = int(h * scale), int(w * scale)
            gray = cv2.resize(gray.astype(np.float32), (new_w, new_h),
                             interpolation=cv2.INTER_AREA).astype(np.float64)

        # Apply Laplacian as high-pass filter (approximates diagonal wavelet detail)
        # This captures high-frequency content which is dominated by noise
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

        # Compute Median Absolute Deviation (MAD)
        # MAD = median(|X - median(X)|)
        median_val = np.median(laplacian)
        mad = np.median(np.abs(laplacian - median_val))

        # Estimate sigma using MAD (robust to outliers like edges)
        # For Gaussian noise: sigma = MAD / 0.6745
        sigma = mad / self.MAD_CONSTANT

        return float(sigma)

    def _detect_salt_pepper(self, gray: np.ndarray) -> float:
        """Detect salt-and-pepper noise by finding isolated extreme pixels.

        Salt-and-pepper noise appears as isolated white (255) or black (0) pixels
        that differ significantly from their neighbors.

        Uses a fast morphological approach to detect truly isolated pixels,
        excluding connected regions like text or graphics.

        Args:
            gray: Grayscale image as float64

        Returns:
            Ratio of salt-and-pepper pixels (0.0-1.0)
        """
        # Convert to uint8 for processing
        gray_uint8 = gray.astype(np.uint8)

        # For large images, subsample to improve performance
        h, w = gray_uint8.shape
        max_dim = 500
        if h > max_dim or w > max_dim:
            scale = min(max_dim / h, max_dim / w)
            new_h, new_w = int(h * scale), int(w * scale)
            gray_uint8 = cv2.resize(gray_uint8, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Find pixels at extreme values (potential salt/pepper)
        # Use near-extreme thresholds to be more robust
        salt_mask = gray_uint8 >= 254
        pepper_mask = gray_uint8 <= 1

        # Use morphological opening to remove small isolated regions
        # Opening = erosion followed by dilation - removes small objects
        kernel = np.ones((3, 3), dtype=np.uint8)

        # Open the masks - connected regions will survive, isolated pixels won't
        salt_opened = cv2.morphologyEx(salt_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
        pepper_opened = cv2.morphologyEx(pepper_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)

        # Isolated pixels = original mask - opened mask (what was removed by opening)
        salt_isolated = salt_mask.astype(np.uint8) - salt_opened
        pepper_isolated = pepper_mask.astype(np.uint8) - pepper_opened

        # Count isolated extreme pixels
        total_pixels = gray_uint8.size
        sp_pixels = np.sum(salt_isolated > 0) + np.sum(pepper_isolated > 0)

        return float(sp_pixels / total_pixels)

    def _classify_noise_type(
        self, noise_score: float, salt_pepper_ratio: float
    ) -> NoiseType:
        """Classify the type of noise present in the image.

        Args:
            noise_score: Overall noise score (0-1)
            salt_pepper_ratio: Ratio of salt-and-pepper pixels

        Returns:
            Classified NoiseType
        """
        has_gaussian = noise_score > self.threshold_medium
        has_salt_pepper = salt_pepper_ratio > self.salt_pepper_threshold

        if has_gaussian and has_salt_pepper:
            return NoiseType.MIXED
        elif has_salt_pepper:
            return NoiseType.SALT_PEPPER
        elif has_gaussian:
            # Distinguish between Gaussian and speckle based on score distribution
            # Speckle noise typically has higher variance in local regions
            if noise_score > self.threshold_high:
                return NoiseType.GAUSSIAN
            else:
                return NoiseType.SPECKLE
        else:
            return NoiseType.CLEAN

    def _compute_severity(self, noise_score: float) -> Severity:
        """Compute severity based on noise score.

        Args:
            noise_score: Noise score (0-1)

        Returns:
            Severity level
        """
        if noise_score >= self.threshold_critical:
            return Severity.CRITICAL
        if noise_score >= self.threshold_high:
            return Severity.HIGH
        if noise_score >= self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(
        self, gray: np.ndarray, noise_score: float, salt_pepper_ratio: float
    ) -> float:
        """Compute confidence score for the detection.

        Confidence is higher for:
        - Larger images (more samples)
        - Clear noise patterns (not borderline cases)

        Args:
            gray: Grayscale image
            noise_score: Computed noise score
            salt_pepper_ratio: Computed salt-pepper ratio

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from image size (more pixels = more reliable)
        pixels = gray.size
        size_confidence = min(1.0, pixels / 250000)  # Full confidence at 500x500

        # Detection clarity (not borderline)
        # If score is far from threshold, we're more confident
        threshold_distances = [
            abs(noise_score - self.threshold_medium),
            abs(noise_score - self.threshold_high),
            abs(noise_score - self.threshold_critical),
        ]
        clarity = min(threshold_distances) * 10  # Scale up
        clarity_confidence = min(1.0, 0.5 + clarity)

        # Combined confidence
        confidence = 0.6 * size_confidence + 0.4 * clarity_confidence

        return float(min(0.95, max(0.5, confidence)))


# Convenience functions
def detect_skew(image: np.ndarray) -> SkewDetectionResult:
    """Convenience function for skew detection.

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
    """Convenience function for blur detection.

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
    """Convenience function for contrast detection.

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


def detect_noise(image: np.ndarray) -> NoiseDetectionResult:
    """Convenience function for noise detection.

    Args:
        image: Input image (BGR format)

    Returns:
        NoiseDetectionResult

    Example:
        >>> img = cv2.imread("noisy_scan.jpg")
        >>> result = detect_noise(img)
        >>> if result.is_noisy:
        ...     print(
        ...         f"Noise detected: {result.noise_type.value}, "
        ...         f"score={result.score:.2f} ({result.severity.value})"
        ...     )
    """
    detector = NoiseDetector()
    return detector.detect(image)
