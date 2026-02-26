#!/usr/bin/env python3
"""Integrate all enrichment sources into mdiw13 Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

mdiw13 specifics:
  - 290,213 multi-script handwritten/printed document images (13 scripts)
  - Scanner-flatbed captured (SIW Multi-script Database)
  - Docling layout extraction: 1,162 batch files (COCO format)
  - Docling OCR extraction: 581 batch files (JSONL)
  - No LLM enrichment, stub language enrichment (unused)
  - Parser SCRIPT_MAPPINGS provides high-confidence script/language ground truth
  - Schema upgrade: 2.1 -> 2.3.0 (adds text_direction, text_directions_present)

Defect mitigations (from defect_catalog.json):
  D01 - split: re-derive from source path (main/competition_train/competition_test)
  D02 - script_family: re-derive via get_script_family(iso15924_script) [KI-008]
  D03 - domain_level1: accept UNK for mixed-domain dataset [KI-007]
  D04 - layout_detections: integrate 1,162 Docling layout batch files [KI-001]
  D05 - text_has_content: integrate 581 Docling OCR batch files
  D06 - orientation_class: default upright (scanner_flatbed)
  D07 - image_properties_color_mode: default grayscale (scanned documents)
  D08 - handwriting_present: copy from content_flags.has_handwriting
  D09 - iso639_language: re-derive from parser SCRIPT_MAPPINGS
  D10 - iso15924_script: re-derive from parser SCRIPT_MAPPINGS
  D11 - schema_version: bump 2.1 -> 2.3.0, populate text_direction fields

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_mdiw13_enrichments.py --dry-run

    # Full integration (writes output):
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_mdiw13_enrichments.py
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "mdiw13"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py"
)


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
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "mdiw13"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "mdiw13_metadata.json"
# LLM enrichment: not available for mdiw13
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "mdiw13_llm_enrichment.json"
# Language enrichment: stub file (1 KB, essentially empty)
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "mdiw13_language_enrichment.json"

# Docling extracted data (multiple batch files)
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "mdiw13"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "mdiw13"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# Target schema version after integration
TARGET_SCHEMA_VERSION = "2.3.0"

# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
APPLY_KI_001_LAYOUT_CASING = True

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

# --- KI-005: Capture method override (HIGH) -------------------------
# mdiw13 is a scanner-captured dataset (SIW Multi-script Database)
KNOWN_CAPTURE_METHOD: str | None = "scanner_flatbed"

# --- KI-007: Domain level 1 ----------------------------------------
# Accept UNK: dataset is mixed newspaper scans + handwritten letters
# No domain reclassification needed.

# --- KI-008: Script family directionality ---------------------------
# script_family contains "ltr"/"rtl" instead of proper family names.
# Fixed by re-deriving via get_script_family(iso15924_script).

# --- Content flag KI overrides (KI-002..KI-006) --------------------
# mdiw13 is a handwriting/script-identification dataset.
# VLM inspection not yet performed; using conservative defaults.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# ===================================================================
# Content flag class mappings
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# ===================================================================
# MDIW-13 Parser mappings (mirrored from Mdiw13Parser.SCRIPT_MAPPINGS)
# ===================================================================
# Script name -> (ISO 15924, ISO 639-1)
SCRIPT_MAPPINGS: dict[str, tuple[str, str]] = {
    "Arabic": ("Arab", "ar"),
    "Bengali": ("Beng", "bn"),
    "Bangla": ("Beng", "bn"),
    "Gujarati": ("Gujr", "gu"),
    "Gurmukhi": ("Guru", "pa"),
    "Devanagari": ("Deva", "hi"),
    "Hindi": ("Deva", "hi"),
    "Japanese": ("Jpan", "ja"),
    "Kannada": ("Knda", "kn"),
    "Malayalam": ("Mlym", "ml"),
    "Oriya": ("Orya", "or"),
    "Roman": ("Latn", "en"),
    "Tamil": ("Taml", "ta"),
    "Telugu": ("Telu", "te"),
    "Thai": ("Thai", "th"),
}

# Reverse lookup: ISO 15924 -> (ISO 639-1, script_name)
ISO15924_TO_LANGUAGE: dict[str, tuple[str, str]] = {}
for _name, (_script, _lang) in SCRIPT_MAPPINGS.items():
    if _script not in ISO15924_TO_LANGUAGE:
        ISO15924_TO_LANGUAGE[_script] = (_lang, _name)

# Script -> text_direction mapping (v2.3.0)
SCRIPT_TO_TEXT_DIRECTION: dict[str, str] = {
    "Arab": "rtl",
    # All others are LTR (including Japanese which is primarily horizontal)
}

# Script -> text_directions_present mapping (v2.3.0)
SCRIPT_TO_DIRECTIONS_PRESENT: dict[str, list[str]] = {
    "Arab": ["rtl"],
    "Jpan": ["ltr", "ttb"],  # Japanese supports both horizontal and vertical
    # All others default to ["ltr"]
}


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to mdiw13_metadata.json.

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


def load_docling_layout_batches(
    layout_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling layout batch files and index by filename.

    Globs ``layout_batch_*.json`` in *layout_dir*. Each file is in
    COCO format with categories, images, and annotations arrays.

    Args:
        layout_dir: Directory containing layout_batch_*.json files.

    Returns:
        Dict mapping image filename to list of detection dicts.
    """
    if not layout_dir.is_dir():
        log.warning("Layout directory not found: %s", layout_dir)
        return {}

    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}

    log.info(
        "Loading %d Docling layout batch files from %s", len(batch_files), layout_dir
    )
    index: dict[str, list[dict[str, Any]]] = {}
    total_detections = 0

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
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
        for ann in coco.get("annotations", []):
            image_id = ann.get("image_id")
            filename = img_map.get(image_id, "")
            if not filename:
                continue
            category_name = cat_map.get(ann.get("category_id", -1), "unknown")
            det: dict[str, Any] = {
                "class_name": category_name,
                "bbox": ann.get("bbox", []),
                "confidence": 1.0,
                "area": ann.get("area", 0.0),
            }
            index.setdefault(filename, []).append(det)
            total_detections += 1

    log.info(
        "  Indexed %d images with %d total detections from %d batch files",
        len(index),
        total_detections,
        len(batch_files),
    )
    return index


def load_docling_ocr_batches(
    ocr_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Load all Docling OCR batch files and index by filename.

    Globs ``ocr_batch_*.jsonl`` in *ocr_dir*. Each line is a JSON
    record with source, text, confidence, success fields.

    Args:
        ocr_dir: Directory containing ocr_batch_*.jsonl files.

    Returns:
        Dict mapping image filename to OCR record.
    """
    if not ocr_dir.is_dir():
        log.warning("OCR directory not found: %s", ocr_dir)
        return {}

    batch_files = sorted(ocr_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        log.warning("No OCR batch files found in %s", ocr_dir)
        return {}

    log.info("Loading %d Docling OCR batch files from %s", len(batch_files), ocr_dir)
    index: dict[str, dict[str, Any]] = {}

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec: dict[str, Any] = json.loads(line)
                if not rec.get("success"):
                    continue
                source = rec.get("source", "")
                filename = Path(source).name
                if filename:
                    index[filename] = rec

    log.info(
        "  Indexed %d OCR records from %d batch files", len(index), len(batch_files)
    )
    return index


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    Args:
        path: Path to LLM enrichment JSON.

    Returns:
        Dict mapping image_id to enrichment record.
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


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from OCR transcription.

    Counts characters, words, lines, and script-specific characters
    for the 13 scripts in MDIW-13.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content,
        and avg_line_length.
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

    # Script-specific character patterns (all 13 MDIW scripts)
    deva_chars = len(re.findall(r"[\u0900-\u097f]", clean_text))
    arab_chars = len(re.findall(r"[\u0600-\u06ff]", clean_text))
    beng_chars = len(re.findall(r"[\u0980-\u09ff]", clean_text))
    gujr_chars = len(re.findall(r"[\u0a80-\u0aff]", clean_text))
    guru_chars = len(re.findall(r"[\u0a00-\u0a7f]", clean_text))
    knda_chars = len(re.findall(r"[\u0c80-\u0cff]", clean_text))
    mlym_chars = len(re.findall(r"[\u0d00-\u0d7f]", clean_text))
    orya_chars = len(re.findall(r"[\u0b00-\u0b7f]", clean_text))
    taml_chars = len(re.findall(r"[\u0b80-\u0bff]", clean_text))
    telu_chars = len(re.findall(r"[\u0c00-\u0c7f]", clean_text))
    thai_chars = len(re.findall(r"[\u0e00-\u0e7f]", clean_text))
    cjk_chars = len(
        re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]", clean_text)
    )
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
    script_counts = [
        ("devanagari_char_count", deva_chars),
        ("arabic_char_count", arab_chars),
        ("bengali_char_count", beng_chars),
        ("gujarati_char_count", gujr_chars),
        ("gurmukhi_char_count", guru_chars),
        ("kannada_char_count", knda_chars),
        ("malayalam_char_count", mlym_chars),
        ("oriya_char_count", orya_chars),
        ("tamil_char_count", taml_chars),
        ("telugu_char_count", telu_chars),
        ("thai_char_count", thai_chars),
        ("cjk_char_count", cjk_chars),
        ("latin_word_count", latin_words),
    ]
    stats.update({key: count for key, count in script_counts if count > 0})

    return stats


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Args:
        detections: List of layout detection dicts with class_name.

    Returns:
        Dict with boolean flags: has_table, has_formula, has_figure,
        has_code.
    """
    canonical_classes = {
        d.get("class_name", "").upper() for d in detections if d.get("class_name")
    }
    return {
        "has_table": bool(canonical_classes & TABLE_CLASSES),
        "has_formula": bool(canonical_classes & FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & FIGURE_CLASSES),
        "has_code": bool(canonical_classes & CODE_CLASSES),
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Dict with min_confidence, field counts, and field_summary.
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
    """Convert Docling lowercase class_name to DocLayNet PascalCase.

    KI-001 mitigation: Docling outputs lowercase labels that must be
    standardized to DocLayNet convention.

    Args:
        class_name: Raw class name from Docling layout output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def resolve_split(sample: dict[str, Any]) -> str:
    """Resolve split from source path (D01 fix).

    Re-derives split from directory structure:
      - SIW_MultiscriptDatabase/* -> "main"
      - TrainCompetition* -> "competition_train"
      - TestCompetition* -> "competition_test"

    Args:
        sample: A single sample from the L2 metadata.

    Returns:
        Split string: "main", "competition_train", or "competition_test".
    """
    source = sample.get("source", {})
    original_path = source.get("original_path", "")
    original_filename = source.get("original_filename", "")
    raw_labels = sample.get("original_labels", {}).get("raw_labels", {})

    # Check raw_labels.data_source first (parser output)
    data_source = raw_labels.get("data_source", "")
    if data_source == "competition_test":
        return "competition_test"
    if data_source == "competition_train":
        return "competition_train"
    if data_source == "main":
        return "main"

    # Fallback: check directory path patterns in original_path (full path)
    path_to_check = original_path or original_filename
    if "TestCompetition" in path_to_check:
        return "competition_test"
    if "TrainCompetition" in path_to_check:
        return "competition_train"
    if "SIW_MultiscriptDatabase" in path_to_check:
        return "main"

    return "main"


def resolve_language_script(
    sample: dict[str, Any],
) -> tuple[str, str, float, str]:
    """Resolve language and script from parser ground truth (D09/D10 fix).

    Uses parser original_labels as highest-confidence source, then
    falls back to SCRIPT_MAPPINGS re-derivation from script_name.

    Args:
        sample: A single sample from the L2 metadata.

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence, method).
    """
    original_labels = sample.get("original_labels", {})
    language_code = original_labels.get("language_code", "")
    script_code = original_labels.get("iso15924_script_code", "")
    script_name = original_labels.get("script_name", "")

    # Source 1: Parser already populated both language_code and script_code
    if language_code and language_code not in ("", "und"):
        if script_code:
            return (language_code, script_code, 0.95, "parser_gt")
        # Have language but no script - look up from script_name
        if script_name and script_name in SCRIPT_MAPPINGS:
            iso15924, _ = SCRIPT_MAPPINGS[script_name]
            return (language_code, iso15924, 0.95, "parser_gt")
        return (language_code, "Zyyy", 0.85, "parser_gt_partial")

    # Source 2: Re-derive from script_name via SCRIPT_MAPPINGS
    if script_name and script_name in SCRIPT_MAPPINGS:
        iso15924, iso639 = SCRIPT_MAPPINGS[script_name]
        return (iso639, iso15924, 0.90, "parser_script_mapping")

    # Source 3: Extract script from directory path (handles unlabeled samples)
    original_path = sample.get("source", {}).get("original_path", "")
    for mapping_name in SCRIPT_MAPPINGS:
        if f"/{mapping_name}/" in original_path:
            iso15924, iso639 = SCRIPT_MAPPINGS[mapping_name]
            return (iso639, iso15924, 0.85, "path_script_extraction")

    # Source 4: Try existing enrichment iso15924_script -> language
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})
    existing_script = v1_data.get("iso15924_script", "")
    if existing_script and existing_script in ISO15924_TO_LANGUAGE:
        iso639, _name = ISO15924_TO_LANGUAGE[existing_script]
        return (iso639, existing_script, 0.80, "enrichment_v1_rederived")

    # Fallback
    return ("und", "Zyyy", 0.1, "none")


def resolve_text_direction(iso15924_script: str) -> str:
    """Get text direction from script code (v2.3.0).

    Args:
        iso15924_script: ISO 15924 script code.

    Returns:
        Text direction: "ltr", "rtl", or "ttb".
    """
    return SCRIPT_TO_TEXT_DIRECTION.get(iso15924_script, "ltr")


def resolve_text_directions_present(iso15924_script: str) -> list[str]:
    """Get all text directions present for a script (v2.3.0).

    Args:
        iso15924_script: ISO 15924 script code.

    Returns:
        List of text directions present (e.g., ["ltr"], ["rtl"], ["ltr", "ttb"]).
    """
    return SCRIPT_TO_DIRECTIONS_PRESENT.get(iso15924_script, ["ltr"])


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Merges parser ground truth, Docling layout, Docling OCR, and
    dataset documentation into a single enrichment version.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (likely empty for mdiw13).
        layout_index: Docling layout index (filename -> detections).
        ocr_index: Docling OCR index (filename -> OCR record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    filename_full = Path(filename).name

    # Get existing enrichment data for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Look up enrichment sources
    llm = llm_index.get(filename_stem)
    layout_dets = layout_index.get(filename_full, [])
    ocr_rec = ocr_index.get(filename_full)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01 - SPLIT: re-derive from source path
    # -------------------------------------------------------------------
    data["split"] = resolve_split(sample)

    # -------------------------------------------------------------------
    # D06 - ORIENTATION: default upright for scanner_flatbed documents
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # CAPTURE METHOD (KI-005: from dataset documentation)
    # -------------------------------------------------------------------
    data["capture_method"] = KNOWN_CAPTURE_METHOD or "scanner_flatbed"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D03 - DOMAIN (KI-007: accept UNK for mixed-domain dataset)
    # -------------------------------------------------------------------
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
    else:
        data["domain_level1"] = "UNK"
        data["domain_confidence"] = 0.3
        data["domain_detection_method"] = "none"

    # -------------------------------------------------------------------
    # D09/D10 - LANGUAGE / SCRIPT: from parser SCRIPT_MAPPINGS
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language_script(sample)
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # D02 - SCRIPT FAMILY: re-derive from iso15924_script (KI-008 fix)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # D11 - TEXT DIRECTION (v2.3.0 fields)
    # -------------------------------------------------------------------
    data["text_direction"] = resolve_text_direction(script)
    data["text_directions_present"] = resolve_text_directions_present(script)

    # -------------------------------------------------------------------
    # D04 - LAYOUT DETECTIONS: integrate Docling batch files (KI-001)
    # -------------------------------------------------------------------
    standardized_layout: list[dict[str, Any]] = []
    for det in layout_dets:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    # Fall back to existing v1 layout if no Docling data for this sample
    if not standardized_layout:
        v1_layout = v1_data.get("layout_detections", [])
        for det in v1_layout:
            new_det = dict(det)
            original_class = det.get("class_name", "")
            new_det["class_name"] = standardize_class_name(original_class)
            if not new_det.get("source_label"):
                new_det["source_label"] = original_class
            standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu" if layout_dets else "none"
    data["layout_confidence"] = 0.85 if layout_dets else 0.0
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (derived from layout + conservative defaults)
    # -------------------------------------------------------------------
    flags = derive_content_flags(standardized_layout)

    # KI-002: has_table -- only VLM-confirmed
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]

    # KI-003: has_figure -- only VLM-confirmed
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES

    # KI-006: has_formula -- only VLM-confirmed
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES

    # D08 - HANDWRITING: derive from directory path
    # MultiscriptHandwritten* -> True, MultiscriptPrinted* -> False
    # TrainCompetition/handwritten -> True, TrainCompetition/printed -> False
    original_path = sample.get("source", {}).get("original_path", "")
    if "Handwritten" in original_path or "/handwritten/" in original_path:
        data["has_handwriting"] = True
    elif "Printed" in original_path or "/printed/" in original_path:
        data["has_handwriting"] = False
    else:
        # Competition test samples without ground truth - assume mixed
        data["has_handwriting"] = True

    data["has_signature"] = False
    data["has_code"] = flags["has_code"]

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 0.80

    # Alias used by prescreening checks
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # D05 - TEXT CONTENT: from Docling OCR batch files
    # -------------------------------------------------------------------
    if ocr_rec:
        ocr_text = ocr_rec.get("text", "")
        ocr_conf = ocr_rec.get("confidence", 0.8)
        if ocr_text and ocr_text.strip():
            data["text_has_content"] = True
            data["text_content"] = ocr_text
            data["text_content_confidence"] = ocr_conf
            data["text_content_source"] = "docling_ocr"
            data["text_statistics"] = compute_text_statistics(ocr_text)
        else:
            data["text_has_content"] = False
            data["text_content_confidence"] = 0.0
            data["text_content_source"] = "docling_ocr_empty"
            data["text_statistics"] = compute_text_statistics("")
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # -------------------------------------------------------------------
    # D07 - IMAGE PROPERTIES COLOR MODE
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = "handwritten_document"
    data["text_scope"] = v1_data.get("text_scope", "mixed")

    # -------------------------------------------------------------------
    # RESOLUTION (preserve v1)
    # -------------------------------------------------------------------
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
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last)
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Statistics tracking
# ===================================================================
def _track_sample_stats(
    stats: dict[str, Any],
    filename_stem: str,
    filename_full: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename_full in layout_index:
        stats["layout_matched"] += 1
    if filename_full in ocr_index:
        stats["ocr_matched"] += 1
    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1
    stats["text_direction_dist"][integrated_data.get("text_direction", "ltr")] += 1

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


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index (likely empty).
        layout_index: Docling layout index (filename -> detections).
        ocr_index: Docling OCR index (filename -> OCR record).
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "text_direction_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }

    now = datetime.now(UTC).isoformat()
    report_interval = 50_000

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem
        filename_full = Path(filename).name

        integrated_data = integrate_sample(sample, llm_index, layout_index, ocr_index)

        _track_sample_stats(
            stats,
            filename_stem,
            filename_full,
            integrated_data,
            llm_index,
            layout_index,
            ocr_index,
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_mdiw13_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser GT + Docling layout (1162 batches) + "
                    "Docling OCR (581 batches) + "
                    "dataset documentation + v2.3.0 schema upgrade"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, ENRICHMENT_VERSION_NUMBER)

        if stats["total"] % report_interval == 0:
            log.info(
                "  Processed %d / %d samples...",
                stats["total"],
                len(metadata["samples"]),
            )

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
    print(f"Layout matched:       {stats['layout_matched']}")
    print(f"OCR matched:          {stats['ocr_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print()

    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {domain:20s}: {count:7d} ({pct:.1f}%)")
    print()

    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {split:25s}: {count:7d} ({pct:.1f}%)")
    print()

    print("Language distribution (top 15):")
    for lang, count in stats["lang_dist"].most_common(15):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:7d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:7d} ({pct:.1f}%)")
    print()

    print("Language detection method:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:7d}")
    print()

    print("Text direction distribution (v2.3.0):")
    for td, count in stats["text_direction_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {td:10s}: {count:7d} ({pct:.1f}%)")
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
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to mdiw13_metadata.json (default: %(default)s)",
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
        "--layout-dir",
        type=Path,
        default=DOCLING_LAYOUT_DIR,
        help="Directory containing layout_batch_*.json files (default: %(default)s)",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=DOCLING_OCR_DIR,
        help="Directory containing ocr_batch_*.jsonl files (default: %(default)s)",
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
    layout_index = load_docling_layout_batches(args.layout_dir)
    ocr_index = load_docling_ocr_batches(args.ocr_dir)

    log.info(
        "Sources loaded: %d LLM, %d layout images, %d OCR records",
        len(llm_index),
        len(layout_index),
        len(ocr_index),
    )

    # ----- Run integration -----
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        layout_index=layout_index,
        ocr_index=ocr_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    # ----- Update schema version (D11 fix) -----
    if not args.dry_run:
        metadata["schema_version"] = TARGET_SCHEMA_VERSION
        # Update splits_included to reflect re-derived splits
        metadata["splits_included"] = sorted(
            set(stats["split_dist"].keys()) - {"unknown"}
        ) or ["unknown"]

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
