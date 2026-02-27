#!/usr/bin/env python3
"""
Generate Combined Document Classification Labels (FR-2.1) via Weak Supervision

Combines two datasets for balanced class coverage:
1. DocLayNet: Born-digital and hybrid documents (scientific PDFs)
2. RVL-CDIP: Scanned/image-only documents (tobacco litigation scans)

Target distribution:
- image_only: 33% (from RVL-CDIP)
- born_digital: 33% (from DocLayNet)
- hybrid: 33% (from DocLayNet)

This provides balanced training data across all three document types.

Usage:
    # Generate balanced dataset with 15,000 samples (5K per class)
    python scripts/generate_combined_classification_labels.py \\
        --doclaynet-dir /path/to/doclaynet \\
        --rvl-cdip-dir /path/to/rvl-cdip \\
        --output-dir data/training/document_classification \\
        --samples-per-class 5000 \\
        --split train

Note: RVL-CDIP requires legal review from UCSF for commercial use.
See: https://www.cs.cmu.edu/~aharley/rvl-cdip/
"""

import argparse
import json
import logging
import random  # nosec B311 - used for non-cryptographic dataset sampling
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# DocLayNet class mapping
DOCLAYNET_CLASSES = {
    1: "Caption",
    2: "Footnote",
    3: "Formula",
    4: "List",
    5: "Page-footer",
    6: "Page-header",
    7: "Picture",
    8: "Section-header",
    9: "Table",
    10: "Text",
    11: "Title",
}

TEXT_CLASSES = {1, 2, 3, 4, 5, 6, 8, 9, 10, 11}  # All except Picture
IMAGE_CLASSES = {7}  # Picture only


def load_doclaynet_annotations(coco_path: Path) -> dict:
    """Load DocLayNet COCO annotations."""
    logger.info(f"Loading DocLayNet annotations from {coco_path}...")
    with open(coco_path) as f:
        coco_data = json.load(f)
    logger.info(
        f"Loaded {len(coco_data.get('images', []))} images, "
        f"{len(coco_data.get('annotations', []))} annotations"
    )
    return coco_data


def classify_doclaynet_page(
    image_id: int, annotations: list[dict]
) -> tuple[str, dict[str, int]]:
    """
    Classify DocLayNet page as born_digital or hybrid.

    Returns:
        Tuple of (classification, class_counts)
    """
    class_counts = defaultdict(int)
    has_text = False
    has_images = False

    for ann in annotations:
        if ann["image_id"] != image_id:
            continue

        category_id = ann["category_id"]
        class_name = DOCLAYNET_CLASSES.get(category_id, "Unknown")
        class_counts[class_name] += 1

        if category_id in TEXT_CLASSES:
            has_text = True
        if category_id in IMAGE_CLASSES:
            has_images = True

    # DocLayNet pages are always born_digital or hybrid (never image_only)
    if has_text and has_images:
        return "hybrid", dict(class_counts)
    return "born_digital", dict(class_counts)


def sample_doclaynet_by_class(
    doclaynet_dir: Path,
    split: str,
    born_digital_count: int,
    hybrid_count: int,
) -> list[dict]:
    """
    Sample DocLayNet pages by target class counts.

    Args:
        doclaynet_dir: Path to DocLayNet dataset
        split: Dataset split (train/val/test)
        born_digital_count: Number of born_digital samples to extract
        hybrid_count: Number of hybrid samples to extract

    Returns:
        List of classification entries
    """
    coco_path = doclaynet_dir / "ground_truth" / "coco" / f"{split}.json"
    if not coco_path.exists():
        raise FileNotFoundError(f"DocLayNet COCO not found: {coco_path}")

    coco_data = load_doclaynet_annotations(coco_path)

    # Group annotations by image
    image_annotations = defaultdict(list)
    for ann in coco_data["annotations"]:
        image_annotations[ann["image_id"]].append(ann)

    # Classify all pages
    born_digital_pages = []
    hybrid_pages = []

    logger.info("Classifying DocLayNet pages...")
    for img in tqdm(coco_data["images"], desc="Classifying DocLayNet"):
        image_id = img["id"]
        anns = image_annotations.get(image_id, [])
        classification, class_counts = classify_doclaynet_page(image_id, anns)

        entry = {
            "image_id": image_id,
            "file_name": img["file_name"],
            "doc_name": img.get("doc_name", Path(img["file_name"]).stem),
            "classification": classification,
            "source": "doclaynet",
            "layout_elements": class_counts,
            "width": img.get("width", 0),
            "height": img.get("height", 0),
        }

        if classification == "born_digital":
            born_digital_pages.append(entry)
        else:
            hybrid_pages.append(entry)

    logger.info(
        f"DocLayNet: {len(born_digital_pages)} born_digital, {len(hybrid_pages)} hybrid"
    )

    # Sample requested counts (deterministic with fixed seed for reproducibility)
    random.seed(42)  # nosec B311 - fixed seed for reproducible dataset sampling
    sampled_born_digital = random.sample(  # nosec B311
        born_digital_pages, min(born_digital_count, len(born_digital_pages))
    )
    sampled_hybrid = random.sample(  # nosec B311
        hybrid_pages, min(hybrid_count, len(hybrid_pages))
    )

    return sampled_born_digital + sampled_hybrid


def sample_rvl_cdip(
    rvl_cdip_dir: Path, split: str, image_only_count: int
) -> list[dict]:
    """
    Sample RVL-CDIP images (all are image_only/scanned documents).

    Args:
        rvl_cdip_dir: Path to RVL-CDIP dataset
        split: Dataset split (train/val/test)
        image_only_count: Number of image_only samples to extract

    Returns:
        List of classification entries
    """
    # RVL-CDIP structure: images/{split}/ + labels/{split}.txt
    split_map = {"train": "train", "val": "val", "test": "test"}
    rvl_split = split_map.get(split, split)

    labels_file = rvl_cdip_dir / "labels" / f"{rvl_split}.txt"
    if not labels_file.exists():
        raise FileNotFoundError(f"RVL-CDIP labels not found: {labels_file}")

    logger.info(f"Loading RVL-CDIP {rvl_split} split...")

    # Load image paths from labels file
    # Format: path/to/image.tif class_id
    image_entries = []
    with open(labels_file) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2:
                continue

            image_path, class_id = parts
            image_entries.append(
                {
                    "file_name": image_path,
                    "classification": "image_only",
                    "source": "rvl-cdip",
                    "rvl_cdip_class": int(class_id),
                    "layout_elements": {},
                    "width": 0,  # Unknown without loading image
                    "height": 0,
                }
            )

    logger.info(f"RVL-CDIP: {len(image_entries)} image_only samples available")

    # Sample requested count (deterministic with fixed seed for reproducibility)
    random.seed(42)  # nosec B311 - fixed seed for reproducible dataset sampling
    sampled = random.sample(  # nosec B311
        image_entries, min(image_only_count, len(image_entries))
    )

    return sampled


def generate_combined_classification_labels(
    doclaynet_dir: Path,
    rvl_cdip_dir: Path,
    output_dir: Path,
    split: str = "train",
    samples_per_class: int = 5000,
) -> None:
    """
    Generate combined document classification labels.

    Args:
        doclaynet_dir: Path to DocLayNet dataset
        rvl_cdip_dir: Path to RVL-CDIP dataset (optional, can be None)
        output_dir: Output directory
        split: Dataset split (train/val/test)
        samples_per_class: Target samples per class (default: 5000)
    """
    logger.info(
        f"Generating combined classification labels for {split} split "
        f"({samples_per_class} samples per class)..."
    )

    classifications = []

    # Sample from DocLayNet (born_digital + hybrid)
    logger.info("Sampling DocLayNet pages...")
    doclaynet_samples = sample_doclaynet_by_class(
        doclaynet_dir, split, samples_per_class, samples_per_class
    )
    classifications.extend(doclaynet_samples)

    # Sample from RVL-CDIP (image_only) if available
    if rvl_cdip_dir and rvl_cdip_dir.exists():
        logger.info("Sampling RVL-CDIP images...")
        try:
            rvl_cdip_samples = sample_rvl_cdip(rvl_cdip_dir, split, samples_per_class)
            classifications.extend(rvl_cdip_samples)
        except FileNotFoundError as e:
            logger.warning(f"RVL-CDIP sampling failed: {e}")
            logger.warning("Proceeding with DocLayNet only (no image_only samples)")
    else:
        logger.warning("RVL-CDIP directory not provided or not found")
        logger.warning("Proceeding with DocLayNet only (no image_only samples)")

    # Compute class distribution
    class_distribution = defaultdict(int)
    for entry in classifications:
        class_distribution[entry["classification"]] += 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output JSON
    output_data = {
        "info": {
            "description": "Combined document classification labels (DocLayNet + RVL-CDIP)",
            "version": "1.0",
            "split": split,
            "total_documents": len(classifications),
            "classification_method": "weak_supervision",
            "sources": ["doclaynet", "rvl-cdip"],
        },
        "classes": ["image_only", "born_digital", "hybrid"],
        "class_distribution": dict(class_distribution),
        "classifications": classifications,
    }

    # Write output
    output_file = output_dir / f"{split}_combined_classification.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✓ Generated {len(classifications)} combined classification labels")
    logger.info(f"✓ Output: {output_file}")
    logger.info("\nClass distribution:")
    for cls in ["image_only", "born_digital", "hybrid"]:
        count = class_distribution.get(cls, 0)
        pct = count / len(classifications) * 100 if len(classifications) > 0 else 0
        logger.info(f"  - {cls}: {count:,} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate combined document classification labels"
    )
    parser.add_argument(
        "--doclaynet-dir",
        type=Path,
        default=Path("data/benchmarks/doclaynet"),
        help="Path to DocLayNet dataset directory",
    )
    parser.add_argument(
        "--rvl-cdip-dir",
        type=Path,
        default=None,
        help="Path to RVL-CDIP dataset directory (optional)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/document_classification"),
        help="Output directory for classification labels",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "val", "test"],
        help="Dataset split to process",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=5000,
        help="Target samples per class (default: 5000, total 15K)",
    )

    args = parser.parse_args()

    # Resolve symlinks
    doclaynet_dir = args.doclaynet_dir.resolve()
    if not doclaynet_dir.exists():
        raise FileNotFoundError(f"DocLayNet directory not found: {doclaynet_dir}")

    rvl_cdip_dir = args.rvl_cdip_dir.resolve() if args.rvl_cdip_dir else None

    generate_combined_classification_labels(
        doclaynet_dir,
        rvl_cdip_dir,
        args.output_dir,
        args.split,
        args.samples_per_class,
    )


if __name__ == "__main__":
    main()
