"""Classical image quality assessment (IQA) detectors.

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
                    best_angle = float(angle)

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
            raise ValueError("Invalid or empty image provided")

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
            raise ValueError("Invalid or empty image provided")

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
            raise ValueError("Invalid or empty image provided")

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
