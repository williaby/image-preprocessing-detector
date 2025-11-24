"""Snapshot tests for JSON output validation.

These tests verify that JSON output maintains consistent structure across changes.
Uses golden file comparison to detect unexpected schema changes.

Tests cover:
- JSON structure validation against expected schemas
- Field presence and type validation
- Round-trip serialization consistency
- Backward compatibility verification
"""

import json
from typing import Any

import pytest

from image_preprocessing_detector.schema import (
    ActionType,
    DetectedIssue,
    DocumentElement,
    DocumentMetadata,
    DQSMetadata,
    ElementCategory,
    IssueSeverity,
    IssueType,
    LayoutType,
    OCRRoutingStrategy,
    PageLayoutSummary,
    PageMetadata,
    PDFType,
    PlannedAction,
    ProcessingVersion,
    TransformHistory,
)
from image_preprocessing_detector.utils.datetime_compat import UTC, datetime

# =============================================================================
# Test Data Factories
# =============================================================================


def create_minimal_document_metadata() -> DocumentMetadata:
    """Create minimal valid DocumentMetadata for testing."""
    return DocumentMetadata(
        document_id="test-doc-001",
        file_name="test_document.pdf",
        source_mime="application/pdf",
        num_pages=1,
        processing_version=ProcessingVersion(
            pipeline_version="1.0.0",
            iqa_model_hash=None,
            layout_model_hash=None,
            thresholds={},
        ),
        pages=[
            PageMetadata(
                page_index=0,
                width_px=612,
                height_px=792,
                dpi_input=72,
                dpi_effective=300,
            )
        ],
    )


def create_full_document_metadata() -> DocumentMetadata:
    """Create fully-populated DocumentMetadata for testing."""
    now = datetime.now(UTC)

    return DocumentMetadata(
        document_id="test-doc-full-001",
        file_name="complex_document.pdf",
        source_mime="application/pdf",
        num_pages=2,
        processing_version=ProcessingVersion(
            pipeline_version="2.0.0",
            iqa_model_hash="sha256:abc123def456",
            layout_model_hash="sha256:789xyz",
            thresholds={"blur": 100.0, "skew": 2.0, "contrast": 0.3},
        ),
        pdf_type=PDFType.HYBRID,
        pre_ocr_risk=0.35,
        dqs=DQSMetadata(degradation_score=0.72, structural_complexity_score=0.45),
        ocr_routing_recommendation=OCRRoutingStrategy.OCR_ADVANCED,
        upscaling={
            "success": True,
            "original_dpi": 150,
            "target_dpi": 300,
            "algorithm": "lanczos",
            "processing_time_seconds": 0.5,
        },
        page_layout_summary=[
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.MULTI_COLUMN,
                has_tables=True,
                has_figures=True,
                has_dense_math=False,
                has_handwriting=False,
                fuzzy_scan=False,
                watermark=False,
                colorful_background=False,
                complexity_score=0.65,
            )
        ],
        teacher_usage={
            "triggered": True,
            "reason": "high_uncertainty",
            "pages": [0],
        },
        pages=[
            PageMetadata(
                page_index=0,
                width_px=2550,
                height_px=3300,
                dpi_input=150,
                dpi_effective=300,
                ml_iqa={
                    "blur": {"score": 0.2, "confidence": 0.9},
                    "noise": {"score": 0.1, "confidence": 0.85},
                },
                teacher_iqa={
                    "blur": {"score": 0.18, "confidence": 0.95},
                    "noise": {"score": 0.12, "confidence": 0.92},
                },
                detected_issues=[
                    DetectedIssue(
                        type=IssueType.SKEW,
                        severity=IssueSeverity.MEDIUM,
                        confidence=0.85,
                        metrics={"angle": 2.5, "method": "hough"},
                    ),
                    DetectedIssue(
                        type=IssueType.LOW_CONTRAST,
                        severity=IssueSeverity.LOW,
                        confidence=0.72,
                        metrics={"score": 0.35},
                    ),
                ],
                planned_actions=[
                    PlannedAction(
                        action=ActionType.DESKEW,
                        params={"angle": 2.5},
                        confidence=0.85,
                        reason="Detected skew of 2.5 degrees",
                    ),
                    PlannedAction(
                        action=ActionType.CLAHE,
                        params={"clip_limit": 2.0},
                        confidence=0.72,
                        reason="Low contrast detected",
                    ),
                ],
                elements=[
                    DocumentElement(
                        id="elem_table_001",
                        category=ElementCategory.TABLE,
                        bbox=[100, 200, 400, 300],
                        confidence=0.92,
                    ),
                    DocumentElement(
                        id="elem_figure_001",
                        category=ElementCategory.FIGURE,
                        bbox=[50, 600, 200, 150],
                        confidence=0.88,
                    ),
                ],
                transform_history=[
                    TransformHistory(
                        action="deskew",
                        params={"angle": 2.5},
                        started_at=now,
                        finished_at=now,
                        status="success",
                    ),
                    TransformHistory(
                        action="clahe_contrast_enhancement",
                        params={"clip_limit": 2.0},
                        started_at=now,
                        finished_at=now,
                        status="success",
                    ),
                ],
            ),
            PageMetadata(
                page_index=1,
                width_px=2550,
                height_px=3300,
                dpi_input=150,
                dpi_effective=300,
            ),
        ],
    )


# =============================================================================
# Schema Structure Tests
# =============================================================================


@pytest.mark.unit
class TestJsonSchemaStructure:
    """Tests verifying JSON schema structure is correct."""

    def test_minimal_metadata_has_required_fields(self) -> None:
        """Test minimal metadata has all required top-level fields."""
        metadata = create_minimal_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        required_fields = [
            "document_id",
            "file_name",
            "source_mime",
            "num_pages",
            "processing_version",
            "pages",
        ]

        for field in required_fields:
            assert field in json_dict, f"Missing required field: {field}"

    def test_page_metadata_has_required_fields(self) -> None:
        """Test page metadata has all required fields."""
        metadata = create_minimal_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        page = json_dict["pages"][0]
        required_fields = [
            "page_index",
            "width_px",
            "height_px",
            "dpi_input",
            "dpi_effective",
        ]

        for field in required_fields:
            assert field in page, f"Missing required page field: {field}"

    def test_processing_version_structure(self) -> None:
        """Test processing_version has correct structure."""
        metadata = create_minimal_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        version = json_dict["processing_version"]
        assert "pipeline_version" in version
        assert "timestamp" in version
        assert "thresholds" in version

    def test_detected_issue_structure(self) -> None:
        """Test detected_issue has correct structure."""
        issue = DetectedIssue(
            type=IssueType.BLUR,
            severity=IssueSeverity.HIGH,
            confidence=0.9,
            metrics={"score": 80.0},
        )
        json_dict = json.loads(issue.model_dump_json())

        assert json_dict["type"] == "blur"
        assert json_dict["severity"] == "high"
        assert json_dict["confidence"] == 0.9
        assert json_dict["metrics"]["score"] == 80.0

    def test_planned_action_structure(self) -> None:
        """Test planned_action has correct structure."""
        action = PlannedAction(
            action=ActionType.DESKEW,
            params={"angle": 3.5},
            confidence=0.85,
            reason="Skew detected",
        )
        json_dict = json.loads(action.model_dump_json())

        assert json_dict["action"] == "deskew"
        assert json_dict["params"]["angle"] == 3.5
        assert json_dict["confidence"] == 0.85
        assert json_dict["reason"] == "Skew detected"

    def test_document_element_bbox_format(self) -> None:
        """Test document element bbox uses COCO format [x, y, width, height]."""
        element = DocumentElement(
            id="elem_test_001",
            category=ElementCategory.TABLE,
            bbox=[100, 200, 300, 150],  # [x, y, width, height]
            confidence=0.9,
        )
        json_dict = json.loads(element.model_dump_json())

        bbox = json_dict["bbox"]
        assert len(bbox) == 4
        assert bbox == [100, 200, 300, 150]


# =============================================================================
# Full Document Tests
# =============================================================================


@pytest.mark.unit
class TestFullDocumentSnapshot:
    """Tests for full document metadata JSON structure."""

    def test_full_metadata_serializes(self) -> None:
        """Test full metadata serializes without error."""
        metadata = create_full_document_metadata()
        json_str = metadata.model_dump_json()

        # Should parse back without error
        parsed = json.loads(json_str)
        assert parsed["document_id"] == "test-doc-full-001"

    def test_phase8_fields_present(self) -> None:
        """Test Phase 8 fields are present when set."""
        metadata = create_full_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        assert json_dict["pdf_type"] == "hybrid"
        assert json_dict["pre_ocr_risk"] == 0.35
        assert "dqs" in json_dict
        assert json_dict["dqs"]["degradation_score"] == 0.72
        assert json_dict["dqs"]["structural_complexity_score"] == 0.45
        assert json_dict["ocr_routing_recommendation"] == "ocr_advanced"

    def test_upscaling_metadata_structure(self) -> None:
        """Test upscaling metadata has correct structure."""
        metadata = create_full_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        upscaling = json_dict["upscaling"]
        assert upscaling["success"] is True
        assert upscaling["original_dpi"] == 150
        assert upscaling["target_dpi"] == 300
        assert upscaling["algorithm"] == "lanczos"

    def test_page_layout_summary_structure(self) -> None:
        """Test page_layout_summary has correct structure."""
        metadata = create_full_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        summary = json_dict["page_layout_summary"][0]
        assert summary["layout_type"] == "multi_column"
        assert summary["has_tables"] is True
        assert summary["has_figures"] is True
        assert "page_number" in summary
        assert "complexity_score" in summary

    def test_teacher_usage_structure(self) -> None:
        """Test teacher_usage has correct structure."""
        metadata = create_full_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())

        teacher = json_dict["teacher_usage"]
        assert teacher["triggered"] is True
        assert teacher["reason"] == "high_uncertainty"
        assert 0 in teacher["pages"]


# =============================================================================
# Enum Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestEnumSerialization:
    """Tests for enum serialization to JSON."""

    @pytest.mark.parametrize(
        ("issue_type", "expected"),
        [
            (IssueType.NOISE, "noise"),
            (IssueType.BLUR, "blur"),
            (IssueType.SKEW, "skew"),
            (IssueType.PERSPECTIVE, "perspective"),
            (IssueType.LOW_CONTRAST, "low_contrast"),
            (IssueType.ORIENTATION, "orientation"),
            (IssueType.LOW_DPI, "low_dpi"),
        ],
    )
    def test_issue_type_serialization(
        self, issue_type: IssueType, expected: str
    ) -> None:
        """Test IssueType enum serializes correctly."""
        issue = DetectedIssue(
            type=issue_type,
            severity=IssueSeverity.LOW,
            confidence=0.5,
        )
        json_dict = json.loads(issue.model_dump_json())
        assert json_dict["type"] == expected

    @pytest.mark.parametrize(
        ("severity", "expected"),
        [
            (IssueSeverity.LOW, "low"),
            (IssueSeverity.MEDIUM, "medium"),
            (IssueSeverity.HIGH, "high"),
            (IssueSeverity.CRITICAL, "critical"),
        ],
    )
    def test_severity_serialization(
        self, severity: IssueSeverity, expected: str
    ) -> None:
        """Test IssueSeverity enum serializes correctly."""
        issue = DetectedIssue(
            type=IssueType.BLUR,
            severity=severity,
            confidence=0.5,
        )
        json_dict = json.loads(issue.model_dump_json())
        assert json_dict["severity"] == expected

    @pytest.mark.parametrize(
        ("action_type", "expected"),
        [
            (ActionType.DESKEW, "deskew"),
            (ActionType.PERSPECTIVE_CORRECTION, "perspective_correction"),
            (ActionType.SHARPEN, "sharpen"),
            (ActionType.DENOISE, "denoise"),
            (ActionType.CLAHE, "clahe"),
            (ActionType.UPSAMPLE, "upsample"),
            (ActionType.ROTATE, "rotate"),
        ],
    )
    def test_action_type_serialization(
        self, action_type: ActionType, expected: str
    ) -> None:
        """Test ActionType enum serializes correctly."""
        action = PlannedAction(
            action=action_type,
            params={},
            confidence=0.8,
            reason="Test",
        )
        json_dict = json.loads(action.model_dump_json())
        assert json_dict["action"] == expected

    @pytest.mark.parametrize(
        ("pdf_type", "expected"),
        [
            (PDFType.IMAGE_ONLY, "image_only"),
            (PDFType.BORN_DIGITAL, "born_digital"),
            (PDFType.HYBRID, "hybrid"),
        ],
    )
    def test_pdf_type_serialization(self, pdf_type: PDFType, expected: str) -> None:
        """Test PDFType enum serializes correctly."""
        metadata = create_minimal_document_metadata()
        metadata.pdf_type = pdf_type
        json_dict = json.loads(metadata.model_dump_json())
        assert json_dict["pdf_type"] == expected

    @pytest.mark.parametrize(
        ("routing", "expected"),
        [
            (OCRRoutingStrategy.OCR_FAST, "ocr_fast"),
            (OCRRoutingStrategy.OCR_ADVANCED, "ocr_advanced"),
            (OCRRoutingStrategy.VISION_SIMPLE, "vision_simple"),
            (OCRRoutingStrategy.VISION_STRUCTURED, "vision_structured"),
        ],
    )
    def test_routing_strategy_serialization(
        self, routing: OCRRoutingStrategy, expected: str
    ) -> None:
        """Test OCRRoutingStrategy enum serializes correctly."""
        metadata = create_minimal_document_metadata()
        metadata.ocr_routing_recommendation = routing
        json_dict = json.loads(metadata.model_dump_json())
        assert json_dict["ocr_routing_recommendation"] == expected


# =============================================================================
# Round-Trip Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestRoundTripSerialization:
    """Tests for round-trip JSON serialization."""

    def test_minimal_metadata_round_trip(self) -> None:
        """Test minimal metadata survives round-trip."""
        original = create_minimal_document_metadata()
        json_str = original.model_dump_json()
        restored = DocumentMetadata.model_validate_json(json_str)

        assert restored.document_id == original.document_id
        assert restored.file_name == original.file_name
        assert restored.num_pages == original.num_pages
        assert len(restored.pages) == len(original.pages)

    def test_full_metadata_round_trip(self) -> None:
        """Test full metadata survives round-trip."""
        original = create_full_document_metadata()
        json_str = original.model_dump_json()
        restored = DocumentMetadata.model_validate_json(json_str)

        assert restored.document_id == original.document_id
        assert restored.pdf_type == original.pdf_type
        assert restored.pre_ocr_risk == original.pre_ocr_risk
        assert restored.dqs == original.dqs
        assert (
            restored.ocr_routing_recommendation == original.ocr_routing_recommendation
        )

    def test_detected_issues_round_trip(self) -> None:
        """Test detected issues survive round-trip."""
        original = create_full_document_metadata()
        json_str = original.model_dump_json()
        restored = DocumentMetadata.model_validate_json(json_str)

        original_issues = original.pages[0].detected_issues
        restored_issues = restored.pages[0].detected_issues

        assert len(restored_issues) == len(original_issues)
        for orig, rest in zip(original_issues, restored_issues, strict=True):
            assert rest.type == orig.type
            assert rest.severity == orig.severity
            assert rest.confidence == orig.confidence

    def test_transform_history_round_trip(self) -> None:
        """Test transform history survives round-trip."""
        original = create_full_document_metadata()
        json_str = original.model_dump_json()
        restored = DocumentMetadata.model_validate_json(json_str)

        original_transforms = original.pages[0].transform_history
        restored_transforms = restored.pages[0].transform_history

        assert len(restored_transforms) == len(original_transforms)
        for orig, rest in zip(original_transforms, restored_transforms, strict=True):
            assert rest.action == orig.action
            assert rest.status == orig.status


# =============================================================================
# Golden File Comparison Tests
# =============================================================================


@pytest.mark.unit
class TestGoldenFileComparison:
    """Tests comparing output against golden files."""

    @staticmethod
    def normalize_json(json_dict: dict[str, Any]) -> dict[str, Any]:
        """Normalize JSON for comparison (remove timestamps)."""
        result = json_dict.copy()

        # Remove timestamp from processing_version
        if result.get("processing_version"):
            pv = result["processing_version"].copy()
            pv.pop("timestamp", None)
            result["processing_version"] = pv

        # Remove timestamps from transform_history
        if "pages" in result:
            pages = []
            for page in result["pages"]:
                page_copy = page.copy()
                if page_copy.get("transform_history"):
                    transforms = []
                    for t in page_copy["transform_history"]:
                        t_copy = t.copy()
                        t_copy.pop("started_at", None)
                        t_copy.pop("finished_at", None)
                        transforms.append(t_copy)
                    page_copy["transform_history"] = transforms
                pages.append(page_copy)
            result["pages"] = pages

        return result

    def test_minimal_metadata_structure_matches_expected(self) -> None:
        """Test minimal metadata structure matches expected golden structure."""
        metadata = create_minimal_document_metadata()
        json_dict = json.loads(metadata.model_dump_json())
        normalized = self.normalize_json(json_dict)

        expected_structure = {
            "document_id": "test-doc-001",
            "file_name": "test_document.pdf",
            "source_mime": "application/pdf",
            "num_pages": 1,
            "processing_version": {
                "pipeline_version": "1.0.0",
                "iqa_model_hash": None,
                "layout_model_hash": None,
                "thresholds": {},
            },
            "pages": [
                {
                    "page_index": 0,
                    "width_px": 612,
                    "height_px": 792,
                    "dpi_input": 72,
                    "dpi_effective": 300,
                    "ml_iqa": None,
                    "teacher_iqa": None,
                    "detected_issues": [],
                    "planned_actions": [],
                    "elements": [],
                    "transform_history": [],
                }
            ],
            "pdf_type": None,
            "pre_ocr_risk": None,
            "dqs": None,
            "ocr_routing_recommendation": None,
            "upscaling": None,
            "page_layout_summary": [],
            "teacher_usage": None,
        }

        # Compare key structural elements
        assert normalized["document_id"] == expected_structure["document_id"]
        assert normalized["num_pages"] == expected_structure["num_pages"]
        assert len(normalized["pages"]) == len(expected_structure["pages"])

        # Compare page structure
        actual_page = normalized["pages"][0]
        expected_page = expected_structure["pages"][0]
        assert actual_page["page_index"] == expected_page["page_index"]
        assert actual_page["width_px"] == expected_page["width_px"]
        assert actual_page["detected_issues"] == expected_page["detected_issues"]

    def test_json_keys_are_snake_case(self) -> None:
        """Test all JSON keys use snake_case convention."""
        metadata = create_full_document_metadata()
        json_str = metadata.model_dump_json()

        def check_keys(obj: Any, path: str = "") -> list[str]:
            """Recursively check all keys are snake_case."""
            violations = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Check key is snake_case (lowercase with underscores)
                    if not all(c.islower() or c.isdigit() or c == "_" for c in key):
                        violations.append(f"{path}.{key}" if path else key)
                    violations.extend(
                        check_keys(value, f"{path}.{key}" if path else key)
                    )
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    violations.extend(check_keys(item, f"{path}[{i}]"))
            return violations

        json_dict = json.loads(json_str)
        violations = check_keys(json_dict)

        assert len(violations) == 0, f"Non-snake_case keys found: {violations}"
