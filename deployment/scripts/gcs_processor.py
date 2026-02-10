#!/usr/bin/env python3
"""GCS Dataset Processor for Docling OCR.

Downloads datasets from GCS, processes through Docling, uploads extracted text.

Usage:
    python gcs_processor.py pubtabnet --batch-size 5000
    python gcs_processor.py tablebank --workers 16
    python gcs_processor.py --list  # List available datasets

Architecture:
    GCS (images) -> Local tmpfs/disk -> Docling API -> GCS (extracted text)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from google.cloud import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Dataset registry
DATASETS = {
    # Tier 1: Born-digital (Docling handles well)
    "pubtabnet": "datasets/pubtabnet",
    "tablebank": "datasets/tablebank",
    "fintabnet": "datasets/fintabnet",
    "doclaynet": "datasets/doclaynet",
    "funsd": "datasets/funsd",
    "sroie": "datasets/sroie",
    "mathverse": "datasets/mathverse",
    "multimodal-textbook": "datasets/multimodal_textbook",
    # Tier 1: Forms
    "nist-sd2": "datasets/nist_db2",
    "nist-sd6": "datasets/nist_sd6",
    # Tier 2: Multilingual (test with Docling first)
    "cc-ocr": "datasets/cc_ocr",
    "mlt19": "datasets/mlt19",
    "jssoda": "datasets/jssoda",
    # Large datasets
    "rvl-cdip": "datasets/rvl_cdip",
}

GCS_BUCKET = "image_detection_b"
GCS_PREFIX = "image-preprocessing-detector"


@dataclass
class ProcessingConfig:
    """Configuration for dataset processing."""

    dataset: str
    docling_urls: list[str] = field(default_factory=lambda: ["http://localhost:5001"])
    batch_size: int = 5000
    workers: int = 8
    local_dir: Path = Path("/tmp/docling_processing")  # noqa: S108  # nosec B108
    use_tmpfs: bool = False  # Use /dev/shm for faster I/O
    dry_run: bool = False


@dataclass
class ExtractionResult:
    """Result of text extraction for a single file."""

    source_path: str
    text: str
    confidence: float
    page_count: int
    tables_found: int
    processing_time_ms: float
    success: bool
    error: str | None = None


class GCSDatasetProcessor:
    """Process datasets from GCS through Docling."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)
        self.http_clients: list[httpx.AsyncClient] = []
        self._client_index = 0  # For round-robin load balancing

        # Set up local directories
        if config.use_tmpfs:
            self.input_dir = Path("/dev/shm/docling_input")  # noqa: S108  # nosec B108
            self.output_dir = Path("/dev/shm/docling_output")  # noqa: S108  # nosec B108
        else:
            self.input_dir = config.local_dir / "input"
            self.output_dir = config.local_dir / "output"

    async def __aenter__(self) -> GCSDatasetProcessor:
        # Create a client for each Docling endpoint
        for url in self.config.docling_urls:
            client = httpx.AsyncClient(
                base_url=url,
                timeout=300.0,  # 5 min timeout for large files
            )
            self.http_clients.append(client)
        logger.info(f"Initialized {len(self.http_clients)} Docling clients")
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self

    async def __aexit__(self, *args: object) -> None:
        for client in self.http_clients:
            await client.aclose()

    def _get_next_client(self) -> httpx.AsyncClient:
        """Get next client using round-robin."""
        client = self.http_clients[self._client_index % len(self.http_clients)]
        self._client_index += 1
        return client

    async def health_check(self) -> bool:
        """Check if all Docling APIs are available."""
        healthy = 0
        for i, client in enumerate(self.http_clients):
            try:
                response = await client.get("/health")
                if response.status_code == 200:
                    healthy += 1
                    logger.info(f"Docling endpoint {i + 1} healthy")
            except httpx.RequestError as e:
                logger.warning(f"Docling endpoint {i + 1} unhealthy: {e}")
        return healthy > 0  # At least one endpoint must be healthy

    def list_gcs_files(self) -> list[str]:
        """List all image files in the dataset."""
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"
        logger.info(f"Listing files in gs://{GCS_BUCKET}/{gcs_path}")

        blobs = self.bucket.list_blobs(prefix=gcs_path)
        image_extensions = {".png", ".jpg", ".jpeg", ".pdf", ".tiff", ".tif"}

        files = [
            blob.name
            for blob in blobs
            if Path(blob.name).suffix.lower() in image_extensions
            and "__MACOSX" not in blob.name
            and not Path(blob.name).name.startswith("._")
        ]

        logger.info(f"Found {len(files)} files")
        return files

    def download_batch(self, gcs_paths: list[str], batch_num: int) -> list[Path]:
        """Download a batch of files from GCS."""
        batch_dir = self.input_dir / f"batch_{batch_num}"
        batch_dir.mkdir(exist_ok=True)

        dataset_prefix = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"

        local_paths = []
        for gcs_path in gcs_paths:
            blob = self.bucket.blob(gcs_path)
            # Preserve relative path to avoid filename collisions
            try:
                relative = Path(gcs_path).relative_to(dataset_prefix)
            except ValueError:
                relative = Path(Path(gcs_path).name)
            local_path = batch_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            local_paths.append(local_path)

        logger.info(f"Downloaded {len(local_paths)} files to {batch_dir}")
        return local_paths

    async def process_file(self, file_path: Path) -> ExtractionResult:
        """Process a single file through Docling using round-robin load balancing."""
        import time

        start = time.perf_counter()
        client = self._get_next_client()

        try:
            with open(file_path, "rb") as f:  # noqa: ASYNC230
                response = await client.post(
                    "/v1/convert/file",
                    files={"file": (file_path.name, f)},
                    data={"output_format": "json"},
                )

            if response.status_code != 200:
                return ExtractionResult(
                    source_path=str(file_path),
                    text="",
                    confidence=0.0,
                    page_count=0,
                    tables_found=0,
                    processing_time_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )

            result = response.json()
            doc = result.get("document", {})

            # Docling returns text in text_content or md_content
            text = doc.get("text_content", "") or doc.get("md_content", "")

            # Parse json_content for structured info if available
            json_content = doc.get("json_content", {})
            pages = (
                json_content.get("pages", []) if isinstance(json_content, dict) else []
            )
            tables = (
                json_content.get("tables", []) if isinstance(json_content, dict) else []
            )

            return ExtractionResult(
                source_path=str(file_path),
                text=text,
                confidence=1.0 if result.get("status") == "success" else 0.5,
                page_count=len(pages) if pages else 1,
                tables_found=len(tables),
                processing_time_ms=result.get(
                    "processing_time", (time.perf_counter() - start) * 1000
                ),
                success=True,
            )

        except Exception as e:
            return ExtractionResult(
                source_path=str(file_path),
                text="",
                confidence=0.0,
                page_count=0,
                tables_found=0,
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e),
            )

    async def process_batch(
        self, file_paths: list[Path], batch_num: int
    ) -> list[ExtractionResult]:
        """Process a batch of files concurrently."""
        semaphore = asyncio.Semaphore(self.config.workers)

        async def process_with_semaphore(path: Path) -> ExtractionResult:
            async with semaphore:
                return await self.process_file(path)

        tasks = [process_with_semaphore(p) for p in file_paths]
        results = await asyncio.gather(*tasks)

        # Log progress
        success = sum(1 for r in results if r.success)
        failed = len(results) - success
        logger.info(f"Batch {batch_num}: {success} success, {failed} failed")

        return results

    def upload_results(self, results: list[ExtractionResult], batch_num: int) -> None:
        """Save extraction results locally (upload via gsutil separately)."""
        local_output_dir = self.output_dir / self.config.dataset
        local_output_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_output_dir / f"batch_{batch_num}.jsonl"

        # Convert to JSONL
        jsonl_content = "\n".join(
            json.dumps(
                {
                    "source": r.source_path,
                    "text": r.text,
                    "confidence": r.confidence,
                    "page_count": r.page_count,
                    "tables_found": r.tables_found,
                    "processing_time_ms": r.processing_time_ms,
                    "success": r.success,
                    "error": r.error,
                }
            )
            for r in results
        )

        # Save locally first
        with open(local_path, "w") as f:
            f.write(jsonl_content)

        logger.info(f"Saved results to {local_path}")

        # Try GCS upload, but don't fail if it doesn't work
        try:
            gcs_path = f"{GCS_PREFIX}/extracted_text/{self.config.dataset}/batch_{batch_num}.jsonl"
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_string(jsonl_content, content_type="application/jsonl")
            logger.info(f"Uploaded to gs://{GCS_BUCKET}/{gcs_path}")
        except Exception as e:
            logger.warning(f"GCS upload failed (will use gsutil later): {e}")

    def cleanup_batch(self, batch_num: int) -> None:
        """Clean up local files for a batch."""
        import shutil

        batch_dir = self.input_dir / f"batch_{batch_num}"
        if batch_dir.exists():
            shutil.rmtree(batch_dir)

    async def process_dataset(self) -> None:
        """Process entire dataset in batches."""
        logger.info(f"=== Processing dataset: {self.config.dataset} ===")

        # Health check
        if not await self.health_check():
            raise RuntimeError(
                f"Docling API not available at {', '.join(self.config.docling_urls)}"
            )

        # List files
        all_files = self.list_gcs_files()
        if not all_files:
            logger.error("No files found in dataset")
            return

        # Calculate batches
        num_batches = (
            len(all_files) + self.config.batch_size - 1
        ) // self.config.batch_size
        logger.info(f"Processing {len(all_files)} files in {num_batches} batches")

        if self.config.dry_run:
            logger.info("Dry run - would process these files:")
            for f in all_files[:10]:
                logger.info(f"  {f}")
            if len(all_files) > 10:
                logger.info(f"  ... and {len(all_files) - 10} more")
            return

        # Process batches
        total_success = 0
        total_failed = 0

        for batch_num in range(num_batches):
            start_idx = batch_num * self.config.batch_size
            end_idx = min(start_idx + self.config.batch_size, len(all_files))
            batch_files = all_files[start_idx:end_idx]

            logger.info(
                f"=== Batch {batch_num + 1}/{num_batches} ({len(batch_files)} files) ==="
            )

            # Download
            local_paths = self.download_batch(batch_files, batch_num)

            # Process
            results = await self.process_batch(local_paths, batch_num)

            # Upload
            self.upload_results(results, batch_num)

            # Cleanup
            self.cleanup_batch(batch_num)

            # Stats
            batch_success = sum(1 for r in results if r.success)
            total_success += batch_success
            total_failed += len(results) - batch_success

        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        logger.info(
            f"Results at: gs://{GCS_BUCKET}/{GCS_PREFIX}/extracted_text/{self.config.dataset}/"
        )


async def main() -> None:
    """Parse arguments and process the specified dataset."""
    parser = argparse.ArgumentParser(
        description="Process datasets from GCS through Docling"
    )
    parser.add_argument("dataset", nargs="?", help="Dataset name to process")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--batch-size", type=int, default=5000, help="Files per batch")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent workers")
    parser.add_argument(
        "--docling-urls",
        nargs="+",
        default=["http://localhost:5001"],
        help="Docling API URLs (multiple for load balancing)",
    )
    parser.add_argument(
        "--use-tmpfs", action="store_true", help="Use /dev/shm for faster I/O"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List files without processing"
    )

    args = parser.parse_args()

    if args.list:
        print("Available datasets:")  # noqa: T201
        for name, path in sorted(DATASETS.items()):
            print(f"  {name:20} -> {path}")  # noqa: T201
        return

    if not args.dataset:
        parser.print_help()
        return

    if args.dataset not in DATASETS:
        print(f"Unknown dataset: {args.dataset}")  # noqa: T201
        print(f"Available: {', '.join(sorted(DATASETS.keys()))}")  # noqa: T201
        return

    config = ProcessingConfig(
        dataset=args.dataset,
        docling_urls=args.docling_urls,
        batch_size=args.batch_size,
        workers=args.workers,
        use_tmpfs=args.use_tmpfs,
        dry_run=args.dry_run,
    )

    async with GCSDatasetProcessor(config) as processor:
        await processor.process_dataset()


if __name__ == "__main__":
    asyncio.run(main())
