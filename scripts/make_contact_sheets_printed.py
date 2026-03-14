#!/usr/bin/env python3
"""Generate contact sheets from harvested john11-printed-editions images for visual review.

Supports four grouping modes:
  --by-source       Group by source institution (internet_archive, wikimedia, gallica)
  --by-script       Group by script_iso15924 for script label validation
  --by-technology   Group by print_technology
  --by-period       Group by time period bins derived from date_range

Usage:
    uv run python scripts/make_contact_sheets_printed.py
    uv run python scripts/make_contact_sheets_printed.py --by-script
    uv run python scripts/make_contact_sheets_printed.py --by-script --by-technology
    uv run python scripts/make_contact_sheets_printed.py --by-source --by-script --by-technology --by-period
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
    _PROJECT_ROOT / "metadata_registry" / "john11_printed_editions_registry.jsonl"
)
_CATALOG_PATH = _PROJECT_ROOT / "config" / "john11_printed_editions_catalog.yaml"
_IMAGE_DIR = Path("/mnt/e/image_detection/01_base_data/printed_editions/john11")
_OUT_DIR = _PROJECT_ROOT / "tmp_cleanup" / "printed_editions_contact_sheets"

# Fallback if E: drive not mounted
_IMAGE_DIR_LOCAL = _PROJECT_ROOT / "data" / "john11-printed-editions"

# Time period bins from sample profile
_PERIOD_BINS = [
    ("incunabula", 1450, 1500),
    ("early_modern", 1501, 1700),
    ("enlightenment", 1701, 1850),
    ("industrial", 1851, 1950),
    ("modern", 1951, 2100),
]


def _resolve_image_dir() -> Path:
    """Return the image directory, preferring E: drive."""
    if _IMAGE_DIR.exists():
        return _IMAGE_DIR
    if _IMAGE_DIR_LOCAL.exists():
        return _IMAGE_DIR_LOCAL
    return _IMAGE_DIR


def _date_to_period(date_range: str) -> str:
    """Convert a date_range string to a time period bin."""
    try:
        year = int(date_range[:4])
    except (ValueError, IndexError):
        return "unknown"
    for name, start, end in _PERIOD_BINS:
        if start <= year <= end:
            return name
    return "unknown"


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
                offset_x = x + (thumb_size - img.width) // 2
                offset_y = y + (thumb_size - img.height) // 2
                sheet.paste(img, (offset_x, offset_y))
        except Exception as e:
            draw.rectangle([x, y, x + thumb_size, y + thumb_size], fill="gray")
            draw.text(
                (x + 5, y + thumb_size // 2),
                f"ERR: {e!s:.30}",
                fill="red",
                font=font,
            )

        label = img_path.stem[:40]
        draw.text((x, y + thumb_size + 2), label, fill="black", font=font)

    sheet.save(output_path, quality=85)
    print(f"  Saved: {output_path} ({sheet_w}x{sheet_h}, {len(image_paths)} images)")


def _load_registry() -> list[dict]:
    """Load registry JSONL."""
    entries = []
    if _REGISTRY_PATH.exists():
        with _REGISTRY_PATH.open("r") as fh:
            for line in fh:
                if line.strip():
                    entries.append(json.loads(line))
    return entries


def _load_catalog() -> dict[int, dict]:
    """Load catalog YAML."""
    with _CATALOG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _resolve_image_path(entry: dict, image_dir: Path) -> Path | None:
    """Resolve image path from registry entry."""
    source_path = entry.get("source_path", "")
    if source_path:
        full_path = image_dir / source_path
        if full_path.exists():
            return full_path
    return None


def _generate_sheets(
    groups: dict[str, list[Path]],
    out_dir: Path,
    prefix: str,
    group_label: str,
    images_per_sheet: int = 25,
) -> None:
    """Generate contact sheets for grouped images."""
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGrouping {sum(len(v) for v in groups.values())} images by {group_label}:")
    for key in sorted(groups.keys()):
        paths = groups[key]
        print(f"  {key}: {len(paths)} images")

        num_sheets = math.ceil(len(paths) / images_per_sheet)
        for sheet_idx in range(num_sheets):
            start = sheet_idx * images_per_sheet
            end = min(start + images_per_sheet, len(paths))
            batch = paths[start:end]

            safe_key = key.replace("/", "_").replace(" ", "_")
            out_path = out_dir / f"{prefix}_{safe_key}_{sheet_idx + 1:02d}.jpg"
            title = (
                f"{group_label}: {key.upper()} - Sheet {sheet_idx + 1}/{num_sheets} "
                f"({start + 1}-{end} of {len(paths)})"
            )
            make_contact_sheet(batch, out_path, title=title)


def _generate_by_source(entries: list[dict], catalog: dict, image_dir: Path) -> None:
    """Generate contact sheets grouped by source institution."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for entry in entries:
        img = _resolve_image_path(entry, image_dir)
        if img:
            inst = entry.get("source_institution", "unknown")
            groups[inst].append(img)

    _generate_sheets(groups, _OUT_DIR / "by_source", "printed_src", "Source")


def _generate_by_script(entries: list[dict], catalog: dict, image_dir: Path) -> None:
    """Generate contact sheets grouped by script_iso15924."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for entry in entries:
        img = _resolve_image_path(entry, image_dir)
        if img:
            script = entry.get("script_iso15924", "unknown")
            groups[script].append(img)

    _generate_sheets(groups, _OUT_DIR / "by_script", "printed_script", "Script")


def _generate_by_technology(
    entries: list[dict], catalog: dict, image_dir: Path
) -> None:
    """Generate contact sheets grouped by print_technology."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for entry in entries:
        img = _resolve_image_path(entry, image_dir)
        if img:
            cat_num = entry.get("catalog_number")
            cat = catalog.get(cat_num, {}) if cat_num else {}
            tech = cat.get("print_technology", "unknown")
            groups[tech].append(img)

    _generate_sheets(
        groups, _OUT_DIR / "by_technology", "printed_tech", "Print Technology"
    )


def _generate_by_period(entries: list[dict], catalog: dict, image_dir: Path) -> None:
    """Generate contact sheets grouped by time period bins."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for entry in entries:
        img = _resolve_image_path(entry, image_dir)
        if img:
            cat_num = entry.get("catalog_number")
            cat = catalog.get(cat_num, {}) if cat_num else {}
            date_range = cat.get("date_range", "")
            period = _date_to_period(date_range)
            groups[period].append(img)

    _generate_sheets(groups, _OUT_DIR / "by_period", "printed_period", "Time Period")


def main() -> None:
    """Generate contact sheets. Use flags to select grouping modes."""
    by_source = "--by-source" in sys.argv
    by_script = "--by-script" in sys.argv
    by_technology = "--by-technology" in sys.argv
    by_period = "--by-period" in sys.argv

    # Default to by-source if no flags
    if not any([by_source, by_script, by_technology, by_period]):
        by_source = True

    image_dir = _resolve_image_dir()
    entries = _load_registry()
    catalog = _load_catalog()

    if not entries:
        print("Registry is empty. Run harvest commands first.")
        return

    print(f"Loaded {len(entries)} registry entries")
    print(f"Image directory: {image_dir}")

    if by_source:
        print("\n=== Contact Sheets by Source ===")
        _generate_by_source(entries, catalog, image_dir)

    if by_script:
        print("\n=== Contact Sheets by Script ===")
        _generate_by_script(entries, catalog, image_dir)

    if by_technology:
        print("\n=== Contact Sheets by Print Technology ===")
        _generate_by_technology(entries, catalog, image_dir)

    if by_period:
        print("\n=== Contact Sheets by Time Period ===")
        _generate_by_period(entries, catalog, image_dir)

    print(f"\nAll contact sheets saved to: {_OUT_DIR}")


if __name__ == "__main__":
    main()
