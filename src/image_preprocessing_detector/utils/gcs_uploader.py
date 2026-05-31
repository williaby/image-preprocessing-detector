# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

"""GCS artifact uploader for model training runs.

Implements the canonical storage pattern for ML artifacts:
- GCS is the complete, immutable archive
- Structured directory hierarchy with run metadata
- Support for Modal training integration

Usage:
    from image_preprocessing_detector.utils.gcs_uploader import (
        GCSRunConfig,
        upload_run_to_gcs,
    )

    config = GCSRunConfig(
        bucket_name="rag-pipeline-models",
        project_name="image-preprocessing-detector",
        model_name="resnet50_teacher",
    )
    upload_run_to_gcs(
        config=config,
        run_id="2025-11-15T01-20Z_run-abc123",
        local_dir="/root/output",
    )
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from google.cloud import storage  # pyright: ignore[reportAttributeAccessIssue]


@dataclass(frozen=True)
class GCSRunConfig:
    """Configuration for GCS training run storage location.

    Groups the bucket and path components for canonical GCS structure:
        gs://{bucket_name}/{project_name}/{model_name}/runs/{run_id}/

    Attributes:
        bucket_name (str): GCS bucket name (e.g., "rag-pipeline-models")
        project_name (str): Project name (e.g., "image-preprocessing-detector")
        model_name (str): Model name (e.g., "resnet50_teacher")
    """

    bucket_name: str
    project_name: str
    model_name: str

    def get_runs_prefix(self) -> str:
        """Get the GCS prefix for the runs directory."""
        return f"{self.project_name}/{self.model_name}/runs"

    def get_run_prefix(self, run_id: str) -> str:
        """Get the GCS prefix for a specific run."""
        return f"{self.get_runs_prefix()}/{run_id}"

    def get_run_gcs_path(self, run_id: str) -> str:
        """Get the full gs:// path for a specific run."""
        return f"gs://{self.bucket_name}/{self.get_run_prefix(run_id)}"


logger = logging.getLogger(__name__)


def upload_dir_to_gcs(
    local_dir: str,
    bucket_name: str,
    gcs_prefix: str,
    verbose: bool = True,
) -> dict[str, int]:
    """Upload a directory to GCS, preserving structure.

    Args:
        local_dir (str): Local directory to upload
        bucket_name (str): GCS bucket name
        gcs_prefix (str): Prefix path in GCS (e.g., "project/model/runs/run-id")
        verbose (bool): Print upload progress

    Returns:
        dict[str, int]: Dictionary with upload statistics:
            - files_uploaded: Number of files uploaded
            - total_bytes: Total bytes uploaded

    Raises:
        ValueError: If local_dir doesn't exist
    """
    local_path_obj = Path(local_dir)
    if not local_path_obj.exists():
        raise ValueError(f"Local directory does not exist: {local_dir}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    stats = {"files_uploaded": 0, "total_bytes": 0}

    for file_path in local_path_obj.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = file_path.relative_to(local_path_obj)
        gcs_path = f"{gcs_prefix}/{rel_path}"

        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(file_path))

        file_size = file_path.stat().st_size
        stats["files_uploaded"] += 1
        stats["total_bytes"] += file_size

        if verbose:
            size_mb = file_size / (1024 * 1024)
            logger.info(
                f"✅ Uploaded {rel_path!s:<40} ({size_mb:>6.2f} MB) → {gcs_path}"
            )

    if verbose:
        total_mb = stats["total_bytes"] / (1024 * 1024)
        logger.info(
            f"\n📦 Upload complete: {stats['files_uploaded']} files, {total_mb:.2f} MB"
        )

    return stats


def upload_run_to_gcs(
    config: GCSRunConfig,
    run_id: str,
    local_dir: str,
    verbose: bool = True,
) -> str:
    """Upload a complete training run to GCS with canonical structure.

    Implements the directory structure:
        gs://{bucket}/{project}/{model}/runs/{run_id}/

    Args:
        config (GCSRunConfig): GCS location configuration (bucket, project, model)
        run_id (str): Run identifier (e.g., "2025-11-15T01-20Z_run-abc123")
        local_dir (str): Local directory containing run artifacts
        verbose (bool): Print upload progress

    Returns:
        str: GCS path to the uploaded run (gs://...)

    Example:
        >>> config = GCSRunConfig(
        ...     bucket_name="rag-pipeline-models",
        ...     project_name="image-preprocessing-detector",
        ...     model_name="resnet50_teacher",
        ... )
        >>> gcs_path = upload_run_to_gcs(
        ...     config=config,
        ...     run_id="2025-11-15T01-20Z_run-abc123",
        ...     local_dir="/root/output",
        ... )
        >>> print(gcs_path)
        gs://rag-pipeline-models/image-preprocessing-detector/resnet50_teacher/runs/2025-11-15T01-20Z_run-abc123
    """
    gcs_prefix = config.get_run_prefix(run_id)

    if verbose:
        logger.info("=" * 80)
        logger.info("📤 Uploading Training Run to GCS")
        logger.info("=" * 80)
        logger.info(f"Local directory:  {local_dir}")
        logger.info(f"GCS bucket:       gs://{config.bucket_name}")
        logger.info(f"GCS prefix:       {gcs_prefix}")
        logger.info("")

    # Upload directory
    stats = upload_dir_to_gcs(
        local_dir=local_dir,
        bucket_name=config.bucket_name,
        gcs_prefix=gcs_prefix,
        verbose=verbose,
    )

    gcs_path = config.get_run_gcs_path(run_id)

    if verbose:
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ Upload Complete!")
        logger.info("=" * 80)
        logger.info(f"GCS path: {gcs_path}")
        logger.info(f"Files:    {stats['files_uploaded']}")
        logger.info(f"Size:     {stats['total_bytes'] / (1024 * 1024):.2f} MB")
        logger.info("")
        logger.info("📋 To list artifacts:")
        logger.info(f"   gsutil ls -lh {gcs_path}/")
        logger.info("")
        logger.info("📥 To download:")
        logger.info(f"   gsutil -m cp -r {gcs_path} ./local_copy/")
        logger.info("=" * 80)

    return gcs_path


def upload_file_to_gcs(
    local_file: str,
    bucket_name: str,
    gcs_path: str,
    verbose: bool = True,
) -> str:
    """Upload a single file to GCS.

    Args:
        local_file (str): Path to local file
        bucket_name (str): GCS bucket name
        gcs_path (str): Destination path in GCS (without gs:// prefix)
        verbose (bool): Print upload progress

    Returns:
        str: Full GCS path (gs://...)

    Raises:
        ValueError: If local_file doesn't exist
    """
    local_file_path = Path(local_file)
    if not local_file_path.exists():
        raise ValueError(f"Local file does not exist: {local_file}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)

    blob.upload_from_filename(str(local_file_path))

    full_path = f"gs://{bucket_name}/{gcs_path}"

    if verbose:
        size_mb = local_file_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Uploaded {local_file} ({size_mb:.2f} MB) → {full_path}")

    return full_path


def list_runs(
    config: GCSRunConfig,
    max_results: int | None = None,
) -> list[str]:
    """List all training runs for a model in GCS.

    Args:
        config (GCSRunConfig): GCS location configuration (bucket, project, model)
        max_results (int | None): Maximum number of runs to return (None = all)

    Returns:
        list[str]: List of run IDs (sorted newest first)

    Example:
        >>> config = GCSRunConfig(
        ...     bucket_name="rag-pipeline-models",
        ...     project_name="image-preprocessing-detector",
        ...     model_name="resnet50_teacher",
        ... )
        >>> runs = list_runs(config)
        >>> print(runs[0])
        2025-11-15T01-20Z_run-abc123
    """
    client = storage.Client()
    bucket = client.bucket(config.bucket_name)

    prefix = f"{config.get_runs_prefix()}/"
    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

    # Extract run IDs from prefixes
    run_ids = []
    for prefix_path in blobs.prefixes:
        # Extract run ID from path like "project/model/runs/2025-11-15T01-20Z_run-abc123/"
        run_id = prefix_path.rstrip("/").split("/")[-1]
        run_ids.append(run_id)

    # Sort by timestamp (newest first)
    run_ids.sort(reverse=True)

    if max_results:
        run_ids = run_ids[:max_results]

    return run_ids


def download_run_from_gcs(
    config: GCSRunConfig,
    run_id: str,
    local_dir: str,
    verbose: bool = True,
) -> str:
    """Download a training run from GCS.

    Args:
        config (GCSRunConfig): GCS location configuration (bucket, project, model)
        run_id (str): Run identifier
        local_dir (str): Local directory to download to
        verbose (bool): Print download progress

    Returns:
        str: Local path to downloaded run

    Example:
        >>> config = GCSRunConfig(
        ...     bucket_name="rag-pipeline-models",
        ...     project_name="image-preprocessing-detector",
        ...     model_name="resnet50_teacher",
        ... )
        >>> local_path = download_run_from_gcs(
        ...     config=config,
        ...     run_id="2025-11-15T01-20Z_run-abc123",
        ...     local_dir="./downloads",
        ... )
    """
    client = storage.Client()
    bucket = client.bucket(config.bucket_name)

    gcs_prefix = f"{config.get_run_prefix(run_id)}/"
    local_path = Path(local_dir) / run_id

    if verbose:
        logger.info(f"📥 Downloading run from gs://{config.bucket_name}/{gcs_prefix}")
        logger.info(f"   Local path: {local_path}")

    # Create local directory
    local_path.mkdir(parents=True, exist_ok=True)

    # Download all blobs with prefix
    blobs = bucket.list_blobs(prefix=gcs_prefix)
    files_downloaded = 0

    for blob in blobs:
        # Extract relative path
        rel_path = blob.name.replace(gcs_prefix, "")
        if not rel_path:  # Skip directory markers
            continue

        local_file = local_path / rel_path
        local_file.parent.mkdir(parents=True, exist_ok=True)

        blob.download_to_filename(str(local_file))
        files_downloaded += 1

        if verbose:
            size_mb = blob.size / (1024 * 1024)
            logger.info(f"✅ Downloaded {rel_path:<40} ({size_mb:>6.2f} MB)")

    if verbose:
        logger.info(f"\n✅ Download complete: {files_downloaded} files → {local_path}")

    return str(local_path)
