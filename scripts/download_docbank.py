#!/usr/bin/env python3
"""
Download DocBank dataset from HuggingFace.

Dataset: 500K document pages with reading order annotations
License: Apache-2.0
Source: https://huggingface.co/datasets/liminghao1630/DocBank
"""

import argparse
import logging
from pathlib import Path

from huggingface_hub import snapshot_download

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def download_docbank(output_dir: Path, use_cache: bool = True) -> None:
    """
    Download DocBank dataset from HuggingFace.

    Args:
        output_dir: Directory to save dataset
        use_cache: Use HuggingFace cache (default: True). When False, forces re-download.
    """
    logger.info(f"Downloading DocBank dataset to {output_dir}")
    logger.info("Dataset size: 500K pages (train: 400K, val: 50K, test: 50K)")
    logger.info("License: Apache-2.0")
    logger.info("Expected download size: ~50-100 GB")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download dataset from HuggingFace
        snapshot_download(  # nosec B615 - trusted dataset source, consider revision pinning
            repo_id="liminghao1630/DocBank",
            repo_type="dataset",
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,  # Don't use symlinks
            resume_download=True,  # Resume if interrupted
            max_workers=4,  # Parallel downloads
            force_download=not use_cache,
        )

        logger.info(f"✅ DocBank dataset downloaded successfully to {output_dir}")
        logger.info("Dataset structure:")
        logger.info("  - 500K document pages with 12 semantic unit types")
        logger.info(
            "  - Semantic units: Abstract, Author, Caption, Date, Equation, Figure, Footer, List, Paragraph, Reference, Section, Table, Title"
        )
        logger.info("  - Token-level annotations with reading order")
        logger.info("  - Covers documents from 2014-2018")

    except Exception as e:
        logger.error(f"❌ Error downloading DocBank: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Download DocBank dataset from HuggingFace"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/layout/docbank"),
        help="Output directory for dataset (default: data/training/layout/docbank)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't use HuggingFace cache (default: use cache)",
    )

    args = parser.parse_args()

    download_docbank(args.output_dir, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
