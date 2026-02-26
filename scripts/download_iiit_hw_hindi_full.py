#!/usr/bin/env python3
"""Download the full IIIT-HW-Hindi dataset from HuggingFace.

Streams all 95,430 images (train/validation/test) from
``c3rl/IIIT-INDIC-HW-WORDS-Hindi`` and saves as JPEG with a ground
truth TSV.  Already-extracted images are skipped so the script is
safely re-runnable / resumable.

Usage::

    uv run python scripts/download_iiit_hw_hindi_full.py

Output::

    /mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi/
        iiit_hw_hindi_{split}_{index:05d}.jpg   (95,430 files)
        iiit_hw_hindi_groundtruth.tsv            (updated with all rows)
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

from datasets import load_dataset
from PIL import Image as PILImage

OUT_DIR    = Path("/mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi")
HF_DATASET = "c3rl/IIIT-INDIC-HW-WORDS-Hindi"
JPEG_Q     = 90

# Splits and their expected sizes
SPLITS: list[tuple[str, int]] = [
    ("test",       12_900),
    ("train",      69_900),
    ("validation", 12_700),
]


def _fname(split: str, index: int) -> str:
    return f"iiit_hw_hindi_{split}_{index:05d}.jpg"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build existing file index once (fast lookup)
    existing: set[str] = {p.name for p in OUT_DIR.glob("*.jpg")}
    print(f"Found {len(existing)} already-extracted images — will skip these.", flush=True)

    all_rows: list[tuple[str, str, str, str]] = []
    total_new   = 0
    total_skips = 0

    for split, expected in SPLITS:
        print(f"\n── {split} split  (expected {expected:,} images) ──", flush=True)
        ds = load_dataset(HF_DATASET, split=split, streaming=True)

        split_new   = 0
        split_skips = 0
        t0 = time.time()

        for idx, sample in enumerate(ds):
            fname = _fname(split, idx)
            out_path = OUT_DIR / fname
            hindi_text: str = sample["text"]

            if fname in existing:
                # Already on disk — just record in TSV
                split_skips += 1
            else:
                img: PILImage.Image = sample["image"]
                img.save(out_path, "JPEG", quality=JPEG_Q)
                existing.add(fname)
                split_new += 1

            all_rows.append((str(out_path), split, fname, hindi_text))

            if (idx + 1) % 1000 == 0:
                elapsed = time.time() - t0
                rate = (idx + 1) / elapsed
                eta_s = (expected - idx - 1) / rate
                print(
                    f"  {split}: {idx+1:,}/{expected:,}  "
                    f"new={split_new} skip={split_skips}  "
                    f"{rate:.1f} img/s  ETA {eta_s/60:.1f}m",
                    flush=True,
                )

        elapsed = time.time() - t0
        print(
            f"  {split} DONE: {split_new} new + {split_skips} skipped "
            f"in {elapsed/60:.1f}m",
            flush=True,
        )
        total_new   += split_new
        total_skips += split_skips

    # Write complete ground truth TSV (overwrites existing partial file)
    tsv_path = OUT_DIR / "iiit_hw_hindi_groundtruth.tsv"
    with open(tsv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["image_path", "split", "filename", "hindi_text"])
        w.writerows(all_rows)

    total = len(all_rows)
    print(f"\n{'='*60}", flush=True)
    print(f"Complete.  {total:,} total images  ({total_new} new, {total_skips} skipped)", flush=True)
    print(f"GT TSV written: {tsv_path}  ({tsv_path.stat().st_size // 1024} KB)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted — safe to resume by re-running.", flush=True)
        sys.exit(1)
