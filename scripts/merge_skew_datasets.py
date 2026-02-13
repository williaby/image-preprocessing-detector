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


def _load_and_filter_natural_scans(
    nscan_path: Path,
    min_confidence: float,
) -> tuple[list[dict[str, Any]], int]:
    """Load natural scan labels and filter by confidence threshold.

    Args:
        nscan_path: Path to natural_scan_skew_labels.json.
        min_confidence: Minimum classical skew confidence to include.

    Returns:
        Tuple of (high-confidence images list, low-confidence excluded count).
    """
    with nscan_path.open() as f:
        nscan_data = json.load(f)

    nscan_images = nscan_data["images"]
    logger.info("Loaded %d natural scan labels", len(nscan_images))

    high_conf = [
        img
        for img in nscan_images
        if img.get("classical_skew_confidence", 0) >= min_confidence
        and img.get("classical_skew_error") is None
    ]
    low_conf = len(nscan_images) - len(high_conf)
    logger.info(
        "After confidence filter (>= %.2f): %d kept, %d excluded",
        min_confidence,
        len(high_conf),
        low_conf,
    )
    return high_conf, low_conf


def _load_synth_labels(skew_dir: Path) -> dict[str, dict[str, Any]]:
    """Load existing synthetic labels for all splits.

    Args:
        skew_dir: Root skew dataset directory.

    Returns:
        Dict mapping split name to labels dict.
    """
    synth_labels: dict[str, dict[str, Any]] = {}
    for split in ["train", "val", "test"]:
        labels_path = skew_dir / split / "labels.json"
        if labels_path.exists():
            with labels_path.open() as f:
                synth_labels[split] = json.load(f)
        else:
            synth_labels[split] = {}
    return synth_labels


def _print_merge_plan(
    high_conf: list[dict[str, Any]],
    nscan_total: int,
    splits: dict[str, list[dict[str, Any]]],
    synth_labels: dict[str, dict[str, Any]],
) -> None:
    """Print merge plan statistics.

    Args:
        high_conf: High-confidence natural scan images.
        nscan_total: Total natural scan images before filtering.
        splits: Natural scan images grouped by split.
        synth_labels: Existing synthetic labels by split.
    """
    print("\n=== Merge Plan ===")
    print(f"Natural scan labels: {len(high_conf)} (filtered from {nscan_total})")
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
    print(
        f"\n  Total: {grand_synth:,d} synthetic + {grand_nscan:,d} natural = {grand_synth + grand_nscan:,d}"
    )

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


def _build_natural_scan_label(record: dict[str, Any]) -> dict[str, Any]:
    """Build a label entry from a natural scan record.

    Args:
        record: Natural scan image record.

    Returns:
        Label dict for the labels.json file.
    """
    return {
        "angle": record["classical_skew_angle"],
        "orientation": 0,
        "skew_bin": -1,
        "script": record.get("script", "Latn"),
        "degradation": "natural",
        "source": record.get("filename", "unknown"),
        "source_type": "natural_scan",
        "dataset": record.get("dataset", "unknown"),
        "text_direction": record.get("text_direction", "ltr"),
        "capture_method": record.get("capture_method", "unknown"),
        "classical_confidence": record.get("classical_skew_confidence", 0),
        "classical_method": record.get("classical_skew_method", "unknown"),
    }


def _process_natural_scans_for_split(
    split: str,
    split_imgs: list[dict[str, Any]],
    skew_dir: Path,
    synth_labels: dict[str, dict[str, Any]],
    nscan_idx: int,
    workers: int,
    start_time: float,
) -> tuple[int, int, int]:
    """Process natural scan images for a single split.

    Args:
        split: Split name.
        split_imgs: Natural scan images for this split.
        skew_dir: Root skew dataset directory.
        synth_labels: Labels dict to update in-place.
        nscan_idx: Starting index for natural scan filenames.
        workers: Number of parallel workers.
        start_time: Start time for rate calculation.

    Returns:
        Tuple of (success_count, error_count, updated nscan_idx).
    """
    split_img_dir = skew_dir / split / "images"
    split_img_dir.mkdir(parents=True, exist_ok=True)

    work_items = []
    nscan_meta: list[tuple[dict[str, Any], int]] = []
    for img_record in split_imgs:
        work_items.append((img_record["path"], str(split_img_dir), nscan_idx))
        nscan_meta.append((img_record, nscan_idx))
        nscan_idx += 1

    logger.info("[%s] Processing %d natural scan images...", split, len(work_items))
    success_count = 0
    error_count = 0
    completed = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        for result, (record, _idx) in zip(
            executor.map(process_natural_image, work_items, chunksize=50),
            nscan_meta,
            strict=True,
        ):
            if result["success"]:
                synth_labels[split][result["filename"]] = _build_natural_scan_label(
                    record
                )
                success_count += 1
            else:
                error_count += 1
                logger.warning("Failed: %s — %s", record.get("path"), result["error"])

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
    return success_count, error_count, nscan_idx


def _write_merge_outputs(
    skew_dir: Path,
    synth_labels: dict[str, dict[str, Any]],
    success_count: int,
    error_count: int,
    low_conf: int,
    elapsed: float,
) -> None:
    """Write updated labels and merge manifest.

    Args:
        skew_dir: Root skew dataset directory.
        synth_labels: Updated labels by split.
        success_count: Total successfully processed natural scans.
        error_count: Total processing errors.
        low_conf: Number of low-confidence images excluded.
        elapsed: Total elapsed time in seconds.
    """
    for split in ["train", "val", "test"]:
        labels_path = skew_dir / split / "labels.json"
        with labels_path.open("w") as f:
            json.dump(synth_labels[split], f, indent=2)
        logger.info(
            "Wrote %d total labels to %s", len(synth_labels[split]), labels_path
        )

    manifest = {
        "merged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "natural_scans_processed": success_count,
        "natural_scans_errors": error_count,
        "natural_scans_excluded_low_conf": low_conf,
        "elapsed_seconds": round(elapsed, 1),
        "splits": {
            split: {
                "synthetic": len(synth_labels[split])
                - sum(
                    1
                    for v in synth_labels[split].values()
                    if v.get("source_type") == "natural_scan"
                ),
                "natural_scan": sum(
                    1
                    for v in synth_labels[split].values()
                    if v.get("source_type") == "natural_scan"
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
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
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

    nscan_path = args.skew_dir / "natural_scan_skew_labels.json"
    if not nscan_path.exists():
        logger.error("Natural scan labels not found: %s", nscan_path)
        return

    high_conf, low_conf = _load_and_filter_natural_scans(
        nscan_path, args.min_confidence
    )

    # Group by split
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for img in high_conf:
        split = img.get("split", "train")
        if split in splits:
            splits[split].append(img)

    synth_labels = _load_synth_labels(args.skew_dir)
    _print_merge_plan(high_conf, len(high_conf) + low_conf, splits, synth_labels)

    if args.dry_run:
        print("\n[DRY RUN] No images processed.")
        return

    # Process natural scan images
    start_time = time.monotonic()
    total_success = 0
    total_errors = 0
    nscan_idx = 0

    for split in ["train", "val", "test"]:
        if not splits[split]:
            continue
        s_count, e_count, nscan_idx = _process_natural_scans_for_split(
            split,
            splits[split],
            args.skew_dir,
            synth_labels,
            nscan_idx,
            args.workers,
            start_time,
        )
        total_success += s_count
        total_errors += e_count

    elapsed = time.monotonic() - start_time
    _write_merge_outputs(
        args.skew_dir, synth_labels, total_success, total_errors, low_conf, elapsed
    )

    print("\n=== Merge Complete ===")
    print(f"Natural scans added: {total_success:,d} ({total_errors} errors)")
    print(f"Time: {elapsed:.1f}s")
    for split in ["train", "val", "test"]:
        total = len(synth_labels[split])
        print(f"  {split}: {total:,d} total labels")
    print(f"Output: {args.skew_dir}")


if __name__ == "__main__":
    main()
