"""Locust load testing scenarios for Image Preprocessing Detector API.

Run scenarios:
    # Baseline load (100 users, 5 minutes)
    locust -f tests/load/locustfile.py --users 100 --spawn-rate 10 --run-time 5m --host http://localhost:8000

    # Stress test (ramp to failure)
    locust -f tests/load/locustfile.py --users 1000 --spawn-rate 50 --host http://localhost:8000

    # Spike test (quick surge)
    locust -f tests/load/locustfile.py --users 500 --spawn-rate 100 --run-time 2m --host http://localhost:8000

    # Web UI (interactive)
    locust -f tests/load/locustfile.py --host http://localhost:8000
"""

import os
import random
import time
from pathlib import Path

from locust import HttpUser, between, task


class DocumentProcessorUser(HttpUser):
    """Simulates a user interacting with the document processing API."""

    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)

    # API key for authentication (loaded from environment variable)
    api_key = os.environ.get("LOAD_TEST_API_KEY", "test-api-key")

    def on_start(self) -> None:
        """Called when a user starts. Load test fixtures."""
        self.fixtures_dir = Path(__file__).parent / "fixtures"

        # Check for fixtures
        if not self.fixtures_dir.exists():
            print(f"WARNING: Fixtures directory not found: {self.fixtures_dir}")
            print("Creating dummy fixtures...")
            self.fixtures_dir.mkdir(parents=True, exist_ok=True)

        # Load available test files
        self.test_pdfs = list(self.fixtures_dir.glob("*.pdf"))
        self.test_images = list(self.fixtures_dir.glob("*.png")) + list(
            self.fixtures_dir.glob("*.jpg")
        )

        if not self.test_pdfs and not self.test_images:
            print(
                "WARNING: No test fixtures found. Please add PDF/image files to tests/load/fixtures/"
            )

        # Set auth header if API key provided
        if self.api_key:
            self.client.headers.update({"X-API-Key": self.api_key})

    @task(10)
    def process_single_document(self) -> None:
        """Process a single document (most common operation - 10x weight).

        Simulates typical user uploading a document for analysis.
        """
        # Select random test file
        if self.test_pdfs:
            test_file = random.choice(self.test_pdfs)
        elif self.test_images:
            test_file = random.choice(self.test_images)
        else:
            # Skip if no fixtures
            return

        # Process with default options
        with open(test_file, "rb") as f:
            self.client.post(
                "/process",
                files={"file": (test_file.name, f, self._get_mime_type(test_file))},
                name="/process [single doc]",
            )

    @task(5)
    def process_single_document_with_options(self) -> None:
        """Process document with custom options (5x weight).

        Simulates users who adjust processing settings.
        """
        if self.test_pdfs:
            test_file = random.choice(self.test_pdfs)
        elif self.test_images:
            test_file = random.choice(self.test_images)
        else:
            return

        # Random options
        options = {
            "prefer_gpu": random.choice([True, False]),
            "enable_corrections": random.choice([True, False]),
            "enable_teacher": random.choice([True, False]),
        }

        with open(test_file, "rb") as f:
            self.client.post(
                "/process",
                files={"file": (test_file.name, f, self._get_mime_type(test_file))},
                data=options,
                name="/process [with options]",
            )

    @task(2)
    def process_batch_small(self) -> None:
        """Process small batch (2-5 files) with status polling (2x weight).

        Simulates batch processing with async job tracking.
        """
        if not self.test_pdfs and not self.test_images:
            return

        # Select 2-5 random files
        num_files = random.randint(2, min(5, len(self.test_pdfs + self.test_images)))
        available_files = self.test_pdfs + self.test_images
        selected_files = random.sample(available_files, num_files)

        # Submit batch job
        # Open files and ensure they're closed properly
        file_handles = []
        files = []
        try:
            for f in selected_files:
                fh = open(f, "rb")
                file_handles.append(fh)
                files.append(("files", (f.name, fh, self._get_mime_type(f))))

            response = self.client.post(
                "/batch", files=files, name="/batch [2-5 files]"
            )
        finally:
            # Close all file handles
            for fh in file_handles:
                fh.close()

        if response.status_code != 200:
            return

        job_id = response.json().get("job_id")
        if not job_id:
            return

        # Poll for completion (max 30 seconds)
        poll_start = time.time()
        poll_count = 0
        max_polls = 30

        while time.time() - poll_start < 30 and poll_count < max_polls:
            status_response = self.client.get(
                f"/batch/{job_id}/status",
                name="/batch/:id/status [polling]",
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get("status") == "completed":
                    # Get results
                    self.client.get(
                        f"/batch/{job_id}/result",
                        name="/batch/:id/result [get results]",
                    )
                    break

            poll_count += 1
            time.sleep(1)

    @task(1)
    def process_batch_large(self) -> None:
        """Process large batch (10-20 files) without polling (1x weight).

        Simulates bulk document processing.
        """
        if not self.test_pdfs and not self.test_images:
            return

        # Select 10-20 random files (with repetition if not enough unique files)
        num_files = random.randint(10, 20)
        available_files = self.test_pdfs + self.test_images

        if not available_files:
            return

        selected_files = [random.choice(available_files) for _ in range(num_files)]

        # Submit batch job (don't poll - just fire and forget)
        # Open files and ensure they're closed properly
        file_handles = []
        files = []
        try:
            for f in selected_files:
                fh = open(f, "rb")
                file_handles.append(fh)
                files.append(("files", (f.name, fh, self._get_mime_type(f))))

            self.client.post("/batch", files=files, name="/batch [10-20 files]")
        finally:
            # Close all file handles
            for fh in file_handles:
                fh.close()

    @task(15)
    def check_health(self) -> None:
        """Health check monitoring (15x weight - frequent health checks).

        Simulates load balancer health probes and monitoring systems.
        """
        self.client.get("/health", name="/health")

    @task(5)
    def check_ready(self) -> None:
        """Readiness check (5x weight).

        Simulates readiness probes.
        """
        self.client.get("/ready", name="/ready")

    @task(2)
    def check_version(self) -> None:
        """Version info check (2x weight).

        Simulates monitoring/observability systems.
        """
        self.client.get("/version", name="/version")

    @task(1)
    def check_docs(self) -> None:
        """Access API docs (1x weight).

        Simulates developers exploring the API.
        """
        self.client.get("/docs", name="/docs")
        self.client.get("/openapi.json", name="/openapi.json")

    @staticmethod
    def _get_mime_type(file_path: Path) -> str:
        """Get MIME type from file extension."""
        ext = file_path.suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        return mime_types.get(ext, "application/octet-stream")


class SpikeTestUser(DocumentProcessorUser):
    """User for spike testing scenarios.

    Generates sudden traffic surges to test system resilience.
    """

    # More aggressive wait times for spike tests
    wait_time = between(0.1, 0.5)


class SoakTestUser(DocumentProcessorUser):
    """User for soak/endurance testing scenarios.

    Sustained load over extended periods (hours/days).
    """

    # Moderate, steady traffic
    wait_time = between(2, 5)

    @task(20)
    def process_single_document(self) -> None:
        """More frequent single document processing for sustained load."""
        super().process_single_document()
