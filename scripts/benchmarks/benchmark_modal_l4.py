#!/usr/bin/env python3
"""Modal L4 GPU benchmark for ML IQA models.

Benchmarks ResNet-18 student and ResNet-50 teacher models on Modal's L4 GPU
to compare cloud GPU performance against local RTX A500 GPU.

Usage:
    poetry run modal run scripts/benchmarks/benchmark_modal_l4.py

Results saved to:
    - docs/benchmarks/results/modal_l4_student_benchmark.json
    - docs/benchmarks/results/modal_l4_teacher_benchmark.json
    - docs/benchmarks/results/modal_l4_comparison.json
"""

import json
import time
from pathlib import Path

import modal

# Constants
FIXTURES_PATH = "/fixtures"

# Create Modal app for benchmarking
stub = modal.App("iqa-benchmark-l4")

# ML image with PyTorch GPU support for reliable L4 benchmarking
# ONNX Runtime GPU has library dependency issues, use PyTorch instead
benchmark_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.1.0",  # PyTorch for CUDA detection
        "onnxruntime-gpu>=1.16.0",  # ONNX Runtime with fallback support
        "numpy>=1.24.0",
        "opencv-python-headless>=4.8.0",
    )
    .add_local_dir(
        "models/iqa/onnx",
        remote_path="/models",
        copy=True,
    )
    .add_local_dir(
        "tests/fixtures/phase1_validation",
        remote_path=FIXTURES_PATH,
        copy=True,
    )
)


@stub.function(
    image=benchmark_image,
    gpu="L4",  # Modal L4 GPU
    timeout=1800,
)
def benchmark_student_l4():
    """Benchmark ResNet-18 student model on Modal L4 GPU."""
    import cv2
    import numpy as np
    import onnxruntime as ort
    import torch

    print("=" * 60)
    print("Modal L4 GPU Benchmark - Student Model (ResNet-18)")
    print("=" * 60)

    # Verify GPU availability
    print(f"\nPyTorch CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Configure ONNX Runtime providers based on CUDA availability
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if torch.cuda.is_available() else ["CPUExecutionProvider"]
    print(f"Using ONNX Runtime providers: {providers}")

    # Load model
    model_path = "/models/resnet18_student.onnx"
    print(f"\nLoading model: {model_path}")

    session = ort.InferenceSession(
        model_path,
        providers=providers,
    )

    # Get input name dynamically from model
    input_name = session.get_inputs()[0].name
    print(f"Model input name: {input_name}")

    # Load test images (use rglob to recursively find all images)
    fixture_dir = Path(FIXTURES_PATH)
    image_files = sorted(fixture_dir.rglob("*.png"))[:50]  # Limit to 50 images

    print(f"Found {len(image_files)} test image files...")
    print("Loading images...")
    images = []
    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # Resize large images to reduce memory usage
        h, w = img.shape[:2]
        if max(h, w) > 1024:
            scale = 1024 / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        images.append(img)

    print(f"Loaded {len(images)} images")

    # Warmup (10 inferences)
    print("\nWarming up model (10 inferences)...")
    for i in range(min(10, len(images))):
        img = images[i]
        # Preprocess
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
        img_float = img_resized.astype(np.float32) / 255.0
        img_norm = (img_float - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        img_chw = np.transpose(img_norm, (2, 0, 1))
        img_batch = np.expand_dims(img_chw, axis=0).astype(np.float32)

        # Inference
        _ = session.run(None, {input_name: img_batch})

    # Benchmark single inference
    print("\nBenchmarking single inference...")
    latencies = []

    for img in images:
        # Preprocess
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
        img_float = img_resized.astype(np.float32) / 255.0
        img_norm = (img_float - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        img_chw = np.transpose(img_norm, (2, 0, 1))
        img_batch = np.expand_dims(img_chw, axis=0).astype(np.float32)

        # Time inference
        start = time.perf_counter()
        _ = session.run(None, {input_name: img_batch})
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Calculate statistics
    latencies_np = np.array(latencies)
    results = {
        "model": "resnet18_student.onnx",
        "device": "Modal L4 GPU",
        "num_images": len(images),
        "single_inference": {
            "mean": float(np.mean(latencies_np)),
            "median": float(np.median(latencies_np)),
            "std": float(np.std(latencies_np)),
            "min": float(np.min(latencies_np)),
            "max": float(np.max(latencies_np)),
            "p50": float(np.percentile(latencies_np, 50)),
            "p95": float(np.percentile(latencies_np, 95)),
            "p99": float(np.percentile(latencies_np, 99)),
        },
        "target_validation": {
            "acceptable_25ms": float(np.mean(latencies_np)) <= 25.0,
            "ideal_10ms": float(np.mean(latencies_np)) <= 10.0,
        },
    }

    print(f"\n{'=' * 60}")
    print("Student Model Results (Modal L4 GPU)")
    print(f"{'=' * 60}")
    print(f"Mean latency: {results['single_inference']['mean']:.2f}ms")
    print(f"P50: {results['single_inference']['p50']:.2f}ms")
    print(f"P95: {results['single_inference']['p95']:.2f}ms")
    print(f"P99: {results['single_inference']['p99']:.2f}ms")
    print(
        f"Acceptable target (≤25ms): {'✅ PASS' if results['target_validation']['acceptable_25ms'] else '❌ FAIL'}"
    )
    print(
        f"Ideal target (≤10ms): {'✅ PASS' if results['target_validation']['ideal_10ms'] else '❌ FAIL'}"
    )

    return results


@stub.function(
    image=benchmark_image,
    gpu="L4",  # Modal L4 GPU
    timeout=1800,
)
def benchmark_teacher_l4():
    """Benchmark ResNet-50 teacher model on Modal L4 GPU."""
    import cv2
    import numpy as np
    import onnxruntime as ort
    import torch

    print("=" * 60)
    print("Modal L4 GPU Benchmark - Teacher Model (ResNet-50)")
    print("=" * 60)

    # Verify GPU availability
    print(f"\nPyTorch CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        print("⚠️  WARNING: CUDA not available, using CPU")
        providers = ["CPUExecutionProvider"]

    print(f"Using ONNX Runtime providers: {providers}")

    # Load model
    model_path = "/models/resnet50_teacher_50epoch.onnx"
    print(f"\nLoading model: {model_path}")
    session = ort.InferenceSession(
        model_path,
        providers=providers,
    )

    # Get input name dynamically from model
    input_name = session.get_inputs()[0].name
    print(f"Model input name: {input_name}")

    # Load test images (use rglob to recursively find all images)
    fixture_dir = Path(FIXTURES_PATH)
    image_files = sorted(fixture_dir.rglob("*.png"))[:50]

    print(f"Found {len(image_files)} test image files...")
    print("Loading images...")
    images = []
    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        h, w = img.shape[:2]
        if max(h, w) > 1024:
            scale = 1024 / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        images.append(img)

    print(f"Loaded {len(images)} images")

    # Warmup
    print("\nWarming up model (10 inferences)...")
    for i in range(min(10, len(images))):
        img = images[i]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
        img_float = img_resized.astype(np.float32) / 255.0
        img_norm = (img_float - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        img_chw = np.transpose(img_norm, (2, 0, 1))
        img_batch = np.expand_dims(img_chw, axis=0).astype(np.float32)
        _ = session.run(None, {input_name: img_batch})

    # Benchmark
    print("\nBenchmarking single inference...")
    latencies = []

    for img in images:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
        img_float = img_resized.astype(np.float32) / 255.0
        img_norm = (img_float - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        img_chw = np.transpose(img_norm, (2, 0, 1))
        img_batch = np.expand_dims(img_chw, axis=0).astype(np.float32)

        start = time.perf_counter()
        _ = session.run(None, {input_name: img_batch})
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Statistics
    latencies_np = np.array(latencies)
    results = {
        "model": "resnet50_teacher_50epoch.onnx",
        "device": "Modal L4 GPU",
        "num_images": len(images),
        "single_inference": {
            "mean": float(np.mean(latencies_np)),
            "median": float(np.median(latencies_np)),
            "std": float(np.std(latencies_np)),
            "min": float(np.min(latencies_np)),
            "max": float(np.max(latencies_np)),
            "p50": float(np.percentile(latencies_np, 50)),
            "p95": float(np.percentile(latencies_np, 95)),
            "p99": float(np.percentile(latencies_np, 99)),
        },
        "target_validation": {
            "target_30ms": float(np.mean(latencies_np)) <= 30.0,
        },
    }

    print(f"\n{'=' * 60}")
    print("Teacher Model Results (Modal L4 GPU)")
    print(f"{'=' * 60}")
    print(f"Mean latency: {results['single_inference']['mean']:.2f}ms")
    print(f"P50: {results['single_inference']['p50']:.2f}ms")
    print(f"P95: {results['single_inference']['p95']:.2f}ms")
    print(f"P99: {results['single_inference']['p99']:.2f}ms")
    print(
        f"Target (≤30ms): {'✅ PASS' if results['target_validation']['target_30ms'] else '❌ FAIL'}"
    )

    return results


@stub.local_entrypoint()
def main():
    """Run benchmarks and save results locally."""
    print("\n" + "=" * 60)
    print("Modal L4 GPU Benchmarking Suite")
    print("=" * 60)

    # Run student benchmark
    print("\n[1/2] Running student model benchmark on Modal L4 GPU...")
    student_results = benchmark_student_l4.remote()

    if "error" in student_results:
        print(f"❌ Student benchmark failed: {student_results['error']}")
        return

    # Save student results
    student_output = Path("docs/benchmarks/results/modal_l4_student_benchmark.json")
    student_output.parent.mkdir(parents=True, exist_ok=True)
    with student_output.open("w") as f:
        json.dump(student_results, f, indent=2)
    print(f"✅ Student results saved to {student_output}")

    # Run teacher benchmark
    print("\n[2/2] Running teacher model benchmark on Modal L4 GPU...")
    teacher_results = benchmark_teacher_l4.remote()

    if "error" in teacher_results:
        print(f"❌ Teacher benchmark failed: {teacher_results['error']}")
        return

    # Save teacher results
    teacher_output = Path("docs/benchmarks/results/modal_l4_teacher_benchmark.json")
    with teacher_output.open("w") as f:
        json.dump(teacher_results, f, indent=2)
    print(f"✅ Teacher results saved to {teacher_output}")

    # Load local GPU results for comparison
    print("\n" + "=" * 60)
    print("Comparison: Modal L4 GPU vs Local RTX A500 GPU")
    print("=" * 60)

    try:
        with open("docs/benchmarks/results/student_gpu_benchmark.json") as f:
            local_student = json.load(f)
        with open("docs/benchmarks/results/teacher_gpu_benchmark.json") as f:
            local_teacher = json.load(f)

        # Calculate speedups
        student_speedup = (
            local_student["single_inference"]["mean"]
            / student_results["single_inference"]["mean"]
        )
        teacher_speedup = (
            local_teacher["single_inference"]["mean"]
            / teacher_results["single_inference"]["mean"]
        )

        comparison = {
            "student": {
                "local_rtx_a500_ms": local_student["single_inference"]["mean"],
                "modal_l4_ms": student_results["single_inference"]["mean"],
                "speedup": student_speedup,
                "improvement": f"{(student_speedup - 1) * 100:.1f}%"
                if student_speedup > 1
                else f"{(1 - student_speedup) * 100:.1f}% slower",
            },
            "teacher": {
                "local_rtx_a500_ms": local_teacher["single_inference"]["mean"],
                "modal_l4_ms": teacher_results["single_inference"]["mean"],
                "speedup": teacher_speedup,
                "improvement": f"{(teacher_speedup - 1) * 100:.1f}%"
                if teacher_speedup > 1
                else f"{(1 - teacher_speedup) * 100:.1f}% slower",
            },
        }

        # Save comparison
        comparison_output = Path(
            "docs/benchmarks/results/modal_l4_comparison.json"
        )
        with comparison_output.open("w") as f:
            json.dump(comparison, f, indent=2)

        print("\nStudent Model (ResNet-18):")
        print(f"  Local RTX A500: {comparison['student']['local_rtx_a500_ms']:.2f}ms")
        print(f"  Modal L4:       {comparison['student']['modal_l4_ms']:.2f}ms")
        print(f"  Speedup:        {comparison['student']['speedup']:.2f}x")
        print(f"  Improvement:    {comparison['student']['improvement']}")

        print("\nTeacher Model (ResNet-50):")
        print(f"  Local RTX A500: {comparison['teacher']['local_rtx_a500_ms']:.2f}ms")
        print(f"  Modal L4:       {comparison['teacher']['modal_l4_ms']:.2f}ms")
        print(f"  Speedup:        {comparison['teacher']['speedup']:.2f}x")
        print(f"  Improvement:    {comparison['teacher']['improvement']}")

        print(f"\n✅ Comparison saved to {comparison_output}")

    except FileNotFoundError as e:
        print(f"⚠️  Could not load local GPU results for comparison: {e}")

    print("\n" + "=" * 60)
    print("Modal L4 GPU Benchmarking Complete!")
    print("=" * 60)
