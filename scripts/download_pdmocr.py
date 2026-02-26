#!/usr/bin/env python3
"""Download PDM OCR dataset images from NDL Digital Collections.

Supports both part1 (JSON annotations) and part2 (NDLOCR XML annotations).
Downloads page images via NDL's IIIF endpoint using PIDs from info.csv.

Usage:
    uv run python scripts/download_pdmocr.py --part 1 --output-dir /mnt/e/image_detection/01_base_data/language/multilingual_scripts/pdmocr-part1/images
    uv run python scripts/download_pdmocr.py --part 2 --output-dir /mnt/e/image_detection/01_base_data/language/multilingual_scripts/pdmocr-part2/images
    uv run python scripts/download_pdmocr.py --part 1 --max-images 50
"""

from __future__ import annotations

import csv
import logging
import re
import time
from pathlib import Path

import click
import requests
from PIL import Image

logger = logging.getLogger(__name__)

PART1_ROOT = Path(
    "/mnt/e/image_detection/01_base_data/language/multilingual_scripts/pdmocr-part1"
)
PART2_ROOT = Path(
    "/mnt/e/image_detection/01_base_data/language/multilingual_scripts/pdmocr-part2"
)
IIIF_BASE = "https://www.dl.ndl.go.jp/api/iiif"


def get_iiif_url(pid: str, frame: int) -> str:
    """Construct IIIF image URL for NDL digital collection item."""
    return f"{IIIF_BASE}/{pid}/R{frame:07d}/full/full/0/default.jpg"


def parse_info_csv(csv_path: Path, part: int) -> list[dict]:
    """Parse info.csv to extract PID and frame information."""
    records = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("PID", "")
            filename = row.get("FileName", "")
            dataset_id = row.get("DatasetID", "")

            if not pid or not filename:
                continue

            # Extract frame number from filename
            # Part 1: {PID}_R{frame}.json
            # Part 2: {PID}.xml (single page per XML)
            if part == 1:
                match = re.search(r"R(\d+)", filename)
                frame = int(match.group(1)) if match else 1
            else:
                # Part 2: frame number from filename or default to 1
                frame = 1

            records.append(
                {
                    "pid": pid,
                    "frame": frame,
                    "filename": filename,
                    "dataset_id": dataset_id,
                    "decade": dataset_id.split("_")[0]
                    if "_" in dataset_id
                    else dataset_id,
                }
            )
    return records


@click.command()
@click.option(
    "--part", type=click.Choice(["1", "2"]), required=True, help="Dataset part"
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (auto-detected if not set)",
)
@click.option("--max-images", type=int, default=None, help="Max images to download")
def main(part: str, output_dir: Path | None, max_images: int | None) -> None:
    """Download PDM OCR dataset images from IIIF."""
    logging.basicConfig(level=logging.INFO)

    part_num = int(part)
    root = PART1_ROOT if part_num == 1 else PART2_ROOT
    if output_dir is None:
        output_dir = root / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = root / "info.csv"
    if not csv_path.exists():
        logger.error("info.csv not found at %s", csv_path)
        return

    records = parse_info_csv(csv_path, part_num)
    logger.info("Found %d records in info.csv (part %d)", len(records), part_num)

    # Deduplicate by PID (multiple annotation files can share same page image)
    seen_pids = set()
    unique_records = []
    for r in records:
        key = f"{r['pid']}_{r['frame']}"
        if key not in seen_pids:
            seen_pids.add(key)
            unique_records.append(r)

    logger.info("Unique pages to download: %d", len(unique_records))

    downloaded = 0
    failed = 0
    skipped = 0

    for record in unique_records:
        if max_images and downloaded >= max_images:
            break

        pid = record["pid"]
        frame = record["frame"]
        decade = record.get("decade", "unknown")
        decade_dir = output_dir / decade
        decade_dir.mkdir(parents=True, exist_ok=True)
        output_path = decade_dir / f"{pid}_{frame:04d}.png"

        if output_path.exists():
            skipped += 1
            continue

        url = get_iiif_url(pid, frame)

        try:
            logger.info("Downloading PID=%s frame=%d", pid, frame)
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            jpg_path = output_path.with_suffix(".jpg")
            jpg_path.write_bytes(resp.content)
            img = Image.open(jpg_path).convert("RGB")
            img.save(output_path, "PNG")
            jpg_path.unlink()

            downloaded += 1
            if downloaded % 50 == 0:
                logger.info("Progress: %d downloaded", downloaded)
            time.sleep(1)

        except Exception:
            logger.exception("Failed to download PID=%s", pid)
            failed += 1
            continue

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed (of %d unique pages)",
        downloaded,
        skipped,
        failed,
        len(unique_records),
    )


if __name__ == "__main__":
    main()
