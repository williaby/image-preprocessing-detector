# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for micro-batching inference engine."""

import threading
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from image_preprocessing_detector.models.batch_inference import (
    BatchInferenceEngine,
    BatchInferenceMetrics,
    InferenceRequest,
    run_batch_inference,
)
from image_preprocessing_detector.utils.tensor_cache import reset_cache_instances


@pytest.fixture(autouse=True)
def reset_caches() -> None:
    """Reset cache instances before each test."""
    reset_cache_instances()
    yield
    reset_cache_instances()


def create_mock_session() -> MagicMock:
    """Create a mock ONNX session for testing."""
    session = MagicMock()

    # Mock input
    mock_input = MagicMock()
    mock_input.name = "input"
    session.get_inputs.return_value = [mock_input]

    # Mock outputs (5 heads)
    mock_outputs = []
    for i in range(5):
        mock_output = MagicMock()
        mock_output.name = f"head_{i}"
        mock_outputs.append(mock_output)
    session.get_outputs.return_value = mock_outputs

    def mock_run(
        output_names: list[str], inputs: dict[str, np.ndarray]
    ) -> list[np.ndarray]:
        """Simulate model inference."""
        batch_size = inputs["input"].shape[0]
        results = []
        for _ in output_names:
            # Return logits for binary classification
            logits = np.random.randn(batch_size, 2).astype(np.float32)
            results.append(logits)
        return results

    session.run = mock_run

    return session


class TestBatchInferenceMetrics:
    """Tests for BatchInferenceMetrics."""

    def test_avg_batch_size_no_batches(self) -> None:
        """Test average batch size with no batches."""
        metrics = BatchInferenceMetrics()
        assert metrics.avg_batch_size == 0.0

    def test_avg_batch_size(self) -> None:
        """Test average batch size calculation."""
        metrics = BatchInferenceMetrics(total_batches=10, total_images=40)
        assert metrics.avg_batch_size == 4.0

    def test_cache_hit_rate_no_accesses(self) -> None:
        """Test cache hit rate with no accesses."""
        metrics = BatchInferenceMetrics()
        assert metrics.cache_hit_rate == 0.0

    def test_cache_hit_rate(self) -> None:
        """Test cache hit rate calculation."""
        metrics = BatchInferenceMetrics(cache_hits=75, cache_misses=25)
        assert metrics.cache_hit_rate == 75.0

    def test_avg_inference_time_no_batches(self) -> None:
        """Test average inference time with no batches."""
        metrics = BatchInferenceMetrics()
        assert metrics.avg_inference_time_ms == 0.0

    def test_avg_inference_time(self) -> None:
        """Test average inference time calculation."""
        metrics = BatchInferenceMetrics(total_batches=10, total_inference_time_ms=100.0)
        assert metrics.avg_inference_time_ms == 10.0

    def test_to_dict(self) -> None:
        """Test metrics serialization."""
        metrics = BatchInferenceMetrics(
            total_batches=10,
            total_images=80,
            full_batches=8,
            partial_batches=2,
            cache_hits=60,
            cache_misses=20,
            total_inference_time_ms=200.0,
        )
        result = metrics.to_dict()

        assert result["total_batches"] == 10
        assert result["total_images"] == 80
        assert result["full_batches"] == 8
        assert result["partial_batches"] == 2
        assert result["cache_hits"] == 60
        assert result["cache_misses"] == 20
        assert result["avg_batch_size"] == 8.0
        assert result["cache_hit_rate_pct"] == 75.0
        assert result["avg_inference_time_ms"] == 20.0


class TestInferenceRequest:
    """Tests for InferenceRequest dataclass."""

    def test_request_creation(self) -> None:
        """Test creating an inference request."""
        image = np.zeros((1, 3, 224, 224), dtype=np.float32)
        request = InferenceRequest(image=image, request_id="test-1")

        assert request.request_id == "test-1"
        assert request.result is None
        assert request.error is None
        assert request.callback is None
        assert isinstance(request.event, threading.Event)

    def test_request_with_callback(self) -> None:
        """Test request with callback."""
        image = np.zeros((1, 3, 224, 224), dtype=np.float32)
        callback = MagicMock()
        request = InferenceRequest(image=image, request_id="test-2", callback=callback)

        assert request.callback is callback


class TestBatchInferenceEngine:
    """Tests for BatchInferenceEngine."""

    def test_engine_initialization(self) -> None:
        """Test engine initialization."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=100,
        )

        assert engine._batch_size == 4
        assert engine._batch_timeout_ms == 100
        assert not engine.is_running

    def test_engine_start_stop(self) -> None:
        """Test starting and stopping the engine."""
        session = create_mock_session()
        engine = BatchInferenceEngine(model_session=session)

        engine.start()
        assert engine.is_running

        engine.stop()
        assert not engine.is_running

    def test_submit_sync_single_image(self) -> None:
        """Test synchronous submission of single image."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,  # Short timeout
            enable_cache=False,
        )

        engine.start()
        try:
            image = np.random.randn(1, 3, 224, 224).astype(np.float32)
            result = engine.submit_sync(image, "test-1", timeout=5.0)

            assert "scores" in result
            assert "confidences" in result
            assert "overall_quality" in result

            # Check metrics
            metrics = engine.get_metrics()
            assert metrics.total_images == 1
            assert metrics.total_batches == 1
        finally:
            engine.stop()

    def test_submit_sync_multiple_images(self) -> None:
        """Test synchronous submission of multiple images."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=100,
            enable_cache=False,
        )

        engine.start()
        try:
            results = []
            threads = []

            def submit_image(idx: int) -> None:
                image = np.random.randn(1, 3, 224, 224).astype(np.float32)
                result = engine.submit_sync(image, f"test-{idx}", timeout=5.0)
                results.append(result)

            # Submit 4 images concurrently
            for i in range(4):
                t = threading.Thread(target=submit_image, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            assert len(results) == 4
            for result in results:
                assert "scores" in result
                assert "overall_quality" in result

        finally:
            engine.stop()

    def test_submit_async_with_callback(self) -> None:
        """Test asynchronous submission with callback."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,
            enable_cache=False,
        )

        engine.start()
        try:
            callback_called = threading.Event()
            callback_result = {"result": None, "error": None}

            def callback(result: dict | None, error: Exception | None) -> None:
                callback_result["result"] = result
                callback_result["error"] = error
                callback_called.set()

            image = np.random.randn(1, 3, 224, 224).astype(np.float32)
            engine.submit_async(image, "async-1", callback)

            assert callback_called.wait(timeout=5.0)
            assert callback_result["result"] is not None
            assert callback_result["error"] is None

        finally:
            engine.stop()

    def test_cache_hit(self) -> None:
        """Test cache hit behavior."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,
            enable_cache=True,
        )

        engine.start()
        try:
            # Use same image twice
            image = np.random.randn(1, 3, 224, 224).astype(np.float32)

            # First request - cache miss
            result1 = engine.submit_sync(image, "test-1", timeout=5.0)

            # Second request with same image - cache hit
            result2 = engine.submit_sync(image, "test-2", timeout=5.0)

            # Both should have results
            assert result1 is not None
            assert result2 is not None

            # Check cache metrics
            metrics = engine.get_metrics()
            assert metrics.cache_misses >= 1
            assert metrics.cache_hits >= 1

        finally:
            engine.stop()

    def test_queue_size(self) -> None:
        """Test queue size reporting."""
        session = create_mock_session()
        engine = BatchInferenceEngine(model_session=session)

        assert engine.queue_size == 0

    def test_reset_metrics(self) -> None:
        """Test resetting metrics."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,
            enable_cache=False,
        )

        engine.start()
        try:
            image = np.random.randn(1, 3, 224, 224).astype(np.float32)
            engine.submit_sync(image, "test-1", timeout=5.0)

            # Metrics should be non-zero
            metrics = engine.get_metrics()
            assert metrics.total_batches > 0

            # Reset
            engine.reset_metrics()

            # Metrics should be zero
            metrics = engine.get_metrics()
            assert metrics.total_batches == 0
            assert metrics.total_images == 0

        finally:
            engine.stop()

    def test_full_batch_tracking(self) -> None:
        """Test tracking of full vs partial batches."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=2,  # Small batch for testing
            batch_timeout_ms=50,
            enable_cache=False,
        )

        engine.start()
        try:
            threads = []

            def submit_image(idx: int) -> None:
                image = np.random.randn(1, 3, 224, 224).astype(np.float32)
                engine.submit_sync(image, f"test-{idx}", timeout=5.0)

            # Submit 2 images quickly to fill a batch
            for i in range(2):
                t = threading.Thread(target=submit_image, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Wait a bit for processing
            time.sleep(0.1)

            metrics = engine.get_metrics()
            assert metrics.total_batches >= 1
            # Should have at least one batch (full or partial)

        finally:
            engine.stop()


class TestRunBatchInference:
    """Tests for run_batch_inference convenience function."""

    def test_empty_input(self) -> None:
        """Test with empty input list."""
        session = create_mock_session()
        results = run_batch_inference(session, [], batch_size=4)
        assert results == []

    def test_single_image(self) -> None:
        """Test with single image."""
        session = create_mock_session()
        images = [np.random.randn(1, 3, 224, 224).astype(np.float32)]

        results = run_batch_inference(session, images, batch_size=4)

        assert len(results) == 1
        assert "scores" in results[0]
        assert "overall_quality" in results[0]

    def test_multiple_images(self) -> None:
        """Test with multiple images."""
        session = create_mock_session()
        images = [np.random.randn(1, 3, 224, 224).astype(np.float32) for _ in range(10)]

        results = run_batch_inference(session, images, batch_size=4)

        assert len(results) == 10
        for result in results:
            assert "scores" in result
            assert "confidences" in result
            assert "overall_quality" in result

    def test_batch_size_larger_than_input(self) -> None:
        """Test with batch size larger than input."""
        session = create_mock_session()
        images = [np.random.randn(1, 3, 224, 224).astype(np.float32) for _ in range(3)]

        results = run_batch_inference(session, images, batch_size=10)

        assert len(results) == 3

    def test_exact_batch_size(self) -> None:
        """Test with input exactly matching batch size."""
        session = create_mock_session()
        images = [np.random.randn(1, 3, 224, 224).astype(np.float32) for _ in range(8)]

        results = run_batch_inference(session, images, batch_size=4)

        assert len(results) == 8


class TestCacheIntegration:
    """Tests for cache integration with batch inference."""

    def test_cache_disabled(self) -> None:
        """Test with cache disabled."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,
            enable_cache=False,
        )

        engine.start()
        try:
            image = np.random.randn(1, 3, 224, 224).astype(np.float32)

            # Same image twice
            engine.submit_sync(image, "test-1", timeout=5.0)
            engine.submit_sync(image, "test-2", timeout=5.0)

            metrics = engine.get_metrics()
            # Both should go through inference (no cache hits)
            assert metrics.cache_hits == 0
            assert metrics.cache_misses == 0  # Cache disabled

        finally:
            engine.stop()

    def test_async_cache_hit(self) -> None:
        """Test async submission with cache hit."""
        session = create_mock_session()
        engine = BatchInferenceEngine(
            model_session=session,
            batch_size=4,
            batch_timeout_ms=10,
            enable_cache=True,
        )

        engine.start()
        try:
            image = np.random.randn(1, 3, 224, 224).astype(np.float32)

            # First sync to populate cache
            engine.submit_sync(image, "sync-1", timeout=5.0)

            # Now async with same image
            callback_result = {"called": False}

            def callback(result: dict | None, error: Exception | None) -> None:
                callback_result["called"] = True
                callback_result["result"] = result

            engine.submit_async(image, "async-1", callback)

            # Cache hit should be immediate
            time.sleep(0.1)
            assert callback_result["called"]
            assert callback_result["result"] is not None

        finally:
            engine.stop()
