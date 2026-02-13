"""Unit tests for Layer 2 schema migration script.

Tests the migration from flat field format to full nested object schema.
"""

from __future__ import annotations

import json

# Import migration functions
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from migrate_layer2_schema_to_full import (
    is_already_migrated,
    migrate_capture_method,
    migrate_content_flags,
    migrate_dataset,
    migrate_domain,
    migrate_language,
    migrate_quality,
    migrate_resolution,
    migrate_sample_data,
    migrate_structure,
    migrate_text_scope,
    normalize_script_family,
)


class TestMigrateCaptureMethod:
    """Tests for capture_method migration."""

    def test_full_data(self):
        """Test with all capture_method fields present."""
        flat = {
            "capture_method": "born_digital",
            "capture_confidence": 0.95,
            "capture_detection_method": "dataset_config",
        }

        result = migrate_capture_method(flat)

        assert result is not None
        assert result["method"] == "born_digital"
        assert result["confidence"] == pytest.approx(0.95)
        assert result["detection_method"] == "dataset_config"

    def test_minimal_data(self):
        """Test with only capture_method string."""
        flat = {"capture_method": "scanner_flatbed"}

        result = migrate_capture_method(flat)

        assert result is not None
        assert result["method"] == "scanner_flatbed"
        assert result["confidence"] == pytest.approx(0.5)  # default
        assert result["detection_method"] == "unknown"  # default

    def test_missing_capture_method(self):
        """Test with no capture_method field."""
        flat = {"other_field": "value"}

        result = migrate_capture_method(flat)

        assert result is None


class TestMigrateResolution:
    """Tests for resolution migration."""

    def test_full_data(self):
        """Test with all resolution fields."""
        flat = {
            "resolution_dpi": 300,
            "resolution_category": "standard_300",
            "resolution_pixels": [1024, 768],
        }

        result = migrate_resolution(flat)

        assert result is not None
        assert result["dpi"] == 300
        assert result["category"] == "standard_300"
        assert result["pixels"] == [1024, 768]

    def test_partial_data(self):
        """Test with only some resolution fields."""
        flat = {
            "resolution_category": "medium_150-299",
            "resolution_pixels": [800, 600],
        }

        result = migrate_resolution(flat)

        assert result is not None
        assert result["dpi"] is None
        assert result["category"] == "medium_150-299"
        assert result["pixels"] == [800, 600]

    def test_no_resolution(self):
        """Test with no resolution fields."""
        flat = {"capture_method": "scanner"}

        result = migrate_resolution(flat)

        assert result is None


class TestMigrateDomain:
    """Tests for domain migration."""

    def test_full_data(self):
        """Test with all domain fields."""
        flat = {
            "domain_level1": "FIN",
            "domain_level2": "banking",
            "domain_level3": "statements",
            "domain_confidence": 0.9,
        }

        result = migrate_domain(flat)

        assert result is not None
        assert result["level1"] == "FIN"
        assert result["level2"] == "banking"
        assert result["level3"] == "statements"
        assert result["confidence"] == pytest.approx(0.9)

    def test_minimal_data_classified(self):
        """Test with only level1 (classified domain)."""
        flat = {"domain_level1": "TAX"}

        result = migrate_domain(flat)

        assert result is not None
        assert result["level1"] == "TAX"
        assert result["level2"] is None
        assert result["confidence"] == pytest.approx(0.8)  # default for classified

    def test_unk_domain_default_confidence(self):
        """Test UNK domain gets lower default confidence."""
        flat = {"domain_level1": "UNK"}

        result = migrate_domain(flat)

        assert result is not None
        assert result["level1"] == "UNK"
        assert result["confidence"] == pytest.approx(0.3)  # default for UNK

    def test_no_domain(self):
        """Test with no domain fields."""
        flat = {"capture_method": "scanner"}

        result = migrate_domain(flat)

        assert result is None


class TestMigrateStructure:
    """Tests for structure placeholder creation."""

    def test_creates_placeholder(self):
        """Test creates structure object even with no data."""
        flat = {}

        result = migrate_structure(flat)

        assert result is not None
        assert result["text_density"] is None
        assert result["layout_type"] is None
        assert result["element_types"] == []

    def test_preserves_existing_data(self):
        """Test preserves any existing structure fields."""
        flat = {
            "text_density": "dense",
            "layout_type": "multi_column",
            "element_types": ["Table", "Text"],
        }

        result = migrate_structure(flat)

        assert result["text_density"] == "dense"
        assert result["layout_type"] == "multi_column"
        assert result["element_types"] == ["Table", "Text"]


class TestMigrateQuality:
    """Tests for quality placeholder creation."""

    def test_creates_placeholder(self):
        """Test creates quality object even with no data."""
        flat = {}

        result = migrate_quality(flat)

        assert result is not None
        assert result["overall_score"] is None
        assert result["degradations"] == []

    def test_preserves_existing_data(self):
        """Test preserves any existing quality fields."""
        flat = {
            "overall_score": 0.85,
            "degradations": [{"type": "blur", "severity_numeric": 0.3}],
        }

        result = migrate_quality(flat)

        assert result["overall_score"] == pytest.approx(0.85)
        assert len(result["degradations"]) == 1


class TestNormalizeScriptFamily:
    """Tests for script_family normalization."""

    def test_ltr_to_latin(self):
        """Test legacy 'ltr' maps to 'latin'."""
        assert normalize_script_family("ltr") == "latin"
        assert normalize_script_family("LTR") == "latin"

    def test_rtl_to_arabic(self):
        """Test legacy 'rtl' maps to 'arabic'."""
        assert normalize_script_family("rtl") == "arabic"

    def test_valid_values_unchanged(self):
        """Test valid values remain unchanged."""
        assert normalize_script_family("latin") == "latin"
        assert normalize_script_family("cjk") == "cjk"
        assert normalize_script_family("arabic") == "arabic"
        assert normalize_script_family("indic") == "indic"
        assert normalize_script_family("cyrillic") == "cyrillic"

    def test_none_returns_none(self):
        """Test None input returns None."""
        assert normalize_script_family(None) is None


class TestMigrateLanguage:
    """Tests for language migration."""

    def test_iso_format_fields(self):
        """Test migration from iso639/iso15924 format."""
        flat = {
            "iso639_language": "en",
            "iso15924_script": "Latn",
            "script_family": "ltr",
        }

        result = migrate_language(flat)

        assert result["language_code"] == "en"
        assert result["script_code"] == "Latn"
        assert result["script_family"] == "latin"  # normalized from ltr
        assert result["bcp47_tag"] == "en-Latn"
        assert result["is_rtl"] is False
        assert result["is_primary"] is True

    def test_rtl_detection(self):
        """Test RTL detection from Arabic script."""
        flat = {
            "iso639_language": "ar",
            "iso15924_script": "Arab",
        }

        result = migrate_language(flat)

        assert result["language_code"] == "ar"
        assert result["script_code"] == "Arab"
        assert result["is_rtl"] is True

    def test_creates_placeholder_with_no_data(self):
        """Test creates language object even with no language data."""
        flat = {"capture_method": "scanner"}

        result = migrate_language(flat)

        assert result is not None
        assert result["language_code"] is None
        assert result["script_code"] is None
        assert result["is_rtl"] is False
        assert result["is_primary"] is True


class TestMigrateTextScope:
    """Tests for text_scope migration."""

    def test_string_scope(self):
        """Test migration from string text_scope."""
        flat = {
            "text_scope": "page",
            "text_scope_content_type": "printed",
            "text_scope_detection_method": "dataset_metadata",
        }

        result = migrate_text_scope(flat)

        assert result is not None
        assert result["scope"] == "page"
        assert result["content_type"] == "printed"
        assert result["detection_method"] == "dataset_metadata"
        assert result["density"] is None

    def test_no_text_scope(self):
        """Test with no text_scope field."""
        flat = {"capture_method": "scanner"}

        result = migrate_text_scope(flat)

        assert result is None


class TestMigrateContentFlags:
    """Tests for content_flags migration."""

    def test_full_data(self):
        """Test with all content flag fields."""
        flat = {
            "has_table": True,
            "has_formula": False,
            "has_handwriting": True,
            "has_signature": False,
            "has_figure": True,
            "content_flags_tier": "tier_2_model",
            "content_flags_source": "doclayout_yolo",
        }

        result = migrate_content_flags(flat)

        assert result["has_table"] is True
        assert result["has_formula"] is False
        assert result["has_handwriting"] is True
        assert result["has_signature"] is False
        assert result["has_figure"] is True
        assert result["tier"] == "tier_2_model"
        assert result["source"] == "doclayout_yolo"

    def test_defaults_to_false(self):
        """Test missing flags default to False."""
        flat = {}

        result = migrate_content_flags(flat)

        assert result["has_table"] is False
        assert result["has_formula"] is False
        assert result["has_handwriting"] is False
        assert result["has_signature"] is False
        assert result["has_figure"] is False
        assert result["tier"] is None
        assert result["source"] is None


class TestMigrateSampleData:
    """Tests for full sample data migration."""

    def test_complete_fintabnet_sample(self):
        """Test migration of a complete fintabnet-style sample."""
        flat = {
            "capture_method": "born_digital",
            "capture_confidence": 0.95,
            "capture_detection_method": "dataset_config",
            "resolution_category": "standard_300",
            "resolution_pixels": [738, 239],
            "domain_level1": "FIN",
            "domain_confidence": 0.9,
            "iso639_language": "en",
            "iso15924_script": "Latn",
            "script_family": "ltr",
            "text_scope": "page",
            "text_scope_content_type": "printed",
            "has_table": True,
            "has_formula": False,
            "has_handwriting": False,
            "has_signature": False,
            "has_figure": False,
            "content_flags_tier": "tier_0_exact",
            "content_flags_source": "tier_0_exact_by_construction",
        }

        result = migrate_sample_data(flat)

        # Check all nested objects exist
        assert "capture_method" in result
        assert result["capture_method"]["method"] == "born_digital"

        assert "resolution" in result
        assert result["resolution"]["pixels"] == [738, 239]

        assert "domain" in result
        assert result["domain"]["level1"] == "FIN"

        assert "structure" in result
        assert "quality" in result
        assert "language" in result
        assert result["language"]["language_code"] == "en"
        assert result["language"]["script_family"] == "latin"

        assert "text_scope" in result
        assert result["text_scope"]["scope"] == "page"

        assert "content_flags" in result
        assert result["content_flags"]["has_table"] is True
        assert result["content_flags"]["tier"] == "tier_0_exact"

    def test_complete_dibco_sample(self):
        """Test migration of a dibco-style sample (minimal language data)."""
        flat = {
            "capture_method": "scanner_flatbed",
            "capture_confidence": 0.95,
            "capture_detection_method": "dataset_config",
            "resolution_dpi": 299,
            "resolution_category": "medium_150-299",
            "resolution_pixels": [2025, 426],
            "domain_level1": "UNK",
            "domain_confidence": 0.3,
            "has_table": False,
            "has_formula": False,
            "has_handwriting": False,
            "has_figure": False,
            "content_flags_tier": "tier_2_model",
            "content_flags_source": "doclayout_yolo",
            "layout_detections": [],
        }

        result = migrate_sample_data(flat)

        assert result["capture_method"]["method"] == "scanner_flatbed"
        assert result["resolution"]["dpi"] == 299
        assert result["domain"]["level1"] == "UNK"
        assert result["language"]["language_code"] is None
        assert result["layout_detections"] == []

    def test_preserves_layout_detections(self):
        """Test that layout_detections are preserved as-is."""
        flat = {
            "capture_method": "born_digital",
            "layout_detections": [
                {
                    "class_name": "Table",
                    "bbox": [100, 200, 300, 400],
                    "confidence": 0.95,
                    "source": "doclayout_yolo",
                }
            ],
        }

        result = migrate_sample_data(flat)

        assert "layout_detections" in result
        assert len(result["layout_detections"]) == 1
        assert result["layout_detections"][0]["class_name"] == "Table"


class TestIsAlreadyMigrated:
    """Tests for already-migrated detection."""

    def test_flat_format_not_migrated(self):
        """Test flat format is detected as not migrated."""
        flat_data = {"capture_method": "born_digital", "capture_confidence": 0.95}

        assert is_already_migrated(flat_data) is False

    def test_nested_format_is_migrated(self):
        """Test nested format is detected as already migrated."""
        nested_data = {"capture_method": {"method": "born_digital", "confidence": 0.95}}

        assert is_already_migrated(nested_data) is True

    def test_empty_data(self):
        """Test empty data is not considered migrated."""
        assert is_already_migrated({}) is False


class TestMigrateDataset:
    """Integration tests for dataset migration."""

    def test_migrate_small_dataset(self, tmp_path: Path):
        """Test migrating a small test dataset."""
        # Create test input
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_dataset = {
            "dataset_name": "test_dataset",
            "sample_count": 2,
            "samples": [
                {
                    "id": "sample-1",
                    "enrichments": {
                        "versions": [
                            {
                                "version": 1,
                                "data": {
                                    "capture_method": "born_digital",
                                    "capture_confidence": 0.95,
                                    "domain_level1": "FIN",
                                    "has_table": True,
                                    "has_formula": False,
                                    "has_handwriting": False,
                                    "has_signature": False,
                                    "has_figure": False,
                                },
                            }
                        ]
                    },
                },
                {
                    "id": "sample-2",
                    "enrichments": {
                        "versions": [
                            {
                                "version": 1,
                                "data": {
                                    "capture_method": "scanner_flatbed",
                                    "resolution_dpi": 300,
                                    "domain_level1": "UNK",
                                    "has_table": False,
                                    "has_formula": False,
                                    "has_handwriting": False,
                                    "has_signature": False,
                                    "has_figure": False,
                                },
                            }
                        ]
                    },
                },
            ],
        }

        input_file = input_dir / "test_dataset_metadata.json"
        with open(input_file, "w") as f:
            json.dump(test_dataset, f)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Run migration
        result = migrate_dataset(
            dataset_name="test_dataset",
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=False,
            verbose=False,
        )

        # Check result
        assert result["status"] == "success"
        assert result["samples_total"] == 2
        assert result["samples_migrated"] == 2
        assert len(result["errors"]) == 0

        # Verify output file
        output_file = output_dir / "test_dataset_metadata.json"
        assert output_file.exists()

        with open(output_file) as f:
            migrated_data = json.load(f)

        # Check migration metadata
        assert "migration" in migrated_data
        assert migrated_data["migration"]["samples_processed"] == 2

        # Check sample data is nested
        sample_data = migrated_data["samples"][0]["enrichments"]["versions"][0]["data"]
        assert isinstance(sample_data["capture_method"], dict)
        assert sample_data["capture_method"]["method"] == "born_digital"
        assert "structure" in sample_data
        assert "quality" in sample_data
        assert "language" in sample_data
        assert "content_flags" in sample_data

    def test_skip_already_migrated(self, tmp_path: Path):
        """Test that already migrated samples are skipped."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create dataset with already-migrated format
        test_dataset = {
            "dataset_name": "test_dataset",
            "sample_count": 1,
            "samples": [
                {
                    "id": "sample-1",
                    "enrichments": {
                        "versions": [
                            {
                                "version": 1,
                                "data": {
                                    "capture_method": {
                                        "method": "born_digital",
                                        "confidence": 0.95,
                                    },
                                    "domain": {"level1": "FIN"},
                                    "content_flags": {"has_table": True},
                                },
                            }
                        ]
                    },
                },
            ],
        }

        input_file = input_dir / "test_dataset_metadata.json"
        with open(input_file, "w") as f:
            json.dump(test_dataset, f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = migrate_dataset(
            dataset_name="test_dataset",
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        assert result["samples_already_migrated"] == 1
        assert result["samples_migrated"] == 0

    def test_dry_run_no_write(self, tmp_path: Path):
        """Test dry run doesn't write files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_dataset = {
            "dataset_name": "test_dataset",
            "sample_count": 1,
            "samples": [
                {
                    "id": "sample-1",
                    "enrichments": {
                        "versions": [
                            {"version": 1, "data": {"capture_method": "scanner"}}
                        ]
                    },
                }
            ],
        }

        input_file = input_dir / "test_dataset_metadata.json"
        with open(input_file, "w") as f:
            json.dump(test_dataset, f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = migrate_dataset(
            dataset_name="test_dataset",
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=True,
        )

        assert result["status"] == "success"
        # Output file should NOT exist in dry run
        output_file = output_dir / "test_dataset_metadata.json"
        assert not output_file.exists()

    def test_creates_backup(self, tmp_path: Path):
        """Test backup is created when specified."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        backup_dir = tmp_path / "backup"

        test_dataset = {
            "dataset_name": "test_dataset",
            "sample_count": 1,
            "samples": [
                {
                    "id": "sample-1",
                    "enrichments": {
                        "versions": [
                            {"version": 1, "data": {"capture_method": "scanner"}}
                        ]
                    },
                }
            ],
        }

        input_file = input_dir / "test_dataset_metadata.json"
        with open(input_file, "w") as f:
            json.dump(test_dataset, f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        migrate_dataset(
            dataset_name="test_dataset",
            input_dir=input_dir,
            output_dir=output_dir,
            backup_dir=backup_dir,
            dry_run=False,
        )

        # Backup should exist
        backup_file = backup_dir / "test_dataset_metadata.json"
        assert backup_file.exists()

        # Backup should contain original data
        with open(backup_file) as f:
            backup_data = json.load(f)
        assert (
            backup_data["samples"][0]["enrichments"]["versions"][0]["data"][
                "capture_method"
            ]
            == "scanner"
        )

    def test_missing_file(self, tmp_path: Path):
        """Test handling of missing metadata file."""
        result = migrate_dataset(
            dataset_name="nonexistent",
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        assert result["status"] == "skipped"
        assert "No metadata file found" in result["reason"]
