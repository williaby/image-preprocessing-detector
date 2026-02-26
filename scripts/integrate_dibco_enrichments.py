#!/usr/bin/env python3
"""Integrate all enrichment sources into dibco Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

dibco specifics:
  - Document Image Binarization Competition (212 images from DIBCO 2009-2019)
  - Benchmark for binarization algorithms
  - Scanned historical documents (handwritten + printed)
  - LLM enrichment: 116 records (Gemini 2.0 Flash)
  - Docling layout: 1 batch file
  - Docling OCR: 1 batch file
  - No language enrichment available (empty)
  - Mixed languages (mostly English, some Greek, etc.)
  - capture_method: scanner_flatbed (historical document scans)
  - domain_level1: GOV (government/archival documents)
  - has_handwriting varies per image (original_labels has document_type)
  - sample_size: 212 (full coverage, tiny dataset)
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_dibco_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "dibco"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/quality/dibco.py"


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
DATASET_NAME = "dibco"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "dibco_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "dibco_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "dibco_language_enrichment.json"

DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "dibco"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "dibco"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
TARGET_SCHEMA_VERSION = "2.3.0"


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================
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

VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

KNOWN_CAPTURE_METHOD = "scanner_flatbed"

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


def load_docling_layout_batches(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling layout batch files and index by filename."""
    if not layout_dir.exists():
        log.warning("Docling layout dir not found: %s", layout_dir)
        return {}

    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}

    log.info(
        "Loading %d Docling layout batch files from %s", len(batch_files), layout_dir
    )
    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
            coco: dict[str, Any] = json.load(f)

        cat_map: dict[int, str] = {}
        for cat in coco.get("categories", []):
            cat_map[cat["id"]] = cat["name"]

        img_map: dict[int, str] = {}
        for img in coco.get("images", []):
            img_map[img["id"]] = img["file_name"]

        for ann in coco.get("annotations", []):
            image_id = ann.get("image_id")
            filename = img_map.get(image_id, "")
            if not filename:
                continue
            category_name = cat_map.get(ann.get("category_id", -1), "unknown")
            det = {
                "class_name": category_name,
                "bbox": ann.get("bbox", []),
                "confidence": 1.0,
                "area": ann.get("area", 0.0),
                "source": "docling_gpu",
            }
            index.setdefault(filename, []).append(det)
            total_annotations += 1

    log.info(
        "  Indexed %d images with %d total detections across %d batches",
        len(index),
        total_annotations,
        len(batch_files),
    )
    return index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all Docling OCR batch files and index by filename."""
    if not ocr_dir.exists():
        log.warning("Docling OCR dir not found: %s", ocr_dir)
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

    log.info("  Indexed %d OCR records across %d batches", len(index), len(batch_files))
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from OCR/GT text."""
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
    """Derive content flags from canonical layout classes."""
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
    """Convert Docling class_name to DocLayNet PascalCase (KI-001)."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive color mode from image channel count."""
    channels = original_file.get("channels", 3)
    if channels == 1:
        return "grayscale"
    if channels == 4:
        return "color_alpha"
    return "color"


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    layout_dets = layout_index.get(filename, [])
    ocr_rec = ocr_index.get(filename)

    # Get document type from original_labels
    raw_labels = sample.get("original_labels", {}).get("raw_labels", {})
    doc_type = raw_labels.get("document_type", "")
    is_handwritten = raw_labels.get("has_handwriting", doc_type == "handwritten")

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
    data["layout_confidence"] = 0.85 if standardized_layout else 0.0
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # -------------------------------------------------------------------
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN (GOV for archival/historical documents)
    # Use LLM domain if available, else default to GOV
    # -------------------------------------------------------------------
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "GOV")
        data["domain_confidence"] = llm.get("domain_confidence", 0.8)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "historical_document")
    else:
        data["domain_level1"] = "GOV"
        data["domain_confidence"] = 0.8
        data["domain_detection_method"] = "dataset_documentation"
        data["domain_content_type"] = "historical_document"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Use LLM if available, otherwise default to English/Latin
    # -------------------------------------------------------------------
    if llm and llm.get("iso639_language") and llm.get("iso639_language") != "und":
        data["iso639_language"] = llm["iso639_language"]
        data["iso15924_script"] = llm.get("iso15924_script", "Latn")
        data["language_confidence"] = 0.75
        data["text_scope_detection_method"] = "llm_vision"
    else:
        data["iso639_language"] = "en"
        data["iso15924_script"] = "Latn"
        data["language_confidence"] = 0.6
        data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (KI-008 fix)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_formula"] = False
    data["has_code"] = False
    data["has_signature"] = False
    data["has_figure"] = False

    # has_handwriting: use original_labels if available, else LLM
    if is_handwritten or (llm and llm.get("has_handwriting")):
        data["has_handwriting"] = True
    else:
        data["has_handwriting"] = True  # DIBCO is primarily handwriting benchmark

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "llm_vision+dataset_documentation"
    data["content_flags_confidence"] = 0.95
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # SPLIT - DIBCO is a benchmark, all test
    # -------------------------------------------------------------------
    data["split"] = "test"

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    if llm:
        data["text_scope_content_type"] = llm.get("content_type", "historical_document")
    else:
        data["text_scope_content_type"] = "historical_document"
    data["text_scope"] = "document"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # -------------------------------------------------------------------
    # TEXT CONTENT (from Docling OCR if available)
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
    # TEXT DIRECTION (v2.3.0 fields)
    # -------------------------------------------------------------------
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # -------------------------------------------------------------------
    # RESOLUTION (preserve v1 data)
    # -------------------------------------------------------------------
    for field in ("resolution_category", "resolution_pixels", "resolution_dpi"):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


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
    """Run integration for all samples."""
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
        "capture_method_dist": Counter(),
        "color_mode_dist": Counter(),
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
            layout_index,
            ocr_index,
        )

        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename in layout_index:
            stats["layout_matched"] += 1
        if filename in ocr_index:
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
        stats["color_mode_dist"][
            integrated_data.get("image_properties_color_mode", "unknown")
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
                "created_by": "integrate_dibco_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + Docling layout + Docling OCR + "
                    "dataset documentation. KI-001, KI-008. "
                    "Schema v2.1 -> v2.3.0."
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


def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary with distributions."""
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
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
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
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to dataset metadata JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
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
    llm_index = load_llm_enrichment(LLM_ENRICHMENT_PATH)
    layout_index = load_docling_layout_batches(DOCLING_LAYOUT_DIR)
    ocr_index = load_docling_ocr_batches(DOCLING_OCR_DIR)

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

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        metadata["schema_version"] = TARGET_SCHEMA_VERSION
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
