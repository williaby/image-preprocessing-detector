"""Document Quality Score (DQS) Calculator.

Calculates degradation and structural complexity scores for routing decisions
in the RAG pipeline (Project A → Project B handoff).
"""

from typing import Any

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
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

# Degradation score weights (must sum to 1.0)
DEGRADATION_WEIGHTS = {
    "blur": 0.30,
    "noise": 0.25,
    "contrast": 0.20,
    "illumination": 0.15,
    "artifacts": 0.10,
}

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
        ...     skew_angles=[1.0, 0.5],
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
