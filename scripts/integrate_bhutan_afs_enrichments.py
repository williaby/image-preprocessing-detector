#!/usr/bin/env python3
"""Integrate all enrichment sources into bhutan-afs Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

bhutan-afs specifics:
  - Born-digital government financial PDFs (135 pages)
  - Docling layout extraction (COCO format, 8 categories, 392 annotations)
  - Docling OCR extraction (JSONL, 135 records, 100% success)
  - No LLM enrichment, no language enrichment
  - BILINGUAL: Dzongkha/Tibetan (120 pages) + English (4 pages) + blank (1 page)
  - VLM Phase 6: 13 true figure positives, 14 false positives (KI-003)
  - capture_method override: born_digital (fixes BA-D01)
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_bhutan_afs_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "bhutan-afs"
__l4_workstream__ = "WS3"


import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import UTC, datetime
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
DATASET_NAME = "bhutan-afs"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "bhutan_financial_metadata.json"
# No LLM or language enrichment available for bhutan-afs
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "bhutan_financial_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "bhutan_financial_language_enrichment.json"
)

# Docling extracted data (COCO layout + OCR JSONL)
DOCLING_LAYOUT_PATH = REGISTRY_DIR / "extracted" / "bhutan-afs" / "layout_batch_0.json"
DOCLING_OCR_PATH = REGISTRY_DIR / "extracted" / "bhutan-afs" / "ocr_batch_0.jsonl"

SCRIPT_VERSION = "3.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v4"
ENRICHMENT_VERSION_NUMBER = 4

# Target schema version after integration
TARGET_SCHEMA_VERSION = "2.3.0"


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# Page stem appearing in multiple KI contexts (figure, Dzongkha, signature)
_AFS_PAGE_4 = "AFS_2024-25-2 4_p000"

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
APPLY_KI_001_LAYOUT_CASING = True


# --- KI-002: Table detection multi-column FP (HIGH) -----------------
# Populated after VLM Phase 6 inspection.
# All unlisted has_table=True samples are overridden to False.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Will be populated after VLM visual inspection (Phase 6)
    }
)

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
# VLM Phase 6 inspection: 13 true positives, 14 false positives
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Government seals/emblems (cover pages, letters)
        "AFS_2024-25-2 1_p000",
        "AFS_2024-25-2 2_p000",
        _AFS_PAGE_4,
        "AFS_2024-25-2 6_p000",
        "AFS_2024-25-2 14_p000",
        "Tax-Act-of-Bhutan-2021_1_p000",
        "Tax-Act-of-Bhutan-2021_3_p000",
        # Charts (pie, bar, donut)
        "AFS_2024-25-2 44_p000",
        "AFS_2024-25-2 45_p000",
        "AFS_2024-25-2 46_p000",
        "AFS_2024-25-2 51_p000",
        "AFS_2024-25-2 61_p000",
        "AFS_2024-25-2 62_p000",
    }
)

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# Not applicable: bhutan-afs is non-synthetic born-digital
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: Capture method override (HIGH) -------------------------
# BA-D01: Current metadata has scanner_flatbed, but these are born-digital
# government PDFs rendered at 299 DPI.
KNOWN_CAPTURE_METHOD: str | None = "born_digital"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- VLM Language Audit (2026-02-12): Corrected language classification ---
# Full VLM review of all 125 active pages revealed the ENTIRE AFS document
# (all 115 active pages) is in Dzongkha/Tibetan script. The original
# DZONGKHA_PAGE_STEMS (32 pages) only captured covers, chart labels, and
# rotated tables — missing that ALL financial tables/notes use Tibetan script
# with Arabic numerals. The Tax Act is bilingual (alternating eng/dzo pages).
#
# Corrected approach: default ALL pages to Dzongkha, list ONLY the English
# and blank exceptions. See: tmp_cleanup/.tmp-bhutan-afs-vlm-language-audit-20260212.md
#
# Previous (WRONG):  32 dzo (23.7%) / 103 eng (76.3%)
# Corrected:        120 dzo (96.0%) /   4 eng (3.2%) / 1 blank (0.8%)

ENGLISH_PAGE_STEMS: frozenset[str] = frozenset(
    {
        # Tax Act of Bhutan 2021 - English pages only
        "Tax-Act-of-Bhutan-2021_4_p000",  # Table of Contents (English)
        "Tax-Act-of-Bhutan-2021_6_p000",  # Preamble + Sections 1-4 (English)
        "Tax-Act-of-Bhutan-2021_8_p000",  # Schedule 1 - Revision of Sales Tax
        "Tax-Act-of-Bhutan-2021_10_p000",  # Schedule 1 continuation (English)
    }
)

BLANK_PAGE_STEMS: frozenset[str] = frozenset(
    {
        "Tax-Act-of-Bhutan-2021_2_p000",  # Empty page (registration marks only)
    }
)

# Kept for backwards compatibility / audit trail — do NOT use for classification
_LEGACY_DZONGKHA_PAGE_STEMS_V2: int = 32  # count from v2.0.0 (incorrect)

# --- VLM Discovery: Signature detection ------------------------------
SIGNATURE_PAGE_STEMS: frozenset[str] = frozenset(
    {
        _AFS_PAGE_4,  # Ministry of Finance formal letter
    }
)

# ===================================================================
# Content flag class mappings
# ===================================================================


# ===================================================================
# Data loaders
# ===================================================================
def load_docling_layout(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load Docling layout extraction (COCO format) and index by filename.

    bhutan-afs specific: COCO format with categories, images, annotations.
    Maps image_id -> file_name, then groups annotations by file_name.

    Args:
        path: Path to layout_batch_0.json.

    Returns:
        Dict mapping filename to list of annotation dicts.
    """
    if not path.exists():
        log.warning("Docling layout not found: %s", path)
        return {}
    log.info("Loading Docling layout (COCO) from %s", path)
    with open(path, encoding="utf-8") as f:
        coco: dict[str, Any] = json.load(f)

    # Build category id -> name mapping
    cat_map: dict[int, str] = {}
    for cat in coco.get("categories", []):
        cat_map[cat["id"]] = cat["name"]

    # Build image_id -> file_name mapping
    img_map: dict[int, str] = {}
    for img in coco.get("images", []):
        img_map[img["id"]] = img["file_name"]

    # Group annotations by filename
    index: dict[str, list[dict[str, Any]]] = {}
    for ann in coco.get("annotations", []):
        image_id = ann.get("image_id")
        filename = img_map.get(image_id, "")
        if not filename:
            continue
        category_name = cat_map.get(ann.get("category_id", -1), "unknown")
        det = {
            "class_name": category_name,
            "bbox": ann.get("bbox", []),
            "confidence": 1.0,  # Docling does not provide per-detection confidence
            "area": ann.get("area", 0.0),
        }
        index.setdefault(filename, []).append(det)

    log.info(
        "  Indexed %d images with %d total detections",
        len(index),
        sum(len(v) for v in index.values()),
    )
    return index


def load_docling_ocr(path: Path) -> dict[str, dict[str, Any]]:
    """Load Docling OCR extraction (JSONL) and index by filename.

    Each line is a JSON record with: source (GCS path), text,
    confidence, tables_found, processing_time_ms, success, error.

    Args:
        path: Path to ocr_batch_0.jsonl.

    Returns:
        Dict mapping filename to OCR record.
    """
    if not path.exists():
        log.warning("Docling OCR not found: %s", path)
        return {}
    log.info("Loading Docling OCR from %s", path)
    index: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec: dict[str, Any] = json.loads(line)
            if not rec.get("success"):
                continue
            # Extract filename from GCS path
            source = rec.get("source", "")
            filename = Path(source).name
            if filename:
                index[filename] = rec
    log.info("  Indexed %d OCR records", len(index))
    return index


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


def standardize_class_name(class_name: str) -> str:
    """Convert Docling lowercase class_name to DocLayNet PascalCase.

    Args:
        class_name: Raw class name from Docling layout output.

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
) -> tuple[str, str, float, str]:
    """Resolve language/script for bhutan-afs.

    bhutan-afs is PREDOMINANTLY Dzongkha: 120 pages (96%) Dzongkha,
    4 pages (3.2%) English, 1 blank. The entire AFS document (115 active
    pages) uses Tibetan script. The Tax Act alternates English/Dzongkha.

    Corrected 2026-02-12 via full VLM review of all 125 active pages.
    Previous classification (32 dzo / 103 eng) was catastrophically wrong —
    Arabic numerals in financial tables were misinterpreted as English.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record (None for bhutan-afs).
        lang_enrichment: Language enrichment record (None for bhutan-afs).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    # --- Source 4: Language enrichment / OpenLID --------------------
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        le_script = lang_enrichment.get("script")
        le_conf = lang_enrichment.get("confidence", 0.5)
        if le_lang and le_lang != "und":
            return (
                le_lang,
                le_script or "Latn",
                min(le_conf, 0.70),
                "openlid_v2",
            )

    # --- Source 5: LLM vision / text enrichment --------------------
    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return (llm_lang, llm_script or "Latn", 0.65, "llm_vision")

    # --- VLM full audit (2026-02-12): Exception-based classification ---
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # English exceptions: only 4 Tax Act pages
    if filename_stem in ENGLISH_PAGE_STEMS:
        return ("eng", "Latn", 0.95, "vlm_full_audit")

    # Blank page exception
    if filename_stem in BLANK_PAGE_STEMS:
        return ("und", "Zyyy", 0.95, "vlm_full_audit")

    # --- Default: Dzongkha (96% of dataset) -----------------------
    return ("dzo", "Tibt", 0.95, "vlm_full_audit")


def resolve_capture_method(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    is_synthetic: bool,
) -> tuple[str, float, str]:
    """Resolve capture method with KI-005 override.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record (None for bhutan-afs).
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


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive image color mode from original_file metadata.

    Args:
        original_file: The original_file dict from the sample.

    Returns:
        Color mode string: "color", "grayscale", or "binarized".
    """
    color_space = original_file.get("color_space", "")
    channels = original_file.get("channels", 0)

    if color_space in ("RGB", "RGBA", "CMYK") or channels >= 3:
        return "color"
    if color_space in ("L", "LA") or channels == 1:
        return "grayscale"
    return "color"  # default for unknown


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Merges all available enrichment sources into a single data dict
    that becomes the new enrichment version for this sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (empty for bhutan-afs).
        lang_index: Language enrichment index (empty for bhutan-afs).
        layout_index: Docling layout index (filename -> detections).
        ocr_index: Docling OCR index (filename -> OCR record).
        vlm_index: VLM enrichment index (optional, post Phase 6).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # Get existing enrichment data (latest version) for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Look up enrichment sources
    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    layout_dets = layout_index.get(filename, [])
    ocr_rec = ocr_index.get(filename)
    _vlm_rec = (vlm_index or {}).get(filename_stem)  # Reserved for VLM integration

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS (with KI-001 casing fix)
    # -------------------------------------------------------------------
    standardized_layout: list[dict[str, Any]] = []
    for det in layout_dets:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        canonical = standardize_class_name(original_class)
        new_det["class_name"] = canonical
        new_det["canonical_class"] = canonical.upper()
        new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (BA-D01 fix: born_digital)
    # -------------------------------------------------------------------
    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # -------------------------------------------------------------------
    # DOMAIN (from v1 enrichment - all FIN for bhutan-afs)
    # -------------------------------------------------------------------
    data["domain_level1"] = v1_data.get("domain_level1", "FIN")
    data["domain_confidence"] = 1.0  # Known from dataset documentation
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "financial_statement"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (dataset documentation: English/Latin)
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (derived from iso15924_script)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (with KI-002, KI-003, KI-006 overrides)
    # -------------------------------------------------------------------
    flags = derive_content_flags(standardized_layout)

    # KI-002: has_table -- only VLM-confirmed true positives
    if VLM_TABLE_TRUE_POSITIVES:
        data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES
    else:
        # Pre-VLM: use layout detection as baseline
        data["has_table"] = flags["has_table"]

    # KI-003: has_figure -- only VLM-confirmed true positives
    if VLM_FIGURE_TRUE_POSITIVES:
        data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    else:
        data["has_figure"] = flags["has_figure"]

    # KI-006: has_formula
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES

    # Born-digital: no handwriting (signatures detected by VLM)
    data["has_handwriting"] = False
    data["has_signature"] = filename_stem in SIGNATURE_PAGE_STEMS
    data["has_code"] = flags["has_code"]

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 0.85

    # Alias used by prescreening checks
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION (born-digital = always upright)
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # SPLIT (BA-D02 fix: single train split)
    # -------------------------------------------------------------------
    data["split"] = "train"

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = "financial_statement"
    data["text_scope"] = "printed"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES (BA-D13 fix: derive from original_file)
    # -------------------------------------------------------------------
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # -------------------------------------------------------------------
    # TEXT CONTENT (from Docling OCR)
    # -------------------------------------------------------------------
    if ocr_rec and ocr_rec.get("text"):
        ocr_text = ocr_rec["text"]
        data["text_has_content"] = True
        data["text_content_confidence"] = ocr_rec.get("confidence", 0.9)
        data["text_content_source"] = "docling_ocr"
        data["text_statistics"] = compute_text_statistics(ocr_text)
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # -------------------------------------------------------------------
    # TEXT DIRECTION (v2.3.0 fields - BA-D09, BA-D10)
    # -------------------------------------------------------------------
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # -------------------------------------------------------------------
    # RESOLUTION (preserve v1 data)
    # -------------------------------------------------------------------
    for field in (
        "resolution_category",
        "resolution_pixels",
        "resolution_dpi",
    ):
        if field in v1_data:
            data[field] = v1_data[field]
    # DPI is known from original_file
    if "resolution_dpi" not in data:
        data["resolution_dpi"] = original_file.get("dpi", 299)

    # -------------------------------------------------------------------
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last)
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _track_match_counts(
    stats: dict[str, Any],
    filename: str,
    filename_stem: str,
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None,
) -> None:
    """Increment source match counters for a single sample."""
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename_stem in lang_index:
        stats["lang_matched"] += 1
    if filename in layout_index:
        stats["layout_matched"] += 1
    if filename in ocr_index:
        stats["ocr_matched"] += 1
    if vlm_index and filename_stem in vlm_index:
        stats["vlm_matched"] += 1


def _track_distributions(
    stats: dict[str, Any],
    integrated_data: dict[str, Any],
) -> None:
    """Update distribution counters and content flag counts from integrated data."""
    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    _dist_fields = {
        "domain_dist": ("domain_level1", "UNK"),
        "split_dist": ("split", "unknown"),
        "lang_dist": ("iso639_language", "und"),
        "script_family_dist": ("script_family", "unknown"),
        "lang_method_dist": ("text_scope_detection_method", "unknown"),
        "capture_method_dist": ("capture_method", "unknown"),
        "content_type_dist": ("text_scope_content_type", "unknown"),
    }
    for stat_key, (data_key, default) in _dist_fields.items():
        stats[stat_key][integrated_data.get(data_key, default)] += 1

    _flag_fields = ["has_table", "has_formula", "has_handwriting", "has_figure"]
    for flag in _flag_fields:
        if integrated_data.get(flag):
            stats[f"{flag}_count"] += 1


def _write_enrichment_version(
    sample: dict[str, Any],
    integrated_data: dict[str, Any],
    now: str,
) -> None:
    """Write or replace the enrichment version on a sample (mutates sample)."""
    new_version = {
        "version": ENRICHMENT_VERSION_NUMBER,
        "created_at": now,
        "created_by": "integrate_bhutan_afs_enrichments.py",
        "method": "tier_2_model",
        "description": (
            f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
            "Docling layout + Docling OCR + VLM Phase 6 corrections "
            "(bilingual dzo+eng, figure FP fix, signature detection)"
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


def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index.
        lang_index: Language enrichment index.
        layout_index: Docling layout index.
        ocr_index: Docling OCR index.
        vlm_index: VLM enrichment index (optional).
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "vlm_matched": 0,
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

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        integrated_data = integrate_sample(
            sample,
            llm_index,
            lang_index,
            layout_index,
            ocr_index,
            vlm_index,
        )

        stats["integrated"] += 1
        _track_match_counts(
            stats,
            filename,
            filename_stem,
            llm_index,
            lang_index,
            layout_index,
            ocr_index,
            vlm_index,
        )
        _track_distributions(stats, integrated_data)

        if not dry_run:
            _write_enrichment_version(sample, integrated_data, now)

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
    print(f"Layout matched:       {stats['layout_matched']}")
    print(f"OCR matched:          {stats['ocr_matched']}")
    print(f"VLM matched:          {stats.get('vlm_matched', 0)}")
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

    print("Language distribution:")
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
        "--layout",
        type=Path,
        default=DOCLING_LAYOUT_PATH,
        help="Path to Docling layout JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--ocr",
        type=Path,
        default=DOCLING_OCR_PATH,
        help="Path to Docling OCR JSONL (default: %(default)s)",
    )
    parser.add_argument(
        "--vlm-enrichment",
        type=Path,
        default=None,
        help="Path to VLM enrichment JSON (optional, post Phase 6)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    # ----- Load all data sources -----
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)
    layout_index = load_docling_layout(args.layout)
    ocr_index = load_docling_ocr(args.ocr)

    vlm_index: dict[str, dict[str, Any]] | None = None
    if args.vlm_enrichment:
        vlm_index = load_vlm_enrichment(args.vlm_enrichment)

    # ----- Run integration -----
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        layout_index=layout_index,
        ocr_index=ocr_index,
        vlm_index=vlm_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    # ----- Update schema version (BA-D14 fix) -----
    if not args.dry_run:
        metadata["schema_version"] = TARGET_SCHEMA_VERSION
        metadata["splits_included"] = ["train"]

    # ----- Write output -----
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
