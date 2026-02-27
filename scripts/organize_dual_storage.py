#!/usr/bin/env python3

"""
Organize datasets across Local + NFS + GCS storage tiers.

This script manages the three-tier storage strategy:
1. Local (WSL): Test fixtures, temporary work (<5GB)
2. NFS (Unraid): Large datasets, training data (~200GB)
3. GCS (Cloud): Backup/fallback, remote access

Usage:
    # Download dataset from GCS to NFS
    python scripts/organize_dual_storage.py pull-from-gcs tablebank

    # Create symlink from local to NFS
    python scripts/organize_dual_storage.py create-symlink tablebank

    # Sync NFS dataset to GCS
    python scripts/organize_dual_storage.py sync-to-gcs tablebank

    # Show storage status for all datasets
    python scripts/organize_dual_storage.py status

    # Setup complete dual storage (GCS → NFS → Local symlinks)
    python scripts/organize_dual_storage.py setup-all
"""

import argparse
import os
import subprocess  # nosec B404 - subprocess used only with gsutil for GCS operations
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
NFS_ROOT = Path("/mnt/unraid/training_data/image_detection")
GCS_BUCKET = "gs://image_detection_b/image-preprocessing-detector/datasets"
GCS_CREDENTIALS = PROJECT_ROOT / ".gcp/service-account.json"

# Dataset definitions
DATASETS = {
    "tablebank": {
        "nfs_path": "benchmarks/tablebank",
        "local_path": "data/benchmarks/tablebank",
        "gcs_path": "tablebank",
        "size_gb": 27,
        "description": "TableBank dataset (424K images)",
    },
    "pubtabnet": {
        "nfs_path": "benchmarks/pubtabnet",
        "local_path": "data/benchmarks/pubtabnet",
        "gcs_path": "pubtabnet",
        "size_gb": 16,
        "description": "PubTabNet dataset (500K images)",
    },
    "diqa-5000": {
        "nfs_path": "benchmarks/diqa-5000",
        "local_path": "data/benchmarks/diqa-5000",
        "gcs_path": "diqa-5000",
        "size_gb": 11,
        "description": "DIQA-5000 dataset (5K images)",
    },
    "external_iqa": {
        "nfs_path": "benchmarks/external_iqa",
        "local_path": "data/benchmarks/external_iqa",
        "gcs_path": "external_iqa",
        "size_gb": 2,
        "description": "External IQA datasets (LIVE, CSIQ, FUNSD)",
    },
    "iqa_phase2_100k": {
        "nfs_path": "training/iqa_phase2_100k",
        "local_path": "data/training/iqa_phase2_100k",
        "gcs_path": "iqa_phase2_100k",
        "size_gb": 50,
        "description": "100K IQA training dataset",
    },
    "doclaynet": {
        "nfs_path": "benchmarks/doclaynet",
        "local_path": "data/benchmarks/doclaynet",
        "gcs_path": "doclaynet",
        "size_gb": 42,
        "description": "DocLayNet dataset (PDFs)",
    },
    "fintabnet": {
        "nfs_path": "benchmarks/fintabnet",
        "local_path": "data/benchmarks/fintabnet",
        "gcs_path": "fintabnet",
        "size_gb": 11,
        "description": "FinTabNet dataset",
    },
    "omnidocbench": {
        "nfs_path": "benchmarks/omnidocbench",
        "local_path": "data/benchmarks/omnidocbench",
        "gcs_path": "omnidocbench",
        "size_gb": 6,
        "description": "OmniDocBench dataset",
    },
    "ohr-bench": {
        "nfs_path": "benchmarks/ohr-bench",
        "local_path": "data/benchmarks/ohr-bench",
        "gcs_path": "ohr-bench",
        "size_gb": 18,
        "description": "OHR-Bench document IQA",
    },
}


def check_prerequisites() -> bool:
    """Check if NFS mount and GCS credentials exist."""
    if not NFS_ROOT.exists():
        print(f"❌ NFS mount not found: {NFS_ROOT}")
        print("   Please ensure Unraid NFS is mounted at /mnt/unraid/training_data")
        return False

    if not GCS_CREDENTIALS.exists():
        print(f"❌ GCS credentials not found: {GCS_CREDENTIALS}")
        print("   Run: mkdir -p .gcp && <setup GCS credentials>")
        return False

    print("✅ Prerequisites OK")
    return True


def pull_from_gcs(dataset_name: str) -> bool:
    """Download dataset from GCS to NFS."""
    if dataset_name not in DATASETS:
        print(f"❌ Unknown dataset: {dataset_name}")
        print(f"Available datasets: {', '.join(DATASETS.keys())}")
        return False

    dataset = DATASETS[dataset_name]
    nfs_full_path = NFS_ROOT / dataset["nfs_path"]
    gcs_source = f"{GCS_BUCKET}/{dataset['gcs_path']}/"

    print(f"\n{'=' * 80}")
    print(f"Downloading {dataset_name} from GCS to NFS")
    print(f"{'=' * 80}")
    print(f"Source: {gcs_source}")
    print(f"Target: {nfs_full_path}")
    print(f"Size: ~{dataset['size_gb']} GB")
    print(f"Description: {dataset['description']}")
    print()

    # Create NFS directory
    nfs_full_path.mkdir(parents=True, exist_ok=True)

    # Download with gsutil
    env = os.environ.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCS_CREDENTIALS)

    # Build command as list (shell=False) - no shell escaping needed
    cmd = [
        "gsutil",
        "-m",
        "rsync",
        "-r",
        gcs_source,
        str(nfs_full_path) + "/",
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        # nosemgrep: dangerous-subprocess-use-tainted-env-args
        # Security: gcs_path and nfs_path come from hardcoded DATASETS dictionary,
        # not from user input. Dataset names are validated via argparse choices.
        subprocess.run(cmd, env=env, check=True)  # nosec B603
        print(f"\n✅ Successfully downloaded {dataset_name} to NFS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to download {dataset_name}: {e}")
        return False


def create_symlink(dataset_name: str) -> bool:
    """Create symlink from local to NFS."""
    if dataset_name not in DATASETS:
        print(f"❌ Unknown dataset: {dataset_name}")
        return False

    dataset = DATASETS[dataset_name]
    local_path = PROJECT_ROOT / dataset["local_path"]
    nfs_full_path = NFS_ROOT / dataset["nfs_path"]

    print(f"\n{'=' * 80}")
    print(f"Creating symlink for {dataset_name}")
    print(f"{'=' * 80}")
    print(f"Local: {local_path}")
    print(f"NFS: {nfs_full_path}")
    print()

    # Check if NFS path exists
    if not nfs_full_path.exists():
        print(f"❌ NFS path not found: {nfs_full_path}")
        print(
            f"   Run: python scripts/organize_dual_storage.py pull-from-gcs {dataset_name}"
        )
        return False

    # Remove existing local path if it exists
    if local_path.exists() or local_path.is_symlink():
        if local_path.is_symlink():
            print(f"Removing existing symlink: {local_path}")
            local_path.unlink()
        else:
            print(f"❌ Local path exists and is not a symlink: {local_path}")
            print("   Please move or remove it first")
            return False

    # Create parent directory
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Create symlink
    local_path.symlink_to(nfs_full_path)
    print(f"✅ Created symlink: {local_path} → {nfs_full_path}")
    return True


def sync_to_gcs(dataset_name: str) -> bool:
    """Sync NFS dataset to GCS."""
    if dataset_name not in DATASETS:
        print(f"❌ Unknown dataset: {dataset_name}")
        return False

    dataset = DATASETS[dataset_name]
    nfs_full_path = NFS_ROOT / dataset["nfs_path"]
    gcs_dest = f"{GCS_BUCKET}/{dataset['gcs_path']}/"

    print(f"\n{'=' * 80}")
    print(f"Syncing {dataset_name} from NFS to GCS")
    print(f"{'=' * 80}")
    print(f"Source: {nfs_full_path}")
    print(f"Target: {gcs_dest}")
    print()

    if not nfs_full_path.exists():
        print(f"❌ NFS path not found: {nfs_full_path}")
        return False

    # Upload with gsutil
    env = os.environ.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCS_CREDENTIALS)

    # Build command as list (shell=False) - no shell escaping needed
    cmd = [
        "gsutil",
        "-m",
        "rsync",
        "-r",
        str(nfs_full_path) + "/",
        gcs_dest,
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        # nosemgrep: dangerous-subprocess-use-tainted-env-args
        # Security: gcs_path and nfs_path come from hardcoded DATASETS dictionary,
        # not from user input. Dataset names are validated via argparse choices.
        subprocess.run(cmd, env=env, check=True)  # nosec B603
        print(f"\n✅ Successfully synced {dataset_name} to GCS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to sync {dataset_name}: {e}")
        return False


def show_status():
    """Show storage status for all datasets."""
    print(f"\n{'=' * 80}")
    print("Dataset Storage Status")
    print(f"{'=' * 80}\n")

    print(f"{'Dataset':<20} {'Local':<15} {'NFS':<15} {'GCS':<15} {'Size (GB)':<10}")
    print("-" * 80)

    for name, dataset in DATASETS.items():
        local_path = PROJECT_ROOT / dataset["local_path"]
        nfs_full_path = NFS_ROOT / dataset["nfs_path"]

        # Check local storage status
        if local_path.is_symlink():
            local_status = "✅ Symlink"
        elif local_path.exists():
            local_status = "📁 Dir"
        else:
            local_status = "❌ Missing"
        nfs_status = "✅ Exists" if nfs_full_path.exists() else "❌ Missing"
        gcs_status = "⚠️ Unknown"  # Would require GCS API call

        print(
            f"{name:<20} {local_status:<15} {nfs_status:<15} {gcs_status:<15} {dataset['size_gb']:<10}"
        )

    print()


def setup_all():
    """Setup complete dual storage for all datasets."""
    print(f"\n{'=' * 80}")
    print("Setting up dual storage for all datasets")
    print(f"{'=' * 80}\n")

    if not check_prerequisites():
        return False

    # Create NFS directory structure
    print("\n[1/3] Creating NFS directory structure...")
    (NFS_ROOT / "benchmarks").mkdir(parents=True, exist_ok=True)
    (NFS_ROOT / "training").mkdir(parents=True, exist_ok=True)
    (NFS_ROOT / "validation").mkdir(parents=True, exist_ok=True)
    print("✅ NFS directories created")

    # Download key datasets from GCS to NFS
    print("\n[2/3] Downloading datasets from GCS to NFS...")
    key_datasets = ["tablebank", "pubtabnet", "diqa-5000", "external_iqa"]

    for dataset in key_datasets:
        if not pull_from_gcs(dataset):
            print(f"⚠️ Failed to download {dataset}, continuing...")

    # Create local symlinks
    print("\n[3/3] Creating local symlinks...")
    for dataset in DATASETS.keys():
        nfs_full_path = NFS_ROOT / DATASETS[dataset]["nfs_path"]
        if nfs_full_path.exists():
            create_symlink(dataset)

    print(f"\n{'=' * 80}")
    print("✅ Dual storage setup complete!")
    print(f"{'=' * 80}\n")

    show_status()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Organize datasets across Local + NFS + GCS storage tiers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        choices=[
            "pull-from-gcs",
            "create-symlink",
            "sync-to-gcs",
            "status",
            "setup-all",
        ],
        help="Command to execute",
    )

    parser.add_argument(
        "dataset",
        nargs="?",
        choices=list(DATASETS.keys()),
        help="Dataset name (required for pull-from-gcs, create-symlink, sync-to-gcs)",
    )

    args = parser.parse_args()

    # Check prerequisites for all commands except status
    if args.command != "status" and not check_prerequisites():
        sys.exit(1)

    # Commands that require a dataset argument
    _dataset_commands = {
        "pull-from-gcs": pull_from_gcs,
        "create-symlink": create_symlink,
        "sync-to-gcs": sync_to_gcs,
    }

    if args.command in _dataset_commands:
        if not args.dataset:
            print(f"❌ Dataset name required for {args.command}")
            parser.print_help()
            sys.exit(1)
        success = _dataset_commands[args.command](args.dataset)
    elif args.command == "status":
        show_status()
        success = True
    elif args.command == "setup-all":
        success = setup_all()
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
