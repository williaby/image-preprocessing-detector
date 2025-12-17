# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal client for Arena VLM inference with circuit breaker.

This module provides a resilient client for running VLM inference on Modal GPUs
with circuit breaker pattern for fault tolerance.

Features:
- Circuit breaker pattern for fast failure during outages
- Exponential backoff with jitter for transient failures
- Automatic fallback signaling
- Mock mode for testing without Modal deployment

Example:
    >>> client = ArenaModalClient()
    >>> response = client.predict(image, "Rate the quality of this document...")
    >>> if response:
    ...     print(f"VLM says: {response.text}")
    ... else:
    ...     print("Modal unavailable")
"""

from __future__ import annotations

import base64
import io
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


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
    request_timeout_ms: int = 30000  # 30s for VLM inference
    max_retries: int = 2
    base_backoff_ms: int = 2000
    max_backoff_ms: int = 16000


@dataclass
class ArenaInferenceRequest:
    """Request format for Arena VLM inference.

    Attributes:
        image: PIL Image or numpy array
        prompt: Text prompt for the model
        model_id: HuggingFace model ID
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        request_id: Unique request identifier
    """

    image: Any  # PIL Image or np.ndarray
    prompt: str
    model_id: str = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit"
    max_new_tokens: int = 256
    temperature: float = 0.1
    request_id: str | None = None


@dataclass
class ArenaInferenceResponse:
    """Response format from Arena VLM inference.

    Attributes:
        text: Generated text response
        inference_time_ms: Server-side inference latency
        model_id: Model that generated the response
        device: Device used (GPU name)
        request_id: Request identifier for correlation
    """

    text: str
    inference_time_ms: float
    model_id: str
    device: str
    request_id: str | None = None


@dataclass
class CircuitBreakerState:
    """Track circuit breaker state and statistics."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0


class ArenaModalClient:
    """Client for Arena VLM inference on Modal with circuit breaker.

    This client provides resilient remote VLM inference with:
    - Circuit breaker pattern for fast failure during outages
    - Exponential backoff with jitter for transient failures
    - Automatic fallback signaling (returns None on breaker open)
    - Mock mode for testing without Modal deployment

    Example:
        >>> from PIL import Image
        >>> client = ArenaModalClient()
        >>> img = Image.open("document.png")
        >>> request = ArenaInferenceRequest(
        ...     image=img,
        ...     prompt="Rate the overall quality from 0-1...",
        ... )
        >>> response = client.predict(request)
        >>> if response:
        ...     print(f"Response: {response.text}")
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        app_name: str = "arena-benchmark",
        class_name: str = "VLMInference",
    ) -> None:
        """Initialize Arena Modal client.

        Args:
            config: Circuit breaker configuration
            app_name: Modal app name
            class_name: Modal class name
        """
        self.config = config or CircuitBreakerConfig()
        self.app_name = app_name
        self.class_name = class_name
        self.breaker_state = CircuitBreakerState()
        self._inference_cls: Any = None

        logger.info(
            "ArenaModalClient initialized",
            app_name=app_name,
            class_name=class_name,
            failure_threshold=self.config.failure_threshold,
        )

    def predict(self, request: ArenaInferenceRequest) -> ArenaInferenceResponse | None:
        """Execute VLM inference on Modal GPU.

        Args:
            request: Inference request with image and prompt

        Returns:
            ArenaInferenceResponse if successful, None if unavailable
        """
        self.breaker_state.total_requests += 1

        # Circuit breaker: Fast fail if open
        if self._should_reject_request():
            logger.warning(
                "Circuit breaker OPEN - rejecting request",
                state=self.breaker_state.state.value,
                failure_count=self.breaker_state.failure_count,
            )
            return None

        # Attempt request with retries
        last_exception: Exception | None = None
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
                self._record_success()
                return response

        # All retries exhausted
        self._record_failure()
        logger.error(
            "Modal request failed after all retries",
            total_attempts=self.config.max_retries + 1,
            error=str(last_exception),
            request_id=request.request_id,
        )
        return None

    def batch_predict(
        self, requests: list[ArenaInferenceRequest]
    ) -> list[ArenaInferenceResponse | None]:
        """Execute batch VLM inference on Modal GPU.

        Args:
            requests: List of inference requests

        Returns:
            List of responses (None for failed requests)
        """
        if not requests:
            return []

        self.breaker_state.total_requests += 1

        # Circuit breaker: Fast fail if open
        if self._should_reject_request():
            logger.warning(
                "Circuit breaker OPEN - rejecting batch request",
                state=self.breaker_state.state.value,
                batch_size=len(requests),
            )
            return [None] * len(requests)

        try:
            responses = self._execute_batch_request(requests)
            self._record_success()
            return responses  # noqa: TRY300
        except Exception as e:
            logger.exception(
                "Modal batch request failed",
                error=str(e),
                batch_size=len(requests),
            )
            self._record_failure()
            return [None] * len(requests)

    def _should_reject_request(self) -> bool:
        """Check if circuit breaker should reject the request."""
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
        self, request: ArenaInferenceRequest, attempt: int
    ) -> ArenaInferenceResponse:
        """Execute single request to Modal."""
        logger.debug(
            "Executing Modal request",
            attempt=attempt + 1,
            model_id=request.model_id,
            request_id=request.request_id,
        )

        # Use mock mode if enabled
        if self._use_mock_mode():
            return self._get_mock_response(request)

        # Call real Modal function
        response_dict = self._call_modal_function(request)

        if "error" in response_dict:
            raise RuntimeError(f"Modal inference error: {response_dict['error']}")

        return ArenaInferenceResponse(
            text=response_dict.get("text", ""),
            inference_time_ms=response_dict.get("inference_time_ms", 0.0),
            model_id=response_dict.get("model_id", request.model_id),
            device=response_dict.get("device", "unknown"),
            request_id=request.request_id,
        )

    def _execute_batch_request(
        self, requests: list[ArenaInferenceRequest]
    ) -> list[ArenaInferenceResponse | None]:
        """Execute batch request to Modal."""
        if self._use_mock_mode():
            return [self._get_mock_response(r) for r in requests]

        # Encode all images
        images_b64 = [self._encode_image(r.image) for r in requests]
        prompts = [r.prompt for r in requests]

        # Get model_id from first request (all should use same model)
        model_id = requests[0].model_id

        # Call Modal batch function
        inference_cls = self._get_inference_cls()
        inference = inference_cls()

        results: list[dict[str, Any]] = inference.batch_predict.remote(
            images_b64=images_b64,
            prompts=prompts,
            model_id=model_id,
            max_new_tokens=requests[0].max_new_tokens,
            temperature=requests[0].temperature,
        )

        # Convert to response objects
        responses: list[ArenaInferenceResponse | None] = []
        for i, result in enumerate(results):
            if "error" in result:
                logger.warning(
                    "Batch item failed",
                    index=i,
                    error=result["error"],
                )
                responses.append(None)
            else:
                responses.append(
                    ArenaInferenceResponse(
                        text=result.get("text", ""),
                        inference_time_ms=result.get("inference_time_ms", 0.0),
                        model_id=result.get("model_id", model_id),
                        device=result.get("device", "unknown"),
                        request_id=requests[i].request_id,
                    )
                )

        return responses

    def _get_inference_cls(self) -> Any:
        """Get or create Modal inference class reference."""
        if self._inference_cls is None:
            import modal

            try:
                self._inference_cls = modal.Cls.lookup(self.app_name, self.class_name)
            except modal.exception.NotFoundError as e:
                raise RuntimeError(
                    f"Modal app '{self.app_name}' not deployed. "
                    "Run: modal deploy modal/arena_benchmark.py"
                ) from e

        return self._inference_cls

    def _call_modal_function(self, request: ArenaInferenceRequest) -> dict[str, Any]:
        """Call Modal function with image data."""
        # Encode image as base64
        image_b64 = self._encode_image(request.image)

        # Get inference class and call predict
        inference_cls = self._get_inference_cls()
        inference = inference_cls()

        result: dict[str, Any] = inference.predict.remote(
            image_b64=image_b64,
            prompt=request.prompt,
            model_id=request.model_id,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
        )

        return result

    def _encode_image(self, image: Any) -> str:
        """Encode image as base64 JPEG.

        Args:
            image: PIL Image or numpy array

        Returns:
            Base64-encoded JPEG string
        """
        from PIL import Image as PILImage

        # Convert numpy array to PIL Image
        if isinstance(image, np.ndarray):
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            image = PILImage.fromarray(image)

        # Ensure RGB
        if hasattr(image, "convert"):
            image = image.convert("RGB")

        # Encode as JPEG
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    def _use_mock_mode(self) -> bool:
        """Check if mock mode is enabled."""
        if os.getenv("ARENA_MODAL_MOCK", "").lower() in ("true", "1", "yes"):
            return True

        # Check if Modal SDK is available
        try:
            import modal  # noqa: F401
        except ImportError:
            logger.warning("Modal SDK not available, using mock mode")
            return True

        return False

    def _get_mock_response(
        self, request: ArenaInferenceRequest
    ) -> ArenaInferenceResponse:
        """Generate mock response for testing."""
        # Generate deterministic mock response based on request
        mock_text = (
            "Overall: 0.75\n"
            "Sharpness: 0.82\n"
            "Color: 0.68\n"
            "The document shows moderate quality with some compression artifacts."
        )

        return ArenaInferenceResponse(
            text=mock_text,
            inference_time_ms=150.0,
            model_id=request.model_id,
            device="T4-mock",
            request_id=request.request_id,
        )

    def _calculate_backoff(self, attempt: int) -> int:
        """Calculate exponential backoff with jitter."""
        backoff = min(
            self.config.base_backoff_ms * (2**attempt),
            self.config.max_backoff_ms,
        )
        # Add jitter (±25%)
        jitter = random.uniform(0.75, 1.25)  # noqa: S311
        return int(backoff * jitter)

    def _record_success(self) -> None:
        """Record successful request."""
        self.breaker_state.total_successes += 1

        if self.breaker_state.state == CircuitState.HALF_OPEN:
            self.breaker_state.success_count += 1
            if self.breaker_state.success_count >= self.config.success_threshold:
                logger.info("Circuit breaker CLOSED - service recovered")
                self.breaker_state.state = CircuitState.CLOSED
                self.breaker_state.failure_count = 0
                self.breaker_state.success_count = 0
        elif self.breaker_state.state == CircuitState.CLOSED:
            self.breaker_state.failure_count = 0

    def _record_failure(self) -> None:
        """Record failed request."""
        self.breaker_state.total_failures += 1
        self.breaker_state.failure_count += 1
        self.breaker_state.last_failure_time = time.time()

        if self.breaker_state.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker OPEN - failure in half-open state")
            self.breaker_state.state = CircuitState.OPEN
            self.breaker_state.success_count = 0
        elif (
            self.breaker_state.state == CircuitState.CLOSED
            and self.breaker_state.failure_count >= self.config.failure_threshold
        ):
            logger.warning(
                "Circuit breaker OPEN - failure threshold exceeded",
                failure_count=self.breaker_state.failure_count,
            )
            self.breaker_state.state = CircuitState.OPEN

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
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
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        logger.info(
            "Circuit breaker reset",
            previous_state=self.breaker_state.state.value,
        )
        self.breaker_state = CircuitBreakerState()
        self._inference_cls = None

    def is_available(self) -> bool:
        """Check if Modal service is available.

        Returns:
            True if circuit is closed or half-open
        """
        return not self._should_reject_request()
