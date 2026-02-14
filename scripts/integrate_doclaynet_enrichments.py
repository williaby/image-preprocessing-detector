#!/usr/bin/env python3
"""Integrate all enrichment sources into DocLayNet Layer 2 metadata.

Resolves 13 defects (D01-D13) identified during audit Phases 1-3:
  D01: split="unknown" -> from COCO GT membership (train/val/test)
  D02: domain_level1="UNK" -> from GT doc_category (KI-007 fix)
  D03: script_family="ltr" -> re-derive via get_script_family() (KI-008 fix)
  D04: iso639_language="en" blanket -> langdetect on GT cells text (KI-009 fix)
  D05: layout_detections partial -> preserve Docling + COCO GT content flags
  D06: text_has_content=False -> populate from GT cells text
  D07: orientation_class missing -> set 0 (born-digital, confirmed)
  D08: color_mode missing -> derive from base metadata color_space
  D09: handwriting_present missing -> set False (born-digital professional)
  D10: text_direction missing -> derive from detected script (v2.3.0)
  D11: text_directions_present missing -> from GT text analysis (v2.3.0)
  D12: schema_version v2.1 -> upgrade to v2.3.0
  D13: content_flags Docling-only -> override with COCO GT categories

Data sources:
  1. Base metadata (81,471 samples, schema v2.1)
  2. GT index (81,470 samples: langdetect + doc_category + COCO split + content)
  3. LLM enrichment (80,857 samples, fallback for domain/language)
  4. Docling layout batches (69,103 samples, already in metadata)

Prerequisites:
  Run standardize_layout_labels.py --dataset doclaynet BEFORE this script.

Usage:
    PYTHONPATH=. uv run python3 scripts/integrate_doclaynet_enrichments.py --dry-run
    PYTHONPATH=. uv run python3 scripts/integrate_doclaynet_enrichments.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
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
# Configuration
# ===================================================================
DATASET_NAME = "doclaynet"
IS_SYNTHETIC_DATASET = False
KNOWN_CAPTURE_METHOD = "born_digital"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "doclaynet_metadata.json"
GT_INDEX_PATH = Path("results/doclaynet_gt_index.json")
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "doclaynet_llm_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# Color space to color mode mapping
COLOR_SPACE_TO_MODE: dict[str, str] = {
    "RGB": "color",
    "RGBA": "color",
    "L": "grayscale",
    "1": "binarized",
    "P": "color",
    "CMYK": "color",
}


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to doclaynet_metadata.json.

    Returns:
        Full metadata dict with "samples" list.
    """
    log.info("Loading metadata from %s (1.65 GB)...", path)
    start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    elapsed = time.monotonic() - start
    log.info("  Loaded %d samples in %.1fs", len(data.get("samples", [])), elapsed)
    return data


def load_gt_index(path: Path) -> dict[str, dict[str, Any]]:
    """Load GT index and return dict keyed by image_id (stem).

    The GT index was produced by extract_doclaynet_gt_index.py and
    contains per-page: doc_category, langdetect language, COCO split,
    COCO content flags, text statistics, and text direction.

    Args:
        path: Path to doclaynet_gt_index.json.

    Returns:
        Dict mapping image_id (hex stem) to GT record.
    """
    if not path.exists():
        log.error("GT index not found: %s", path)
        return {}
    log.info("Loading GT index from %s...", path)
    start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    elapsed = time.monotonic() - start
    samples = raw.get("samples", {})
    log.info("  Loaded %d GT records in %.1fs", len(samples), elapsed)
    return samples


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    Args:
        path: Path to doclaynet_llm_enrichment.json.

    Returns:
        Dict mapping image_id to LLM enrichment record.
    """
    if not path.exists():
        log.warning("LLM enrichment not found: %s", path)
        return {}
    log.info("Loading LLM enrichment from %s...", path)
    start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    elapsed = time.monotonic() - start

    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            # LLM enrichment image_id includes .png extension; strip it
            stem = Path(image_id).stem
            index[stem] = rec
    log.info("  Indexed %d LLM records in %.1fs", len(index), elapsed)
    return index


# ===================================================================
# Derivation helpers
# ===================================================================
def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute text statistics from consolidated cell text.

    Args:
        text: Consolidated cell text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content,
        avg_line_length, latin_word_count.
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
    digit_count = len(re.findall(r"\d", clean_text))

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
    if digit_count > 0:
        stats["digit_count"] = digit_count

    return stats


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


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    gt_rec: dict[str, Any] | None,
    llm_rec: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single DocLayNet sample.

    Addresses all 13 audit defects (D01-D13).

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        gt_rec: GT index record for this sample (or None).
        llm_rec: LLM enrichment record for this sample (or None).

    Returns:
        New enrichment data dict with all sources merged.
    """
    # Get existing V1 enrichment data for fallback
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01: SPLIT (from COCO GT membership, confidence 1.0)
    # -------------------------------------------------------------------
    if gt_rec:
        data["split"] = gt_rec.get("split", "unknown")
    else:
        data["split"] = "unknown"

    # -------------------------------------------------------------------
    # CAPTURE METHOD (born-digital, from documentation)
    # -------------------------------------------------------------------
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D02: DOMAIN (from GT doc_category, confidence 1.0, KI-007 fix)
    # -------------------------------------------------------------------
    if gt_rec and gt_rec.get("domain_level1", "UNK") != "UNK":
        data["domain_level1"] = gt_rec["domain_level1"]
        data["domain_confidence"] = 1.0
        data["domain_detection_method"] = "ground_truth_doc_category"
    elif llm_rec:
        data["domain_level1"] = llm_rec.get("domain_level1", "UNK")
        data["domain_confidence"] = 0.65
        data["domain_detection_method"] = "llm_vision"
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = 0.3
        data["domain_detection_method"] = "fallback"

    # -------------------------------------------------------------------
    # D04: LANGUAGE / SCRIPT (from GT langdetect, confidence 0.95, KI-009)
    # -------------------------------------------------------------------
    if gt_rec and gt_rec.get("iso639_language", "und") != "und":
        data["iso639_language"] = gt_rec["iso639_language"]
        data["iso15924_script"] = gt_rec["iso15924_script"]
        data["language_confidence"] = min(
            gt_rec.get("language_confidence", 0.95), 0.95
        )
        data["text_scope_detection_method"] = "langdetect_gt_text"
    elif llm_rec:
        data["iso639_language"] = llm_rec.get("iso639_language", "en")
        data["iso15924_script"] = llm_rec.get("iso15924_script", "Latn")
        data["language_confidence"] = 0.65
        data["text_scope_detection_method"] = "llm_vision"
    else:
        data["iso639_language"] = v1_data.get("iso639_language", "en")
        data["iso15924_script"] = v1_data.get("iso15924_script", "Latn")
        data["language_confidence"] = 0.50
        data["text_scope_detection_method"] = "fallback"

    # -------------------------------------------------------------------
    # D03: SCRIPT FAMILY (re-derive from iso15924_script, KI-008 fix)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # -------------------------------------------------------------------
    # D05: LAYOUT DETECTIONS (preserve existing Docling, add provenance)
    # -------------------------------------------------------------------
    existing_layout = v1_data.get("layout_detections", [])
    if existing_layout:
        data["layout_detections"] = existing_layout
        data["layout_source"] = "docling_layout"
        data["layout_confidence"] = 0.85
        data["layout_detection_count"] = len(existing_layout)
    else:
        data["layout_detections"] = []
        data["layout_source"] = "none"
        data["layout_confidence"] = 0.0
        data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # D13: CONTENT FLAGS (from COCO GT categories, confidence 1.0)
    # -------------------------------------------------------------------
    if gt_rec and gt_rec.get("content_flags"):
        cf = gt_rec["content_flags"]
        data["has_table"] = cf.get("has_table", False)
        data["has_figure"] = cf.get("has_figure", False)
        data["has_formula"] = cf.get("has_formula", False)
        data["has_handwriting"] = cf.get("has_handwriting", False)
        data["has_code"] = cf.get("has_code", False)
        data["has_signature"] = cf.get("has_signature", False)
        data["content_flags_tier"] = "tier_0_exact"
        data["content_flags_source"] = "coco_gt_annotation"
        data["content_flags_confidence"] = 1.0
    else:
        # Fallback to Docling-derived flags (soft labels)
        data["has_table"] = v1_data.get("has_table", False)
        data["has_figure"] = v1_data.get("has_figure", False)
        data["has_formula"] = v1_data.get("has_formula", False)
        data["has_handwriting"] = False
        data["has_code"] = False
        data["has_signature"] = False
        data["content_flags_tier"] = "tier_2_model"
        data["content_flags_source"] = "docling_layout"
        data["content_flags_confidence"] = 0.85

    # D09: handwriting_present alias
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # D07: ORIENTATION (born-digital, no rotation)
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D06: TEXT CONTENT (from GT cells text)
    # -------------------------------------------------------------------
    if gt_rec and gt_rec.get("text_statistics"):
        ts = gt_rec["text_statistics"]
        data["text_has_content"] = ts.get("has_content", False)
        data["text_content_confidence"] = 1.0
        data["text_content_source"] = "ground_truth_cell_text"
        data["text_statistics"] = ts
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # -------------------------------------------------------------------
    # TEXT SCOPE (preserve V1 or set defaults)
    # -------------------------------------------------------------------
    data["text_scope"] = v1_data.get("text_scope", "page")
    data["text_scope_content_type"] = v1_data.get(
        "text_scope_content_type", "printed"
    )

    # -------------------------------------------------------------------
    # D08: IMAGE PROPERTIES COLOR MODE
    # -------------------------------------------------------------------
    color_space = sample.get("original_file", {}).get("color_space", "RGB")
    data["image_properties_color_mode"] = COLOR_SPACE_TO_MODE.get(
        color_space, "color"
    )

    # -------------------------------------------------------------------
    # RESOLUTION (preserve V1 values)
    # -------------------------------------------------------------------
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # D10, D11: TEXT DIRECTION (v2.3.0 fields)
    # -------------------------------------------------------------------
    if gt_rec:
        data["text_direction"] = gt_rec.get("text_direction", "ltr")
        data["text_directions_present"] = gt_rec.get(
            "text_directions_present", ["ltr"]
        )
    else:
        data["text_direction"] = "ltr"
        data["text_directions_present"] = ["ltr"]

    # -------------------------------------------------------------------
    # PRESERVE V1 QUALITY FIELDS
    # -------------------------------------------------------------------
    for field in (
        "text_quality_confidence",
        "text_quality_is_soft_label",
        "text_quality_method",
        "text_quality_provenance_tier",
        "quality_overall",
        "llm_predicted_mos",
        "llm_predicted_normalized",
        "llm_prediction_confidence",
        "llm_model_name",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # PAPER SIZE (preserve V1)
    # -------------------------------------------------------------------
    for field in (
        "paper_size",
        "paper_size_standard",
        "paper_size_orientation",
        "paper_size_confidence",
        "paper_size_is_exact",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # DATASET SHORT CODE
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last)
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _init_stats() -> dict[str, Any]:
    """Create empty stats tracking dict."""
    return {
        "total": 0,
        "integrated": 0,
        "gt_matched": 0,
        "llm_matched": 0,
        "has_text_content_count": 0,
        "has_layout_count": 0,
        "split_dist": Counter(),
        "domain_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "color_mode_dist": Counter(),
        "lang_method_dist": Counter(),
        "content_flags_source_dist": Counter(),
    }


def run_integration(
    metadata: dict[str, Any],
    gt_index: dict[str, dict[str, Any]],
    llm_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
    limit: int = 0,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict.
        gt_index: GT index keyed by image_id (stem).
        llm_index: LLM enrichment index keyed by image_id.
        dry_run: If True, compute stats without modifying metadata.
        limit: If >0, process only this many samples (for testing).

    Returns:
        Stats dict with counts and distributions.
    """
    stats = _init_stats()
    now = datetime.now(UTC).isoformat()
    total_samples = len(metadata["samples"])
    start = time.monotonic()

    for i, sample in enumerate(metadata["samples"]):
        if limit > 0 and stats["total"] >= limit:
            break

        filename = sample["source"]["original_filename"]
        # DocLayNet image_id is the hex stem (no extension)
        stem = Path(filename).stem

        gt_rec = gt_index.get(stem)
        llm_rec = llm_index.get(stem)

        integrated_data = integrate_sample(sample, gt_rec, llm_rec)

        # Track stats
        stats["total"] += 1
        stats["integrated"] += 1
        if gt_rec:
            stats["gt_matched"] += 1
        if llm_rec:
            stats["llm_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1
        if integrated_data.get("layout_detection_count", 0) > 0:
            stats["has_layout_count"] += 1

        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["color_mode_dist"][
            integrated_data.get("image_properties_color_mode", "unknown")
        ] += 1
        stats["lang_method_dist"][
            integrated_data.get("text_scope_detection_method", "unknown")
        ] += 1
        stats["content_flags_source_dist"][
            integrated_data.get("content_flags_source", "unknown")
        ] += 1

        # Write enrichment version
        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_doclaynet_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "GT doc_category domain + langdetect language + COCO GT "
                    "split/content flags + v2.3.0 text direction"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            versions = sample["enrichments"]["versions"]
            replaced = False
            for j, ver in enumerate(versions):
                if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[j] = new_version
                    replaced = True
                    break
            if not replaced:
                versions.append(new_version)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER

        if (i + 1) % 10000 == 0:
            elapsed = time.monotonic() - start
            rate = stats["total"] / elapsed if elapsed > 0 else 0
            log.info(
                "  Progress: %d/%d (%.0f/sec)",
                stats["total"],
                total_samples,
                rate,
            )

    total_elapsed = time.monotonic() - start
    log.info(
        "Integration complete: %d samples in %.1fs (%.0f/sec)",
        stats["total"],
        total_elapsed,
        stats["total"] / total_elapsed if total_elapsed > 0 else 0,
    )

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary.

    Args:
        stats: Stats dict from run_integration().
        total_samples: Total sample count.
    """
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 70)
    print(f"  {DATASET_NAME.upper()} Enrichment Integration Summary")
    print("=" * 70)
    print(f"  Total samples:        {stats['total']:,}")
    print(f"  Integrated:           {stats['integrated']:,}")
    print(f"  GT matched:           {stats['gt_matched']:,}")
    print(f"  LLM matched:          {stats['llm_matched']:,}")
    print(f"  Has text content:     {stats['has_text_content_count']:,}")
    print(f"  Has layout:           {stats['has_layout_count']:,}")
    print()

    print("  Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"    {split:12s}: {count:>8,}")
    print()

    print("  Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"    {domain:6s}: {count:>8,} ({pct:.1f}%)")
    print()

    print("  Language distribution (top 10):")
    for lang, count in stats["lang_dist"].most_common(10):
        pct = count / safe_total * 100
        print(f"    {lang:10s}: {count:>8,} ({pct:.1f}%)")
    print()

    print("  Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"    {sf:12s}: {count:>8,} ({pct:.1f}%)")
    print()

    print("  Color mode distribution:")
    for cm, count in stats["color_mode_dist"].most_common():
        print(f"    {cm:12s}: {count:>8,}")
    print()

    print("  Content flags source distribution:")
    for src, count in stats["content_flags_source_dist"].most_common():
        print(f"    {src:25s}: {count:>8,}")
    print()

    print("  Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"    {method:25s}: {count:>8,}")
    print("=" * 70)


# ===================================================================
# CLI
# ===================================================================
def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into DocLayNet metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    parser.add_argument(
        "--gt-index",
        type=Path,
        default=GT_INDEX_PATH,
        help="Path to GT index JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--llm-enrichment",
        type=Path,
        default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N samples (for testing, 0=all)",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    # Validate inputs
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1
    if not args.gt_index.is_file():
        log.error("GT index not found: %s (run extract_doclaynet_gt_index.py first)", args.gt_index)
        return 1

    # Load all data sources
    metadata = load_metadata(args.metadata)
    gt_index = load_gt_index(args.gt_index)
    llm_index = load_llm_enrichment(args.llm_enrichment)

    # Run integration
    log.info("Starting integration (%d samples)...", len(metadata["samples"]))
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        gt_index=gt_index,
        llm_index=llm_index,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info(
        "Integration completed in %.1f seconds (%.0f samples/sec)",
        elapsed,
        stats["total"] / elapsed if elapsed > 0 else 0,
    )

    # D12: Update metadata header to v2.3.0
    if not args.dry_run:
        metadata["schema_version"] = "2.3.0"
        metadata["splits_included"] = sorted(stats["split_dist"].keys())
        metadata["split_counts"] = dict(stats["split_dist"])

    # Write output
    if args.dry_run:
        log.info("Dry run -- no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s (this may take a moment)...", output_path)
        write_start = time.monotonic()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False)
        write_elapsed = time.monotonic() - write_start
        log.info(
            "  Written %d samples in %.1fs",
            len(metadata["samples"]),
            write_elapsed,
        )

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
