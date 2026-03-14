#!/usr/bin/env python3
"""Integrate enrichment sources into casia-hwdb2 Layer 2 metadata.

CASIA-HWDB2 (CASIA Handwriting Database 2) provides 5,091 full-page images of
Chinese handwriting collected from 1,019 writers. Sub-datasets: HWDB2.0, HWDB2.1,
HWDB2.2. Pages are digitized from paper using a flatbed scanner and stored in DGRL
binary format; extracted PNGs are in HWDB/*_images/ subdirectories.

Enrichments applied:
  - capture_method: "scanner_flatbed" (flatbed scanner originals)
  - has_handwriting: True (all samples)
  - iso639_language: "zh" (Chinese)
  - iso15924_script: "Hans" (Simplified Chinese)
  - script_family: "han"
  - text_direction: "ltr"
  - domain_level1: "EDU" (academic handwriting collection, CASIA research)
  - text_scope: "page"
  - text_scope_content_type: "handwritten"
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_casia_hwdb2_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "casia-hwdb2"
__l4_workstream__ = "WS4"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2.py"
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
DATASET_NAME = "casia-hwdb2"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "casia-hwdb2_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single casia-hwdb2 sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

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
    # The parser does not map HWDB2.xTrain_images/ → "train" reliably.
    # Derive from original_path when split is "unknown".
    # -------------------------------------------------------------------
    split = sample.get("source", {}).get("split", "unknown")
    if split == "unknown":
        orig_path = sample.get("source", {}).get("original_path", "")
        if "Train_images" in orig_path:
            split = "train"
        elif "Test_images" in orig_path:
            split = "test"
    data["split"] = split

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # CASIA-HWDB2 scanned from paper using a flatbed scanner; DGRL
    # binary files are the official distribution format.
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.95
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Academic handwriting research collection (CASIA / NLPR, China)
    # -------------------------------------------------------------------
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Simplified Chinese (ISO 639-1: zh) in Hans script (ISO 15924: Hans)
    # -------------------------------------------------------------------
    data["iso639_language"] = "zh"
    data["iso15924_script"] = "Hans"
    data["language_confidence"] = 0.99
    data["script_family"] = "cjk"  # Schema enum requires "cjk" (not "han")
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr", "ttb"]  # Chinese: horizontal + vertical
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable for full-page scans)
    # -------------------------------------------------------------------
    data["layout_detections"] = []
    data["layout_source"] = "none"
    data["layout_confidence"] = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # All samples are full-page Chinese handwriting
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
    # Full-page Chinese handwriting; transcription extracted from DGRL
    # per-line annotations during base annotation step.
    # -------------------------------------------------------------------
    data["text_has_content"] = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "page"

    # Preserve transcription from base annotation if present
    if "transcription" in v1_data:
        data["transcription"] = v1_data["transcription"]

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

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
                "created_by": "integrate_casia_hwdb2_enrichments.py",
                "method": "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset-documentation heuristics for CASIA-HWDB2 Chinese handwriting"
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
    print()
    print("Split distribution:")
    for sp, count in stats["split_dist"].most_common():
        print(f"  {sp:20s}: {count:6d} ({count / total * 100:.1f}%)")
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
