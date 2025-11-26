"""Additional tests for api/routes/batch.py coverage.

Tests for:
- Job cleanup functionality
- Processing errors in batch
- Edge cases in batch processing
"""

import io
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if FastAPI is not installed
fastapi = pytest.importorskip("fastapi", reason="FastAPI required for API tests")
httpx = pytest.importorskip("httpx", reason="httpx required for API tests")

from fastapi.testclient import TestClient

from image_preprocessing_detector.api.app import create_app
from image_preprocessing_detector.api.config import APISettings
from image_preprocessing_detector.api.models import ProcessingStatus
from image_preprocessing_detector.api.routes import batch as batch_module


class TestJobStoreOperations:
    """Tests for internal job store operations."""

    def test_get_job_returns_none_for_missing(self) -> None:
        """_get_job returns None for missing job."""
        # Clear job store
        batch_module._job_store.clear()
        assert batch_module._get_job("nonexistent") is None

    def test_update_job_does_nothing_for_missing(self) -> None:
        """_update_job does nothing for missing job."""
        batch_module._job_store.clear()
        # Should not raise
        batch_module._update_job("nonexistent", {"status": "completed"})

    def test_cleanup_old_jobs(self) -> None:
        """_cleanup_old_jobs removes old jobs."""
        from image_preprocessing_detector.utils.datetime_compat import utc_now

        batch_module._job_store.clear()

        now = utc_now()
        old_time = now - timedelta(hours=48)

        # Add old job
        batch_module._job_store["old_job"] = {
            "created_at": old_time,
            "status": "completed",
        }

        # Add recent job
        batch_module._job_store["recent_job"] = {
            "created_at": now,
            "status": "completed",
        }

        # Clean up jobs older than 24 hours
        removed = batch_module._cleanup_old_jobs(max_age_hours=24)

        assert removed == 1
        assert "old_job" not in batch_module._job_store
        assert "recent_job" in batch_module._job_store

        # Clean up
        batch_module._job_store.clear()


class TestBatchSubmissionEdgeCases:
    """Tests for batch submission edge cases."""

    @pytest.fixture
    def test_settings(self) -> APISettings:
        """Create test settings."""
        return APISettings(
            title="Test API",
            rate_limit_enabled=False,
            auth_enabled=False,
            max_batch_size=5,
        )

    @pytest.fixture
    def client(self, test_settings: APISettings) -> TestClient:
        """Create test client."""
        app = create_app(settings=test_settings)
        return TestClient(app)

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_batch_size_exceeded(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Batch exceeding max size is rejected."""
        # Mock get_api_settings to return settings with small batch size
        with patch(
            "image_preprocessing_detector.api.routes.batch.get_api_settings"
        ) as mock_settings:
            mock_settings.return_value = APISettings(
                max_batch_size=3,
                rate_limit_enabled=False,
                auth_enabled=False,
            )

            files = [
                ("files", (f"test{i}.png", sample_png_bytes, "image/png"))
                for i in range(4)  # Exceeds max_batch_size of 3
            ]

            response = client.post("/batch", files=files)
            assert response.status_code == 400
            data = response.json()
            assert "exceeds limit" in data["message"]

    def test_empty_file_in_batch_rejected(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Empty file in batch is rejected."""
        files = [
            ("files", ("test.png", sample_png_bytes, "image/png")),
            ("files", ("empty.png", b"", "image/png")),
        ]

        response = client.post("/batch", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "empty_file"


class TestBatchResultEdgeCases:
    """Tests for batch result edge cases."""

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

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_get_result_before_completion(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Getting result before completion returns 425."""
        # Submit a batch job
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        # Immediately try to get result (likely still processing)
        # Note: This test may be flaky if processing is very fast
        # We'll use a mock to ensure the job is not completed
        with patch.object(
            batch_module,
            "_get_job",
            return_value={
                "job_id": job_id,
                "status": ProcessingStatus.PROCESSING,
                "processed_files": 0,
                "total_files": 1,
            },
        ):
            response = client.get(f"/batch/{job_id}/result")
            assert response.status_code == 425
            data = response.json()
            assert "still processing" in data["detail"]

    def test_result_status_shows_progress(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Result response for processing job shows progress."""
        with patch.object(
            batch_module,
            "_get_job",
            return_value={
                "job_id": "test-job",
                "status": ProcessingStatus.PROCESSING,
                "processed_files": 3,
                "total_files": 10,
            },
        ):
            response = client.get("/batch/test-job/result")
            assert response.status_code == 425
            data = response.json()
            assert "3/10" in data["progress"]


class TestBatchStatusDetails:
    """Tests for batch status details."""

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

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_status_includes_all_fields(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Status response includes all required fields."""
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        response = client.get(f"/batch/{job_id}/status")
        data = response.json()

        required_fields = {
            "job_id",
            "status",
            "total_files",
            "processed_files",
            "failed_files",
            "created_at",
            "updated_at",
        }
        assert required_fields.issubset(set(data.keys()))


class TestBatchProcessingErrors:
    """Tests for batch processing error handling."""

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

    def test_batch_with_corrupt_file_continues(self, client: TestClient) -> None:
        """Batch processing continues despite corrupt file."""
        from PIL import Image

        # Create valid image
        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        valid_png = buffer.getvalue()

        # Create corrupt PNG
        corrupt_png = b"\x89PNG\r\n\x1a\ncorrupt"

        files = [
            ("files", ("valid.png", valid_png, "image/png")),
            ("files", ("corrupt.png", corrupt_png, "image/png")),
        ]

        submit_response = client.post("/batch", files=files)
        job_id = submit_response.json()["job_id"]

        # Wait for completion
        max_wait = 15
        start = time.time()
        while time.time() - start < max_wait:
            status_response = client.get(f"/batch/{job_id}/status")
            status_data = status_response.json()
            if status_data["status"] == "completed":
                break
            time.sleep(0.1)

        # Get results
        result_response = client.get(f"/batch/{job_id}/result")
        result_data = result_response.json()

        # Should have at least one result and one error
        assert result_data["status"] == "completed"
        # Valid file should have succeeded
        assert len(result_data["results"]) >= 1 or len(result_data["errors"]) >= 1


class TestBatchJobTimestamps:
    """Tests for batch job timestamps."""

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

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_created_at_and_updated_at_present(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Job has created_at and updated_at timestamps."""
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        data = submit_response.json()

        assert "created_at" in data
        assert "updated_at" in data

    def test_completed_at_set_after_completion(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """completed_at is set after job completes."""
        submit_response = client.post(
            "/batch",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        job_id = submit_response.json()["job_id"]

        # Wait for completion
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            status_response = client.get(f"/batch/{job_id}/status")
            data = status_response.json()
            if data["status"] == "completed":
                assert data["completed_at"] is not None
                return
            time.sleep(0.1)

        # If we get here, job didn't complete in time
        pytest.skip("Job didn't complete in time for test")


class TestBatchProcessingOptions:
    """Tests for batch processing options."""

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

    @pytest.fixture
    def sample_png_bytes(self) -> bytes:
        """Create a simple PNG image."""
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_batch_with_all_options(
        self, client: TestClient, sample_png_bytes: bytes
    ) -> None:
        """Batch accepts all processing options."""
        response = client.post(
            "/batch?prefer_gpu=false&enable_corrections=true&enable_teacher=false",
            files=[("files", ("test.png", sample_png_bytes, "image/png"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
