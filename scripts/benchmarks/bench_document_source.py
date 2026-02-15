#!/usr/bin/env python3
"""Benchmark DocumentSourceClassifier against SmartDoc-QA + Tobacco800 + DocReal.

SmartDoc-QA images are camera-captured (CAMERA_SMARTPHONE).
Tobacco800 images are scanner-produced (SCANNER_ADF).
DocReal: distorted/ = camera, scanned/ = scanner.

Evaluates binary camera-vs-scanner accuracy.

Usage:
    python scripts/benchmarks/bench_document_source.py \
        --data-dir /mnt/e/image_detection \
        --output-dir results/stream3_benchmarks \
        --max-samples 0 \
        --seed 42
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from image_preprocessing_detector.classification.document_source_classifier import (
    DocumentSourceClassifier,
)

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


def load_samples(
    data_dir: Path,
    max_samples: int,
    seed: int,
) -> list[tuple[Path, int]]:
    """Load image paths with binary camera(1)/scanner(0) labels.

    Args:
        data_dir: Root data directory.
        max_samples: Maximum samples per source (0 = all).
        seed: Random seed.

    Returns:
        List of (image_path, label) where 1=camera, 0=scanner.
    """
    camera_images: list[Path] = []
    scanner_images: list[Path] = []

    # SmartDoc-QA -> camera
    smartdoc_dir = (
        data_dir
        / "02_benchmark_only"
        / "smartdoc-qa"
        / "Dataset SmartDoc-QA"
        / "Captured_Images"
    )
    if smartdoc_dir.exists():
        camera_images.extend(sorted(smartdoc_dir.rglob("*.jpg")))
        logger.info("SmartDoc-QA: %d camera images", len(camera_images))
    else:
        logger.warning("SmartDoc-QA not found at %s", smartdoc_dir)

    # DocReal distorted/ -> camera
    docreal_distorted = (
        data_dir / "01_base_data" / "correction" / "docreal" / "DocReal" / "distorted"
    )
    if docreal_distorted.exists():
        docreal_camera = sorted(docreal_distorted.glob("*.png"))
        camera_images.extend(docreal_camera)
        logger.info("DocReal distorted: %d camera images", len(docreal_camera))

    # Tobacco800 -> scanner
    tobacco_dir = data_dir / "01_base_data" / "degraded" / "tobacco800" / "images"
    if tobacco_dir.exists():
        scanner_images.extend(sorted(tobacco_dir.glob("*.png")))
        logger.info("Tobacco800: %d scanner images", len(scanner_images))
    else:
        logger.warning("Tobacco800 not found at %s", tobacco_dir)

    # DocReal scanned/ -> scanner
    docreal_scanned = (
        data_dir / "01_base_data" / "correction" / "docreal" / "DocReal" / "scanned"
    )
    if docreal_scanned.exists():
        docreal_scanner = sorted(docreal_scanned.glob("*.png"))
        scanner_images.extend(docreal_scanner)
        logger.info("DocReal scanned: %d scanner images", len(docreal_scanner))

    if not camera_images and not scanner_images:
        msg = "No images found for document source benchmark"
        raise FileNotFoundError(msg)

    # Subsample if requested
    rng = np.random.default_rng(seed)
    if max_samples > 0:
        if len(camera_images) > max_samples:
            idx = rng.choice(len(camera_images), size=max_samples, replace=False)
            idx.sort()
            camera_images = [camera_images[i] for i in idx]
        if len(scanner_images) > max_samples:
            idx = rng.choice(len(scanner_images), size=max_samples, replace=False)
            idx.sort()
            scanner_images = [scanner_images[i] for i in idx]

    samples: list[tuple[Path, int]] = []
    samples.extend(
        (p, 1) for p in camera_images
    )  # label: camera-captured are positive class
    samples.extend(
        (p, 0) for p in scanner_images
    )  # label: scanned docs are negative class

    # Shuffle
    perm = rng.permutation(len(samples))
    return [samples[i] for i in perm]


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_samples: int,
    seed: int,
) -> dict:
    """Run the document source classification benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory for results.
        max_samples: Max samples per source class (0 = all).
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Document Source Classification")
    print("=" * 60)

    samples = load_samples(data_dir, max_samples, seed)
    print(f"Evaluating {len(samples)} images...")

    classifier = DocumentSourceClassifier()

    y_true: list[int] = []
    y_pred: list[int] = []
    y_scores: list[float] = []
    latencies_ms: list[float] = []
    failures = 0

    for idx, (img_path, gt_label) in enumerate(samples):
        if (idx + 1) % 200 == 0:
            print(f"  Progress: {idx + 1}/{len(samples)}")

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
        result = classifier.classify(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        # Map classifier output to binary: camera=1, scanner=0
        capture_str = str(result.capture_method).lower()
        is_camera = "camera" in capture_str
        pred_label = 1 if is_camera else 0

        y_true.append(gt_label)
        y_pred.append(pred_label)
        # scanner_score: 1.0 = scanner, 0.0 = camera -> invert for camera score
        y_scores.append(1.0 - result.scanner_score)

    print(f"\nProcessed {len(samples)} images ({failures} failed to load)")

    # Metrics
    report = compute_binary_report(y_true, y_pred, y_scores=y_scores)
    print(f"\nBinary accuracy: {report['accuracy']:.1%}")
    print(f"Precision: {report['precision']:.4f}")
    print(f"Recall: {report['recall']:.4f}")
    print(f"F1: {report['f1']:.4f}")
    print(f"ROC-AUC: {report['roc_auc']}")

    latency = compute_latency_stats(latencies_ms)
    print(f"\nLatency: mean={latency['mean_ms']:.1f}ms, p95={latency['p95_ms']:.1f}ms")

    # Go/No-Go
    threshold = THRESHOLDS["document_source"]
    metric_value = report[threshold.metric]
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")

    result_dict = {
        "detector": "DocumentSourceClassifier",
        "dataset": "smartdoc-qa+tobacco800+docreal",
        "num_samples": len(samples),
        "metrics": report,
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
    saved_path = save_benchmark_result(result_dict, out_dir, "document_source")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark DocumentSourceClassifier against SmartDoc-QA + Tobacco800 + DocReal"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/stream3_benchmarks")
    )
    parser.add_argument(
        "--max-samples", type=int, default=0, help="Max samples per class (0=all)"
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
