#!/usr/bin/env python3
"""Integrate enrichment sources into salami Layer 2 metadata.

SALAMI (Systematic Analysis of Legibility in Ancient Manuscript Images)
provides 250 manuscript pages with 4,811 region-level legibility annotations
from 20 expert annotators.  The dataset spans 8 historical scripts:
Armenian (Armn), Georgian (Geor), German (Latn), Gothic (Goth),
Greek (Grek), Latin (Latn), Ottoman (Arab), and Slavonic (Cyrl).

This is a gold-standard legibility calibration dataset with expert
pixel-level annotations (tier_1_annotation quality).

License: CC-BY-4.0

Enrichments applied:
  - capture_method: "scanner_flatbed" (manuscript scans)
  - has_handwriting: True (all samples — historical manuscripts)
  - iso639_language: per-script (hy/ka/de/got/el/la/ota/cu)
  - iso15924_script: per-script (Armn/Geor/Latn/Goth/Grek/Arab/Cyrl)
  - script_family: per-script (armenian/georgian/latin/gothic/greek/arabic/cyrillic)
  - text_direction: per-script (ltr or rtl for Arab)
  - domain_level1: "UNK" (historical manuscripts from diverse periods)
  - text_scope: "page"
  - text_scope_content_type: "handwritten"
  - content_flags_tier: "tier_1_annotation" (expert pixel-level annotations)
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_salami_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "salami"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/salami.py"
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
DATASET_NAME = "salami"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "salami_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1

# ===================================================================
# SCRIPT MAPPING TABLE
# Maps manuscript script name to (iso639_language, iso15924_script,
# script_family).  Script names come from original_labels in the
# parser output.
# ===================================================================
_SCRIPT_MAP: dict[str, tuple[str, str, str]] = {
    "Armenian": ("hy", "Armn", "armenian"),
    "Georgian": ("ka", "Geor", "georgian"),
    "German": ("de", "Latn", "latin"),
    "Gothic": ("got", "Goth", "gothic"),
    "Greek": ("el", "Grek", "greek"),
    "Latin": ("la", "Latn", "latin"),
    "Ottoman": ("ota", "Arab", "arabic"),
    "Slavonic": ("cu", "Cyrl", "cyrillic"),
}

# Scripts that use right-to-left text direction
_RTL_SCRIPTS: frozenset[str] = frozenset({"Arab"})

# Fallback for unknown script names
_FALLBACK_SCRIPT = ("und", "Zyyy", "other")


def _resolve_script(
    sample: dict[str, Any],
    v1_data: dict[str, Any],
) -> tuple[str, str, str]:
    """Derive language, script, and script family from sample metadata.

    Checks parser original_labels and v1 enrichment data to determine
    the manuscript's script.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.
        v1_data: Data dict from the latest enrichment version.

    Returns:
        Tuple of (iso639_language, iso15924_script, script_family).
    """
    # Try original_labels from parser (primary source)
    original_labels = sample.get("original_labels", {})
    script_name = original_labels.get("script", "")
    if script_name and script_name in _SCRIPT_MAP:
        return _SCRIPT_MAP[script_name]

    # Try v1 enrichment data (secondary source)
    v1_script = v1_data.get("iso15924_script", "")
    if v1_script:
        for name, (lang, scr, fam) in _SCRIPT_MAP.items():
            if scr == v1_script:
                return (lang, scr, fam)

    v1_family = v1_data.get("script_family", "")
    if v1_family:
        for name, (lang, scr, fam) in _SCRIPT_MAP.items():
            if fam == v1_family:
                return (lang, scr, fam)

    # Try source path heuristic (folder names may contain script)
    orig_path = sample.get("source", {}).get("original_path", "")
    for name, mapping in _SCRIPT_MAP.items():
        if name.lower() in orig_path.lower():
            return mapping

    log.warning(
        "Could not resolve script for sample %s — using fallback",
        sample.get("sample_id", "unknown"),
    )
    return _FALLBACK_SCRIPT


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single SALAMI sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with per-script language, handwriting,
        and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data = get_current_version_data(sample)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # Historical manuscript scans from library/archive collections
    # -------------------------------------------------------------------
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 0.9
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Historical manuscripts from diverse periods and traditions;
    # no single domain applies
    # -------------------------------------------------------------------
    data["domain_level1"] = "UNK"
    data["domain_confidence"] = 0.3
    data["domain_detection_method"] = "none"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Derived per-sample from parser original_labels or v1 enrichment
    # -------------------------------------------------------------------
    iso_lang, iso_script, script_fam = _resolve_script(sample, v1_data)
    data["iso639_language"] = iso_lang
    data["iso15924_script"] = iso_script
    data["language_confidence"] = 0.9
    data["script_family"] = script_fam

    text_dir = "rtl" if iso_script in _RTL_SCRIPTS else "ltr"
    data["text_direction"] = text_dir
    data["text_directions_present"] = [text_dir]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable — full page manuscripts)
    # -------------------------------------------------------------------
    data["layout_detections"] = []
    data["layout_source"] = "none"
    data["layout_confidence"] = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # All samples are full-page historical manuscripts with expert
    # pixel-level legibility annotations (tier_1_annotation quality)
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = False
    data["has_formula"] = False
    data["has_handwriting"] = True  # Primary characteristic
    data["has_signature"] = False
    data["has_code"] = False
    data["handwriting_present"] = True
    data["content_flags_tier"] = "tier_1_annotation"
    data["content_flags_source"] = "ground_truth"
    data["content_flags_confidence"] = 0.99

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"] = float(v1_data.get("orientation_confidence", 0.7))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Full page manuscript scans; legibility annotated but no
    # transcription ground truth in the dataset
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
    # Derive from original_file.channels (manuscript scans)
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
        "language_dist": Counter(),
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
        stats["language_dist"][integrated_data["iso639_language"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at": now,
                "created_by": ("integrate_salami_enrichments.py"),
                "method": "tier_1_annotation",
                "description": (
                    f"Integrated enrichment"
                    f" {ENRICHMENT_VERSION_TAG}: "
                    "per-script heuristics for SALAMI"
                    " multi-script manuscript legibility"
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
    print("Language distribution:")
    for lang, count in stats["language_dist"].most_common():
        pct = count / total * 100
        print(f"  {lang:20s}: {count:6d} ({pct:.1f}%)")
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
        log.info(
            "Done. Written %d samples.",
            len(metadata["samples"]),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
