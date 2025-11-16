# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Download IQA datasets with quality labels for validation."""

import sys
from pathlib import Path

print("=" * 60)
print("IQA DATASET DOWNLOAD - PHASE 1 (VALIDATION)")
print("=" * 60)
print()
print("Downloading 3 datasets with ground-truth quality labels:")
print("  1. LIVE (779 images, ~1 GB)")
print("  2. CSIQ (866 images, ~2 GB)")
print("  3. LIVE Challenge (1,162 images, ~2 GB)")
print()
print("Total: ~5 GB, 2,807 images")
print("=" * 60)
print()

# Import after message so user sees progress
try:
    from iqadataset import load_dataset
except ImportError as e:
    print(f"ERROR: Failed to import iqadataset: {e}")
    print("Please install: poetry run pip install iqadataset")
    sys.exit(1)

# Set download root
root = Path("data/benchmarks/external_iqa/")
root.mkdir(parents=True, exist_ok=True)

try:
    print("\n[1/3] Downloading LIVE dataset (779 images, ~1 GB)...")
    print("      Defects: JPEG compression, Gaussian blur, white noise, fastfading")
    live = load_dataset("LIVE", dataset_root=str(root), download=True)
    print(f"      ✓ LIVE: {len(live)} images downloaded")
except Exception as e:
    print(f"      ✗ LIVE download failed: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\n[2/3] Downloading CSIQ dataset (866 images, ~2 GB)...")
    print("      Defects: JPEG, JPEG2000, blur, contrast degradation, pink noise")
    csiq = load_dataset("CSIQ", dataset_root=str(root), download=True)
    print(f"      ✓ CSIQ: {len(csiq)} images downloaded")
except Exception as e:
    print(f"      ✗ CSIQ download failed: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\n[3/3] Downloading LIVE Challenge dataset (1,162 images, ~2 GB)...")
    print("      Defects: Authentic camera captures (blur, noise, compression)")
    live_challenge = load_dataset(
        "LIVE_Challenge", dataset_root=str(root), download=True
    )
    print(f"      ✓ LIVE Challenge: {len(live_challenge)} images downloaded")
except Exception as e:
    print(f"      ✗ LIVE Challenge download failed: {e}")
    import traceback

    traceback.print_exc()

print()
print("=" * 60)
print("DOWNLOAD COMPLETE")
print("=" * 60)
print(f"Location: {root}")
print("Total downloaded: ~5 GB, 2,807 images with quality labels")
print()
print("Next steps:")
print("  1. Run analyze_iqa_datasets.py to inspect quality scores")
print("  2. Upload to GCS: gsutil -m cp -r data/benchmarks/external_iqa/ gs://...")
print("=" * 60)
