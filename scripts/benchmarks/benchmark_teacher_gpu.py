#!/usr/bin/env python3
"""Benchmark teacher model GPU inference performance.

Measures latency metrics for ResNet-50 teacher model using ONNX Runtime on GPU (CUDA).
Teacher model is only used for escalated/high-risk cases (5-15% of pages).

Target: ≤30ms per image
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
        detector.run_teacher_inference(img)
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


def warmup_model(
    detector: MLIQADetector, warmup_image: np.ndarray, num_warmup: int = 10
) -> None:
    """Warm up model before benchmarking.

    Args:
        detector: MLIQADetector instance
        warmup_image: Image to use for warmup
        num_warmup: Number of warmup inferences
    """
    print(f"\nWarming up teacher model ({num_warmup} inferences)...")
    for _ in range(num_warmup):
        detector.run_teacher_inference(warmup_image)
    print("Warmup complete")


def run_benchmark() -> dict[str, Any]:
    """Run complete teacher CPU benchmark.

    Returns:
        Dictionary with all benchmark results
    """
    print("=" * 60)
    print("Teacher Model (GPU) Benchmark")
    print("=" * 60)

    # Initialize detector with teacher model and explicit GPU device
    teacher_path = Path("models/iqa/onnx/resnet50_teacher_50epoch.onnx")
    if not teacher_path.exists():
        msg = f"Teacher model not found: {teacher_path}"
        raise FileNotFoundError(msg)

    detector = MLIQADetector(
        teacher_model_path=teacher_path,
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
    print("\nBenchmarking teacher inference...")
    single_results = benchmark_single_inference(detector, images)

    print("\nTeacher Inference Results (GPU):")
    print(f"  Mean:   {single_results['mean']:.2f}ms")
    print(f"  Median: {single_results['median']:.2f}ms")
    print(f"  Std:    {single_results['std']:.2f}ms")
    print(f"  P50:    {single_results['p50']:.2f}ms")
    print(f"  P95:    {single_results['p95']:.2f}ms")
    print(f"  P99:    {single_results['p99']:.2f}ms")

    # Target validation
    meets_target = single_results["mean"] <= 30.0
    target_mark = "✅ PASS" if meets_target else "❌ FAIL"

    print("\nTarget Validation:")
    print(f"  Target (≤30ms): {target_mark} ({single_results['mean']:.2f}ms)")

    # Compile final results
    output = {
        "benchmark": "teacher_gpu",
        "device": "gpu",
        "model": "resnet50_teacher",
        "model_path": str(teacher_path),
        "num_images": len(images),
        "single_inference": single_results,
        "targets": {
            "target_ms": 30.0,
            "meets_target": meets_target,
            "note": "Teacher used for 5-15% of pages (escalation only)",
        },
    }

    # Save results
    output_path = Path("docs/benchmarks/results/teacher_gpu_benchmark.json")
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
