#!/usr/bin/env python3
"""Integrate all enrichment sources into smartdoc-qa Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/integrate_tobacco800_enrichments.py

smartdoc-qa specifics:
  - SmartDoc Quality Assessment benchmark (4,260 images)
  - Mobile-captured documents with controlled distortions
  - Robotic arm capture (Fanuc LR Mate 200iD), Samsung Galaxy S4
  - LLM + language enrichment available
  - Docling layout (22 batches) + OCR (22 batches) extracted
  - No official splits -> hash-based 80/10/10
  - Multi-domain (ADM, FIN, SCI, LEG), multilingual (English dominant)
  - BENCHMARK ONLY: NEVER train on this dataset

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_smartdoc_qa_enrichments.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
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
DATASET_NAME = "smartdoc-qa"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "smartdoc-qa_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "smartdoc-qa_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "smartdoc-qa_language_enrichment.json"
)

# Docling extracted data (layout + OCR)
DOCLING_EXTRACTED_DIR = REGISTRY_DIR / "extracted" / "smartdoc-qa"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


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

# --- KI-002 through KI-006 -----------------------------------------
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: Camera-captured by robotic arm -------------------------
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

# ===================================================================
# Content flag class mappings
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the dataset's *_metadata.json file.

    Returns:
        Full metadata dict with "samples" list.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    The LLM enrichment for smartdoc-qa uses image_id which may be
    the full filename (with extension) rather than just the stem.

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping image_id to enrichment record.
        Indexes by both full filename and stem for flexible matching.
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
            # Index by both full name and stem for flexible matching
            index[image_id] = rec
            stem = Path(image_id).stem
            if stem != image_id:
                index[stem] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id.

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
            stem = Path(image_id).stem
            if stem != image_id:
                index[stem] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_docling_layout_batches(
    extracted_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Load Docling layout annotations from COCO-format batch files.

    Args:
        extracted_dir: Directory containing layout_batch_*.json files.

    Returns:
        Dict mapping image filename to list of annotation dicts.
    """
    if not extracted_dir.exists():
        log.warning("Docling extracted dir not found: %s", extracted_dir)
        return {}

    batch_files = sorted(extracted_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", extracted_dir)
        return {}

    log.info("Loading %d layout batch files from %s", len(batch_files), extracted_dir)

    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for batch_file in batch_files:
        with open(batch_file, encoding="utf-8") as f:
            batch: dict[str, Any] = json.load(f)

        id_to_filename: dict[int, str] = {}
        for img in batch.get("images", []):
            id_to_filename[img["id"]] = img["file_name"]

        for ann in batch.get("annotations", []):
            image_id = ann.get("image_id")
            filename = id_to_filename.get(image_id, "")
            if not filename:
                continue

            detection = {
                "class_name": ann.get("category_name", ""),
                "bbox": ann.get("bbox", []),
                "confidence": 0.85,
                "source_label": ann.get("category_name", ""),
                "source_schema": "docling-native",
            }
            if filename not in index:
                index[filename] = []
            index[filename].append(detection)
            total_annotations += 1

    log.info(
        "  Indexed %d annotations across %d images",
        total_annotations,
        len(index),
    )
    return index


def load_docling_ocr_batches(extracted_dir: Path) -> dict[str, dict[str, Any]]:
    """Load Docling OCR text from JSONL batch files.

    Args:
        extracted_dir: Directory containing ocr_batch_*.jsonl files.

    Returns:
        Dict mapping image filename to OCR record.
    """
    if not extracted_dir.exists():
        log.warning("Docling extracted dir not found: %s", extracted_dir)
        return {}

    batch_files = sorted(extracted_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        log.warning("No OCR batch files found in %s", extracted_dir)
        return {}

    log.info("Loading %d OCR batch files from %s", len(batch_files), extracted_dir)

    index: dict[str, dict[str, Any]] = {}

    for batch_file in batch_files:
        with open(batch_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec: dict[str, Any] = json.loads(line)
                source = rec.get("source", "")
                filename = Path(source).name if source else ""
                if filename and rec.get("success", False):
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


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content.
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

    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", clean_text))

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

    if latin_words > 0:
        stats["latin_word_count"] = latin_words
    if cjk_chars > 0:
        stats["cjk_char_count"] = cjk_chars

    return stats


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Args:
        detections: List of layout detection dicts with "class_name".

    Returns:
        Dict with boolean flags.
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
    """Convert layout extractor class_name to DocLayNet PascalCase.

    Args:
        class_name: Raw class name from layout extractor output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def assign_split(filename: str) -> str:
    """Assign deterministic train/val/test split using filename hash.

    Args:
        filename: Image filename to hash for split assignment.

    Returns:
        Split string: "train", "val", or "test".
    """
    hash_val = int(hashlib.sha256(filename.encode()).hexdigest(), 16) % 100
    if hash_val < 80:
        return "train"
    if hash_val < 90:
        return "val"
    return "test"


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
    vlm: dict[str, Any] | None = None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a sample using priority chain.

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).
        vlm: VLM enrichment record (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
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

    # Fallback: smartdoc-qa is predominantly English
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})
    base_lang = v1_data.get("iso639_language", "en")
    base_script = v1_data.get("iso15924_script", "Latn")
    return (base_lang, base_script, 0.50, "base_metadata")


def resolve_capture_method(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    is_synthetic: bool,
) -> tuple[str, float, str]:
    """Resolve capture method.

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
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index.
        lang_index: Language enrichment index.
        layout_index: Docling layout index (filename -> annotations).
        ocr_index: Docling OCR index (filename -> record).
        vlm_index: VLM enrichment index (optional).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    filename_full = Path(filename).name

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem) or llm_index.get(filename_full)
    lang_enrichment = lang_index.get(filename_stem) or lang_index.get(filename_full)
    vlm_rec = (vlm_index or {}).get(filename_stem)

    data: dict[str, Any] = {}

    # LAYOUT DETECTIONS (from Docling batch files)
    raw_detections = layout_index.get(filename_full, [])
    standardized_layout: list[dict[str, Any]] = []
    for det in raw_detections:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    # Fallback to v1 layout detections
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
    data["layout_source"] = "docling_gpu" if raw_detections else "base_metadata"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # CAPTURE METHOD
    capture, capture_conf, capture_method_src = resolve_capture_method(
        sample, llm, IS_SYNTHETIC_DATASET
    )
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # DOMAIN - VLM contact sheet override (2026-02-13): use LLM domain
    # when available and non-UNK, otherwise default to GENERAL
    # (all smartdoc-qa images are printed documents - letters, papers, forms)
    if llm:
        llm_domain = llm.get("domain_level1", "UNK")
        if llm_domain and llm_domain != "UNK":
            data["domain_level1"] = llm_domain
            data["domain_confidence"] = llm.get("domain_confidence", 0.5)
            data["domain_detection_method"] = "llm_vision"
        else:
            data["domain_level1"] = "GENERAL"
            data["domain_confidence"] = 0.7
            data["domain_detection_method"] = "vlm_contact_sheet_default"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = "GENERAL"
        data["domain_confidence"] = 0.7
        data["domain_detection_method"] = "vlm_contact_sheet_default"

    # LANGUAGE / SCRIPT
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm_rec
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # KI-008 fix: convert script to script_family properly
    data["script_family"] = _get_script_family(script)

    # CONTENT FLAGS
    flags = derive_content_flags(standardized_layout)

    if llm:
        data["has_table"] = bool(llm.get("has_table", False)) or flags["has_table"]
        data["has_figure"] = bool(llm.get("has_figure", False)) or flags["has_figure"]
        data["has_formula"] = (
            bool(llm.get("has_formula", False)) or flags["has_formula"]
        )
        data["has_handwriting"] = bool(llm.get("has_handwriting", False))
        data["has_signature"] = bool(llm.get("has_signature", False))
    else:
        # Use v1 data content flags if available
        data["has_table"] = bool(v1_data.get("has_table", False)) or flags["has_table"]
        data["has_figure"] = (
            bool(v1_data.get("has_figure", False)) or flags["has_figure"]
        )
        data["has_formula"] = (
            bool(v1_data.get("has_formula", False)) or flags["has_formula"]
        )
        data["has_handwriting"] = bool(v1_data.get("has_handwriting", False))
        data["has_signature"] = False

    data["has_code"] = flags["has_code"]

    # VLM true positive overrides (applied after Phase C)
    if VLM_TABLE_TRUE_POSITIVES and filename_stem not in VLM_TABLE_TRUE_POSITIVES:
        data["has_table"] = False
    if VLM_FIGURE_TRUE_POSITIVES and filename_stem not in VLM_FIGURE_TRUE_POSITIVES:
        data["has_figure"] = False
    if VLM_FORMULA_TRUE_POSITIVES and filename_stem not in VLM_FORMULA_TRUE_POSITIVES:
        data["has_formula"] = False
    if (
        VLM_HANDWRITING_TRUE_POSITIVES
        and filename_stem not in VLM_HANDWRITING_TRUE_POSITIVES
    ):
        data["has_handwriting"] = False

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "llm_vision+docling_gpu"
    data["content_flags_confidence"] = 0.80

    # Handwriting: printed documents only (benchmark dataset)
    data["handwriting_present"] = False

    # ORIENTATION (controlled robotic capture, documents upright)
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.95
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT (hash-based deterministic 80/10/10)
    data["split"] = assign_split(filename_full)

    # TEXT SCOPE
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "printed"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "printed"
        )

    data["text_scope"] = "page"

    # IMAGE PROPERTIES (all RGB JPEG smartphone captures)
    data["image_properties_color_mode"] = "color"

    # RESOLUTION
    for field in (
        "resolution_category",
        "resolution_pixels",
        "resolution_dpi",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # TEXT CONTENT (from Docling OCR batches)
    ocr_rec = ocr_index.get(filename_full)
    if ocr_rec and ocr_rec.get("text"):
        text = ocr_rec["text"]
        data["text_has_content"] = True
        data["text_content"] = text
        data["text_content_confidence"] = ocr_rec.get("confidence", 1.0)
        data["text_content_source"] = "docling_ocr"
        data["text_statistics"] = compute_text_statistics(text)
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
        "vlm_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
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
            layout_index,
            ocr_index,
            vlm_index,
        )

        stats["integrated"] += 1
        if filename_stem in llm_index or filename_full in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index or filename_full in lang_index:
            stats["lang_matched"] += 1
        if vlm_index and filename_stem in vlm_index:
            stats["vlm_matched"] += 1
        if filename_full in layout_index:
            stats["layout_matched"] += 1
        if filename_full in ocr_index:
            stats["ocr_matched"] += 1
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
                    "LLM vision + language + Docling layout/OCR + "
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
    print(f"Layout matched:       {stats.get('layout_matched', 0)}")
    print(f"OCR matched:          {stats.get('ocr_matched', 0)}")
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
        "--docling-extracted-dir",
        type=Path,
        default=DOCLING_EXTRACTED_DIR,
        help="Path to Docling extracted data dir (default: %(default)s)",
    )
    parser.add_argument(
        "--vlm-enrichment",
        type=Path,
        default=None,
        help="Path to VLM enrichment JSON (optional)",
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
    layout_index = load_docling_layout_batches(args.docling_extracted_dir)
    ocr_index = load_docling_ocr_batches(args.docling_extracted_dir)

    vlm_index: dict[str, dict[str, Any]] | None = None
    if args.vlm_enrichment:
        vlm_index = load_vlm_enrichment(args.vlm_enrichment)

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
