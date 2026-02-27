"""Unit tests for annotation schema validators.

Tests Pydantic-based validation for all annotation schema types.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from image_preprocessing_detector.annotation.schemas.validators import (
    BboxValidator,
    ConfidenceValidator,
    DpiValidator,
    FileHashValidator,
    IsoDateValidator,
    MosScoreValidator,
    OcrQualityScoreValidator,
    PixelDimensionsValidator,
    SampleIdValidator,
    validate_enrichment_data,
    validate_enrichment_version,
    validate_original_file_metadata,
    validate_original_labels,
    validate_sample_metadata,
)

# ============================================================================
# Field Validator Tests
# ============================================================================


class TestSampleIdValidator:
    """Test sample ID validation."""

    def test_valid_sample_id(self) -> None:
        """Valid 32-char hex sample ID."""
        validator = SampleIdValidator(id="a" * 32)
        assert validator.id == "a" * 32

    def test_mixed_hex_characters(self) -> None:
        """Valid sample ID with mixed hex characters."""
        validator = SampleIdValidator(id="abc123def456" + "0" * 20)
        assert len(validator.id) == 32

    def test_too_short(self) -> None:
        """Sample ID too short."""
        with pytest.raises(ValidationError):
            SampleIdValidator(id="a" * 31)

    def test_too_long(self) -> None:
        """Sample ID too long."""
        with pytest.raises(ValidationError):
            SampleIdValidator(id="a" * 33)

    def test_uppercase_rejected(self) -> None:
        """Uppercase hex rejected."""
        with pytest.raises(ValidationError):
            SampleIdValidator(id="A" * 32)

    def test_non_hex_characters(self) -> None:
        """Non-hex characters rejected."""
        with pytest.raises(ValidationError):
            SampleIdValidator(id="g" * 32)


class TestFileHashValidator:
    """Test file hash validation."""

    def test_valid_file_hash(self) -> None:
        """Valid 64-char hex file hash."""
        validator = FileHashValidator(file_hash="a" * 64)
        assert validator.file_hash == "a" * 64

    def test_too_short(self) -> None:
        """File hash too short."""
        with pytest.raises(ValidationError):
            FileHashValidator(file_hash="a" * 63)

    def test_too_long(self) -> None:
        """File hash too long."""
        with pytest.raises(ValidationError):
            FileHashValidator(file_hash="a" * 65)

    def test_uppercase_rejected(self) -> None:
        """Uppercase hex rejected."""
        with pytest.raises(ValidationError):
            FileHashValidator(file_hash="A" * 64)


class TestConfidenceValidator:
    """Test confidence score validation."""

    def test_valid_confidence_zero(self) -> None:
        """Valid confidence score at lower bound."""
        validator = ConfidenceValidator(confidence=0.0)
        assert validator.confidence == pytest.approx(0.0)

    def test_valid_confidence_one(self) -> None:
        """Valid confidence score at upper bound."""
        validator = ConfidenceValidator(confidence=1.0)
        assert validator.confidence == pytest.approx(1.0)

    def test_valid_confidence_middle(self) -> None:
        """Valid confidence score in middle."""
        validator = ConfidenceValidator(confidence=0.5)
        assert validator.confidence == pytest.approx(0.5)

    def test_negative_confidence(self) -> None:
        """Negative confidence rejected."""
        with pytest.raises(ValidationError):
            ConfidenceValidator(confidence=-0.1)

    def test_too_high_confidence(self) -> None:
        """Confidence > 1.0 rejected."""
        with pytest.raises(ValidationError):
            ConfidenceValidator(confidence=1.1)


class TestBboxValidator:
    """Test bounding box validation."""

    def test_valid_bbox(self) -> None:
        """Valid COCO-format bbox."""
        validator = BboxValidator(bbox=[10.0, 20.0, 100.0, 200.0])
        assert validator.bbox == [10.0, 20.0, 100.0, 200.0]

    def test_zero_origin(self) -> None:
        """Bbox at origin (0, 0)."""
        validator = BboxValidator(bbox=[0.0, 0.0, 100.0, 200.0])
        assert validator.bbox[0] == pytest.approx(0.0)

    def test_negative_x(self) -> None:
        """Negative x coordinate rejected."""
        with pytest.raises(ValueError, match="x must be non-negative"):
            BboxValidator(bbox=[-10.0, 20.0, 100.0, 200.0])

    def test_negative_y(self) -> None:
        """Negative y coordinate rejected."""
        with pytest.raises(ValueError, match="y must be non-negative"):
            BboxValidator(bbox=[10.0, -20.0, 100.0, 200.0])

    def test_zero_width(self) -> None:
        """Zero width rejected."""
        with pytest.raises(ValueError, match="width must be positive"):
            BboxValidator(bbox=[10.0, 20.0, 0.0, 200.0])

    def test_zero_height(self) -> None:
        """Zero height rejected."""
        with pytest.raises(ValueError, match="height must be positive"):
            BboxValidator(bbox=[10.0, 20.0, 100.0, 0.0])

    def test_negative_width(self) -> None:
        """Negative width rejected."""
        with pytest.raises(ValueError, match="width must be positive"):
            BboxValidator(bbox=[10.0, 20.0, -100.0, 200.0])

    def test_wrong_length(self) -> None:
        """Wrong number of values rejected."""
        with pytest.raises(ValidationError):
            BboxValidator(bbox=[10.0, 20.0, 100.0])


class TestDpiValidator:
    """Test DPI validation."""

    def test_valid_dpi(self) -> None:
        """Valid DPI value."""
        validator = DpiValidator(dpi=300)
        assert validator.dpi == 300

    def test_zero_dpi(self) -> None:
        """Zero DPI rejected."""
        with pytest.raises(ValidationError):
            DpiValidator(dpi=0)

    def test_negative_dpi(self) -> None:
        """Negative DPI rejected."""
        with pytest.raises(ValidationError):
            DpiValidator(dpi=-100)


class TestPixelDimensionsValidator:
    """Test pixel dimensions validation."""

    def test_valid_dimensions(self) -> None:
        """Valid pixel dimensions."""
        validator = PixelDimensionsValidator(width_px=2480, height_px=3508)
        assert validator.width_px == 2480
        assert validator.height_px == 3508

    def test_zero_width(self) -> None:
        """Zero width rejected."""
        with pytest.raises(ValidationError):
            PixelDimensionsValidator(width_px=0, height_px=3508)

    def test_zero_height(self) -> None:
        """Zero height rejected."""
        with pytest.raises(ValidationError):
            PixelDimensionsValidator(width_px=2480, height_px=0)


class TestIsoDateValidator:
    """Test ISO date validation."""

    def test_valid_date_only(self) -> None:
        """Valid date-only format."""
        validator = IsoDateValidator(date_str="2025-01-15")
        assert validator.date_str == "2025-01-15"

    def test_valid_datetime_utc(self) -> None:
        """Valid datetime with UTC."""
        validator = IsoDateValidator(date_str="2025-01-15T10:30:45Z")
        assert "2025-01-15" in validator.date_str

    def test_valid_datetime_with_timezone(self) -> None:
        """Valid datetime with timezone offset."""
        validator = IsoDateValidator(date_str="2025-01-15T10:30:45+05:30")
        assert "2025-01-15" in validator.date_str

    def test_valid_datetime_with_microseconds(self) -> None:
        """Valid datetime with microseconds."""
        validator = IsoDateValidator(date_str="2025-01-15T10:30:45.123456Z")
        assert "2025-01-15" in validator.date_str

    def test_invalid_format(self) -> None:
        """Invalid date format rejected."""
        with pytest.raises(ValueError, match="Invalid ISO 8601"):
            IsoDateValidator(date_str="01/15/2025")

    def test_missing_separators(self) -> None:
        """Date without separators rejected."""
        with pytest.raises(ValueError, match="Invalid ISO 8601"):
            IsoDateValidator(date_str="20250115")


class TestMosScoreValidator:
    """Test MOS score validation."""

    def test_valid_mos_min(self) -> None:
        """Valid MOS at minimum (1.0)."""
        validator = MosScoreValidator(mos=1.0)
        assert validator.mos == pytest.approx(1.0)

    def test_valid_mos_max(self) -> None:
        """Valid MOS at maximum (5.0)."""
        validator = MosScoreValidator(mos=5.0)
        assert validator.mos == pytest.approx(5.0)

    def test_valid_mos_middle(self) -> None:
        """Valid MOS in middle range."""
        validator = MosScoreValidator(mos=3.5)
        assert validator.mos == pytest.approx(3.5)

    def test_too_low_mos(self) -> None:
        """MOS < 1.0 rejected."""
        with pytest.raises(ValidationError):
            MosScoreValidator(mos=0.5)

    def test_too_high_mos(self) -> None:
        """MOS > 5.0 rejected."""
        with pytest.raises(ValidationError):
            MosScoreValidator(mos=5.5)


class TestOcrQualityScoreValidator:
    """Test OCR quality score validation."""

    def test_valid_score_one(self) -> None:
        """Valid score at best quality (1)."""
        validator = OcrQualityScoreValidator(score=1)
        assert validator.score == 1

    def test_valid_score_four(self) -> None:
        """Valid score at worst quality (4)."""
        validator = OcrQualityScoreValidator(score=4)
        assert validator.score == 4

    def test_too_low_score(self) -> None:
        """Score < 1 rejected."""
        with pytest.raises(ValidationError):
            OcrQualityScoreValidator(score=0)

    def test_too_high_score(self) -> None:
        """Score > 4 rejected."""
        with pytest.raises(ValidationError):
            OcrQualityScoreValidator(score=5)


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestValidateSampleMetadata:
    """Test SampleMetadata validation."""

    def test_valid_sample_metadata(self) -> None:
        """Valid sample metadata passes validation."""
        data = {
            "id": "a" * 32,
            "file_hash": "b" * 64,
            "dataset_name": "diqa-5000",
            "dataset_version": "1.0",
            "original_path": "train/img001.png",
            "original_filename": "img001.png",
            "download_date": "2025-01-15",
            "original_labels": {},
            "original_file": {
                "format": "png",
                "width_px": 2480,
                "height_px": 3508,
                "channels": 3,
                "bit_depth": 8,
                "file_size_bytes": 1_500_000,
            },
            "current_version": 0,
            "enrichment_versions": [],
            "created_at": "2025-01-15T10:30:45Z",
            "schema_version": "2.1",
        }

        result = validate_sample_metadata(data)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_required_fields(self) -> None:
        """Missing required fields detected."""
        data: dict[str, str] = {}
        result = validate_sample_metadata(data)
        assert not result.valid
        assert "Missing required field: id" in result.errors
        assert "Missing required field: file_hash" in result.errors

    def test_invalid_sample_id(self) -> None:
        """Invalid sample ID format detected."""
        data = {
            "id": "invalid",
            "file_hash": "b" * 64,
            "dataset_name": "test",
            "dataset_version": "1.0",
            "original_path": "test.png",
            "original_filename": "test.png",
            "download_date": "2025-01-15",
            "original_labels": {},
            "original_file": {
                "format": "png",
                "width_px": 100,
                "height_px": 100,
                "channels": 3,
                "bit_depth": 8,
                "file_size_bytes": 1000,
            },
        }

        result = validate_sample_metadata(data)
        assert not result.valid
        assert any("Invalid sample ID" in err for err in result.errors)

    def test_invalid_file_hash(self) -> None:
        """Invalid file hash format detected."""
        data = {
            "id": "a" * 32,
            "file_hash": "invalid",
            "dataset_name": "test",
            "dataset_version": "1.0",
            "original_path": "test.png",
            "original_filename": "test.png",
            "download_date": "2025-01-15",
            "original_labels": {},
            "original_file": {
                "format": "png",
                "width_px": 100,
                "height_px": 100,
                "channels": 3,
                "bit_depth": 8,
                "file_size_bytes": 1000,
            },
        }

        result = validate_sample_metadata(data)
        assert not result.valid
        assert any("Invalid file hash" in err for err in result.errors)

    def test_missing_schema_version_warning(self) -> None:
        """Missing schema_version produces warning."""
        data = {
            "id": "a" * 32,
            "file_hash": "b" * 64,
            "dataset_name": "test",
            "dataset_version": "1.0",
            "original_path": "test.png",
            "original_filename": "test.png",
            "download_date": "2025-01-15",
            "original_labels": {},
            "original_file": {
                "format": "png",
                "width_px": 100,
                "height_px": 100,
                "channels": 3,
                "bit_depth": 8,
                "file_size_bytes": 1000,
            },
        }

        result = validate_sample_metadata(data)
        assert result.valid
        assert any("schema_version" in warn for warn in result.warnings)


class TestValidateEnrichmentVersion:
    """Test EnrichmentVersion validation."""

    def test_valid_enrichment_version(self) -> None:
        """Valid enrichment version passes validation."""
        data = {
            "version": 1,
            "created_at": "2025-01-15T10:30:45Z",
            "created_by": "test_script",
            "method": "tier_0_exact",
            "description": "Test enrichment",
            "data": {},
            "git_sha": "abc123",
        }

        result = validate_enrichment_version(data)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_required_fields(self) -> None:
        """Missing required fields detected."""
        data: dict[str, int] = {"version": 1}
        result = validate_enrichment_version(data)
        assert not result.valid
        assert any("Missing required field: created_at" in err for err in result.errors)

    def test_invalid_version_number(self) -> None:
        """Invalid version number detected."""
        data = {
            "version": 0,
            "created_at": "2025-01-15T10:30:45Z",
            "created_by": "test",
            "method": "tier_0_exact",
            "description": "test",
        }

        result = validate_enrichment_version(data)
        assert not result.valid
        assert any("version must be positive" in err for err in result.errors)

    def test_missing_git_sha_warning(self) -> None:
        """Missing git_sha produces warning."""
        data = {
            "version": 1,
            "created_at": "2025-01-15T10:30:45Z",
            "created_by": "test",
            "method": "tier_0_exact",
            "description": "test",
            "data": {},
        }

        result = validate_enrichment_version(data)
        assert result.valid
        assert any("git_sha" in warn for warn in result.warnings)


class TestValidateEnrichmentData:
    """Test EnrichmentData validation."""

    def test_valid_enrichment_data_empty(self) -> None:
        """Empty enrichment data is valid."""
        result = validate_enrichment_data({})
        assert result.valid

    def test_valid_confidence_fields(self) -> None:
        """Valid confidence fields pass validation."""
        data = {
            "capture_confidence": 0.95,
            "domain_confidence": 0.88,
            "language_confidence": 0.92,
            "paper_size_confidence": 0.99,
            "llm_prediction_confidence": 0.85,
            "quality_overall": 0.75,
        }

        result = validate_enrichment_data(data)
        assert result.valid

    def test_invalid_confidence_range(self) -> None:
        """Confidence outside [0, 1] detected."""
        data = {"capture_confidence": 1.5}
        result = validate_enrichment_data(data)
        assert not result.valid
        assert any("capture_confidence" in err for err in result.errors)

    def test_valid_layout_detections(self) -> None:
        """Valid layout detections pass validation."""
        data = {
            "layout_detections": [
                {
                    "class_name": "table",
                    "bbox": [100.0, 200.0, 300.0, 400.0],
                    "confidence": 0.95,
                    "source": "doclayout_yolo",
                }
            ]
        }

        result = validate_enrichment_data(data)
        assert result.valid

    def test_invalid_bbox_in_detections(self) -> None:
        """Invalid bbox in layout detections detected."""
        data = {
            "layout_detections": [
                {
                    "class_name": "table",
                    "bbox": [-10.0, 200.0, 300.0, 400.0],
                    "confidence": 0.95,
                    "source": "test",
                }
            ]
        }

        result = validate_enrichment_data(data)
        assert not result.valid
        assert any("layout_detections[0].bbox" in err for err in result.errors)

    def test_missing_class_name_in_detections(self) -> None:
        """Missing class_name in layout detections detected."""
        data = {
            "layout_detections": [
                {"bbox": [100.0, 200.0, 300.0, 400.0], "confidence": 0.95}
            ]
        }

        result = validate_enrichment_data(data)
        assert not result.valid
        assert any("missing class_name" in err for err in result.errors)

    def test_invalid_paper_size_orientation(self) -> None:
        """Invalid paper size orientation detected."""
        data = {"paper_size_orientation": "diagonal"}
        result = validate_enrichment_data(data)
        assert not result.valid
        assert any("paper_size_orientation" in err for err in result.errors)

    def test_iso_language_code_warning(self) -> None:
        """Invalid ISO 639 language code produces warning."""
        data = {"iso639_language": "invalid123"}
        result = validate_enrichment_data(data)
        assert result.valid
        assert any("iso639_language" in warn for warn in result.warnings)

    def test_iso_script_code_warning(self) -> None:
        """Invalid ISO 15924 script code produces warning."""
        data = {"iso15924_script": "invalid"}
        result = validate_enrichment_data(data)
        assert result.valid
        assert any("iso15924_script" in warn for warn in result.warnings)


class TestValidateOriginalFileMetadata:
    """Test OriginalFileMetadata validation."""

    def test_valid_file_metadata(self) -> None:
        """Valid file metadata passes validation."""
        data = {
            "format": "png",
            "width_px": 2480,
            "height_px": 3508,
            "channels": 3,
            "bit_depth": 8,
            "file_size_bytes": 1_500_000,
            "dpi": 300,
            "color_space": "RGB",
        }

        result = validate_original_file_metadata(data)
        assert result.valid

    def test_missing_required_fields(self) -> None:
        """Missing required fields detected."""
        data: dict[str, str] = {"format": "png"}
        result = validate_original_file_metadata(data)
        assert not result.valid
        assert any("Missing required field: width_px" in err for err in result.errors)

    def test_negative_dimensions(self) -> None:
        """Negative dimensions detected."""
        data = {
            "format": "png",
            "width_px": -100,
            "height_px": 3508,
            "channels": 3,
            "bit_depth": 8,
            "file_size_bytes": 1000,
        }

        result = validate_original_file_metadata(data)
        assert not result.valid
        assert any("width_px must be positive" in err for err in result.errors)

    def test_uncommon_format_warning(self) -> None:
        """Uncommon image format produces warning."""
        data = {
            "format": "xyz",
            "width_px": 100,
            "height_px": 100,
            "channels": 3,
            "bit_depth": 8,
            "file_size_bytes": 1000,
        }

        result = validate_original_file_metadata(data)
        assert result.valid
        assert any("Uncommon image format" in warn for warn in result.warnings)

    def test_unusual_channel_count_warning(self) -> None:
        """Unusual channel count produces warning."""
        data = {
            "format": "png",
            "width_px": 100,
            "height_px": 100,
            "channels": 5,
            "bit_depth": 8,
            "file_size_bytes": 1000,
        }

        result = validate_original_file_metadata(data)
        assert result.valid
        assert any("Unusual channel count" in warn for warn in result.warnings)


class TestValidateOriginalLabels:
    """Test OriginalLabels validation."""

    def test_valid_labels_empty(self) -> None:
        """Empty labels are valid."""
        result = validate_original_labels({})
        assert result.valid

    def test_valid_diqa_mos(self) -> None:
        """Valid DIQA MOS scores pass validation."""
        data = {
            "diqa_overall": 4.5,
            "diqa_sharpness": 4.2,
            "diqa_color_fidelity": 4.8,
        }

        result = validate_original_labels(data)
        assert result.valid

    def test_invalid_diqa_mos_range(self) -> None:
        """DIQA MOS outside [1, 5] detected."""
        data = {"diqa_overall": 6.0}
        result = validate_original_labels(data)
        assert not result.valid
        assert any("diqa_overall" in err for err in result.errors)

    def test_valid_ocr_quality_score(self) -> None:
        """Valid OCR quality score passes validation."""
        data = {"ocr_quality_score": 2}
        result = validate_original_labels(data)
        assert result.valid

    def test_invalid_ocr_quality_score(self) -> None:
        """OCR quality score outside [1, 4] detected."""
        data = {"ocr_quality_score": 5}
        result = validate_original_labels(data)
        assert not result.valid
        assert any("ocr_quality_score" in err for err in result.errors)

    def test_valid_coco_annotations(self) -> None:
        """Valid COCO annotations pass validation."""
        data = {
            "doclaynet_annotations": [
                {"bbox": [10.0, 20.0, 100.0, 200.0], "category_id": 1}
            ]
        }

        result = validate_original_labels(data)
        assert result.valid

    def test_funsd_must_be_dict(self) -> None:
        """FUNSD annotations must be dict, not list (P0-4 fix)."""
        data = {"funsd_annotations": [{"key": "value"}]}
        result = validate_original_labels(data)
        assert not result.valid
        assert any("funsd_annotations must be a dict" in err for err in result.errors)

    def test_valid_funsd_dict(self) -> None:
        """Valid FUNSD dict annotations pass validation."""
        data = {"funsd_annotations": {"form": {"key": "value"}}}
        result = validate_original_labels(data)
        assert result.valid

    def test_invalid_bbox_in_annotations(self) -> None:
        """Invalid bbox in COCO annotations detected."""
        data = {
            "doclaynet_annotations": [
                {"bbox": [-10.0, 20.0, 100.0, 200.0], "category_id": 1}
            ]
        }

        result = validate_original_labels(data)
        assert not result.valid
        assert any("doclaynet_annotations[0].bbox" in err for err in result.errors)
