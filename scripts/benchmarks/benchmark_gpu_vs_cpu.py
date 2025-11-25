#!/usr/bin/env python3
"""GPU vs CPU speedup comparison.

Loads existing benchmark results and calculates speedup factors.
"""

import json
from pathlib import Path


def load_results(filepath: Path) -> dict:
    """Load benchmark results JSON file."""
    with open(filepath) as f:
        return json.load(f)


def calculate_speedup(cpu_ms: float, gpu_ms: float) -> float:
    """Calculate speedup factor (CPU time / GPU time)."""
    return cpu_ms / gpu_ms


def run_comparison():
    """Compare GPU vs CPU performance."""
    print("=" * 60)
    print("GPU vs CPU Speedup Analysis")
    print("=" * 60)

    results_dir = Path("docs/benchmarks/results")

    # Load all results
    student_cpu = load_results(results_dir / "student_cpu_benchmark.json")
    student_gpu = load_results(results_dir / "student_gpu_benchmark.json")
    teacher_cpu = load_results(results_dir / "teacher_cpu_benchmark.json")
    teacher_gpu = load_results(results_dir / "teacher_gpu_benchmark.json")

    # Student comparison
    student_cpu_mean = student_cpu["single_inference"]["mean"]
    student_gpu_mean = student_gpu["single_inference"]["mean"]
    student_speedup = calculate_speedup(student_cpu_mean, student_gpu_mean)

    print("\nStudent Model (ResNet-18):")
    print(f"  CPU:     {student_cpu_mean:.2f}ms")
    print(f"  GPU:     {student_gpu_mean:.2f}ms")
    print(f"  Speedup: {student_speedup:.2f}x")

    if student_speedup < 1.0:
        print(f"  ⚠️  GPU is SLOWER than CPU ({1 / student_speedup:.2f}x slower)")
    elif student_speedup < 2.0:
        print("  ⚠️  Modest speedup (<2x)")
    else:
        print("  ✅ Good speedup")

    # Teacher comparison
    teacher_cpu_mean = teacher_cpu["single_inference"]["mean"]
    teacher_gpu_mean = teacher_gpu["single_inference"]["mean"]
    teacher_speedup = calculate_speedup(teacher_cpu_mean, teacher_gpu_mean)

    print("\nTeacher Model (ResNet-50):")
    print(f"  CPU:     {teacher_cpu_mean:.2f}ms")
    print(f"  GPU:     {teacher_gpu_mean:.2f}ms")
    print(f"  Speedup: {teacher_speedup:.2f}x")

    if teacher_speedup < 1.0:
        print(f"  ⚠️  GPU is SLOWER than CPU ({1 / teacher_speedup:.2f}x slower)")
    elif teacher_speedup < 2.0:
        print("  ⚠️  Modest speedup (<2x)")
    else:
        print("  ✅ Good speedup")

    # Summary
    print("\n" + "=" * 60)
    print("Summary & Recommendations")
    print("=" * 60)

    print("\n**Key Findings**:")
    print(f"- Student GPU provides {student_speedup:.2f}x speedup over CPU")
    print(f"- Teacher GPU provides {teacher_speedup:.2f}x speedup over CPU")

    # Analysis
    print("\n**Analysis**:")
    if student_speedup < 1.5:
        print("- Student model shows minimal GPU benefit")
        print("  → Small model (48MB) dominated by CPU-GPU transfer overhead")
        print("  → CPU inference is highly optimized for small models")
        print("  → Recommendation: Use CPU for student inference")

    if teacher_speedup < 2.0:
        print("- Teacher model shows modest GPU benefit")
        print("  → Larger model (106MB) but still below GPU sweet spot")
        print("  → 400ms GPU latency still too slow for production")
        print("  → Recommendation: Limit teacher usage or optimize model")

    # Save comparison
    output = {
        "student": {
            "cpu_ms": student_cpu_mean,
            "gpu_ms": student_gpu_mean,
            "speedup": student_speedup,
        },
        "teacher": {
            "cpu_ms": teacher_cpu_mean,
            "gpu_ms": teacher_gpu_mean,
            "speedup": teacher_speedup,
        },
        "analysis": {
            "student_recommendation": "Use CPU (minimal GPU benefit)"
            if student_speedup < 1.5
            else "Use GPU",
            "teacher_recommendation": "Limit usage (both CPU/GPU too slow)"
            if teacher_gpu_mean > 100
            else "Use GPU",
        },
    }

    output_path = Path("docs/benchmarks/results/gpu_vs_cpu_comparison.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to {output_path}")


if __name__ == "__main__":
    try:
        run_comparison()
        print("\n" + "=" * 60)
        print("Comparison Complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        raise
