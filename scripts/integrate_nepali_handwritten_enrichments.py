#!/usr/bin/env python3
"""Integrate all enrichment sources into nepali-handwritten Layer 2 metadata.

Merges 3 data sources into the main metadata JSON for all 958 records:
  1. Language enrichment (Nepali/Deva): language_code, script_code, confidence
  2. Docling layout (5 batches): layout_detections, content_flags derivation
  3. VLM text labels (10 samples): text_content, text_statistics

Also applies:
  - Layout label PascalCase conversion (KI-001): docling lowercase -> DocLayNet
  - Script family derivation (KI-008): Deva -> "indic"
  - Hardcoded known values: capture_method=camera_smartphone, language=ne,
    script=Deva, has_handwriting=True (all samples)
  - v2.3.0 fields: text_direction=ltr, text_directions_present=[ltr]
  - Reliability summary recomputation

Creates a new enrichment version (v4) in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_nepali_handwritten_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "nepali-handwritten"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/multilingual/nepali_handwritten.py"


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
DATASET_NAME = "nepali-handwritten"

# False: camera-captured handwriting dataset.
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths - Uncomment and fill in the sources your dataset uses
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "nepali_handwritten_metadata.json"
# No LLM enrichment available for this dataset
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "nepali_handwritten_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "nepali_handwritten_language_enrichment.json"
)

SCRIPT_VERSION = "1.2.0"
ENRICHMENT_VERSION_TAG = "integrated_v3_vlm_text_labels"

# The enrichment version number written into each sample.
# Use 2 for first integration, 3 for re-integration, etc.
ENRICHMENT_VERSION_NUMBER = 4

# VLM text labels from manual transcription
VLM_TEXT_LABELS_PATH = Path(
    "/home/byron/dev/image_detection/results/nepali_handwritten_text_labels.json"
)


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
        "207",  # Handwritten table with grid lines and rows/columns
    }
)

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
# Docling classifies dense text blocks or dark backgrounds as Picture.
# List sample IDs where VLM confirmed REAL figures/pictures.
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        "437",  # Hand-drawn advertisement poster with decorative borders
    }
)

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# N/A for nepali-handwritten (IS_SYNTHETIC_DATASET=False).
# ALL samples are handwritten by dataset definition - override
# in integrate_sample() instead of using this set.
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Not used -- has_handwriting=True for ALL samples (ground truth)
    }
)

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# Auto-applied when IS_SYNTHETIC_DATASET=True: override
# capture_method from dataset documentation.
# For non-synthetic datasets, set to the known capture method or
# leave as None to use LLM detection.
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
# LLM flags text *discussing* math/science as has_formula even when
# no rendered equations exist. List VLM-confirmed true positives:
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        # Populated after VLM inspection Phase 5
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


def load_vlm_text_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM text transcription labels and index by filename stem.

    Expected JSON structure (from nepali_handwritten_text_labels.json):
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
        # image_id is like "train/1" - extract stem
        stem = image_id.split("/")[-1] if "/" in image_id else image_id
        if stem:
            index[stem] = rec
    log.info("  Indexed %d VLM text label records", len(index))
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, devanagari_char_count,
        latin_word_count, has_content, and avg_line_length.
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

    # Detect Devanagari characters (primary script for this dataset)
    deva_pattern = re.compile(r"[\u0900-\u097f]")
    deva_chars = len(deva_pattern.findall(clean_text))
    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))

    avg_line_len = 0.0
    if non_empty_lines:
        avg_line_len = round(
            sum(len(ln) for ln in non_empty_lines) / len(non_empty_lines),
            1,
        )

    return {
        "char_count": len(clean_text),
        "word_count": len(words),
        "line_count": len(non_empty_lines),
        "devanagari_char_count": deva_chars,
        "latin_word_count": latin_words,
        "has_content": len(clean_text) > 0,
        "avg_line_length": avg_line_len,
    }


def load_train_gt(path: Path) -> dict[str, dict[str, Any]]:
    """Load dataset-specific ground truth annotations.

    nepali-handwritten uses PASCAL VOC XML annotations with bounding
    boxes. No separate GT enrichment file is available -- ground truth
    overrides are applied directly in integrate_sample().

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
      6. Dataset documentation fallback (confidence 1.0)

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
    # Source 1: Parser ground truth (highest confidence)
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if parser_lang and parser_lang not in ("", "und"):
        parser_script = original_labels.get("iso15924_script_code", "") or "Deva"
        return (parser_lang, parser_script, 0.95, "parser_gt")

    # Sources 2-5: enrichment records via priority chain
    sources = [
        (
            train_gt,
            "iso639_language",
            "iso15924_script",
            0.90,
            "train_gt",
            {"conf_key": "language_confidence"},
        ),
        (
            vlm,
            "iso639_language",
            "iso15924_script",
            0.75,
            "vlm_contact_sheet",
            {"conf_key": "language_confidence"},
        ),
        (
            lang_enrichment,
            "language",
            "script",
            0.5,
            "openlid_v2",
            {"conf_key": "confidence", "cap_conf": 0.70},
        ),
        (llm, "iso639_language", "iso15924_script", 0.65, "llm_vision", {}),
    ]
    for record, lang_key, script_key, default_conf, method, kwargs in sources:
        result = _resolve_from_enrichment_record(
            record,
            lang_key,
            script_key,
            default_conf,
            method,
            **kwargs,
        )
        if result:
            return result

    # Source 6: Dataset documentation fallback
    return ("ne", "Deva", 1.0, "dataset_documentation")


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
def _standardize_layout_detections(
    detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Standardize class_name to PascalCase and preserve source_label."""
    result: list[dict[str, Any]] = []
    for det in detections:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        result.append(new_det)
    return result


def _resolve_nepali_orientation(
    skew_rec: dict[str, Any] | None,
    llm: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve orientation fields from skew pipeline or LLM."""
    if skew_rec:
        return {
            "orientation_class": skew_rec.get("orientation_class", 0),
            "orientation_confidence": skew_rec.get("orientation_confidence", 0.9),
            "orientation_detection_method": "mobilenetv4_skew_estimator_v1",
        }
    if llm and llm.get("orientation") is not None:
        return {
            "orientation_class": llm.get("orientation", 0),
            "orientation_confidence": 0.5,
            "orientation_detection_method": "llm_vision",
        }
    return {
        "orientation_class": 0,
        "orientation_confidence": 0.5,
        "orientation_detection_method": "default_upright",
    }


def _resolve_nepali_resolution(
    resolution_rec: dict[str, Any] | None,
    v1_data: dict[str, Any],
    data: dict[str, Any],
) -> None:
    """Populate resolution quality fields into data dict."""
    if resolution_rec:
        data["resolution_quality_score"] = resolution_rec.get("quality_score")
        data["resolution_quality_bucket"] = resolution_rec.get("bucket")
        data["resolution_char_height_px"] = resolution_rec.get("median_char_height_px")
        data["resolution_detection_method"] = resolution_rec.get(
            "method", "paddleocr_cc_v1"
        )
        return
    for field in (
        "resolution_category",
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field in v1_data:
            data[field] = v1_data[field]


def _resolve_nepali_text_content(
    text_label: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve text content fields from VLM transcription labels."""
    if text_label and text_label.get("transcription"):
        transcription = text_label["transcription"]
        return {
            "text_has_content": True,
            "text_content": transcription,
            "text_content_confidence": text_label.get("confidence", 0.8),
            "text_content_source": "vlm_manual_transcription",
            "text_statistics": compute_text_statistics(transcription),
        }
    return {
        "text_has_content": False,
        "text_content": "",
        "text_content_confidence": 0.0,
        "text_content_source": "none",
        "text_statistics": compute_text_statistics(""),
    }


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

    # LAYOUT DETECTIONS (with KI-001 casing fix)
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout = _standardize_layout_detections(v1_layout)
    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # CAPTURE METHOD (with KI-005 synthetic override)
    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # DOMAIN
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "EDU")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = "EDU"
        data["domain_confidence"] = 0.9
        data["domain_detection_method"] = "dataset_documentation"

    # LANGUAGE / SCRIPT
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_rec, train_gt
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method
    data["script_family"] = _get_script_family(script)

    # CONTENT FLAGS (with KI-002, KI-003, KI-004, KI-006 overrides)
    flags = derive_content_flags(standardized_layout)
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = True
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "vlm_corrected+dataset_documentation+docling_gpu"
    data["content_flags_confidence"] = 0.90
    data["handwriting_present"] = data["has_handwriting"]

    # ORIENTATION
    data.update(_resolve_nepali_orientation(skew_rec, llm))

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
        data["text_scope_content_type"] = content_type or "handwritten"
    else:
        data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "word"

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # RESOLUTION QUALITY
    _resolve_nepali_resolution(resolution_rec, v1_data, data)

    # TEXT CONTENT
    data.update(_resolve_nepali_text_content(text_label))

    # v2.3.0 FIELDS
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]
    data["character_height_rendered_px"] = None
    data["output_size_px"] = None
    data["schema_version"] = "2.3.0"

    # ADDITIONAL DERIVED FIELDS
    data["dataset_short_code"] = DATASET_NAME
    data["handwriting_assessment"] = {
        "presence": "DOMINANT",
        "legibility": "FAIR",
        "content_type": "alphanumeric",
        "detection_method": "dataset_documentation",
        "confidence": 1.0,
    }

    # RELIABILITY SUMMARY (must be last)
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


def _track_nepali_match_counts(
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
    """Increment source match counters."""
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


def _track_nepali_flag_counts(
    stats: dict[str, Any],
    integrated_data: dict[str, Any],
) -> None:
    """Increment content flag and text content counters."""
    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
        ("text_has_content", "has_text_content_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1


def _track_nepali_sample_stats(
    stats: dict[str, Any],
    filename_stem: str,
    filename_full: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None,
    train_gt_index: dict[str, dict[str, Any]] | None,
    skew_index: dict[str, dict[str, Any]] | None,
    resolution_index: dict[str, dict[str, Any]] | None,
    text_labels_index: dict[str, dict[str, Any]] | None,
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    _track_nepali_match_counts(
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
    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1
    stats["capture_method_dist"][integrated_data.get("capture_method", "unknown")] += 1
    stats["content_type_dist"][
        integrated_data.get("text_scope_content_type", "unknown")
    ] += 1
    _track_nepali_flag_counts(stats, integrated_data)


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for i, ver in enumerate(versions):
        if ver.get("version") == version_number:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


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
        "has_text_content_count": 0,
        "text_labels_matched": 0,
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

        _track_nepali_sample_stats(
            stats,
            filename_stem,
            filename_full,
            integrated_data,
            llm_index,
            lang_index,
            vlm_index,
            train_gt_index,
            skew_index,
            resolution_index,
            text_labels_index,
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": (f"integrate_{DATASET_NAME}_enrichments.py"),
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "VLM text transcriptions (10 samples) + "
                    "VLM-corrected content flags + language enrichment + "
                    "dataset documentation (v2.3.0)"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(
                sample,
                new_version,
                ENRICHMENT_VERSION_NUMBER,
            )

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
    print(f"  has_text_content:   {stats['has_text_content_count']}")
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
        default=VLM_TEXT_LABELS_PATH,
        help="Path to VLM text transcription labels JSON (default: %(default)s)",
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
