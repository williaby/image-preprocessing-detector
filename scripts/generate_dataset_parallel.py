#!/usr/bin/env python3
"""Parallel synthetic dataset generation script.

Generates 250K multi-script document samples using hybrid augmentation
(Augraphy for document effects + Albumentations for capture effects).

Usage:
    python scripts/generate_dataset_parallel.py --workers 2 --samples 250000

This script is designed to run overnight with limited resource usage.
"""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.synthetic.config import SCRIPT_CONFIGS
from image_preprocessing_detector.synthetic.generator import (
    GenerationConfig,
    MultiScriptDocumentGenerator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dataset_generation.log"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class WorkerTask:
    """Task for a worker process."""

    worker_id: int
    samples_to_generate: int
    seed: int
    output_dir: Path
    scripts: list[str]


@dataclass
class WorkerResult:
    """Result from a worker process."""

    worker_id: int
    samples_generated: int
    samples_failed: int
    elapsed_seconds: float
    errors: list[str]


def generate_worker(task: WorkerTask) -> WorkerResult:
    """Worker function for parallel generation.

    Each worker runs in a separate process with its own generator instance.

    Args:
        task: WorkerTask with generation parameters

    Returns:
        WorkerResult with generation statistics
    """
    start_time = time.time()
    errors: list[str] = []

    # Create worker-specific output directory
    worker_dir = task.output_dir / f"worker_{task.worker_id}"
    worker_dir.mkdir(parents=True, exist_ok=True)

    # Configure generator for this worker
    config = GenerationConfig(
        scripts=task.scripts,
        samples_per_script=task.samples_to_generate // len(task.scripts) + 1,
        output_dir=worker_dir,
        save_images=True,
        save_metadata=True,
        image_format="png",
        seed=task.seed,
        augmenter="hybrid",  # Use hybrid augmentation
    )

    generator = MultiScriptDocumentGenerator(config)

    # Initialize (load corpus from cache, scan fonts)
    logger.info(f"Worker {task.worker_id}: Initializing generator...")
    if not generator.initialize(download_corpus=False, scan_fonts=True):
        errors.append("Failed to initialize generator")
        return WorkerResult(
            worker_id=task.worker_id,
            samples_generated=0,
            samples_failed=0,
            elapsed_seconds=time.time() - start_time,
            errors=errors,
        )

    # Generate samples
    samples_generated = 0
    samples_failed = 0
    last_progress_report = time.time()
    progress_interval = 60  # Report every 60 seconds

    logger.info(
        f"Worker {task.worker_id}: Starting generation of {task.samples_to_generate} samples..."
    )

    try:
        for _ in generator.generate():
            samples_generated += 1

            # Progress reporting
            now = time.time()
            if now - last_progress_report > progress_interval:
                elapsed = now - start_time
                rate = samples_generated / elapsed
                remaining = (task.samples_to_generate - samples_generated) / rate
                logger.info(
                    f"Worker {task.worker_id}: {samples_generated}/{task.samples_to_generate} "
                    f"({samples_generated / task.samples_to_generate * 100:.1f}%) - "
                    f"{rate:.1f} samples/sec - ETA: {remaining / 60:.0f} min"
                )
                last_progress_report = now

            # Stop when we have enough
            if samples_generated >= task.samples_to_generate:
                break

    except Exception as e:
        logger.error(f"Worker {task.worker_id}: Generation error: {e}")
        errors.append(str(e))

    # Get final stats
    stats = generator.get_statistics()
    samples_failed = stats.failed_samples
    errors.extend(stats.errors)

    elapsed = time.time() - start_time
    logger.info(
        f"Worker {task.worker_id}: Completed - {samples_generated} samples in {elapsed / 60:.1f} min"
    )

    return WorkerResult(
        worker_id=task.worker_id,
        samples_generated=samples_generated,
        samples_failed=samples_failed,
        elapsed_seconds=elapsed,
        errors=errors,
    )


def merge_worker_outputs(output_dir: Path, num_workers: int) -> dict[str, Any]:
    """Merge outputs from all workers into unified structure.

    Args:
        output_dir: Base output directory
        num_workers: Number of workers

    Returns:
        Statistics dictionary
    """
    logger.info("Merging worker outputs...")

    total_samples = 0
    total_failed = 0
    samples_by_script: dict[str, int] = {}

    for worker_id in range(num_workers):
        worker_dir = output_dir / f"worker_{worker_id}"
        if not worker_dir.exists():
            continue

        # Count samples per script
        for script_dir in worker_dir.iterdir():
            if script_dir.is_dir():
                script_code = script_dir.name
                png_files = list(script_dir.glob("*.png"))
                count = len(png_files)
                total_samples += count
                samples_by_script[script_code] = (
                    samples_by_script.get(script_code, 0) + count
                )

    stats = {
        "total_samples": total_samples,
        "total_failed": total_failed,
        "samples_by_script": samples_by_script,
        "num_scripts": len(samples_by_script),
    }

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "total_samples": total_samples,
                "scripts": list(samples_by_script.keys()),
                "samples_by_script": samples_by_script,
                "augmentation": "hybrid",
                "format": "png",
            },
            f,
            indent=2,
        )

    logger.info(f"Manifest saved to {manifest_path}")
    return stats


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic multi-script document dataset"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of parallel workers (default: 2)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=250000,
        help="Total samples to generate (default: 250000)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic_250k"),
        help="Output directory (default: data/synthetic_250k)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base random seed (default: 42)",
    )
    parser.add_argument(
        "--scripts",
        nargs="+",
        default=None,
        help="Specific scripts to generate (default: all 27)",
    )

    args = parser.parse_args()

    # Validate
    if args.workers < 1:
        logger.error("Workers must be >= 1")
        return 1

    if args.samples < 1:
        logger.error("Samples must be >= 1")
        return 1

    # Get scripts
    scripts = args.scripts or list(SCRIPT_CONFIGS.keys())
    logger.info(f"Will generate for {len(scripts)} scripts: {scripts[:5]}...")

    # Create output directory
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Calculate samples per worker
    samples_per_worker = args.samples // args.workers
    remainder = args.samples % args.workers

    logger.info(
        f"Starting generation: {args.samples} samples with {args.workers} workers"
    )
    logger.info(f"Each worker will generate ~{samples_per_worker} samples")

    # Create tasks
    tasks: list[WorkerTask] = []
    for i in range(args.workers):
        # Distribute remainder to first workers
        worker_samples = samples_per_worker + (1 if i < remainder else 0)
        task = WorkerTask(
            worker_id=i,
            samples_to_generate=worker_samples,
            seed=args.seed + i * 10000,  # Different seed per worker
            output_dir=output_dir,
            scripts=scripts,
        )
        tasks.append(task)
        logger.info(f"Worker {i}: {worker_samples} samples, seed={task.seed}")

    # Run workers
    start_time = time.time()

    if args.workers == 1:
        # Single worker - no multiprocessing overhead
        results = [generate_worker(tasks[0])]
    else:
        # Multiple workers - use process pool
        # Use spawn to avoid fork issues with CUDA/etc
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=args.workers) as pool:
            results = pool.map(generate_worker, tasks)

    # Summarize results
    total_generated = sum(r.samples_generated for r in results)
    total_failed = sum(r.samples_failed for r in results)
    total_elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total samples generated: {total_generated}")
    logger.info(f"Total samples failed: {total_failed}")
    logger.info(f"Total time: {total_elapsed / 3600:.2f} hours")
    logger.info(f"Average rate: {total_generated / total_elapsed:.1f} samples/sec")

    # Report per-worker stats
    for result in results:
        rate = (
            result.samples_generated / result.elapsed_seconds
            if result.elapsed_seconds > 0
            else 0
        )
        logger.info(
            f"  Worker {result.worker_id}: {result.samples_generated} samples, "
            f"{rate:.1f}/sec, {len(result.errors)} errors"
        )

    # Merge outputs
    stats = merge_worker_outputs(output_dir, args.workers)
    logger.info(
        f"Final dataset: {stats['total_samples']} samples across {stats['num_scripts']} scripts"
    )

    # Save final stats
    stats_path = output_dir / "generation_stats.json"
    with open(stats_path, "w") as f:
        json.dump(
            {
                "total_samples": total_generated,
                "total_failed": total_failed,
                "total_elapsed_seconds": total_elapsed,
                "workers": args.workers,
                "seed": args.seed,
                "samples_by_script": stats["samples_by_script"],
                "completed_at": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )

    logger.info(f"Stats saved to {stats_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
