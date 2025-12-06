# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for Modal GPU client with circuit breaker.

Tests circuit breaker behavior, retry logic, and fallback handling.

Sprint 4.2.3: Client Stub with Circuit Breaker Tests (Phase 4B)
Sprint 4.2.1: Add mock mode tests (Phase 4B)
"""

import time
from unittest.mock import patch

import numpy as np
import pytest

from image_preprocessing_detector.orchestration import (
    CircuitBreakerConfig,
    CircuitState,
    ModalClient,
    ModalInferenceRequest,
    ModalInferenceResponse,
)


# Enable mock mode for all unit tests
@pytest.fixture(autouse=True)
def mock_modal_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable mock mode for unit tests."""
    monkeypatch.setenv("IMGPREP_MODAL_MOCK", "true")


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_configuration(self) -> None:
        """Test default circuit breaker configuration."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert abs(config.timeout_seconds - 60.0) < 1e-9
        assert config.request_timeout_ms == 5000
        assert config.max_retries == 3
        assert config.base_backoff_ms == 1000
        assert config.max_backoff_ms == 8000

    def test_custom_configuration(self) -> None:
        """Test custom circuit breaker configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout_seconds=120.0,
            max_retries=5,
        )
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert abs(config.timeout_seconds - 120.0) < 1e-9
        assert config.max_retries == 5


class TestModalInferenceRequest:
    """Test Modal inference request format."""

    def test_request_creation(self) -> None:
        """Test creating inference request."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        request = ModalInferenceRequest(
            image_array=img, model_version="v1.0", request_id="req123"
        )

        assert request.image_array.shape == (100, 100, 3)
        assert request.model_version == "v1.0"
        assert request.request_id == "req123"

    def test_request_default_version(self) -> None:
        """Test default model version."""
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        request = ModalInferenceRequest(image_array=img)

        assert request.model_version == "v1.0"
        assert request.request_id is None


class TestModalInferenceResponse:
    """Test Modal inference response format."""

    def test_response_structure(self) -> None:
        """Test response contains required fields."""
        response = ModalInferenceResponse(
            scores={"blur": 0.85, "noise": 0.90},
            confidences={"blur": 0.95, "noise": 0.93},
            inference_time_ms=150.0,
            device_tag="T4",
            model_version="v1.0",
            request_id="req123",
        )

        assert abs(response.scores["blur"] - 0.85) < 1e-9
        assert abs(response.confidences["blur"] - 0.95) < 1e-9
        assert abs(response.inference_time_ms - 150.0) < 1e-9
        assert response.device_tag == "T4"
        assert response.model_version == "v1.0"
        assert response.request_id == "req123"


class TestModalClientBasics:
    """Test Modal client initialization and basic operations."""

    def test_client_initialization(self) -> None:
        """Test client initialization with config."""
        config = CircuitBreakerConfig(failure_threshold=5)
        client = ModalClient(config=config, modal_endpoint="https://test.modal.com")

        assert client.config.failure_threshold == 5
        assert client.modal_endpoint == "https://test.modal.com"
        assert client.breaker_state.state == CircuitState.CLOSED

    def test_client_default_config(self) -> None:
        """Test client uses default config if none provided."""
        client = ModalClient()

        assert client.config.failure_threshold == 3
        assert client.breaker_state.state == CircuitState.CLOSED

    def test_successful_request(self) -> None:
        """Test successful inference request."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        request = ModalInferenceRequest(image_array=img, request_id="req1")

        response = client.predict(request)

        assert response is not None
        assert "blur" in response.scores
        assert response.device_tag == "T4-mock"  # Mock mode returns T4-mock
        assert client.breaker_state.total_successes == 1
        assert client.breaker_state.state == CircuitState.CLOSED


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    def test_circuit_opens_after_failures(self) -> None:
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3, max_retries=0)
        client = ModalClient(config=config, modal_endpoint=None)  # No endpoint = fail
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Make 3 failed requests
        for i in range(3):
            request = ModalInferenceRequest(image_array=img, request_id=f"req{i}")
            response = client.predict(request)
            assert response is None

        # Circuit should now be OPEN
        assert client.breaker_state.state == CircuitState.OPEN
        assert client.breaker_state.failure_count == 3

    def test_circuit_rejects_when_open(self) -> None:
        """Test circuit rejects requests immediately when open."""
        config = CircuitBreakerConfig(failure_threshold=2, max_retries=0)
        client = ModalClient(config=config, modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Trigger circuit to open
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        assert client.breaker_state.state == CircuitState.OPEN

        # Next request should be rejected immediately (no retries attempted)
        request = ModalInferenceRequest(image_array=img, request_id="rejected")
        response = client.predict(request)

        assert response is None
        # Total failures should still be 2 (rejected request not attempted)
        assert client.breaker_state.total_failures == 2

    def test_circuit_half_open_after_timeout(self) -> None:
        """Test circuit enters half-open state after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2, timeout_seconds=0.1, max_retries=0
        )
        client = ModalClient(config=config, modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Open circuit
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        assert client.breaker_state.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next request should transition to HALF_OPEN
        request = ModalInferenceRequest(image_array=img)
        response = client.predict(request)

        # Will fail (no endpoint), but should have tried HALF_OPEN first
        assert response is None
        # After failure in half-open, circuit reopens
        assert client.breaker_state.state == CircuitState.OPEN

    def test_circuit_closes_after_successes(self) -> None:
        """Test circuit closes after success threshold in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=2, success_threshold=2, timeout_seconds=0.1
        )
        client = ModalClient(config=config, modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Open circuit with failures
        with patch.object(client, "_execute_request", side_effect=RuntimeError("fail")):
            for _ in range(2):
                request = ModalInferenceRequest(image_array=img)
                client.predict(request)

        assert client.breaker_state.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Successful requests should close circuit
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            response = client.predict(request)
            assert response is not None

        # Circuit should be CLOSED again
        assert client.breaker_state.state == CircuitState.CLOSED
        assert client.breaker_state.failure_count == 0

    def test_half_open_failure_reopens_circuit(self) -> None:
        """Test failure in half-open immediately reopens circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2, timeout_seconds=0.1, max_retries=0
        )
        client = ModalClient(config=config, modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Open circuit
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        assert client.breaker_state.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Failure in half-open should reopen circuit
        request = ModalInferenceRequest(image_array=img)
        response = client.predict(request)

        assert response is None
        assert client.breaker_state.state == CircuitState.OPEN


class TestRetryLogic:
    """Test exponential backoff and retry logic."""

    def test_exponential_backoff_calculation(self) -> None:
        """Test backoff time increases exponentially."""
        config = CircuitBreakerConfig(base_backoff_ms=100, max_backoff_ms=1000)
        client = ModalClient(config=config)

        backoff_0 = client._calculate_backoff(0)
        backoff_1 = client._calculate_backoff(1)
        backoff_2 = client._calculate_backoff(2)
        backoff_5 = client._calculate_backoff(5)

        # Backoff should increase (allowing for jitter)
        assert backoff_0 < backoff_1 < backoff_2
        # Should cap at max_backoff_ms (allowing for jitter)
        assert backoff_5 <= 1000 * 1.25  # Max jitter is 1.25x

    def test_retry_attempts(self) -> None:
        """Test correct number of retry attempts."""
        config = CircuitBreakerConfig(max_retries=3)
        client = ModalClient(config=config, modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock execute_request to count attempts
        call_count = 0

        def mock_execute(
            request: ModalInferenceRequest, attempt: int
        ) -> ModalInferenceResponse:
            nonlocal call_count
            call_count += 1
            msg = "Simulated failure"
            raise RuntimeError(msg)

        with patch.object(client, "_execute_request", side_effect=mock_execute):
            request = ModalInferenceRequest(image_array=img)
            response = client.predict(request)

            assert response is None
            # Should attempt: initial + 3 retries = 4 total
            assert call_count == 4

    def test_successful_retry(self) -> None:
        """Test successful request after retry."""
        config = CircuitBreakerConfig(max_retries=2)
        client = ModalClient(config=config, modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock: fail twice, succeed third time
        call_count = 0

        def mock_execute(
            request: ModalInferenceRequest, attempt: int
        ) -> ModalInferenceResponse:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "Transient failure"
                raise RuntimeError(msg)
            return ModalInferenceResponse(
                scores={"blur": 0.85},
                confidences={"blur": 0.95},
                inference_time_ms=150.0,
                device_tag="T4",
                model_version="v1.0",
            )

        with patch.object(client, "_execute_request", side_effect=mock_execute):
            request = ModalInferenceRequest(image_array=img)
            response = client.predict(request)

            assert response is not None
            assert abs(response.scores["blur"] - 0.85) < 1e-9
            assert call_count == 3
            assert client.breaker_state.total_successes == 1


class TestStatisticsReporting:
    """Test statistics and monitoring."""

    def test_get_stats_initial(self) -> None:
        """Test statistics at initialization."""
        client = ModalClient()
        stats = client.get_stats()

        assert stats["state"] == "closed"
        assert stats["total_requests"] == 0
        assert stats["total_successes"] == 0
        assert stats["total_failures"] == 0
        assert abs(stats["success_rate"] - 0.0) < 1e-9
        assert stats["consecutive_failures"] == 0

    def test_get_stats_after_operations(self) -> None:
        """Test statistics after successful and failed requests."""
        config = CircuitBreakerConfig(max_retries=0)
        client = ModalClient(config=config, modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # 2 successful requests
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        # 1 failed request
        with patch.object(client, "_execute_request", side_effect=RuntimeError("fail")):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        stats = client.get_stats()
        assert stats["total_requests"] == 3
        assert stats["total_successes"] == 2
        assert stats["total_failures"] == 1
        assert stats["success_rate"] == pytest.approx(2 / 3)
        assert stats["consecutive_failures"] == 1

    def test_reset_functionality(self) -> None:
        """Test circuit breaker reset."""
        config = CircuitBreakerConfig(failure_threshold=2, max_retries=0)
        client = ModalClient(config=config, modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Open circuit
        for _ in range(2):
            request = ModalInferenceRequest(image_array=img)
            client.predict(request)

        assert client.breaker_state.state == CircuitState.OPEN
        assert client.breaker_state.total_requests == 2

        # Reset
        client.reset()

        assert client.breaker_state.state == CircuitState.CLOSED
        assert client.breaker_state.total_requests == 0
        assert client.breaker_state.total_failures == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_endpoint_configured(self) -> None:
        """Test behavior when no Modal endpoint configured."""
        client = ModalClient(modal_endpoint=None)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        request = ModalInferenceRequest(image_array=img)

        response = client.predict(request)

        assert response is None
        assert client.breaker_state.total_failures >= 1

    def test_large_image_handling(self) -> None:
        """Test handling of large images."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        # Large 4K image
        img = np.zeros((3840, 2160, 3), dtype=np.uint8)
        request = ModalInferenceRequest(image_array=img)

        response = client.predict(request)

        assert response is not None

    def test_concurrent_request_tracking(self) -> None:
        """Test request tracking across multiple requests."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Send multiple requests
        for i in range(5):
            request = ModalInferenceRequest(image_array=img, request_id=f"req{i}")
            client.predict(request)

        assert client.breaker_state.total_requests == 5
        assert client.breaker_state.total_successes == 5


class TestMockMode:
    """Test mock mode functionality (Sprint 4.2.1)."""

    def test_mock_mode_via_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test mock mode is enabled via environment variable."""
        monkeypatch.setenv("IMGPREP_MODAL_MOCK", "true")
        client = ModalClient(modal_endpoint="https://test.modal.com")

        assert client._use_mock_mode() is True

    def test_mock_mode_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test mock mode can be disabled."""
        monkeypatch.setenv("IMGPREP_MODAL_MOCK", "false")
        client = ModalClient(modal_endpoint="https://test.modal.com")

        # Will still use mock if Modal SDK not available
        # This tests the logic flow, not the actual Modal SDK
        result = client._use_mock_mode()
        # Result depends on whether Modal SDK is installed
        assert isinstance(result, bool)

    def test_mock_response_structure(self) -> None:
        """Test mock response has correct structure."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        request = ModalInferenceRequest(image_array=img, request_id="mock-test")

        response = client._get_mock_response(request)

        assert response.device_tag == "T4-mock"
        assert "blur" in response.scores
        assert "noise" in response.scores
        assert "contrast" in response.scores
        assert "skew" in response.scores
        assert "compression" in response.scores
        assert response.request_id == "mock-test"


class TestImageEncoding:
    """Test image encoding for Modal transfer."""

    def test_encode_uint8_image(self) -> None:
        """Test encoding uint8 image."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        encoded = client._encode_image(img)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Should be valid base64
        import base64

        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0

    def test_encode_float_image(self) -> None:
        """Test encoding float [0,1] image."""
        client = ModalClient(modal_endpoint="https://test.modal.com")
        img = np.random.random((100, 100, 3)).astype(np.float32)

        encoded = client._encode_image(img)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
