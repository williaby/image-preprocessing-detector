#!/usr/bin/env python3
"""Integrate all enrichment sources into warpdoc Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

warpdoc specifics:
  - Document dewarping dataset with 6 distortion types:
    curved, fold, incomplete, perspective, random, rotate
  - Three categories: image/ (camera-captured), digital/ (GT),
    digital_margin/ (GT with margins)
  - Paired: distorted camera captures + digital GT
  - LLM + language enrichment available
  - capture_method override: camera_smartphone (all camera-captured)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_warpdoc_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "warpdoc"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/correction/warpdoc.py"
)


import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

from l2_integration_utils import (
    compute_reliability_summary,
    compute_text_statistics,
    derive_content_flags,
    load_language_enrichment,
    load_llm_enrichment,
    load_metadata,
    load_resolution_labels,
    load_skew_labels,
    DOCLING_TO_DOCLAYNET,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "warpdoc"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "warpdoc_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "warpdoc_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "warpdoc_language_enrichment.json"

# Uncomment the enrichment sources that apply to your dataset:
# DOCLING_LAYOUT_PATH = REGISTRY_DIR / "enrichments" / "warpdoc_docling_layout.json"
# DOCLING_OCR_PATH = REGISTRY_DIR / "enrichments" / "warpdoc_docling_ocr.json"
# SKEW_LABELS_PATH = Path("results/warpdoc_skew_labels.json")
# RESOLUTION_LABELS_PATH = Path("results/warpdoc_resolution_labels.json")
# VLM_ENRICHMENT_PATH = Path("scripts/audit/results/warpdoc/vlm_test_enrichments.json")
# TRAIN_GT_PATH = Path("...")  # Dataset-specific GT annotation path

# VLM text transcription labels (Phase 6.5 conditional text labeling)
# Uncomment if text_has_content < 50% at prescreening
# VLM_TEXT_LABELS_PATH = Path("results/warpdoc_text_labels.json")

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"

# The enrichment version number written into each sample.
# Use 2 for first integration, 3 for re-integration, etc.
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
#
# Toggle each based on applicability.
# See scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json for
# full descriptions, evidence, and remediation guidance.
#
# Pre-flight checklist:
#   [ ] Read CROSS_DATASET_KNOWN_ISSUES.json
#   [ ] Determine capture_method from dataset documentation
#   [ ] Run standardize_layout_labels.py BEFORE this script (KI-001)
#   [ ] VLM-inspect flagged content-flag samples (KI-002..KI-006)
#   [ ] Document VLM corrections in vlm_corrections.json
# ===================================================================

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
# Set True if dataset has Docling layout extraction (lowercase labels).
# If False, layout labels are assumed already in PascalCase.
APPLY_KI_001_LAYOUT_CASING = True


# --- KI-002: Table detection multi-column FP (HIGH) -----------------
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# Not applicable: warpdoc is non-synthetic camera-captured.
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# Camera-captured document dataset - override from documentation.
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# ===================================================================
# Content flag class mappings (canonical layout -> content flags)
# ===================================================================


# ===================================================================
# Data loaders
#
# Each loader handles missing files gracefully (log warning, return
# empty dict). All loaders index by filename stem (image_id) unless
# noted otherwise.
# ===================================================================
def load_vlm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM enrichment and index by image stem.

    Args:
        path: Path to VLM enrichment JSON.

    Returns:
        Dict mapping image stem to VLM enrichment record.
    """
    if not path.exists():
        log.warning("VLM enrichment not found: %s", path)
        return {}
    log.info("Loading VLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d VLM records", len(index))
    return index


def load_train_gt(path: Path) -> dict[str, dict[str, Any]]:
    """Load dataset-specific ground truth annotations.

    warpdoc: GT is the digital/ and digital_margin/ directories.

    Args:
        path: Path to ground truth annotation file.

    Returns:
        Dict mapping image identifier to GT record.
    """
    if not path.exists():
        log.warning("Train GT not found: %s", path)
        return {}
    log.info("Loading train GT from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d train GT records", len(index))
    return index


def load_vlm_text_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM text transcription labels and index by filename stem.

    Args:
        path: Path to VLM text labels JSON.

    Returns:
        Dict mapping filename stem to label record.
    """
    if not path.exists():
        log.warning("VLM text labels not found: %s", path)
        return {}
    log.info("Loading VLM text labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("labels", []):
        image_id = rec.get("image_id", "")
        stem = image_id.split("/")[-1] if "/" in image_id else image_id
        if stem:
            index[stem] = rec
    log.info("  Indexed %d VLM text label records", len(index))
    return index


def standardize_class_name(class_name: str) -> str:
    """Convert layout extractor class_name to DocLayNet PascalCase.

    Args:
        class_name: Raw class name from layout extractor output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
    vlm: dict[str, Any] | None = None,
    train_gt: dict[str, Any] | None = None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a sample using priority chain.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).
        vlm: VLM enrichment record (or None).
        train_gt: Train GT enrichment record (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if parser_lang and parser_lang not in ("", "und"):
        parser_script = original_labels.get("iso15924_script_code", "")
        if not parser_script:
            parser_script = "Zyyy"
        return (parser_lang, parser_script, 0.95, "parser_gt")

    if train_gt:
        gt_lang = train_gt.get("iso639_language")
        gt_script = train_gt.get("iso15924_script")
        if gt_lang and gt_lang != "und":
            gt_conf = train_gt.get("language_confidence", 0.90)
            return (gt_lang, gt_script or "Zyyy", gt_conf, "train_gt")

    if vlm:
        vlm_lang = vlm.get("iso639_language")
        vlm_script = vlm.get("iso15924_script")
        if vlm_lang and vlm_lang != "und":
            vlm_conf = vlm.get("language_confidence", 0.75)
            return (vlm_lang, vlm_script or "Zyyy", vlm_conf, "vlm_contact_sheet")

    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        le_script = lang_enrichment.get("script")
        le_conf = lang_enrichment.get("confidence", 0.5)
        if le_lang and le_lang != "und":
            return (
                le_lang,
                le_script or "Zyyy",
                min(le_conf, 0.70),
                "openlid_v2",
            )

    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return (
                llm_lang,
                llm_script or "Zyyy",
                0.65,
                "llm_vision",
            )

    # warpdoc is a multilingual dataset; no single default language
    return ("und", "Zyyy", 0.1, "none")


def resolve_capture_method(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    is_synthetic: bool,
) -> tuple[str, float, str]:
    """Resolve capture method with KI-005 synthetic override.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        is_synthetic: Whether this is a synthetic dataset.

    Returns:
        Tuple of (capture_method, confidence, detection_method).
    """
    if is_synthetic:
        return ("synthetic", 1.0, "dataset_documentation")

    if KNOWN_CAPTURE_METHOD:
        return (KNOWN_CAPTURE_METHOD, 1.0, "dataset_documentation")

    if llm:
        method = llm.get("capture_method", "unknown")
        conf = llm.get("capture_confidence", 0.5)
        return (method, conf, "llm_vision")

    return ("unknown", 0.3, "none")


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    skew_index: dict[str, dict[str, Any]] | None = None,
    resolution_index: dict[str, dict[str, Any]] | None = None,
    vlm_index: dict[str, dict[str, Any]] | None = None,
    train_gt_index: dict[str, dict[str, Any]] | None = None,
    text_labels_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (image_id -> record).
        lang_index: Language enrichment index (image_id -> record).
        skew_index: Skew/orientation index (filename -> record).
        resolution_index: Resolution quality index (filename -> record).
        vlm_index: VLM enrichment index (image_stem -> record).
        train_gt_index: Train GT index (image_id -> record).
        text_labels_index: VLM text transcription index (stem -> record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    filename_full = Path(filename).name

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    skew_rec = (skew_index or {}).get(filename_full)
    resolution_rec = (resolution_index or {}).get(filename_full)
    vlm_rec = (vlm_index or {}).get(filename_stem)
    train_gt = (train_gt_index or {}).get(filename_stem)
    text_label = (text_labels_index or {}).get(filename_stem)

    data: dict[str, Any] = {}

    # LAYOUT DETECTIONS
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
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # CAPTURE METHOD
    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # DOMAIN - VLM contact sheet override (2026-02-13): all warpdoc images
    # are camera-captured English printed documents (papers, articles, etc.)
    data["domain_level1"] = "GENERAL"
    data["domain_confidence"] = 0.85
    data["domain_detection_method"] = "vlm_contact_sheet"
    data["domain_content_type"] = llm.get("content_type", "") if llm else ""

    # LANGUAGE / SCRIPT - VLM contact sheet override: 100% English
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_rec, train_gt
    )
    # Override: all warpdoc documents are English (confirmed via contact sheet)
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 0.85
    data["text_scope_detection_method"] = "vlm_contact_sheet"

    data["script_family"] = _get_script_family(data["iso15924_script"])

    # CONTENT FLAGS
    flags = derive_content_flags(standardized_layout)

    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = filename_stem in VLM_HANDWRITING_TRUE_POSITIVES

    data["has_signature"] = False
    data["has_code"] = flags["has_code"]

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "vlm_corrected+docling_gpu+llm_vision"
    data["content_flags_confidence"] = 0.95

    data["handwriting_present"] = data["has_handwriting"]

    # ORIENTATION
    if skew_rec:
        data["orientation_class"] = skew_rec.get("orientation_class", 0)
        data["orientation_confidence"] = skew_rec.get("orientation_confidence", 0.9)
        data["orientation_detection_method"] = "mobilenetv4_skew_estimator_v1"
    elif llm and llm.get("orientation") is not None:
        data["orientation_class"] = llm.get("orientation", 0)
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "llm_vision"
    else:
        data["orientation_class"] = 0
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "default_upright"

    # SKEW
    if skew_rec:
        data["skew_angle_degrees"] = skew_rec.get("skew_angle_degrees")
        data["skew_confidence"] = skew_rec.get("skew_bin_confidence")
        data["skew_detection_method"] = "mobilenetv4_skew_estimator_v1"

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "unknown")

    # TEXT SCOPE
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )

    data["text_scope"] = "page"

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # RESOLUTION QUALITY
    if resolution_rec:
        data["resolution_quality_score"] = resolution_rec.get("quality_score")
        data["resolution_quality_bucket"] = resolution_rec.get("bucket")
        data["resolution_char_height_px"] = resolution_rec.get("median_char_height_px")
        data["resolution_detection_method"] = resolution_rec.get(
            "method", "paddleocr_cc_v1"
        )
    else:
        for field in (
            "resolution_category",
            "resolution_pixels",
            "resolution_quality_score",
            "resolution_quality_bucket",
            "resolution_char_height_px",
        ):
            if field in v1_data:
                data[field] = v1_data[field]

    # TEXT CONTENT
    if text_label and text_label.get("transcription"):
        transcription = text_label["transcription"]
        confidence = text_label.get("confidence", 0.8)
        data["text_has_content"] = True
        data["text_content"] = transcription
        data["text_content_confidence"] = confidence
        data["text_content_source"] = "vlm_manual_transcription"
        data["text_statistics"] = compute_text_statistics(transcription)
    else:
        data["text_has_content"] = False
        data["text_content"] = ""
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # ADDITIONAL DERIVED FIELDS
    data["dataset_short_code"] = DATASET_NAME

    # RELIABILITY SUMMARY
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    skew_index: dict[str, dict[str, Any]] | None = None,
    resolution_index: dict[str, dict[str, Any]] | None = None,
    vlm_index: dict[str, dict[str, Any]] | None = None,
    train_gt_index: dict[str, dict[str, Any]] | None = None,
    text_labels_index: dict[str, dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index.
        lang_index: Language enrichment index.
        skew_index: Skew/orientation index (optional).
        resolution_index: Resolution quality index (optional).
        vlm_index: VLM enrichment index (optional).
        train_gt_index: Train GT enrichment index (optional).
        text_labels_index: VLM text transcription index (optional).
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "vlm_matched": 0,
        "train_gt_matched": 0,
        "skew_matched": 0,
        "resolution_matched": 0,
        "text_labels_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "capture_method_dist": Counter(),
        "content_type_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }

    now = datetime.now(timezone.utc).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem
        filename_full = Path(filename).name

        integrated_data = integrate_sample(
            sample,
            llm_index,
            lang_index,
            skew_index,
            resolution_index,
            vlm_index,
            train_gt_index,
            text_labels_index,
        )

        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1
        if vlm_index and filename_stem in vlm_index:
            stats["vlm_matched"] += 1
        if train_gt_index and filename_stem in train_gt_index:
            stats["train_gt_matched"] += 1
        if skew_index and filename_full in skew_index:
            stats["skew_matched"] += 1
        if resolution_index and filename_full in resolution_index:
            stats["resolution_matched"] += 1
        if text_labels_index and filename_stem in text_labels_index:
            stats["text_labels_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["lang_method_dist"][
            integrated_data.get("text_scope_detection_method", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        stats["content_type_dist"][
            integrated_data.get("text_scope_content_type", "unknown")
        ] += 1

        if integrated_data.get("has_table"):
            stats["has_table_count"] += 1
        if integrated_data.get("has_formula"):
            stats["has_formula_count"] += 1
        if integrated_data.get("has_handwriting"):
            stats["has_handwriting_count"] += 1
        if integrated_data.get("has_figure"):
            stats["has_figure_count"] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": (f"integrate_{DATASET_NAME}_enrichments.py"),
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + layout + language enrichment + "
                    "dataset documentation"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            versions = sample["enrichments"]["versions"]
            replaced = False
            for i, ver in enumerate(versions):
                if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[i] = new_version
                    replaced = True
                    break
            if not replaced:
                versions.append(new_version)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary with distributions.

    Args:
        stats: Stats dict returned by run_integration().
        total_samples: Total number of samples in the metadata.
    """
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"VLM matched:          {stats.get('vlm_matched', 0)}")
    print(f"Train GT matched:     {stats.get('train_gt_matched', 0)}")
    print(f"Skew matched:         {stats.get('skew_matched', 0)}")
    print(f"Resolution matched:   {stats.get('resolution_matched', 0)}")
    print(f"Text labels matched:  {stats.get('text_labels_matched', 0)}")
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

    print("Capture method distribution:")
    for cm, count in stats["capture_method_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
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


# ===================================================================
# CLI
# ===================================================================
def main() -> int:
    """Entry point with argument parsing.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description=(f"Integrate all enrichment sources into {DATASET_NAME} metadata."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to dataset metadata JSON (default: %(default)s)",
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
        "--skew-labels",
        type=Path,
        default=None,
        help="Path to skew/orientation labels JSON (optional)",
    )
    parser.add_argument(
        "--resolution-labels",
        type=Path,
        default=None,
        help="Path to resolution quality labels JSON (optional)",
    )
    parser.add_argument(
        "--vlm-enrichment",
        type=Path,
        default=None,
        help="Path to VLM enrichment JSON (optional)",
    )
    parser.add_argument(
        "--train-gt",
        type=Path,
        default=None,
        help="Path to train GT enrichment JSON (optional)",
    )
    parser.add_argument(
        "--vlm-text-labels",
        type=Path,
        default=None,
        help="Path to VLM text transcription labels JSON (Phase 6.5, optional)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only, do not write output"
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)

    skew_index: dict[str, dict[str, Any]] | None = None
    if args.skew_labels:
        skew_index = load_skew_labels(args.skew_labels)

    resolution_index: dict[str, dict[str, Any]] | None = None
    if args.resolution_labels:
        resolution_index = load_resolution_labels(args.resolution_labels)

    vlm_index: dict[str, dict[str, Any]] | None = None
    if args.vlm_enrichment:
        vlm_index = load_vlm_enrichment(args.vlm_enrichment)

    train_gt_index: dict[str, dict[str, Any]] | None = None
    if args.train_gt:
        train_gt_index = load_train_gt(args.train_gt)

    text_labels_index: dict[str, dict[str, Any]] | None = None
    if args.vlm_text_labels:
        text_labels_index = load_vlm_text_labels(args.vlm_text_labels)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        skew_index=skew_index,
        resolution_index=resolution_index,
        vlm_index=vlm_index,
        train_gt_index=train_gt_index,
        text_labels_index=text_labels_index,
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
    sys.exit(main())
