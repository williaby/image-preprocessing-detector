#!/usr/bin/env python3
"""Integrate all enrichment sources into {DATASET_NAME} Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

Customization guide:
  1. Replace all {FILL_IN} placeholders with dataset-specific values
  2. Enable/disable KI-NNN mitigation sections based on dataset characteristics
  3. Add dataset-specific enrichment source loaders
  4. Customize the resolve_* functions with appropriate priority chains
  5. Run with --dry-run first to verify before writing

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_{DATASET_NAME}_enrichments.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
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


# ===================================================================
# DATASET CONFIGURATION - Customize these for your dataset
# ===================================================================
# The canonical short name used in filenames, paths, and metadata.
# Must match the name in DATASET_NAMING_STANDARD.md.
DATASET_NAME = "{FILL_IN}"  # e.g., "diqa-5000", "jssoda", "mlt19"

# True for rendered/generated datasets (affects KI-004, KI-005).
# False for scanned, camera-captured, or born-digital datasets.
IS_SYNTHETIC_DATASET = False  # {FILL_IN}: True or False

# ===================================================================
# Paths - Uncomment and fill in the sources your dataset uses
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "{FILL_IN}_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "{FILL_IN}_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "{FILL_IN}_language_enrichment.json"

# Uncomment the enrichment sources that apply to your dataset:
# DOCLING_LAYOUT_PATH = REGISTRY_DIR / "enrichments" / "{FILL_IN}_docling_layout.json"
# DOCLING_OCR_PATH = REGISTRY_DIR / "enrichments" / "{FILL_IN}_docling_ocr.json"
# SKEW_LABELS_PATH = Path("results/{FILL_IN}_skew_labels.json")
# RESOLUTION_LABELS_PATH = Path("results/{FILL_IN}_resolution_labels.json")
# VLM_ENRICHMENT_PATH = Path("scripts/audit/results/{FILL_IN}/vlm_test_enrichments.json")
# TRAIN_GT_PATH = Path("{FILL_IN}")  # Dataset-specific GT annotation path

# VLM text transcription labels (Phase 6.5 conditional text labeling)
# Uncomment if text_has_content < 50% at prescreening
# VLM_TEXT_LABELS_PATH = Path("results/{FILL_IN}_text_labels.json")

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

# Full Docling lowercase -> DocLayNet PascalCase mapping.
# Covers core 11 DocLayNet classes plus Docling extensions.
DOCLING_TO_DOCLAYNET: dict[str, str] = {
    "text": "Text",
    "list_item": "List-Item",
    "section_header": "Section-Header",
    "table": "Table",
    "picture": "Picture",
    "formula": "Formula",
    "caption": "Caption",
    "footnote": "Footnote",
    "page_footer": "Page-Footer",
    "page_header": "Page-Header",
    "title": "Title",
    "code": "Code",
    "checkbox_selected": "Checkbox-Selected",
    "checkbox_unselected": "Checkbox-Unselected",
}

# If using DocLayout-YOLO (docstructbench) instead of Docling,
# uncomment this mapping and set APPLY_KI_001_LAYOUT_CASING = False:
# DOCLAYOUT_YOLO_TO_DOCLAYNET: dict[str, str] = {
#     "figure": "Picture",
#     "title": "Title",
#     "plain text": "Text",
#     "abandon": "Text",
#     "figure_caption": "Caption",
#     "table": "Table",
#     "table_caption": "Caption",
#     "table_footnote": "Footnote",
#     "isolate_formula": "Formula",
#     "formula_caption": "Caption",
# }

# --- KI-002: Table detection multi-column FP (HIGH) -----------------
# Docling/DocLayout-YOLO classifies multi-column text as Table.
# List sample IDs (filename stems) where VLM confirmed REAL tables.
# All unlisted has_table=True samples are overridden to False.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # "{FILL_IN}",  # description of confirmed table
    }
)

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
# Docling classifies dense text blocks or dark backgrounds as Picture.
# List sample IDs where VLM confirmed REAL figures/pictures.
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # "{FILL_IN}",  # description of confirmed figure
    }
)

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# Auto-applied when IS_SYNTHETIC_DATASET=True: override
# has_handwriting=False for all samples (LLM cannot distinguish
# rendered text from handwriting on synthetic images).
# For non-synthetic datasets, list VLM-confirmed handwriting samples:
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # "{FILL_IN}",  # description of confirmed handwriting
    }
)

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# Auto-applied when IS_SYNTHETIC_DATASET=True: override
# capture_method from dataset documentation.
# For non-synthetic datasets, set to the known capture method or
# leave as None to use LLM detection.
KNOWN_CAPTURE_METHOD: str | None = (
    None  # {FILL_IN}: e.g., "synthetic", "camera_smartphone", "scanner_flatbed", "born_digital"
)

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
# LLM flags text *discussing* math/science as has_formula even when
# no rendered equations exist. List VLM-confirmed true positives:
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # "{FILL_IN}",  # description of confirmed formula
    }
)

# ===================================================================
# Content flag class mappings (canonical layout -> content flags)
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


# ===================================================================
# Data loaders
#
# Each loader handles missing files gracefully (log warning, return
# empty dict). All loaders index by filename stem (image_id) unless
# noted otherwise.
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the dataset's *_metadata.json file.

    Returns:
        Full metadata dict with "samples" list.

    Raises:
        FileNotFoundError: If the metadata file does not exist.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    Expected JSON structure: {"samples": [{"image_id": "...", ...}]}

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping image_id (filename stem) to enrichment record.
    """
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
    """Load language enrichment (OpenLID) and index by image_id.

    Expected JSON structure: {"samples": [{"image_id": "...", ...}]}

    Args:
        path: Path to *_language_enrichment.json.

    Returns:
        Dict mapping image_id to language enrichment record.
    """
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


def load_skew_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load skew/orientation labels and index by filename.

    Expected JSON structure from label_skew_orientation.py:
      {"results": [{"image_path": "...", ...}], "metadata": {...}}

    Note: Indexed by full filename (with extension), not stem.

    Args:
        path: Path to *_skew_labels.json.

    Returns:
        Dict mapping filename to skew/orientation measurement.
    """
    if not path.exists():
        log.warning("Skew labels not found: %s", path)
        return {}
    log.info("Loading skew labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    results = raw.get("results", [])
    index: dict[str, dict[str, Any]] = {}
    for rec in results:
        if rec.get("error"):
            continue
        image_path = rec.get("image_path", "")
        filename = Path(image_path).name
        if filename:
            index[filename] = rec
    log.info("  Indexed %d skew records", len(index))
    return index


def load_resolution_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load resolution quality labels and index by filename.

    Expected JSON structure from label_resolution_quality.py:
      {"results": [{"image_path": "...", ...}], "metadata": {...}}

    Args:
        path: Path to *_resolution_labels.json.

    Returns:
        Dict mapping filename to resolution quality measurement.
    """
    if not path.exists():
        log.warning("Resolution labels not found: %s", path)
        return {}
    log.info("Loading resolution labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    results = raw.get("results", [])
    index: dict[str, dict[str, Any]] = {}
    for rec in results:
        if rec.get("error"):
            continue
        image_path = rec.get("image_path", "")
        filename = Path(image_path).name
        if filename:
            index[filename] = rec
    log.info("  Indexed %d resolution records", len(index))
    return index


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

    {FILL_IN}: Customize this loader for your dataset's GT format.
    This is a placeholder -- the JSON structure, key names, and
    indexing strategy will vary per dataset.

    Common patterns:
      - COCO-style: {"images": [...], "annotations": [...]}
      - Simple list: {"samples": [{"image_id": "...", ...}]}
      - Manifest: {"split": [...]}

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

    # {FILL_IN}: Customize indexing for your GT format.
    # Example for samples-list format:
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


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Counts characters, words, lines, and script-specific characters.
    Includes Devanagari, CJK, and Arabic character detection patterns.
    {FILL_IN}: Add or remove script patterns based on dataset language.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content,
        and avg_line_length. Script-specific counts included when
        non-zero.
    """
    if not text or text.strip() == "":
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_content": False,
        }

    clean_text = text.strip()
    lines = clean_text.split("\n")
    non_empty_lines = [ln for ln in lines if ln.strip()]
    words = clean_text.split()

    # Script-specific character patterns
    # {FILL_IN}: Uncomment/add patterns for your dataset's script(s)
    deva_chars = len(re.findall(r"[\u0900-\u097f]", clean_text))
    # {FILL_IN}: Add CJK character counting for range U+4E00-U+9FFF, U+3400-U+4DBF
    # {FILL_IN}: Add Arabic character counting for range U+0600-U+06FF
    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))

    avg_line_len = 0.0
    if non_empty_lines:
        avg_line_len = round(
            sum(len(ln.strip()) for ln in non_empty_lines) / len(non_empty_lines),
            1,
        )

    stats: dict[str, Any] = {
        "char_count": len(clean_text),
        "word_count": len(words),
        "line_count": len(non_empty_lines),
        "has_content": True,
        "avg_line_length": avg_line_len,
    }

    # Only include script-specific counts if non-zero
    if deva_chars > 0:
        stats["devanagari_char_count"] = deva_chars
    if latin_words > 0:
        stats["latin_word_count"] = latin_words

    return stats


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Scans all layout detections and checks canonical_class against
    known class sets for table, formula, figure, and code.

    Args:
        detections: List of layout detection dicts, each containing
            at minimum a "canonical_class" key.

    Returns:
        Dict with boolean flags: has_table, has_formula, has_figure,
        has_code.
    """
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
    """Compute sample_reliability_summary for an enrichment data dict.

    Assesses five field groups (capture, domain, language, layout,
    content_flags) and produces a reliability tier for each based on
    confidence thresholds:
      >= 0.9 -> hard_label
      >= 0.7 -> soft_label
      >= 0.5 -> active_learning
      <  0.5 -> unreliable

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Dict with min_confidence, min_confidence_field,
        min_confidence_category, field counts, field_summary list,
        and computed_at timestamp.
    """
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
    # If using DocLayout-YOLO mapping, uncomment and use:
    # return DOCLAYOUT_YOLO_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def _try_parser_gt_language(
    sample: dict[str, Any],
) -> tuple[str, str, float, str] | None:
    """Attempt to resolve language from parser ground truth (confidence 0.95)."""
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if not parser_lang or parser_lang == "und":
        return None
    parser_script = original_labels.get("iso15924_script_code", "") or "Zyyy"
    return (parser_lang, parser_script, 0.95, "parser_gt")


def _try_train_gt_language(
    train_gt: dict[str, Any] | None,
) -> tuple[str, str, float, str] | None:
    """Attempt to resolve language from train GT file (confidence 0.90)."""
    if not train_gt:
        return None
    gt_lang = train_gt.get("iso639_language")
    if not gt_lang or gt_lang == "und":
        return None
    gt_script = train_gt.get("iso15924_script")
    gt_conf = train_gt.get("language_confidence", 0.90)
    return (gt_lang, gt_script or "Zyyy", gt_conf, "train_gt")


def _try_vlm_language(
    vlm: dict[str, Any] | None,
) -> tuple[str, str, float, str] | None:
    """Attempt to resolve language from VLM contact sheet (confidence 0.75)."""
    if not vlm:
        return None
    vlm_lang = vlm.get("iso639_language")
    if not vlm_lang or vlm_lang == "und":
        return None
    vlm_script = vlm.get("iso15924_script")
    vlm_conf = vlm.get("language_confidence", 0.75)
    return (vlm_lang, vlm_script or "Zyyy", vlm_conf, "vlm_contact_sheet")


def _try_openlid_language(
    lang_enrichment: dict[str, Any] | None,
) -> tuple[str, str, float, str] | None:
    """Attempt to resolve language from OpenLID (confidence capped at 0.70)."""
    if not lang_enrichment:
        return None
    le_lang = lang_enrichment.get("language")
    if not le_lang or le_lang == "und":
        return None
    le_script = lang_enrichment.get("script")
    le_conf = lang_enrichment.get("confidence", 0.5)
    return (le_lang, le_script or "Zyyy", min(le_conf, 0.70), "openlid_v2")


def _try_llm_language(
    llm: dict[str, Any] | None,
) -> tuple[str, str, float, str] | None:
    """Attempt to resolve language from LLM vision (confidence 0.65)."""
    if not llm:
        return None
    llm_lang = llm.get("iso639_language")
    if not llm_lang or llm_lang == "und":
        return None
    llm_script = llm.get("iso15924_script")
    return (llm_lang, llm_script or "Zyyy", 0.65, "llm_vision")


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
      6. Dataset documentation fallback (confidence varies)

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
    # Try sources in priority order; first non-None result wins.
    resolvers = [
        _try_parser_gt_language(sample),
        _try_train_gt_language(train_gt),
        _try_vlm_language(vlm),
        _try_openlid_language(lang_enrichment),
        _try_llm_language(llm),
    ]
    for result in resolvers:
        if result is not None:
            return result

    # {FILL_IN}: Dataset documentation fallback.
    # Example: return ("ja", "Jpan", 1.0, "dataset_documentation")
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


def _integrate_layout(
    v1_data: dict[str, Any],
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Standardize layout detections (KI-001) and populate data dict.

    Returns the standardized layout list for downstream use.
    """
    v1_layout = v1_data.get("layout_detections", [])
    standardized: list[dict[str, Any]] = []
    for det in v1_layout:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized.append(new_det)

    data["layout_detections"] = standardized
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized)
    return standardized


def _integrate_domain(
    llm: dict[str, Any] | None,
    v1_data: dict[str, Any],
    data: dict[str, Any],
) -> None:
    """Populate domain fields from LLM enrichment or v1 fallback."""
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
        data["domain_detection_method"] = v1_data.get("domain_detection_method", "none")


def _integrate_content_flags(
    filename_stem: str,
    standardized_layout: list[dict[str, Any]],
    data: dict[str, Any],
) -> None:
    """Populate content flags with KI-002 through KI-006 overrides."""
    flags = derive_content_flags(standardized_layout)

    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = (
        False
        if IS_SYNTHETIC_DATASET
        else filename_stem in VLM_HANDWRITING_TRUE_POSITIVES
    )
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "vlm_corrected+docling_gpu+llm_vision"
    data["content_flags_confidence"] = 0.95
    data["handwriting_present"] = data["has_handwriting"]


def _integrate_orientation(
    skew_rec: dict[str, Any] | None,
    llm: dict[str, Any] | None,
    data: dict[str, Any],
) -> None:
    """Populate orientation fields from skew pipeline, LLM, or default."""
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


def _integrate_resolution(
    resolution_rec: dict[str, Any] | None,
    v1_data: dict[str, Any],
    data: dict[str, Any],
) -> None:
    """Populate resolution quality fields from pipeline or v1 fallback."""
    if resolution_rec:
        data["resolution_quality_score"] = resolution_rec.get("quality_score")
        data["resolution_quality_bucket"] = resolution_rec.get("bucket")
        data["resolution_char_height_px"] = resolution_rec.get("median_char_height_px")
        data["resolution_detection_method"] = resolution_rec.get(
            "method", "paddleocr_cc_v1"
        )
        return

    for field_name in (
        "resolution_category",
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field_name in v1_data:
            data[field_name] = v1_data[field_name]


def _integrate_text_content(
    text_label: dict[str, Any] | None,
    data: dict[str, Any],
) -> None:
    """Populate text content fields from VLM text labels or defaults."""
    if text_label and text_label.get("transcription"):
        transcription = text_label["transcription"]
        data["text_has_content"] = True
        data["text_content"] = transcription
        data["text_content_confidence"] = text_label.get("confidence", 0.8)
        data["text_content_source"] = "vlm_manual_transcription"
        data["text_statistics"] = compute_text_statistics(transcription)
    else:
        data["text_has_content"] = False
        data["text_content"] = ""
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")


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

    standardized_layout = _integrate_layout(v1_data, data)

    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    _integrate_domain(llm, v1_data, data)

    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_rec, train_gt
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method
    data["script_family"] = _get_script_family(script)

    _integrate_content_flags(filename_stem, standardized_layout, data)
    _integrate_orientation(skew_rec, llm, data)

    if skew_rec:
        data["skew_angle_degrees"] = skew_rec.get("skew_angle_degrees")
        data["skew_confidence"] = skew_rec.get("skew_bin_confidence")
        data["skew_detection_method"] = "mobilenetv4_skew_estimator_v1"

    data["split"] = sample.get("source", {}).get("split", "unknown")

    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type or "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )

    data["text_scope"] = v1_data.get("text_scope", "printed")
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    _integrate_resolution(resolution_rec, v1_data, data)
    _integrate_text_content(text_label, data)

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _init_stats() -> dict[str, Any]:
    """Create an empty statistics dict for run_integration."""
    return {
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


def _track_source_matches(
    stats: dict[str, Any],
    filename_stem: str,
    filename_full: str,
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None,
    train_gt_index: dict[str, dict[str, Any]] | None,
    skew_index: dict[str, dict[str, Any]] | None,
    resolution_index: dict[str, dict[str, Any]] | None,
    text_labels_index: dict[str, dict[str, Any]] | None,
) -> None:
    """Increment source-match counters in stats dict."""
    source_checks: list[tuple[str, dict[str, Any] | None, str]] = [
        ("llm_matched", llm_index, filename_stem),
        ("lang_matched", lang_index, filename_stem),
        ("vlm_matched", vlm_index, filename_stem),
        ("train_gt_matched", train_gt_index, filename_stem),
        ("skew_matched", skew_index, filename_full),
        ("resolution_matched", resolution_index, filename_full),
        ("text_labels_matched", text_labels_index, filename_stem),
    ]
    for stat_key, index, key in source_checks:
        if index and key in index:
            stats[stat_key] += 1


def _track_distributions(
    stats: dict[str, Any],
    integrated_data: dict[str, Any],
) -> None:
    """Update distribution counters and content flag counts."""
    dist_fields: list[tuple[str, str, str]] = [
        ("domain_dist", "domain_level1", "UNK"),
        ("split_dist", "split", "unknown"),
        ("lang_dist", "iso639_language", "und"),
        ("script_family_dist", "script_family", "unknown"),
        ("lang_method_dist", "text_scope_detection_method", "unknown"),
        ("capture_method_dist", "capture_method", "unknown"),
        ("content_type_dist", "text_scope_content_type", "unknown"),
    ]
    for counter_key, data_key, default in dist_fields:
        stats[counter_key][integrated_data.get(data_key, default)] += 1

    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    flag_keys: list[tuple[str, str]] = [
        ("has_table_count", "has_table"),
        ("has_formula_count", "has_formula"),
        ("has_handwriting_count", "has_handwriting"),
        ("has_figure_count", "has_figure"),
    ]
    for stat_key, data_key in flag_keys:
        if integrated_data.get(data_key):
            stats[stat_key] += 1


def _write_enrichment_version(
    sample: dict[str, Any],
    integrated_data: dict[str, Any],
    now: str,
) -> None:
    """Write (or replace) an enrichment version into sample."""
    new_version = {
        "version": ENRICHMENT_VERSION_NUMBER,
        "created_at": now,
        "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
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
    for i, ver in enumerate(versions):
        if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER


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
    stats = _init_stats()
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

        stats["integrated"] += 1
        _track_source_matches(
            stats,
            filename_stem,
            filename_full,
            llm_index,
            lang_index,
            vlm_index,
            train_gt_index,
            skew_index,
            resolution_index,
            text_labels_index,
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
