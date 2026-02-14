#!/usr/bin/env python3
"""Extract images from IndicDLP HuggingFace Parquet files to standalone PNGs.

Reads Parquet files with embedded PNG bytes and writes them to disk
alongside COCO-format JSON annotations.

Usage:
    PYTHONPATH=. uv run python scripts/extract_indicdlp_images.py
    PYTHONPATH=. uv run python scripts/extract_indicdlp_images.py --max-per-split 100
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path("/mnt/e/image_detection/01_base_data/layout/indicdlp")
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"


def extract_split(
    split_prefix: str,
    max_images: int | None = None,
) -> int:
    """Extract images for a single split (train/test/validation).

    Supports resume: skips files that already exist on disk.
    Returns number of images extracted (new + existing).
    """
    parquet_files = sorted(DATA_DIR.glob(f"{split_prefix}-*.parquet"))
    if not parquet_files:
        logger.warning("No parquet files found for split: %s", split_prefix)
        return 0

    split_dir = IMAGES_DIR / split_prefix
    split_dir.mkdir(parents=True, exist_ok=True)

    # Load existing annotations for resume
    ann_path = split_dir / "annotations.json"
    existing_annotations: list[dict] = []
    existing_fnames: set[str] = set()
    if ann_path.exists():
        with ann_path.open() as f:
            existing_annotations = json.load(f)
            existing_fnames = {a["file_name"] for a in existing_annotations}

    # Also check for files on disk without annotations
    for p in split_dir.glob("*.png"):
        existing_fnames.add(p.name)

    annotations = list(existing_annotations)
    new_extracted = 0
    total_count = len(existing_fnames)

    if existing_fnames:
        logger.info("  Resuming: %d existing images found", len(existing_fnames))

    for pf_path in parquet_files:
        table = pq.read_table(pf_path)
        num_rows = len(table)

        pf_new = 0
        pf_skipped = 0

        for i in range(num_rows):
            if max_images is not None and total_count >= max_images:
                break

            image_data = table.column("image")[i].as_py()
            img_bytes = image_data.get("bytes")
            img_path = image_data.get("path", "")

            if not img_bytes:
                continue

            # Determine filename
            if img_path:
                fname = Path(img_path).name
            else:
                fname = f"{split_prefix}_{total_count:06d}.png"

            # Skip if already extracted
            if fname in existing_fnames:
                pf_skipped += 1
                total_count += 1
                continue

            out_path = split_dir / fname
            out_path.write_bytes(img_bytes)

            # Extract bboxes and category_ids
            bboxes = table.column("bboxes")[i].as_py()
            category_ids = table.column("category_ids")[i].as_py()

            annotations.append(
                {
                    "file_name": fname,
                    "bboxes": bboxes,
                    "category_ids": category_ids,
                }
            )

            existing_fnames.add(fname)
            new_extracted += 1
            pf_new += 1
            total_count += 1

        logger.info(
            "  %s: %d rows, %d new, %d skipped",
            pf_path.name,
            num_rows,
            pf_new,
            pf_skipped,
        )

        if max_images is not None and total_count >= max_images:
            break

    # Write merged annotations JSON
    with ann_path.open("w") as f:
        json.dump(annotations, f, indent=2)

    logger.info(
        "  Split %s: %d new + %d existing = %d total, annotations at %s",
        split_prefix,
        new_extracted,
        len(existing_fnames) - new_extracted,
        total_count,
        ann_path,
    )
    return total_count


def main() -> int:
    """Extract all images from IndicDLP Parquet files."""
    parser = argparse.ArgumentParser(description="Extract IndicDLP images")
    parser.add_argument(
        "--max-per-split",
        type=int,
        default=None,
        help="Max images per split (default: all)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help="Only process this split (default: all)",
    )
    args = parser.parse_args()

    if not DATA_DIR.exists():
        logger.error("Data directory not found: %s", DATA_DIR)
        return 1

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Discover splits from parquet filenames
    splits = set()
    for f in DATA_DIR.glob("*.parquet"):
        split_name = f.name.split("-")[0]
        if args.split and split_name != args.split:
            continue
        splits.add(split_name)

    splits_sorted = sorted(splits)
    logger.info("Found splits: %s", splits_sorted)

    total = 0
    for split in splits_sorted:
        logger.info("Extracting split: %s", split)
        count = extract_split(split, args.max_per_split)
        total += count

    logger.info("Total images extracted: %d", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
