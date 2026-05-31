"""Blank page detection using a 3-signal ensemble.

Combines pixel variance, Canny edge density, and content ratio to determine
whether a page is blank. Each signal is independently thresholded and then
fused into a single blankness score with an associated confidence value.

Performance target: <5ms per page, 95%+ accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _validate_and_preprocess,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass
class BlankPageResult:
    """Result of blank page detection.

    Attributes:
        is_blank (bool): Whether the page is classified as blank.
        blankness_score (float): Aggregate score from 0 (full content) to 1 (blank).
        content_ratio (float): Ratio of non-background pixels (0-1).
        edge_density (float): Canny edge pixel density (0-1).
        pixel_variance (float): Variance of grayscale pixel intensities.
        confidence (float): Confidence in the classification (0-1).
    """

    is_blank: bool
    blankness_score: float
    content_ratio: float
    edge_density: float
    pixel_variance: float
    confidence: float


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
_DEFAULT_VARIANCE_THRESHOLD = 100.0
_DEFAULT_EDGE_DENSITY_THRESHOLD = 0.01
_DEFAULT_CONTENT_RATIO_THRESHOLD = 0.02

# Weights for the blankness score (must sum to 1.0)
_W_VARIANCE = 0.4
_W_EDGE = 0.3
_W_CONTENT = 0.3


def _compute_variance_signal(pixel_variance: float, threshold: float) -> float:
    """Return a 0-1 blankness signal from pixel variance.

    A variance of 0 maps to 1.0 (blank); values >= threshold map to 0.0.
    """
    if pixel_variance >= threshold:
        return 0.0
    return 1.0 - (pixel_variance / threshold)


def _compute_edge_signal(edge_density: float, threshold: float) -> float:
    """Return a 0-1 blankness signal from edge density.

    Density of 0 maps to 1.0 (blank); values >= threshold map to 0.0.
    """
    if edge_density >= threshold:
        return 0.0
    return 1.0 - (edge_density / threshold)


def _compute_content_signal(content_ratio: float, threshold: float) -> float:
    """Return a 0-1 blankness signal from content ratio.

    Ratio of 0 maps to 1.0 (blank); values >= threshold map to 0.0.
    """
    if content_ratio >= threshold:
        return 0.0
    return 1.0 - (content_ratio / threshold)


class BlankPageDetector:
    """Detect blank pages using a 3-signal ensemble.

    Signals:
        1. **Pixel variance** -- low variance indicates uniform (blank) content.
        2. **Canny edge density** -- few edges indicate lack of content.
        3. **Content ratio** -- proportion of non-background pixels from
           Otsu-thresholded binary image.

    Each signal is independently mapped to a 0-1 blankness indicator, then
    fused via weighted average to produce the final ``blankness_score``.

    Args:
        variance_threshold (float): Pixel variance below which the image is likely
            blank (default: 100).
        edge_density_threshold (float): Edge density below which the image is
            likely blank (default: 0.01).
        content_ratio_threshold (float): Content ratio below which the image is
            likely blank (default: 0.02).
    """

    def __init__(
        self,
        variance_threshold: float = _DEFAULT_VARIANCE_THRESHOLD,
        edge_density_threshold: float = _DEFAULT_EDGE_DENSITY_THRESHOLD,
        content_ratio_threshold: float = _DEFAULT_CONTENT_RATIO_THRESHOLD,
    ) -> None:
        self.variance_threshold = variance_threshold
        self.edge_density_threshold = edge_density_threshold
        self.content_ratio_threshold = content_ratio_threshold

        logger.info(
            "blank_page_detector_init",
            variance_threshold=variance_threshold,
            edge_density_threshold=edge_density_threshold,
            content_ratio_threshold=content_ratio_threshold,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> BlankPageResult:
        """Analyse an image and determine whether it is blank.

        Args:
            image: Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            BlankPageResult with classification, score, and raw signals.
        """
        gray, binary, height, width = _validate_and_preprocess(image)
        total_pixels = height * width

        # --- Signal 1: pixel variance ---
        pixel_variance = float(np.var(gray))

        # --- Signal 2: Canny edge density ---
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges) / total_pixels)

        # --- Signal 3: content ratio (from Otsu binary) ---
        # When the image is near-uniform (very low variance), Otsu
        # thresholding is unreliable -- a solid black page binarises as
        # all-white foreground.  Fall back to 0 in that case.
        if pixel_variance < 1.0:
            content_ratio = 0.0
        else:
            content_ratio = float(np.count_nonzero(binary) / total_pixels)

        # --- Fuse signals ---
        var_signal = _compute_variance_signal(pixel_variance, self.variance_threshold)
        edge_signal = _compute_edge_signal(edge_density, self.edge_density_threshold)
        content_signal = _compute_content_signal(
            content_ratio, self.content_ratio_threshold
        )

        blankness_score = (
            _W_VARIANCE * var_signal
            + _W_EDGE * edge_signal
            + _W_CONTENT * content_signal
        )

        # Count how many signals agree on "blank"
        blank_votes = sum(
            [
                pixel_variance < self.variance_threshold,
                edge_density < self.edge_density_threshold,
                content_ratio < self.content_ratio_threshold,
            ]
        )

        is_blank = blank_votes >= 2
        confidence = self._compute_confidence(blank_votes, blankness_score)

        logger.debug(
            "blank_page_result",
            is_blank=is_blank,
            blankness_score=round(blankness_score, 4),
            pixel_variance=round(pixel_variance, 2),
            edge_density=round(edge_density, 6),
            content_ratio=round(content_ratio, 6),
            confidence=round(confidence, 4),
        )

        return BlankPageResult(
            is_blank=is_blank,
            blankness_score=round(blankness_score, 4),
            content_ratio=round(content_ratio, 6),
            edge_density=round(edge_density, 6),
            pixel_variance=round(pixel_variance, 2),
            confidence=round(confidence, 4),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(blank_votes: int, blankness_score: float) -> float:
        """Derive a confidence value from vote agreement and score magnitude.

        Three agreeing signals yield the highest confidence.  When signals
        disagree the confidence is reduced, reflecting ambiguity.

        Args:
            blank_votes: Number of signals that voted "blank" (0-3).
            blankness_score: Fused blankness score (0-1).

        Returns:
            Confidence value between 0 and 1.
        """
        if blank_votes == 3:
            return min(1.0, 0.85 + 0.15 * blankness_score)
        if blank_votes == 0:
            return min(1.0, 0.85 + 0.15 * (1.0 - blankness_score))
        # 1 or 2 votes -- moderate confidence
        return 0.5 + 0.3 * abs(blankness_score - 0.5)


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_default_detector: BlankPageDetector | None = None


def detect_blank_page(image: np.ndarray) -> BlankPageResult:
    """Convenience function to detect a blank page with default thresholds.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image: Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        BlankPageResult with classification, score, and raw signals.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = BlankPageDetector()
    return _default_detector.detect(image)
