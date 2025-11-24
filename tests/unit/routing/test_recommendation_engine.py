"""Unit tests for OCR Routing Recommendation Engine.

Tests cover all decision tree branches:
1. Documents with tables/figures → VISION_STRUCTURED
2. Born-digital with good quality and simple layout → OCR_FAST
3. High pre-OCR risk or handwriting → OCR_ADVANCED
4. Image-only with simple layout → VISION_SIMPLE
5. Conservative fallback → OCR_ADVANCED
"""

import pytest

from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.schema import (
    DocumentQualityScore,
    LayoutType,
    OCRRoutingRecommendation,
    PageLayoutSummary,
    PDFType,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_layout() -> PageLayoutSummary:
    """Create a simple single-column page layout."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.1,
    )


@pytest.fixture
def multi_column_layout() -> PageLayoutSummary:
    """Create a multi-column page layout."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.MULTI_COLUMN,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.3,
    )


@pytest.fixture
def table_layout() -> PageLayoutSummary:
    """Create a page layout with tables."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,
        has_tables=True,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.5,
    )


@pytest.fixture
def figure_layout() -> PageLayoutSummary:
    """Create a page layout with figures."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,
        has_tables=False,
        has_figures=True,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.4,
    )


@pytest.fixture
def handwriting_layout() -> PageLayoutSummary:
    """Create a page layout with handwriting."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=True,
        complexity_score=0.6,
    )


@pytest.fixture
def complex_layout() -> PageLayoutSummary:
    """Create a complex page layout."""
    return PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.COMPLEX,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.8,
    )


@pytest.fixture
def high_quality_dqs() -> DocumentQualityScore:
    """Create high quality document score (low degradation)."""
    return DocumentQualityScore(
        degradation_score=0.9,  # High = good quality
        structural_complexity_score=0.2,
    )


@pytest.fixture
def low_quality_dqs() -> DocumentQualityScore:
    """Create low quality document score (high degradation)."""
    return DocumentQualityScore(
        degradation_score=0.3,  # Low = poor quality
        structural_complexity_score=0.7,
    )


# =============================================================================
# Rule 1: Tables/Figures → VISION_STRUCTURED
# =============================================================================


@pytest.mark.unit
class TestVisionStructuredRouting:
    """Tests for VISION_STRUCTURED routing (tables/figures)."""

    def test_tables_trigger_vision_structured(
        self, table_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that tables trigger VISION_STRUCTURED routing."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[table_layout],
        )

        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED
        assert "tables" in rationale.lower()

    def test_figures_trigger_vision_structured(
        self, figure_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that figures trigger VISION_STRUCTURED routing."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[figure_layout],
        )

        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED
        assert "figures" in rationale.lower()

    def test_tables_and_figures_both_mentioned(
        self, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that both tables and figures are mentioned in rationale."""
        layout_with_both = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=True,
            has_figures=True,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.6,
        )

        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.9,  # Even with high risk, tables/figures take precedence
            page_layout_summary=[layout_with_both],
        )

        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED
        assert "tables" in rationale.lower()
        assert "figures" in rationale.lower()


# =============================================================================
# Rule 2: Born-digital + High Quality + Simple Layout → OCR_FAST
# =============================================================================


@pytest.mark.unit
class TestOCRFastRouting:
    """Tests for OCR_FAST routing (born-digital + high quality)."""

    def test_born_digital_high_quality_simple_layout(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that born-digital + high quality + simple layout → OCR_FAST."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[simple_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_FAST
        assert "born-digital" in rationale.lower()
        assert "fast" in rationale.lower()

    def test_born_digital_with_multi_column_still_fast(
        self, multi_column_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that multi-column layout is still considered simple."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[multi_column_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_FAST

    def test_born_digital_low_quality_not_fast(
        self, simple_layout: PageLayoutSummary, low_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that low quality prevents OCR_FAST routing."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=low_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[simple_layout],
        )

        # Should fall through to conservative fallback
        assert recommendation != OCRRoutingRecommendation.OCR_FAST


# =============================================================================
# Rule 3: High Risk or Handwriting → OCR_ADVANCED
# =============================================================================


@pytest.mark.unit
class TestOCRAdvancedRouting:
    """Tests for OCR_ADVANCED routing (high risk/handwriting)."""

    def test_high_risk_triggers_advanced(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that high pre-OCR risk triggers OCR_ADVANCED."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.7,  # > 0.6 threshold
            page_layout_summary=[simple_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED
        assert "risk" in rationale.lower()

    def test_handwriting_triggers_advanced(
        self, handwriting_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that handwriting triggers OCR_ADVANCED."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[handwriting_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED
        assert "handwriting" in rationale.lower()

    def test_risk_threshold_boundary(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that exactly 0.6 risk does NOT trigger advanced (> not >=)."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.6,  # Exactly at threshold, should NOT trigger
            page_layout_summary=[simple_layout],
        )

        # At exactly 0.6, should fall through to VISION_SIMPLE for image-only
        assert recommendation == OCRRoutingRecommendation.VISION_SIMPLE


# =============================================================================
# Rule 4: Image-only + Simple Layout → VISION_SIMPLE
# =============================================================================


@pytest.mark.unit
class TestVisionSimpleRouting:
    """Tests for VISION_SIMPLE routing (image-only + simple)."""

    def test_image_only_simple_layout(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that image-only + simple layout → VISION_SIMPLE."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.3,
            page_layout_summary=[simple_layout],
        )

        assert recommendation == OCRRoutingRecommendation.VISION_SIMPLE
        assert "image-only" in rationale.lower()

    def test_image_only_complex_layout_not_simple(
        self, complex_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that complex layout prevents VISION_SIMPLE routing."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.3,
            page_layout_summary=[complex_layout],
        )

        # Should fall through to conservative fallback
        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED


# =============================================================================
# Rule 5: Conservative Fallback → OCR_ADVANCED
# =============================================================================


@pytest.mark.unit
class TestConservativeFallback:
    """Tests for conservative fallback routing."""

    def test_hybrid_pdf_falls_through(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that hybrid PDF type falls through to conservative fallback."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.HYBRID,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.3,
            page_layout_summary=[simple_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED
        assert "conservative" in rationale.lower() or "fallback" in rationale.lower()

    def test_none_pdf_type_falls_through(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that None PDF type falls through to conservative fallback."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=None,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.3,
            page_layout_summary=[simple_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED

    def test_empty_layout_summary_falls_through(
        self, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that empty page layout summary falls through to fallback."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.3,
            page_layout_summary=[],  # Empty
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED


# =============================================================================
# Multi-page Document Tests
# =============================================================================


@pytest.mark.unit
class TestMultiPageDocuments:
    """Tests for multi-page document routing."""

    def test_any_page_with_table_triggers_vision_structured(
        self, simple_layout: PageLayoutSummary, table_layout: PageLayoutSummary,
        high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that any page with tables triggers VISION_STRUCTURED."""
        # First page simple, second page has table
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[simple_layout, table_layout],
        )

        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED

    def test_any_page_with_handwriting_triggers_advanced(
        self, simple_layout: PageLayoutSummary, handwriting_layout: PageLayoutSummary,
        high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that any page with handwriting triggers OCR_ADVANCED."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[simple_layout, handwriting_layout],
        )

        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED

    def test_mixed_layouts_not_considered_simple(
        self, simple_layout: PageLayoutSummary, complex_layout: PageLayoutSummary,
        high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that mixed simple/complex layouts are not considered simple."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[simple_layout, complex_layout],
        )

        # Complex page prevents OCR_FAST
        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_rationale_always_returned(
        self, simple_layout: PageLayoutSummary, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that rationale is always a non-empty string."""
        for pdf_type in [PDFType.BORN_DIGITAL, PDFType.IMAGE_ONLY, PDFType.HYBRID, None]:
            recommendation, rationale = recommend_ocr_routing(
                pdf_type=pdf_type,
                dqs=high_quality_dqs,
                pre_ocr_risk=0.3,
                page_layout_summary=[simple_layout],
            )
            assert isinstance(rationale, str)
            assert len(rationale) > 0

    def test_unknown_layout_not_simple(
        self, high_quality_dqs: DocumentQualityScore
    ) -> None:
        """Test that UNKNOWN layout type is not treated as simple."""
        unknown_layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.UNKNOWN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.5,
        )

        recommendation, rationale = recommend_ocr_routing(
            pdf_type=PDFType.BORN_DIGITAL,
            dqs=high_quality_dqs,
            pre_ocr_risk=0.2,
            page_layout_summary=[unknown_layout],
        )

        # UNKNOWN should not be treated as simple, so should fall through
        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED


# =============================================================================
# Parametrized Tests for Comprehensive Coverage
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "has_tables,has_figures,expected",
    [
        (True, False, OCRRoutingRecommendation.VISION_STRUCTURED),
        (False, True, OCRRoutingRecommendation.VISION_STRUCTURED),
        (True, True, OCRRoutingRecommendation.VISION_STRUCTURED),
    ],
    ids=["tables_only", "figures_only", "tables_and_figures"],
)
def test_vision_structured_triggers(
    has_tables: bool, has_figures: bool, expected: OCRRoutingRecommendation
) -> None:
    """Parametrized test for VISION_STRUCTURED routing triggers."""
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,
        has_tables=has_tables,
        has_figures=has_figures,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.5,
    )
    dqs = DocumentQualityScore(degradation_score=0.9, structural_complexity_score=0.3)

    recommendation, _ = recommend_ocr_routing(
        pdf_type=PDFType.BORN_DIGITAL,
        dqs=dqs,
        pre_ocr_risk=0.2,
        page_layout_summary=[layout],
    )

    assert recommendation == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "pdf_type,degradation_score,layout_type,pre_ocr_risk,expected",
    [
        # Rule 2: Born-digital + high quality + simple → OCR_FAST
        (PDFType.BORN_DIGITAL, 0.9, LayoutType.SINGLE_COLUMN, 0.2, OCRRoutingRecommendation.OCR_FAST),
        (PDFType.BORN_DIGITAL, 0.9, LayoutType.MULTI_COLUMN, 0.2, OCRRoutingRecommendation.OCR_FAST),
        # Rule 3: High risk → OCR_ADVANCED
        (PDFType.BORN_DIGITAL, 0.9, LayoutType.SINGLE_COLUMN, 0.7, OCRRoutingRecommendation.OCR_ADVANCED),
        # Rule 4: Image-only + simple → VISION_SIMPLE
        (PDFType.IMAGE_ONLY, 0.9, LayoutType.SINGLE_COLUMN, 0.3, OCRRoutingRecommendation.VISION_SIMPLE),
        # Rule 5: Fallback cases
        (PDFType.HYBRID, 0.9, LayoutType.SINGLE_COLUMN, 0.3, OCRRoutingRecommendation.OCR_ADVANCED),
        (PDFType.IMAGE_ONLY, 0.9, LayoutType.COMPLEX, 0.3, OCRRoutingRecommendation.OCR_ADVANCED),
    ],
    ids=[
        "born_digital_high_quality_single",
        "born_digital_high_quality_multi",
        "high_risk_triggers_advanced",
        "image_only_simple_vision",
        "hybrid_falls_through",
        "complex_layout_falls_through",
    ],
)
def test_routing_decision_tree(
    pdf_type: PDFType,
    degradation_score: float,
    layout_type: LayoutType,
    pre_ocr_risk: float,
    expected: OCRRoutingRecommendation,
) -> None:
    """Parametrized test covering all major routing decision tree paths."""
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=layout_type,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.3,
    )
    dqs = DocumentQualityScore(
        degradation_score=degradation_score,
        structural_complexity_score=0.3,
    )

    recommendation, _ = recommend_ocr_routing(
        pdf_type=pdf_type,
        dqs=dqs,
        pre_ocr_risk=pre_ocr_risk,
        page_layout_summary=[layout],
    )

    assert recommendation == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "layout_type",
    [
        LayoutType.SINGLE_COLUMN,
        LayoutType.MULTI_COLUMN,
    ],
    ids=["single_column", "multi_column"],
)
def test_simple_layouts_for_ocr_fast(layout_type: LayoutType) -> None:
    """Parametrized test that simple layout types qualify for OCR_FAST."""
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=layout_type,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.2,
    )
    dqs = DocumentQualityScore(degradation_score=0.9, structural_complexity_score=0.2)

    recommendation, _ = recommend_ocr_routing(
        pdf_type=PDFType.BORN_DIGITAL,
        dqs=dqs,
        pre_ocr_risk=0.2,
        page_layout_summary=[layout],
    )

    assert recommendation == OCRRoutingRecommendation.OCR_FAST


@pytest.mark.unit
@pytest.mark.parametrize(
    "layout_type",
    [
        LayoutType.THREE_COLUMN,
        LayoutType.COMPLEX,
        LayoutType.UNKNOWN,
    ],
    ids=["three_column", "complex", "unknown"],
)
def test_complex_layouts_disqualify_ocr_fast(layout_type: LayoutType) -> None:
    """Parametrized test that complex layout types don't qualify for OCR_FAST."""
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=layout_type,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=0.6,
    )
    dqs = DocumentQualityScore(degradation_score=0.9, structural_complexity_score=0.2)

    recommendation, _ = recommend_ocr_routing(
        pdf_type=PDFType.BORN_DIGITAL,
        dqs=dqs,
        pre_ocr_risk=0.2,
        page_layout_summary=[layout],
    )

    # Should fall through to OCR_ADVANCED (not OCR_FAST)
    assert recommendation != OCRRoutingRecommendation.OCR_FAST
