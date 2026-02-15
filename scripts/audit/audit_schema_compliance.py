#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Generic schema compliance checker for Layer 2 enrichment metadata.

Validates any metadata JSON file against ``layer2_enrichment_v2.schema.json``
and produces a structured report covering:

* **Coverage**: What percentage of samples have each field populated.
* **Validity**: Type correctness and enum membership for every value.
* **Completeness**: Whether required sub-fields are present.
* **Semantic rules**: COCO bbox format, confidence ranges, content-flag /
  layout-detection consistency.

Supports both the *nested* schema format (post-migration, ``data.capture_method
= {method: ..., confidence: ...}``) and the *flat* legacy format
(``data.capture_method = "born_digital"``).

CLI usage::

    python scripts/audit/audit_schema_compliance.py \\
        --metadata-path /mnt/e/.../diqa_5000_metadata.json \\
        --schema-path docs/schema/layer2_enrichment_v2.schema.json \\
        --output audit_report.json

    # With audit_config shortcut:
    python scripts/audit/audit_schema_compliance.py \\
        --dataset diqa-5000 --output audit_report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SCHEMA = PROJECT_ROOT / "docs" / "schema" / "layer2_enrichment_v2.schema.json"

# Common string constants (S1192: avoid duplicate string literals)
PREDICTED_MOS_KEY = "llm_scores.predicted_mos"

# Defect classification taxonomy.
DEFECT_TYPES = (
    "wrong_value",
    "missing_value",
    "wrong_format",
    "wrong_enum",
    "inconsistent",
    "not_populated",
)


class DefectType(str, Enum):
    """Taxonomy of enrichment defects."""

    WRONG_VALUE = "wrong_value"
    MISSING_VALUE = "missing_value"
    WRONG_FORMAT = "wrong_format"
    WRONG_ENUM = "wrong_enum"
    INCONSISTENT = "inconsistent"
    NOT_POPULATED = "not_populated"


# ---------------------------------------------------------------------------
# Dataclasses for reporting
# ---------------------------------------------------------------------------
@dataclass
class FieldDefect:
    """A single defect found on one sample for one field."""

    sample_id: str
    field_path: str
    defect_type: str
    message: str
    actual_value: Any = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "sample_id": self.sample_id,
            "field_path": self.field_path,
            "defect_type": self.defect_type,
            "message": self.message,
            "actual_value": _safe_json_value(self.actual_value),
        }


@dataclass
class FieldReport:
    """Aggregated statistics for a single schema field."""

    field_path: str
    populated_count: int = 0
    valid_count: int = 0
    total_samples: int = 0
    defects: list[FieldDefect] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        """Percentage of samples where this field is populated."""
        if self.total_samples == 0:
            return 0.0
        return (self.populated_count / self.total_samples) * 100

    @property
    def validity_pct(self) -> float:
        """Percentage of populated samples that are valid."""
        if self.populated_count == 0:
            return 100.0
        return (self.valid_count / self.populated_count) * 100

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "field_path": self.field_path,
            "populated_count": self.populated_count,
            "valid_count": self.valid_count,
            "total_samples": self.total_samples,
            "coverage_pct": round(self.coverage_pct, 2),
            "validity_pct": round(self.validity_pct, 2),
            "defect_count": len(self.defects),
            "defect_type_counts": dict(Counter(d.defect_type for d in self.defects)),
        }


@dataclass
class SampleResult:
    """Pass / fail result for a single sample."""

    sample_id: str
    is_valid: bool
    defects: list[FieldDefect] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "sample_id": self.sample_id,
            "is_valid": self.is_valid,
            "defect_count": len(self.defects),
            "defects": [d.as_dict() for d in self.defects],
        }


@dataclass
class ComplianceReport:
    """Top-level audit report."""

    dataset_name: str
    schema_version: str
    total_samples: int
    valid_samples: int
    audited_at: str
    field_reports: dict[str, FieldReport] = field(default_factory=dict)
    sample_results: list[SampleResult] = field(default_factory=list)
    consistency_defects: list[FieldDefect] = field(default_factory=list)

    @property
    def validity_pct(self) -> float:
        """Overall percentage of samples with zero defects."""
        if self.total_samples == 0:
            return 0.0
        return (self.valid_samples / self.total_samples) * 100

    def as_dict(self) -> dict[str, Any]:
        """Serialize the full report to a JSON-safe dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "schema_version": self.schema_version,
            "total_samples": self.total_samples,
            "valid_samples": self.valid_samples,
            "validity_pct": round(self.validity_pct, 2),
            "audited_at": self.audited_at,
            "field_summary": {k: v.as_dict() for k, v in self.field_reports.items()},
            "consistency_defects": [d.as_dict() for d in self.consistency_defects],
            "sample_results": [s.as_dict() for s in self.sample_results],
        }


# ---------------------------------------------------------------------------
# Schema loading helpers
# ---------------------------------------------------------------------------
def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load and return the JSON Schema as a dictionary.

    Args:
        schema_path: Absolute path to the schema JSON file.

    Returns:
        Parsed JSON Schema dictionary.

    Raises:
        FileNotFoundError: If the schema file does not exist.
    """
    if not schema_path.exists():
        msg = f"Schema file not found: {schema_path}"
        raise FileNotFoundError(msg)
    with open(schema_path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a ``$ref`` pointer within the schema's ``$defs``."""
    if not ref.startswith("#/$defs/"):
        return {}
    def_name = ref.split("/")[-1]
    return schema.get("$defs", {}).get(def_name, {})


def _get_enum_values(
    schema: dict[str, Any],
    field_schema: dict[str, Any],
) -> list[Any] | None:
    """Extract allowed enum values from a field schema.

    Handles direct ``enum`` and ``$ref`` indirection.
    """
    if "enum" in field_schema:
        return field_schema["enum"]
    ref = field_schema.get("$ref")
    if ref:
        resolved = _resolve_ref(schema, ref)
        if "enum" in resolved:
            return resolved["enum"]
    return None


# ---------------------------------------------------------------------------
# Enrichment data extractors -- handle flat + nested formats
# ---------------------------------------------------------------------------
def _extract_enrichment_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Extract the enrichment ``data`` dict from a sample.

    Supports nested format: ``sample.enrichments.versions[-1].data``
    and gracefully returns an empty dict if the path is missing.
    """
    enrichments = sample.get("enrichments", {})
    versions = enrichments.get("versions", [])
    if not versions:
        return {}
    latest = versions[-1]
    return latest.get("data", {})


def _get_value(
    data: dict[str, Any],
    nested_key: str,
    flat_key: str,
    sub_key: str | None = None,
) -> Any:
    """Get a value from enrichment data in either format.

    Tries nested first (``data[nested_key][sub_key]``), then falls
    back to flat (``data[flat_key]``).

    When the value at *nested_key* is a dict and *sub_key* is given,
    extracts the sub-field.  When it is a non-dict scalar (flat
    format) and *nested_key* == *flat_key*, returns that scalar
    directly.  Otherwise falls back to *flat_key*.
    """
    val = data.get(nested_key)
    if isinstance(val, dict) and sub_key:
        return val.get(sub_key)
    # Flat format: nested_key IS the flat key (e.g. both are
    # "capture_method") and value is a scalar.
    if val is not None and nested_key == flat_key:
        return val
    # Flat format: different key name (e.g. nested_key is
    # "capture_method" but flat_key is "capture_confidence").
    return data.get(flat_key)


# ---------------------------------------------------------------------------
# Per-field validators
# ---------------------------------------------------------------------------
# Each validator returns a list of FieldDefect (empty = valid).

_CAPTURE_ENUMS = [
    "born_digital",
    "scanner_flatbed",
    "scanner_adf",
    "camera_professional",
    "camera_smartphone",
    "fax",
    "synthetic",
    "unknown",
]

_PROVENANCE_TIERS = [
    "tier_0_exact",
    "tier_1_annotation",
    "tier_2_model",
    "tier_3_heuristic",
]

_DOMAIN_LEVEL1 = [
    "TAX",
    "LEG",
    "FIN",
    "TEC",
    "SCI",
    "ADM",
    "MED",
    "EDU",
    "PER",
    "UNK",
]

_RESOLUTION_CATEGORIES = [
    "low_<150",
    "medium_150-299",
    "standard_300",
    "high_>300",
]

_TEXT_SCOPE_ENUMS = [
    "character",
    "word",
    "phrase",
    "sentence",
    "line",
    "paragraph",
    "page",
    "document",
    "mixed",
    "unknown",
]

_CONTENT_TYPE_ENUMS = [
    "printed",
    "handwritten",
    "mixed",
    "scene_text",
    "synthetic",
    "unknown",
]

_LAYOUT_CLASSES = [
    "Caption",
    "Footnote",
    "Formula",
    "List-Item",
    "Page-Footer",
    "Page-Header",
    "Picture",
    "Section-Header",
    "Table",
    "Text",
    "Title",
]

_LAYOUT_TYPES = [
    "single_column",
    "multi_column",
    "three_column",
    "complex",
    "form_based",
    "tabular",
    "unknown",
]


def _validate_confidence(
    sample_id: str,
    field_path: str,
    value: Any,
) -> list[FieldDefect]:
    """Validate a confidence value is a float in [0, 1] or null."""
    if value is None:
        return []
    if not isinstance(value, (int, float)):
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message=(f"Confidence must be numeric, got {type(value).__name__}"),
                actual_value=value,
            )
        ]
    if not (0 <= value <= 1):
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_VALUE,
                message=(f"Confidence must be 0-1, got {value}"),
                actual_value=value,
            )
        ]
    return []


def _validate_enum(
    sample_id: str,
    field_path: str,
    value: Any,
    allowed: list[Any],
) -> list[FieldDefect]:
    """Validate value is one of the allowed enum members."""
    if value is None:
        return []
    if value not in allowed:
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_ENUM,
                message=(f"Value '{value}' not in {allowed!r}"),
                actual_value=value,
            )
        ]
    return []


def _validate_coco_bbox(
    sample_id: str,
    field_path: str,
    bbox: Any,
) -> list[FieldDefect]:
    """Validate COCO bounding box [x, y, width, height]."""
    defects: list[FieldDefect] = []
    if bbox is None:
        return []
    if not isinstance(bbox, list):
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message=(f"bbox must be a list, got {type(bbox).__name__}"),
                actual_value=bbox,
            )
        ]
    if len(bbox) != 4:
        defects.append(
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message=(f"bbox must have 4 elements, got {len(bbox)}"),
                actual_value=bbox,
            )
        )
        return defects

    for idx, val in enumerate(bbox):
        if not isinstance(val, (int, float)):
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=field_path,
                    defect_type=DefectType.WRONG_FORMAT,
                    message=(f"bbox[{idx}] must be numeric, got {type(val).__name__}"),
                    actual_value=bbox,
                )
            )

    # Width and height (indices 2, 3) must be non-negative for COCO.
    if len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox):
        if bbox[2] < 0 or bbox[3] < 0:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=field_path,
                    defect_type=DefectType.WRONG_VALUE,
                    message=("COCO bbox width/height must be >= 0"),
                    actual_value=bbox,
                )
            )
    return defects


def _validate_pixels(
    sample_id: str,
    field_path: str,
    pixels: Any,
) -> list[FieldDefect]:
    """Validate resolution_pixels is [width, height] with ints > 0."""
    if pixels is None:
        return []
    if not isinstance(pixels, list) or len(pixels) != 2:
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message="pixels must be [width, height]",
                actual_value=pixels,
            )
        ]
    for idx, val in enumerate(pixels):
        if not isinstance(val, (int, float)) or val < 1:
            return [
                FieldDefect(
                    sample_id=sample_id,
                    field_path=field_path,
                    defect_type=DefectType.WRONG_VALUE,
                    message=(f"pixels[{idx}] must be a positive number"),
                    actual_value=pixels,
                )
            ]
    return []


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------
def _track_field(
    field_path: str,
    is_populated: bool,
    defects: list[FieldDefect],
    total_fields_report: dict[str, FieldReport],
    all_defects: list[FieldDefect],
) -> None:
    """Track field validation results in reports."""
    if field_path not in total_fields_report:
        total_fields_report[field_path] = FieldReport(field_path=field_path)
    rpt = total_fields_report[field_path]
    rpt.total_samples += 1
    if is_populated:
        rpt.populated_count += 1
        if not defects:
            rpt.valid_count += 1
    rpt.defects.extend(defects)
    all_defects.extend(defects)


def _validate_iso_string(
    sample_id: str,
    field_path: str,
    value: Any,
    expected_len: int | tuple[int, int],
    label: str,
) -> list[FieldDefect]:
    """Validate an ISO code string (language or script)."""
    if value is None:
        return []
    if not isinstance(value, str):
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message=f"{label} must be a string",
                actual_value=value,
            )
        ]
    if isinstance(expected_len, tuple):
        min_len, max_len = expected_len
        if len(value) < min_len or len(value) > max_len:
            return [
                FieldDefect(
                    sample_id=sample_id,
                    field_path=field_path,
                    defect_type=DefectType.WRONG_FORMAT,
                    message=f"{label} must be {min_len}-{max_len} chars",
                    actual_value=value,
                )
            ]
    elif len(value) != expected_len:
        return [
            FieldDefect(
                sample_id=sample_id,
                field_path=field_path,
                defect_type=DefectType.WRONG_FORMAT,
                message=f"{label} must be {expected_len} chars",
                actual_value=value,
            )
        ]
    return []


def _validate_predicted_mos(
    sample_id: str,
    data: dict[str, Any],
) -> tuple[bool, list[FieldDefect]]:
    """Validate llm_scores.predicted_mos field."""
    llm = data.get("llm_scores")
    if not isinstance(llm, dict):
        return False, []
    mos = llm.get("predicted_mos")
    if mos is None:
        return False, []
    if not isinstance(mos, (int, float)):
        return True, [
            FieldDefect(
                sample_id=sample_id,
                field_path=PREDICTED_MOS_KEY,
                defect_type=DefectType.WRONG_FORMAT,
                message="predicted_mos must be numeric",
                actual_value=mos,
            )
        ]
    if not (1 <= mos <= 5):
        return True, [
            FieldDefect(
                sample_id=sample_id,
                field_path=PREDICTED_MOS_KEY,
                defect_type=DefectType.WRONG_VALUE,
                message=f"predicted_mos must be 1-5, got {mos}",
                actual_value=mos,
            )
        ]
    return True, []


def _validate_reliability_summary(
    sample_id: str,
    data: dict[str, Any],
) -> tuple[bool, list[FieldDefect]]:
    """Validate sample_reliability_summary field."""
    srs = data.get("sample_reliability_summary")
    if not isinstance(srs, dict):
        return srs is not None, []
    valid_cats = [
        "hard_label",
        "soft_label",
        "active_learning",
        "unreliable",
        "unassessed",
    ]
    cat = srs.get("min_confidence_category")
    if cat is not None and cat not in valid_cats:
        return True, [
            FieldDefect(
                sample_id=sample_id,
                field_path="sample_reliability_summary.min_confidence_category",
                defect_type=DefectType.WRONG_ENUM,
                message=f"Invalid category '{cat}'",
                actual_value=cat,
            )
        ]
    return True, []


def validate_sample(
    sample_id: str,
    data: dict[str, Any],
    total_fields_report: dict[str, FieldReport],
) -> list[FieldDefect]:
    """Validate a single enrichment data dict.

    Populates *total_fields_report* in-place and returns all defects
    for this sample.

    Args:
        sample_id: Unique sample identifier.
        data: The enrichment ``data`` dictionary (flat or nested).
        total_fields_report: Running field-level statistics accumulator.

    Returns:
        List of defects found for this sample.
    """
    all_defects: list[FieldDefect] = []

    def _track(
        field_path: str,
        is_populated: bool,
        defects: list[FieldDefect],
    ) -> None:
        _track_field(
            field_path, is_populated, defects, total_fields_report, all_defects
        )

    # -- Enum-validated fields (data-driven) ------------------------------
    _enum_fields: list[tuple[str, str, str, str, list[str]]] = [
        (
            "capture_method",
            "capture_method",
            "capture_method",
            "method",
            _CAPTURE_ENUMS,
        ),
        (
            "resolution_category",
            "resolution",
            "resolution_category",
            "category",
            _RESOLUTION_CATEGORIES,
        ),
        ("domain_level1", "domain", "domain_level1", "level1", _DOMAIN_LEVEL1),
        (
            "script_family",
            "language",
            "script_family",
            "script_family",
            ["latin", "cjk", "arabic", "indic", "cyrillic", "other"],
        ),
        ("text_scope", "text_scope", "text_scope", "scope", _TEXT_SCOPE_ENUMS),
        (
            "text_scope_content_type",
            "text_scope",
            "text_scope_content_type",
            "content_type",
            _CONTENT_TYPE_ENUMS,
        ),
    ]
    for field_path, group, flat_key, nested_key, enums in _enum_fields:
        val = _get_value(data, group, flat_key, nested_key)
        _track(
            field_path,
            val is not None,
            _validate_enum(sample_id, field_path, val, enums),
        )

    # -- Confidence-validated fields (data-driven) ------------------------
    _conf_fields: list[tuple[str, str, str, str]] = [
        ("capture_confidence", "capture_method", "capture_confidence", "confidence"),
        ("domain_confidence", "domain", "domain_confidence", "confidence"),
        ("quality_overall_score", "quality", "quality_overall_score", "overall_score"),
    ]
    for field_path, group, flat_key, nested_key in _conf_fields:
        val = _get_value(data, group, flat_key, nested_key)
        _track(
            field_path,
            val is not None,
            _validate_confidence(sample_id, field_path, val),
        )

    # -- resolution_pixels ------------------------------------------------
    rp = _get_value(data, "resolution", "resolution_pixels", "pixels")
    _track(
        "resolution_pixels",
        rp is not None,
        _validate_pixels(sample_id, "resolution_pixels", rp),
    )

    # -- iso639_language --------------------------------------------------
    lang = _get_value(data, "language", "iso639_language", "language_code")
    _track(
        "iso639_language",
        lang is not None,
        _validate_iso_string(
            sample_id, "iso639_language", lang, (2, 3), "language_code"
        ),
    )

    # -- iso15924_script --------------------------------------------------
    script = _get_value(data, "language", "iso15924_script", "script_code")
    _track(
        "iso15924_script",
        script is not None,
        _validate_iso_string(sample_id, "iso15924_script", script, 4, "script_code"),
    )

    # -- content_flags (boolean flags) ------------------------------------
    _validate_content_flags(sample_id, data, total_fields_report, all_defects)

    # -- layout_detections ------------------------------------------------
    _validate_layout_detections(sample_id, data, total_fields_report, all_defects)

    # -- llm_scores.predicted_mos -----------------------------------------
    mos_populated, mos_defects = _validate_predicted_mos(sample_id, data)
    _track(PREDICTED_MOS_KEY, mos_populated, mos_defects)

    # -- sample_reliability_summary ---------------------------------------
    srs_populated, srs_defects = _validate_reliability_summary(sample_id, data)
    _track("sample_reliability_summary", srs_populated, srs_defects)

    return all_defects


def _validate_content_flags(
    sample_id: str,
    data: dict[str, Any],
    report: dict[str, FieldReport],
    all_defects: list[FieldDefect],
) -> None:
    """Validate content_flags booleans and their confidence companions."""
    cf = data.get("content_flags")
    flags_dict: dict[str, Any] = {}
    if isinstance(cf, dict):
        flags_dict = cf

    flag_names = [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_signature",
        "has_figure",
        "has_code",
    ]

    def _track(
        fp: str,
        is_pop: bool,
        defects: list[FieldDefect],
    ) -> None:
        if fp not in report:
            report[fp] = FieldReport(field_path=fp)
        rpt = report[fp]
        rpt.total_samples += 1
        if is_pop:
            rpt.populated_count += 1
            if not defects:
                rpt.valid_count += 1
        rpt.defects.extend(defects)
        all_defects.extend(defects)

    for flag_name in flag_names:
        # Flat format: data["has_table"], data["has_formula"]
        val = flags_dict.get(flag_name) if flags_dict else None
        if val is None:
            val = data.get(flag_name)
        is_populated = val is not None
        defects: list[FieldDefect] = []
        if is_populated and not isinstance(val, bool):
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"content_flags.{flag_name}",
                    defect_type=DefectType.WRONG_FORMAT,
                    message=(f"{flag_name} must be boolean, got {type(val).__name__}"),
                    actual_value=val,
                )
            )
        _track(
            f"content_flags.{flag_name}",
            is_populated,
            defects,
        )

        # Companion confidence field.
        conf_name = flag_name.replace("has_", "") + "_confidence"
        conf_val = flags_dict.get(conf_name) if flags_dict else None
        if conf_val is None:
            conf_val = data.get(conf_name)
        _track(
            f"content_flags.{conf_name}",
            conf_val is not None,
            _validate_confidence(
                sample_id,
                f"content_flags.{conf_name}",
                conf_val,
            ),
        )


def _validate_layout_detections(
    sample_id: str,
    data: dict[str, Any],
    report: dict[str, FieldReport],
    all_defects: list[FieldDefect],
) -> None:
    """Validate layout_detections array elements."""
    fp = "layout_detections"
    if fp not in report:
        report[fp] = FieldReport(field_path=fp)
    rpt = report[fp]
    rpt.total_samples += 1

    ld = data.get("layout_detections")
    if ld is None or not isinstance(ld, list):
        return

    rpt.populated_count += 1
    defects: list[FieldDefect] = []

    for idx, det in enumerate(ld):
        if not isinstance(det, dict):
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}]",
                    defect_type=DefectType.WRONG_FORMAT,
                    message="detection must be a dict",
                    actual_value=det,
                )
            )
            continue

        # class_name
        cn = det.get("class_name")
        if cn is None:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}].class_name",
                    defect_type=DefectType.MISSING_VALUE,
                    message="class_name is required",
                )
            )
        elif cn not in _LAYOUT_CLASSES:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}].class_name",
                    defect_type=DefectType.WRONG_ENUM,
                    message=(f"'{cn}' not in DocLayNet 11-class taxonomy"),
                    actual_value=cn,
                )
            )

        # bbox -- must be COCO xywh
        bbox = det.get("bbox")
        if bbox is None:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}].bbox",
                    defect_type=DefectType.MISSING_VALUE,
                    message="bbox is required",
                )
            )
        else:
            defects.extend(_validate_coco_bbox(sample_id, f"{fp}[{idx}].bbox", bbox))

        # confidence
        conf = det.get("confidence")
        if conf is None:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}].confidence",
                    defect_type=DefectType.MISSING_VALUE,
                    message="confidence is required",
                )
            )
        else:
            defects.extend(
                _validate_confidence(
                    sample_id,
                    f"{fp}[{idx}].confidence",
                    conf,
                )
            )

        # source
        if det.get("source") is None:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=f"{fp}[{idx}].source",
                    defect_type=DefectType.MISSING_VALUE,
                    message="source is required",
                )
            )

    if not defects:
        rpt.valid_count += 1
    rpt.defects.extend(defects)
    all_defects.extend(defects)


# ---------------------------------------------------------------------------
# Cross-field consistency checks
# ---------------------------------------------------------------------------
def check_consistency(
    sample_id: str,
    data: dict[str, Any],
) -> list[FieldDefect]:
    """Run cross-field consistency checks for a single sample.

    Checks:
    1. Layout detections contain "Table" but has_table is false.
    2. Layout detections contain "Formula" but has_formula is false.
    3. Layout detections contain "Picture" but has_figure is false.

    Returns:
        List of consistency defects.
    """
    defects: list[FieldDefect] = []

    ld = data.get("layout_detections", [])
    if not isinstance(ld, list):
        return defects

    detected_classes: set[str] = set()
    for det in ld:
        if isinstance(det, dict):
            cn = det.get("class_name")
            if cn:
                detected_classes.add(cn)

    # Map layout class -> content flag
    consistency_map: list[tuple[str, str, str]] = [
        ("Table", "has_table", "content_flags.has_table"),
        ("Formula", "has_formula", "content_flags.has_formula"),
        ("Picture", "has_figure", "content_flags.has_figure"),
    ]

    cf = data.get("content_flags", {})
    for layout_class, flag_key, field_path in consistency_map:
        if layout_class not in detected_classes:
            continue

        # Check flat format first, then nested.
        flag_val = data.get(flag_key)
        if flag_val is None and isinstance(cf, dict):
            flag_val = cf.get(flag_key)

        if flag_val is False:
            defects.append(
                FieldDefect(
                    sample_id=sample_id,
                    field_path=field_path,
                    defect_type=DefectType.INCONSISTENT,
                    message=(
                        f"layout_detections has '{layout_class}' but {flag_key}=false"
                    ),
                    actual_value=False,
                )
            )

    return defects


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run_compliance_audit(
    metadata_path: Path,
    schema_path: Path | None = None,
) -> ComplianceReport:
    """Run a full compliance audit on a metadata JSON file.

    Args:
        metadata_path: Path to the dataset metadata JSON.
        schema_path: Optional override for the schema path.

    Returns:
        A ``ComplianceReport`` with per-field and per-sample results.

    Raises:
        FileNotFoundError: If the metadata file does not exist.
    """
    # schema_path is accepted for future schema-driven validation;
    # currently the audit uses hard-coded field definitions.
    _ = schema_path or DEFAULT_SCHEMA

    if not metadata_path.exists():
        msg = f"Metadata file not found: {metadata_path}"
        raise FileNotFoundError(msg)

    logger.info("Loading metadata from %s", metadata_path)
    with open(metadata_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    dataset_name = meta.get("dataset_name", metadata_path.stem)
    schema_version = meta.get("schema_version", "unknown")
    samples = meta.get("samples", [])

    logger.info(
        "Auditing %d samples for dataset '%s' (schema %s)",
        len(samples),
        dataset_name,
        schema_version,
    )

    field_reports: dict[str, FieldReport] = {}
    sample_results: list[SampleResult] = []
    consistency_defects: list[FieldDefect] = []
    valid_count = 0

    for sample in samples:
        sid = sample.get("id", "unknown")
        data = _extract_enrichment_data(sample)

        sample_defects = validate_sample(sid, data, field_reports)

        # Cross-field consistency.
        cons_defects = check_consistency(sid, data)
        consistency_defects.extend(cons_defects)
        sample_defects.extend(cons_defects)

        is_valid = len(sample_defects) == 0
        if is_valid:
            valid_count += 1
        sample_results.append(
            SampleResult(
                sample_id=sid,
                is_valid=is_valid,
                defects=sample_defects,
            )
        )

    report = ComplianceReport(
        dataset_name=dataset_name,
        schema_version=schema_version,
        total_samples=len(samples),
        valid_samples=valid_count,
        audited_at=datetime.now(UTC).isoformat(),
        field_reports=field_reports,
        sample_results=sample_results,
        consistency_defects=consistency_defects,
    )

    logger.info(
        "Audit complete: %d/%d samples valid (%.1f%%)",
        valid_count,
        len(samples),
        report.validity_pct,
    )

    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_json_value(value: Any) -> Any:
    """Ensure value is JSON-serializable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_json_value(v) for k, v in value.items()}
    return str(value)


def write_report(report: ComplianceReport, output_path: Path) -> None:
    """Write the compliance report to a JSON file.

    Args:
        report: The completed compliance report.
        output_path: Destination file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report.as_dict(), fh, indent=2, ensure_ascii=False)
    logger.info("Report written to %s", output_path)


def print_summary(report: ComplianceReport) -> None:
    """Print a concise summary table to stdout."""
    header = (
        f"\n{'=' * 60}\n"
        f"  COMPLIANCE REPORT: {report.dataset_name}\n"
        f"  Schema: {report.schema_version}  |  "
        f"Audited: {report.audited_at}\n"
        f"{'=' * 60}\n"
    )
    print(header)
    print(
        f"  Samples: {report.total_samples}  |  "
        f"Valid: {report.valid_samples}  |  "
        f"Rate: {report.validity_pct:.1f}%\n"
    )

    print(f"  {'Field':<40} {'Coverage':>8} {'Validity':>8}")
    print(f"  {'-' * 40} {'-' * 8} {'-' * 8}")
    for fp in sorted(report.field_reports):
        fr = report.field_reports[fp]
        print(f"  {fp:<40} {fr.coverage_pct:>7.1f}% {fr.validity_pct:>7.1f}%")

    if report.consistency_defects:
        print(f"\n  Consistency defects: {len(report.consistency_defects)}")
        type_counts = Counter(d.defect_type for d in report.consistency_defects)
        for dtype, count in type_counts.most_common():
            print(f"    {dtype}: {count}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate Layer 2 metadata against layer2_enrichment_v2.schema.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--metadata-path",
        type=Path,
        help="Path to the metadata JSON file to audit.",
    )
    group.add_argument(
        "--dataset",
        type=str,
        help=(
            "Known dataset name (loads path from audit_config). "
            "Use --list-datasets to see available names."
        ),
    )
    group.add_argument(
        "--list-datasets",
        action="store_true",
        help="List known datasets and exit.",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=None,
        help=(
            "Path to JSON Schema file. "
            "Default: docs/schema/layer2_enrichment_v2.schema.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write structured JSON report to this path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output to stdout.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = defects found, 2 = error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.list_datasets:
        from scripts.audit.audit_config import list_known_datasets

        datasets = list_known_datasets()
        print("Known datasets:")
        for name in datasets:
            print(f"  {name}")
        return 0

    metadata_path: Path | None = args.metadata_path
    schema_path: Path | None = args.schema_path

    if args.dataset:
        try:
            from scripts.audit.audit_config import (
                load_dataset_config,
            )

            cfg = load_dataset_config(
                args.dataset,
                schema_path=schema_path,
            )
            metadata_path = cfg.metadata_json_path
            if schema_path is None:
                schema_path = cfg.schema_path
        except ValueError as exc:
            logger.error("%s", exc)
            return 2

    if metadata_path is None:
        logger.error("No metadata path resolved.")
        return 2

    try:
        report = run_compliance_audit(metadata_path, schema_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    if not args.quiet:
        print_summary(report)

    output_path: Path | None = args.output

    # Auto-output to results/{dataset}/compliance.json when --dataset is used
    # and no explicit --output is given.  This ensures compute_scorecard.py can
    # find the artifact without manual --output flags.
    if output_path is None and args.dataset:
        auto_dir = Path(__file__).resolve().parent / "results" / args.dataset
        auto_dir.mkdir(parents=True, exist_ok=True)
        output_path = auto_dir / "compliance.json"
        logger.info("Auto-outputting to %s (use --output to override)", output_path)

    if output_path:
        write_report(report, output_path)

    # Exit code 1 if any defects found.
    if report.valid_samples < report.total_samples:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
