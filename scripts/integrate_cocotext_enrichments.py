#!/usr/bin/env python3
"""Integrate all enrichment sources into cocotext Layer 2 metadata.

TEMPLATE VERSION: 1.1.0 (customized)
CREATED FROM: scripts/audit/integration_script_template.py
REFERENCE: scripts/integrate_mlt19_enrichments.py (closest peer: scene text)

Merges 3 data sources into the main metadata JSON:
  1. Parser original_labels: language ("english"/"not_english"/"na"),
     text_class ("machine printed"/"handwritten"), split, word-level text_instances
  2. LLM enrichment (text-only, 16,441/63,686 images): domain, language, content_type
  3. Language enrichment (OpenLID, ~16K images): language, script (UNRELIABLE for
     scene text - average confidence 0.437, detects zh as dominant for English corpus)

Also applies:
  - Hardcoded known values: capture_method=camera_smartphone
  - has_handwriting from parser ground truth (class="handwritten" annotations)
  - Missing field population: split, orientation_class, color_mode
  - Reliability summary computation

Known issue mitigations:
  - KI-006 (formula semantic confusion): No formulas in scene text -> all False
  - KI-007 (UNK domain): Acceptable for scene text, ~81.6% UNK expected
  - KI-008 (script_family directionality): Re-derive from ISO 15924
  - KI-009 (unreliable language claims): Parser labels are coarse; OpenLID
    unreliable for short text; LLM is low-coverage

v2 changes (schema v2.3.0):
  - Added text_direction (ltr/rtl) derived from iso15924_script
  - Added text_directions_present aggregated from parser language labels

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_cocotext_enrichments.py --dry-run

    # Write output:
    PYTHONPATH=... uv run python3 scripts/integrate_cocotext_enrichments.py
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "coco-text"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/cocotext.py"
)


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
METADATA_PATH = REGISTRY_DIR / "json" / "cocotext_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "cocotext_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "cocotext_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# Content flag derivation classes (for layout detections, if any)
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# COCO-Text parser language -> ISO 15924 script mapping
# "english" is Latn; "not_english" could be anything, resolved below
COCOTEXT_LANG_TO_SCRIPT: dict[str, str] = {
    "english": "Latn",
    "not_english": "Zyyy",  # Common (undetermined script for non-English)
    "na": "Zyyy",
}

# ISO 15924 script code -> text direction mapping (v2.3.0 schema)
# Scene text: CJK is predominantly horizontal (ltr) in signage context
SCRIPT_TO_DIRECTION: dict[str, str] = {
    "Arab": "rtl",
    "Hebr": "rtl",
    "Latn": "ltr",
    "Deva": "ltr",
    "Beng": "ltr",
    "Hans": "ltr",
    "Hant": "ltr",
    "Jpan": "ltr",
    "Hang": "ltr",
    "Kore": "ltr",
    "Cyrl": "ltr",
    "Grek": "ltr",
    "Zyyy": "ltr",
    "Zmth": "ltr",
}

# VLM corrections: per-sample overrides from visual inspection (Phase 6).
# Populated during VLM inspection phase.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# NOTE: has_handwriting is derived from PARSER ground truth (class="handwritten"),
# NOT from VLM inspection. The VLM set below is for additional corrections only.
VLM_HANDWRITING_CORRECTIONS: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Key bridging: COCO filename stem <-> enrichment image_id
# ---------------------------------------------------------------------------
def _extract_coco_image_id(filename_stem: str) -> int | None:
    """Extract COCO integer image_id from a filename stem.

    COCO-Text filenames follow the pattern: COCO_{split}_{image_id:012d}
    e.g., "COCO_train2014_000000217925" -> 217925

    Enrichment files are keyed by this integer image_id, while base metadata
    uses the full filename stem. This function bridges the two.

    Returns:
        Integer image_id, or None if the pattern doesn't match.
    """
    parts = filename_stem.rsplit("_", maxsplit=1)
    if len(parts) == 2:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


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


def load_llm_enrichment(path: Path) -> dict[int, dict[str, Any]]:
    """Load LLM enrichment and index by integer COCO image_id.

    Enrichment files store image_id as strings (e.g., "217925").
    We convert to int for consistent lookup via _extract_coco_image_id().
    """
    if not path.exists():
        log.warning("LLM enrichment not found: %s", path)
        return {}
    log.info("Loading LLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[int, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            try:
                index[int(image_id)] = rec
            except (ValueError, TypeError):
                log.debug("Skipping non-integer image_id: %r", image_id)
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[int, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by integer COCO image_id.

    Enrichment files store image_id as strings (e.g., "217925").
    We convert to int for consistent lookup via _extract_coco_image_id().
    """
    if not path.exists():
        log.warning("Language enrichment not found: %s", path)
        return {}
    log.info("Loading language enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[int, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            try:
                index[int(image_id)] = rec
            except (ValueError, TypeError):
                log.debug("Skipping non-integer image_id: %r", image_id)
    log.info("  Indexed %d language records", len(index))
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


def derive_text_direction(iso15924_script: str) -> str | None:
    """Derive text reading direction from ISO 15924 script code.

    Returns:
        "ltr", "rtl", or None if script is unknown/unresolvable.
    """
    if not iso15924_script or iso15924_script == "Zyyy":
        return None
    return SCRIPT_TO_DIRECTION.get(iso15924_script, "ltr")


def derive_text_directions_present(
    primary_script: str,
    parser_languages: list[str] | None = None,
) -> list[str]:
    """Aggregate all text directions present in a sample.

    For COCO-Text images that may contain both English and non-English
    text instances, collects the unique set of text directions.

    Args:
        primary_script: The resolved iso15924_script for this sample.
        parser_languages: Optional list of COCO-Text language labels
            ("english", "not_english", "na") from parser raw_labels.

    Returns:
        Sorted list of unique directions (e.g., ["ltr"], ["ltr", "rtl"]).
    """
    directions: set[str] = set()

    # Primary script direction
    primary_dir = SCRIPT_TO_DIRECTION.get(primary_script)
    if primary_dir:
        directions.add(primary_dir)

    # COCO-Text language labels are too coarse for direction derivation:
    # "not_english" could be Arabic (rtl) or Chinese (ltr).
    # We can only reliably add directions from resolved script.
    # If we had per-instance LLM/VLM language ID, we could be more specific.

    return sorted(directions) if directions else []


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a COCO-Text sample.

    Priority chain (KI-009 mitigation):
      1. Parser GT "english" label -> en/Latn (confidence 0.90)
         Parser GT "not_english" -> check LLM/OpenLID for specifics
      2. LLM enrichment iso639_language (confidence 0.65)
      3. OpenLID language enrichment (confidence capped at 0.50 for
         scene text - KI-009: avg_confidence 0.437 in this dataset)
      4. Fallback to "und"

    COCO-Text language labels are coarse:
      - "english": Reliable -> en/Latn
      - "not_english": Unreliable -> need secondary source
      - "na": No text annotations -> fallback

    Args:
        sample: Full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).

    Returns:
        (iso639_language, iso15924_script, confidence, method)
    """
    original_labels = sample.get("original_labels", {})
    raw_labels = original_labels.get("raw_labels", {})
    parser_lang_code = original_labels.get("language_code", "")
    parser_languages = raw_labels.get("languages_present", [])

    # Source 1: Parser ground truth
    if parser_lang_code == "en":
        return ("en", "Latn", 0.90, "parser_gt")

    # For "not_english" or no parser label, try secondary sources
    # Source 2: LLM enrichment (text-only, 25.8% coverage)
    if llm:
        llm_lang = llm.get("iso639_language")
        if llm_lang and llm_lang != "und":
            llm_script = llm.get("iso15924_script") or "Zyyy"
            return (llm_lang, llm_script, 0.65, "llm_text")

    # Source 3: OpenLID (UNRELIABLE for scene text, cap at 0.50)
    # KI-009: avg_confidence=0.437, detects zh as dominant for English-majority
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        if le_lang and le_lang != "und":
            le_script = lang_enrichment.get("script") or "Zyyy"
            le_conf = lang_enrichment.get("confidence", 0.4)
            return (le_lang, le_script, min(le_conf, 0.50), "openlid_v2")

    # Source 4: Parser says "not_english" but no secondary source resolved
    if parser_lang_code == "und" or "not_english" in parser_languages:
        return ("und", "Zyyy", 0.40, "parser_gt_coarse")

    # Fallback: No text annotations or parser labels
    return ("und", "Zyyy", 0.10, "none")


# ---------------------------------------------------------------------------
# Per-sample integration
# ---------------------------------------------------------------------------
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[int, dict[str, Any]],
    lang_index: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single cocotext sample.

    Returns a new enrichment version data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # Get existing v1 data (if any)
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Source lookups: enrichments are keyed by COCO integer image_id,
    # not by filename_stem. Bridge via _extract_coco_image_id().
    coco_id = _extract_coco_image_id(filename_stem)
    llm = llm_index.get(coco_id) if coco_id is not None else None
    lang_enrichment = lang_index.get(coco_id) if coco_id is not None else None

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01 - split: from source.split (train/val/test)
    # -------------------------------------------------------------------
    data["split"] = sample["source"]["split"]

    # -------------------------------------------------------------------
    # D02 - capture_method: ALL camera_smartphone
    # MS COCO 2014 natural images captured by cameras
    # -------------------------------------------------------------------
    data["capture_method"] = "camera_smartphone"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D02 - domain_level1: VLM contact sheet override (2026-02-13)
    # All COCO-Text images are natural scene photographs (NOT documents).
    # Domain is SCN (scene) for all samples.
    # -------------------------------------------------------------------
    data["domain_level1"] = "SCN"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "vlm_contact_sheet"
    data["domain_content_type"] = llm.get("content_type", "") if llm else ""

    # -------------------------------------------------------------------
    # D07/D11 - Language & script: multi-source resolution (KI-009)
    # VLM override: default to en/Latn when no better source available
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment
    )
    if lang == "und" or lang_conf < 0.3:
        # Default to English (majority language in COCO scene text)
        data["iso639_language"] = "en"
        data["iso15924_script"] = "Latn"
        data["language_confidence"] = 0.7
        data["text_scope_detection_method"] = "vlm_contact_sheet_majority"
    else:
        data["iso639_language"] = lang
        data["iso15924_script"] = script
        data["language_confidence"] = lang_conf
        data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # D03 - script_family: derived from iso15924_script (KI-008)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # -------------------------------------------------------------------
    # D09 - Layout detections: preserve v1 if present (no new layout source)
    # COCO-Text has no Docling/DocLayout-YOLO extraction
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    data["layout_detections"] = v1_layout
    data["layout_source"] = v1_data.get("layout_source", "none")
    data["layout_confidence"] = v1_data.get("layout_confidence", 0.0)
    data["layout_detection_count"] = len(v1_layout)

    # -------------------------------------------------------------------
    # D10 - Content flags: from parser GT + layout + VLM overrides
    # Scene text: figures/tables/formulas extremely rare
    # -------------------------------------------------------------------
    original_labels = sample.get("original_labels", {})
    raw_labels = original_labels.get("raw_labels", {})

    # has_handwriting: PARSER ground truth (most reliable for this dataset)
    # COCO-Text annotates text_class="handwritten" per word instance
    parser_has_handwriting = raw_labels.get("has_handwriting", False)
    data["has_handwriting"] = parser_has_handwriting or (
        filename_stem in VLM_HANDWRITING_CORRECTIONS
    )

    # has_table/has_formula/has_figure: only VLM-confirmed true positives
    # Scene text images are photos - figures means embedded charts (not the photo)
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_signature"] = False
    data["has_code"] = False

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "parser_gt+vlm_corrected"
    data["content_flags_confidence"] = 0.90

    # D06 - handwriting_present: prescreening alias
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # D04 - orientation_class: default upright (no source available)
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
        data["text_scope_content_type"] = content_type or "scene_text"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "scene_text"
        )
    data["text_scope"] = v1_data.get("text_scope", "word")

    # -------------------------------------------------------------------
    # v2.3.0 - text_direction & text_directions_present
    # -------------------------------------------------------------------
    text_dir = derive_text_direction(script)
    if text_dir:
        data["text_direction"] = text_dir
        data["text_direction_confidence"] = lang_conf

    parser_languages = raw_labels.get("languages_present", [])
    dirs_present = derive_text_directions_present(script, parser_languages)
    if dirs_present:
        data["text_directions_present"] = dirs_present

    # -------------------------------------------------------------------
    # Text content from parser (word-level transcriptions)
    # Prescreening expects text_statistics.has_content (nested dict)
    # -------------------------------------------------------------------
    text_count = raw_labels.get("text_count", 0) or 0
    legible_count = raw_labels.get("legible_count", 0) or 0
    data["text_has_content"] = text_count > 0
    data["text_statistics"] = {
        "has_content": text_count > 0,
        "word_count": text_count,
        "legible_word_count": legible_count,
        "source": "parser_cocotext_v2",
    }

    # Resolution from v1 (if any)
    for field in (
        "resolution_category",
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # Additional derived fields
    # -------------------------------------------------------------------
    data["dataset_short_code"] = "cocotext"

    # Preserve v1 text quality fields
    for field in (
        "text_quality_confidence",
        "text_quality_is_soft_label",
        "text_quality_method",
        "text_quality_provenance_tier",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # Reliability summary
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
    llm_index: dict[int, dict[str, Any]],
    lang_index: dict[int, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    # Enrichment indices are keyed by COCO integer image_id
    coco_id = _extract_coco_image_id(filename_stem)
    if coco_id is not None and coco_id in llm_index:
        stats["llm_matched"] += 1
    if coco_id is not None and coco_id in lang_index:
        stats["lang_matched"] += 1
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

    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1

    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    # v2.3.0 tracking
    td = integrated_data.get("text_direction")
    if td:
        stats["text_direction_dist"][td] += 1
    else:
        stats["text_direction_dist"]["null"] += 1

    for d in integrated_data.get("text_directions_present", []):
        stats["text_directions_present_dist"][d] += 1


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
    llm_index: dict[int, dict[str, Any]],
    lang_index: dict[int, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "content_type_dist": Counter(),
        "text_direction_dist": Counter(),
        "text_directions_present_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
        "has_text_content_count": 0,
    }

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        integrated_data = integrate_sample(sample, llm_index, lang_index)

        _track_sample_stats(
            stats,
            filename_stem,
            integrated_data,
            llm_index,
            lang_index,
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_cocotext_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser GT (has_handwriting, split, text) + "
                    "LLM text enrichment + OpenLID language + "
                    "dataset documentation + "
                    "v2.3.0 text_direction/text_directions_present"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, ENRICHMENT_VERSION_NUMBER)

    return stats


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print("cocotext Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"Has text content:     {stats.get('has_text_content_count', 0)}")
    print()

    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:5d}")
    print()

    print("Language distribution (top 15):")
    for lang, count in stats["lang_dist"].most_common(15):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
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
    print()

    # v2.3.0 fields
    print("Text direction distribution (v2.3.0):")
    for td, count in stats["text_direction_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {td:20s}: {count:5d} ({pct:.1f}%)")

    print("Text directions present (aggregate):")
    for d, count in stats["text_directions_present_dist"].most_common():
        print(f"  {d:20s}: {count:5d}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into cocotext metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to cocotext_metadata.json (default: %(default)s)",
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
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    # Load all data sources
    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)

    # Run integration
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
