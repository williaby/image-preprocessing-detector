#!/usr/bin/env python3
"""Integrate all enrichment sources into JSSODa Layer 2 metadata.

Merges 3 data sources into the main metadata JSON for all 2,000 records:
  1. LLM enrichment (tier_2, 2000 images): domain, content flags, content_type
  2. Language enrichment (dataset-level): ja/Jpan (backup; known values primary)
  3. Parser manifest data: split, is_vertical, num_columns

Also applies:
  - Layout label PascalCase conversion (D01): docling lowercase -> DocLayNet
  - Hardcoded known values: capture_method=synthetic, language=ja, script=Jpan
  - Content flag derivation from layout detections + LLM merge
  - Reliability summary recomputation

Creates a new enrichment version (v2) in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_jssoda_enrichments.py

    # Dry run (report only, no write):
    PYTHONPATH=... uv run python3 scripts/integrate_jssoda_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "jssoda"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/multilingual/jssoda.py"
)


import argparse
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

from l2_integration_utils import (
    compute_reliability_summary,
    derive_content_flags,
    load_llm_enrichment,
    load_metadata,
    DOCLING_TO_DOCLAYNET,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "jssoda_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "jssoda_llm_enrichment.json"
MANIFEST_PATH = (
    Path("/mnt/e/image_detection/01_base_data")
    / "language"
    / "multilingual_scripts"
    / "jssoda"
    / "manifest.json"
)

SCRIPT_VERSION = "1.1.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"

# Content flag derivation from canonical layout classes

# VLM corrections (2026-02-11): per-sample overrides from visual inspection.
# Full audit: scripts/audit/results/jssoda/vlm_corrections.json
# has_formula: only these 2 samples confirmed to contain visible formulas.
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset(
    {
        "jssoda_horizontal_00537",  # math expression: x = (c - b) / a
        "jssoda_horizontal_00956",  # equation: (a+b)^2 = a^2 + 2ab + b^2
    }
)

# Docling lowercase -> DocLayNet PascalCase mapping


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    """Load manifest.json and index by filename."""
    if not path.exists():
        log.warning("Manifest not found: %s", path)
        return {}
    log.info("Loading manifest from %s", path)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for orientation in ["vertical", "horizontal"]:
        for rec in raw.get(orientation, []):
            filename = rec.get("filename", "")
            if filename:
                index[filename] = rec
    log.info("  Indexed %d manifest records", len(index))
    return index


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------
def standardize_class_name(class_name: str) -> str:
    """Convert Docling lowercase class_name to DocLayNet PascalCase."""
    return DOCLING_TO_DOCLAYNET.get(class_name, class_name)


def _standardize_layout_detections(
    detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Standardize class_name to PascalCase and preserve source_label."""
    result: list[dict[str, Any]] = []
    for det in detections:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        result.append(new_det)
    return result


def _resolve_jssoda_split(
    filename: str,
    manifest_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve split and layout properties from manifest or filename."""
    manifest_rec = manifest_index.get(filename)
    if manifest_rec:
        return {
            "split": manifest_rec.get("split", "train"),
            "is_vertical": manifest_rec.get("is_vertical", False),
            "num_columns": manifest_rec.get("num_columns", 1),
        }
    if "vertical" in filename:
        return {"split": "train", "is_vertical": True}
    if "horizontal" in filename:
        return {"split": "train", "is_vertical": False}
    return {"split": "unknown"}


# ---------------------------------------------------------------------------
# Per-sample integration
# ---------------------------------------------------------------------------
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    manifest_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Returns a new enrichment version data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # Get existing v1 data (layout_detections + sample_reliability_summary)
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][0].get("data", {})

    data: dict[str, Any] = {}

    # D01 - Layout detections with PascalCase class_name conversion
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout = _standardize_layout_detections(v1_layout)
    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # D02 - capture_method
    data["capture_method"] = "synthetic"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # D03 - domain_level1
    llm = llm_index.get(filename_stem)
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = "UNK"
        data["domain_confidence"] = 0.3
        data["domain_detection_method"] = "none"

    # D04/D05/D06 - language, script, script_family
    data["iso639_language"] = "ja"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["iso15924_script"] = "Jpan"
    data["script_family"] = _get_script_family("Jpan")

    # D07 - content_flags: VLM-corrected (v1.1.0)
    flags = derive_content_flags(standardized_layout)
    data["has_table"] = False
    data["has_figure"] = False
    data["has_handwriting"] = False
    data["has_signature"] = False
    data["has_code"] = flags["has_code"]
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "vlm_corrected+docling_gpu+llm_vision"
    data["content_flags_confidence"] = 0.95
    data["handwriting_present"] = False

    # D10 - text_scope_content_type
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type or "unknown"
    else:
        data["text_scope_content_type"] = "unknown"
    data["text_scope"] = "printed"

    # D11 - split from manifest
    data.update(_resolve_jssoda_split(filename, manifest_index))

    # Additional derived fields
    data["dataset_short_code"] = "jssoda"
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"
    data["image_properties_color_mode"] = "color"

    # Reliability summary recomputation
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ---------------------------------------------------------------------------
# Integration runner helpers
# ---------------------------------------------------------------------------
def _track_jssoda_sample_stats(
    stats: dict[str, Any],
    filename: str,
    filename_stem: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    manifest_index: dict[str, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename in manifest_index:
        stats["manifest_matched"] += 1
    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["content_type_dist"][
        integrated_data.get("text_scope_content_type", "unknown")
    ] += 1
    stats["capture_method_dist"][integrated_data.get("capture_method", "unknown")] += 1
    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for i, v in enumerate(versions):
        if v.get("version") == version_number:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


# ---------------------------------------------------------------------------
# Integration runner
# ---------------------------------------------------------------------------
def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    manifest_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "manifest_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "content_type_dist": Counter(),
        "capture_method_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }

    now = datetime.now(timezone.utc).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        integrated_data = integrate_sample(sample, llm_index, manifest_index)

        _track_jssoda_sample_stats(
            stats,
            filename,
            filename_stem,
            integrated_data,
            llm_index,
            manifest_index,
        )

        if not dry_run:
            new_version = {
                "version": 2,
                "created_at": now,
                "created_by": "integrate_jssoda_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + Docling layout + manifest parser + "
                    "known dataset values (synthetic, ja, Jpan)"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, 2)

    return stats


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    print("\n" + "=" * 60)
    print("JSSODa Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Manifest matched:     {stats['manifest_matched']}")
    print()
    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        print(f"  {domain:20s}: {count:5d} ({count / total_samples * 100:.1f}%)")
    print()
    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:5d}")
    print()
    print("Content type distribution:")
    for ct, count in stats["content_type_dist"].most_common(10):
        print(f"  {ct:30s}: {count:5d}")
    print()
    print("Capture method distribution:")
    for cm, count in stats["capture_method_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
    print()
    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into JSSODa metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to jssoda_metadata.json (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--llm-enrichment",
        type=Path,
        default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Path to manifest.json (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path = args.output or args.metadata

    # Load all data sources
    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    manifest_index = load_manifest(args.manifest)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        manifest_index=manifest_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))


if __name__ == "__main__":
    main()
