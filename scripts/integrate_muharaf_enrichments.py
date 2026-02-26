#!/usr/bin/env python3
"""Integrate all enrichment sources into muharaf Layer 2 metadata.

muharaf specifics:
  - 25,711 Arabic handwritten-cursive line images
  - Scanner-captured, all handwritten-cursive, RTL Arabic
  - LLM enrichment available, language enrichment, Docling layout (129) + OCR (129)
  - KI-009: LLM language > language_enrichment > docs

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_muharaf_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "muharaf"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/muharaf.py"
)


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

from l2_integration_utils import (
    compute_reliability_summary,
    compute_text_statistics,
    derive_content_flags,
    load_language_enrichment,
    load_llm_enrichment,
    load_metadata,
    DOCLING_TO_DOCLAYNET,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATASET_NAME = "muharaf"
IS_SYNTHETIC_DATASET = False
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "muharaf_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "muharaf_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "muharaf_language_enrichment.json"
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "muharaf"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "muharaf"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
APPLY_KI_001_LAYOUT_CASING = True
KNOWN_CAPTURE_METHOD: str | None = "scanner"
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()


def load_docling_layout_batches(d: Path) -> dict[str, list[dict[str, Any]]]:
    """Load layout batches."""
    if not d.is_dir():
        return {}
    idx: dict[str, list[dict[str, Any]]] = {}
    for bp in sorted(d.glob("layout_batch_*.json")):
        with open(bp, encoding="utf-8") as f:
            coco: dict[str, Any] = json.load(f)
        cm = {c["id"]: c["name"] for c in coco.get("categories", [])}
        im = {i["id"]: i["file_name"] for i in coco.get("images", [])}
        for a in coco.get("annotations", []):
            fn = im.get(a.get("image_id"), "")
            if fn:
                idx.setdefault(fn, []).append(
                    {
                        "class_name": cm.get(a.get("category_id", -1), "unknown"),
                        "bbox": a.get("bbox", []),
                        "confidence": 1.0,
                        "area": a.get("area", 0.0),
                    }
                )
    log.info("  Layout: %d images", len(idx))
    return idx


def load_docling_ocr_batches(d: Path) -> dict[str, dict[str, Any]]:
    """Load OCR batches."""
    if not d.is_dir():
        return {}
    idx: dict[str, dict[str, Any]] = {}
    for bp in sorted(d.glob("ocr_batch_*.jsonl")):
        with open(bp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r: dict[str, Any] = json.loads(line)
                if r.get("success"):
                    fn = Path(r.get("source", "")).name
                    if fn:
                        idx[fn] = r
    log.info("  OCR: %d records", len(idx))
    return idx


def standardize_class_name(cn: str) -> str:
    """Standardize class name (KI-001)."""
    return DOCLING_TO_DOCLAYNET.get(cn, cn) if APPLY_KI_001_LAYOUT_CASING else cn


def integrate_sample(
    s: dict[str, Any],
    llm_idx: dict[str, dict[str, Any]],
    la: dict[str, list[dict[str, Any]]],
    oc: dict[str, dict[str, Any]],
    _li: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Integrate single sample."""
    fn = s["source"]["original_filename"]
    stem = Path(fn).stem
    full = Path(fn).name
    v1: dict[str, Any] = {}
    if s["enrichments"]["versions"]:
        v1 = s["enrichments"]["versions"][-1].get("data", {})
    llm = llm_idx.get(stem)
    layout_dets = la.get(full, [])
    ocr_rec = oc.get(full)
    data: dict[str, Any] = {}

    # Split: muharaf has no official splits
    data["split"] = "unknown"
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"
    data["capture_method"] = "scanner"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # Domain: from LLM if available
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
    else:
        data["domain_level1"] = v1.get("domain_level1", "UNK")
        data["domain_confidence"] = v1.get("domain_confidence", 0.3)
        data["domain_detection_method"] = "none"

    # Language: always Arabic for muharaf (KI-009: dataset documentation > LLM)
    data["iso639_language"] = "ar"
    data["iso15924_script"] = "Arab"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Arab")
    data["text_direction"] = "rtl"
    data["text_directions_present"] = ["rtl"]

    # Layout
    std: list[dict[str, Any]] = []
    for d in layout_dets:
        nd = dict(d)
        orig = d.get("class_name", "")
        nd["class_name"] = standardize_class_name(orig)
        if not nd.get("source_label"):
            nd["source_label"] = orig
        std.append(nd)
    if not std:
        for d in v1.get("layout_detections", []):
            nd = dict(d)
            orig = d.get("class_name", "")
            nd["class_name"] = standardize_class_name(orig)
            if not nd.get("source_label"):
                nd["source_label"] = orig
            std.append(nd)
    data["layout_detections"] = std
    data["layout_source"] = "docling_gpu" if layout_dets else "none"
    data["layout_confidence"] = 0.85 if layout_dets else 0.0
    data["layout_detection_count"] = len(std)

    flags = derive_content_flags(std)
    data["has_table"] = stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]
    data["has_figure"] = stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = True  # All handwritten-cursive
    data["has_signature"] = v1.get("has_signature", False)
    data["has_code"] = flags["has_code"]
    data["handwriting_present"] = True
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+llm_vision+dataset_documentation"
    data["content_flags_confidence"] = 0.90

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

    data["image_properties_color_mode"] = v1.get(
        "image_properties_color_mode", "grayscale"
    )
    data["text_scope_content_type"] = "handwritten_document"
    data["text_scope"] = v1.get("text_scope", "handwritten")
    for f in ("resolution_category", "resolution_pixels"):
        if f in v1:
            data[f] = v1[f]
    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


def run_integration(
    md: dict[str, Any],
    llm_idx: dict[str, dict[str, Any]],
    la: dict[str, list[dict[str, Any]]],
    oc: dict[str, dict[str, Any]],
    li: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
    }
    now = datetime.now(UTC).isoformat()
    for sample in md["samples"]:
        stats["total"] += 1
        fn = sample["source"]["original_filename"]
        stem = Path(fn).stem
        full = Path(fn).name
        idata = integrate_sample(sample, llm_idx, la, oc, li)
        stats["integrated"] += 1
        if stem in llm_idx:
            stats["llm_matched"] += 1
        if full in la:
            stats["layout_matched"] += 1
        if full in oc:
            stats["ocr_matched"] += 1
        if idata.get("text_has_content"):
            stats["has_text_content_count"] += 1
        stats["domain_dist"][idata.get("domain_level1", "UNK")] += 1
        if not dry_run:
            nv = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: LLM + Docling + docs",
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
    return stats


def main() -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=f"Integrate {DATASET_NAME} enrichments.")
    ap.add_argument("--metadata", type=Path, default=METADATA_PATH)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--llm-enrichment", type=Path, default=LLM_ENRICHMENT_PATH)
    ap.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    ap.add_argument("--layout-dir", type=Path, default=DOCLING_LAYOUT_DIR)
    ap.add_argument("--ocr-dir", type=Path, default=DOCLING_OCR_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Not found: %s", args.metadata)
        return 1
    md = load_metadata(args.metadata)
    llm = load_llm_enrichment(args.llm_enrichment)
    li = load_language_enrichment(args.language_enrichment)
    la = load_docling_layout_batches(args.layout_dir)
    oc = load_docling_ocr_batches(args.ocr_dir)
    t0 = time.monotonic()
    stats = run_integration(md, llm, la, oc, li, dry_run=args.dry_run)
    log.info(
        "Done in %.2fs. %d integrated, LLM: %d, Layout: %d, OCR: %d, Text: %d",
        time.monotonic() - t0,
        stats["integrated"],
        stats["llm_matched"],
        stats["layout_matched"],
        stats["ocr_matched"],
        stats["has_text_content_count"],
    )
    log.info("Domain: %s", dict(stats["domain_dist"]))
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
