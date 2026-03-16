#!/usr/bin/env python3
"""Integrate enrichment sources into iiit-hw-hindi Layer 2 metadata.

IIIT-HW-Hindi (IIIT Handwritten Hindi Words, c3rl/IIIT-INDIC-HW-WORDS-Hindi)
provides 95,430 word-level images of Hindi handwriting in Devanagari script,
collected at IIIT Hyderabad via flatbed scanner.

Enrichments applied:
  - capture_method: "scanner_flatbed" (physical handwriting on paper, then scanned)
  - has_handwriting: True (all samples)
  - iso639_language: "hi" (Hindi)
  - iso15924_script: "Deva" (Devanagari)
  - script_family: "indic"
  - text_direction: "ltr"
  - domain_level1: "EDU" (academic handwriting collection)
  - text_scope: "word"
  - text_scope_content_type: "handwritten"
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_iiit_hw_hindi_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "iiit-hw-hindi"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/iiit_hw_hindi.py"
)


import argparse
import csv
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from l2_integration_utils import (
    compute_reliability_summary,
    load_metadata,
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
DATASET_NAME = "iiit-hw-hindi"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "iiit-hw-hindi_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1

_BASE_DATA_DIR = Path("/mnt/e/image_detection/01_base_data")
GROUNDTRUTH_TSV = (
    _BASE_DATA_DIR / "handwriting" / "iiit-hw-hindi" / "iiit_hw_hindi_groundtruth.tsv"
)


def load_transcription_index(tsv_path: Path) -> dict[str, str]:
    """Load the ground-truth TSV into a filename → Hindi text lookup dict.

    Args:
        tsv_path: Path to ``iiit_hw_hindi_groundtruth.tsv``.

    Returns:
        Dict mapping filename (e.g. ``"iiit_hw_hindi_test_00000.jpg"``) to
        Devanagari Unicode transcription string.  Returns empty dict on error.
    """
    if not tsv_path.is_file():
        log.warning(
            "Transcription TSV not found: %s — transcriptions will be empty", tsv_path
        )
        return {}
    index: dict[str, str] = {}
    try:
        with open(tsv_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                filename = row.get("filename") or row.get("image_path", "")
                text = row.get("hindi_text", "")
                if filename and text:
                    index[filename] = text
        log.info("  Loaded %d transcriptions from TSV", len(index))
    except Exception:
        log.exception("Failed to load transcription TSV: %s", tsv_path)
    return index


def integrate_sample(
    sample: dict[str, Any],
    transcription_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single iiit-hw-hindi sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.
        transcription_index: Optional filename → Hindi text lookup from TSV.

    Returns:
        New enrichment data dict with language, handwriting, and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # Filenames encode split: iiit_hw_hindi_{split}_{index:05d}.jpg
    # Parser does not extract split — derive from filename.
    # -------------------------------------------------------------------
    split = sample.get("source", {}).get("split", "unknown")
    if split == "unknown":
        orig_path = sample.get("source", {}).get("original_path", "")
        filename_stem = Path(orig_path).stem  # e.g. "iiit_hw_hindi_test_00000"
        parts = filename_stem.split("_")
        # parts: ['iiit', 'hw', 'hindi', 'train'/'test'/'val', '00000']
        if len(parts) >= 4 and parts[3] in ("train", "test", "val", "validation"):
            split = parts[3] if parts[3] != "validation" else "val"
    data["split"] = split

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # Physical handwriting on paper, digitized via flatbed scanner at IIIT
    # Confidence 0.7 — inferred from dataset type (research institute collection)
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Academic handwriting collection from IIIT Hyderabad
    # -------------------------------------------------------------------
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Hindi (ISO 639-1: hi) in Devanagari (ISO 15924: Deva)
    # -------------------------------------------------------------------
    data["iso639_language"] = "hi"
    data["iso15924_script"] = "Deva"
    data["language_confidence"] = 0.99
    data["script_family"] = "indic"
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable for word-level crops)
    # -------------------------------------------------------------------
    data["layout_detections"] = []
    data["layout_source"] = "none"
    data["layout_confidence"] = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # All samples are word-level handwriting — no tables, figures, formulas
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = False
    data["has_formula"] = False
    data["has_handwriting"] = True  # Primary characteristic of this dataset
    data["has_signature"] = False
    data["has_code"] = False
    data["handwriting_present"] = True
    data["content_flags_tier"] = "tier_3_heuristic"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 0.99

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"] = float(v1_data.get("orientation_confidence", 0.7))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Word-level handwriting; transcription may be available from TSV
    # -------------------------------------------------------------------
    data["text_has_content"] = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "word"

    # Look up transcription from TSV index (keyed by filename)
    orig_path = sample.get("source", {}).get("original_path", "")
    filename = Path(orig_path).name  # e.g. "iiit_hw_hindi_test_00000.jpg"
    if transcription_index and filename in transcription_index:
        data["transcription"] = transcription_index[filename]
    elif "transcription" in v1_data:
        data["transcription"] = v1_data["transcription"]

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # Preserve resolution fields if previously populated (except resolution_category)
    for field in (
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field in v1_data:
            data[field] = v1_data[field]
    # resolution_category is meaningless for variable-size word crops — suppress it
    data["resolution_category"] = None

    # -------------------------------------------------------------------
    # ADDITIONAL
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


def run_integration(
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with ``"samples"`` list.
        dry_run: If True, compute statistics without modifying metadata.

    Returns:
        Stats dict with distribution Counters.
    """
    transcription_index = load_transcription_index(GROUNDTRUTH_TSV)

    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "capture_method_dist": Counter(),
        "script_family_dist": Counter(),
        "domain_dist": Counter(),
        "split_dist": Counter(),
    }
    now = datetime.now(timezone.utc).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample, transcription_index)
        stats["integrated"] += 1
        stats["capture_method_dist"][integrated_data["capture_method"]] += 1
        stats["script_family_dist"][integrated_data["script_family"]] += 1
        stats["domain_dist"][integrated_data["domain_level1"]] += 1
        stats["split_dist"][integrated_data["split"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at": now,
                "created_by": "integrate_iiit_hw_hindi_enrichments.py",
                "method": "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset-documentation heuristics for Devanagari handwriting"
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


def print_summary(stats: dict[str, Any]) -> None:
    """Print integration statistics.

    Args:
        stats: Stats dict returned by run_integration().
    """
    total = max(stats["total"], 1)
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:  {stats['total']}")
    print(f"Integrated:     {stats['integrated']}")
    print()
    print("Capture method distribution:")
    for method, count in stats["capture_method_dist"].most_common():
        print(f"  {method:25s}: {count:6d} ({count / total * 100:.1f}%)")
    print()
    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        print(f"  {sf:20s}: {count:6d} ({count / total * 100:.1f}%)")
    print()
    print("Domain distribution:")
    for dom, count in stats["domain_dist"].most_common():
        print(f"  {dom:20s}: {count:6d} ({count / total * 100:.1f}%)")
    print("=" * 60)


def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    p = argparse.ArgumentParser(
        description=f"Integrate per-dataset enrichments into {DATASET_NAME} metadata.",
    )
    p.add_argument("--metadata", type=Path, default=METADATA_PATH)
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report statistics only, do not write output",
    )
    args = p.parse_args()

    output_path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)

    start = time.monotonic()
    stats = run_integration(metadata, dry_run=args.dry_run)
    elapsed = time.monotonic() - start

    print_summary(stats)
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run — no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
