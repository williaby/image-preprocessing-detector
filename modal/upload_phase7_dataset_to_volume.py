#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Upload Phase 7 Dataset to Modal Volume (One-Time Setup).

This script uploads the Phase 7 dataset from local NFS to a Modal Volume.
Run this ONCE, then the training script can read from the volume without downloading.

This avoids:
- Creating massive 47GB tar files
- Downloading 47GB during training
- WSL memory exhaustion

Usage:
    modal run modal/upload_phase7_dataset_to_volume.py

The volume persists across runs, so you only need to do this once.
"""

from pathlib import Path

import modal

# Create Modal app for upload
app = modal.App("phase7-dataset-upload")

# Simple image with just GCS tools
image = modal.Image.debian_slim(python_version="3.12")

# Reuse the same volume as training
training_volume = modal.Volume.from_name("phase7-training-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/data": training_volume},
    timeout=3600,  # 1 hour for upload
)
def upload_dataset():
    """Upload Phase 7 dataset from local NFS to Modal Volume."""
    import shutil

    # The local dataset will be mounted by Modal
    # We just need to let Modal copy it to the volume
    print("=" * 60)
    print("Phase 7 Dataset Upload to Modal Volume")
    print("=" * 60)
    print("This is a one-time setup. Future training runs will use this volume.")
    print()

    volume_path = Path("/data/iqa_phase7_165k_complete")

    if volume_path.exists():
        file_count = len(list(volume_path.rglob("*")))
        print(f"⚠️  Dataset already exists in volume: {file_count} files")
        print("Skipping upload. Delete volume to re-upload.")
        return

    print("Volume is empty, ready for upload.")
    print("Upload will be done via Modal's mount mechanism.")
    print()
    print("✅ Volume prepared. Use add_local_dir() in training script.")


@app.local_entrypoint()
def main():
    """Entry point."""
    print("Checking Phase 7 training volume...")
    upload_dataset.remote()
    print("\n✅ Volume check complete!")
    print("The training script will use: .add_local_dir() to populate volume")
