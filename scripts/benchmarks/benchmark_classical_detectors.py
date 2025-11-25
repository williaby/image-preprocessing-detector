#!/usr/bin/env python3
"""Benchmark classical IQA detector latency.

Measures individual and combined latency for all 8 classical CV detectors.
These detectors run on every page for ML IQA comparison and discrepancy checks.

Target: Combined <50ms per page (already achieved <25ms in Phase 4)
"""

import json
import time
from pathlib import Path
from typing import Any
from collections.abc import Callable

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    detect_binarization_quality,
    detect_bleed_through,
    detect_blur,
    detect_contrast,
    detect_illumination,
    detect_jpeg_blockiness,
    detect_noise,
    detect_skew,
)


def load_test_images(num_images: int = 50) -> list[np.ndarray]:
    """Load test images from fixtures.

    Args:
        num_images: Maximum number of images to load

    Returns:
        List of images in BGR format (OpenCV)
    """
    fixture_path = Path("tests/fixtures/phase1_validation")
    image_files = sorted(fixture_path.rglob("*.png"))[:num_images]

    if len(image_files) == 0:
        msg = f"No test images found in {fixture_path}"
        raise FileNotFoundError(msg)

    images = []
    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is not None:
            # Resize large images
            h, w = img.shape[:2]
            if max(h, w) > 1024:
                scale = 1024 / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            images.append(img)

    print(f"Loaded {len(images)} test images")
    return images


def benchmark_detector(
    detector_fn: Callable,
    _detector_name: str,
    images: list[np.ndarray],
) -> dict[str, float]:
    """Benchmark a single detector function.

    Args:
        detector_fn: Detector function to benchmark
        detector_name: Name for logging
        images: List of test images

    Returns:
        Dictionary with latency statistics (ms)
    """
    latencies = []

    for img in images:
        start = time.perf_counter()
        _ = detector_fn(img)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms

    latencies_arr = np.array(latencies)

    return {
        "mean": float(np.mean(latencies_arr)),
        "median": float(np.median(latencies_arr)),
        "p95": float(np.percentile(latencies_arr, 95)),
        "p99": float(np.percentile(latencies_arr, 99)),
        "min": float(np.min(latencies_arr)),
        "max": float(np.max(latencies_arr)),
        "std": float(np.std(latencies_arr)),
    }


def benchmark_all_detectors(images: list[np.ndarray]) -> dict[str, Any]:
    """Benchmark all detectors and measure combined latency.

    Args:
        images: List of test images

    Returns:
        Dictionary with per-detector and combined results
    """
    detectors = {
        "blur": detect_blur,
        "noise": detect_noise,
        "skew": detect_skew,
        "contrast": detect_contrast,
        "illumination": detect_illumination,
        "jpeg_blockiness": detect_jpeg_blockiness,
        "binarization": detect_binarization_quality,
        "bleed_through": detect_bleed_through,
    }

    results = {}

    # Benchmark each detector individually
    print("\nBenchmarking individual detectors:")
    print("-" * 60)

    for name, detector_fn in detectors.items():
        print(f"  {name:20s}...", end=" ", flush=True)
        result = benchmark_detector(detector_fn, name, images)
        results[name] = result
        print(f"mean={result['mean']:6.2f}ms, p95={result['p95']:6.2f}ms")

    # Benchmark combined execution (all detectors on same image)
    print("\nBenchmarking combined execution (all 8 detectors):")
    combined_latencies = []

    for img in images:
        start = time.perf_counter()

        # Run all detectors
        _ = detect_blur(img)
        _ = detect_noise(img)
        _ = detect_skew(img)
        _ = detect_contrast(img)
        _ = detect_illumination(img)
        _ = detect_jpeg_blockiness(img)
        _ = detect_binarization_quality(img)
        _ = detect_bleed_through(img)

        end = time.perf_counter()
        combined_latencies.append((end - start) * 1000)

    combined_latencies_arr = np.array(combined_latencies)

    results["combined"] = {
        "mean": float(np.mean(combined_latencies_arr)),
        "median": float(np.median(combined_latencies_arr)),
        "p95": float(np.percentile(combined_latencies_arr, 95)),
        "p99": float(np.percentile(combined_latencies_arr, 99)),
        "min": float(np.min(combined_latencies_arr)),
        "max": float(np.max(combined_latencies_arr)),
        "std": float(np.std(combined_latencies_arr)),
    }

    return results


def run_benchmark() -> dict[str, Any]:
    """Run complete classical detector benchmark.

    Returns:
        Dictionary with all benchmark results
    """
    print("=" * 60)
    print("Classical IQA Detectors Benchmark")
    print("=" * 60)

    # Load test images
    images = load_test_images(num_images=50)

    # Run benchmarks
    results = benchmark_all_detectors(images)

    # Display combined results
    print("\nCombined Results (All 8 Detectors):")
    print(f"  Mean:   {results['combined']['mean']:.2f}ms")
    print(f"  Median: {results['combined']['median']:.2f}ms")
    print(f"  P95:    {results['combined']['p95']:.2f}ms")
    print(f"  P99:    {results['combined']['p99']:.2f}ms")

    # Target validation
    target_ms = 50.0
    meets_target = results["combined"]["mean"] <= target_ms
    target_mark = "✅ PASS" if meets_target else "❌ FAIL"

    print("\nTarget Validation:")
    print(
        f"  Target (<{target_ms}ms): {target_mark} ({results['combined']['mean']:.2f}ms)"
    )

    # Improvement over target
    if meets_target:
        improvement_pct = ((target_ms - results["combined"]["mean"]) / target_ms) * 100
        print(f"  Performance: {improvement_pct:.1f}% faster than target")

    # Compile output
    output = {
        "benchmark": "classical_detectors",
        "num_images": len(images),
        "individual_detectors": {k: v for k, v in results.items() if k != "combined"},
        "combined_all_detectors": results["combined"],
        "targets": {
            "combined_target_ms": target_ms,
            "meets_target": meets_target,
        },
    }

    # Save results
    output_path = Path("docs/benchmarks/results/classical_detectors_benchmark.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to {output_path}")

    return output


if __name__ == "__main__":
    try:
        results = run_benchmark()
        print("\n" + "=" * 60)
        print("Benchmark Complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        raise
