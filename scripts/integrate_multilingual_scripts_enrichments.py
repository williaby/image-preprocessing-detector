#!/usr/bin/env python3
"""Integrate enrichment sources into multilingual-scripts Layer 2 metadata.

multilingual-scripts is a composite dataset of 4 subdatasets:
  - arabic_ocr   (500 images): Arabic OCR documents, flatbed scanner
  - dzongkha_digit (62 images): Tibetan/Dzongkha digit images, smartphone camera
  - jssoda_*    (2000 images): Japanese synthetic document pages
  - nepal_book/newspaper (717 images): Nepali Devanagari documents, born-digital PDF

Defects fixed:
  D01: script_family="rtl" for arabic_ocr → "arabic"
  D02: script_family="indic" for dzongkha_digits → "other" (Tibetan not in named families)
  D03: capture_method="unknown" for all → per-subdataset values
  D06: content_flags absent → all False (printed text only, no handwriting/tables/formulas)
  D08: schema_version absent in version object → "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_multilingual_scripts_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "multilingual-scripts"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py"


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
DATASET_NAME = "multilingual-scripts"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "multilingual_scripts_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# ===================================================================
# Subdataset routing table
# Derived from filename prefix (set by MultilingualScriptsParser).
# ===================================================================
_SUBDATASET_RULES: list[tuple[re.Pattern[str], dict[str, Any]]] = [
    (
        re.compile(r"^arabic_ocr"),
        {
            "capture_method": "scanner_flatbed",
            "capture_confidence": 1.0,
            "iso639_language": "ar",
            "iso15924_script": "Arab",
            "script_family": "arabic",  # D01: was "rtl"
            "text_direction": "rtl",
            "text_directions_present": ["rtl"],
        },
    ),
    (
        re.compile(r"^dzongkha_digit"),
        {
            "capture_method": "camera_smartphone",  # D03: was "unknown"
            "capture_confidence": 0.9,
            "iso639_language": "dz",
            "iso15924_script": "Tibt",
            "script_family": "other",  # D02: was "indic"; Tibetan not in named families
            "text_direction": "ltr",
            "text_directions_present": ["ltr"],
        },
    ),
    (
        re.compile(r"^jssoda"),
        {
            "capture_method": "synthetic",  # D03: was "unknown"
            "capture_confidence": 1.0,
            "iso639_language": "ja",
            "iso15924_script": "Jpan",
            "script_family": "cjk",
            "text_direction": "ltr",
            "text_directions_present": ["ltr", "ttb"],
        },
    ),
    (
        re.compile(r"^nepal"),
        {
            "capture_method": "born_digital",  # D03: was "unknown" (PDF-derived scans)
            "capture_confidence": 0.9,
            "iso639_language": "ne",
            "iso15924_script": "Deva",
            "script_family": "indic",
            "text_direction": "ltr",
            "text_directions_present": ["ltr"],
        },
    ),
]

_FALLBACK_SUBDATASET: dict[str, Any] = {
    "capture_method": "unknown",
    "capture_confidence": 0.5,
    "iso639_language": "und",
    "iso15924_script": "Zyyy",
    "script_family": "other",
    "text_direction": "ltr",
    "text_directions_present": ["ltr"],
}


def _resolve_subdataset(filename: str) -> dict[str, Any]:
    """Return per-subdataset enrichment attributes based on filename prefix.

    Args:
        filename: The sample's original_filename (basename only).

    Returns:
        Dict with capture_method, iso639_language, iso15924_script, script_family,
        text_direction, and text_directions_present.
    """
    for pattern, attrs in _SUBDATASET_RULES:
        if pattern.match(filename):
            return attrs
    log.warning("No subdataset match for filename: %s — using fallback", filename)
    return _FALLBACK_SUBDATASET


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to *_metadata.json.

    Returns:
        Full metadata dict with "samples" list.
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
        Reliability summary dict.
    """
    field_defs = [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
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


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single multilingual-scripts sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.

    Returns:
        New enrichment data dict with corrected per-subdataset values.
    """
    filename = Path(sample["source"]["original_filename"]).name
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    sub = _resolve_subdataset(filename)
    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # CAPTURE METHOD  (D03: was "unknown" for all)
    # -------------------------------------------------------------------
    data["capture_method"] = sub["capture_method"]
    data["capture_confidence"] = sub["capture_confidence"]
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN  (UNK: subdataset-level heuristics are too coarse for L1 domain)
    # -------------------------------------------------------------------
    data["domain_level1"] = "UNK"
    data["domain_confidence"] = 0.3
    data["domain_detection_method"] = "none"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (D01, D02: wrong script_family for Arab/Tibt)
    # -------------------------------------------------------------------
    data["iso639_language"] = sub["iso639_language"]
    data["iso15924_script"] = sub["iso15924_script"]
    data["language_confidence"] = sub["capture_confidence"]
    data["script_family"] = sub["script_family"]  # D01/D02: corrected per subdataset
    data["text_direction"] = sub["text_direction"]
    data["text_directions_present"] = sub["text_directions_present"]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not available; future work D07)
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    data["layout_detections"] = v1_layout if isinstance(v1_layout, list) else []
    data["layout_source"] = v1_data.get("layout_source", "none")
    data["layout_confidence"] = v1_data.get("layout_confidence", 0.0)
    data["layout_detection_count"] = len(data["layout_detections"])

    # -------------------------------------------------------------------
    # CONTENT FLAGS  (D06: was entirely absent)
    # All subdatasets contain printed text only — no handwriting, tables, formulas.
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
    data["content_flags_confidence"] = 0.9

    # -------------------------------------------------------------------
    # ORIENTATION
    # -------------------------------------------------------------------
    data["orientation_class"] = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"] = float(v1_data.get("orientation_confidence", 0.7))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # -------------------------------------------------------------------
    data["text_has_content"] = True  # All subdatasets have readable text/digits
    data["text_content_confidence"] = 0.8
    data["text_content_source"] = "dataset_documentation"
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = v1_data.get("text_scope", "page")

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
    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


def run_integration(
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "capture_method_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_dist": Counter(),
        "split_dist": Counter(),
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample)
        stats["integrated"] += 1
        stats["capture_method_dist"][integrated_data["capture_method"]] += 1
        stats["script_family_dist"][integrated_data["script_family"]] += 1
        stats["lang_dist"][integrated_data["iso639_language"]] += 1
        stats["split_dist"][integrated_data["split"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",  # D08: was absent
                "created_at": now,
                "created_by": "integrate_multilingual_scripts_enrichments.py",
                "method": "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "per-subdataset heuristics (D01/D02/D03/D06 fixed)"
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
        print(f"  {method:25s}: {count:5d} ({count / total * 100:.1f}%)")
    print()
    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        print(f"  {sf:20s}: {count:5d} ({count / total * 100:.1f}%)")
    print()
    print("Language distribution:")
    for lang, count in stats["lang_dist"].most_common():
        print(f"  {lang:20s}: {count:5d} ({count / total * 100:.1f}%)")
    print("=" * 60)


def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    p = argparse.ArgumentParser(
        description=f"Integrate per-subdataset enrichments into {DATASET_NAME} metadata.",
    )
    p.add_argument("--metadata", type=Path, default=METADATA_PATH)
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Report only, do not write output"
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
