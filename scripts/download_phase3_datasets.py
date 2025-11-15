#!/usr/bin/env python3
"""
Download Phase 3+ datasets from HuggingFace and GitHub.

This script downloads the following datasets:
1. OHR-Bench (Priority 1): RAG-specific benchmark (~10 GB)
2. DocSynth-300K (Priority 2): Layout detection training (113 GB)
3. PubTables-1M (Priority 3): Table structure extraction (~25 GB)
4. IAM Handwriting (Priority 4): Handwriting detection (~266 MB)

Total download size: ~148 GB
Estimated time: 2-6 hours depending on network speed

Usage:
    python scripts/download_phase3_datasets.py [--dataset DATASET] [--dry-run]

Options:
    --dataset DATASET    Download specific dataset only (ohr-bench, docsynth300k, pubtables1m, iam)
    --dry-run           Show what would be downloaded without actually downloading
"""

import argparse
import logging
import subprocess  # nosec B404 - Safe subprocess usage with list args, no shell=True
import sys
from pathlib import Path
from typing import Any, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Dataset configurations
DATASETS = {
    "ohr-bench": {
        "source": "huggingface",
        "repo_id": "opendatalab/OHR-Bench",
        "local_dir": PROJECT_ROOT / "data/benchmarks/ohr-bench",
        "size_gb": 10,
        "priority": 1,
        "license": "CC-BY-4.0",
        "description": "RAG-specific OCR benchmark (8,500+ PDFs, 7 domains)",
    },
    "docsynth300k": {
        "source": "huggingface",
        "repo_id": "juliozhao/DocSynth300K",
        "local_dir": PROJECT_ROOT / "data/training/layout/docsynth300k",
        "size_gb": 113,
        "priority": 2,
        "license": "Not specified (assume research use)",
        "description": "Synthetic layout detection training (300k samples)",
    },
    "pubtables1m": {
        "source": "huggingface",
        "repo_id": "bsmock/pubtables-1m",
        "local_dir": PROJECT_ROOT / "data/training/tables/pubtables1m",
        "size_gb": 25,
        "priority": 3,
        "license": "CDLA-Permissive-1.0",
        "description": "Table structure extraction (1M real-world tables)",
    },
    "iam": {
        "source": "huggingface",
        "repo_id": "Teklia/IAM-line",
        "local_dir": PROJECT_ROOT / "data/training/specialized/handwriting/iam",
        "size_gb": 0.266,
        "priority": 4,
        "license": "MIT",
        "description": "Handwriting detection (13,353 text line images)",
    },
}


def download_from_huggingface(
    repo_id: str, local_dir: Path, dry_run: bool = False
) -> bool:
    """
    Download dataset from HuggingFace using huggingface_hub library.

    Args:
        repo_id: HuggingFace repository ID (e.g., "opendatalab/OHR-Bench")
        local_dir: Local directory to save dataset
        dry_run: If True, only show what would be downloaded

    Returns:
        True if download successful, False otherwise
    """
    logger.info(f"Downloading {repo_id} to {local_dir}")

    if dry_run:
        logger.info(f"[DRY RUN] Would download {repo_id} to {local_dir}")
        return True

    try:
        from huggingface_hub import snapshot_download

        # Create local directory
        local_dir.mkdir(parents=True, exist_ok=True)

        # Download dataset
        logger.info(f"Starting download from HuggingFace: {repo_id}")
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=str(local_dir),
            resume_download=True,  # Resume if interrupted
            max_workers=4,  # Parallel downloads
        )

        logger.info(f"✅ Successfully downloaded {repo_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download {repo_id}: {e}")
        return False


def download_from_github(repo_url: str, local_dir: Path, dry_run: bool = False) -> bool:
    """
    Download dataset from GitHub using git clone.

    Args:
        repo_url: GitHub repository URL
        local_dir: Local directory to save dataset
        dry_run: If True, only show what would be downloaded

    Returns:
        True if download successful, False otherwise
    """
    logger.info(f"Cloning {repo_url} to {local_dir}")

    if dry_run:
        logger.info(f"[DRY RUN] Would git clone {repo_url} to {local_dir}")
        return True

    try:
        # Create parent directory
        local_dir.parent.mkdir(parents=True, exist_ok=True)

        # Git clone command
        cmd = ["git", "clone", repo_url, str(local_dir)]

        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(  # noqa: S603  # nosec B603 - Safe git clone, known args, no shell
            cmd, capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info(f"✅ Successfully cloned {repo_url}")
            return True
        logger.error(f"❌ Git clone failed: {result.stderr}")
        return False

    except Exception as e:
        logger.error(f"❌ Failed to clone {repo_url}: {e}")
        return False


def download_dataset(dataset_name: str, dry_run: bool = False) -> bool:
    """
    Download a specific dataset by name.

    Args:
        dataset_name: Name of dataset to download
        dry_run: If True, only show what would be downloaded

    Returns:
        True if download successful, False otherwise
    """
    if dataset_name not in DATASETS:
        logger.error(f"Unknown dataset: {dataset_name}")
        logger.info(f"Available datasets: {', '.join(DATASETS.keys())}")
        return False

    config: dict[str, Any] = DATASETS[dataset_name]

    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"Description: {config['description']}")
    logger.info(f"Size: ~{config['size_gb']} GB")
    logger.info(f"License: {config['license']}")
    logger.info(f"Priority: {config['priority']}")
    logger.info(f"Local directory: {config['local_dir']}")
    logger.info("=" * 80)

    # Check if already exists
    local_dir: Path = config["local_dir"]
    if local_dir.exists() and any(local_dir.iterdir()):
        logger.warning(f"Directory {local_dir} already exists and is not empty")
        response = input("Continue anyway? [y/N]: ").strip().lower()
        if response != "y":
            logger.info("Skipping download")
            return False

    # Download based on source
    if config["source"] == "huggingface":
        return download_from_huggingface(
            repo_id=str(config["repo_id"]),
            local_dir=Path(config["local_dir"]),
            dry_run=dry_run,
        )
    if config["source"] == "github":
        return download_from_github(
            repo_url=str(config["repo_url"]),
            local_dir=Path(config["local_dir"]),
            dry_run=dry_run,
        )
    logger.error(f"Unknown source type: {config['source']}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Phase 3+ datasets for Image Preprocessing Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=[*list(DATASETS.keys()), "all"],
        default="all",
        help="Dataset to download (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )

    args = parser.parse_args()

    # Show summary
    if args.dataset == "all":
        total_size = sum(cast(float, d["size_gb"]) for d in DATASETS.values())
        logger.info(f"Downloading ALL datasets (~{total_size:.1f} GB total)")
        logger.info("This may take 2-6 hours depending on network speed")

        if not args.dry_run:
            response = input("\nContinue? [y/N]: ").strip().lower()
            if response != "y":
                logger.info("Download cancelled")
                sys.exit(0)

        # Download in priority order
        datasets_to_download = sorted(
            DATASETS.items(), key=lambda x: cast(int, x[1]["priority"])
        )
    else:
        datasets_to_download = [(args.dataset, DATASETS[args.dataset])]

    # Download datasets
    success_count = 0
    fail_count = 0

    for dataset_name, _ in datasets_to_download:
        if download_dataset(dataset_name, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    logger.info("=" * 80)
    logger.info("Download Summary:")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info("=" * 80)

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
