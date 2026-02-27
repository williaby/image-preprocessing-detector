"""Warping and curvature distortion detection for scanned documents.

Detects page warping typical of book scans and mobile captures using:
1. Hough line detection for horizontal text baselines
2. Line curvature analysis (endpoint deviation from horizontal)
3. Page boundary rectangularity assessment
4. Polynomial fit to line midpoints for barrel/pincushion classification

Populates ``PageLayoutSummary.has_warping``, ``PageLayoutSummary.warping_score``,
and ``PageLayoutSummary.warping_type`` in the Stream 1 schema.

Performance target: <15ms per page.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _filter_horizontal_lines,
    _validate_and_preprocess,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# Result dataclass (Stream 1 schema-aligned)
# ============================================================================


@dataclass
class WarpingDetectionResult:
    """Result of warping distortion detection.

    Attributes:
        has_warping: Whether the page exhibits significant warping.
        warping_score: Severity from 0 (no warping) to 1 (severe warping).
        warping_type: Classification -- ``"barrel"``, ``"pincushion"``,
            ``"perspective"``, ``"wave"``, or ``None`` when no warping.
        line_count: Number of horizontal lines detected via Hough transform.
        confidence: Confidence in the detection result (0-1).
    """

    has_warping: bool
    warping_score: float
    warping_type: str | None
    line_count: int
    confidence: float


# ============================================================================
# Default thresholds
# ============================================================================

_DEFAULT_WARPING_THRESHOLD = 0.15
_DEFAULT_MIN_HORIZONTAL_LINES = 5
_DEFAULT_CURVATURE_WEIGHT = 0.45
_DEFAULT_RECTANGULARITY_WEIGHT = 0.30
_DEFAULT_POLYNOMIAL_WEIGHT = 0.25


# ============================================================================
# Internal helpers
# ============================================================================


def _detect_lines_for_warping(
    gray: np.ndarray,
    width: int,
) -> np.ndarray | None:
    """Detect lines using parameters tuned for warping analysis.

    Uses shorter minimum line length and lower threshold than the
    general-purpose ``_detect_hough_lines`` to capture curved segments
    that appear as short line fragments.

    Args:
        gray: Grayscale image.
        width: Image width in pixels.

    Returns:
        Array of detected line segments, or None.
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    min_line_length = max(width // 8, 30)
    return cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=min_line_length,
        maxLineGap=15,
    )


def _compute_line_curvature(
    horizontal_lines: list[tuple[int, int, int, int]],
    image_height: int,
) -> tuple[float, float]:
    """Measure endpoint deviation of horizontal lines from perfect horizontal.

    For each detected horizontal line, the vertical offset between its two
    endpoints is normalised by image height.  The aggregate statistic
    captures how much the lines bow upward or downward.

    Args:
        horizontal_lines: Filtered near-horizontal lines (x1, y1, x2, y2).
        image_height: Height of the source image in pixels.

    Returns:
        Tuple of (curvature_score, max_deviation).
        ``curvature_score`` is in [0, 1]; ``max_deviation`` is the largest
        normalised endpoint offset observed.
    """
    if not horizontal_lines or image_height <= 0:
        return 0.0, 0.0

    deviations: list[float] = []
    for x1, y1, x2, y2 in horizontal_lines:
        line_length = float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        if line_length > 0:
            deviation = abs(y2 - y1) / line_length
            deviations.append(deviation)

    if not deviations:
        return 0.0, 0.0

    max_deviation = max(deviations)
    mean_deviation = float(np.mean(deviations))
    # Scale: deviation of ~0.17 (10 degrees) maps to ~1.0
    curvature_score = min(1.0, mean_deviation * 6.0)
    return curvature_score, max_deviation


def _compute_rectangularity(
    gray: np.ndarray,
    image_height: int,
    image_width: int,
) -> float:
    """Assess how rectangular the dominant page contour is.

    A perfectly rectangular page yields a score near 0.  Non-rectangular
    contours (e.g. barrel-distorted or wavy edges) produce higher scores.

    Args:
        gray: Grayscale image.
        image_height: Image height in pixels.
        image_width: Image width in pixels.

    Returns:
        Rectangularity deficit in [0, 1] where 0 = perfect rectangle.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0

    largest = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(largest)
    image_area = image_height * image_width

    # Ignore contours that are too small to be the page boundary
    if contour_area < image_area * 0.1:
        return 0.0

    # Compare contour area to its minimum-area bounding rectangle
    _rect_center, _rect_size, _rect_angle = cv2.minAreaRect(largest)
    rect_area = _rect_size[0] * _rect_size[1]
    if rect_area <= 0:
        return 0.0

    # Rectangularity = contour_area / bounding_rect_area  (1.0 = perfect)
    rectangularity_ratio = float(contour_area / rect_area)
    # Invert: deficit = 1 - ratio, so higher = more warped
    deficit = 1.0 - min(1.0, rectangularity_ratio)
    # Scale up: small deficits are significant for warping
    return float(min(1.0, deficit * 5.0))


def _compute_polynomial_fit(
    horizontal_lines: list[tuple[int, int, int, int]],
    image_width: int,
) -> tuple[float, float, float]:
    """Fit a 2nd-degree polynomial to horizontal line midpoints.

    The quadratic coefficient indicates barrel (>0) or pincushion (<0)
    distortion.  High residuals indicate wavy distortion.

    Args:
        horizontal_lines: Filtered near-horizontal lines (x1, y1, x2, y2).
        image_width: Image width in pixels.

    Returns:
        Tuple of (poly_score, quadratic_coefficient, residual_score).
        ``poly_score`` is in [0, 1]; ``quadratic_coefficient`` is the raw
        a-coefficient from the fit; ``residual_score`` is the normalised
        mean absolute residual.
    """
    if len(horizontal_lines) < 3 or image_width <= 0:
        return 0.0, 0.0, 0.0

    midpoints_x: list[float] = []
    midpoints_y: list[float] = []
    for x1, y1, x2, y2 in horizontal_lines:
        midpoints_x.append((x1 + x2) / 2.0)
        midpoints_y.append((y1 + y2) / 2.0)

    arr_x = np.array(midpoints_x)
    arr_y = np.array(midpoints_y)

    # Sort by x for meaningful polynomial fit
    sort_idx = np.argsort(arr_x)
    arr_x = arr_x[sort_idx]
    arr_y = arr_y[sort_idx]

    # Check y-range: if midpoints span many different y-levels (e.g. many
    # parallel text lines), the data describes *separate* baselines rather
    # than a single curved line.  A large y-range relative to image height
    # indicates this situation; the polynomial fit would be meaningless.
    y_range = float(np.ptp(arr_y))
    if y_range > 100:
        # Many parallel lines -- not a single curve; skip polynomial fit
        return 0.0, 0.0, 0.0

    # Normalise x to [0, 1] for numerical stability
    arr_x_norm = arr_x / image_width

    # Fit 2nd-degree polynomial: y = a*x^2 + b*x + c
    try:
        with np.errstate(all="ignore"):
            coeffs = np.polyfit(arr_x_norm, arr_y, 2)
    except (np.linalg.LinAlgError, ValueError):
        return 0.0, 0.0, 0.0

    # Reject obviously degenerate fits (NaN / Inf)
    if not np.all(np.isfinite(coeffs)):
        return 0.0, 0.0, 0.0

    quadratic_coeff = float(coeffs[0])

    # Compute residuals
    fitted_y = np.polyval(coeffs, arr_x_norm)
    residuals = np.abs(arr_y - fitted_y)
    mean_residual = float(np.mean(residuals))

    # Normalise quadratic coefficient: values around +-200 are strongly warped
    poly_score = min(1.0, abs(quadratic_coeff) / 200.0)

    # Normalise residual: high residuals => wavy distortion
    residual_score = min(1.0, mean_residual / 20.0)

    return poly_score, quadratic_coeff, residual_score


def _classify_warping_type(
    quadratic_coeff: float,
    residual_score: float,
    horizontal_lines: list[tuple[int, int, int, int]],
) -> str | None:
    """Classify the warping type based on polynomial fit and line analysis.

    Args:
        quadratic_coeff: Quadratic coefficient from polynomial fit.
        residual_score: Normalised mean residual from polynomial fit.
        horizontal_lines: Filtered near-horizontal lines.

    Returns:
        One of ``"barrel"``, ``"pincushion"``, ``"perspective"``, ``"wave"``,
        or ``None`` if no warping type can be determined.
    """
    # High residuals indicate wavy distortion
    if residual_score > 0.3:
        return "wave"

    # Check for perspective: inconsistently angled lines
    if len(horizontal_lines) >= 3:
        angles: list[float] = []
        for x1, y1, x2, y2 in horizontal_lines:
            dx = float(x2 - x1)
            dy = float(y2 - y1)
            if abs(dx) > 1e-6:
                angle = np.arctan2(dy, dx) * 180.0 / np.pi
                angles.append(angle)
        if len(angles) >= 3:
            angle_std = float(np.std(angles))
            # High angular spread = perspective distortion
            if angle_std > 2.5:
                return "perspective"

    # Barrel vs pincushion from polynomial curvature
    if abs(quadratic_coeff) > 10.0:
        return "barrel" if quadratic_coeff > 0 else "pincushion"

    return None


def _compute_confidence(line_count: int, warping_score: float) -> float:
    """Compute detection confidence from evidence quality.

    Args:
        line_count: Number of horizontal lines detected.
        warping_score: Combined warping score.

    Returns:
        Confidence value in [0, 1].
    """
    # More lines => higher confidence
    if line_count >= 20:
        base_confidence = 0.85
    elif line_count >= 10:
        base_confidence = 0.70
    elif line_count >= 5:
        base_confidence = 0.55
    else:
        base_confidence = 0.35

    # Extreme scores (near 0 or near 1) are more certain
    score_certainty = abs(warping_score - 0.5) * 0.3
    return min(1.0, base_confidence + score_certainty)


# ============================================================================
# Public API: WarpingDetector class
# ============================================================================


class WarpingDetector:
    """Detect warping and curvature distortion in scanned documents.

    Combines three complementary signals:

    1. **Line curvature** -- endpoint deviation of Hough-detected horizontal
       lines from a perfect horizontal.
    2. **Page boundary rectangularity** -- how well the largest page contour
       approximates a rectangle.
    3. **Polynomial fit** -- a quadratic fit to horizontal line midpoints
       reveals barrel, pincushion, or wavy distortion.

    Signals are fused via weighted average into ``warping_score`` (0-1).

    Example:
        >>> detector = WarpingDetector()
        >>> image = cv2.imread("book_scan.jpg")
        >>> result = detector.detect(image)
        >>> if result.has_warping:
        ...     print(
        ...         f"Warping: {result.warping_type}, score={result.warping_score:.2f}"
        ...     )
    """

    def __init__(
        self,
        warping_threshold: float = _DEFAULT_WARPING_THRESHOLD,
        min_horizontal_lines: int = _DEFAULT_MIN_HORIZONTAL_LINES,
        curvature_weight: float = _DEFAULT_CURVATURE_WEIGHT,
        rectangularity_weight: float = _DEFAULT_RECTANGULARITY_WEIGHT,
        polynomial_weight: float = _DEFAULT_POLYNOMIAL_WEIGHT,
    ) -> None:
        """Initialise warping detector with configurable thresholds.

        Args:
            warping_threshold: Score above which ``has_warping`` is True.
            min_horizontal_lines: Minimum horizontal lines required for
                reliable analysis (below this, returns no-warping).
            curvature_weight: Weight for line curvature signal.
            rectangularity_weight: Weight for page rectangularity signal.
            polynomial_weight: Weight for polynomial fit signal.
        """
        self.warping_threshold = warping_threshold
        self.min_horizontal_lines = min_horizontal_lines
        self.curvature_weight = curvature_weight
        self.rectangularity_weight = rectangularity_weight
        self.polynomial_weight = polynomial_weight

        logger.info(
            "warping_detector_init",
            warping_threshold=warping_threshold,
            min_horizontal_lines=min_horizontal_lines,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> WarpingDetectionResult:
        """Analyse an image for warping distortion.

        Args:
            image: Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            WarpingDetectionResult with warping classification and metrics.

        Raises:
            ValueError: If the image is ``None`` or empty.
        """
        gray, _binary, height, width = _validate_and_preprocess(image)

        # Detect and filter horizontal lines (warping-tuned parameters)
        raw_lines = _detect_lines_for_warping(gray, width)
        if raw_lines is None:
            return self._no_warping_result(line_count=0)

        horizontal_lines = _filter_horizontal_lines(raw_lines)
        line_count = len(horizontal_lines)

        if line_count < self.min_horizontal_lines:
            return self._no_warping_result(line_count=line_count)

        # Signal 1: Line curvature
        curvature_score, _max_dev = _compute_line_curvature(horizontal_lines, height)

        # Signal 2: Page boundary rectangularity
        rectangularity_score = _compute_rectangularity(gray, height, width)

        # Signal 3: Polynomial fit
        poly_score, quadratic_coeff, residual_score = _compute_polynomial_fit(
            horizontal_lines, width
        )

        # Fuse signals via weighted average
        warping_score = (
            self.curvature_weight * curvature_score
            + self.rectangularity_weight * rectangularity_score
            + self.polynomial_weight * poly_score
        )
        warping_score = min(1.0, max(0.0, warping_score))

        # Classification
        has_warping = warping_score > self.warping_threshold

        warping_type: str | None = None
        if has_warping:
            warping_type = _classify_warping_type(
                quadratic_coeff, residual_score, horizontal_lines
            )

        confidence = _compute_confidence(line_count, warping_score)

        logger.debug(
            "warping_detection_result",
            has_warping=has_warping,
            warping_score=round(warping_score, 4),
            warping_type=warping_type,
            line_count=line_count,
            curvature_score=round(curvature_score, 4),
            rectangularity_score=round(rectangularity_score, 4),
            poly_score=round(poly_score, 4),
            confidence=round(confidence, 4),
        )

        return WarpingDetectionResult(
            has_warping=has_warping,
            warping_score=round(warping_score, 4),
            warping_type=warping_type,
            line_count=line_count,
            confidence=round(confidence, 4),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _no_warping_result(self, line_count: int) -> WarpingDetectionResult:
        """Create a result indicating no warping detected.

        Args:
            line_count: Number of horizontal lines found (may be 0).

        Returns:
            WarpingDetectionResult with has_warping=False.
        """
        confidence = _compute_confidence(line_count, 0.0)
        return WarpingDetectionResult(
            has_warping=False,
            warping_score=0.0,
            warping_type=None,
            line_count=line_count,
            confidence=round(confidence, 4),
        )


# ============================================================================
# Module-level convenience function
# ============================================================================

_default_detector: WarpingDetector | None = None


def detect_warping_distortion(image: np.ndarray) -> WarpingDetectionResult:
    """Convenience function to detect warping with default thresholds.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image: Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        WarpingDetectionResult with warping classification and metrics.

    Raises:
        ValueError: If the image is ``None`` or empty.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = WarpingDetector()
    return _default_detector.detect(image)
