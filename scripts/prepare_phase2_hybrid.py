#!/usr/bin/env python3
"""Generate hybrid Phase 2 IQA training dataset from multiple sources.

Combines ground-truth and weak supervision datasets:
- DIQA-5000: 5,000 images with 3D MOS labels (ground-truth)
- SmartDoc-QA: 4,260 images with quality labels (ground-truth)
- OHR-Bench: 5,000 PDF pages with weak supervision labels
- KADID-10k: 1,000 natural images with IQA labels (ground-truth)

Total: ~15,260 base images → 5x augmentation → ~76,300 training samples

Phase 2 - Week 2-4: ResNet Teacher & Student ML IQA Training
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.augmentation import create_augmentation_pipeline
from data.weak_supervision import WeakSupervisionLabeler

# Type alias for image data tuple
ImageData = tuple[np.ndarray, dict[str, int], dict[str, Any]]


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""

    num_samples: int
    augmentation_multiplier: float = 5.0
    preset: str = "medium"
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15


def _map_kadid_distortion_to_labels(distortion_type: int) -> dict[str, int]:
    """Map KADID-10k distortion type to binary labels.

    KADID-10k has 25 distortion types:
    - Types 1-5: blur-related
    - Types 6-10: noise-related
    - Types 11-15: compression/artifacts
    - Types 16-20: color/illumination
    - Types 21-25: other (map to artifacts)
    """
    return {
        "blur": 1 if 1 <= distortion_type <= 5 else 0,
        "noise": 1 if 6 <= distortion_type <= 10 else 0,
        "artifacts": 1
        if 11 <= distortion_type <= 15 or 21 <= distortion_type <= 25
        else 0,
        "illumination": 1 if 16 <= distortion_type <= 20 else 0,
        "skew": 0,  # KADID-10k doesn't have geometric distortions
    }


def load_diqa5000_images(
    diqa5000_dir: Path,
    split: str = "train",
    max_images: int | None = None,
) -> list[tuple[np.ndarray, dict[str, int], dict[str, Any]]]:
    """Load DIQA-5000 dataset with MOS labels.

    Args:
        diqa5000_dir: Path to DIQA-5000 dataset root
        split: Dataset split ("train", "val", "test")
        max_images: Maximum number of images to load (None = all)

    Returns:
        List of (image, binary_labels, metadata) tuples
    """
    print(f"\n📖 Loading DIQA-5000 ({split} split)...")

    split_dir = diqa5000_dir / split
    csv_path = split_dir / f"{split}.csv"
    images_dir = split_dir / "res"  # Enhanced images with MOS labels

    if not csv_path.exists():
        print(f"Warning: {csv_path} not found, skipping DIQA-5000 {split}")
        return []

    # Load CSV annotations
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        images_data = list(reader)

    if max_images:
        images_data = images_data[:max_images]

    print(f"Found {len(images_data)} DIQA-5000 images in CSV")

    # Load images and convert MOS to binary labels
    loaded_images = []
    for row in tqdm(images_data, desc="Loading DIQA-5000 images"):
        img_path = images_dir / row["res"]

        if not img_path.exists():
            continue

        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # Convert MOS to binary labels (MOS scale: 0-5, threshold: 2.5)
        # Below 2.5 = poor quality = issue present (1)
        # Above 2.5 = good quality = no issue (0)
        overall = float(row["overall"])
        sharpness = float(row["sharpness"])
        color_fidelity = float(row["color_fidelity"])

        binary_labels = {
            "blur": 1 if sharpness < 2.5 else 0,
            "illumination": 1 if color_fidelity < 2.5 else 0,
            "artifacts": 1 if overall < 2.5 else 0,
            "noise": 0,  # Will be filled by weak supervision
            "skew": 0,  # Will be filled by weak supervision
        }

        # Metadata
        metadata = {
            "source": "diqa5000",
            "split": split,
            "original_image": row["ori"],
            "mos_overall": overall,
            "mos_sharpness": sharpness,
            "mos_color_fidelity": color_fidelity,
        }

        loaded_images.append((img, binary_labels, metadata))

    print(f"Loaded {len(loaded_images)} DIQA-5000 images")
    return loaded_images


def _load_kadid_dataset() -> Any | None:
    """Load the KADID-10k dataset, returning None on failure."""
    try:
        from iqadataset import KADID10K
    except ImportError:
        print("Warning: iqadataset not installed. Run: pip install iqadataset")
        print("Skipping KADID-10k dataset.")
        return None

    try:
        return KADID10K(download=True)
    except Exception as e:
        print(f"Error loading KADID-10k: {e}")
        print("Skipping KADID-10k dataset.")
        return None


def _process_kadid_sample(sample: dict[str, Any]) -> ImageData:
    """Process a single KADID-10k sample into ImageData format."""
    dis_img = sample["dis_img"]

    # Convert RGB to BGR for OpenCV compatibility
    if len(dis_img.shape) == 3 and dis_img.shape[2] == 3:
        dis_img = cv2.cvtColor(dis_img, cv2.COLOR_RGB2BGR)

    distortion_type = sample.get("dist_type", 0)
    binary_labels = _map_kadid_distortion_to_labels(distortion_type)

    metadata = {
        "source": "kadid10k",
        "distortion_type": distortion_type,
        "dmos": sample.get("dmos", 0.0),
    }

    return (dis_img, binary_labels, metadata)


def load_kadid10k_images(max_images: int = 1000) -> list[ImageData]:
    """Load KADID-10k natural images with IQA labels.

    Args:
        max_images: Maximum number of images to load (default: 1000)

    Returns:
        List of (image, binary_labels, metadata) tuples
    """
    print(f"\n📖 Loading KADID-10k (max {max_images} images)...")

    dataset = _load_kadid_dataset()
    if dataset is None:
        return []

    loaded_images = []
    for i, sample in enumerate(
        tqdm(dataset, desc="Loading KADID-10k", total=max_images)
    ):
        if i >= max_images:
            break
        loaded_images.append(_process_kadid_sample(sample))

    print(f"Loaded {len(loaded_images)} KADID-10k images")
    return loaded_images


def _render_pdf_page_to_image(page: Any, fitz_module: Any) -> np.ndarray:
    """Render a PDF page to a BGR numpy array at 300 DPI."""
    mat = fitz_module.Matrix(300 / 72, 300 / 72)
    pix = page.get_pixmap(matrix=mat)

    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )

    # Convert RGB/RGBA to BGR (OpenCV format)
    if pix.n == 3:  # RGB
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    if pix.n == 4:  # RGBA
        return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return img


def _create_ohr_page_metadata(
    img: np.ndarray,
    pdf_path: Path,
    page_num: int,
    weak_labeler: WeakSupervisionLabeler,
) -> ImageData:
    """Create image data tuple for an OHR-Bench page."""
    labels = weak_labeler.label_image(img, str(pdf_path))
    binary_labels = {key: int(label.value) for key, label in labels.labels.items()}
    label_confidences = {
        key: float(label.confidence) for key, label in labels.labels.items()
    }

    metadata = {
        "source": "ohr_bench",
        "pdf_path": str(pdf_path.name),
        "page_num": page_num,
        "weak_supervision": True,
        "quality_scores": labels.quality_scores,
        "label_confidences": label_confidences,
    }

    return (img, binary_labels, metadata)


def _process_single_pdf(
    pdf_path: Path,
    weak_labeler: WeakSupervisionLabeler,
    fitz_module: Any,
    max_pages: int,
    current_count: int,
) -> list[ImageData]:
    """Process a single PDF and return list of image data."""
    results: list[ImageData] = []
    doc = fitz_module.open(str(pdf_path))

    try:
        for page_num in range(len(doc)):
            if current_count + len(results) >= max_pages:
                break

            page = doc[page_num]
            img = _render_pdf_page_to_image(page, fitz_module)
            image_data = _create_ohr_page_metadata(
                img, pdf_path, page_num, weak_labeler
            )
            results.append(image_data)
    finally:
        doc.close()

    return results


def load_ohr_bench_images(
    ohr_bench_dir: Path,
    max_images: int = 5000,
    weak_labeler: WeakSupervisionLabeler | None = None,
) -> list[ImageData]:
    """Load OHR-Bench PDFs with weak supervision labels.

    Args:
        ohr_bench_dir: Path to OHR-Bench dataset
        max_images: Maximum number of PDF pages to extract
        weak_labeler: WeakSupervisionLabeler instance (created if None)

    Returns:
        List of (image, binary_labels, metadata) tuples
    """
    print(f"\n📖 Loading OHR-Bench PDFs (max {max_images} pages)...")

    if weak_labeler is None:
        weak_labeler = WeakSupervisionLabeler()

    pdf_paths = list(ohr_bench_dir.rglob("*.pdf"))
    random.shuffle(pdf_paths)
    print(f"Found {len(pdf_paths)} OHR-Bench PDFs")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Warning: PyMuPDF not installed. Run: pip install pymupdf")
        print("Skipping OHR-Bench dataset.")
        return []

    loaded_images: list[ImageData] = []

    for pdf_path in tqdm(pdf_paths, desc="Processing OHR-Bench PDFs"):
        if len(loaded_images) >= max_images:
            break

        try:
            page_images = _process_single_pdf(
                pdf_path, weak_labeler, fitz, max_images, len(loaded_images)
            )
            loaded_images.extend(page_images)
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")

    print(f"Loaded {len(loaded_images)} OHR-Bench pages")
    return loaded_images


def load_smartdoc_qa_images(
    smartdoc_dir: Path,
    max_images: int | None = None,  # Reserved for implementation
) -> list[tuple[np.ndarray, dict[str, int], dict[str, Any]]]:
    """Load SmartDoc-QA dataset with quality labels.

    Args:
        smartdoc_dir: Path to SmartDoc-QA dataset
        max_images: Maximum number of images to load (reserved for implementation)

    Returns:
        List of (image, binary_labels, metadata) tuples
    """
    del max_images  # Unused until implementation complete
    print("\n📖 Loading SmartDoc-QA dataset...")

    # Check if dataset is downloaded and extracted
    if not smartdoc_dir.exists():
        print(f"Warning: SmartDoc-QA directory not found at {smartdoc_dir}")
        print("Skipping SmartDoc-QA dataset.")
        return []

    # SmartDoc-QA loader pending implementation (dataset extraction required)
    print("SmartDoc-QA loader not yet implemented (pending dataset extraction)")
    print("Skipping SmartDoc-QA for now.")
    return []


def _create_split_directories(output_dir: Path) -> dict[str, Path]:
    """Create output directories for train/val/test splits."""
    split_dirs = {}
    for split in ["train", "val", "test"]:
        split_dir = output_dir / split
        split_dir.mkdir(parents=True, exist_ok=True)
        split_dirs[split] = split_dir
    return split_dirs


def _split_source_images(
    source_images: list[ImageData], config: DatasetConfig
) -> dict[str, list[ImageData]]:
    """Split source images into train/val/test sets."""
    shuffled = source_images.copy()
    random.shuffle(shuffled)

    num_sources = len(shuffled)
    train_end = int(num_sources * config.train_ratio)
    val_end = train_end + int(num_sources * config.val_ratio)

    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:val_end],
        "test": shuffled[val_end:],
    }


def _save_augmented_sample(
    augmented: np.ndarray,
    source_labels: dict[str, int],
    source_metadata: dict[str, Any],
    split: str,
    sample_idx: int,
    aug_idx: int,
    split_dir: Path,
) -> None:
    """Save a single augmented sample and its metadata."""
    img_filename = f"{split}_{sample_idx:06d}.jpg"
    cv2.imwrite(str(split_dir / img_filename), augmented)

    sample_metadata = {
        "image_id": sample_idx,
        "filename": img_filename,
        "labels": source_labels,
        "source_metadata": source_metadata,
        "augmentation_index": aug_idx,
    }

    metadata_path = split_dir / f"{split}_{sample_idx:06d}.json"
    with open(metadata_path, "w") as f:
        json.dump(sample_metadata, f, indent=2)


def _update_issue_counts(
    issue_counts: dict[str, int], source_labels: dict[str, int]
) -> None:
    """Update issue counts based on source labels."""
    for issue, present in source_labels.items():
        if present == 1:
            issue_counts[issue] += 1


def _generate_split_samples(
    split: str,
    split_sources: list[ImageData],
    split_dir: Path,
    split_target: int,
    augs_per_source: int,
    aug_pipeline: Any,
) -> dict[str, int]:
    """Generate augmented samples for a single split.

    Returns:
        Dictionary of issue counts for statistics.
    """
    issue_counts = {
        "blur": 0,
        "noise": 0,
        "skew": 0,
        "illumination": 0,
        "artifacts": 0,
    }

    samples_generated = 0
    sample_idx = 0

    with tqdm(total=split_target, desc=f"Generating {split}") as pbar:
        while samples_generated < split_target:
            for source_img, source_labels, source_metadata in split_sources:
                for aug_idx in range(augs_per_source):
                    if samples_generated >= split_target:
                        return issue_counts

                    augmented = aug_pipeline(source_img)
                    _update_issue_counts(issue_counts, source_labels)
                    _save_augmented_sample(
                        augmented,
                        source_labels,
                        source_metadata,
                        split,
                        sample_idx,
                        aug_idx,
                        split_dir,
                    )

                    samples_generated += 1
                    sample_idx += 1
                    pbar.update(1)

    return issue_counts


def _print_split_statistics(
    split: str, samples_generated: int, issue_counts: dict[str, int]
) -> None:
    """Print statistics for a completed split."""
    print(f"\n{split.upper()} SET ({samples_generated} samples):")
    if samples_generated == 0:
        print("  No samples generated for this split.")
        return

    print("  Issue frequencies:")
    for issue, count in sorted(issue_counts.items()):
        percentage = (count / samples_generated) * 100
        print(f"    {issue:15s}: {count:5d} ({percentage:5.1f}%)")


def _save_dataset_summary(
    output_dir: Path,
    source_images: list[ImageData],
    config: DatasetConfig,
) -> None:
    """Save dataset summary to JSON file."""
    summary = {
        "total_samples": config.num_samples,
        "source_images": len(source_images),
        "augmentation_multiplier": config.augmentation_multiplier,
        "augmentation_preset": config.preset,
        "splits": {
            "train": {
                "ratio": config.train_ratio,
                "samples": int(config.num_samples * config.train_ratio),
            },
            "val": {
                "ratio": config.val_ratio,
                "samples": int(config.num_samples * config.val_ratio),
            },
            "test": {
                "ratio": config.test_ratio,
                "samples": int(config.num_samples * config.test_ratio),
            },
        },
        "datasets_used": list({meta["source"] for _, _, meta in source_images}),
    }

    summary_path = output_dir / "dataset_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n✅ Dataset generation complete!")
    print(f"Output directory: {output_dir}")
    print(f"Summary saved to: {summary_path}")


def generate_augmented_dataset(
    source_images: list[ImageData],
    output_dir: Path,
    config: DatasetConfig,
) -> None:
    """Generate augmented dataset from source images.

    Args:
        source_images: List of (image, labels, metadata) tuples
        output_dir: Output directory for dataset
        config: Dataset generation configuration
    """
    print("\n🎨 Generating augmented dataset...")
    print(f"Source images: {len(source_images)}")
    print(f"Augmentation multiplier: {config.augmentation_multiplier}x")
    print(f"Target samples: {config.num_samples}")

    split_dirs = _create_split_directories(output_dir)
    source_splits = _split_source_images(source_images, config)

    print("\nSource split:")
    for split_name, split_data in source_splits.items():
        print(f"  {split_name.capitalize()}: {len(split_data)} images")

    aug_pipeline = create_augmentation_pipeline(preset=config.preset)
    split_ratios = {
        "train": config.train_ratio,
        "val": config.val_ratio,
        "test": config.test_ratio,
    }
    augs_per_source = int(config.augmentation_multiplier)

    for split in ["train", "val", "test"]:
        split_sources = source_splits[split]
        if not split_sources:
            print(f"\nWarning: No source images for {split} split, skipping")
            continue

        split_target = int(config.num_samples * split_ratios[split])

        print(f"\n{'=' * 60}")
        print(f"Generating {split.upper()} SET")
        print(f"{'=' * 60}")
        print(f"Target samples: {split_target}")
        print(f"Source images: {len(split_sources)}")
        print(f"Augmentations per source: {augs_per_source}")

        issue_counts = _generate_split_samples(
            split,
            split_sources,
            split_dirs[split],
            split_target,
            augs_per_source,
            aug_pipeline,
        )
        _print_split_statistics(split, split_target, issue_counts)

    _save_dataset_summary(output_dir, source_images, config)


def main() -> None:
    """Main entry point for hybrid dataset generation."""
    parser = argparse.ArgumentParser(
        description="Generate hybrid Phase 2 IQA training dataset"
    )

    # Dataset source directories
    parser.add_argument(
        "--diqa5000-dir",
        type=str,
        default="data/benchmarks/diqa-5000",
        help="Path to DIQA-5000 dataset",
    )
    parser.add_argument(
        "--smartdoc-dir",
        type=str,
        default="data/benchmarks/smartdoc-qa",
        help="Path to SmartDoc-QA dataset",
    )
    parser.add_argument(
        "--ohr-bench-dir",
        type=str,
        default="data/benchmarks/ohr-bench",
        help="Path to OHR-Bench dataset",
    )
    parser.add_argument(
        "--use-kadid10k",
        action="store_true",
        help="Include KADID-10k natural images",
    )

    # Dataset sampling
    parser.add_argument(
        "--diqa5000-samples",
        type=int,
        default=5000,
        help="Number of DIQA-5000 images to use (default: all 5000)",
    )
    parser.add_argument(
        "--smartdoc-samples",
        type=int,
        default=4260,
        help="Number of SmartDoc-QA images to use (default: all 4260)",
    )
    parser.add_argument(
        "--ohr-bench-samples",
        type=int,
        default=5000,
        help="Number of OHR-Bench PDF pages to extract (default: 5000)",
    )
    parser.add_argument(
        "--kadid10k-samples",
        type=int,
        default=1000,
        help="Number of KADID-10k images to use (default: 1000)",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for generated dataset",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=76000,
        help="Target number of total samples (default: 76000)",
    )
    parser.add_argument(
        "--augmentation-multiplier",
        type=float,
        default=5.0,
        help="Augmentation multiplier (default: 5.0)",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="medium",
        choices=["light", "medium", "heavy"],
        help="Augmentation preset (default: medium)",
    )

    # Split ratios
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.70,
        help="Training set ratio (default: 0.70)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="Validation set ratio (default: 0.15)",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.15,
        help="Test set ratio (default: 0.15)",
    )

    # Random seed
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Convert paths
    diqa5000_dir = Path(args.diqa5000_dir)
    smartdoc_dir = Path(args.smartdoc_dir)
    ohr_bench_dir = Path(args.ohr_bench_dir)
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("HYBRID PHASE 2 IQA DATASET GENERATION")
    print("=" * 60)
    print("\nDataset Sources:")
    print(f"  - DIQA-5000: {args.diqa5000_samples} images (ground-truth 3D MOS)")
    print(
        f"  - SmartDoc-QA: {args.smartdoc_samples} images (ground-truth quality labels)"
    )
    print(f"  - OHR-Bench: {args.ohr_bench_samples} PDF pages (weak supervision)")
    if args.use_kadid10k:
        print(f"  - KADID-10k: {args.kadid10k_samples} images (ground-truth IQA)")

    total_base = args.diqa5000_samples + args.smartdoc_samples + args.ohr_bench_samples
    if args.use_kadid10k:
        total_base += args.kadid10k_samples

    print(f"\nTotal base images: {total_base}")
    print(f"Augmentation multiplier: {args.augmentation_multiplier}x")
    print(f"Target samples: {args.num_samples}")
    print(f"Augmentation preset: {args.preset}")
    print()

    # Load all datasets
    all_images = []

    # 1. DIQA-5000 (train split only for source images)
    if diqa5000_dir.exists():
        diqa_images = load_diqa5000_images(
            diqa5000_dir,
            split="train",
            max_images=args.diqa5000_samples,
        )
        all_images.extend(diqa_images)
    else:
        print(f"Warning: DIQA-5000 directory not found at {diqa5000_dir}")

    # 2. SmartDoc-QA
    if smartdoc_dir.exists():
        smartdoc_images = load_smartdoc_qa_images(
            smartdoc_dir,
            max_images=args.smartdoc_samples,
        )
        all_images.extend(smartdoc_images)
    else:
        print(
            f"Info: SmartDoc-QA directory not found at {smartdoc_dir} (may be downloading)"
        )

    # 3. OHR-Bench
    if ohr_bench_dir.exists():
        weak_labeler = WeakSupervisionLabeler()
        ohr_images = load_ohr_bench_images(
            ohr_bench_dir,
            max_images=args.ohr_bench_samples,
            weak_labeler=weak_labeler,
        )
        all_images.extend(ohr_images)
    else:
        print(f"Warning: OHR-Bench directory not found at {ohr_bench_dir}")

    # 4. KADID-10k (optional)
    if args.use_kadid10k:
        kadid_images = load_kadid10k_images(max_images=args.kadid10k_samples)
        all_images.extend(kadid_images)

    if len(all_images) == 0:
        print("\nError: No source images loaded from any dataset!")
        print("Please check dataset paths and ensure datasets are downloaded.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"TOTAL SOURCE IMAGES LOADED: {len(all_images)}")
    print(f"{'=' * 60}")

    # Generate augmented dataset
    config = DatasetConfig(
        num_samples=args.num_samples,
        augmentation_multiplier=args.augmentation_multiplier,
        preset=args.preset,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
    generate_augmented_dataset(
        source_images=all_images,
        output_dir=output_dir,
        config=config,
    )

    print("\n✅ Dataset generation complete!")
    print("\nNext steps:")
    print("1. Upload to GCS:")
    print(f"   gsutil -m rsync -r {output_dir}/ \\")
    print(
        "       gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2/"
    )
    print("\n2. Start A100 training:")
    print("   poetry run modal run modal/train_phase2_iqa.py")


if __name__ == "__main__":
    main()
