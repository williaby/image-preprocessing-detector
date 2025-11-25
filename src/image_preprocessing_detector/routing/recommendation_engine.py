"""OCR Routing Recommendation Engine.

Implements decision tree logic to recommend optimal OCR engine routing based on:
- PDF type classification
- Document Quality Score (DQS)
- Pre-OCR risk assessment
- Layout complexity
- Content attributes (tables, handwriting, etc.)
"""

from image_preprocessing_detector.schema import (
    DocumentQualityScore,
    LayoutType,
    OCRRoutingRecommendation,
    PageLayoutSummary,
    PDFType,
)


def recommend_ocr_routing(
    pdf_type: PDFType | None,
    dqs: DocumentQualityScore,
    pre_ocr_risk: float,
    page_layout_summary: list[PageLayoutSummary],
) -> tuple[OCRRoutingRecommendation, str]:
    """Recommend optimal OCR engine routing strategy.

    Decision tree logic (in evaluation order):
    1. IF has_tables OR has_figures → vision_structured
    2. ELIF pre_ocr_risk > 0.6 OR has_handwriting → ocr_advanced
    3. ELIF pdf_type == born_digital AND dqs.degradation_score > 0.8 AND layout simple
       → ocr_fast
    4. ELIF pdf_type == image_only AND layout simple → vision_simple
    5. ELSE → ocr_advanced (conservative fallback)

    Args:
        pdf_type: PDF classification (image_only, born_digital, hybrid, or None)
        dqs: Document Quality Score with degradation and complexity metrics
        pre_ocr_risk: Aggregated risk score for OCR difficulty (0-1)
        page_layout_summary: Per-page layout analysis with content flags

    Returns:
        Tuple of (routing_recommendation, rationale_string)

    Examples:
        >>> dqs = DocumentQualityScore(
        ...     degradation_score=0.9, structural_complexity_score=0.2
        ... )
        >>> layouts = [
        ...     PageLayoutSummary(
        ...         page_index=0,
        ...         layout_type=LayoutType.SINGLE_COLUMN,
        ...         has_tables=False,
        ...         has_figures=False,
        ...         has_dense_math=False,
        ...         has_handwriting=False,
        ...     )
        ... ]
        >>> recommendation, rationale = recommend_ocr_routing(
        ...     PDFType.BORN_DIGITAL, dqs, 0.1, layouts
        ... )
        >>> recommendation
        <OCRRoutingRecommendation.OCR_FAST: 'ocr_fast'>
    """
    # Aggregate content attributes across all pages
    has_tables = any(page.has_tables for page in page_layout_summary)
    has_figures = any(page.has_figures for page in page_layout_summary)
    has_handwriting = any(page.has_handwriting for page in page_layout_summary)

    # Determine if layout is simple (single or multi-column, not complex)
    # Handle edge case: empty page_layout_summary is NOT simple
    # UNKNOWN layout is treated conservatively as complex for routing safety
    is_simple_layout = len(page_layout_summary) > 0 and all(
        page.layout_type in (LayoutType.SINGLE_COLUMN, LayoutType.MULTI_COLUMN)
        for page in page_layout_summary
    )

    # Decision Tree Implementation
    # Rule 1: Documents with tables or figures → vision-based structured extraction
    # (Evaluated first as it takes precedence over other rules)
    if has_tables or has_figures:
        content_types = []
        if has_tables:
            content_types.append("tables")
        if has_figures:
            content_types.append("figures")
        rationale = (
            f"Document contains {' and '.join(content_types)}. "
            f"Vision-based structured extraction recommended."
        )
        return OCRRoutingRecommendation.VISION_STRUCTURED, rationale

    # Rule 2: High-risk documents or handwriting → advanced OCR
    # (Evaluated before born-digital fast path to ensure safety)
    if pre_ocr_risk > 0.6 or has_handwriting:
        reasons = []
        if pre_ocr_risk > 0.6:
            reasons.append(f"high OCR risk score ({pre_ocr_risk:.2f})")
        if has_handwriting:
            reasons.append("handwriting detected")
        rationale = f"Advanced OCR required due to: {', '.join(reasons)}."
        return OCRRoutingRecommendation.OCR_ADVANCED, rationale

    # Rule 3: Born-digital PDFs with good quality and simple layout → fast OCR
    if (
        pdf_type == PDFType.BORN_DIGITAL
        and dqs.degradation_score > 0.8  # High score = low degradation (pristine)
        and is_simple_layout
    ):
        rationale = (
            f"Born-digital PDF with excellent quality (degradation={dqs.degradation_score:.2f}) "
            f"and simple layout. Fast OCR sufficient."
        )
        return OCRRoutingRecommendation.OCR_FAST, rationale

    # Rule 4: Image-only PDFs with simple layout → simple vision extraction
    if pdf_type == PDFType.IMAGE_ONLY and is_simple_layout:
        rationale = (
            "Image-only PDF with simple layout. "
            "Vision-based simple extraction appropriate."
        )
        return OCRRoutingRecommendation.VISION_SIMPLE, rationale

    # Rule 5: Conservative fallback for all other cases
    rationale = (
        f"Conservative fallback: pdf_type={pdf_type}, "
        f"degradation={dqs.degradation_score:.2f}, "
        f"complexity={dqs.structural_complexity_score:.2f}, "
        f"risk={pre_ocr_risk:.2f}. "
        f"Using advanced OCR for safety."
    )
    return OCRRoutingRecommendation.OCR_ADVANCED, rationale
