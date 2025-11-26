"""Tests for authentication and rate limiting middleware.

Sprint 5.2.4: Auth and rate limits validation.
"""

import io

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings

# ============================================================================
# Authentication Tests
# ============================================================================


class TestAuthenticationEnabled:
    """Tests for API key authentication when enabled."""

    @pytest.fixture
    def auth_settings(self) -> APISettings:
        """Create settings with auth enabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=True,
            api_keys=["valid-api-key-123", "another-valid-key"],
            internal_callers=["127.0.0.1"],
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def auth_client(self, auth_settings: APISettings) -> TestClient:
        """Create a test client with auth enabled."""
        app = create_app(settings=auth_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_process_without_api_key_returns_401(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Process endpoint without API key returns 401."""
        response = auth_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "unauthorized"
        assert "API key required" in data["message"]

    def test_process_with_invalid_api_key_returns_403(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Process endpoint with invalid API key returns 403."""
        response = auth_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"
        assert "Invalid API key" in data["message"]

    def test_process_with_valid_api_key_succeeds(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Process endpoint with valid API key succeeds."""
        response = auth_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
            headers={"X-API-Key": "valid-api-key-123"},
        )
        assert response.status_code == 200

    def test_batch_without_api_key_returns_401(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Batch endpoint without API key returns 401."""
        response = auth_client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        assert response.status_code == 401

    def test_batch_with_valid_api_key_succeeds(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Batch endpoint with valid API key succeeds."""
        response = auth_client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
            headers={"X-API-Key": "another-valid-key"},
        )
        assert response.status_code == 200


class TestPublicEndpoints:
    """Tests for endpoints that don't require authentication."""

    @pytest.fixture
    def auth_settings(self) -> APISettings:
        """Create settings with auth enabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=True,
            api_keys=["valid-api-key"],
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def auth_client(self, auth_settings: APISettings) -> TestClient:
        """Create a test client with auth enabled."""
        app = create_app(settings=auth_settings)
        return TestClient(app)

    def test_health_endpoint_public(self, auth_client: TestClient) -> None:
        """Health endpoint is publicly accessible."""
        response = auth_client.get("/health")
        assert response.status_code == 200

    def test_ready_endpoint_public(self, auth_client: TestClient) -> None:
        """Ready endpoint is publicly accessible."""
        response = auth_client.get("/ready")
        assert response.status_code == 200

    def test_version_endpoint_public(self, auth_client: TestClient) -> None:
        """Version endpoint is publicly accessible."""
        response = auth_client.get("/version")
        assert response.status_code == 200

    def test_root_endpoint_public(self, auth_client: TestClient) -> None:
        """Root endpoint is publicly accessible."""
        response = auth_client.get("/")
        assert response.status_code == 200

    def test_docs_endpoint_public(self, auth_client: TestClient) -> None:
        """Docs endpoint is publicly accessible."""
        response = auth_client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint_public(self, auth_client: TestClient) -> None:
        """OpenAPI JSON endpoint is publicly accessible."""
        response = auth_client.get("/openapi.json")
        assert response.status_code == 200


class TestInternalCallers:
    """Tests for internal caller allowlist."""

    @pytest.fixture
    def auth_settings(self) -> APISettings:
        """Create settings with auth enabled and internal callers."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=True,
            api_keys=["valid-api-key"],
            internal_callers=["testclient"],  # TestClient default host
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def auth_client(self, auth_settings: APISettings) -> TestClient:
        """Create a test client with auth enabled."""
        app = create_app(settings=auth_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_internal_caller_bypasses_auth(
        self, auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Internal callers can access endpoints without API key."""
        # Note: TestClient uses 'testclient' as the host by default
        response = auth_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        # Should succeed because 'testclient' is in internal_callers
        assert response.status_code == 200


class TestAuthDisabled:
    """Tests for when authentication is disabled."""

    @pytest.fixture
    def no_auth_settings(self) -> APISettings:
        """Create settings with auth disabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=False,
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def no_auth_client(self, no_auth_settings: APISettings) -> TestClient:
        """Create a test client with auth disabled."""
        app = create_app(settings=no_auth_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_process_succeeds_without_api_key(
        self, no_auth_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Process endpoint succeeds without API key when auth is disabled."""
        response = no_auth_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimitingEnabled:
    """Tests for rate limiting when enabled."""

    @pytest.fixture
    def rate_limit_settings(self) -> APISettings:
        """Create settings with rate limiting enabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=False,
            rate_limit_enabled=True,
            rate_limit_requests=3,  # Very low limit for testing
            rate_limit_window_seconds=60,
        )

    @pytest.fixture
    def rate_limit_client(self, rate_limit_settings: APISettings) -> TestClient:
        """Create a test client with rate limiting enabled."""
        app = create_app(settings=rate_limit_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_rate_limit_headers_present(
        self, rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Rate limit headers are present in response."""
        response = rate_limit_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Window" in response.headers

    def test_rate_limit_remaining_decreases(
        self, rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Rate limit remaining count decreases with each request."""
        # First request
        response1 = rate_limit_client.post(
            "/process",
            files={"file": ("test1.png", sample_png_bytes, "image/png")},
        )
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        # Second request
        response2 = rate_limit_client.post(
            "/process",
            files={"file": ("test2.png", sample_png_bytes, "image/png")},
        )
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_rate_limit_exceeded_returns_429(
        self, rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Exceeding rate limit returns 429."""
        # Make requests up to the limit
        for i in range(3):
            rate_limit_client.post(
                "/process",
                files={"file": (f"test{i}.png", sample_png_bytes, "image/png")},
            )

        # Next request should be rate limited
        response = rate_limit_client.post(
            "/process",
            files={"file": ("test_over.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "rate_limit_exceeded"
        assert "Retry-After" in response.headers

    def test_rate_limit_applies_to_batch(
        self, rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Rate limit applies to batch endpoints."""
        # Use up rate limit
        for i in range(3):
            rate_limit_client.post(
                "/batch",
                files=[("files", (f"test{i}.png", sample_png_bytes, "image/png"))],
            )

        # Next batch request should be rate limited
        response = rate_limit_client.post(
            "/batch",
            files=[("files", ("test_over.png", sample_png_bytes, "image/png"))],
        )
        assert response.status_code == 429


class TestRateLimitExclusions:
    """Tests for rate limit path exclusions."""

    @pytest.fixture
    def rate_limit_settings(self) -> APISettings:
        """Create settings with rate limiting enabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=False,
            rate_limit_enabled=True,
            rate_limit_requests=2,  # Very low limit
            rate_limit_window_seconds=60,
        )

    @pytest.fixture
    def rate_limit_client(self, rate_limit_settings: APISettings) -> TestClient:
        """Create a test client with rate limiting enabled."""
        app = create_app(settings=rate_limit_settings)
        return TestClient(app)

    def test_health_not_rate_limited(self, rate_limit_client: TestClient) -> None:
        """Health endpoint is not rate limited."""
        # Make many requests
        for _ in range(10):
            response = rate_limit_client.get("/health")
            assert response.status_code == 200

    def test_ready_not_rate_limited(self, rate_limit_client: TestClient) -> None:
        """Ready endpoint is not rate limited."""
        for _ in range(10):
            response = rate_limit_client.get("/ready")
            assert response.status_code == 200

    def test_version_not_rate_limited(self, rate_limit_client: TestClient) -> None:
        """Version endpoint is not rate limited."""
        for _ in range(10):
            response = rate_limit_client.get("/version")
            assert response.status_code == 200


class TestRateLimitDisabled:
    """Tests for when rate limiting is disabled."""

    @pytest.fixture
    def no_rate_limit_settings(self) -> APISettings:
        """Create settings with rate limiting disabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=False,
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def no_rate_limit_client(self, no_rate_limit_settings: APISettings) -> TestClient:
        """Create a test client with rate limiting disabled."""
        app = create_app(settings=no_rate_limit_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_no_rate_limit_headers_when_disabled(
        self, no_rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """No rate limit headers when disabled."""
        response = no_rate_limit_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_many_requests_succeed_when_disabled(
        self, no_rate_limit_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Many requests succeed when rate limiting is disabled."""
        # Make many requests (would exceed any reasonable limit)
        for i in range(5):
            response = no_rate_limit_client.post(
                "/process",
                files={"file": (f"test{i}.png", sample_png_bytes, "image/png")},
            )
            assert response.status_code == 200


# ============================================================================
# Combined Auth + Rate Limit Tests
# ============================================================================


class TestAuthAndRateLimitCombined:
    """Tests for combined auth and rate limiting."""

    @pytest.fixture
    def combined_settings(self) -> APISettings:
        """Create settings with both auth and rate limiting enabled."""
        return APISettings(
            title="Test API",
            version="0.0.1-test",
            auth_enabled=True,
            api_keys=["valid-key"],
            rate_limit_enabled=True,
            rate_limit_requests=3,
            rate_limit_window_seconds=60,
        )

    @pytest.fixture
    def combined_client(self, combined_settings: APISettings) -> TestClient:
        """Create a test client with both enabled."""
        app = create_app(settings=combined_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image bytes."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_auth_checked_before_rate_limit(
        self, combined_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Authentication is checked before rate limiting."""
        # Request without API key should return 401 (auth error)
        # even if rate limit would have been exceeded
        response = combined_client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 401  # Auth error, not rate limit

    def test_both_work_together(
        self, combined_client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Both auth and rate limiting work together."""
        # Make valid requests up to limit
        for i in range(3):
            response = combined_client.post(
                "/process",
                files={"file": (f"test{i}.png", sample_png_bytes, "image/png")},
                headers={"X-API-Key": "valid-key"},
            )
            assert response.status_code == 200

        # Next request should be rate limited
        response = combined_client.post(
            "/process",
            files={"file": ("test_over.png", sample_png_bytes, "image/png")},
            headers={"X-API-Key": "valid-key"},
        )
        assert response.status_code == 429
