#!/usr/bin/env python3
"""Generate contact sheets from harvested TCC images for visual review.

Supports two grouping modes:
  --by-source    Group by source institution (met, ndl, wikimedia) [default]
  --by-label     Group by script_style from catalog for label validation

Usage:
    uv run python scripts/make_contact_sheets.py
    uv run python scripts/make_contact_sheets.py --by-label
    uv run python scripts/make_contact_sheets.py --by-label --by-source
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "thousand_character_classic_registry.jsonl"
)
_CATALOG_PATH = _PROJECT_ROOT / "config" / "thousand_character_classic_catalog.yaml"
_IMAGE_DIR = _PROJECT_ROOT / "data" / "thousand-character-classic"
_OUT_DIR = _PROJECT_ROOT / "tmp_cleanup" / "tcc_contact_sheets"


def make_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
    *,
    cols: int = 5,
    thumb_size: int = 300,
    padding: int = 10,
    label_height: int = 20,
    title: str = "",
) -> None:
    """Create a contact sheet from a list of image paths."""
    rows = math.ceil(len(image_paths) / cols)
    cell_w = thumb_size + padding
    cell_h = thumb_size + padding + label_height
    title_h = 40 if title else 0

    sheet_w = cols * cell_w + padding
    sheet_h = rows * cell_h + padding + title_h
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    if title:
        draw.text((padding, 5), title, fill="black", font=title_font)

    for idx, img_path in enumerate(image_paths):
        row = idx // cols
        col = idx % cols
        x = col * cell_w + padding
        y = row * cell_h + padding + title_h

        try:
            with Image.open(img_path) as img:
                img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                # Center the thumbnail in the cell
                offset_x = x + (thumb_size - img.width) // 2
                offset_y = y + (thumb_size - img.height) // 2
                sheet.paste(img, (offset_x, offset_y))
        except Exception as e:
            draw.rectangle([x, y, x + thumb_size, y + thumb_size], fill="gray")
            draw.text(
                (x + 5, y + thumb_size // 2), f"ERR: {e!s:.30}", fill="red", font=font
            )

        # Label with filename
        label = img_path.stem[:40]
        draw.text((x, y + thumb_size + 2), label, fill="black", font=font)

    sheet.save(output_path, quality=85)
    print(f"  Saved: {output_path} ({sheet_w}x{sheet_h}, {len(image_paths)} images)")


def _generate_by_source() -> None:
    """Generate contact sheets grouped by source institution."""
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    images_per_sheet = 25  # 5x5 grid
    sources = ["met", "ndl", "wikimedia"]

    for source in sources:
        src_dir = _IMAGE_DIR / source
        if not src_dir.exists():
            print(f"Skipping {source}: directory not found")
            continue

        imgs = sorted(src_dir.glob("*.*"))
        imgs = [
            p
            for p in imgs
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif"}
        ]

        if not imgs:
            print(f"Skipping {source}: no images")
            continue

        num_sheets = math.ceil(len(imgs) / images_per_sheet)
        print(f"\n{source}: {len(imgs)} images -> {num_sheets} contact sheet(s)")

        for sheet_idx in range(num_sheets):
            start = sheet_idx * images_per_sheet
            end = min(start + images_per_sheet, len(imgs))
            batch = imgs[start:end]

            out_path = _OUT_DIR / f"tcc_{source}_{sheet_idx + 1:02d}.jpg"
            title = (
                f"TCC {source.upper()} - Sheet {sheet_idx + 1}/{num_sheets} "
                f"({start + 1}-{end} of {len(imgs)})"
            )
            make_contact_sheet(batch, out_path, title=title)


def _generate_by_label() -> None:
    """Generate contact sheets grouped by script_style for label validation.

    Each sheet shows images that share a catalog-derived script_style, with the
    calligrapher name and catalog number in the title for cross-referencing.
    """
    out_dir = _OUT_DIR / "by_label"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load catalog (YAML is dict with int keys -> entry dicts)
    with _CATALOG_PATH.open("r") as fh:
        catalog: dict[int, dict] = yaml.safe_load(fh)

    # Load registry and group by script_style
    groups: dict[str, list[tuple[Path, str, int | None]]] = defaultdict(list)
    with _REGISTRY_PATH.open("r") as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            cat_num = entry.get("catalog_number")
            cat_entry = catalog.get(cat_num, {}) if cat_num else {}
            script_style = cat_entry.get("script_style", "unknown")
            calligrapher = cat_entry.get("calligrapher", "unknown")

            source_path = entry.get("source_path", "")
            img_path = _IMAGE_DIR / source_path
            if img_path.exists():
                groups[script_style].append((img_path, calligrapher, cat_num))

    images_per_sheet = 25

    print(f"\nGrouping {sum(len(v) for v in groups.values())} images by script_style:")
    for style in sorted(groups.keys()):
        items = groups[style]
        print(f"  {style}: {len(items)} images")

        # Sub-group by catalog_number for better organization
        by_cat: dict[int | None, list[tuple[Path, str]]] = defaultdict(list)
        for img_path, calligrapher, cat_num in items:
            by_cat[cat_num].append((img_path, calligrapher))

        # Flatten in catalog-number order, keeping images from same source together
        ordered_paths: list[Path] = []
        cat_labels: list[str] = []
        for cat_num in sorted(
            by_cat.keys(), key=lambda x: x if x is not None else 9999
        ):
            paths_for_cat = by_cat[cat_num]
            calligrapher = paths_for_cat[0][1]
            for img_path, _ in sorted(paths_for_cat, key=lambda x: x[0].name):
                ordered_paths.append(img_path)
                cat_labels.append(
                    f"#{cat_num}: {calligrapher}" if cat_num else "unmatched"
                )

        num_sheets = math.ceil(len(ordered_paths) / images_per_sheet)
        for sheet_idx in range(num_sheets):
            start = sheet_idx * images_per_sheet
            end = min(start + images_per_sheet, len(ordered_paths))
            batch = ordered_paths[start:end]

            # Collect unique calligraphers for title
            batch_cats = set(cat_labels[start:end])
            cats_str = ", ".join(sorted(batch_cats)[:3])
            if len(batch_cats) > 3:
                cats_str += f" +{len(batch_cats) - 3} more"

            safe_style = style.replace("/", "_")
            out_path = out_dir / f"tcc_label_{safe_style}_{sheet_idx + 1:02d}.jpg"
            title = (
                f"Script: {style.upper()} - Sheet {sheet_idx + 1}/{num_sheets} "
                f"({len(items)} total) | {cats_str}"
            )
            make_contact_sheet(batch, out_path, title=title)

    print(f"\nLabel contact sheets saved to: {out_dir}")


def main() -> None:
    """Generate contact sheets. Use --by-label for script_style grouping."""
    by_label = "--by-label" in sys.argv
    by_source = "--by-source" in sys.argv

    # Default to both if neither specified, or just --by-source if that's the only flag
    if not by_label and not by_source:
        by_source = True

    if by_source:
        print("=== Contact Sheets by Source ===")
        _generate_by_source()

    if by_label:
        print("\n=== Contact Sheets by Script Style (Label Validation) ===")
        _generate_by_label()

    print(f"\nAll contact sheets saved to: {_OUT_DIR}")


if __name__ == "__main__":
    main()
