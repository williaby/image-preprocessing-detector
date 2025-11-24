#!/usr/bin/env python3
"""Benchmark ONNX model loading (cold start) times.

Measures initial model loading latency for both student and teacher models.
Important for understanding startup costs and lazy-loading decisions.

Targets: ≤2s student, ≤5s teacher
"""

import json
import time
from pathlib import Path
from typing import Any

from image_preprocessing_detector.detection.iqa_ml import Device, MLIQADetector


def benchmark_model_loading(model_path: Path, model_name: str, num_trials: int = 5) -> dict[str, float]:
    """Benchmark model loading time.

    Args:
        model_path: Path to ONNX model
        model_name: Model identifier (student/teacher)
        num_trials: Number of loading trials

    Returns:
        Dictionary with loading time statistics (seconds)
    """
    import numpy as np

    loading_times = []

    for trial in range(num_trials):
        print(f"  Trial {trial + 1}/{num_trials}...", end=" ", flush=True)

        start = time.perf_counter()

        # Create new detector instance (forces model loading)
        if "student" in model_name:
            detector = MLIQADetector(
                student_model_path=model_path,
                device=Device.CPU,
                enable_modal_fallback=False,
            )
            # Trigger lazy loading by accessing session
            _ = detector._load_student_session()
        else:
            detector = MLIQADetector(
                teacher_model_path=model_path,
                device=Device.CPU,
                enable_modal_fallback=False,
            )
            # Trigger lazy loading by accessing session
            _ = detector._load_teacher_session()

        end = time.perf_counter()
        load_time = end - start
        loading_times.append(load_time)
        print(f"{load_time:.3f}s")

        # Clean up to ensure fresh load next iteration
        del detector

    loading_times_arr = np.array(loading_times)

    return {
        "mean": float(np.mean(loading_times_arr)),
        "median": float(np.median(loading_times_arr)),
        "min": float(np.min(loading_times_arr)),
        "max": float(np.max(loading_times_arr)),
        "std": float(np.std(loading_times_arr)),
    }


def run_benchmark() -> dict[str, Any]:
    """Run complete model loading benchmark.

    Returns:
        Dictionary with all benchmark results
    """
    print("=" * 60)
    print("Model Loading Time Benchmark")
    print("=" * 60)

    # Paths
    student_path = Path("models/iqa/onnx/resnet18_student.onnx")
    teacher_path = Path("models/iqa/onnx/resnet50_teacher_50epoch.onnx")

    if not student_path.exists():
        msg = f"Student model not found: {student_path}"
        raise FileNotFoundError(msg)

    if not teacher_path.exists():
        msg = f"Teacher model not found: {teacher_path}"
        raise FileNotFoundError(msg)

    # Get file sizes
    student_size_mb = student_path.stat().st_size / (1024 * 1024)
    teacher_size_mb = teacher_path.stat().st_size / (1024 * 1024)

    print(f"\nModel sizes:")
    print(f"  Student: {student_size_mb:.1f} MB")
    print(f"  Teacher: {teacher_size_mb:.1f} MB")

    # Benchmark student loading
    print("\nBenchmarking student model loading...")
    student_results = benchmark_model_loading(student_path, "student", num_trials=5)

    print(f"\nStudent Loading Results:")
    print(f"  Mean:   {student_results['mean']:.3f}s")
    print(f"  Median: {student_results['median']:.3f}s")
    print(f"  Min:    {student_results['min']:.3f}s")
    print(f"  Max:    {student_results['max']:.3f}s")

    # Target check
    student_acceptable = student_results["mean"] <= 2.0
    student_mark = "✅ PASS" if student_acceptable else "❌ FAIL"
    print(f"  Target (≤2.0s): {student_mark} ({student_results['mean']:.3f}s)")

    # Benchmark teacher loading
    print("\nBenchmarking teacher model loading...")
    teacher_results = benchmark_model_loading(teacher_path, "teacher", num_trials=5)

    print(f"\nTeacher Loading Results:")
    print(f"  Mean:   {teacher_results['mean']:.3f}s")
    print(f"  Median: {teacher_results['median']:.3f}s")
    print(f"  Min:    {teacher_results['min']:.3f}s")
    print(f"  Max:    {teacher_results['max']:.3f}s")

    # Target check
    teacher_acceptable = teacher_results["mean"] <= 5.0
    teacher_mark = "✅ PASS" if teacher_acceptable else "❌ FAIL"
    print(f"  Target (≤5.0s): {teacher_mark} ({teacher_results['mean']:.3f}s)")

    # Combined loading (worst case: both models loaded)
    combined_mean = student_results["mean"] + teacher_results["mean"]
    print(f"\nCombined (both models): {combined_mean:.3f}s")

    # Compile results
    output = {
        "benchmark": "model_loading",
        "student": {
            "model_path": str(student_path),
            "size_mb": student_size_mb,
            "loading_time": student_results,
            "target_s": 2.0,
            "meets_target": student_acceptable,
        },
        "teacher": {
            "model_path": str(teacher_path),
            "size_mb": teacher_size_mb,
            "loading_time": teacher_results,
            "target_s": 5.0,
            "meets_target": teacher_acceptable,
        },
        "combined": {
            "total_size_mb": student_size_mb + teacher_size_mb,
            "total_loading_time_s": combined_mean,
            "note": "Worst case if both models loaded at startup",
        },
    }

    # Save results
    output_path = Path("docs/benchmarks/results/model_loading_benchmark.json")
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
