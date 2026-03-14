#!/usr/bin/env python3
"""Integrate enrichment sources into ndl-docl Layer 2 metadata.

NDL-DocL (National Diet Library Document Layout) provides 2,290 historical
Japanese layout images from the National Diet Library:
  - 1,219 kotenseki (pre-1868 rare books, kuzushiji handwritten script)
  - 1,071 kindai (post-1868 modern printed documents)

Pascal VOC XML bounding box annotations with 12 layout classes: illustration,
stamp, chart, handwriting, text, table, advertisement, headline, caption,
page_number, running_title, other.

Enrichments applied:
  - capture_method: "scanner_flatbed" (National Diet Library scans)
  - has_handwriting: True for kotenseki subset, False for kindai
  - iso639_language: "ja" (Japanese)
  - iso15924_script: "Jpan" (Japanese)
  - script_family: "cjk"
  - text_direction: "ttb" (vertical Japanese)
  - domain_level1: "HIS" (historical Japanese documents)
  - text_scope: "page"
  - text_scope_content_type: "handwritten" (kotenseki) / "printed" (kindai)
  - layout_detections: derived from Pascal VOC XML annotations
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_ndl_docl_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "ndl-docl"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/ndl_docl.py"
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
DATASET_NAME = "ndl-docl"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "ndl-docl_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1

# NDL-DocL layout classes from Pascal VOC annotations
NDL_DOCL_LAYOUT_CLASSES: frozenset[str] = frozenset(
    {
        "illustration",
        "stamp",
        "chart",
        "handwriting",
        "text",
        "table",
        "advertisement",
        "headline",
        "caption",
        "page_number",
        "running_title",
        "other",
    }
)

# Classes that indicate table presence
_TABLE_CLASSES: frozenset[str] = frozenset({"table"})

# Classes that indicate figure/illustration presence
_FIGURE_CLASSES: frozenset[str] = frozenset({"illustration", "chart"})


def _is_kotenseki(sample: dict[str, Any]) -> bool:
    """Determine if a sample is from the kotenseki (pre-1868) subset.

    Checks the source path and original_labels for "kotenseki" vs
    "kindai" indicators.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        True if the sample belongs to the kotenseki subset.
    """
    # Check source path
    source = sample.get("source", {})
    original_path = source.get("original_path", "")
    if "kotenseki" in original_path.lower():
        return True
    if "kindai" in original_path.lower():
        return False

    # Check original_labels subset field
    orig_labels = sample.get("original_labels", {})
    raw_labels = orig_labels.get("raw_labels", {})
    subset = raw_labels.get("subset", "")
    if subset == "kotenseki":
        return True
    if subset == "kindai":
        return False

    # Check sample_id as last resort
    sample_id = sample.get("sample_id", "")
    if "kotenseki" in sample_id.lower():
        return True

    # Default to False (kindai is the larger subset)
    return False


def _extract_layout_detections(
    sample: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract layout detections from Pascal VOC annotation data.

    Reads layout_annotations from the parser's raw_labels and converts
    to canonical detection format.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        List of detection dicts with canonical_class, confidence, and
        bbox fields.
    """
    orig_labels = sample.get("original_labels", {})
    raw_labels = orig_labels.get("raw_labels", {})
    annotations = raw_labels.get("layout_annotations", [])

    detections: list[dict[str, Any]] = []
    for ann in annotations:
        label = ann.get("label", "").lower()
        if label not in NDL_DOCL_LAYOUT_CLASSES:
            continue
        bbox = ann.get("bbox", {})
        detection: dict[str, Any] = {
            "canonical_class": label,
            "confidence": 1.0,
            "source": "ground_truth",
        }
        if bbox:
            detection["bbox"] = bbox
        detections.append(detection)

    return detections


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single ndl-docl sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with language, layout, and schema fields.
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
    # SUBSET DETERMINATION
    # Kotenseki = pre-1868 rare books (handwritten kuzushiji)
    # Kindai = post-1868 modern (printed)
    # -------------------------------------------------------------------
    is_koten = _is_kotenseki(sample)

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # National Diet Library digitization — flatbed scanner
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Historical Japanese documents (National Diet Library collection)
    # -------------------------------------------------------------------
    data["domain_level1"] = "HIS"
    data["domain_confidence"] = 0.95
    data["domain_detection_method"] = "dataset_documentation"

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
    # LAYOUT DETECTIONS
    # Derived from Pascal VOC XML annotations (12 classes)
    # -------------------------------------------------------------------
    detections = _extract_layout_detections(sample)
    data["layout_detections"] = detections
    data["layout_source"] = "ground_truth" if detections else "none"
    data["layout_confidence"] = 1.0 if detections else 0.0
    data["layout_detection_count"] = len(detections)

    # Derive content flags from layout detections
    detection_classes = {d.get("canonical_class", "").lower() for d in detections}
    has_table = bool(detection_classes & _TABLE_CLASSES)
    has_figure = bool(detection_classes & _FIGURE_CLASSES)

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # Kotenseki: handwritten kuzushiji; Kindai: printed modern text
    # -------------------------------------------------------------------
    data["has_table"] = has_table
    data["has_figure"] = has_figure
    data["has_formula"] = False
    data["has_handwriting"] = is_koten
    data["has_signature"] = False
    data["has_code"] = False
    data["handwriting_present"] = is_koten
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
    # Page-level Japanese text; kotenseki = handwritten, kindai = printed
    # -------------------------------------------------------------------
    data["text_has_content"] = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "handwritten" if is_koten else "printed"
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
        "subset_dist": Counter(),
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
        # Track subset distribution (kotenseki vs kindai)
        subset_label = (
            "kotenseki" if integrated_data.get("has_handwriting") else "kindai"
        )
        stats["subset_dist"][subset_label] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at": now,
                "created_by": "integrate_ndl_docl_enrichments.py",
                "method": "tier_1_annotation",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "VOC annotations + documentation heuristics "
                    "for NDL-DocL Japanese layout"
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
    print()
    print("Subset distribution (kotenseki/kindai):")
    for subset, count in stats["subset_dist"].most_common():
        pct = count / total * 100
        print(f"  {subset:20s}: {count:6d} ({pct:.1f}%)")
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
