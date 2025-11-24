"""Document Quality Score (DQS) Calculator.

Calculates degradation and structural complexity scores for routing decisions
in the RAG pipeline (Project A → Project B handoff).

Phase 4.10: Updated with configurable weights and integration with new classical
IQA detectors (illumination, JPEG blockiness, binarization, bleed-through).
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityResult,
    BleedThroughResult,
    BlurDetectionResult,
    ContrastDetectionResult,
    IlluminationDetectionResult,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    SkewDetectionResult,
)
from image_preprocessing_detector.schema import (
    DQSMetadata,
    LayoutType,
    PageLayoutSummary,
    PDFType,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Legacy degradation score weights (must sum to 1.0)
# Kept for backward compatibility
DEGRADATION_WEIGHTS = {
    "blur": 0.30,
    "noise": 0.25,
    "contrast": 0.20,
    "illumination": 0.15,
    "artifacts": 0.10,
}


@dataclass
class DQSWeightConfig:
    """Configurable weights for DQS degradation score calculation.

    Phase 4.10: Extended to include new classical IQA detectors.

    Weight Selection Rationale:
    ---------------------------
    Weights are calibrated based on impact on OCR accuracy:

    1. **Blur (0.25)**: High impact - blurry text is difficult to recognize.
       Reduced from 0.30 to accommodate new metrics.

    2. **Noise (0.20)**: Medium-high impact - noise interferes with character
       recognition. Reduced slightly to balance with new metrics.

    3. **Contrast (0.15)**: Medium impact - low contrast reduces readability
       but OCR engines handle it reasonably well.

    4. **Illumination (0.12)**: Medium impact - uneven lighting can cause
       partial text degradation.

    5. **Compression (0.10)**: Medium-low impact - JPEG artifacts can blur
       character edges but modern OCR handles it well.

    6. **Binarization (0.10)**: Medium-low impact - poor binarization quality
       affects thresholding-based preprocessing.

    7. **Bleed-through (0.08)**: Low-medium impact - verso text showing through
       can confuse OCR, but often still readable.

    These weights should be refined through OCR accuracy correlation (Phase 10).

    Attributes:
        blur: Weight for blur quality (default: 0.25)
        noise: Weight for noise quality (default: 0.20)
        contrast: Weight for contrast quality (default: 0.15)
        illumination: Weight for illumination quality (default: 0.12)
        compression: Weight for compression artifacts (default: 0.10)
        binarization: Weight for binarization quality (default: 0.10)
        bleed_through: Weight for bleed-through quality (default: 0.08)
    """

    blur: float = 0.25
    noise: float = 0.20
    contrast: float = 0.15
    illumination: float = 0.12
    compression: float = 0.10
    binarization: float = 0.10
    bleed_through: float = 0.08

    def __post_init__(self) -> None:
        """Validate weights sum to approximately 1.0."""
        total = (
            self.blur
            + self.noise
            + self.contrast
            + self.illumination
            + self.compression
            + self.binarization
            + self.bleed_through
        )
        if not (0.99 <= total <= 1.01):
            logger.warning(
                "DQS weights do not sum to 1.0",
                total=total,
                expected=1.0,
            )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary format."""
        return {
            "blur": self.blur,
            "noise": self.noise,
            "contrast": self.contrast,
            "illumination": self.illumination,
            "compression": self.compression,
            "binarization": self.binarization,
            "bleed_through": self.bleed_through,
        }

    @classmethod
    def from_dict(cls, weights: dict[str, float]) -> "DQSWeightConfig":
        """Create from dictionary."""
        return cls(
            blur=weights.get("blur", 0.25),
            noise=weights.get("noise", 0.20),
            contrast=weights.get("contrast", 0.15),
            illumination=weights.get("illumination", 0.12),
            compression=weights.get("compression", 0.10),
            binarization=weights.get("binarization", 0.10),
            bleed_through=weights.get("bleed_through", 0.08),
        )

    def get_rationale(self) -> dict[str, str]:
        """Get rationale for each weight."""
        return {
            "blur": (
                f"Weight {self.blur}: High impact - blurry text is difficult "
                "to recognize. Critical for OCR accuracy."
            ),
            "noise": (
                f"Weight {self.noise}: Medium-high impact - noise interferes "
                "with character recognition."
            ),
            "contrast": (
                f"Weight {self.contrast}: Medium impact - low contrast reduces "
                "readability but OCR engines handle it reasonably."
            ),
            "illumination": (
                f"Weight {self.illumination}: Medium impact - uneven lighting "
                "can cause partial text degradation."
            ),
            "compression": (
                f"Weight {self.compression}: Medium-low impact - JPEG artifacts "
                "can blur character edges."
            ),
            "binarization": (
                f"Weight {self.binarization}: Medium-low impact - affects "
                "thresholding-based preprocessing."
            ),
            "bleed_through": (
                f"Weight {self.bleed_through}: Low-medium impact - verso text "
                "showing through can confuse OCR."
            ),
        }


# Default weight configuration
DEFAULT_DQS_WEIGHTS = DQSWeightConfig()

# Layout type base complexity scores
LAYOUT_COMPLEXITY_BASE = {
    LayoutType.SINGLE_COLUMN: 0.1,
    LayoutType.MULTI_COLUMN: 0.4,
    LayoutType.THREE_COLUMN: 0.6,
    LayoutType.COMPLEX: 0.9,
    LayoutType.UNKNOWN: 0.5,  # Medium complexity as default
}

# Structural feature weights
STRUCTURAL_FEATURE_WEIGHTS = {
    "has_tables": 0.20,
    "has_figures": 0.15,
    "has_dense_math": 0.15,
    "has_handwriting": 0.10,
}


def calculate_degradation_score(
    classical_iqa: dict[str, Any],
    ml_iqa: dict[str, Any] | None = None,
) -> float:
    """Calculate degradation score from IQA metrics.

    Weighted formula: 0.3*blur + 0.25*noise + 0.2*contrast + 0.15*illumination + 0.1*artifacts
    All input metrics should be normalized to 0-1 range where 1=best quality.

    Args:
        classical_iqa: Classical IQA metrics dict with keys:
            - blur_score: Laplacian variance normalized (0-1, higher=sharper)
            - noise_score: Noise level normalized (0-1, higher=cleaner)
            - contrast_score: Contrast quality normalized (0-1, higher=better)
            - illumination_score: Illumination quality normalized (0-1, higher=better)
            - artifacts_score: Artifact presence normalized (0-1, higher=fewer artifacts)
        ml_iqa: Optional ML-based IQA metrics (Phase 2+). If provided, will be
            blended with classical metrics.

    Returns:
        Degradation score (0-1, where 0=worst degradation, 1=pristine quality)

    Raises:
        ValueError: If required metrics are missing or out of range

    Example:
        >>> classical_iqa = {
        ...     "blur_score": 0.8,
        ...     "noise_score": 0.7,
        ...     "contrast_score": 0.6,
        ...     "illumination_score": 0.9,
        ...     "artifacts_score": 0.95,
        ... }
        >>> score = calculate_degradation_score(classical_iqa)
        >>> assert 0.0 <= score <= 1.0
    """
    # Validate required metrics are present
    required_metrics = [
        "blur_score",
        "noise_score",
        "contrast_score",
        "illumination_score",
        "artifacts_score",
    ]

    for metric in required_metrics:
        if metric not in classical_iqa:
            raise ValueError(f"Missing required metric: {metric}")

        value = classical_iqa[metric]
        if not isinstance(value, int | float):
            raise TypeError(f"Metric {metric} must be numeric, got {type(value)}")

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Metric {metric} must be in range [0.0, 1.0], got {value}"
            )

    # Calculate weighted score
    degradation_score = (
        DEGRADATION_WEIGHTS["blur"] * classical_iqa["blur_score"]
        + DEGRADATION_WEIGHTS["noise"] * classical_iqa["noise_score"]
        + DEGRADATION_WEIGHTS["contrast"] * classical_iqa["contrast_score"]
        + DEGRADATION_WEIGHTS["illumination"] * classical_iqa["illumination_score"]
        + DEGRADATION_WEIGHTS["artifacts"] * classical_iqa["artifacts_score"]
    )

    # If ML IQA is available (Phase 2+), blend with classical
    if ml_iqa is not None and "overall_quality" in ml_iqa:
        ml_quality = ml_iqa["overall_quality"]
        if not 0.0 <= ml_quality <= 1.0:
            logger.warning(
                "ML IQA quality score out of range, ignoring",
                ml_quality=ml_quality,
            )
        else:
            # Blend: 70% classical, 30% ML (tunable)
            degradation_score = 0.7 * degradation_score + 0.3 * ml_quality
            logger.debug(
                "Blended classical and ML IQA scores",
                classical_score=degradation_score / 0.7,
                ml_score=ml_quality,
                final_score=degradation_score,
            )

    # Ensure result is in valid range
    degradation_score = max(0.0, min(1.0, degradation_score))

    logger.debug(
        "Degradation score calculated",
        score=degradation_score,
        blur=classical_iqa["blur_score"],
        noise=classical_iqa["noise_score"],
        contrast=classical_iqa["contrast_score"],
        illumination=classical_iqa["illumination_score"],
        artifacts=classical_iqa["artifacts_score"],
    )

    return float(degradation_score)


def calculate_structural_complexity_score(
    layout_summary: PageLayoutSummary,
) -> float:
    """Calculate structural complexity score from layout metadata.

    Base score from layout_type:
    - single_column: 0.1
    - multi_column: 0.4
    - three_column: 0.6
    - complex: 0.9
    - unknown: 0.5

    Additional increments:
    - +0.2 if has_tables
    - +0.15 if has_figures
    - +0.15 if has_dense_math
    - +0.1 if has_handwriting

    Score is capped at 1.0.

    Args:
        layout_summary: PageLayoutSummary with layout type and feature flags

    Returns:
        Structural complexity score (0-1, where 0=simple, 1=very complex)

    Example:
        >>> from image_preprocessing_detector.schema import (
        ...     PageLayoutSummary,
        ...     LayoutType,
        ...     PageAttributes,
        ... )
        >>> layout = PageLayoutSummary(
        ...     page_index=0,
        ...     layout_type=LayoutType.MULTI_COLUMN,
        ...     has_tables=True,
        ...     has_figures=False,
        ...     has_dense_math=False,
        ...     has_handwriting=False,
        ...     page_attributes=PageAttributes(),
        ... )
        >>> score = calculate_structural_complexity_score(layout)
        >>> assert score == 0.4 + 0.2  # multi_column + has_tables
    """
    # Start with base complexity from layout type
    complexity_score = LAYOUT_COMPLEXITY_BASE[layout_summary.layout_type]

    logger.debug(
        "Base complexity from layout type",
        layout_type=layout_summary.layout_type.value,
        base_score=complexity_score,
    )

    # Add increments for structural features
    if layout_summary.has_tables:
        complexity_score += STRUCTURAL_FEATURE_WEIGHTS["has_tables"]
        logger.debug("Added tables complexity", increment=0.20)

    if layout_summary.has_figures:
        complexity_score += STRUCTURAL_FEATURE_WEIGHTS["has_figures"]
        logger.debug("Added figures complexity", increment=0.15)

    if layout_summary.has_dense_math:
        complexity_score += STRUCTURAL_FEATURE_WEIGHTS["has_dense_math"]
        logger.debug("Added dense math complexity", increment=0.15)

    if layout_summary.has_handwriting:
        complexity_score += STRUCTURAL_FEATURE_WEIGHTS["has_handwriting"]
        logger.debug("Added handwriting complexity", increment=0.10)

    # Cap at 1.0
    complexity_score = min(1.0, complexity_score)

    logger.debug(
        "Structural complexity score calculated",
        score=complexity_score,
        layout_type=layout_summary.layout_type.value,
        has_tables=layout_summary.has_tables,
        has_figures=layout_summary.has_figures,
        has_dense_math=layout_summary.has_dense_math,
        has_handwriting=layout_summary.has_handwriting,
    )

    return float(complexity_score)


def aggregate_dqs(
    page_dqs_list: list[DQSMetadata],
) -> DQSMetadata:
    """Aggregate page-level DQS scores to document-level.

    Aggregation strategy:
    - degradation_score: median (representative of typical page quality)
    - structural_complexity_score: max (worst page determines routing needs)

    Rationale: For routing decisions, we need to handle the most complex page
    and be aware of the typical quality level across all pages.

    Args:
        page_dqs_list: List of DQSMetadata instances, one per page

    Returns:
        Aggregated DQSMetadata for the entire document

    Raises:
        ValueError: If page_dqs_list is empty

    Example:
        >>> page_scores = [
        ...     DQSMetadata(degradation_score=0.8, structural_complexity_score=0.3),
        ...     DQSMetadata(degradation_score=0.7, structural_complexity_score=0.6),
        ...     DQSMetadata(degradation_score=0.9, structural_complexity_score=0.4),
        ... ]
        >>> doc_score = aggregate_dqs(page_scores)
        >>> assert doc_score.degradation_score == 0.8  # median
        >>> assert doc_score.structural_complexity_score == 0.6  # max
    """
    if not page_dqs_list:
        raise ValueError("Cannot aggregate empty page_dqs_list")

    # Extract scores into arrays
    degradation_scores = np.array([page.degradation_score for page in page_dqs_list])
    complexity_scores = np.array(
        [page.structural_complexity_score for page in page_dqs_list]
    )

    # Aggregate: median degradation, max complexity
    aggregated_degradation = float(np.median(degradation_scores))
    aggregated_complexity = float(np.max(complexity_scores))

    logger.info(
        "Aggregated document-level DQS",
        num_pages=len(page_dqs_list),
        degradation_median=aggregated_degradation,
        degradation_min=float(np.min(degradation_scores)),
        degradation_max=float(np.max(degradation_scores)),
        complexity_max=aggregated_complexity,
        complexity_min=float(np.min(complexity_scores)),
        complexity_median=float(np.median(complexity_scores)),
    )

    return DQSMetadata(
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )


def normalize_classical_iqa(
    blur_result: BlurDetectionResult | None = None,
    contrast_result: ContrastDetectionResult | None = None,
    _skew_result: SkewDetectionResult | None = None,
    noise_score: float | None = None,
    illumination_score: float | None = None,
    artifacts_score: float | None = None,
) -> dict[str, Any]:
    """Normalize classical IQA results into DQS-compatible format.

    Converts raw detector outputs into normalized 0-1 scores where 1=best quality.
    Uses sensible defaults for missing metrics.

    Args:
        blur_result: BlurDetectionResult from BlurDetector
        contrast_result: ContrastDetectionResult from ContrastDetector
        _skew_result: SkewDetectionResult from SkewDetector (not directly used in DQS,
            but provided for completeness)
        noise_score: Pre-normalized noise score (0-1, 1=clean)
        illumination_score: Pre-normalized illumination score (0-1, 1=good)
        artifacts_score: Pre-normalized artifacts score (0-1, 1=clean)

    Returns:
        Dictionary with normalized IQA metrics ready for calculate_degradation_score()

    Example:
        >>> from image_preprocessing_detector.detection.iqa_classical import (
        ...     detect_blur,
        ...     detect_contrast,
        ... )
        >>> import cv2
        >>> image = cv2.imread("document.jpg")
        >>> blur_result = detect_blur(image)
        >>> contrast_result = detect_contrast(image)
        >>> iqa = normalize_classical_iqa(
        ...     blur_result=blur_result, contrast_result=contrast_result
        ... )
        >>> dqs = calculate_degradation_score(iqa)
    """
    # Normalize blur score (Laplacian variance)
    # Typical range: 0-1000+, good quality > 200
    # Normalize using sigmoid-like function
    if blur_result is not None:
        # Use inverse severity as quality indicator
        # Also consider the raw score normalized
        raw_blur = blur_result.score
        # Normalize: 0-200 -> 0-1 (200+ = 1.0)
        blur_normalized = min(1.0, raw_blur / 200.0)
    else:
        blur_normalized = 0.8  # Default: assume reasonable quality

    # Normalize contrast score (already 0-1 from detector)
    contrast_normalized = (
        contrast_result.score if contrast_result is not None else 0.7
    )  # Default: assume moderate contrast

    # Use provided normalized scores or defaults
    noise_normalized = noise_score if noise_score is not None else 0.85
    illumination_normalized = (
        illumination_score if illumination_score is not None else 0.9
    )
    artifacts_normalized = artifacts_score if artifacts_score is not None else 0.95

    return {
        "blur_score": blur_normalized,
        "noise_score": noise_normalized,
        "contrast_score": contrast_normalized,
        "illumination_score": illumination_normalized,
        "artifacts_score": artifacts_normalized,
    }


def calculate_dqs(
    blur_scores: list[float],
    contrast_scores: list[float],
    noise_scores: list[float],
    _skew_angles: list[float],
    layout_complexities: list[float],
) -> DQSMetadata:
    """Calculate Document Quality Score from page-level metrics.

    Aggregates IQA metrics across all pages to produce document-level DQS.

    Args:
        blur_scores: List of blur scores per page (0-1, 1=sharp)
        contrast_scores: List of contrast scores per page (0-1, 1=good)
        noise_scores: List of noise scores per page (0-1, 1=clean)
        _skew_angles: List of skew angles per page (degrees, unused in current implementation)
        layout_complexities: List of layout complexity scores per page (0-1)

    Returns:
        DQSMetadata with aggregated degradation and complexity scores

    Example:
        >>> dqs = calculate_dqs(
        ...     blur_scores=[0.8, 0.7],
        ...     contrast_scores=[0.9, 0.85],
        ...     noise_scores=[0.75, 0.8],
        ...     _skew_angles=[1.0, 0.5],
        ...     layout_complexities=[0.3, 0.4],
        ... )
        >>> assert 0.0 <= dqs.degradation_score <= 1.0
    """
    import numpy as np

    # Aggregate degradation score: median of weighted IQA metrics
    num_pages = len(blur_scores)
    degradation_scores = []

    for i in range(num_pages):
        # Weight: 40% blur, 30% noise, 30% contrast
        page_degradation = (
            0.4 * blur_scores[i] + 0.3 * noise_scores[i] + 0.3 * contrast_scores[i]
        )
        degradation_scores.append(page_degradation)

    aggregated_degradation = float(np.median(degradation_scores))

    # Aggregate complexity: max complexity across all pages
    aggregated_complexity = float(np.max(layout_complexities))

    logger.debug(
        "Calculated DQS from page metrics",
        num_pages=num_pages,
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )

    return DQSMetadata(
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )


def calculate_pre_ocr_risk(
    dqs: DQSMetadata,
    pdf_type: PDFType | None,
    page_layout_summary: list[PageLayoutSummary],
) -> float:
    """Calculate pre-OCR processing risk score.

    Risk score combines degradation quality, structural complexity, and document type
    to predict OCR difficulty (0=low risk, 1=high risk).

    Formula:
    - Base risk from degradation: (1 - degradation_score) * 0.4
    - Complexity contribution: complexity_score * 0.3
    - PDF type penalty: +0.2 for image_only, +0.0 for born_digital
    - Layout features: +0.1 if has_handwriting

    Args:
        dqs: Document Quality Score
        pdf_type: PDF classification (image_only/born_digital/hybrid)
        page_layout_summary: Per-page layout analysis

    Returns:
        Pre-OCR risk score (0-1, where 0=low risk, 1=high risk)

    Example:
        >>> dqs = DQSMetadata(degradation_score=0.7, structural_complexity_score=0.5)
        >>> risk = calculate_pre_ocr_risk(dqs, PDFType.HYBRID, [])
        >>> assert 0.0 <= risk <= 1.0
    """
    # Base risk from degradation (inverse: low quality = high risk)
    degradation_risk = (1.0 - dqs.degradation_score) * 0.4

    # Complexity contribution
    complexity_risk = dqs.structural_complexity_score * 0.3

    # PDF type penalty
    pdf_type_penalty = 0.0
    if pdf_type == PDFType.IMAGE_ONLY:
        pdf_type_penalty = 0.2
    elif pdf_type == PDFType.HYBRID:
        pdf_type_penalty = 0.1

    # Layout feature penalties
    has_handwriting = any(page.has_handwriting for page in page_layout_summary)
    handwriting_penalty = 0.1 if has_handwriting else 0.0

    # Aggregate risk
    total_risk = (
        degradation_risk + complexity_risk + pdf_type_penalty + handwriting_penalty
    )

    # Clamp to [0, 1]
    total_risk = max(0.0, min(1.0, total_risk))

    logger.debug(
        "Calculated pre-OCR risk",
        degradation_risk=degradation_risk,
        complexity_risk=complexity_risk,
        pdf_type_penalty=pdf_type_penalty,
        handwriting_penalty=handwriting_penalty,
        total_risk=total_risk,
    )

    return float(total_risk)


# =============================================================================
# Phase 4.10: Extended DQS with new classical IQA detectors
# =============================================================================


@dataclass
class ExtendedIQAScores:
    """Extended IQA scores from all classical detectors (Phase 4.10).

    All scores normalized to 0-1 where 1=best quality.

    Attributes:
        blur_score: Blur quality (from BlurDetector)
        noise_score: Noise quality (from NoiseDetector)
        contrast_score: Contrast quality (from ContrastDetector)
        illumination_score: Illumination quality (from IlluminationDetector)
        compression_score: Compression quality (from JPEGBlockinessDetector)
        binarization_score: Binarization quality (from BinarizationQualityDetector)
        bleed_through_score: Bleed-through quality (from BleedThroughDetector)
    """

    blur_score: float = 1.0
    noise_score: float = 1.0
    contrast_score: float = 1.0
    illumination_score: float = 1.0
    compression_score: float = 1.0
    binarization_score: float = 1.0
    bleed_through_score: float = 1.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "blur": self.blur_score,
            "noise": self.noise_score,
            "contrast": self.contrast_score,
            "illumination": self.illumination_score,
            "compression": self.compression_score,
            "binarization": self.binarization_score,
            "bleed_through": self.bleed_through_score,
        }


def normalize_extended_iqa(
    blur_result: BlurDetectionResult | None = None,
    noise_result: NoiseDetectionResult | None = None,
    contrast_result: ContrastDetectionResult | None = None,
    illumination_result: IlluminationDetectionResult | None = None,
    compression_result: JPEGBlockinessResult | None = None,
    binarization_result: BinarizationQualityResult | None = None,
    bleed_through_result: BleedThroughResult | None = None,
    _skew_result: SkewDetectionResult | None = None,  # Not used in DQS but accepted
) -> ExtendedIQAScores:
    """Normalize all classical detector outputs to ExtendedIQAScores.

    Phase 4.10: Integrates all Phase 4 classical IQA detectors into a
    unified score format for DQS calculation.

    Args:
        blur_result: BlurDetectionResult from BlurDetector
        noise_result: NoiseDetectionResult from NoiseDetector
        contrast_result: ContrastDetectionResult from ContrastDetector
        illumination_result: IlluminationDetectionResult from IlluminationDetector
        compression_result: JPEGBlockinessResult from JPEGBlockinessDetector
        binarization_result: BinarizationQualityResult from BinarizationQualityDetector
        bleed_through_result: BleedThroughResult from BleedThroughDetector
        skew_result: SkewDetectionResult (not used in DQS, but accepted for API completeness)

    Returns:
        ExtendedIQAScores with all normalized scores

    Example:
        >>> from image_preprocessing_detector.detection import (
        ...     detect_blur, detect_noise, detect_contrast,
        ... )
        >>> blur = detect_blur(image)
        >>> noise = detect_noise(image)
        >>> contrast = detect_contrast(image)
        >>> scores = normalize_extended_iqa(
        ...     blur_result=blur,
        ...     noise_result=noise,
        ...     contrast_result=contrast,
        ... )
        >>> dqs = calculate_extended_degradation_score(scores)
    """
    scores = ExtendedIQAScores()

    # Blur: Normalize Laplacian variance (0-1000+ → 0-1)
    if blur_result is not None:
        if blur_result.is_blurred:
            # Use severity-based quality
            severity_map = {"low": 0.85, "medium": 0.65, "high": 0.40, "critical": 0.15}
            scores.blur_score = severity_map.get(blur_result.severity.value, 0.5)
        else:
            # Normalize raw score
            scores.blur_score = min(1.0, blur_result.score / 500.0)

    # Noise: Invert noise score (0-1 where 1=noisy → 0-1 where 1=clean)
    if noise_result is not None:
        if noise_result.is_noisy:
            severity_map = {"low": 0.85, "medium": 0.65, "high": 0.40, "critical": 0.15}
            scores.noise_score = severity_map.get(noise_result.severity.value, 0.5)
        else:
            scores.noise_score = 1.0 - noise_result.score

    # Contrast: Already 0-1 range
    if contrast_result is not None:
        if contrast_result.is_low_contrast:
            severity_map = {"low": 0.85, "medium": 0.65, "high": 0.40, "critical": 0.15}
            scores.contrast_score = severity_map.get(contrast_result.severity.value, 0.5)
        else:
            scores.contrast_score = contrast_result.score

    # Illumination: Use uniformity score
    if illumination_result is not None:
        if illumination_result.has_issues:
            severity_map = {"low": 0.85, "medium": 0.65, "high": 0.40, "critical": 0.15}
            scores.illumination_score = severity_map.get(
                illumination_result.severity.value, 0.5
            )
        else:
            scores.illumination_score = illumination_result.uniformity

    # Compression: Use compression_score (already 0-1)
    if compression_result is not None:
        if compression_result.has_artifacts:
            severity_map = {"low": 0.85, "medium": 0.65, "high": 0.40, "critical": 0.15}
            scores.compression_score = severity_map.get(
                compression_result.severity.value, 0.5
            )
        else:
            scores.compression_score = compression_result.compression_score

    # Binarization: Use binarization_score (already 0-1)
    if binarization_result is not None:
        scores.binarization_score = binarization_result.binarization_score

    # Bleed-through: Invert severity (0=bleed-through, 1=clean)
    if bleed_through_result is not None:
        if bleed_through_result.bleed_through_detected:
            scores.bleed_through_score = 1.0 - bleed_through_result.severity
        else:
            scores.bleed_through_score = 1.0

    return scores


def calculate_extended_degradation_score(
    iqa_scores: ExtendedIQAScores,
    weights: DQSWeightConfig | None = None,
    ml_iqa: dict[str, Any] | None = None,
) -> float:
    """Calculate degradation score using extended IQA metrics and configurable weights.

    Phase 4.10: Uses all Phase 4 classical IQA detectors with configurable weights.

    Args:
        iqa_scores: ExtendedIQAScores with all normalized IQA metrics
        weights: DQSWeightConfig with calibrated weights (default: DEFAULT_DQS_WEIGHTS)
        ml_iqa: Optional ML-based IQA metrics. If provided, blends with classical.

    Returns:
        Degradation score (0-1, where 0=worst degradation, 1=pristine quality)

    Example:
        >>> scores = ExtendedIQAScores(
        ...     blur_score=0.8,
        ...     noise_score=0.7,
        ...     contrast_score=0.85,
        ...     illumination_score=0.9,
        ...     compression_score=0.95,
        ...     binarization_score=0.88,
        ...     bleed_through_score=1.0,
        ... )
        >>> dqs = calculate_extended_degradation_score(scores)
        >>> assert 0.0 <= dqs <= 1.0
    """
    if weights is None:
        weights = DEFAULT_DQS_WEIGHTS

    # Calculate weighted score
    degradation_score = (
        weights.blur * iqa_scores.blur_score
        + weights.noise * iqa_scores.noise_score
        + weights.contrast * iqa_scores.contrast_score
        + weights.illumination * iqa_scores.illumination_score
        + weights.compression * iqa_scores.compression_score
        + weights.binarization * iqa_scores.binarization_score
        + weights.bleed_through * iqa_scores.bleed_through_score
    )

    # Blend with ML IQA if available (Phase 2+)
    if ml_iqa is not None and "overall_quality" in ml_iqa:
        ml_quality = ml_iqa["overall_quality"]
        if 0.0 <= ml_quality <= 1.0:
            # Blend: 70% classical, 30% ML
            degradation_score = 0.7 * degradation_score + 0.3 * ml_quality
            logger.debug(
                "Blended extended IQA with ML scores",
                classical_score=degradation_score / 0.7,
                ml_score=ml_quality,
                final_score=degradation_score,
            )

    # Ensure result is in valid range
    degradation_score = max(0.0, min(1.0, degradation_score))

    logger.debug(
        "Extended degradation score calculated",
        score=degradation_score,
        weights=weights.to_dict(),
        input_scores=iqa_scores.to_dict(),
    )

    return float(degradation_score)
