#!/usr/bin/env python3
"""Integrate all enrichment sources into cvsi Layer 2 metadata.

TEMPLATE VERSION: 1.1.0

cvsi specifics:
  - 10,715 Camera-captured Video Script Identification images (10 scripts)
  - Camera/smartphone captured (scene text video frames)
  - Parser provides script/language ground truth via original_labels
  - Language enrichment available (OpenLID)
  - Docling layout extraction available (54 batch files)
  - Docling OCR extraction available (54 batch files)
  - No LLM enrichment

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_cvsi_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "cvsi"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/cvsi.py"
)


import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
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
    load_metadata,
    DOCLING_TO_DOCLAYNET,
    SCRIPT_TO_TEXT_DIRECTION,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATASET_NAME = "cvsi"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "cvsi_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "cvsi_language_enrichment.json"
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "cvsi"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "cvsi"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

APPLY_KI_001_LAYOUT_CASING = True


# CVSI is camera-captured scene text (video frames)
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()


# CVSI script mappings
SCRIPT_MAPPINGS: dict[str, tuple[str, str]] = {
    "Arabic": ("Arab", "ar"),
    "Bengali": ("Beng", "bn"),
    "Bangla": ("Beng", "bn"),
    "Gujarati": ("Gujr", "gu"),
    "Gurmukhi": ("Guru", "pa"),
    "Devanagari": ("Deva", "hi"),
    "Hindi": ("Deva", "hi"),
    "Kannada": ("Knda", "kn"),
    "Malayalam": ("Mlym", "ml"),
    "Oriya": ("Orya", "or"),
    "Roman": ("Latn", "en"),
    "Tamil": ("Taml", "ta"),
    "Telugu": ("Telu", "te"),
    "Thai": ("Thai", "th"),
    "English": ("Latn", "en"),
}

SCRIPT_TO_DIRECTIONS_PRESENT: dict[str, list[str]] = {
    "Arab": ["rtl"],
    "Jpan": ["ltr", "ttb"],
}


def load_docling_layout_batches(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling layout batch files and index by filename."""
    if not layout_dir.is_dir():
        return {}
    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        return {}
    log.info("Loading %d layout batch files", len(batch_files))
    index: dict[str, list[dict[str, Any]]] = {}
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
            }
            index.setdefault(filename, []).append(det)
    log.info("  Indexed %d images with layout", len(index))
    return index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all Docling OCR batch files and index by filename."""
    if not ocr_dir.is_dir():
        return {}
    batch_files = sorted(ocr_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        return {}
    log.info("Loading %d OCR batch files", len(batch_files))
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


def standardize_class_name(class_name: str) -> str:
    """Convert Docling lowercase to DocLayNet PascalCase."""
    return (
        DOCLING_TO_DOCLAYNET.get(class_name, class_name)
        if APPLY_KI_001_LAYOUT_CASING
        else class_name
    )


def resolve_split(sample: dict[str, Any]) -> str:
    """Resolve split from source."""
    raw_split = sample.get("source", {}).get("split", "")
    path = sample.get("source", {}).get("original_path", "")
    if raw_split in ("testing", "test"):
        return "test"
    if raw_split in ("training", "train"):
        return "train"
    if "Testing" in path or "Test" in path:
        return "test"
    if "Training" in path or "Train" in path:
        return "train"
    return "unknown"


def resolve_language_script(sample: dict[str, Any]) -> tuple[str, str, float, str]:
    """Resolve language and script from parser GT."""
    ol = sample.get("original_labels", {})
    lang = ol.get("language_code", "")
    script_code = ol.get("iso15924_script_code", "")
    script_name = ol.get("script_name", "")

    if lang and lang not in ("", "und"):
        if script_code:
            return (lang, script_code, 0.95, "parser_gt")
        if script_name and script_name in SCRIPT_MAPPINGS:
            return (lang, SCRIPT_MAPPINGS[script_name][0], 0.95, "parser_gt")
        return (lang, "Zyyy", 0.85, "parser_gt_partial")

    if script_name and script_name in SCRIPT_MAPPINGS:
        iso15924, iso639 = SCRIPT_MAPPINGS[script_name]
        return (iso639, iso15924, 0.90, "parser_script_mapping")

    path = sample.get("source", {}).get("original_path", "")
    for name, (iso15924, iso639) in SCRIPT_MAPPINGS.items():
        if f"/{name}/" in path:
            return (iso639, iso15924, 0.85, "path_script_extraction")

    return ("und", "Zyyy", 0.1, "none")


def integrate_sample(
    sample: dict[str, Any],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem
    filename_full = Path(filename).name

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    layout_dets = layout_index.get(filename_full, [])
    ocr_rec = ocr_index.get(filename_full)
    data: dict[str, Any] = {}

    data["split"] = resolve_split(sample)
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.5
    data["orientation_detection_method"] = "default_upright"
    data["capture_method"] = "camera_smartphone"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"
    # Scene text -> SCN domain
    data["domain_level1"] = "SCN"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "dataset_documentation"

    lang, script, lang_conf, lang_method = resolve_language_script(sample)
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method
    data["script_family"] = _get_script_family(script)
    data["text_direction"] = SCRIPT_TO_TEXT_DIRECTION.get(script, "ltr")
    data["text_directions_present"] = SCRIPT_TO_DIRECTIONS_PRESENT.get(script, ["ltr"])

    # Layout
    standardized: list[dict[str, Any]] = []
    for det in layout_dets:
        nd = dict(det)
        orig = det.get("class_name", "")
        nd["class_name"] = standardize_class_name(orig)
        if not nd.get("source_label"):
            nd["source_label"] = orig
        standardized.append(nd)
    if not standardized:
        for det in v1_data.get("layout_detections", []):
            nd = dict(det)
            orig = det.get("class_name", "")
            nd["class_name"] = standardize_class_name(orig)
            if not nd.get("source_label"):
                nd["source_label"] = orig
            standardized.append(nd)

    data["layout_detections"] = standardized
    data["layout_source"] = "docling_gpu" if layout_dets else "none"
    data["layout_confidence"] = 0.85 if layout_dets else 0.0
    data["layout_detection_count"] = len(standardized)

    flags = derive_content_flags(standardized)
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_handwriting"] = False
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]
    data["handwriting_present"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 0.80

    if ocr_rec:
        ocr_text = ocr_rec.get("text", "")
        if ocr_text and ocr_text.strip():
            data["text_has_content"] = True
            data["text_content"] = ocr_text
            data["text_content_confidence"] = ocr_rec.get("confidence", 0.8)
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

    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )
    data["text_scope_content_type"] = "scene_text"
    data["text_scope"] = v1_data.get("text_scope", "phrase")
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
    lang_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "lang_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }
    now = datetime.now(timezone.utc).isoformat()
    for sample in metadata["samples"]:
        stats["total"] += 1
        fn = sample["source"]["original_filename"]
        stem = Path(fn).stem
        full = Path(fn).name
        idata = integrate_sample(sample, layout_index, ocr_index, lang_index)
        stats["integrated"] += 1
        if full in layout_index:
            stats["layout_matched"] += 1
        if full in ocr_index:
            stats["ocr_matched"] += 1
        if stem in lang_index:
            stats["lang_matched"] += 1
        if idata.get("text_has_content"):
            stats["has_text_content_count"] += 1
        stats["domain_dist"][idata.get("domain_level1", "UNK")] += 1
        stats["split_dist"][idata.get("split", "unknown")] += 1
        stats["lang_dist"][idata.get("iso639_language", "und")] += 1
        stats["script_family_dist"][idata.get("script_family", "unknown")] += 1
        stats["lang_method_dist"][
            idata.get("text_scope_detection_method", "unknown")
        ] += 1
        for fk, sk in [
            ("has_table", "has_table_count"),
            ("has_formula", "has_formula_count"),
            ("has_handwriting", "has_handwriting_count"),
            ("has_figure", "has_figure_count"),
        ]:
            if idata.get(fk):
                stats[sk] += 1
        if not dry_run:
            nv = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: parser GT + Docling layout + OCR + docs",
                "script_version": SCRIPT_VERSION,
                "data": idata,
            }
            versions = sample["enrichments"]["versions"]
            replaced = False
            for i, v in enumerate(versions):
                if v.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[i] = nv
                    replaced = True
                    break
            if not replaced:
                versions.append(nv)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER
    return stats


def print_summary(stats: dict[str, Any], total: int) -> None:
    """Print summary."""
    st = max(total, 1)
    print(f"\n{'=' * 60}\n{DATASET_NAME} Integration Summary\n{'=' * 60}")
    print(f"Total: {stats['total']}, Integrated: {stats['integrated']}")
    print(
        f"Layout: {stats['layout_matched']}, OCR: {stats['ocr_matched']}, Lang: {stats['lang_matched']}"
    )
    print(f"Text content: {stats['has_text_content_count']}")
    for name, key in [
        ("Language", "lang_dist"),
        ("Script", "script_family_dist"),
        ("Split", "split_dist"),
    ]:
        print(f"\n{name}:")
        for v, c in stats[key].most_common(15):
            print(f"  {v:20s}: {c:6d} ({c / st * 100:.1f}%)")
    print(
        f"\nContent: table={stats['has_table_count']}, formula={stats['has_formula_count']}, "
        f"handwriting={stats['has_handwriting_count']}, figure={stats['has_figure_count']}"
    )
    print("=" * 60)


def main() -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=f"Integrate {DATASET_NAME} enrichments.")
    ap.add_argument("--metadata", type=Path, default=METADATA_PATH)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    ap.add_argument("--layout-dir", type=Path, default=DOCLING_LAYOUT_DIR)
    ap.add_argument("--ocr-dir", type=Path, default=DOCLING_OCR_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Metadata not found: %s", args.metadata)
        return 1
    md = load_metadata(args.metadata)
    li = load_language_enrichment(args.language_enrichment)
    la = load_docling_layout_batches(args.layout_dir)
    oc = load_docling_ocr_batches(args.ocr_dir)
    t0 = time.monotonic()
    stats = run_integration(md, la, oc, li, dry_run=args.dry_run)
    print_summary(stats, len(md["samples"]))
    log.info("Done in %.2fs", time.monotonic() - t0)
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
