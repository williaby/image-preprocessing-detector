#!/usr/bin/env python3
"""Create symlinks for COCO-Text images to enable parser compatibility.

The COCO images are stored in train2014/ and val2014/ subdirectories, but the
parser expects a flat directory structure. This script creates symlinks without
duplicating the ~20GB of image data.

Usage:
    uv run python scripts/setup_cocotext_symlinks.py \\
        --source /mnt/e/image_detection/01_base_data/text_detection/cocotext/images \\
        --target /mnt/e/image_detection/01_base_data/language/cocotext

This creates:
    /mnt/e/image_detection/01_base_data/language/cocotext/COCO_train2014_*.jpg -> ../../text_detection/cocotext/images/train2014/COCO_train2014_*.jpg
    /mnt/e/image_detection/01_base_data/language/cocotext/COCO_val2014_*.jpg -> ../../text_detection/cocotext/images/val2014/COCO_val2014_*.jpg
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_required_images(annotation_path: Path) -> set[str]:
    """Load list of images actually used in COCO-Text annotations.

    Args:
        annotation_path: Path to cocotext.v2.json

    Returns:
        Set of filenames (e.g., "COCO_train2014_000000123456.jpg")
    """
    logger.info(f"Loading annotations from {annotation_path}")

    with open(annotation_path, encoding="utf-8") as f:
        data = json.load(f)

    required = set()
    for img_id, img_info in data["imgs"].items():
        filename = img_info.get("file_name")
        if filename:
            required.add(filename)

    logger.info(f"Found {len(required):,} images in annotations")
    return required


def find_source_images(source_dir: Path) -> dict[str, Path]:
    """Find all COCO images in source directory structure.

    Args:
        source_dir: Directory containing train2014/ and val2014/ subdirs

    Returns:
        Dict mapping filename -> full path
    """
    logger.info(f"Scanning source directory: {source_dir}")

    source_images = {}

    # Scan train2014 and val2014 subdirectories
    for subdir_name in ["train2014", "val2014"]:
        subdir = source_dir / subdir_name
        if not subdir.exists():
            logger.warning(f"Subdirectory not found: {subdir}")
            continue

        logger.info(f"Scanning {subdir_name}/...")
        for img_path in subdir.glob("COCO_*.jpg"):
            source_images[img_path.name] = img_path

    logger.info(f"Found {len(source_images):,} total source images")
    return source_images


def create_symlinks(
    required: set[str],
    source_images: dict[str, Path],
    target_dir: Path,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Create symlinks for required images.

    Args:
        required: Set of required filenames from annotations
        source_images: Dict mapping filename -> source path
        target_dir: Target directory for symlinks
        dry_run: If True, don't create symlinks

    Returns:
        Tuple of (created, skipped, missing)
    """
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    missing = 0

    logger.info(f"Creating symlinks in {target_dir}...")

    for filename in tqdm(sorted(required), desc="Creating symlinks", unit="file"):
        target_path = target_dir / filename

        # Skip if already exists
        if target_path.exists():
            skipped += 1
            continue

        # Check if source exists
        if filename not in source_images:
            logger.warning(f"Missing source image: {filename}")
            missing += 1
            continue

        source_path = source_images[filename]

        # Create relative symlink
        if not dry_run:
            try:
                # Calculate relative path from target to source
                # target: /mnt/e/.../language/cocotext/COCO_*.jpg
                # source: /mnt/e/.../text_detection/cocotext/images/train2014/COCO_*.jpg
                # relative: ../../text_detection/cocotext/images/train2014/COCO_*.jpg
                rel_path = (
                    Path("../../text_detection/cocotext/images")
                    / source_path.parent.name
                    / source_path.name
                )
                target_path.symlink_to(rel_path)
                created += 1
            except Exception as e:
                logger.error(f"Failed to create symlink for {filename}: {e}")
                missing += 1
        else:
            created += 1

    return created, skipped, missing


def main():
    parser = argparse.ArgumentParser(
        description="Create symlinks for COCO-Text images in flat directory structure"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default="/mnt/e/image_detection/01_base_data/text_detection/cocotext/images",
        help="Source directory with train2014/ and val2014/ subdirectories",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default="/mnt/e/image_detection/01_base_data/language/cocotext",
        help="Target directory for flat symlink structure",
    )
    parser.add_argument(
        "--annotation",
        type=Path,
        default="/mnt/e/image_detection/01_base_data/text_detection/cocotext/cocotext.v2.json",
        help="Path to cocotext.v2.json annotation file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show what would be done without creating symlinks",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing target directory before creating symlinks",
    )
    args = parser.parse_args()

    # Validate inputs
    if not args.source.exists():
        logger.error(f"Source directory not found: {args.source}")
        sys.exit(1)

    if not args.annotation.exists():
        logger.error(f"Annotation file not found: {args.annotation}")
        sys.exit(1)

    if args.dry_run:
        logger.info("DRY RUN MODE - no files will be modified")

    # Load required images from annotations
    required = load_required_images(args.annotation)

    # Find source images
    source_images = find_source_images(args.source)

    # Check coverage
    available = len([f for f in required if f in source_images])
    logger.info(f"Coverage: {available:,}/{len(required):,} images available")

    if available < len(required):
        missing_count = len(required) - available
        logger.warning(f"{missing_count:,} images from annotations not found in source")

    # Handle existing target directory
    if args.target.exists():
        if args.force:
            if not args.dry_run:
                import shutil

                logger.warning(f"Removing existing target directory: {args.target}")
                shutil.rmtree(args.target)
        else:
            logger.info(f"Target directory exists: {args.target} (will skip existing)")

    # Create symlinks
    created, skipped, missing = create_symlinks(
        required, source_images, args.target, args.dry_run
    )

    # Report results
    logger.info("=" * 80)
    logger.info("Symlink Creation Complete!")
    logger.info(f"  ✅ Created:  {created:,} symlinks")
    if skipped > 0:
        logger.info(f"  ⏭️  Skipped:  {skipped:,} (already exist)")
    if missing > 0:
        logger.warning(f"  ❌ Missing:  {missing:,} (source not found)")

    # Verify
    if not args.dry_run:
        actual_links = len(list(args.target.glob("COCO_*.jpg")))
        logger.info(f"  📁 Total files in target: {actual_links:,}")

        if actual_links >= len(required):
            logger.info("  ✅ All required images available!")
        else:
            missing_final = len(required) - actual_links
            logger.warning(f"  ⚠️  Still missing: {missing_final:,} images")
    logger.info("=" * 80)

    if missing > 0:
        sys.exit(1)
    else:
        logger.info("Success!")
        sys.exit(0)


if __name__ == "__main__":
    main()
