#!/usr/bin/env python3
"""Integrate all enrichment sources into RealDAE Layer 2 metadata.

Merges 4 data sources into the main metadata JSON for all 583 records:
  1. LLM enrichment (600 images, keyed by image_id): domain, language, script,
     content flags, orientation, handwriting
  2. Docling GPU layout (6 batch files, COCO format): layout detections
  3. Docling GPU OCR (6 JSONL batch files): text content, text_has_content
  4. Dataset documentation: capture_method=camera_smartphone, split from path

Defect fixes applied:
  D01: split not populated -> derived from original_file path
       (task_*_train -> train, task_*_test -> test)
  D02: domain_level1 all UNK -> merge from LLM enrichment
  D03: iso639_language wrong (all 'en') -> LLM enrichment (74% Chinese)
  D04: iso15924_script wrong (all 'Latn') -> LLM enrichment (74% Hans)
  D05: script_family wrong ('ltr') -> derived from corrected iso15924_script
       via ScriptMLMapping.to_ml_class()
  D06: layout_detections not integrated -> load from Docling layout batch files
  D07: content_flags not populated -> derived from LLM + Docling layout
  D08: capture_method -> keep L2 per documentation (camera_smartphone)
  D09: text_has_content -> derived from Docling OCR batch files
  D10: orientation_class -> use LLM orientation (portrait/landscape)
  D11: image_properties_color_mode -> not populated, default "color"
  D12: handwriting_present -> use LLM has_handwriting

KI mitigations:
  KI-001: APPLY (Docling layout casing fix)
  KI-002: APPLY (flag table detections, non-synthetic -> no auto-override)
  KI-003: APPLY (flag picture detections, non-synthetic -> no auto-override)
  KI-004: DO NOT apply synthetic override (camera-captured dataset)
  KI-005: capture_method = camera_smartphone from documentation
  KI-006: APPLY (flag formula detections for VLM verification)
  KI-007: Accept UNK from LLM domain classification

Creates a new enrichment version (v2) in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_realdae_enrichments.py

    # Dry run (report only, no write):
    PYTHONPATH=... uv run python3 scripts/integrate_realdae_enrichments.py --dry-run
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
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "realdae"

# RealDAE is camera-captured (NOT synthetic)
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "realdae_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "realdae_llm_enrichment.json"

# Docling layout: 6 COCO-format JSON batch files
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "realdae"

# Docling OCR: 6 JSONL batch files
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "realdae"

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

# Docling category -> canonical class mapping (for content flag derivation)
DOCLING_CATEGORY_TO_CANONICAL: dict[str, str] = {
    "caption": "CAPTION",
    "checkbox_selected": "CHECKBOX_SELECTED",
    "checkbox_unselected": "CHECKBOX_UNSELECTED",
    "code": "CODE",
    "footnote": "FOOTNOTE",
    "formula": "FORMULA",
    "list_item": "LIST_ITEM",
    "page_footer": "PAGE_FOOTER",
    "page_header": "PAGE_HEADER",
    "picture": "PICTURE",
    "section_header": "SECTION_HEADER",
    "table": "TABLE",
    "text": "TEXT",
    "title": "TITLE",
}

# --- KI-002: Table detection multi-column FP (HIGH) -----------------
# RealDAE is camera-captured: flag but do not auto-override.
# No VLM corrections yet; leave layout-derived flags as soft labels.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# NOT synthetic -- LLM handwriting detection may be partially valid.
# No VLM corrections yet; use LLM has_handwriting as soft label.
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: capture method from documentation -----------------------
# RealDAE is camera-captured per dataset paper.
# LLM disagrees (38% scanner) but documentation takes precedence.
KNOWN_CAPTURE_METHOD = "camera_smartphone"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# ===================================================================
# Content flag class mappings
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# Script family mapping uses get_script_family from iso_language_script
# Returns lowercase family names: "latin", "cjk", "arabic", etc.


# ===================================================================
# Data loaders
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
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
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
    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def _build_detection_from_annotation(
    ann: dict[str, Any],
    cat_map: dict[int, str],
) -> dict[str, Any]:
    """Build a detection dict from a single COCO annotation."""
    category_name = ann.get("category_name", "")
    if not category_name:
        category_name = cat_map.get(ann.get("category_id", -1), "unknown")
    return {
        "class_name": category_name,
        "bbox": ann["bbox"],
        "confidence": 1.0,
        "source": "docling_gpu",
        "canonical_class": DOCLING_CATEGORY_TO_CANONICAL.get(
            category_name, category_name.upper()
        ),
        "source_schema": "docling",
        "text_snippet": (ann.get("text", "")[:200] if ann.get("text") else ""),
    }


def _process_layout_batch(
    batch_path: Path,
    index: dict[str, list[dict[str, Any]]],
) -> int:
    """Process a single COCO-format layout batch file into the index.

    Returns the number of annotations added.
    """
    with open(batch_path, encoding="utf-8") as fh:
        batch: dict[str, Any] = json.load(fh)

    cat_map: dict[int, str] = {
        cat["id"]: cat["name"] for cat in batch.get("categories", [])
    }

    image_id_to_filename: dict[int, str] = {}
    for img in batch.get("images", []):
        image_id_to_filename[img["id"]] = img["file_name"]
        if img["file_name"] not in index:
            index[img["file_name"]] = []

    count = 0
    for ann in batch.get("annotations", []):
        filename = image_id_to_filename.get(ann["image_id"])
        if filename is None:
            continue
        index[filename].append(_build_detection_from_annotation(ann, cat_map))
        count += 1
    return count


def load_docling_layout(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load Docling GPU layout from COCO-format JSON batch files.

    Each batch file is a JSON dict with "images", "annotations", and
    optionally "categories" arrays in COCO format.

    Args:
        layout_dir: Directory containing layout_batch_*.json files.

    Returns:
        Dict mapping filename -> list of detection dicts with class_name,
        bbox (COCO xywh), confidence, source, canonical_class, source_schema,
        and text_snippet fields.
    """
    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}

    log.info(
        "Loading Docling layout from %s (%d batch files)", layout_dir, len(batch_files)
    )
    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for batch_path in batch_files:
        total_annotations += _process_layout_batch(batch_path, index)

    log.info(
        "  Loaded %d annotations across %d images from %d batch files",
        total_annotations,
        len(index),
        len(batch_files),
    )
    return index


def load_docling_ocr(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load Docling GPU OCR from JSONL batch files.

    Each line in a batch file is a JSON object with at minimum an
    image identifier and text content.

    Args:
        ocr_dir: Directory containing ocr_batch_*.jsonl files.

    Returns:
        Dict mapping filename -> OCR record with text and metadata.
    """
    batch_files = sorted(ocr_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        log.warning("No OCR batch files found in %s", ocr_dir)
        return {}

    log.info("Loading Docling OCR from %s (%d batch files)", ocr_dir, len(batch_files))
    index: dict[str, dict[str, Any]] = {}

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record: dict[str, Any] = json.loads(line)
                # Extract filename from source path (may be GCS or local)
                source_path = record.get("source", "")
                filename = Path(source_path).name if source_path else ""
                if filename:
                    index[filename] = record

    log.info(
        "  Loaded %d OCR records from %d batch files", len(index), len(batch_files)
    )
    return index


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_split_from_path(original_file_path: str) -> str:
    """Derive train/test split from original file path.

    RealDAE directory structure uses task_*_train and task_*_test
    subdirectories.

    Args:
        original_file_path: The original_file or original_path field
            from the sample source.

    Returns:
        "train", "test", or "unknown".
    """
    path_lower = original_file_path.lower()
    if "_train" in path_lower or "/train/" in path_lower:
        return "train"
    if "_test" in path_lower or "/test/" in path_lower:
        return "test"
    return "unknown"


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


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from OCR output.

    Args:
        text: Raw OCR text content.

    Returns:
        Dict with char_count, word_count, line_count, cjk_char_count,
        latin_word_count, has_content, and avg_line_length.
    """
    if not text or text.strip() == "":
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_content": False,
        }

    # Clean up image placeholders
    clean_text = text.replace("<!-- image -->", "").strip()
    lines = clean_text.split("\n")
    non_empty_lines = [ln for ln in lines if ln.strip()]
    words = clean_text.split()

    # Detect CJK characters
    cjk_pattern = re.compile(
        r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\u3040-\u309f"
        r"\u30a0-\u30ff\uac00-\ud7af]"
    )
    cjk_chars = len(cjk_pattern.findall(clean_text))
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
        "cjk_char_count": cjk_chars,
        "latin_word_count": latin_words,
        "has_content": len(clean_text) > 0,
        "avg_line_length": avg_line_len,
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Assesses five field groups and produces a reliability tier for each
    based on confidence thresholds:
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
    """Convert Docling lowercase class_name to DocLayNet PascalCase.

    Uses DOCLING_TO_DOCLAYNET mapping (KI-001). Passes through
    unmapped names unchanged.

    Args:
        class_name: Raw class name from Docling layout output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


# ===================================================================
# Per-sample integration
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


def _resolve_realdae_language(
    llm: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve language/script fields from LLM enrichment."""
    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return {
                "iso639_language": llm_lang,
                "iso15924_script": llm_script or "Zyyy",
                "language_confidence": 0.65,
                "text_scope_detection_method": "llm_vision",
            }
    return {
        "iso639_language": "und",
        "iso15924_script": "Zyyy",
        "language_confidence": 0.1,
        "text_scope_detection_method": "none",
    }


def _resolve_realdae_layout(
    layout_dets: list[dict[str, Any]],
    v1_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve layout detections and metadata. Returns (standardized_layout, layout_fields)."""
    if layout_dets:
        standardized = _standardize_layout_detections(layout_dets)
        fields = {
            "layout_source": "docling_gpu",
            "layout_confidence": 0.85,
        }
    else:
        v1_layout = v1_data.get("layout_detections", [])
        standardized = _standardize_layout_detections(v1_layout)
        fields = {
            "layout_source": v1_data.get("layout_source", "none"),
            "layout_confidence": 0.5 if standardized else 0.0,
        }
    fields["layout_detection_count"] = len(standardized)
    return standardized, fields


def _resolve_realdae_orientation(
    llm: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve orientation fields from LLM enrichment."""
    if not llm or not llm.get("orientation"):
        return {
            "orientation_class": 0,
            "orientation_confidence": 0.5,
            "orientation_detection_method": "default_upright",
        }
    orientation_str = str(llm["orientation"]).lower()
    orientation_map = {"portrait": 0, "landscape": 90}
    return {
        "orientation_class": orientation_map.get(orientation_str, 0),
        "orientation_confidence": 0.6,
        "orientation_detection_method": "llm_vision",
    }


def _resolve_realdae_ocr(
    ocr_rec: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve text content fields from Docling OCR record."""
    if ocr_rec and ocr_rec.get("success") and ocr_rec.get("text"):
        ocr_text = ocr_rec["text"]
        return {
            "text_has_content": True,
            "text_content": ocr_text,
            "text_content_confidence": ocr_rec.get("confidence", 0.8),
            "text_content_source": "docling_gpu_ocr",
            "text_statistics": compute_text_statistics(ocr_text),
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
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single RealDAE sample.

    Merges all available enrichment sources into a single data dict
    that becomes the new enrichment version for this sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (image_id -> record).
        layout_index: Docling layout index (filename -> detection list).
        ocr_index: Docling OCR index (filename -> OCR record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    original_path = sample["source"].get("original_path", "")

    # Get existing v1 data for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Look up enrichment sources
    llm = llm_index.get(filename_stem)
    layout_dets = layout_index.get(filename, [])
    ocr_rec = ocr_index.get(filename)

    data: dict[str, Any] = {}

    # D01 - split
    data["split"] = derive_split_from_path(original_path)

    # D08 - capture_method (KI-005)
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # D02 - domain_level1 (KI-007)
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
        data["domain_detection_method"] = v1_data.get("domain_detection_method", "none")

    # D03/D04 - language/script
    data.update(_resolve_realdae_language(llm))

    # D05 - script_family
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # D06 - Layout detections (KI-001)
    standardized_layout, layout_fields = _resolve_realdae_layout(layout_dets, v1_data)
    data["layout_detections"] = standardized_layout
    data.update(layout_fields)

    # D07 - Content flags (KI-002/003/006)
    active_layout = data.get("layout_detections", [])
    flags = derive_content_flags(active_layout)
    data["has_table"] = flags["has_table"]
    data["has_figure"] = flags["has_figure"]
    data["has_formula"] = flags["has_formula"]
    data["has_code"] = flags["has_code"]

    # D12 - has_handwriting (KI-004: non-synthetic, trust LLM as soft label)
    if llm and llm.get("has_handwriting") is not None:
        data["has_handwriting"] = bool(llm.get("has_handwriting", False))
    else:
        data["has_handwriting"] = False

    data["has_signature"] = False
    data["handwriting_present"] = data["has_handwriting"]
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+llm_vision"
    data["content_flags_confidence"] = 0.70

    # D10 - orientation
    data.update(_resolve_realdae_orientation(llm))

    # D09 - text content from OCR
    data.update(_resolve_realdae_ocr(ocr_rec))

    # D11 - color mode
    data["image_properties_color_mode"] = "color"

    # Text scope
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )
    data["text_scope"] = v1_data.get("text_scope", "printed")

    # Additional derived fields
    data["dataset_short_code"] = DATASET_NAME

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

    # Reliability summary (must be last)
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _track_realdae_sample_stats(
    stats: dict[str, Any],
    filename: str,
    filename_stem: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename in layout_index:
        stats["layout_matched"] += 1
    if filename in ocr_index:
        stats["ocr_matched"] += 1

    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "UNKNOWN")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1
    stats["capture_method_dist"][integrated_data.get("capture_method", "unknown")] += 1
    stats["content_type_dist"][
        integrated_data.get("text_scope_content_type", "unknown")
    ] += 1
    stats["orientation_dist"][integrated_data.get("orientation_class", 0)] += 1

    _track_realdae_flag_counts(stats, integrated_data)


def _track_realdae_flag_counts(
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


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for idx, ver in enumerate(versions):
        if ver.get("version") == version_number:
            versions[idx] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Iterates over every sample in metadata, calls integrate_sample(),
    tracks statistics, and (unless dry_run) writes a new enrichment
    version into each sample.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index (image_id -> record).
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
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "capture_method_dist": Counter(),
        "content_type_dist": Counter(),
        "orientation_dist": Counter(),
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

        integrated_data = integrate_sample(sample, llm_index, layout_index, ocr_index)

        _track_realdae_sample_stats(
            stats,
            filename,
            filename_stem,
            integrated_data,
            llm_index,
            layout_index,
            ocr_index,
        )

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_realdae_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + Docling GPU layout + Docling GPU OCR + "
                    "dataset documentation (capture_method, split)"
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
    for script_fam, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {script_fam:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:5d}")
    print()

    print("Capture method distribution:")
    for capture_m, count in stats["capture_method_dist"].most_common():
        print(f"  {capture_m:20s}: {count:5d}")
    print()

    print("Content type (top 10):")
    for content_t, count in stats["content_type_dist"].most_common(10):
        print(f"  {content_t:30s}: {count:5d}")
    print()

    print("Orientation distribution:")
    for orient, count in stats["orientation_dist"].most_common():
        print(f"  {orient!s:20s}: {count:5d}")
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
        help="Path to realdae_metadata.json (default: %(default)s)",
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
        help="Path to Docling layout batch directory (default: %(default)s)",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=DOCLING_OCR_DIR,
        help="Path to Docling OCR batch directory (default: %(default)s)",
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
    layout_index = load_docling_layout(args.layout_dir)
    ocr_index = load_docling_ocr(args.ocr_dir)

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

    # ----- Write output -----
    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
