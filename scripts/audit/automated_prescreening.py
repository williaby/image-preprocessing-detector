#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Automated pre-screening validator for Layer 2 metadata samples.

Validates ALL samples in a dataset's metadata against schema compliance
rules that go beyond structural JSON Schema validation.  These rules check
**semantic readiness** for downstream training pipelines: splits are
assigned, capture methods are recognized, languages are identified, layout
detections are present and well-formed, content flags are boolean, etc.

The script reads the *latest* enrichment version for each sample
(``enrichments.current_version`` selects from ``enrichments.versions[]``)
and applies 14 field-level validation rules.

CLI usage::

    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/audit/automated_prescreening.py --dataset diqa-5000

    # Dry run (count only, no file output)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/audit/automated_prescreening.py --dataset diqa-5000 --dry-run

    # All datasets at once
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/audit/automated_prescreening.py --all-datasets
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

METADATA_REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry/json")


def _metadata_path_for(dataset: str) -> Path:
    """Derive metadata JSON path from dataset name.

    Consults the audit_config registry first for the correct path,
    falling back to simple ``{dataset}_metadata.json`` derivation.
    """
    try:
        from scripts.audit.audit_config import load_dataset_config

        cfg = load_dataset_config(dataset)
        if cfg.metadata_json_path is not None:
            return cfg.metadata_json_path
    except (ImportError, ValueError):
        pass
    return METADATA_REGISTRY_DIR / f"{dataset}_metadata.json"


def _output_path_for(dataset: str) -> Path:
    """Derive output report path from dataset name."""
    return (
        PROJECT_ROOT
        / "scripts"
        / "audit"
        / "results"
        / dataset
        / "automated_screening.json"
    )


VALID_CAPTURE_METHODS = frozenset(
    {
        "camera_smartphone",
        "synthetic",
        "scanner",
        "scanner_flatbed",
        "scanner_adf",
        "born_digital",
        "screen_capture",
        "unknown",
    }
)

VALID_SCRIPT_FAMILIES = frozenset(
    {
        "latin",
        "cjk",
        "arabic",
        "indic",
        "cyrillic",
        "greek",
        "hebrew",
        "ethiopic",
        "georgian",
        "armenian",
        "other",
    }
)

VALID_ORIENTATION_CLASSES = frozenset({0, 90, 180, 270})

VALID_PROVENANCE_TIERS = frozenset(
    {
        "tier_0_exact",
        "tier_1_annotation",
        "tier_2_model",
        "tier_3_heuristic",
    }
)

VALID_RELIABILITY_CATEGORIES = frozenset(
    {
        "hard_label",
        "soft_label",
        "active_learning",
        "unreliable",
        "unassessed",
    }
)

VALID_SCRIPT_CODES = frozenset(
    {
        "Latn", "Hans", "Hant", "Jpan", "Kore", "Hani",
        "Deva", "Beng", "Taml", "Telu", "Gujr", "Knda",
        "Mlym", "Orya", "Sinh", "Guru",
        "Thai", "Khmr", "Mymr", "Laoo", "Tibt",
        "Arab", "Hebr",
        "Cyrl", "Grek", "Armn", "Geor",
        "Ethi", "Hang", "Hira", "Kana",
        "Zyyy", "Zinh", "Zzzz",
    }
)

VALID_RESOLUTION_CATEGORIES = frozenset(
    {
        "low_<150",
        "medium_150-299",
        "standard_300",
        "high_>300",
    }
)

VALID_LAYOUT_TYPES = frozenset(
    {
        "single_column",
        "multi_column",
        "three_column",
        "complex",
        "form_based",
        "tabular",
        "unknown",
    }
)

VALID_TEXT_DENSITIES = frozenset({"sparse", "moderate", "dense"})


# ---------------------------------------------------------------------------
# Enrichment data extraction
# ---------------------------------------------------------------------------
def _get_current_enrichment_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Extract the enrichment data dict for the current version.

    Uses ``enrichments.current_version`` to look up the correct entry
    in ``enrichments.versions[]``.  Falls back to the last entry if
    no exact version match is found.

    Args:
        sample: A single sample dictionary from the metadata file.

    Returns:
        The ``data`` dict from the matching enrichment version, or an
        empty dict if no enrichment data is available.
    """
    enrichments = sample.get("enrichments", {})
    current_version = enrichments.get("current_version")
    versions = enrichments.get("versions", [])

    if not versions:
        return {}

    # Look for the exact version match.
    if current_version is not None:
        for entry in versions:
            if entry.get("version") == current_version:
                return entry.get("data", {})

    # Fallback: use the last version in the list.
    return versions[-1].get("data", {})


# ---------------------------------------------------------------------------
# Individual field validators
# ---------------------------------------------------------------------------
# Each validator returns (is_pass: bool, detail: str | None).
# A None detail means no extra info is needed for the pass case.


def _check_split(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check that split is not 'unknown'."""
    val = data.get("split")
    if val is None:
        return False, "split is missing"
    if val == "unknown":
        return False, "split is 'unknown'"
    return True, None


def _check_capture_method(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check capture_method is a recognized enum value."""
    val = data.get("capture_method")
    if val is None:
        return False, "capture_method is missing"
    if val not in VALID_CAPTURE_METHODS:
        return False, f"capture_method='{val}' not in allowed set"
    return True, None


def _check_domain_level1(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check domain_level1 is not 'UNK'."""
    val = data.get("domain_level1")
    if val is None:
        return False, "domain_level1 is missing"
    if val == "UNK":
        return False, "domain_level1 is 'UNK'"
    return True, None


def _check_iso639_language(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check iso639_language is not 'und' and not null."""
    val = data.get("iso639_language")
    if val is None:
        return False, "iso639_language is null/missing"
    if val == "und":
        return False, "iso639_language is 'und' (undetermined)"
    return True, None


def _check_script_family(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check script_family is one of the recognized families."""
    val = data.get("script_family")
    if val is None:
        return False, "script_family is missing"
    if val not in VALID_SCRIPT_FAMILIES:
        return False, f"script_family='{val}' not in allowed set"
    return True, None


def _check_layout_detections_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check layout_detections is a list with >= 1 element."""
    val = data.get("layout_detections")
    if val is None:
        return False, "layout_detections is missing"
    if not isinstance(val, list):
        return False, f"layout_detections is not a list (type={type(val).__name__})"
    if len(val) < 1:
        return False, "layout_detections is empty"
    return True, None


def _check_layout_bbox_valid(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check all bbox values in layout_detections are [x, y, w, h] with w>0, h>0."""
    detections = data.get("layout_detections")
    if not isinstance(detections, list) or len(detections) == 0:
        # Already caught by _check_layout_detections_present; skip here.
        return True, None

    bad_indices: list[str] = []
    for idx, det in enumerate(detections):
        if not isinstance(det, dict):
            bad_indices.append(f"[{idx}]: not a dict")
            continue
        bbox = det.get("bbox")
        if bbox is None:
            bad_indices.append(f"[{idx}]: bbox missing")
            continue
        if not isinstance(bbox, list) or len(bbox) != 4:
            bad_indices.append(f"[{idx}]: bbox not [x,y,w,h]")
            continue
        # All elements must be numeric.
        if not all(isinstance(v, (int, float)) for v in bbox):
            bad_indices.append(f"[{idx}]: bbox has non-numeric values")
            continue
        # w (index 2) and h (index 3) must be > 0.
        if bbox[2] <= 0 or bbox[3] <= 0:
            bad_indices.append(f"[{idx}]: w={bbox[2]}, h={bbox[3]} (must be >0)")

    if bad_indices:
        summary = "; ".join(bad_indices[:5])
        if len(bad_indices) > 5:
            summary += f" ...and {len(bad_indices) - 5} more"
        return False, f"{len(bad_indices)} bad bbox(es): {summary}"
    return True, None


def _check_content_flags_boolean(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check content flags (has_table, has_formula, etc.) are boolean."""
    flag_names = [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_figure",
        "has_code",
    ]
    bad_flags: list[str] = []
    for name in flag_names:
        val = data.get(name)
        if val is not None and not isinstance(val, bool):
            bad_flags.append(f"{name}={val!r} (type={type(val).__name__})")

    if bad_flags:
        return False, f"non-boolean content flags: {', '.join(bad_flags)}"
    return True, None


def _check_text_has_content(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check text_statistics.has_content is true (text_content is not empty)."""
    stats = data.get("text_statistics")
    if stats is None:
        return False, "text_statistics is missing"
    if not isinstance(stats, dict):
        return False, f"text_statistics is not a dict (type={type(stats).__name__})"
    has_content = stats.get("has_content")
    if has_content is None:
        return False, "text_statistics.has_content is missing"
    if has_content is not True:
        return False, f"text_statistics.has_content={has_content!r}"
    return True, None


def _check_orientation_class(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check orientation_class is in [0, 90, 180, 270]."""
    val = data.get("orientation_class")
    if val is None:
        return False, "orientation_class is missing"
    if val not in VALID_ORIENTATION_CLASSES:
        return False, f"orientation_class={val} not in {{0, 90, 180, 270}}"
    return True, None


def _check_quality_overall_mos(
    data: dict[str, Any],
    original_path: str,
) -> tuple[bool, str | None]:
    """Check quality_overall_mos exists for /res/ images.

    Only applies when original_path contains '/res/'.  For non-res
    images this check auto-passes.

    Args:
        data: Enrichment data dict.
        original_path: The sample's original file path.

    Returns:
        Tuple of (pass, detail).
    """
    if "/res/" not in original_path:
        return True, None

    val = data.get("quality_overall_mos")
    if val is None:
        return False, "quality_overall_mos missing for /res/ image"
    if not isinstance(val, (int, float)):
        return False, f"quality_overall_mos is not numeric (type={type(val).__name__})"
    return True, None


def _check_image_properties_color_mode(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check image_properties_color_mode is set."""
    val = data.get("image_properties_color_mode")
    if val is None:
        return False, "image_properties_color_mode is missing"
    if not isinstance(val, str) or val.strip() == "":
        return False, f"image_properties_color_mode is empty or not a string: {val!r}"
    return True, None


def _check_handwriting_present(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check handwriting_present is boolean."""
    val = data.get("handwriting_present")
    if val is None:
        return False, "handwriting_present is missing"
    if not isinstance(val, bool):
        return False, f"handwriting_present={val!r} (type={type(val).__name__})"
    return True, None


# v2.3.0 optional field validators
VALID_TEXT_DIRECTIONS = frozenset({"ltr", "rtl", "ttb"})


def _check_text_direction(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check text_direction is a valid enum if populated (v2.3.0).

    This is an optional field - returns pass if not populated.
    Only fails if populated with an invalid value.
    """
    val = data.get("text_direction")
    if val is None:
        return True, None
    if val not in VALID_TEXT_DIRECTIONS:
        return False, f"text_direction='{val}' not in {{ltr, rtl, ttb}}"
    return True, None


def _check_text_directions_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check text_directions_present items are valid enums if populated (v2.3.0).

    This is an optional field - returns pass if not populated.
    Only fails if populated with invalid values.
    """
    val = data.get("text_directions_present")
    if val is None:
        return True, None
    if not isinstance(val, list):
        return (
            False,
            f"text_directions_present is not a list (type={type(val).__name__})",
        )
    invalid = [v for v in val if v not in VALID_TEXT_DIRECTIONS]
    if invalid:
        return False, f"text_directions_present has invalid values: {invalid}"
    return True, None


# ---------------------------------------------------------------------------
# Group A: Sample Reliability & Confidence (8 new validators)
# ---------------------------------------------------------------------------
def _check_reliability_summary_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check sample_reliability_summary object exists (Core)."""
    val = data.get("sample_reliability_summary")
    if val is None or not isinstance(val, dict):
        return False, "sample_reliability_summary is missing"
    return True, None


def _check_reliability_min_confidence_category(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check min_confidence_category is a valid enum (Core)."""
    summary = data.get("sample_reliability_summary")
    if not isinstance(summary, dict):
        return False, "sample_reliability_summary is missing"
    val = summary.get("min_confidence_category")
    if val is None:
        return False, "min_confidence_category is missing"
    if val not in VALID_RELIABILITY_CATEGORIES:
        return False, f"min_confidence_category='{val}' not in allowed set"
    return True, None


def _check_reliability_assessed_count(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check assessed_field_count >= 3 (Core)."""
    summary = data.get("sample_reliability_summary")
    if not isinstance(summary, dict):
        return False, "sample_reliability_summary is missing"
    val = summary.get("assessed_field_count")
    if val is None:
        return False, "assessed_field_count is missing"
    if not isinstance(val, int) or val < 3:
        return False, f"assessed_field_count={val} (min 3)"
    return True, None


def _check_reliability_min_confidence(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check min_confidence >= 0.5 (Extended, pass-if-absent)."""
    summary = data.get("sample_reliability_summary")
    if not isinstance(summary, dict):
        return True, None
    val = summary.get("min_confidence")
    if val is None:
        return True, None
    if not isinstance(val, (int, float)) or val < 0.5:
        return False, f"min_confidence={val} (min 0.5)"
    return True, None


def _check_reliability_hard_label_ratio(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check hard_field_count / assessed_field_count >= 0.3 (Extended, pass-if-absent)."""
    summary = data.get("sample_reliability_summary")
    if not isinstance(summary, dict):
        return True, None
    hard = summary.get("hard_field_count")
    assessed = summary.get("assessed_field_count")
    if hard is None or assessed is None or assessed == 0:
        return True, None
    ratio = hard / assessed
    if ratio < 0.3:
        return False, f"hard_label_ratio={ratio:.2f} ({hard}/{assessed}, min 0.3)"
    return True, None


def _check_capture_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check capture_method confidence >= 0.5 (Core)."""
    capture = data.get("capture_method_info")
    if not isinstance(capture, dict):
        # Fall back to flat field
        conf = data.get("capture_confidence")
        if conf is None:
            return False, "capture confidence is missing"
        if not isinstance(conf, (int, float)) or conf < 0.5:
            return False, f"capture_confidence={conf} (min 0.5)"
        return True, None
    conf = capture.get("confidence")
    if conf is None:
        return False, "capture_method_info.confidence is missing"
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"capture_method_info.confidence={conf} (min 0.5)"
    return True, None


def _check_domain_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check domain confidence >= 0.5 (Core)."""
    domain = data.get("domain_info")
    if not isinstance(domain, dict):
        conf = data.get("domain_confidence")
        if conf is None:
            return False, "domain confidence is missing"
        if not isinstance(conf, (int, float)) or conf < 0.5:
            return False, f"domain_confidence={conf} (min 0.5)"
        return True, None
    conf = domain.get("confidence")
    if conf is None:
        return False, "domain_info.confidence is missing"
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"domain_info.confidence={conf} (min 0.5)"
    return True, None


def _check_language_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check language confidence >= 0.5 (Core)."""
    lang = data.get("language_info")
    if not isinstance(lang, dict):
        conf = data.get("language_confidence")
        if conf is None:
            return False, "language confidence is missing"
        if not isinstance(conf, (int, float)) or conf < 0.5:
            return False, f"language_confidence={conf} (min 0.5)"
        return True, None
    conf = lang.get("confidence")
    if conf is None:
        return False, "language_info.confidence is missing"
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"language_info.confidence={conf} (min 0.5)"
    return True, None


# ---------------------------------------------------------------------------
# Group B: Language & Script Completeness (3 new validators)
# ---------------------------------------------------------------------------
def _check_language_script_code_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check script_code is a valid ISO 15924 enum (Core)."""
    val = data.get("iso15924_script_code")
    if val is None:
        lang = data.get("language_info")
        if isinstance(lang, dict):
            val = lang.get("script_code")
    if val is None:
        return False, "script_code is missing"
    if val not in VALID_SCRIPT_CODES:
        return False, f"script_code='{val}' not in ISO 15924 set"
    return True, None


def _check_language_bcp47_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check bcp47_tag is present (Extended, pass-if-absent)."""
    lang = data.get("language_info")
    if not isinstance(lang, dict):
        return True, None
    val = lang.get("bcp47_tag")
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return False, "bcp47_tag is missing or empty"
    return True, None


def _check_language_detection_method_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check detection_method is present (Extended, pass-if-absent)."""
    lang = data.get("language_info")
    if not isinstance(lang, dict):
        return True, None
    val = lang.get("detection_method")
    if val is None:
        return False, "language detection_method is missing"
    return True, None


# ---------------------------------------------------------------------------
# Group C: Geometric Properties (4 new validators)
# ---------------------------------------------------------------------------
def _check_geometric_present(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check geometric object exists (Extended, pass-if-absent)."""
    val = data.get("geometric")
    if val is None or not isinstance(val, dict):
        # Extended: pass if completely absent
        return True, None
    # Present but empty is also fine -- just checks existence
    return True, None


def _check_skew_angle_present(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check skew_angle_degrees is present (Extended, pass-if-absent)."""
    geo = data.get("geometric")
    if not isinstance(geo, dict):
        return True, None
    val = geo.get("skew_angle_degrees")
    if val is None:
        return False, "geometric.skew_angle_degrees is missing"
    return True, None


def _check_skew_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check skew_confidence >= 0.5 if skew present (Extended, pass-if-absent)."""
    geo = data.get("geometric")
    if not isinstance(geo, dict):
        return True, None
    if geo.get("skew_angle_degrees") is None:
        return True, None
    conf = geo.get("skew_confidence")
    if conf is None:
        return False, "skew_confidence is missing (skew_angle present)"
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"skew_confidence={conf} (min 0.5)"
    return True, None


def _check_orientation_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check orientation_confidence >= 0.5 if orientation present (Extended)."""
    geo = data.get("geometric")
    if not isinstance(geo, dict):
        return True, None
    if geo.get("orientation_class") is None:
        return True, None
    conf = geo.get("orientation_confidence")
    if conf is None:
        return False, "orientation_confidence missing (orientation present)"
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"orientation_confidence={conf} (min 0.5)"
    return True, None


# ---------------------------------------------------------------------------
# Group D: Resolution & Character Height (4 new validators)
# ---------------------------------------------------------------------------
def _check_resolution_dpi_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check resolution.dpi is present (Extended, pass-if-absent)."""
    res = data.get("resolution_info")
    if not isinstance(res, dict):
        # Fall back to flat field
        val = data.get("resolution_dpi")
        if val is None:
            return True, None
        return True, None
    val = res.get("dpi")
    if val is None:
        return False, "resolution_info.dpi is missing"
    return True, None


def _check_resolution_category_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check resolution.category is valid enum (Core, pass if no resolution)."""
    res = data.get("resolution_info")
    if not isinstance(res, dict):
        val = data.get("resolution_category")
        if val is None:
            return False, "resolution_category is missing"
        if val not in VALID_RESOLUTION_CATEGORIES:
            return False, f"resolution_category='{val}' not in allowed set"
        return True, None
    val = res.get("category")
    if val is None:
        return False, "resolution_info.category is missing"
    if val not in VALID_RESOLUTION_CATEGORIES:
        return False, f"resolution_info.category='{val}' not in allowed set"
    return True, None


def _check_resolution_quality_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check resolution_quality_score is present (Extended, pass-if-absent)."""
    res = data.get("resolution_info")
    if not isinstance(res, dict):
        return True, None
    val = res.get("resolution_quality_score")
    if val is None:
        return True, None  # Extended: pass if absent
    return True, None


def _check_character_height_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check character_height_px is present and > 0 (Extended, pass-if-absent)."""
    res = data.get("resolution_info")
    if not isinstance(res, dict):
        return True, None
    val = res.get("character_height_px")
    if val is None:
        return True, None  # Extended: pass if absent
    if not isinstance(val, (int, float)) or val <= 0:
        return False, f"character_height_px={val} (must be > 0)"
    return True, None


# ---------------------------------------------------------------------------
# Group E: Content Flags Expanded (3 new validators)
# ---------------------------------------------------------------------------
def _check_content_flag_confidence_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check content_flags_confidence is present (Extended, pass-if-absent)."""
    val = data.get("content_flags_confidence")
    if val is not None:
        return True, None
    # Check nested structure
    flags = data.get("content_flags")
    if isinstance(flags, dict) and flags.get("confidence") is not None:
        return True, None
    return True, None  # Extended: pass if absent


def _check_has_code_present(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Check has_code field exists (Extended, pass-if-absent)."""
    if "has_code" in data:
        return True, None
    flags = data.get("content_flags")
    if isinstance(flags, dict) and "has_code" in flags:
        return True, None
    return False, "has_code field not present (v2.1.0+ completeness)"


def _check_has_signature_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check has_signature field exists (Extended, pass-if-absent)."""
    if "has_signature" in data:
        return True, None
    flags = data.get("content_flags")
    if isinstance(flags, dict) and "has_signature" in flags:
        return True, None
    return False, "has_signature field not present"


# ---------------------------------------------------------------------------
# Group F: Handwriting Assessment (2 new validators)
# ---------------------------------------------------------------------------
def _check_handwriting_assessment_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check handwriting_assessment object exists (Extended, pass-if-absent)."""
    val = data.get("handwriting_assessment")
    if not isinstance(val, dict):
        return True, None  # Extended: pass if absent
    # Present: verify it has the presence field
    if val.get("presence") is None:
        return False, "handwriting_assessment exists but missing presence field"
    return True, None


def _check_handwriting_confidence_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check handwriting confidence >= 0.5 (Extended, pass-if-absent)."""
    hw = data.get("handwriting_assessment")
    if not isinstance(hw, dict):
        return True, None
    conf = hw.get("confidence")
    if conf is None:
        return True, None  # Extended: pass if absent
    if not isinstance(conf, (int, float)) or conf < 0.5:
        return False, f"handwriting confidence={conf} (min 0.5)"
    return True, None


# ---------------------------------------------------------------------------
# Group G: Structure & Layout Quality (3 new validators)
# ---------------------------------------------------------------------------
def _check_structure_layout_type_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check layout_type is valid enum if present (Extended, pass-if-absent)."""
    struct = data.get("structure_info")
    if not isinstance(struct, dict):
        return True, None
    val = struct.get("layout_type")
    if val is None:
        return True, None
    if val not in VALID_LAYOUT_TYPES:
        return False, f"layout_type='{val}' not in allowed set"
    return True, None


def _check_structure_text_density_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check text_density is valid enum if present (Extended, pass-if-absent)."""
    struct = data.get("structure_info")
    if not isinstance(struct, dict):
        return True, None
    val = struct.get("text_density")
    if val is None:
        return True, None
    if val not in VALID_TEXT_DENSITIES:
        return False, f"text_density='{val}' not in allowed set"
    return True, None


def _check_structure_confidence_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check structure confidence is present (Extended, pass-if-absent)."""
    struct = data.get("structure_info")
    if not isinstance(struct, dict):
        return True, None
    conf = struct.get("confidence")
    if conf is None:
        return False, "structure_info.confidence is missing"
    return True, None


# ---------------------------------------------------------------------------
# Group H: Image Properties & Physical Degradation (2 new validators)
# ---------------------------------------------------------------------------
def _check_image_properties_document_age(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check document_age is present (Extended, pass-if-absent)."""
    props = data.get("image_properties")
    if not isinstance(props, dict):
        return True, None
    val = props.get("document_age")
    if val is None:
        return True, None  # Extended: pass if absent
    valid_ages = {"modern", "aged", "historical"}
    if val not in valid_ages:
        return False, f"document_age='{val}' not in {{modern, aged, historical}}"
    return True, None


def _check_physical_degradation_present(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check physical_degradation object exists (Extended, pass-if-absent)."""
    val = data.get("physical_degradation")
    if val is None or not isinstance(val, dict):
        return True, None  # Extended: pass if absent
    return True, None


# ---------------------------------------------------------------------------
# Group I: Provenance & Audit Trail (1 new validator)
# ---------------------------------------------------------------------------
def _check_provenance_tier_valid(
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Check root provenance_tier is valid (Core)."""
    val = data.get("method")
    if val is None:
        val = data.get("provenance_tier")
    if val is None:
        return False, "provenance_tier (root method) is missing"
    if val not in VALID_PROVENANCE_TIERS:
        return False, f"provenance_tier='{val}' not in allowed set"
    return True, None


# ---------------------------------------------------------------------------
# Validator registry
# ---------------------------------------------------------------------------
# Each entry is (field_name, validator_func).
# Validators that need extra context (e.g. original_path) are handled
# separately in _validate_sample.
#
# Core validators penalize absence/invalidity (training readiness).
# Extended validators validate-if-populated but pass if absent (quality bonus).

_CORE_VALIDATORS: list[tuple[str, Any]] = [
    # --- Existing core validators ---
    ("split", _check_split),
    ("capture_method", _check_capture_method),
    ("domain_level1", _check_domain_level1),
    ("iso639_language", _check_iso639_language),
    ("script_family", _check_script_family),
    ("layout_detections", _check_layout_detections_present),
    ("layout_bbox_valid", _check_layout_bbox_valid),
    ("content_flags_boolean", _check_content_flags_boolean),
    ("text_has_content", _check_text_has_content),
    ("orientation_class", _check_orientation_class),
    ("image_properties_color_mode", _check_image_properties_color_mode),
    ("handwriting_present", _check_handwriting_present),
    # v2.3.0 optional fields (pass if not populated, fail only on invalid values)
    ("text_direction", _check_text_direction),
    ("text_directions_present", _check_text_directions_present),
    # --- New core validators (v2.0) ---
    # Group A: Reliability & Confidence
    ("reliability_summary_present", _check_reliability_summary_present),
    ("reliability_min_confidence_category", _check_reliability_min_confidence_category),
    ("reliability_assessed_count", _check_reliability_assessed_count),
    ("capture_confidence_valid", _check_capture_confidence_valid),
    ("domain_confidence_valid", _check_domain_confidence_valid),
    ("language_confidence_valid", _check_language_confidence_valid),
    # Group B: Language & Script
    ("language_script_code_valid", _check_language_script_code_valid),
    # Group D: Resolution
    ("resolution_category_valid", _check_resolution_category_valid),
    # Group I: Provenance
    ("provenance_tier_valid", _check_provenance_tier_valid),
]

_EXTENDED_VALIDATORS: list[tuple[str, Any]] = [
    # Group A: Reliability (pass-if-absent)
    ("reliability_min_confidence", _check_reliability_min_confidence),
    ("reliability_hard_label_ratio", _check_reliability_hard_label_ratio),
    # Group B: Language (pass-if-absent)
    ("language_bcp47_present", _check_language_bcp47_present),
    ("language_detection_method_present", _check_language_detection_method_present),
    # Group C: Geometric (pass-if-absent)
    ("geometric_present", _check_geometric_present),
    ("skew_angle_present", _check_skew_angle_present),
    ("skew_confidence_valid", _check_skew_confidence_valid),
    ("orientation_confidence_valid", _check_orientation_confidence_valid),
    # Group D: Resolution (pass-if-absent)
    ("resolution_dpi_present", _check_resolution_dpi_present),
    ("resolution_quality_present", _check_resolution_quality_present),
    ("character_height_present", _check_character_height_present),
    # Group E: Content flags (pass-if-absent)
    ("content_flag_confidence_present", _check_content_flag_confidence_present),
    ("has_code_present", _check_has_code_present),
    ("has_signature_present", _check_has_signature_present),
    # Group F: Handwriting (pass-if-absent)
    ("handwriting_assessment_present", _check_handwriting_assessment_present),
    ("handwriting_confidence_valid", _check_handwriting_confidence_valid),
    # Group G: Structure (pass-if-absent)
    ("structure_layout_type_valid", _check_structure_layout_type_valid),
    ("structure_text_density_valid", _check_structure_text_density_valid),
    ("structure_confidence_present", _check_structure_confidence_present),
    # Group H: Image properties & degradation (pass-if-absent)
    ("image_properties_document_age", _check_image_properties_document_age),
    ("physical_degradation_present", _check_physical_degradation_present),
]

_SIMPLE_VALIDATORS = _CORE_VALIDATORS + _EXTENDED_VALIDATORS


# ---------------------------------------------------------------------------
# Sample-level validation
# ---------------------------------------------------------------------------
def _validate_sample(
    sample: dict[str, Any],
) -> tuple[list[str], dict[str, str]]:
    """Run all validation rules on a single sample.

    Args:
        sample: A single sample dictionary from the metadata file.

    Returns:
        Tuple of (failed_fields, details_dict) where details_dict maps
        each failed field name to a description string.
    """
    data = _get_current_enrichment_data(sample)
    original_path = sample.get("source", {}).get("original_path", "")

    failed_fields: list[str] = []
    details: dict[str, str] = {}

    # Run simple validators.
    for field_name, validator_fn in _SIMPLE_VALIDATORS:
        is_pass, detail = validator_fn(data)
        if not is_pass:
            failed_fields.append(field_name)
            if detail is not None:
                details[field_name] = detail

    # Run quality_overall_mos (needs original_path context).
    is_pass, detail = _check_quality_overall_mos(data, original_path)
    if not is_pass:
        failed_fields.append("quality_overall_mos")
        if detail is not None:
            details["quality_overall_mos"] = detail

    return failed_fields, details


# ---------------------------------------------------------------------------
# Field result tracking
# ---------------------------------------------------------------------------
CORE_FIELD_NAMES = [name for name, _ in _CORE_VALIDATORS] + ["quality_overall_mos"]
EXTENDED_FIELD_NAMES = [name for name, _ in _EXTENDED_VALIDATORS]
ALL_FIELD_NAMES = CORE_FIELD_NAMES + EXTENDED_FIELD_NAMES


def _build_empty_field_counters() -> dict[str, dict[str, int]]:
    """Create zeroed pass/fail counters for every field.

    Returns:
        Dict mapping field_name -> {"pass": 0, "fail": 0}.
    """
    return {name: {"pass": 0, "fail": 0} for name in ALL_FIELD_NAMES}


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------
def run_prescreening(
    metadata_path: Path,
    dataset_name: str = "unknown",
) -> dict[str, Any]:
    """Run the full pre-screening audit across all samples.

    Args:
        metadata_path: Path to the dataset metadata JSON file.
        dataset_name: Canonical dataset name for the report header.

    Returns:
        The complete result dictionary ready for JSON serialization.

    Raises:
        FileNotFoundError: If metadata_path does not exist.
        ValueError: If the metadata file cannot be parsed.
    """
    if not metadata_path.exists():
        msg = f"Metadata file not found: {metadata_path}"
        raise FileNotFoundError(msg)

    logger.info("Loading metadata from %s", metadata_path)
    with open(metadata_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    samples = meta.get("samples", [])
    total_samples = len(samples)
    logger.info("Loaded %d samples for pre-screening", total_samples)

    field_counters = _build_empty_field_counters()
    failing_samples: list[dict[str, Any]] = []
    passed_all_count = 0

    for sample in samples:
        image_id = sample.get("id", "unknown")
        failed_fields, details = _validate_sample(sample)

        # Update per-field counters.
        failed_set = set(failed_fields)
        for field_name in ALL_FIELD_NAMES:
            if field_name in failed_set:
                field_counters[field_name]["fail"] += 1
            else:
                field_counters[field_name]["pass"] += 1

        if failed_fields:
            failing_samples.append(
                {
                    "image_id": image_id,
                    "failed_fields": failed_fields,
                    "details": details,
                }
            )
        else:
            passed_all_count += 1

    # Build per-field results with fail_rate_pct.
    per_field_results: dict[str, dict[str, Any]] = {}
    for field_name in ALL_FIELD_NAMES:
        counters = field_counters[field_name]
        total_checked = counters["pass"] + counters["fail"]
        fail_rate = (
            round((counters["fail"] / total_checked) * 100, 2)
            if total_checked > 0
            else 0.0
        )
        per_field_results[field_name] = {
            "pass": counters["pass"],
            "fail": counters["fail"],
            "fail_rate_pct": fail_rate,
        }

    # Compute core/extended pass rates
    def _avg_pass_rate(field_names: list[str]) -> float:
        rates: list[float] = []
        for fname in field_names:
            info = per_field_results.get(fname)
            if info is None:
                continue
            total_checked = info["pass"] + info["fail"]
            if total_checked > 0:
                rates.append(info["pass"] / total_checked * 100)
        return round(sum(rates) / max(len(rates), 1), 2) if rates else 0.0

    core_pass_rate = _avg_pass_rate(CORE_FIELD_NAMES)
    extended_pass_rate = _avg_pass_rate(EXTENDED_FIELD_NAMES)

    result: dict[str, Any] = {
        "dataset": dataset_name,
        "metadata_path": str(metadata_path),
        "audited_at": datetime.now(UTC).isoformat(),
        "total_samples": total_samples,
        "passed_all": passed_all_count,
        "failed_any": total_samples - passed_all_count,
        "core_pass_rate_pct": core_pass_rate,
        "extended_pass_rate_pct": extended_pass_rate,
        "core_field_count": len(CORE_FIELD_NAMES),
        "extended_field_count": len(EXTENDED_FIELD_NAMES),
        "per_field_results": per_field_results,
        "failing_samples": failing_samples,
    }

    return result


# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------
def print_summary(result: dict[str, Any]) -> None:
    """Print a formatted summary table to stdout.

    Args:
        result: The audit result dictionary.
    """
    total = result["total_samples"]
    passed = result["passed_all"]
    failed = result["failed_any"]
    pass_rate = round((passed / total) * 100, 2) if total > 0 else 0.0

    print()
    dataset = result.get("dataset", "unknown")
    print("=" * 72)
    print(f"  {dataset.upper()} AUTOMATED PRE-SCREENING RESULTS")
    print("=" * 72)
    print(f"  Audited at:    {result['audited_at']}")
    print(f"  Metadata:      {result['metadata_path']}")
    print(f"  Total samples: {total}")
    print(f"  Passed all:    {passed} ({pass_rate}%)")
    print(f"  Failed any:    {failed} ({round(100.0 - pass_rate, 2)}%)")
    print()
    print(f"  {'Field':<35} {'Pass':>7} {'Fail':>7} {'Fail%':>8}")
    print(f"  {'-' * 35} {'-' * 7} {'-' * 7} {'-' * 8}")

    per_field = result["per_field_results"]
    for field_name in ALL_FIELD_NAMES:
        info = per_field[field_name]
        print(
            f"  {field_name:<35} {info['pass']:>7} {info['fail']:>7} "
            f"{info['fail_rate_pct']:>7.2f}%"
        )

    print()

    # Top failing fields (non-zero fail rate).
    failing_fields = [
        (name, per_field[name]["fail_rate_pct"])
        for name in ALL_FIELD_NAMES
        if per_field[name]["fail"] > 0
    ]
    failing_fields.sort(key=lambda x: x[1], reverse=True)

    if failing_fields:
        print("  Top failing fields:")
        for name, rate in failing_fields[:10]:
            print(f"    {name}: {rate:.2f}%")
    else:
        print("  All fields passed for every sample.")

    # Show core/extended pass rates if present
    core_rate = result.get("core_pass_rate_pct")
    ext_rate = result.get("extended_pass_rate_pct")
    if core_rate is not None:
        core_count = result.get("core_field_count", "?")
        ext_count = result.get("extended_field_count", "?")
        print(f"  Core pass rate ({core_count} fields):     {core_rate:.2f}%")
        print(f"  Extended pass rate ({ext_count} fields):  {ext_rate:.2f}%")

    print()
    print("=" * 72)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the pre-screening script.

    Returns:
        Configured argparse.ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Validate dataset metadata samples against schema compliance "
            "rules and produce a structured pre-screening report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Single dataset\n"
            "  uv run python3 scripts/audit/automated_prescreening.py --dataset diqa-5000\n\n"
            "  # All datasets in metadata registry\n"
            "  uv run python3 scripts/audit/automated_prescreening.py --all-datasets\n\n"
            "  # Custom paths\n"
            "  uv run python3 scripts/audit/automated_prescreening.py \\\n"
            "      --dataset ohr-bench --metadata-path /path/to/metadata.json\n"
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dataset",
        type=str,
        help="Canonical dataset name (e.g., diqa-5000, ohr-bench).",
    )
    group.add_argument(
        "--all-datasets",
        action="store_true",
        help="Run prescreening on ALL datasets in metadata registry.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=None,
        help=("Override the metadata JSON path. Default: auto-derived from --dataset."),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override the output JSON report path. Default: auto-derived.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count and display results without writing the output file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the summary table output to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 = all passed, 1 = some failures found, 2 = error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.all_datasets:
        return _run_all_datasets(args)
    return _run_single_dataset(args)


def _run_single_dataset(args: argparse.Namespace) -> int:
    """Run prescreening on a single dataset."""
    dataset_name: str = args.dataset
    metadata_path = args.metadata_path or _metadata_path_for(dataset_name)
    output_path = args.output or _output_path_for(dataset_name)

    try:
        result = run_prescreening(metadata_path, dataset_name=dataset_name)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Failed to parse metadata: %s", exc)
        return 2

    if not args.quiet:
        print_summary(result)

    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        logger.info("Report written to %s", output_path)
    else:
        logger.info("Dry run: skipping file output.")

    if result["failed_any"] > 0:
        return 1
    return 0


def _run_all_datasets(args: argparse.Namespace) -> int:
    """Run prescreening on all datasets in the metadata registry."""
    if not METADATA_REGISTRY_DIR.exists():
        logger.error("Metadata registry not found: %s", METADATA_REGISTRY_DIR)
        return 2

    # Find all *_metadata.json files
    metadata_files = sorted(METADATA_REGISTRY_DIR.glob("*_metadata.json"))
    if not metadata_files:
        logger.error("No metadata files found in %s", METADATA_REGISTRY_DIR)
        return 2

    logger.info("Found %d metadata files", len(metadata_files))

    cross_dataset_results: list[dict[str, Any]] = []
    any_failures = False

    for meta_file in metadata_files:
        # Extract dataset name from filename: "diqa-5000_metadata.json" -> "diqa-5000"
        dataset_name = meta_file.stem.replace("_metadata", "")
        logger.info("--- Prescreening: %s ---", dataset_name)

        try:
            result = run_prescreening(meta_file, dataset_name=dataset_name)
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping %s: %s", dataset_name, exc)
            cross_dataset_results.append(
                {
                    "dataset": dataset_name,
                    "error": str(exc),
                }
            )
            continue

        if not args.quiet:
            print_summary(result)

        # Write individual report
        if not args.dry_run:
            output_path = _output_path_for(dataset_name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2, ensure_ascii=False)

        total = result["total_samples"]
        passed = result["passed_all"]
        pass_rate = round((passed / total) * 100, 2) if total > 0 else 0.0

        cross_dataset_results.append(
            {
                "dataset": dataset_name,
                "total_samples": total,
                "passed_all": passed,
                "failed_any": result["failed_any"],
                "pass_rate_pct": pass_rate,
            }
        )

        if result["failed_any"] > 0:
            any_failures = True

    # Write cross-dataset summary
    if not args.dry_run:
        summary_path = (
            PROJECT_ROOT
            / "scripts"
            / "audit"
            / "results"
            / "cross_dataset_summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "audited_at": datetime.now(UTC).isoformat(),
            "datasets_scanned": len(metadata_files),
            "results": cross_dataset_results,
        }
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
        logger.info("Cross-dataset summary written to %s", summary_path)

    return 1 if any_failures else 0


if __name__ == "__main__":
    sys.exit(main())
