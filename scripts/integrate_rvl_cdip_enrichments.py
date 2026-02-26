#!/usr/bin/env python3
"""Integrate all enrichment sources into rvl-cdip Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

rvl-cdip specifics:
  - 16K document classification images (subset of RVL-CDIP 400K)
  - Document types: advertisement, budget, email, file_folder, form,
    handwritten, invoice, letter, memo, news_article, presentation,
    questionnaire, resume, scientific_publication, scientific_report,
    specification
  - Has 4 enrichment sources: BASE + LLM + LANG + DOCL (Docling layout)
  - capture_method: scanner (scanned grayscale office documents)
  - domain: varies per document type (GOV, FIN, SCI, COM, etc.)
  - Docling layout labels already in PascalCase (DocLayNet categories)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_rvl_cdip_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__      = 'integrate-script'
__l4_dataset__       = 'rvl-cdip'
__l4_workstream__    = 'WS3'
__l4_parser__        = 'src/image_preprocessing_detector/annotation/parsers/document/rvl_cdip.py'



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
DATASET_NAME = "rvl-cdip"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "rvl_cdip_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "rvl-cdip_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "rvl-cdip_language_enrichment.json"

# Docling layout batches (COCO format, 160 batch files)
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "rvl-cdip"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
# Docling layout for rvl-cdip is already in PascalCase (DocLayNet standard)
# from the COCO category names. No casing conversion needed.
APPLY_KI_001_LAYOUT_CASING = False

# --- KI-002: Table detection multi-column FP (HIGH) -----------------
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# Not synthetic; use LLM detection for handwriting
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# rvl-cdip: scanned grayscale office documents
KNOWN_CAPTURE_METHOD: str | None = "scanner"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

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
    """Load LLM enrichment and index by filename stem.

    rvl-cdip LLM enrichment uses full filenames as image_id
    (e.g., 'rvl_advertisement_0000.jpg'). We index by stem.

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping filename stem to enrichment record.
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
            # Index by stem (strip extension)
            stem = Path(image_id).stem
            index[stem] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id.

    rvl-cdip language enrichment uses stems (no extension) as image_id.

    Args:
        path: Path to *_language_enrichment.json.

    Returns:
        Dict mapping image_id (stem) to language enrichment record.
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


def load_docling_layout_batches(
    layout_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling COCO layout batches and index by filename stem.

    Each batch is a COCO-format JSON with images and annotations.
    We merge all batches into a single index mapping filename stem
    to a list of layout detection dicts.

    Args:
        layout_dir: Directory containing layout_batch_*.json files.

    Returns:
        Dict mapping filename stem to list of detection dicts.
    """
    if not layout_dir.exists():
        log.warning("Docling layout dir not found: %s", layout_dir)
        return {}

    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}

    log.info("Loading %d Docling layout batches from %s", len(batch_files), layout_dir)

    # Build image_id -> filename stem mapping across all batches
    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for batch_file in batch_files:
        with open(batch_file, encoding="utf-8") as f:
            batch: dict[str, Any] = json.load(f)

        # Build image_id -> filename stem for this batch
        img_id_to_stem: dict[int, str] = {}
        for img in batch.get("images", []):
            img_id_to_stem[img["id"]] = Path(img["file_name"]).stem

        # Group annotations by image
        for ann in batch.get("annotations", []):
            img_id = ann.get("image_id")
            stem = img_id_to_stem.get(img_id, "")
            if not stem:
                continue

            det = {
                "class_name": ann.get("category_name", ""),
                "canonical_class": ann.get("category_name", ""),
                "source_label": ann.get("category_name", ""),
                "bbox": ann.get("bbox", []),
                "confidence": ann.get("confidence", 0.0),
                "source": "docling_gpu",
            }

            if stem not in index:
                index[stem] = []
            index[stem].append(det)
            total_annotations += 1

    log.info(
        "  Indexed %d images with %d total annotations",
        len(index),
        total_annotations,
    )
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


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Args:
        detections: List of layout detection dicts.

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

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Reliability summary dict.
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


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a sample.

    Priority chain:
      1. Parser GT (confidence 0.95)
      2. Language enrichment / OpenLID (confidence 0.70)
      3. LLM vision (confidence 0.65)
      4. rvl-cdip documentation fallback: English (confidence 0.80)

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    # Source 1: Parser GT
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if parser_lang and parser_lang not in ("", "und"):
        parser_script = original_labels.get("iso15924_script_code", "") or "Zyyy"
        return (parser_lang, parser_script, 0.95, "parser_gt")

    # Source 2: Language enrichment / OpenLID
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        le_script = lang_enrichment.get("script")
        le_conf = lang_enrichment.get("confidence", 0.5)
        if le_lang and le_lang != "und":
            return (le_lang, le_script or "Zyyy", min(le_conf, 0.70), "openlid_v2")

    # Source 3: LLM vision
    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return (llm_lang, llm_script or "Zyyy", 0.65, "llm_vision")

    # Source 4: rvl-cdip is predominantly English scanned documents
    return ("en", "Latn", 0.80, "dataset_documentation")


def resolve_capture_method(
    llm: dict[str, Any] | None,
) -> tuple[str, float, str]:
    """Resolve capture method.

    rvl-cdip: scanned grayscale office documents.

    Returns:
        Tuple of (capture_method, confidence, detection_method).
    """
    if KNOWN_CAPTURE_METHOD:
        return (KNOWN_CAPTURE_METHOD, 1.0, "dataset_documentation")

    if llm:
        method = llm.get("capture_method", "unknown")
        conf = llm.get("capture_confidence", 0.5)
        return (method, conf, "llm_vision")

    return ("unknown", 0.3, "none")


# ===================================================================
# RVL-CDIP document type to domain mapping
# ===================================================================
DOC_TYPE_TO_DOMAIN: dict[str, str] = {
    "advertisement": "COM",
    "budget": "FIN",
    "email": "COM",
    "file_folder": "GOV",
    "form": "GOV",
    "handwritten": "GOV",
    "invoice": "FIN",
    "letter": "COM",
    "memo": "GOV",
    "news_article": "MEDIA",
    "presentation": "COM",
    "questionnaire": "GOV",
    "resume": "COM",
    "scientific_publication": "SCI",
    "scientific_report": "SCI",
    "specification": "TECH",
}


def _extract_doc_type(filename: str) -> str:
    """Extract document type from rvl-cdip filename.

    Filenames follow pattern: rvl_{doctype}_{number}.jpg

    Args:
        filename: Original filename (e.g., 'rvl_advertisement_0000.jpg').

    Returns:
        Document type string (e.g., 'advertisement').
    """
    stem = Path(filename).stem
    # Remove 'rvl_' prefix and trailing '_NNNN' number
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0] == "rvl":
        # Rejoin middle parts (handles multi-word types like 'scientific_publication')
        doc_type = "_".join(parts[1:-1])
        return doc_type
    return ""


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    docling_layout_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (stem -> record).
        lang_index: Language enrichment index (stem -> record).
        docling_layout_index: Docling layout index (stem -> detections).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    docling_detections = docling_layout_index.get(filename_stem, [])

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS (from Docling COCO batches)
    # Already PascalCase -- no KI-001 needed
    # -------------------------------------------------------------------
    if docling_detections:
        data["layout_detections"] = docling_detections
        data["layout_source"] = "docling_gpu"
        data["layout_confidence"] = 0.85
        data["layout_detection_count"] = len(docling_detections)
    else:
        # Fall back to v1 layout if available
        v1_layout = v1_data.get("layout_detections", [])
        data["layout_detections"] = v1_layout
        data["layout_source"] = v1_data.get("layout_source", "none")
        data["layout_confidence"] = v1_data.get("layout_confidence", 0.0)
        data["layout_detection_count"] = len(v1_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (KI-005: scanner from documentation)
    # -------------------------------------------------------------------
    capture, capture_conf, capture_method_src = resolve_capture_method(llm)
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # -------------------------------------------------------------------
    # DOMAIN (from document type in filename, LLM fallback)
    # -------------------------------------------------------------------
    doc_type = _extract_doc_type(filename)
    mapped_domain = DOC_TYPE_TO_DOMAIN.get(doc_type, "")

    if mapped_domain:
        data["domain_level1"] = mapped_domain
        data["domain_confidence"] = 0.95
        data["domain_detection_method"] = "filename_mapping"
        data["domain_content_type"] = doc_type
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
    # LANGUAGE / SCRIPT (KI-009: LLM > language_enrichment > docs)
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (KI-008: re-derive from iso15924_script)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (from layout detections + KI-002..KI-006 overrides)
    # -------------------------------------------------------------------
    layout_for_flags = data.get("layout_detections", [])
    flags = derive_content_flags(layout_for_flags)

    # Conservative: use layout-derived flags + VLM corrections
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]
    data["has_figure"] = (
        filename_stem in VLM_FIGURE_TRUE_POSITIVES or flags["has_figure"]
    )
    data["has_formula"] = (
        filename_stem in VLM_FORMULA_TRUE_POSITIVES or flags["has_formula"]
    )
    data["has_handwriting"] = filename_stem in VLM_HANDWRITING_TRUE_POSITIVES
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]

    # Check if document type suggests handwriting
    if doc_type == "handwritten":
        data["has_handwriting"] = True

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+llm_vision+filename_mapping"
    data["content_flags_confidence"] = 0.85
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION (from LLM or default upright)
    # -------------------------------------------------------------------
    if llm and llm.get("orientation") is not None:
        data["orientation_class"] = llm.get("orientation", 0)
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "llm_vision"
    else:
        data["orientation_class"] = 0
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "default_upright"

    # -------------------------------------------------------------------
    # SPLIT (from source metadata)
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "unknown")

    # If split is unknown, try to infer from filename structure
    if data["split"] == "unknown":
        # rvl-cdip subset has no split info; assign proportionally
        data["split"] = "train"  # default for training subset

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )

    data["text_scope"] = v1_data.get("text_scope", "printed")

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # rvl-cdip images are predominantly grayscale scanned documents
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # -------------------------------------------------------------------
    # RESOLUTION QUALITY (preserve v1 fields)
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
    # TEXT CONTENT (no VLM text labels available)
    # -------------------------------------------------------------------
    data["text_has_content"] = False
    data["text_content"] = ""
    data["text_content_confidence"] = 0.0
    data["text_content_source"] = "none"
    data["text_statistics"] = compute_text_statistics("")

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
    docling_layout_index: dict[str, list[dict[str, Any]]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index.
        lang_index: Language enrichment index.
        docling_layout_index: Docling layout index.
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "docling_layout_matched": 0,
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
            docling_layout_index,
        )

        # Track statistics
        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1
        if filename_stem in docling_layout_index:
            stats["docling_layout_matched"] += 1

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

        # Write enrichment version
        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME.replace('-', '_')}_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + Docling layout + language enrichment + "
                    "filename mapping + dataset documentation"
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
    print(f"Total samples:            {stats['total']}")
    print(f"Integrated:               {stats['integrated']}")
    print(f"LLM matched:              {stats['llm_matched']}")
    print(f"Language matched:         {stats['lang_matched']}")
    print(f"Docling layout matched:   {stats['docling_layout_matched']}")
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
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
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
        "--docling-layout-dir",
        type=Path,
        default=DOCLING_LAYOUT_DIR,
        help="Path to Docling layout batch dir (default: %(default)s)",
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

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)
    docling_layout_index = load_docling_layout_batches(args.docling_layout_dir)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        docling_layout_index=docling_layout_index,
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
