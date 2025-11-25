#!/usr/bin/env python3
"""Benchmark student model GPU inference performance.

Measures latency metrics for ResNet-18 student model using ONNX Runtime on GPU (CUDA).
Tests single-image and batch inference performance.

Target: ≤25ms (acceptable), ≤10ms (ideal) per image
"""

import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_ml import Device, MLIQADetector


def load_test_images(num_images: int = 50) -> list[np.ndarray]:
    """Load test images from fixtures.

    Args:
        num_images: Maximum number of images to load (default: 50 for memory efficiency)

    Returns:
        List of images in BGR format (OpenCV), resized to reduce memory footprint
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
            # Resize large images to reduce memory usage (max 1024x1024)
            h, w = img.shape[:2]
            if max(h, w) > 1024:
                scale = 1024 / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            images.append(img)

    print(f"Loaded {len(images)} test images from {fixture_path}")
    return images


def benchmark_single_inference(
    detector: MLIQADetector,
    images: list[np.ndarray],
) -> dict[str, float]:
    """Benchmark single-image inference.

    Args:
        detector: MLIQADetector instance
        images: List of test images

    Returns:
        Dictionary with latency statistics (ms)
    """
    latencies = []

    for img in images:
        start = time.perf_counter()
        detector.run_student_inference(img)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms

    latencies_arr = np.array(latencies)

    return {
        "mean": float(np.mean(latencies_arr)),
        "median": float(np.median(latencies_arr)),
        "std": float(np.std(latencies_arr)),
        "min": float(np.min(latencies_arr)),
        "max": float(np.max(latencies_arr)),
        "p50": float(np.percentile(latencies_arr, 50)),
        "p95": float(np.percentile(latencies_arr, 95)),
        "p99": float(np.percentile(latencies_arr, 99)),
    }


def benchmark_batch_inference(
    detector: MLIQADetector,
    images: list[np.ndarray],
    batch_size: int,
) -> dict[str, float]:
    """Benchmark batch inference.

    Args:
        detector: MLIQADetector instance
        images: List of test images
        batch_size: Number of images per batch

    Returns:
        Dictionary with per-image latency statistics (ms)
    """
    latencies = []

    for i in range(0, len(images), batch_size):
        batch = images[i : i + batch_size]

        start = time.perf_counter()
        for img in batch:
            detector.run_student_inference(img)
        end = time.perf_counter()

        # Calculate per-image latency
        per_image_latency = ((end - start) / len(batch)) * 1000
        latencies.append(per_image_latency)

    latencies_arr = np.array(latencies)

    return {
        "mean": float(np.mean(latencies_arr)),
        "p95": float(np.percentile(latencies_arr, 95)),
        "p99": float(np.percentile(latencies_arr, 99)),
    }


def warmup_model(
    detector: MLIQADetector, warmup_image: np.ndarray, num_warmup: int = 10
) -> None:
    """Warm up model before benchmarking.

    Args:
        detector: MLIQADetector instance
        warmup_image: Image to use for warmup
        num_warmup: Number of warmup inferences
    """
    print(f"\nWarming up model ({num_warmup} inferences)...")
    for _ in range(num_warmup):
        detector.run_student_inference(warmup_image)
    print("Warmup complete")


def run_benchmark() -> dict[str, Any]:
    """Run complete CPU benchmark.

    Returns:
        Dictionary with all benchmark results
    """
    print("=" * 60)
    print("Student Model (GPU) Benchmark")
    print("=" * 60)

    # Initialize detector with explicit GPU device
    student_path = Path("models/iqa/onnx/resnet18_student.onnx")
    if not student_path.exists():
        msg = f"Student model not found: {student_path}"
        raise FileNotFoundError(msg)

    detector = MLIQADetector(
        student_model_path=student_path,
        device=Device.GPU,
        enable_modal_fallback=False,
    )

    # Load test images (reduced to 50 for memory efficiency)
    print("\nLoading test images...")
    images = load_test_images(num_images=50)

    if len(images) == 0:
        msg = "No test images loaded"
        raise ValueError(msg)

    # Warm up model
    warmup_model(detector, images[0])

    # Benchmark single inference
    print("\nBenchmarking single inference...")
    single_results = benchmark_single_inference(detector, images)

    print("\nSingle Inference Results:")
    print(f"  Mean:   {single_results['mean']:.2f}ms")
    print(f"  Median: {single_results['median']:.2f}ms")
    print(f"  Std:    {single_results['std']:.2f}ms")
    print(f"  P50:    {single_results['p50']:.2f}ms")
    print(f"  P95:    {single_results['p95']:.2f}ms")
    print(f"  P99:    {single_results['p99']:.2f}ms")

    # Target validation (GPU targets: ≤25ms acceptable, ≤10ms ideal)
    print("\nTarget Validation:")
    acceptable = single_results["mean"] <= 25.0
    ideal = single_results["mean"] <= 10.0

    acceptable_mark = "✅ PASS" if acceptable else "❌ FAIL"
    ideal_mark = "✅ PASS" if ideal else "❌ MISS"

    print(f"  Acceptable (≤25ms): {acceptable_mark} ({single_results['mean']:.1f}ms)")
    print(f"  Ideal (≤10ms):      {ideal_mark} ({single_results['mean']:.1f}ms)")

    # Benchmark batch inference
    batch_sizes = [1, 4, 8, 16, 32]
    print("\nBenchmarking batch inference...")

    batch_results = {}
    for batch_size in batch_sizes:
        results = benchmark_batch_inference(detector, images, batch_size)
        batch_results[batch_size] = results
        print(
            f"  Batch {batch_size:2d}: mean={results['mean']:.2f}ms, "
            f"p95={results['p95']:.2f}ms"
        )

    # Compile final results
    output = {
        "benchmark": "student_gpu",
        "device": "gpu",
        "model": "resnet18_student",
        "model_path": str(student_path),
        "num_images": len(images),
        "single_inference": single_results,
        "batch_inference": {
            str(k): v for k, v in batch_results.items()
        },  # JSON requires string keys
        "targets": {
            "acceptable_ms": 25.0,
            "ideal_ms": 10.0,
            "meets_acceptable": acceptable,
            "meets_ideal": ideal,
        },
    }

    # Save results
    output_path = Path("docs/benchmarks/results/student_gpu_benchmark.json")
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
