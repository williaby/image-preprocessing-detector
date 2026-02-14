#!/usr/bin/env python3
"""Benchmark OrientationDetector against synth_multiscript_v3 test split.

Evaluates 4-class orientation detection (0/90/180/270) using the synthetic
multilingual dataset with:
- 27 scripts (Tier 1/2/3) with known ground truth orientation_class
- 7 DPI tiers (72-600) for resolution sensitivity analysis
- CJK vertical text (tategaki) edge case analysis

Falls back to synth_multiscript_v2 if v3 is not available.

Usage:
    python scripts/benchmarks/bench_orientation.py \
        --data-dir /mnt/e/image_detection \
        --output-dir results/stream3_benchmarks \
        --max-samples 5000 \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.orientation_detector import (
    OrientationDetector,
)

from scripts.benchmarks.classification_metrics import (
    collect_system_info,
    compute_classification_report,
    compute_latency_stats,
    save_benchmark_result,
)
from scripts.benchmarks.stream3_config import (
    THRESHOLDS,
    ensure_output_dir,
)

logger = logging.getLogger(__name__)

ORIENTATION_CLASSES = ["0", "90", "180", "270"]

# Map OrientationAngle enum values to class index
_ANGLE_TO_IDX: dict[int, int] = {0: 0, 90: 1, 180: 2, 270: 3}

MAX_IMAGE_DIM = 800

# Script tier grouping for breakdown analysis
SCRIPT_TIERS: dict[str, list[str]] = {
    "tier1": ["Latn", "Arab", "Hans", "Cyrl", "Deva", "Hant"],
    "tier2": ["Jpan", "Kore", "Beng", "Thai", "Taml", "Grek", "Hebr", "Geor", "Armn"],
    "tier3": [],  # Remaining scripts
}


def find_dataset_root(data_dir: Path) -> Path | None:
    """Find synth_multiscript_v3 (or v2 fallback) dataset root.

    Searches local paths for the dataset test split.

    Args:
        data_dir: Root data directory.

    Returns:
        Path to dataset test split directory, or None if not found.
    """
    # Try v3 locations
    v3_candidates = [
        data_dir.parent / "03_training_datasets" / "synthetic_multiscript_v3" / "test",
        Path("/mnt/e/03_training_datasets/synthetic_multiscript_v3/test"),
    ]
    for candidate in v3_candidates:
        if candidate.exists():
            logger.info("Found synth_multiscript_v3 test at %s", candidate)
            return candidate

    # Fall back to v2
    v2_candidates = [
        data_dir.parent / "03_training_datasets" / "synthetic_multiscript" / "test",
        Path("/mnt/e/03_training_datasets/synthetic_multiscript/test"),
    ]
    for candidate in v2_candidates:
        if candidate.exists():
            logger.info("Falling back to synth_multiscript_v2 test at %s", candidate)
            return candidate

    return None


def load_orientation_samples(
    dataset_root: Path,
    max_samples: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Load images with orientation ground truth from co-located JSON metadata.

    Each image has a co-located JSON file with metadata including
    `data.geometric.orientation_class` (0/90/180/270).

    Args:
        dataset_root: Path to dataset test split directory.
        max_samples: Maximum samples (0 = all). Stratified by orientation class.
        seed: Random seed.

    Returns:
        List of sample dicts with keys: image_path, orientation_class, script,
        dpi_tier, text_direction.
    """
    samples: list[dict[str, Any]] = []

    # Discover all image files with co-located JSON metadata
    image_extensions = {".jpg", ".jpeg", ".png"}
    for img_path in sorted(dataset_root.rglob("*")):
        if img_path.suffix.lower() not in image_extensions:
            continue

        # Look for co-located JSON metadata
        json_path = img_path.with_suffix(".json")
        if not json_path.exists():
            continue

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # Extract orientation_class from nested metadata
        data = meta.get("data", meta)
        geometric = data.get("geometric", {})
        orientation_class = geometric.get("orientation_class")

        if orientation_class is None:
            continue

        # Validate orientation value
        if orientation_class not in (0, 90, 180, 270):
            continue

        # Extract additional metadata for breakdowns
        language = data.get("language", {})
        script_code = language.get("iso15924_script_code", "Unknown")
        text_direction = language.get("text_direction", "ltr")

        rendering = data.get("rendering", {})
        dpi = rendering.get("target_dpi", 300)

        samples.append({
            "image_path": img_path,
            "orientation_class": orientation_class,
            "script": script_code,
            "text_direction": text_direction,
            "dpi": dpi,
        })

    logger.info("Found %d images with orientation metadata", len(samples))

    if not samples:
        return samples

    # Stratified sampling by orientation class
    if max_samples > 0 and len(samples) > max_samples:
        rng = np.random.default_rng(seed)
        per_class: dict[int, list[int]] = defaultdict(list)
        for idx, s in enumerate(samples):
            per_class[s["orientation_class"]].append(idx)

        per_class_budget = max_samples // 4
        selected_indices: list[int] = []

        for cls in (0, 90, 180, 270):
            cls_indices = per_class.get(cls, [])
            if len(cls_indices) > per_class_budget:
                chosen = rng.choice(cls_indices, size=per_class_budget, replace=False)
                selected_indices.extend(chosen)
            else:
                selected_indices.extend(cls_indices)

        selected_indices.sort()
        samples = [samples[i] for i in selected_indices]
        logger.info("Stratified to %d samples", len(samples))

    return samples


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_samples: int,
    seed: int,
) -> dict:
    """Run the orientation detection benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory.
        max_samples: Max samples (0=all, stratified by class).
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Orientation Detection")
    print("=" * 60)

    dataset_root = find_dataset_root(data_dir)
    if dataset_root is None:
        msg = (
            "synth_multiscript_v3 test split not found. "
            "Check /mnt/e/03_training_datasets/synthetic_multiscript_v3/test/"
        )
        raise FileNotFoundError(msg)

    samples = load_orientation_samples(dataset_root, max_samples, seed)
    if not samples:
        msg = "No valid orientation samples found with co-located JSON metadata"
        raise RuntimeError(msg)

    print(f"Evaluating {len(samples)} images from {dataset_root}...")

    detector = OrientationDetector()
    rng = np.random.default_rng(seed)

    # Shuffle
    perm = rng.permutation(len(samples))
    samples = [samples[i] for i in perm]

    # Overall evaluation
    y_true: list[int] = []
    y_pred: list[int] = []
    latencies_ms: list[float] = []
    failures = 0

    # Per-script and per-DPI tracking
    per_script_true: dict[str, list[int]] = defaultdict(list)
    per_script_pred: dict[str, list[int]] = defaultdict(list)
    per_dpi_true: dict[int, list[int]] = defaultdict(list)
    per_dpi_pred: dict[int, list[int]] = defaultdict(list)
    vertical_text_true: list[int] = []
    vertical_text_pred: list[int] = []

    for idx, sample in enumerate(samples):
        if (idx + 1) % 500 == 0:
            print(f"  Progress: {idx + 1}/{len(samples)}")

        img = cv2.imread(str(sample["image_path"]))
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

        gt_class = _ANGLE_TO_IDX[sample["orientation_class"]]
        pred_angle = result.detected_angle
        # Extract numeric angle from enum
        if hasattr(pred_angle, "value"):
            pred_angle_int = pred_angle.value
        else:
            pred_angle_int = int(pred_angle)
        pred_class = _ANGLE_TO_IDX.get(pred_angle_int, 0)

        y_true.append(gt_class)
        y_pred.append(pred_class)

        # Track per-script
        script = sample["script"]
        per_script_true[script].append(gt_class)
        per_script_pred[script].append(pred_class)

        # Track per-DPI
        dpi = sample["dpi"]
        per_dpi_true[dpi].append(gt_class)
        per_dpi_pred[dpi].append(pred_class)

        # Track CJK vertical text
        if sample["text_direction"] == "ttb":
            vertical_text_true.append(gt_class)
            vertical_text_pred.append(pred_class)

    print(f"\nProcessed {len(samples)} images ({failures} failed to load)")

    # Overall metrics
    overall_report = compute_classification_report(y_true, y_pred, ORIENTATION_CLASSES)
    print(f"\nOverall accuracy: {overall_report['accuracy']:.1%}")
    print(f"Macro F1: {overall_report['macro_f1']:.4f}")
    print(f"Cohen's kappa: {overall_report['cohens_kappa']:.4f}")

    # Per-script breakdowns
    per_script_accuracy: dict[str, dict[str, Any]] = {}
    for script in sorted(per_script_true.keys()):
        if len(per_script_true[script]) >= 10:  # Skip tiny groups
            script_report = compute_classification_report(
                per_script_true[script], per_script_pred[script], ORIENTATION_CLASSES,
            )
            per_script_accuracy[script] = {
                "accuracy": script_report["accuracy"],
                "num_samples": script_report["num_samples"],
            }
            print(f"  {script}: {script_report['accuracy']:.1%} ({script_report['num_samples']} samples)")

    # Per-DPI breakdowns
    per_dpi_accuracy: dict[str, dict[str, Any]] = {}
    for dpi in sorted(per_dpi_true.keys()):
        if len(per_dpi_true[dpi]) >= 10:
            dpi_report = compute_classification_report(
                per_dpi_true[dpi], per_dpi_pred[dpi], ORIENTATION_CLASSES,
            )
            per_dpi_accuracy[str(dpi)] = {
                "accuracy": dpi_report["accuracy"],
                "num_samples": dpi_report["num_samples"],
            }
            print(f"  DPI {dpi}: {dpi_report['accuracy']:.1%} ({dpi_report['num_samples']} samples)")

    # CJK vertical text analysis
    vertical_text_report = None
    if len(vertical_text_true) >= 5:
        vertical_text_report = compute_classification_report(
            vertical_text_true, vertical_text_pred, ORIENTATION_CLASSES,
        )
        print(f"\nCJK vertical text (ttb): {vertical_text_report['accuracy']:.1%} ({len(vertical_text_true)} samples)")

    latency = compute_latency_stats(latencies_ms)
    print(f"\nLatency: mean={latency['mean_ms']:.1f}ms, p95={latency['p95_ms']:.1f}ms")

    # Go/No-Go
    threshold = THRESHOLDS["orientation"]
    metric_value = overall_report[threshold.metric]
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")

    result_dict: dict[str, Any] = {
        "detector": "OrientationDetector",
        "dataset": "synth_multiscript_v3",
        "dataset_root": str(dataset_root),
        "num_samples": len(samples),
        "metrics": {
            "overall": overall_report,
            "per_script": per_script_accuracy,
            "per_dpi": per_dpi_accuracy,
            "vertical_text": vertical_text_report,
        },
        "latency": latency,
        "failure_rate": round(failures / len(samples), 4) if samples else 0.0,
        "threshold": {
            "target": threshold.target,
            "metric": threshold.metric,
            "met": threshold_met,
        },
        "go_nogo": go_nogo,
        "system_info": collect_system_info(),
    }

    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "orientation")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark OrientationDetector against synth_multiscript_v3"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/stream3_benchmarks"))
    parser.add_argument("--max-samples", type=int, default=5000, help="Max samples (0=all, stratified)")
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
