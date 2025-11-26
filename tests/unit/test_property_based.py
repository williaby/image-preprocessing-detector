"""
Property-based testing examples using Hypothesis.

Property-based testing generates random test cases to verify invariants
and find edge cases that traditional example-based tests might miss.

These examples demonstrate:
1. Data validation invariants (schema constraints)
2. Roundtrip serialization (JSON encode/decode)
3. Idempotent operations (corrections don't change twice)
4. Boundary conditions (confidence scores, coordinates)
"""

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import composite
from pydantic import ValidationError

from image_preprocessing_detector.schema import (
    DetectedIssue,
    DocumentElement,
    DocumentMetadata,
    ElementCategory,
    IssueSeverity,
    IssueType,
    PageMetadata,
    ProcessingVersion,
    TransformHistory,
)
from image_preprocessing_detector.utils.datetime_compat import UTC, datetime


# Custom Hypothesis strategies for domain-specific types
@composite
def confidence_scores(draw: Any) -> float:
    """Generate valid confidence scores (0.0 to 1.0)."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@composite
def bounding_boxes(draw: Any) -> list[int]:
    """Generate valid COCO-format bounding boxes [x, y, width, height]."""
    x = draw(st.integers(min_value=0, max_value=1000))
    y = draw(st.integers(min_value=0, max_value=1000))
    width = draw(st.integers(min_value=1, max_value=500))
    height = draw(st.integers(min_value=1, max_value=500))
    return [x, y, width, height]


@composite
def detected_issues(draw: Any) -> DetectedIssue:
    """Generate valid DetectedIssue instances."""
    issue_type = draw(st.sampled_from(list(IssueType)))
    confidence = draw(confidence_scores())
    severity = draw(st.sampled_from(list(IssueSeverity)))

    return DetectedIssue(
        type=issue_type,
        confidence=confidence,
        severity=severity,
        metrics={"test_metric": draw(st.floats(allow_nan=False))},
    )


@composite
def document_elements(draw: Any) -> DocumentElement:
    """Generate valid DocumentElement instances."""
    element_id = draw(st.text(min_size=1, max_size=50))
    category = draw(st.sampled_from(list(ElementCategory)))
    bbox = draw(bounding_boxes())
    confidence = draw(confidence_scores())
    quality_issues = draw(st.lists(detected_issues(), max_size=3))

    return DocumentElement(
        id=element_id,
        category=category,
        bbox=bbox,
        confidence=confidence,
        quality_issues=quality_issues,
    )


class TestPropertyBasedValidation:
    """Property-based tests for schema validation invariants."""

    @given(confidence_scores())
    def test_confidence_always_in_valid_range(self, confidence: float) -> None:
        """Property: All generated confidence scores must be valid."""
        # This property should always hold
        assert 0.0 <= confidence <= 1.0

        # Pydantic validation should accept it
        issue = DetectedIssue(
            type=IssueType.BLUR,
            confidence=confidence,
            severity=IssueSeverity.LOW,
        )
        assert issue.confidence == confidence

    @given(st.floats())
    def test_invalid_confidence_rejected(self, value: float) -> None:
        """Property: Values outside [0,1] should be rejected."""
        # Skip NaN and valid range
        if math.isnan(value) or 0.0 <= value <= 1.0:
            return

        # Values outside valid range should raise ValidationError
        with pytest.raises(ValidationError):
            DetectedIssue(
                type=IssueType.BLUR,
                confidence=value,
                severity=IssueSeverity.LOW,
            )

    @given(bounding_boxes())
    def test_bounding_box_format_invariant(self, bbox: list[int]) -> None:
        """Property: COCO bounding boxes must be [x, y, width, height]."""
        assert len(bbox) == 4
        x, y, width, height = bbox
        assert x >= 0
        assert y >= 0
        assert width > 0
        assert height > 0

    @given(detected_issues())
    def test_detected_issue_roundtrip_serialization(self, issue: DetectedIssue) -> None:
        """Property: Serialize → deserialize should be identity."""
        # Serialize to dict
        serialized = issue.model_dump()

        # Deserialize back
        deserialized = DetectedIssue(**serialized)

        # Should be equivalent
        assert deserialized.type == issue.type
        assert deserialized.confidence == issue.confidence
        assert deserialized.severity == issue.severity

    @given(detected_issues())
    def test_detected_issue_json_roundtrip(self, issue: DetectedIssue) -> None:
        """Property: JSON encode → decode should preserve data."""
        # Serialize to JSON string
        json_str = issue.model_dump_json()

        # Deserialize from JSON
        deserialized = DetectedIssue.model_validate_json(json_str)

        # Should be equivalent (within floating point precision)
        assert deserialized.type == issue.type
        assert abs(deserialized.confidence - issue.confidence) < 1e-6
        assert deserialized.severity == issue.severity

    @given(document_elements())
    def test_document_element_bbox_length(self, element: DocumentElement) -> None:
        """Property: All document elements must have 4-element bboxes."""
        assert len(element.bbox) == 4
        x, y, w, h = element.bbox
        assert x >= 0
        assert y >= 0
        assert w > 0
        assert h > 0

    @given(
        st.lists(
            document_elements(),
            min_size=0,
            max_size=10,
        )
    )
    def test_page_metadata_element_collection(
        self, elements: list[DocumentElement]
    ) -> None:
        """Property: PageMetadata can contain any number of valid elements."""
        page = PageMetadata(
            page_index=0,
            width_px=1000,
            height_px=1200,
            dpi_input=300,
            dpi_effective=300,
            elements=elements,
        )

        assert len(page.elements) == len(elements)
        assert page.page_index == 0

    @given(st.integers(min_value=0, max_value=999))
    def test_page_index_must_be_non_negative(self, page_idx: int) -> None:
        """Property: Page indices must be non-negative integers."""
        page = PageMetadata(
            page_index=page_idx,
            width_px=1000,
            height_px=1200,
            dpi_input=300,
            dpi_effective=300,
        )
        assert page.page_index >= 0


class TestPropertyBasedTransformations:
    """Property-based tests for correction transformations."""

    @given(
        st.floats(min_value=-180.0, max_value=180.0, allow_nan=False),
        confidence_scores(),
    )
    def test_transform_history_records_angle(
        self, angle: float, confidence: float
    ) -> None:
        """Property: Transform history should record skew corrections."""
        now = datetime.now(UTC)
        transform = TransformHistory(
            action="deskew",
            params={"angle": angle, "confidence": confidence},
            started_at=now,
            finished_at=now,
            status="success",
        )

        assert transform.action == "deskew"
        assert transform.params["angle"] == angle
        assert transform.status == "success"

    @given(
        st.lists(
            st.builds(
                TransformHistory,
                action=st.sampled_from(["deskew", "denoise", "contrast", "sharpen"]),
                params=st.dictionaries(
                    st.text(min_size=1, max_size=10),
                    st.floats(allow_nan=False),
                    min_size=0,
                    max_size=3,
                ),
                started_at=st.datetimes(
                    min_value=datetime(2020, 1, 1),
                    max_value=datetime(2023, 12, 31),
                    timezones=st.just(UTC),
                ),
                finished_at=st.datetimes(
                    min_value=datetime(2024, 1, 1),
                    max_value=datetime(2025, 12, 31),
                    timezones=st.just(UTC),
                ),
                status=st.sampled_from(["success", "failed", "skipped"]),
            ),
            max_size=5,
        )
    )
    def test_document_metadata_transform_history(
        self, transforms: list[TransformHistory]
    ) -> None:
        """Property: Document metadata can track multiple transforms."""
        page = PageMetadata(
            page_index=0,
            width_px=1000,
            height_px=1200,
            dpi_input=300,
            dpi_effective=300,
        )
        doc = DocumentMetadata(
            document_id="test-doc",
            file_name="test.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="test-v1.0"),
            pages=[page],
        )

        # Add transform history
        for transform in transforms:
            doc.pages[0].transform_history.append(transform)

        assert len(doc.pages[0].transform_history) == len(transforms)


class TestPropertyBasedEdgeCases:
    """Property-based tests for boundary conditions and edge cases."""

    @given(st.integers(min_value=-100, max_value=5000))
    def test_page_dimensions_must_be_positive(self, dimension: int) -> None:
        """Property: Page dimensions must be positive."""
        if dimension <= 0:
            with pytest.raises(ValidationError):
                PageMetadata(
                    page_index=0,
                    width_px=dimension,
                    height_px=1000,
                    dpi_input=300,
                    dpi_effective=300,
                )
        else:
            page = PageMetadata(
                page_index=0,
                width_px=dimension,
                height_px=1000,
                dpi_input=300,
                dpi_effective=300,
            )
            assert page.width_px > 0

    @given(
        st.text(min_size=1, max_size=100),
        st.text(min_size=1, max_size=20),
    )
    def test_document_metadata_requires_id_and_version(
        self, doc_id: str, pipeline_version: str
    ) -> None:
        """Property: Document metadata requires ID and version."""
        page = PageMetadata(
            page_index=0,
            width_px=1000,
            height_px=1200,
            dpi_input=300,
            dpi_effective=300,
        )
        version = ProcessingVersion(pipeline_version=pipeline_version)
        doc = DocumentMetadata(
            document_id=doc_id,
            file_name="test.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=version,
            pages=[page],
        )

        assert len(doc.document_id) > 0
        assert doc.processing_version == version
        assert len(doc.pages) > 0

    @given(
        st.lists(
            st.builds(
                PageMetadata,
                page_index=st.integers(min_value=0, max_value=999),
                width_px=st.integers(min_value=100, max_value=5000),
                height_px=st.integers(min_value=100, max_value=5000),
                dpi_input=st.integers(min_value=72, max_value=600),
                dpi_effective=st.integers(min_value=72, max_value=600),
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_document_with_many_pages(self, pages: list[PageMetadata]) -> None:
        """Property: Documents can have arbitrary number of pages."""
        doc = DocumentMetadata(
            document_id="multi-page-doc",
            file_name="test.pdf",
            source_mime="application/pdf",
            num_pages=len(pages),
            processing_version=ProcessingVersion(pipeline_version="test-v1.0"),
            pages=pages,
        )

        assert len(doc.pages) == len(pages)
        assert all(p.page_index >= 0 for p in doc.pages)


# Example of how to use Hypothesis with existing code
class TestPropertyBasedIntegration:
    """Integration tests using property-based testing."""

    @given(
        st.lists(detected_issues(), min_size=1, max_size=10),
    )
    def test_quality_issues_serialization(self, issues: list[DetectedIssue]) -> None:
        """Property: Quality issues can be serialized to JSON."""
        element = DocumentElement(
            id="test-element-1",
            category=ElementCategory.TEXT_BLOCK,
            bbox=[0, 0, 100, 100],
            confidence=0.9,
            quality_issues=issues,
        )

        # Serialize to JSON
        json_str = element.model_dump_json()

        # Deserialize
        deserialized = DocumentElement.model_validate_json(json_str)

        # Should have same number of issues
        assert len(deserialized.quality_issues) == len(issues)


# =============================================================================
# DQS Calculator Property-Based Tests (Sprint 5.1.1)
# =============================================================================

from image_preprocessing_detector.metrics.dqs_calculator import (
    DQSWeightConfig,
    calculate_pre_ocr_risk,
    calculate_structural_complexity_score,
)
from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.schema import (
    DocumentQualityScore,
    DQSMetadata,
    LayoutType,
    OCRRoutingRecommendation,
    PageLayoutSummary,
    PDFType,
)


@composite
def dqs_weight_configs(draw: Any) -> DQSWeightConfig:
    """Generate valid DQS weight configurations."""
    return DQSWeightConfig(
        blur_weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        noise_weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        contrast_weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        illumination_weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        artifacts_weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        ml_blend_ratio=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@composite
def degradation_scores(draw: Any) -> float:
    """Generate valid degradation scores (0.0 to 1.0)."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@composite
def page_layout_summaries(draw: Any) -> PageLayoutSummary:
    """Generate valid PageLayoutSummary instances."""
    return PageLayoutSummary(
        page_number=draw(st.integers(min_value=1, max_value=999)),
        layout_type=draw(st.sampled_from(list(LayoutType))),
        has_tables=draw(st.booleans()),
        has_figures=draw(st.booleans()),
        has_dense_math=draw(st.booleans()),
        has_handwriting=draw(st.booleans()),
        complexity_score=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@composite
def document_quality_scores(draw: Any) -> DocumentQualityScore:
    """Generate valid DocumentQualityScore instances."""
    return DocumentQualityScore(
        degradation_score=draw(degradation_scores()),
        structural_complexity_score=draw(degradation_scores()),
    )


class TestDQSWeightConfigProperties:
    """Property-based tests for DQS weight configuration."""

    @given(dqs_weight_configs())
    def test_all_weights_non_negative(self, config: DQSWeightConfig) -> None:
        """Property: All weights must be non-negative."""
        assert config.blur_weight >= 0
        assert config.noise_weight >= 0
        assert config.contrast_weight >= 0
        assert config.illumination_weight >= 0
        assert config.artifacts_weight >= 0
        assert config.ml_blend_ratio >= 0

    @given(dqs_weight_configs())
    def test_ml_blend_ratio_in_valid_range(self, config: DQSWeightConfig) -> None:
        """Property: ML blend ratio must be between 0 and 1."""
        assert 0.0 <= config.ml_blend_ratio <= 1.0

    @given(
        st.floats(min_value=0.01, max_value=1.0),
        st.floats(min_value=0.01, max_value=1.0),
        st.floats(min_value=0.01, max_value=1.0),
    )
    def test_normalized_weights_sum_to_one(
        self, w1: float, w2: float, w3: float
    ) -> None:
        """Property: Normalized degradation weights should sum to 1.0."""
        config = DQSWeightConfig(
            blur_weight=w1,
            noise_weight=w2,
            contrast_weight=w3,
            illumination_weight=0.0,
            artifacts_weight=0.0,
        )
        weights = config.get_normalized_degradation_weights()
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6


class TestDQSCalculatorProperties:
    """Property-based tests for DQS calculations."""

    @given(
        degradation_scores(),
        degradation_scores(),
        st.sampled_from([None] + list(PDFType)),
    )
    def test_pre_ocr_risk_in_valid_range(
        self, degradation: float, complexity: float, pdf_type: PDFType | None
    ) -> None:
        """Property: Pre-OCR risk must be between 0 and 1."""
        dqs = DQSMetadata(
            degradation_score=degradation,
            structural_complexity_score=complexity,
        )
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=complexity,
        )
        risk = calculate_pre_ocr_risk(dqs, pdf_type, [layout])
        assert 0.0 <= risk <= 1.0

    @given(
        degradation_scores(),
        degradation_scores(),
        st.sampled_from([None] + list(PDFType)),
    )
    def test_pre_ocr_risk_increases_with_worse_quality(
        self, base_degradation: float, complexity: float, pdf_type: PDFType | None
    ) -> None:
        """Property: Higher degradation (lower score) → higher risk."""
        # Lower degradation score means worse quality
        low_quality_degradation = max(0.0, base_degradation - 0.2)
        high_quality_degradation = min(1.0, base_degradation + 0.2)

        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=complexity,
        )

        low_risk = calculate_pre_ocr_risk(
            DQSMetadata(
                degradation_score=high_quality_degradation,
                structural_complexity_score=complexity,
            ),
            pdf_type,
            [layout],
        )
        high_risk = calculate_pre_ocr_risk(
            DQSMetadata(
                degradation_score=low_quality_degradation,
                structural_complexity_score=complexity,
            ),
            pdf_type,
            [layout],
        )

        # Lower degradation score (worse quality) should give higher risk
        assert high_risk >= low_risk or abs(high_risk - low_risk) < 0.01

    @given(st.sampled_from(list(LayoutType)))
    def test_structural_complexity_in_valid_range(
        self, layout_type: LayoutType
    ) -> None:
        """Property: Structural complexity must be between 0 and 1."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=layout_type,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.5,
        )
        complexity = calculate_structural_complexity_score(layout)
        assert 0.0 <= complexity <= 1.0

    @given(page_layout_summaries())
    def test_structural_complexity_always_valid(
        self, layout: PageLayoutSummary
    ) -> None:
        """Property: Structural complexity is valid for any layout."""
        complexity = calculate_structural_complexity_score(layout)
        assert 0.0 <= complexity <= 1.0


class TestRoutingRecommendationProperties:
    """Property-based tests for OCR routing recommendations."""

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.lists(page_layout_summaries(), min_size=1, max_size=5),
    )
    def test_routing_returns_valid_recommendation(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
        layouts: list[PageLayoutSummary],
    ) -> None:
        """Property: Routing always returns valid recommendation."""
        recommendation, rationale = recommend_ocr_routing(
            pdf_type, dqs, pre_ocr_risk, layouts
        )
        assert recommendation in OCRRoutingRecommendation
        assert isinstance(rationale, str)
        assert len(rationale) > 0

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.lists(page_layout_summaries(), min_size=1, max_size=5),
    )
    def test_routing_is_deterministic(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
        layouts: list[PageLayoutSummary],
    ) -> None:
        """Property: Same inputs should always produce same outputs."""
        result1 = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        result2 = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        assert result1[0] == result2[0]

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.0, max_value=0.6, allow_nan=False),
    )
    def test_tables_always_route_to_vision_structured(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
    ) -> None:
        """Property: Documents with tables should route to vision_structured."""
        layouts = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=True,  # Has tables
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.5,
            )
        ]
        recommendation, _ = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.0, max_value=0.6, allow_nan=False),
    )
    def test_figures_always_route_to_vision_structured(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
    ) -> None:
        """Property: Documents with figures should route to vision_structured."""
        layouts = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=True,  # Has figures
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.5,
            )
        ]
        recommendation, _ = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.61, max_value=1.0, allow_nan=False),
    )
    def test_high_risk_never_routes_to_fast(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
    ) -> None:
        """Property: High risk documents should not route to ocr_fast."""
        layouts = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.5,
            )
        ]
        recommendation, _ = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        assert recommendation != OCRRoutingRecommendation.OCR_FAST

    @given(
        st.sampled_from([None] + list(PDFType)),
        document_quality_scores(),
        st.floats(min_value=0.0, max_value=0.6, allow_nan=False),
    )
    def test_handwriting_routes_to_advanced(
        self,
        pdf_type: PDFType | None,
        dqs: DocumentQualityScore,
        pre_ocr_risk: float,
    ) -> None:
        """Property: Documents with handwriting should route to ocr_advanced."""
        layouts = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=True,  # Has handwriting
                complexity_score=0.5,
            )
        ]
        recommendation, _ = recommend_ocr_routing(pdf_type, dqs, pre_ocr_risk, layouts)
        assert recommendation == OCRRoutingRecommendation.OCR_ADVANCED
