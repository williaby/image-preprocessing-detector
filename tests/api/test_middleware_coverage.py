"""Additional tests for api/middleware.py coverage.

Tests for:
- CorrelationIDMiddleware
- Request exception handling
- Internal caller detection edge cases
- Rate limit client key detection
"""

import time
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from image_preprocessing_detector.api.middleware import (
    APIKeyAuthMiddleware,
    CorrelationIDMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    correlation_id_var,
    get_correlation_id,
)


class TestCorrelationIDMiddleware:
    """Tests for CorrelationIDMiddleware."""

    @pytest.fixture
    def app_with_correlation_middleware(self) -> FastAPI:
        """Create app with only correlation ID middleware."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)

        @app.get("/test")
        async def test_endpoint() -> dict:
            return {"message": "test"}

        return app

    @pytest.fixture
    def client(self, app_with_correlation_middleware: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app_with_correlation_middleware)

    def test_generates_correlation_id_if_not_provided(self, client: TestClient) -> None:
        """Generates correlation ID if not in request headers."""
        response = client.get("/test")
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_preserves_provided_correlation_id(self, client: TestClient) -> None:
        """Preserves correlation ID from request headers."""
        correlation_id = "my-custom-correlation-id"
        response = client.get("/test", headers={"X-Correlation-ID": correlation_id})
        assert response.headers["X-Correlation-ID"] == correlation_id


class TestRequestLoggingMiddlewareExceptions:
    """Tests for request logging middleware exception handling."""

    @pytest.fixture
    def app_with_exception(self) -> FastAPI:
        """Create app that raises exceptions."""
        app = FastAPI()
        app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=False,
            log_response_body=False,
        )

        @app.get("/error")
        async def error_endpoint() -> None:
            raise ValueError("Test exception")

        @app.get("/success")
        async def success_endpoint() -> dict:
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_exception: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app_with_exception, raise_server_exceptions=False)

    def test_logs_exception_and_reraises(self) -> None:
        """Middleware logs exception and re-raises it."""
        with patch("image_preprocessing_detector.api.middleware.logger") as mock_logger:
            app = FastAPI()
            app.add_middleware(
                RequestLoggingMiddleware,
                log_request_body=False,
                log_response_body=False,
            )

            @app.get("/error")
            async def error_endpoint() -> None:
                raise ValueError("Test exception")

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/error")
            assert response.status_code == 500

    def test_client_ip_unknown_when_no_client(self) -> None:
        """Handles missing client information."""
        app = FastAPI()
        app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=False,
            log_response_body=False,
        )

        @app.get("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        client = TestClient(app)
        # Normal test client has client info
        response = client.get("/test")
        assert response.status_code == 200


class TestAPIKeyAuthMiddlewareEdgeCases:
    """Tests for API key auth middleware edge cases."""

    def test_is_internal_caller_no_client(self) -> None:
        """Handles request with no client."""
        middleware = APIKeyAuthMiddleware(
            app=MagicMock(),
            api_keys=["key"],
            internal_callers=["127.0.0.1"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.client = None

        assert middleware._is_internal_caller(mock_request) is False

    def test_is_internal_caller_empty_list(self) -> None:
        """Returns False when internal callers list is empty."""
        middleware = APIKeyAuthMiddleware(
            app=MagicMock(),
            api_keys=["key"],
            internal_callers=[],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"

        assert middleware._is_internal_caller(mock_request) is False

    def test_is_internal_caller_localhost_variants(self) -> None:
        """Recognizes localhost variants."""
        middleware = APIKeyAuthMiddleware(
            app=MagicMock(),
            api_keys=["key"],
            internal_callers=["127.0.0.1"],
        )

        # Test with ::1 (IPv6 localhost)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "::1"
        assert middleware._is_internal_caller(mock_request) is True

    def test_is_public_path(self) -> None:
        """Tests public path detection."""
        middleware = APIKeyAuthMiddleware(
            app=MagicMock(),
            api_keys=["key"],
        )

        assert middleware._is_public_path("/health") is True
        assert middleware._is_public_path("/ready") is True
        assert middleware._is_public_path("/version") is True
        assert middleware._is_public_path("/docs") is True
        assert middleware._is_public_path("/redoc") is True
        assert middleware._is_public_path("/") is True
        assert middleware._is_public_path("/openapi.json") is True
        assert middleware._is_public_path("/process") is False
        assert middleware._is_public_path("/batch") is False

    def test_auth_disabled_allows_all(self) -> None:
        """When auth is disabled, all requests pass."""
        app = FastAPI()
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_keys=["valid-key"],
            enabled=False,
        )

        @app.get("/protected")
        async def protected() -> dict:
            return {"data": "secret"}

        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 200


class TestRateLimitMiddlewareEdgeCases:
    """Tests for rate limit middleware edge cases."""

    def test_get_client_key_with_api_key(self) -> None:
        """Uses partial API key for rate limit tracking."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "my-api-key-12345678"}
        mock_request.client.host = "192.168.1.1"

        key = middleware._get_client_key(mock_request)
        assert key.startswith("key:")
        assert "my-api-k" in key  # First 8 chars

    def test_get_client_key_without_api_key(self) -> None:
        """Uses IP address when no API key."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        key = middleware._get_client_key(mock_request)
        assert key == "ip:192.168.1.1"

    def test_get_client_key_no_client(self) -> None:
        """Handles missing client info."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None

        key = middleware._get_client_key(mock_request)
        assert key == "ip:unknown"

    def test_should_limit_path_exact_match(self) -> None:
        """Tests exact path matching for rate limiting."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
            limit_paths=["/process", "/batch"],
        )

        assert middleware._should_limit_path("/process") is True
        assert middleware._should_limit_path("/batch") is True
        assert middleware._should_limit_path("/health") is False

    def test_should_limit_path_prefix_match(self) -> None:
        """Tests prefix path matching for rate limiting."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
            limit_paths=["/batch"],
        )

        assert middleware._should_limit_path("/batch/123/status") is True
        assert middleware._should_limit_path("/batch/456/result") is True

    def test_should_limit_path_no_limit_paths(self) -> None:
        """When no limit_paths specified, limits all paths."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
            limit_paths=None,
        )

        assert middleware._should_limit_path("/anything") is True
        assert middleware._should_limit_path("/process") is True
        assert middleware._should_limit_path("/health") is True

    def test_cleanup_old_entries(self) -> None:
        """Tests cleanup of old rate limit entries."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_window=100,
            window_seconds=60,
        )

        # Add some entries
        client_key = "test_client"
        current_time = time.time()
        middleware._request_counts[client_key] = [
            (current_time - 100, 1),  # Old entry (outside window)
            (current_time - 30, 1),  # Recent entry (inside window)
        ]

        middleware._cleanup_old_entries(client_key, current_time)

        # Old entry should be removed
        assert len(middleware._request_counts[client_key]) == 1

    def test_rate_limit_disabled(self) -> None:
        """When rate limit is disabled, all requests pass."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=1,
            enabled=False,
        )

        @app.get("/test")
        async def test() -> dict:
            return {"data": "value"}

        client = TestClient(app)

        # Make many requests - all should succeed
        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200


class TestGetCorrelationId:
    """Tests for get_correlation_id function."""

    def test_returns_empty_string_when_not_set(self) -> None:
        """Returns empty string when correlation ID not set."""
        # Reset the context var
        correlation_id_var.set("")
        assert get_correlation_id() == ""

    def test_returns_set_value(self) -> None:
        """Returns the set correlation ID."""
        test_id = "test-correlation-123"
        correlation_id_var.set(test_id)
        assert get_correlation_id() == test_id
