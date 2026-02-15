#!/usr/bin/env python3
"""Extract images from MarkushGrapher HuggingFace Arrow files to standalone PNGs.

Reads Arrow files containing page_image (HF Image type) and writes to disk.

Usage:
    PYTHONPATH=. uv run python scripts/extract_markushgrapher_images.py
    PYTHONPATH=. uv run python scripts/extract_markushgrapher_images.py --max-per-subset 100
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path("/mnt/e/image_detection/01_base_data/specialized/markushgrapher")
IMAGES_DIR = BASE_DIR / "images"


def extract_subset(
    subset_name: str,
    subset_dir: Path,
    max_images: int | None = None,
    target_split: str | None = None,
) -> int:
    """Extract images from a single subset (m2s, markushgrapher-synthetic, etc.).

    Supports resume: skips files that already exist on disk.
    Returns number of images extracted (new + existing).
    """
    from datasets import load_dataset

    arrow_files = sorted(subset_dir.rglob("*.arrow"))
    if not arrow_files:
        logger.warning("No arrow files in %s", subset_dir)
        return 0

    out_dir = IMAGES_DIR / subset_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load existing files for resume
    existing_fnames: set[str] = set()
    for p in out_dir.glob("*.png"):
        existing_fnames.add(p.name)

    # Load existing metadata for resume
    meta_path = out_dir / "metadata.json"
    metadata_records: list[dict] = []
    if meta_path.exists():
        with meta_path.open() as f:
            metadata_records = json.load(f)

    if existing_fnames:
        logger.info("  Resuming: %d existing images found", len(existing_fnames))

    new_extracted = 0
    total_count = len(existing_fnames)

    # Load all splits in this subset
    for split_entry in sorted(subset_dir.iterdir()):
        if not split_entry.is_dir():
            continue

        split_arrows = sorted(split_entry.glob("*.arrow"))
        if not split_arrows:
            continue

        split_name = split_entry.name

        # Skip splits if target_split specified
        if target_split and split_name != target_split:
            logger.info("  Skipping %s/%s (not target split)", subset_name, split_name)
            continue

        logger.info(
            "  Loading %s/%s (%d arrow files)",
            subset_name,
            split_name,
            len(split_arrows),
        )

        ds = load_dataset(
            "arrow",
            data_files=[str(f) for f in split_arrows],
            split="train",
        )

        for i, row in enumerate(ds):
            if max_images is not None and total_count >= max_images:
                break

            image = row.get("page_image")
            image_name = row.get("image_name", f"{split_name}_{i:06d}")

            if image is None:
                continue

            # Save image as PNG
            fname = (
                f"{image_name}.png" if not image_name.endswith(".png") else image_name
            )
            full_fname = f"{split_name}_{fname}"

            # Skip if already extracted
            if full_fname in existing_fnames:
                total_count += 1
                continue

            out_path = out_dir / full_fname
            image.save(out_path)

            # Collect metadata
            record = {
                "file_name": full_fname,
                "split": split_name,
                "subset": subset_name,
            }
            for field in ("description", "cxsmiles", "annotation"):
                if row.get(field):
                    record[field] = str(row[field])[:500]

            metadata_records.append(record)
            existing_fnames.add(full_fname)
            new_extracted += 1
            total_count += 1

            # Periodic progress logging
            if new_extracted % 5000 == 0:
                logger.info("    Progress: %d new images extracted", new_extracted)

        if max_images is not None and total_count >= max_images:
            break

    # Write merged metadata
    with meta_path.open("w") as f:
        json.dump(metadata_records, f, indent=2)

    logger.info(
        "  Subset %s: %d new + %d existing = %d total",
        subset_name,
        new_extracted,
        len(existing_fnames) - new_extracted,
        total_count,
    )
    return total_count


def main() -> int:
    """Extract all images from MarkushGrapher Arrow files."""
    parser = argparse.ArgumentParser(description="Extract MarkushGrapher images")
    parser.add_argument(
        "--max-per-subset",
        type=int,
        default=None,
        help="Max images per subset (default: all)",
    )
    parser.add_argument(
        "--subset",
        type=str,
        default=None,
        help="Only process this subset (default: all)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        help="Only process this split within subset (default: all)",
    )
    args = parser.parse_args()

    if not BASE_DIR.exists():
        logger.error("Base directory not found: %s", BASE_DIR)
        return 1

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Discover subsets (directories with arrow files)
    subsets = []
    for d in sorted(BASE_DIR.iterdir()):
        if d.is_dir() and d.name != "images" and list(d.rglob("*.arrow")):
            if args.subset and d.name != args.subset:
                continue
            subsets.append(d.name)

    logger.info("Found subsets: %s", subsets)

    total = 0
    for subset in subsets:
        logger.info("Extracting subset: %s", subset)
        count = extract_subset(
            subset,
            BASE_DIR / subset,
            args.max_per_subset,
            args.split,
        )
        total += count

    logger.info("Total images extracted: %d", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
