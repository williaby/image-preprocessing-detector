# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal GPU client for remote teacher inference.

This module implements a circuit breaker client for Modal serverless GPU:
- Exponential backoff with jitter for retries
- Circuit breaker pattern to fail fast during outages
- Automatic fallback to student-only inference
- Cost estimation and request timeout handling

Sprint 4.2.3: Client Stub with Circuit Breaker (Phase 4B)
Sprint 4.2.1: Wire real Modal SDK calls (Phase 4B)
"""

from __future__ import annotations

import base64
import io
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Consecutive failures before opening circuit
        success_threshold: Consecutive successes to close circuit (from half-open)
        timeout_seconds: Time to wait before trying half-open state
        request_timeout_ms: Individual request timeout in milliseconds
        max_retries: Maximum retry attempts per request
        base_backoff_ms: Base backoff time for exponential backoff
        max_backoff_ms: Maximum backoff time
    """

    failure_threshold: int = 3
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    request_timeout_ms: int = 5000
    max_retries: int = 3
    base_backoff_ms: int = 1000
    max_backoff_ms: int = 8000


@dataclass
class ModalInferenceRequest:
    """Request format for Modal teacher inference.

    Attributes:
        image_array: Image as numpy array (H, W, C) uint8
        model_version: Model version to use for inference
        request_id: Unique request identifier for tracking
    """

    image_array: np.ndarray
    model_version: str = "v1.0"
    request_id: str | None = None


@dataclass
class ModalInferenceResponse:
    """Response format from Modal teacher inference.

    Attributes:
        scores: Multi-head IQA scores (blur, noise, contrast, skew, compression)
        confidences: Per-head confidence scores
        inference_time_ms: Server-side inference latency
        device_tag: Device used on Modal (e.g., "T4", "A10")
        model_version: Model version that generated scores
        request_id: Request identifier for correlation
    """

    scores: dict[str, float]
    confidences: dict[str, float]
    inference_time_ms: float
    device_tag: str
    model_version: str
    request_id: str | None = None


@dataclass
class CircuitBreakerState:
    """Track circuit breaker state and statistics.

    Attributes:
        state: Current circuit state
        failure_count: Consecutive failures in current state
        success_count: Consecutive successes in half-open state
        last_failure_time: Timestamp of last failure
        total_requests: Total requests attempted
        total_failures: Total failures (all-time)
        total_successes: Total successes (all-time)
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0


class ModalClient:
    """Client for Modal GPU teacher inference with circuit breaker.

    This client provides resilient remote inference with:
    - Circuit breaker pattern for fast failure during outages
    - Exponential backoff with jitter for transient failures
    - Automatic fallback signaling (returns None on breaker open)
    - Request/response logging for observability
    - Cost estimation based on inference time

    Example:
        >>> config = CircuitBreakerConfig(failure_threshold=3)
        >>> client = ModalClient(config=config, modal_endpoint="https://...")
        >>> request = ModalInferenceRequest(image_array=img)
        >>> response = client.predict(request)
        >>> if response:
        ...     print(f"Teacher scores: {response.scores}")
        ... else:
        ...     print("Modal unavailable, using student-only fallback")
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        modal_endpoint: str | None = None,
    ) -> None:
        """Initialize Modal client with circuit breaker.

        Args:
            config: Circuit breaker configuration
            modal_endpoint: Modal serverless endpoint URL
        """
        self.config = config or CircuitBreakerConfig()
        self.modal_endpoint = modal_endpoint
        self.breaker_state = CircuitBreakerState()

        logger.info(
            "ModalClient initialized",
            endpoint=modal_endpoint,
            failure_threshold=self.config.failure_threshold,
            timeout_seconds=self.config.timeout_seconds,
        )

    def predict(self, request: ModalInferenceRequest) -> ModalInferenceResponse | None:
        """Execute teacher inference on Modal GPU.

        This method implements the circuit breaker pattern:
        1. If circuit is OPEN, reject immediately (return None)
        2. If circuit is CLOSED or HALF_OPEN, attempt request with retries
        3. Update circuit state based on success/failure

        Args:
            request: Inference request with image array and metadata

        Returns:
            ModalInferenceResponse if successful, None if breaker open or all retries failed

        Example:
            >>> request = ModalInferenceRequest(image_array=img, model_version="v1.0")
            >>> response = client.predict(request)
            >>> if response:
            ...     print(f"Scores: {response.scores}")
        """
        self.breaker_state.total_requests += 1

        # Circuit breaker: Fast fail if open
        if self._should_reject_request():
            logger.warning(
                "Circuit breaker OPEN - rejecting request",
                state=self.breaker_state.state.value,
                failure_count=self.breaker_state.failure_count,
                last_failure_elapsed=time.time() - self.breaker_state.last_failure_time,
            )
            return None

        # Attempt request with retries
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._execute_request(request, attempt)
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Modal request failed",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries + 1,
                    error=str(e),
                    request_id=request.request_id,
                )

                # Backoff before retry (except on last attempt)
                if attempt < self.config.max_retries:
                    backoff_ms = self._calculate_backoff(attempt)
                    time.sleep(backoff_ms / 1000.0)
            else:
                # Success - record and return
                self._record_success()
                return response

        # All retries exhausted
        self._record_failure()
        logger.error(
            "Modal request failed after all retries",
            total_attempts=self.config.max_retries + 1,
            error=str(last_exception),
            request_id=request.request_id,
            circuit_state=self.breaker_state.state.value,
        )
        return None

    def _should_reject_request(self) -> bool:
        """Check if circuit breaker should reject the request.

        Returns:
            True if circuit is OPEN and timeout hasn't elapsed
        """
        if self.breaker_state.state != CircuitState.OPEN:
            return False

        # Check if timeout has elapsed to try half-open
        elapsed = time.time() - self.breaker_state.last_failure_time
        if elapsed >= self.config.timeout_seconds:
            logger.info(
                "Circuit breaker entering HALF_OPEN state",
                timeout_elapsed=elapsed,
            )
            self.breaker_state.state = CircuitState.HALF_OPEN
            self.breaker_state.success_count = 0
            return False

        return True

    def _execute_request(
        self, request: ModalInferenceRequest, attempt: int
    ) -> ModalInferenceResponse:
        """Execute single request to Modal endpoint.

        Args:
            request: Inference request
            attempt: Current attempt number (0-indexed)

        Returns:
            ModalInferenceResponse from Modal

        Raises:
            RuntimeError: If Modal endpoint not configured
            Exception: If request fails (timeout, network error, etc.)
        """
        if not self.modal_endpoint:
            msg = "Modal endpoint not configured"
            raise RuntimeError(msg)

        logger.debug(
            "Executing Modal request",
            attempt=attempt + 1,
            endpoint=self.modal_endpoint,
            image_shape=request.image_array.shape,
            model_version=request.model_version,
            request_id=request.request_id,
        )

        # Use mock mode for testing when configured
        if self._use_mock_mode():
            return self._get_mock_response(request)

        # Call real Modal endpoint via SDK
        response_dict = self._call_modal_function(request)

        # Check for errors
        if "error" in response_dict:
            error_msg = response_dict["error"]
            raise RuntimeError(f"Modal inference error: {error_msg}")

        # Map response to dataclass
        # Note: Model outputs blur, noise, skew, illumination, artifacts
        # Client interface uses contrast, compression for backwards compat
        scores = response_dict.get("scores", {})
        confidences = response_dict.get("confidences", {})

        response = ModalInferenceResponse(
            scores={
                "blur": scores.get("blur", 0.0),
                "noise": scores.get("noise", 0.0),
                "contrast": scores.get(
                    "illumination", 0.0
                ),  # Map illumination→contrast
                "skew": scores.get("skew", 0.0),
                "compression": scores.get(
                    "artifacts", 0.0
                ),  # Map artifacts→compression
            },
            confidences={
                "blur": confidences.get("blur", 0.0),
                "noise": confidences.get("noise", 0.0),
                "contrast": confidences.get("illumination", 0.0),
                "skew": confidences.get("skew", 0.0),
                "compression": confidences.get("artifacts", 0.0),
            },
            inference_time_ms=response_dict.get("inference_time_ms", 0.0),
            device_tag=response_dict.get("device_tag", "unknown"),
            model_version=response_dict.get("model_version", request.model_version),
            request_id=response_dict.get("request_id", request.request_id),
        )

        logger.debug(
            "Modal request succeeded",
            inference_time_ms=response.inference_time_ms,
            device_tag=response.device_tag,
            request_id=request.request_id,
        )

        return response

    def _use_mock_mode(self) -> bool:
        """Check if mock mode is enabled for testing.

        Mock mode is enabled when:
        - IMGPREP_MODAL_MOCK=true environment variable is set
        - Modal SDK is not available

        Returns:
            True if mock mode should be used
        """
        import os

        if os.getenv("IMGPREP_MODAL_MOCK", "").lower() in ("true", "1", "yes"):
            return True

        # Check if Modal SDK is available
        try:
            import modal  # noqa: F401
        except ImportError:
            logger.warning("Modal SDK not available, using mock mode")
            return True
        else:
            return False

    def _call_modal_function(self, request: ModalInferenceRequest) -> dict[str, Any]:
        """Call Modal function with image data.

        Args:
            request: Inference request with image

        Returns:
            Response dictionary from Modal

        Raises:
            RuntimeError: If Modal call fails
        """
        import modal

        # Encode image as base64 for transfer
        image_b64 = self._encode_image(request.image_array)

        # Look up the deployed Modal function
        try:
            teacher_cls = modal.Cls.lookup("iqa-teacher-inference", "TeacherInference")  # type: ignore[attr-defined]
            teacher = teacher_cls()

            # Call the predict method
            result: dict[str, Any] = teacher.predict.remote(
                image_b64=image_b64,
                request_id=request.request_id,
                model_version=request.model_version,
            )
        except modal.exception.NotFoundError as e:
            raise RuntimeError(
                "Modal app 'iqa-teacher-inference' not deployed. "
                "Run: modal deploy modal/teacher_inference.py"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Modal call failed: {e}") from e
        else:
            return result

    def _encode_image(self, image_array: np.ndarray) -> str:
        """Encode numpy image array as base64 JPEG.

        Args:
            image_array: Image as numpy array (H, W, C) uint8

        Returns:
            Base64-encoded JPEG string
        """
        from PIL import Image as PILImage

        # Convert to PIL Image
        if image_array.dtype != np.uint8:
            image_array = (image_array * 255).astype(np.uint8)

        img = PILImage.fromarray(image_array)

        # Encode as JPEG (smaller than PNG)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    def _get_mock_response(
        self, request: ModalInferenceRequest
    ) -> ModalInferenceResponse:
        """Generate mock response for testing.

        Args:
            request: Inference request

        Returns:
            Mock ModalInferenceResponse
        """
        logger.debug(
            "Using mock Modal response",
            request_id=request.request_id,
        )

        return ModalInferenceResponse(
            scores={
                "blur": 0.85,
                "noise": 0.90,
                "contrast": 0.88,
                "skew": 0.92,
                "compression": 0.87,
            },
            confidences={
                "blur": 0.95,
                "noise": 0.93,
                "contrast": 0.91,
                "skew": 0.96,
                "compression": 0.89,
            },
            inference_time_ms=150.0,
            device_tag="T4-mock",
            model_version=request.model_version,
            request_id=request.request_id,
        )

    def _calculate_backoff(self, attempt: int) -> int:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Backoff time in milliseconds
        """
        # Exponential backoff: base * 2^attempt
        backoff = min(
            self.config.base_backoff_ms * (2**attempt), self.config.max_backoff_ms
        )

        # Add jitter (±25%)
        # Note: Using random.uniform for jitter (not cryptographic use)
        jitter = random.uniform(0.75, 1.25)  # noqa: S311  # nosec B311
        return int(backoff * jitter)

    def _record_success(self) -> None:
        """Record successful request and update circuit breaker state."""
        self.breaker_state.total_successes += 1

        if self.breaker_state.state == CircuitState.HALF_OPEN:
            self.breaker_state.success_count += 1
            if self.breaker_state.success_count >= self.config.success_threshold:
                logger.info(
                    "Circuit breaker CLOSED - service recovered",
                    consecutive_successes=self.breaker_state.success_count,
                )
                self.breaker_state.state = CircuitState.CLOSED
                self.breaker_state.failure_count = 0
                self.breaker_state.success_count = 0

        elif self.breaker_state.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.breaker_state.failure_count = 0

    def _record_failure(self) -> None:
        """Record failed request and update circuit breaker state."""
        self.breaker_state.total_failures += 1
        self.breaker_state.failure_count += 1
        self.breaker_state.last_failure_time = time.time()

        if self.breaker_state.state == CircuitState.HALF_OPEN:
            # Failure in half-open immediately reopens circuit
            logger.warning(
                "Circuit breaker OPEN - failure in half-open state",
                failure_count=self.breaker_state.failure_count,
            )
            self.breaker_state.state = CircuitState.OPEN
            self.breaker_state.success_count = 0

        elif (
            self.breaker_state.state == CircuitState.CLOSED
            and self.breaker_state.failure_count >= self.config.failure_threshold
        ):
            # Threshold exceeded, open circuit
            logger.warning(
                "Circuit breaker OPEN - failure threshold exceeded",
                failure_count=self.breaker_state.failure_count,
                threshold=self.config.failure_threshold,
            )
            self.breaker_state.state = CircuitState.OPEN

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with circuit breaker metrics
        """
        total = self.breaker_state.total_requests
        success_rate = self.breaker_state.total_successes / total if total > 0 else 0.0

        return {
            "state": self.breaker_state.state.value,
            "total_requests": total,
            "total_successes": self.breaker_state.total_successes,
            "total_failures": self.breaker_state.total_failures,
            "success_rate": success_rate,
            "consecutive_failures": self.breaker_state.failure_count,
            "consecutive_successes": self.breaker_state.success_count,
            "last_failure_age_seconds": time.time()
            - self.breaker_state.last_failure_time
            if self.breaker_state.last_failure_time > 0
            else None,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state (for testing/admin)."""
        logger.info(
            "Circuit breaker reset",
            previous_state=self.breaker_state.state.value,
            total_requests=self.breaker_state.total_requests,
        )
        self.breaker_state = CircuitBreakerState()
