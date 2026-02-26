#!/usr/bin/env python3
"""Download NDL-DocL full images from NDL Digital Collections.

The layout-dataset repo only includes samples. Full images must be downloaded
from NDL's IIIF endpoint using PIDs from the annotation XML files.

Usage:
    uv run python scripts/download_ndl_docl.py --output-dir /mnt/e/image_detection/01_base_data/language/multilingual_scripts/ndl-docl/full_images
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

import click
import requests
from PIL import Image

logger = logging.getLogger(__name__)

NDL_DOCL_ROOT = Path(
    "/mnt/e/image_detection/01_base_data/language/multilingual_scripts/ndl-docl"
)
IIIF_BASE = "https://www.dl.ndl.go.jp/api/iiif"


def get_iiif_url(pid: str, frame: int) -> str:
    """Construct IIIF image URL for NDL digital collection item."""
    return f"{IIIF_BASE}/{pid}/R{frame:07d}/full/full/0/default.jpg"


def find_annotation_pids(annotation_dir: Path) -> list[dict]:
    """Extract PIDs and frame numbers from annotation directory structure."""
    records = []
    for xml_file in sorted(annotation_dir.rglob("*.xml")):
        # Parse PID and frame from filename pattern: {PID}_{frame}.xml
        stem = xml_file.stem
        match = re.match(r"(\d+)_(\d+)", stem)
        if match:
            pid = match.group(1)
            frame = int(match.group(2))
            records.append(
                {
                    "pid": pid,
                    "frame": frame,
                    "xml_path": str(xml_file),
                    "filename": f"{pid}_{frame}",
                    "subset": xml_file.parent.name,
                }
            )
    return records


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=NDL_DOCL_ROOT / "full_images",
    help="Output directory for downloaded images",
)
@click.option("--max-images", type=int, default=None, help="Max images to download")
@click.option(
    "--subset",
    type=click.Choice(["all", "kotenseki", "kindai"]),
    default="all",
    help="Which subset to download",
)
def main(output_dir: Path, max_images: int | None, subset: str) -> None:
    """Download NDL-DocL images from IIIF endpoint."""
    logging.basicConfig(level=logging.INFO)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all annotation XML files to get PID list
    annotation_dir = NDL_DOCL_ROOT / "tugidigi-annotation"
    if not annotation_dir.exists():
        logger.error("Annotation directory not found: %s", annotation_dir)
        return

    records = find_annotation_pids(annotation_dir)
    logger.info("Found %d annotated pages", len(records))

    if subset != "all":
        records = [r for r in records if subset in r["xml_path"]]
        logger.info("Filtered to %d records for subset '%s'", len(records), subset)

    downloaded = 0
    failed = 0
    skipped = 0

    for record in records:
        if max_images and downloaded >= max_images:
            break

        pid = record["pid"]
        frame = record["frame"]
        filename = record["filename"]
        subset_dir = output_dir / record.get("subset", "unknown")
        subset_dir.mkdir(parents=True, exist_ok=True)
        output_path = subset_dir / f"{filename}.png"

        if output_path.exists():
            skipped += 1
            continue

        url = get_iiif_url(pid, frame)

        try:
            logger.info("Downloading %s (PID=%s, frame=%d)", filename, pid, frame)
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            # Save as PNG for consistency
            jpg_path = output_path.with_suffix(".jpg")
            jpg_path.write_bytes(resp.content)
            img = Image.open(jpg_path).convert("RGB")
            img.save(output_path, "PNG")
            jpg_path.unlink()

            downloaded += 1
            logger.info("Saved %s (%dx%d)", output_path.name, img.width, img.height)
            time.sleep(1)  # Rate limiting

        except Exception:
            logger.exception("Failed to download %s", filename)
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
