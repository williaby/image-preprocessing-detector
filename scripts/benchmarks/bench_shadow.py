#!/usr/bin/env python3
"""Benchmark ShadowDetector against SD7K (primary) + WSRD (validation).

Uses true paired ground truth: input/ images have shadows (positive),
target/ images are shadow-free (negative). This gives actual TP/TN/FP/FN
instead of proxy labels.

SD7K test split: 760 input + 760 target = 1,520 evaluations.
WSRD val split: ~100 input + ~100 target = ~200 evaluations.

Usage:
    python scripts/benchmarks/bench_shadow.py \
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

from image_preprocessing_detector.detection.shadow_detector import ShadowDetector

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


def load_paired_dataset(
    input_dir: Path,
    target_dir: Path,
    dataset_name: str,
) -> list[tuple[Path, int]]:
    """Load paired shadow/clean images with binary labels.

    Args:
        input_dir: Directory with shadow-degraded images (positive).
        target_dir: Directory with shadow-free images (negative).
        dataset_name: Name for logging.

    Returns:
        List of (image_path, label) where 1=shadow, 0=clean.
    """
    samples: list[tuple[Path, int]] = []

    if not input_dir.exists():
        logger.warning("%s input dir not found: %s", dataset_name, input_dir)
        return samples
    if not target_dir.exists():
        logger.warning("%s target dir not found: %s", dataset_name, target_dir)
        return samples

    input_files = sorted(input_dir.glob("*.png"))
    target_files = sorted(target_dir.glob("*.png"))

    samples.extend(
        (p, 1) for p in input_files
    )  # label: shadow images are positive class
    samples.extend(
        (p, 0) for p in target_files
    )  # label: clean images are negative class

    logger.info(
        "%s: %d input (shadow) + %d target (clean) = %d total",
        dataset_name,
        len(input_files),
        len(target_files),
        len(samples),
    )
    return samples


def evaluate_samples(
    samples: list[tuple[Path, int]],
    detector: ShadowDetector,
    dataset_name: str,
) -> dict[str, Any]:
    """Run shadow detector on samples and compute metrics.

    Args:
        samples: List of (image_path, label) tuples.
        detector: ShadowDetector instance.
        dataset_name: Name for reporting.

    Returns:
        Evaluation result dictionary.
    """
    y_true: list[int] = []
    y_pred: list[int] = []
    y_scores: list[float] = []
    latencies_ms: list[float] = []
    failures = 0

    for idx, (img_path, gt_label) in enumerate(samples):
        if (idx + 1) % 200 == 0:
            print(f"  [{dataset_name}] Progress: {idx + 1}/{len(samples)}")

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

        pred_label = 1 if result.has_shadows else 0
        y_true.append(gt_label)
        y_pred.append(pred_label)
        y_scores.append(result.shadow_score)

    report = compute_binary_report(y_true, y_pred, y_scores=y_scores)
    latency = compute_latency_stats(latencies_ms)

    # Score distribution for shadow vs clean
    shadow_scores = [s for s, label in zip(y_scores, y_true) if label == 1]
    clean_scores = [s for s, label in zip(y_scores, y_true) if label == 0]

    return {
        "dataset": dataset_name,
        "metrics": report,
        "latency": latency,
        "failures": failures,
        "score_distribution": {
            "shadow_mean": round(float(np.mean(shadow_scores)), 4)
            if shadow_scores
            else None,
            "shadow_std": round(float(np.std(shadow_scores)), 4)
            if shadow_scores
            else None,
            "clean_mean": round(float(np.mean(clean_scores)), 4)
            if clean_scores
            else None,
            "clean_std": round(float(np.std(clean_scores)), 4)
            if clean_scores
            else None,
        },
    }


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    seed: int,
) -> dict:
    """Run the shadow detection benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory for results.
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Shadow Detection (SD7K + WSRD)")
    print("=" * 60)

    detector = ShadowDetector()

    # Primary: SD7K test split
    sd7k_root = data_dir / "01_base_data" / "correction" / "sd7k"
    sd7k_samples = load_paired_dataset(
        sd7k_root / "test" / "input",
        sd7k_root / "test" / "target",
        "SD7K-test",
    )

    # Validation: WSRD val split
    # Actual structure: ntire2023/val_input + ntire2023/val_gt
    wsrd_root = data_dir / "01_base_data" / "correction" / "wsrd"
    wsrd_samples = load_paired_dataset(
        wsrd_root / "ntire2023" / "val_input",
        wsrd_root / "ntire2023" / "val_gt",
        "WSRD-val",
    )

    if not sd7k_samples and not wsrd_samples:
        msg = "No shadow detection datasets found"
        raise FileNotFoundError(msg)

    # Shuffle both
    rng = np.random.default_rng(seed)
    if sd7k_samples:
        perm = rng.permutation(len(sd7k_samples))
        sd7k_samples = [sd7k_samples[i] for i in perm]
    if wsrd_samples:
        perm = rng.permutation(len(wsrd_samples))
        wsrd_samples = [wsrd_samples[i] for i in perm]

    # Evaluate SD7K (primary)
    sd7k_result = None
    if sd7k_samples:
        print(f"\nEvaluating SD7K test ({len(sd7k_samples)} images)...")
        sd7k_result = evaluate_samples(sd7k_samples, detector, "SD7K-test")
        print(f"  F1: {sd7k_result['metrics']['f1']:.4f}")
        print(f"  Accuracy: {sd7k_result['metrics']['accuracy']:.1%}")

    # Evaluate WSRD (validation)
    wsrd_result = None
    if wsrd_samples:
        print(f"\nEvaluating WSRD val ({len(wsrd_samples)} images)...")
        wsrd_result = evaluate_samples(wsrd_samples, detector, "WSRD-val")
        print(f"  F1: {wsrd_result['metrics']['f1']:.4f}")
        print(f"  Accuracy: {wsrd_result['metrics']['accuracy']:.1%}")

    # Go/No-Go based on SD7K (primary)
    threshold = THRESHOLDS["shadow"]
    primary = sd7k_result if sd7k_result else wsrd_result
    metric_value = primary["metrics"][threshold.metric] if primary else 0.0
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")

    result_dict: dict[str, Any] = {
        "detector": "ShadowDetector",
        "dataset": "sd7k+wsrd",
        "num_samples": len(sd7k_samples) + len(wsrd_samples),
        "primary": sd7k_result,
        "validation": wsrd_result,
        "threshold": {
            "target": threshold.target,
            "metric": threshold.metric,
            "met": threshold_met,
        },
        "go_nogo": go_nogo,
        "system_info": collect_system_info(),
    }

    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "shadow")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark ShadowDetector against SD7K + WSRD"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/stream3_benchmarks")
    )
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        run_benchmark(args.data_dir, args.output_dir, args.seed)
    except FileNotFoundError as exc:
        print(f"\nDataset not found: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
