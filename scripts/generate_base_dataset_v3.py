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

    # Targeted fill using audit output (skip scripts already at target)
    python scripts/audit_v3_per_script_counts.py \\
        --output results/v3_per_script_audit.json
    python scripts/generate_base_dataset_v3.py \\
        --output-dir /mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3 \\
        --resume-from-audit results/v3_per_script_audit.json \\
        --fail-on-corpus-error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
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

# All 27 training scripts.  "Kore" renamed to "Hang" (ISO 15924 Hangul-only code;
# both map to the KORE ML class — see config/script_ml_classes.yaml).
# "Geor" is generated but tagged split_type="ood" at save time (see OOD_ONLY_SCRIPTS).
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
    "Hang",  # renamed from "Kore" (ISO 15924 Hangul; maps to KORE ML class)
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

# Scripts reserved exclusively for OOD evaluation — never appear in training manifests.
# Images generated for these scripts have split_type="ood" in their sidecar metadata.
# Mongolian (Mong) and Syriac (Syrc) are listed here but NOT in ALL_SCRIPTS yet;
# they will be added once Noto Sans fonts are installed (see docs/planning/... font setup).
# Armn added: only 5 SALAMI samples — too few for training, reserved for OOD.
OOD_ONLY_SCRIPTS: frozenset[str] = frozenset(
    {
        "Armn",  # Armenian — 5 SALAMI samples only; OOD anchor
        "Geor",  # Georgian — Noto Sans Georgian (OFL); OOD anchor
        "Mong",  # Mongolian — Noto Sans Mongolian (OFL); TTB script; OOD anchor
        "Syrc",  # Syriac — Noto Sans Syriac (OFL); RTL script; OOD anchor
    }
)


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


def _load_audit_distribution(
    audit_path: Path, total_images: int
) -> tuple[list[str], dict[str, int]]:
    """Load a targeted fill distribution from an audit JSON file.

    Reads the output of ``audit_v3_per_script_counts.py`` and derives a
    per-script allocation that only generates images for scripts that have not
    yet reached their target.  Scripts marked ``"done": true`` in the audit are
    excluded from the returned script list so workers skip them entirely.

    Args:
        audit_path: Path to the JSON file produced by audit_v3_per_script_counts.py.
        total_images: The overall target total (used only for display; individual
            targets come from the audit file itself).

    Returns:
        Tuple of (scripts_needing_generation, per_script_distribution).

    Raises:
        SystemExit: If the audit file cannot be read or is malformed.
    """
    try:
        with audit_path.open() as fh:
            audit = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot read audit file {audit_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    per_script_data: dict[str, dict[str, object]] = audit.get("per_script", {})
    if not per_script_data:
        print(
            f"ERROR: Audit file {audit_path} has no 'per_script' key or it is empty.",
            file=sys.stderr,
        )
        sys.exit(1)

    scripts_needed: list[str] = []
    distribution: dict[str, int] = {}

    for script, info in per_script_data.items():
        remaining = int(info.get("remaining", 0))  # type: ignore[arg-type]
        done = bool(info.get("done", False))
        if done or remaining <= 0:
            continue
        scripts_needed.append(script)
        distribution[script] = remaining

    total_remaining = sum(distribution.values())
    print(
        f"Audit-guided fill: {len(scripts_needed)} scripts need generation "
        f"({total_remaining:,} images remaining to reach target)"
    )
    if not scripts_needed:
        print("All scripts already at target — nothing to generate.")
        sys.exit(0)

    return scripts_needed, distribution


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

    is_ood = primary_script in OOD_ONLY_SCRIPTS

    metadata = generator.schema_adapter.build_enrichment_metadata(
        sample, augmentation_source=augmenter
    )
    metadata["generation_params"] = sample.generation_params
    # OOD scripts are never assigned to train/val/test — mark them explicitly.
    if is_ood:
        metadata["split_type"] = "ood"
    metadata_path = script_dir / f"{sample.sample_id}.json"
    with open(metadata_path, "w") as f:
        json_mod.dump(metadata, f, indent=2, default=str)

    # OOD images must not enter the split registry (train/val/test only).
    sha256 = sample.generation_params.get("base_image_sha256", "")
    if sha256 and not is_ood:
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
    fail_on_corpus_error: bool = False,
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
        fail_on_corpus_error: If True, treat an empty corpus as a fatal error
            instead of silently falling back to built-in sample texts.

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
        if fail_on_corpus_error:
            corpus_scripts = generator.corpus_manager.get_available_scripts()
            missing = [s for s in scripts if s not in corpus_scripts]
            if missing:
                stats["error"] = (
                    f"--fail-on-corpus-error: no corpus data for scripts: "
                    f"{', '.join(missing)}. Install corpora before generating."
                )
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
        "created_at": datetime.now(timezone.utc).isoformat(),
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
    parser.add_argument(
        "--resume-from-audit",
        type=Path,
        default=None,
        metavar="AUDIT_JSON",
        help=(
            "Path to audit JSON produced by audit_v3_per_script_counts.py. "
            "When set, only scripts with remaining>0 in the audit are generated; "
            "scripts already at their target are skipped entirely.  Implies --resume."
        ),
    )
    parser.add_argument(
        "--fail-on-corpus-error",
        action="store_true",
        help=(
            "Exit with error if the text corpus is empty for any configured script "
            "instead of silently falling back to built-in sample texts."
        ),
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


def _samples_per_script_for_worker(
    worker_scripts: list[str],
    distribution: dict[str, int],
) -> int:
    """Compute the samples_per_script value to pass to a worker.

    Each worker owns a subset of scripts.  Since the generator config accepts a
    single ``samples_per_script`` that applies uniformly to all scripts assigned
    to the worker, we take the *maximum* allocation across the worker's scripts
    from the distribution.  This guarantees that every script reaches at least
    its target; any marginal over-generation (at most 1 image per script when
    the remainder is distributed unevenly) is negligible.

    Previously the code always used ``distribution[scripts[0]]`` regardless of
    which scripts were actually assigned to the worker.  That caused scripts that
    did not happen to be ``scripts[0]`` to get the wrong (sometimes zero-inflated)
    target when the first script received a remainder +1 bonus.

    Args:
        worker_scripts: Scripts assigned to this worker process.
        distribution: Full per-script allocation from ``_compute_distribution``.

    Returns:
        The samples_per_script value for this worker.
    """
    if not worker_scripts:
        return 0
    return max(distribution.get(script, 0) for script in worker_scripts)


def _run_workers(
    args: argparse.Namespace,
    scripts: list[str],
    distribution: dict[str, int],
    split_registry_path: Path,
) -> list[dict[str, Any]]:
    """Dispatch generation work to single or multiple worker processes.

    Args:
        args: Parsed command-line arguments.
        scripts: List of script codes to generate.
        distribution: Per-script allocation from ``_compute_distribution``.
            Each worker receives the correct ``samples_per_script`` value
            derived from its own assigned scripts, not a single global value.
        split_registry_path: Path to the split registry JSONL file.

    Returns:
        List of per-worker statistics dicts.
    """
    all_stats: list[dict[str, Any]] = []

    fail_on_corpus = getattr(args, "fail_on_corpus_error", False)

    if args.workers == 1:
        samples_per_script = _samples_per_script_for_worker(scripts, distribution)
        result = _generate_worker_batch(
            worker_id=0,
            scripts=scripts,
            samples_per_script=samples_per_script,
            output_dir=str(args.output_dir),
            seed=args.seed,
            augmenter=args.augmenter,
            split_registry_path=str(split_registry_path),
            fail_on_corpus_error=fail_on_corpus,
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
            # Fix: derive samples_per_script from the actual distribution for
            # this worker's scripts, not a single global value taken from
            # scripts[0] which may have a remainder +1 that does not apply to
            # all workers.
            samples_per_script = _samples_per_script_for_worker(
                worker_scripts, distribution
            )
            future = executor.submit(
                _generate_worker_batch,
                worker_id=worker_id,
                scripts=worker_scripts,
                samples_per_script=samples_per_script,
                output_dir=str(args.output_dir),
                seed=args.seed,
                augmenter=args.augmenter,
                split_registry_path=str(split_registry_path),
                fail_on_corpus_error=fail_on_corpus,
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

    # --resume-from-audit implies --resume (skip existing files on disk)
    if args.resume_from_audit:
        args.resume = True

    # Parse scripts (and per-script targets) from audit or command line
    audit_distribution: dict[str, int] | None = None
    if args.resume_from_audit:
        scripts, audit_distribution = _load_audit_distribution(
            args.resume_from_audit, args.total_images
        )
    else:
        scripts = ALL_SCRIPTS
        if args.scripts:
            scripts = [s.strip() for s in args.scripts.split(",")]

    # Dry run
    if args.dry_run:
        distribution = audit_distribution or _compute_distribution(
            args.total_images, scripts
        )
        _show_distribution_plan(distribution, args.output_dir, args.seed, args.workers)
        return 0

    # Determine how many images we need to generate
    existing_count = 0
    if args.resume:
        existing_count = _check_resume(args.output_dir)
        if existing_count > 0:
            print(f"Found {existing_count:,} existing samples. Resuming...")

    if audit_distribution:
        # In audit-guided mode, remaining is the sum of per-script deficits
        remaining = sum(audit_distribution.values())
    else:
        remaining = max(0, args.total_images - existing_count)

    if remaining == 0:
        print("Generation already complete!")
        return 0

    # Confirmation
    est_gb = remaining * 200 / 1024 / 1024
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

    # Track the audit-guided per-script budget across chunks.
    # We copy it so we can decrement each script's remaining budget as chunks complete.
    audit_budget: dict[str, int] | None = (
        dict(audit_distribution) if audit_distribution else None
    )

    while True:
        if audit_budget is not None:
            # Audit-guided mode: remaining is total still-needed across scripts.
            # Prune scripts that have been satisfied.
            audit_budget = {s: n for s, n in audit_budget.items() if n > 0}
            scripts = list(audit_budget.keys())
            remaining = sum(audit_budget.values())
        else:
            # Normal mode: re-count images on disk.
            current_count = _check_resume(args.output_dir)
            remaining = max(0, args.total_images - current_count)

        if remaining == 0 or not scripts:
            break

        # Determine this chunk's size
        if use_chunking:
            chunk_total = min(args.chunk_size, remaining)
        else:
            chunk_total = remaining

        # Compute per-script distribution for this chunk.
        if audit_budget is not None:
            # Proportionally scale the audit budget down to this chunk's size.
            total_needed = sum(audit_budget.values())
            scale = chunk_total / total_needed if total_needed > 0 else 1.0
            chunk_distribution = {
                s: max(1, round(n * scale)) for s, n in audit_budget.items()
            }
            # Correct for rounding so chunk_distribution sums to chunk_total exactly.
            diff = chunk_total - sum(chunk_distribution.values())
            if diff != 0:
                adj_script = max(
                    chunk_distribution, key=lambda k: chunk_distribution[k]
                )
                chunk_distribution[adj_script] += diff
        else:
            # Each script receives base_count or base_count+1 images so that the
            # chunk total is exact.  Pass the full distribution dict to _run_workers
            # so each worker derives the correct samples_per_script for its own
            # assigned scripts instead of blindly using scripts[0]'s allocation.
            chunk_distribution = _compute_distribution(chunk_total, scripts)

        if chunk_total == 0 or not any(chunk_distribution.values()):
            break

        # Offset seed per chunk so we don't regenerate identical images
        chunk_seed = args.seed + chunk_idx * 100_000
        chunk_args = argparse.Namespace(**vars(args))
        chunk_args.seed = chunk_seed

        if use_chunking:
            progress_of = (
                f"{sum(audit_distribution.values() if audit_distribution else []):,} remaining"
                if audit_budget is not None
                else f"{current_count:,}/{args.total_images:,} complete"
            )
            print(
                f"\n--- Chunk {chunk_idx + 1}: generating {chunk_total:,} images "
                f"({progress_of}) ---"
            )

        chunk_stats = _run_workers(
            chunk_args, scripts, chunk_distribution, split_registry_path
        )
        _merge_stats(all_stats, chunk_stats)

        chunk_generated = sum(s.get("generated", 0) for s in chunk_stats)
        chunk_failed = sum(s.get("failed", 0) for s in chunk_stats)

        # In audit-guided mode, reduce each script's budget by what was generated.
        if audit_budget is not None:
            for s in list(chunk_distribution.keys()):
                script_generated = sum(
                    w.get("per_script", {}).get(s, 0) for w in chunk_stats
                )
                audit_budget[s] = max(0, audit_budget.get(s, 0) - script_generated)

        if use_chunking:
            elapsed_so_far = time.time() - start_time
            total_on_disk = _check_resume(args.output_dir)
            rate = total_on_disk / elapsed_so_far if elapsed_so_far > 0 else 0
            if audit_budget is not None:
                still_remaining = sum(v for v in audit_budget.values() if v > 0)
            else:
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
