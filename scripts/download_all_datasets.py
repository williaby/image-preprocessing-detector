#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Comprehensive dataset download and organization script.

Downloads and organizes ALL training and benchmark datasets according to
the data README structure:
- data/benchmarks/ - Evaluation datasets
- data/training/ - Source datasets for augmented training generation
- data/test_fixtures/ - Small test datasets (committed to git)

Usage:
    python scripts/download_all_datasets.py --all
    python scripts/download_all_datasets.py --benchmarks-only
    python scripts/download_all_datasets.py --training-only
"""

import argparse
import os
import shutil
import subprocess  # nosec B404 - subprocess used only with gsutil/wget for dataset operations
import sys
from pathlib import Path
from collections.abc import Callable

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
NFS_ROOT = Path("/mnt/unraid/training_data/image_detection")
GCS_BUCKET = "gs://image_detection_b/image-preprocessing-detector"
GCS_CREDENTIALS = PROJECT_ROOT / ".gcp/service-account.json"

# Get HF token from environment
HF_TOKEN = os.getenv("HF_TOKEN", "")
if not HF_TOKEN:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                if line.startswith("HF_TOKEN="):
                    HF_TOKEN = line.strip().split("=", 1)[1]
                    break


# Dataset definitions
BENCHMARK_DATASETS = {
    # Required for 100K training generation
    "tablebank": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/tablebank/",
        "nfs_path": NFS_ROOT / "benchmarks/tablebank",
        "size_gb": 27,
        "description": "TableBank dataset (424K images)",
    },
    "pubtabnet": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/pubtabnet/",
        "nfs_path": NFS_ROOT / "benchmarks/pubtabnet",
        "size_gb": 16,
        "description": "PubTabNet dataset (500K images)",
    },
    "diqa-5000": {
        "source": "local",  # Already extracted
        "nfs_path": NFS_ROOT / "benchmarks/diqa-5000",
        "size_gb": 5.4,
        "description": "DIQA-5000 dataset (5.5K images with quality annotations)",
    },
    "funsd_plus": {
        "source": "huggingface",
        "hf_dataset": "konfuzio/funsd_plus",
        "nfs_path": NFS_ROOT / "benchmarks/funsd_plus",
        "size_gb": 0.5,
        "description": "FUNSD+ enhanced form understanding (1,113 samples)",
    },
    # Optional benchmark datasets
    "omnidocbench": {
        "source": "huggingface",
        "hf_dataset": "opendatalab/OmniDocBench",
        "nfs_path": NFS_ROOT / "benchmarks/omnidocbench",
        "size_gb": 1.2,
        "description": "Comprehensive document understanding benchmark",
    },
    "ohr-bench": {
        "source": "huggingface",
        "hf_dataset": "jordyvl/OHR-Bench",
        "nfs_path": NFS_ROOT / "benchmarks/ohr-bench",
        "size_gb": 1.8,
        "description": "OCR Handwriting Recognition benchmark",
    },
    "external_iqa": {
        "source": "manual",  # Needs manual download
        "nfs_path": NFS_ROOT / "benchmarks/external_iqa",
        "size_gb": 2,
        "description": "External IQA datasets (LIVE, CSIQ, FUNSD)",
        "note": "Requires manual download from multiple sources",
    },
    "signatr6k": {
        "source": "huggingface",
        "hf_dataset": "ryota39/signatr6k",
        "nfs_path": NFS_ROOT / "benchmarks/signatr6k",
        "size_gb": 0.142,
        "description": "Signature detection dataset (6K samples)",
    },
    "wili_2018": {
        "source": "huggingface",
        "hf_dataset": "wietsedv/wili_2018",
        "nfs_path": NFS_ROOT / "benchmarks/wili_2018",
        "size_gb": 0.129,
        "description": "Language identification dataset (235K samples)",
    },
    "cocotext": {
        "source": "url",
        "url": "https://github.com/bgshih/cocotext/raw/master/data/cocotext.v2.json",
        "nfs_path": NFS_ROOT / "benchmarks/cocotext",
        "size_gb": 0.053,
        "description": "COCO-Text dataset (63K text instances)",
    },
}

# Training dataset definitions
TRAINING_DATASETS = {
    # Phase 2 IQA training datasets
    "iqa_phase2": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/iqa_phase2/",
        "nfs_path": NFS_ROOT / "training/iqa_phase2",
        "size_gb": 0.5,
        "description": "Original IQA Phase 2 training dataset",
    },
    "iqa_phase2_100k": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/iqa_phase2_100k/",
        "nfs_path": NFS_ROOT / "training/iqa_phase2_100k",
        "size_gb": 10,
        "description": "100K IQA training dataset (15K partial)",
        "note": "Currently 15,350 samples, needs regeneration",
    },
    # Real-world receipts & invoices
    "receipts_hitl": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/receipts_hitl/",
        "nfs_path": NFS_ROOT / "training/receipts_hitl",
        "size_gb": 0.024,
        "description": "HITL annotated receipts dataset",
    },
    "mobile_receipts_voxel51": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/mobile_receipts_voxel51/",
        "nfs_path": NFS_ROOT / "training/mobile_receipts_voxel51",
        "size_gb": 0.379,
        "description": "Mobile-captured receipts from Voxel51",
    },
    "invoices_kaggle": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/invoices_kaggle/",
        "nfs_path": NFS_ROOT / "training/invoices_kaggle",
        "size_gb": 0.278,
        "description": "High-quality invoice dataset from Kaggle",
    },
    # Phase 3 training datasets (handwriting & layout)
    "iam_handwriting": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/iam_handwriting/",
        "nfs_path": NFS_ROOT / "training/iam_handwriting",
        "size_gb": 0.254,
        "description": "IAM Handwriting Database",
    },
    "docsynth300k": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/docsynth300k/",
        "nfs_path": NFS_ROOT / "training/docsynth300k",
        "size_gb": 112,
        "description": "DocSynth-300K synthetic layout training dataset",
    },
    "nist_db2": {
        "source": "gcs",
        "gcs_path": f"{GCS_BUCKET}/datasets/nist_db2/",
        "nfs_path": NFS_ROOT / "training/nist_db2",
        "size_gb": 1.0,  # Estimate
        "description": "NIST Special Database 2 (handwriting)",
    },
}


def download_from_gcs(dataset_name: str, config: dict) -> bool:
    """Download dataset from GCS to NFS."""
    print(f"\n{'=' * 80}")
    print(f"Downloading {dataset_name} from GCS")
    print(f"{'=' * 80}")
    print(f"Source: {config['gcs_path']}")
    print(f"Target: {config['nfs_path']}")
    print(f"Size: ~{config['size_gb']} GB")
    print()

    # Create NFS directory
    config["nfs_path"].mkdir(parents=True, exist_ok=True)

    # Download with gsutil
    env = os.environ.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCS_CREDENTIALS)

    gcs_path = config["gcs_path"]
    nfs_path = str(config["nfs_path"]) + "/"

    cmd = [
        "gsutil",
        "-m",
        "rsync",
        "-r",
        gcs_path,
        nfs_path,
    ]

    print(f"Running: {' '.join(cmd)}")
    try:
        # nosemgrep: dangerous-subprocess-use-tainted-env-args  # noqa: ERA001
        # Security: gcs_path and nfs_path come from hardcoded BENCHMARK_DATASETS/TRAINING_DATASETS
        # dictionaries, not from user input. Dataset names are validated against these whitelists.
        subprocess.run(cmd, env=env, check=True)  # nosec B603
        print(f"\n✅ Successfully downloaded {dataset_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to download {dataset_name}: {e}")
        return False


def download_from_huggingface(dataset_name: str, config: dict) -> bool:
    """Download dataset from HuggingFace."""
    print(f"\n{'=' * 80}")
    print(f"Downloading {dataset_name} from HuggingFace")
    print(f"{'=' * 80}")
    print(f"Dataset: {config['hf_dataset']}")
    print(f"Target: {config['nfs_path']}")
    print(f"Size: ~{config['size_gb']} GB")
    print()

    # Create NFS directory
    config["nfs_path"].mkdir(parents=True, exist_ok=True)

    # Python script to download with HuggingFace datasets
    script = f"""
import os
from datasets import load_dataset

os.environ["HF_TOKEN"] = "{HF_TOKEN}"

print("Loading dataset {config["hf_dataset"]}...")
dataset = load_dataset("{config["hf_dataset"]}")

print("Saving to {config["nfs_path"]}...")
dataset.save_to_disk("{config["nfs_path"]}")

print("✅ Download complete!")
if hasattr(dataset, 'keys'):
    for split in dataset.keys():
        print(f"  {{split}}: {{len(dataset[split])}} samples")
"""

    try:
        # Resolve full path to uv executable for security (B607)
        uv_path = shutil.which("uv")
        if uv_path is None:
            print("❌ 'uv' command not found in PATH")
            return False

        # Security: script content is constructed from hardcoded config values only
        result = subprocess.run(  # nosec B603
            [uv_path, "run", "python", "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        print(f"\n✅ Successfully downloaded {dataset_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to download {dataset_name}: {e}")
        print(e.stderr)
        return False


def download_from_url(dataset_name: str, config: dict) -> bool:
    """Download dataset from direct URL."""
    print(f"\n{'=' * 80}")
    print(f"Downloading {dataset_name} from URL")
    print(f"{'=' * 80}")
    print(f"URL: {config['url']}")
    print(f"Target: {config['nfs_path']}")
    print()

    # Create NFS directory
    config["nfs_path"].mkdir(parents=True, exist_ok=True)

    # Download with wget (sanitize paths for defensive coding)
    output_file = config["nfs_path"] / Path(config["url"]).name
    cmd = [
        "wget",
        "-O",
        str(output_file),
        config["url"],
    ]

    try:
        # nosemgrep: dangerous-subprocess-use-tainted-env-args  # noqa: ERA001
        # Security: url comes from hardcoded BENCHMARK_DATASETS dictionary with explicit URLs,
        # not from user input. Dataset names are validated against this whitelist.
        subprocess.run(cmd, check=True)  # nosec B603
        print(f"\n✅ Successfully downloaded {dataset_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to download {dataset_name}: {e}")
        return False


def _handle_local_source(dataset_name: str, _config: dict) -> bool:
    """Handle local source datasets."""
    print(f"✅ {dataset_name} already present locally")
    return True


def _handle_manual_source(dataset_name: str, config: dict) -> bool:
    """Handle manual download datasets."""
    print(f"⚠️ {dataset_name} requires manual download: {config.get('note', '')}")
    return True


# Dispatch table for download sources
_DOWNLOAD_HANDLERS: dict[str, Callable[[str, dict], bool]] = {
    "local": _handle_local_source,
    "gcs": download_from_gcs,
    "huggingface": download_from_huggingface,
    "url": download_from_url,
    "manual": _handle_manual_source,
}


def download_dataset(dataset_name: str, config: dict) -> bool:
    """Download a single dataset based on its source type."""
    source = config.get("source", "")
    handler = _DOWNLOAD_HANDLERS.get(source)

    if handler is None:
        print(f"❌ Unknown source type: {source}")
        return False

    return handler(dataset_name, config)


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Download and organize all datasets")
    parser.add_argument("--all", action="store_true", help="Download all datasets")
    parser.add_argument(
        "--benchmarks-only",
        action="store_true",
        help="Download only benchmark datasets",
    )
    parser.add_argument(
        "--training-only",
        action="store_true",
        help="Download only training datasets",
    )
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Download only datasets required for 100K training",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Download specific dataset by name",
    )
    return parser


def _determine_datasets_to_download(
    args: argparse.Namespace,
    all_datasets: dict,
    parser: argparse.ArgumentParser,
) -> dict:
    """Determine which datasets to download based on CLI arguments."""
    if args.dataset:
        if args.dataset not in all_datasets:
            print(f"❌ Unknown dataset: {args.dataset}")
            print(f"Available benchmarks: {', '.join(BENCHMARK_DATASETS.keys())}")
            print(f"Available training: {', '.join(TRAINING_DATASETS.keys())}")
            sys.exit(1)
        return {args.dataset: all_datasets[args.dataset]}

    if args.required_only:
        return {
            k: BENCHMARK_DATASETS[k]
            for k in ["tablebank", "pubtabnet", "diqa-5000", "funsd_plus"]
        }
    if args.benchmarks_only:
        return BENCHMARK_DATASETS
    if args.training_only:
        return TRAINING_DATASETS
    if args.all:
        return all_datasets

    parser.print_help()
    sys.exit(1)


def _check_prerequisites() -> None:
    """Check that required prerequisites exist."""
    if not NFS_ROOT.exists():
        print(f"❌ NFS mount not found: {NFS_ROOT}")
        sys.exit(1)

    if not GCS_CREDENTIALS.exists():
        print(f"❌ GCS credentials not found: {GCS_CREDENTIALS}")
        sys.exit(1)


def _print_download_plan(datasets_to_download: dict) -> None:
    """Print the download plan."""
    print(f"\n{'=' * 80}")
    print("Dataset Download Plan")
    print(f"{'=' * 80}")
    print(f"Datasets to download: {len(datasets_to_download)}")
    for name, config in datasets_to_download.items():
        print(f"  - {name}: {config['description']} (~{config['size_gb']} GB)")
    print()


def _print_download_summary(results: dict[str, bool]) -> None:
    """Print download summary with success/failure counts."""
    print(f"\n{'=' * 80}")
    print("Download Summary")
    print(f"{'=' * 80}")
    successful = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print("\nFailed downloads:")
        for name, success in results.items():
            if not success:
                print(f"  - {name}")


def main() -> bool:
    """Main entry point for dataset download script."""
    parser = _create_argument_parser()
    args = parser.parse_args()

    all_datasets = {**BENCHMARK_DATASETS, **TRAINING_DATASETS}
    datasets_to_download = _determine_datasets_to_download(args, all_datasets, parser)

    _check_prerequisites()
    _print_download_plan(datasets_to_download)

    # Download datasets
    results = {
        name: download_dataset(name, config)
        for name, config in datasets_to_download.items()
    }

    _print_download_summary(results)

    return all(results.values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
