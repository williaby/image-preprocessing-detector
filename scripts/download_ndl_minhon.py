#!/usr/bin/env python3
"""Download ndl-minhon-ocrdataset images from IIIF endpoints.

Downloads page images for the kuzushiji/classical Japanese handwriting dataset.
Uses v2_metadata.csv which has 47,619 entries with IIIF image URLs.

Usage:
    uv run python scripts/download_ndl_minhon.py --output-dir /mnt/e/image_detection/01_base_data/handwriting/ndl-minhon/images
    uv run python scripts/download_ndl_minhon.py --max-images 500
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path

import click
import requests
from PIL import Image

logger = logging.getLogger(__name__)

MINHON_ROOT = Path(
    "/mnt/e/image_detection/01_base_data/handwriting/ndl-minhon"
)


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=MINHON_ROOT / "images",
    help="Output directory for images",
)
@click.option("--max-images", type=int, default=None, help="Max images to download")
@click.option(
    "--version",
    type=click.Choice(["v1", "v2"]),
    default="v2",
    help="Metadata version to use",
)
def main(output_dir: Path, max_images: int | None, version: str) -> None:
    """Download ndl-minhon images from IIIF endpoints."""
    logging.basicConfig(level=logging.INFO)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = MINHON_ROOT / f"{version}_metadata.csv"
    if not csv_path.exists():
        logger.error("Metadata CSV not found: %s", csv_path)
        return

    downloaded = 0
    failed = 0
    skipped = 0
    total = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            total += 1
            if max_images and downloaded >= max_images:
                break

            img_url = row.get("Image URL", "")
            if not img_url:
                failed += 1
                continue

            # Build output filename from identifiers
            if version == "v2":
                project_id = row.get("Project ID ", "").strip()
                book_id = row.get("Book ID", "").strip()
                file_id = row.get("File ID(Minna De Honkoku)", "").strip()
                rel_dir = output_dir / project_id / book_id
                filename = f"{file_id}.png"
            else:
                book_id = row.get("Book ID", "").strip()
                file_id = row.get("File ID(NDL)", "").strip()
                rel_dir = output_dir / book_id
                filename = f"{file_id}.png"

            rel_dir.mkdir(parents=True, exist_ok=True)
            output_path = rel_dir / filename

            if output_path.exists():
                skipped += 1
                continue

            try:
                resp = requests.get(img_url, timeout=60)
                resp.raise_for_status()

                # Save as PNG
                jpg_path = output_path.with_suffix(".jpg")
                jpg_path.write_bytes(resp.content)
                img = Image.open(jpg_path).convert("RGB")
                img.save(output_path, "PNG")
                jpg_path.unlink()

                downloaded += 1
                if downloaded % 100 == 0:
                    logger.info("Progress: %d downloaded, %d failed", downloaded, failed)
                time.sleep(0.5)  # Rate limiting

            except Exception:
                logger.exception("Failed: %s", img_url[:80])
                failed += 1
                continue

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed (of %d total)",
        downloaded,
        skipped,
        failed,
        total,
    )


if __name__ == "__main__":
    main()
