#!/usr/bin/env python3
"""Integrate all enrichment sources into funsd-plus Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/integrate_tobacco800_enrichments.py

funsd-plus specifics:
  - Extended FUNSD dataset (1,139 scanned administrative forms)
  - ADF-scanned English-only documents
  - Filename-based splits: funsd_plus_train_* / funsd_plus_test_*
  - 6 DocLayout-YOLO layout batches with COCO batch ID collisions
  - 6 Docling OCR batches with ground-truth-quality text
  - Known language: English (en), Latin script
  - Domain: ADM (Administrative)
  - v2.3.0 fields: text_direction, text_directions_present

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_funsd_plus_enrichments.py --dry-run
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
DATASET_NAME = "funsd-plus"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "funsd_plus_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "funsd_plus_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "funsd_plus_language_enrichment.json"

# DocLayout-YOLO extracted data (layout + OCR)
DOCLING_EXTRACTED_DIR = REGISTRY_DIR / "extracted" / "funsd_plus"

# HuggingFace Arrow data (for filename mapping)
HF_ARROW_DIR = Path("/mnt/e/image_detection/01_base_data/forms/funsd_plus")

SCRIPT_VERSION = "1.1.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001: Layout label casing (CRITICAL) -----------------------
# funsd-plus uses DocLayout-YOLO (docstructbench schema), NOT Docling.
# Labels like "abandon", "plain text", "title" need normalization.
APPLY_KI_001_LAYOUT_CASING = True

# DocLayout-YOLO docstructbench -> DocLayNet canonical mapping
DOCLAYOUT_YOLO_TO_CANONICAL: dict[str, str] = {
    "title": "Title",
    "plain text": "Text",
    "abandon": "Abandoned",
    "figure": "Picture",
    "figure_caption": "Caption",
    "table": "Table",
    "table_caption": "Caption",
    "table_footnote": "Footnote",
    "isolate_formula": "Formula",
    "formula_caption": "Caption",
    "header": "Page-Header",
    "footer": "Page-Footer",
    "seal": "Picture",
    "code": "Code",
}

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -----------
# ADF scanner-captured forms - override from dataset documentation.
KNOWN_CAPTURE_METHOD: str | None = "scanner_adf"

# --- VLM true positive overrides (populated after Phase 6) --------
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# ===================================================================
# Content flag class mappings (canonical layout -> content flags)
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON."""
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
    # Handle both list-of-samples and single-record known_language format
    if "enrichment_type" in raw and raw.get("enrichment_type") == "known_language":
        log.info("  Known-language enrichment: %s/%s", raw.get("language"), raw.get("script"))
        return {}  # No per-image index needed; use defaults
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_docling_layout_batches(
    extracted_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Load layout annotations from COCO-format batch files.

    CRITICAL: funsd-plus has COCO batch ID collisions (all batches use
    IDs 0-199). Process each batch independently with per-batch mapping.
    """
    if not extracted_dir.exists():
        log.warning("Extracted dir not found: %s", extracted_dir)
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

        # Build PER-BATCH image_id -> filename mapping (collision-safe)
        id_to_filename: dict[int, str] = {}
        for img in batch.get("images", []):
            id_to_filename[img["id"]] = img["file_name"]

        # Index annotations by filename
        for ann in batch.get("annotations", []):
            image_id = ann.get("image_id")
            filename = id_to_filename.get(image_id, "")
            if not filename:
                continue

            detection = {
                "class_name": ann.get("category_name", ""),
                "bbox": ann.get("bbox", []),
                "confidence": ann.get("score", 0.85),
                "source_label": ann.get("category_name", ""),
                "source_schema": "docstructbench",
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
    """Load OCR text from JSONL batch files."""
    if not extracted_dir.exists():
        log.warning("Extracted dir not found: %s", extracted_dir)
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


def build_filename_mapping(arrow_dir: Path) -> dict[str, str]:
    """Build mapping from renamed filenames to HuggingFace original names.

    The base metadata uses renamed files (funsd_plus_test_0000.jpg) but the
    Docling layout/OCR extraction used original HF names (578118.png).

    Returns:
        Dict mapping renamed -> original (e.g. "funsd_plus_test_0000.jpg" -> "578118.png")
    """
    try:
        import pyarrow.ipc as ipc  # noqa: PLC0415
    except ImportError:
        log.warning("pyarrow not available; filename mapping disabled")
        return {}

    mapping: dict[str, str] = {}

    for split in ["test", "train"]:
        arrow_path = arrow_dir / split / "data-00000-of-00001.arrow"
        if not arrow_path.exists():
            log.warning("Arrow file not found: %s", arrow_path)
            continue

        with open(arrow_path, "rb") as f:
            reader = ipc.open_stream(f)
            table = reader.read_all()

        img_col = table.column("image")
        for i in range(table.num_rows):
            img = img_col[i].as_py()
            hf_name = img.get("path", "")
            renamed = f"funsd_plus_{split}_{i:04d}.jpg"
            if hf_name:
                mapping[renamed] = hf_name

        log.info("  Arrow %s: %d rows mapped", split, table.num_rows)

    log.info("Built filename mapping: %d entries", len(mapping))
    return mapping


# ===================================================================
# Helpers
# ===================================================================
def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text."""
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

    return stats


def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes."""
    canonical_classes = {
        d.get("class_name", "").upper()
        for d in detections
        if d.get("class_name")
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
    """Convert DocLayout-YOLO class_name to canonical PascalCase."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLAYOUT_YOLO_TO_CANONICAL.get(class_name, class_name)
    return class_name


def assign_split(filename: str) -> str:
    """Assign split from funsd-plus filename convention.

    Filenames follow: funsd_plus_train_NNN.jpg / funsd_plus_test_NNN.jpg
    Falls back to "train" if pattern not matched.
    """
    name_lower = filename.lower()
    if "_train_" in name_lower or "train" in name_lower:
        return "train"
    if "_test_" in name_lower or "test" in name_lower:
        return "test"
    return "train"


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    filename_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    filename_full = Path(filename).name

    # Map renamed filename -> original HuggingFace filename for batch lookups
    hf_filename = (filename_map or {}).get(filename_full, filename_full)

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)

    data: dict[str, Any] = {}

    # LAYOUT DETECTIONS (from DocLayout-YOLO batch files, collision-safe)
    # Use HF filename for batch lookup (batch files use original HF names)
    raw_detections = layout_index.get(hf_filename, [])
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
    data["layout_source"] = "doclayout_yolo" if raw_detections else "base_metadata"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # CAPTURE METHOD (known: scanner_adf from dataset documentation)
    data["capture_method"] = KNOWN_CAPTURE_METHOD or "scanner_adf"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN (known: ADM from dataset documentation)
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "ADM")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = "ADM"
        data["domain_confidence"] = 1.0
        data["domain_detection_method"] = "dataset_documentation"

    # LANGUAGE / SCRIPT (known: English, Latin)
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_known_language"
    data["language_detection_method"] = "dataset_known_language"
    data["language_is_soft_label"] = False
    data["language_provenance_tier"] = "tier_0_gt"

    # KI-008 fix: convert ISO 15924 script to script_family
    data["script_family"] = _get_script_family("Latn")

    # CONTENT FLAGS (from layout detections + LLM/v1 enrichment)
    flags = derive_content_flags(standardized_layout)

    if llm:
        data["has_table"] = bool(llm.get("has_table", False)) or flags["has_table"]
        data["has_figure"] = bool(llm.get("has_figure", False)) or flags["has_figure"]
        data["has_formula"] = bool(llm.get("has_formula", False)) or flags["has_formula"]
        data["has_handwriting"] = bool(llm.get("has_handwriting", False))
        data["has_signature"] = bool(llm.get("has_signature", False))
    else:
        # Use v1 enrichment flags as fallback
        data["has_table"] = bool(v1_data.get("has_table", False)) or flags["has_table"]
        data["has_figure"] = bool(v1_data.get("has_figure", False)) or flags["has_figure"]
        data["has_formula"] = bool(v1_data.get("has_formula", False)) or flags["has_formula"]
        data["has_handwriting"] = bool(v1_data.get("has_handwriting", False))
        data["has_signature"] = False

    data["has_code"] = flags["has_code"]

    # VLM true positive overrides (applied after Phase 6)
    if VLM_TABLE_TRUE_POSITIVES and filename_stem not in VLM_TABLE_TRUE_POSITIVES:
        data["has_table"] = False
    if VLM_FIGURE_TRUE_POSITIVES and filename_stem not in VLM_FIGURE_TRUE_POSITIVES:
        data["has_figure"] = False
    if VLM_FORMULA_TRUE_POSITIVES and filename_stem not in VLM_FORMULA_TRUE_POSITIVES:
        data["has_formula"] = False
    if VLM_HANDWRITING_TRUE_POSITIVES and filename_stem not in VLM_HANDWRITING_TRUE_POSITIVES:
        data["has_handwriting"] = False

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "doclayout_yolo+base_metadata"
    data["content_flags_confidence"] = 0.80

    data["handwriting_present"] = data["has_handwriting"]

    # ORIENTATION (scanned forms are upright/portrait)
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.95
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT (filename-based: funsd_plus_train_* / funsd_plus_test_*)
    data["split"] = assign_split(filename_full)

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # IMAGE PROPERTIES (from original_file metadata)
    color_space = sample.get("original_file", {}).get("color_space", "RGB")
    if color_space == "L":
        data["image_properties_color_mode"] = "grayscale"
    elif color_space == "1":
        data["image_properties_color_mode"] = "binarized"
    else:
        data["image_properties_color_mode"] = "color"

    # RESOLUTION (carry forward from v1)
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    # TEXT CONTENT (from Docling OCR batches - use HF filename)
    ocr_rec = ocr_index.get(hf_filename)
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

    # v2.3.0 FIELDS
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

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
    filename_map: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "capture_method_dist": Counter(),
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
            sample, llm_index, lang_index, layout_index, ocr_index,
            filename_map=filename_map,
        )

        # Match stats using HF filename for batch lookups
        hf_fn = (filename_map or {}).get(filename_full, filename_full)

        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1
        if hf_fn in layout_index:
            stats["layout_matched"] += 1
        if hf_fn in ocr_index:
            stats["ocr_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
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
                "created_by": f"integrate_{DATASET_NAME.replace('-', '_')}_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "DocLayout-YOLO layout + Docling OCR + "
                    "dataset documentation (v2.3.0)"
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

    # Bump schema version to v2.3.0
    if not dry_run:
        metadata["schema_version"] = "2.3.0"

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary with distributions."""
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
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

    print("Language distribution:")
    for lang, count in stats["lang_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
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
    """Entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata", type=Path, default=METADATA_PATH,
        help="Path to dataset metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--llm-enrichment", type=Path, default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--docling-extracted-dir", type=Path, default=DOCLING_EXTRACTED_DIR,
        help="Path to extracted data dir (default: %(default)s)",
    )
    parser.add_argument(
        "--arrow-dir", type=Path, default=HF_ARROW_DIR,
        help="Path to HuggingFace Arrow data for filename mapping (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only, do not write output",
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
    filename_map = build_filename_mapping(args.arrow_dir)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        layout_index=layout_index,
        ocr_index=ocr_index,
        filename_map=filename_map,
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
