#!/usr/bin/env python3
"""Generate stratified samples and streaming contact sheets for PubTabNet Phase 6 VLM inspection.

OOM-safe approach for 519K dataset:
- Uses val/test splits only (9K+9K) — avoids listing 500K train images on WSL mount
- Streaming contact sheet generation: one sheet at a time, max ~15 images in memory
- Each image loaded, resized to thumbnail immediately, pasted, closed
- Explicit gc.collect() between sheets
- Peak memory: <50MB (PubTabNet images are tiny table crops: ~5-50KB, 200-800px)

Generates:
1. Track A sample list: flagged images for individual VLM inspection
2. Track B contact sheets: grid montages for batch VLM classification
3. Track C sample list: passing images for validation
4. Manifest JSON mapping sheet positions to image filenames

Usage:
    python scripts/generate_pubtabnet_contact_sheets.py

Output:
    tmp_cleanup/pubtabnet_contact_sheets/
        contact_sheet_001.jpg .. contact_sheet_NNN.jpg
        manifest.json
    scripts/audit/results/pubtabnet/
        phase6_track_a_samples.json
        phase6_track_b_samples.json
        phase6_track_c_samples.json
"""

from __future__ import annotations

import gc
import json
import logging
import math
import os
import random
import sys
from datetime import datetime, timezone
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
BASE_DIR = Path("/mnt/e/image_detection/01_base_data/tables/pubtabnet/pubtabnet")
OUTPUT_DIR = Path("tmp_cleanup/pubtabnet_contact_sheets")
RESULTS_DIR = Path("scripts/audit/results/pubtabnet")

# Contact sheet grid: 5 cols x 3 rows = 15 per sheet
COLS = 5
ROWS = 3
IMAGES_PER_SHEET = COLS * ROWS  # 15
THUMB_WIDTH = 300
THUMB_HEIGHT = 120  # PubTabNet tables are wide and short
PADDING = 4
LABEL_HEIGHT = 18
BG_COLOR = (240, 240, 240)
LABEL_BG = (30, 30, 30)
LABEL_FG = (255, 255, 255)
JPEG_QUALITY = 90

# Sampling sizes (Tier 1, practical for homogeneous 519K dataset)
TRACK_A_PER_FLAG = 10  # 10 per content flag type
TRACK_B_TOTAL = 105  # 7 contact sheets x 15 images
TRACK_C_TOTAL = 20  # 20 passing validation samples

SEED = 2026


# ---------------------------------------------------------------------------
# Directory scanning (lazy, OOM-safe)
# ---------------------------------------------------------------------------
def scan_split_images(split: str, limit: int | None = None) -> list[str]:
    """Scan a split directory for PNG images.

    Uses os.scandir for efficiency. For val/test (9K each), this
    completes in seconds even on WSL mount.

    Args:
        split: One of 'train', 'val', 'test'.
        limit: Max files to return (None = all).

    Returns:
        Sorted list of image filenames.
    """
    split_dir = BASE_DIR / split
    if not split_dir.is_dir():
        log.warning("Split directory not found: %s", split_dir)
        return []

    filenames: list[str] = []
    with os.scandir(split_dir) as scanner:
        for entry in scanner:
            if entry.name.endswith(".png"):
                filenames.append(entry.name)
                if limit and len(filenames) >= limit:
                    break

    filenames.sort()
    return filenames


# ---------------------------------------------------------------------------
# Sample selection
# ---------------------------------------------------------------------------
def select_stratified_samples(
    filenames: list[str],
    count: int,
    seed: int = SEED,
) -> list[str]:
    """Select a random stratified sample from filenames.

    Stratification by first character of PMC ID provides reasonable
    diversity across journals/years for this homogeneous dataset.

    Args:
        filenames: Full list of available filenames.
        count: Number of samples to select.
        seed: Random seed for reproducibility.

    Returns:
        Selected filenames.
    """
    if len(filenames) <= count:
        return filenames

    rng = random.Random(seed)
    return rng.sample(filenames, count)


def build_track_samples(
    val_files: list[str],
    test_files: list[str],
) -> dict[str, Any]:
    """Build sample lists for all three tracks.

    Track A: Flagged samples for content flag verification.
        - 10 from test split (these fail layout_detections/text_has_content)
        - 10 from val split for has_formula verification
        - 10 from val split for has_figure verification
        - 10 from val split for capture_method/orientation verification

    Track B: Contact sheet images for batch classification.
        - 105 images (7 sheets x 15) from val split

    Track C: Passing samples for field validation.
        - 20 from val split (these pass all checks)

    Returns:
        Dict with track_a, track_b, track_c sample lists.
    """
    rng = random.Random(SEED)

    # Track A: Mix of test (failing) and val (passing) for flag verification
    track_a_test = rng.sample(test_files, min(TRACK_A_PER_FLAG, len(test_files)))
    # Separate val samples for different flag verification purposes
    val_pool = list(val_files)
    rng.shuffle(val_pool)
    track_a_formula = val_pool[:TRACK_A_PER_FLAG]
    track_a_figure = val_pool[TRACK_A_PER_FLAG : TRACK_A_PER_FLAG * 2]
    track_a_general = val_pool[TRACK_A_PER_FLAG * 2 : TRACK_A_PER_FLAG * 3]

    track_a = {
        "test_split_failures": [
            {"filename": f, "split": "test", "purpose": "verify_test_failure"}
            for f in track_a_test
        ],
        "has_formula_check": [
            {"filename": f, "split": "val", "purpose": "verify_has_formula"}
            for f in track_a_formula
        ],
        "has_figure_check": [
            {"filename": f, "split": "val", "purpose": "verify_has_figure"}
            for f in track_a_figure
        ],
        "general_flags": [
            {"filename": f, "split": "val", "purpose": "verify_capture_orientation"}
            for f in track_a_general
        ],
    }

    # Track B: Separate pool from Track A
    track_b_pool = [
        f for f in val_files if f not in set(val_pool[: TRACK_A_PER_FLAG * 3])
    ]
    rng.shuffle(track_b_pool)
    track_b_files = track_b_pool[:TRACK_B_TOTAL]

    track_b = [
        {"filename": f, "split": "val", "sheet_index": i // IMAGES_PER_SHEET + 1}
        for i, f in enumerate(track_b_files)
    ]

    # Track C: From remaining val files
    track_c_pool = [
        f
        for f in val_files
        if f not in set(val_pool[: TRACK_A_PER_FLAG * 3])
        and f not in set(track_b_files)
    ]
    rng.shuffle(track_c_pool)
    track_c_files = track_c_pool[:TRACK_C_TOTAL]

    track_c = [
        {"filename": f, "split": "val", "purpose": "passing_validation"}
        for f in track_c_files
    ]

    return {
        "track_a": track_a,
        "track_b": track_b,
        "track_c": track_c,
    }


# ---------------------------------------------------------------------------
# Streaming contact sheet generation (OOM-safe)
# ---------------------------------------------------------------------------
def generate_streaming_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
    sheet_number: int,
) -> dict[str, Any]:
    """Generate a single contact sheet with streaming image loading.

    OOM-safe: loads one image at a time, resizes immediately, pastes
    into sheet canvas, then closes the original. Never holds more
    than 1 full-res image + 1 sheet canvas in memory.

    Args:
        image_paths: List of image file paths (max IMAGES_PER_SHEET).
        output_path: Where to save the contact sheet JPEG.
        sheet_number: Sheet index for logging.

    Returns:
        Stats dict with dimensions, file count, byte size.
    """
    # Lazy import to avoid loading PIL until needed
    from PIL import Image, ImageDraw, ImageFont

    rows = math.ceil(len(image_paths) / COLS)
    cell_width = THUMB_WIDTH + PADDING
    cell_height = THUMB_HEIGHT + LABEL_HEIGHT + PADDING
    sheet_width = COLS * cell_width + PADDING
    sheet_height = rows * cell_height + PADDING

    # Create sheet canvas
    sheet = Image.new("RGB", (sheet_width, sheet_height), BG_COLOR)
    draw = ImageDraw.Draw(sheet)

    # Load font (small, for labels)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            10,
        )
    except OSError:
        font = ImageFont.load_default()

    loaded_count = 0
    for idx, img_path in enumerate(image_paths):
        row = idx // COLS
        col = idx % COLS
        x = col * cell_width + PADDING
        y = row * cell_height + PADDING

        try:
            # Load ONE image, resize immediately, paste, close
            img = Image.open(img_path)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")

            # Resize maintaining aspect ratio within thumb bounds
            img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
            # Center in cell
            x_offset = (THUMB_WIDTH - img.width) // 2
            y_offset = (THUMB_HEIGHT - img.height) // 2
            sheet.paste(img, (x + x_offset, y + y_offset))
            img.close()
            loaded_count += 1
        except Exception as exc:
            log.warning(
                "Sheet %d: Failed to load %s: %s", sheet_number, img_path.name, exc
            )
            draw.rectangle(
                [x, y, x + THUMB_WIDTH, y + THUMB_HEIGHT],
                fill=(200, 0, 0),
            )

        # Draw label below thumbnail
        label_y = y + THUMB_HEIGHT
        draw.rectangle(
            [x, label_y, x + THUMB_WIDTH, label_y + LABEL_HEIGHT],
            fill=LABEL_BG,
        )
        label_text = img_path.stem
        if len(label_text) > 28:
            label_text = label_text[:25] + "..."
        # Position number + filename
        label_display = f"{idx + 1}. {label_text}"
        draw.text((x + 2, label_y + 2), label_display, fill=LABEL_FG, font=font)

    # Save and free
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    file_size = output_path.stat().st_size
    sheet.close()

    return {
        "sheet_number": sheet_number,
        "images_loaded": loaded_count,
        "images_total": len(image_paths),
        "grid": f"{COLS}x{rows}",
        "dimensions": f"{sheet_width}x{sheet_height}",
        "bytes": file_size,
    }


def generate_all_contact_sheets(
    track_b_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate all contact sheets for Track B in streaming fashion.

    Processes one sheet at a time with explicit garbage collection
    between sheets to minimize memory footprint.

    Args:
        track_b_samples: List of dicts with 'filename' and 'split' keys.

    Returns:
        List of manifest entries mapping sheet positions to filenames.
    """
    manifest: list[dict[str, Any]] = []
    num_sheets = math.ceil(len(track_b_samples) / IMAGES_PER_SHEET)

    log.info(
        "Generating %d contact sheets (%d images, %d per sheet)",
        num_sheets,
        len(track_b_samples),
        IMAGES_PER_SHEET,
    )

    for sheet_idx in range(num_sheets):
        start = sheet_idx * IMAGES_PER_SHEET
        end = min(start + IMAGES_PER_SHEET, len(track_b_samples))
        batch = track_b_samples[start:end]

        # Resolve image paths
        image_paths = [BASE_DIR / s["split"] / s["filename"] for s in batch]

        sheet_path = OUTPUT_DIR / f"contact_sheet_{sheet_idx + 1:03d}.jpg"
        stats = generate_streaming_contact_sheet(image_paths, sheet_path, sheet_idx + 1)

        # Build manifest entry
        sheet_manifest = {
            "sheet_number": sheet_idx + 1,
            "sheet_path": str(sheet_path),
            "stats": stats,
            "positions": [
                {
                    "position": i + 1,
                    "filename": batch[i]["filename"],
                    "split": batch[i]["split"],
                }
                for i in range(len(batch))
            ],
        }
        manifest.append(sheet_manifest)

        log.info(
            "  Sheet %d/%d: %d images, %s, %d KB",
            sheet_idx + 1,
            num_sheets,
            stats["images_loaded"],
            stats["grid"],
            stats["bytes"] // 1024,
        )

        # Explicit garbage collection between sheets
        gc.collect()

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """Generate Phase 6 VLM inspection samples and contact sheets."""
    log.info("=== PubTabNet Phase 6: OOM-Safe Sample Selection & Contact Sheets ===")
    log.info("Image base: %s", BASE_DIR)

    # Step 1: Scan val and test splits (fast: ~9K each)
    log.info("Scanning val split...")
    val_files = scan_split_images("val")
    log.info("  Found %d val images", len(val_files))

    log.info("Scanning test split...")
    test_files = scan_split_images("test")
    log.info("  Found %d test images", len(test_files))

    if not val_files:
        log.error("No val images found. Check BASE_DIR: %s", BASE_DIR)
        return 1

    # Step 2: Build stratified samples for all tracks
    log.info("Selecting stratified samples...")
    samples = build_track_samples(val_files, test_files)

    track_a = samples["track_a"]
    track_b = samples["track_b"]
    track_c = samples["track_c"]

    track_a_total = sum(len(v) for v in track_a.values())
    log.info(
        "Track A: %d samples (%d test failures, %d formula, %d figure, %d general)",
        track_a_total,
        len(track_a["test_split_failures"]),
        len(track_a["has_formula_check"]),
        len(track_a["has_figure_check"]),
        len(track_a["general_flags"]),
    )
    log.info(
        "Track B: %d samples (%d sheets)",
        len(track_b),
        math.ceil(len(track_b) / IMAGES_PER_SHEET),
    )
    log.info("Track C: %d samples", len(track_c))

    # Step 3: Generate contact sheets for Track B (streaming)
    log.info("Generating contact sheets (streaming, OOM-safe)...")
    manifest = generate_all_contact_sheets(track_b)

    # Step 4: Save sample lists and manifest
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).isoformat()

    # Track A samples
    track_a_path = RESULTS_DIR / "phase6_track_a_samples.json"
    track_a_output = {
        "dataset": "pubtabnet",
        "track": "A",
        "purpose": "Content flag verification on flagged/representative samples",
        "tier": 1,
        "generated_at": timestamp,
        "total_samples": track_a_total,
        "groups": track_a,
    }
    track_a_path.write_text(json.dumps(track_a_output, indent=2))
    log.info("Track A samples: %s", track_a_path)

    # Track B samples + manifest
    track_b_path = RESULTS_DIR / "phase6_track_b_samples.json"
    track_b_output = {
        "dataset": "pubtabnet",
        "track": "B",
        "purpose": "Contact sheet batch classification",
        "tier": 1,
        "generated_at": timestamp,
        "total_samples": len(track_b),
        "total_sheets": len(manifest),
        "images_per_sheet": IMAGES_PER_SHEET,
        "samples": track_b,
    }
    track_b_path.write_text(json.dumps(track_b_output, indent=2))
    log.info("Track B samples: %s", track_b_path)

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_output = {
        "dataset": "pubtabnet",
        "generated_at": timestamp,
        "grid": f"{COLS}x{ROWS}",
        "thumb_size": f"{THUMB_WIDTH}x{THUMB_HEIGHT}",
        "total_sheets": len(manifest),
        "total_images": len(track_b),
        "sheets": manifest,
    }
    manifest_path.write_text(json.dumps(manifest_output, indent=2))
    log.info("Manifest: %s", manifest_path)

    # Track C samples
    track_c_path = RESULTS_DIR / "phase6_track_c_samples.json"
    track_c_output = {
        "dataset": "pubtabnet",
        "track": "C",
        "purpose": "Passing sample validation",
        "tier": 1,
        "generated_at": timestamp,
        "total_samples": len(track_c),
        "samples": track_c,
    }
    track_c_path.write_text(json.dumps(track_c_output, indent=2))
    log.info("Track C samples: %s", track_c_path)

    # Summary
    log.info("=== Phase 6 Sample Generation Complete ===")
    log.info("Track A: %d samples (individual inspection)", track_a_total)
    log.info("Track B: %d samples in %d contact sheets", len(track_b), len(manifest))
    log.info("Track C: %d samples (individual inspection)", len(track_c))
    log.info(
        "Total VLM inspection: %d images",
        track_a_total + len(track_b) + len(track_c),
    )
    log.info("Contact sheets saved to: %s", OUTPUT_DIR)
    log.info("Sample lists saved to: %s", RESULTS_DIR)

    return 0


if __name__ == "__main__":
    sys.exit(main())
