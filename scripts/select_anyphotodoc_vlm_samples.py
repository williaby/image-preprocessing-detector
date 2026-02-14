#!/usr/bin/env python3
"""Select stratified VLM samples from AnyPhotoDoc6300 for language + content flag labeling.

Selects representative images per layout category, varying warping pattern,
lighting condition, and document instance for maximum diversity.

Usage:
    PYTHONPATH=. uv run python3 scripts/select_anyphotodoc_vlm_samples.py \
        --per-category 6 --output results/anyphotodoc6300_vlm_samples.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

BASE_DIR = Path("/mnt/e/image_detection/01_base_data/correction/anyphotodoc6300")

LAYOUT_CATEGORIES = {
    1: "single_column",
    2: "complex_layout",
    3: "invoice",
    4: "education",
    5: "book",
    6: "two_column",
    7: "magazine",
    8: "bill",
}


def parse_filename(filename: str) -> dict | None:
    """Parse AnyPhotoDoc6300 5-position filename convention."""
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) != 5:
        return None
    try:
        return {
            "layout_cat": int(parts[0]),
            "warp": int(parts[1]),
            "light": int(parts[2]),
            "doc_id": int(parts[3]),
            "angle": int(parts[4]),
        }
    except ValueError:
        return None


def select_samples(per_category: int, seed: int = 42) -> list[dict]:
    """Select stratified samples maximizing diversity within each category."""
    rng = random.Random(seed)
    samples = []

    for cat_id, cat_name in LAYOUT_CATEGORIES.items():
        init_dir = BASE_DIR / f"init_{cat_id}"
        if not init_dir.exists():
            continue

        files = sorted(init_dir.iterdir())
        parsed = []
        for f in files:
            meta = parse_filename(f.name)
            if meta:
                meta["path"] = str(f)
                meta["filename"] = f.name
                parsed.append(meta)

        # Group by (warp, light) to maximize diversity
        groups: dict[tuple[int, int], list[dict]] = {}
        for p in parsed:
            key = (p["warp"], p["light"])
            groups.setdefault(key, []).append(p)

        # Round-robin across groups to pick per_category samples
        selected = []
        group_keys = sorted(groups.keys())
        rng.shuffle(group_keys)
        idx = 0
        while len(selected) < per_category and idx < len(parsed):
            for key in group_keys:
                if len(selected) >= per_category:
                    break
                group = groups[key]
                # Pick from different doc_ids
                remaining = [g for g in group if g not in selected]
                if remaining:
                    pick = rng.choice(remaining)
                    selected.append(pick)
            idx += 1
            # Safety: don't infinite loop
            if idx > per_category * 10:
                break

        for s in selected:
            samples.append(
                {
                    "filename": s["filename"],
                    "path": s["path"],
                    "layout_category": cat_name,
                    "layout_cat_id": cat_id,
                    "warping_pattern": s["warp"],
                    "lighting_condition": s["light"],
                    "doc_id": s["doc_id"],
                    "angle": s["angle"],
                }
            )

    return samples


def main() -> None:
    """Run sample selection."""
    parser = argparse.ArgumentParser(description="Select VLM samples from AnyPhotoDoc6300")
    parser.add_argument("--per-category", type=int, default=6, help="Samples per category")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output",
        type=str,
        default="results/anyphotodoc6300_vlm_samples.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    samples = select_samples(args.per_category, args.seed)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(
            {
                "dataset": "anyphotodoc6300",
                "per_category": args.per_category,
                "total_samples": len(samples),
                "seed": args.seed,
                "samples": samples,
            },
            f,
            indent=2,
        )

    print(f"Selected {len(samples)} samples across {len(LAYOUT_CATEGORIES)} categories")
    for cat_id, cat_name in LAYOUT_CATEGORIES.items():
        cat_samples = [s for s in samples if s["layout_cat_id"] == cat_id]
        print(f"  init_{cat_id} ({cat_name}): {len(cat_samples)} samples")

    print(f"\nOutput: {output_path}")


if __name__ == "__main__":
    main()
