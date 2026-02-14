#!/usr/bin/env python3
"""Generate full-dataset contact sheets for HierText Phase 6 VLM inspection.

Generates 233 contact sheets (10x5 grid, 50 images each) covering all 11,639
HierText images for full-dataset VLM visual inspection. Streaming approach
loads one image at a time to minimize memory.

Output:
    tmp_cleanup/hiertext_contact_sheets/
        contact_sheet_001.jpg .. contact_sheet_233.jpg
        manifest.json

Usage:
    python scripts/generate_hiertext_contact_sheets.py [--metadata PATH]
"""

from __future__ import annotations

import gc
import json
import logging
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IMAGE_BASE = Path("/mnt/e/image_detection/01_base_data/text_detection/hiertext")
METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/hiertext_metadata.json"
)
OUTPUT_DIR = Path("tmp_cleanup/hiertext_contact_sheets")

# Contact sheet grid: 10 cols x 5 rows = 50 per sheet
COLS = 10
ROWS = 5
IMAGES_PER_SHEET = COLS * ROWS  # 50
THUMB_WIDTH = 200
THUMB_HEIGHT = 150  # Larger for scene text readability
PADDING = 3
LABEL_HEIGHT = 14
BG_COLOR = (240, 240, 240)
LABEL_BG = (30, 30, 30)
LABEL_FG = (255, 255, 255)
JPEG_QUALITY = 90


# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------
def load_image_list(metadata_path: Path) -> list[dict[str, str]]:
    """Load image list from metadata, sorted by split then filename.

    Metadata structure: top-level has 'samples' list, each sample has:
    - source.original_path (e.g. "test/00077e330dbb3c57.jpg")
    - source.original_filename (e.g. "00077e330dbb3c57.jpg")
    - source.split (e.g. "test")
    - enrichments.versions[-1].data.split (post-integration)

    Args:
        metadata_path: Path to hiertext_metadata.json.

    Returns:
        List of dicts with 'image_id', 'filename', 'split', 'path'.
    """
    log.info("Loading metadata from %s", metadata_path)
    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])
    images: list[dict[str, str]] = []
    split_order = {"train": 0, "validation": 1, "test": 2}

    for sample in samples:
        source = sample.get("source", {})
        original_path = source.get("original_path", "")
        filename = source.get("original_filename", "")

        # Get split from enrichments (post-integration) or source
        split = "unknown"
        versions = sample.get("enrichments", {}).get("versions", [])
        if versions:
            split = versions[-1].get("data", {}).get("split", "unknown")
        if split == "unknown":
            split = source.get("split", "unknown")

        # Use original_path for filename if needed
        if not filename and original_path:
            filename = Path(original_path).name

        # Image ID is the filename stem (hash)
        image_id = Path(filename).stem if filename else sample.get("id", "unknown")

        # Build full path: IMAGE_BASE / split / filename
        img_path = IMAGE_BASE / split / filename

        images.append(
            {
                "image_id": image_id,
                "filename": filename,
                "split": split,
                "path": str(img_path),
            }
        )

    # Sort by split order, then filename
    images.sort(key=lambda x: (split_order.get(x["split"], 9), x["filename"]))
    log.info(
        "  Found %d images (train=%d, val=%d, test=%d)",
        len(images),
        sum(1 for i in images if i["split"] == "train"),
        sum(1 for i in images if i["split"] == "validation"),
        sum(1 for i in images if i["split"] == "test"),
    )
    return images


# ---------------------------------------------------------------------------
# Streaming contact sheet generation
# ---------------------------------------------------------------------------
def generate_contact_sheet(
    image_entries: list[dict[str, str]],
    output_path: Path,
    sheet_number: int,
    start_index: int,
) -> dict[str, Any]:
    """Generate a single contact sheet with streaming image loading.

    Args:
        image_entries: List of image info dicts (max IMAGES_PER_SHEET).
        output_path: Where to save the contact sheet JPEG.
        sheet_number: Sheet index for logging/manifest.
        start_index: Global image index of first image on this sheet.

    Returns:
        Stats dict with dimensions, file count, byte size.
    """
    from PIL import Image, ImageDraw, ImageFont

    rows = math.ceil(len(image_entries) / COLS)
    cell_width = THUMB_WIDTH + PADDING
    cell_height = THUMB_HEIGHT + LABEL_HEIGHT + PADDING
    sheet_width = COLS * cell_width + PADDING
    sheet_height = rows * cell_height + PADDING

    sheet = Image.new("RGB", (sheet_width, sheet_height), BG_COLOR)
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except OSError:
        font = ImageFont.load_default()

    loaded_count = 0
    errors: list[str] = []

    for idx, entry in enumerate(image_entries):
        row = idx // COLS
        col = idx % COLS
        x = col * cell_width + PADDING
        y = row * cell_height + PADDING

        img_path = Path(entry["path"])
        try:
            img = Image.open(img_path)
            if img.mode not in ("RGB",):
                img = img.convert("RGB")

            img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
            x_offset = (THUMB_WIDTH - img.width) // 2
            y_offset = (THUMB_HEIGHT - img.height) // 2
            sheet.paste(img, (x + x_offset, y + y_offset))
            img.close()
            loaded_count += 1
        except Exception as exc:
            errors.append(f"{entry['image_id']}: {exc}")
            draw.rectangle(
                [x, y, x + THUMB_WIDTH, y + THUMB_HEIGHT],
                fill=(200, 0, 0),
            )

        # Label below thumbnail: global position + truncated image_id
        label_y = y + THUMB_HEIGHT
        draw.rectangle(
            [x, label_y, x + THUMB_WIDTH, label_y + LABEL_HEIGHT],
            fill=LABEL_BG,
        )
        global_pos = start_index + idx + 1
        label_text = entry["image_id"]
        if len(label_text) > 18:
            label_text = label_text[:15] + "..."
        draw.text(
            (x + 2, label_y + 1),
            f"{global_pos}. {label_text}",
            fill=LABEL_FG,
            font=font,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    file_size = output_path.stat().st_size
    sheet.close()

    return {
        "sheet_number": sheet_number,
        "images_loaded": loaded_count,
        "images_total": len(image_entries),
        "errors": errors,
        "grid": f"{COLS}x{rows}",
        "dimensions": f"{sheet_width}x{sheet_height}",
        "bytes": file_size,
    }


def generate_all_sheets(
    images: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Generate all contact sheets for the full dataset.

    Args:
        images: Full sorted image list.

    Returns:
        Manifest entries mapping sheet positions to image IDs.
    """
    num_sheets = math.ceil(len(images) / IMAGES_PER_SHEET)
    log.info(
        "Generating %d contact sheets (%d images, %d per sheet, %dx%d grid)",
        num_sheets,
        len(images),
        IMAGES_PER_SHEET,
        COLS,
        ROWS,
    )

    manifest: list[dict[str, Any]] = []
    total_errors = 0

    for sheet_idx in range(num_sheets):
        start = sheet_idx * IMAGES_PER_SHEET
        end = min(start + IMAGES_PER_SHEET, len(images))
        batch = images[start:end]

        sheet_path = OUTPUT_DIR / f"contact_sheet_{sheet_idx + 1:03d}.jpg"
        stats = generate_contact_sheet(batch, sheet_path, sheet_idx + 1, start)

        total_errors += len(stats["errors"])

        sheet_manifest = {
            "sheet_number": sheet_idx + 1,
            "sheet_path": str(sheet_path),
            "start_index": start,
            "end_index": end - 1,
            "image_count": len(batch),
            "stats": {
                "images_loaded": stats["images_loaded"],
                "grid": stats["grid"],
                "bytes": stats["bytes"],
            },
            "positions": [
                {
                    "position": i + 1,
                    "global_index": start + i + 1,
                    "image_id": batch[i]["image_id"],
                    "filename": batch[i]["filename"],
                    "split": batch[i]["split"],
                }
                for i in range(len(batch))
            ],
        }
        manifest.append(sheet_manifest)

        if (sheet_idx + 1) % 25 == 0 or (sheet_idx + 1) == num_sheets:
            log.info(
                "  Progress: %d/%d sheets (%d images, %d errors)",
                sheet_idx + 1,
                num_sheets,
                min(end, len(images)),
                total_errors,
            )

        gc.collect()

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """Generate full-dataset contact sheets for HierText Phase 6."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate HierText contact sheets for VLM inspection"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to hiertext_metadata.json",
    )
    args = parser.parse_args()

    log.info("=== HierText Phase 6: Full-Dataset Contact Sheet Generation ===")

    # Load and sort image list
    images = load_image_list(args.metadata)
    if not images:
        log.error("No images found in metadata")
        return 1

    # Verify a sample of image paths exist
    sample_paths = [Path(images[i]["path"]) for i in range(0, len(images), 1000)]
    existing = sum(1 for p in sample_paths if p.exists())
    log.info(
        "Path verification: %d/%d sample paths exist",
        existing,
        len(sample_paths),
    )
    if existing == 0:
        log.error("No image paths resolve. Check IMAGE_BASE: %s", IMAGE_BASE)
        return 1

    # Generate all contact sheets
    manifest = generate_all_sheets(images)

    # Save manifest
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).isoformat()

    manifest_output = {
        "dataset": "hiertext",
        "generated_at": timestamp,
        "grid": f"{COLS}x{ROWS}",
        "thumb_size": f"{THUMB_WIDTH}x{THUMB_HEIGHT}",
        "total_sheets": len(manifest),
        "total_images": len(images),
        "images_per_sheet": IMAGES_PER_SHEET,
        "split_distribution": {
            "train": sum(1 for i in images if i["split"] == "train"),
            "validation": sum(1 for i in images if i["split"] == "validation"),
            "test": sum(1 for i in images if i["split"] == "test"),
        },
        "sheets": manifest,
    }

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_output, indent=2))

    total_bytes = sum(s["stats"]["bytes"] for s in manifest)
    log.info("=== Contact Sheet Generation Complete ===")
    log.info("  Total sheets: %d", len(manifest))
    log.info("  Total images: %d", len(images))
    log.info("  Total size: %.1f MB", total_bytes / (1024 * 1024))
    log.info("  Output: %s", OUTPUT_DIR)
    log.info("  Manifest: %s", manifest_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
