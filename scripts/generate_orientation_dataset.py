#!/usr/bin/env python3
"""
Generate Orientation Detection Training Dataset

Creates a balanced 4-class orientation dataset by:
1. Sampling documents from multiple sources per composition table
2. Applying document-level train/val/test split (prevents leakage)
3. Rotating each document by 0°, 90°, 180°, 270°
4. Saving with metadata for training

Dataset Composition (12,500 unique documents → 50,000 rotated samples):
- Scientific papers: 2,000 (DocLayNet)
- Financial reports: 1,500 (DocLayNet)
- Forms: 1,500 (FUNSD, FUNSD+, NIST)
- Receipts: 1,000 (SROIE)
- Tables: 1,500 (TableBank, PubTabNet)
- Legal documents: 1,000 (DocLayNet)
- Handwritten pages: 1,000 (NIST SD-19)
- Mixed layouts: 1,000 (DocLayNet)
- Arabic documents: 1,500 (Arabic Docs OCR)
- Devanagari documents: 700 (Nepal Devanagari)
- Japanese vertical: 1,050 (MLT-19)

Usage:
    python scripts/generate_orientation_dataset.py --output-dir /path/to/output
    python scripts/generate_orientation_dataset.py --dry-run  # Preview only
"""

from __future__ import annotations

import argparse
import hashlib  # nosemgrep: python.lang.security.audit.insecure-hash-algorithms  # Uses SHA256, not MD5
import json
import logging
import random
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Base data path
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")

# Dataset composition configuration
DATASET_COMPOSITION: dict[str, dict[str, Any]] = {
    "scientific_papers": {
        "count": 2000,
        "sources": [
            {
                "path": BASE_DATA_PATH / "documents/doclaynet",
                "pattern": "**/*.png",
                "filter_fn": lambda p: "scientific" in str(p).lower()
                or random.random() < 0.3,
            }
        ],
        "doc_type": "scientific",
    },
    "financial_reports": {
        "count": 1500,
        "sources": [
            {
                "path": BASE_DATA_PATH / "documents/doclaynet",
                "pattern": "**/*.png",
                "filter_fn": lambda p: "financial" in str(p).lower()
                or random.random() < 0.2,
            }
        ],
        "doc_type": "financial",
    },
    "forms": {
        "count": 1500,
        "sources": [
            {"path": BASE_DATA_PATH / "forms/funsd", "pattern": "**/*.png"},
            {"path": BASE_DATA_PATH / "forms/funsd_plus", "pattern": "**/*.png"},
            {"path": BASE_DATA_PATH / "forms/nist-sd2", "pattern": "**/*.*"},
            {"path": BASE_DATA_PATH / "forms/nist_sd6", "pattern": "**/*.*"},
        ],
        "doc_type": "form",
    },
    "receipts": {
        "count": 1000,
        "sources": [
            {"path": BASE_DATA_PATH / "forms/sroie_icdar2019", "pattern": "**/*.jpg"},
        ],
        "doc_type": "receipt",
    },
    "tables": {
        "count": 1500,
        "sources": [
            {"path": BASE_DATA_PATH / "tables/tablebank", "pattern": "**/*.jpg"},
            {"path": BASE_DATA_PATH / "tables/pubtabnet", "pattern": "**/*.png"},
        ],
        "doc_type": "table",
    },
    "legal_documents": {
        "count": 1000,
        "sources": [
            {
                "path": BASE_DATA_PATH / "documents/doclaynet",
                "pattern": "**/*.png",
                "filter_fn": lambda p: "law" in str(p).lower()
                or random.random() < 0.15,
            }
        ],
        "doc_type": "legal",
    },
    "handwritten_pages": {
        "count": 1000,
        "sources": [
            {"path": BASE_DATA_PATH / "handwriting/nist-sd19", "pattern": "**/*.*"},
        ],
        "doc_type": "handwritten",
    },
    "mixed_layouts": {
        "count": 1000,
        "sources": [
            {
                "path": BASE_DATA_PATH / "documents/doclaynet",
                "pattern": "**/*.png",
                "filter_fn": lambda p: random.random() < 0.15,
            }
        ],
        "doc_type": "mixed",
    },
    "arabic_documents": {
        "count": 1500,
        "sources": [
            {
                "path": BASE_DATA_PATH / "language/arabic_docs_ocr",
                "pattern": "**/*.jpg",
            },
            {
                "path": BASE_DATA_PATH / "language/arabic_docs_ocr",
                "pattern": "**/*.png",
            },
        ],
        "doc_type": "arabic",
    },
    "devanagari_documents": {
        "count": 700,
        "sources": [
            {
                "path": BASE_DATA_PATH
                / "language/multilingual_scripts/nepal_devanagari",
                "pattern": "**/*.png",
            },
        ],
        "doc_type": "devanagari",
    },
    "japanese_vertical": {
        "count": 1050,
        "sources": [
            {"path": BASE_DATA_PATH / "language/mlt19", "pattern": "**/*.jpg"},
            {"path": BASE_DATA_PATH / "language/mlt19", "pattern": "**/*.png"},
        ],
        "doc_type": "japanese",
    },
}

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Rotation angles (class labels)
ROTATIONS = {
    0: 0,  # Class 0: Upright
    1: 90,  # Class 1: 90° clockwise
    2: 180,  # Class 2: Upside-down
    3: 270,  # Class 3: 270° clockwise (90° counter-clockwise)
}


@dataclass
class DocumentSample:
    """Represents a source document sample."""

    source_path: Path
    doc_type: str
    doc_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.doc_id:
            # Generate unique ID from path hash
            self.doc_id = hashlib.sha256(str(self.source_path).encode()).hexdigest()[
                :12
            ]


def scan_directory_fast(
    root: Path,
    extensions: set[str],
    max_files: int = 50000,
) -> list[Path]:
    """Fast directory scanning with early termination."""
    files: list[Path] = []

    def _scan(path: Path, depth: int = 0) -> None:
        if len(files) >= max_files or depth > 5:
            return
        try:
            for entry in path.iterdir():
                if len(files) >= max_files:
                    return
                if entry.is_file():
                    if entry.suffix.lower() in extensions:
                        files.append(entry)
                elif entry.is_dir() and not entry.name.startswith("."):
                    _scan(entry, depth + 1)
        except PermissionError:
            pass

    _scan(root)
    return files


def collect_source_files(category: str, config: dict[str, Any]) -> list[DocumentSample]:
    """Collect source files for a category."""
    samples: list[DocumentSample] = []
    target_count = config["count"]
    doc_type = config["doc_type"]

    all_files: list[Path] = []

    # Determine extensions from patterns
    extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

    for source in config["sources"]:
        source_path = source["path"]
        filter_fn = source.get("filter_fn", lambda x: True)

        if not source_path.exists():
            logger.warning(f"Source path not found: {source_path}")
            continue

        # Use fast scanning with early termination
        # Collect more than needed to allow for filtering
        max_scan = target_count * 5
        files = scan_directory_fast(source_path, extensions, max_scan)

        # Apply filter if specified
        files = [f for f in files if filter_fn(f)]
        all_files.extend(files)

        # Early termination if we have enough
        if len(all_files) >= target_count * 3:
            break

    if not all_files:
        logger.warning(f"No files found for category: {category}")
        return samples

    # Shuffle and sample
    random.shuffle(all_files)
    selected = all_files[:target_count]

    logger.info(f"{category}: Found {len(all_files)} files, selected {len(selected)}")

    for f in selected:
        samples.append(DocumentSample(source_path=f, doc_type=doc_type))

    return samples


def split_by_document_id(
    samples: list[DocumentSample],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> tuple[list[DocumentSample], list[DocumentSample], list[DocumentSample]]:
    """
    Split samples by document ID to prevent data leakage.

    CRITICAL: Same document must NOT appear in different splits.
    """
    # Group by doc_type for stratified splitting
    by_type: dict[str, list[DocumentSample]] = {}
    for sample in samples:
        if sample.doc_type not in by_type:
            by_type[sample.doc_type] = []
        by_type[sample.doc_type].append(sample)

    train_samples: list[DocumentSample] = []
    val_samples: list[DocumentSample] = []
    test_samples: list[DocumentSample] = []

    for doc_type, type_samples in by_type.items():
        random.shuffle(type_samples)
        n = len(type_samples)

        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_samples.extend(type_samples[:train_end])
        val_samples.extend(type_samples[train_end:val_end])
        test_samples.extend(type_samples[val_end:])

    # Verify no overlap
    train_ids = {s.doc_id for s in train_samples}
    val_ids = {s.doc_id for s in val_samples}
    test_ids = {s.doc_id for s in test_samples}

    assert len(train_ids & val_ids) == 0, "Train/Val ID overlap detected!"
    assert len(train_ids & test_ids) == 0, "Train/Test ID overlap detected!"
    assert len(val_ids & test_ids) == 0, "Val/Test ID overlap detected!"

    logger.info(
        f"Split complete: Train={len(train_samples)}, "
        f"Val={len(val_samples)}, Test={len(test_samples)}"
    )

    return train_samples, val_samples, test_samples


def load_and_rotate_image(
    source_path: Path,
    rotation_angle: int,
    target_size: tuple[int, int] = (224, 224),
) -> np.ndarray | None:
    """Load image, rotate, and resize to target size."""
    try:
        # Load with PIL for better format support
        img = Image.open(source_path)

        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Rotate (PIL rotates counter-clockwise, so negate for clockwise)
        if rotation_angle != 0:
            img = img.rotate(-rotation_angle, expand=True)

        # Resize to target size
        img = img.resize(target_size, Image.Resampling.LANCZOS)

        # Convert to numpy array
        return np.array(img)

    except Exception as e:
        logger.warning(f"Failed to process {source_path}: {e}")
        return None


def generate_rotated_samples(
    samples: list[DocumentSample],
    output_dir: Path,
    split_name: str,
    target_size: tuple[int, int] = (224, 224),
) -> list[dict[str, Any]]:
    """Generate rotated samples for a split."""
    metadata: list[dict[str, Any]] = []
    split_dir = output_dir / split_name

    # Create class directories
    for class_id in ROTATIONS:
        (split_dir / str(class_id)).mkdir(parents=True, exist_ok=True)

    for sample in tqdm(samples, desc=f"Processing {split_name}"):
        for class_id, angle in ROTATIONS.items():
            # Load and rotate
            img_array = load_and_rotate_image(sample.source_path, angle, target_size)

            if img_array is None:
                continue

            # Generate output filename
            output_name = f"{sample.doc_id}_rot{angle}.jpg"
            output_path = split_dir / str(class_id) / output_name

            # Save image
            img = Image.fromarray(img_array)
            img.save(output_path, "JPEG", quality=95)

            # Record metadata
            metadata.append(
                {
                    "filename": str(output_path.relative_to(output_dir)),
                    "source_path": str(sample.source_path),
                    "doc_id": sample.doc_id,
                    "doc_type": sample.doc_type,
                    "rotation_angle": angle,
                    "class_id": class_id,
                    "split": split_name,
                }
            )

    return metadata


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Orientation Detection Training Dataset"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/02_training_data/orientation_dataset"),
        help="Output directory for the dataset",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        nargs=2,
        default=[224, 224],
        help="Target image size (width height)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sampling without generating images",
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)
    np.random.seed(args.seed)

    logger.info("=" * 60)
    logger.info("Orientation Dataset Generation")
    logger.info("=" * 60)

    # Step 1: Collect source files from all categories
    logger.info("\n[Step 1] Collecting source documents...")
    all_samples: list[DocumentSample] = []

    for category, config in DATASET_COMPOSITION.items():
        samples = collect_source_files(category, config)
        all_samples.extend(samples)

    logger.info(f"\nTotal source documents collected: {len(all_samples)}")

    # Count by type
    type_counts: dict[str, int] = {}
    for s in all_samples:
        type_counts[s.doc_type] = type_counts.get(s.doc_type, 0) + 1

    logger.info("\nComposition by document type:")
    for doc_type, count in sorted(type_counts.items()):
        logger.info(f"  {doc_type}: {count}")

    if args.dry_run:
        logger.info("\n[DRY RUN] Would generate:")
        logger.info(f"  - Train: {int(len(all_samples) * TRAIN_RATIO) * 4} samples")
        logger.info(f"  - Val: {int(len(all_samples) * VAL_RATIO) * 4} samples")
        logger.info(f"  - Test: {int(len(all_samples) * TEST_RATIO) * 4} samples")
        logger.info(f"  - Total: {len(all_samples) * 4} samples")
        return 0

    # Step 2: Split by document ID (CRITICAL - prevents leakage)
    logger.info("\n[Step 2] Splitting by document ID...")
    train_samples, val_samples, test_samples = split_by_document_id(
        all_samples, TRAIN_RATIO, VAL_RATIO
    )

    # Step 3: Create output directory
    output_dir = args.output_dir
    if output_dir.exists():
        logger.warning(f"Output directory exists: {output_dir}")
        response = input("Overwrite? (y/n): ")
        if response.lower() != "y":
            logger.info("Aborted.")
            return 1
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 4: Generate rotated samples
    logger.info("\n[Step 3] Generating rotated samples...")
    target_size = tuple(args.target_size)

    all_metadata: list[dict[str, Any]] = []

    # Process each split
    train_meta = generate_rotated_samples(
        train_samples, output_dir, "train", target_size
    )
    all_metadata.extend(train_meta)

    val_meta = generate_rotated_samples(val_samples, output_dir, "val", target_size)
    all_metadata.extend(val_meta)

    test_meta = generate_rotated_samples(test_samples, output_dir, "test", target_size)
    all_metadata.extend(test_meta)

    # Step 5: Save metadata
    logger.info("\n[Step 4] Saving metadata...")

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "dataset_name": "orientation_detection_v1",
                "created_at": str(np.datetime64("now")),
                "total_samples": len(all_metadata),
                "splits": {
                    "train": len(train_meta),
                    "val": len(val_meta),
                    "test": len(test_meta),
                },
                "classes": {
                    "0": "0° (upright)",
                    "1": "90° clockwise",
                    "2": "180° (inverted)",
                    "3": "270° clockwise",
                },
                "composition": {
                    doc_type: count for doc_type, count in type_counts.items()
                },
                "samples": all_metadata,
            },
            f,
            indent=2,
        )

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Dataset Generation Complete!")
    logger.info("=" * 60)
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Total samples: {len(all_metadata)}")
    logger.info(
        f"  Train: {len(train_meta)} ({len(train_meta) // 4} docs × 4 rotations)"
    )
    logger.info(f"  Val: {len(val_meta)} ({len(val_meta) // 4} docs × 4 rotations)")
    logger.info(f"  Test: {len(test_meta)} ({len(test_meta) // 4} docs × 4 rotations)")
    logger.info(f"Metadata: {metadata_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
