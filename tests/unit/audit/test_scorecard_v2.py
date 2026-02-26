"""Tests for Scorecard v2.0: expanded prescreening, new dimensions, grade caps.

Covers:
  - 30 new prescreening validators (Groups A-I)
  - Core vs Extended registry split
  - compute_label_accuracy
  - compute_confidence_quality
  - Updated field_coverage (core/extended weighted)
  - Grade cap logic (7 caps + stacking)
  - Integration / backward compatibility
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.audit.automated_prescreening import (
    _CORE_VALIDATORS,
    _EXTENDED_VALIDATORS,
    _SIMPLE_VALIDATORS,
    ALL_FIELD_NAMES,
    CORE_FIELD_NAMES,
    EXTENDED_FIELD_NAMES,
    VALID_LAYOUT_TYPES,
    VALID_PROVENANCE_TIERS,
    VALID_RELIABILITY_CATEGORIES,
    VALID_RESOLUTION_CATEGORIES,
    VALID_SCRIPT_CODES,
    VALID_TEXT_DENSITIES,
    _check_capture_confidence_valid,
    _check_character_height_present,
    _check_content_flag_confidence_present,
    _check_domain_confidence_valid,
    _check_geometric_present,
    _check_handwriting_assessment_present,
    _check_handwriting_confidence_valid,
    _check_has_code_present,
    _check_has_signature_present,
    _check_image_properties_document_age,
    _check_language_bcp47_present,
    _check_language_confidence_valid,
    _check_language_detection_method_present,
    _check_language_script_code_valid,
    _check_orientation_confidence_valid,
    _check_physical_degradation_present,
    _check_provenance_tier_valid,
    _check_reliability_assessed_count,
    _check_reliability_hard_label_ratio,
    _check_reliability_min_confidence,
    _check_reliability_min_confidence_category,
    _check_reliability_summary_present,
    _check_resolution_category_valid,
    _check_resolution_dpi_present,
    _check_resolution_quality_present,
    _check_skew_angle_present,
    _check_skew_confidence_valid,
    _check_structure_confidence_present,
    _check_structure_layout_type_valid,
    _check_structure_text_density_valid,
    run_prescreening,
)
from scripts.audit.compute_scorecard import (
    CONFIDENCE_FIELDS,
    _apply_grade_cap,
    _load_content_flag_fp_rates,
    compute_confidence_quality,
    compute_field_coverage,
    compute_label_accuracy,
    compute_overall,
    load_scorecard_config,
)


# ===================================================================
# Helpers
# ===================================================================
def _make_screening_json(
    tmp_path: Path,
    per_field: dict[str, dict[str, int]],
    *,
    core_pass_rate_pct: float | None = None,
    extended_pass_rate_pct: float | None = None,
) -> Path:
    """Write a minimal automated_screening.json and return its path."""
    data: dict[str, Any] = {"per_field_results": per_field}
    if core_pass_rate_pct is not None:
        data["core_pass_rate_pct"] = core_pass_rate_pct
    if extended_pass_rate_pct is not None:
        data["extended_pass_rate_pct"] = extended_pass_rate_pct
    path = tmp_path / "automated_screening.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_vlm_json(
    tmp_path: Path,
    data: dict[str, Any],
) -> Path:
    """Write vlm_corrections.json and return its path."""
    path = tmp_path / "vlm_corrections.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_catalog_json(
    tmp_path: Path,
    data: dict[str, Any],
) -> Path:
    """Write defect_catalog.json and return its path."""
    path = tmp_path / "defect_catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _v2_config() -> dict[str, Any]:
    """Return a minimal v2.0 scorecard config."""
    return load_scorecard_config()


# ===================================================================
# 1. Expanded Prescreening Validators  (~30 tests)
# ===================================================================


class TestGroupAReliabilityValidators:
    """Group A: Sample Reliability & Confidence (8 validators)."""

    def test_reliability_summary_present_pass(self) -> None:
        data = {"sample_reliability_summary": {"min_confidence": 0.8}}
        ok, _ = _check_reliability_summary_present(data)
        assert ok

    def test_reliability_summary_present_missing(self) -> None:
        ok, detail = _check_reliability_summary_present({})
        assert not ok
        assert "missing" in (detail or "")

    def test_reliability_min_confidence_category_pass(self) -> None:
        data = {
            "sample_reliability_summary": {
                "min_confidence_category": "hard_label",
            },
        }
        ok, _ = _check_reliability_min_confidence_category(data)
        assert ok

    def test_reliability_min_confidence_category_invalid(self) -> None:
        data = {
            "sample_reliability_summary": {
                "min_confidence_category": "garbage",
            },
        }
        ok, detail = _check_reliability_min_confidence_category(data)
        assert not ok
        assert "garbage" in (detail or "")

    def test_reliability_assessed_count_pass(self) -> None:
        data = {"sample_reliability_summary": {"assessed_field_count": 5}}
        ok, _ = _check_reliability_assessed_count(data)
        assert ok

    def test_reliability_assessed_count_too_low(self) -> None:
        data = {"sample_reliability_summary": {"assessed_field_count": 2}}
        ok, detail = _check_reliability_assessed_count(data)
        assert not ok
        assert "min 3" in (detail or "")

    def test_reliability_min_confidence_pass(self) -> None:
        data = {"sample_reliability_summary": {"min_confidence": 0.7}}
        ok, _ = _check_reliability_min_confidence(data)
        assert ok

    def test_reliability_min_confidence_too_low(self) -> None:
        data = {"sample_reliability_summary": {"min_confidence": 0.3}}
        ok, detail = _check_reliability_min_confidence(data)
        assert not ok
        assert "min 0.5" in (detail or "")

    def test_reliability_min_confidence_absent_passes(self) -> None:
        """Extended validator: pass when parent is absent."""
        ok, _ = _check_reliability_min_confidence({})
        assert ok

    def test_reliability_hard_label_ratio_pass(self) -> None:
        data = {
            "sample_reliability_summary": {
                "hard_field_count": 4,
                "assessed_field_count": 10,
            },
        }
        ok, _ = _check_reliability_hard_label_ratio(data)
        assert ok

    def test_reliability_hard_label_ratio_too_low(self) -> None:
        data = {
            "sample_reliability_summary": {
                "hard_field_count": 1,
                "assessed_field_count": 10,
            },
        }
        ok, detail = _check_reliability_hard_label_ratio(data)
        assert not ok
        assert "min 0.3" in (detail or "")

    def test_reliability_hard_label_ratio_absent_passes(self) -> None:
        ok, _ = _check_reliability_hard_label_ratio({})
        assert ok

    def test_capture_confidence_valid_flat(self) -> None:
        data = {"capture_confidence": 0.8}
        ok, _ = _check_capture_confidence_valid(data)
        assert ok

    def test_capture_confidence_valid_nested(self) -> None:
        data = {"capture_method_info": {"confidence": 0.9}}
        ok, _ = _check_capture_confidence_valid(data)
        assert ok

    def test_capture_confidence_missing(self) -> None:
        ok, detail = _check_capture_confidence_valid({})
        assert not ok
        assert "missing" in (detail or "")

    def test_capture_confidence_too_low(self) -> None:
        data = {"capture_confidence": 0.3}
        ok, detail = _check_capture_confidence_valid(data)
        assert not ok
        assert "min 0.5" in (detail or "")

    def test_domain_confidence_valid_pass(self) -> None:
        data = {"domain_confidence": 0.6}
        ok, _ = _check_domain_confidence_valid(data)
        assert ok

    def test_domain_confidence_missing(self) -> None:
        ok, detail = _check_domain_confidence_valid({})
        assert not ok
        assert "missing" in (detail or "")

    def test_language_confidence_valid_pass(self) -> None:
        data = {"language_confidence": 0.7}
        ok, _ = _check_language_confidence_valid(data)
        assert ok

    def test_language_confidence_too_low(self) -> None:
        data = {"language_confidence": 0.2}
        ok, detail = _check_language_confidence_valid(data)
        assert not ok
        assert "min 0.5" in (detail or "")


class TestGroupBLanguageValidators:
    """Group B: Language & Script Completeness (3 validators)."""

    def test_language_script_code_valid_pass(self) -> None:
        data = {"iso15924_script_code": "Latn"}
        ok, _ = _check_language_script_code_valid(data)
        assert ok

    def test_language_script_code_valid_nested(self) -> None:
        data = {"language_info": {"script_code": "Hans"}}
        ok, _ = _check_language_script_code_valid(data)
        assert ok

    def test_language_script_code_invalid(self) -> None:
        data = {"iso15924_script_code": "INVALID"}
        ok, detail = _check_language_script_code_valid(data)
        assert not ok
        assert "ISO 15924" in (detail or "")

    def test_language_script_code_missing(self) -> None:
        ok, detail = _check_language_script_code_valid({})
        assert not ok
        assert "missing" in (detail or "")

    def test_language_bcp47_present_pass(self) -> None:
        data = {"language_info": {"bcp47_tag": "en-US"}}
        ok, _ = _check_language_bcp47_present(data)
        assert ok

    def test_language_bcp47_absent_passes(self) -> None:
        """Extended: pass if parent absent."""
        ok, _ = _check_language_bcp47_present({})
        assert ok

    def test_language_bcp47_empty_fails(self) -> None:
        data = {"language_info": {"bcp47_tag": ""}}
        ok, detail = _check_language_bcp47_present(data)
        assert not ok
        assert "empty" in (detail or "")

    def test_language_detection_method_pass(self) -> None:
        data = {"language_info": {"detection_method": "fasttext"}}
        ok, _ = _check_language_detection_method_present(data)
        assert ok

    def test_language_detection_method_absent_passes(self) -> None:
        ok, _ = _check_language_detection_method_present({})
        assert ok


class TestGroupCGeometricValidators:
    """Group C: Geometric Properties (4 validators)."""

    def test_geometric_present_pass(self) -> None:
        data = {"geometric": {"skew_angle_degrees": 2.5}}
        ok, _ = _check_geometric_present(data)
        assert ok

    def test_geometric_absent_passes(self) -> None:
        """Extended: pass if absent."""
        ok, _ = _check_geometric_present({})
        assert ok

    def test_skew_angle_present_pass(self) -> None:
        data = {"geometric": {"skew_angle_degrees": 1.2}}
        ok, _ = _check_skew_angle_present(data)
        assert ok

    def test_skew_angle_missing_when_geo_present(self) -> None:
        data = {"geometric": {}}
        ok, detail = _check_skew_angle_present(data)
        assert not ok
        assert "missing" in (detail or "")

    def test_skew_angle_no_geo_passes(self) -> None:
        ok, _ = _check_skew_angle_present({})
        assert ok

    def test_skew_confidence_valid_pass(self) -> None:
        data = {"geometric": {"skew_angle_degrees": 1.0, "skew_confidence": 0.8}}
        ok, _ = _check_skew_confidence_valid(data)
        assert ok

    def test_skew_confidence_too_low(self) -> None:
        data = {"geometric": {"skew_angle_degrees": 1.0, "skew_confidence": 0.3}}
        ok, detail = _check_skew_confidence_valid(data)
        assert not ok
        assert "min 0.5" in (detail or "")

    def test_skew_confidence_no_skew_passes(self) -> None:
        data = {"geometric": {}}
        ok, _ = _check_skew_confidence_valid(data)
        assert ok

    def test_orientation_confidence_valid_pass(self) -> None:
        data = {"geometric": {"orientation_class": 0, "orientation_confidence": 0.9}}
        ok, _ = _check_orientation_confidence_valid(data)
        assert ok

    def test_orientation_confidence_missing(self) -> None:
        data = {"geometric": {"orientation_class": 0}}
        ok, detail = _check_orientation_confidence_valid(data)
        assert not ok
        assert "missing" in (detail or "")


class TestGroupDResolutionValidators:
    """Group D: Resolution & Character Height (4 validators)."""

    def test_resolution_dpi_present_pass(self) -> None:
        data = {"resolution_info": {"dpi": 300}}
        ok, _ = _check_resolution_dpi_present(data)
        assert ok

    def test_resolution_dpi_absent_passes(self) -> None:
        ok, _ = _check_resolution_dpi_present({})
        assert ok

    def test_resolution_dpi_missing_in_obj(self) -> None:
        data = {"resolution_info": {}}
        ok, detail = _check_resolution_dpi_present(data)
        assert not ok
        assert "missing" in (detail or "")

    def test_resolution_category_valid_pass(self) -> None:
        data = {"resolution_category": "standard_300"}
        ok, _ = _check_resolution_category_valid(data)
        assert ok

    def test_resolution_category_invalid(self) -> None:
        data = {"resolution_category": "super_high"}
        ok, detail = _check_resolution_category_valid(data)
        assert not ok
        assert "not in allowed set" in (detail or "")

    def test_resolution_category_missing(self) -> None:
        ok, detail = _check_resolution_category_valid({})
        assert not ok
        assert "missing" in (detail or "")

    def test_resolution_quality_present_absent_passes(self) -> None:
        ok, _ = _check_resolution_quality_present({})
        assert ok

    def test_character_height_present_pass(self) -> None:
        data = {"resolution_info": {"character_height_px": 32.0}}
        ok, _ = _check_character_height_present(data)
        assert ok

    def test_character_height_zero_fails(self) -> None:
        data = {"resolution_info": {"character_height_px": 0}}
        ok, detail = _check_character_height_present(data)
        assert not ok
        assert "must be > 0" in (detail or "")

    def test_character_height_absent_passes(self) -> None:
        ok, _ = _check_character_height_present({})
        assert ok


class TestGroupEContentFlagValidators:
    """Group E: Content Flags Expanded (3 validators)."""

    def test_content_flag_confidence_present_pass(self) -> None:
        data = {"content_flags_confidence": 0.85}
        ok, _ = _check_content_flag_confidence_present(data)
        assert ok

    def test_content_flag_confidence_absent_passes(self) -> None:
        ok, _ = _check_content_flag_confidence_present({})
        assert ok

    def test_has_code_present_pass(self) -> None:
        data = {"has_code": False}
        ok, _ = _check_has_code_present(data)
        assert ok

    def test_has_code_missing_passes(self) -> None:
        """Extended validator: pass-if-absent."""
        ok, detail = _check_has_code_present({})
        assert ok
        assert detail is None

    def test_has_code_in_nested_flags_pass(self) -> None:
        data = {"content_flags": {"has_code": True}}
        ok, _ = _check_has_code_present(data)
        assert ok

    def test_has_signature_present_pass(self) -> None:
        data = {"has_signature": False}
        ok, _ = _check_has_signature_present(data)
        assert ok

    def test_has_signature_missing_passes(self) -> None:
        """Extended validator: pass-if-absent."""
        ok, detail = _check_has_signature_present({})
        assert ok
        assert detail is None


class TestGroupFHandwritingValidators:
    """Group F: Handwriting Assessment (2 validators)."""

    def test_handwriting_assessment_present_pass(self) -> None:
        data = {"handwriting_assessment": {"presence": "none"}}
        ok, _ = _check_handwriting_assessment_present(data)
        assert ok

    def test_handwriting_assessment_absent_passes(self) -> None:
        ok, _ = _check_handwriting_assessment_present({})
        assert ok

    def test_handwriting_assessment_no_presence_fails(self) -> None:
        data = {"handwriting_assessment": {"confidence": 0.8}}
        ok, detail = _check_handwriting_assessment_present(data)
        assert not ok
        assert "presence" in (detail or "")

    def test_handwriting_confidence_valid_pass(self) -> None:
        data = {"handwriting_assessment": {"confidence": 0.7}}
        ok, _ = _check_handwriting_confidence_valid(data)
        assert ok

    def test_handwriting_confidence_too_low(self) -> None:
        data = {"handwriting_assessment": {"confidence": 0.3}}
        ok, detail = _check_handwriting_confidence_valid(data)
        assert not ok
        assert "min 0.5" in (detail or "")

    def test_handwriting_confidence_absent_passes(self) -> None:
        ok, _ = _check_handwriting_confidence_valid({})
        assert ok


class TestGroupGStructureValidators:
    """Group G: Structure & Layout Quality (3 validators)."""

    def test_structure_layout_type_valid_pass(self) -> None:
        data = {"structure_info": {"layout_type": "single_column"}}
        ok, _ = _check_structure_layout_type_valid(data)
        assert ok

    def test_structure_layout_type_invalid(self) -> None:
        data = {"structure_info": {"layout_type": "invalid_type"}}
        ok, detail = _check_structure_layout_type_valid(data)
        assert not ok
        assert "not in allowed set" in (detail or "")

    def test_structure_layout_type_absent_passes(self) -> None:
        ok, _ = _check_structure_layout_type_valid({})
        assert ok

    def test_structure_text_density_valid_pass(self) -> None:
        data = {"structure_info": {"text_density": "dense"}}
        ok, _ = _check_structure_text_density_valid(data)
        assert ok

    def test_structure_text_density_invalid(self) -> None:
        data = {"structure_info": {"text_density": "packed"}}
        ok, detail = _check_structure_text_density_valid(data)
        assert not ok
        assert "not in allowed set" in (detail or "")

    def test_structure_confidence_present_pass(self) -> None:
        data = {"structure_info": {"confidence": 0.9}}
        ok, _ = _check_structure_confidence_present(data)
        assert ok

    def test_structure_confidence_missing_when_present(self) -> None:
        data = {"structure_info": {"layout_type": "complex"}}
        ok, detail = _check_structure_confidence_present(data)
        assert not ok
        assert "missing" in (detail or "")

    def test_structure_confidence_absent_passes(self) -> None:
        ok, _ = _check_structure_confidence_present({})
        assert ok


class TestGroupHImagePropertiesValidators:
    """Group H: Image Properties & Physical Degradation (2 validators)."""

    def test_image_properties_document_age_pass(self) -> None:
        data = {"image_properties": {"document_age": "modern"}}
        ok, _ = _check_image_properties_document_age(data)
        assert ok

    def test_image_properties_document_age_invalid(self) -> None:
        data = {"image_properties": {"document_age": "ancient"}}
        ok, detail = _check_image_properties_document_age(data)
        assert not ok
        assert "ancient" in (detail or "")

    def test_image_properties_document_age_absent_passes(self) -> None:
        ok, _ = _check_image_properties_document_age({})
        assert ok

    def test_physical_degradation_present_pass(self) -> None:
        data = {"physical_degradation": {"shadow_severity": "none"}}
        ok, _ = _check_physical_degradation_present(data)
        assert ok

    def test_physical_degradation_absent_passes(self) -> None:
        ok, _ = _check_physical_degradation_present({})
        assert ok


class TestGroupIProvenanceValidator:
    """Group I: Provenance & Audit Trail (1 validator)."""

    def test_provenance_tier_valid_method(self) -> None:
        data = {"method": "tier_2_model"}
        ok, _ = _check_provenance_tier_valid(data)
        assert ok

    def test_provenance_tier_valid_flat(self) -> None:
        data = {"provenance_tier": "tier_0_exact"}
        ok, _ = _check_provenance_tier_valid(data)
        assert ok

    def test_provenance_tier_invalid(self) -> None:
        # An explicitly-set but unrecognised value must fail.
        data = {"provenance_tier": "manual_guess"}
        ok, detail = _check_provenance_tier_valid(data)
        assert not ok
        assert "not in allowed set" in (detail or "")

    def test_provenance_tier_missing(self) -> None:
        # pass-if-absent: until integration scripts populate the field,
        # absence must not penalise every sample.
        ok, _detail = _check_provenance_tier_valid({})
        assert ok


class TestCoreExtendedRegistrySplit:
    """Tests for Core vs Extended validator registry structure."""

    def test_core_validators_count(self) -> None:
        """Core should have 23 validators (+ quality_overall_mos tracked separately)."""
        # _CORE_VALIDATORS list + quality_overall_mos handled separately
        assert len(_CORE_VALIDATORS) == 23
        assert len(CORE_FIELD_NAMES) == 24  # +quality_overall_mos

    def test_extended_validators_count(self) -> None:
        """Extended should have 21 validators."""
        assert len(_EXTENDED_VALIDATORS) == 21
        assert len(EXTENDED_FIELD_NAMES) == 21

    def test_simple_is_union(self) -> None:
        """_SIMPLE_VALIDATORS should be Core + Extended."""
        assert len(_SIMPLE_VALIDATORS) == len(_CORE_VALIDATORS) + len(
            _EXTENDED_VALIDATORS
        )

    def test_all_field_names_complete(self) -> None:
        """ALL_FIELD_NAMES = CORE_FIELD_NAMES + EXTENDED_FIELD_NAMES."""
        assert set(ALL_FIELD_NAMES) == set(CORE_FIELD_NAMES) | set(EXTENDED_FIELD_NAMES)

    def test_no_overlap(self) -> None:
        """No field name appears in both core and extended."""
        overlap = set(CORE_FIELD_NAMES) & set(EXTENDED_FIELD_NAMES)
        assert overlap == set(), f"Overlapping fields: {overlap}"

    def test_valid_constant_sets_populated(self) -> None:
        """Verify all new frozensets have expected members."""
        assert "tier_0_exact" in VALID_PROVENANCE_TIERS
        assert "hard_label" in VALID_RELIABILITY_CATEGORIES
        assert "Latn" in VALID_SCRIPT_CODES
        assert "standard_300" in VALID_RESOLUTION_CATEGORIES
        assert "single_column" in VALID_LAYOUT_TYPES
        assert "dense" in VALID_TEXT_DENSITIES


# ===================================================================
# 2. compute_label_accuracy  (~6 tests)
# ===================================================================


class TestComputeLabelAccuracy:
    """Tests for compute_label_accuracy."""

    def test_per_field_accuracy_weighted(self, tmp_path: Path) -> None:
        """Per-field accuracy with both critical and structural fields."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "accuracy_by_field": {
                    "iso639_language": 0.95,
                    "script_family": 0.90,
                    "domain_level1": 0.85,
                    "capture_method": 0.80,
                    "orientation_class": 0.70,
                    "handwriting_present": 0.60,
                },
            },
        )
        catalog = tmp_path / "defect_catalog.json"
        config = _v2_config()
        score = compute_label_accuracy(vlm, catalog, config)
        assert score is not None
        # Critical avg = (95+90+85+80)/4 = 87.5
        # Structural avg = (70+60)/2 = 65.0
        # Weighted = 87.5*0.6 + 65.0*0.4 = 52.5 + 26.0 = 78.5
        assert abs(score - 78.5) < 0.5

    def test_per_field_accuracy_dict_format(self, tmp_path: Path) -> None:
        """Per-field accuracy with dict-format values (accuracy_pct, correct/incorrect)."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "accuracy_by_field": {
                    "iso639_language": {
                        "correct": 95,
                        "incorrect": 5,
                        "accuracy_pct": 95.0,
                    },
                    "script_family": {
                        "correct": 90,
                        "incorrect": 10,
                        "accuracy_pct": 90.0,
                    },
                    "domain_level1": {
                        "correct": 85,
                        "incorrect": 15,
                        "accuracy_pct": 85.0,
                    },
                    "capture_method": {
                        "correct": 80,
                        "incorrect": 20,
                        "accuracy_pct": 80.0,
                    },
                    "orientation_class": {
                        "correct": 70,
                        "incorrect": 30,
                        "accuracy_pct": 70.0,
                    },
                    "handwriting_present": {
                        "correct": 60,
                        "incorrect": 40,
                        "accuracy_pct": 60.0,
                    },
                },
            },
        )
        catalog = tmp_path / "defect_catalog.json"
        config = _v2_config()
        score = compute_label_accuracy(vlm, catalog, config)
        assert score is not None
        # Critical avg = (95+90+85+80)/4 = 87.5
        # Structural avg = (70+60)/2 = 65.0
        # Weighted = 87.5*0.6 + 65.0*0.4 = 52.5 + 26.0 = 78.5
        assert abs(score - 78.5) < 0.5

    def test_per_field_accuracy_dict_without_pct(self, tmp_path: Path) -> None:
        """Dict-format values computed from correct/incorrect when accuracy_pct missing."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "accuracy_by_field": {
                    "iso639_language": {"correct": 90, "incorrect": 10},
                    "script_family": {"correct": 80, "incorrect": 20},
                },
            },
        )
        catalog = tmp_path / "defect_catalog.json"
        config = _v2_config()
        score = compute_label_accuracy(vlm, catalog, config)
        assert score is not None
        # Only critical fields: avg = (90+80)/2 = 85.0
        assert abs(score - 85.0) < 0.5

    def test_fallback_to_passing_sample_accuracy(self, tmp_path: Path) -> None:
        """Falls back to passing_sample_accuracy if no per-field data."""
        vlm = _make_vlm_json(tmp_path, {"passing_sample_accuracy": 0.92})
        catalog = tmp_path / "defect_catalog.json"
        score = compute_label_accuracy(vlm, catalog)
        assert score is not None
        assert abs(score - 92.0) < 0.1

    def test_fallback_to_defect_catalog(self, tmp_path: Path) -> None:
        """Falls back to defect_catalog vlm_validation."""
        catalog = _make_catalog_json(
            tmp_path,
            {"vlm_validation": {"passing_sample_accuracy": 0.88}},
        )
        vlm = tmp_path / "vlm_corrections.json"  # Does not exist
        score = compute_label_accuracy(vlm, catalog)
        assert score is not None
        assert abs(score - 88.0) < 0.1

    def test_missing_all_returns_none(self, tmp_path: Path) -> None:
        """Returns None when no VLM data available."""
        vlm = tmp_path / "vlm_corrections.json"
        catalog = tmp_path / "defect_catalog.json"
        score = compute_label_accuracy(vlm, catalog)
        assert score is None

    def test_only_critical_fields(self, tmp_path: Path) -> None:
        """Score uses only critical fields when no structural data."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "accuracy_by_field": {
                    "iso639_language": 0.90,
                    "domain_level1": 0.80,
                },
            },
        )
        catalog = tmp_path / "defect_catalog.json"
        score = compute_label_accuracy(vlm, catalog)
        assert score is not None
        # Only critical avg = (90+80)/2 = 85.0
        assert abs(score - 85.0) < 0.5

    def test_validation_summary_fallback(self, tmp_path: Path) -> None:
        """Per-field accuracy from nested validation_summary."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "validation_summary": {
                    "accuracy_by_field": {
                        "iso639_language": 0.95,
                        "script_family": 0.90,
                    },
                },
            },
        )
        catalog = tmp_path / "defect_catalog.json"
        score = compute_label_accuracy(vlm, catalog)
        assert score is not None
        assert score > 0


# ===================================================================
# 3. compute_confidence_quality  (~6 tests)
# ===================================================================


class TestComputeConfidenceQuality:
    """Tests for compute_confidence_quality."""

    def test_all_confidence_fields_present(self, tmp_path: Path) -> None:
        """All 13 confidence fields present with high pass rates."""
        per_field = {field: {"pass": 90, "fail": 10} for field in CONFIDENCE_FIELDS}
        path = _make_screening_json(tmp_path, per_field)
        score = compute_confidence_quality(path)
        assert score is not None
        assert abs(score - 90.0) < 0.1

    def test_partial_confidence_fields(self, tmp_path: Path) -> None:
        """Only some confidence fields available."""
        per_field = {
            "reliability_summary_present": {"pass": 100, "fail": 0},
            "capture_confidence_valid": {"pass": 80, "fail": 20},
            "domain_confidence_valid": {"pass": 60, "fail": 40},
        }
        path = _make_screening_json(tmp_path, per_field)
        score = compute_confidence_quality(path)
        assert score is not None
        # avg = (100 + 80 + 60) / 3 = 80.0
        assert abs(score - 80.0) < 0.1

    def test_all_confidence_fields_zero(self, tmp_path: Path) -> None:
        """All confidence fields at 0% pass rate."""
        per_field = {field: {"pass": 0, "fail": 100} for field in CONFIDENCE_FIELDS}
        path = _make_screening_json(tmp_path, per_field)
        score = compute_confidence_quality(path)
        assert score is not None
        assert score == 0.0

    def test_missing_screening_file_returns_none(self, tmp_path: Path) -> None:
        """Returns None if screening file missing."""
        path = tmp_path / "automated_screening.json"
        score = compute_confidence_quality(path)
        assert score is None

    def test_no_confidence_fields_returns_none(self, tmp_path: Path) -> None:
        """Returns None if no confidence fields in screening."""
        per_field = {"split": {"pass": 100, "fail": 0}}
        path = _make_screening_json(tmp_path, per_field)
        score = compute_confidence_quality(path)
        assert score is None

    def test_uses_config_field_list(self, tmp_path: Path) -> None:
        """Respects custom confidence field list from config."""
        per_field = {
            "reliability_summary_present": {"pass": 70, "fail": 30},
            "capture_confidence_valid": {"pass": 90, "fail": 10},
        }
        path = _make_screening_json(tmp_path, per_field)
        config = {
            "dimensions": {
                "confidence_quality": {
                    "confidence_fields": [
                        "reliability_summary_present",
                        "capture_confidence_valid",
                    ],
                },
            },
        }
        score = compute_confidence_quality(path, config)
        assert score is not None
        assert abs(score - 80.0) < 0.1


# ===================================================================
# 4. Updated field_coverage  (~3 tests)
# ===================================================================


class TestUpdatedFieldCoverage:
    """Tests for field_coverage with core/extended weighted approach."""

    def test_core_extended_weighted(self, tmp_path: Path) -> None:
        """Uses pre-computed core/extended rates with 70/30 weighting."""
        path = _make_screening_json(
            tmp_path,
            {},
            core_pass_rate_pct=80.0,
            extended_pass_rate_pct=60.0,
        )
        score = compute_field_coverage(path)
        assert score is not None
        # 80*0.7 + 60*0.3 = 56 + 18 = 74.0
        assert abs(score - 74.0) < 0.1

    def test_fallback_to_simple_average(self, tmp_path: Path) -> None:
        """Falls back to simple average when no core/extended data (old format)."""
        per_field = {
            "split": {"pass": 90, "fail": 10},
            "capture_method": {"pass": 80, "fail": 20},
        }
        path = _make_screening_json(tmp_path, per_field)
        score = compute_field_coverage(path)
        assert score is not None
        # avg = (90 + 80) / 2 = 85.0
        assert abs(score - 85.0) < 0.1

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Returns None when file is missing."""
        path = tmp_path / "automated_screening.json"
        score = compute_field_coverage(path)
        assert score is None


# ===================================================================
# 5. Grade cap logic  (~7 tests)
# ===================================================================


class TestGradeCapLogic:
    """Tests for grade cap application and stacking."""

    def test_apply_grade_cap_downgrades(self) -> None:
        """Cap downgrades A to C."""
        grade, msg = _apply_grade_cap("A", "C", "test reason", None)
        assert grade == "C"
        assert "capped" in (msg or "").lower()

    def test_apply_grade_cap_no_effect_when_already_low(self) -> None:
        """Cap does not change grade if already at or below max."""
        grade, msg = _apply_grade_cap("D", "C", "test", None)
        assert grade == "D"
        assert msg is None

    def test_cap_stacking(self) -> None:
        """Multiple caps stack correctly (pipe-separated messages)."""
        grade, msg = _apply_grade_cap("A", "C", "reason1", None)
        grade, msg = _apply_grade_cap(grade, "D", "reason2", msg)
        assert grade == "D"
        assert "|" in (msg or "")
        assert "reason1" in (msg or "")
        assert "reason2" in (msg or "")

    def test_missing_vlm_cap(self, tmp_path: Path) -> None:
        """Missing label_accuracy -> grade capped at D."""
        config = _v2_config()
        scores: dict[str, float | None] = {
            "field_coverage": 95.0,
            "field_validity": 95.0,
            "doc_completeness": 90.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 90.0,
            "label_accuracy": None,
            "confidence_quality": 80.0,
        }
        result = compute_overall(scores, config)
        # label_accuracy is required=True, so missing triggers cap
        assert result["grade"] in ("D", "F")

    def test_low_label_accuracy_cap(self, tmp_path: Path) -> None:
        """label_accuracy below 70% -> max grade C."""
        config = _v2_config()
        scores: dict[str, float | None] = {
            "field_coverage": 95.0,
            "field_validity": 95.0,
            "doc_completeness": 90.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 90.0,
            "label_accuracy": 60.0,
            "confidence_quality": 90.0,
        }
        result = compute_overall(scores, config)
        grade_order = ["A", "B", "C", "D", "F"]
        assert grade_order.index(result["grade"]) >= grade_order.index("C")

    def test_content_flag_fp_critical_cap(self, tmp_path: Path) -> None:
        """Content flag FP >80% -> grade capped at D."""
        config = _v2_config()
        vlm = _make_vlm_json(
            tmp_path,
            {
                "passing_sample_accuracy": 0.95,
                "content_flag_analysis": {
                    "has_table": {"false_positive_rate": 0.90},
                },
            },
        )
        scores: dict[str, float | None] = {
            "field_coverage": 95.0,
            "field_validity": 95.0,
            "doc_completeness": 90.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 90.0,
            "label_accuracy": 95.0,
            "confidence_quality": 90.0,
        }
        result = compute_overall(scores, config, vlm_path=vlm)
        grade_order = ["A", "B", "C", "D", "F"]
        assert grade_order.index(result["grade"]) >= grade_order.index("D")

    def test_low_confidence_quality_cap(self, tmp_path: Path) -> None:
        """confidence_quality < 60% -> max grade B."""
        config = _v2_config()
        scores: dict[str, float | None] = {
            "field_coverage": 95.0,
            "field_validity": 95.0,
            "doc_completeness": 90.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 90.0,
            "label_accuracy": 95.0,
            "confidence_quality": 50.0,
        }
        result = compute_overall(scores, config)
        # Score would be ~93+ (all high), but confidence cap at B
        if result["overall_score"] >= 93.0:
            assert result["grade"] != "A"

    def test_low_core_prescreening_cap(self, tmp_path: Path) -> None:
        """Core prescreening < 70% -> max grade C."""
        config = _v2_config()
        screening = _make_screening_json(
            tmp_path,
            {},
            core_pass_rate_pct=60.0,
            extended_pass_rate_pct=80.0,
        )
        scores: dict[str, float | None] = {
            "field_coverage": 95.0,
            "field_validity": 95.0,
            "doc_completeness": 90.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 90.0,
            "label_accuracy": 95.0,
            "confidence_quality": 90.0,
        }
        result = compute_overall(scores, config, screening_path=screening)
        grade_order = ["A", "B", "C", "D", "F"]
        assert grade_order.index(result["grade"]) >= grade_order.index("C")

    def test_caps_only_downgrade_never_upgrade(self) -> None:
        """Grade caps can only lower grades, never raise them."""
        grade, msg = _apply_grade_cap("F", "B", "reason", None)
        assert grade == "F"
        assert msg is None


# ===================================================================
# 6. Content flag FP rate loader  (~2 tests)
# ===================================================================


class TestContentFlagFPRates:
    """Tests for _load_content_flag_fp_rates."""

    def test_loads_fp_rates(self, tmp_path: Path) -> None:
        vlm = _make_vlm_json(
            tmp_path,
            {
                "content_flag_analysis": {
                    "has_table": {"false_positive_rate": 0.50},
                    "has_figure": {"false_positive_rate": 0.20},
                },
            },
        )
        rates = _load_content_flag_fp_rates(vlm)
        assert rates is not None
        assert abs(rates["has_table"] - 50.0) < 0.1
        assert abs(rates["has_figure"] - 20.0) < 0.1

    def test_loads_from_track_a(self, tmp_path: Path) -> None:
        vlm = _make_vlm_json(
            tmp_path,
            {
                "track_a_analysis": {
                    "content_flag_analysis": {
                        "has_handwriting": {"false_positive_rate": 1.0},
                    },
                },
            },
        )
        rates = _load_content_flag_fp_rates(vlm)
        assert rates is not None
        assert abs(rates["has_handwriting"] - 100.0) < 0.1

    def test_loads_from_validation_summary(self, tmp_path: Path) -> None:
        """FP rates loaded from validation_summary.content_flag_analysis."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "validation_summary": {
                    "content_flag_analysis": {
                        "has_table": {
                            "total_flagged": 20,
                            "true_positive": 15,
                            "false_positive": 5,
                            "fp_rate_pct": 25.0,
                        },
                    },
                },
            },
        )
        rates = _load_content_flag_fp_rates(vlm)
        assert rates is not None
        assert abs(rates["has_table"] - 25.0) < 0.1

    def test_loads_fp_rate_pct_format(self, tmp_path: Path) -> None:
        """FP rates loaded using fp_rate_pct key (already 0-100)."""
        vlm = _make_vlm_json(
            tmp_path,
            {
                "content_flag_analysis": {
                    "has_figure": {"fp_rate_pct": 33.5},
                },
            },
        )
        rates = _load_content_flag_fp_rates(vlm)
        assert rates is not None
        assert abs(rates["has_figure"] - 33.5) < 0.1

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        rates = _load_content_flag_fp_rates(tmp_path / "nonexistent.json")
        assert rates is None


# ===================================================================
# 7. Integration / backward compatibility  (~3 tests)
# ===================================================================


class TestIntegrationBackwardCompat:
    """Integration and backward compatibility tests."""

    def test_v1_artifacts_compute_with_redistribution(self, tmp_path: Path) -> None:
        """v1.1 artifacts (no label_accuracy/confidence_quality) redistribute weight."""
        config = _v2_config()
        scores: dict[str, float | None] = {
            "field_coverage": 90.0,
            "field_validity": 85.0,
            "doc_completeness": 80.0,
            "defect_rate": 100.0,
            "cross_source_agreement": 75.0,
            "label_accuracy": None,
            "confidence_quality": None,
        }
        result = compute_overall(scores, config)
        # Should compute with redistributed weights
        assert result["overall_score"] > 0
        assert "label_accuracy" in result["excluded_dimensions"]
        assert "confidence_quality" in result["excluded_dimensions"]
        # Effective weights should sum to ~1.0
        total_eff = sum(result["effective_weights"].values())
        assert abs(total_eff - 1.0) < 0.01

    def test_scorecard_config_version(self) -> None:
        """Config returns version 2.0.0."""
        config = _v2_config()
        assert config["version"] == "2.0.0"

    def test_grade_thresholds_tightened(self) -> None:
        """v2.0 grade thresholds are stricter than v1.1."""
        config = _v2_config()
        thresholds = config["grade_thresholds"]
        assert thresholds["A"] == 93
        assert thresholds["B"] == 85
        assert thresholds["C"] == 75
        assert thresholds["D"] == 65

    def test_no_dimensions_returns_f(self) -> None:
        """All dimensions None returns grade F."""
        config = _v2_config()
        scores: dict[str, float | None] = {
            "field_coverage": None,
            "field_validity": None,
            "doc_completeness": None,
            "defect_rate": None,
            "cross_source_agreement": None,
            "label_accuracy": None,
            "confidence_quality": None,
        }
        result = compute_overall(scores, config)
        assert result["grade"] == "F"
        assert result["overall_score"] == 0.0


# ===================================================================
# 8. Run prescreening integration  (~2 tests)
# ===================================================================


class TestRunPrescreeningIntegration:
    """Tests for run_prescreening with expanded validators."""

    def test_output_includes_core_extended_rates(self, tmp_path: Path) -> None:
        """run_prescreening output has core/extended pass rate fields."""
        metadata = {
            "samples": [
                {
                    "id": "img001",
                    "source": {"original_path": "test/img001.jpg"},
                    "enrichments": {
                        "current_version": 1,
                        "versions": [
                            {
                                "version": 1,
                                "data": {
                                    "split": "train",
                                    "capture_method": "born_digital",
                                    "domain_level1": "SCI",
                                    "iso639_language": "en",
                                    "script_family": "latin",
                                    "layout_detections": [
                                        {
                                            "class_name": "text",
                                            "confidence": 0.9,
                                            "bbox": [0, 0, 100, 50],
                                        },
                                    ],
                                    "has_table": False,
                                    "has_formula": False,
                                    "has_handwriting": False,
                                    "has_figure": False,
                                    "has_code": False,
                                    "has_signature": False,
                                    "text_statistics": {"has_content": True},
                                    "orientation_class": 0,
                                    "image_properties_color_mode": "color",
                                    "handwriting_present": False,
                                    "method": "tier_2_model",
                                    "iso15924_script_code": "Latn",
                                    "resolution_category": "standard_300",
                                    "capture_confidence": 0.8,
                                    "domain_confidence": 0.7,
                                    "language_confidence": 0.9,
                                    "sample_reliability_summary": {
                                        "min_confidence_category": "hard_label",
                                        "assessed_field_count": 5,
                                        "min_confidence": 0.7,
                                        "hard_field_count": 4,
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        }
        meta_path = tmp_path / "test_metadata.json"
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = run_prescreening(meta_path, dataset_name="test")
        assert "core_pass_rate_pct" in result
        assert "extended_pass_rate_pct" in result
        assert "core_field_count" in result
        assert "extended_field_count" in result
        assert result["core_field_count"] > 0
        assert result["extended_field_count"] > 0
        assert result["total_samples"] == 1

    def test_45_fields_in_per_field_results(self, tmp_path: Path) -> None:
        """Per-field results include all 45 fields."""
        metadata = {
            "samples": [
                {
                    "id": "img001",
                    "source": {"original_path": "test/img001.jpg"},
                    "enrichments": {
                        "current_version": 1,
                        "versions": [{"version": 1, "data": {}}],
                    },
                },
            ],
        }
        meta_path = tmp_path / "test_metadata.json"
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = run_prescreening(meta_path, dataset_name="test")
        per_field = result["per_field_results"]
        assert len(per_field) == len(ALL_FIELD_NAMES)
        for field_name in ALL_FIELD_NAMES:
            assert field_name in per_field, f"Missing field: {field_name}"
