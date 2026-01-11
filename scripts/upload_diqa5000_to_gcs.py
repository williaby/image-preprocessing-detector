#!/usr/bin/env python3
"""Upload DIQA-5000 test set to GCS for Modal access.

This script creates a tarball of the test set and uploads it to GCS.
"""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

# Dataset paths
DIQA_ROOT = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
TEST_DIR = DIQA_ROOT / "test"
ARCHIVE_NAME = "diqa5000-test.tar.gz"
ARCHIVE_PATH = Path("/tmp") / ARCHIVE_NAME  # nosec B108 - temp archive location, cleaned up after upload

# GCS bucket
GCS_BUCKET = "gs://assured-oss-457903-diqa5000"
GCS_PATH = f"{GCS_BUCKET}/{ARCHIVE_NAME}"


def create_archive() -> Path:
    """Create a tarball of the test set.

    Returns:
        Path to the created archive.
    """
    print(f"Creating archive: {ARCHIVE_PATH}")
    print(f"Source directory: {TEST_DIR}")

    with tarfile.open(ARCHIVE_PATH, "w:gz") as tar:
        # Add the test directory with relative paths
        tar.add(TEST_DIR, arcname="test")

    size_mb = ARCHIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"Archive created: {size_mb:.1f} MB")

    return ARCHIVE_PATH


def upload_to_gcs(archive_path: Path) -> str:
    """Upload archive to GCS.

    Args:
        archive_path: Path to the archive file.

    Returns:
        GCS URI of the uploaded file.
    """
    print(f"\nUploading to: {GCS_PATH}")

    result = subprocess.run(
        ["gsutil", "-m", "cp", str(archive_path), GCS_PATH],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"gsutil cp failed: {result.stderr}")

    print(f"Upload complete: {GCS_PATH}")
    return GCS_PATH


def verify_upload() -> bool:
    """Verify the upload was successful.

    Returns:
        True if the file exists in GCS.
    """
    print("\nVerifying upload...")

    result = subprocess.run(
        ["gsutil", "ls", "-l", GCS_PATH],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Verified: {result.stdout.strip()}")
        return True
    else:
        print(f"Verification failed: {result.stderr}")
        return False


def main() -> int:
    """Upload DIQA-5000 test set to GCS."""
    print("=" * 60)
    print("DIQA-5000 Test Set Upload to GCS")
    print("=" * 60)

    # Check source exists
    if not TEST_DIR.exists():
        print(f"Error: Test directory not found: {TEST_DIR}")
        return 1

    # Create archive
    archive_path = create_archive()

    # Upload to GCS
    try:
        upload_to_gcs(archive_path)
    except RuntimeError as e:
        print(f"Upload failed: {e}")
        return 1

    # Verify
    if not verify_upload():
        return 1

    # Cleanup local archive
    print(f"\nCleaning up: {archive_path}")
    archive_path.unlink()

    print("\n" + "=" * 60)
    print("Upload complete!")
    print(f"GCS URI: {GCS_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
