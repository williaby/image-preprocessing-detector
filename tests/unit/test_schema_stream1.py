"""Unit tests for Stream 1 schema extensions.

Tests for:
- ScriptDetectionResult (three-tier architecture)
- DocumentScriptDetection (multi-script handling)
- TableComplexity
- DoclingRoutingParams
- PageLayoutSummary extensions (continuous scores)
- DocumentMetadata extensions (capture_method, script_detection, etc.)
- ScriptMLMapping
- ScriptRouter
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.schema import (
    DoclingRoutingParams,
    DocumentMetadata,
    DocumentScriptDetection,
    LanguageInfo,
    LayoutType,
    PageLayoutSummary,
    PageMetadata,
    ProcessingVersion,
    ScriptDetectionResult,
    TableComplexity,
)
from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
    ScriptFamily,
)


class TestScriptDetectionResult:
    """Test ScriptDetectionResult model (Tier 1 of three-tier architecture)."""

    def test_valid_script_detection(self) -> None:
        """Test creating valid script detection result."""
        result = ScriptDetectionResult(
            detected_script="Latn",
            confidence=0.95,
            detection_method="siglip2_multitask",
            script_probabilities={"Latn": 0.95, "Cyrl": 0.03, "Grek": 0.02},
        )
        assert result.detected_script == "Latn"
        assert result.confidence == pytest.approx(0.95)
        assert result.is_unknown is False

    def test_script_code_length_validation(self) -> None:
        """Test ISO 15924 codes must be exactly 4 characters."""
        with pytest.raises(ValidationError):
            ScriptDetectionResult(
                detected_script="La",  # Too short
                confidence=0.95,
                detection_method="heuristic",
            )

        with pytest.raises(ValidationError):
            ScriptDetectionResult(
                detected_script="Latin",  # Too long
                confidence=0.95,
                detection_method="heuristic",
            )

    def test_unknown_script_factory(self) -> None:
        """Test creating unknown script result."""
        result = ScriptDetectionResult.unknown(
            reason="no_text_detected",
            method="heuristic",
        )
        assert result.detected_script == "Zzzz"
        assert result.confidence == 0.0
        assert result.is_unknown is True
        assert result.unknown_reason == "no_text_detected"

    def test_from_source_label(self) -> None:
        """Test creating from source dataset label."""
        result = ScriptDetectionResult.from_source_label(
            source_label="Latin",
            confidence=1.0,
            method="dataset_ground_truth",
        )
        assert result.detected_script == "Latn"
        assert result.source_label == "Latin"  # Original preserved

    def test_from_source_label_unknown(self) -> None:
        """Test unknown source label maps to Zzzz."""
        result = ScriptDetectionResult.from_source_label(
            source_label="UnknownScript",
            confidence=0.5,
        )
        assert result.detected_script == "Zzzz"
        assert result.is_unknown is True

    def test_get_script_family(self) -> None:
        """Test script family classification."""
        latin = ScriptDetectionResult(
            detected_script="Latn",
            confidence=0.95,
            detection_method="heuristic",
        )
        assert latin.get_script_family() == ScriptFamily.LATIN

        cjk = ScriptDetectionResult(
            detected_script="Hans",
            confidence=0.90,
            detection_method="heuristic",
        )
        assert cjk.get_script_family() == ScriptFamily.CJK

    def test_bbox_for_region_detection(self) -> None:
        """Test region-level script detection with bounding box."""
        result = ScriptDetectionResult(
            detected_script="Arab",
            confidence=0.88,
            detection_method="ocr_langdetect",
            bbox=[100, 200, 300, 150],
            page_index=0,
        )
        assert result.bbox == [100, 200, 300, 150]
        assert result.page_index == 0


class TestDocumentScriptDetection:
    """Test DocumentScriptDetection model for multi-script documents."""

    def test_from_instances_single_script(self) -> None:
        """Test aggregating single-script instances."""
        instances = [
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.95,
                detection_method="heuristic",
                page_index=0,
            ),
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.92,
                detection_method="heuristic",
                page_index=1,
            ),
        ]
        detection = DocumentScriptDetection.from_instances(instances)

        assert detection.dominant_script == "Latn"
        assert detection.is_multilingual is False
        assert detection.unique_scripts == ["Latn"]
        assert detection.page_count == 2

    def test_from_instances_multi_script(self) -> None:
        """Test aggregating multi-script instances."""
        instances = [
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.95,
                detection_method="heuristic",
                page_index=0,
            ),
            ScriptDetectionResult(
                detected_script="Hans",
                confidence=0.88,
                detection_method="heuristic",
                page_index=1,
            ),
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.90,
                detection_method="heuristic",
                page_index=2,
            ),
        ]
        detection = DocumentScriptDetection.from_instances(instances)

        assert detection.dominant_script == "Latn"  # More occurrences
        assert detection.is_multilingual is True
        assert "Latn" in detection.unique_scripts
        assert "Hans" in detection.unique_scripts
        assert detection.needs_multi_engine is True

    def test_from_instances_empty(self) -> None:
        """Test aggregating empty instances list."""
        detection = DocumentScriptDetection.from_instances([])

        assert detection.dominant_script == "Zzzz"
        assert detection.dominant_confidence == 0.0
        assert detection.is_multilingual is False

    def test_script_distribution(self) -> None:
        """Test script distribution calculation."""
        instances = [
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.95,
                detection_method="heuristic",
            ),
            ScriptDetectionResult(
                detected_script="Latn",
                confidence=0.90,
                detection_method="heuristic",
            ),
            ScriptDetectionResult(
                detected_script="Hans",
                confidence=0.88,
                detection_method="heuristic",
            ),
        ]
        detection = DocumentScriptDetection.from_instances(instances)

        assert detection.script_distribution["Latn"] == pytest.approx(2 / 3)
        assert detection.script_distribution["Hans"] == pytest.approx(1 / 3)


class TestTableComplexity:
    """Test TableComplexity model."""

    def test_valid_table_complexity(self) -> None:
        """Test creating valid table complexity."""
        tc = TableComplexity(
            has_borders=True,
            estimated_rows=10,
            estimated_columns=5,
            has_merged_cells=False,
            complexity_score=0.3,
        )
        assert tc.has_borders is True
        assert tc.complexity_score == pytest.approx(0.3)

    def test_complexity_score_bounds(self) -> None:
        """Test complexity score must be 0-1."""
        with pytest.raises(ValidationError):
            TableComplexity(complexity_score=1.5)

        with pytest.raises(ValidationError):
            TableComplexity(complexity_score=-0.1)

    def test_default_values(self) -> None:
        """Test default values are sensible."""
        tc = TableComplexity()
        assert tc.has_borders is True
        assert tc.complexity_score == 0.5


class TestDoclingRoutingParams:
    """Test DoclingRoutingParams model."""

    def test_valid_params(self) -> None:
        """Test creating valid Docling routing params."""
        params = DoclingRoutingParams(
            pipeline="vlm",
            vlm_model="deepseekocr_ollama",
            ocr_enabled=False,
            table_mode="accurate",
        )
        assert params.pipeline == "vlm"
        assert params.ocr_enabled is False

    def test_to_cli_args_basic(self) -> None:
        """Test CLI argument generation."""
        params = DoclingRoutingParams(
            pipeline="standard",
            ocr_engine="rapidocr",
            table_mode="fast",
            page_batch_size=8,
        )
        args = params.to_cli_args()

        assert "--pipeline=standard" in args
        assert "--ocr-engine=rapidocr" in args
        assert "--table-mode=fast" in args
        assert "--page-batch-size=8" in args

    def test_to_cli_args_no_ocr(self) -> None:
        """Test CLI args with OCR disabled."""
        params = DoclingRoutingParams(ocr_enabled=False)
        args = params.to_cli_args()

        assert "--no-ocr" in args

    def test_to_cli_args_vlm(self) -> None:
        """Test CLI args with VLM pipeline."""
        params = DoclingRoutingParams(
            pipeline="vlm",
            vlm_model="deepseekocr_ollama",
        )
        args = params.to_cli_args()

        assert "--pipeline=vlm" in args
        assert "--vlm-model=deepseekocr_ollama" in args

    def test_to_cli_args_enrichments(self) -> None:
        """Test CLI args with enrichments."""
        params = DoclingRoutingParams(
            enrich_code=True,
            enrich_formula=True,
        )
        args = params.to_cli_args()

        assert "--enrich-code" in args
        assert "--enrich-formula" in args

    def test_psm_bounds(self) -> None:
        """Test PSM must be 0-13."""
        with pytest.raises(ValidationError):
            DoclingRoutingParams(psm=14)

        with pytest.raises(ValidationError):
            DoclingRoutingParams(psm=-1)


class TestPageLayoutSummaryExtensions:
    """Test PageLayoutSummary Stream 1 extensions."""

    def test_continuous_shadow_score(self) -> None:
        """Test shadow detection with continuous score."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            has_shadows=True,
            shadow_score=0.65,
            shadow_severity="moderate",
        )
        assert summary.has_shadows is True
        assert summary.shadow_score == pytest.approx(0.65)
        assert summary.shadow_severity == "moderate"

    def test_continuous_warping_score(self) -> None:
        """Test warping detection with continuous score."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            has_warping=True,
            warping_score=0.78,
            warping_type="barrel",
        )
        assert summary.has_warping is True
        assert summary.warping_score == pytest.approx(0.78)
        assert summary.warping_type == "barrel"

    def test_code_detection(self) -> None:
        """Test code detection field."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.5,
            has_code=True,
            code_confidence=0.88,
        )
        assert summary.has_code is True
        assert summary.code_confidence == pytest.approx(0.88)

    def test_table_complexity_field(self) -> None:
        """Test table complexity nested field."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.COMPLEX,
            complexity_score=0.7,
            has_tables=True,
            table_complexity=TableComplexity(
                has_borders=False,
                estimated_rows=15,
                estimated_columns=8,
                has_merged_cells=True,
                complexity_score=0.85,
            ),
        )
        assert summary.table_complexity is not None
        assert summary.table_complexity.has_merged_cells is True
        assert summary.table_complexity.complexity_score == pytest.approx(0.85)

    def test_orientation_fields(self) -> None:
        """Test orientation tracking fields."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            orientation_angle=90,
            orientation_confidence=0.95,
            orientation_corrected=True,
        )
        assert summary.orientation_angle == 90
        assert summary.orientation_corrected is True

    def test_degradations_list(self) -> None:
        """Test degradations list for VLM escalation."""
        summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            degradations=["water_damage", "faded"],
        )
        assert "water_damage" in summary.degradations


class TestDocumentMetadataExtensions:
    """Test DocumentMetadata Stream 1 extensions."""

    def test_capture_method(self) -> None:
        """Test capture method field."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="scan.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="0.1.0"),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            capture_method=CaptureMethod.SCANNER_FLATBED,
            capture_method_confidence=0.92,
        )
        assert metadata.capture_method == CaptureMethod.SCANNER_FLATBED
        assert metadata.capture_method_confidence == pytest.approx(0.92)

    def test_script_detection_field(self) -> None:
        """Test script detection nested field."""
        script_detection = DocumentScriptDetection(
            script_instances=[],
            dominant_script="Latn",
            dominant_confidence=0.95,
            is_multilingual=False,
            unique_scripts=["Latn"],
        )
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
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            script_detection=script_detection,
        )
        assert metadata.script_detection is not None
        assert metadata.script_detection.dominant_script == "Latn"

    def test_text_layer_quality(self) -> None:
        """Test text layer quality fields."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="born_digital.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="0.1.0"),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            text_layer_quality=0.95,
            text_layer_skip_ocr=True,
        )
        assert metadata.text_layer_quality == pytest.approx(0.95)
        assert metadata.text_layer_skip_ocr is True

    def test_degradation_severity(self) -> None:
        """Test degradation severity field."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="camera_capture.jpg",
            source_mime="image/jpeg",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="0.1.0"),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            degradation_severity="complex",
        )
        assert metadata.degradation_severity == "complex"

    def test_docling_params_field(self) -> None:
        """Test Docling routing params field."""
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
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            docling_params=DoclingRoutingParams(
                pipeline="standard",
                ocr_engine="rapidocr",
            ),
        )
        assert metadata.docling_params is not None
        assert metadata.docling_params.ocr_engine == "rapidocr"

    def test_vlm_escalation_reasons(self) -> None:
        """Test VLM escalation reasons tracking."""
        metadata = DocumentMetadata(
            document_id="doc_001",
            file_name="difficult.pdf",
            source_mime="application/pdf",
            num_pages=1,
            processing_version=ProcessingVersion(pipeline_version="0.1.0"),
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=2550,
                    height_px=3300,
                    dpi_input=300,
                    dpi_effective=300,
                )
            ],
            vlm_escalation_reasons=[
                "handwriting_detected",
                "severe_degradation",
            ],
        )
        assert "handwriting_detected" in metadata.vlm_escalation_reasons


class TestLanguageInfoExtensions:
    """Test LanguageInfo Stream 1 extensions."""

    def test_typed_script_enum(self) -> None:
        """Test script uses typed ISO15924Script enum."""
        info = LanguageInfo(
            script=ISO15924Script.LATN,
            confidence=0.95,
        )
        assert info.script == ISO15924Script.LATN
        assert info.script_str == "Latn"

    def test_from_legacy(self) -> None:
        """Test creating from legacy string script name."""
        info = LanguageInfo.from_legacy("Latin", confidence=0.90)
        assert info.script == ISO15924Script.LATN
        assert info.confidence == pytest.approx(0.90)

    def test_from_legacy_unknown(self) -> None:
        """Test unknown legacy script maps to ZZZZ."""
        info = LanguageInfo.from_legacy("UnknownScript", confidence=0.5)
        assert info.script == ISO15924Script.ZZZZ
