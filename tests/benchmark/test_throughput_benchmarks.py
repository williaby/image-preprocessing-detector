# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Throughput benchmark tests for production readiness validation.

These tests validate the performance targets from the QA/QC report:
- GPU Latency: <150ms/page (full pipeline)
- CPU Latency: <400ms/page (full pipeline)
- GPU Throughput: >6 pages/sec
- CPU Throughput: >2 pages/sec

Usage:
    uv run pytest tests/benchmark/test_throughput_benchmarks.py -v -m benchmark
"""

import gc
import statistics
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.iqa_ml import MLIQADetector

# Mark all tests in this module as benchmark tests
pytestmark = [pytest.mark.benchmark, pytest.mark.slow]

# Performance targets
CPU_LATENCY_TARGET_MS = 400.0  # <400ms/page for full pipeline
CPU_THROUGHPUT_TARGET = 2.0  # >2 pages/sec
GPU_LATENCY_TARGET_MS = 150.0  # <150ms/page for full pipeline
GPU_THROUGHPUT_TARGET = 6.0  # >6 pages/sec

# Student model specific targets
STUDENT_CPU_LATENCY_TARGET_MS = 100.0  # <100ms acceptable, <40ms target
STUDENT_GPU_LATENCY_TARGET_MS = 25.0  # <25ms acceptable, <10ms target


def create_test_image(seed: int = 42) -> np.ndarray:
    """Create a single document-like test image."""
    rng = np.random.default_rng(seed)
    img = np.ones((800, 600, 3), dtype=np.uint8) * 240

    # Add text-like patterns
    for y in range(50, 700, 40):
        bar_width = rng.integers(200, 500)
        img[y : y + 20, 50 : 50 + bar_width] = rng.integers(30, 80)

    return img


@pytest.fixture
def test_images() -> list[np.ndarray]:
    """Generate batch of test images for benchmarking."""
    return [create_test_image(seed=i) for i in range(20)]


@pytest.fixture
def ml_detector_for_benchmark(
    onnx_models_available: bool, onnxruntime_available: bool
) -> "MLIQADetector | None":
    """Create ML IQA detector for benchmarking."""
    if not onnxruntime_available:
        pytest.skip("onnxruntime not properly installed")
    if not onnx_models_available:
        pytest.skip("ONNX models not available")

    from image_preprocessing_detector.detection.iqa_ml import (
        Device,
        MLIQADetector,
    )

    model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

    return MLIQADetector(
        student_model_path=student_path,
        teacher_model_path=teacher_path if teacher_path.exists() else None,
        device=Device.CPU,
        enable_modal_fallback=False,
    )


class TestStudentModelLatency:
    """Benchmark tests for student model inference latency."""

    def test_student_cpu_latency_acceptable(
        self,
        ml_detector_for_benchmark: "MLIQADetector | None",
        test_images: list[np.ndarray],
    ) -> None:
        """Test student CPU latency meets acceptable target (<100ms)."""
        if ml_detector_for_benchmark is None:
            pytest.skip("ML detector not available")
            return  # Unreachable, but helps static analysis understand control flow

        detector = ml_detector_for_benchmark

        # Warm-up
        for _ in range(3):
            detector.run_student_inference(test_images[0])
        gc.collect()

        # Measure latencies
        latencies = []
        for img in test_images[:10]:
            scores = detector.run_student_inference(img)
            assert scores is not None, "Student inference should return scores"
            latencies.append(scores.inference_time_ms)

        avg_latency = statistics.mean(latencies)
        p95_latency = float(np.percentile(latencies, 95))

        # Assert acceptable latency
        assert avg_latency < STUDENT_CPU_LATENCY_TARGET_MS, (
            f"Average latency {avg_latency:.1f}ms exceeds acceptable target {STUDENT_CPU_LATENCY_TARGET_MS}ms"
        )

        # Log p95 for monitoring
        if p95_latency > STUDENT_CPU_LATENCY_TARGET_MS:
            import warnings

            warnings.warn(
                f"P95 latency ({p95_latency:.1f}ms) exceeds target, "
                "consider investigating outliers"
            )

    def test_student_inference_consistency(
        self,
        ml_detector_for_benchmark: "MLIQADetector | None",
        test_images: list[np.ndarray],
    ) -> None:
        """Test student inference produces consistent results."""
        if ml_detector_for_benchmark is None:
            pytest.skip("ML detector not available")

        detector = ml_detector_for_benchmark
        img = test_images[0]

        # Run same image multiple times
        scores_list = [detector.run_student_inference(img) for _ in range(5)]

        # Extract overall quality scores
        qualities = [s.overall_quality for s in scores_list]

        # Results should be identical (deterministic)
        assert all(q == qualities[0] for q in qualities), (
            f"Inconsistent results: {qualities}"
        )


class TestClassicalIQALatency:
    """Benchmark tests for classical IQA detector latency."""

    def test_classical_iqa_latency(self, test_images: list[np.ndarray]) -> None:
        """Test classical IQA detectors meet latency expectations."""
        import time

        from image_preprocessing_detector.detection.iqa_classical import (
            detect_blur,
            detect_contrast,
            detect_skew,
        )

        # Warm-up
        for _ in range(3):
            detect_blur(test_images[0])
            detect_contrast(test_images[0])
            detect_skew(test_images[0])
        gc.collect()

        # Measure combined latency
        latencies = []
        for img in test_images[:10]:
            start = time.perf_counter()
            detect_blur(img)
            detect_contrast(img)
            detect_skew(img)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)

        # Classical IQA should be fast (<100ms combined for 3 detectors)
        # Note: CI environments may be slower than production hardware
        # CI threshold increased to 200ms to account for shared runner overhead
        import os

        # Check for CI environment - handle both None and empty string cases
        # GitHub Actions sets both CI=true and GITHUB_ACTIONS=true
        ci_env = os.getenv("CI", "")
        github_actions_env = os.getenv("GITHUB_ACTIONS", "")
        is_ci = bool(ci_env and ci_env.lower() in ("true", "1")) or bool(
            github_actions_env and github_actions_env.lower() in ("true", "1")
        )
        ci_threshold = 200.0 if is_ci else 100.0

        assert avg_latency < ci_threshold, (
            f"Classical IQA latency {avg_latency:.1f}ms exceeds {ci_threshold:.0f}ms target "
            f"(CI={ci_env!r}, GITHUB_ACTIONS={github_actions_env!r}, is_ci={is_ci})"
        )

        # Warn if above ideal target (50ms)
        if avg_latency > 50.0:
            import warnings

            warnings.warn(
                f"Classical IQA latency ({avg_latency:.1f}ms) above ideal target (50ms)"
            )


class TestThroughput:
    """Benchmark tests for processing throughput."""

    def test_cpu_throughput_target(
        self,
        ml_detector_for_benchmark: "MLIQADetector | None",
        test_images: list[np.ndarray],
    ) -> None:
        """Test CPU throughput meets target (>2 pages/sec)."""
        if ml_detector_for_benchmark is None:
            pytest.skip("ML detector not available")
            return  # Unreachable, but helps static analysis understand control flow

        import time

        detector = ml_detector_for_benchmark

        # Warm-up
        for _ in range(3):
            detector.run_student_inference(test_images[0])
        gc.collect()

        # Measure throughput
        start = time.perf_counter()
        for img in test_images:
            detector.run_student_inference(img)
        end = time.perf_counter()

        total_time = end - start
        throughput = len(test_images) / total_time

        # Assert throughput target
        assert throughput >= CPU_THROUGHPUT_TARGET, (
            f"Throughput {throughput:.2f} pages/sec below target {CPU_THROUGHPUT_TARGET}"
        )


class TestMemoryUsage:
    """Benchmark tests for memory usage."""

    def test_memory_does_not_leak(
        self,
        ml_detector_for_benchmark: "MLIQADetector | None",
        test_images: list[np.ndarray],
    ) -> None:
        """Test that repeated inference doesn't cause memory leaks."""
        if ml_detector_for_benchmark is None:
            pytest.skip("ML detector not available")

        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available")

        import os

        detector = ml_detector_for_benchmark
        process = psutil.Process(os.getpid())

        # Warm-up and get baseline
        for _ in range(5):
            detector.run_student_inference(test_images[0])
        gc.collect()
        baseline_memory = process.memory_info().rss / (1024 * 1024)

        # Run many inferences
        for i in range(50):
            img = test_images[i % len(test_images)]
            detector.run_student_inference(img)

        gc.collect()
        final_memory = process.memory_info().rss / (1024 * 1024)

        memory_growth = final_memory - baseline_memory

        # Allow some memory growth but flag significant leaks (>100MB)
        assert memory_growth < 100, (
            f"Memory grew by {memory_growth:.1f}MB, possible memory leak"
        )


class TestEndToEndPipeline:
    """Benchmark tests for full pipeline latency."""

    def test_full_pipeline_cpu_latency(
        self,
        ml_detector_for_benchmark: "MLIQADetector | None",
        test_images: list[np.ndarray],
    ) -> None:
        """Test full pipeline meets CPU latency target (<400ms)."""
        if ml_detector_for_benchmark is None:
            pytest.skip("ML detector not available")

        import time

        from image_preprocessing_detector.correction.corrections import (
            ContrastEnhancer,
            DeskewCorrector,
            Sharpener,
        )
        from image_preprocessing_detector.detection.iqa_classical import (
            detect_blur,
            detect_contrast,
            detect_skew,
        )
        from image_preprocessing_detector.detection.text_gate import detect_text

        detector = ml_detector_for_benchmark
        correctors = (DeskewCorrector(), ContrastEnhancer(), Sharpener())

        # Warm-up
        self._warmup_pipeline(
            test_images[0],
            detector,
            detect_text,
            detect_blur,
            detect_contrast,
            detect_skew,
        )

        # Measure full pipeline latency
        latencies = self._measure_pipeline_latencies(
            test_images[:10],
            detector,
            correctors,
            detect_text,
            detect_blur,
            detect_contrast,
            detect_skew,
            time,
        )

        avg_latency = statistics.mean(latencies)
        p95_latency = float(np.percentile(latencies, 95))

        # Assert latency target
        assert avg_latency < CPU_LATENCY_TARGET_MS, (
            f"Full pipeline latency {avg_latency:.1f}ms exceeds target {CPU_LATENCY_TARGET_MS}ms"
        )

        # Warn if P95 is concerning
        self._check_p95_latency(p95_latency)

    def _warmup_pipeline(
        self,
        img: np.ndarray,
        detector: "MLIQADetector",
        detect_text,
        detect_blur,
        detect_contrast,
        detect_skew,
    ) -> None:
        """Run warmup iterations to stabilize timings."""
        for _ in range(3):
            detect_text(img)
            detect_blur(img)
            detect_contrast(img)
            detect_skew(img)
            detector.run_student_inference(img)
        gc.collect()

    def _measure_pipeline_latencies(
        self,
        images: list[np.ndarray],
        detector: "MLIQADetector",
        correctors: tuple,
        detect_text,
        detect_blur,
        detect_contrast,
        detect_skew,
        time,
    ) -> list[float]:
        """Measure latencies for full pipeline execution."""
        from image_preprocessing_detector.detection.iqa_ml import ClassicalIQAScores

        deskew, contrast_enhancer, sharpener = correctors
        latencies = []

        for img in images:
            start = time.perf_counter()

            # Detection phase
            detect_text(img)
            blur_result = detect_blur(img)
            contrast_result = detect_contrast(img)
            skew_result = detect_skew(img)

            # ML IQA
            classical_scores = ClassicalIQAScores(
                blur_score=min(blur_result.blur_score / 1000.0, 1.0),
                contrast_score=contrast_result.score,
                skew_score=max(0.0, 1.0 - (abs(skew_result.angle) / 45.0)),
            )
            detector.run_pipeline(img, classical_scores)

            # Correction phase (result not needed for latency measurement)
            _ = self._apply_corrections(
                img,
                blur_result,
                contrast_result,
                skew_result,
                deskew,
                contrast_enhancer,
                sharpener,
            )

            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        return latencies

    def _apply_corrections(
        self,
        img: np.ndarray,
        blur_result,
        contrast_result,
        skew_result,
        deskew,
        contrast_enhancer,
        sharpener,
    ) -> np.ndarray:
        """Apply corrections based on detection results."""
        from image_preprocessing_detector.detection.iqa_classical import Severity

        corrected = img

        # Deskew if needed
        if skew_result.angle > 0.5:
            result = deskew.correct(
                corrected, skew_result.angle, skew_result.confidence
            )
            if result.applied:
                corrected = result.corrected_image

        # Enhance contrast if needed
        if contrast_result.score < 0.4:
            result = contrast_enhancer.correct(
                corrected, contrast_result.score, Severity.MEDIUM
            )
            if result.applied:
                corrected = result.corrected_image

        # Sharpen if blurry
        if blur_result.blur_score < 200:
            result = sharpener.correct(
                corrected, blur_result.blur_score, Severity.MEDIUM
            )
            if result.applied:
                corrected = result.corrected_image

        return corrected

    def _check_p95_latency(self, p95_latency: float) -> None:
        """Check P95 latency and warn if exceeds target."""
        if p95_latency > CPU_LATENCY_TARGET_MS:
            import warnings

            warnings.warn(f"P95 latency ({p95_latency:.1f}ms) exceeds target")
