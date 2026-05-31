"""Shadow detection using local variance, gradient consistency, and area ratio.

Detects shadow artifacts in document images by combining three signals:
1. **Local variance analysis**: Grid-based mean intensity comparison to identify
   cells significantly darker than the overall image mean.
2. **Gradient direction consistency**: Sobel-based gradient analysis detects
   consistent dark-to-light transitions characteristic of shadow boundaries.
3. **Shadow ratio**: Ratio of shadow-region pixels to total image area.

The three signals are fused via weighted average into a single ``shadow_score``
(0-1), which is mapped to a categorical severity label.

Performance target: <10ms per page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _validate_and_preprocess,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShadowDetectionResult:
    """Result of shadow detection analysis.

    Attributes:
        has_shadows: Whether the page has detectable shadow artifacts.
        shadow_score: Aggregate shadow severity from 0 (none) to 1 (severe).
        shadow_severity: Categorical severity label for display.
        shadow_ratio: Ratio of shadow-region area to total image area (0-1).
        confidence: Confidence in the detection result (0-1).
    """

    has_shadows: bool
    shadow_score: float
    shadow_severity: Literal["none", "mild", "moderate", "severe"]
    shadow_ratio: float
    confidence: float


# ---------------------------------------------------------------------------
# Default thresholds and weights
# ---------------------------------------------------------------------------

# Grid-based local variance analysis
_DEFAULT_GRID_SIZE = 8
_DEFAULT_SHADOW_THRESHOLD = 0.6

# A cell is a shadow candidate when its mean intensity is this fraction
# below the global mean.  0.6 means the cell must be at least 40% darker.
_CELL_DARKNESS_FRACTION = 0.6

# Gradient direction consistency: minimum fraction of gradient magnitudes
# that share a dominant direction bin for shadow-boundary detection.
_GRADIENT_CONSISTENCY_BASELINE = 0.15

# Signal fusion weights (must sum to 1.0)
_W_LOCAL_VARIANCE = 0.40
_W_GRADIENT = 0.25
_W_SHADOW_RATIO = 0.35

# Severity thresholds
_SEVERITY_MILD = 0.1
_SEVERITY_MODERATE = 0.3
_SEVERITY_SEVERE = 0.6

# Number of direction bins for gradient histogram
_NUM_DIRECTION_BINS = 8


# ---------------------------------------------------------------------------
# Private signal computation helpers
# ---------------------------------------------------------------------------


def _compute_local_variance_signal(
    gray: np.ndarray,
    grid_size: int,
    shadow_threshold: float,
) -> tuple[float, float]:
    """Compute the local-variance shadow signal and raw shadow ratio.

    Divides the image into *grid_size x grid_size* cells and compares each
    cell's mean intensity against the overall image mean.  Cells whose mean
    is below ``shadow_threshold * global_mean`` are shadow candidates.

    Args:
        gray (np.ndarray): Grayscale image (uint8).
        grid_size (int): Number of grid divisions per axis.
        shadow_threshold (float): Fraction of global mean below which a cell is considered a shadow candidate.

    Returns:
        tuple[float, float]: Tuple of (local_variance_signal, shadow_ratio) both in [0, 1]."""
    height, width = gray.shape[:2]
    global_mean = float(np.mean(gray))

    # Avoid division-by-zero on all-black images
    if global_mean < 1.0:
        return 0.0, 0.0

    cell_h = max(height // grid_size, 1)
    cell_w = max(width // grid_size, 1)

    shadow_cells = 0
    total_cells = 0
    darkness_accumulator = 0.0

    threshold_intensity = global_mean * shadow_threshold

    for row in range(grid_size):
        y_start = row * cell_h
        y_end = min(y_start + cell_h, height)
        for col in range(grid_size):
            x_start = col * cell_w
            x_end = min(x_start + cell_w, width)

            cell = gray[y_start:y_end, x_start:x_end]
            if cell.size == 0:
                continue

            total_cells += 1
            cell_mean = float(np.mean(cell))

            if cell_mean < threshold_intensity:
                shadow_cells += 1
                # How far below the threshold (normalised)
                darkness_accumulator += 1.0 - (cell_mean / global_mean)

    if total_cells == 0:
        return 0.0, 0.0

    shadow_ratio = shadow_cells / total_cells
    # Scale the average darkness of shadow cells into [0, 1]
    avg_darkness = darkness_accumulator / total_cells
    local_signal = min(1.0, avg_darkness * 2.5)

    return local_signal, shadow_ratio


def _compute_gradient_consistency_signal(gray: np.ndarray) -> float:
    """Compute a 0-1 signal from Sobel gradient direction consistency.

    Shadow boundaries typically exhibit consistent dark-to-light gradient
    direction.  We bin gradient directions into *_NUM_DIRECTION_BINS* buckets
    and measure how dominant the peak bin is relative to a uniform baseline.

    Args:
        gray (np.ndarray): Grayscale image (uint8).

    Returns:
        float: Gradient consistency signal in [0, 1]."""
    # Sobel gradients
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    direction = np.arctan2(grad_y, grad_x)  # -pi .. pi

    # Only consider pixels with meaningful gradient magnitude
    mag_threshold = float(np.percentile(magnitude, 75))
    if mag_threshold < 1.0:
        return 0.0

    strong_mask = magnitude >= mag_threshold
    strong_dirs = direction[strong_mask]

    if strong_dirs.size == 0:
        return 0.0

    # Bin directions into _NUM_DIRECTION_BINS buckets
    bin_edges = np.linspace(-np.pi, np.pi, _NUM_DIRECTION_BINS + 1)
    hist, _ = np.histogram(strong_dirs, bins=bin_edges)

    total = hist.sum()
    if total == 0:
        return 0.0

    peak_fraction = float(hist.max()) / total
    # Baseline for uniform distribution
    uniform_fraction = 1.0 / _NUM_DIRECTION_BINS

    # Normalise excess dominance above the uniform baseline into [0, 1]
    consistency = (peak_fraction - uniform_fraction) / (1.0 - uniform_fraction)
    return float(np.clip(consistency, 0.0, 1.0))


def _score_to_severity(
    shadow_score: float,
) -> Literal["none", "mild", "moderate", "severe"]:
    """Map a continuous shadow score to a categorical severity label.

    Args:
        shadow_score (float): Aggregate shadow score in [0, 1].

    Returns:
        Literal['none', 'mild', 'moderate', 'severe']: Severity label string."""
    if shadow_score >= _SEVERITY_SEVERE:
        return "severe"
    if shadow_score >= _SEVERITY_MODERATE:
        return "moderate"
    if shadow_score >= _SEVERITY_MILD:
        return "mild"
    return "none"


def _compute_confidence(
    shadow_score: float,
    shadow_ratio: float,
    gradient_signal: float,
) -> float:
    """Derive detection confidence from signal agreement.

    When multiple signals point in the same direction (all high or all low)
    confidence is elevated.  Disagreement reduces confidence.

    Args:
        shadow_score (float): Fused shadow score (0-1).
        shadow_ratio (float): Raw shadow-area ratio (0-1).
        gradient_signal (float): Gradient consistency signal (0-1).

    Returns:
        float: Confidence value in [0, 1]."""
    signals = [shadow_score, shadow_ratio, gradient_signal]
    mean_signal = sum(signals) / len(signals)

    # Standard deviation of signals measures disagreement
    variance = sum((s - mean_signal) ** 2 for s in signals) / len(signals)
    std_dev = variance**0.5

    # High agreement -> high confidence; high disagreement -> lower confidence
    agreement_bonus = max(0.0, 0.2 - std_dev)
    base_confidence = 0.65 + agreement_bonus

    # Extreme scores (very high or very low) are inherently more confident
    extremity_bonus = 0.15 * abs(shadow_score - 0.5) * 2.0
    confidence = base_confidence + extremity_bonus

    return float(min(1.0, max(0.0, confidence)))


# ---------------------------------------------------------------------------
# ShadowDetector class
# ---------------------------------------------------------------------------


class ShadowDetector:
    """Detect shadow artifacts using a 3-signal ensemble.

    Signals:
        1. **Local variance** -- grid-based intensity analysis identifies
           cells significantly darker than the global mean.
        2. **Gradient consistency** -- Sobel gradient direction histogram
           detects dominant dark-to-light transitions at shadow boundaries.
        3. **Shadow ratio** -- fraction of grid cells classified as shadow.

    Each signal is fused via weighted average to produce the final
    ``shadow_score``.
    """

    def __init__(
        self,
        grid_size: int = _DEFAULT_GRID_SIZE,
        shadow_threshold: float = _DEFAULT_SHADOW_THRESHOLD,
    ) -> None:
        """Initialise shadow detector.

        Args:
            grid_size (int): Number of grid divisions per axis for local variance analysis (default: 8, yielding 64 cells).
            shadow_threshold (float): Fraction of global mean intensity below which a grid cell is flagged as a shadow candidate (default: 0.6)."""
        self.grid_size = grid_size
        self.shadow_threshold = shadow_threshold

        logger.info(
            "shadow_detector_init",
            grid_size=grid_size,
            shadow_threshold=shadow_threshold,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> ShadowDetectionResult:
        """Analyse an image for shadow artifacts.

        Args:
            image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            ShadowDetectionResult: ShadowDetectionResult with score, severity, ratio, and confidence.

        Raises:
            ValueError: If the image is *None* or empty.
        """
        gray, _binary, _height, _width = _validate_and_preprocess(image)

        # --- Signal 1: local variance + shadow ratio ---
        local_signal, shadow_ratio = _compute_local_variance_signal(
            gray, self.grid_size, self.shadow_threshold
        )

        # --- Signal 2: gradient direction consistency ---
        gradient_signal = _compute_gradient_consistency_signal(gray)

        # --- Signal 3: shadow ratio contributes directly ---
        ratio_signal = min(1.0, shadow_ratio * 2.5)

        # --- Fuse signals ---
        shadow_score = (
            _W_LOCAL_VARIANCE * local_signal
            + _W_GRADIENT * gradient_signal
            + _W_SHADOW_RATIO * ratio_signal
        )
        shadow_score = float(np.clip(shadow_score, 0.0, 1.0))

        severity = _score_to_severity(shadow_score)
        has_shadows = severity != "none"
        confidence = _compute_confidence(shadow_score, shadow_ratio, gradient_signal)

        logger.debug(
            "shadow_detection_result",
            has_shadows=has_shadows,
            shadow_score=round(shadow_score, 4),
            shadow_severity=severity,
            shadow_ratio=round(shadow_ratio, 4),
            local_signal=round(local_signal, 4),
            gradient_signal=round(gradient_signal, 4),
            confidence=round(confidence, 4),
        )

        return ShadowDetectionResult(
            has_shadows=has_shadows,
            shadow_score=round(shadow_score, 4),
            shadow_severity=severity,
            shadow_ratio=round(shadow_ratio, 4),
            confidence=round(confidence, 4),
        )


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_default_detector: ShadowDetector | None = None


def detect_shadows(image: np.ndarray) -> ShadowDetectionResult:
    """Convenience function to detect shadows with default thresholds.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        ShadowDetectionResult: ShadowDetectionResult with score, severity, ratio, and confidence.

    Raises:
        ValueError: If the image is *None* or empty.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = ShadowDetector()
    return _default_detector.detect(image)
