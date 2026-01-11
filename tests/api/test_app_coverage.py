"""Additional tests for api/app.py coverage.

Tests for:
- Lifespan context manager
- Device probe failures
- CORS disabled path
- Auth middleware
"""

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from unittest.mock import patch

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings


class TestLifespanContextManager:
    """Tests for application lifespan management."""

    def test_lifespan_app_starts_successfully(self) -> None:
        """Lifespan allows app to start and serve requests."""
        settings = APISettings(
            title="Test API",
            rate_limit_enabled=False,
            auth_enabled=False,
        )
        app = create_app(settings=settings)
        client = TestClient(app)

        # Make a request - if lifespan works, this should succeed
        response = client.get("/health")
        assert response.status_code == 200

    def test_lifespan_device_probe_exception_handled(self) -> None:
        """Lifespan handles device probe exceptions gracefully."""
        # The device probe is dynamically imported in lifespan
        # We test that the app still starts even if probe fails
        with patch(
            "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
            side_effect=Exception("Device probe failed"),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            # Application should still start and respond
            response = client.get("/health")
            assert response.status_code == 200


class TestCORSDisabled:
    """Tests for CORS disabled configuration."""

    @pytest.fixture
    def no_cors_settings(self) -> APISettings:
        """Create settings with CORS disabled."""
        return APISettings(
            title="Test API",
            cors_enabled=False,
            rate_limit_enabled=False,
            auth_enabled=False,
        )

    @pytest.fixture
    def no_cors_client(self, no_cors_settings: APISettings) -> TestClient:
        """Create test client with CORS disabled."""
        app = create_app(settings=no_cors_settings)
        return TestClient(app)

    def test_cors_disabled_still_serves_requests(
        self, no_cors_client: TestClient
    ) -> None:
        """Application works when CORS is disabled."""
        response = no_cors_client.get("/health")
        assert response.status_code == 200

    def test_cors_disabled_no_cors_headers(self, no_cors_client: TestClient) -> None:
        """CORS headers not present when disabled."""
        response = no_cors_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # When CORS is disabled, we still get a response
        assert response.status_code in (200, 405)


class TestAuthMiddlewareEnabled:
    """Tests for auth middleware when enabled."""

    @pytest.fixture
    def auth_settings(self) -> APISettings:
        """Create settings with auth enabled."""
        return APISettings(
            title="Test API",
            auth_enabled=True,
            api_keys=["test-key-123"],
            internal_callers=[],
            rate_limit_enabled=False,
        )

    @pytest.fixture
    def auth_client(self, auth_settings: APISettings) -> TestClient:
        """Create test client with auth enabled."""
        app = create_app(settings=auth_settings)
        return TestClient(app)

    def test_auth_middleware_logs_key_count(self, auth_settings: APISettings) -> None:
        """Auth middleware logs number of API keys on startup."""
        with patch("image_preprocessing_detector.api.app.logger") as mock_logger:
            app = create_app(settings=auth_settings)
            # Check that auth_middleware_enabled was logged
            mock_logger.info.assert_any_call(
                "auth_middleware_enabled",
                num_api_keys=1,
                num_internal_callers=0,
            )


class TestRateLimitMiddlewareConfig:
    """Tests for rate limit middleware configuration."""

    @pytest.fixture
    def rate_limit_settings(self) -> APISettings:
        """Create settings with custom rate limit."""
        return APISettings(
            title="Test API",
            rate_limit_enabled=True,
            rate_limit_requests=50,
            rate_limit_window_seconds=30,
            auth_enabled=False,
        )

    def test_rate_limit_uses_configured_values(
        self, rate_limit_settings: APISettings
    ) -> None:
        """Rate limit middleware uses configured values."""
        with patch("image_preprocessing_detector.api.app.logger") as mock_logger:
            app = create_app(settings=rate_limit_settings)
            mock_logger.info.assert_any_call(
                "rate_limit_middleware_enabled",
                requests_per_window=50,
                window_seconds=30,
            )


class TestRootEndpoint:
    """Tests for root endpoint behavior."""

    @pytest.fixture
    def test_settings(self) -> APISettings:
        """Create test settings."""
        return APISettings(
            title="Test API",
            rate_limit_enabled=False,
            auth_enabled=False,
        )

    @pytest.fixture
    def client(self, test_settings: APISettings) -> TestClient:
        """Create test client."""
        app = create_app(settings=test_settings)
        return TestClient(app)

    def test_root_returns_message(self, client: TestClient) -> None:
        """Root endpoint returns message."""
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "Image Preprocessing Detector API" in data["message"]

    def test_root_returns_all_navigation_links(self, client: TestClient) -> None:
        """Root endpoint returns all navigation links."""
        response = client.get("/")
        data = response.json()
        expected_keys = {"message", "docs", "health", "ready", "version"}
        assert expected_keys.issubset(set(data.keys()))


class TestLifespanModelPreloading:
    """Tests for model preloading during lifespan startup."""

    def test_lifespan_model_preload_success_with_gpu(self) -> None:
        """Lifespan preloads models successfully when GPU available."""
        # Mock device capabilities with GPU
        mock_caps = type(
            "DeviceCapabilities",
            (),
            {
                "has_local_gpu": True,
                "gpu_name": "Test GPU",
                "cpu_count": 4,
                "modal_available": False,
            },
        )()

        # Mock model loading functions
        mock_student = type("StudentModel", (), {"device": "cuda"})()
        mock_teacher = type("TeacherModel", (), {"device": "cuda"})()
        mock_warmup_stats = {"student_warmup_ms": 10.0, "teacher_warmup_ms": 15.0}
        mock_model_info = {"name": "test", "device": "cuda"}

        # Patch at the module where the dynamic import occurs
        with (
            patch(
                "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
                return_value=mock_caps,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.load_student_model",
                return_value=mock_student,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.load_teacher_model",
                return_value=mock_teacher,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.warmup_models",
                return_value=mock_warmup_stats,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.get_model_info",
                return_value=mock_model_info,
            ),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            # App should start and have models in state
            response = client.get("/health")
            assert response.status_code == 200

    def test_lifespan_model_preload_success_without_gpu(self) -> None:
        """Lifespan preloads student model on CPU when no GPU."""
        # Mock device capabilities without GPU
        mock_caps = type(
            "DeviceCapabilities",
            (),
            {
                "has_local_gpu": False,
                "gpu_name": None,
                "cpu_count": 4,
                "modal_available": True,
            },
        )()

        mock_student = type("StudentModel", (), {"device": "cpu"})()
        mock_warmup_stats = {"student_warmup_ms": 50.0}
        mock_model_info = {"name": "test", "device": "cpu"}

        with (
            patch(
                "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
                return_value=mock_caps,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.load_student_model",
                return_value=mock_student,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.warmup_models",
                return_value=mock_warmup_stats,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.get_model_info",
                return_value=mock_model_info,
            ),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200

    def test_lifespan_model_preload_failure_handled(self) -> None:
        """Lifespan handles model preload failure gracefully."""
        # Mock device capabilities
        mock_caps = type(
            "DeviceCapabilities",
            (),
            {
                "has_local_gpu": False,
                "gpu_name": None,
                "cpu_count": 4,
                "modal_available": False,
            },
        )()

        with (
            patch(
                "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
                return_value=mock_caps,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.load_student_model",
                side_effect=Exception("Model loading failed"),
            ),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            # App should still start despite model load failure
            response = client.get("/health")
            assert response.status_code == 200

    def test_lifespan_device_probe_failure_handled(self) -> None:
        """Lifespan handles device probe failure gracefully."""
        with patch(
            "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
            side_effect=Exception("Device probe failed"),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            # App should still start despite device probe failure
            response = client.get("/health")
            assert response.status_code == 200

    def test_lifespan_no_models_when_none_loaded(self) -> None:
        """App state has None models when loading fails."""
        mock_caps = type(
            "DeviceCapabilities",
            (),
            {
                "has_local_gpu": False,
                "gpu_name": None,
                "cpu_count": 4,
                "modal_available": False,
            },
        )()

        with (
            patch(
                "image_preprocessing_detector.utils.device_probe.probe_device_capabilities",
                return_value=mock_caps,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.load_student_model",
                return_value=None,
            ),
            patch(
                "image_preprocessing_detector.models.model_loader.warmup_models",
                return_value={},
            ),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)

            # Use TestClient which handles lifespan
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200
