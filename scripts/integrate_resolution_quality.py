#!/usr/bin/env python3
"""Integrate resolution quality labels into Layer 2 metadata for any dataset.

Merges output from label_resolution_quality.py into the enrichment data of
a dataset's Layer 2 metadata JSON. Works with any dataset (DIQA-5000,
OHR-Bench, RealDAE, etc.) by matching on image filename.

Adds 10 resolution quality fields to each sample's enrichment data:
  - resolution_quality_score (float 0-1)
  - resolution_quality_confidence (float 0-1)
  - resolution_quality_char_height_px (float)
  - resolution_quality_char_height_range_px ([float, float])
  - resolution_quality_score_range ([float, float])
  - resolution_quality_coarse_bucket (str)
  - resolution_quality_measurement_method (str)
  - resolution_quality_num_text_regions (int)
  - resolution_quality_height_cv (float)
  - resolution_quality_source (str, e.g. "paddleocr_dbnet_cc_v1")

Usage:
    # Integrate into DIQA-5000
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_resolution_quality.py \
        --rq-json results/diqa5000_resolution_labels.json \
        --metadata /mnt/e/image_detection/metadata_registry/json/diqa-5000_metadata.json

    # Integrate into OHR-Bench
    PYTHONPATH=... uv run python3 scripts/integrate_resolution_quality.py \
        --rq-json results/ohrbench_resolution_labels.json \
        --metadata /mnt/e/image_detection/metadata_registry/json/ohr-bench_metadata.json

    # Dry run (report only)
    PYTHONPATH=... uv run python3 scripts/integrate_resolution_quality.py \
        --rq-json results/diqa5000_resolution_labels.json \
        --metadata /mnt/e/.../diqa-5000_metadata.json \
        --dry-run

    # Patch current enrichment version (instead of creating new version)
    PYTHONPATH=... uv run python3 scripts/integrate_resolution_quality.py \
        --rq-json results/diqa5000_resolution_labels.json \
        --metadata /mnt/e/.../diqa-5000_metadata.json \
        --patch-current
"""

from __future__ import annotations

import argparse
import json
import logging
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

RQ_SOURCE_TAG = "paddleocr_dbnet_cc_v1"
SCRIPT_VERSION = "1.0.0"

# Fields extracted from resolution quality results
RQ_FIELDS = [
    "resolution_quality_score",
    "resolution_quality_confidence",
    "resolution_quality_char_height_px",
    "resolution_quality_char_height_range_px",
    "resolution_quality_score_range",
    "resolution_quality_coarse_bucket",
    "resolution_quality_measurement_method",
    "resolution_quality_num_text_regions",
    "resolution_quality_height_cv",
    "resolution_quality_source",
    # Provenance fields (v2.2)
    "resolution_quality_label_provenance",
    "resolution_quality_label_source",
    "resolution_quality_label_confidence",
    "resolution_quality_script_used",
    "resolution_quality_script_confidence",
]


def load_rq_results(path: Path) -> dict[str, dict[str, Any]]:
    """Load resolution quality JSON and index by filename.

    Builds two indices to handle different path conventions:
    - Full relative path (e.g. "diqa-5000/test/ori/test_ori_00001.jpg")
    - Filename only (e.g. "test_ori_00001.jpg")

    Returns:
        Dict mapping filename -> resolution quality measurement dict.
    """
    with open(path) as f:
        data = json.load(f)

    results = data.get("results", [])
    meta = data.get("metadata", {})
    log.info(
        "Loaded %d resolution quality results from %s (errors=%d, flagged=%d)",
        len(results),
        path,
        meta.get("errors", 0),
        meta.get("flagged_for_review", 0),
    )

    # Build index by filename (basename) for flexible matching
    index: dict[str, dict[str, Any]] = {}
    for r in results:
        if r.get("error"):
            continue
        image_path = r.get("image_path", "")
        filename = Path(image_path).name
        if filename:
            index[filename] = r

    log.info("Indexed %d successful measurements by filename", len(index))
    return index


def extract_rq_fields(rq: dict[str, Any]) -> dict[str, Any]:
    """Extract resolution quality fields from a measurement result.

    Maps the raw output field names to the L2 enrichment field naming convention
    (resolution_quality_* prefix).

    Args:
        rq: Single measurement result from label_resolution_quality.py.

    Returns:
        Dict with 10-15 resolution quality fields for L2 enrichment
        (10 core + up to 5 provenance fields when present).
    """
    fields: dict[str, Any] = {
        "resolution_quality_score": rq.get("resolution_quality_score"),
        "resolution_quality_confidence": rq.get("confidence_pct"),
        "resolution_quality_char_height_px": rq.get("char_height_px"),
        "resolution_quality_char_height_range_px": rq.get("char_height_range_px"),
        "resolution_quality_score_range": rq.get("score_range"),
        "resolution_quality_coarse_bucket": rq.get("coarse_bucket"),
        "resolution_quality_measurement_method": rq.get("measurement_method"),
        "resolution_quality_num_text_regions": rq.get("num_text_regions"),
        "resolution_quality_height_cv": rq.get("height_cv"),
        "resolution_quality_source": RQ_SOURCE_TAG,
    }

    # Provenance fields (v2.2) — include if present in source data
    for provenance_field in (
        "label_provenance",
        "label_source",
        "label_confidence",
        "script_used",
        "script_confidence",
    ):
        value = rq.get(provenance_field)
        if value is not None:
            fields[f"resolution_quality_{provenance_field}"] = value

    return fields


def get_sample_filename(sample: dict[str, Any]) -> str | None:
    """Extract the original filename from a L2 metadata sample.

    Handles multiple field locations used across datasets.

    Args:
        sample: A single sample dict from the L2 metadata.

    Returns:
        The original filename string, or None if not found.
    """
    # Try source.original_filename first (standard L2 field)
    source = sample.get("source", {})
    filename = source.get("original_filename")
    if filename:
        return str(Path(filename).name)

    # Fallback: sample_id may contain the filename
    sample_id = sample.get("sample_id", "")
    if sample_id and "." in sample_id:
        return sample_id

    return None


def _next_version_number(enrichments: dict[str, Any]) -> int:
    """Compute the next version number from the enrichments structure."""
    current_ver = enrichments.get("current_version", "v0")
    if current_ver and current_ver.startswith("v"):
        try:
            return int(current_ver[1:]) + 1
        except ValueError:
            return len(enrichments.get("versions", [])) + 1
    return 1


def _apply_rq_to_sample(
    sample: dict[str, Any],
    rq_fields: dict[str, Any],
    patch_current: bool,
    stats: dict[str, int],
) -> None:
    """Apply resolution quality fields to a single sample (mutates sample)."""
    enrichments = sample.setdefault("enrichments", {"versions": []})
    versions = enrichments.setdefault("versions", [])

    if patch_current and versions:
        current = versions[-1]
        current_data = current.setdefault("data", {})
        current_data.update(rq_fields)
        stats["patched"] += 1
        return

    ver_num = _next_version_number(enrichments)
    new_version = {
        "version": f"v{ver_num}",
        "timestamp": datetime.now(UTC).isoformat(),
        "method": "resolution_quality_integration",
        "description": (
            "Added resolution quality labels from PaddleOCR DBNet + "
            "connected component analysis pipeline"
        ),
        "script": "integrate_resolution_quality.py",
        "script_version": SCRIPT_VERSION,
        "data": rq_fields,
    }
    versions.append(new_version)
    enrichments["current_version"] = new_version["version"]
    stats["new_version"] += 1


def integrate_into_metadata(
    metadata: dict[str, Any],
    rq_index: dict[str, dict[str, Any]],
    patch_current: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Merge resolution quality data into L2 metadata samples.

    Args:
        metadata: The full L2 metadata dict (with "samples" key).
        rq_index: Resolution quality index keyed by filename.
        patch_current: If True, patch the current enrichment version instead
            of creating a new one.
        dry_run: If True, report only without modifying metadata.

    Returns:
        Stats dict with match counts and bucket distribution.
    """
    samples = metadata.get("samples", [])
    total = len(samples)
    stats: dict[str, int] = Counter()

    log.info("Integrating resolution quality for %d samples ...", total)
    start = time.time()

    for idx, sample in enumerate(samples):
        filename = get_sample_filename(sample)
        if not filename:
            stats["no_filename"] += 1
            continue

        rq = rq_index.get(filename)
        if not rq:
            stats["no_match"] += 1
            continue

        stats["matched"] += 1
        rq_fields = extract_rq_fields(rq)

        bucket = rq_fields.get("resolution_quality_coarse_bucket", "unknown")
        stats[f"bucket_{bucket}"] += 1

        if rq.get("flagged_for_review"):
            stats["flagged"] += 1

        if not dry_run:
            _apply_rq_to_sample(sample, rq_fields, patch_current, stats)

        if (idx + 1) % 1000 == 0:
            elapsed = time.time() - start
            rate = (idx + 1) / elapsed
            log.info("  [%d/%d] %.0f samples/sec", idx + 1, total, rate)

    elapsed = time.time() - start
    log.info("Integration complete in %.1f seconds", elapsed)

    return dict(stats)


def print_summary(stats: dict[str, int], total: int) -> None:
    """Print integration summary report."""
    matched = stats.get("matched", 0)
    no_match = stats.get("no_match", 0)
    no_filename = stats.get("no_filename", 0)
    flagged = stats.get("flagged", 0)

    print("\n" + "=" * 60)
    print("  Resolution Quality Integration Summary")
    print("=" * 60)
    print(f"  Total samples:     {total:>6d}")
    print(f"  Matched:           {matched:>6d}  ({matched / max(total, 1) * 100:.1f}%)")
    print(
        f"  No match:          {no_match:>6d}  ({no_match / max(total, 1) * 100:.1f}%)"
    )
    if no_filename:
        print(f"  No filename:       {no_filename:>6d}")
    print(
        f"  Flagged for review:{flagged:>6d}  ({flagged / max(matched, 1) * 100:.1f}%)"
    )

    if stats.get("patched", 0):
        print(f"  Patched versions:  {stats['patched']:>6d}")
    if stats.get("new_version", 0):
        print(f"  New versions:      {stats['new_version']:>6d}")

    # Bucket distribution
    bucket_names = [
        "needs_major_upscale",
        "needs_light_upscale",
        "optimal",
        "good",
        "oversized",
    ]
    has_buckets = any(stats.get(f"bucket_{b}", 0) for b in bucket_names)
    if has_buckets:
        print("\n  Coarse bucket distribution:")
        for bucket in bucket_names:
            count = stats.get(f"bucket_{bucket}", 0)
            pct = count / max(matched, 1) * 100
            print(f"    {bucket:<24s} {count:>5d}  ({pct:5.1f}%)")

    print("=" * 60)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate resolution quality labels into L2 metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--rq-json",
        type=Path,
        required=True,
        help="Path to resolution quality JSON (from label_resolution_quality.py).",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Path to dataset's Layer 2 metadata JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input metadata file).",
    )
    parser.add_argument(
        "--patch-current",
        action="store_true",
        default=False,
        help="Patch current enrichment version instead of creating a new one.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report only, do not write output.",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.rq_json.is_file():
        log.error("Resolution quality JSON not found: %s", args.rq_json)
        return 1
    if not args.metadata.is_file():
        log.error("Metadata JSON not found: %s", args.metadata)
        return 1

    output_path = args.output or args.metadata

    # Load data
    rq_index = load_rq_results(args.rq_json)

    log.info("Loading metadata from %s ...", args.metadata)
    with open(args.metadata) as f:
        metadata = json.load(f)

    total = len(metadata.get("samples", []))
    log.info("Loaded %d samples", total)

    # Run integration
    stats = integrate_into_metadata(
        metadata=metadata,
        rq_index=rq_index,
        patch_current=args.patch_current,
        dry_run=args.dry_run,
    )

    # Print summary
    print_summary(stats, total)

    # Write output
    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Written to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
