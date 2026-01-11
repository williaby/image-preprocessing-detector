#!/usr/bin/env python3
"""
Assemble Stage 2 DIQA Ensemble Training Dataset.

This script:
1. Copies images from source locations to the training dataset directory
2. Merges Stage 1 DeQA labels with DIQA-5000 human MOS scores
3. Generates train/val/test split JSONL files
4. Computes SHA256 checksums for all images
5. Creates tarballs for upload

Usage:
    python scripts/assemble_stage2_dataset.py \\
        --output E:/image_detection/03_training_datasets/stage2_diqa_ensemble \\
        --stage1-labels E:/image_detection/06_staging/stage1_deqa_results/stage1_deqa_all_labels.jsonl
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import shutil
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Fixed random seed for reproducibility
RANDOM_SEED = 42

# Split ratios for non-DIQA datasets
TRAIN_RATIO = 0.70
VAL_RATIO = 0.10
TEST_RATIO = 0.20


@dataclass
class DatasetConfig:
    """Configuration for a source dataset."""

    name: str
    source_base: Path
    path_prefix: str  # Prefix in Stage 1 labels
    has_human_mos: bool = False
    use_official_splits: bool = False


@dataclass
class ImageRecord:
    """A single image record with all labels."""

    image_id: str
    source_dataset: str
    split: str
    source_path: str
    local_path: str
    deqa_logits: dict[str, float]
    deqa_probs: dict[str, float]
    deqa_predicted_score: float
    soft_label_10bin: list[float]
    human_mos: dict[str, float] | None = None
    has_human_mos: bool = False
    sha256: str = ""


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def deqa_probs_to_10bin(probs: dict[str, float]) -> list[float]:
    """
    Convert DeQA 5-level probabilities to 10-bin soft label.

    DeQA levels map to score ranges:
    - excellent (5): bins 8-9 (0.8-1.0)
    - good (4): bins 6-7 (0.6-0.8)
    - fair (3): bins 4-5 (0.4-0.6)
    - poor (2): bins 2-3 (0.2-0.4)
    - bad (1): bins 0-1 (0.0-0.2)

    We spread each level's probability across its 2 bins.
    """
    # Map DeQA levels to bin pairs (normalized 0-1 scale, 0=worst, 1=best)
    level_to_bins = {
        "bad": [0, 1],
        "poor": [2, 3],
        "fair": [4, 5],
        "good": [6, 7],
        "excellent": [8, 9],
    }

    soft_label = [0.0] * 10
    for level, prob in probs.items():
        bins = level_to_bins[level]
        for b in bins:
            soft_label[b] += prob / 2  # Split probability across 2 bins

    # Normalize to sum to 1
    total = sum(soft_label)
    if total > 0:
        soft_label = [p / total for p in soft_label]

    return soft_label


def load_stage1_labels(labels_path: Path) -> dict[str, dict[str, Any]]:
    """Load Stage 1 DeQA labels into a lookup dictionary."""
    logger.info(f"Loading Stage 1 labels from {labels_path}")
    labels = {}

    with open(labels_path) as f:
        for line in f:
            record = json.loads(line)
            # Key: dataset + image path
            key = f"{record['dataset']}:{record['image']}"
            labels[key] = record

    logger.info(f"Loaded {len(labels)} Stage 1 labels")
    return labels


def load_diqa_human_mos(diqa_base: Path) -> dict[str, dict[str, float]]:
    """Load DIQA-5000 human MOS scores from CSV files."""
    logger.info(f"Loading DIQA-5000 human MOS from {diqa_base}")
    mos_scores = {}

    for split in ["train", "val", "test"]:
        csv_path = diqa_base / split / f"{split}.csv"
        if not csv_path.exists():
            logger.warning(f"Missing CSV: {csv_path}")
            continue

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Key matches the image filename
                res_file = row["res"]
                key = f"{split}/res/{res_file}"
                mos_scores[key] = {
                    "overall": float(row["overall"]),
                    "sharpness": float(row["sharpness"]),
                    "color": float(row["color_fidelity"]),
                }

    logger.info(f"Loaded {len(mos_scores)} DIQA-5000 human MOS scores")
    return mos_scores


def get_diqa_split(image_path: str) -> str:
    """Extract split from DIQA-5000 image path."""
    # Path format: train/res/train_res_00001.jpg or test/res/test_res_00001.jpg
    parts = image_path.split("/")
    if len(parts) >= 1:
        return parts[0]  # train, val, or test
    return "train"


def random_split_dataset(
    images: list[str],
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
    seed: int = RANDOM_SEED,
) -> dict[str, list[str]]:
    """Randomly split images into train/val/test."""
    rng = np.random.default_rng(seed)
    shuffled = images.copy()
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
    }


def resolve_source_path(
    dataset_name: str,
    image_path: str,
    base_data: Path,
    benchmark_data: Path,
) -> Path | None:
    """Resolve the full source path for an image."""
    if dataset_name == "diqa-5000":
        return benchmark_data / "diqa-5000" / image_path
    elif dataset_name == "smartdoc-qa":
        return (
            benchmark_data
            / "smartdoc-qa"
            / "Dataset SmartDoc-QA"
            / "Captured_Images"
            / image_path
        )
    elif dataset_name == "funsd":
        # image_path: images/funsd_000074.jpg -> just the filename part
        filename = Path(image_path).name
        return base_data / "forms" / "funsd" / "images" / filename
    elif dataset_name == "sroie":
        filename = Path(image_path).name
        return base_data / "forms" / "sroie" / "images" / filename
    elif dataset_name == "tobacco-800":
        filename = Path(image_path).name
        return base_data / "degraded" / "tobacco800" / "images" / filename
    else:
        logger.warning(f"Unknown dataset: {dataset_name}")
        return None


def assemble_dataset(
    output_dir: Path,
    stage1_labels_path: Path,
    base_data: Path,
    benchmark_data: Path,
    dry_run: bool = False,
) -> dict[str, list[ImageRecord]]:
    """Assemble the complete Stage 2 training dataset."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load labels
    stage1_labels = load_stage1_labels(stage1_labels_path)
    diqa_human_mos = load_diqa_human_mos(benchmark_data / "diqa-5000")

    # Group Stage 1 labels by dataset
    by_dataset: dict[str, list[tuple[str, dict]]] = {}
    for key, record in stage1_labels.items():
        dataset = record["dataset"]
        if dataset not in by_dataset:
            by_dataset[dataset] = []
        by_dataset[dataset].append((record["image"], record))

    # Process each dataset
    all_records: dict[str, list[ImageRecord]] = {"train": [], "val": [], "test": []}

    for dataset_name, items in by_dataset.items():
        logger.info(f"Processing {dataset_name}: {len(items)} images")

        if dataset_name == "diqa-5000":
            # Use official splits
            for image_path, deqa_record in items:
                split = get_diqa_split(image_path)

                # Get human MOS if available
                human_mos = diqa_human_mos.get(image_path)

                # Create record
                record = ImageRecord(
                    image_id=f"{dataset_name}/{image_path}",
                    source_dataset=dataset_name,
                    split=split,
                    source_path=str(
                        resolve_source_path(
                            dataset_name, image_path, base_data, benchmark_data
                        )
                    ),
                    local_path=f"images/{dataset_name}/{split}/{Path(image_path).name}",
                    deqa_logits=deqa_record["logits"],
                    deqa_probs=deqa_record["probs"],
                    deqa_predicted_score=deqa_record["predicted_score"],
                    soft_label_10bin=deqa_probs_to_10bin(deqa_record["probs"]),
                    human_mos=human_mos,
                    has_human_mos=human_mos is not None,
                )
                all_records[split].append(record)
        else:
            # Random split for other datasets
            image_paths = [img for img, _ in items]
            splits = random_split_dataset(image_paths)

            path_to_record = {img: rec for img, rec in items}

            for split, paths in splits.items():
                for image_path in paths:
                    deqa_record = path_to_record[image_path]

                    record = ImageRecord(
                        image_id=f"{dataset_name}/{split}/{Path(image_path).name}",
                        source_dataset=dataset_name,
                        split=split,
                        source_path=str(
                            resolve_source_path(
                                dataset_name, image_path, base_data, benchmark_data
                            )
                        ),
                        local_path=f"images/{dataset_name}/{split}/{Path(image_path).name}",
                        deqa_logits=deqa_record["logits"],
                        deqa_probs=deqa_record["probs"],
                        deqa_predicted_score=deqa_record["predicted_score"],
                        soft_label_10bin=deqa_probs_to_10bin(deqa_record["probs"]),
                        human_mos=None,
                        has_human_mos=False,
                    )
                    all_records[split].append(record)

    # Log split statistics
    for split, records in all_records.items():
        by_ds = {}
        for r in records:
            by_ds[r.source_dataset] = by_ds.get(r.source_dataset, 0) + 1
        logger.info(f"{split}: {len(records)} total - {by_ds}")

    if dry_run:
        logger.info("Dry run - skipping file operations")
        return all_records

    # Copy images and compute checksums
    logger.info("Copying images and computing checksums...")
    for split, records in all_records.items():
        for record in records:
            src_path = Path(record.source_path)
            dst_path = output_dir / record.local_path

            if not src_path.exists():
                logger.warning(f"Source not found: {src_path}")
                continue

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if not dst_path.exists():
                shutil.copy2(src_path, dst_path)

            record.sha256 = compute_sha256(dst_path)

    # Write split JSONL files
    splits_dir = output_dir / "splits"
    splits_dir.mkdir(exist_ok=True)

    for split, records in all_records.items():
        jsonl_path = splits_dir / f"{split}.jsonl"
        with open(jsonl_path, "w") as f:
            for record in records:
                f.write(
                    json.dumps(
                        {
                            "image_id": record.image_id,
                            "source_dataset": record.source_dataset,
                            "split": record.split,
                            "source_path": record.source_path,
                            "local_path": record.local_path,
                            "deqa_logits": record.deqa_logits,
                            "deqa_probs": record.deqa_probs,
                            "deqa_predicted_score": record.deqa_predicted_score,
                            "soft_label_10bin": record.soft_label_10bin,
                            "human_mos": record.human_mos,
                            "has_human_mos": record.has_human_mos,
                            "sha256": record.sha256,
                        }
                    )
                    + "\n"
                )
        logger.info(f"Wrote {len(records)} records to {jsonl_path}")

    # Write checksums
    checksums_dir = output_dir / "checksums"
    checksums_dir.mkdir(exist_ok=True)

    for split, records in all_records.items():
        checksum_path = checksums_dir / f"{split}_checksums.sha256"
        with open(checksum_path, "w") as f:
            for record in records:
                if record.sha256:
                    f.write(f"{record.sha256}  {record.local_path}\n")
        logger.info(f"Wrote checksums to {checksum_path}")

    return all_records


def create_tarballs(output_dir: Path, splits: list[str] | None = None):
    """Create tarballs for each split."""
    if splits is None:
        splits = ["train", "val", "test"]

    tarballs_dir = output_dir / "tarballs"
    tarballs_dir.mkdir(exist_ok=True)

    for split in splits:
        tarball_path = tarballs_dir / f"stage2_{split}.tar.gz"
        logger.info(f"Creating {tarball_path}...")

        with tarfile.open(tarball_path, "w:gz") as tar:
            # Add split JSONL
            jsonl_path = output_dir / "splits" / f"{split}.jsonl"
            if jsonl_path.exists():
                tar.add(jsonl_path, arcname=f"splits/{split}.jsonl")

            # Add images for this split
            images_dir = output_dir / "images"
            for dataset_dir in images_dir.iterdir():
                split_dir = dataset_dir / split
                if split_dir.exists():
                    for img_file in split_dir.iterdir():
                        tar.add(
                            img_file,
                            arcname=f"images/{dataset_dir.name}/{split}/{img_file.name}",
                        )

        logger.info(f"Created {tarball_path}")


def create_manifest(output_dir: Path, all_records: dict[str, list[ImageRecord]]):
    """Create machine-readable MANIFEST.json."""
    manifest = {
        "version": "1.0.0",
        "created": "2025-12-19",
        "description": "Stage 2 DIQA Ensemble Training Dataset",
        "splits": {},
        "datasets": {},
        "totals": {"train": 0, "val": 0, "test": 0},
    }

    # Count by split and dataset
    for split, records in all_records.items():
        manifest["totals"][split] = len(records)

        by_dataset = {}
        for r in records:
            ds = r.source_dataset
            if ds not in by_dataset:
                by_dataset[ds] = {"count": 0, "has_human_mos": r.has_human_mos}
            by_dataset[ds]["count"] += 1

        manifest["splits"][split] = by_dataset

    # Overall dataset stats
    all_datasets = set()
    for records in all_records.values():
        for r in records:
            all_datasets.add(r.source_dataset)

    for ds in sorted(all_datasets):
        total = sum(
            1
            for records in all_records.values()
            for r in records
            if r.source_dataset == ds
        )
        has_mos = any(
            r.has_human_mos
            for records in all_records.values()
            for r in records
            if r.source_dataset == ds
        )
        manifest["datasets"][ds] = {
            "total_images": total,
            "has_human_mos": has_mos,
        }

    manifest_path = output_dir / "MANIFEST.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Wrote {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Assemble Stage 2 DIQA Ensemble Training Dataset"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for assembled dataset",
    )
    parser.add_argument(
        "--stage1-labels",
        type=Path,
        default=Path(
            "E:/image_detection/06_staging/stage1_deqa_results/stage1_deqa_all_labels.jsonl"
        ),
        help="Path to Stage 1 DeQA labels JSONL",
    )
    parser.add_argument(
        "--base-data",
        type=Path,
        default=Path("E:/image_detection/01_base_data"),
        help="Path to 01_base_data directory",
    )
    parser.add_argument(
        "--benchmark-data",
        type=Path,
        default=Path("E:/image_detection/02_benchmark_only"),
        help="Path to 02_benchmark_only directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't copy files, just show what would be done",
    )
    parser.add_argument(
        "--create-tarballs",
        action="store_true",
        help="Create tarballs after assembly",
    )

    args = parser.parse_args()

    logger.info("Starting Stage 2 dataset assembly")
    logger.info(f"Output: {args.output}")
    logger.info(f"Stage 1 labels: {args.stage1_labels}")

    all_records = assemble_dataset(
        output_dir=args.output,
        stage1_labels_path=args.stage1_labels,
        base_data=args.base_data,
        benchmark_data=args.benchmark_data,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        create_manifest(args.output, all_records)

        if args.create_tarballs:
            create_tarballs(args.output)

    logger.info("Done!")


if __name__ == "__main__":
    main()
