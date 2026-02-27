#!/usr/bin/env python3
"""
Prepare Kaggle invoice dataset for training.

Flattens nested batch structure, combines CSV annotations,
and splits into train/val sets.

Usage:
    poetry run python scripts/prepare_invoice_dataset.py \
        --input=data/downloads/kaggle_invoices \
        --output=data/training/invoices_kaggle \
        --split=0.7,0.3
"""

import argparse
import csv
import json
import random
import shutil
from pathlib import Path


def _find_image_in_subdirs(subdirs: list[Path], filename: str) -> Path | None:
    """Search subdirectories for a file by name, returning the first match.

    Args:
        subdirs: Subdirectories to search.
        filename: Image filename to locate.

    Returns:
        The first matching file path if found, otherwise None.
    """
    for subdir in subdirs:
        image_path = subdir / filename
        if image_path.is_file():
            return image_path
    return None


def find_all_images(input_dir: Path) -> list[tuple[Path, Path, dict[str, str]]]:
    """Find all images and their corresponding CSV rows.

    Args:
        input_dir: Root directory containing CSV batches.

    Returns:
        List of (image_path, csv_path, row_dict) tuples.
    """
    image_csv_pairs = []

    csv_files = list(input_dir.rglob("*.csv"))

    for csv_file in csv_files:
        image_dir = csv_file.parent
        batch_subdirs = sorted(
            [d for d in image_dir.iterdir() if d.is_dir()], key=lambda d: d.name
        )

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get("File Name", "")
                if not filename:
                    continue
                image_path = _find_image_in_subdirs(batch_subdirs, filename)
                if image_path is not None:
                    image_csv_pairs.append((image_path, csv_file, row))

    return image_csv_pairs


def combine_annotations(
    image_csv_pairs: list[tuple[Path, Path, dict]],
) -> dict[str, dict]:
    """
    Combine all CSV annotations into single dict.

    Returns:
        Dict mapping image filename -> annotation data
    """
    annotations = {}

    for image_path, csv_path, row in image_csv_pairs:
        filename = image_path.name
        annotations[filename] = {
            "filename": filename,
            "original_path": str(image_path),
            "csv_source": str(csv_path),
            "json_data": row.get("Json Data", ""),
            "ocred_text": row.get("OCRed Text", ""),
        }

    return annotations


def split_dataset(
    image_csv_pairs: list[tuple[Path, Path, dict]],
    split_ratios: tuple[float, float],
    seed: int = 42,
) -> tuple[list, list]:
    """
    Split dataset into train and validation sets.

    Args:
        image_csv_pairs: List of (image_path, csv_path, row) tuples
        split_ratios: (train_ratio, val_ratio) e.g., (0.7, 0.3)
        seed: Random seed for reproducibility

    Returns:
        (train_pairs, val_pairs)
    """
    random.seed(seed)
    pairs_shuffled = image_csv_pairs.copy()
    random.shuffle(pairs_shuffled)

    train_ratio, val_ratio = split_ratios
    if abs(train_ratio + val_ratio - 1.0) >= 0.001:
        raise ValueError("Split ratios must sum to 1.0")

    train_size = int(len(pairs_shuffled) * train_ratio)

    train_pairs = pairs_shuffled[:train_size]
    val_pairs = pairs_shuffled[train_size:]

    return train_pairs, val_pairs


def copy_images_and_create_manifest(
    pairs: list[tuple[Path, Path, dict]], output_dir: Path, split_name: str
) -> None:
    """
    Copy images to output directory and create annotation manifest.

    Args:
        pairs: List of (image_path, csv_path, row) tuples
        output_dir: Output directory
        split_name: 'train' or 'val'
    """
    images_dir = output_dir / split_name / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    for idx, (image_path, csv_path, row) in enumerate(pairs):
        # Copy image with sequential naming
        ext = image_path.suffix
        new_filename = f"{split_name}_{idx:05d}{ext}"
        dest_path = images_dir / new_filename

        shutil.copy2(image_path, dest_path)

        # Add to manifest
        manifest.append(
            {
                "filename": new_filename,
                "original_filename": image_path.name,
                "original_path": str(image_path),
                "csv_source": str(csv_path),
                "json_data": row.get("Json Data", ""),
                "ocred_text": row.get("OCRed Text", ""),
            }
        )

    # Write manifest
    manifest_path = output_dir / split_name / "annotations.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"  {split_name}: {len(pairs)} images -> {images_dir}")
    print(f"  {split_name}: annotations -> {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare Kaggle invoice dataset")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input directory (e.g., data/downloads/kaggle_invoices)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory (e.g., data/training/invoices_kaggle)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="0.7,0.3",
        help="Train,val split ratios (default: 0.7,0.3)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    # Parse split ratios
    split_values = [float(x) for x in args.split.split(",")]
    if len(split_values) != 2:
        raise ValueError("Split must have exactly 2 values (train,val)")
    train_ratio, val_ratio = split_values

    print("Preparing Kaggle invoice dataset...")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Split: train={train_ratio:.1%}, val={val_ratio:.1%}")
    print()

    # Find all images and CSV annotations
    print("Finding images and annotations...")
    image_csv_pairs = find_all_images(input_dir)
    print(f"  Found {len(image_csv_pairs)} images with annotations")
    print()

    # Split dataset
    print("Splitting dataset...")
    train_pairs, val_pairs = split_dataset(
        image_csv_pairs, (train_ratio, val_ratio), seed=args.seed
    )
    print(
        f"  Train: {len(train_pairs)} images ({len(train_pairs) / len(image_csv_pairs):.1%})"
    )
    print(
        f"  Val: {len(val_pairs)} images ({len(val_pairs) / len(image_csv_pairs):.1%})"
    )
    print()

    # Copy images and create manifests
    print("Copying images and creating manifests...")
    copy_images_and_create_manifest(train_pairs, output_dir, "train")
    copy_images_and_create_manifest(val_pairs, output_dir, "val")
    print()

    # Create dataset metadata
    metadata = {
        "dataset_name": "Kaggle High-Quality Invoice Images",
        "source": "https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr",
        "license": "ODbL 1.0",
        "author": "Osama Hosam Abdellatif",
        "total_images": len(image_csv_pairs),
        "train_images": len(train_pairs),
        "val_images": len(val_pairs),
        "split_ratio": f"{train_ratio}/{val_ratio}",
        "random_seed": args.seed,
        "input_directory": str(input_dir),
        "preparation_date": "2025-11-13",
    }

    metadata_path = output_dir / "dataset_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Dataset metadata: {metadata_path}")
    print()
    print("✅ Dataset preparation complete!")
    print(f"   Train: {output_dir}/train/images/ ({len(train_pairs)} images)")
    print(f"   Val: {output_dir}/val/images/ ({len(val_pairs)} images)")


if __name__ == "__main__":
    main()
