"""Code/monospace text detection using a 3-signal ensemble.

Combines character-width uniformity, indentation analysis, and line-height
uniformity to determine whether a page contains code or monospace text.

Each signal is independently scored (0-1) and fused via weighted average
into a single confidence value.

Performance target: <10ms per page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _get_filtered_components,
    _validate_and_preprocess,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CodeDetectionResult:
    """Result of code/monospace text detection.

    Attributes:
        has_code: Whether the page likely contains code blocks.
        code_confidence: Overall confidence in code detection (0-1).
        width_uniformity: Character-width uniformity score
            (0-1, 1 = perfectly uniform / monospace-like).
        indentation_levels: Number of distinct indentation levels found.
        line_height_uniformity: Line-spacing uniformity score
            (0-1, 1 = perfectly uniform).
        confidence: Alias for code_confidence (for API consistency).
    """

    has_code: bool
    code_confidence: float
    width_uniformity: float
    indentation_levels: int
    line_height_uniformity: float
    confidence: float


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
_DEFAULT_WIDTH_CV_THRESHOLD = 0.3
_DEFAULT_MIN_INDENT_LEVELS = 3
_DEFAULT_LINE_CV_THRESHOLD = 0.25
_DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_MIN_COMPONENTS = 15

# Weights for the ensemble (must sum to 1.0)
_W_WIDTH = 0.4
_W_INDENT = 0.3
_W_LINE = 0.3


# ---------------------------------------------------------------------------
# Signal computation helpers
# ---------------------------------------------------------------------------


def _compute_width_uniformity(components: list[dict[str, Any]]) -> float:
    """Compute character-width uniformity score.

    In monospace/code text, connected components (characters) have very
    uniform widths.  The coefficient of variation (CV = std/mean) is a
    robust measure: lower CV means more uniform.

    Args:
        components (list[dict[str, Any]]): Filtered connected components from the binary image.

    Returns:
        float: Score in [0, 1] where 1 means perfectly uniform (monospace-like)."""
    widths = np.array([c["bbox"][2] for c in components], dtype=np.float64)
    mean_w = float(np.mean(widths))
    if mean_w <= 0:
        return 0.0

    cv = float(np.std(widths) / mean_w)

    # Map CV to a 0-1 uniformity score.
    # CV=0 -> 1.0, CV >= threshold -> 0.0
    if cv >= _DEFAULT_WIDTH_CV_THRESHOLD:
        return 0.0
    return 1.0 - (cv / _DEFAULT_WIDTH_CV_THRESHOLD)


def _compute_indentation_score(
    components: list[dict[str, Any]],
) -> tuple[float, int]:
    """Analyse left-edge x-coordinates for structured indentation.

    Code typically has multiple distinct left-margin levels (e.g. 0, 4, 8,
    12 spaces).  We cluster component left-edge x-coordinates into bins and
    count the number of distinct levels.

    Args:
        components (list[dict[str, Any]]): Filtered connected components from the binary image.

    Returns:
        tuple[float, int]: Tuple of (indentation_score 0-1, indentation_levels count)."""
    left_edges = np.array([c["bbox"][0] for c in components], dtype=np.float64)

    if len(left_edges) == 0:
        return 0.0, 0

    # Quantise left-edges into bins of ~10 pixels to cluster indentation
    # levels.  The bin width approximates a character width at typical DPIs.
    bin_width = max(10, int(np.median([c["bbox"][2] for c in components])))
    quantised = (left_edges / bin_width).astype(int)
    unique_levels = len(np.unique(quantised))

    # Score: 0 levels -> 0.0; >= MIN_INDENT_LEVELS -> 1.0
    if unique_levels >= _DEFAULT_MIN_INDENT_LEVELS:
        score = min(1.0, unique_levels / (_DEFAULT_MIN_INDENT_LEVELS + 2))
    else:
        score = unique_levels / _DEFAULT_MIN_INDENT_LEVELS

    return float(score), unique_levels


def _compute_line_height_uniformity(
    components: list[dict[str, Any]],
) -> float:
    """Compute line-spacing uniformity score.

    Code has very regular line spacing.  Group components by Y-centroid
    into approximate rows, compute inter-row distances, then measure their
    coefficient of variation.

    Args:
        components (list[dict[str, Any]]): Filtered connected components from the binary image.

    Returns:
        float: Score in [0, 1] where 1 means perfectly uniform line spacing."""
    y_centroids = np.array([c["centroid"][1] for c in components], dtype=np.float64)

    if len(y_centroids) < 3:
        return 0.0

    # Sort and cluster centroids into rows using a gap-based heuristic.
    # Components within `row_tolerance` pixels are considered the same row.
    sorted_y = np.sort(y_centroids)
    median_height = float(np.median([c["bbox"][3] for c in components]))
    row_tolerance = max(5.0, median_height * 0.5)

    row_centres: list[float] = []
    current_cluster: list[float] = [float(sorted_y[0])]

    for y_val in sorted_y[1:]:
        if float(y_val) - current_cluster[-1] < row_tolerance:
            current_cluster.append(float(y_val))
        else:
            row_centres.append(float(np.mean(current_cluster)))
            current_cluster = [float(y_val)]

    # Flush the last cluster
    if current_cluster:
        row_centres.append(float(np.mean(current_cluster)))

    if len(row_centres) < 3:
        return 0.0

    # Compute inter-row spacings
    spacings = np.diff(row_centres)
    mean_spacing = float(np.mean(spacings))
    if mean_spacing <= 0:
        return 0.0

    cv = float(np.std(spacings) / mean_spacing)

    # Map CV to a 0-1 uniformity score.
    if cv >= _DEFAULT_LINE_CV_THRESHOLD:
        return 0.0
    return 1.0 - (cv / _DEFAULT_LINE_CV_THRESHOLD)


# ---------------------------------------------------------------------------
# CodeDetector class
# ---------------------------------------------------------------------------


class CodeDetector:
    """Detect code/monospace text using a 3-signal ensemble.

    Signals:
        1. **Character-width uniformity** -- low CV of component widths
           indicates monospace font (code).
        2. **Indentation analysis** -- multiple distinct left-margin levels
           indicate structured code indentation.
        3. **Line-height uniformity** -- low CV of inter-row spacing
           indicates regular line spacing (code).

    Each signal is independently mapped to a 0-1 score, then fused via
    weighted average to produce the final ``code_confidence``.
    """

    def __init__(
        self,
        confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
        min_components: int = _MIN_COMPONENTS,
    ) -> None:
        """Initialise code detector.

        Args:
            confidence_threshold (float): Confidence above which ``has_code`` is True (default: 0.5).
            min_components (int): Minimum connected components required for analysis (default: 15)."""
        self.confidence_threshold = confidence_threshold
        self.min_components = min_components

        logger.info(
            "code_detector_init",
            confidence_threshold=confidence_threshold,
            min_components=min_components,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> CodeDetectionResult:
        """Analyse an image for code/monospace text content.

        Args:
            image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            CodeDetectionResult: CodeDetectionResult with classification and signal scores.

        Raises:
            ValueError: If the image is *None* or empty.
        """
        _gray, binary, height, width = _validate_and_preprocess(image)

        components = _get_filtered_components(
            binary, height, width, min_area=20, min_size=5
        )

        if len(components) < self.min_components:
            return self._empty_result()

        # --- Signal 1: character-width uniformity ---
        width_uniformity = _compute_width_uniformity(components)

        # --- Signal 2: indentation analysis ---
        indent_score, indent_levels = _compute_indentation_score(components)

        # --- Signal 3: line-height uniformity ---
        line_uniformity = _compute_line_height_uniformity(components)

        # --- Fuse signals ---
        confidence = (
            _W_WIDTH * width_uniformity
            + _W_INDENT * indent_score
            + _W_LINE * line_uniformity
        )
        confidence = max(0.0, min(1.0, confidence))
        has_code = confidence > self.confidence_threshold

        logger.debug(
            "code_detection_result",
            has_code=has_code,
            confidence=round(confidence, 4),
            width_uniformity=round(width_uniformity, 4),
            indentation_levels=indent_levels,
            line_height_uniformity=round(line_uniformity, 4),
            num_components=len(components),
        )

        return CodeDetectionResult(
            has_code=has_code,
            code_confidence=round(confidence, 4),
            width_uniformity=round(width_uniformity, 4),
            indentation_levels=indent_levels,
            line_height_uniformity=round(line_uniformity, 4),
            confidence=round(confidence, 4),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_result() -> CodeDetectionResult:
        """Return a no-code result for edge cases (too few components)."""
        return CodeDetectionResult(
            has_code=False,
            code_confidence=0.0,
            width_uniformity=0.0,
            indentation_levels=0,
            line_height_uniformity=0.0,
            confidence=0.0,
        )


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_default_detector: CodeDetector | None = None


def detect_code(image: np.ndarray) -> CodeDetectionResult:
    """Convenience function to detect code with default thresholds.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        CodeDetectionResult: CodeDetectionResult with classification and signal scores.

    Raises:
        ValueError: If the image is *None* or empty.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = CodeDetector()
    return _default_detector.detect(image)
