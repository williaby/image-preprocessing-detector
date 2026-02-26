#!/usr/bin/env python3
"""Integrate all enrichment sources into invoices-kg Layer 2 metadata.

TEMPLATE VERSION: 1.1.0

invoices-kg specifics:
  - 1,414 invoice images from Kaggle (mostly born-digital, some scanned).
  - FIN domain, primarily English
  - LLM + language + Docling layout enrichment available
  - Docling layout uses PascalCase DocLayNet classes

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_invoices_kg_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "invoices-kg"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py"
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
DATASET_NAME = "invoices-kg"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "invoices-kg_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "invoices_kg_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "invoices_kg_language_enrichment.json"
)
DOCLING_LAYOUT_PATH = (
    REGISTRY_DIR / "extracted" / "invoices-kaggle" / "layout_batch_0.json"
)

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================
APPLY_KI_001_LAYOUT_CASING = False

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

KNOWN_CAPTURE_METHOD: str | None = "born_digital"


# ===================================================================
# Content flag class mappings
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA"}
FIGURE_CLASSES = {"PICTURE"}
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
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_docling_layout(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load Docling layout (COCO format) and index by filename."""
    if not path.exists():
        log.warning("Docling layout not found: %s", path)
        return {}
    log.info("Loading Docling layout from %s", path)
    with open(path, encoding="utf-8") as f:
        coco: dict[str, Any] = json.load(f)
    cat_map: dict[int, str] = {}
    for cat in coco.get("categories", []):
        cat_map[cat["id"]] = cat["name"]
    img_map: dict[int, str] = {}
    for img in coco.get("images", []):
        img_map[img["id"]] = img["file_name"]
    index: dict[str, list[dict[str, Any]]] = {}
    for ann in coco.get("annotations", []):
        image_id = ann.get("image_id")
        fn = img_map.get(image_id, "")
        if not fn:
            continue
        category_name = cat_map.get(ann.get("category_id", -1), "unknown")
        det = {
            "class_name": category_name,
            "bbox": ann.get("bbox", []),
            "confidence": 1.0,
            "source": "docling_gpu",
            "area": ann.get("area", 0.0),
        }
        index.setdefault(fn, []).append(det)
    log.info(
        "  Indexed %d images with %d detections",
        len(index),
        sum(len(v) for v in index.values()),
    )
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics."""
    if not text or text.strip() == "":
        return {"char_count": 0, "word_count": 0, "line_count": 0, "has_content": False}
    clean_text = text.strip()
    lines = clean_text.split("\n")
    non_empty_lines = [ln for ln in lines if ln.strip()]
    words = clean_text.split()
    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))
    avg_line_len = 0.0
    if non_empty_lines:
        avg_line_len = round(
            sum(len(ln.strip()) for ln in non_empty_lines) / len(non_empty_lines), 1
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
def derive_content_flags(detections: list[dict[str, Any]]) -> dict[str, bool]:
    """Derive content flags from canonical layout classes."""
    canonical_classes = {
        d.get("class_name", "").upper() for d in detections if d.get("class_name")
    }
    return {
        "has_table": bool(canonical_classes & TABLE_CLASSES),
        "has_formula": bool(canonical_classes & FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & FIGURE_CLASSES),
        "has_code": bool(canonical_classes & CODE_CLASSES),
    }


def standardize_class_name(class_name: str) -> str:
    """Convert layout class_name to DocLayNet PascalCase."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary."""
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


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    layout_dets = layout_index.get(filename, [])

    data: dict[str, Any] = {}

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "train")
    if data["split"] == "unknown":
        data["split"] = "train"

    # CAPTURE METHOD
    data["capture_method"] = "born_digital"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "FIN")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "FIN")
        data["domain_confidence"] = 0.95
        data["domain_detection_method"] = "dataset_documentation"

    # LANGUAGE / SCRIPT
    if lang_enrichment:
        le_lang = lang_enrichment.get("language", "en")
        le_script = lang_enrichment.get("script", "Latn")
        le_conf = lang_enrichment.get("confidence", 0.70)
        if le_lang and le_lang != "und":
            data["iso639_language"] = le_lang
            data["iso15924_script"] = le_script or "Latn"
            data["language_confidence"] = min(le_conf, 0.70)
            data["text_scope_detection_method"] = "openlid_v2"
        elif llm:
            llm_lang = llm.get("iso639_language", "en")
            llm_script = llm.get("iso15924_script", "Latn")
            if llm_lang and llm_lang != "und":
                data["iso639_language"] = llm_lang
                data["iso15924_script"] = llm_script or "Latn"
                data["language_confidence"] = 0.65
                data["text_scope_detection_method"] = "llm_vision"
            else:
                data["iso639_language"] = "en"
                data["iso15924_script"] = "Latn"
                data["language_confidence"] = 0.95
                data["text_scope_detection_method"] = "dataset_documentation"
        else:
            data["iso639_language"] = "en"
            data["iso15924_script"] = "Latn"
            data["language_confidence"] = 0.95
            data["text_scope_detection_method"] = "dataset_documentation"
    elif llm:
        llm_lang = llm.get("iso639_language", "en")
        llm_script = llm.get("iso15924_script", "Latn")
        if llm_lang and llm_lang != "und":
            data["iso639_language"] = llm_lang
            data["iso15924_script"] = llm_script or "Latn"
            data["language_confidence"] = 0.65
            data["text_scope_detection_method"] = "llm_vision"
        else:
            data["iso639_language"] = "en"
            data["iso15924_script"] = "Latn"
            data["language_confidence"] = 0.95
            data["text_scope_detection_method"] = "dataset_documentation"
    else:
        data["iso639_language"] = "en"
        data["iso15924_script"] = "Latn"
        data["language_confidence"] = 0.95
        data["text_scope_detection_method"] = "dataset_documentation"

    # KI-008: script_family
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # v2.3.0: TEXT DIRECTION
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # LAYOUT DETECTIONS
    standardized_layout: list[dict[str, Any]] = []
    for det in layout_dets:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        mapped = standardize_class_name(original_class)
        new_det["class_name"] = mapped
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)
    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # CONTENT FLAGS
    if cfg_has_docling := True:
        flags = derive_content_flags(standardized_layout)
        data["has_table"] = flags["has_table"]
        data["has_formula"] = flags["has_formula"]
        data["has_figure"] = flags["has_figure"]
        data["has_code"] = flags["has_code"]
    data["has_handwriting"] = False
    data["has_signature"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu"
    data["content_flags_confidence"] = 0.85
    data["handwriting_present"] = data["has_handwriting"]

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # RESOLUTION (preserve v1)
    for field in ("resolution_category", "resolution_pixels", "resolution_dpi"):
        if field in v1_data:
            data[field] = v1_data[field]

    # TEXT CONTENT
    data["text_has_content"] = False
    data["text_content"] = ""
    data["text_content_confidence"] = 0.0
    data["text_content_source"] = "none"
    data["text_statistics"] = compute_text_statistics("")

    data["dataset_short_code"] = DATASET_NAME
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
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "layout_matched": 0,
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
        integrated_data = integrate_sample(sample, llm_index, lang_index, layout_index)
        stats["integrated"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        for flag in ("has_table", "has_formula", "has_handwriting", "has_figure"):
            if integrated_data.get(flag):
                stats[f"{flag}_count"] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": f"Integrated enrichment {ENRICHMENT_VERSION_TAG}",
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
    """Print integration summary."""
    safe_total = max(total_samples, 1)
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total: {stats['total']}, Integrated: {stats['integrated']}")
    print(f"Domain: {dict(stats['domain_dist'])}")
    print(
        f"has_table: {stats['has_table_count']}, has_handwriting: {stats['has_handwriting_count']}"
    )
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Integrate enrichments into {DATASET_NAME} metadata.",
    )
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--llm-enrichment", type=Path, default=LLM_ENRICHMENT_PATH)
    parser.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    parser.add_argument("--layout", type=Path, default=DOCLING_LAYOUT_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)
    layout_index = load_docling_layout(args.layout)

    start = time.monotonic()
    stats = run_integration(
        metadata, llm_index, lang_index, layout_index, dry_run=args.dry_run
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
