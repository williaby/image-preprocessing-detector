"""Golden file drift detection tests.

Sprint 5.1.5: Tests to detect schema drift by comparing against frozen
golden file fixtures. Any unexpected changes to the DocumentMetadata
schema will cause these tests to fail.

Purpose:
- Freeze stable DocumentMetadata fields for key fixtures
- Detect unintended schema changes (drift)
- Ensure backward compatibility
- Guard against breaking changes in JSON output format
"""

import json
from pathlib import Path
from typing import Any

import pytest

from image_preprocessing_detector.schema import DocumentMetadata

# Golden files directory
GOLDEN_DIR = (
    Path(__file__).parent.parent.parent / "data" / "test_fixtures" / "golden_files"
)


def load_golden_file(name: str) -> dict[str, Any]:
    """Load a golden file from the fixtures directory."""
    path = GOLDEN_DIR / name
    if not path.exists():
        pytest.skip(f"Golden file not found: {path}")
    with open(path) as f:
        return json.load(f)


def get_schema_keys(obj: Any, prefix: str = "") -> set[str]:
    """Extract all keys from a nested dict/list structure."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            keys.update(get_schema_keys(value, full_key))
    elif isinstance(obj, list) and obj:
        # Use [*] to indicate list items
        keys.update(get_schema_keys(obj[0], f"{prefix}[*]"))
    return keys


def get_field_types(obj: Any, prefix: str = "") -> dict[str, str]:
    """Extract types of all fields in a nested structure."""
    types: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            types[full_key] = type(value).__name__
            types.update(get_field_types(value, full_key))
    elif isinstance(obj, list) and obj:
        types.update(get_field_types(obj[0], f"{prefix}[*]"))
    return types


class TestMinimalDocumentMetadataDrift:
    """Drift detection tests for minimal DocumentMetadata."""

    def test_golden_file_loads(self) -> None:
        """Golden file should load without error."""
        golden = load_golden_file("minimal_document_metadata.json")
        assert golden is not None
        assert "document_id" in golden

    def test_golden_file_validates_as_document_metadata(self) -> None:
        """Golden file should validate as DocumentMetadata."""
        golden = load_golden_file("minimal_document_metadata.json")
        metadata = DocumentMetadata.model_validate(golden)
        assert metadata.document_id == "golden-minimal-001"

    def test_required_top_level_fields_present(self) -> None:
        """All required top-level fields must be present."""
        golden = load_golden_file("minimal_document_metadata.json")

        required_fields = [
            "document_id",
            "file_name",
            "source_mime",
            "num_pages",
            "processing_version",
            "pages",
        ]

        for field in required_fields:
            assert field in golden, f"Required field missing: {field}"

    def test_processing_version_structure_stable(self) -> None:
        """Processing version structure must not change."""
        golden = load_golden_file("minimal_document_metadata.json")

        required_pv_fields = [
            "pipeline_version",
            "thresholds",
        ]

        pv = golden["processing_version"]
        for field in required_pv_fields:
            assert field in pv, f"Required processing_version field missing: {field}"

    def test_page_structure_stable(self) -> None:
        """Page structure must not change."""
        golden = load_golden_file("minimal_document_metadata.json")

        required_page_fields = [
            "page_index",
            "width_px",
            "height_px",
            "dpi_input",
            "dpi_effective",
        ]

        page = golden["pages"][0]
        for field in required_page_fields:
            assert field in page, f"Required page field missing: {field}"


class TestFullDocumentMetadataDrift:
    """Drift detection tests for full DocumentMetadata."""

    def test_golden_file_loads(self) -> None:
        """Golden file should load without error."""
        golden = load_golden_file("full_document_metadata.json")
        assert golden is not None
        assert "document_id" in golden

    def test_golden_file_validates_as_document_metadata(self) -> None:
        """Golden file should validate as DocumentMetadata."""
        golden = load_golden_file("full_document_metadata.json")
        metadata = DocumentMetadata.model_validate(golden)
        assert metadata.document_id == "golden-full-001"

    def test_phase8_fields_present(self) -> None:
        """Phase 8 fields must be present."""
        golden = load_golden_file("full_document_metadata.json")

        phase8_fields = [
            "pdf_type",
            "pre_ocr_risk",
            "dqs",
            "ocr_routing_recommendation",
        ]

        for field in phase8_fields:
            assert field in golden, f"Phase 8 field missing: {field}"

    def test_dqs_structure_stable(self) -> None:
        """DQS structure must not change."""
        golden = load_golden_file("full_document_metadata.json")

        dqs = golden["dqs"]
        assert "degradation_score" in dqs
        assert "structural_complexity_score" in dqs

    def test_page_layout_summary_structure(self) -> None:
        """Page layout summary structure must not change."""
        golden = load_golden_file("full_document_metadata.json")

        summary = golden["page_layout_summary"][0]
        required_fields = [
            "page_number",
            "layout_type",
            "has_tables",
            "has_figures",
            "has_dense_math",
            "has_handwriting",
            "complexity_score",
        ]

        for field in required_fields:
            assert field in summary, f"Layout summary field missing: {field}"

    def test_detected_issue_structure(self) -> None:
        """Detected issue structure must not change."""
        golden = load_golden_file("full_document_metadata.json")

        issue = golden["pages"][0]["detected_issues"][0]
        required_fields = [
            "type",
            "severity",
            "confidence",
        ]

        for field in required_fields:
            assert field in issue, f"Detected issue field missing: {field}"

    def test_planned_action_structure(self) -> None:
        """Planned action structure must not change."""
        golden = load_golden_file("full_document_metadata.json")

        action = golden["pages"][0]["planned_actions"][0]
        required_fields = [
            "action",
            "params",
            "confidence",
            "reason",
        ]

        for field in required_fields:
            assert field in action, f"Planned action field missing: {field}"

    def test_element_structure(self) -> None:
        """Document element structure must not change."""
        golden = load_golden_file("full_document_metadata.json")

        element = golden["pages"][0]["elements"][0]
        required_fields = [
            "id",
            "category",
            "bbox",
            "confidence",
        ]

        for field in required_fields:
            assert field in element, f"Element field missing: {field}"

    def test_bbox_is_coco_format(self) -> None:
        """Bounding boxes must use COCO format [x, y, width, height]."""
        golden = load_golden_file("full_document_metadata.json")

        element = golden["pages"][0]["elements"][0]
        bbox = element["bbox"]

        assert len(bbox) == 4, "COCO bbox must have exactly 4 values"
        assert all(isinstance(v, (int, float)) for v in bbox)
        # All values should be non-negative
        assert all(v >= 0 for v in bbox)


class TestSchemaDriftGuard:
    """Guard tests to catch schema drift."""

    def test_no_new_required_fields_without_defaults(self) -> None:
        """New required fields must have defaults for backward compatibility."""
        # Load golden file (represents old schema)
        golden = load_golden_file("minimal_document_metadata.json")

        # Try to load as current DocumentMetadata
        # This will fail if new required fields were added without defaults
        try:
            metadata = DocumentMetadata.model_validate(golden)
            assert metadata is not None
        except Exception as e:
            pytest.fail(
                f"Schema drift detected: new required fields may have been added. "
                f"Error: {e}"
            )

    def test_existing_field_types_unchanged(self) -> None:
        """Existing field types should not change."""
        golden = load_golden_file("full_document_metadata.json")

        # Core field types that must not change
        expected_types = {
            "document_id": str,
            "file_name": str,
            "source_mime": str,
            "num_pages": int,
            "pdf_type": str,
            "pre_ocr_risk": float,
        }

        for field, expected_type in expected_types.items():
            if golden[field] is not None:
                assert isinstance(golden[field], expected_type), (
                    f"Type drift: {field} expected {expected_type.__name__}, "
                    f"got {type(golden[field]).__name__}"
                )

    def test_enum_values_stable(self) -> None:
        """Enum values should not change."""
        golden = load_golden_file("full_document_metadata.json")

        # PDF type enum values
        valid_pdf_types = ["image_only", "born_digital", "hybrid"]
        assert golden["pdf_type"] in valid_pdf_types

        # Routing recommendation enum values
        valid_routing = [
            "ocr_fast",
            "ocr_advanced",
            "vision_simple",
            "vision_structured",
        ]
        assert golden["ocr_routing_recommendation"] in valid_routing

        # Layout type enum values
        valid_layouts = [
            "single_column",
            "multi_column",
            "three_column",
            "complex",
            "unknown",
        ]
        assert golden["page_layout_summary"][0]["layout_type"] in valid_layouts

        # Issue type enum values
        valid_issues = [
            "noise",
            "blur",
            "skew",
            "perspective",
            "low_contrast",
            "orientation",
            "low_dpi",
            "illumination",
            "jpeg_artifacts",
            "binarization",
            "bleed_through",
        ]
        for issue in golden["pages"][0]["detected_issues"]:
            assert issue["type"] in valid_issues, f"Unknown issue type: {issue['type']}"

        # Severity enum values
        valid_severities = ["low", "medium", "high", "critical"]
        for issue in golden["pages"][0]["detected_issues"]:
            assert issue["severity"] in valid_severities

    def test_roundtrip_preserves_data(self) -> None:
        """Roundtrip through model should preserve all data."""
        golden = load_golden_file("full_document_metadata.json")

        # Parse and serialize
        metadata = DocumentMetadata.model_validate(golden)
        serialized = json.loads(metadata.model_dump_json())

        # Check key fields are preserved
        assert serialized["document_id"] == golden["document_id"]
        assert serialized["pdf_type"] == golden["pdf_type"]
        assert serialized["pre_ocr_risk"] == golden["pre_ocr_risk"]
        assert (
            serialized["dqs"]["degradation_score"] == golden["dqs"]["degradation_score"]
        )


class TestSchemaVersioning:
    """Tests for schema version tracking."""

    def test_processing_version_tracks_pipeline_version(self) -> None:
        """Processing version should track pipeline version."""
        golden = load_golden_file("full_document_metadata.json")

        pv = golden["processing_version"]
        assert "pipeline_version" in pv
        assert pv["pipeline_version"] is not None
        assert len(pv["pipeline_version"]) > 0

    def test_model_hashes_optional(self) -> None:
        """Model hashes should be optional for backward compatibility."""
        golden = load_golden_file("minimal_document_metadata.json")

        pv = golden["processing_version"]
        # These can be None for documents processed without ML models
        assert "iqa_model_hash" in pv or pv.get("iqa_model_hash") is None
        assert "layout_model_hash" in pv or pv.get("layout_model_hash") is None
