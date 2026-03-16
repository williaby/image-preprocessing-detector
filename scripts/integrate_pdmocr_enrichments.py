#!/usr/bin/env python3
"""Integrate enrichment sources into pdmocr-part1 Layer 2 metadata.

PDM OCR (Pre-modern Digital Manuscripts OCR) provides ~2,713 historical
Japanese pre-modern printed documents (1870s-1940s) from the National Diet
Library.  Character-level bounding box annotations with archaic kanji
preservation.  Bibliographic metadata from info.csv includes NDC (Nippon
Decimal Classification) categories.

Enrichments applied:
  - capture_method: "scanner_flatbed" (National Diet Library scans)
  - has_handwriting: False (printed documents)
  - iso639_language: "ja" (Japanese)
  - iso15924_script: "Jpan" (Japanese)
  - script_family: "cjk"
  - text_direction: "ttb" (vertical Japanese)
  - domain_level1: "HIS" (historical Japanese printed documents)
  - text_scope: "page"
  - text_scope_content_type: "printed"
  - orientation_class: 0
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_pdmocr_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "pdmocr-part1"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/pdmocr.py"
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

from enrichment_utils import (
    ensure_enrichment_scaffold,
    get_current_version_data,
    upsert_version,
)

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
DATASET_NAME = "pdmocr-part1"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "pdmocr-part1_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single pdmocr sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with language, domain, and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data = get_current_version_data(sample)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------
    split = sample.get("source", {}).get("split", "train")
    data["split"] = split

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # National Diet Library digitization — flatbed scanner
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Historical Japanese printed documents, NDC classified
    # -------------------------------------------------------------------
    data["domain_level1"] = "HIS"
    data["domain_confidence"] = 0.95
    data["domain_detection_method"] = "dataset_documentation"

    # Preserve NDC classification from parser if available
    orig_labels = sample.get("original_labels", {})
    raw_labels = orig_labels.get("raw_labels", {})
    ndc = raw_labels.get("ndc_classification", "")
    if ndc:
        data["ndc_classification"] = ndc

    # Preserve decade from parser if available
    decade = raw_labels.get("decade", "")
    if decade:
        data["publication_decade"] = decade

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Japanese (ISO 639-1: ja) in Japanese script (ISO 15924: Jpan)
    # -------------------------------------------------------------------
    data["iso639_language"] = "ja"
    data["iso15924_script"] = "Jpan"
    data["language_confidence"] = 0.99
    data["script_family"] = "cjk"
    data["text_direction"] = "ttb"
    data["text_directions_present"] = ["ttb"]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable — page-level images)
    # -------------------------------------------------------------------
    data["layout_detections"] = []
    data["layout_source"] = "none"
    data["layout_confidence"] = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # Pre-modern printed documents — no annotations for structure
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = False
    data["has_formula"] = False
    data["has_handwriting"] = False
    data["has_signature"] = False
    data["has_code"] = False
    data["handwriting_present"] = False
    data["content_flags_tier"] = "tier_3_heuristic"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 0.85

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"] = float(v1_data.get("orientation_confidence", 0.7))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Page-level printed Japanese text (1870s-1940s)
    # -------------------------------------------------------------------
    data["text_has_content"] = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    channels = sample.get("original_file", {}).get("channels", 3)
    data["image_properties_color_mode"] = "grayscale" if channels == 1 else "rgb"

    # Preserve resolution fields if previously populated
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
        integrated_data = integrate_sample(sample)
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
                "created_by": "integrate_pdmocr_enrichments.py",
                "method": "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset-documentation heuristics for "
                    "PDM OCR historical Japanese documents"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            ensure_enrichment_scaffold(sample)
            upsert_version(sample, new_version, ENRICHMENT_VERSION_NUMBER)

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
        pct = count / total * 100
        print(f"  {method:25s}: {count:6d} ({pct:.1f}%)")
    print()
    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / total * 100
        print(f"  {sf:20s}: {count:6d} ({pct:.1f}%)")
    print()
    print("Domain distribution:")
    for dom, count in stats["domain_dist"].most_common():
        pct = count / total * 100
        print(f"  {dom:20s}: {count:6d} ({pct:.1f}%)")
    print("=" * 60)


def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    p = argparse.ArgumentParser(
        description=(
            f"Integrate per-dataset enrichments into {DATASET_NAME} metadata."
        ),
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
