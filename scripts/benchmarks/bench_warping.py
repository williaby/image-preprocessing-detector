#!/usr/bin/env python3
"""Benchmark WarpingDetector against AnyPhotoDoc6300 + WarpDoc.

AnyPhotoDoc6300 (primary): warped images in init_{1-8}/ + flat GT in flat/{category}/.
  NOT 1:1 paired - treats init_* as warp-positive, flat/* as warp-negative.

WarpDoc (detailed): 6 distortion type folders with true paired GT:
  WarpDoc/image/{type}/ (warped) + WarpDoc/digital/{type}/ (flat GT).
  Types: Fold, Curved, Incomplete, Random, Rotating, Perspective.

Usage:
    python scripts/benchmarks/bench_warping.py \
        --data-dir /mnt/e/image_detection \
        --output-dir results/stream3_benchmarks \
        --seed 42
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.warping_detector import WarpingDetector

from scripts.benchmarks.classification_metrics import (
    collect_system_info,
    compute_binary_report,
    compute_latency_stats,
    save_benchmark_result,
)
from scripts.benchmarks.stream3_config import (
    THRESHOLDS,
    ensure_output_dir,
)

logger = logging.getLogger(__name__)

MAX_IMAGE_DIM = 800

WARPDOC_TYPES = ["Curved", "Fold", "Incomplete", "Perspective", "Random", "Rotating"]


def load_anyphotodoc_samples(data_dir: Path) -> list[tuple[Path, int]]:
    """Load AnyPhotoDoc6300 images with binary warp labels.

    init_{1-8}/ folders contain warped images (positive).
    flat/{category}/ folders contain flat GT images (negative).

    Args:
        data_dir: Root data directory.

    Returns:
        List of (image_path, label) where 1=warped, 0=flat.
    """
    root = data_dir / "01_base_data" / "correction" / "anyphotodoc6300"
    samples: list[tuple[Path, int]] = []

    if not root.exists():
        logger.warning("AnyPhotoDoc6300 not found at %s", root)
        return samples

    # Warped images: init_{1-8}/ -> JPG files
    warped_count = 0
    for init_dir in sorted(root.glob("init_*")):
        if init_dir.is_dir():
            for img_path in sorted(init_dir.iterdir()):
                if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    samples.append((img_path, 1))
                    warped_count += 1

    # Flat images: flat/{category}/ -> PNG files
    flat_dir = root / "flat"
    flat_count = 0
    if flat_dir.exists():
        for category_dir in sorted(flat_dir.iterdir()):
            if category_dir.is_dir():
                for img_path in sorted(category_dir.iterdir()):
                    if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        samples.append((img_path, 0))
                        flat_count += 1

    logger.info(
        "AnyPhotoDoc6300: %d warped + %d flat = %d total",
        warped_count,
        flat_count,
        len(samples),
    )
    return samples


def load_warpdoc_samples(
    data_dir: Path,
) -> dict[str, list[tuple[Path, int]]]:
    """Load WarpDoc images grouped by distortion type.

    Each type has WarpDoc/image/{type}/ (warped) and WarpDoc/digital/{type}/ (flat GT).

    Args:
        data_dir: Root data directory.

    Returns:
        Dict mapping distortion type to list of (image_path, label) tuples.
    """
    root = data_dir / "01_base_data" / "correction" / "warpdoc" / "WarpDoc"
    per_type: dict[str, list[tuple[Path, int]]] = {}

    if not root.exists():
        logger.warning("WarpDoc not found at %s", root)
        return per_type

    for dtype in WARPDOC_TYPES:
        warped_dir = root / "image" / dtype
        flat_dir = root / "digital" / dtype
        samples: list[tuple[Path, int]] = []

        if warped_dir.exists():
            warped_files = sorted(warped_dir.glob("*.*"))
            warped_files = [
                f for f in warped_files if f.suffix.lower() in (".jpg", ".jpeg", ".png")
            ]
            samples.extend((p, 1) for p in warped_files)

        if flat_dir.exists():
            flat_files = sorted(flat_dir.glob("*.*"))
            flat_files = [
                f for f in flat_files if f.suffix.lower() in (".jpg", ".jpeg", ".png")
            ]
            samples.extend((p, 0) for p in flat_files)

        if samples:
            per_type[dtype] = samples
            warped = sum(1 for _, l in samples if l == 1)
            flat = sum(1 for _, l in samples if l == 0)
            logger.info("WarpDoc %s: %d warped + %d flat", dtype, warped, flat)

    return per_type


def evaluate_samples(
    samples: list[tuple[Path, int]],
    detector: WarpingDetector,
    label: str,
) -> dict[str, Any]:
    """Run warping detector on samples and compute binary metrics.

    Args:
        samples: List of (image_path, gt_label) tuples.
        detector: WarpingDetector instance.
        label: Label for progress reporting.

    Returns:
        Evaluation result dictionary.
    """
    y_true: list[int] = []
    y_pred: list[int] = []
    y_scores: list[float] = []
    latencies_ms: list[float] = []
    failures = 0

    for idx, (img_path, gt_label) in enumerate(samples):
        if (idx + 1) % 500 == 0:
            print(f"  [{label}] Progress: {idx + 1}/{len(samples)}")

        img = cv2.imread(str(img_path))
        if img is None:
            failures += 1
            continue

        height, width = img.shape[:2]
        if max(height, width) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(height, width)
            img = cv2.resize(
                img,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        start = time.perf_counter()
        result = detector.detect(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        pred_label = 1 if result.has_warping else 0
        y_true.append(gt_label)
        y_pred.append(pred_label)
        y_scores.append(result.warping_score)

    report = compute_binary_report(y_true, y_pred, y_scores=y_scores)
    latency = compute_latency_stats(latencies_ms)

    return {
        "label": label,
        "metrics": report,
        "latency": latency,
        "failures": failures,
    }


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_samples: int,
    seed: int,
) -> dict:
    """Run the warping detection benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory.
        max_samples: Max samples for AnyPhotoDoc (0=all).
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Warping Detection")
    print("=" * 60)

    detector = WarpingDetector()
    rng = np.random.default_rng(seed)

    # Primary: AnyPhotoDoc6300
    apd_samples = load_anyphotodoc_samples(data_dir)
    if max_samples > 0 and len(apd_samples) > max_samples:
        perm = rng.choice(len(apd_samples), size=max_samples, replace=False)
        perm.sort()
        apd_samples = [apd_samples[i] for i in perm]

    apd_result = None
    if apd_samples:
        perm = rng.permutation(len(apd_samples))
        apd_samples = [apd_samples[i] for i in perm]
        print(f"\nEvaluating AnyPhotoDoc6300 ({len(apd_samples)} images)...")
        apd_result = evaluate_samples(apd_samples, detector, "AnyPhotoDoc")
        print(f"  F1: {apd_result['metrics']['f1']:.4f}")
        print(f"  Accuracy: {apd_result['metrics']['accuracy']:.1%}")

    # Detailed: WarpDoc per-type
    warpdoc_per_type = load_warpdoc_samples(data_dir)
    warpdoc_results: dict[str, Any] = {}
    warpdoc_all_samples: list[tuple[Path, int]] = []

    for dtype, dtype_samples in warpdoc_per_type.items():
        warpdoc_all_samples.extend(dtype_samples)
        print(f"\nEvaluating WarpDoc/{dtype} ({len(dtype_samples)} images)...")
        dtype_result = evaluate_samples(dtype_samples, detector, f"WarpDoc-{dtype}")
        warpdoc_results[dtype] = dtype_result
        print(f"  F1: {dtype_result['metrics']['f1']:.4f}")

    # WarpDoc aggregate
    warpdoc_aggregate = None
    if warpdoc_all_samples:
        perm = rng.permutation(len(warpdoc_all_samples))
        all_shuffled = [warpdoc_all_samples[i] for i in perm]
        print(f"\nEvaluating WarpDoc aggregate ({len(all_shuffled)} images)...")
        warpdoc_aggregate = evaluate_samples(all_shuffled, detector, "WarpDoc-all")
        print(f"  F1: {warpdoc_aggregate['metrics']['f1']:.4f}")

    if not apd_result and not warpdoc_aggregate:
        msg = "No warping detection datasets found"
        raise FileNotFoundError(msg)

    # Go/No-Go based on AnyPhotoDoc6300 (primary)
    threshold = THRESHOLDS["warping"]
    primary = apd_result if apd_result else warpdoc_aggregate
    metric_value = primary["metrics"][threshold.metric] if primary else 0.0
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")

    total_samples = len(apd_samples) + len(warpdoc_all_samples)
    result_dict: dict[str, Any] = {
        "detector": "WarpingDetector",
        "dataset": "anyphotodoc6300+warpdoc",
        "num_samples": total_samples,
        "primary": apd_result,
        "warpdoc_per_type": warpdoc_results,
        "warpdoc_aggregate": warpdoc_aggregate,
        "threshold": {
            "target": threshold.target,
            "metric": threshold.metric,
            "met": threshold_met,
        },
        "go_nogo": go_nogo,
        "system_info": collect_system_info(),
    }

    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "warping")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark WarpingDetector against AnyPhotoDoc6300 + WarpDoc"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/stream3_benchmarks")
    )
    parser.add_argument(
        "--max-samples", type=int, default=0, help="Max AnyPhotoDoc samples (0=all)"
    )
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        run_benchmark(args.data_dir, args.output_dir, args.max_samples, args.seed)
    except FileNotFoundError as exc:
        print(f"\nDataset not found: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
