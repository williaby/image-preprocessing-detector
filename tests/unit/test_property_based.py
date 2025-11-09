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
from datetime import UTC, datetime
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


# Custom Hypothesis strategies for domain-specific types
@composite
def confidence_scores(draw: Any) -> float:
    """Generate valid confidence scores (0.0 to 1.0)."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@composite
def bounding_boxes(draw: Any) -> list[float]:
    """Generate valid COCO-format bounding boxes [x, y, width, height]."""
    x = draw(
        st.floats(
            min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        )
    )
    y = draw(
        st.floats(
            min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        )
    )
    width = draw(
        st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    height = draw(
        st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
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
    def test_bounding_box_format_invariant(self, bbox: list[float]) -> None:
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
                    min_value=datetime(2020, 1, 1),  # noqa: DTZ001
                    max_value=datetime(2023, 12, 31),  # noqa: DTZ001
                    timezones=st.just(UTC),
                ),
                finished_at=st.datetimes(
                    min_value=datetime(2024, 1, 1),  # noqa: DTZ001
                    max_value=datetime(2025, 12, 31),  # noqa: DTZ001
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
