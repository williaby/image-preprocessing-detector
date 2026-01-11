# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""GCS utilities for Modal applications.

Provides credential setup and dataset download functionality
shared across benchmark and training scripts.
"""

from __future__ import annotations

import base64
import os
import tarfile
import tempfile
import time
from pathlib import Path

from modal.shared.constants import GCS_ARCHIVE, GCS_BUCKET


def setup_gcs_credentials() -> None:
    """Setup GCS credentials from Modal secret.

    Decodes base64-encoded service account key from GCP_SA_KEY
    environment variable and writes to a temporary file for
    Google Cloud Storage client authentication.
    """
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        print("Warning: GCP_SA_KEY not found, trying default credentials")
        return

    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
    ) as f:
        f.write(gcp_sa_key_json)
        f.flush()
        credentials_path = f.name

    os.chmod(credentials_path, 0o600)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"GCS credentials configured at {credentials_path}")


def download_dataset_from_gcs(
    cache_dir: str,
    bucket: str = GCS_BUCKET,
    archive: str = GCS_ARCHIVE,
) -> Path:
    """Download and extract dataset from GCS.

    Args:
        cache_dir: Local directory for caching the dataset.
        bucket: GCS bucket name (default: DIQA-5000 bucket).
        archive: Archive filename in the bucket.

    Returns:
        Path to the extracted dataset directory.
    """
    from google.cloud import storage

    cache_path = Path(cache_dir)
    test_dir = cache_path / "test"
    csv_path = test_dir / "test.csv"

    if csv_path.exists():
        print(f"Dataset already cached at {cache_path}")
        return cache_path

    setup_gcs_credentials()

    print(f"Downloading dataset from gs://{bucket}/{archive}...")
    start = time.time()

    cache_path.mkdir(parents=True, exist_ok=True)
    archive_path = cache_path / archive

    client = storage.Client()
    gcs_bucket = client.bucket(bucket)
    blob = gcs_bucket.blob(archive)
    blob.download_to_filename(str(archive_path))

    download_time = time.time() - start
    print(f"Downloaded in {download_time:.1f}s")

    print("Extracting dataset...")
    start = time.time()
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(cache_path, filter="data")
    extract_time = time.time() - start
    print(f"Extracted in {extract_time:.1f}s")

    archive_path.unlink()
    return cache_path


def upload_to_gcs(
    local_path: Path,
    remote_path: str,
    bucket: str = GCS_BUCKET,
) -> str:
    """Upload a file to GCS.

    Args:
        local_path: Local file path to upload.
        remote_path: Destination path in the bucket.
        bucket: GCS bucket name.

    Returns:
        GCS URI of the uploaded file.
    """
    from google.cloud import storage

    setup_gcs_credentials()

    client = storage.Client()
    gcs_bucket = client.bucket(bucket)
    blob = gcs_bucket.blob(remote_path)

    print(f"Uploading {local_path} to gs://{bucket}/{remote_path}...")
    start = time.time()
    blob.upload_from_filename(str(local_path))
    upload_time = time.time() - start
    print(f"Uploaded in {upload_time:.1f}s")

    return f"gs://{bucket}/{remote_path}"
