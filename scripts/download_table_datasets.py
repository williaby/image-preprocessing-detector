# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Table Dataset Downloader for TableBank, PubTabNet, and FinTabNet

Downloads table detection/recognition datasets from HuggingFace with rate-limit
handling and progress tracking.

Datasets:
---------
1. TableBank (liminghao1630/TableBank) - 23.7 GB
   - 417K high-quality labeled tables from Word and LaTeX documents
   - Multi-part zip (5 parts) requires joining

2. PubTabNet (ajimeno/PubTabNet) - 10.5 GB
   - 568K+ scientific publication tables with HTML annotations
   - Single tar.gz file

3. FinTabNet.c (bsmock/FinTabNet.c) - 3.2 GB
   - Financial tables with corrections
   - Two tar.gz files (PDF annotations + structure)

Usage:
------
    # Download all datasets
    python scripts/download_table_datasets.py --all

    # Download specific datasets
    python scripts/download_table_datasets.py --datasets tablebank pubtabnet

    # Custom output directory
    python scripts/download_table_datasets.py --datasets fintabnet --output-dir /path/to/data

HuggingFace Rate Limits (Free Tier):
- 5,000 requests per 5-minute window
- Large files may hit limits - script will retry automatically
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Dataset configurations
DATASETS = {
    "tablebank": {
        "repo_id": "liminghao1630/TableBank",
        "size_gb": 23.7,
        "files": [
            "TableBank.zip.001",
            "TableBank.zip.002",
            "TableBank.zip.003",
            "TableBank.zip.004",
            "TableBank.zip.005",
        ],
        "output_subdir": "tablebank",
        "description": "TableBank - 417K tables from Word/LaTeX documents",
    },
    "pubtabnet": {
        "repo_id": "ajimeno/PubTabNet",
        "size_gb": 10.5,
        "files": ["pubtabnet.tar.gz"],
        "output_subdir": "pubtabnet",
        "description": "PubTabNet - 568K+ scientific tables with HTML",
    },
    "fintabnet": {
        "repo_id": "bsmock/FinTabNet.c",
        "size_gb": 3.2,
        "files": ["FinTabNet.c-PDF_Annotations.tar.gz", "FinTabNet.c-Structure.tar.gz"],
        "output_subdir": "fintabnet",
        "description": "FinTabNet.c - Financial tables (corrected version)",
    },
}


def load_token_from_env() -> str | None:
    """Load HuggingFace token from .env file."""
    env_file = Path(__file__).parent.parent / ".env"

    if not env_file.exists():
        return None

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("HF_TOKEN="):
                token = line.split("=", 1)[1].strip()
                if token and not token.startswith("#"):
                    return token

    return None


def download_file_with_hf_cli(
    repo_id: str, filename: str, output_dir: Path, hf_token: str
) -> bool:
    """
    Download a single file from HuggingFace using Python API.

    Args:
        repo_id: HuggingFace repository ID
        filename: File to download
        output_dir: Local output directory
        hf_token: HuggingFace API token

    Returns:
        bool: True if download successful
    """
    try:
        from huggingface_hub import hf_hub_download

        logger.info(f"Downloading: {filename}")

        # Use huggingface_hub Python API
        # nosec B615 - trusted dataset, consider revision pinning
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="dataset",
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            token=hf_token,
        )

        logger.info(f"✓ Downloaded: {filename}")
        return True

    except Exception as e:
        logger.error(f"Unexpected error downloading {filename}: {e}")
        return False


def join_zip_parts(output_dir: Path, dataset_name: str) -> bool:
    """
    Join multi-part zip files (for TableBank).

    Args:
        output_dir: Directory containing zip parts
        dataset_name: Name of dataset (for logging)

    Returns:
        bool: True if joining successful
    """
    try:
        logger.info(f"Joining multi-part zip for {dataset_name}...")

        # Find all zip parts
        zip_parts = sorted(output_dir.glob("*.zip.*"))

        if not zip_parts:
            logger.error("No zip parts found!")
            return False

        logger.info(f"Found {len(zip_parts)} zip parts")

        # Join parts using cat
        output_zip = output_dir / f"{dataset_name}.zip"

        with open(output_zip, "wb") as outfile:
            for part in zip_parts:
                logger.info(f"Adding: {part.name}")
                with open(part, "rb") as infile:
                    outfile.write(infile.read())

        logger.info(f"✓ Created joined zip: {output_zip}")
        logger.info(f"Size: {output_zip.stat().st_size / (1024**3):.2f} GB")

        # Verify zip integrity using Python's zipfile module
        logger.info("Verifying zip integrity...")
        import zipfile

        try:
            with zipfile.ZipFile(output_zip, "r") as zip_ref:
                # testzip() returns None if all files are OK, or the name of the first bad file
                bad_file = zip_ref.testzip()
                if bad_file is None:
                    logger.info("✓ Zip integrity verified")
                    return True
                logger.error(f"Zip verification failed: corrupted file {bad_file}")
                return False
        except Exception as e:
            logger.error(f"Zip verification failed: {e}")
            return False

    except Exception as e:
        logger.error(f"Error joining zip parts: {e}")
        return False


def extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    """
    Extract tar.gz or zip archive using Python's built-in libraries.

    Args:
        archive_path: Path to archive file (must exist and be within project)
        extract_dir: Directory to extract to

    Returns:
        bool: True if extraction successful

    Raises:
        ValueError: If paths are invalid or potentially unsafe
    """
    import tarfile
    import zipfile

    try:
        # Resolve paths to prevent directory traversal attacks
        archive_path = archive_path.resolve()
        extract_dir = extract_dir.resolve()

        # Validate archive exists
        if not archive_path.exists():
            msg = f"Archive does not exist: {archive_path}"
            logger.error(msg)
            raise ValueError(msg)

        # Ensure archive is a file (not a directory or symlink to something dangerous)
        if not archive_path.is_file():
            msg = f"Archive path is not a regular file: {archive_path}"
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"Extracting: {archive_path.name}")
        extract_dir.mkdir(parents=True, exist_ok=True)

        # Extract based on archive type using Python's built-in libraries
        if archive_path.suffix == ".gz" or archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                # Security: filter="data" prevents path traversal attacks (Python 3.12+)
                # nosec B202 - Using filter="data" for safe extraction
                tar.extractall(path=extract_dir, filter="data")  # nosec
            logger.info(f"✓ Extracted tar.gz to: {extract_dir}")
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                # nosec B202 - Extracting from validated archive path (resolved, exists, is_file checks)
                zip_ref.extractall(extract_dir)  # nosec
            logger.info(f"✓ Extracted zip to: {extract_dir}")
        else:
            logger.error(f"Unknown archive type: {archive_path.suffix}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error extracting archive: {e}")
        return False


def _download_all_files(
    config: dict[str, Any], output_dir: Path, hf_token: str
) -> bool:
    """Download all files for a dataset.

    Args:
        config: Dataset configuration dictionary
        output_dir: Output directory for downloads
        hf_token: HuggingFace API token

    Returns:
        True if all files downloaded successfully
    """
    for filename in config["files"]:
        if not download_file_with_hf_cli(
            config["repo_id"], filename, output_dir, hf_token
        ):
            return False
    return True


def _is_extractable_archive(archive_path: Path) -> bool:
    """Check if a path is an extractable archive.

    Args:
        archive_path: Path to check

    Returns:
        True if the file is a tar.gz or zip archive
    """
    if not archive_path.exists():
        return False
    return archive_path.suffix in [".gz", ".zip"] or str(archive_path).endswith(
        ".tar.gz"
    )


def _handle_tablebank_postprocess(
    output_dir: Path, dataset_name: str, extract: bool
) -> bool:
    """Handle TableBank multi-part zip joining and extraction.

    Args:
        output_dir: Output directory
        dataset_name: Dataset name
        extract: Whether to extract after joining

    Returns:
        True if post-processing succeeded
    """
    if not join_zip_parts(output_dir, dataset_name):
        return False

    if extract:
        joined_zip = output_dir / f"{dataset_name}.zip"
        if joined_zip.exists():
            extract_archive(joined_zip, output_dir)

    return True


def _extract_archives(config: dict[str, Any], output_dir: Path) -> None:
    """Extract all archives for a dataset.

    Args:
        config: Dataset configuration dictionary
        output_dir: Output directory containing archives
    """
    for filename in config["files"]:
        archive_path = output_dir / filename
        if _is_extractable_archive(archive_path):
            extract_archive(archive_path, output_dir)


def _log_download_header(config: dict[str, Any], output_dir: Path) -> None:
    """Log download header information.

    Args:
        config: Dataset configuration dictionary
        output_dir: Output directory
    """
    logger.info("\n" + "=" * 80)
    logger.info(f"Downloading: {config['description']}")
    logger.info(f"Repository: {config['repo_id']}")
    logger.info(f"Size: {config['size_gb']:.1f} GB")
    logger.info(f"Files: {len(config['files'])}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 80 + "\n")


def download_dataset(
    dataset_name: str, output_base_dir: str, hf_token: str, extract: bool = True
) -> bool:
    """Download a table dataset from HuggingFace.

    Args:
        dataset_name: Name of dataset ('tablebank', 'pubtabnet', or 'fintabnet')
        output_base_dir: Base output directory
        hf_token: HuggingFace API token
        extract: Whether to extract archives after download

    Returns:
        bool: True if download successful
    """
    if dataset_name not in DATASETS:
        logger.error(f"Unknown dataset: {dataset_name}")
        logger.info(f"Available datasets: {', '.join(DATASETS.keys())}")
        return False

    config = DATASETS[dataset_name]
    output_dir = Path(output_base_dir) / config["output_subdir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    _log_download_header(config, output_dir)

    # Download all files
    if not _download_all_files(config, output_dir, hf_token):
        return False

    # Post-process based on dataset type
    is_multipart = dataset_name == "tablebank" and len(config["files"]) > 1
    if is_multipart:
        if not _handle_tablebank_postprocess(output_dir, dataset_name, extract):
            return False
    elif extract:
        _extract_archives(config, output_dir)

    logger.info("\n" + "=" * 80)
    logger.info(f"✓ {dataset_name.upper()} Download Complete!")
    logger.info(f"Location: {output_dir.absolute()}")
    logger.info("=" * 80 + "\n")

    return True


def _resolve_hf_token(token_arg: str | None) -> str | None:
    """Resolve HuggingFace token from argument, .env, or environment.

    Args:
        token_arg: Token from command line argument (if any)

    Returns:
        Resolved token or None if not found
    """
    return token_arg or load_token_from_env() or os.getenv("HF_TOKEN")


def _log_missing_token_error() -> None:
    """Log error message for missing HuggingFace token."""
    logger.error("No HuggingFace token found!")
    logger.error("Please either:")
    logger.error("  1. Add HF_TOKEN to .env file")
    logger.error("  2. Set HF_TOKEN environment variable")
    logger.error("  3. Pass --token argument")
    logger.error("\nGet your token at: https://huggingface.co/settings/tokens")


def _check_disk_space(output_path: Path, total_size_gb: float) -> bool:
    """Check if sufficient disk space is available.

    Args:
        output_path: Output directory path
        total_size_gb: Total size needed in GB

    Returns:
        True if user confirms to proceed or space is sufficient
    """
    stat = os.statvfs(output_path)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

    logger.info(f"Available disk space: {free_gb:.1f} GB")

    required_gb = total_size_gb * 1.5  # Need 1.5x for extraction
    if free_gb >= required_gb:
        return True

    logger.warning(
        f"Low disk space! Need ~{required_gb:.1f} GB for download + extraction"
    )
    response = input("Continue anyway? (y/N): ")
    return response.lower() == "y"


def _run_downloads(
    datasets: list[str], output_dir: str, hf_token: str, extract: bool
) -> int:
    """Run downloads for all specified datasets.

    Args:
        datasets: List of dataset names to download
        output_dir: Output directory
        hf_token: HuggingFace API token
        extract: Whether to extract archives

    Returns:
        Number of successfully downloaded datasets, or -1 if interrupted
    """
    success_count = 0
    for dataset in datasets:
        try:
            if download_dataset(dataset, output_dir, hf_token, extract=extract):
                success_count += 1
            else:
                logger.error(f"Failed to download {dataset}")
        except KeyboardInterrupt:
            logger.warning("\nDownload interrupted by user")
            return -1
        except Exception as e:
            logger.error(f"Error downloading {dataset}: {e}")
    return success_count


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download table datasets from HuggingFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["tablebank", "pubtabnet", "fintabnet"],
        help="Datasets to download (space-separated)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Download all table datasets"
    )
    parser.add_argument(
        "--output-dir",
        default="data/benchmarks",
        help="Base output directory (default: data/benchmarks)",
    )
    parser.add_argument(
        "--token", help="HuggingFace API token (default: read from .env)"
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Do not extract archives after download",
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    if not args.datasets and not args.all:
        parser.error("Must specify either --datasets or --all")

    # Get HuggingFace token
    hf_token = _resolve_hf_token(args.token)
    if not hf_token:
        _log_missing_token_error()
        return 1

    # Determine which datasets to download
    datasets_to_download = list(DATASETS.keys()) if args.all else args.datasets

    # Print summary
    total_size = sum(DATASETS[d]["size_gb"] for d in datasets_to_download)
    print("\n" + "=" * 80)
    print("TABLE DATASETS DOWNLOADER")
    print("=" * 80)
    print(f"Datasets: {', '.join(datasets_to_download)}")
    print(f"Output directory: {args.output_dir}")
    print(f"Total size: {total_size:.1f} GB")
    print(f"Extract after download: {not args.no_extract}")
    print("=" * 80 + "\n")

    # Check disk space
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not _check_disk_space(output_path, total_size):
        logger.info("Download cancelled")
        return 0

    # Download datasets
    success_count = _run_downloads(
        datasets_to_download, args.output_dir, hf_token, extract=not args.no_extract
    )
    if success_count == -1:  # Interrupted
        return 1

    # Final summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(
        f"Successfully downloaded: {success_count}/{len(datasets_to_download)} datasets"
    )

    if success_count == len(datasets_to_download):
        print("\n✓ All downloads completed successfully!")
        return 0
    print("\n✗ Some downloads failed. Check errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
