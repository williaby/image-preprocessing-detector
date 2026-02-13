#!/usr/bin/env python3
"""Prepare images for VLM visual inspection during audits.

Resizes images to Claude API-safe dimensions to prevent context
window exhaustion and session crashes. Images are saved as JPEG
at reduced resolution for efficient batch inspection.

Claude API vision limits (as of 2026):
- Max single dimension: 20,000 px (hard limit)
- Auto-resize threshold: 1,568 px (recommended max)
- Context-safe max for batch inspection: 1,024 px

Usage:
    python scripts/audit/prepare_vlm_images.py \\
        --input-dir /mnt/e/image_detection/01_base_data/documents/bhutan_financial/ \\
        --output-dir /tmp/vlm_inspection/bhutan-afs/ \\
        --max-side 1024 \\
        --quality 85
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Claude API recommended limits
DEFAULT_MAX_SIDE = 1024
DEFAULT_QUALITY = 85
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def resize_image(
    input_path: Path,
    output_path: Path,
    max_side: int = DEFAULT_MAX_SIDE,
    quality: int = DEFAULT_QUALITY,
) -> dict[str, int | str]:
    """Resize a single image to fit within max_side constraint.

    Uses LANCZOS resampling for quality. Saves as JPEG for size
    efficiency. Preserves aspect ratio.

    Args:
        input_path: Source image path.
        output_path: Destination path (will be .jpg).
        max_side: Maximum pixels on longest side.
        quality: JPEG quality (1-100).

    Returns:
        Dict with original_size, new_size, original_bytes, new_bytes.
    """
    img = Image.open(input_path)
    original_size = img.size
    original_bytes = input_path.stat().st_size

    # Convert to RGB if necessary (RGBA, P, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize if needed
    if max(img.size) > max_side:
        ratio = max_side / max(img.size)
        new_width = int(img.size[0] * ratio)
        new_height = int(img.size[1] * ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)

    # Save as JPEG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    jpeg_path = output_path.with_suffix(".jpg")
    img.save(jpeg_path, "JPEG", quality=quality, optimize=True)
    new_bytes = jpeg_path.stat().st_size

    return {
        "original_width": original_size[0],
        "original_height": original_size[1],
        "new_width": img.size[0],
        "new_height": img.size[1],
        "original_bytes": original_bytes,
        "new_bytes": new_bytes,
        "reduction_pct": round((1 - new_bytes / original_bytes) * 100, 1),
    }


def prepare_directory(
    input_dir: Path,
    output_dir: Path,
    max_side: int = DEFAULT_MAX_SIDE,
    quality: int = DEFAULT_QUALITY,
) -> list[dict[str, int | str]]:
    """Resize all images in a directory.

    Args:
        input_dir: Source directory containing images.
        output_dir: Destination directory for resized images.
        max_side: Maximum pixels on longest side.
        quality: JPEG quality (1-100).

    Returns:
        List of stats dicts, one per image processed.
    """
    results: list[dict[str, int | str]] = []
    images = sorted(
        f for f in input_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    log.info("Found %d images in %s", len(images), input_dir)
    log.info("Output: %s (max_side=%d, quality=%d)", output_dir, max_side, quality)

    for i, img_path in enumerate(images):
        output_path = output_dir / img_path.name
        try:
            stats = resize_image(img_path, output_path, max_side, quality)
            stats["filename"] = img_path.name
            stats["status"] = "ok"
            results.append(stats)
            if (i + 1) % 25 == 0:
                log.info("  Processed %d/%d images", i + 1, len(images))
        except Exception as exc:
            log.warning("  Failed %s: %s", img_path.name, exc)
            results.append({"filename": img_path.name, "status": f"error: {exc}"})

    total_orig = sum(
        r.get("original_bytes", 0) for r in results if r.get("status") == "ok"
    )
    total_new = sum(r.get("new_bytes", 0) for r in results if r.get("status") == "ok")
    ok_count = sum(1 for r in results if r.get("status") == "ok")

    log.info("Done: %d/%d successful", ok_count, len(images))
    if total_orig > 0:
        log.info(
            "Total: %.1f MB -> %.1f MB (%.0f%% reduction)",
            total_orig / 1e6,
            total_new / 1e6,
            (1 - total_new / total_orig) * 100,
        )

    return results


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare images for VLM audit inspection",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Source image directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for resized images",
    )
    parser.add_argument(
        "--max-side",
        type=int,
        default=DEFAULT_MAX_SIDE,
        help=f"Max pixels on longest side (default: {DEFAULT_MAX_SIDE})",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"JPEG quality 1-100 (default: {DEFAULT_QUALITY})",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        log.error("Input directory not found: %s", args.input_dir)
        return 1

    prepare_directory(args.input_dir, args.output_dir, args.max_side, args.quality)
    return 0


if __name__ == "__main__":
    sys.exit(main())
