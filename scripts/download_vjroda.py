#!/usr/bin/env python3
"""Download VJRODa images from source PDFs.

VJRODa provides PDF URLs; images must be rendered from specific pages.
Uses PyMuPDF (fitz) to render PDF pages at 150 DPI (matching paper methodology).

Usage:
    uv run python scripts/download_vjroda.py --output-dir /mnt/e/image_detection/01_base_data/language/multilingual_scripts/vjroda/images
    uv run python scripts/download_vjroda.py --output-dir /mnt/e/image_detection/01_base_data/language/multilingual_scripts/vjroda/images --max-images 20
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import click
import fitz  # PyMuPDF
import requests
from PIL import Image

logger = logging.getLogger(__name__)

VJRODA_ROOT = Path(
    "/mnt/e/image_detection/01_base_data/language/multilingual_scripts/vjroda"
)
DPI = 150  # Match paper methodology


def render_pdf_page(pdf_bytes: bytes, page_num: int, dpi: int = DPI) -> Image.Image:
    """Render a specific page from a PDF to a PIL Image."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_num >= len(doc):
        msg = f"Page {page_num} out of range (PDF has {len(doc)} pages)"
        raise ValueError(msg)
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=VJRODA_ROOT / "images",
    help="Output directory for rendered images",
)
@click.option("--max-images", type=int, default=None, help="Max images to download")
@click.option("--dpi", type=int, default=DPI, help="Render DPI")
@click.option("--use-warp/--no-use-warp", default=True, help="Prefer WARP URLs")
def main(output_dir: Path, max_images: int | None, dpi: int, use_warp: bool) -> None:
    """Download and render VJRODa images from source PDFs."""
    logging.basicConfig(level=logging.INFO)
    output_dir.mkdir(parents=True, exist_ok=True)

    url_list_path = VJRODA_ROOT / "url_list.jsonl"
    if not url_list_path.exists():
        logger.error("url_list.jsonl not found at %s", url_list_path)
        return

    records = []
    with open(url_list_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    logger.info("Found %d records in url_list.jsonl", len(records))

    downloaded = 0
    failed = 0
    skipped = 0

    for record in records:
        if max_images and downloaded >= max_images:
            break

        image_id = record["id"]
        page_num = record["page"]
        output_path = output_dir / f"{image_id}.png"

        if output_path.exists():
            skipped += 1
            continue

        # Choose URL (prefer WARP for stability)
        url = record.get("warp_url", "") if use_warp else ""
        if not url:
            raw_url = record.get("url", "")
            url = raw_url if raw_url.startswith("http") else f"https://{raw_url}"

        if not url:
            logger.warning("No URL for %s, skipping", image_id)
            failed += 1
            continue

        try:
            logger.info(
                "Downloading %s (page %d) from %s", image_id, page_num, url[:80]
            )
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            img = render_pdf_page(resp.content, page_num, dpi=dpi)
            img.save(output_path, "PNG")
            downloaded += 1
            logger.info("Saved %s (%dx%d)", output_path.name, img.width, img.height)

            time.sleep(1)  # Rate limiting

        except Exception:
            logger.exception("Failed to download/render %s", image_id)
            failed += 1
            continue

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed (of %d total)",
        downloaded,
        skipped,
        failed,
        len(records),
    )


if __name__ == "__main__":
    main()
