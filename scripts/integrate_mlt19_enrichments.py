#!/usr/bin/env python3
"""Integrate all enrichment sources into MLT19 Layer 2 metadata.

Merges 5 data sources into the main metadata JSON for all 19,657 records:
  1. Parser original_labels: language_code, raw_labels.languages (train split GT)
  2. Train GT enrichments (134 low-conf train samples): script from GT file parsing
  3. VLM contact sheet enrichments (9735 test samples): visual script identification
  4. LLM enrichment (text-only, 9989 images): domain, language, script, content_type
  5. Language enrichment (OpenLID, 1000 images): language, script, confidence

Also applies:
  - Layout label standardization (D09): DocLayout-YOLO class_name -> DocLayNet PascalCase
  - Hardcoded known values: capture_method=camera_smartphone
  - Content flag derivation from layout canonical_class
  - Missing field population: split, orientation_class, color_mode, handwriting_present
  - Reliability summary recomputation

Creates a new enrichment version (v3) in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_mlt19_enrichments.py

    # Dry run (report only, no write):
    PYTHONPATH=... uv run python3 scripts/integrate_mlt19_enrichments.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "mlt19_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "mlt19_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "mlt19_language_enrichment.json"

# Audit-phase enrichments (VLM contact sheet + train GT)
AUDIT_DIR = Path("scripts/audit/results/mlt19")
VLM_TEST_ENRICHMENT_PATH = AUDIT_DIR / "vlm_test_enrichments.json"
TRAIN_GT_ENRICHMENT_PATH = AUDIT_DIR / "train_gt_enrichments.json"

SCRIPT_VERSION = "2.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v3"

# Content flag derivation from canonical layout classes
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# DocLayout-YOLO (docstructbench) -> DocLayNet PascalCase mapping
# Used for class_name standardization alongside canonical_class
DOCLAYOUT_YOLO_TO_DOCLAYNET: dict[str, str] = {
    "figure": "Picture",
    "title": "Title",
    "plain text": "Text",
    "abandon": "Text",  # No direct equivalent; map to Text
    "figure_caption": "Caption",
    "table": "Table",
    "table_caption": "Caption",
    "table_footnote": "Footnote",
    "isolate_formula": "Formula",
    "formula_caption": "Caption",
}

# MLT19 parser language code -> ISO 15924 script mapping
# Mirrors Mlt19Parser.LANGUAGE_TO_SCRIPT
LANGUAGE_TO_SCRIPT: dict[str, str] = {
    "Arabic": "Arab",
    "Bangla": "Beng",
    "Chinese": "Hans",
    "Hindi": "Deva",
    "Japanese": "Jpan",
    "Korean": "Hang",
    "Latin": "Latn",
    "Symbols": "Zyyy",
    "Mixed": "Zmth",
    "None": "Zyyy",
}

# MLT19 parser language name -> ISO 639-1 code mapping
LANGUAGE_TO_ISO639: dict[str, str] = {
    "Arabic": "ar",
    "Bangla": "bn",
    "Chinese": "zh",
    "Hindi": "hi",
    "Japanese": "ja",
    "Korean": "ko",
    "Latin": "en",  # Default for Latin script
    "French": "fr",
    "German": "de",
    "Italian": "it",
}

# VLM corrections: per-sample overrides from visual inspection (Phase 6).
# Updated after VLM inspection.
# has_figure: scene text images themselves ARE photographs, not embedded figures.
# Override ALL has_figure=True to False unless VLM confirms actual embedded figure.
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # VLM inspection: 0/19657 true positives. Scene photos are NOT embedded figures.
    }
)

VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # VLM inspection: 12/14 flagged are true positives (85.7% TP rate)
        "ts_img_00093",  # Italian train departure board with grid
        "ts_img_05637",  # Prayer times table with handwritten entries
        "tr_img_03126",  # Chinese metro schedule with grid
        "tr_img_05080",  # Korean key manager contact info grid
        "tr_img_05409",  # Korean fire safety officer table
        "tr_img_05704",  # Korean warning with form/table + handwritten phone
        "tr_img_05857",  # Korean schedule fragment with grid
        "tr_img_05950",  # Korean waste bag change info table
        "tr_img_05965",  # Korean management number plate grid
        "tr_img_06896",  # Japanese parking lot pricing table
        "tr_img_07480",  # Italian bank security notice 3-row grid
        "tr_img_07885",  # Italian store hours table (day x time)
    }
)

VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # VLM inspection: 0/6 flagged are true positives (100% FP rate)
    }
)

VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # VLM inspection: 3 samples confirmed with handwritten elements
        "ts_img_05637",  # Prayer times with handwritten "12:30" and "3:55"
        "tr_img_05704",  # Korean warning form with handwritten phone "042-821-1656"
        "tr_img_07588",  # Italian referendum notice with handwritten date/location
    }
)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_metadata(path: Path) -> dict[str, Any]:
    """Load L2 metadata JSON."""
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id."""
    if not path.exists():
        log.warning("LLM enrichment not found: %s", path)
        return {}
    log.info("Loading LLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment and index by image_id."""
    if not path.exists():
        log.warning("Language enrichment not found: %s", path)
        return {}
    log.info("Loading language enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_vlm_test_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM contact sheet enrichment and index by image stem.

    These are visual script identifications for 9735 test samples.
    """
    if not path.exists():
        log.warning("VLM test enrichment not found: %s", path)
        return {}
    log.info("Loading VLM test enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d VLM test records", len(index))
    return index


def load_train_gt_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load train GT enrichment for low-confidence train samples.

    These are script identifications from ground truth annotation files
    for 134 train samples that had UNK domain.
    """
    if not path.exists():
        log.warning("Train GT enrichment not found: %s", path)
        return {}
    log.info("Loading train GT enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d train GT records", len(index))
    return index


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes."""
    canonical_classes = {
        d.get("canonical_class", "").upper()
        for d in detections
        if d.get("canonical_class")
    }
    return {
        "has_table": bool(canonical_classes & TABLE_CLASSES),
        "has_formula": bool(canonical_classes & FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & FIGURE_CLASSES),
        "has_code": bool(canonical_classes & CODE_CLASSES),
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict."""
    fields: list[dict[str, Any]] = []

    field_defs = [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]

    for field_name, conf_key in field_defs:
        confidence = data.get(conf_key, 0.0)
        if confidence is None:
            confidence = 0.0

        if confidence >= 0.9:
            category = "hard_label"
        elif confidence >= 0.7:
            category = "soft_label"
        elif confidence >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"

        fields.append(
            {
                "field": field_name,
                "confidence": round(confidence, 4),
                "category": category,
                "is_soft_label": category == "soft_label",
            }
        )

    min_field = min(fields, key=lambda f: f["confidence"])

    return {
        "min_confidence": min_field["confidence"],
        "min_confidence_field": min_field["field"],
        "min_confidence_category": min_field["category"],
        "assessed_field_count": len(fields),
        "hard_field_count": sum(1 for f in fields if f["category"] == "hard_label"),
        "soft_field_count": sum(1 for f in fields if f["category"] == "soft_label"),
        "field_summary": fields,
        "computed_at": datetime.now(UTC).isoformat(),
    }


def standardize_class_name(class_name: str) -> str:
    """Convert DocLayout-YOLO class_name to DocLayNet PascalCase."""
    return DOCLAYOUT_YOLO_TO_DOCLAYNET.get(class_name, class_name)


def _resolve_multilingual_primary(
    raw_labels: dict[str, Any],
) -> tuple[str, str, float, str] | None:
    """Resolve primary language from multi-lingual raw_labels.languages."""
    languages = raw_labels.get("languages", [])
    for lang_name in languages:
        if lang_name in ("None", "Symbols", "Mixed"):
            continue
        primary_lang = LANGUAGE_TO_ISO639.get(lang_name)
        primary_script = LANGUAGE_TO_SCRIPT.get(lang_name)
        if primary_lang:
            return (primary_lang, primary_script or "Zyyy", 0.95, "parser_gt_primary")
    return None


def _resolve_parser_gt(
    sample: dict[str, Any],
) -> tuple[str, str, float, str] | None:
    """Try to resolve language from parser ground truth (train split only)."""
    split = sample["source"]["split"]
    ol = sample.get("original_labels", {})
    language_code = ol.get("language_code", "")
    raw_labels = ol.get("raw_labels", {})

    if split != "train" or not language_code or language_code in ("und", ""):
        return None

    if language_code == "mul":
        result = _resolve_multilingual_primary(raw_labels)
        if result:
            return result
        return ("mul", "Zmth", 0.9, "parser_gt_multilingual")

    script = ol.get("iso15924_script_code", "")
    if not script:
        languages = raw_labels.get("languages", [])
        if languages:
            script = LANGUAGE_TO_SCRIPT.get(languages[0], "Zyyy")
    return (language_code, script or "Zyyy", 0.95, "parser_gt")


def _resolve_from_enrichment_record(
    record: dict[str, Any] | None,
    lang_key: str,
    script_key: str,
    default_conf: float,
    method: str,
    *,
    conf_key: str | None = None,
    cap_conf: float | None = None,
) -> tuple[str, str, float, str] | None:
    """Try to resolve language from a single enrichment source record."""
    if not record:
        return None
    lang_val = record.get(lang_key)
    if not lang_val or lang_val == "und":
        return None
    script_val = record.get(script_key) or "Zyyy"
    if conf_key is not None:
        conf = record.get(conf_key, default_conf)
        if cap_conf is not None:
            conf = min(conf, cap_conf)
    else:
        conf = default_conf
    return (lang_val, script_val, conf, method)


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
    vlm_enrichment: dict[str, Any] | None = None,
    train_gt: dict[str, Any] | None = None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a sample.

    Priority:
      1. Parser original_labels (train split GT) - highest confidence
      2. Train GT enrichments (134 low-conf train samples from GT files)
      3. VLM contact sheet enrichments (9735 test samples, visual script ID)
      4. LLM enrichment iso639_language
      5. Language enrichment (OpenLID)
      6. Fallback "und"

    Returns:
        (iso639_language, iso15924_script, confidence, method)
    """
    # Source 1: Parser ground truth (train split only)
    result = _resolve_parser_gt(sample)
    if result:
        return result

    # Source 2: Train GT enrichments (from GT file parsing, 134 samples)
    result = _resolve_from_enrichment_record(
        train_gt,
        "iso639_language",
        "iso15924_script",
        0.9,
        "train_gt_enrichment",
        conf_key="language_confidence",
    )
    if result:
        return result

    # Source 3: VLM contact sheet enrichments (visual script ID, 9735 test samples)
    result = _resolve_from_enrichment_record(
        vlm_enrichment,
        "iso639_language",
        "iso15924_script",
        0.75,
        "vlm_contact_sheet",
        conf_key="language_confidence",
    )
    if result:
        return result

    # Source 4: LLM enrichment
    result = _resolve_from_enrichment_record(
        llm,
        "iso639_language",
        "iso15924_script",
        0.7,
        "llm_vision",
    )
    if result:
        return result

    # Source 5: Language enrichment (OpenLID)
    result = _resolve_from_enrichment_record(
        lang_enrichment,
        "language",
        "script",
        0.5,
        "openlid_v2",
        conf_key="confidence",
        cap_conf=0.6,
    )
    if result:
        return result

    # Fallback
    return ("und", "Zyyy", 0.1, "none")


# ---------------------------------------------------------------------------
# Per-sample integration
# ---------------------------------------------------------------------------
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None = None,
    train_gt_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Returns a new enrichment version data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # Get existing v1 data
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # All enrichment source lookups
    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    vlm_enrichment = (vlm_index or {}).get(filename_stem)
    train_gt = (train_gt_index or {}).get(filename_stem)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01 - split: from source.split
    # -------------------------------------------------------------------
    data["split"] = sample["source"]["split"]

    # -------------------------------------------------------------------
    # D02 - capture_method: ALL camera_smartphone (from dataset documentation)
    # MLT19 is a camera-captured scene text dataset
    # -------------------------------------------------------------------
    data["capture_method"] = "camera_smartphone"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D02 - domain_level1: from LLM enrichment (or keep UNK)
    # KI-007: UNK is acceptable for scene text
    # -------------------------------------------------------------------
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_text"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        # Keep v1 or default UNK
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
        data["domain_detection_method"] = v1_data.get("domain_detection_method", "none")

    # -------------------------------------------------------------------
    # D07 - iso639_language & D11 - iso15924_script: multi-source resolution
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_enrichment, train_gt
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # D03 - script_family: derived from iso15924_script
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # D09 - Layout detections: standardize class_name
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout: list[dict[str, Any]] = []
    for det in v1_layout:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "doclayout_yolo"
    data["layout_confidence"] = 0.6  # Lower than Docling; DocLayout-YOLO on scene text
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # D10 - Content flags: derived from layout + VLM overrides
    # Scene text: figures=scene photos (not embedded), tables/formulas very rare
    # -------------------------------------------------------------------
    flags = derive_content_flags(standardized_layout)

    # has_figure: DocLayout-YOLO classifies whole scene photos as "figure".
    # For scene text, the image IS a photograph - has_figure means embedded
    # charts/diagrams within a document. Override to False unless VLM-confirmed.
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES

    # has_table: only VLM-confirmed true positives (14 flagged by DocLayout-YOLO)
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES

    # has_formula: only VLM-confirmed true positives (8 flagged by DocLayout-YOLO)
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES

    # has_handwriting: VLM inspection found 3 true positives
    data["has_handwriting"] = filename_stem in VLM_HANDWRITING_TRUE_POSITIVES
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]  # No code detections expected

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "doclayout_yolo+vlm_corrected"
    data["content_flags_confidence"] = 0.85

    # D06 - handwriting_present: prescreening alias
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # D04 - orientation_class: default upright (no source available)
    # LLM enrichment was text-only, orientation=None for all
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.5
    data["orientation_detection_method"] = "default_upright"

    # -------------------------------------------------------------------
    # D05 - image_properties_color_mode: all camera photos are color
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = "color"

    # -------------------------------------------------------------------
    # Text scope: scene text with word-level annotations
    # -------------------------------------------------------------------
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "scene_text"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "scene_text"
        )
    data["text_scope"] = v1_data.get("text_scope", "phrase")

    # -------------------------------------------------------------------
    # Additional derived fields
    # -------------------------------------------------------------------
    data["dataset_short_code"] = "mlt19"

    # Preserve v1 text quality fields
    for field in (
        "text_quality_confidence",
        "text_quality_is_soft_label",
        "text_quality_method",
        "text_quality_provenance_tier",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # Resolution from v1
    data["resolution_category"] = v1_data.get("resolution_category", "standard_300")
    data["resolution_pixels"] = v1_data.get("resolution_pixels")

    # -------------------------------------------------------------------
    # Reliability summary recomputation
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ---------------------------------------------------------------------------
# Integration runner
# ---------------------------------------------------------------------------
def _track_sample_stats(
    stats: dict[str, Any],
    filename_stem: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None,
    train_gt_index: dict[str, dict[str, Any]] | None,
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename_stem in lang_index:
        stats["lang_matched"] += 1
    if vlm_index and filename_stem in vlm_index:
        stats["vlm_matched"] += 1
    if train_gt_index and filename_stem in train_gt_index:
        stats["train_gt_matched"] += 1
    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1
    stats["content_type_dist"][
        integrated_data.get("text_scope_content_type", "unknown")
    ] += 1
    _track_content_flag_counts(stats, integrated_data)


def _track_content_flag_counts(
    stats: dict[str, Any],
    integrated_data: dict[str, Any],
) -> None:
    """Increment content flag counters based on integrated data."""
    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for i, v in enumerate(versions):
        if v.get("version") == version_number:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None = None,
    train_gt_index: dict[str, dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "vlm_matched": 0,
        "train_gt_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "content_type_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        integrated_data = integrate_sample(
            sample, llm_index, lang_index, vlm_index, train_gt_index
        )

        _track_sample_stats(
            stats,
            filename_stem,
            integrated_data,
            llm_index,
            lang_index,
            vlm_index,
            train_gt_index,
        )

        if not dry_run:
            new_version = {
                "version": 3,
                "created_at": now,
                "created_by": "integrate_mlt19_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser GT + train GT enrichment + VLM contact sheet + "
                    "LLM text + OpenLID language + "
                    "DocLayout-YOLO layout + dataset documentation"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, 3)

    return stats


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    print("\n" + "=" * 60)
    print("MLT19 Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"VLM test matched:     {stats.get('vlm_matched', 0)}")
    print(f"Train GT matched:     {stats.get('train_gt_matched', 0)}")
    print()
    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / total_samples * 100
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
    print()
    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:5d}")
    print()
    print("Language distribution (top 15):")
    for lang, count in stats["lang_dist"].most_common(15):
        pct = count / total_samples * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()
    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / total_samples * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
    print()
    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:5d}")
    print()
    print("Content type (top 10):")
    for ct, count in stats["content_type_dist"].most_common(10):
        print(f"  {ct:30s}: {count:5d}")
    print()
    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into MLT19 metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to mlt19_metadata.json (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--llm-enrichment",
        type=Path,
        default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--language-enrichment",
        type=Path,
        default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--vlm-enrichment",
        type=Path,
        default=VLM_TEST_ENRICHMENT_PATH,
        help="Path to VLM test enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--train-gt-enrichment",
        type=Path,
        default=TRAIN_GT_ENRICHMENT_PATH,
        help="Path to train GT enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path = args.output or args.metadata

    # Load all data sources
    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)
    vlm_index = load_vlm_test_enrichment(args.vlm_enrichment)
    train_gt_index = load_train_gt_enrichment(args.train_gt_enrichment)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        vlm_index=vlm_index,
        train_gt_index=train_gt_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))


if __name__ == "__main__":
    main()
