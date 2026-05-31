"""Resolution quality measurement via two-stage text height analysis.

Provides tools to generate resolution quality pseudo-labels (0-1 score) for
document images that lack DPI metadata. Uses a two-stage approach:

Stage 1: DL-based text line detection (PaddleOCR DBNet) for robust region
         identification that handles CJK text, shadows, blur, and degradations.
Stage 2: Connected component analysis within detected text regions for precise
         character height measurement (~2-3px aggregate precision).

The quality score maps character pixel height to OCR readability:
    <16px  = 0.00-0.15  (needs major upscaling)
    16-32px = 0.15-0.55  (needs light upscaling)
    32-48px = 0.55-0.75  (optimal OCR range)
    48-96px = 0.75-0.95  (good, may downscale)
    >96px  = 0.95-1.00  (oversized)

Validated by 5-model consensus (Gemini 2.5 Pro, Gemini 3 Pro Preview,
DeepSeek R1, Grok 4) at 8.75/10 confidence. See:
docs/planning/RESOLUTION_QUALITY_LABELING_STRATEGY.md

Example:
    >>> from image_preprocessing_detector.schema_utils.resolution_quality import (
    ...     piecewise_quality_score,
    ...     measure_char_height_in_region,
    ...     ResolutionQualityResult,
    ... )
    >>> score = piecewise_quality_score(38.5)  # optimal range
    >>> assert 0.55 <= score <= 0.75
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class CoarseBucket(str, Enum):
    """Resolution quality coarse classification buckets."""

    NEEDS_MAJOR_UPSCALE = "needs_major_upscale"
    NEEDS_LIGHT_UPSCALE = "needs_light_upscale"
    OPTIMAL = "optimal"
    GOOD = "good"
    OVERSIZED = "oversized"


# Bucket boundaries in pixels (char height thresholds)
BUCKET_THRESHOLDS: dict[CoarseBucket, tuple[float, float]] = {
    CoarseBucket.NEEDS_MAJOR_UPSCALE: (0.0, 16.0),
    CoarseBucket.NEEDS_LIGHT_UPSCALE: (16.0, 32.0),
    CoarseBucket.OPTIMAL: (32.0, 48.0),
    CoarseBucket.GOOD: (48.0, 96.0),
    CoarseBucket.OVERSIZED: (96.0, float("inf")),
}


@dataclass(frozen=True)
class ScriptAwareMeasurementConfig:
    """Per-script measurement parameters for resolution quality.

    Used when script is known (synthetic data or high-confidence script detection)
    to apply script-appropriate CC filtering and morphological operations.

    Attributes:
        script_family (str): Script family identifier ("cjk", "latin", "arabic", etc.).
        cc_aspect_ratio_range (tuple[float, float]): Valid component height/width ratio range for CC filtering.
        morphological_closing_kernel (tuple[int, int]): Kernel size (h, w) for reconnecting strokes.
        min_script_confidence (float): Minimum script confidence required to use these params.
    """

    script_family: str
    cc_aspect_ratio_range: tuple[float, float]
    morphological_closing_kernel: tuple[int, int]
    min_script_confidence: float = 0.8


# Conservative starting defaults. Arabic CC aspect ratios are uncertain — standard CC
# detects whole words in cursive Arabic, not individual characters. For Arabic, vertical
# projection profiling (V2 Phase B) will be needed for accurate per-character measurement.
SCRIPT_MEASUREMENT_CONFIGS: dict[str, ScriptAwareMeasurementConfig] = {
    "cjk": ScriptAwareMeasurementConfig("cjk", (0.6, 1.4), (3, 3), 0.8),
    "latin": ScriptAwareMeasurementConfig("latin", (0.2, 0.8), (1, 1), 0.8),
    "arabic": ScriptAwareMeasurementConfig("arabic", (0.3, 1.5), (2, 1), 0.8),
    "devanagari": ScriptAwareMeasurementConfig("devanagari", (0.4, 1.2), (2, 2), 0.8),
    "mixed": ScriptAwareMeasurementConfig("mixed", (0.2, 5.0), (2, 2), 0.0),
}

_CJK_SCRIPTS = frozenset({"Hans", "Hant", "Jpan", "Kore"})
_ARABIC_SCRIPTS = frozenset({"Arab"})
_DEVANAGARI_SCRIPTS = frozenset({"Deva"})


def resolve_script_family(iso15924_code: str) -> str:
    """Map ISO 15924 script code to measurement family.

    Args:
        iso15924_code (str): ISO 15924 4-letter script code (e.g., "Latn", "Hans").

    Returns:
        str: Script family string ("cjk", "arabic", "devanagari", or "latin" (default)).
    """
    if iso15924_code in _CJK_SCRIPTS:
        return "cjk"
    if iso15924_code in _ARABIC_SCRIPTS:
        return "arabic"
    if iso15924_code in _DEVANAGARI_SCRIPTS:
        return "devanagari"
    return "latin"


def get_script_measurement_config(
    iso15924_code: str | None = None,
    script_confidence: float | None = None,
) -> ScriptAwareMeasurementConfig:
    """Get measurement config for a script, falling back to 'mixed' if uncertain.

    Args:
        iso15924_code (str | None): ISO 15924 script code, or None for unknown script.
        script_confidence (float | None): Confidence of script detection (0-1), or None.

    Returns:
        ScriptAwareMeasurementConfig: ScriptAwareMeasurementConfig for the appropriate script family."""
    if iso15924_code is None:
        return SCRIPT_MEASUREMENT_CONFIGS["mixed"]

    family = resolve_script_family(iso15924_code)
    config = SCRIPT_MEASUREMENT_CONFIGS.get(family, SCRIPT_MEASUREMENT_CONFIGS["mixed"])

    if (
        script_confidence is not None
        and script_confidence < config.min_script_confidence
    ):
        return SCRIPT_MEASUREMENT_CONFIGS["mixed"]

    return config


@dataclass(frozen=True)
class ResolutionQualityResult:
    """Per-image resolution quality measurement with confidence and range.

    Attributes:
        resolution_quality_score (float): Primary label (0-1), piecewise-mapped from char_height_px.
        confidence_pct (float): Measurement confidence (0-1).
        char_height_px (float): Weighted median character height across all text regions.
        char_height_range_px (tuple[float, float]): 95% CI as [P25, P75] of per-region heights.
        score_range (tuple[float, float]): Quality score range from char_height_range_px through piecewise mapping.
        coarse_bucket (str): One of the CoarseBucket enum values.
        measurement_method (str): 'stage_1_2' (full) or 'stage_1_only' (CC failed).
        num_text_regions (int): Total text line regions detected by DBNet.
        num_valid_cc_regions (int): Regions where Stage 2 CC analysis succeeded.
        height_cv (float): Coefficient of variation of per-region heights.
        flagged_for_review (bool): True if low confidence or insufficient data.
        label_provenance (str): Provenance tier for weak label pipeline.
        label_source (str): Source identifier for the label.
        label_confidence (float): Confidence in the label (0-1), used for training weight.
        script_used (str | None): ISO 15924 code if script-aware measurement was used.
        script_confidence (float | None): Confidence of script detection (None if N/A).
        bucket_probabilities (dict[str, float] | None): Soft label distribution over 5 coarse buckets.
        quality_score_std (float | None): Teacher's quality_score regression uncertainty (std dev).
        char_height_std (float | None): Teacher's char_height regression uncertainty (std dev).
    """

    resolution_quality_score: float
    confidence_pct: float
    char_height_px: float
    char_height_range_px: tuple[float, float]
    score_range: tuple[float, float]
    coarse_bucket: str
    measurement_method: str
    num_text_regions: int
    num_valid_cc_regions: int
    height_cv: float
    flagged_for_review: bool

    # Provenance fields for weak label pipeline
    label_provenance: str = "tier_3_heuristic"
    label_source: str = "paddleocr_dbnet_cc_v1"
    label_confidence: float = 1.0
    script_used: str | None = None
    script_confidence: float | None = None

    # Soft label fields for teacher-student knowledge transfer
    bucket_probabilities: dict[str, float] | None = None
    quality_score_std: float | None = None
    char_height_std: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dictionary."""
        result: dict[str, object] = {
            "resolution_quality_score": round(self.resolution_quality_score, 4),
            "confidence_pct": round(self.confidence_pct, 4),
            "char_height_px": round(self.char_height_px, 2),
            "char_height_range_px": [
                round(self.char_height_range_px[0], 2),
                round(self.char_height_range_px[1], 2),
            ],
            "score_range": [
                round(self.score_range[0], 4),
                round(self.score_range[1], 4),
            ],
            "coarse_bucket": self.coarse_bucket,
            "measurement_method": self.measurement_method,
            "num_text_regions": self.num_text_regions,
            "num_valid_cc_regions": self.num_valid_cc_regions,
            "height_cv": round(self.height_cv, 4),
            "flagged_for_review": self.flagged_for_review,
            "label_provenance": self.label_provenance,
            "label_source": self.label_source,
            "label_confidence": round(self.label_confidence, 4),
        }
        if self.script_used is not None:
            result["script_used"] = self.script_used
        if self.script_confidence is not None:
            result["script_confidence"] = round(self.script_confidence, 4)
        if self.bucket_probabilities is not None:
            result["bucket_probabilities"] = {
                k: round(v, 6) for k, v in self.bucket_probabilities.items()
            }
        if self.quality_score_std is not None:
            result["quality_score_std"] = round(self.quality_score_std, 6)
        if self.char_height_std is not None:
            result["char_height_std"] = round(self.char_height_std, 4)
        return result


def piecewise_quality_score(char_height_px: float) -> float:
    """Map character pixel height to resolution quality score (0-1).

    Uses a piecewise linear mapping calibrated for OCR readability:
    - 32-48px is the optimal range for most OCR engines (score 0.55-0.75).
    - Below 16px text is illegible for OCR (score < 0.15).
    - Above 96px text is oversized with diminishing returns (score > 0.95).

    Args:
        char_height_px (float): Median character height in pixels.

    Returns:
        float: Quality score between 0.0 and 1.0."""
    if char_height_px < 0:
        return 0.0
    if char_height_px < 16:
        return char_height_px / 16.0 * 0.15
    if char_height_px < 24:
        return 0.15 + (char_height_px - 16) / 8.0 * 0.20
    if char_height_px < 32:
        return 0.35 + (char_height_px - 24) / 8.0 * 0.20
    if char_height_px < 48:
        return 0.55 + (char_height_px - 32) / 16.0 * 0.20
    if char_height_px < 64:
        return 0.75 + (char_height_px - 48) / 16.0 * 0.10
    if char_height_px < 96:
        return 0.85 + (char_height_px - 64) / 32.0 * 0.10
    return min(1.0, 0.95 + (char_height_px - 96) / 200.0 * 0.05)


def classify_coarse_bucket(char_height_px: float) -> str:
    """Classify character height into a coarse resolution bucket.

    Args:
        char_height_px (float): Median character height in pixels.

    Returns:
        str: CoarseBucket value string."""
    for bucket, (low, high) in BUCKET_THRESHOLDS.items():
        if low <= char_height_px < high:
            return bucket.value
    return CoarseBucket.OVERSIZED.value


def measure_char_height_in_region(
    region_gray: NDArray[np.uint8],
    *,
    min_components: int = 3,
    aspect_ratio_range: tuple[float, float] = (0.2, 5.0),
    min_area_frac: float = 0.001,
    max_area_frac: float = 0.10,
) -> tuple[float | None, list[float]]:
    """Measure character height via CC analysis within a detected text region.

    This is Stage 2 of the two-stage approach. It operates on a cropped
    grayscale region that is already known to contain text (from Stage 1
    DBNet detection), making CC analysis far more reliable than running
    it on a full page image.

    Uses adaptive thresholding per-region instead of global threshold,
    handling uneven lighting and shadow gradients within the text line.

    Args:
        region_gray (NDArray[np.uint8]): Grayscale numpy array of a cropped text region.
        min_components (int): Minimum valid CCs required (default 3).
        aspect_ratio_range (tuple[float, float]): Valid component height/width ratio range.
        min_area_frac (float): Minimum component area as fraction of region.
        max_area_frac (float): Maximum component area as fraction of region.

    Returns:
        tuple[float | None, list[float]]: Tuple of (median_height, list of all valid component heights).
        Returns (None, []) if measurement fails."""
    import cv2
    import numpy as np

    if region_gray.size < 16:
        return None, []

    # Adaptive threshold per-region handles shadow/lighting gradients
    # Use Gaussian adaptive threshold for robustness
    binary = cv2.adaptiveThreshold(
        region_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=max(3, (min(region_gray.shape) // 4) | 1),  # Odd number
        C=10,
    )

    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    if num_labels < 2:  # Only background
        return None, []

    heights = stats[1:, cv2.CC_STAT_HEIGHT].astype(np.float64)
    widths = stats[1:, cv2.CC_STAT_WIDTH].astype(np.float64)
    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float64)

    aspect_ratios = heights / np.maximum(widths, 1.0)
    region_area = float(region_gray.size)
    min_area = max(4.0, region_area * min_area_frac)
    max_area = region_area * max_area_frac

    valid_mask = (
        (areas > min_area)
        & (areas < max_area)
        & (aspect_ratios > aspect_ratio_range[0])
        & (aspect_ratios < aspect_ratio_range[1])
    )

    valid_heights = heights[valid_mask]
    if len(valid_heights) < min_components:
        return None, []

    median_h = float(np.median(valid_heights))
    return median_h, valid_heights.tolist()


def compute_confidence(
    num_text_regions: int,
    _num_valid_cc_regions: int,
    height_cv: float,
    method: str,
) -> float:
    """Compute measurement confidence from signal quality indicators.

    Args:
        num_text_regions (int): Total text regions detected by DBNet.
        _num_valid_cc_regions (int): Regions where CC analysis succeeded.
        height_cv (float): Coefficient of variation of per-region heights.
        method (str): 'stage_1_2' or 'stage_1_only'.

    Returns:
        float: Confidence score between 0.0 and 1.0."""
    region_factor = min(1.0, num_text_regions / 10.0)
    uniformity_factor = max(0.0, 1.0 - height_cv)
    method_factor = 1.0 if method == "stage_1_2" else 0.8
    return round(region_factor * uniformity_factor * method_factor, 4)


def aggregate_measurements(
    region_heights: list[float],
    _bbox_heights: list[float],
    cc_success_flags: list[bool],
    region_areas: list[float],
) -> ResolutionQualityResult:
    """Aggregate per-region measurements into a single image-level result.

    For each region, uses the CC-measured height if available (Stage 2),
    otherwise falls back to the DBNet bbox height (Stage 1 only).

    Args:
        region_heights (list[float]): Per-region character heights (CC median or bbox height).
        _bbox_heights (list[float]): Per-region DBNet bounding box heights (Stage 1).
        cc_success_flags (list[bool]): Whether CC analysis succeeded per region.
        region_areas (list[float]): Per-region areas in pixels (for weighting).

    Returns:
        ResolutionQualityResult: ResolutionQualityResult with all fields populated."""
    import numpy as np

    num_regions = len(region_heights)
    num_valid_cc = sum(cc_success_flags)

    if num_regions == 0:
        return ResolutionQualityResult(
            resolution_quality_score=0.5,
            confidence_pct=0.0,
            char_height_px=0.0,
            char_height_range_px=(0.0, 0.0),
            score_range=(0.5, 0.5),
            coarse_bucket=CoarseBucket.OPTIMAL.value,
            measurement_method="none",
            num_text_regions=0,
            num_valid_cc_regions=0,
            height_cv=0.0,
            flagged_for_review=True,
        )

    heights = np.array(region_heights, dtype=np.float64)
    areas = np.array(region_areas, dtype=np.float64)

    # Weighted median by region area
    sorted_indices = np.argsort(heights)
    sorted_heights = heights[sorted_indices]
    sorted_weights = areas[sorted_indices]
    cumulative_weight = np.cumsum(sorted_weights)
    total_weight = cumulative_weight[-1]

    if total_weight > 0:
        median_idx = np.searchsorted(cumulative_weight, total_weight / 2.0)
        median_idx = min(median_idx, len(sorted_heights) - 1)
        weighted_median = float(sorted_heights[median_idx])
    else:
        weighted_median = float(np.median(heights))

    p25 = float(np.percentile(heights, 25))
    p75 = float(np.percentile(heights, 75))

    # Coefficient of variation
    mean_h = float(np.mean(heights))
    std_h = float(np.std(heights))
    height_cv = std_h / mean_h if mean_h > 0 else 0.0

    # Determine method
    method = "stage_1_2" if num_valid_cc > 0 else "stage_1_only"

    # Compute scores
    quality_score = piecewise_quality_score(weighted_median)
    score_low = piecewise_quality_score(p25)
    score_high = piecewise_quality_score(p75)
    bucket = classify_coarse_bucket(weighted_median)

    # Confidence
    confidence = compute_confidence(num_regions, num_valid_cc, height_cv, method)

    # Review flags
    flagged = num_regions < 3 or confidence < 0.4 or height_cv > 0.5
    if flagged and num_regions < 3:
        confidence = min(confidence, 0.3)

    return ResolutionQualityResult(
        resolution_quality_score=quality_score,
        confidence_pct=confidence,
        char_height_px=weighted_median,
        char_height_range_px=(p25, p75),
        score_range=(score_low, score_high),
        coarse_bucket=bucket,
        measurement_method=method,
        num_text_regions=num_regions,
        num_valid_cc_regions=num_valid_cc,
        height_cv=height_cv,
        flagged_for_review=flagged,
    )


def extract_line_height_from_polygon(
    polygon: list[list[float]],
) -> float:
    """Compute the height of a text line from its polygon bounding box.

    PaddleOCR returns 4-point polygons [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    where points are ordered: top-left, top-right, bottom-right, bottom-left.
    The line height is the average of the left and right edge lengths.

    For CJK text, this measures the short side of the text line (= char height).

    Args:
        polygon (list[list[float]]): 4-point polygon as [[x,y], ...].

    Returns:
        float: Line height in pixels."""
    import numpy as np

    pts = np.array(polygon, dtype=np.float64)
    if pts.shape != (4, 2):
        # Fallback: use bounding rect
        min_y = pts[:, 1].min()
        max_y = pts[:, 1].max()
        return float(max_y - min_y)

    # Left edge: top-left to bottom-left
    left_height = float(np.linalg.norm(pts[3] - pts[0]))
    # Right edge: top-right to bottom-right
    right_height = float(np.linalg.norm(pts[2] - pts[1]))

    return (left_height + right_height) / 2.0


def crop_polygon_region(
    image_gray: NDArray[np.uint8],
    polygon: list[list[float]],
    padding: int = 2,
) -> NDArray[np.uint8] | None:
    """Crop and mask a text region from a grayscale image using a polygon.

    Args:
        image_gray (NDArray[np.uint8]): Full grayscale image.
        polygon (list[list[float]]): 4-point polygon [[x,y], ...].
        padding (int): Pixels of padding around the bounding rect.

    Returns:
        NDArray[np.uint8] | None: Cropped grayscale region, or None if too small."""
    import cv2
    import numpy as np

    pts = np.array(polygon, dtype=np.int32)
    x_min = max(0, int(pts[:, 0].min()) - padding)
    y_min = max(0, int(pts[:, 1].min()) - padding)
    x_max = min(image_gray.shape[1], int(pts[:, 0].max()) + padding)
    y_max = min(image_gray.shape[0], int(pts[:, 1].max()) + padding)

    if (x_max - x_min) < 4 or (y_max - y_min) < 4:
        return None

    cropped = image_gray[y_min:y_max, x_min:x_max].copy()

    # Apply polygon mask within the crop
    shifted_pts = pts - np.array([x_min, y_min])
    mask = np.zeros(cropped.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [np.array(shifted_pts, dtype=np.int32)], (255,))

    # Set non-text pixels to white (255) so they don't create dark CCs
    cropped[mask == 0] = 255

    return cropped


def measure_char_height_v2(
    image_gray: NDArray[np.uint8],
    script_family: str = "mixed",
    use_sauvola: bool = True,
) -> tuple[float | None, float | None]:
    """Measure character height using V2 method (Sauvola + script-aware CC).

    Shared measurement function used by both the synthetic generator and
    the resolution quality labeling pipeline. Uses Sauvola binarization
    (when available) for improved local thresholding, with script-aware
    morphological closing and CC aspect ratio filtering.

    Args:
        image_gray (NDArray[np.uint8]): Grayscale image (uint8, single channel).
        script_family (str): Script family for measurement parameters. One of: "cjk", "latin", "arabic", "devanagari", "mixed".
        use_sauvola (bool): If True, attempt Sauvola binarization via cv2.ximgproc.niBlackThreshold. Falls back to adaptive threshold if opencv-contrib-python is not available.

    Returns:
        tuple[float | None, float | None]: Tuple of (char_height_px, quality_score) where quality_score is
        the piecewise mapping from height to 0-1 score. Returns
        (None, None) if measurement fails (e.g., no text detected)."""
    import cv2
    import numpy as np

    if image_gray.size < 64:
        return None, None

    config = SCRIPT_MEASUREMENT_CONFIGS.get(
        script_family, SCRIPT_MEASUREMENT_CONFIGS["mixed"]
    )

    # Step 1: Binarize with Sauvola (preferred) or adaptive threshold
    if use_sauvola:
        try:
            binary = cv2.ximgproc.niBlackThreshold(  # type: ignore[attr-defined]
                image_gray,
                maxValue=255,
                type=cv2.THRESH_BINARY_INV,
                blockSize=max(15, (min(image_gray.shape) // 8) | 1),
                k=0.2,
                binarizationMethod=cv2.ximgproc.BINARIZATION_SAUVOLA,  # type: ignore[attr-defined]
            )
        except (AttributeError, cv2.error):
            # opencv-contrib-python not installed; fall back
            binary = cv2.adaptiveThreshold(
                image_gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                blockSize=max(3, (min(image_gray.shape) // 4) | 1),
                C=10,
            )
    else:
        binary = cv2.adaptiveThreshold(
            image_gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=max(3, (min(image_gray.shape) // 4) | 1),
            C=10,
        )

    # Step 2: Script-aware morphological closing to reconnect strokes
    kernel_h, kernel_w = config.morphological_closing_kernel
    if kernel_h > 1 or kernel_w > 1:
        # CJK: 3x3 reconnects radicals. Latin: 1x1 = no-op
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, kernel_h))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Step 3: Connected component analysis with script-aware filtering
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    if num_labels < 2:
        return None, None

    heights = stats[1:, cv2.CC_STAT_HEIGHT].astype(np.float64)
    widths = stats[1:, cv2.CC_STAT_WIDTH].astype(np.float64)
    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float64)

    aspect_ratios = heights / np.maximum(widths, 1.0)
    total_area = float(image_gray.size)
    min_area = max(4.0, total_area * 0.0001)
    max_area = total_area * 0.5

    ar_min, ar_max = config.cc_aspect_ratio_range
    valid_mask = (
        (areas > min_area)
        & (areas < max_area)
        & (aspect_ratios > ar_min)
        & (aspect_ratios < ar_max)
    )

    valid_heights = heights[valid_mask]
    if len(valid_heights) < 3:
        return None, None

    median_h = float(np.median(valid_heights))
    quality_score = piecewise_quality_score(median_h)
    return median_h, quality_score
