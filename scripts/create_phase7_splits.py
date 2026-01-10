#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Create stratified train/val/test splits for Phase 7 IQA dataset.

Stratifies by:
- Source dataset (to maintain domain distribution)
- Defect level (to maintain quality distribution)

Split ratio: 70% train, 15% val, 15% test

Usage:
    uv run python scripts/create_phase7_splits.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/01_augmented"
OUTPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/splits"

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


def main():
    """Create stratified splits."""
    print("=" * 70)
    print("PHASE 7 MVP - CREATING TRAIN/VAL/TEST SPLITS")
    print("=" * 70)

    # Load metadata
    metadata_path = INPUT_DIR / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata["samples"]
    print(f"Total samples: {len(samples):,}")

    # Stratify by source dataset and defect level
    strata = defaultdict(list)
    for sample in samples:
        key = (sample["source_dataset"], sample.get("defect_level", "unknown"))
        strata[key].append(sample)

    print(f"Number of strata: {len(strata)}")

    # Split each stratum
    train_samples = []
    val_samples = []
    test_samples = []

    random.seed(42)
    for key, group in strata.items():
        random.shuffle(group)
        n = len(group)
        n_train = int(n * TRAIN_RATIO)
        n_val = int(n * VAL_RATIO)

        train_samples.extend(group[:n_train])
        val_samples.extend(group[n_train : n_train + n_val])
        test_samples.extend(group[n_train + n_val :])

    print(
        f"Train: {len(train_samples):,} ({len(train_samples) / len(samples) * 100:.1f}%)"
    )
    print(f"Val: {len(val_samples):,} ({len(val_samples) / len(samples) * 100:.1f}%)")
    print(
        f"Test: {len(test_samples):,} ({len(test_samples) / len(samples) * 100:.1f}%)"
    )

    # Create split directories and symlinks
    for split_name, split_samples in [
        ("train", train_samples),
        ("val", val_samples),
        ("test", test_samples),
    ]:
        split_dir = OUTPUT_DIR / split_name / "images"
        split_dir.mkdir(parents=True, exist_ok=True)

        split_metadata = []
        for sample in tqdm(split_samples, desc=f"Creating {split_name}"):
            src = INPUT_DIR / "images" / sample["filename"]
            dst = split_dir / sample["filename"]

            if src.exists():
                # Remove existing symlink if any
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                dst.symlink_to(src.resolve())
                split_metadata.append(sample)

        # Save split metadata
        split_metadata_file = OUTPUT_DIR / split_name / "metadata.json"
        with open(split_metadata_file, "w") as f:
            json.dump(
                {
                    "split": split_name,
                    "count": len(split_metadata),
                    "samples": split_metadata,
                },
                f,
                indent=2,
            )

        print(f"  {split_name}: {len(split_metadata):,} samples saved")

    # Save split assignment summary
    assignment = {
        "created": metadata.get("created", "unknown"),
        "total_samples": len(samples),
        "train_count": len(train_samples),
        "val_count": len(val_samples),
        "test_count": len(test_samples),
        "split_ratios": {"train": TRAIN_RATIO, "val": VAL_RATIO, "test": TEST_RATIO},
    }

    with open(OUTPUT_DIR / "split_assignment.json", "w") as f:
        json.dump(assignment, f, indent=2)

    print(f"\nSplits created at: {OUTPUT_DIR}")
    print(f"Assignment file: {OUTPUT_DIR / 'split_assignment.json'}")


if __name__ == "__main__":
    main()
