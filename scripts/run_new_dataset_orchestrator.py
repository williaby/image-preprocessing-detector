#!/usr/bin/env python3
"""Run annotation orchestrator on newly onboarded datasets.

Processes: document-haystack, drccbi, staindoc, markushgrapher, indicdlp
Skips: q-doc (no images available)

Usage:
    PYTHONPATH=. uv run python scripts/run_new_dataset_orchestrator.py
    PYTHONPATH=. uv run python scripts/run_new_dataset_orchestrator.py --dataset drccbi
    PYTHONPATH=. uv run python scripts/run_new_dataset_orchestrator.py --max-samples 100
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

NEW_DATASETS = [
    "document-haystack",
    "drccbi",
    "staindoc",
    "markushgrapher",
    "indicdlp",
]

SKIP_DATASETS = [
    "q-doc",  # No images available (code-only repo)
]


def main() -> int:
    """Run orchestrator on new datasets."""
    parser = argparse.ArgumentParser(description="Run orchestrator on new datasets")
    parser.add_argument(
        "--dataset",
        type=str,
        help="Process only this dataset (default: all new datasets)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limit samples per dataset (default: no limit)",
    )
    parser.add_argument(
        "--use-yolo",
        action="store_true",
        default=False,
        help="Enable YOLO enrichment (default: off for base annotation)",
    )
    args = parser.parse_args()

    datasets = [args.dataset] if args.dataset else NEW_DATASETS

    # Validate datasets
    from image_preprocessing_detector.annotation.config.datasets import DATASET_CONFIGS

    for name in datasets:
        if name not in DATASET_CONFIGS:
            logger.error("Unknown dataset: %s", name)
            return 1

    # Create orchestrator
    from image_preprocessing_detector.annotation.config.settings import (
        AnnotationSettings,
    )
    from image_preprocessing_detector.annotation.workflow.orchestrator import (
        create_orchestrator,
    )

    settings = AnnotationSettings(
        e_drive_root=Path("/mnt/e/image_detection"),
        metadata_root=Path("/mnt/e/image_detection/metadata_registry"),
        checkpoint_dir=Path("/mnt/e/image_detection/metadata_registry/.checkpoints"),
    )

    logger.info("Creating orchestrator (use_yolo=%s)...", args.use_yolo)
    orchestrator = create_orchestrator(settings=settings, use_yolo=args.use_yolo)

    # Process each dataset
    results = []
    for dataset_name in datasets:
        if dataset_name in SKIP_DATASETS:
            logger.info("Skipping %s (no images available)", dataset_name)
            continue

        logger.info("=" * 60)
        logger.info("Processing: %s", dataset_name)
        logger.info("=" * 60)

        result = orchestrator.process_dataset(
            dataset_name=dataset_name,
            use_yolo=args.use_yolo,
            max_samples=args.max_samples,
        )

        status = "SUCCESS" if result.success else "FAILED"
        logger.info(
            "%s: %s - %d samples processed, %d failed (%.1fs)",
            dataset_name,
            status,
            result.samples_processed,
            result.samples_failed,
            result.duration_seconds,
        )
        if result.errors:
            for err in result.errors[:5]:
                logger.warning("  Error: %s", err[:200])

        results.append(result)

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    total_processed = 0
    total_failed = 0
    for r in results:
        status = "OK" if r.success else "FAIL"
        logger.info(
            "  [%s] %s: %d processed, %d failed",
            status,
            r.dataset_name,
            r.samples_processed,
            r.samples_failed,
        )
        total_processed += r.samples_processed
        total_failed += r.samples_failed

    logger.info("Total: %d processed, %d failed", total_processed, total_failed)
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
