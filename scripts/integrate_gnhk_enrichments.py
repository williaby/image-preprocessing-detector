#!/usr/bin/env python3
"""Integrate enrichment sources into gnhk Layer 2 metadata.

GNHK (GoodNotes Handwriting Knowledge) provides 687 full-page English
handwritten documents with word-level polygon annotations.  515 train +
172 test images captured via tablet/camera (GoodNotes app).  Licensed
under CC-BY-4.0.

Enrichments applied:
  - capture_method: "camera_smartphone" (tablet captures via GoodNotes)
  - has_handwriting: True (all samples — 100% handwritten pages)
  - iso639_language: "en" (English)
  - iso15924_script: "Latn" (Latin)
  - script_family: "latin"
  - text_direction: "ltr"
  - domain_level1: "EDU" (academic handwriting dataset)
  - text_scope: "page"
  - text_scope_content_type: "handwritten"
  - layout: single "Text" region covering full page
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_gnhk_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "gnhk"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/gnhk.py"
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
DATASET_NAME = "gnhk"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "gnhk_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single gnhk sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with language, handwriting, layout,
        and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data = get_current_version_data(sample)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # GNHK has explicit train/test splits (515/172).
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # GNHK images are tablet captures from the GoodNotes app —
    # categorized as camera_smartphone (tablet camera/digitizer).
    # -------------------------------------------------------------------
    data["capture_method"] = "camera_smartphone"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Academic handwriting research dataset (GoodNotes collaboration)
    # -------------------------------------------------------------------
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # English (ISO 639-1: en) in Latin script (ISO 15924: Latn)
    # -------------------------------------------------------------------
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 0.99
    data["script_family"] = "latin"
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS
    # Full-page handwritten documents — single "Text" region covering
    # the entire page.  Word-level polygon annotations exist in the
    # original dataset but are not modeled as layout regions here.
    # -------------------------------------------------------------------
    data["layout_detections"] = [
        {
            "canonical_class": "Text",
            "source": "dataset_documentation",
            "confidence": 0.9,
            "description": ("Full-page handwritten text region"),
        }
    ]
    data["layout_source"] = "dataset_documentation"
    data["layout_confidence"] = 0.9
    data["layout_detection_count"] = 1

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # All samples are full-page English handwriting; no tables, figures,
    # formulas, signatures, or code present.
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = False
    data["has_formula"] = False
    data["has_handwriting"] = True
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
    # Full-page handwritten English; word-level transcriptions from
    # polygon annotations in the original dataset.
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
    # Derive from original_file.channels; tablet captures are typically
    # stored as 3-channel RGB.
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
                "created_by": "integrate_gnhk_enrichments.py",
                "method": "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}"
                    ": dataset-documentation heuristics for "
                    "GNHK English handwritten page documents"
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
        log.info("Dry run -- no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
