#!/usr/bin/env python3
"""Descriptive statistics for Tier 3 detectors (no ground truth labels).

Runs detectors that lack labeled ground truth and reports score distributions.
No Go/No-Go threshold is applied - results are for manual review only.

Detectors:
    - BlankPageDetector: Synthetic blank + content images + random real docs
    - CodeDetector: Score distribution on random document images
    - TableComplexityAnalyzer: Run on random document images, report complexity scores

Usage:
    python scripts/benchmarks/bench_descriptive.py \
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

from image_preprocessing_detector.detection.blank_page_detector import (
    BlankPageDetector,
)
from image_preprocessing_detector.detection.code_detector import CodeDetector
from image_preprocessing_detector.detection.table_complexity import (
    TableComplexityAnalyzer,
)

from scripts.benchmarks.classification_metrics import (
    collect_system_info,
    compute_binary_report,
    compute_latency_stats,
    save_benchmark_result,
)
from scripts.benchmarks.stream3_config import ensure_output_dir

logger = logging.getLogger(__name__)

MAX_IMAGE_DIM = 800


def create_synthetic_images(
    num_blank: int = 100,
    num_content: int = 100,
    seed: int = 42,
) -> list[tuple[np.ndarray, int]]:
    """Create synthetic blank and content images for BlankPageDetector testing.

    Args:
        num_blank: Number of blank (white/near-white) images.
        num_content: Number of content (text-like patterns) images.
        seed: Random seed.

    Returns:
        List of (image, label) where 1=blank, 0=content.
    """
    rng = np.random.default_rng(seed)
    samples: list[tuple[np.ndarray, int]] = []

    # Blank images: white with slight noise
    for _ in range(num_blank):
        img = np.full((800, 600, 3), 255, dtype=np.uint8)
        noise = rng.integers(-5, 6, size=img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        samples.append((img, 1))  # blank = positive

    # Content images: horizontal lines simulating text
    for _ in range(num_content):
        img = np.full((800, 600, 3), 255, dtype=np.uint8)
        num_lines = rng.integers(10, 40)
        for _ in range(num_lines):
            y = int(rng.integers(50, 750))
            x_start = int(rng.integers(30, 100))
            x_end = int(rng.integers(400, 570))
            thickness = int(rng.integers(1, 3))
            color = int(rng.integers(0, 80))
            cv2.line(img, (x_start, y), (x_end, y), (color, color, color), thickness)
        samples.append((img, 0))  # content = negative

    return samples


def load_random_real_images(
    data_dir: Path,
    num_images: int,
    seed: int,
) -> list[Path]:
    """Load random real document images from DIQA-5000 or Tobacco800.

    Args:
        data_dir: Root data directory.
        num_images: Number of images to sample.
        seed: Random seed.

    Returns:
        List of image paths.
    """
    rng = np.random.default_rng(seed)

    # Try DIQA-5000 first
    diqa_dir = data_dir / "02_benchmark_only" / "diqa-5000"
    if diqa_dir.exists():
        images = sorted(diqa_dir.rglob("*.jpg"))
        if images:
            if len(images) > num_images:
                idx = rng.choice(len(images), size=num_images, replace=False)
                images = [images[i] for i in sorted(idx)]
            logger.info("Loaded %d DIQA-5000 images", len(images))
            return images

    # Fallback: Tobacco800
    tobacco_dir = data_dir / "01_base_data" / "degraded" / "tobacco800" / "images"
    if tobacco_dir.exists():
        images = sorted(tobacco_dir.glob("*.png"))
        if images:
            if len(images) > num_images:
                idx = rng.choice(len(images), size=num_images, replace=False)
                images = [images[i] for i in sorted(idx)]
            logger.info("Loaded %d Tobacco800 images", len(images))
            return images

    logger.warning("No real document images found for descriptive stats")
    return []


def benchmark_blank_page(
    data_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Benchmark BlankPageDetector on synthetic + real images.

    Args:
        data_dir: Root data directory.
        seed: Random seed.

    Returns:
        Benchmark results dict.
    """
    print("\n--- BlankPageDetector ---")

    detector = BlankPageDetector()

    # Synthetic evaluation (has ground truth)
    synthetic = create_synthetic_images(num_blank=100, num_content=100, seed=seed)
    y_true: list[int] = []
    y_pred: list[int] = []
    y_scores: list[float] = []
    latencies_ms: list[float] = []

    for img, label in synthetic:
        start = time.perf_counter()
        result = detector.detect(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        y_true.append(label)
        y_pred.append(1 if result.is_blank else 0)
        y_scores.append(result.blankness_score)

    synth_report = compute_binary_report(y_true, y_pred, y_scores=y_scores)
    print(f"Synthetic accuracy: {synth_report['accuracy']:.1%}")
    print(f"Synthetic F1: {synth_report['f1']:.4f}")

    # Real document images (no GT - should all be non-blank)
    real_images = load_random_real_images(data_dir, num_images=200, seed=seed)
    false_blank_count = 0
    real_scores: list[float] = []

    for img_path in real_images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        height, width = img.shape[:2]
        if max(height, width) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

        result = detector.detect(img)
        real_scores.append(result.blankness_score)
        if result.is_blank:
            false_blank_count += 1

    real_false_positive_rate = false_blank_count / len(real_images) if real_images else 0.0
    print(f"Real docs false blank rate: {real_false_positive_rate:.1%} ({false_blank_count}/{len(real_images)})")

    return {
        "detector": "BlankPageDetector",
        "synthetic_metrics": synth_report,
        "synthetic_latency": compute_latency_stats(latencies_ms),
        "real_docs_tested": len(real_images),
        "real_false_blank_count": false_blank_count,
        "real_false_positive_rate": round(real_false_positive_rate, 4),
        "real_score_distribution": {
            "mean": round(float(np.mean(real_scores)), 4) if real_scores else None,
            "std": round(float(np.std(real_scores)), 4) if real_scores else None,
            "max": round(float(np.max(real_scores)), 4) if real_scores else None,
        },
    }


def benchmark_code_detector(
    data_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Run CodeDetector on random real images and report distributions.

    Args:
        data_dir: Root data directory.
        seed: Random seed.

    Returns:
        Benchmark results dict.
    """
    print("\n--- CodeDetector ---")

    detector = CodeDetector()
    images = load_random_real_images(data_dir, num_images=200, seed=seed + 1)

    scores: list[float] = []
    positive_count = 0
    latencies_ms: list[float] = []
    high_confidence_samples: list[dict[str, Any]] = []

    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        height, width = img.shape[:2]
        if max(height, width) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

        start = time.perf_counter()
        result = detector.detect(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        scores.append(result.code_confidence)
        if result.has_code:
            positive_count += 1
            if result.code_confidence > 0.7:
                high_confidence_samples.append({
                    "path": str(img_path.name),
                    "confidence": round(result.code_confidence, 4),
                })

    detection_rate = positive_count / len(images) if images else 0.0
    print(f"Detection rate: {detection_rate:.1%} ({positive_count}/{len(images)})")
    print(f"High-confidence detections: {len(high_confidence_samples)}")

    return {
        "detector": "CodeDetector",
        "num_images": len(images),
        "positive_count": positive_count,
        "detection_rate": round(detection_rate, 4),
        "score_distribution": {
            "mean": round(float(np.mean(scores)), 4) if scores else None,
            "std": round(float(np.std(scores)), 4) if scores else None,
            "p50": round(float(np.median(scores)), 4) if scores else None,
            "p95": round(float(np.percentile(scores, 95)), 4) if scores else None,
            "max": round(float(np.max(scores)), 4) if scores else None,
        },
        "high_confidence_samples": high_confidence_samples[:10],
        "latency": compute_latency_stats(latencies_ms),
    }


def benchmark_table_complexity(
    data_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Run TableComplexityAnalyzer on random real images.

    Args:
        data_dir: Root data directory.
        seed: Random seed.

    Returns:
        Benchmark results dict.
    """
    print("\n--- TableComplexityAnalyzer ---")

    analyzer = TableComplexityAnalyzer()
    images = load_random_real_images(data_dir, num_images=200, seed=seed + 2)

    complexity_scores: list[float] = []
    row_counts: list[int] = []
    col_counts: list[int] = []
    latencies_ms: list[float] = []

    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        height, width = img.shape[:2]
        if max(height, width) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

        start = time.perf_counter()
        result = analyzer.analyze(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        complexity_scores.append(result.complexity_score)
        row_counts.append(result.estimated_rows)
        col_counts.append(result.estimated_columns)

    print(f"Analyzed {len(complexity_scores)} images")

    return {
        "detector": "TableComplexityAnalyzer",
        "num_images": len(complexity_scores),
        "complexity_distribution": {
            "mean": round(float(np.mean(complexity_scores)), 4) if complexity_scores else None,
            "std": round(float(np.std(complexity_scores)), 4) if complexity_scores else None,
            "p50": round(float(np.median(complexity_scores)), 4) if complexity_scores else None,
            "p95": round(float(np.percentile(complexity_scores, 95)), 4) if complexity_scores else None,
        },
        "row_count_distribution": {
            "mean": round(float(np.mean(row_counts)), 1) if row_counts else None,
            "max": max(row_counts) if row_counts else None,
        },
        "col_count_distribution": {
            "mean": round(float(np.mean(col_counts)), 1) if col_counts else None,
            "max": max(col_counts) if col_counts else None,
        },
        "latency": compute_latency_stats(latencies_ms),
    }


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    seed: int,
) -> dict:
    """Run all descriptive benchmarks.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory.
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Descriptive Stats (Tier 3)")
    print("=" * 60)
    print("No Go/No-Go thresholds. Results for manual review.\n")

    blank_result = benchmark_blank_page(data_dir, seed)
    code_result = benchmark_code_detector(data_dir, seed)
    table_result = benchmark_table_complexity(data_dir, seed)

    result_dict: dict[str, Any] = {
        "detector": "Tier3_Descriptive",
        "note": "No Go/No-Go thresholds. Results for manual review only.",
        "blank_page": blank_result,
        "code_detector": code_result,
        "table_complexity": table_result,
        "system_info": collect_system_info(),
    }

    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "descriptive")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Descriptive stats for Tier 3 detectors"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/stream3_benchmarks"))
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    run_benchmark(args.data_dir, args.output_dir, args.seed)


if __name__ == "__main__":
    main()
