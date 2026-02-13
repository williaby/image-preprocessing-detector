#!/usr/bin/env python3
"""Create contact sheet montages for efficient VLM batch inspection.

Tiles multiple document images into grid contact sheets with labels,
enabling inspection of 10-15 images per VLM call instead of one at a
time. Each image is labeled with its filename for identification.

Usage:
    python scripts/audit/create_contact_sheets.py \
        --input-dir /tmp/vlm_inspection/bhutan-afs/ \
        --output-dir /tmp/vlm_inspection/bhutan-afs/contact_sheets/ \
        --cols 5 --rows 2 \
        --thumb-width 400
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

LABEL_HEIGHT = 20
PADDING = 4
BG_COLOR = (240, 240, 240)
LABEL_BG = (30, 30, 30)
LABEL_FG = (255, 255, 255)


def create_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
    cols: int = 5,
    thumb_width: int = 400,
    quality: int = 90,
) -> dict[str, int | str]:
    """Create a single contact sheet from a list of images.

    Args:
        image_paths: List of image file paths to include.
        output_path: Path to save the contact sheet.
        cols: Number of columns in the grid.
        thumb_width: Width of each thumbnail in pixels.
        quality: JPEG quality for output.

    Returns:
        Stats dict with dimensions, file count, and output size.
    """
    rows = math.ceil(len(image_paths) / cols)

    # Calculate thumbnail height from first image's aspect ratio
    sample = Image.open(image_paths[0])
    aspect = sample.height / sample.width
    thumb_height = int(thumb_width * aspect)
    sample.close()

    cell_width = thumb_width + PADDING
    cell_height = thumb_height + LABEL_HEIGHT + PADDING

    sheet_width = cols * cell_width + PADDING
    sheet_height = rows * cell_height + PADDING

    sheet = Image.new("RGB", (sheet_width, sheet_height), BG_COLOR)
    draw = ImageDraw.Draw(sheet)

    # Try to load a small font; fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for idx, img_path in enumerate(image_paths):
        row = idx // cols
        col = idx % cols

        x = col * cell_width + PADDING
        y = row * cell_height + PADDING

        try:
            img = Image.open(img_path)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img = img.resize((thumb_width, thumb_height), Image.LANCZOS)
            sheet.paste(img, (x, y))
        except Exception as exc:
            log.warning("Failed to load %s: %s", img_path.name, exc)
            draw.rectangle([x, y, x + thumb_width, y + thumb_height], fill=(200, 0, 0))

        # Draw label below thumbnail
        label_y = y + thumb_height
        draw.rectangle(
            [x, label_y, x + thumb_width, label_y + LABEL_HEIGHT],
            fill=LABEL_BG,
        )
        # Truncate filename to fit
        label_text = img_path.stem
        if len(label_text) > 35:
            label_text = label_text[:32] + "..."
        draw.text((x + 3, label_y + 2), label_text, fill=LABEL_FG, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "JPEG", quality=quality, optimize=True)

    return {
        "images": len(image_paths),
        "grid": f"{cols}x{rows}",
        "dimensions": f"{sheet_width}x{sheet_height}",
        "bytes": output_path.stat().st_size,
    }


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create contact sheet montages for VLM inspection",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory of resized images",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for contact sheets",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=5,
        help="Columns per sheet (default: 5)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=3,
        help="Rows per sheet (default: 3)",
    )
    parser.add_argument(
        "--thumb-width",
        type=int,
        default=350,
        help="Thumbnail width in pixels (default: 350)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=90,
        help="JPEG quality (default: 90)",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        log.error("Input directory not found: %s", args.input_dir)
        return 1

    images_per_sheet = args.cols * args.rows
    images = sorted(
        f
        for f in args.input_dir.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and "contact_sheet" not in f.name
    )

    log.info(
        "Creating contact sheets: %d images, %d per sheet (%dx%d)",
        len(images),
        images_per_sheet,
        args.cols,
        args.rows,
    )

    num_sheets = math.ceil(len(images) / images_per_sheet)
    for i in range(num_sheets):
        batch = images[i * images_per_sheet : (i + 1) * images_per_sheet]
        sheet_path = args.output_dir / f"contact_sheet_{i + 1:03d}.jpg"
        stats = create_contact_sheet(
            batch,
            sheet_path,
            args.cols,
            args.thumb_width,
            args.quality,
        )
        log.info(
            "  Sheet %d/%d: %d images, %s, %s, %d KB",
            i + 1,
            num_sheets,
            stats["images"],
            stats["grid"],
            stats["dimensions"],
            stats["bytes"] // 1024,
        )

    log.info("Done: %d contact sheets created", num_sheets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
