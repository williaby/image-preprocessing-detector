"""Tests for batch processing endpoints.

Sprint 5.2.3: Batch endpoint validation.
"""

import io
import time

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
        rate_limit_enabled=False,
        auth_enabled=False,
        max_batch_size=10,
    )


@pytest.fixture
def client(test_settings: APISettings) -> TestClient:
    """Create a test client with test settings."""
    app = create_app(settings=test_settings)
    return TestClient(app)


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Create a simple PNG image bytes."""
    from PIL import Image

    img = Image.new("RGB", (50, 50), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestBatchSubmission:
    """Tests for batch job submission."""

    def test_submit_batch_returns_job_id(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Submitting a batch returns a job ID."""
        response = client.post(
            "/batch",
            files=[
                ("files", ("test1.png", sample_png_bytes, "image/png")),
                ("files", ("test2.png", sample_png_bytes, "image/png")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_submit_batch_returns_status(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Submitting a batch returns initial status."""
        response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        data = response.json()
        assert data["status"] in ["pending", "processing"]
        assert data["total_files"] == 1
        assert data["processed_files"] == 0

    def test_empty_batch_rejected(self, client: TestClient) -> None:
        """Empty batch is rejected."""
        response = client.post("/batch", files=[])
        # FastAPI returns 422 for missing required field (files)
        assert response.status_code in (400, 422)

    def test_invalid_file_in_batch_rejected(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Invalid file in batch is rejected."""
        response = client.post(
            "/batch",
            files=[
                ("files", ("test.png", sample_png_bytes, "image/png")),
                ("files", ("test.txt", b"hello", "text/plain")),
            ],
        )
        assert response.status_code == 400


class TestBatchStatus:
    """Tests for batch job status endpoint."""

    def test_get_status_returns_progress(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Status endpoint returns progress information."""
        # Submit batch
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        # Get status
        response = client.get(f"/batch/{job_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "total_files" in data
        assert "processed_files" in data

    def test_get_status_unknown_job_returns_404(self, client: TestClient) -> None:
        """Unknown job ID returns 404."""
        response = client.get("/batch/unknown-job-id/status")
        assert response.status_code == 404


class TestBatchResult:
    """Tests for batch job result endpoint."""

    def test_get_result_completed_job(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Result endpoint returns results for completed job."""
        # Submit batch
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        # Wait for completion (poll status)
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            status_response = client.get(f"/batch/{job_id}/status")
            if status_response.json()["status"] == "completed":
                break
            time.sleep(0.1)

        # Get result
        response = client.get(f"/batch/{job_id}/result")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "results" in data
        assert "total_processing_time_ms" in data

    def test_get_result_unknown_job_returns_404(self, client: TestClient) -> None:
        """Unknown job ID returns 404."""
        response = client.get("/batch/unknown-job-id/result")
        assert response.status_code == 404


class TestBatchDeletion:
    """Tests for batch job deletion."""

    def test_delete_job(self, client: TestClient, sample_png_bytes: bytes) -> None:
        """Deleting a job removes it."""
        # Submit batch
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        # Delete job
        delete_response = client.delete(f"/batch/{job_id}")
        assert delete_response.status_code == 200

        # Verify deleted
        status_response = client.get(f"/batch/{job_id}/status")
        assert status_response.status_code == 404

    def test_delete_unknown_job_returns_404(self, client: TestClient) -> None:
        """Deleting unknown job returns 404."""
        response = client.delete("/batch/unknown-job-id")
        assert response.status_code == 404


class TestBatchPagination:
    """Tests for batch result pagination."""

    def test_result_pagination_offset(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Result endpoint supports offset parameter."""
        # Submit batch with multiple files
        submit_response = client.post(
            "/batch",
            files=[
                ("files", ("test1.png", sample_png_bytes, "image/png")),
                ("files", ("test2.png", sample_png_bytes, "image/png")),
            ],
        )
        job_id = submit_response.json()["job_id"]

        # Wait for completion
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            status_response = client.get(f"/batch/{job_id}/status")
            if status_response.json()["status"] == "completed":
                break
            time.sleep(0.1)

        # Get result with offset
        response = client.get(f"/batch/{job_id}/result?offset=1")
        assert response.status_code == 200
        data = response.json()
        # Should have fewer results due to offset
        assert len(data["results"]) <= 1

    def test_result_pagination_limit(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Result endpoint supports limit parameter."""
        # Submit batch with multiple files
        submit_response = client.post(
            "/batch",
            files=[
                ("files", ("test1.png", sample_png_bytes, "image/png")),
                ("files", ("test2.png", sample_png_bytes, "image/png")),
                ("files", ("test3.png", sample_png_bytes, "image/png")),
            ],
        )
        job_id = submit_response.json()["job_id"]

        # Wait for completion
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            status_response = client.get(f"/batch/{job_id}/status")
            if status_response.json()["status"] == "completed":
                break
            time.sleep(0.1)

        # Get result with limit
        response = client.get(f"/batch/{job_id}/result?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 1
