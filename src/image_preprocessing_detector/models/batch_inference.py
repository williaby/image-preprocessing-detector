# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Micro-batching for optimized student model inference.

This module provides batched inference for the student IQA model to improve
throughput by processing multiple images simultaneously.

Features:
- Configurable batch size (default: 8)
- Automatic batch accumulation with timeout
- Tensor caching integration
- Thread-safe batch queue
- Metrics for batch efficiency

Phase 4 Integration - Week 17 Sprint 4.3.1
"""

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from image_preprocessing_detector.utils.log_config import get_logger
from image_preprocessing_detector.utils.tensor_cache import (
    compute_tensor_key,
    get_array_size_bytes,
    get_tensor_cache,
)

logger = get_logger(__name__)

# Default configuration
DEFAULT_BATCH_SIZE = 8
DEFAULT_BATCH_TIMEOUT_MS = 50  # Wait up to 50ms to fill batch
DEFAULT_MAX_QUEUE_SIZE = 100


@dataclass
class BatchInferenceMetrics:
    """Metrics for batch inference performance.

    Attributes:
        total_batches: Total number of batches processed
        total_images: Total number of images processed
        full_batches: Number of full batches (reached max size)
        partial_batches: Number of partial batches (timeout)
        cache_hits: Number of cache hits
        cache_misses: Number of cache misses
        total_inference_time_ms: Total inference time
        avg_batch_size: Average batch size
    """

    total_batches: int = 0
    total_images: int = 0
    full_batches: int = 0
    partial_batches: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_inference_time_ms: float = 0.0

    @property
    def avg_batch_size(self) -> float:
        """Calculate average batch size."""
        if self.total_batches == 0:
            return 0.0
        return self.total_images / self.total_batches

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    @property
    def avg_inference_time_ms(self) -> float:
        """Calculate average inference time per batch."""
        if self.total_batches == 0:
            return 0.0
        return self.total_inference_time_ms / self.total_batches

    def to_dict(self) -> dict[str, int | float]:
        """Convert metrics to dictionary."""
        return {
            "total_batches": self.total_batches,
            "total_images": self.total_images,
            "full_batches": self.full_batches,
            "partial_batches": self.partial_batches,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_inference_time_ms": round(self.total_inference_time_ms, 2),
            "avg_batch_size": round(self.avg_batch_size, 2),
            "cache_hit_rate_pct": round(self.cache_hit_rate, 2),
            "avg_inference_time_ms": round(self.avg_inference_time_ms, 2),
        }


@dataclass
class InferenceRequest:
    """Single inference request in batch queue.

    Attributes:
        image: Input image (preprocessed tensor)
        request_id: Unique request identifier
        callback: Optional callback for result delivery
        result: Placeholder for inference result
        error: Placeholder for error if any
    """

    image: np.ndarray
    request_id: str
    callback: Callable[[dict[str, Any] | None, Exception | None], None] | None = None
    result: dict[str, Any] | None = field(default=None, repr=False)
    error: Exception | None = field(default=None, repr=False)
    event: threading.Event = field(default_factory=threading.Event, repr=False)


class BatchInferenceEngine:
    """Micro-batching engine for student inference.

    Accumulates inference requests and processes them in batches
    for improved throughput.

    Example:
        >>> engine = BatchInferenceEngine(batch_size=8, model_session=session)
        >>> engine.start()
        >>> result = engine.submit_sync(image, "request-1")
        >>> engine.stop()
    """

    def __init__(
        self,
        model_session: Any,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_timeout_ms: int = DEFAULT_BATCH_TIMEOUT_MS,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        enable_cache: bool = True,
        model_name: str = "student",
        input_size: tuple[int, int] = (224, 224),
    ) -> None:
        """Initialize batch inference engine.

        Args:
            model_session: ONNX InferenceSession for student model
            batch_size: Maximum images per batch
            batch_timeout_ms: Maximum wait time to fill batch
            max_queue_size: Maximum pending requests
            enable_cache: Whether to use tensor caching
            model_name: Model name for cache keys
            input_size: Model input dimensions
        """
        self._session = model_session
        self._batch_size = batch_size
        self._batch_timeout_ms = batch_timeout_ms
        self._max_queue_size = max_queue_size
        self._enable_cache = enable_cache
        self._model_name = model_name
        self._input_size = input_size

        # Request queue
        self._queue: queue.Queue[InferenceRequest | None] = queue.Queue(
            maxsize=max_queue_size
        )

        # Worker thread
        self._worker_thread: threading.Thread | None = None
        self._running = False

        # Metrics
        self._metrics = BatchInferenceMetrics()
        self._metrics_lock = threading.Lock()

        # Get input/output names from session
        self._input_name = model_session.get_inputs()[0].name
        self._output_names = [out.name for out in model_session.get_outputs()]

        logger.info(
            "BatchInferenceEngine initialized",
            batch_size=batch_size,
            batch_timeout_ms=batch_timeout_ms,
            enable_cache=enable_cache,
            model_name=model_name,
        )

    def start(self) -> None:
        """Start the batch processing worker thread."""
        if self._running:
            logger.warning("BatchInferenceEngine already running")
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, name="BatchInferenceWorker", daemon=True
        )
        self._worker_thread.start()
        logger.info("BatchInferenceEngine started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the batch processing worker thread.

        Args:
            timeout: Maximum time to wait for worker to finish
        """
        if not self._running:
            return

        self._running = False
        # Send poison pill to wake up worker
        self._queue.put(None)

        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("BatchInferenceEngine worker did not stop cleanly")
            else:
                logger.info("BatchInferenceEngine stopped")

    def submit_sync(
        self, image: np.ndarray, request_id: str, timeout: float = 5.0
    ) -> dict[str, Any]:
        """Submit image for inference and wait for result.

        Args:
            image: Preprocessed input tensor (1, 3, H, W)
            request_id: Unique request identifier
            timeout: Maximum wait time in seconds

        Returns:
            Inference results dictionary

        Raises:
            TimeoutError: If inference doesn't complete in time
            RuntimeError: If inference fails
        """
        # Check cache first
        if self._enable_cache:
            cache_key = compute_tensor_key(
                image, model_name=self._model_name, input_size=self._input_size
            )
            cache = get_tensor_cache()
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                with self._metrics_lock:
                    self._metrics.cache_hits += 1
                logger.debug("Cache hit", request_id=request_id, cache_key=cache_key)
                # Convert cached numpy array back to result dict
                return self._postprocess_single(cached_result)

            with self._metrics_lock:
                self._metrics.cache_misses += 1

        # Create request
        request = InferenceRequest(image=image, request_id=request_id)

        # Submit to queue
        try:
            self._queue.put(request, timeout=timeout)
        except queue.Full as e:
            raise RuntimeError("Inference queue full") from e

        # Wait for result
        if not request.event.wait(timeout=timeout):
            raise TimeoutError(f"Inference timeout for request {request_id}")

        if request.error:
            raise RuntimeError(f"Inference failed: {request.error}") from request.error

        if request.result is None:
            raise RuntimeError("No result returned from inference")

        return request.result

    def submit_async(
        self,
        image: np.ndarray,
        request_id: str,
        callback: Callable[[dict[str, Any] | None, Exception | None], None],
    ) -> None:
        """Submit image for inference with callback.

        Args:
            image: Preprocessed input tensor
            request_id: Unique request identifier
            callback: Function to call with (result, error)
        """
        # Check cache first
        if self._enable_cache:
            cache_key = compute_tensor_key(
                image, model_name=self._model_name, input_size=self._input_size
            )
            cache = get_tensor_cache()
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                with self._metrics_lock:
                    self._metrics.cache_hits += 1
                result = self._postprocess_single(cached_result)
                callback(result, None)
                return

            with self._metrics_lock:
                self._metrics.cache_misses += 1

        # Create request with callback
        request = InferenceRequest(image=image, request_id=request_id, callback=callback)

        # Submit to queue
        try:
            self._queue.put_nowait(request)
        except queue.Full:
            callback(None, RuntimeError("Inference queue full"))

    def _worker_loop(self) -> None:
        """Main worker loop for batch processing."""
        while self._running:
            try:
                batch = self._collect_batch()
                if batch:
                    self._process_batch(batch)
            except Exception as e:
                logger.exception("Batch processing error", error=str(e))

    def _collect_batch(self) -> list[InferenceRequest]:
        """Collect requests into a batch.

        Returns:
            List of requests to process
        """
        batch: list[InferenceRequest] = []
        deadline = time.time() + (self._batch_timeout_ms / 1000.0)

        while len(batch) < self._batch_size:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                request = self._queue.get(timeout=remaining)
                if request is None:  # Poison pill
                    break
                batch.append(request)
            except queue.Empty:
                break

        return batch

    def _process_batch(self, batch: list[InferenceRequest]) -> None:
        """Process a batch of requests.

        Args:
            batch: List of inference requests
        """
        if not batch:
            return

        start_time = time.perf_counter()
        is_full_batch = len(batch) >= self._batch_size

        try:
            # Stack images into batch tensor
            images = np.vstack([req.image for req in batch])

            # Run batch inference
            outputs = self._session.run(self._output_names, {self._input_name: images})

            # Convert outputs to dict
            outputs_dict = dict(zip(self._output_names, outputs, strict=False))

            # Process results for each request
            for i, request in enumerate(batch):
                try:
                    # Extract single result from batch
                    single_outputs = {
                        name: arr[i : i + 1] for name, arr in outputs_dict.items()
                    }
                    result = self._postprocess_outputs(single_outputs)
                    request.result = result

                    # Cache the raw outputs
                    if self._enable_cache:
                        cache_key = compute_tensor_key(
                            request.image,
                            model_name=self._model_name,
                            input_size=self._input_size,
                        )
                        cache = get_tensor_cache()
                        # Store the outputs array for caching
                        cache_data = np.array(
                            [single_outputs[name][0] for name in self._output_names]
                        )
                        cache.put(
                            cache_key, cache_data, size_bytes=get_array_size_bytes(cache_data)
                        )

                    # Notify completion
                    if request.callback:
                        request.callback(result, None)
                    request.event.set()

                except Exception as e:
                    request.error = e
                    if request.callback:
                        request.callback(None, e)
                    request.event.set()

            # Update metrics
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            with self._metrics_lock:
                self._metrics.total_batches += 1
                self._metrics.total_images += len(batch)
                self._metrics.total_inference_time_ms += elapsed_ms
                if is_full_batch:
                    self._metrics.full_batches += 1
                else:
                    self._metrics.partial_batches += 1

            logger.debug(
                "Batch processed",
                batch_size=len(batch),
                elapsed_ms=round(elapsed_ms, 2),
                is_full=is_full_batch,
            )

        except Exception as e:
            # Mark all requests as failed
            for request in batch:
                request.error = e
                if request.callback:
                    request.callback(None, e)
                request.event.set()
            logger.exception("Batch inference failed", batch_size=len(batch), error=str(e))

    def _postprocess_outputs(self, outputs: dict[str, np.ndarray]) -> dict[str, Any]:
        """Postprocess model outputs to scores.

        Args:
            outputs: Raw model outputs

        Returns:
            Dictionary with scores and confidences
        """
        head_names = ["blur", "noise", "contrast", "skew", "compression"]
        scores = {}
        confidences = {}

        for i, head_name in enumerate(head_names):
            output_key = f"head_{i}"
            if output_key in outputs:
                logits = outputs[output_key][0]
                # Softmax
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
                scores[f"{head_name}_score"] = float(probs[1])
                confidences[head_name] = float(np.max(probs))

        # Calculate overall quality
        overall = (
            scores.get("blur_score", 0.0) * 0.25
            + scores.get("noise_score", 0.0) * 0.20
            + scores.get("contrast_score", 0.0) * 0.25
            + scores.get("skew_score", 0.0) * 0.15
            + scores.get("compression_score", 0.0) * 0.15
        )

        return {
            "scores": scores,
            "confidences": confidences,
            "overall_quality": overall,
        }

    def _postprocess_single(self, cached_data: np.ndarray) -> dict[str, Any]:
        """Postprocess cached data back to result format.

        Args:
            cached_data: Cached numpy array from previous inference

        Returns:
            Dictionary with scores and confidences
        """
        head_names = ["blur", "noise", "contrast", "skew", "compression"]
        scores = {}
        confidences = {}

        for i, head_name in enumerate(head_names):
            if i < len(cached_data):
                logits = cached_data[i]
                # Softmax
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
                scores[f"{head_name}_score"] = float(probs[1])
                confidences[head_name] = float(np.max(probs))

        # Calculate overall quality
        overall = (
            scores.get("blur_score", 0.0) * 0.25
            + scores.get("noise_score", 0.0) * 0.20
            + scores.get("contrast_score", 0.0) * 0.25
            + scores.get("skew_score", 0.0) * 0.15
            + scores.get("compression_score", 0.0) * 0.15
        )

        return {
            "scores": scores,
            "confidences": confidences,
            "overall_quality": overall,
        }

    def get_metrics(self) -> BatchInferenceMetrics:
        """Get current batch inference metrics."""
        with self._metrics_lock:
            return BatchInferenceMetrics(
                total_batches=self._metrics.total_batches,
                total_images=self._metrics.total_images,
                full_batches=self._metrics.full_batches,
                partial_batches=self._metrics.partial_batches,
                cache_hits=self._metrics.cache_hits,
                cache_misses=self._metrics.cache_misses,
                total_inference_time_ms=self._metrics.total_inference_time_ms,
            )

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._metrics_lock:
            self._metrics = BatchInferenceMetrics()

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running


def run_batch_inference(
    session: Any,
    images: list[np.ndarray],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Run batch inference synchronously (convenience function).

    Args:
        session: ONNX InferenceSession
        images: List of preprocessed input tensors
        batch_size: Batch size for inference

    Returns:
        List of result dictionaries
    """
    if not images:
        return []

    input_name = session.get_inputs()[0].name
    output_names = [out.name for out in session.get_outputs()]

    results: list[dict[str, Any]] = []

    # Process in batches
    for i in range(0, len(images), batch_size):
        batch_images = images[i : i + batch_size]

        # Stack into batch
        batch_tensor = np.vstack(batch_images)

        # Run inference
        outputs = session.run(output_names, {input_name: batch_tensor})
        outputs_dict = dict(zip(output_names, outputs, strict=False))

        # Extract individual results
        for j in range(len(batch_images)):
            single_outputs = {name: arr[j : j + 1] for name, arr in outputs_dict.items()}
            result = _postprocess_batch_outputs(single_outputs)
            results.append(result)

    return results


def _postprocess_batch_outputs(outputs: dict[str, np.ndarray]) -> dict[str, Any]:
    """Postprocess outputs from batch inference."""
    head_names = ["blur", "noise", "contrast", "skew", "compression"]
    scores = {}
    confidences = {}

    for i, head_name in enumerate(head_names):
        output_key = f"head_{i}"
        if output_key in outputs:
            logits = outputs[output_key][0]
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            scores[f"{head_name}_score"] = float(probs[1])
            confidences[head_name] = float(np.max(probs))

    overall = (
        scores.get("blur_score", 0.0) * 0.25
        + scores.get("noise_score", 0.0) * 0.20
        + scores.get("contrast_score", 0.0) * 0.25
        + scores.get("skew_score", 0.0) * 0.15
        + scores.get("compression_score", 0.0) * 0.15
    )

    return {
        "scores": scores,
        "confidences": confidences,
        "overall_quality": overall,
    }
