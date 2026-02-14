#!/usr/bin/env python3
"""Integrate all enrichment sources into signatr6k Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

signatr6k specifics:
  - Signature 6K dataset (12,514 images)
  - Handwritten signatures
  - Docling layout: 63 batch files
  - Docling OCR: 63 batch files
  - No LLM enrichment, no language enrichment
  - capture_method: scanner_flatbed (scanned signature forms)
  - domain_level1: PER (personal documents)
  - has_handwriting: True (signatures)
  - has_signature: True (primary content)
  - Language: en/Latn (signatures, though mostly non-linguistic)
  - script_family fix: ltr -> latin (KI-008)
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_signatr6k_enrichments.py --dry-run
"""

from __future__ import annotations

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "signatr6k"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "signatr6k_metadata.json"
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "signatr6k"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "signatr6k"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
TARGET_SCHEMA_VERSION = "2.3.0"

APPLY_KI_001_LAYOUT_CASING = True

DOCLING_TO_DOCLAYNET: dict[str, str] = {
    "text": "Text", "list_item": "List-Item", "section_header": "Section-Header",
    "table": "Table", "picture": "Picture", "formula": "Formula", "caption": "Caption",
    "footnote": "Footnote", "page_footer": "Page-Footer", "page_header": "Page-Header",
    "title": "Title", "code": "Code",
    "checkbox_selected": "Checkbox-Selected", "checkbox_unselected": "Checkbox-Unselected",
}

KNOWN_CAPTURE_METHOD = "scanner_flatbed"

TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON."""
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_docling_layout_batches(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling layout batch files and index by filename."""
    if not layout_dir.exists():
        return {}
    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        return {}
    log.info("Loading %d Docling layout batch files", len(batch_files))
    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0
    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
            coco: dict[str, Any] = json.load(f)
        cat_map = {cat["id"]: cat["name"] for cat in coco.get("categories", [])}
        img_map = {img["id"]: img["file_name"] for img in coco.get("images", [])}
        for ann in coco.get("annotations", []):
            filename = img_map.get(ann.get("image_id"), "")
            if not filename:
                continue
            det = {
                "class_name": cat_map.get(ann.get("category_id", -1), "unknown"),
                "bbox": ann.get("bbox", []),
                "confidence": 1.0,
                "area": ann.get("area", 0.0),
                "source": "docling_gpu",
            }
            index.setdefault(filename, []).append(det)
            total_annotations += 1
    log.info("  Indexed %d images with %d detections", len(index), total_annotations)
    return index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all Docling OCR batch files and index by filename."""
    if not ocr_dir.exists():
        return {}
    batch_files = sorted(ocr_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        return {}
    log.info("Loading %d Docling OCR batch files", len(batch_files))
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
                filename = Path(rec.get("source", "")).name
                if filename:
                    index[filename] = rec
    log.info("  Indexed %d OCR records", len(index))
    return index


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive color mode from image channel count."""
    channels = original_file.get("channels", 3)
    if channels == 1:
        return "grayscale"
    if channels == 4:
        return "color_alpha"
    return "color"


def standardize_class_name(class_name: str) -> str:
    """Convert Docling class_name to DocLayNet PascalCase (KI-001)."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary."""
    fields: list[dict[str, Any]] = []
    for field_name, conf_key in [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]:
        confidence = data.get(conf_key, 0.0) or 0.0
        if confidence >= 0.9:
            category = "hard_label"
        elif confidence >= 0.7:
            category = "soft_label"
        elif confidence >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"
        fields.append({"field": field_name, "confidence": round(confidence, 4),
                        "category": category, "is_soft_label": category == "soft_label"})
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


def integrate_sample(
    sample: dict[str, Any],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    layout_dets = layout_index.get(filename, [])
    ocr_rec = ocr_index.get(filename)
    data: dict[str, Any] = {}

    # LAYOUT DETECTIONS (KI-001)
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

    # CAPTURE METHOD
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "PER"
    data["domain_confidence"] = 1.0
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "signature"

    # LANGUAGE / SCRIPT
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 0.8
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Latn")

    # CONTENT FLAGS
    data["has_table"] = False
    data["has_formula"] = False
    data["has_code"] = False
    data["has_signature"] = True  # Primary content type
    data["has_figure"] = False  # Docling Picture detections are FP on signatures
    data["has_handwriting"] = True  # Signatures are handwritten
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = True

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "unknown")

    # TEXT SCOPE
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "signature"

    # IMAGE PROPERTIES
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # TEXT CONTENT
    if ocr_rec and ocr_rec.get("text"):
        data["text_has_content"] = True
        data["text_content_confidence"] = ocr_rec.get("confidence", 0.5)
        data["text_content_source"] = "docling_ocr"
        text = ocr_rec["text"]
        data["text_statistics"] = {
            "char_count": len(text.strip()),
            "word_count": len(text.strip().split()),
            "line_count": len([l for l in text.strip().split("\n") if l.strip()]),
            "has_content": True,
        }
    else:
        # Signatures may not have readable text
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = {"char_count": 0, "word_count": 0, "line_count": 0, "has_content": False}

    # TEXT DIRECTION
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # RESOLUTION
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


def run_integration(
    metadata: dict[str, Any],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0, "integrated": 0, "layout_matched": 0, "ocr_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(), "split_dist": Counter(),
        "has_handwriting_count": 0, "has_signature_count": 0,
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]

        integrated_data = integrate_sample(sample, layout_index, ocr_index)

        stats["integrated"] += 1
        if filename in layout_index:
            stats["layout_matched"] += 1
        if filename in ocr_index:
            stats["ocr_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1
        if integrated_data.get("has_handwriting"):
            stats["has_handwriting_count"] += 1
        if integrated_data.get("has_signature"):
            stats["has_signature_count"] += 1
        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER, "created_at": now,
                "created_by": "integrate_signatr6k_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "Docling layout + OCR + dataset documentation. "
                    "KI-001, KI-008. Schema v2.1 -> v2.3.0."
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
    """Print integration summary."""
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"Layout matched:       {stats['layout_matched']}")
    print(f"OCR matched:          {stats['ocr_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print(f"Has handwriting:      {stats['has_handwriting_count']}")
    print(f"Has signature:        {stats.get('has_signature_count', 0)}")
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Integrate enrichment sources into {DATASET_NAME} metadata.",
    )
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    layout_index = load_docling_layout_batches(DOCLING_LAYOUT_DIR)
    ocr_index = load_docling_ocr_batches(DOCLING_OCR_DIR)

    start = time.monotonic()
    stats = run_integration(metadata, layout_index, ocr_index, dry_run=args.dry_run)
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
