"""Document source/capture method classifier using a 5-signal ensemble.

Classifies how a document was digitised (scanner vs. camera) by analysing
low-level image properties: background uniformity, edge sharpness, page
boundary rectangularity, perspective distortion, and illumination evenness.

Each signal produces a scanner-likelihood score in [0, 1].  A weighted
combination maps to a :class:`CaptureMethod` enum value with an associated
confidence score.

Example:
    >>> import cv2
    >>> from image_preprocessing_detector.classification.document_source_classifier import (
    ...     classify_document_source,
    ... )
    >>> image = cv2.imread("scan.png")
    >>> result = classify_document_source(image)
    >>> print(result.capture_method, result.scanner_score)
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.detection.advanced_detectors import (
    _validate_and_preprocess,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Valid CaptureMethod values (for runtime validation)
# ---------------------------------------------------------------------------
_VALID_CAPTURE_METHODS: frozenset[str] = frozenset(m.value for m in CaptureMethod)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentSourceResult:
    """Result of document source classification.

    Attributes:
        capture_method: CaptureMethod enum value string.
        scanner_score: Weighted ensemble score in [0, 1] (1 = definitely scanner).
        background_uniformity: Border region uniformity in [0, 1].
        edge_sharpness: Canny edge density at page boundaries in [0, 1].
        rectangularity: Contour-to-bounding-rect area ratio in [0, 1].
        perspective_distortion: Degree of line convergence in [0, 1] (1 = heavy).
        illumination_evenness: Quadrant intensity variance in [0, 1] (1 = even).
        confidence: Classification confidence in [0, 1].
    """

    capture_method: str
    scanner_score: float
    background_uniformity: float
    edge_sharpness: float
    rectangularity: float
    perspective_distortion: float
    illumination_evenness: float
    confidence: float


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

_DEFAULT_BORDER_FRACTION = 0.10
_DEFAULT_BACKGROUND_WEIGHT = 0.25
_DEFAULT_EDGE_WEIGHT = 0.20
_DEFAULT_RECTANGULARITY_WEIGHT = 0.20
_DEFAULT_PERSPECTIVE_WEIGHT = 0.15
_DEFAULT_ILLUMINATION_WEIGHT = 0.20

_DEFAULT_SCANNER_HIGH_THRESHOLD = 0.60
_DEFAULT_SCANNER_MID_THRESHOLD = 0.40
_DEFAULT_CAMERA_THRESHOLD = 0.30

# Normalisation constants (empirically determined)
_BACKGROUND_STD_MAX = 40.0
_EDGE_DENSITY_MAX = 0.15
_PERSPECTIVE_ANGLE_MAX = 15.0
_ILLUMINATION_STD_MAX = 30.0


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class DocumentSourceClassifier:
    """Five-signal ensemble for document capture method classification.

    Signals:
        1. **Background uniformity** (weight 0.25): Scanners produce very
           uniform backgrounds.  Measured as std-dev of the border region.
        2. **Edge sharpness** (weight 0.20): Canny edge density at page
           boundaries.  Sharp, clean edges indicate a scanner.
        3. **Page boundary rectangularity** (weight 0.20): Ratio of the
           largest contour area to its bounding rectangle.  High ratio
           (> 0.95) indicates a scanner.
        4. **Perspective distortion** (weight 0.15): Convergence of detected
           lines.  Non-parallel lines suggest a camera capture.
        5. **Illumination evenness** (weight 0.20): Variance of mean
           intensity across image quadrants.  Low variance = scanner.

    Args:
        border_fraction: Fraction of width/height used as the border region.
        scanner_high_threshold: Scanner score above this -> scanner_flatbed.
        scanner_mid_threshold: Scanner score above this -> scanner_adf.
        camera_threshold: Scanner score below this -> camera_smartphone.
    """

    def __init__(
        self,
        *,
        border_fraction: float = _DEFAULT_BORDER_FRACTION,
        scanner_high_threshold: float = _DEFAULT_SCANNER_HIGH_THRESHOLD,
        scanner_mid_threshold: float = _DEFAULT_SCANNER_MID_THRESHOLD,
        camera_threshold: float = _DEFAULT_CAMERA_THRESHOLD,
    ) -> None:
        self.border_fraction = border_fraction
        self.scanner_high_threshold = scanner_high_threshold
        self.scanner_mid_threshold = scanner_mid_threshold
        self.camera_threshold = camera_threshold

    # -- public API ---------------------------------------------------------

    def classify(self, image: np.ndarray) -> DocumentSourceResult:
        """Classify document capture method from a single page image.

        Args:
            image: Input image (BGR, BGRA, or grayscale).

        Returns:
            DocumentSourceResult with all signal scores and final label.

        Raises:
            ValueError: If image is None, empty, or otherwise invalid.
        """
        gray, _binary, height, width = _validate_and_preprocess(image)

        background_uniformity = self._measure_background_uniformity(gray, height, width)
        edge_sharpness = self._measure_edge_sharpness(gray, height, width)
        rectangularity = self._measure_rectangularity(gray)
        perspective_distortion = self._measure_perspective_distortion(gray)
        illumination_evenness = self._measure_illumination_evenness(gray)

        scanner_score = self._compute_scanner_score(
            background_uniformity=background_uniformity,
            edge_sharpness=edge_sharpness,
            rectangularity=rectangularity,
            perspective_distortion=perspective_distortion,
            illumination_evenness=illumination_evenness,
        )

        capture_method = self._map_to_capture_method(scanner_score)
        confidence = self._compute_confidence(scanner_score)

        result = DocumentSourceResult(
            capture_method=capture_method,
            scanner_score=round(scanner_score, 4),
            background_uniformity=round(background_uniformity, 4),
            edge_sharpness=round(edge_sharpness, 4),
            rectangularity=round(rectangularity, 4),
            perspective_distortion=round(perspective_distortion, 4),
            illumination_evenness=round(illumination_evenness, 4),
            confidence=round(confidence, 4),
        )

        logger.debug(
            "document_source_classified",
            capture_method=result.capture_method,
            scanner_score=result.scanner_score,
            confidence=result.confidence,
        )

        return result

    # -- signal measurements ------------------------------------------------

    def _measure_background_uniformity(
        self,
        gray: np.ndarray,
        height: int,
        width: int,
    ) -> float:
        """Compute background uniformity from border region std-dev.

        Low std-dev in the border strip indicates a scanner (uniform
        background).  The score is inverted so 1.0 = perfectly uniform.

        Args:
            gray: Grayscale image.
            height: Image height in pixels.
            width: Image width in pixels.

        Returns:
            Uniformity score in [0, 1].
        """
        inset_y = max(1, int(height * self.border_fraction))
        inset_x = max(1, int(width * self.border_fraction))

        border_pixels = _extract_border_pixels(gray, inset_y, inset_x)

        if border_pixels.size == 0:
            return 0.5

        std_val = float(np.std(border_pixels))
        uniformity = 1.0 - min(std_val / _BACKGROUND_STD_MAX, 1.0)
        return float(np.clip(uniformity, 0.0, 1.0))

    def _measure_edge_sharpness(
        self,
        gray: np.ndarray,
        height: int,
        width: int,
    ) -> float:
        """Measure Canny edge density along page boundaries.

        High density of sharp edges at the page border indicates a clean
        scanner cut.  Soft or blurred edges suggest a camera capture.

        Args:
            gray: Grayscale image.
            height: Image height in pixels.
            width: Image width in pixels.

        Returns:
            Edge sharpness score in [0, 1].
        """
        inset_y = max(1, int(height * self.border_fraction))
        inset_x = max(1, int(width * self.border_fraction))

        edges = cv2.Canny(gray, 50, 150)
        border_edges = _extract_border_pixels(edges, inset_y, inset_x)

        if border_edges.size == 0:
            return 0.5

        density = float(np.count_nonzero(border_edges)) / border_edges.size
        sharpness = min(density / _EDGE_DENSITY_MAX, 1.0)
        return float(np.clip(sharpness, 0.0, 1.0))

    @staticmethod
    def _measure_rectangularity(gray: np.ndarray) -> float:
        """Measure how rectangular the page boundary is.

        Finds the largest contour in a thresholded image and computes the
        ratio of contour area to bounding rectangle area.  A ratio > 0.95
        strongly suggests a scanner.

        Args:
            gray: Grayscale image.

        Returns:
            Rectangularity score in [0, 1].
        """
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return 0.5

        largest = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest)
        _x, _y, rect_w, rect_h = cv2.boundingRect(largest)
        rect_area = rect_w * rect_h

        if rect_area == 0:
            return 0.5

        ratio = contour_area / rect_area
        return float(np.clip(ratio, 0.0, 1.0))

    @staticmethod
    def _measure_perspective_distortion(gray: np.ndarray) -> float:
        """Detect perspective distortion via within-group line convergence.

        Uses probabilistic Hough transform to find lines, classifies them
        into near-horizontal (< 20 deg) and near-vertical (> 70 deg)
        groups, then measures the angular std-dev *within* each group.
        High within-group variance indicates converging lines (camera
        perspective).  Clean horizontal/vertical lines (scanner) yield
        near-zero within-group variance.

        Args:
            gray: Grayscale image.

        Returns:
            Distortion score in [0, 1] (1 = heavy distortion).
        """
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=max(50, gray.shape[1] // 10),
            maxLineGap=10,
        )

        if lines is None or len(lines) < 2:
            return 0.0

        angles = _compute_line_angles(lines)

        if len(angles) < 2:
            return 0.0

        distortion = _compute_within_group_distortion(angles)
        return float(np.clip(distortion, 0.0, 1.0))

    @staticmethod
    def _measure_illumination_evenness(gray: np.ndarray) -> float:
        """Measure illumination evenness across image quadrants.

        Splits the image into four quadrants, computes mean intensity per
        quadrant, then uses the std-dev of those means.  Low variance
        indicates even illumination (scanner).

        Args:
            gray: Grayscale image.

        Returns:
            Evenness score in [0, 1] (1 = perfectly even).
        """
        height, width = gray.shape[:2]
        mid_y = height // 2
        mid_x = width // 2

        # Guard against tiny images where a quadrant might be empty.
        if mid_y == 0 or mid_x == 0:
            return 0.5

        quadrants = [
            gray[:mid_y, :mid_x],
            gray[:mid_y, mid_x:],
            gray[mid_y:, :mid_x],
            gray[mid_y:, mid_x:],
        ]

        means = [float(np.mean(quad)) for quad in quadrants if quad.size > 0]

        if len(means) < 2:
            return 0.5

        std_val = float(np.std(means))
        evenness = 1.0 - min(std_val / _ILLUMINATION_STD_MAX, 1.0)
        return float(np.clip(evenness, 0.0, 1.0))

    # -- aggregation --------------------------------------------------------

    @staticmethod
    def _compute_scanner_score(
        *,
        background_uniformity: float,
        edge_sharpness: float,
        rectangularity: float,
        perspective_distortion: float,
        illumination_evenness: float,
    ) -> float:
        """Weighted combination of all five signals.

        Perspective distortion is a *negative* indicator (high value means
        camera), so it is inverted (1 - distortion) before weighting.

        Args:
            background_uniformity: [0, 1] score from border analysis.
            edge_sharpness: [0, 1] score from Canny edge density.
            rectangularity: [0, 1] score from contour analysis.
            perspective_distortion: [0, 1] distortion score.
            illumination_evenness: [0, 1] evenness score.

        Returns:
            Combined scanner likelihood in [0, 1].
        """
        score = (
            _DEFAULT_BACKGROUND_WEIGHT * background_uniformity
            + _DEFAULT_EDGE_WEIGHT * edge_sharpness
            + _DEFAULT_RECTANGULARITY_WEIGHT * rectangularity
            + _DEFAULT_PERSPECTIVE_WEIGHT * (1.0 - perspective_distortion)
            + _DEFAULT_ILLUMINATION_WEIGHT * illumination_evenness
        )
        return float(np.clip(score, 0.0, 1.0))

    def _map_to_capture_method(self, scanner_score: float) -> str:
        """Map aggregate scanner score to a CaptureMethod value.

        Args:
            scanner_score: Combined scanner likelihood in [0, 1].

        Returns:
            CaptureMethod enum value string.
        """
        if scanner_score > self.scanner_high_threshold:
            return CaptureMethod.SCANNER_FLATBED.value
        if scanner_score > self.scanner_mid_threshold:
            return CaptureMethod.SCANNER_ADF.value
        if scanner_score < self.camera_threshold:
            return CaptureMethod.CAMERA_SMARTPHONE.value
        return CaptureMethod.UNKNOWN.value

    @staticmethod
    def _compute_confidence(scanner_score: float) -> float:
        """Derive confidence from distance to decision boundaries.

        Scores far from the thresholds yield high confidence; scores near
        boundaries yield lower confidence.

        Args:
            scanner_score: Combined scanner likelihood in [0, 1].

        Returns:
            Confidence in [0.5, 1.0].
        """
        boundaries = [
            _DEFAULT_CAMERA_THRESHOLD,
            _DEFAULT_SCANNER_MID_THRESHOLD,
            _DEFAULT_SCANNER_HIGH_THRESHOLD,
        ]
        min_distance = min(abs(scanner_score - b) for b in boundaries)
        # Scale: distance 0 -> 0.5, distance >= 0.2 -> 1.0
        confidence = 0.5 + min(min_distance / 0.2, 1.0) * 0.5
        return float(np.clip(confidence, 0.5, 1.0))


# ---------------------------------------------------------------------------
# Private helpers (extracted to keep classifier methods short)
# ---------------------------------------------------------------------------


def _extract_border_pixels(
    image: np.ndarray,
    inset_y: int,
    inset_x: int,
) -> np.ndarray:
    """Extract pixel values from the border strip of an image.

    The border strip is the region within *inset_y* / *inset_x* of each
    edge, excluding the interior.

    Args:
        image: 2-D array (grayscale or single-channel).
        inset_y: Vertical inset in pixels.
        inset_x: Horizontal inset in pixels.

    Returns:
        1-D array of border pixel values.
    """
    height, width = image.shape[:2]

    if inset_y >= height // 2 or inset_x >= width // 2:
        return image.ravel()

    top = image[:inset_y, :]
    bottom = image[height - inset_y :, :]
    left = image[inset_y : height - inset_y, :inset_x]
    right = image[inset_y : height - inset_y, width - inset_x :]

    return np.concatenate([top.ravel(), bottom.ravel(), left.ravel(), right.ravel()])


def _compute_line_angles(lines: np.ndarray) -> np.ndarray:
    """Compute angles (in degrees) for Hough line segments.

    Args:
        lines: Output of ``cv2.HoughLinesP``, shape ``(N, 1, 4)``.

    Returns:
        1-D array of angles in degrees, range [0, 90].
    """
    angles: list[float] = []
    for line in lines:
        x_1, y_1, x_2, y_2 = line[0]
        dx = float(x_2 - x_1)
        dy = float(y_2 - y_1)
        angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
        angles.append(float(angle))
    return np.array(angles, dtype=np.float64)


def _compute_within_group_distortion(angles: np.ndarray) -> float:
    """Compute perspective distortion from within-group angular variance.

    Lines are classified into near-horizontal (< 20 deg) and near-vertical
    (> 70 deg) groups.  The max within-group std-dev is used as the
    distortion signal.  This avoids penalising images that contain both
    horizontal and vertical lines (normal for scanned documents).

    Lines between 20-70 deg (oblique) are counted directly as evidence of
    distortion if they constitute a significant fraction.

    Args:
        angles: 1-D array of line angles in [0, 90] degrees.

    Returns:
        Distortion score in [0, 1].
    """
    horizontal = angles[angles < 20.0]
    vertical = angles[angles > 70.0]
    oblique = angles[(angles >= 20.0) & (angles <= 70.0)]

    group_stds: list[float] = []
    if len(horizontal) >= 2:
        group_stds.append(float(np.std(horizontal)))
    if len(vertical) >= 2:
        group_stds.append(float(np.std(vertical)))

    # Within-group std-dev component.
    max_group_std = max(group_stds) if group_stds else 0.0
    std_distortion = min(max_group_std / _PERSPECTIVE_ANGLE_MAX, 1.0)

    # Oblique line fraction component: many oblique lines suggest
    # perspective distortion or a rotated document.
    total = len(angles)
    oblique_fraction = len(oblique) / total if total > 0 else 0.0
    oblique_distortion = min(oblique_fraction / 0.5, 1.0)

    # Weighted combination: 60% within-group std, 40% oblique fraction.
    distortion = 0.6 * std_distortion + 0.4 * oblique_distortion
    return float(min(distortion, 1.0))


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def classify_document_source(image: np.ndarray) -> DocumentSourceResult:
    """Classify document capture method from a single page image.

    Module-level convenience wrapper around
    :meth:`DocumentSourceClassifier.classify`.

    Args:
        image: Input image (BGR, BGRA, or grayscale).

    Returns:
        DocumentSourceResult with all signal scores and final label.

    Raises:
        ValueError: If image is None, empty, or otherwise invalid.
    """
    return DocumentSourceClassifier().classify(image)
