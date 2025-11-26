"""
Unit tests for JSON schema validation using Pydantic models.
"""

import json
from datetime import datetime

import pytest
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


class TestDetectedIssue:
    """Test DetectedIssue model validation."""

    def test_valid_issue(self) -> None:
        """Test creating a valid detected issue."""
        issue = DetectedIssue(
            type=IssueType.BLUR,
            confidence=0.87,
            severity=IssueSeverity.MEDIUM,
            metrics={"laplacian_variance": 125.4},
        )
        assert issue.type == IssueType.BLUR
        assert issue.confidence == pytest.approx(0.87)
        assert issue.severity == IssueSeverity.MEDIUM

    def test_confidence_validation(self) -> None:
        """Test confidence score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            DetectedIssue(
                type=IssueType.BLUR,
                confidence=1.5,  # Invalid: > 1.0
                severity=IssueSeverity.MEDIUM,
            )

        with pytest.raises(ValidationError):
            DetectedIssue(
                type=IssueType.BLUR,
                confidence=-0.1,  # Invalid: < 0.0
                severity=IssueSeverity.MEDIUM,
            )


class TestDocumentElement:
    """Test DocumentElement model validation."""

    def test_valid_element(self) -> None:
        """Test creating a valid document element."""
        element = DocumentElement(
            id="elem_001",
            category=ElementCategory.TABLE,
            bbox=[100, 200, 300, 400],
            confidence=0.95,
        )
        assert element.id == "elem_001"
        assert element.category == ElementCategory.TABLE
        assert len(element.bbox) == 4

    def test_bbox_validation(self) -> None:
        """Test bounding box must have exactly 4 values."""
        with pytest.raises(ValidationError):
            DocumentElement(
                id="elem_001",
                category=ElementCategory.TABLE,
                bbox=[100, 200, 300],  # Invalid: only 3 values
                confidence=0.95,
            )

    def test_element_with_quality_issues(self) -> None:
        """Test element with embedded quality issues (hybrid IQA)."""
        element = DocumentElement(
            id="elem_001",
            category=ElementCategory.IMAGE,
            bbox=[100, 200, 300, 400],
            confidence=0.95,
            quality_issues=[
                DetectedIssue(
                    type=IssueType.NOISE,
                    confidence=0.78,
                    severity=IssueSeverity.LOW,
                    metrics={"snr": 15.2},
                )
            ],
            needs_correction=True,
        )
        assert len(element.quality_issues) == 1
        assert element.needs_correction is True


class TestPageMetadata:
    """Test PageMetadata model."""

    def test_valid_page_metadata(self) -> None:
        """Test creating valid page metadata."""
        page = PageMetadata(
            page_index=0,
            width_px=2550,
            height_px=3300,
            dpi_input=200,
            dpi_effective=300,
        )
        assert page.page_index == 0
        assert page.dpi_effective == 300


class TestDocumentMetadata:
    """Test complete DocumentMetadata model."""

    def test_valid_document_metadata(self) -> None:
        """Test creating valid document metadata."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="sample.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(
                pipeline_version="0.1.0",
                iqa_model_hash="abc123",
                layout_model_hash="def456",
            ),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=200,
                    dpi_effective=300,
                )
            ],
        )
        assert metadata.num_pages == 1
        assert len(metadata.pages) == 1

    def test_pages_count_validation(self) -> None:
        """Test num_pages must match length of pages list."""
        with pytest.raises(ValidationError):
            DocumentMetadata(
                document_id="doc_001",
                file_name="sample.pdf",
                source_mime="application/pdf",
                num_pages=2,  # Says 2 pages
                processing_version=ProcessingVersion(pipeline_version="0.1.0"),
                pages=[  # But only provides 1 page
                    PageMetadata(
                        page_index=0,
                        width_px=2550,
                        height_px=3300,
                        dpi_input=200,
                        dpi_effective=300,
                    )
                ],
            )

    def test_json_serialization(self) -> None:
        """Test JSON serialization and deserialization."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="sample.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="0.1.0"),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=200,
                    dpi_effective=300,
                    detected_issues=[
                        DetectedIssue(
                            type=IssueType.BLUR,
                            confidence=0.87,
                            severity=IssueSeverity.MEDIUM,
                        )
                    ],
                )
            ],
        )

        # Serialize to JSON
        json_str = metadata.model_dump_json(indent=2)
        assert json_str is not None

        # Deserialize from JSON
        json_data = json.loads(json_str)
        restored = DocumentMetadata.model_validate(json_data)

        assert restored.document_id == metadata.document_id
        assert len(restored.pages) == len(metadata.pages)
        assert len(restored.pages[0].detected_issues) == 1


class TestTransformHistory:
    """Test TransformHistory model."""

    def test_valid_transform(self) -> None:
        """Test creating valid transform history entry."""
        started = datetime.now()  # noqa: DTZ005 (test fixture uses naive datetime)
        finished = datetime.now()  # noqa: DTZ005 (test fixture uses naive datetime)

        transform = TransformHistory(
            action="deskew",
            params={"angle": -3.2},
            started_at=started,
            finished_at=finished,
            status="success",
        )
        assert transform.action == "deskew"
        assert transform.status == "success"
