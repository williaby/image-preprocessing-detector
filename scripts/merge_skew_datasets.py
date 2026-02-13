#!/usr/bin/env python3
"""Merge synthetic skew dataset with natural scan labels into unified training set.

Reads:
  - Synthetic labels from skew/{train,val,test}/labels.json (already processed)
  - Natural scan labels from skew/natural_scan_skew_labels.json (need resize+copy)

Produces:
  - Unified labels.json per split with both synthetic and natural scan entries
  - Resized natural scan images (384x384 JPEG) copied into split image dirs
  - Merge manifest with statistics

The natural scan images are processed with:
  1. Resize to 384x384 (matching synthetic output resolution)
  2. Save as JPEG quality 90
  3. Filename prefix "nscan_" to distinguish from synthetic "skew_" files

Usage:
    python scripts/merge_skew_datasets.py \\
        --skew-dir /path/to/skew \\
        --workers 4

    # Dry run (show statistics only)
    python scripts/merge_skew_datasets.py \\
        --skew-dir /path/to/skew \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def process_natural_image(args: tuple[Any, ...]) -> dict[str, Any]:
    """Resize and save a natural scan image for training.

    Args:
        args: Tuple of (source_path, output_path, idx).

    Returns:
        Dict with output_filename, success, error.
    """
    source_path, output_path, idx = args
    output_filename = f"nscan_{idx:07d}.jpg"
    try:
        from PIL import Image

        img = Image.open(source_path).convert("RGB")
        img = img.resize((384, 384), Image.Resampling.LANCZOS)

        out = Path(output_path) / output_filename
        img.save(out, "JPEG", quality=90)

        return {"filename": output_filename, "success": True, "error": None}
    except Exception as exc:
        return {"filename": output_filename, "success": False, "error": str(exc)}


def main() -> None:
    """CLI entry point for merging skew datasets."""
    parser = argparse.ArgumentParser(
        description="Merge synthetic + natural scan skew datasets",
    )
    parser.add_argument(
        "--skew-dir",
        type=Path,
        required=True,
        help="Root skew dataset directory (contains train/val/test and natural_scan_skew_labels.json)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show statistics only, do not process images",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum classical skew confidence to include (default: 0.7)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    skew_dir = args.skew_dir
    nscan_path = skew_dir / "natural_scan_skew_labels.json"

    if not nscan_path.exists():
        logger.error("Natural scan labels not found: %s", nscan_path)
        return

    # Load natural scan labels
    with nscan_path.open() as f:
        nscan_data = json.load(f)

    nscan_images = nscan_data["images"]
    logger.info("Loaded %d natural scan labels", len(nscan_images))

    # Filter by confidence
    high_conf = [
        img
        for img in nscan_images
        if img.get("classical_skew_confidence", 0) >= args.min_confidence
        and img.get("classical_skew_error") is None
    ]
    low_conf = len(nscan_images) - len(high_conf)
    logger.info(
        "After confidence filter (>= %.2f): %d kept, %d excluded",
        args.min_confidence,
        len(high_conf),
        low_conf,
    )

    # Group by split
    splits = {"train": [], "val": [], "test": []}
    for img in high_conf:
        split = img.get("split", "train")
        if split in splits:
            splits[split].append(img)

    # Load existing synthetic labels
    synth_labels: dict[str, dict[str, Any]] = {}
    for split in ["train", "val", "test"]:
        labels_path = skew_dir / split / "labels.json"
        if labels_path.exists():
            with labels_path.open() as f:
                synth_labels[split] = json.load(f)
        else:
            synth_labels[split] = {}

    # Print statistics
    print("\n=== Merge Plan ===")
    print(f"Natural scan labels: {len(high_conf)} (filtered from {len(nscan_images)})")
    for split in ["train", "val", "test"]:
        synth_count = len(synth_labels[split])
        nscan_count = len(splits[split])
        total = synth_count + nscan_count
        nscan_pct = 100 * nscan_count / max(total, 1)
        print(
            f"  {split:5s}: {synth_count:6,d} synthetic + {nscan_count:5,d} natural = "
            f"{total:6,d} total ({nscan_pct:.1f}% natural)"
        )

    grand_synth = sum(len(synth_labels[s]) for s in synth_labels)
    grand_nscan = len(high_conf)
    grand_total = grand_synth + grand_nscan
    print(
        f"\n  Total: {grand_synth:,d} synthetic + {grand_nscan:,d} natural = {grand_total:,d}"
    )

    # Natural scan dataset composition
    script_counts: dict[str, int] = {}
    capture_counts: dict[str, int] = {}
    for img in high_conf:
        sc = img.get("script", "unknown")
        script_counts[sc] = script_counts.get(sc, 0) + 1
        cm = img.get("capture_method", "unknown")
        capture_counts[cm] = capture_counts.get(cm, 0) + 1

    print("\n--- Natural Scan Script Distribution ---")
    for code, count in sorted(script_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(high_conf)
        print(f"  {code:5s}: {count:5,d} ({pct:5.1f}%)")

    print("\n--- Natural Scan Capture Method ---")
    for method, count in sorted(capture_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(high_conf)
        print(f"  {method:20s}: {count:5,d} ({pct:5.1f}%)")

    if args.dry_run:
        print("\n[DRY RUN] No images processed.")
        return

    # Process natural scan images
    start_time = time.monotonic()
    success_count = 0
    error_count = 0
    nscan_idx = 0

    for split in ["train", "val", "test"]:
        split_imgs = splits[split]
        if not split_imgs:
            continue

        split_img_dir = skew_dir / split / "images"
        split_img_dir.mkdir(parents=True, exist_ok=True)

        # Build work items
        work_items = []
        nscan_meta: list[tuple[dict[str, Any], int]] = []
        for img_record in split_imgs:
            work_items.append(
                (
                    img_record["path"],
                    str(split_img_dir),
                    nscan_idx,
                )
            )
            nscan_meta.append((img_record, nscan_idx))
            nscan_idx += 1

        # Process in parallel
        logger.info("[%s] Processing %d natural scan images...", split, len(work_items))
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            for result, (record, _idx) in zip(
                executor.map(process_natural_image, work_items, chunksize=50),
                nscan_meta,
                strict=True,
            ):
                if result["success"]:
                    # Add to labels with natural scan metadata
                    synth_labels[split][result["filename"]] = {
                        "angle": record["classical_skew_angle"],
                        "orientation": 0,  # Natural scans: unknown orientation, assume 0
                        "skew_bin": -1,  # Will be computed during training
                        "script": record.get("script", "Latn"),
                        "degradation": "natural",
                        "source": record.get("filename", "unknown"),
                        "source_type": "natural_scan",
                        "dataset": record.get("dataset", "unknown"),
                        "text_direction": record.get("text_direction", "ltr"),
                        "capture_method": record.get("capture_method", "unknown"),
                        "classical_confidence": record.get(
                            "classical_skew_confidence", 0
                        ),
                        "classical_method": record.get(
                            "classical_skew_method", "unknown"
                        ),
                    }
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(
                        "Failed: %s — %s", record.get("path"), result["error"]
                    )

                completed += 1
                if completed % 2000 == 0:
                    elapsed = time.monotonic() - start_time
                    rate = (success_count + error_count) / max(elapsed, 0.01)
                    logger.info(
                        "[%s] Progress: %d/%d (%.1f img/s)",
                        split,
                        completed,
                        len(work_items),
                        rate,
                    )

        logger.info("[%s] Complete: %d natural scan images added", split, completed)

    # Write updated labels
    for split in ["train", "val", "test"]:
        labels_path = skew_dir / split / "labels.json"
        with labels_path.open("w") as f:
            json.dump(synth_labels[split], f, indent=2)
        logger.info(
            "Wrote %d total labels to %s", len(synth_labels[split]), labels_path
        )

    # Write merge manifest
    elapsed = time.monotonic() - start_time
    manifest = {
        "merged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "natural_scans_processed": success_count,
        "natural_scans_errors": error_count,
        "natural_scans_excluded_low_conf": low_conf,
        "elapsed_seconds": round(elapsed, 1),
        "splits": {
            split: {
                "synthetic": len(synth_labels[split])
                - len(
                    [
                        v
                        for v in synth_labels[split].values()
                        if v.get("source_type") == "natural_scan"
                    ]
                ),
                "natural_scan": len(
                    [
                        v
                        for v in synth_labels[split].values()
                        if v.get("source_type") == "natural_scan"
                    ]
                ),
                "total": len(synth_labels[split]),
            }
            for split in ["train", "val", "test"]
        },
    }
    manifest_path = skew_dir / "merge_manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Wrote merge manifest to %s", manifest_path)

    print("\n=== Merge Complete ===")
    print(f"Natural scans added: {success_count:,d} ({error_count} errors)")
    print(f"Time: {elapsed:.1f}s")
    for split in ["train", "val", "test"]:
        total = len(synth_labels[split])
        print(f"  {split}: {total:,d} total labels")
    print(f"Output: {skew_dir}")


if __name__ == "__main__":
    main()
