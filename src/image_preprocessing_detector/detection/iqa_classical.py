"""Classical image quality assessment (IQA) detectors.

Implements fast classical computer vision methods for detecting image quality issues:
- SkewDetector: Hough Transform + Projection Profile analysis
- BlurDetector: Laplacian variance with multi-scale analysis
- NoiseDetector: Wavelet-based noise estimation
- ContrastDetector: Histogram analysis for contrast issues
- IlluminationDetector: Lighting uniformity assessment
- JPEGBlockinessDetector: DCT block artifact detection
- BinarizationQualityDetector: Document binarization quality
- BleedThroughDetector: Ink bleed-through detection

Note: This module has low maintainability index (MI ~4.5) due to its size (2800+ LOC).
Future refactoring should split this into separate modules per detector:
    detection/iqa_classical/
    ├── __init__.py        # Public exports
    ├── severity.py        # Severity enum
    ├── skew.py           # SkewDetector
    ├── blur.py           # BlurDetector
    ├── noise.py          # NoiseDetector
    ├── contrast.py       # ContrastDetector
    ├── illumination.py   # IlluminationDetector
    ├── jpeg.py           # JPEGBlockinessDetector
    ├── binarization.py   # BinarizationQualityDetector
    └── bleed.py          # BleedThroughDetector
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Error message constant to avoid duplication
_INVALID_IMAGE_ERROR = "Invalid or empty image provided"


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
            raise ValueError(_INVALID_IMAGE_ERROR)

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
                x1, y1, x2, y2 = line[0]  # type: ignore[index]
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
class BlurMetrics:
    """Detailed blur metrics for analysis.

    Attributes:
        laplacian_variance: Raw Laplacian variance score (higher = sharper)
        blur_score: Normalized 0-1 score (0=very blurry, 1=very sharp)
        local_variance_mean: Mean of local variance across image blocks
        local_variance_std: Std dev of local variance (uniformity indicator)
        edge_density: Proportion of edge pixels (0-1)
    """

    laplacian_variance: float
    blur_score: float
    local_variance_mean: float
    local_variance_std: float
    edge_density: float


@dataclass
class BlurDetectionResult:
    """Result of blur detection analysis.

    Attributes:
        is_blurred: Whether significant blur is detected
        score: Laplacian variance score (higher = sharper)
        blur_score: Normalized 0-1 blur score (0=blurry, 1=sharp)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        metrics: Detailed blur metrics (optional)
    """

    is_blurred: bool
    score: float
    blur_score: float
    confidence: float
    severity: Severity
    metrics: BlurMetrics | None = None


def normalize_blur_score(
    variance: float,
    min_variance: float = 10.0,
    max_variance: float = 500.0,
) -> float:
    """Normalize Laplacian variance to 0-1 blur score.

    Args:
        variance: Raw Laplacian variance value
        min_variance: Minimum expected variance (very blurry)
        max_variance: Maximum expected variance (very sharp)

    Returns:
        Normalized score between 0 (very blurry) and 1 (very sharp)

    Example:
        >>> normalize_blur_score(50.0)  # Low variance = blurry
        0.08
        >>> normalize_blur_score(400.0)  # High variance = sharp
        0.8
    """
    if variance <= min_variance:
        return 0.0
    if variance >= max_variance:
        return 1.0

    # Linear interpolation between min and max
    normalized = (variance - min_variance) / (max_variance - min_variance)
    return float(np.clip(normalized, 0.0, 1.0))


def compute_laplacian_variance(image: np.ndarray) -> float:
    """Compute Laplacian variance for blur detection.

    Args:
        image: Grayscale image (single channel)

    Returns:
        Laplacian variance (higher = sharper)

    Example:
        >>> import cv2
        >>> gray = cv2.imread("image.jpg", cv2.IMREAD_GRAYSCALE)
        >>> variance = compute_laplacian_variance(gray)
    """
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    return float(laplacian.var())


class BlurDetector:
    """Detects image blur using Laplacian variance with enhanced metrics.

    Higher variance indicates sharper images (more high-frequency content).

    Attributes:
        threshold_critical: Critical blur threshold (variance < 50)
        threshold_high: High blur threshold (variance < 100)
        threshold_medium: Medium blur threshold (variance < 200)
        min_variance: Minimum variance for normalization
        max_variance: Maximum variance for normalization
        block_size: Block size for local variance analysis
    """

    def __init__(
        self,
        threshold_critical: float = 50.0,
        threshold_high: float = 100.0,
        threshold_medium: float = 200.0,
        min_variance: float = 10.0,
        max_variance: float = 500.0,
        block_size: int = 64,
    ) -> None:
        """Initialize blur detector.

        Args:
            threshold_critical: Critical blur threshold (< 50 = severe blur)
            threshold_high: High blur threshold (< 100 = noticeable blur)
            threshold_medium: Medium blur threshold (< 200 = slight blur)
            min_variance: Minimum variance for normalization (default: 10.0)
            max_variance: Maximum variance for normalization (default: 500.0)
            block_size: Block size for local analysis (default: 64)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.min_variance = min_variance
        self.max_variance = max_variance
        self.block_size = block_size

        logger.info(
            "Blur detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

    def detect(
        self,
        image: np.ndarray,
        compute_detailed_metrics: bool = False,
    ) -> BlurDetectionResult:
        """Detect blur using Laplacian variance.

        Args:
            image: Input image (BGR or grayscale format)
            compute_detailed_metrics: Whether to compute detailed metrics

        Returns:
            BlurDetectionResult with score and severity

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        logger.debug("Running blur detection", image_shape=image.shape)

        # Convert to grayscale if needed
        gray = self._to_grayscale(image)

        # Compute Laplacian variance
        variance = compute_laplacian_variance(gray)

        # Normalize to 0-1 score
        blur_score = normalize_blur_score(
            variance, self.min_variance, self.max_variance
        )

        # Determine severity
        severity = self._compute_severity(variance)

        # Is blurred if below medium threshold
        is_blurred = variance < self.threshold_medium

        # Confidence based on image properties
        confidence = self._compute_confidence(gray)

        # Compute detailed metrics if requested
        metrics = None
        if compute_detailed_metrics:
            metrics = self._compute_detailed_metrics(gray, variance, blur_score)

        logger.debug(
            "Blur detection complete",
            variance=variance,
            blur_score=blur_score,
            is_blurred=is_blurred,
            severity=severity.value,
        )

        return BlurDetectionResult(
            is_blurred=is_blurred,
            score=variance,
            blur_score=blur_score,
            confidence=confidence,
            severity=severity,
            metrics=metrics,
        )

    def detect_roi(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> BlurDetectionResult:
        """Detect blur in a specific region of interest.

        Args:
            image: Input image (BGR or grayscale format)
            bbox: Region of interest as (x, y, width, height) in COCO format

        Returns:
            BlurDetectionResult for the specified region

        Raises:
            ValueError: If image or bbox is invalid
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid bbox dimensions: {bbox}")

        # Extract ROI
        if len(image.shape) == 3:
            roi = image[y : y + h, x : x + w, :]
        else:
            roi = image[y : y + h, x : x + w]

        if roi.size == 0:
            raise ValueError(f"ROI is empty for bbox: {bbox}")

        logger.debug("Running ROI blur detection", bbox=bbox, roi_shape=roi.shape)

        return self.detect(roi)

    def detect_blocks(
        self,
        image: np.ndarray,
        block_size: int | None = None,
    ) -> list[tuple[tuple[int, int, int, int], BlurDetectionResult]]:
        """Detect blur in image blocks for spatial analysis.

        Args:
            image: Input image (BGR or grayscale format)
            block_size: Size of blocks to analyze (default: self.block_size)

        Returns:
            List of (bbox, BlurDetectionResult) tuples for each block
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        block_size = block_size or self.block_size
        gray = self._to_grayscale(image)
        h, w = gray.shape[:2]

        results = []
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                bbox = (x, y, block_size, block_size)
                block = gray[y : y + block_size, x : x + block_size]

                # Compute variance for this block
                variance = compute_laplacian_variance(block)
                blur_score = normalize_blur_score(
                    variance, self.min_variance, self.max_variance
                )
                severity = self._compute_severity(variance)
                is_blurred = variance < self.threshold_medium

                result = BlurDetectionResult(
                    is_blurred=is_blurred,
                    score=variance,
                    blur_score=blur_score,
                    confidence=0.85,  # Slightly lower for block-level
                    severity=severity,
                )
                results.append((bbox, result))

        return results

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if needed.

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            Grayscale image
        """
        if len(image.shape) == 2:
            return image
        if len(image.shape) == 3:
            if image.shape[2] == 1:
                return image[:, :, 0]
            if image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        raise ValueError(f"Unsupported image shape: {image.shape}")

    def _compute_severity(self, variance: float) -> Severity:
        """Compute severity based on Laplacian variance.

        Args:
            variance: Laplacian variance value

        Returns:
            Severity level
        """
        if variance < self.threshold_critical:
            return Severity.CRITICAL
        if variance < self.threshold_high:
            return Severity.HIGH
        if variance < self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(
        self,
        gray: np.ndarray,
    ) -> float:
        """Compute confidence score for blur detection.

        Higher confidence when image properties are suitable for blur analysis.

        Args:
            gray: Grayscale image

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence is high for Laplacian variance
        base_confidence = 0.9

        # Reduce confidence for very small images
        h, w = gray.shape[:2]
        if h < 100 or w < 100:
            base_confidence *= 0.8

        # Reduce confidence for uniform images (low variance in pixel values)
        pixel_std = gray.std()
        if pixel_std < 10:  # Very uniform image
            base_confidence *= 0.7

        return float(np.clip(base_confidence, 0.5, 1.0))

    def _compute_detailed_metrics(
        self,
        gray: np.ndarray,
        variance: float,
        blur_score: float,
    ) -> BlurMetrics:
        """Compute detailed blur metrics.

        Args:
            gray: Grayscale image
            variance: Global Laplacian variance
            blur_score: Normalized blur score

        Returns:
            BlurMetrics with detailed measurements
        """
        h, w = gray.shape[:2]
        block_size = min(self.block_size, h // 2, w // 2)
        if block_size < 16:
            block_size = min(h, w, 16)

        # Compute local variances
        local_variances = []
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                block = gray[y : y + block_size, x : x + block_size]
                local_var = compute_laplacian_variance(block)
                local_variances.append(local_var)

        if local_variances:
            local_variance_mean = float(np.mean(local_variances))
            local_variance_std = float(np.std(local_variances))
        else:
            local_variance_mean = variance
            local_variance_std = 0.0

        # Compute edge density using Canny
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges) / edges.size)

        return BlurMetrics(
            laplacian_variance=variance,
            blur_score=blur_score,
            local_variance_mean=local_variance_mean,
            local_variance_std=local_variance_std,
            edge_density=edge_density,
        )


@dataclass
class NoiseMetrics:
    """Detailed noise metrics for analysis.

    Attributes:
        noise_sigma: Estimated noise standard deviation
        noise_score: Normalized 0-1 score (0=very noisy, 1=clean)
        wavelet_detail_energy: Energy in wavelet detail coefficients
        snr_estimate: Estimated signal-to-noise ratio (dB)
        noise_type_hint: Suggested noise type (gaussian, salt_pepper, uniform)
    """

    noise_sigma: float
    noise_score: float
    wavelet_detail_energy: float
    snr_estimate: float
    noise_type_hint: str


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
        noise_sigma: Estimated noise standard deviation
        noise_score: Normalized 0-1 score (0=noisy, 1=clean)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        metrics: Detailed noise metrics (optional)
    """

    is_noisy: bool
    noise_sigma: float
    noise_score: float
    confidence: float
    severity: Severity
    metrics: NoiseMetrics | None = None


def estimate_noise_mad(detail_coeffs: np.ndarray) -> float:
    """Estimate noise sigma using Median Absolute Deviation (MAD).

    The MAD estimator is robust to outliers and commonly used for
    noise estimation in wavelet domain.

    Args:
        detail_coeffs: Wavelet detail coefficients (HH subband preferred)

    Returns:
        Estimated noise standard deviation

    Note:
        Uses the formula: sigma = MAD / 0.6745
        where 0.6745 is the consistency constant for Gaussian noise
    """
    # Flatten coefficients
    coeffs_flat = detail_coeffs.flatten()

    # Compute MAD (Median Absolute Deviation)
    median = np.median(np.abs(coeffs_flat))

    # Convert MAD to sigma estimate
    # 0.6745 is the consistency constant for Gaussian distribution
    sigma = median / 0.6745

    return float(sigma)


def normalize_noise_score(
    sigma: float,
    min_sigma: float = 0.0,
    max_sigma: float = 30.0,
) -> float:
    """Normalize noise sigma to 0-1 score (inverted: 0=noisy, 1=clean).

    Args:
        sigma: Estimated noise standard deviation
        min_sigma: Minimum sigma (clean image)
        max_sigma: Maximum sigma (very noisy)

    Returns:
        Normalized score between 0 (very noisy) and 1 (clean)
    """
    if sigma <= min_sigma:
        return 1.0
    if sigma >= max_sigma:
        return 0.0

    # Inverted linear interpolation (higher sigma = lower score)
    normalized = 1.0 - (sigma - min_sigma) / (max_sigma - min_sigma)
    return float(np.clip(normalized, 0.0, 1.0))


class NoiseDetector:
    """Detects image noise using wavelet-based estimation.

    Uses discrete wavelet transform (DWT) and Median Absolute Deviation (MAD)
    to estimate noise levels in images. This method is robust and commonly
    used in image denoising algorithms.

    Attributes:
        threshold_critical: Critical noise threshold (sigma > 20)
        threshold_high: High noise threshold (sigma > 12)
        threshold_medium: Medium noise threshold (sigma > 5)
        wavelet: Wavelet family to use (default: 'db1' Daubechies)
        level: Decomposition level (default: 1)
    """

    def __init__(
        self,
        threshold_critical: float = 20.0,
        threshold_high: float = 12.0,
        threshold_medium: float = 5.0,
        wavelet: str = "db1",
        level: int = 1,
        min_sigma: float = 0.0,
        max_sigma: float = 30.0,
    ) -> None:
        """Initialize noise detector.

        Args:
            threshold_critical: Critical noise threshold (sigma > 20 = severe)
            threshold_high: High noise threshold (sigma > 12 = noticeable)
            threshold_medium: Medium noise threshold (sigma > 5 = slight)
            wavelet: Wavelet family ('db1', 'haar', 'sym2', etc.)
            level: Wavelet decomposition level (1-3 recommended)
            min_sigma: Minimum sigma for score normalization
            max_sigma: Maximum sigma for score normalization
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.wavelet = wavelet
        self.level = level
        self.min_sigma = min_sigma
        self.max_sigma = max_sigma

        logger.info(
            "Noise detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            wavelet=wavelet,
        )

    def detect(
        self,
        image: np.ndarray,
        compute_detailed_metrics: bool = False,
    ) -> NoiseDetectionResult:
        """Detect noise using wavelet-based MAD estimation.

        Args:
            image: Input image (BGR or grayscale format)
            compute_detailed_metrics: Whether to compute detailed metrics

        Returns:
            NoiseDetectionResult with sigma and severity

        Raises:
            ValueError: If image is invalid or empty
        """
        import pywt

        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        logger.debug("Running noise detection", image_shape=image.shape)

        # Convert to grayscale if needed
        gray = self._to_grayscale(image)

        # Perform wavelet decomposition
        coeffs = pywt.wavedec2(gray, self.wavelet, level=self.level)

        # Get detail coefficients (HH subband from first level)
        # coeffs[0] is approximation, coeffs[1] is (LH, HL, HH) tuple
        detail_hh = coeffs[1][2]  # HH (diagonal detail)

        # Estimate noise using MAD
        noise_sigma = estimate_noise_mad(detail_hh)

        # Normalize to 0-1 score
        noise_score = normalize_noise_score(noise_sigma, self.min_sigma, self.max_sigma)

        # Determine severity
        severity = self._compute_severity(noise_sigma)

        # Is noisy if above medium threshold
        is_noisy = noise_sigma > self.threshold_medium

        # Compute confidence
        confidence = self._compute_confidence(gray)

        # Compute detailed metrics if requested
        metrics = None
        if compute_detailed_metrics:
            metrics = self._compute_detailed_metrics(
                gray, coeffs, noise_sigma, noise_score
            )

        logger.debug(
            "Noise detection complete",
            noise_sigma=noise_sigma,
            noise_score=noise_score,
            is_noisy=is_noisy,
            severity=severity.value,
        )

        return NoiseDetectionResult(
            is_noisy=is_noisy,
            noise_sigma=noise_sigma,
            noise_score=noise_score,
            confidence=confidence,
            severity=severity,
            metrics=metrics,
        )

    def detect_roi(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int],
    ) -> NoiseDetectionResult:
        """Detect noise in a specific region of interest.

        Args:
            image: Input image (BGR or grayscale format)
            bbox: Region of interest as (x, y, width, height) in COCO format

        Returns:
            NoiseDetectionResult for the specified region

        Raises:
            ValueError: If image or bbox is invalid
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid bbox dimensions: {bbox}")

        # Extract ROI
        if len(image.shape) == 3:
            roi = image[y : y + h, x : x + w, :]
        else:
            roi = image[y : y + h, x : x + w]

        if roi.size == 0:
            raise ValueError(f"ROI is empty for bbox: {bbox}")

        logger.debug("Running ROI noise detection", bbox=bbox, roi_shape=roi.shape)

        return self.detect(roi)

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if needed."""
        if len(image.shape) == 2:
            return image.astype(np.float64)
        if len(image.shape) == 3:
            if image.shape[2] == 1:
                return image[:, :, 0].astype(np.float64)
            if image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                return gray.astype(np.float64)
            if image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
                return gray.astype(np.float64)
        raise ValueError(f"Unsupported image shape: {image.shape}")

    def _compute_severity(self, sigma: float) -> Severity:
        """Compute severity based on noise sigma.

        Args:
            sigma: Estimated noise standard deviation

        Returns:
            Severity level
        """
        if sigma >= self.threshold_critical:
            return Severity.CRITICAL
        if sigma >= self.threshold_high:
            return Severity.HIGH
        if sigma >= self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(
        self,
        gray: np.ndarray,
    ) -> float:
        """Compute confidence score for noise detection.

        Args:
            gray: Grayscale image

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence
        base_confidence = 0.85

        # Reduce confidence for very small images (wavelet needs space)
        h, w = gray.shape[:2]
        if h < 64 or w < 64:
            base_confidence *= 0.7

        # Reduce confidence for very uniform images
        pixel_std = np.std(gray)
        if pixel_std < 5:  # Very uniform
            base_confidence *= 0.8

        return float(np.clip(base_confidence, 0.5, 1.0))

    def _compute_detailed_metrics(
        self,
        gray: np.ndarray,
        coeffs: list[Any],
        noise_sigma: float,
        noise_score: float,
    ) -> NoiseMetrics:
        """Compute detailed noise metrics.

        Args:
            gray: Grayscale image (float64)
            coeffs: Wavelet coefficients from decomposition
            noise_sigma: Estimated noise sigma
            noise_score: Normalized noise score

        Returns:
            NoiseMetrics with detailed measurements
        """
        # Compute detail energy
        detail_hh = coeffs[1][2]
        detail_energy = float(np.sum(detail_hh**2) / detail_hh.size)

        # Estimate SNR
        signal_power = float(np.var(gray))
        noise_power = noise_sigma**2 if noise_sigma > 0 else 1e-10
        snr_db = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 100.0

        # Guess noise type based on distribution
        noise_type = self._estimate_noise_type(gray, noise_sigma)

        return NoiseMetrics(
            noise_sigma=noise_sigma,
            noise_score=noise_score,
            wavelet_detail_energy=detail_energy,
            snr_estimate=float(snr_db),
            noise_type_hint=noise_type,
        )

    def _estimate_noise_type(
        self,
        gray: np.ndarray,
        sigma: float,
    ) -> str:
        """Estimate the type of noise present.

        Args:
            gray: Grayscale image
            sigma: Estimated noise sigma

        Returns:
            Noise type hint: 'gaussian', 'salt_pepper', 'uniform', or 'mixed'
        """
        if sigma < 1.0:
            return "clean"

        # Check for salt-and-pepper noise (extreme values)
        h, w = gray.shape[:2]
        total_pixels = h * w

        # Count extreme pixels
        black_pixels = np.sum(gray < 5)
        white_pixels = np.sum(gray > 250)
        extreme_ratio = (black_pixels + white_pixels) / total_pixels

        if extreme_ratio > 0.01:  # More than 1% extreme pixels
            return "salt_pepper"

        # Check distribution shape for Gaussian vs uniform
        # Gaussian noise should have most values near mean
        normalized = gray / 255.0
        pixel_std = np.std(normalized)

        # Kurtosis check (Gaussian ~ 3, uniform ~ 1.8)
        mean_val = np.mean(normalized)
        fourth_moment = np.mean((normalized - mean_val) ** 4)
        kurtosis = fourth_moment / (pixel_std**4) if pixel_std > 0 else 3.0

        if kurtosis > 2.5:
            return "gaussian"
        if kurtosis < 2.0:
            return "uniform"
        return "mixed"


def detect_noise(image: np.ndarray) -> NoiseDetectionResult:
    """Convenience function for noise detection.

    Args:
        image: Input image (BGR format)

    Returns:
        NoiseDetectionResult

    Example:
        >>> img = cv2.imread("scan.jpg")
        >>> result = detect_noise(img)
        >>> if result.is_noisy:
        ...     print(f"Noise detected: sigma={result.noise_sigma:.2f}")
    """
    detector = NoiseDetector()
    return detector.detect(image)


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
            raise ValueError(_INVALID_IMAGE_ERROR)

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


class IlluminationType(str, Enum):
    """Types of illumination issues."""

    UNIFORM = "uniform"
    SHADOWS = "shadows"
    HOTSPOTS = "hotspots"
    VIGNETTING = "vignetting"
    UNEVEN = "uneven"


@dataclass
class IlluminationDetectionResult:
    """Result of illumination detection analysis.

    Attributes:
        has_issues: Whether illumination issues are detected
        score: Illumination quality score (0.0-1.0, higher = better uniformity)
        issue_type: Classified type of illumination issue
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        uniformity: Regional intensity uniformity (0.0-1.0)
        vignetting_ratio: Edge-to-center intensity ratio (1.0 = no vignetting)
        shadow_ratio: Ratio of shadow pixels (0.0-1.0)
        hotspot_ratio: Ratio of hotspot pixels (0.0-1.0)
    """

    has_issues: bool
    score: float
    issue_type: IlluminationType
    confidence: float
    severity: Severity
    uniformity: float
    vignetting_ratio: float
    shadow_ratio: float
    hotspot_ratio: float


class IlluminationDetector:
    """Detects illumination issues in document images.

    Analyzes regional brightness variations to detect:
    - Uneven illumination (different brightness across regions)
    - Shadows (unexpectedly dark regions)
    - Hotspots (overexposed regions)
    - Vignetting (darkening towards edges)
    """

    def __init__(
        self,
        threshold_critical: float = 0.50,
        threshold_high: float = 0.65,
        threshold_medium: float = 0.80,
        grid_size: int = 5,
        shadow_percentile: float = 10.0,
        hotspot_percentile: float = 95.0,
    ) -> None:
        """Initialize illumination detector.

        Args:
            threshold_critical: Critical uniformity threshold (< 0.50 = severe issues)
            threshold_high: High severity threshold (< 0.65 = noticeable issues)
            threshold_medium: Medium severity threshold (< 0.80 = slight issues)
            grid_size: Grid divisions for regional analysis (default: 5x5)
            shadow_percentile: Percentile for shadow detection (default: 10%)
            hotspot_percentile: Percentile for hotspot detection (default: 95%)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.grid_size = grid_size
        self.shadow_percentile = shadow_percentile
        self.hotspot_percentile = hotspot_percentile

        logger.info(
            "Illumination detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            grid_size=grid_size,
        )

    def detect(self, image: np.ndarray) -> IlluminationDetectionResult:
        """Detect illumination issues in an image.

        Args:
            image: Input image (BGR format)

        Returns:
            IlluminationDetectionResult with uniformity and issue details

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        logger.debug("Running illumination detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # For large images, subsample for performance
        h, w = gray.shape
        max_dim = 500
        if h > max_dim or w > max_dim:
            scale = min(max_dim / h, max_dim / w)
            new_h, new_w = int(h * scale), int(w * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Analyze regional uniformity
        uniformity = self._compute_uniformity(gray)

        # Detect vignetting
        vignetting_ratio = self._detect_vignetting(gray)

        # Detect shadows and hotspots
        shadow_ratio, hotspot_ratio = self._detect_shadows_hotspots(gray)

        # Compute overall score (higher = better)
        score = self._compute_score(
            uniformity, vignetting_ratio, shadow_ratio, hotspot_ratio
        )

        # Classify issue type
        issue_type = self._classify_issue(
            uniformity, vignetting_ratio, shadow_ratio, hotspot_ratio
        )

        # Determine severity
        severity = self._compute_severity(score)

        # Determine if there are issues
        has_issues = score < self.threshold_medium

        # Compute confidence
        confidence = self._compute_confidence(gray, score)

        logger.debug(
            "Illumination detection complete",
            score=score,
            uniformity=uniformity,
            vignetting_ratio=vignetting_ratio,
            shadow_ratio=shadow_ratio,
            hotspot_ratio=hotspot_ratio,
            issue_type=issue_type.value,
            severity=severity.value,
            has_issues=has_issues,
        )

        return IlluminationDetectionResult(
            has_issues=has_issues,
            score=score,
            issue_type=issue_type,
            confidence=confidence,
            severity=severity,
            uniformity=uniformity,
            vignetting_ratio=vignetting_ratio,
            shadow_ratio=shadow_ratio,
            hotspot_ratio=hotspot_ratio,
        )

    def _compute_uniformity(self, gray: np.ndarray) -> float:
        """Compute regional intensity uniformity.

        Divides image into grid and measures intensity variation.

        Args:
            gray: Grayscale image

        Returns:
            Uniformity score (0-1, higher = more uniform)
        """
        h, w = gray.shape
        cell_h = h // self.grid_size
        cell_w = w // self.grid_size

        # Skip if image too small for grid
        if cell_h < 10 or cell_w < 10:
            return 1.0

        # Compute mean intensity for each cell
        means = []
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w
                cell = gray[y1:y2, x1:x2]
                means.append(np.mean(cell))

        means_array = np.array(means)

        # Compute coefficient of variation (std/mean)
        # Lower CV = more uniform
        if np.mean(means_array) > 0:
            cv = np.std(means_array) / np.mean(means_array)
            # Convert to uniformity score (0-1, higher = better)
            # CV of 0.3 or more is considered severe non-uniformity
            uniformity = max(0.0, 1.0 - cv / 0.3)
        else:
            uniformity = 0.0

        return float(uniformity)

    def _detect_vignetting(self, gray: np.ndarray) -> float:
        """Detect vignetting by comparing edge and center intensities.

        Vignetting causes edges to be darker than center.

        Args:
            gray: Grayscale image

        Returns:
            Vignetting ratio (edge_mean / center_mean, <1.0 = vignetting)
        """
        h, w = gray.shape

        # Define center region (middle 40%)
        margin_y = int(h * 0.3)
        margin_x = int(w * 0.3)
        center = gray[margin_y : h - margin_y, margin_x : w - margin_x]

        # Define edge regions (outer 15% on each side)
        edge_width = int(min(h, w) * 0.15)
        if edge_width < 5:
            return 1.0

        # Sample edges
        top = gray[:edge_width, :]
        bottom = gray[-edge_width:, :]
        left = gray[:, :edge_width]
        right = gray[:, -edge_width:]

        # Compute means
        center_mean = np.mean(center)
        edge_mean = np.mean(
            [np.mean(top), np.mean(bottom), np.mean(left), np.mean(right)]
        )

        # Avoid division by zero
        if center_mean < 1:
            return 1.0

        ratio = edge_mean / center_mean
        return float(ratio)

    def _detect_shadows_hotspots(self, gray: np.ndarray) -> tuple[float, float]:
        """Detect shadow and hotspot regions.

        Shadows are unexpectedly dark regions (intensity < 50).
        Hotspots are unexpectedly bright regions (intensity > 240).

        Uses absolute thresholds suitable for document images where
        shadows and hotspots represent scanning/lighting artifacts.

        Args:
            gray: Grayscale image

        Returns:
            Tuple of (shadow_ratio, hotspot_ratio)
        """
        # Use absolute thresholds for document images
        # Shadows: very dark regions (< 50 intensity)
        # Hotspots: very bright/saturated regions (> 240 intensity)
        shadow_thresh = 50
        hotspot_thresh = 240

        # Adjust based on image characteristics
        overall_mean = np.mean(gray)

        # For dark documents (e.g., inverted), adjust shadow threshold
        if overall_mean < 80:
            shadow_thresh = 30  # Lower threshold for dark images
        # For very bright documents, adjust hotspot threshold
        if overall_mean > 220:
            hotspot_thresh = 250  # Higher threshold for bright images

        # Count shadow and hotspot pixels
        shadow_pixels = np.sum(gray < shadow_thresh)
        hotspot_pixels = np.sum(gray > hotspot_thresh)
        total_pixels = gray.size

        shadow_ratio = shadow_pixels / total_pixels
        hotspot_ratio = hotspot_pixels / total_pixels

        return float(shadow_ratio), float(hotspot_ratio)

    def _compute_score(
        self,
        uniformity: float,
        vignetting_ratio: float,
        shadow_ratio: float,
        hotspot_ratio: float,
    ) -> float:
        """Compute overall illumination quality score.

        Args:
            uniformity: Regional uniformity (0-1)
            vignetting_ratio: Edge/center ratio
            shadow_ratio: Shadow pixel ratio
            hotspot_ratio: Hotspot pixel ratio

        Returns:
            Quality score (0-1, higher = better)
        """
        # Vignetting penalty (ratio < 0.8 means significant vignetting)
        vignetting_score = min(1.0, vignetting_ratio / 0.8)

        # Shadow/hotspot penalties (more than 5% is concerning)
        shadow_score = max(0.0, 1.0 - shadow_ratio / 0.05)
        hotspot_score = max(0.0, 1.0 - hotspot_ratio / 0.05)

        # Weighted combination
        score = (
            0.40 * uniformity
            + 0.25 * vignetting_score
            + 0.20 * shadow_score
            + 0.15 * hotspot_score
        )

        return float(max(0.0, min(1.0, score)))

    def _classify_issue(
        self,
        uniformity: float,
        vignetting_ratio: float,
        shadow_ratio: float,
        hotspot_ratio: float,
    ) -> IlluminationType:
        """Classify the primary illumination issue.

        Args:
            uniformity: Regional uniformity (0-1)
            vignetting_ratio: Edge/center ratio
            shadow_ratio: Shadow pixel ratio
            hotspot_ratio: Hotspot pixel ratio

        Returns:
            Primary IlluminationType
        """
        # Check for specific issues in order of severity
        # Prioritize shadows and hotspots (specific artifacts) over vignetting
        if shadow_ratio > 0.10:
            return IlluminationType.SHADOWS
        if hotspot_ratio > 0.10:
            return IlluminationType.HOTSPOTS
        if vignetting_ratio < 0.75:
            return IlluminationType.VIGNETTING
        if uniformity < 0.70:
            return IlluminationType.UNEVEN
        return IlluminationType.UNIFORM

    def _compute_severity(self, score: float) -> Severity:
        """Compute severity based on illumination score.

        Args:
            score: Illumination quality score (0-1)

        Returns:
            Severity level
        """
        if score < self.threshold_critical:
            return Severity.CRITICAL
        if score < self.threshold_high:
            return Severity.HIGH
        if score < self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(self, gray: np.ndarray, score: float) -> float:
        """Compute confidence score for the detection.

        Args:
            gray: Grayscale image
            score: Computed quality score

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from image size
        pixels = gray.size
        size_confidence = min(1.0, pixels / 250000)

        # Detection clarity
        threshold_distances = [
            abs(score - self.threshold_medium),
            abs(score - self.threshold_high),
            abs(score - self.threshold_critical),
        ]
        clarity = min(threshold_distances) * 5
        clarity_confidence = min(1.0, 0.5 + clarity)

        confidence = 0.6 * size_confidence + 0.4 * clarity_confidence
        return float(min(0.95, max(0.5, confidence)))


@dataclass
class JPEGBlockinessResult:
    """Result of JPEG blockiness detection analysis.

    Attributes:
        has_artifacts: Whether significant JPEG blockiness is detected
        blockiness_score: Blockiness metric (0.0-1.0, higher = more blocky)
        compression_score: Quality score (0.0-1.0, higher = better quality)
        estimated_quality: Estimated JPEG quality factor (1-100)
        confidence: Confidence score (0.0-1.0)
        severity: Issue severity level
        horizontal_blockiness: Blockiness at horizontal block boundaries
        vertical_blockiness: Blockiness at vertical block boundaries
    """

    has_artifacts: bool
    blockiness_score: float
    compression_score: float
    estimated_quality: int
    confidence: float
    severity: Severity
    horizontal_blockiness: float
    vertical_blockiness: float


class JPEGBlockinessDetector:
    """Detects JPEG compression artifacts (blockiness) in images.

    JPEG compression divides images into 8x8 pixel blocks and applies
    DCT (Discrete Cosine Transform) to each block. At low quality settings,
    this creates visible discontinuities at block boundaries.

    This detector measures the difference between pixel gradients at
    8x8 block boundaries versus within blocks. Higher ratio indicates
    more visible compression artifacts.
    """

    BLOCK_SIZE = 8  # JPEG uses 8x8 DCT blocks

    def __init__(
        self,
        threshold_critical: float = 0.25,
        threshold_high: float = 0.15,
        threshold_medium: float = 0.08,
    ) -> None:
        """Initialize JPEG blockiness detector.

        Args:
            threshold_critical: Critical blockiness threshold (> 0.25 = severe artifacts)
            threshold_high: High severity threshold (> 0.15 = noticeable artifacts)
            threshold_medium: Medium severity threshold (> 0.08 = slight artifacts)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium

        logger.info(
            "JPEG blockiness detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

    def detect(self, image: np.ndarray) -> JPEGBlockinessResult:
        """Detect JPEG blockiness in an image.

        Args:
            image: Input image (BGR format)

        Returns:
            JPEGBlockinessResult with blockiness metrics

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        logger.debug("Running JPEG blockiness detection", image_shape=image.shape)

        # Convert to grayscale first (single channel is faster to resize)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # For large images, subsample aggressively for performance
        h, w = gray.shape
        max_dim = 256
        if h > max_dim or w > max_dim:
            scale = min(max_dim / h, max_dim / w)
            new_h, new_w = int(h * scale), int(w * scale)
            # Round to nearest multiple of 8 for proper block alignment
            new_h = (new_h // 8) * 8
            new_w = (new_w // 8) * 8
            if new_h < 24 or new_w < 24:
                new_h, new_w = max(24, new_h), max(24, new_w)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)

        gray = gray.astype(np.float64)

        # Compute blockiness at horizontal and vertical boundaries
        h_blockiness = self._compute_horizontal_blockiness(gray)
        v_blockiness = self._compute_vertical_blockiness(gray)

        # Combined blockiness score
        blockiness_score = (h_blockiness + v_blockiness) / 2.0

        # Normalize to 0-1 range (typical blockiness values are 0-0.5)
        blockiness_score = min(1.0, blockiness_score / 0.5)

        # Compression score (inverse of blockiness, higher = better)
        compression_score = max(0.0, 1.0 - blockiness_score)

        # Estimate JPEG quality from blockiness
        estimated_quality = self._estimate_quality(blockiness_score)

        # Determine severity
        severity = self._compute_severity(blockiness_score)

        # Determine if artifacts are significant
        has_artifacts = blockiness_score > self.threshold_medium

        # Compute confidence
        confidence = self._compute_confidence(gray, blockiness_score)

        logger.debug(
            "JPEG blockiness detection complete",
            blockiness_score=blockiness_score,
            compression_score=compression_score,
            estimated_quality=estimated_quality,
            h_blockiness=h_blockiness,
            v_blockiness=v_blockiness,
            severity=severity.value,
            has_artifacts=has_artifacts,
        )

        return JPEGBlockinessResult(
            has_artifacts=has_artifacts,
            blockiness_score=blockiness_score,
            compression_score=compression_score,
            estimated_quality=estimated_quality,
            confidence=confidence,
            severity=severity,
            horizontal_blockiness=h_blockiness,
            vertical_blockiness=v_blockiness,
        )

    def _compute_horizontal_blockiness(self, gray: np.ndarray) -> float:
        """Compute blockiness at horizontal 8-pixel boundaries.

        Measures the average absolute difference between pixels
        at block boundaries versus within blocks.

        Args:
            gray: Grayscale image as float64

        Returns:
            Horizontal blockiness metric
        """
        _h, w = gray.shape

        # Compute horizontal differences (column-wise)
        h_diff = np.abs(np.diff(gray, axis=1))

        # Separate boundary and inner differences
        # Boundaries are at columns 7, 15, 23, ... (every 8th column)
        boundary_cols = list(range(self.BLOCK_SIZE - 1, w - 1, self.BLOCK_SIZE))
        all_cols = list(range(w - 1))
        inner_cols = [c for c in all_cols if c not in boundary_cols]

        if not boundary_cols or not inner_cols:
            return 0.0

        boundary_diff = np.mean(h_diff[:, boundary_cols])
        inner_diff = np.mean(h_diff[:, inner_cols])

        # Blockiness ratio: how much larger are boundary differences?
        if inner_diff < 1e-6:
            return 0.0

        blockiness_value = (boundary_diff - inner_diff) / (inner_diff + 1e-6)
        return max(0.0, float(blockiness_value))

    def _compute_vertical_blockiness(self, gray: np.ndarray) -> float:
        """Compute blockiness at vertical 8-pixel boundaries.

        Args:
            gray: Grayscale image as float64

        Returns:
            Vertical blockiness metric
        """
        h, _w = gray.shape

        # Compute vertical differences (row-wise)
        v_diff = np.abs(np.diff(gray, axis=0))

        # Separate boundary and inner differences
        # Boundaries are at rows 7, 15, 23, ... (every 8th row)
        boundary_rows = list(range(self.BLOCK_SIZE - 1, h - 1, self.BLOCK_SIZE))
        all_rows = list(range(h - 1))
        inner_rows = [r for r in all_rows if r not in boundary_rows]

        if not boundary_rows or not inner_rows:
            return 0.0

        boundary_diff = np.mean(v_diff[boundary_rows, :])
        inner_diff = np.mean(v_diff[inner_rows, :])

        # Blockiness ratio
        if inner_diff < 1e-6:
            return 0.0

        blockiness_value = (boundary_diff - inner_diff) / (inner_diff + 1e-6)
        return max(0.0, float(blockiness_value))

    def _estimate_quality(self, blockiness_score: float) -> int:
        """Estimate JPEG quality factor from blockiness score.

        Uses empirical mapping based on typical JPEG compression behavior.

        Args:
            blockiness_score: Normalized blockiness (0-1)

        Returns:
            Estimated quality factor (1-100)
        """
        # Empirical mapping: higher blockiness = lower quality
        # blockiness 0.0 -> quality ~95
        # blockiness 0.5 -> quality ~50
        # blockiness 1.0 -> quality ~5
        if blockiness_score <= 0.0:
            return 95
        if blockiness_score >= 1.0:
            return 5

        # Exponential decay mapping
        quality = int(95 * (1.0 - blockiness_score) ** 1.5 + 5)
        return max(1, min(100, quality))

    def _compute_severity(self, blockiness_score: float) -> Severity:
        """Compute severity based on blockiness score.

        Args:
            blockiness_score: Normalized blockiness (0-1)

        Returns:
            Severity level
        """
        if blockiness_score >= self.threshold_critical:
            return Severity.CRITICAL
        if blockiness_score >= self.threshold_high:
            return Severity.HIGH
        if blockiness_score >= self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(self, gray: np.ndarray, blockiness_score: float) -> float:
        """Compute confidence score for the detection.

        Args:
            gray: Grayscale image
            blockiness_score: Computed blockiness score

        Returns:
            Confidence score (0-1)
        """
        # Size confidence
        h, w = gray.shape
        size_confidence = min(1.0, (h * w) / 250000)

        # Detection clarity (not borderline)
        threshold_distances = [
            abs(blockiness_score - self.threshold_medium),
            abs(blockiness_score - self.threshold_high),
            abs(blockiness_score - self.threshold_critical),
        ]
        clarity = min(threshold_distances) * 10
        clarity_confidence = min(1.0, 0.5 + clarity)

        confidence = 0.6 * size_confidence + 0.4 * clarity_confidence
        return float(min(0.95, max(0.5, confidence)))


@dataclass
class ProblemRegion:
    """A region with binarization issues.

    Attributes:
        x: X coordinate of region (top-left)
        y: Y coordinate of region (top-left)
        width: Width of region
        height: Height of region
        issue: Type of issue (low_contrast, noisy, blurry)
        severity: Severity of the issue
    """

    x: int
    y: int
    width: int
    height: int
    issue: str
    severity: float


@dataclass
class BinarizationQualityResult:
    """Result of binarization quality assessment.

    Attributes:
        binarization_score: Overall quality score (0.0-1.0, higher = better)
        bimodality_score: Histogram bimodality (0.0-1.0, higher = clearer separation)
        contrast_score: Local contrast score (0.0-1.0)
        noise_score: Noise impact score (0.0-1.0, higher = less noise)
        problem_regions: List of regions with binarization issues
        confidence: Confidence score (0.0-1.0)
        severity: Overall severity level
        estimated_threshold: Estimated optimal Otsu threshold (0-255)
    """

    binarization_score: float
    bimodality_score: float
    contrast_score: float
    noise_score: float
    problem_regions: list[ProblemRegion]
    confidence: float
    severity: Severity
    estimated_threshold: int


class BinarizationQualityDetector:
    """Assesses how well a document image would binarize.

    Evaluates factors that affect binarization quality:
    - Histogram bimodality (clear text/background separation)
    - Local contrast in different regions
    - Noise levels that interfere with thresholding
    - Edge clarity for text boundaries

    Identifies problem regions that may need special handling.
    """

    def __init__(
        self,
        threshold_critical: float = 0.40,
        threshold_high: float = 0.55,
        threshold_medium: float = 0.70,
        grid_size: int = 4,
        min_contrast: float = 0.15,
    ) -> None:
        """Initialize binarization quality detector.

        Args:
            threshold_critical: Critical quality threshold (< 0.40 = severe issues)
            threshold_high: High severity threshold (< 0.55 = noticeable issues)
            threshold_medium: Medium severity threshold (< 0.70 = slight issues)
            grid_size: Grid divisions for regional analysis (default: 4x4)
            min_contrast: Minimum contrast to consider region viable (default: 0.15)
        """
        self.threshold_critical = threshold_critical
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium
        self.grid_size = grid_size
        self.min_contrast = min_contrast

        logger.info(
            "Binarization quality detector initialized",
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            grid_size=grid_size,
        )

    def detect(self, image: np.ndarray) -> BinarizationQualityResult:
        """Assess binarization quality of an image.

        Args:
            image: Input image (BGR format)

        Returns:
            BinarizationQualityResult with quality metrics

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        logger.debug("Running binarization quality detection", image_shape=image.shape)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # For large images, subsample for performance
        h, w = gray.shape
        original_h, original_w = h, w
        max_dim = 500
        scale = 1.0
        if h > max_dim or w > max_dim:
            scale = min(max_dim / h, max_dim / w)
            new_h, new_w = int(h * scale), int(w * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = gray.shape

        # Compute bimodality score (histogram analysis)
        bimodality_score, estimated_threshold = self._compute_bimodality(gray)

        # Compute local contrast score
        contrast_score, problem_regions = self._analyze_local_contrast(
            gray, scale, original_h, original_w
        )

        # Compute noise impact score
        noise_score = self._compute_noise_impact(gray)

        # Combined binarization score
        binarization_score = (
            0.40 * bimodality_score + 0.35 * contrast_score + 0.25 * noise_score
        )

        # Determine severity
        severity = self._compute_severity(binarization_score)

        # Compute confidence
        confidence = self._compute_confidence(gray, binarization_score)

        logger.debug(
            "Binarization quality detection complete",
            binarization_score=binarization_score,
            bimodality_score=bimodality_score,
            contrast_score=contrast_score,
            noise_score=noise_score,
            num_problem_regions=len(problem_regions),
            severity=severity.value,
        )

        return BinarizationQualityResult(
            binarization_score=binarization_score,
            bimodality_score=bimodality_score,
            contrast_score=contrast_score,
            noise_score=noise_score,
            problem_regions=problem_regions,
            confidence=confidence,
            severity=severity,
            estimated_threshold=estimated_threshold,
        )

    def _compute_bimodality(self, gray: np.ndarray) -> tuple[float, int]:
        """Compute histogram bimodality score.

        A bimodal histogram indicates clear separation between text and background,
        which is ideal for binarization.

        Args:
            gray: Grayscale image

        Returns:
            Tuple of (bimodality_score, estimated_threshold)
        """
        # Use Otsu's method to find optimal threshold
        threshold, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        threshold = int(threshold)

        # Compute histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = hist.sum()
        if total_pixels < 1:
            return 0.0, threshold

        hist = hist / total_pixels  # Normalize

        # Calculate between-class variance using Otsu's method
        # This measures how well separated the two classes are
        # Use threshold + 1 to include threshold pixel in foreground
        w0 = np.sum(hist[: threshold + 1])
        w1 = np.sum(hist[threshold + 1 :])

        # Handle edge cases
        if w0 < 1e-6 or w1 < 1e-6:
            # Try to find actual peaks in histogram
            # This handles uniform or near-uniform images
            # Check histogram spread
            non_zero_bins = np.nonzero(hist > 0.001)[0]
            if len(non_zero_bins) > 0:
                spread = non_zero_bins[-1] - non_zero_bins[0]
                # Spread of 0 = uniform, spread of 255 = full range
                return float(min(1.0, spread / 200.0)), threshold
            return 0.0, threshold

        # Compute class means
        indices = np.arange(256)
        mean0 = np.sum(indices[: threshold + 1] * hist[: threshold + 1]) / w0
        mean1 = np.sum(indices[threshold + 1 :] * hist[threshold + 1 :]) / w1

        # Between-class variance (Otsu's criterion)
        between_var = w0 * w1 * (mean0 - mean1) ** 2

        # Normalize to 0-1
        # For clear document images, between_var can range from 0 to ~4000+
        bimodality_score = min(1.0, between_var / 3000.0)

        return float(bimodality_score), threshold

    def _determine_contrast_issue_type(
        self, cell_std: float, local_contrast: float
    ) -> str:
        """Determine the type of contrast issue for a cell.

        Args:
            cell_std: Standard deviation of cell pixel values
            local_contrast: Normalized local contrast value

        Returns:
            Issue type string: 'uniform', 'low_contrast', or 'marginal_contrast'
        """
        if cell_std < 5:
            return "uniform"
        if local_contrast < 0.05:
            return "low_contrast"
        return "marginal_contrast"

    def _create_problem_region(
        self,
        x1: int,
        y1: int,
        cell_w: int,
        cell_h: int,
        scale: float,
        original_w: int,
        original_h: int,
        issue: str,
        local_contrast: float,
    ) -> ProblemRegion:
        """Create a ProblemRegion for a low-contrast cell.

        Args:
            x1: Cell x-coordinate in subsampled image
            y1: Cell y-coordinate in subsampled image
            cell_w: Cell width in subsampled image
            cell_h: Cell height in subsampled image
            scale: Scale factor used for subsampling
            original_w: Original image width
            original_h: Original image height
            issue: Issue type string
            local_contrast: Normalized local contrast value

        Returns:
            ProblemRegion instance
        """
        orig_x = int(x1 / scale)
        orig_y = int(y1 / scale)
        orig_w = int(cell_w / scale)
        orig_h_cell = int(cell_h / scale)
        severity = 1.0 - (local_contrast / self.min_contrast)

        return ProblemRegion(
            x=orig_x,
            y=orig_y,
            width=min(orig_w, original_w - orig_x),
            height=min(orig_h_cell, original_h - orig_y),
            issue=issue,
            severity=float(min(1.0, severity)),
        )

    def _analyze_local_contrast(
        self, gray: np.ndarray, scale: float, original_h: int, original_w: int
    ) -> tuple[float, list[ProblemRegion]]:
        """Analyze local contrast across image regions.

        Args:
            gray: Grayscale image (possibly subsampled)
            scale: Scale factor used for subsampling
            original_h: Original image height
            original_w: Original image width

        Returns:
            Tuple of (contrast_score, problem_regions)
        """
        h, w = gray.shape
        cell_h = h // self.grid_size
        cell_w = w // self.grid_size

        if cell_h < 10 or cell_w < 10:
            return 1.0, []

        problem_regions = []
        contrast_scores = []

        for i in range(self.grid_size):
            for j in range(self.grid_size):
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w
                cell = gray[y1:y2, x1:x2]

                # Compute local contrast (std / mean)
                cell_mean = np.mean(cell)
                cell_std = np.std(cell)

                # Normalize contrast (cell_std / 255.0), handle zero mean
                local_contrast = cell_std / 255.0 if cell_mean > 0 else 0.0

                contrast_scores.append(local_contrast)

                # Identify problem regions
                if local_contrast < self.min_contrast:
                    issue = self._determine_contrast_issue_type(
                        cell_std, local_contrast
                    )
                    region = self._create_problem_region(
                        x1,
                        y1,
                        cell_w,
                        cell_h,
                        scale,
                        original_w,
                        original_h,
                        issue,
                        local_contrast,
                    )
                    problem_regions.append(region)

        # Overall contrast score
        if contrast_scores:
            avg_contrast = np.mean(contrast_scores)
            # Scale to 0-1 (typical good contrast is 0.15-0.30)
            contrast_score = min(1.0, avg_contrast / 0.20)
        else:
            contrast_score = 0.5

        return float(contrast_score), problem_regions

    def _compute_noise_impact(self, gray: np.ndarray) -> float:
        """Estimate how much noise would affect binarization.

        Uses Laplacian variance to estimate noise/texture level.
        High noise makes binarization difficult.

        Args:
            gray: Grayscale image

        Returns:
            Noise impact score (0-1, higher = less noise = better)
        """
        # Compute Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = laplacian.var()

        # Very high variance suggests noise or complex textures
        # Very low variance suggests blur (also bad for binarization)
        # Optimal is moderate variance (clear edges)

        # Normalize: ideal variance is around 500-2000 for documents
        if lap_var < 100:
            # Too blurry
            noise_score = lap_var / 100.0
        elif lap_var > 5000:
            # Too noisy/textured
            noise_score = max(0.0, 1.0 - (lap_var - 5000) / 10000.0)
        else:
            # Good range
            noise_score = 1.0

        return float(max(0.0, min(1.0, noise_score)))

    def _compute_severity(self, score: float) -> Severity:
        """Compute severity based on binarization score.

        Args:
            score: Binarization quality score (0-1)

        Returns:
            Severity level
        """
        if score < self.threshold_critical:
            return Severity.CRITICAL
        if score < self.threshold_high:
            return Severity.HIGH
        if score < self.threshold_medium:
            return Severity.MEDIUM
        return Severity.LOW

    def _compute_confidence(self, gray: np.ndarray, score: float) -> float:
        """Compute confidence score for the detection.

        Args:
            gray: Grayscale image
            score: Binarization quality score

        Returns:
            Confidence score (0-1)
        """
        # Size confidence
        h, w = gray.shape
        size_confidence = min(1.0, (h * w) / 250000)

        # Detection clarity
        threshold_distances = [
            abs(score - self.threshold_medium),
            abs(score - self.threshold_high),
            abs(score - self.threshold_critical),
        ]
        clarity = min(threshold_distances) * 5
        clarity_confidence = min(1.0, 0.5 + clarity)

        confidence = 0.6 * size_confidence + 0.4 * clarity_confidence
        return float(min(0.95, max(0.5, confidence)))


@dataclass
class BleedThroughResult:
    """Result from bleed-through detection.

    Attributes:
        bleed_through_detected: Whether bleed-through is present
        severity: Overall severity (0-1, higher = worse)
        affected_ratio: Ratio of image area affected by bleed-through
        affected_regions: List of ProblemRegion objects identifying affected areas
        confidence: Detection confidence (0-1)
        severity_level: Categorical severity level
        background_uniformity: How uniform the background is (0-1, higher = more uniform)
        bleed_intensity: Average intensity of detected bleed-through patterns
    """

    bleed_through_detected: bool
    severity: float
    affected_ratio: float
    affected_regions: list[ProblemRegion]
    confidence: float
    severity_level: Severity
    background_uniformity: float
    bleed_intensity: float


class BleedThroughDetector:
    """Detector for bleed-through artifacts in scanned documents.

    Bleed-through occurs when text or images from the reverse side (verso)
    of a page show through to the front side (recto) during scanning.
    This is common in thin paper or aggressive scan settings.

    Detection approach:
    1. Extract background regions (non-text areas)
    2. Apply morphological operations to isolate faint patterns
    3. Detect low-contrast, diffuse patterns characteristic of bleed-through
    4. Distinguish from legitimate content using intensity and structure analysis

    Attributes:
        severity_threshold_low: Minimum severity for LOW rating
        severity_threshold_medium: Minimum severity for MEDIUM rating
        severity_threshold_high: Minimum severity for HIGH rating
        min_region_size: Minimum pixels for a region to be considered
        background_sample_ratio: Ratio of image to sample for background analysis

    Example:
        >>> detector = BleedThroughDetector()
        >>> result = detector.detect(image)
        >>> if result.bleed_through_detected:
        ...     print(f"Bleed-through: {result.severity:.2f} severity")
        ...     for region in result.affected_regions:
        ...         print(f"  Region at ({region.x}, {region.y})")
    """

    def __init__(
        self,
        severity_threshold_low: float = 0.1,
        severity_threshold_medium: float = 0.25,
        severity_threshold_high: float = 0.5,
        min_region_size: int = 100,
        background_sample_ratio: float = 0.3,
    ) -> None:
        """Initialize bleed-through detector.

        Args:
            severity_threshold_low: Threshold for LOW severity (default: 0.1)
            severity_threshold_medium: Threshold for MEDIUM severity (default: 0.25)
            severity_threshold_high: Threshold for HIGH severity (default: 0.5)
            min_region_size: Minimum region size in pixels (default: 100)
            background_sample_ratio: Expected background ratio (default: 0.3)
        """
        self.severity_threshold_low = severity_threshold_low
        self.severity_threshold_medium = severity_threshold_medium
        self.severity_threshold_high = severity_threshold_high
        self.min_region_size = min_region_size
        self.background_sample_ratio = background_sample_ratio

    def detect(self, image: np.ndarray) -> BleedThroughResult:
        """Detect bleed-through artifacts in an image.

        Args:
            image: Input image (BGR or grayscale format)

        Returns:
            BleedThroughResult with detection details

        Raises:
            ValueError: If image is invalid or too small
        """
        if image is None or image.size == 0:
            raise ValueError("Image cannot be empty")

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape
        if h < 16 or w < 16:
            raise ValueError(f"Image too small: {w}x{h}, minimum 16x16")

        # Subsample for performance (target < 15ms)
        max_dim = 512
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            gray_small = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            gray_small = gray

        # Detect bleed-through patterns
        (
            bleed_mask,
            bleed_intensity,
            background_uniformity,
        ) = self._detect_bleed_patterns(gray_small)

        # Find affected regions
        affected_regions = self._find_affected_regions(bleed_mask, scale)

        # Calculate severity
        affected_ratio = float(np.sum(bleed_mask > 0) / bleed_mask.size)
        severity = self._calculate_severity(
            affected_ratio, bleed_intensity, background_uniformity
        )

        # Determine if bleed-through is detected
        bleed_detected = severity >= self.severity_threshold_low

        # Get severity level
        severity_level = self._get_severity_level(severity)

        # Calculate confidence
        confidence = self._compute_confidence(gray_small, severity, bleed_detected)

        return BleedThroughResult(
            bleed_through_detected=bleed_detected,
            severity=severity,
            affected_ratio=affected_ratio,
            affected_regions=affected_regions,
            confidence=confidence,
            severity_level=severity_level,
            background_uniformity=background_uniformity,
            bleed_intensity=bleed_intensity,
        )

    def _detect_bleed_patterns(
        self, gray: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Detect bleed-through patterns in the image.

        Bleed-through appears as faint, diffuse patterns in background regions.
        We detect this by:
        1. Identifying background (light) regions
        2. Looking for unexpected low-contrast patterns in those regions
        3. Using morphological operations to isolate ghost text/images

        Args:
            gray: Grayscale image

        Returns:
            Tuple of (bleed_mask, bleed_intensity, background_uniformity)
        """
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Identify foreground (dark text) using Otsu's threshold
        _, fg_mask = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Background is the inverse
        bg_mask = cv2.bitwise_not(fg_mask)

        # Calculate background uniformity
        bg_pixels = gray[bg_mask > 0]
        if len(bg_pixels) > 0:
            background_uniformity = 1.0 - (float(np.std(bg_pixels)) / 128.0)
            background_uniformity = max(0.0, min(1.0, background_uniformity))
        else:
            background_uniformity = 1.0

        # Apply morphological opening to remove foreground, keeping only faint patterns
        # Use a larger kernel to suppress legitimate text
        kernel_size = max(3, min(gray.shape) // 50)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        # Subtract opened from original to get fine structures
        # This reveals faint patterns that were "underneath" the text
        diff = cv2.absdiff(gray, opened)

        # Focus on background regions only (where bleed-through appears)
        bg_diff = cv2.bitwise_and(diff, diff, mask=bg_mask)

        # Threshold to find significant bleed-through patterns
        # Bleed-through is typically faint (10-50 intensity difference)
        _, bleed_mask = cv2.threshold(bg_diff, 8, 255, cv2.THRESH_BINARY)

        # Remove small noise with morphological opening
        small_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bleed_mask = cv2.morphologyEx(bleed_mask, cv2.MORPH_OPEN, small_kernel)

        # Calculate bleed intensity (average intensity of detected patterns)
        bleed_pixels = bg_diff[bleed_mask > 0]
        bleed_intensity = (
            float(np.mean(bleed_pixels.astype(np.float64))) / 255.0
            if len(bleed_pixels) > 0
            else 0.0
        )

        return bleed_mask, bleed_intensity, background_uniformity

    def _find_affected_regions(
        self, bleed_mask: np.ndarray, scale: float
    ) -> list[ProblemRegion]:
        """Find and characterize affected regions.

        Args:
            bleed_mask: Binary mask of bleed-through areas
            scale: Scale factor used for subsampling

        Returns:
            List of ProblemRegion objects
        """
        regions: list[ProblemRegion] = []

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            bleed_mask, connectivity=8
        )

        # Minimum area (accounting for scale)
        min_area = self.min_region_size * (scale**2)

        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area:
                continue

            # Get bounding box and scale back to original size
            x = int(stats[i, cv2.CC_STAT_LEFT] / scale)
            y = int(stats[i, cv2.CC_STAT_TOP] / scale)
            width = int(stats[i, cv2.CC_STAT_WIDTH] / scale)
            height = int(stats[i, cv2.CC_STAT_HEIGHT] / scale)

            # Calculate region severity based on coverage within bounding box
            region_mask = labels == i
            region_coverage = float(np.sum(region_mask)) / (
                stats[i, cv2.CC_STAT_WIDTH] * stats[i, cv2.CC_STAT_HEIGHT]
            )

            regions.append(
                ProblemRegion(
                    x=x,
                    y=y,
                    width=max(1, width),
                    height=max(1, height),
                    issue="bleed_through",
                    severity=min(1.0, region_coverage),
                )
            )

        # Sort by severity (worst first)
        regions.sort(key=lambda r: r.severity, reverse=True)

        # Limit to top 10 regions
        return regions[:10]

    def _calculate_severity(
        self,
        affected_ratio: float,
        bleed_intensity: float,
        background_uniformity: float,
    ) -> float:
        """Calculate overall bleed-through severity.

        Args:
            affected_ratio: Ratio of image affected by bleed-through
            bleed_intensity: Average intensity of bleed-through patterns
            background_uniformity: How uniform the background is

        Returns:
            Severity score (0-1)
        """
        # Affected ratio is the primary factor
        # More affected area = higher severity
        ratio_score = min(1.0, affected_ratio * 5)  # 20% coverage = max severity

        # Bleed intensity indicates how visible the bleed-through is
        # 25% intensity reaches maximum severity
        intensity_score = min(1.0, bleed_intensity * 4)

        # Low background uniformity suggests bleed-through
        uniformity_score = max(0.0, 1.0 - background_uniformity)

        # Weighted combination
        severity = 0.5 * ratio_score + 0.3 * intensity_score + 0.2 * uniformity_score

        return float(max(0.0, min(1.0, severity)))

    def _get_severity_level(self, severity: float) -> Severity:
        """Convert severity score to categorical level.

        Args:
            severity: Numeric severity (0-1)

        Returns:
            Severity enum value
        """
        if severity >= self.severity_threshold_high:
            return Severity.HIGH
        if severity >= self.severity_threshold_medium:
            return Severity.MEDIUM
        # Return LOW for minimal or no bleed-through (no NONE in Severity enum)
        return Severity.LOW

    def _compute_confidence(
        self, gray: np.ndarray, severity: float, detected: bool
    ) -> float:
        """Compute detection confidence.

        Args:
            gray: Grayscale image
            severity: Calculated severity score
            detected: Whether bleed-through was detected

        Returns:
            Confidence score (0-1)
        """
        # Size-based confidence
        h, w = gray.shape
        size_confidence = min(1.0, (h * w) / 100000)

        # Severity clarity (how far from thresholds)
        if detected:
            # Higher severity = more confident in detection
            clarity = min(1.0, severity / self.severity_threshold_high)
        else:
            # Lower severity = more confident in no-detection
            clarity = (
                1.0 - (severity / self.severity_threshold_low)
                if self.severity_threshold_low > 0
                else 1.0
            )
            clarity = max(0.0, min(1.0, clarity))

        confidence = 0.5 * size_confidence + 0.5 * clarity
        return float(min(0.95, max(0.5, confidence)))


# Convenience functions
def detect_illumination(image: np.ndarray) -> IlluminationDetectionResult:
    """Convenience function for illumination detection.

    Args:
        image: Input image (BGR format)

    Returns:
        IlluminationDetectionResult

    Example:
        >>> img = cv2.imread("scanned_page.jpg")
        >>> result = detect_illumination(img)
        >>> if result.has_issues:
        ...     print(
        ...         f"Illumination issue: {result.issue_type.value}, "
        ...         f"score={result.score:.2f} ({result.severity.value})"
        ...     )
    """
    detector = IlluminationDetector()
    return detector.detect(image)


def detect_jpeg_blockiness(image: np.ndarray) -> JPEGBlockinessResult:
    """Convenience function for JPEG blockiness detection.

    Args:
        image: Input image (BGR format)

    Returns:
        JPEGBlockinessResult

    Example:
        >>> img = cv2.imread("compressed.jpg")
        >>> result = detect_jpeg_blockiness(img)
        >>> if result.has_artifacts:
        ...     print(
        ...         f"JPEG artifacts detected: quality~{result.estimated_quality}, "
        ...         f"blockiness={result.blockiness_score:.2f} ({result.severity.value})"
        ...     )
    """
    detector = JPEGBlockinessDetector()
    return detector.detect(image)


def detect_binarization_quality(image: np.ndarray) -> BinarizationQualityResult:
    """Convenience function for binarization quality assessment.

    Args:
        image: Input image (BGR format)

    Returns:
        BinarizationQualityResult

    Example:
        >>> img = cv2.imread("document.jpg")
        >>> result = detect_binarization_quality(img)
        >>> if result.binarization_score < 0.7:
        ...     print(
        ...         f"Binarization issues: score={result.binarization_score:.2f}, "
        ...         f"problem regions: {len(result.problem_regions)}"
        ...     )
    """
    detector = BinarizationQualityDetector()
    return detector.detect(image)


def detect_bleed_through(image: np.ndarray) -> BleedThroughResult:
    """Convenience function for bleed-through detection.

    Detects text or images showing through from the verso (reverse) side
    of a scanned document, common with thin paper or aggressive scanning.

    Args:
        image: Input image (BGR format)

    Returns:
        BleedThroughResult

    Example:
        >>> img = cv2.imread("scanned_page.jpg")
        >>> result = detect_bleed_through(img)
        >>> if result.bleed_through_detected:
        ...     print(
        ...         f"Bleed-through detected: severity={result.severity:.2f}, "
        ...         f"affected regions: {len(result.affected_regions)}"
        ...     )
    """
    detector = BleedThroughDetector()
    return detector.detect(image)
