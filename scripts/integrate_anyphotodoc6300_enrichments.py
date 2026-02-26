#!/usr/bin/env python3
"""Integrate all enrichment sources into anyphotodoc6300 Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

anyphotodoc6300 specifics:
  - Camera-captured document dewarping dataset (6,300 images)
  - 8 categories: bill, book, complex, education, invoice, magazine,
    single_column, two_column
  - Distortion variants: init_1 through init_8, flat/ is ground truth
  - Paired: distorted camera captures + flat GT scans
  - LLM + language enrichment available
  - capture_method override: camera_smartphone (all camera-captured)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_anyphotodoc6300_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "anyphotodoc6300"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/correction/anyphotodoc6300.py"
)


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
DATASET_NAME = "anyphotodoc6300"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "anyphotodoc6300_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "anyphotodoc6300_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "anyphotodoc6300_language_enrichment.json"
)

# Uncomment the enrichment sources that apply to your dataset:
# DOCLING_LAYOUT_PATH = REGISTRY_DIR / "enrichments" / "anyphotodoc6300_docling_layout.json"
# DOCLING_OCR_PATH = REGISTRY_DIR / "enrichments" / "anyphotodoc6300_docling_ocr.json"
# SKEW_LABELS_PATH = Path("results/anyphotodoc6300_skew_labels.json")
# RESOLUTION_LABELS_PATH = Path("results/anyphotodoc6300_resolution_labels.json")
# VLM_ENRICHMENT_PATH = Path("scripts/audit/results/anyphotodoc6300/vlm_test_enrichments.json")
# TRAIN_GT_PATH = Path("...")  # Dataset-specific GT annotation path

# VLM text transcription labels (Phase 6.5 conditional text labeling)
# Uncomment if text_has_content < 50% at prescreening
# VLM_TEXT_LABELS_PATH = Path("results/anyphotodoc6300_text_labels.json")

SCRIPT_VERSION = "4.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v5"

# The enrichment version number written into each sample.
# Use 2 for first integration, 3 for re-integration, etc.
ENRICHMENT_VERSION_NUMBER = 5


# ===================================================================
# GROUND TRUTH METADATA FROM BENCHMARK.md (DvD paper)
#
# Filename convention: {layout_cat}_{warp_pattern}_{lighting}_{doc_id}_{angle}.ext
#
# Position 1 = Layout Category (= init directory number)
# Position 2 = Warping Pattern (1-3; only 1 for bound books)
# Position 3 = Environment Lighting (1-3)
# Position 4 = Document Instance ID
# Position 5 = Shooting Angle Variant (1-2)
# ===================================================================

# Layout category mapping: init directory number -> (document_type, domain_level1)
# domain_level1 uses 3-letter schema codes: FIN, EDU, UNK, etc.
LAYOUT_CATEGORY_MAP: dict[int, tuple[str, str]] = {
    1: ("single_column", "SCI"),  # Scientific papers (VLM: all 6 were academic)
    2: ("complex_layout", "UNK"),  # Mixed content: news, magazines, lifestyle
    3: ("invoice", "FIN"),  # Financial invoices
    4: ("education", "EDU"),  # Educational materials
    5: ("book", "TEC"),  # Chinese tech books + CCF journal articles
    6: ("two_column", "SCI"),  # Scientific papers (VLM: all 6 were academic)
    7: ("magazine", "UNK"),  # Advertisements and magazine articles
    8: ("bill", "FIN"),  # Financial receipts, bills, tickets
}

WARPING_PATTERN_MAP: dict[int, str] = {
    1: "crumple",
    2: "curve",
    3: "fold",
}

LIGHTING_CONDITION_MAP: dict[int, str] = {
    1: "dim",
    2: "daylight",
    3: "indoor",
}


def parse_filename_metadata(filename: str) -> dict[str, Any]:
    """Extract GT metadata from AnyPhotoDoc6300 filename convention.

    Parses the 5-position naming convention defined in DvD BENCHMARK.md:
    {layout_cat}_{warp_pattern}_{lighting}_{doc_id}_{angle}.ext

    Args:
        filename: Original filename (e.g. "1_2_3_42_1.JPG").

    Returns:
        Dict with document_type, domain_level1, warping_pattern,
        lighting_condition, document_instance_id, shooting_angle,
        and init_group. Empty dict if filename doesn't match pattern.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) != 5:
        return {}

    try:
        layout_cat = int(parts[0])
        warp_num = int(parts[1])
        light_num = int(parts[2])
        doc_id = int(parts[3])
        angle = int(parts[4])
    except ValueError:
        return {}

    cat_info = LAYOUT_CATEGORY_MAP.get(layout_cat)
    if not cat_info:
        return {}

    document_type, domain = cat_info

    return {
        "init_group": layout_cat,
        "document_type": document_type,
        "domain_level1": domain,
        "warping_pattern": WARPING_PATTERN_MAP.get(warp_num, f"unknown_{warp_num}"),
        "warping_pattern_id": warp_num,
        "lighting_condition": LIGHTING_CONDITION_MAP.get(
            light_num, f"unknown_{light_num}"
        ),
        "lighting_condition_id": light_num,
        "document_instance_id": doc_id,
        "shooting_angle": angle,
    }


def assign_split(layout_cat: int, doc_id: int) -> str:
    """Assign train/val/test split by document instance to prevent leakage.

    All captures of the same physical document (same layout_cat + doc_id)
    are assigned to the same split. This prevents different warping/lighting/
    angle variants of the same document from appearing in different splits.

    Split boundaries per layout category (approximately 70/15/15):
      - Categories 1-4,6,7 have 50 docs each:
        train=1-35, val=36-42, test=43-50
      - Category 5 (book) has 100 docs:
        train=1-70, val=71-85, test=86-100
      - Category 8 (bill) has 51 docs:
        train=1-36, val=37-43, test=44-51

    Args:
        layout_cat: Layout category number (1-8).
        doc_id: Document instance ID.

    Returns:
        Split name: "train", "val", or "test".
    """
    if layout_cat == 5:
        # Book: 100 docs -> 70/15/15
        if doc_id <= 70:
            return "train"
        if doc_id <= 85:
            return "val"
        return "test"
    if layout_cat == 8:
        # Bill: 51 docs -> 36/7/8
        if doc_id <= 36:
            return "train"
        if doc_id <= 43:
            return "val"
        return "test"
    # All other categories: 50 docs -> 35/7/8
    if doc_id <= 35:
        return "train"
    if doc_id <= 42:
        return "val"
    return "test"


def get_per_doc_language(layout_cat: int, doc_id: int) -> tuple[str, str] | None:
    """Per-document language+script from VLM classification of 200 unique documents.

    Returns (iso639_language, iso15924_script) or None if no per-doc mapping exists.
    Covers mixed-language categories: init_1, init_2, init_6, init_7.
    Monolingual categories (init_3-5, init_8) use category-level assignment.
    """
    if layout_cat == 1:  # single_column: en bioprinting + zh cognitive modeling
        if 1 <= doc_id <= 28:
            return ("en", "Latn")
        if 29 <= doc_id <= 50:
            return ("zh", "Hans")
    elif layout_cat == 2:  # complex_layout: en news/lifestyle + zh-Hant/ja tech
        if 1 <= doc_id <= 32:
            return ("en", "Latn")
        if 33 <= doc_id <= 41:
            return ("zh", "Hant")
        if 42 <= doc_id <= 50:
            return ("ja", "Jpan")
    elif layout_cat == 6:  # two_column: en/zh academic papers
        if 1 <= doc_id <= 28:
            return ("en", "Latn")
        if 29 <= doc_id <= 36:
            return ("zh", "Hans")
        if doc_id == 37:
            return ("en", "Latn")
        if 38 <= doc_id <= 46:
            return ("zh", "Hans")
        if 47 <= doc_id <= 50:
            return ("en", "Latn")
    elif layout_cat == 7:  # magazine: en/de/zh mixed publications
        if 1 <= doc_id <= 17:
            return ("en", "Latn")
        if 18 <= doc_id <= 29:
            return ("de", "Latn")
        if 30 <= doc_id <= 33:
            return ("en", "Latn")
        if doc_id == 34:
            return ("de", "Latn")
        if 35 <= doc_id <= 37:
            return ("en", "Latn")
        if 38 <= doc_id <= 50:
            return ("zh", "Hans")
    return None


def get_per_doc_domain(layout_cat: int, doc_id: int) -> str | None:
    """Per-document domain from VLM classification (only where non-UNK).

    Returns DomainLevel1 code or None if category default should apply.
    Only overrides UNK categories where tech/science content was identified.
    """
    if layout_cat == 2:  # complex_layout: docs 33-50 are tech magazines
        if 33 <= doc_id <= 50:
            return "TEC"
    elif layout_cat == 7:  # magazine: docs 1-10 are C++/Python coding manual
        if 1 <= doc_id <= 10:
            return "TEC"
    return None


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
# Docling/DocLayout-YOLO classifies multi-column text as Table.
# List sample IDs (filename stems) where VLM confirmed REAL tables.
# All unlisted has_table=True samples are overridden to False.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
# Docling classifies dense text blocks or dark backgrounds as Picture.
# List sample IDs where VLM confirmed REAL figures/pictures.
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# Not applicable: anyphotodoc6300 is non-synthetic camera-captured.
# For non-synthetic datasets, list VLM-confirmed handwriting samples:
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# Camera-captured document dataset - override from documentation.
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
# LLM flags text *discussing* math/science as has_formula even when
# no rendered equations exist. List VLM-confirmed true positives:
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populate after VLM Phase 6 inspection
    }
)

# ===================================================================
# VLM CATEGORY-LEVEL CONTENT FLAGS AND LANGUAGE
#
# Derived from stratified VLM inspection of 48 images (6 per category)
# using Claude Opus 4.6 vision (2026-02-13). Content flags are set True
# when observed prevalence >= 50% in the 6-sample stratum.
#
# Language assigned only for categories with clear single-language
# dominance (>= 83% of samples). Mixed-language categories use None
# (fall through to existing language resolution chain).
# ===================================================================
VLM_CATEGORY_CONTENT_FLAGS: dict[int, dict[str, bool]] = {
    1: {  # single_column: scientific papers
        "has_figure": False,  # 33% observed
        "has_table": False,  # 0% observed
        "has_formula": True,  # 50% observed
        "has_handwriting": False,
        "has_signature": False,
    },
    2: {  # complex_layout: magazines, news
        "has_figure": True,  # 100% observed
        "has_table": False,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    3: {  # invoice: financial invoices
        "has_figure": False,
        "has_table": True,  # 100% observed
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,  # 33% observed (below threshold)
    },
    4: {  # education: exams, handwritten notes
        "has_figure": True,  # 50% observed
        "has_table": False,  # 33% observed
        "has_formula": True,  # 67% observed
        "has_handwriting": True,  # 67% observed
        "has_signature": False,
    },
    5: {  # book: Chinese tech books, CCF journals
        "has_figure": True,  # 100% observed
        "has_table": False,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    6: {  # two_column: scientific papers
        "has_figure": False,  # 17% observed
        "has_table": False,
        "has_formula": True,  # 67% observed
        "has_handwriting": False,
        "has_signature": False,
    },
    7: {  # magazine: advertisements, articles
        "has_figure": True,  # 100% observed
        "has_table": False,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    8: {  # bill: receipts, tickets
        "has_figure": False,
        "has_table": True,  # 67% observed
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
}

# Language assignment for clear single-language categories.
# None means mixed/multilingual - fall through to existing resolution.
VLM_CATEGORY_LANGUAGE: dict[int, str | None] = {
    1: None,  # Mixed en/zh scientific papers
    2: None,  # Mixed en/zh-Hant/ja
    3: "en",  # Predominantly English invoices
    4: "zh",  # Predominantly Chinese education
    5: "zh",  # All Chinese books/journals
    6: None,  # Mixed en/zh scientific papers
    7: None,  # Mixed zh/en/de
    8: "zh",  # All Chinese receipts/bills
}

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

    Expected JSON structure:
      {"samples": {"image_stem": {...}, ...}}

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
    # VLM enrichments are typically pre-indexed by image stem
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d VLM records", len(index))
    return index


def load_train_gt(path: Path) -> dict[str, dict[str, Any]]:
    """Load dataset-specific ground truth annotations.

    anyphotodoc6300: GT is the flat/ directory with undistorted versions.
    This loader handles any supplementary GT annotation file.

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

    Used by Phase 6.5 conditional text labeling when text_has_content
    pass rate is below 50%. Labels are manually transcribed VLM outputs.

    Expected JSON structure:
      {"labels": [{"image_id": "train/1", "transcription": "...", ...}]}

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
        # image_id may be "train/1" or just "1" - extract final component
        stem = image_id.split("/")[-1] if "/" in image_id else image_id
        if stem:
            index[stem] = rec
    log.info("  Indexed %d VLM text label records", len(index))
    return index


def standardize_class_name(class_name: str) -> str:
    """Convert layout extractor class_name to DocLayNet PascalCase.

    Uses DOCLING_TO_DOCLAYNET mapping by default (KI-001).
    Passes through unmapped names unchanged.

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

    Six-level priority chain (highest to lowest confidence):

      1. Parser GT (confidence 0.95)
      2. Train GT file (confidence 0.90)
      3. VLM contact sheet (confidence 0.75)
      4. Language enrichment / OpenLID (confidence 0.70)
      5. LLM vision (confidence 0.65)
      6. Dataset documentation fallback

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
    # --- Source 1: Parser ground truth (highest confidence) ----------
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if parser_lang and parser_lang not in ("", "und"):
        parser_script = original_labels.get("iso15924_script_code", "")
        if not parser_script:
            parser_script = "Zyyy"
        return (parser_lang, parser_script, 0.95, "parser_gt")

    # --- Source 2: Train GT file (high confidence) -------------------
    if train_gt:
        gt_lang = train_gt.get("iso639_language")
        gt_script = train_gt.get("iso15924_script")
        if gt_lang and gt_lang != "und":
            gt_conf = train_gt.get("language_confidence", 0.90)
            return (gt_lang, gt_script or "Zyyy", gt_conf, "train_gt")

    # --- Source 3: VLM contact sheet (good confidence) ---------------
    if vlm:
        vlm_lang = vlm.get("iso639_language")
        vlm_script = vlm.get("iso15924_script")
        if vlm_lang and vlm_lang != "und":
            vlm_conf = vlm.get("language_confidence", 0.75)
            return (vlm_lang, vlm_script or "Zyyy", vlm_conf, "vlm_contact_sheet")

    # --- Source 4: Language enrichment / OpenLID --------------------
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

    # --- Source 5: LLM vision / text enrichment --------------------
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

    # --- Source 6: Dataset documentation fallback -------------------
    # anyphotodoc6300 is a multilingual dataset; no single default language
    return ("und", "Zyyy", 0.1, "none")


def resolve_capture_method(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    is_synthetic: bool,
) -> tuple[str, float, str]:
    """Resolve capture method with KI-005 synthetic override.

    For synthetic datasets, LLM misclassifies as born_digital or
    scanner_flatbed (KI-005). Always override from documentation.

    For non-synthetic datasets, use KNOWN_CAPTURE_METHOD if set,
    otherwise fall back to LLM enrichment.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        is_synthetic: Whether this is a synthetic dataset.

    Returns:
        Tuple of (capture_method, confidence, detection_method).
    """
    # KI-005: Synthetic override
    if is_synthetic:
        return ("synthetic", 1.0, "dataset_documentation")

    # Known capture method from documentation
    if KNOWN_CAPTURE_METHOD:
        return (KNOWN_CAPTURE_METHOD, 1.0, "dataset_documentation")

    # LLM enrichment
    if llm:
        method = llm.get("capture_method", "unknown")
        conf = llm.get("capture_confidence", 0.5)
        return (method, conf, "llm_vision")

    # Fallback
    return ("unknown", 0.3, "none")


# ===================================================================
# Per-sample integration
#
# This is the main function to customize per dataset. Each labeled
# section corresponds to a field group in the enrichment schema.
# Enable/disable sections and adjust logic as needed.
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

    Merges all available enrichment sources into a single data dict
    that becomes the new enrichment version for this sample.

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

    # Parse GT metadata from filename convention (DvD BENCHMARK.md)
    gt_meta = parse_filename_metadata(filename_full)

    # Get existing enrichment data (latest version) for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Look up all enrichment sources for this sample
    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    skew_rec = (skew_index or {}).get(filename_full)
    resolution_rec = (resolution_index or {}).get(filename_full)
    vlm_rec = (vlm_index or {}).get(filename_stem)
    train_gt = (train_gt_index or {}).get(filename_stem)
    text_label = (text_labels_index or {}).get(filename_stem)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS (with KI-001 casing fix)
    #
    # Standardizes class_name from layout extractor output to DocLayNet
    # PascalCase. Preserves original label in source_label field.
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout: list[dict[str, Any]] = []
    for det in v1_layout:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        # Preserve original label for traceability
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (with KI-005 override: camera_smartphone)
    # -------------------------------------------------------------------
    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # -------------------------------------------------------------------
    # DOMAIN (from GT filename convention)
    #
    # DvD BENCHMARK.md maps layout categories to document types which
    # map to domain_level1. This is ground truth from the dataset
    # authors, so confidence is 1.0.
    # Falls back to LLM or v1 data if filename parse fails.
    # -------------------------------------------------------------------
    if gt_meta and gt_meta.get("domain_level1"):
        data["domain_level1"] = gt_meta["domain_level1"]
        data["domain_confidence"] = 1.0
        data["domain_detection_method"] = "filename_gt"
        data["domain_content_type"] = gt_meta.get("document_type", "")
    elif llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
        data["domain_detection_method"] = v1_data.get("domain_detection_method", "none")

    # -------------------------------------------------------------------
    # VLM CATEGORY + DOC ID (used by language, domain, and content flags)
    # -------------------------------------------------------------------
    layout_cat = gt_meta.get("init_group") if gt_meta else None
    doc_id = gt_meta.get("document_instance_id") if gt_meta else None

    # -------------------------------------------------------------------
    # PER-DOCUMENT DOMAIN OVERRIDE (VLM classification of 200 docs)
    #
    # For mixed categories (init_2, init_7) where GT domain is UNK,
    # use per-document VLM classification to assign specific domains
    # (currently only TEC where tech/science content was identified).
    # -------------------------------------------------------------------
    if (
        data.get("domain_level1") == "UNK"
        and layout_cat is not None
        and doc_id is not None
    ):
        per_doc_domain = get_per_doc_domain(layout_cat, doc_id)
        if per_doc_domain:
            data["domain_level1"] = per_doc_domain
            data["domain_confidence"] = 0.90
            data["domain_detection_method"] = "vlm_per_document"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (from priority chain + VLM per-doc/category fallback)
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_rec, train_gt
    )

    # Per-document VLM language override: if standard chain returned "und"
    # and we have per-document classification from VLM inspection of 200
    # unique documents across mixed-language categories.
    if lang == "und" and layout_cat is not None and doc_id is not None:
        per_doc_lang = get_per_doc_language(layout_cat, doc_id)
        if per_doc_lang:
            lang, script = per_doc_lang
            lang_conf = 0.85
            lang_method = "vlm_per_document"

    # VLM category-level language fallback: if per-doc didn't resolve
    # (e.g. monolingual categories not in per-doc map), try category level.
    if lang == "und" and layout_cat is not None:
        vlm_cat_lang = VLM_CATEGORY_LANGUAGE.get(layout_cat)
        if vlm_cat_lang:
            lang = vlm_cat_lang
            script = "Hans" if vlm_cat_lang == "zh" else "Latn"
            lang_conf = 0.70
            lang_method = "vlm_category_inspection"

    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (derived from iso15924_script)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (VLM category-level enrichment)
    #
    # Uses category-level content flag assignments derived from
    # stratified VLM inspection of 48 images (6 per category).
    # Flags set True when observed prevalence >= 50% in stratum.
    # Falls back to layout-derived flags if no GT category available.
    # -------------------------------------------------------------------
    vlm_cat_flags = VLM_CATEGORY_CONTENT_FLAGS.get(layout_cat) if layout_cat else None

    if vlm_cat_flags:
        data["has_figure"] = vlm_cat_flags["has_figure"]
        data["has_table"] = vlm_cat_flags["has_table"]
        data["has_formula"] = vlm_cat_flags["has_formula"]
        data["has_handwriting"] = vlm_cat_flags["has_handwriting"]
        data["has_signature"] = vlm_cat_flags["has_signature"]
        data["has_code"] = False
        data["content_flags_tier"] = "tier_2_model"
        data["content_flags_source"] = "vlm_category_inspection_48_samples"
        data["content_flags_confidence"] = 0.80
    else:
        flags = derive_content_flags(standardized_layout)
        data["has_figure"] = flags["has_figure"]
        data["has_table"] = flags["has_table"]
        data["has_formula"] = flags["has_formula"]
        data["has_handwriting"] = flags["has_handwriting"]
        data["has_signature"] = False
        data["has_code"] = flags["has_code"]
        data["content_flags_tier"] = "tier_3_heuristic"
        data["content_flags_source"] = "layout_derived_fallback"
        data["content_flags_confidence"] = 0.5

    # Alias used by prescreening checks
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION (from skew/orientation pipeline if available)
    #
    # Priority:
    #   1. Skew estimator pipeline (MobileNetV4, MAE=0.956)
    #   2. LLM enrichment orientation (lower confidence)
    #   3. Default upright (0 degrees, low confidence)
    # -------------------------------------------------------------------
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

    # -------------------------------------------------------------------
    # SKEW (from skew/orientation pipeline)
    # -------------------------------------------------------------------
    if skew_rec:
        data["skew_angle_degrees"] = skew_rec.get("skew_angle_degrees")
        data["skew_confidence"] = skew_rec.get("skew_bin_confidence")
        data["skew_detection_method"] = "mobilenetv4_skew_estimator_v1"
    # If no skew data, fields are simply omitted (not set to defaults)

    # -------------------------------------------------------------------
    # SPLIT (document-instance-based assignment from GT filename)
    #
    # Uses layout_cat + doc_id to assign splits deterministically.
    # All captures of the same physical document (same layout_cat +
    # doc_id) go to the same split to prevent data leakage.
    # Approximately 70/15/15 train/val/test.
    # -------------------------------------------------------------------
    if gt_meta and gt_meta.get("init_group") and gt_meta.get("document_instance_id"):
        data["split"] = assign_split(
            gt_meta["init_group"], gt_meta["document_instance_id"]
        )
    else:
        data["split"] = sample.get("source", {}).get("split", "unknown")

    # -------------------------------------------------------------------
    # TEXT SCOPE (from LLM content_type)
    # -------------------------------------------------------------------
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )

    # Full-page document images (camera-captured documents)
    data["text_scope"] = "page"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # -------------------------------------------------------------------
    # RESOLUTION QUALITY (if available)
    # -------------------------------------------------------------------
    if resolution_rec:
        data["resolution_quality_score"] = resolution_rec.get("quality_score")
        data["resolution_quality_bucket"] = resolution_rec.get("bucket")
        data["resolution_char_height_px"] = resolution_rec.get("median_char_height_px")
        data["resolution_detection_method"] = resolution_rec.get(
            "method", "paddleocr_cc_v1"
        )
    else:
        # Preserve v1 resolution fields if they exist
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
    # TEXT CONTENT (Phase 6.5: VLM text labeling)
    #
    # Populated when VLM text transcription labels are available.
    # Only a subset of samples will have transcriptions (typically
    # max(ceil(1% of dataset), 10) samples at >75% confidence).
    # -------------------------------------------------------------------
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

    # -------------------------------------------------------------------
    # STRUCTURED GT METADATA (from DvD filename convention)
    #
    # These fields capture the experimental design variables that the
    # dataset authors encoded in the filename: document type, warping
    # pattern, lighting condition, and shooting angle variant.
    # -------------------------------------------------------------------
    if gt_meta:
        data["gt_document_type"] = gt_meta.get("document_type", "")
        data["gt_warping_pattern"] = gt_meta.get("warping_pattern", "")
        data["gt_warping_pattern_id"] = gt_meta.get("warping_pattern_id")
        data["gt_lighting_condition"] = gt_meta.get("lighting_condition", "")
        data["gt_lighting_condition_id"] = gt_meta.get("lighting_condition_id")
        data["gt_document_instance_id"] = gt_meta.get("document_instance_id")
        data["gt_shooting_angle"] = gt_meta.get("shooting_angle")
        data["gt_init_group"] = gt_meta.get("init_group")

    # -------------------------------------------------------------------
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last -- uses confidence fields above)
    # -------------------------------------------------------------------
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

    Iterates over every sample in metadata, calls integrate_sample(),
    tracks statistics, and (unless dry_run) writes a new enrichment
    version into each sample.

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

    now = datetime.now(UTC).isoformat()

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

        # ----- Track statistics -----
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

        # ----- Write enrichment version -----
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
            # Replace existing version if present, otherwise append
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

    Shows match rates, domain/split/language/capture distributions,
    and content flag counts.

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
        help=("Path to language enrichment JSON (default: %(default)s)"),
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

    # ----- Run integration -----
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
