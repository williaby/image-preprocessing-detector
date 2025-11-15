# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Test GCS Access from Modal.

Verifies that Modal can access GCS bucket using base64-encoded credentials.

Usage:
    modal run modal/test_gcs.py
"""
# bandit: noqa: B108

import os

import modal

stub = modal.App("test-gcs-access")

# GCS credentials secret (base64-encoded)
gcs_secret = modal.Secret.from_name("gcs-credentials")


@stub.function(
    image=modal.Image.debian_slim().pip_install("google-cloud-storage"),
    secrets=[gcs_secret],
)
def test_gcs():
    """Test GCS bucket access with base64-encoded credentials."""
    import base64

    from google.cloud import storage

    print("=" * 60)
    print("Testing GCS Access from Modal")
    print("=" * 60)

    # Setup GCS credentials from base64-encoded secret
    print("\n[1/3] Setting up GCS credentials...")
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")

    if not gcp_sa_key_b64:
        print("❌ ERROR: GCP_SA_KEY environment variable not found")
        print("Did you create the Modal secret?")
        print("Run: ./scripts/modal_helpers.sh setup-gcs-secret /path/to/key.json")
        return {"error": "GCP_SA_KEY not found"}

    # Decode base64 and write to temp file
    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")
    credentials_path = "/tmp/gcp-sa-key.json"
    with open(credentials_path, "w") as f:
        f.write(gcp_sa_key_json)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print("✅ GCS credentials configured from base64 secret")

    # Test GCS access
    print("\n[2/3] Connecting to GCS bucket...")
    try:
        client = storage.Client()
        bucket = client.bucket("image_detection_b")

        # List first 10 objects
        print("\n[3/3] Listing objects in bucket...")
        blobs = list(bucket.list_blobs(max_results=10))

        print("\n✅ GCS Access Verified!")
        print("   Bucket: gs://image_detection_b")
        print(f"   Found {len(blobs)} objects (showing first 10):")

        for blob in blobs:
            size_mb = blob.size / (1024 * 1024)
            print(f"   - {blob.name:<50} ({size_mb:.2f} MB)")

        print("\n" + "=" * 60)
        print("✅ SUCCESS: Modal can access GCS bucket!")
        print("=" * 60)

        return {
            "success": True,
            "bucket": "image_detection_b",
            "objects_found": len(blobs),
        }

    except Exception as e:
        print("\n❌ ERROR: Failed to access GCS bucket")
        print(f"Error: {e!s}")
        print("\nTroubleshooting:")
        print("1. Check service account has Storage Object Viewer role")
        print("2. Verify bucket name: gs://image_detection_b")
        print("3. Check GCP project: image-detection-478105")

        return {"success": False, "error": str(e)}


@stub.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    print("Testing GCS access from Modal...")
    print()

    result = test_gcs.remote()

    if result.get("success"):
        print("\n✅ Test passed! Ready for training.")
    else:
        print(f"\n❌ Test failed: {result.get('error')}")
        exit(1)


if __name__ == "__main__":
    print("Use: modal run modal/test_gcs.py")
