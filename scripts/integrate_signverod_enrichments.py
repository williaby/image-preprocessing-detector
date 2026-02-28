#!/usr/bin/env python3
"""Integrate enrichment sources into signverod Layer 2 metadata.

SignVerOD provides 2,765 scanned government/contract documents with
bounding box annotations for signature verification and document
analysis.  Annotations cover 4 categories: signature (5,044),
initials (1,163), redaction (2,308), and date (700) totaling 9,215
annotations.  1,939 train + 354 test images.  Licensed under CC0-1.0.

Enrichments applied:
  - capture_method: "scanner_flatbed" (office scanner output)
  - has_handwriting: True (signatures and initials present)
  - has_signature: True (primary annotation target)
  - iso639_language: "en" (English)
  - iso15924_script: "Latn" (Latin)
  - script_family: "latin"
  - text_direction: "ltr"
  - domain_level1: "ADM" (NIST/GSA government/administrative documents)
  - text_scope: "page"
  - text_scope_content_type: "mixed" (typed text + handwritten signatures)
  - content_flags_tier: "tier_1_annotation" (bounding box annotations)
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_signverod_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "signverod"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/signverod.py"
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
DATASET_NAME = "signverod"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "signverod_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1

# SignVerOD annotation category names (from CSV ground truth)
SIGNATURE_CATEGORIES: frozenset[str] = frozenset({"signature", "initials"})
REDACTION_CATEGORIES: frozenset[str] = frozenset({"redaction"})
DATE_CATEGORIES: frozenset[str] = frozenset({"date"})


def _derive_layout_from_annotations(
    sample: dict[str, Any],
) -> list[dict[str, Any]]:
    """Derive layout detections from SignVerOD CSV annotations.

    If annotation data is available in the sample (via parser), convert
    bounding boxes to layout detections.  Otherwise return an empty
    list — the script still sets content flags from documentation.

    Args:
        sample: A single sample from the L2 metadata ``"samples"``
            list, potentially containing parsed annotation data.

    Returns:
        List of layout detection dicts in canonical format.
    """
    annotations = sample.get("annotations", [])
    if not annotations:
        return []

    detections: list[dict[str, Any]] = []
    for ann in annotations:
        category = ann.get("category", "").lower()
        bbox = ann.get("bbox")
        if not category:
            continue

        # Map SignVerOD categories to canonical layout classes
        if category in SIGNATURE_CATEGORIES:
            canonical = "Signature"
        elif category in REDACTION_CATEGORIES:
            canonical = "Redaction"
        elif category in DATE_CATEGORIES:
            canonical = "Text"
        else:
            canonical = "Text"

        detection: dict[str, Any] = {
            "canonical_class": canonical,
            "source": "ground_truth",
            "confidence": 0.95,
            "original_class": category,
        }
        if bbox:
            detection["bbox"] = bbox
        detections.append(detection)

    return detections


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single signverod sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with language, signature detection,
        layout, and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # SignVerOD has explicit train/test splits (1,939/354).
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # SignVerOD documents are scanned office/government documents
    # (NIST/GSA provenance) — standard flatbed scanner output.
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # NIST/GSA government and administrative documents
    # -------------------------------------------------------------------
    data["domain_level1"] = "ADM"
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
    # Derive from CSV bounding box annotations if available; otherwise
    # leave empty (content flags still set from documentation).
    # -------------------------------------------------------------------
    layout_detections = _derive_layout_from_annotations(sample)
    data["layout_detections"] = layout_detections

    if layout_detections:
        data["layout_source"] = "ground_truth"
        data["layout_confidence"] = 0.95
        data["layout_detection_count"] = len(layout_detections)
    else:
        data["layout_source"] = "none"
        data["layout_confidence"] = 0.0
        data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # Government documents with handwritten signatures/initials,
    # typed text, redactions, and dates.  Bounding box annotations
    # provide tier-1 ground truth for signature presence.
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = False
    data["has_formula"] = False
    data["has_handwriting"] = True
    data["has_signature"] = True  # Primary annotation target
    data["has_code"] = False
    data["handwriting_present"] = True
    data["content_flags_tier"] = "tier_1_annotation"
    data["content_flags_source"] = "ground_truth"
    data["content_flags_confidence"] = 0.95

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"] = float(v1_data.get("orientation_confidence", 0.7))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Full-page scanned government documents; mixed content with typed
    # text body and handwritten signatures/initials.
    # -------------------------------------------------------------------
    data["text_has_content"] = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "mixed"
    data["text_scope"] = "page"

    # Preserve transcription from base annotation if present
    if "transcription" in v1_data:
        data["transcription"] = v1_data["transcription"]

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # Derive from original_file.channels; scanned government documents
    # are typically stored as RGB.
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
        "has_signature_dist": Counter(),
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample)
        stats["integrated"] += 1
        stats["capture_method_dist"][integrated_data["capture_method"]] += 1
        stats["script_family_dist"][integrated_data["script_family"]] += 1
        stats["domain_dist"][integrated_data["domain_level1"]] += 1
        stats["split_dist"][integrated_data["split"]] += 1
        stats["has_signature_dist"][integrated_data["has_signature"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at": now,
                "created_by": ("integrate_signverod_enrichments.py"),
                "method": "tier_1_annotation",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}"
                    ": ground-truth annotations + documentation "
                    "heuristics for SignVerOD government documents"
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
    print()
    print("Signature presence distribution:")
    for sig, count in stats["has_signature_dist"].most_common():
        pct = count / total * 100
        print(f"  {sig!s:20s}: {count:6d} ({pct:.1f}%)")
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
