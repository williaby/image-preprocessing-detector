# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""Phase 2 Dataset Preparation Pipeline.

Generates synthetic augmented dataset with weak supervision labels for IQA training.

Pipeline:
1. Load base document images from source datasets
2. Apply document-specific augmentations (noise, blur, skew, etc.)
3. Generate weak supervision labels using image quality metrics
4. Split into train/val/test sets
5. Save with proper directory structure for GCS upload

Usage:
    python scripts/prepare_phase2_data.py \
        --source-dir data/raw/rvl-cdip \
        --output-dir datasets/iqa_phase2 \
        --num-samples 50000 \
        --preset medium

Output Structure:
    datasets/iqa_phase2/
    ├── train/
    │   ├── images/
    │   │   ├── img_000001.png
    │   │   └── ... (35,000 images)
    │   └── labels.json
    ├── val/
    │   ├── images/
    │   │   └── ... (7,500 images)
    │   └── labels.json
    └── test/
        ├── images/
        │   └── ... (7,500 images)
        └── labels.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.augmentation import DocumentAugmentationPipeline, create_augmentation_pipeline
from data.weak_supervision import WeakSupervisionLabeler


def convert_pdf_to_images(pdf_path: Path) -> list[np.ndarray]:
    """Convert PDF pages to images using PyMuPDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of page images as numpy arrays (BGR format for OpenCV)
    """
    try:
        doc = fitz.open(str(pdf_path))
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at 300 DPI for quality
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)

            # Convert to numpy array
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            # Convert RGB/RGBA to BGR (OpenCV format)
            if pix.n == 3:  # RGB
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

            images.append(img)

        doc.close()
        return images
    except Exception as e:
        print(f"Warning: Failed to convert {pdf_path}: {e}")
        return []


def collect_source_images(
    source_dirs: list[Path],
    max_images: int | None = None,
    include_pdfs: bool = True,
) -> list[np.ndarray]:
    """Collect and load all source images from directories (supports PDFs and images).

    Args:
        source_dirs: List of directories containing source images/PDFs
        max_images: Maximum number of images to collect (None = all)
        include_pdfs: Whether to convert PDF files to images

    Returns:
        List of loaded images as numpy arrays (BGR format)
    """
    valid_image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
    pdf_extension = {".pdf"}

    all_images = []

    for source_dir in source_dirs:
        if not source_dir.exists():
            print(f"Warning: Source directory not found: {source_dir}")
            continue

        print(f"Scanning {source_dir}...")

        # Collect image files
        image_paths = []
        for ext in valid_image_extensions:
            image_paths.extend(source_dir.rglob(f"*{ext}"))

        # Load images
        for img_path in tqdm(image_paths, desc="Loading images", leave=False):
            img = cv2.imread(str(img_path))
            if img is not None:
                all_images.append(img)
                if max_images and len(all_images) >= max_images:
                    break

        # Collect and convert PDFs if enabled
        if include_pdfs:
            pdf_paths = list(source_dir.rglob("*.pdf"))
            print(f"Found {len(pdf_paths)} PDF files to convert...")

            for pdf_path in tqdm(pdf_paths, desc="Converting PDFs"):
                pdf_images = convert_pdf_to_images(pdf_path)
                all_images.extend(pdf_images)

                if max_images and len(all_images) >= max_images:
                    break

        if max_images and len(all_images) >= max_images:
            break

    # Shuffle and limit
    random.shuffle(all_images)
    if max_images:
        all_images = all_images[:max_images]

    print(f"Loaded {len(all_images)} source images (images + PDF pages)")
    return all_images


def generate_augmented_dataset(
    source_images: list[np.ndarray],
    output_dir: Path,
    num_samples: int,
    augmentation_pipeline: DocumentAugmentationPipeline,
    labeler: WeakSupervisionLabeler,
    train_split: float = 0.70,
    val_split: float = 0.15,
    test_split: float = 0.15,
) -> dict[str, Any]:
    """Generate augmented dataset with weak supervision labels.

    Args:
        source_images: List of source images as numpy arrays (BGR format)
        output_dir: Output directory for dataset
        num_samples: Total number of samples to generate
        augmentation_pipeline: Configured augmentation pipeline
        labeler: Weak supervision labeler
        train_split: Fraction for training set
        val_split: Fraction for validation set
        test_split: Fraction for test set

    Returns:
        Dictionary with dataset statistics
    """
    # Calculate split sizes
    num_train = int(num_samples * train_split)
    num_val = int(num_samples * val_split)
    num_test = num_samples - num_train - num_val

    print(f"\nGenerating {num_samples} samples:")
    print(f"  Train: {num_train}")
    print(f"  Val: {num_val}")
    print(f"  Test: {num_test}")

    # Create output directories
    splits = {
        "train": (output_dir / "train", num_train),
        "val": (output_dir / "val", num_val),
        "test": (output_dir / "test", num_test),
    }

    for split_name, (split_dir, _) in splits.items():
        images_dir = split_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

    # Generate samples for each split
    stats = {}
    sample_idx = 0

    for split_name, (split_dir, split_size) in splits.items():
        print(f"\n{'=' * 60}")
        print(f"Generating {split_name} set ({split_size} samples)")
        print(f"{'=' * 60}")

        split_labels = []
        images_dir = split_dir / "images"

        for i in tqdm(range(split_size), desc=f"{split_name} set"):
            # Select random source image (with replacement)
            image = random.choice(source_images)

            # Apply augmentations
            augmented = augmentation_pipeline(image)

            # Save augmented image
            output_filename = f"img_{sample_idx:06d}.png"
            output_path = images_dir / output_filename
            cv2.imwrite(str(output_path), augmented)

            # Generate weak supervision labels
            labels = labeler.label_image(augmented, output_filename)

            # Add to split labels
            split_labels.append(labels.to_dict())

            sample_idx += 1

        # Save labels.json for this split
        labels_path = split_dir / "labels.json"
        with open(labels_path, "w") as f:
            json.dump(split_labels, f, indent=2)

        print(f"✓ Saved {split_size} samples to {split_dir}")
        print(f"✓ Saved labels to {labels_path}")

        # Compute statistics (5 classes aligned with ResNetTeacher model)
        issue_counts = {
            "blur": 0,
            "noise": 0,
            "skew": 0,
            "illumination": 0,
            "artifacts": 0,
        }

        for label_dict in split_labels:
            for issue_type, label_info in label_dict["labels"].items():
                if label_info["value"] == 1:
                    issue_counts[issue_type] += 1

        stats[split_name] = {
            "num_samples": split_size,
            "issue_counts": issue_counts,
            "issue_frequencies": {k: v / split_size for k, v in issue_counts.items()},
        }

    return stats


def print_dataset_summary(stats: dict[str, Any], output_dir: Path) -> None:
    """Print dataset generation summary.

    Args:
        stats: Dataset statistics
        output_dir: Output directory
    """
    print("\n" + "=" * 60)
    print("DATASET GENERATION COMPLETE")
    print("=" * 60)

    print(f"\nOutput directory: {output_dir}")
    print(f"Total samples: {sum(s['num_samples'] for s in stats.values())}")

    for split_name, split_stats in stats.items():
        print(f"\n{split_name.upper()} SET ({split_stats['num_samples']} samples):")
        print("  Issue frequencies:")
        for issue, freq in split_stats["issue_frequencies"].items():
            count = split_stats["issue_counts"][issue]
            print(f"    {issue:15s}: {count:5d} ({freq:.1%})")

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("\n1. Upload dataset to GCS:")
    print("   ./scripts/gcs_helpers.sh upload-phase2")
    print("\n2. Verify upload:")
    print("   gsutil du -sh gs://image_detection_b/datasets/iqa_phase2/")
    print("\n3. Start Colab training:")
    print("   Open: notebooks/colab/phase2_iqa_training.ipynb")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Phase 2 IQA training dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source-dirs",
        type=str,
        nargs="+",
        required=True,
        help="Source directories containing document images",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="datasets/iqa_phase2",
        help="Output directory for generated dataset (default: datasets/iqa_phase2)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=50000,
        help="Total number of samples to generate (default: 50000)",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="medium",
        choices=["light", "medium", "heavy"],
        help="Augmentation preset (default: medium)",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.70,
        help="Training set fraction (default: 0.70)",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.15,
        help="Validation set fraction (default: 0.15)",
    )
    parser.add_argument(
        "--test-split",
        type=float,
        default=0.15,
        help="Test set fraction (default: 0.15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # Validate splits
    if abs(args.train_split + args.val_split + args.test_split - 1.0) > 0.001:
        print("Error: train_split + val_split + test_split must equal 1.0")
        sys.exit(1)

    # Set random seeds
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Parse source directories
    source_dirs = [Path(d) for d in args.source_dirs]
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("PHASE 2 DATASET GENERATION")
    print("=" * 60)
    print("\nConfiguration:")
    print(f"  Source dirs: {', '.join(str(d) for d in source_dirs)}")
    print(f"  Output dir: {output_dir}")
    print(f"  Total samples: {args.num_samples}")
    print(f"  Augmentation preset: {args.preset}")
    print(
        f"  Splits: {args.train_split:.0%} train / {args.val_split:.0%} val / {args.test_split:.0%} test"
    )
    print(f"  Random seed: {args.seed}")

    # Collect source images
    print("\n" + "=" * 60)
    print("COLLECTING SOURCE IMAGES")
    print("=" * 60)
    source_images = collect_source_images(source_dirs)

    if not source_images:
        print("Error: No source images found")
        sys.exit(1)

    # Create augmentation pipeline
    print("\n" + "=" * 60)
    print("INITIALIZING PIPELINES")
    print("=" * 60)
    print(f"Creating augmentation pipeline (preset: {args.preset})...")
    augmentation_pipeline = create_augmentation_pipeline(
        preset=args.preset,
        random_seed=args.seed,
    )

    print("Creating weak supervision labeler...")
    labeler = WeakSupervisionLabeler()

    # Generate dataset
    stats = generate_augmented_dataset(
        source_images=source_images,
        output_dir=output_dir,
        num_samples=args.num_samples,
        augmentation_pipeline=augmentation_pipeline,
        labeler=labeler,
        train_split=args.train_split,
        val_split=args.val_split,
        test_split=args.test_split,
    )

    # Print summary
    print_dataset_summary(stats, output_dir)


if __name__ == "__main__":
    main()
