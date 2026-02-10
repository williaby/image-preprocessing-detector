#!/usr/bin/env python3
"""Post-processing fix for Docling native layout bbox coordinates.

Docling uses PDF coordinate system (origin bottom-left, y increases upward),
so top > bottom for valid boxes. The original extraction computed height as
b - t which yielded negative values. This script fixes:
  - bbox: [x, y, width, height] -> abs()/min() corrected COCO format
  - Adds bbox_raw: [l, t, r, b] original Docling coordinates
  - Adds coord_origin: "bottom-left"
  - Recalculates area as abs(width * height)
"""

import json
import sys
from pathlib import Path


def fix_layout_file(path: Path, dry_run: bool = False) -> dict:
    """Fix bbox values in a single layout batch file.

    Returns stats dict with counts.
    """
    with open(path) as f:
        data = json.load(f)

    annotations = data.get("annotations", [])
    stats = {"total": len(annotations), "fixed": 0, "already_ok": 0, "no_bbox": 0}

    for ann in annotations:
        bbox = ann.get("bbox")
        if not bbox or len(bbox) != 4:
            stats["no_bbox"] += 1
            continue

        x, y, w, h = bbox

        if w >= 0 and h >= 0 and "bbox_raw" in ann:
            stats["already_ok"] += 1
            continue

        # Reconstruct raw coordinates from the buggy bbox
        # Original code did: bbox = [l, t, r-l, b-t] where t > b (PDF coords)
        # So: x=l, y=t, w=r-l, h=b-t (h negative because b < t in PDF coords)
        l = x  # x was set to l
        t = y  # y was set to t
        r = x + w  # w = r - l, so r = x + w
        b = y + h  # h = b - t, so b = y + h

        # Fix to proper COCO format
        x_min = min(l, r)
        y_min = min(t, b)
        width = abs(w)
        height = abs(h)

        ann["bbox"] = [float(x_min), float(y_min), float(width), float(height)]
        ann["bbox_raw"] = [float(l), float(t), float(r), float(b)]
        ann["coord_origin"] = "bottom-left"
        ann["area"] = float(width * height)
        stats["fixed"] += 1

    if not dry_run and stats["fixed"] > 0:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    return stats


def fix_dataset(dataset_dir: Path, dry_run: bool = False) -> None:
    """Fix all layout batch files in a dataset directory."""
    layout_files = sorted(dataset_dir.glob("layout_batch_*.json"))
    if not layout_files:
        # Check for layout/ subdirectory
        layout_files = sorted(dataset_dir.glob("layout/layout_batch_*.json"))

    if not layout_files:
        print(f"  No layout files found in {dataset_dir}")
        return

    total_stats = {"total": 0, "fixed": 0, "already_ok": 0, "no_bbox": 0}

    for lf in layout_files:
        stats = fix_layout_file(lf, dry_run=dry_run)
        for k in total_stats:
            total_stats[k] += stats[k]

    action = "Would fix" if dry_run else "Fixed"
    print(
        f"  {len(layout_files)} files | "
        f"{total_stats['total']} annotations | "
        f"{action}: {total_stats['fixed']} | "
        f"Already OK: {total_stats['already_ok']} | "
        f"No bbox: {total_stats['no_bbox']}"
    )


def main() -> None:
    base_dir = Path("/mnt/e/image_detection/metadata_registry/extracted")

    # Only fix docling-native v2.0 datasets (the ones with negative bboxes)
    affected_datasets = [
        "arabic-docs",
        "bhutan-afs",
        "cvsi",
        "dibco",
        "realdae",
        "signatr6k",
        "siw13",
        "tobacco800",
    ]

    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN (no files modified) ===\n")
    else:
        print("=== Fixing Docling native bbox coordinates ===\n")

    for ds_name in affected_datasets:
        ds_dir = base_dir / ds_name
        if not ds_dir.exists():
            print(f"[SKIP] {ds_name}: directory not found")
            continue
        print(f"[{'CHECK' if dry_run else 'FIX'}] {ds_name}:")
        fix_dataset(ds_dir, dry_run=dry_run)

    if not dry_run:
        print("\nDone. All bbox values corrected to positive COCO format.")
        print("Added bbox_raw and coord_origin fields for traceability.")


if __name__ == "__main__":
    main()
