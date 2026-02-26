#!/usr/bin/env python3
"""Integrate enrichment sources into doc3d Layer 2 metadata.

Doc3D provides 102,064 synthetically rendered document images produced via
BlenderProc 3D mesh rendering.  Real document textures are projected onto
curved/folded mesh models and rendered under diverse lighting conditions.

Three render modes (warp types):
  - pp (plain photo): primary training images, clean synthetic render
  - tc (color checker): includes calibration target in frame
  - pr (projected rainbow): rainbow stripe projection for shape estimation

Enrichments applied:
  - capture_method: "synthetic" (BlenderProc 3D rendering — NOT camera captured)
  - has_handwriting: False (printed document textures)
  - iso639_language: mixed (printed English/multi-language documents)
  - domain_level1: "UNK" (diverse printed document textures)
  - text_scope: "page"
  - text_scope_content_type: "printed"
  - warping_present: True (all images have geometric distortion)
  - schema_version: "2.4.0"

IMPORTANT: capture_method is ALWAYS "synthetic" regardless of the dataset's
parent directory name ("camera_captured/"). Doc3D uses BlenderProc rendering
and is not camera-captured.

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_doc3d_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__   = "integrate-script"
__l4_dataset__    = "doc3d"
__l4_workstream__ = "WS5c"
__l4_parser__     = (
    "src/image_preprocessing_detector/annotation/parsers/correction/doc3d.py"
)


import argparse
import json
import logging
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "doc3d"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "doc3d_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the *_metadata.json file.

    Returns:
        Full metadata dict with ``"samples"`` list.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Reliability summary dict with per-field confidence breakdown.
    """
    field_defs = [
        ("capture_method",    "capture_confidence"),
        ("domain",            "domain_confidence"),
        ("language",          "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags",     "content_flags_confidence"),
    ]
    fields: list[dict[str, Any]] = []
    for field_name, conf_key in field_defs:
        confidence = float(data.get(conf_key) or 0.0)
        if confidence >= 0.9:
            category = "hard_label"
        elif confidence >= 0.7:
            category = "soft_label"
        elif confidence >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"
        fields.append({
            "field":         field_name,
            "confidence":    round(confidence, 4),
            "category":      category,
            "is_soft_label": category == "soft_label",
        })

    min_field = min(fields, key=lambda f: f["confidence"])
    return {
        "min_confidence":          min_field["confidence"],
        "min_confidence_field":    min_field["field"],
        "min_confidence_category": min_field["category"],
        "assessed_field_count":    len(fields),
        "hard_field_count":  sum(1 for f in fields if f["category"] == "hard_label"),
        "soft_field_count":  sum(1 for f in fields if f["category"] == "soft_label"),
        "field_summary":     fields,
        "computed_at":       datetime.now(UTC).isoformat(),
    }


# Matches both standard and N_-prefixed Doc3D filenames:
#   {docID}_{viewID}-{warpType}_Page_{pageID}-{docCode}.ext
#   N_{docID}_{viewID}-{warpType}_Page_{pageID}-{docCode}.ext
_WARP_TYPE_RE = re.compile(
    r"^(?:\d+_)?(?P<doc_id>\d+)_(?P<view_id>\d+)-(?P<warp_type>pp|tc|pr)"
    r"_Page_"
)


def _get_warp_type(sample: dict[str, Any]) -> str:
    """Extract warp_type from raw_labels or filename.

    Reads ``original_labels.raw_labels.warp_type`` first; falls back to
    parsing the filename directly (handles N_-prefixed format not matched
    by the parser's regex at annotation time).

    Args:
        sample: Sample dict from metadata.

    Returns:
        Warp type string: ``"pp"``, ``"tc"``, ``"pr"``, or ``"unknown"``.
    """
    raw = sample.get("original_labels", {})
    if raw is None:
        raw = {}
    # warp_type is nested under raw_labels, not at the top level of original_labels
    raw_labels = raw.get("raw_labels", {}) if isinstance(raw, dict) else {}
    warp_type = raw_labels.get("warp_type", "")
    if warp_type and warp_type != "unknown":
        return warp_type

    # Fallback: parse from filename stem directly (handles N_-prefix variants)
    orig_path = sample.get("source", {}).get("original_path", "")
    stem = Path(orig_path).stem
    match = _WARP_TYPE_RE.match(stem)
    if match:
        return match.group("warp_type")

    # Last resort: prior enrichment version
    versions = sample.get("enrichments", {}).get("versions", [])
    if versions:
        prior = versions[-1].get("data", {}).get("warp_type", "")
        if prior and prior != "unknown":
            return prior

    return "unknown"


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single doc3d sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.

    Returns:
        New enrichment data dict with synthetic dewarping and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # ALWAYS "synthetic" — BlenderProc 3D rendering, NOT camera capture.
    # The dataset resides in camera_captured/ for historical reasons only.
    # -------------------------------------------------------------------
    data["capture_method"]           = "synthetic"
    data["capture_confidence"]       = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Diverse printed document textures — domain cannot be reliably
    # determined without per-image inspection.
    # -------------------------------------------------------------------
    data["domain_level1"]           = "UNK"
    data["domain_confidence"]       = 0.4
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Mixed printed documents; primary language unknown without VLM.
    # -------------------------------------------------------------------
    data["iso639_language"]    = "unk"
    data["iso15924_script"]    = "Latn"  # Primary script of rendered document textures
    data["language_confidence"] = 0.3
    data["script_family"]      = "latin"   # Most textures are Latin-script
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable — synthetic renders of full pages)
    # -------------------------------------------------------------------
    data["layout_detections"]      = []
    data["layout_source"]          = "none"
    data["layout_confidence"]      = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # Synthetically rendered printed documents — no handwriting
    # -------------------------------------------------------------------
    data["has_table"]       = False
    data["has_figure"]      = False
    data["has_formula"]     = False
    data["has_handwriting"] = False
    data["has_signature"]   = False
    data["has_code"]        = False
    data["warping_present"]          = True  # Primary characteristic
    data["content_flags_tier"]       = "tier_3_heuristic"
    data["content_flags_source"]     = "dataset_documentation"
    data["content_flags_confidence"] = 0.8

    # -------------------------------------------------------------------
    # ORIENTATION
    # Synthetic renders have controlled orientation; most are upright.
    # -------------------------------------------------------------------
    data["orientation_class"]            = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"]       = float(v1_data.get("orientation_confidence", 0.8))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # WARP TYPE
    # Derived from filename via parser; propagate if available
    # -------------------------------------------------------------------
    warp_type = _get_warp_type(sample)
    data["warp_type"] = warp_type
    data["is_primary_warp_type"] = warp_type == "pp"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Printed text from document textures
    # -------------------------------------------------------------------
    data["text_has_content"]        = True
    data["text_content_confidence"] = 0.7
    data["text_content_source"]     = "dataset_documentation"
    data["text_scope_content_type"] = "printed"
    data["text_scope"]              = "page"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
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
    data["dataset_short_code"]         = DATASET_NAME
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
        "total":               0,
        "integrated":          0,
        "capture_method_dist": Counter(),
        "warp_type_dist":      Counter(),
        "domain_dist":         Counter(),
        "split_dist":          Counter(),
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample)
        stats["integrated"] += 1
        stats["capture_method_dist"][integrated_data["capture_method"]] += 1
        stats["warp_type_dist"][integrated_data["warp_type"]] += 1
        stats["domain_dist"][integrated_data["domain_level1"]] += 1
        stats["split_dist"][integrated_data["split"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version":        ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at":     now,
                "created_by":     "integrate_doc3d_enrichments.py",
                "method":         "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset-documentation heuristics for Doc3D synthetic dewarping"
                ),
                "script_version": SCRIPT_VERSION,
                "data":           integrated_data,
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
    print("Warp type distribution:")
    for wt, count in stats["warp_type_dist"].most_common():
        print(f"  {wt:20s}: {count:6d} ({count / total * 100:.1f}%)")
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
    p.add_argument("--output",   type=Path, default=None,
                   help="Output path (default: overwrite input)")
    p.add_argument("--dry-run",  action="store_true",
                   help="Report statistics only, do not write output")
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
