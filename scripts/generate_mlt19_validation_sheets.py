#!/usr/bin/env python3
"""Generate contact sheets for mlt19 language/script validation.

Creates tiled contact sheets organized by language, sampling from both
train and test splits, with image_id and assigned language overlaid.

Usage:
    PYTHONPATH=. uv run python3 scripts/generate_mlt19_validation_sheets.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
METADATA_PATH = Path("/mnt/e/image_detection/metadata_registry/json/mlt19_metadata.json")
TRAIN_IMG_DIR = Path("/mnt/e/image_detection/01_base_data/language/mlt19/TrainImages/TrainImages")
TEST_IMG_DIR = Path("/mnt/e/image_detection/01_base_data/language/mlt19/TestImages/TestImages")
OUTPUT_DIR = Path("scripts/audit/results/mlt19/validation_sheets")

# Contact sheet layout
COLS = 5
ROWS = 5
THUMB_W = 384
THUMB_H = 384
LABEL_H = 32
CELL_H = THUMB_H + LABEL_H
SHEET_W = COLS * THUMB_W
SHEET_H = ROWS * CELL_H

# Sampling strategy: how many images per language per split
SAMPLES_PER_LANG_PER_SPLIT = 25  # 1 full sheet per language per split


def load_metadata() -> list[dict]:
    """Load mlt19 metadata and extract latest enrichment data per sample."""
    with open(METADATA_PATH) as f:
        data = json.load(f)

    results = []
    for s in data["samples"]:
        latest = s["enrichments"]["versions"][-1]["data"]
        filename = s["source"]["original_filename"]
        split = s["source"]["split"]
        results.append({
            "filename": filename,
            "split": split,
            "iso639_language": latest.get("iso639_language", "und"),
            "iso15924_script": latest.get("iso15924_script", "Zyyy"),
            "script_family": latest.get("script_family", "other"),
            "language_confidence": latest.get("language_confidence", 0),
            "method": latest.get("text_scope_detection_method", "unknown"),
            "text_direction": latest.get("text_direction"),
        })
    return results


def get_image_path(filename: str, split: str) -> Path:
    """Resolve image path from filename and split."""
    if split == "train":
        return TRAIN_IMG_DIR / filename
    return TEST_IMG_DIR / filename


def create_contact_sheet(
    samples: list[dict],
    title: str,
    output_path: Path,
) -> int:
    """Create a single contact sheet from sample list.

    Returns number of images successfully placed.
    """
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    placed = 0
    for idx, sample in enumerate(samples[: COLS * ROWS]):
        row = idx // COLS
        col = idx % COLS
        x = col * THUMB_W
        y = row * CELL_H

        img_path = get_image_path(sample["filename"], sample["split"])
        if not img_path.exists():
            # Draw placeholder
            draw.rectangle([x, y, x + THUMB_W - 1, y + THUMB_H - 1], fill=(80, 0, 0))
            draw.text((x + 5, y + 5), f"MISSING: {sample['filename']}", fill="red", font=font)
        else:
            try:
                img = Image.open(img_path)
                img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
                # Center in cell
                paste_x = x + (THUMB_W - img.width) // 2
                paste_y = y + (THUMB_H - img.height) // 2
                sheet.paste(img, (paste_x, paste_y))
                placed += 1
            except Exception as e:
                draw.rectangle([x, y, x + THUMB_W - 1, y + THUMB_H - 1], fill=(80, 0, 0))
                draw.text((x + 5, y + 5), f"ERROR: {e!s:.40}", fill="red", font=font)

        # Label bar
        label_y = y + THUMB_H
        draw.rectangle([x, label_y, x + THUMB_W - 1, label_y + LABEL_H - 1], fill=(20, 20, 20))

        stem = Path(sample["filename"]).stem
        lang = sample["iso639_language"]
        script = sample["iso15924_script"]
        conf = sample["language_confidence"]
        method = sample["method"]
        # Abbreviate method for display
        method_short = method.replace("parser_gt+llm_refined", "GT+LLM").replace(
            "parser_gt_primary", "GT-pri"
        ).replace("parser_gt", "GT").replace("vlm_contact_sheet", "VLM").replace(
            "llm_vision", "LLM"
        ).replace("openlid_v2", "OL").replace("none", "-")

        label = f"{stem} | {lang}/{script} | {method_short} c={conf:.2f}"
        draw.text((x + 3, label_y + 2), label, fill="white", font=font)

    # Title bar at top (overlay)
    draw.rectangle([0, 0, SHEET_W, 24], fill=(0, 0, 80))
    draw.text((10, 3), title, fill="white", font=title_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "JPEG", quality=90)
    return placed


def main() -> None:
    """Generate validation contact sheets."""
    print("Loading metadata...")
    samples = load_metadata()
    print(f"Loaded {len(samples)} samples")

    # Group by language + split
    by_lang_split: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        key = f"{s['iso639_language']}_{s['split']}"
        by_lang_split[key].append(s)

    # Define validation categories
    # 1. Major languages (both splits where available)
    # 2. Refined Latin languages (train only, method=parser_gt+llm_refined)
    # 3. Edge cases (und, mixed methods, low confidence)
    categories: list[tuple[str, str, list[dict]]] = []

    # Major languages
    for lang in ["en", "hi", "ko", "zh", "bn", "ar", "ja"]:
        for split in ["train", "test"]:
            key = f"{lang}_{split}"
            if key in by_lang_split:
                pool = by_lang_split[key]
                sample_size = min(SAMPLES_PER_LANG_PER_SPLIT, len(pool))
                sampled = random.sample(pool, sample_size)
                categories.append((f"{lang}_{split}", f"{lang.upper()} ({split}, n={len(pool)})", sampled))

    # Refined Latin languages (KI-009 fix)
    for lang in ["fr", "de", "it"]:
        key = f"{lang}_train"
        if key in by_lang_split:
            pool = by_lang_split[key]
            sample_size = min(SAMPLES_PER_LANG_PER_SPLIT, len(pool))
            sampled = random.sample(pool, sample_size)
            categories.append((f"{lang}_train_refined", f"{lang.upper()} Refined ({len(pool)} samples)", sampled))

    # Undetermined / edge cases
    und_samples = [s for s in samples if s["iso639_language"] == "und"]
    if und_samples:
        sample_size = min(SAMPLES_PER_LANG_PER_SPLIT, len(und_samples))
        sampled = random.sample(und_samples, sample_size)
        categories.append(("und_all", f"UNDETERMINED (n={len(und_samples)})", sampled))

    # Low confidence (< 0.7)
    low_conf = [s for s in samples if s["language_confidence"] < 0.7 and s["iso639_language"] != "und"]
    if low_conf:
        sample_size = min(SAMPLES_PER_LANG_PER_SPLIT, len(low_conf))
        sampled = random.sample(low_conf, sample_size)
        categories.append(("low_conf", f"LOW CONFIDENCE (<0.7, n={len(low_conf)})", sampled))

    # Minor European languages
    minor_eu = [s for s in samples if s["iso639_language"] in {"es", "pt", "nl", "da", "sv", "ro", "hu", "pl", "cs", "fi", "tr"}]
    if minor_eu:
        sample_size = min(SAMPLES_PER_LANG_PER_SPLIT, len(minor_eu))
        sampled = random.sample(minor_eu, sample_size)
        categories.append(("minor_eu", f"MINOR EUROPEAN ({len(minor_eu)} samples)", sampled))

    print(f"\nGenerating {len(categories)} contact sheets...")
    total_placed = 0
    manifest = []

    for sheet_id, (name, title, sheet_samples) in enumerate(categories, 1):
        output_path = OUTPUT_DIR / f"sheet_{sheet_id:02d}_{name}.jpg"
        placed = create_contact_sheet(sheet_samples, f"Sheet {sheet_id}: {title}", output_path)
        total_placed += placed
        print(f"  Sheet {sheet_id:2d}: {name:30s} -> {placed}/{len(sheet_samples)} images ({output_path.name})")

        manifest.append({
            "sheet_id": sheet_id,
            "name": name,
            "title": title,
            "filename": output_path.name,
            "images_requested": len(sheet_samples),
            "images_placed": placed,
            "samples": [
                {
                    "filename": s["filename"],
                    "iso639_language": s["iso639_language"],
                    "iso15924_script": s["iso15924_script"],
                    "method": s["method"],
                    "confidence": s["language_confidence"],
                }
                for s in sheet_samples
            ],
        })

    # Write manifest
    manifest_path = OUTPUT_DIR / "validation_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "total_sheets": len(categories),
            "total_images": total_placed,
            "seed": None,
            "sheets": manifest,
        }, f, indent=2)

    print(f"\nDone: {len(categories)} sheets, {total_placed} images")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible sampling
    main()
