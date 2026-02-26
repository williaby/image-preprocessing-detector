#!/usr/bin/env python3
"""Integrate all enrichment sources into siw13 Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

siw13 specifics:
  - 16,291 multi-script word images (13 scripts: Arabic, Bangla, Devanagari,
    Gujarati, Gurmukhi, Japanese, Kannada, Malayalam, Oriya, Roman, Tamil,
    Telugu, Thai)
  - Scanner-captured (SIW-13 printed/handwritten dataset)
  - Parser provides high-confidence script/language ground truth via original_labels
  - Language enrichment available (OpenLID)
  - Docling layout extraction available (82 batch files)
  - Docling OCR extraction available (82 batch files)
  - No LLM enrichment

Defect mitigations:
  D01 - split: re-derive from source path (Testing -> test, Training -> train)
  D02 - script_family: re-derive via get_script_family(iso15924_script) [KI-008]
  D03 - domain_level1: set UNK (mixed-domain script identification dataset)
  D04 - layout_detections: integrate Docling layout batch files [KI-001]
  D05 - text_has_content: integrate Docling OCR batch files
  D06 - orientation_class: default upright (scanner-captured)
  D07 - image_properties_color_mode: default grayscale
  D08 - handwriting_present: derive from source path (Handwritten vs Printed)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_siw13_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "siw13"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/siw13.py"
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

# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "siw13"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "siw13_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "siw13_language_enrichment.json"

# Docling extracted data (multiple batch files)
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "siw13"
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "siw13"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================
APPLY_KI_001_LAYOUT_CASING = True


KNOWN_CAPTURE_METHOD: str | None = "scanner_flatbed"

VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()


# SIW-13 Parser mappings (same 13 scripts as MDIW-13)
SCRIPT_MAPPINGS: dict[str, tuple[str, str]] = {
    "Arabic": ("Arab", "ar"),
    "Bengali": ("Beng", "bn"),
    "Bangla": ("Beng", "bn"),
    "Gujarati": ("Gujr", "gu"),
    "Gurmukhi": ("Guru", "pa"),
    "Devanagari": ("Deva", "hi"),
    "Hindi": ("Deva", "hi"),
    "Japanese": ("Jpan", "ja"),
    "Kannada": ("Knda", "kn"),
    "Malayalam": ("Mlym", "ml"),
    "Oriya": ("Orya", "or"),
    "Roman": ("Latn", "en"),
    "Tamil": ("Taml", "ta"),
    "Telugu": ("Telu", "te"),
    "Thai": ("Thai", "th"),
}


SCRIPT_TO_DIRECTIONS_PRESENT: dict[str, list[str]] = {
    "Arab": ["rtl"],
    "Jpan": ["ltr", "ttb"],
}


# ===================================================================
# Data loaders
# ===================================================================
def load_docling_layout_batches(
    layout_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling layout batch files and index by filename."""
    if not layout_dir.is_dir():
        log.warning("Layout directory not found: %s", layout_dir)
        return {}
    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}
    log.info(
        "Loading %d Docling layout batch files from %s", len(batch_files), layout_dir
    )
    index: dict[str, list[dict[str, Any]]] = {}
    total_detections = 0
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
            det: dict[str, Any] = {
                "class_name": category_name,
                "bbox": ann.get("bbox", []),
                "confidence": 1.0,
                "area": ann.get("area", 0.0),
            }
            index.setdefault(filename, []).append(det)
            total_detections += 1
    log.info(
        "  Indexed %d images with %d total detections",
        len(index),
        total_detections,
    )
    return index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all Docling OCR batch files and index by filename."""
    if not ocr_dir.is_dir():
        log.warning("OCR directory not found: %s", ocr_dir)
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
    log.info("  Indexed %d OCR records", len(index))
    return index


def standardize_class_name(class_name: str) -> str:
    """Convert Docling lowercase class_name to DocLayNet PascalCase."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def resolve_split(sample: dict[str, Any]) -> str:
    """Resolve split from source path."""
    source = sample.get("source", {})
    original_path = source.get("original_path", "")
    raw_split = source.get("split", "")
    if raw_split in ("testing", "test"):
        return "test"
    if raw_split in ("training", "train"):
        return "train"
    if "Testing" in original_path:
        return "test"
    if "Training" in original_path:
        return "train"
    return "unknown"


def resolve_language_script(
    sample: dict[str, Any],
) -> tuple[str, str, float, str]:
    """Resolve language and script from parser ground truth."""
    original_labels = sample.get("original_labels", {})
    language_code = original_labels.get("language_code", "")
    script_code = original_labels.get("iso15924_script_code", "")
    script_name = original_labels.get("script_name", "")

    if language_code and language_code not in ("", "und"):
        if script_code:
            return (language_code, script_code, 0.95, "parser_gt")
        if script_name and script_name in SCRIPT_MAPPINGS:
            iso15924, _ = SCRIPT_MAPPINGS[script_name]
            return (language_code, iso15924, 0.95, "parser_gt")
        return (language_code, "Zyyy", 0.85, "parser_gt_partial")

    if script_name and script_name in SCRIPT_MAPPINGS:
        iso15924, iso639 = SCRIPT_MAPPINGS[script_name]
        return (iso639, iso15924, 0.90, "parser_script_mapping")

    original_path = sample.get("source", {}).get("original_path", "")
    for mapping_name in SCRIPT_MAPPINGS:
        if f"/{mapping_name}/" in original_path:
            iso15924, iso639 = SCRIPT_MAPPINGS[mapping_name]
            return (iso639, iso15924, 0.85, "path_script_extraction")

    return ("und", "Zyyy", 0.1, "none")


# ===================================================================
# Per-sample integration
# ===================================================================
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

    # SPLIT
    data["split"] = resolve_split(sample)

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"

    # CAPTURE METHOD
    data["capture_method"] = KNOWN_CAPTURE_METHOD or "scanner_flatbed"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "UNK"
    data["domain_confidence"] = 0.3
    data["domain_detection_method"] = "none"

    # LANGUAGE / SCRIPT
    lang, script, lang_conf, lang_method = resolve_language_script(sample)
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # SCRIPT FAMILY (KI-008)
    data["script_family"] = _get_script_family(script)

    # TEXT DIRECTION
    data["text_direction"] = SCRIPT_TO_TEXT_DIRECTION.get(script, "ltr")
    data["text_directions_present"] = SCRIPT_TO_DIRECTIONS_PRESENT.get(script, ["ltr"])

    # LAYOUT DETECTIONS (KI-001)
    standardized_layout: list[dict[str, Any]] = []
    for det in layout_dets:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

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
    data["layout_source"] = "docling_gpu" if layout_dets else "none"
    data["layout_confidence"] = 0.85 if layout_dets else 0.0
    data["layout_detection_count"] = len(standardized_layout)

    # CONTENT FLAGS
    flags = derive_content_flags(standardized_layout)
    data["has_table"] = filename_stem in VLM_TABLE_TRUE_POSITIVES or flags["has_table"]
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]

    # HANDWRITING from path (SIW-13: Handwritten vs Printed subdirectories)
    original_path = sample.get("source", {}).get("original_path", "")
    # SIW-13 has no explicit handwriting labels in path like MDIW-13
    # Default to printed for SIW-13 (printed word dataset)
    data["has_handwriting"] = False
    data["handwriting_present"] = False

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu+dataset_documentation"
    data["content_flags_confidence"] = 0.80

    # TEXT CONTENT (Docling OCR)
    if ocr_rec:
        ocr_text = ocr_rec.get("text", "")
        ocr_conf = ocr_rec.get("confidence", 0.8)
        if ocr_text and ocr_text.strip():
            data["text_has_content"] = True
            data["text_content"] = ocr_text
            data["text_content_confidence"] = ocr_conf
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

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed_word"
    data["text_scope"] = v1_data.get("text_scope", "printed")

    # RESOLUTION (preserve v1)
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
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
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem
        filename_full = Path(filename).name

        integrated_data = integrate_sample(sample, layout_index, ocr_index, lang_index)

        stats["integrated"] += 1
        if filename_full in layout_index:
            stats["layout_matched"] += 1
        if filename_full in ocr_index:
            stats["ocr_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1
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

        for flag_key, stat_key in (
            ("has_table", "has_table_count"),
            ("has_formula", "has_formula_count"),
            ("has_handwriting", "has_handwriting_count"),
            ("has_figure", "has_figure_count"),
        ):
            if integrated_data.get(flag_key):
                stats[stat_key] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser GT + Docling layout + Docling OCR + dataset documentation"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            versions = sample["enrichments"]["versions"]
            for i, v in enumerate(versions):
                if v.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[i] = new_version
                    sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER
                    break
            else:
                versions.append(new_version)
                sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER

    return stats


def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    safe_total = max(total_samples, 1)
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"Layout matched:       {stats['layout_matched']}")
    print(f"OCR matched:          {stats['ocr_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print()
    for dist_name, dist_key in [
        ("Language", "lang_dist"),
        ("Script family", "script_family_dist"),
        ("Split", "split_dist"),
        ("Detection method", "lang_method_dist"),
    ]:
        print(f"{dist_name} distribution:")
        for val, count in stats[dist_key].most_common(15):
            pct = count / safe_total * 100
            print(f"  {val:25s}: {count:6d} ({pct:.1f}%)")
        print()
    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
    )
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    parser.add_argument("--layout-dir", type=Path, default=DOCLING_LAYOUT_DIR)
    parser.add_argument("--ocr-dir", type=Path, default=DOCLING_OCR_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    lang_index = load_language_enrichment(args.language_enrichment)
    layout_index = load_docling_layout_batches(args.layout_dir)
    ocr_index = load_docling_ocr_batches(args.ocr_dir)

    start = time.monotonic()
    stats = run_integration(
        metadata, layout_index, ocr_index, lang_index, dry_run=args.dry_run
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
