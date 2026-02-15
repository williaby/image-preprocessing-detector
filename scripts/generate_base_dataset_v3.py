#!/usr/bin/env python3
"""Generate synth-multiscript v3 base dataset (350K pristine images).

Phase 1 of the synth-multiscript regeneration plan. Produces 350K pristine
base images across 27 scripts with expanded v2.3 Layer 2 metadata.

Key features:
    - 350K images across 27 scripts, 7 DPI tiers, 5 quality tiers
    - All v2.3 metadata: text_direction, char_height_rendered_px, etc.
    - Multi-script composition with English secondary weighting (40%)
    - CJK vertical text (Jpan 30% TTB, Hans/Hant 10% TTB)
    - Skew range ±22° in base images
    - Global split registry integration (SHA256-keyed)
    - Hybrid augmentation pipeline (Augraphy + Albumentations)
    - JPEG q95 output (~200KB/image, ~70GB total)
    - Multi-worker parallel generation with progress tracking
    - Resume capability via manifest checkpoint

Output structure:
    output_dir/
        {ScriptCode}/
            {sample_id}.jpg          # JPEG q95 pristine base image
            {sample_id}.json         # Layer 2 v2.3 metadata
        manifest.json                # Generation manifest with stats
        splits.jsonl                 # Global split registry
        generation.log               # Detailed generation log

Usage:
    # Dry run (show distribution plan, no generation)
    python scripts/generate_base_dataset_v3.py \\
        --output-dir /mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3 \\
        --dry-run

    # Generate full 350K dataset
    python scripts/generate_base_dataset_v3.py \\
        --output-dir /mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3 \\
        --total-images 350000 --workers 4 --seed 42

    # Generate small test batch
    python scripts/generate_base_dataset_v3.py \\
        --output-dir ./test_v3 --total-images 100 --workers 1 --seed 42

    # Resume interrupted generation
    python scripts/generate_base_dataset_v3.py \\
        --output-dir /mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3 \\
        --resume
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Version & Constants
# ---------------------------------------------------------------------------
SCRIPT_VERSION = "3.0.0"
SCHEMA_VERSION = "2.3.0"
IMAGE_FORMAT = "jpg"
JPEG_QUALITY = 95
DEFAULT_TOTAL = 350_000
DEFAULT_WORKERS = 4
DEFAULT_SEED = 42
DEFAULT_CHUNK_SIZE = 10_000  # Images per chunk to bound memory leaks

# All 27 scripts
ALL_SCRIPTS = [
    "Arab",
    "Armn",
    "Beng",
    "Cyrl",
    "Deva",
    "Ethi",
    "Geor",
    "Grek",
    "Gujr",
    "Guru",
    "Hans",
    "Hant",
    "Hebr",
    "Jpan",
    "Khmr",
    "Knda",
    "Kore",
    "Laoo",
    "Latn",
    "Mlym",
    "Mymr",
    "Orya",
    "Sinh",
    "Taml",
    "Telu",
    "Thai",
    "Tibt",
]


def _compute_distribution(
    total: int,
    scripts: list[str],
) -> dict[str, int]:
    """Compute per-script sample counts ensuring even distribution.

    Each script gets an equal share, with remainder distributed
    to underrepresented scripts. This provides ~12,963 samples per
    script for 350K across 27 scripts.

    Args:
        total: Total number of images to generate
        scripts: List of script codes

    Returns:
        Dict mapping script code to sample count
    """
    base_count = total // len(scripts)
    remainder = total % len(scripts)

    distribution: dict[str, int] = {}
    for i, script in enumerate(scripts):
        distribution[script] = base_count + (1 if i < remainder else 0)

    return distribution


def _show_distribution_plan(
    distribution: dict[str, int],
    output_dir: Path,
    seed: int,
    workers: int,
) -> None:
    """Display the generation plan without creating files.

    Args:
        distribution: Per-script sample counts
        output_dir: Target output directory
        seed: Random seed
        workers: Number of worker processes
    """
    total = sum(distribution.values())
    print("=" * 70)
    print("Synth-Multiscript v3 Base Dataset - Generation Plan")
    print("=" * 70)
    print(f"  Total images:    {total:,}")
    print(f"  Scripts:         {len(distribution)}")
    print(f"  Output:          {output_dir}")
    print(f"  Image format:    JPEG q{JPEG_QUALITY}")
    print(f"  Schema version:  {SCHEMA_VERSION}")
    print(f"  Seed:            {seed}")
    print(f"  Workers:         {workers}")
    print(
        f"  Est. storage:    ~{total * 200 / 1024:.0f} MB ({total * 200 / 1024 / 1024:.1f} GB)"
    )
    print()
    print("Per-script distribution:")
    for script, count in sorted(distribution.items()):
        print(f"    {script}: {count:,}")
    print()
    print("Multi-task features:")
    print("    - Orientation augmentation (0/90/180/270)")
    print("    - Skew augmentation (±22°)")
    print("    - Color mode conversion (color/grayscale/binarized)")
    print("    - CJK vertical text (Jpan 30%, Hans/Hant 10%)")
    print("    - English secondary weighting (40% in multi-script)")
    print("    - Hybrid augmentation (Augraphy + Albumentations)")
    print("    - 7 DPI tiers (72-600)")
    print("    - char_height_rendered_px (CC analysis on pristine)")
    print("    - base_image_sha256 (split registry)")
    print("    - degradation_seed (reproducible replay)")
    print("    - font_families_used (diversity audit)")
    print("=" * 70)


def _update_composition_stats(stats: dict[str, Any], sample: Any) -> None:
    """Update multi-script composition and vertical text tracking stats.

    Args:
        stats: Worker statistics dict to update in-place.
        sample: Generated sample with scripts and text_directions.
    """
    if len(sample.scripts) > 1:
        stats["multi_script_count"] += 1
        comp = f"{len(sample.scripts)}_script"
        stats["per_composition"][comp] += 1
        if "Latn" in sample.scripts:
            stats["english_secondary_count"] += 1
    else:
        stats["per_composition"]["single"] += 1

    if sample.text_directions:
        for _sc, direction in sample.text_directions.items():
            if direction == "ttb":
                stats["vertical_text_count"] += 1
                break


def _save_sample(
    sample: Any,
    output: Path,
    generator: Any,
    augmenter: str,
    registry: Any,
    json_mod: Any,
) -> Path:
    """Save a single generated sample (image + metadata) and register in split registry.

    Args:
        sample: Generated sample to save.
        output: Base output directory.
        generator: Generator instance for building metadata.
        augmenter: Augmentation library name.
        registry: Split registry instance.
        json_mod: JSON module reference.

    Returns:
        Path to saved image file.
    """
    primary_script = sorted(sample.scripts)[0]
    script_dir = output / primary_script
    script_dir.mkdir(parents=True, exist_ok=True)

    image_path = script_dir / f"{sample.sample_id}.{IMAGE_FORMAT}"
    sample.image.save(image_path, format="JPEG", quality=JPEG_QUALITY)

    metadata = generator.schema_adapter.build_enrichment_metadata(
        sample, augmentation_source=augmenter
    )
    metadata["generation_params"] = sample.generation_params
    metadata_path = script_dir / f"{sample.sample_id}.json"
    with open(metadata_path, "w") as f:
        json_mod.dump(metadata, f, indent=2, default=str)

    sha256 = sample.generation_params.get("base_image_sha256", "")
    if sha256:
        registry.assign_split(
            sha256_hex=sha256,
            source_dataset="synth_multiscript_v3",
            source_path=str(image_path),
        )

    return image_path


def _generate_worker_batch(
    worker_id: int,
    scripts: list[str],
    samples_per_script: int,
    output_dir: str,
    seed: int,
    augmenter: str,
    split_registry_path: str,
) -> dict[str, Any]:
    """Generate a batch of samples in a worker process.

    Each worker generates samples for assigned scripts, saving images
    and metadata to the output directory. The split registry is updated
    atomically after each sample.

    Args:
        worker_id: Worker process identifier
        scripts: Script codes assigned to this worker
        samples_per_script: Number of samples per script
        output_dir: Output directory path
        seed: Base random seed (offset by worker_id)
        augmenter: Augmentation library to use
        split_registry_path: Path to split registry JSONL

    Returns:
        Dict with generation statistics for this worker
    """
    # Import heavy deps inside worker to avoid fork overhead
    import json as json_mod

    from image_preprocessing_detector.schema_utils.split_registry import SplitRegistry
    from image_preprocessing_detector.synthetic.generator import (
        GenerationConfig,
        MultiScriptDocumentGenerator,
    )

    output = Path(output_dir)
    worker_seed = seed + worker_id * 10_000

    stats: dict[str, Any] = {
        "worker_id": worker_id,
        "scripts": scripts,
        "generated": 0,
        "failed": 0,
        "per_script": {},
        "per_layout": Counter(),
        "per_resolution_tier": Counter(),
        "per_quality_tier": Counter(),
        "per_composition": Counter(),
        "vertical_text_count": 0,
        "english_secondary_count": 0,
        "multi_script_count": 0,
        "start_time": time.time(),
    }

    registry = SplitRegistry(split_registry_path)

    config = GenerationConfig(
        scripts=scripts,
        samples_per_script=samples_per_script,
        output_dir=None,
        save_images=False,
        save_metadata=False,
        image_format=IMAGE_FORMAT,
        seed=worker_seed,
        pristine_ratio=0.2,
        augmenter=augmenter,
        color_mode_enabled=True,
        skew_augmentation=True,
        orientation_augmentation=True,
    )

    generator = MultiScriptDocumentGenerator(config=config)

    try:
        success = generator.initialize(download_corpus=True)
        if not success:
            stats["error"] = "Failed to initialize generator"
            return stats
    except Exception as e:
        stats["error"] = f"Initialization error: {e}"
        return stats

    for sample in generator.generate():
        try:
            _save_sample(sample, output, generator, augmenter, registry, json_mod)

            stats["generated"] += 1
            for sc in sample.scripts:
                stats["per_script"][sc] = stats["per_script"].get(sc, 0) + 1

            stats["per_layout"][sample.layout_type.value] += 1
            stats["per_resolution_tier"][sample.resolution_tier] += 1
            stats["per_quality_tier"][sample.quality_tier] += 1

            _update_composition_stats(stats, sample)

            if stats["generated"] % 500 == 0:
                elapsed = time.time() - stats["start_time"]
                rate = stats["generated"] / elapsed if elapsed > 0 else 0
                print(
                    f"  [Worker {worker_id}] {stats['generated']:,} samples "
                    f"({rate:.1f} img/s)"
                )

        except Exception as e:
            stats["failed"] += 1
            logger.warning("Worker %d: sample save failed: %s", worker_id, e)

    stats["end_time"] = time.time()
    stats["duration_s"] = stats["end_time"] - stats["start_time"]
    stats["rate_img_s"] = (
        stats["generated"] / stats["duration_s"] if stats["duration_s"] > 0 else 0
    )
    return stats


def _write_manifest(
    output_dir: Path,
    all_stats: list[dict[str, Any]],
    total_target: int,
    seed: int,
    augmenter: str,
) -> Path:
    """Write generation manifest with aggregate statistics.

    Args:
        output_dir: Output directory
        all_stats: Per-worker statistics
        total_target: Target total images
        seed: Random seed
        augmenter: Augmentation library used

    Returns:
        Path to manifest file
    """
    # Aggregate stats
    total_generated = sum(s.get("generated", 0) for s in all_stats)
    total_failed = sum(s.get("failed", 0) for s in all_stats)
    total_duration = max(s.get("duration_s", 0) for s in all_stats) if all_stats else 0

    # Merge per-script counts
    per_script: dict[str, int] = {}
    per_layout: dict[str, int] = {}
    per_resolution: dict[str, int] = {}
    per_quality: dict[str, int] = {}
    per_composition: dict[str, int] = {}
    vertical_text = 0
    english_secondary = 0
    multi_script = 0

    for s in all_stats:
        for k, v in s.get("per_script", {}).items():
            per_script[k] = per_script.get(k, 0) + v
        for k, v in s.get("per_layout", {}).items():
            per_layout[k] = per_layout.get(k, 0) + v
        for k, v in s.get("per_resolution_tier", {}).items():
            per_resolution[k] = per_resolution.get(k, 0) + v
        for k, v in s.get("per_quality_tier", {}).items():
            per_quality[k] = per_quality.get(k, 0) + v
        for k, v in s.get("per_composition", {}).items():
            per_composition[k] = per_composition.get(k, 0) + v
        vertical_text += s.get("vertical_text_count", 0)
        english_secondary += s.get("english_secondary_count", 0)
        multi_script += s.get("multi_script_count", 0)

    manifest = {
        "dataset_name": "synth_multiscript_v3",
        "dataset_version": SCRIPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "augmenter": augmenter,
        "image_format": f"JPEG q{JPEG_QUALITY}",
        "target_total": total_target,
        "total_generated": total_generated,
        "total_failed": total_failed,
        "duration_seconds": round(total_duration, 1),
        "rate_images_per_second": round(total_generated / total_duration, 2)
        if total_duration > 0
        else 0,
        "scripts": sorted(per_script.keys()),
        "num_scripts": len(per_script),
        "features": {
            "orientation_augmentation": True,
            "skew_augmentation": True,
            "skew_range_degrees": [-22.0, 22.0],
            "color_mode_enabled": True,
            "cjk_vertical_text": True,
            "english_secondary_weight": 0.40,
            "hybrid_augmentation": augmenter == "hybrid",
            "dpi_tiers": [72, 100, 150, 200, 300, 400, 600],
            "char_height_rendered_px": True,
            "base_image_sha256": True,
            "degradation_seed": True,
            "font_families_used": True,
            "split_registry": True,
        },
        "distributions": {
            "per_script": dict(sorted(per_script.items())),
            "per_layout": dict(sorted(per_layout.items())),
            "per_resolution_tier": dict(sorted(per_resolution.items())),
            "per_quality_tier": dict(sorted(per_quality.items())),
            "per_composition": dict(sorted(per_composition.items())),
        },
        "v23_metadata_stats": {
            "vertical_text_samples": vertical_text,
            "english_secondary_samples": english_secondary,
            "multi_script_samples": multi_script,
        },
        "workers": [
            {
                "id": s.get("worker_id"),
                "scripts": s.get("scripts"),
                "generated": s.get("generated", 0),
                "failed": s.get("failed", 0),
                "duration_s": round(s.get("duration_s", 0), 1),
                "rate_img_s": round(s.get("rate_img_s", 0), 2),
            }
            for s in all_stats
        ],
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    return manifest_path


def _check_resume(output_dir: Path) -> int:
    """Check for existing generation progress for resume capability.

    Counts existing .jpg files in the output directory to determine
    how many samples were already generated.

    Args:
        output_dir: Output directory to check

    Returns:
        Number of existing samples found
    """
    if not output_dir.exists():
        return 0

    count = 0
    for script_dir in output_dir.iterdir():
        if script_dir.is_dir() and script_dir.name in ALL_SCRIPTS:
            count += len(list(script_dir.glob(f"*.{IMAGE_FORMAT}")))
    return count


def _parse_main_args() -> argparse.Namespace:
    """Parse command-line arguments for base dataset generation.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate synth-multiscript v3 base dataset (350K pristine images)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "/mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3"
        ),
        help="Output directory for generated dataset",
    )
    parser.add_argument(
        "--total-images",
        type=int,
        default=DEFAULT_TOTAL,
        help=f"Total images to generate (default: {DEFAULT_TOTAL:,})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of worker processes (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--augmenter",
        choices=["albumentations", "hybrid", "augraphy"],
        default="hybrid",
        help="Augmentation library (default: hybrid)",
    )
    parser.add_argument(
        "--scripts",
        type=str,
        default=None,
        help="Comma-separated script codes (default: all 27)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generation plan without creating files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted generation (skip existing samples)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=(
            f"Images per chunk before restarting workers to reclaim memory "
            f"(default: {DEFAULT_CHUNK_SIZE:,}). Set to 0 to disable chunking."
        ),
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser.parse_args()


def _setup_logging(args: argparse.Namespace) -> None:
    """Configure logging handlers for the generation run.

    Args:
        args: Parsed command-line arguments.
    """
    log_handlers: list[logging.Handler] = [logging.StreamHandler()]
    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(args.output_dir / "generation.log")
        log_handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=log_handlers,
    )


def _run_workers(
    args: argparse.Namespace,
    scripts: list[str],
    samples_per_script: int,
    split_registry_path: Path,
) -> list[dict[str, Any]]:
    """Dispatch generation work to single or multiple worker processes.

    Args:
        args: Parsed command-line arguments.
        scripts: List of script codes to generate.
        samples_per_script: Number of samples per script.
        split_registry_path: Path to the split registry JSONL file.

    Returns:
        List of per-worker statistics dicts.
    """
    all_stats: list[dict[str, Any]] = []

    if args.workers == 1:
        result = _generate_worker_batch(
            worker_id=0,
            scripts=scripts,
            samples_per_script=samples_per_script,
            output_dir=str(args.output_dir),
            seed=args.seed,
            augmenter=args.augmenter,
            split_registry_path=str(split_registry_path),
        )
        all_stats.append(result)
        return all_stats

    from concurrent.futures import ProcessPoolExecutor

    scripts_per_worker: list[list[str]] = [[] for _ in range(args.workers)]
    for i, script in enumerate(scripts):
        scripts_per_worker[i % args.workers].append(script)

    futures = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for worker_id, worker_scripts in enumerate(scripts_per_worker):
            if not worker_scripts:
                continue
            future = executor.submit(
                _generate_worker_batch,
                worker_id=worker_id,
                scripts=worker_scripts,
                samples_per_script=samples_per_script,
                output_dir=str(args.output_dir),
                seed=args.seed,
                augmenter=args.augmenter,
                split_registry_path=str(split_registry_path),
            )
            futures.append(future)

        for future in futures:
            try:
                result = future.result()
                all_stats.append(result)
            except Exception as e:
                logger.error("Worker failed: %s", e)
                all_stats.append({"error": str(e), "generated": 0, "failed": 0})

    return all_stats


def _print_summary(
    all_stats: list[dict[str, Any]],
    manifest_path: Path,
    split_registry_path: Path,
    elapsed: float,
) -> int:
    """Print generation summary and return exit code.

    Args:
        all_stats: Per-worker statistics.
        manifest_path: Path to the written manifest.
        split_registry_path: Path to the split registry.
        elapsed: Total elapsed time in seconds.

    Returns:
        Exit code (0 for success, 1 if failure rate exceeds 1%).
    """
    from image_preprocessing_detector.schema_utils.split_registry import SplitRegistry

    total_generated = sum(s.get("generated", 0) for s in all_stats)
    total_failed = sum(s.get("failed", 0) for s in all_stats)
    rate = total_generated / elapsed if elapsed > 0 else 0

    print()
    print("=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    print(f"  Total generated: {total_generated:,}")
    print(f"  Failed:          {total_failed:,}")
    print(f"  Duration:        {elapsed / 3600:.1f} hours ({elapsed:.0f}s)")
    print(f"  Rate:            {rate:.1f} img/s")
    print(f"  Output:          {manifest_path.parent}")
    print(f"  Manifest:        {manifest_path}")
    print(f"  Split registry:  {split_registry_path}")

    registry = SplitRegistry(str(split_registry_path))
    split_stats = registry.stats
    print("\n  Split distribution:")
    for split_name, count in sorted(split_stats.items()):
        pct = count / total_generated * 100 if total_generated > 0 else 0
        print(f"    {split_name}: {count:,} ({pct:.1f}%)")

    vertical = sum(s.get("vertical_text_count", 0) for s in all_stats)
    eng_sec = sum(s.get("english_secondary_count", 0) for s in all_stats)
    multi = sum(s.get("multi_script_count", 0) for s in all_stats)
    print("\n  v2.3 metadata:")
    print(f"    Vertical text (TTB): {vertical:,}")
    print(f"    English secondary:   {eng_sec:,}")
    print(f"    Multi-script:        {multi:,}")
    print("=" * 70)

    return 1 if total_failed > total_generated * 0.01 else 0


def _merge_stats(
    accumulated: list[dict[str, Any]], chunk_stats: list[dict[str, Any]]
) -> None:
    """Merge chunk worker stats into accumulated totals.

    Args:
        accumulated: Running totals (modified in-place).
        chunk_stats: Stats from the current chunk's workers.
    """
    accumulated.extend(chunk_stats)


def main() -> int:
    """Main entry point for base dataset generation.

    Supports chunked generation to prevent OOM: workers are restarted
    every ``--chunk-size`` images so leaked memory is reclaimed by the OS.
    """
    args = _parse_main_args()
    _setup_logging(args)

    # Parse scripts
    scripts = ALL_SCRIPTS
    if args.scripts:
        scripts = [s.strip() for s in args.scripts.split(",")]

    # Dry run
    if args.dry_run:
        distribution = _compute_distribution(args.total_images, scripts)
        _show_distribution_plan(distribution, args.output_dir, args.seed, args.workers)
        return 0

    # Determine how many images we need to generate
    existing_count = 0
    if args.resume:
        existing_count = _check_resume(args.output_dir)
        if existing_count > 0:
            print(f"Found {existing_count:,} existing samples. Resuming...")

    remaining = max(0, args.total_images - existing_count)
    if remaining == 0:
        print("Generation already complete!")
        return 0

    # Confirmation
    est_gb = remaining * 200 / 1024 / 1024 / 1024
    if not args.yes:
        print(f"\nWill generate {remaining:,} images (~{est_gb:.1f} GB)")
        print(f"Output: {args.output_dir}")
        if args.chunk_size > 0:
            print(f"Chunk size: {args.chunk_size:,} (workers restart each chunk)")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return 0

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    split_registry_path = args.output_dir / "splits.jsonl"

    use_chunking = args.chunk_size > 0

    print("=" * 70)
    print(f"Starting generation: {remaining:,} images across {args.workers} workers")
    print(f"Augmenter: {args.augmenter}")
    print(f"Seed: {args.seed}")
    if use_chunking:
        print(f"Chunk size: {args.chunk_size:,} (OOM protection)")
    print("=" * 70)

    start_time = time.time()
    all_stats: list[dict[str, Any]] = []
    chunk_idx = 0

    while True:
        # Re-count existing images each iteration for accurate remaining
        current_count = _check_resume(args.output_dir)
        remaining = max(0, args.total_images - current_count)

        if remaining == 0:
            break

        # Determine this chunk's size
        if use_chunking:
            chunk_total = min(args.chunk_size, remaining)
        else:
            chunk_total = remaining

        # Compute per-script distribution for this chunk
        chunk_distribution = _compute_distribution(chunk_total, scripts)
        chunk_per_script = chunk_distribution[scripts[0]]

        if chunk_per_script == 0:
            break

        # Offset seed per chunk so we don't regenerate identical images
        chunk_seed = args.seed + chunk_idx * 100_000
        chunk_args = argparse.Namespace(**vars(args))
        chunk_args.seed = chunk_seed

        if use_chunking:
            print(
                f"\n--- Chunk {chunk_idx + 1}: generating {chunk_total:,} images "
                f"({current_count:,}/{args.total_images:,} complete) ---"
            )

        chunk_stats = _run_workers(
            chunk_args, scripts, chunk_per_script, split_registry_path
        )
        _merge_stats(all_stats, chunk_stats)

        chunk_generated = sum(s.get("generated", 0) for s in chunk_stats)
        chunk_failed = sum(s.get("failed", 0) for s in chunk_stats)

        if use_chunking:
            elapsed_so_far = time.time() - start_time
            total_on_disk = _check_resume(args.output_dir)
            rate = total_on_disk / elapsed_so_far if elapsed_so_far > 0 else 0
            still_remaining = max(0, args.total_images - total_on_disk)
            eta_s = still_remaining / rate if rate > 0 else 0
            print(
                f"  Chunk done: +{chunk_generated:,} generated, "
                f"{chunk_failed:,} failed | "
                f"Total on disk: {total_on_disk:,} | "
                f"ETA: {eta_s / 3600:.1f}h"
            )

        chunk_idx += 1

        # If all workers in the chunk failed, bail out to avoid infinite loop
        if chunk_generated == 0 and chunk_failed == 0:
            any_errors = any(s.get("error") for s in chunk_stats)
            if any_errors:
                logger.error("All workers failed in chunk %d, aborting", chunk_idx)
                break

    manifest_path = _write_manifest(
        args.output_dir, all_stats, args.total_images, args.seed, args.augmenter
    )

    elapsed = time.time() - start_time
    return _print_summary(all_stats, manifest_path, split_registry_path, elapsed)


if __name__ == "__main__":
    sys.exit(main())
