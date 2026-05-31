"""Handwriting detection using a 4-signal classical ensemble.

Classical fallback for SigLIP 2 Group 4 handwriting head when confidence
drops below 0.5.  Combines four heuristic signals to estimate whether a
document page contains handwriting:

1. **Stroke width variance** (weight 0.30): Distance-transform analysis on
   binary image.  Handwriting exhibits HIGH variance in stroke widths
   (irregular pen strokes) vs. printed text (uniform typeset strokes).
2. **Baseline irregularity** (weight 0.25): Connected components are grouped
   into text rows by Y-centroid proximity.  Within each row the std-dev of
   centroids is computed.  Irregular baselines indicate handwriting.
3. **Inter-component spacing variance** (weight 0.20): Horizontal gaps
   between adjacent CCs within rows.  Handwriting has high gap variance
   compared to the even spacing of printed text.
4. **Component complexity / form factor** (weight 0.25): perimeter^2 / area
   for each CC.  Handwriting glyphs are geometrically complex (high form
   factor) relative to the simpler shapes of typeset glyphs.

The four normalised signals are fused via weighted average into a single
``handwriting_score`` (0-1).  Score > 0.4 indicates ``has_handwriting``.

Performance target: <15 ms per page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _get_filtered_components,
    _validate_and_preprocess,
)
from image_preprocessing_detector.schema import (
    HandwritingAssessment,
    HandwritingContentType,
    HandwritingLegibility,
    HandwritingPresence,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class HandwritingDetectionResult:
    """Result of handwriting detection analysis.

    Attributes:
        has_handwriting: Whether the page contains handwriting.
        handwriting_score: Aggregate handwriting likelihood (0-1).
        stroke_width_variance: Normalised stroke-width variance signal (0-1).
        baseline_irregularity: Normalised baseline irregularity signal (0-1).
        spacing_variance: Normalised inter-component spacing variance (0-1).
        form_factor_score: Normalised component complexity signal (0-1).
        confidence: Confidence in the detection result (0-1).
    """

    has_handwriting: bool
    handwriting_score: float
    stroke_width_variance: float
    baseline_irregularity: float
    spacing_variance: float
    form_factor_score: float
    confidence: float

    # ------------------------------------------------------------------
    # Schema bridge
    # ------------------------------------------------------------------

    def to_assessment(self) -> HandwritingAssessment:
        """Convert to Pydantic HandwritingAssessment for schema output.

        Maps the continuous ``handwriting_score`` to a discrete
        :class:`HandwritingPresence` enum value:

        - score < 0.2  -> NONE
        - score < 0.4  -> SPARSE
        - score < 0.7  -> MODERATE
        - score >= 0.7 -> DOMINANT

        Legibility and content-type cannot be determined from heuristics
        alone and are set to NOT_APPLICABLE.

        Returns:
            HandwritingAssessment: HandwritingAssessment with presence, scores, and confidence."""
        if self.handwriting_score < 0.2:
            presence = HandwritingPresence.NONE
        elif self.handwriting_score < 0.4:
            presence = HandwritingPresence.SPARSE
        elif self.handwriting_score < 0.7:
            presence = HandwritingPresence.MODERATE
        else:
            presence = HandwritingPresence.DOMINANT

        return HandwritingAssessment(
            presence=presence,
            legibility=HandwritingLegibility.NOT_APPLICABLE,
            content_type=HandwritingContentType.NOT_APPLICABLE,
            presence_score=self.handwriting_score,
            legibility_score=0.0,
            presence_confidence=self.confidence,
            legibility_confidence=0.0,
            content_type_confidence=0.0,
            detection_method="heuristic",
        )


# ---------------------------------------------------------------------------
# Default thresholds and weights
# ---------------------------------------------------------------------------

# Ensemble signal weights (must sum to 1.0)
_W_STROKE_WIDTH = 0.30
_W_BASELINE = 0.25
_W_SPACING = 0.20
_W_FORM_FACTOR = 0.25

# Score threshold for binary classification
_DEFAULT_THRESHOLD = 0.4

# Minimum number of connected components for reliable analysis
_MIN_COMPONENTS = 5

# Row grouping tolerance: CCs within this fraction of image height
# are considered to be on the same text row.
_ROW_TOLERANCE_FRAC = 0.025

# Normalisation caps (clamp raw values before mapping to [0,1])
_STROKE_CV_CAP = 1.0  # coefficient-of-variation cap
_BASELINE_STD_CAP = 0.035  # std-dev / image-height cap
_SPACING_CV_CAP = 1.5  # coefficient-of-variation cap
_FORM_FACTOR_CAP = 20.0  # median form-factor cap (circle=12.57)


# ---------------------------------------------------------------------------
# Private signal computation helpers
# ---------------------------------------------------------------------------


def _compute_stroke_width_variance(binary: np.ndarray) -> float:
    """Compute normalised stroke-width variance via distance transform.

    The distance transform of the binary (ink-foreground) image gives the
    distance to the nearest background pixel at every foreground pixel.
    Non-zero values approximate half the local stroke width.  The
    coefficient of variation (std / mean) of these values is a proxy for
    stroke-width irregularity.

    Args:
        binary (np.ndarray): Binary image (ink=255, background=0).

    Returns:
        float: Normalised stroke-width variance in [0, 1]."""
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    foreground = dist[dist > 0]

    if foreground.size < 10:
        return 0.0

    fg_float = foreground.astype(np.float64)
    mean_val = float(np.mean(fg_float))
    if mean_val < 1e-6:
        return 0.0

    coeff_var = float(np.std(fg_float)) / mean_val
    return float(np.clip(coeff_var / _STROKE_CV_CAP, 0.0, 1.0))


def _group_components_into_rows(
    components: list[dict[str, Any]],
    image_height: int,
) -> list[list[dict[str, Any]]]:
    """Group connected components into approximate text rows by Y-centroid.

    Components are sorted by Y-centroid and merged into rows using a
    tolerance proportional to image height.

    Args:
        components (list[dict[str, Any]]): Filtered CC dictionaries (must contain ``centroid``).
        image_height (int): Image height in pixels.

    Returns:
        list[list[dict[str, Any]]]: List of rows, where each row is a list of component dicts sorted
        by X-centroid."""
    if not components:
        return []

    tolerance = image_height * _ROW_TOLERANCE_FRAC
    sorted_comps = sorted(components, key=lambda c: c["centroid"][1])

    rows: list[list[dict[str, Any]]] = []
    current_row: list[dict[str, Any]] = [sorted_comps[0]]
    current_y = sorted_comps[0]["centroid"][1]

    for comp in sorted_comps[1:]:
        comp_y = comp["centroid"][1]
        if abs(comp_y - current_y) <= tolerance:
            current_row.append(comp)
        else:
            rows.append(sorted(current_row, key=lambda c: c["centroid"][0]))
            current_row = [comp]
            current_y = comp_y

    if current_row:
        rows.append(sorted(current_row, key=lambda c: c["centroid"][0]))

    return rows


def _compute_baseline_irregularity(
    rows: list[list[dict[str, Any]]],
    image_height: int,
) -> float:
    """Compute normalised baseline irregularity from row Y-centroid spread.

    For each row with >= 3 components the std-dev of Y-centroids is
    computed.  The mean std-dev across all qualifying rows, normalised by
    image height, serves as the irregularity signal.

    Args:
        rows (list[list[dict[str, Any]]]): Grouped component rows.
        image_height (int): Image height in pixels.

    Returns:
        float: Normalised baseline irregularity in [0, 1]."""
    if image_height < 1:
        return 0.0

    row_stds: list[float] = []
    for row in rows:
        if len(row) < 3:
            continue
        y_centroids = [c["centroid"][1] for c in row]
        row_stds.append(float(np.std(y_centroids)))

    if not row_stds:
        return 0.0

    mean_std = float(np.mean(row_stds)) / image_height
    return float(np.clip(mean_std / _BASELINE_STD_CAP, 0.0, 1.0))


def _compute_spacing_variance(rows: list[list[dict[str, Any]]]) -> float:
    """Compute normalised inter-component horizontal spacing variance.

    For each row, horizontal gaps between adjacent CCs (right edge to left
    edge) are collected.  The coefficient of variation of all gaps across
    all rows captures spacing irregularity.

    Args:
        rows (list[list[dict[str, Any]]]): Grouped component rows (each sorted by X-centroid).

    Returns:
        float: Normalised spacing variance in [0, 1]."""
    all_gaps: list[float] = []

    for row in rows:
        if len(row) < 2:
            continue
        for idx in range(len(row) - 1):
            x_curr, _, w_curr, _ = row[idx]["bbox"]
            x_next, _, _, _ = row[idx + 1]["bbox"]
            gap = float(x_next - (x_curr + w_curr))
            if gap > 0:
                all_gaps.append(gap)

    if len(all_gaps) < 3:
        return 0.0

    mean_gap = float(np.mean(all_gaps))
    if mean_gap < 1e-6:
        return 0.0

    coeff_var = float(np.std(all_gaps)) / mean_gap
    return float(np.clip(coeff_var / _SPACING_CV_CAP, 0.0, 1.0))


def _compute_form_factor_score(
    binary: np.ndarray,
) -> float:
    """Compute normalised form-factor (perimeter^2 / area) score.

    Handwriting glyphs are geometrically complex with high form-factor
    values, while printed glyphs tend toward simpler shapes (lower
    form-factor).  A circle has form-factor = 4*pi ~= 12.57.

    Args:
        binary (np.ndarray): Binary image.

    Returns:
        float: Normalised form-factor score in [0, 1]."""
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return 0.0

    form_factors: list[float] = []
    min_area = 20

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        perimeter = cv2.arcLength(contour, closed=True)
        if perimeter < 1e-6:
            continue
        form_factor = (perimeter * perimeter) / area
        form_factors.append(form_factor)

    if not form_factors:
        return 0.0

    median_ff = float(np.median(form_factors))
    # A circle has ff ~12.57; printed text typically 14-18; handwriting 20-40+
    # Subtract the circle baseline and normalise against the cap.
    baseline = 4.0 * np.pi  # ~12.57
    excess = max(0.0, median_ff - baseline)
    normalised = excess / (_FORM_FACTOR_CAP - baseline)
    return float(np.clip(normalised, 0.0, 1.0))


def _compute_confidence(
    handwriting_score: float,
    stroke_var: float,
    baseline_irreg: float,
    spacing_var: float,
    form_factor: float,
    num_components: int,
) -> float:
    """Derive detection confidence from signal agreement and evidence amount.

    Confidence increases when signals agree (all high or all low) and when
    the number of analysed components provides adequate statistical basis.

    Args:
        handwriting_score (float): Fused handwriting score (0-1).
        stroke_var (float): Normalised stroke-width variance (0-1).
        baseline_irreg (float): Normalised baseline irregularity (0-1).
        spacing_var (float): Normalised spacing variance (0-1).
        form_factor (float): Normalised form-factor score (0-1).
        num_components (int): Number of filtered connected components.

    Returns:
        float: Confidence value in [0, 1]."""
    signals = [stroke_var, baseline_irreg, spacing_var, form_factor]
    mean_sig = sum(signals) / len(signals)

    # Measure signal disagreement
    variance = sum((s - mean_sig) ** 2 for s in signals) / len(signals)
    std_dev = variance**0.5

    # High agreement -> higher confidence
    agreement_bonus = max(0.0, 0.15 - std_dev)
    base_confidence = 0.55 + agreement_bonus

    # More components -> more evidence -> higher confidence
    evidence_bonus = min(0.15, num_components / 200.0)

    # Extreme scores (near 0 or 1) are inherently more confident
    extremity_bonus = 0.10 * abs(handwriting_score - 0.5) * 2.0

    confidence = base_confidence + evidence_bonus + extremity_bonus
    return float(min(1.0, max(0.0, confidence)))


# ---------------------------------------------------------------------------
# HandwritingDetector class
# ---------------------------------------------------------------------------


class HandwritingDetector:
    """Detect handwriting using a 4-signal classical ensemble.

    Architecture role: Classical fallback for SigLIP 2 Group 4 handwriting
    head when ML confidence < 0.5.

    Signals:
        1. **Stroke width variance** -- distance-transform coefficient of
           variation captures irregular pen strokes.
        2. **Baseline irregularity** -- Y-centroid spread within text rows
           detects wavy or uneven writing lines.
        3. **Inter-component spacing variance** -- horizontal gap CV between
           adjacent CCs in each row.
        4. **Component complexity** -- median form-factor (perimeter^2/area)
           distinguishes complex handwriting glyphs from simpler typeset.

    Signals are fused via weighted average into ``handwriting_score`` (0-1).

    Args:
        threshold (float): Score threshold for binary has_handwriting decision (default: 0.4).
        min_components (int): Minimum CCs required for reliable analysis (default: 5).
    """

    def __init__(
        self,
        threshold: float = _DEFAULT_THRESHOLD,
        min_components: int = _MIN_COMPONENTS,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            msg = f"threshold must be between 0.0 and 1.0, got {threshold}"
            raise ValueError(msg)
        if min_components < 1:
            msg = f"min_components must be >= 1, got {min_components}"
            raise ValueError(msg)

        self.threshold = threshold
        self.min_components = min_components

        logger.info(
            "handwriting_detector_init",
            threshold=threshold,
            min_components=min_components,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> HandwritingDetectionResult:
        """Analyse an image for handwriting presence.

        Args:
            image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            HandwritingDetectionResult: HandwritingDetectionResult with score, per-signal breakdown,
            and confidence.

        Raises:
            ValueError: If the image is *None* or empty.
        """
        _gray, binary, height, width = _validate_and_preprocess(image)

        components = _get_filtered_components(
            binary, height, width, min_area=20, min_size=5
        )

        if len(components) < self.min_components:
            return _empty_result()

        # --- Signal 1: stroke width variance ---
        stroke_var = _compute_stroke_width_variance(binary)

        # --- Signal 2: baseline irregularity ---
        rows = _group_components_into_rows(components, height)
        baseline_irreg = _compute_baseline_irregularity(rows, height)

        # --- Signal 3: spacing variance ---
        spacing_var = _compute_spacing_variance(rows)

        # --- Signal 4: form-factor complexity ---
        form_factor = _compute_form_factor_score(binary)

        # --- Fuse signals ---
        handwriting_score = (
            _W_STROKE_WIDTH * stroke_var
            + _W_BASELINE * baseline_irreg
            + _W_SPACING * spacing_var
            + _W_FORM_FACTOR * form_factor
        )
        handwriting_score = float(np.clip(handwriting_score, 0.0, 1.0))

        has_handwriting = handwriting_score >= self.threshold

        confidence = _compute_confidence(
            handwriting_score,
            stroke_var,
            baseline_irreg,
            spacing_var,
            form_factor,
            len(components),
        )

        logger.debug(
            "handwriting_detection_result",
            has_handwriting=has_handwriting,
            handwriting_score=round(handwriting_score, 4),
            stroke_width_variance=round(stroke_var, 4),
            baseline_irregularity=round(baseline_irreg, 4),
            spacing_variance=round(spacing_var, 4),
            form_factor_score=round(form_factor, 4),
            confidence=round(confidence, 4),
            num_components=len(components),
        )

        return HandwritingDetectionResult(
            has_handwriting=has_handwriting,
            handwriting_score=round(handwriting_score, 4),
            stroke_width_variance=round(stroke_var, 4),
            baseline_irregularity=round(baseline_irreg, 4),
            spacing_variance=round(spacing_var, 4),
            form_factor_score=round(form_factor, 4),
            confidence=round(confidence, 4),
        )


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def _empty_result() -> HandwritingDetectionResult:
    """Return a zero-valued result for images with insufficient components."""
    return HandwritingDetectionResult(
        has_handwriting=False,
        handwriting_score=0.0,
        stroke_width_variance=0.0,
        baseline_irregularity=0.0,
        spacing_variance=0.0,
        form_factor_score=0.0,
        confidence=0.5,
    )


_default_detector: HandwritingDetector | None = None


def detect_handwriting(image: np.ndarray) -> HandwritingDetectionResult:
    """Convenience function to detect handwriting with default thresholds.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image (np.ndarray): Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        HandwritingDetectionResult: HandwritingDetectionResult with score, signal breakdown, and
        confidence.

    Raises:
        ValueError: If the image is *None* or empty.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = HandwritingDetector()
    return _default_detector.detect(image)
