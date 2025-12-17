"""Tests for Arena Modal client."""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import numpy as np

from image_preprocessing_detector.labeling.arena.modal_client import (
    ArenaInferenceRequest,
    ArenaInferenceResponse,
    ArenaModalClient,
    CircuitBreakerConfig,
    CircuitState,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout_seconds == 60.0
        assert config.request_timeout_ms == 30000
        assert config.max_retries == 2
        assert config.base_backoff_ms == 2000
        assert config.max_backoff_ms == 16000

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout_seconds=120.0,
        )

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_seconds == 120.0


class TestArenaInferenceRequest:
    """Tests for ArenaInferenceRequest dataclass."""

    def test_minimal_request(self) -> None:
        """Test request with minimal fields."""
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        request = ArenaInferenceRequest(
            image=image,
            prompt="Rate this image",
        )

        assert request.prompt == "Rate this image"
        assert request.model_id == "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit"
        assert request.max_new_tokens == 256
        assert request.temperature == 0.1
        assert request.request_id is None

    def test_full_request(self) -> None:
        """Test request with all fields."""
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        request = ArenaInferenceRequest(
            image=image,
            prompt="Rate this image",
            model_id="custom/model",
            max_new_tokens=512,
            temperature=0.5,
            request_id="test-123",
        )

        assert request.model_id == "custom/model"
        assert request.max_new_tokens == 512
        assert request.temperature == 0.5
        assert request.request_id == "test-123"


class TestArenaInferenceResponse:
    """Tests for ArenaInferenceResponse dataclass."""

    def test_response_creation(self) -> None:
        """Test response creation."""
        response = ArenaInferenceResponse(
            text="Overall: 0.75\nSharpness: 0.82\nColor: 0.68",
            inference_time_ms=150.0,
            model_id="test/model",
            device="T4",
        )

        assert "Overall: 0.75" in response.text
        assert response.inference_time_ms == 150.0
        assert response.model_id == "test/model"
        assert response.device == "T4"


class TestArenaModalClient:
    """Tests for ArenaModalClient class."""

    def test_initialization(self) -> None:
        """Test client initialization."""
        client = ArenaModalClient()

        assert client.app_name == "arena-benchmark"
        assert client.class_name == "VLMInference"
        assert client.breaker_state.state == CircuitState.CLOSED

    def test_custom_config(self) -> None:
        """Test client with custom config."""
        config = CircuitBreakerConfig(failure_threshold=5)
        client = ArenaModalClient(config=config)

        assert client.config.failure_threshold == 5

    def test_mock_mode_enabled_by_env(self) -> None:
        """Test that mock mode is enabled via environment variable."""
        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            client = ArenaModalClient()
            assert client._use_mock_mode() is True

    def test_mock_response_format(self) -> None:
        """Test mock response has expected format."""
        client = ArenaModalClient()
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        request = ArenaInferenceRequest(
            image=image,
            prompt="Rate this image",
            request_id="test-123",
        )

        response = client._get_mock_response(request)

        assert response.text is not None
        assert "Overall:" in response.text
        assert "Sharpness:" in response.text
        assert "Color:" in response.text
        assert response.inference_time_ms > 0
        assert response.device == "T4-mock"
        assert response.request_id == "test-123"

    def test_predict_with_mock_mode(self) -> None:
        """Test predict returns mock response when modal unavailable."""
        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            client = ArenaModalClient()
            image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            request = ArenaInferenceRequest(
                image=image,
                prompt="Rate this image",
            )

            response = client.predict(request)

            assert response is not None
            assert response.text is not None
            assert response.device == "T4-mock"

    def test_circuit_breaker_opens_on_failures(self) -> None:
        """Test circuit breaker opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        client = ArenaModalClient(config=config)

        # Record failures
        client._record_failure()
        assert client.breaker_state.state == CircuitState.CLOSED

        client._record_failure()
        assert client.breaker_state.state == CircuitState.OPEN

    def test_circuit_breaker_rejects_when_open(self) -> None:
        """Test circuit breaker rejects requests when open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=60.0,
        )
        client = ArenaModalClient(config=config)

        # Force circuit open
        client._record_failure()
        assert client.breaker_state.state == CircuitState.OPEN

        # Should reject
        assert client._should_reject_request() is True

    def test_circuit_breaker_half_open_after_timeout(self) -> None:
        """Test circuit breaker enters half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.1,  # Very short timeout for test
        )
        client = ArenaModalClient(config=config)

        # Force circuit open
        client._record_failure()
        assert client.breaker_state.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Should transition to half-open
        assert client._should_reject_request() is False
        assert client.breaker_state.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_on_success(self) -> None:
        """Test circuit breaker closes after successful requests."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        client = ArenaModalClient(config=config)

        # Force circuit open then half-open
        client._record_failure()
        time.sleep(0.15)
        client._should_reject_request()  # Triggers transition to half-open

        assert client.breaker_state.state == CircuitState.HALF_OPEN

        # Record successes
        client._record_success()
        assert client.breaker_state.state == CircuitState.HALF_OPEN

        client._record_success()
        assert client.breaker_state.state == CircuitState.CLOSED

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        config = CircuitBreakerConfig(
            base_backoff_ms=1000,
            max_backoff_ms=8000,
        )
        client = ArenaModalClient(config=config)

        # First attempt backoff should be around base
        backoff0 = client._calculate_backoff(0)
        assert 750 <= backoff0 <= 1250  # With jitter

        # Second attempt should be around 2x base
        backoff1 = client._calculate_backoff(1)
        assert 1500 <= backoff1 <= 2500  # With jitter

        # Later attempts should be capped
        backoff3 = client._calculate_backoff(10)
        assert backoff3 <= 10000  # Max with jitter

    def test_get_stats(self) -> None:
        """Test getting circuit breaker statistics."""
        client = ArenaModalClient()

        stats = client.get_stats()

        assert "state" in stats
        assert "total_requests" in stats
        assert "total_successes" in stats
        assert "total_failures" in stats
        assert "success_rate" in stats
        assert stats["state"] == "closed"
        assert stats["total_requests"] == 0

    def test_reset(self) -> None:
        """Test resetting circuit breaker."""
        client = ArenaModalClient()

        # Force some state changes
        client._record_failure()
        client._record_failure()
        client._record_failure()

        assert client.breaker_state.state == CircuitState.OPEN
        assert client.breaker_state.total_failures > 0

        # Reset
        client.reset()

        assert client.breaker_state.state == CircuitState.CLOSED
        assert client.breaker_state.total_failures == 0
        assert client.breaker_state.failure_count == 0

    def test_is_available(self) -> None:
        """Test is_available method."""
        client = ArenaModalClient()

        # Initially available
        assert client.is_available() is True

        # Force circuit open
        config = CircuitBreakerConfig(failure_threshold=1)
        client = ArenaModalClient(config=config)
        client._record_failure()

        # Now unavailable
        assert client.is_available() is False

    def test_image_encoding(self) -> None:
        """Test image encoding to base64."""
        client = ArenaModalClient()

        # Test with numpy array
        image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        encoded = client._encode_image(image)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

        # Test with PIL Image
        from PIL import Image as PILImage

        pil_image = PILImage.fromarray(image)
        encoded_pil = client._encode_image(pil_image)

        assert isinstance(encoded_pil, str)
        assert len(encoded_pil) > 0

    def test_batch_predict_with_mock(self) -> None:
        """Test batch predict with mock mode."""
        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            client = ArenaModalClient()

            images = [
                np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
                for _ in range(3)
            ]
            requests = [
                ArenaInferenceRequest(
                    image=img,
                    prompt="Rate this image",
                    request_id=f"batch-{i}",
                )
                for i, img in enumerate(images)
            ]

            responses = client.batch_predict(requests)

            assert len(responses) == 3
            for response in responses:
                assert response is not None
                assert response.text is not None

    def test_batch_predict_empty_list(self) -> None:
        """Test batch predict with empty list."""
        client = ArenaModalClient()

        responses = client.batch_predict([])

        assert responses == []
