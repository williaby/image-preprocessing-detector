#!/usr/bin/env python3
"""Convert COCO-Text HuggingFace dataset to JPG files for parser compatibility.

This script extracts all images from the COCO-Text HuggingFace dataset (stored in
Parquet format) and saves them as JPG files with COCO naming convention.

Usage:
    uv run python scripts/convert_cocotext_parquet.py \\
        --output-dir /mnt/e/image_detection/01_base_data/language/cocotext \\
        --num-workers 8 \\
        --batch-size 100

Requirements:
    - HuggingFace datasets library
    - Pillow (PIL)
    - ~25 GB disk space available

Expected Output:
    - 63,686 JPG files in COCO naming format: COCO_{split}_{image_id:012d}.jpg
    - ~20 GB total storage
    - Runtime: 30-60 minutes (parallel) or 2-4 hours (single-threaded)
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_huggingface_dataset():
    """Load COCO-Text dataset from HuggingFace with multiple name attempts."""
    from datasets import load_dataset

    dataset_names = [
        "cocotext",
        "coco-text",
        "coco_text",
        "cocotext-v2",
        "nielsr/COCO-Text",  # Sometimes datasets are user-namespaced
    ]

    for name in dataset_names:
        try:
            logger.info(f"Attempting to load dataset: {name}")
            dataset = load_dataset(name)
            logger.info(f"✅ Successfully loaded dataset: {name}")
            return dataset, name
        except Exception as e:
            logger.debug(f"Failed to load '{name}': {e}")
            continue

    logger.error("❌ Failed to load COCO-Text dataset with any known name")
    logger.error("Tried names: " + ", ".join(dataset_names))
    sys.exit(1)


def get_coco_filename(example: dict) -> tuple[str | None, str | None]:
    """Generate COCO filename from example metadata.

    Returns:
        Tuple of (filename, error_message). If successful, error_message is None.
    """
    try:
        # Try different field names for image_id
        image_id = example.get("image_id") or example.get("id")
        if image_id is None:
            return None, "Missing image_id field"

        # Determine split for COCO naming convention
        split = example.get("set", example.get("split", "train"))

        # Map to COCO split names (train2014/val2014)
        if split in ["val", "test"]:
            coco_split = "val2014"
        else:
            coco_split = "train2014"

        # COCO filename pattern: COCO_train2014_000000123456.jpg
        filename = f"COCO_{coco_split}_{int(image_id):012d}.jpg"
        return filename, None

    except Exception as e:
        return None, f"Filename generation error: {e}"


def save_image(
    example: dict, output_dir: Path, skip_existing: bool = True
) -> tuple[str, bool, str | None]:
    """Save single image from HuggingFace example.

    Args:
        example: HuggingFace dataset example
        output_dir: Output directory path
        skip_existing: Skip if file already exists

    Returns:
        Tuple of (filename, success, error_message)
    """
    try:
        filename, error = get_coco_filename(example)
        if filename is None:
            return "unknown", False, error

        output_path = output_dir / filename

        # Skip if already exists (resume capability)
        if skip_existing and output_path.exists():
            return filename, True, None

        # Get image from example (should be PIL Image)
        image = example.get("image")
        if image is None:
            return filename, False, "No image field in example"

        # Save as JPG with high quality
        image.save(output_path, "JPEG", quality=95, optimize=True)
        return filename, True, None

    except Exception as e:
        image_id = example.get("image_id", "unknown")
        return str(image_id), False, f"Save error: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Convert COCO-Text HuggingFace dataset to filesystem JPG files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="/mnt/e/image_detection/01_base_data/language/cocotext",
        help="Output directory for JPG files",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=8,
        help="Number of parallel workers (default: 8)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip already converted images (enables resume)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for progress updates (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show what would be done without writing files",
    )
    args = parser.parse_args()

    # Create output directory
    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {args.output_dir}")
    else:
        logger.info("DRY RUN MODE - no files will be written")

    # Load HuggingFace dataset
    logger.info("Loading COCO-Text dataset from HuggingFace...")
    dataset, dataset_name = load_huggingface_dataset()

    # Count total images
    total_images = sum(len(dataset[split]) for split in dataset.keys())
    logger.info(f"Found {total_images:,} total images across {len(dataset)} splits")

    for split_name in dataset.keys():
        logger.info(f"  - {split_name}: {len(dataset[split_name]):,} images")

    # Check disk space (rough estimate: 320 KB per image average)
    estimated_size_gb = (total_images * 320 * 1024) / (1024**3)
    logger.info(f"Estimated storage required: ~{estimated_size_gb:.1f} GB")

    if args.dry_run:
        logger.info("Dry run complete - exiting without conversion")
        sys.exit(0)

    # Collect all examples from all splits
    logger.info("Collecting examples from all splits...")
    all_examples = []
    for split_name, split_data in dataset.items():
        logger.info(f"Processing split: {split_name} ({len(split_data):,} images)")
        all_examples.extend(list(split_data))

    logger.info(f"Total examples collected: {len(all_examples):,}")

    # Process with parallel workers
    success_count = 0
    fail_count = 0
    skip_count = 0
    errors: dict[str, int] = {}

    logger.info(f"Starting conversion with {args.num_workers} workers...")

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(save_image, example, args.output_dir, args.skip_existing)
            for example in all_examples
        ]

        # Progress tracking with tqdm
        with tqdm(total=len(futures), desc="Converting images", unit="img") as pbar:
            for future in as_completed(futures):
                filename, success, error = future.result()

                if success:
                    if args.skip_existing and (args.output_dir / filename).exists():
                        skip_count += 1
                    else:
                        success_count += 1
                else:
                    fail_count += 1
                    # Track error types
                    error_type = error.split(":")[0] if error else "Unknown"
                    errors[error_type] = errors.get(error_type, 0) + 1

                    # Log first few errors for debugging
                    if fail_count <= 10:
                        logger.warning(f"Failed: {filename} - {error}")

                pbar.update(1)

                # Update progress display
                pbar.set_postfix(
                    {
                        "success": success_count,
                        "skipped": skip_count,
                        "failed": fail_count,
                    }
                )

    # Final statistics
    logger.info("=" * 80)
    logger.info("Conversion Complete!")
    logger.info(f"  ✅ Successfully converted: {success_count:,} images")
    if skip_count > 0:
        logger.info(f"  ⏭️  Skipped (existing):    {skip_count:,} images")
    if fail_count > 0:
        logger.warning(f"  ❌ Failed:               {fail_count:,} images")
        logger.warning("  Error breakdown:")
        for error_type, count in sorted(
            errors.items(), key=lambda x: x[1], reverse=True
        ):
            logger.warning(f"    - {error_type}: {count} images")

    # Verify output
    jpg_count = len(list(args.output_dir.glob("*.jpg")))
    logger.info(f"  📁 Total JPG files:      {jpg_count:,}")

    if jpg_count < total_images:
        missing = total_images - jpg_count
        logger.warning(f"  ⚠️  Missing images:       {missing:,}")
    else:
        logger.info("  ✅ All images converted successfully!")

    # Show sample filenames
    sample_files = list(args.output_dir.glob("COCO_*.jpg"))[:5]
    if sample_files:
        logger.info("Sample filenames:")
        for f in sample_files:
            logger.info(f"    {f.name}")

    logger.info("=" * 80)

    # Exit code based on success
    if fail_count > 0:
        logger.error(f"Conversion completed with {fail_count} failures")
        sys.exit(1)
    else:
        logger.info("Conversion completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
