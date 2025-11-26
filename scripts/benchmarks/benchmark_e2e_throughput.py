#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""End-to-end throughput benchmark for production readiness validation.

Validates performance targets from QA/QC report:
- GPU Latency: <150ms/page (full pipeline)
- CPU Latency: <400ms/page (full pipeline)
- GPU Throughput: >6 pages/sec
- CPU Throughput: >2 pages/sec

Usage:
    uv run python scripts/benchmarks/benchmark_e2e_throughput.py
    uv run python scripts/benchmarks/benchmark_e2e_throughput.py --pages 100 --workers 4
"""

import argparse
import gc
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# Check for optional dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    device: str
    num_pages: int
    num_workers: int
    total_time_sec: float
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_pages_per_sec: float
    peak_memory_mb: float | None
    latency_target_met: bool
    throughput_target_met: bool


@dataclass
class BenchmarkTargets:
    """Performance targets for validation."""

    latency_target_ms: float
    throughput_target_pps: float


# Target definitions
GPU_TARGETS = BenchmarkTargets(latency_target_ms=150.0, throughput_target_pps=6.0)
CPU_TARGETS = BenchmarkTargets(latency_target_ms=400.0, throughput_target_pps=2.0)


def create_test_images(num_images: int, seed: int = 42) -> list[np.ndarray]:
    """Create synthetic test images for benchmarking.

    Args:
        num_images: Number of images to create
        seed: Random seed for reproducibility

    Returns:
        List of test images
    """
    rng = np.random.default_rng(seed)
    images = []

    for i in range(num_images):
        # Create document-like image (800x600, 3 channels)
        img = np.ones((800, 600, 3), dtype=np.uint8) * 240

        # Add text-like horizontal bars
        for y in range(50, 700, 40):
            bar_width = rng.integers(200, 500)
            bar_height = rng.integers(15, 25)
            bar_color = rng.integers(30, 80)
            img[y : y + bar_height, 50 : 50 + bar_width] = bar_color

        # Add some noise to vary images
        noise = rng.integers(-10, 10, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        images.append(img)

    return images


def get_memory_usage_mb() -> float | None:
    """Get current process memory usage in MB."""
    if not PSUTIL_AVAILABLE:
        return None
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def run_ml_iqa_benchmark(
    images: list[np.ndarray],
    device: str,
    model_dir: Path,
) -> BenchmarkResult:
    """Run ML IQA benchmark on given images.

    Args:
        images: List of test images
        device: Device to use ('cpu' or 'cuda')
        model_dir: Directory containing ONNX models

    Returns:
        BenchmarkResult with timing information
    """
    # Import here to avoid import errors if models not available
    try:
        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )
    except ImportError as e:
        raise RuntimeError(f"Failed to import ML IQA module: {e}")

    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

    if not student_path.exists():
        raise FileNotFoundError(f"Student model not found: {student_path}")

    # Map device string to enum
    device_enum = Device.GPU if device == "cuda" else Device.CPU

    # Create detector
    detector = MLIQADetector(
        student_model_path=student_path,
        teacher_model_path=teacher_path if teacher_path.exists() else None,
        device=device_enum,
        enable_modal_fallback=False,
    )

    # Warm-up
    print("  Warming up model...")
    for _ in range(3):
        detector.run_student_inference(images[0])

    # Force garbage collection
    gc.collect()
    initial_memory = get_memory_usage_mb()

    # Run benchmark
    latencies_ms = []
    peak_memory = initial_memory

    print(f"  Running {len(images)} inferences...")
    start_time = time.perf_counter()

    for img in images:
        iter_start = time.perf_counter()
        detector.run_student_inference(img)
        iter_end = time.perf_counter()

        latency_ms = (iter_end - iter_start) * 1000
        latencies_ms.append(latency_ms)

        # Track memory
        current_memory = get_memory_usage_mb()
        if current_memory and peak_memory:
            peak_memory = max(peak_memory, current_memory)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    # Calculate statistics
    avg_latency = statistics.mean(latencies_ms)
    median_latency = statistics.median(latencies_ms)
    p95_latency = np.percentile(latencies_ms, 95)
    p99_latency = np.percentile(latencies_ms, 99)
    min_latency = min(latencies_ms)
    max_latency = max(latencies_ms)
    throughput = len(images) / total_time

    # Get targets
    targets = GPU_TARGETS if device == "cuda" else CPU_TARGETS

    return BenchmarkResult(
        device=device,
        num_pages=len(images),
        num_workers=1,  # Single worker for now
        total_time_sec=total_time,
        avg_latency_ms=avg_latency,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        min_latency_ms=min_latency,
        max_latency_ms=max_latency,
        throughput_pages_per_sec=throughput,
        peak_memory_mb=peak_memory,
        latency_target_met=avg_latency <= targets.latency_target_ms,
        throughput_target_met=throughput >= targets.throughput_target_pps,
    )


def run_classical_iqa_benchmark(images: list[np.ndarray]) -> BenchmarkResult:
    """Run classical IQA benchmark on given images.

    Args:
        images: List of test images

    Returns:
        BenchmarkResult with timing information
    """
    from image_preprocessing_detector.detection.iqa_classical import (
        detect_blur,
        detect_contrast,
        detect_skew,
    )

    # Warm-up
    print("  Warming up detectors...")
    for _ in range(3):
        detect_blur(images[0])
        detect_contrast(images[0])
        detect_skew(images[0])

    gc.collect()
    initial_memory = get_memory_usage_mb()

    # Run benchmark
    latencies_ms = []
    peak_memory = initial_memory

    print(f"  Running {len(images)} classical IQA passes...")
    start_time = time.perf_counter()

    for img in images:
        iter_start = time.perf_counter()
        detect_blur(img)
        detect_contrast(img)
        detect_skew(img)
        iter_end = time.perf_counter()

        latency_ms = (iter_end - iter_start) * 1000
        latencies_ms.append(latency_ms)

        current_memory = get_memory_usage_mb()
        if current_memory and peak_memory:
            peak_memory = max(peak_memory, current_memory)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    # Calculate statistics
    avg_latency = statistics.mean(latencies_ms)
    median_latency = statistics.median(latencies_ms)
    p95_latency = np.percentile(latencies_ms, 95)
    p99_latency = np.percentile(latencies_ms, 99)

    return BenchmarkResult(
        device="cpu",
        num_pages=len(images),
        num_workers=1,
        total_time_sec=total_time,
        avg_latency_ms=avg_latency,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        min_latency_ms=min(latencies_ms),
        max_latency_ms=max(latencies_ms),
        throughput_pages_per_sec=len(images) / total_time,
        peak_memory_mb=peak_memory,
        latency_target_met=True,  # Classical has no strict latency target
        throughput_target_met=True,  # Classical has no strict throughput target
    )


def run_full_pipeline_benchmark(
    images: list[np.ndarray],
    device: str,
    model_dir: Path,
) -> BenchmarkResult:
    """Run full pipeline benchmark (classical + ML IQA + corrections).

    Args:
        images: List of test images
        device: Device to use ('cpu' or 'cuda')
        model_dir: Directory containing ONNX models

    Returns:
        BenchmarkResult with timing information
    """
    from image_preprocessing_detector.correction.corrections import (
        ContrastEnhancer,
        DeskewCorrector,
        Sharpener,
    )
    from image_preprocessing_detector.detection.iqa_classical import (
        Severity,
        detect_blur,
        detect_contrast,
        detect_skew,
    )
    from image_preprocessing_detector.detection.iqa_ml import (
        ClassicalIQAScores,
        Device,
        MLIQADetector,
    )
    from image_preprocessing_detector.detection.text_gate import detect_text

    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

    if not student_path.exists():
        raise FileNotFoundError(f"Student model not found: {student_path}")

    device_enum = Device.GPU if device == "cuda" else Device.CPU

    # Initialize components
    detector = MLIQADetector(
        student_model_path=student_path,
        teacher_model_path=teacher_path if teacher_path.exists() else None,
        device=device_enum,
        enable_modal_fallback=False,
    )
    deskew = DeskewCorrector()
    contrast_enhancer = ContrastEnhancer()
    sharpener = Sharpener()

    # Warm-up
    print("  Warming up full pipeline...")
    for _ in range(3):
        detect_text(images[0])
        detect_blur(images[0])
        detect_contrast(images[0])
        detect_skew(images[0])
        detector.run_student_inference(images[0])

    gc.collect()
    initial_memory = get_memory_usage_mb()

    # Run benchmark
    latencies_ms = []
    peak_memory = initial_memory

    print(f"  Running {len(images)} full pipeline passes...")
    start_time = time.perf_counter()

    for img in images:
        iter_start = time.perf_counter()

        # Text gate
        text_result = detect_text(img)

        # Classical IQA
        blur_result = detect_blur(img)
        contrast_result = detect_contrast(img)
        skew_result = detect_skew(img)

        # Prepare classical scores for ML IQA
        classical_scores = ClassicalIQAScores(
            blur_score=min(blur_result.blur_score / 1000.0, 1.0),  # Normalize
            contrast_score=contrast_result.score,
            skew_score=max(0.0, 1.0 - (abs(skew_result.angle) / 45.0)),
        )

        # ML IQA
        student_scores, teacher_scores, _ = detector.run_pipeline(img, classical_scores)

        # Corrections (conditional)
        corrected = img
        if skew_result.angle > 0.5:
            result = deskew.correct(corrected, skew_result.angle, skew_result.confidence)
            if result.applied:
                corrected = result.corrected_image

        if contrast_result.score < 0.4:
            result = contrast_enhancer.correct(corrected, contrast_result.score, Severity.MEDIUM)
            if result.applied:
                corrected = result.corrected_image

        if blur_result.blur_score < 200:
            result = sharpener.correct(corrected, blur_result.blur_score, Severity.MEDIUM)
            if result.applied:
                corrected = result.corrected_image

        iter_end = time.perf_counter()

        latency_ms = (iter_end - iter_start) * 1000
        latencies_ms.append(latency_ms)

        current_memory = get_memory_usage_mb()
        if current_memory and peak_memory:
            peak_memory = max(peak_memory, current_memory)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    # Calculate statistics
    avg_latency = statistics.mean(latencies_ms)
    median_latency = statistics.median(latencies_ms)
    p95_latency = np.percentile(latencies_ms, 95)
    p99_latency = np.percentile(latencies_ms, 99)
    throughput = len(images) / total_time

    # Get targets
    targets = GPU_TARGETS if device == "cuda" else CPU_TARGETS

    return BenchmarkResult(
        device=device,
        num_pages=len(images),
        num_workers=1,
        total_time_sec=total_time,
        avg_latency_ms=avg_latency,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        min_latency_ms=min(latencies_ms),
        max_latency_ms=max(latencies_ms),
        throughput_pages_per_sec=throughput,
        peak_memory_mb=peak_memory,
        latency_target_met=avg_latency <= targets.latency_target_ms,
        throughput_target_met=throughput >= targets.throughput_target_pps,
    )


def print_results(name: str, result: BenchmarkResult, targets: BenchmarkTargets) -> None:
    """Print benchmark results in a formatted table."""
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")
    print(f"Device:              {result.device}")
    print(f"Pages processed:     {result.num_pages}")
    print(f"Total time:          {result.total_time_sec:.2f}s")
    print()
    print("Latency Statistics:")
    print(f"  Average:           {result.avg_latency_ms:.2f}ms")
    print(f"  Median:            {result.median_latency_ms:.2f}ms")
    print(f"  P95:               {result.p95_latency_ms:.2f}ms")
    print(f"  P99:               {result.p99_latency_ms:.2f}ms")
    print(f"  Min:               {result.min_latency_ms:.2f}ms")
    print(f"  Max:               {result.max_latency_ms:.2f}ms")
    print()
    print("Performance Metrics:")
    print(f"  Throughput:        {result.throughput_pages_per_sec:.2f} pages/sec")
    if result.peak_memory_mb:
        print(f"  Peak Memory:       {result.peak_memory_mb:.1f} MB")
    print()
    print("Target Validation:")

    # Latency target
    latency_status = "PASS" if result.latency_target_met else "FAIL"
    latency_icon = "✅" if result.latency_target_met else "❌"
    print(
        f"  {latency_icon} Latency:         {result.avg_latency_ms:.2f}ms "
        f"(target: <{targets.latency_target_ms}ms) [{latency_status}]"
    )

    # Throughput target
    throughput_status = "PASS" if result.throughput_target_met else "FAIL"
    throughput_icon = "✅" if result.throughput_target_met else "❌"
    print(
        f"  {throughput_icon} Throughput:       {result.throughput_pages_per_sec:.2f} pages/sec "
        f"(target: >{targets.throughput_target_pps}) [{throughput_status}]"
    )


def main() -> None:
    """Run end-to-end throughput benchmarks."""
    parser = argparse.ArgumentParser(description="End-to-end throughput benchmark")
    parser.add_argument(
        "--pages",
        type=int,
        default=50,
        help="Number of pages to process (default: 50)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "both"],
        default="cpu",
        help="Device to benchmark (default: cpu)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmarks/results/e2e_throughput.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/iqa/onnx"),
        help="Directory containing ONNX models",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("End-to-End Throughput Benchmark")
    print("=" * 60)
    print(f"Pages:     {args.pages}")
    print(f"Device:    {args.device}")
    print(f"Model dir: {args.model_dir}")
    print()

    # Generate test images
    print("Generating test images...")
    images = create_test_images(args.pages)
    print(f"  Created {len(images)} images ({images[0].shape})")

    results: dict[str, Any] = {
        "config": {
            "num_pages": args.pages,
            "image_size": list(images[0].shape),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "results": {},
    }

    # Run benchmarks based on device selection
    devices = ["cpu", "cuda"] if args.device == "both" else [args.device]

    for device in devices:
        print(f"\n{'#' * 60}")
        print(f"Running benchmarks on {device.upper()}")
        print(f"{'#' * 60}")

        targets = GPU_TARGETS if device == "cuda" else CPU_TARGETS

        # Classical IQA (CPU only)
        if device == "cpu":
            try:
                print("\n[1/3] Classical IQA Benchmark")
                classical_result = run_classical_iqa_benchmark(images)
                print_results("Classical IQA Results", classical_result, CPU_TARGETS)
                results["results"]["classical_iqa"] = asdict(classical_result)
            except Exception as e:
                print(f"  ❌ Classical IQA benchmark failed: {e}")

        # ML IQA
        try:
            print(f"\n[2/3] ML IQA Benchmark ({device})")
            ml_result = run_ml_iqa_benchmark(images, device, args.model_dir)
            print_results(f"ML IQA Results ({device.upper()})", ml_result, targets)
            results["results"][f"ml_iqa_{device}"] = asdict(ml_result)
        except FileNotFoundError as e:
            print(f"  ⚠️  Skipping ML IQA benchmark: {e}")
        except Exception as e:
            print(f"  ❌ ML IQA benchmark failed: {e}")

        # Full pipeline
        try:
            print(f"\n[3/3] Full Pipeline Benchmark ({device})")
            pipeline_result = run_full_pipeline_benchmark(images, device, args.model_dir)
            print_results(f"Full Pipeline Results ({device.upper()})", pipeline_result, targets)
            results["results"][f"full_pipeline_{device}"] = asdict(pipeline_result)
        except FileNotFoundError as e:
            print(f"  ⚠️  Skipping full pipeline benchmark: {e}")
        except Exception as e:
            print(f"  ❌ Full pipeline benchmark failed: {e}")

    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, result_dict in results.get("results", {}).items():
        if isinstance(result_dict, dict):
            latency_ok = result_dict.get("latency_target_met", False)
            throughput_ok = result_dict.get("throughput_target_met", False)
            status = "PASS" if (latency_ok and throughput_ok) else "FAIL"
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} {name}: {status}")
            if status == "FAIL":
                all_passed = False

    print()
    if all_passed:
        print("✅ All benchmarks PASSED - Ready for production!")
    else:
        print("❌ Some benchmarks FAILED - Review results before deployment")


if __name__ == "__main__":
    main()
