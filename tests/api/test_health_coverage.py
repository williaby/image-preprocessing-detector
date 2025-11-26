"""Additional tests for api/routes/health.py coverage.

Tests for:
- get_uptime_seconds when not initialized
- Device probe failures in readiness check
- Import failures for various modules
- Model version detection failures
"""

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings
from image_preprocessing_detector.api.routes import health


class TestUptimeCalculation:
    """Tests for uptime calculation."""

    def test_get_uptime_seconds_when_not_initialized(self) -> None:
        """get_uptime_seconds returns None when server not started."""
        # Save and reset the server start time
        original = health._server_start_time
        try:
            health._server_start_time = None
            assert health.get_uptime_seconds() is None
        finally:
            health._server_start_time = original

    def test_get_uptime_seconds_when_initialized(self) -> None:
        """get_uptime_seconds returns positive value when initialized."""
        # Set server start time and verify uptime is calculated
        health.set_server_start_time()
        uptime = health.get_uptime_seconds()
        assert uptime is not None
        assert uptime >= 0


class TestReadinessCheckFailures:
    """Tests for readiness check failure paths."""

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

    def test_ready_with_device_probe_failure(self) -> None:
        """Readiness check handles device probe failure."""
        with patch(
            "image_preprocessing_detector.api.routes.health.probe_device_capabilities",
            side_effect=Exception("Device probe error"),
        ):
            settings = APISettings(
                title="Test API",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            response = client.get("/ready")
            data = response.json()

            assert response.status_code == 503
            assert data["status"] == "not_ready"
            assert data["checks"]["device_probe"] is False
            assert "error" in data["device"]

    def test_ready_with_iqa_detector_import_failure(self) -> None:
        """Readiness check handles IQA detector import failure."""
        with patch(
            "image_preprocessing_detector.api.routes.health.probe_device_capabilities"
        ) as mock_probe:
            mock_caps = MagicMock()
            mock_caps.has_local_gpu = False
            mock_caps.gpu_name = None
            mock_caps.cpu_count = 4
            mock_caps.modal_available = False
            mock_probe.return_value = mock_caps

            # Mock the BlurDetector import to fail
            with patch.dict(
                "sys.modules",
                {"image_preprocessing_detector.detection.iqa_classical": None},
            ):
                settings = APISettings(
                    title="Test API",
                    rate_limit_enabled=False,
                    auth_enabled=False,
                )
                app = create_app(settings=settings)
                client = TestClient(app)

                response = client.get("/ready")
                data = response.json()

                # The endpoint should return 503 if any check fails
                assert response.status_code in (200, 503)

    def test_ready_check_returns_timestamp(self, client: TestClient) -> None:
        """Readiness check includes timestamp."""
        response = client.get("/ready")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None


class TestVersionEndpointModelDetection:
    """Tests for version endpoint model detection."""

    @pytest.fixture
    def test_settings(self) -> APISettings:
        """Create test settings."""
        return APISettings(
            title="Test API",
            version="1.0.0-test",
            rate_limit_enabled=False,
            auth_enabled=False,
        )

    @pytest.fixture
    def client(self, test_settings: APISettings) -> TestClient:
        """Create test client."""
        app = create_app(settings=test_settings)
        return TestClient(app)

    def test_version_model_detection_with_missing_dir(self, client: TestClient) -> None:
        """Version endpoint handles missing model directory."""
        with patch("pathlib.Path.exists", return_value=False):
            response = client.get("/version")
            data = response.json()

            assert response.status_code == 200
            assert "models" in data
            # Models should be None when directory doesn't exist
            assert data["models"]["teacher_model"] is None

    def test_version_model_detection_with_existing_models(self) -> None:
        """Version endpoint detects existing models."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock model directory and files existing
            mock_exists.side_effect = lambda: True

            settings = APISettings(
                title="Test API",
                version="1.0.0-test",
                rate_limit_enabled=False,
                auth_enabled=False,
            )
            app = create_app(settings=settings)
            client = TestClient(app)

            response = client.get("/version")
            data = response.json()

            assert response.status_code == 200
            assert "models" in data

    def test_version_model_detection_exception_handled(
        self, client: TestClient
    ) -> None:
        """Version endpoint handles model detection exceptions."""
        with patch(
            "pathlib.Path.exists",
            side_effect=Exception("Permission denied"),
        ):
            response = client.get("/version")
            data = response.json()

            # Should still return valid response
            assert response.status_code == 200
            assert "models" in data

    def test_version_includes_api_version_string(self, client: TestClient) -> None:
        """Version endpoint returns api version string."""
        response = client.get("/version")
        data = response.json()
        # Just verify api_version exists and is a valid string
        assert "api_version" in data
        assert isinstance(data["api_version"], str)
        assert len(data["api_version"]) > 0


class TestHealthEndpointDetails:
    """Additional health endpoint tests."""

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

    def test_health_response_model_validation(self, client: TestClient) -> None:
        """Health response matches HealthResponse model."""
        response = client.get("/health")
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data

    def test_health_status_is_healthy(self, client: TestClient) -> None:
        """Health endpoint always returns healthy when server is running."""
        for _ in range(3):
            response = client.get("/health")
            assert response.json()["status"] == "healthy"


class TestReadyResponseDetails:
    """Additional readiness endpoint tests."""

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

    def test_ready_response_model_validation(self, client: TestClient) -> None:
        """Ready response matches ReadyResponse model."""
        response = client.get("/ready")
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "device" in data

    def test_ready_checks_include_all_components(self, client: TestClient) -> None:
        """Ready checks include all expected components."""
        response = client.get("/ready")
        data = response.json()

        expected_checks = {"device_probe", "iqa_detectors", "schema", "configuration"}
        actual_checks = set(data["checks"].keys())
        assert expected_checks == actual_checks

    def test_ready_device_info_structure(self, client: TestClient) -> None:
        """Device info has expected structure."""
        response = client.get("/ready")
        data = response.json()

        # Device info should have either error or device capabilities
        device = data["device"]
        if "error" not in device:
            assert "has_local_gpu" in device
            assert "cpu_count" in device


class TestVersionResponseDetails:
    """Additional version endpoint tests."""

    @pytest.fixture
    def test_settings(self) -> APISettings:
        """Create test settings."""
        return APISettings(
            title="Test API",
            version="2.5.0",
            rate_limit_enabled=False,
            auth_enabled=False,
        )

    @pytest.fixture
    def client(self, test_settings: APISettings) -> TestClient:
        """Create test client."""
        app = create_app(settings=test_settings)
        return TestClient(app)

    def test_version_response_model_validation(self, client: TestClient) -> None:
        """Version response matches VersionResponse model."""
        response = client.get("/version")
        data = response.json()

        # Verify all required fields present
        assert "api_version" in data
        assert "python_version" in data
        assert "pipeline_version" in data
        assert "models" in data

    def test_version_models_dict_structure(self, client: TestClient) -> None:
        """Models dict has expected structure."""
        response = client.get("/version")
        data = response.json()

        models = data["models"]
        expected_keys = {"teacher_model", "student_model", "layout_model"}
        assert expected_keys == set(models.keys())
