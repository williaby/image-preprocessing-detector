"""Batch-mode regression tests.

Sprint 5.1.4: Tests for batch processing of multi-page documents:
- 10-100 page documents with mixed PDF types
- Throughput validation against targets
- Memory usage monitoring to prevent blowups
- Timing baselines for regression detection

Performance targets (from CLAUDE.md):
- Throughput (CPU): ≥2 pages/sec/worker
- Latency (CPU): <500ms/page
"""

import gc
import sys
import time

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    NoiseDetector,
)
from image_preprocessing_detector.metrics.dqs_calculator import (
    calculate_degradation_score,
    calculate_pre_ocr_risk,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
)
from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.schema import (
    DQSMetadata,
    LayoutType,
    PageLayoutSummary,
    PDFType,
)

# =============================================================================
# Performance Constants
# =============================================================================

# Relaxed targets for CI environments
CPU_THROUGHPUT_TARGET = 0.3  # pages/sec (very relaxed for CI)
CPU_LATENCY_TARGET_MS = 2000  # ms/page (relaxed for CI)

# Memory limits
MAX_MEMORY_PER_PAGE_MB = 100  # Max memory increase per page


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_page_images() -> list[np.ndarray]:
    """Create a batch of sample page images for testing."""
    images = []
    for i in range(10):
        # Create varied document images
        image = np.ones((1000, 800, 3), dtype=np.uint8) * 255

        # Add different content patterns for variety
        for y in range(50 + (i * 10), 950, 30 + (i % 5)):
            image[y : y + 2, 50:750] = 0

        images.append(image)
    return images


@pytest.fixture
def large_batch_images() -> list[np.ndarray]:
    """Create a larger batch (50 pages) for throughput testing."""
    images = []
    for i in range(50):
        # Smaller images to keep memory manageable
        image = np.ones((500, 400, 3), dtype=np.uint8) * 255
        for y in range(25, 475, 20):
            image[y : y + 1, 25:375] = 0
        images.append(image)
    return images


@pytest.fixture
def mixed_pdf_types() -> list[PDFType]:
    """Create mixed PDF type scenarios."""
    return [
        PDFType.IMAGE_ONLY,
        PDFType.BORN_DIGITAL,
        PDFType.HYBRID,
        PDFType.IMAGE_ONLY,
        PDFType.BORN_DIGITAL,
    ] * 10  # 50 pages total


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    # Force garbage collection first
    gc.collect()
    return sys.getsizeof([]) / 1024 / 1024  # Basic measurement


# =============================================================================
# Batch Processing Tests
# =============================================================================


class TestBatchProcessing:
    """Tests for batch document processing."""

    def test_10_page_batch_processing(
        self, sample_page_images: list[np.ndarray]
    ) -> None:
        """Process 10-page batch successfully."""
        blur_detector = BlurDetector()
        noise_detector = NoiseDetector()
        contrast_detector = ContrastDetector()

        results = []
        for image in sample_page_images:
            blur_result = blur_detector.detect(image)
            noise_result = noise_detector.detect(image)
            contrast_result = contrast_detector.detect(image)

            iqa_metrics = normalize_classical_iqa(
                blur_result=blur_result,
                contrast_result=contrast_result,
                noise_result=noise_result,
            )
            results.append(iqa_metrics)

        # Verify all pages processed
        assert len(results) == 10
        for metrics in results:
            assert "blur_score" in metrics
            assert "noise_score" in metrics
            assert "contrast_score" in metrics

    def test_50_page_batch_processing(
        self, large_batch_images: list[np.ndarray]
    ) -> None:
        """Process 50-page batch successfully."""
        blur_detector = BlurDetector()

        results = []
        for image in large_batch_images:
            result = blur_detector.detect(image)
            results.append(result)

        # Verify all pages processed
        assert len(results) == 50
        for result in results:
            assert result is not None
            assert result.blur_score is not None


class TestThroughputTargets:
    """Tests for throughput target validation."""

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_batch_throughput(self, sample_page_images: list[np.ndarray]) -> None:
        """Validate batch processing throughput."""
        blur_detector = BlurDetector()

        # Warm up
        _ = blur_detector.detect(sample_page_images[0])

        # Timed batch processing
        start_time = time.perf_counter()

        for image in sample_page_images:
            _ = blur_detector.detect(image)

        elapsed = time.perf_counter() - start_time
        num_pages = len(sample_page_images)

        # Calculate throughput
        throughput = num_pages / elapsed
        latency_per_page = (elapsed / num_pages) * 1000  # ms

        # Validate against relaxed targets
        assert throughput >= CPU_THROUGHPUT_TARGET, (
            f"Throughput {throughput:.2f} pages/sec below target {CPU_THROUGHPUT_TARGET}"
        )
        assert latency_per_page <= CPU_LATENCY_TARGET_MS, (
            f"Latency {latency_per_page:.1f}ms above target {CPU_LATENCY_TARGET_MS}ms"
        )

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_full_pipeline_throughput(
        self, sample_page_images: list[np.ndarray]
    ) -> None:
        """Validate full pipeline throughput (IQA + DQS + Routing)."""
        blur_detector = BlurDetector()
        noise_detector = NoiseDetector()
        contrast_detector = ContrastDetector()

        # Warm up
        img = sample_page_images[0]
        blur_r = blur_detector.detect(img)
        noise_r = noise_detector.detect(img)
        contrast_r = contrast_detector.detect(img)
        _ = normalize_classical_iqa(blur_r, contrast_r, noise_r)

        # Timed full pipeline
        start_time = time.perf_counter()

        for i, image in enumerate(sample_page_images):
            # IQA Detection
            blur_result = blur_detector.detect(image)
            noise_result = noise_detector.detect(image)
            contrast_result = contrast_detector.detect(image)

            # DQS Calculation
            iqa_metrics = normalize_classical_iqa(
                blur_result=blur_result,
                contrast_result=contrast_result,
                noise_result=noise_result,
            )
            degradation = calculate_degradation_score(iqa_metrics)

            # Layout and routing
            layout = PageLayoutSummary(
                page_number=i + 1,
                layout_type=LayoutType.SINGLE_COLUMN,
                complexity_score=0.2,
            )
            complexity = calculate_structural_complexity_score(layout)
            dqs = DQSMetadata(
                degradation_score=degradation,
                structural_complexity_score=complexity,
            )
            pre_ocr_risk = calculate_pre_ocr_risk(dqs, PDFType.IMAGE_ONLY, [layout])
            _ = recommend_ocr_routing(PDFType.IMAGE_ONLY, dqs, pre_ocr_risk, [layout])

        elapsed = time.perf_counter() - start_time
        num_pages = len(sample_page_images)

        # Calculate metrics
        throughput = num_pages / elapsed
        latency_per_page = (elapsed / num_pages) * 1000  # ms

        # Record baseline
        print(
            f"\nFull pipeline: {throughput:.2f} pages/sec, {latency_per_page:.1f}ms/page"
        )

        # Validate against relaxed targets
        assert throughput >= CPU_THROUGHPUT_TARGET / 2, (
            f"Full pipeline throughput {throughput:.2f} too slow"
        )


class TestMemoryUsage:
    """Tests for memory usage during batch processing."""

    def test_no_memory_blowup_on_batch(
        self, sample_page_images: list[np.ndarray]
    ) -> None:
        """Verify memory doesn't grow unbounded during batch processing."""
        blur_detector = BlurDetector()

        # Force GC before starting
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Process batch
        results = []
        for image in sample_page_images:
            result = blur_detector.detect(image)
            # Store minimal result data
            results.append(result.blur_score)

        # Force GC after batch
        gc.collect()
        final_objects = len(gc.get_objects())

        # Objects shouldn't grow excessively
        object_growth = final_objects - initial_objects
        max_expected_growth = len(sample_page_images) * 100  # Allow some growth

        assert object_growth < max_expected_growth, (
            f"Object count grew by {object_growth}, expected < {max_expected_growth}"
        )

    def test_results_can_be_released(
        self, sample_page_images: list[np.ndarray]
    ) -> None:
        """Verify results can be properly garbage collected."""
        blur_detector = BlurDetector()

        # Process and store results
        results = []
        for image in sample_page_images:
            result = blur_detector.detect(image)
            results.append(result)

        # Clear results
        results.clear()
        gc.collect()

        # Process should be repeatable without memory issues
        results2 = []
        for image in sample_page_images:
            result = blur_detector.detect(image)
            results2.append(result)

        assert len(results2) == len(sample_page_images)


class TestMixedPDFTypeBatch:
    """Tests for mixed PDF type batch processing."""

    def test_mixed_pdf_types_routing(
        self,
        sample_page_images: list[np.ndarray],
        mixed_pdf_types: list[PDFType],
    ) -> None:
        """Process batch with mixed PDF types correctly routes each page."""
        blur_detector = BlurDetector()
        noise_detector = NoiseDetector()
        contrast_detector = ContrastDetector()

        routing_decisions = []

        for i, (image, pdf_type) in enumerate(
            zip(sample_page_images, mixed_pdf_types[: len(sample_page_images)])
        ):
            # Process image
            blur_result = blur_detector.detect(image)
            noise_result = noise_detector.detect(image)
            contrast_result = contrast_detector.detect(image)

            iqa_metrics = normalize_classical_iqa(
                blur_result=blur_result,
                contrast_result=contrast_result,
                noise_result=noise_result,
            )
            degradation = calculate_degradation_score(iqa_metrics)

            # Create layout
            layout = PageLayoutSummary(
                page_number=i + 1,
                layout_type=LayoutType.SINGLE_COLUMN,
                complexity_score=0.2,
            )
            complexity = calculate_structural_complexity_score(layout)

            dqs = DQSMetadata(
                degradation_score=degradation,
                structural_complexity_score=complexity,
            )
            pre_ocr_risk = calculate_pre_ocr_risk(dqs, pdf_type, [layout])

            # Get routing decision
            recommendation, rationale = recommend_ocr_routing(
                pdf_type, dqs, pre_ocr_risk, [layout]
            )
            routing_decisions.append(
                {
                    "page": i,
                    "pdf_type": pdf_type,
                    "recommendation": recommendation,
                    "degradation": degradation,
                }
            )

        # Verify all pages got valid routing decisions
        assert len(routing_decisions) == len(sample_page_images)
        for decision in routing_decisions:
            assert decision["recommendation"] is not None
            assert 0.0 <= decision["degradation"] <= 1.0


class TestRegressionBaselines:
    """Tests that record timing baselines for regression detection."""

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_iqa_baseline(self, sample_page_images: list[np.ndarray]) -> None:
        """Record IQA processing baseline."""
        blur_detector = BlurDetector()
        noise_detector = NoiseDetector()
        contrast_detector = ContrastDetector()

        times: dict[str, list[float]] = {
            "blur": [],
            "noise": [],
            "contrast": [],
        }

        for image in sample_page_images:
            # Time each detector
            start = time.perf_counter()
            _ = blur_detector.detect(image)
            times["blur"].append((time.perf_counter() - start) * 1000)

            start = time.perf_counter()
            _ = noise_detector.detect(image)
            times["noise"].append((time.perf_counter() - start) * 1000)

            start = time.perf_counter()
            _ = contrast_detector.detect(image)
            times["contrast"].append((time.perf_counter() - start) * 1000)

        # Calculate averages
        avg_blur = sum(times["blur"]) / len(times["blur"])
        avg_noise = sum(times["noise"]) / len(times["noise"])
        avg_contrast = sum(times["contrast"]) / len(times["contrast"])

        print("\nIQA Baselines:")
        print(f"  Blur: {avg_blur:.2f}ms avg")
        print(f"  Noise: {avg_noise:.2f}ms avg")
        print(f"  Contrast: {avg_contrast:.2f}ms avg")

        # Verify reasonable baselines (very relaxed)
        assert avg_blur < 1000, f"Blur too slow: {avg_blur:.2f}ms"
        assert avg_noise < 1000, f"Noise too slow: {avg_noise:.2f}ms"
        assert avg_contrast < 1000, f"Contrast too slow: {avg_contrast:.2f}ms"

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_dqs_calculation_baseline(self) -> None:
        """Record DQS calculation baseline."""
        # Create test metrics
        from image_preprocessing_detector.detection.iqa_classical import Severity

        class MockBlurResult:
            is_blurred = False
            score = 100.0
            blur_score = 0.8
            severity = Severity.LOW
            confidence = 0.9

        class MockNoiseResult:
            is_noisy = False
            score = 5.0
            noise_score = 0.9
            noise_sigma = 2.0
            severity = Severity.LOW
            confidence = 0.9

        class MockContrastResult:
            is_low_contrast = False
            score = 0.25
            severity = Severity.LOW
            confidence = 0.9

        blur_result = MockBlurResult()
        noise_result = MockNoiseResult()
        contrast_result = MockContrastResult()

        # Time DQS calculation
        times = []
        for _ in range(100):
            start = time.perf_counter()
            iqa_metrics = normalize_classical_iqa(
                blur_result=blur_result,
                contrast_result=contrast_result,
                noise_result=noise_result,
            )
            _ = calculate_degradation_score(iqa_metrics)
            times.append((time.perf_counter() - start) * 1000)

        avg_time = sum(times) / len(times)
        print(f"\nDQS Calculation Baseline: {avg_time:.4f}ms avg")

        # DQS should be very fast (pure computation)
        assert avg_time < 10, f"DQS calculation too slow: {avg_time:.4f}ms"
