#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Process all datasets with the refactored annotation system.

This script provides tiered processing of all 40 datasets using the modular
annotation system. It replaces the legacy subprocess-based incremental wrapper.

Features:
    - Tiered processing by dataset size (smallest first)
    - Checkpoint/resume support via AnnotationOrchestrator
    - Optional YOLO enrichment (disabled by default for speed)
    - Dry-run mode for validation
    - Sample limiting for testing

Processing Tiers:
    1: Small datasets (<10K images): funsd, tobacco800, sroie, etc.
    2: Medium datasets (10K-100K): signatr6k, doclaynet, fintabnet, etc.
    3: Large datasets (100K-500K): rvl_cdip, tablebank, tibhcr
    4: Very large datasets (>500K): pubtabnet, nist_sd19
    5: Multilingual datasets: multilingual_scripts, cc_ocr, mlt19, etc.

Usage:
    # Test with tier 1 first (smallest datasets)
    uv run python scripts/process_all_datasets.py --tier 1 --no-yolo

    # Process all tiers sequentially with resume
    uv run python scripts/process_all_datasets.py --no-yolo --resume

    # Dry run to see what would be processed
    uv run python scripts/process_all_datasets.py --dry-run

    # Process specific dataset with sample limit (for testing)
    uv run python scripts/process_all_datasets.py --dataset funsd --max-samples 50

    # Force reprocessing (ignore existing data)
    uv run python scripts/process_all_datasets.py --tier 1 --no-resume

Example Output:
    Processing Tier 1: 12 datasets (~25K images estimated)
    [1/12] funsd: 149 images processed (169.4 img/s) ✓
    [2/12] tobacco800: 1,290 images processed (158.2 img/s) ✓
    ...

    Tier 1 complete: 24,832 images in 2h 14m
    Total: 24,832 images | 0 errors | 2h 14m

Note:
    YOLO enrichment is disabled by default for faster processing (~169 img/s).
    Enable with --use-yolo for full layout-lite detection (~50 img/s).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from image_preprocessing_detector.annotation import (
        AnnotationOrchestrator,
        DatasetResult,
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Processing Tiers
# =============================================================================

# Tier 1: Small datasets (<10K images) - ~2 hours processing
TIER_1_SMALL: list[str] = [
    "funsd",  # ~149 images
    "funsd_plus",  # ~149 images
    "dibco",  # ~500 images
    "diqa-5000",  # 5,000 images
    "smartdoc-qa",  # ~2,000 images
    "sroie",  # ~1,000 images
    "tobacco800",  # 1,290 images
    "historical_degraded",  # ~500 images
    "realdae",  # ~500 images
    "ocr_quality",  # ~500 images
    "mathverse",  # ~3,000 images
    "multimodal_textbook",  # ~100 images
]

# Tier 2: Medium datasets (10K-100K images) - ~8 hours processing
TIER_2_MEDIUM: list[str] = [
    "signatr6k",  # 6,000 images
    "nist-sd2",  # ~12,000 images
    "nist_sd6",  # ~12,000 images
    "doclaynet",  # ~80,000 images
    "fintabnet",  # ~90,000 images
    "im2latex",  # ~100,000 images
    "maths_handwriting",  # ~10,000 images
]

# Tier 3: Large datasets (100K-500K images) - ~24 hours processing
TIER_3_LARGE: list[str] = [
    "rvl_cdip",  # ~400,000 images
    "tablebank",  # ~145,000 images
    "tibhcr",  # ~200,000 images
]

# Tier 4: Very large datasets (>500K images) - ~48 hours processing
TIER_4_VERY_LARGE: list[str] = [
    "pubtabnet",  # ~568,000 images
    "nist_sd19",  # ~800,000 images
]

# Tier 5: Multilingual/Script datasets - ~12 hours processing
TIER_5_MULTILINGUAL: list[str] = [
    "multilingual_scripts",  # ~50,000 images
    "cc_ocr",  # ~100,000 images
    "mlt19",  # ~10,000 images
    "pucit_ohul",  # ~15,000 images
    "midv500",  # ~15,000 images
    "bhutan_financial",  # ~1,000 images
    "mdiw13",  # ~8,000 images
    "arabic_docs_ocr",  # ~5,000 images
    "hindi_ocr_synthetic",  # ~10,000 images
    "nepali_handwritten",  # ~5,000 images
    "yarmouk_ocr",  # ~3,000 images
    "cvsi",  # ~3,000 images
    "siw13",  # ~1,000 images
    "mle2e",  # ~2,000 images
    "omnidocbench",  # ~2,000 images
    "ohr-bench",  # ~5,000 images
]

# All tiers combined
TIERS: dict[int, list[str]] = {
    1: TIER_1_SMALL,
    2: TIER_2_MEDIUM,
    3: TIER_3_LARGE,
    4: TIER_4_VERY_LARGE,
    5: TIER_5_MULTILINGUAL,
}

# Estimated image counts per tier (approximate)
TIER_ESTIMATES: dict[int, int] = {
    1: 15_000,
    2: 320_000,
    3: 745_000,
    4: 1_368_000,
    5: 235_000,
}


# =============================================================================
# Helper Functions
# =============================================================================


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if td.days:
        return f"{td.days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def format_rate(images: int, seconds: float) -> str:
    """Format processing rate in images per second."""
    if seconds <= 0:
        return "N/A"
    rate = images / seconds
    return f"{rate:.1f} img/s"


def get_tier_datasets(tier: int | None, dataset: str | None) -> list[str]:
    """Get list of datasets to process based on arguments.

    Args:
        tier: Specific tier number (1-5) or None for all
        dataset: Specific dataset name or None

    Returns:
        List of dataset names to process
    """
    if dataset:
        return [dataset]

    if tier is not None:
        if tier not in TIERS:
            logger.error(f"Invalid tier: {tier}. Valid tiers are 1-5.")
            return []
        return TIERS[tier]

    # All tiers in order
    datasets: list[str] = []
    for t in sorted(TIERS.keys()):
        datasets.extend(TIERS[t])
    return datasets


def print_processing_plan(
    datasets: Sequence[str],
    tier: int | None,
    use_yolo: bool,
    max_samples: int | None,
    resume: bool,
) -> None:
    """Print the processing plan before execution."""
    print("\n" + "=" * 60)
    print("ANNOTATION PROCESSING PLAN")
    print("=" * 60)

    if tier is not None:
        print(f"Tier: {tier}")
        est = TIER_ESTIMATES.get(tier, 0)
        print(f"Estimated images: ~{est:,}")
    else:
        total_est = sum(TIER_ESTIMATES.values())
        print(f"Processing all tiers ({len(datasets)} datasets)")
        print(f"Estimated images: ~{total_est:,}")

    print(f"\nDatasets to process: {len(datasets)}")
    print(f"YOLO enrichment: {'Enabled' if use_yolo else 'Disabled'}")
    print(f"Resume mode: {'Enabled' if resume else 'Disabled'}")
    if max_samples:
        print(f"Sample limit: {max_samples} per dataset")

    print("\nDatasets:")
    for i, ds in enumerate(datasets, 1):
        print(f"  {i:2}. {ds}")

    print("=" * 60 + "\n")


def _filter_pending_datasets(
    orchestrator: AnnotationOrchestrator,
    datasets: Sequence[str],
    resume: bool,
) -> list[str]:
    """Filter datasets to only those pending processing (if resume enabled)."""
    if not resume:
        return list(datasets)

    pending = orchestrator.get_pending_datasets()
    datasets_to_process = [d for d in datasets if d in pending]
    skipped = len(datasets) - len(datasets_to_process)
    if skipped > 0:
        logger.info(f"Skipping {skipped} already-completed datasets (resume=True)")
    return datasets_to_process


def _process_single_dataset(
    orchestrator: AnnotationOrchestrator,
    dataset_name: str,
    prefix: str,
    use_yolo: bool,
    max_samples: int | None,
) -> tuple[int, int]:
    """Process one dataset and log results. Returns (images, errors)."""
    start = time.perf_counter()
    result: DatasetResult = orchestrator.process_dataset(
        dataset_name,
        use_yolo=use_yolo,
        max_samples=max_samples,
    )
    elapsed = time.perf_counter() - start

    status = "+" if result.success else "x"
    rate = format_rate(result.samples_processed, elapsed)
    logger.info(
        f"{prefix} {dataset_name}: {result.samples_processed:,} images "
        f"({rate}) {status}"
    )

    if result.errors:
        for err in result.errors[:3]:
            logger.warning(f"  Error: {err}")

    errors = result.samples_failed
    if not result.success and errors == 0:
        errors = max(len(result.errors), 1)
    return result.samples_processed, errors


def process_tier(
    orchestrator: AnnotationOrchestrator,
    datasets: Sequence[str],
    tier: int | None,
    use_yolo: bool,
    max_samples: int | None,
    resume: bool,
    dry_run: bool,
) -> tuple[int, int, float]:
    """Process a list of datasets.

    Args:
        orchestrator: Configured AnnotationOrchestrator
        datasets: List of dataset names to process
        tier: Tier number for display (or None)
        use_yolo: Whether to use YOLO enrichment
        max_samples: Optional sample limit per dataset
        resume: Whether to skip already-completed datasets
        dry_run: If True, only show what would be processed

    Returns:
        Tuple of (total_images, total_errors, total_seconds)
    """
    if dry_run:
        print_processing_plan(datasets, tier, use_yolo, max_samples, resume)
        return 0, 0, 0.0

    datasets_to_process = _filter_pending_datasets(orchestrator, datasets, resume)
    if not datasets_to_process:
        logger.info("No datasets to process (all completed)")
        return 0, 0, 0.0

    tier_label = f"Tier {tier}" if tier else "All datasets"
    print(f"\n{'=' * 60}")
    print(f"Processing {tier_label}: {len(datasets_to_process)} datasets")
    print("=" * 60 + "\n")

    tier_start = time.perf_counter()
    total_images = 0
    total_errors = 0

    for i, dataset_name in enumerate(datasets_to_process, 1):
        prefix = f"[{i}/{len(datasets_to_process)}]"
        logger.info(f"{prefix} Processing {dataset_name}...")
        images, errors = _process_single_dataset(
            orchestrator,
            dataset_name,
            prefix,
            use_yolo,
            max_samples,
        )
        total_images += images
        total_errors += errors

    tier_elapsed = time.perf_counter() - tier_start
    print(
        f"\n{tier_label} complete: {total_images:,} images in {format_duration(tier_elapsed)}"
    )

    return total_images, total_errors, tier_elapsed


# =============================================================================
# Main Entry Point
# =============================================================================


def main(args: argparse.Namespace) -> int:
    """Main processing function.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    # Add project root to path for imports
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from image_preprocessing_detector.annotation import create_orchestrator

    # Get datasets to process
    datasets = get_tier_datasets(args.tier, args.dataset)
    if not datasets:
        return 1

    # Dry run mode
    if args.dry_run:
        print_processing_plan(
            datasets, args.tier, args.use_yolo, args.max_samples, args.resume
        )
        return 0

    # Create orchestrator
    logger.info("Initializing annotation orchestrator...")
    orchestrator = create_orchestrator(use_yolo=args.use_yolo)
    logger.info("Orchestrator ready")

    # Process datasets
    total_start = time.perf_counter()

    if args.tier is not None:
        # Single tier
        total_images, total_errors, _ = process_tier(
            orchestrator,
            datasets,
            args.tier,
            args.use_yolo,
            args.max_samples,
            args.resume,
            args.dry_run,
        )
    elif args.dataset:
        # Single dataset
        total_images, total_errors, _ = process_tier(
            orchestrator,
            datasets,
            None,
            args.use_yolo,
            args.max_samples,
            args.resume,
            args.dry_run,
        )
    else:
        # All tiers
        total_images = 0
        total_errors = 0
        for tier_num in sorted(TIERS.keys()):
            tier_datasets = TIERS[tier_num]
            images, errors, _ = process_tier(
                orchestrator,
                tier_datasets,
                tier_num,
                args.use_yolo,
                args.max_samples,
                args.resume,
                args.dry_run,
            )
            total_images += images
            total_errors += errors

    total_elapsed = time.perf_counter() - total_start

    # Final summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total images: {total_images:,}")
    print(f"Total errors: {total_errors:,}")
    print(f"Total time: {format_duration(total_elapsed)}")
    if total_images > 0:
        print(f"Average rate: {format_rate(total_images, total_elapsed)}")
    print("=" * 60 + "\n")

    return 0 if total_errors == 0 else 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Process all datasets with the annotation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process tier 1 (smallest datasets) without YOLO
    %(prog)s --tier 1 --no-yolo

    # Process all tiers with resume
    %(prog)s --no-yolo --resume

    # Process single dataset with sample limit
    %(prog)s --dataset funsd --max-samples 50

    # Dry run to see processing plan
    %(prog)s --dry-run
        """,
    )

    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Process specific tier (1=small, 2=medium, 3=large, 4=very large, 5=multilingual)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Process specific dataset by name",
    )
    parser.add_argument(
        "--use-yolo",
        action="store_true",
        default=False,
        help="Enable YOLO enrichment (slower, ~50 img/s). Default: disabled.",
    )
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Explicitly disable YOLO enrichment (default)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Skip already-completed datasets (default: True)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Reprocess all datasets, ignoring previous completion status",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        help="Maximum samples per dataset (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show processing plan without executing",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Handle no-* flags
    if args.no_yolo:
        args.use_yolo = False
    if args.no_resume:
        args.resume = False

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    return args


if __name__ == "__main__":
    sys.exit(main(parse_args()))
