"""Heuristic script family detection using a 4-signal ensemble.

Classifies document pages into broad script families (CJK, Latin, Arabic,
Devanagari, Unknown) and maps each family to the most likely ISO 15924 code.

Signals:
1. **Character aspect ratio** (weight 0.30): CJK characters are roughly
   square (~0.8-1.2), Latin taller than wide (~1.5-2.5), Arabic wider
   (~0.3-0.8).
2. **Stroke density** (weight 0.25): CJK has high stroke density per
   bounding box (~0.4-0.6), Latin moderate (~0.2-0.4), Arabic lower.
3. **CC complexity** (weight 0.20): Perimeter^2 / area form factor.
   CJK highest, Arabic moderate, Latin lower.
4. **RTL flow detection** (weight 0.25): CC centroid progression
   right-to-left within text rows suggests Arabic/Hebrew.

This detector establishes a baseline for Stream 3 benchmarking and provides
Tier 3 enrichment.  OpenLID is the fallback for the SigLIP 2 script head,
NOT this heuristic.

Performance target: <15ms per page.
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
from image_preprocessing_detector.schema import ScriptDetectionResult
from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# Script family definitions and mapping
# ============================================================================

# Script families detected by the heuristic ensemble
_SCRIPT_FAMILIES = ("cjk", "latin", "arabic", "devanagari", "unknown")

# Map script families to default ISO 15924 codes
_FAMILY_TO_ISO: dict[str, str] = {
    "cjk": ISO15924Script.HANS.value,  # "Hans"
    "latin": ISO15924Script.LATN.value,  # "Latn"
    "arabic": ISO15924Script.ARAB.value,  # "Arab"
    "devanagari": ISO15924Script.DEVA.value,  # "Deva"
    "unknown": ISO15924Script.ZZZZ.value,  # "Zzzz"
}


# ============================================================================
# Signal weights (must sum to 1.0)
# ============================================================================

_W_ASPECT_RATIO = 0.30
_W_STROKE_DENSITY = 0.25
_W_CC_COMPLEXITY = 0.20
_W_RTL_FLOW = 0.25

# Default minimum connected components for reliable detection
_DEFAULT_MIN_COMPONENTS = 10


# ============================================================================
# Score profile dataclass
# ============================================================================


@dataclass(frozen=True)
class _ScriptScoreProfile:
    """Ideal signal values for a script family.

    Attributes:
        aspect_ratio_center: Expected mean aspect ratio.
        aspect_ratio_range: Acceptable (low, high) bounds.
        density_center: Expected mean stroke density.
        density_range: Acceptable (low, high) bounds.
        complexity_center: Expected mean CC complexity.
        complexity_range: Acceptable (low, high) bounds.
        expects_rtl: Whether the family is right-to-left.
    """

    aspect_ratio_center: float
    aspect_ratio_range: tuple[float, float]
    density_center: float
    density_range: tuple[float, float]
    complexity_center: float
    complexity_range: tuple[float, float]
    expects_rtl: bool


# Empirical profiles for each script family
_PROFILES: dict[str, _ScriptScoreProfile] = {
    "cjk": _ScriptScoreProfile(
        aspect_ratio_center=1.0,
        aspect_ratio_range=(0.7, 1.3),
        density_center=0.50,
        density_range=(0.35, 0.70),
        complexity_center=25.0,
        complexity_range=(15.0, 50.0),
        expects_rtl=False,
    ),
    "latin": _ScriptScoreProfile(
        aspect_ratio_center=0.6,
        aspect_ratio_range=(0.3, 1.0),
        density_center=0.30,
        density_range=(0.15, 0.45),
        complexity_center=14.0,
        complexity_range=(8.0, 22.0),
        expects_rtl=False,
    ),
    "arabic": _ScriptScoreProfile(
        aspect_ratio_center=1.8,
        aspect_ratio_range=(1.0, 3.5),
        density_center=0.25,
        density_range=(0.10, 0.40),
        complexity_center=18.0,
        complexity_range=(10.0, 30.0),
        expects_rtl=True,
    ),
    "devanagari": _ScriptScoreProfile(
        aspect_ratio_center=0.8,
        aspect_ratio_range=(0.5, 1.2),
        density_center=0.40,
        density_range=(0.25, 0.55),
        complexity_center=22.0,
        complexity_range=(14.0, 35.0),
        expects_rtl=False,
    ),
}


# ============================================================================
# Internal signal computation helpers
# ============================================================================


def _compute_aspect_ratio_signal(
    components: list[dict[str, Any]],
) -> float:
    """Compute mean aspect ratio (w/h) of filtered connected components.

    Args:
        components: List of CC dicts from ``_get_filtered_components``.

    Returns:
        Mean aspect ratio as a float.
    """
    ratios = [c["aspect_ratio"] for c in components]
    return float(np.mean(ratios))


def _compute_stroke_density_signal(
    components: list[dict[str, Any]],
) -> float:
    """Compute mean stroke density (fill ratio) of bounding boxes.

    Args:
        components: List of CC dicts from ``_get_filtered_components``.

    Returns:
        Mean density in [0, 1].
    """
    densities = [c["density"] for c in components]
    return float(np.mean(densities))


def _compute_cc_complexity_signal(
    binary: np.ndarray,
) -> float:
    """Compute mean CC complexity using perimeter^2 / area form factor.

    Higher values indicate more complex glyphs (e.g., CJK characters
    have many strokes yielding large perimeters relative to area).

    Args:
        binary: Binary (thresholded) image.

    Returns:
        Mean form factor (perimeter^2 / area).
    """
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return 0.0

    form_factors: list[float] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 20:
            continue
        perimeter = cv2.arcLength(contour, closed=True)
        if perimeter < 1.0:
            continue
        form_factor = (perimeter * perimeter) / area
        form_factors.append(form_factor)

    if not form_factors:
        return 0.0

    return float(np.mean(form_factors))


def _compute_rtl_flow_signal(
    components: list[dict[str, Any]],
    image_height: int,
) -> float:
    """Detect right-to-left reading flow from CC centroid progression.

    Groups components into approximate text rows by y-coordinate, then
    checks whether centroids within each row generally progress from
    right to left.

    Args:
        components: List of CC dicts from ``_get_filtered_components``.
        image_height: Height of the image in pixels.

    Returns:
        RTL score in [0, 1].  Values > 0.5 suggest RTL text flow.
    """
    if len(components) < 3:
        return 0.0

    # Sort by y-centroid to group into rows
    sorted_comps = sorted(components, key=lambda c: c["centroid"][1])

    # Cluster into rows using a gap threshold proportional to image height
    row_gap = max(image_height * 0.03, 10)
    rows: list[list[dict[str, Any]]] = []
    current_row: list[dict[str, Any]] = [sorted_comps[0]]

    for comp in sorted_comps[1:]:
        if comp["centroid"][1] - current_row[-1]["centroid"][1] > row_gap:
            if len(current_row) >= 3:
                rows.append(current_row)
            current_row = [comp]
        else:
            current_row.append(comp)

    if len(current_row) >= 3:
        rows.append(current_row)

    if not rows:
        return 0.0

    # Check if centroids in each row are predominantly ordered
    # right-to-left (descending x), indicating RTL text flow.
    rtl_row_count = 0
    for row in rows:
        x_coords = [c["centroid"][0] for c in row]
        # Count pairwise descending pairs
        descending = sum(
            1 for i in range(len(x_coords) - 1) if x_coords[i] > x_coords[i + 1]
        )
        ascending = len(x_coords) - 1 - descending
        if descending > ascending:
            rtl_row_count += 1

    return rtl_row_count / len(rows) if rows else 0.0


def _score_family(
    mean_aspect: float,
    mean_density: float,
    mean_complexity: float,
    rtl_score: float,
    profile: _ScriptScoreProfile,
) -> float:
    """Score how well observed signals match a script family profile.

    Each signal contributes a 0-1 match score based on Gaussian-like
    proximity to the profile centre, weighted by the signal weights.

    Args:
        mean_aspect: Observed mean aspect ratio.
        mean_density: Observed mean stroke density.
        mean_complexity: Observed mean CC complexity.
        rtl_score: Observed RTL flow score (0-1).
        profile: Reference profile for a script family.

    Returns:
        Weighted match score in [0, 1].
    """
    # Aspect ratio match
    ar_low, ar_high = profile.aspect_ratio_range
    ar_span = ar_high - ar_low
    ar_match = max(
        0.0,
        1.0
        - abs(mean_aspect - profile.aspect_ratio_center)
        / (ar_span if ar_span > 0 else 1.0),
    )

    # Stroke density match
    sd_low, sd_high = profile.density_range
    sd_span = sd_high - sd_low
    sd_match = max(
        0.0,
        1.0
        - abs(mean_density - profile.density_center)
        / (sd_span if sd_span > 0 else 1.0),
    )

    # CC complexity match
    cc_low, cc_high = profile.complexity_range
    cc_span = cc_high - cc_low
    cc_match = max(
        0.0,
        1.0
        - abs(mean_complexity - profile.complexity_center)
        / (cc_span if cc_span > 0 else 1.0),
    )

    # RTL flow match
    rtl_match = rtl_score if profile.expects_rtl else 1.0 - rtl_score

    return (
        _W_ASPECT_RATIO * ar_match
        + _W_STROKE_DENSITY * sd_match
        + _W_CC_COMPLEXITY * cc_match
        + _W_RTL_FLOW * rtl_match
    )


def _build_probabilities(
    family_scores: dict[str, float],
) -> dict[str, float]:
    """Normalise family scores into ISO 15924 probability distribution.

    Args:
        family_scores: Raw match scores keyed by family name.

    Returns:
        dict mapping ISO 15924 codes to probabilities summing to ~1.0.
    """
    total = sum(family_scores.values())
    if total < 1e-9:
        return {_FAMILY_TO_ISO["unknown"]: 1.0}

    probabilities: dict[str, float] = {}
    for family, score in family_scores.items():
        iso_code = _FAMILY_TO_ISO[family]
        probabilities[iso_code] = round(score / total, 4)

    return probabilities


def _compute_confidence(
    best_score: float,
    second_score: float,
    num_components: int,
    min_components: int,
) -> float:
    """Derive detection confidence from score separation and data quantity.

    Args:
        best_score: Highest family match score.
        second_score: Second-highest family match score.
        num_components: Number of connected components used.
        min_components: Minimum components for full confidence.

    Returns:
        Confidence value in [0, 1].
    """
    # Score separation: wider gap = higher confidence
    separation = best_score - second_score if best_score > 0 else 0.0
    separation_factor = min(1.0, separation / 0.3)

    # Data quantity factor
    quantity_factor = min(1.0, num_components / (min_components * 3))

    # Base confidence for heuristic method capped at 0.7
    base = 0.35
    confidence = base + 0.20 * separation_factor + 0.15 * quantity_factor

    return float(min(1.0, max(0.0, round(confidence, 4))))


# ============================================================================
# ScriptDetectorHeuristic class
# ============================================================================


class ScriptDetectorHeuristic:
    """Heuristic script family detection using a 4-signal ensemble.

    Signals:
        1. **Aspect ratio** -- mean w/h ratio of connected components.
        2. **Stroke density** -- mean fill ratio of CC bounding boxes.
        3. **CC complexity** -- perimeter^2/area form factor.
        4. **RTL flow** -- centroid progression within text rows.

    Each signal is scored against script family profiles and combined
    via weighted average to produce a probability distribution over
    ISO 15924 codes.
    """

    def __init__(
        self,
        min_components: int = _DEFAULT_MIN_COMPONENTS,
    ) -> None:
        """Initialise the heuristic script detector.

        Args:
            min_components: Minimum connected components required for
                reliable detection.  Below this threshold the result
                is ``Zzzz`` (unknown) with an appropriate reason.
        """
        self.min_components = min_components

        logger.info(
            "script_detector_heuristic_init",
            min_components=min_components,
        )

    def detect(self, image: np.ndarray) -> ScriptDetectionResult:
        """Detect the dominant script family in a document image.

        Args:
            image: Input image (BGR, BGRA, or grayscale numpy array).

        Returns:
            ScriptDetectionResult with ISO 15924 code, confidence,
            and probability distribution.

        Raises:
            ValueError: If the image is *None* or empty.
        """
        _gray, binary, height, width = _validate_and_preprocess(image)

        # Get filtered connected components
        components = _get_filtered_components(
            binary, height, width, min_area=20, min_size=5
        )

        if len(components) < self.min_components:
            return self._unknown_result(
                num_components=len(components),
                reason=(
                    f"insufficient_components: {len(components)} "
                    f"< {self.min_components}"
                ),
            )

        # Compute the four signals
        mean_aspect = _compute_aspect_ratio_signal(components)
        mean_density = _compute_stroke_density_signal(components)
        mean_complexity = _compute_cc_complexity_signal(binary)
        rtl_score = _compute_rtl_flow_signal(components, height)

        # Score each family
        family_scores: dict[str, float] = {}
        for family_name, profile in _PROFILES.items():
            family_scores[family_name] = _score_family(
                mean_aspect, mean_density, mean_complexity, rtl_score, profile
            )

        # Determine best family
        sorted_families = sorted(
            family_scores.items(), key=lambda x: x[1], reverse=True
        )
        best_family, best_score = sorted_families[0]
        second_score = sorted_families[1][1] if len(sorted_families) > 1 else 0.0

        # Build probability distribution
        probabilities = _build_probabilities(family_scores)

        # Compute confidence
        confidence = _compute_confidence(
            best_score, second_score, len(components), self.min_components
        )

        iso_code = _FAMILY_TO_ISO[best_family]

        logger.debug(
            "script_detection_result",
            detected_script=iso_code,
            confidence=confidence,
            best_family=best_family,
            best_score=round(best_score, 4),
            num_components=len(components),
            mean_aspect=round(mean_aspect, 3),
            mean_density=round(mean_density, 3),
            mean_complexity=round(mean_complexity, 1),
            rtl_score=round(rtl_score, 3),
        )

        return ScriptDetectionResult(
            detected_script=iso_code,
            confidence=confidence,
            detection_method="heuristic",
            source_label=None,
            script_probabilities=probabilities,
            is_unknown=False,
            unknown_reason=None,
            bbox=None,
            page_index=None,
        )

    def _unknown_result(
        self,
        num_components: int,
        reason: str,
    ) -> ScriptDetectionResult:
        """Create an unknown/indeterminate result.

        Args:
            num_components: Number of CCs found (for logging).
            reason: Human-readable explanation.

        Returns:
            ScriptDetectionResult with ``Zzzz`` code and ``is_unknown=True``.
        """
        logger.debug(
            "script_detection_unknown",
            reason=reason,
            num_components=num_components,
        )

        return ScriptDetectionResult(
            detected_script=ISO15924Script.ZZZZ.value,
            confidence=0.0,
            detection_method="heuristic",
            source_label=None,
            script_probabilities={ISO15924Script.ZZZZ.value: 1.0},
            is_unknown=True,
            unknown_reason=reason,
            bbox=None,
            page_index=None,
        )


# ============================================================================
# Module-level convenience function
# ============================================================================

_default_detector: ScriptDetectorHeuristic | None = None


def detect_script_heuristic(image: np.ndarray) -> ScriptDetectionResult:
    """Convenience function to detect script with default settings.

    Uses a lazily-initialised module-level detector instance.

    Args:
        image: Input image (BGR, BGRA, or grayscale numpy array).

    Returns:
        ScriptDetectionResult with ISO 15924 code, confidence,
        and probability distribution.

    Raises:
        ValueError: If the image is *None* or empty.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = ScriptDetectorHeuristic()
    return _default_detector.detect(image)
