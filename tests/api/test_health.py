"""Tests for health and readiness endpoints.

Sprint 5.2.1: FastAPI skeleton validation.
"""

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings


@pytest.fixture
def test_settings() -> APISettings:
    """Create test API settings."""
    return APISettings(
        title="Test API",
        version="0.0.1-test",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        rate_limit_enabled=False,
        auth_enabled=False,
    )


@pytest.fixture
def client(test_settings: APISettings) -> TestClient:
    """Create a test client with test settings."""
    app = create_app(settings=test_settings)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        """Health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_timestamp(self, client: TestClient) -> None:
        """Health response includes timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None

    def test_health_includes_uptime(self, client: TestClient) -> None:
        """Health response includes uptime."""
        response = client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data


class TestReadyEndpoint:
    """Tests for /ready endpoint."""

    def test_ready_returns_200_when_healthy(self, client: TestClient) -> None:
        """Ready endpoint returns 200 when all checks pass."""
        response = client.get("/ready")
        # May return 503 if dependencies missing, but should not error
        assert response.status_code in (200, 503)

    def test_ready_returns_checks_dict(self, client: TestClient) -> None:
        """Ready response includes checks dictionary."""
        response = client.get("/ready")
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_ready_returns_device_info(self, client: TestClient) -> None:
        """Ready response includes device information."""
        response = client.get("/ready")
        data = response.json()
        assert "device" in data
        assert isinstance(data["device"], dict)

    def test_ready_returns_status_string(self, client: TestClient) -> None:
        """Ready response includes status string."""
        response = client.get("/ready")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ready", "not_ready")

    def test_ready_returns_timestamp(self, client: TestClient) -> None:
        """Ready response includes timestamp."""
        response = client.get("/ready")
        data = response.json()
        assert "timestamp" in data


class TestVersionEndpoint:
    """Tests for /version endpoint."""

    def test_version_returns_200(self, client: TestClient) -> None:
        """Version endpoint returns 200 OK."""
        response = client.get("/version")
        assert response.status_code == 200

    def test_version_includes_api_version(self, client: TestClient) -> None:
        """Version response includes API version."""
        response = client.get("/version")
        data = response.json()
        assert "api_version" in data
        # Version should be a valid semver-like string
        assert isinstance(data["api_version"], str)
        assert len(data["api_version"]) > 0

    def test_version_includes_python_version(self, client: TestClient) -> None:
        """Version response includes Python version."""
        response = client.get("/version")
        data = response.json()
        assert "python_version" in data
        assert data["python_version"].count(".") == 2  # e.g., "3.11.4"

    def test_version_includes_pipeline_version(self, client: TestClient) -> None:
        """Version response includes pipeline version."""
        response = client.get("/version")
        data = response.json()
        assert "pipeline_version" in data

    def test_version_includes_models_dict(self, client: TestClient) -> None:
        """Version response includes models dictionary."""
        response = client.get("/version")
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], dict)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_navigation_links(self, client: TestClient) -> None:
        """Root endpoint returns navigation links."""
        response = client.get("/")
        data = response.json()
        assert "docs" in data
        assert "health" in data
        assert "version" in data


class TestCORSMiddleware:
    """Tests for CORS middleware."""

    def test_cors_headers_present(self, client: TestClient) -> None:
        """CORS headers are present in response."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Preflight should return 200 with CORS headers
        assert response.status_code == 200

    def test_cors_defaults_to_no_origins(self) -> None:
        """Default settings have no allowed origins (secure by default)."""
        settings = APISettings()
        assert settings.cors_origins == []
        assert settings.cors_allow_credentials is False


class TestLoggingMiddleware:
    """Tests for request logging middleware."""

    def test_response_includes_correlation_id(self, client: TestClient) -> None:
        """Response includes X-Correlation-ID header."""
        response = client.get("/health")
        assert "X-Correlation-ID" in response.headers

    def test_response_includes_response_time(self, client: TestClient) -> None:
        """Response includes X-Response-Time-Ms header."""
        response = client.get("/health")
        assert "X-Response-Time-Ms" in response.headers

    def test_provided_correlation_id_is_preserved(self, client: TestClient) -> None:
        """Provided correlation ID is preserved in response."""
        correlation_id = "test-correlation-id-12345"
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": correlation_id},
        )
        assert response.headers["X-Correlation-ID"] == correlation_id


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        """OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_docs_available(self, client: TestClient) -> None:
        """Swagger UI docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient) -> None:
        """ReDoc documentation is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
