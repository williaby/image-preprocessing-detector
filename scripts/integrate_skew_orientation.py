#!/usr/bin/env python3
"""Integrate skew/orientation labels into Layer 2 metadata for any dataset.

Merges output from label_skew_orientation.py into the enrichment data of
a dataset's Layer 2 metadata JSON. Works with any dataset by matching on
image filename.

Adds 7 skew/orientation fields to each sample's enrichment data:
  - orientation_class (int: 0/90/180/270)
  - orientation_confidence (float 0-1)
  - orientation_detection_method (str)
  - orientation_corrected (None - labeling only)
  - skew_angle_degrees (float)
  - skew_confidence (float 0-1)
  - skew_detection_method (str)

Usage:
    # Dry run
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python scripts/integrate_skew_orientation.py \
        --skew-json results/diqa5000_skew_labels.json \
        --metadata /mnt/e/image_detection/metadata_registry/json/diqa-5000_metadata.json \
        --dry-run

    # Patch current version
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python scripts/integrate_skew_orientation.py \
        --skew-json results/diqa5000_skew_labels.json \
        --metadata /mnt/e/image_detection/metadata_registry/json/diqa-5000_metadata.json \
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

DETECTION_METHOD = "mobilenetv4_skew_estimator_v1"
SCRIPT_VERSION = "1.0.0"


def load_skew_results(path: Path) -> dict[str, dict[str, Any]]:
    """Load skew/orientation JSON and index by filename.

    Args:
        path: Path to skew labels JSON from label_skew_orientation.py.

    Returns:
        Dict mapping filename -> measurement dict.
    """
    with open(path) as f:
        data = json.load(f)

    results = data.get("results", [])
    meta = data.get("metadata", {})
    log.info(
        "Loaded %d skew/orientation results from %s (errors=%d)",
        len(results),
        path,
        meta.get("errors", 0),
    )

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


def extract_skew_fields(skew: dict[str, Any]) -> dict[str, Any]:
    """Extract skew/orientation fields for L2 enrichment.

    Maps raw label output to the enrichment schema field names defined
    in enrichment.py (orientation_class, orientation_confidence, etc.).

    Args:
        skew: Single measurement result from label_skew_orientation.py.

    Returns:
        Dict with 7 orientation/skew fields for L2 enrichment.
    """
    return {
        "orientation_class": skew.get("orientation_class"),
        "orientation_confidence": skew.get("orientation_confidence"),
        "orientation_detection_method": DETECTION_METHOD,
        "orientation_corrected": None,
        "skew_angle_degrees": skew.get("skew_angle_degrees"),
        "skew_confidence": skew.get("skew_bin_confidence"),
        "skew_detection_method": DETECTION_METHOD,
    }


def get_sample_filename(sample: dict[str, Any]) -> str | None:
    """Extract the original filename from a L2 metadata sample.

    Handles multiple field locations used across datasets.

    Args:
        sample: A single sample dict from the L2 metadata.

    Returns:
        The original filename string, or None if not found.
    """
    source = sample.get("source", {})
    filename = source.get("original_filename")
    if filename:
        return str(Path(filename).name)

    sample_id = sample.get("sample_id", "")
    if sample_id and "." in sample_id:
        return sample_id

    return None


def integrate_into_metadata(
    metadata: dict[str, Any],
    skew_index: dict[str, dict[str, Any]],
    patch_current: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Merge skew/orientation data into L2 metadata samples.

    Args:
        metadata: The full L2 metadata dict (with "samples" key).
        skew_index: Skew/orientation index keyed by filename.
        patch_current: If True, patch the current enrichment version.
        dry_run: If True, report only without modifying metadata.

    Returns:
        Stats dict with match counts and orientation distribution.
    """
    samples = metadata.get("samples", [])
    total = len(samples)
    stats: dict[str, int] = Counter()

    log.info("Integrating skew/orientation for %d samples ...", total)
    start = time.time()

    for idx, sample in enumerate(samples):
        filename = get_sample_filename(sample)
        if not filename:
            stats["no_filename"] += 1
            continue

        skew = skew_index.get(filename)
        if not skew:
            stats["no_match"] += 1
            continue

        stats["matched"] += 1
        skew_fields = extract_skew_fields(skew)

        orient = skew_fields.get("orientation_class", -1)
        stats[f"orient_{orient}"] += 1

        if dry_run:
            continue

        enrichments = sample.setdefault("enrichments", {"versions": []})
        versions = enrichments.setdefault("versions", [])

        if patch_current and versions:
            current = versions[-1]
            current_data = current.setdefault("data", {})
            current_data.update(skew_fields)
            stats["patched"] += 1
        else:
            current_ver = enrichments.get("current_version", "v0")
            ver_num = 1
            if current_ver and current_ver.startswith("v"):
                try:
                    ver_num = int(current_ver[1:]) + 1
                except ValueError:
                    ver_num = len(versions) + 1

            new_version = {
                "version": f"v{ver_num}",
                "timestamp": datetime.now(UTC).isoformat(),
                "method": "skew_orientation_integration",
                "description": (
                    "Added skew/orientation labels from MobileNetV4-Conv-S "
                    "ONNX estimator (test MAE=0.956, orient_acc=99.5%)"
                ),
                "script": "integrate_skew_orientation.py",
                "script_version": SCRIPT_VERSION,
                "data": skew_fields,
            }
            versions.append(new_version)
            enrichments["current_version"] = new_version["version"]
            stats["new_version"] += 1

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

    print("\n" + "=" * 60)
    print("  Skew/Orientation Integration Summary")
    print("=" * 60)
    print(f"  Total samples:     {total:>6d}")
    print(f"  Matched:           {matched:>6d}  ({matched/max(total,1)*100:.1f}%)")
    print(f"  No match:          {no_match:>6d}  ({no_match/max(total,1)*100:.1f}%)")
    if no_filename:
        print(f"  No filename:       {no_filename:>6d}")

    if stats.get("patched", 0):
        print(f"  Patched versions:  {stats['patched']:>6d}")
    if stats.get("new_version", 0):
        print(f"  New versions:      {stats['new_version']:>6d}")

    # Orientation distribution
    orient_labels = {0: "0 deg", 90: "90 deg", 180: "180 deg", 270: "270 deg"}
    has_orient = any(stats.get(f"orient_{o}", 0) for o in orient_labels)
    if has_orient:
        print("\n  Orientation distribution:")
        for orient_val, label in orient_labels.items():
            count = stats.get(f"orient_{orient_val}", 0)
            pct = count / max(matched, 1) * 100
            print(f"    {label:<12s} {count:>5d}  ({pct:5.1f}%)")

    print("=" * 60)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate skew/orientation labels into L2 metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skew-json",
        type=Path,
        required=True,
        help="Path to skew/orientation JSON (from label_skew_orientation.py).",
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

    if not args.skew_json.is_file():
        log.error("Skew/orientation JSON not found: %s", args.skew_json)
        return 1
    if not args.metadata.is_file():
        log.error("Metadata JSON not found: %s", args.metadata)
        return 1

    output_path = args.output or args.metadata

    skew_index = load_skew_results(args.skew_json)

    log.info("Loading metadata from %s ...", args.metadata)
    with open(args.metadata) as f:
        metadata = json.load(f)

    total = len(metadata.get("samples", []))
    log.info("Loaded %d samples", total)

    stats = integrate_into_metadata(
        metadata=metadata,
        skew_index=skew_index,
        patch_current=args.patch_current,
        dry_run=args.dry_run,
    )

    print_summary(stats, total)

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
