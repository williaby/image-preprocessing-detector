#!/usr/bin/env python3
"""Integrate all enrichment sources into hindi-synth Layer 2 metadata.

hindi-synth specifics:
  - 80,008 SYNTHETIC Hindi OCR images (Devanagari script)
  - KI-004: has_handwriting=False (synthetic, LLM cannot distinguish)
  - KI-005: capture_method=synthetic (LLM misclassifies)
  - Language enrichment available, Docling layout + OCR available (161 batches)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_hindi_synth_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__      = 'integrate-script'
__l4_dataset__       = 'hindi-synth'
__l4_workstream__    = 'WS3'
__l4_parser__        = 'src/image_preprocessing_detector/annotation/parsers/multilingual/hindi_ocr_synthetic.py'



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

DATASET_NAME = "hindi-synth"
IS_SYNTHETIC_DATASET = True  # KI-004, KI-005

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "hindi_ocr_synthetic_metadata.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "hindi_ocr_synthetic_language_enrichment.json"
)
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "hindi-synth"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "hindi-synth"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

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
}

# KI-005: synthetic dataset
KNOWN_CAPTURE_METHOD: str | None = "synthetic"

VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


def load_metadata(path: Path) -> dict[str, Any]:
    """Load metadata."""
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    return {
        rec["image_id"]: rec for rec in raw.get("samples", []) if rec.get("image_id")
    }


def load_docling_layout_batches(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load Docling layout batches."""
    if not layout_dir.is_dir():
        return {}
    index: dict[str, list[dict[str, Any]]] = {}
    for bp in sorted(layout_dir.glob("layout_batch_*.json")):
        with open(bp, encoding="utf-8") as f:
            coco: dict[str, Any] = json.load(f)
        cat_map = {c["id"]: c["name"] for c in coco.get("categories", [])}
        img_map = {i["id"]: i["file_name"] for i in coco.get("images", [])}
        for ann in coco.get("annotations", []):
            fn = img_map.get(ann.get("image_id"), "")
            if fn:
                index.setdefault(fn, []).append(
                    {
                        "class_name": cat_map.get(
                            ann.get("category_id", -1), "unknown"
                        ),
                        "bbox": ann.get("bbox", []),
                        "confidence": 1.0,
                        "area": ann.get("area", 0.0),
                    }
                )
    log.info("  Layout: %d images indexed", len(index))
    return index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load Docling OCR batches."""
    if not ocr_dir.is_dir():
        return {}
    index: dict[str, dict[str, Any]] = {}
    for bp in sorted(ocr_dir.glob("ocr_batch_*.jsonl")):
        with open(bp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec: dict[str, Any] = json.loads(line)
                if rec.get("success"):
                    fn = Path(rec.get("source", "")).name
                    if fn:
                        index[fn] = rec
    log.info("  OCR: %d records indexed", len(index))
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute text stats."""
    if not text or not text.strip():
        return {"char_count": 0, "word_count": 0, "line_count": 0, "has_content": False}
    c = text.strip()
    lines = [l for l in c.split("\n") if l.strip()]
    avg = round(sum(len(l.strip()) for l in lines) / max(len(lines), 1), 1)
    stats: dict[str, Any] = {
        "char_count": len(c),
        "word_count": len(c.split()),
        "line_count": len(lines),
        "has_content": True,
        "avg_line_length": avg,
    }
    deva = len(re.findall(r"[\u0900-\u097f]", c))
    if deva > 0:
        stats["devanagari_char_count"] = deva
    latin = len(re.findall(r"[a-zA-Z]+", c))
    if latin > 0:
        stats["latin_word_count"] = latin
    return stats


def derive_content_flags(dets: list[dict[str, Any]]) -> dict[str, bool]:
    """Derive content flags."""
    cls = {d.get("class_name", "").upper() for d in dets if d.get("class_name")}
    return {
        "has_table": bool(cls & TABLE_CLASSES),
        "has_formula": bool(cls & FORMULA_CLASSES),
        "has_figure": bool(cls & FIGURE_CLASSES),
        "has_code": bool(cls & CODE_CLASSES),
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute reliability summary."""
    fields: list[dict[str, Any]] = []
    for fn, ck in [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]:
        c = data.get(ck, 0.0) or 0.0
        if c >= 0.9:
            cat = "hard_label"
        elif c >= 0.7:
            cat = "soft_label"
        elif c >= 0.5:
            cat = "active_learning"
        else:
            cat = "unreliable"
        fields.append(
            {
                "field": fn,
                "confidence": round(c, 4),
                "category": cat,
                "is_soft_label": cat == "soft_label",
            }
        )
    mf = min(fields, key=lambda f: f["confidence"])
    return {
        "min_confidence": mf["confidence"],
        "min_confidence_field": mf["field"],
        "min_confidence_category": mf["category"],
        "assessed_field_count": len(fields),
        "hard_field_count": sum(1 for f in fields if f["category"] == "hard_label"),
        "soft_field_count": sum(1 for f in fields if f["category"] == "soft_label"),
        "field_summary": fields,
        "computed_at": datetime.now(UTC).isoformat(),
    }


def standardize_class_name(cn: str) -> str:
    """Standardize layout class name."""
    return DOCLING_TO_DOCLAYNET.get(cn, cn) if APPLY_KI_001_LAYOUT_CASING else cn


def integrate_sample(
    sample: dict[str, Any],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Integrate a single sample."""
    fn = sample["source"]["original_filename"]
    stem = Path(fn).stem
    full = Path(fn).name
    v1: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1 = sample["enrichments"]["versions"][-1].get("data", {})

    layout_dets = layout_index.get(full, [])
    ocr_rec = ocr_index.get(full)
    data: dict[str, Any] = {}

    # Split
    raw_split = sample.get("source", {}).get("split", "")
    data["split"] = raw_split if raw_split in ("train", "test", "val") else "unknown"

    # Orientation
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"

    # KI-005: synthetic capture method
    data["capture_method"] = "synthetic"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # Domain: synthetic Hindi OCR -> EDU (education/language learning)
    data["domain_level1"] = v1.get("domain_level1", "EDU")
    data["domain_confidence"] = v1.get("domain_confidence", 0.7)
    data["domain_detection_method"] = "dataset_documentation"

    # Language: always Hindi/Devanagari for this dataset
    data["iso639_language"] = "hi"
    data["iso15924_script"] = "Deva"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Deva")
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # Layout
    std_layout: list[dict[str, Any]] = []
    for d in layout_dets:
        nd = dict(d)
        orig = d.get("class_name", "")
        nd["class_name"] = standardize_class_name(orig)
        if not nd.get("source_label"):
            nd["source_label"] = orig
        std_layout.append(nd)
    if not std_layout:
        for d in v1.get("layout_detections", []):
            nd = dict(d)
            orig = d.get("class_name", "")
            nd["class_name"] = standardize_class_name(orig)
            if not nd.get("source_label"):
                nd["source_label"] = orig
            std_layout.append(nd)

    data["layout_detections"] = std_layout
    data["layout_source"] = "docling_gpu" if layout_dets else "none"
    data["layout_confidence"] = 0.85 if layout_dets else 0.0
    data["layout_detection_count"] = len(std_layout)

    # Content flags - KI-004: has_handwriting=False for synthetic
    flags = derive_content_flags(std_layout)
    data["has_table"] = stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]
    data["has_figure"] = stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = False  # KI-004: synthetic
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]
    data["handwriting_present"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 0.90

    # Text content
    if ocr_rec:
        txt = ocr_rec.get("text", "")
        if txt and txt.strip():
            data["text_has_content"] = True
            data["text_content"] = txt
            data["text_content_confidence"] = ocr_rec.get("confidence", 0.8)
            data["text_content_source"] = "docling_ocr"
            data["text_statistics"] = compute_text_statistics(txt)
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

    data["image_properties_color_mode"] = v1.get("image_properties_color_mode", "color")
    data["text_scope_content_type"] = "synthetic_ocr"
    data["text_scope"] = v1.get("text_scope", "printed")
    for f in ("resolution_category", "resolution_pixels", "resolution_dpi"):
        if f in v1:
            data[f] = v1[f]

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


def run_integration(
    md: dict[str, Any],
    la: dict[str, list[dict[str, Any]]],
    oc: dict[str, dict[str, Any]],
    li: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "has_table_count": 0,
        "has_handwriting_count": 0,
    }
    now = datetime.now(UTC).isoformat()
    report_interval = 20000
    for sample in md["samples"]:
        stats["total"] += 1
        fn = sample["source"]["original_filename"]
        full = Path(fn).name
        idata = integrate_sample(sample, la, oc, li)
        stats["integrated"] += 1
        if full in la:
            stats["layout_matched"] += 1
        if full in oc:
            stats["ocr_matched"] += 1
        if idata.get("text_has_content"):
            stats["has_text_content_count"] += 1
        stats["split_dist"][idata.get("split", "unknown")] += 1
        stats["lang_dist"][idata.get("iso639_language", "und")] += 1
        stats["script_family_dist"][idata.get("script_family", "unknown")] += 1
        if idata.get("has_table"):
            stats["has_table_count"] += 1
        if not dry_run:
            nv = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: Docling + docs + KI-004/005",
                "script_version": SCRIPT_VERSION,
                "data": idata,
            }
            vs = sample["enrichments"]["versions"]
            replaced = False
            for i, v in enumerate(vs):
                if v.get("version") == ENRICHMENT_VERSION_NUMBER:
                    vs[i] = nv
                    replaced = True
                    break
            if not replaced:
                vs.append(nv)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER
        if stats["total"] % report_interval == 0:
            log.info("  Processed %d / %d", stats["total"], len(md["samples"]))
    return stats


def main() -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=f"Integrate {DATASET_NAME} enrichments.")
    ap.add_argument("--metadata", type=Path, default=METADATA_PATH)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--layout-dir", type=Path, default=DOCLING_LAYOUT_DIR)
    ap.add_argument("--ocr-dir", type=Path, default=DOCLING_OCR_DIR)
    ap.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Not found: %s", args.metadata)
        return 1
    md = load_metadata(args.metadata)
    li = load_language_enrichment(args.language_enrichment)
    la = load_docling_layout_batches(args.layout_dir)
    oc = load_docling_ocr_batches(args.ocr_dir)
    t0 = time.monotonic()
    stats = run_integration(md, la, oc, li, dry_run=args.dry_run)
    log.info(
        "Done in %.2fs. Integrated: %d, Layout: %d, OCR: %d, Text: %d",
        time.monotonic() - t0,
        stats["integrated"],
        stats["layout_matched"],
        stats["ocr_matched"],
        stats["has_text_content_count"],
    )
    log.info("Splits: %s", dict(stats["split_dist"]))
    if args.dry_run:
        log.info("Dry run")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(md, f, indent=2, ensure_ascii=False)
        log.info("Written %d samples to %s", len(md["samples"]), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
