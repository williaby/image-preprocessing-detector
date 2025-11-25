"""Tests for document processing endpoint.

Sprint 5.2.2: POST /process endpoint validation.
"""

import io
from pathlib import Path

import numpy as np
import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings
from image_preprocessing_detector.api.models import ProcessingStatus


@pytest.fixture
def test_settings() -> APISettings:
    """Create test API settings."""
    return APISettings(
        title="Test API",
        version="0.0.1-test",
        cors_enabled=True,
        rate_limit_enabled=False,
        auth_enabled=False,
        max_file_size_mb=10,
    )


@pytest.fixture
def client(test_settings: APISettings) -> TestClient:
    """Create a test client with test settings."""
    app = create_app(settings=test_settings)
    return TestClient(app)


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Create a simple PNG image bytes."""
    # Create a simple 100x100 white image
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Create a simple JPEG image bytes."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestProcessEndpointValidation:
    """Tests for file validation on /process endpoint."""

    def test_unsupported_file_type_rejected(self, client: TestClient) -> None:
        """Unsupported file types are rejected with 400."""
        response = client.post(
            "/process",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"]["error"] == "invalid_file_type"

    def test_empty_file_rejected(self, client: TestClient) -> None:
        """Empty files are rejected with 400."""
        response = client.post(
            "/process",
            files={"file": ("test.png", b"", "image/png")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"]["error"] == "empty_file"

    @pytest.mark.slow
    def test_file_too_large_rejected(self, client: TestClient) -> None:
        """Files exceeding size limit are rejected.

        Note: This test creates a 51MB file which may be slow.
        The default limit is 50MB (from get_api_settings cache).
        """
        # Create a file larger than the default 50MB limit
        large_content = b"x" * (51 * 1024 * 1024)
        response = client.post(
            "/process",
            files={"file": ("test.png", large_content, "image/png")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"]["error"] == "file_too_large"


class TestProcessEndpointSuccess:
    """Tests for successful document processing."""

    def test_png_image_processing(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """PNG image is processed successfully."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["result"]["num_pages"] == 1
        assert data["result"]["file_name"] == "test.png"

    def test_jpeg_image_processing(
        self, client: TestClient, sample_jpeg_bytes: bytes
    ) -> None:
        """JPEG image is processed successfully."""
        response = client.post(
            "/process",
            files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None

    def test_processing_result_has_document_id(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes document ID."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert data["result"]["document_id"] is not None
        assert len(data["result"]["document_id"]) > 0

    def test_processing_result_has_pages(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes page information."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert "pages" in data["result"]
        assert len(data["result"]["pages"]) == 1

        page = data["result"]["pages"][0]
        assert "page_index" in page
        assert "width_px" in page
        assert "height_px" in page

    def test_processing_result_has_iqa_scores(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes IQA scores."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        page = data["result"]["pages"][0]
        assert "iqa_scores" in page

    def test_processing_result_has_dqs(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes DQS summary."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert "dqs" in data["result"]
        if data["result"]["dqs"]:
            assert "degradation_score" in data["result"]["dqs"]

    def test_processing_result_has_routing_recommendation(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes OCR routing recommendation."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert "ocr_routing_recommendation" in data["result"]

    def test_processing_result_has_timing(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes timing information."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert "processing_time_ms" in data["result"]
        assert data["result"]["processing_time_ms"] > 0

    def test_processing_result_has_device_used(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Processing result includes device information."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        data = response.json()
        assert "device_used" in data["result"]
        # Device can be cpu, gpu, cuda, or modal
        assert data["result"]["device_used"] in ["cpu", "gpu", "cuda", "modal"]


class TestProcessEndpointOptions:
    """Tests for processing options."""

    def test_prefer_gpu_option(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """prefer_gpu option is passed to processing."""
        response = client.post(
            "/process?prefer_gpu=false",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_enable_corrections_option(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """enable_corrections option is accepted."""
        response = client.post(
            "/process?enable_corrections=true",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_enable_teacher_option(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """enable_teacher option is accepted."""
        response = client.post(
            "/process?enable_teacher=false",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestProcessEndpointHeaders:
    """Tests for response headers."""

    def test_correlation_id_in_response(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Correlation ID is present in response headers."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert "X-Correlation-ID" in response.headers

    def test_provided_correlation_id_preserved(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Provided correlation ID is preserved."""
        correlation_id = "test-process-123"
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
            headers={"X-Correlation-ID": correlation_id},
        )
        assert response.headers["X-Correlation-ID"] == correlation_id

    def test_response_time_header(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Response time header is present."""
        response = client.post(
            "/process",
            files={"file": ("test.png", sample_png_bytes, "image/png")},
        )
        assert "X-Response-Time-Ms" in response.headers
