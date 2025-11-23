# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
OmniDocBench Dataset Downloader with Rate Limit Handling

This script downloads the OmniDocBench dataset from HuggingFace with intelligent
rate limit handling, progress tracking, and resume capability.

Dataset: https://huggingface.co/datasets/opendatalab/OmniDocBench
Size: ~1.25 GB
Files: 1,358 rows with thousands of image files
License: CC-BY-NC-4.0 (Evaluation only, non-commercial)

HuggingFace Rate Limits (Free Tier):
- 5,000 requests per 5-minute window (Resolver/file downloads)
- Rate limits reset every 5 minutes
- Authentication via HF_TOKEN significantly increases limits

Usage:
    # Using token from .env
    python scripts/download_omnidocbench.py

    # Override token
    python scripts/download_omnidocbench.py --token hf_xxx

    # Custom output directory
    python scripts/download_omnidocbench.py --output-dir /path/to/data
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RateLimitHandler:
    """Handles HuggingFace rate limiting with backoff strategy."""

    def __init__(self, requests_per_window: int = 5000, window_minutes: int = 5):
        """
        Initialize rate limit handler.

        Args:
            requests_per_window: Maximum requests allowed in window (default: 5000 for free tier)
            window_minutes: Window duration in minutes (default: 5)
        """
        self.requests_per_window = requests_per_window
        self.window_duration = timedelta(minutes=window_minutes)
        self.request_count = 0
        self.window_start = datetime.now()

    def check_and_wait(self):
        """Check rate limit and wait if necessary."""
        now = datetime.now()
        elapsed = now - self.window_start

        # Reset window if expired
        if elapsed >= self.window_duration:
            logger.info(
                f"Rate limit window reset. Processed {self.request_count} requests in last {self.window_duration.seconds // 60} minutes."
            )
            self.request_count = 0
            self.window_start = now
            return

        # Check if approaching limit (90% threshold)
        threshold = int(self.requests_per_window * 0.9)
        if self.request_count >= threshold:
            wait_time = (self.window_duration - elapsed).total_seconds()
            if wait_time > 0:
                logger.warning(
                    f"Approaching rate limit ({self.request_count}/{self.requests_per_window} requests)."
                )
                logger.info(
                    f"Waiting {wait_time:.1f}s for rate limit window to reset..."
                )
                time.sleep(wait_time + 1)  # Add 1s buffer
                # Reset after waiting
                self.request_count = 0
                self.window_start = datetime.now()

        self.request_count += 1


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


def download_omnidocbench(
    output_dir: str = "data/benchmarks/omnidocbench",
    hf_token: str | None = None,
    max_retries: int = 5,
    retry_delay: int = 60,
) -> bool:
    """
    Download OmniDocBench dataset with rate limit handling.

    Args:
        output_dir: Directory to save dataset
        hf_token: HuggingFace API token (if None, loads from .env)
        max_retries: Maximum retry attempts on rate limit errors
        retry_delay: Initial delay between retries (seconds, with exponential backoff)

    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        # Import here to provide better error messages
        from huggingface_hub import HfApi, login

        from datasets import load_dataset
    except ImportError:
        logger.error("Required packages not found. Install with: uv sync --extra ml")
        logger.error("Or: pip install datasets huggingface-hub")
        return False

    # Get HuggingFace token
    if hf_token is None:
        hf_token = load_token_from_env()

    if hf_token is None:
        hf_token = os.getenv("HF_TOKEN")

    if not hf_token:
        logger.error("No HuggingFace token found!")
        logger.error("Please either:")
        logger.error("  1. Add HF_TOKEN to .env file")
        logger.error("  2. Set HF_TOKEN environment variable")
        logger.error("  3. Pass --token argument")
        logger.error("\nGet your token at: https://huggingface.co/settings/tokens")
        return False

    # Authenticate with HuggingFace
    logger.info("Authenticating with HuggingFace...")
    try:
        login(token=hf_token, add_to_git_credential=False)
        logger.info("✓ Authentication successful")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

    # Check rate limit status (optional, requires API)
    try:
        api = HfApi(token=hf_token)
        user_info = api.whoami()
        logger.info(f"Logged in as: {user_info.get('name', 'Unknown')}")

        # Check if PRO account (higher rate limits)
        if user_info.get("isPro", False) or user_info.get("orgs", []):
            logger.info(
                "✓ PRO/Enterprise account detected - higher rate limits available"
            )
        else:
            logger.info(
                "Free tier account - using conservative rate limiting (5,000 req/5min)"
            )
    except Exception as e:
        logger.warning(f"Could not check account status: {e}")

    # Initialize rate limit handler
    rate_limiter = RateLimitHandler()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_path.absolute()}")

    # Download dataset with retries
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Download Attempt {attempt}/{max_retries}")
            logger.info(f"{'=' * 70}")
            logger.info("Dataset: opendatalab/OmniDocBench")
            logger.info("Size: ~1.25 GB (1,358 rows with images)")
            logger.info("This may take 10-30 minutes depending on connection speed...")
            logger.info("")

            # Check rate limit before starting
            rate_limiter.check_and_wait()

            # Download dataset
            # Using streaming=False to download everything at once
            # Using cache_dir to avoid redundant downloads
            dataset = load_dataset(
                "opendatalab/OmniDocBench",
                cache_dir=str(output_path / ".cache"),
                token=hf_token,
                trust_remote_code=True,  # Required for some datasets
            )

            # Save to disk in arrow format (efficient)
            logger.info(f"\nSaving dataset to: {output_path}")
            dataset.save_to_disk(str(output_path))

            # Print dataset info
            logger.info("\n" + "=" * 70)
            logger.info("✓ Download Complete!")
            logger.info("=" * 70)
            logger.info(f"Dataset saved to: {output_path.absolute()}")
            logger.info("\nDataset structure:")
            for split_name, split_dataset in dataset.items():
                logger.info(f"  {split_name}: {len(split_dataset)} rows")
                logger.info(f"    Features: {list(split_dataset.features.keys())}")

            logger.info(
                f"\nTotal size on disk: {get_directory_size(output_path):.2f} MB"
            )
            logger.info("\nTo use this dataset:")
            logger.info("  from datasets import load_from_disk")
            logger.info(f"  dataset = load_from_disk('{output_path}')")

            return True

        except Exception as e:
            error_msg = str(e).lower()

            # Check if rate limit error
            if (
                "rate limit" in error_msg
                or "429" in error_msg
                or "too many requests" in error_msg
            ):
                wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(f"Rate limit hit on attempt {attempt}/{max_retries}")

                if attempt < max_retries:
                    logger.info(f"Waiting {wait_time}s before retry...")
                    logger.info("Consider:")
                    logger.info(
                        "  1. Using a PRO account for higher limits (12,000 req/5min)"
                    )
                    logger.info("  2. Running during off-peak hours")
                    logger.info("  3. Downloading in smaller batches")
                    time.sleep(wait_time)
                    continue
                logger.error("Max retries exceeded due to rate limiting")
                logger.error("Please try again later or upgrade to PRO account")
                return False
            # Other error
            logger.error(f"Download failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            return False

    return False


def get_directory_size(path: Path) -> float:
    """Calculate directory size in MB."""
    total_size = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
    except Exception:
        return 0.0
    return total_size / (1024 * 1024)  # Convert to MB


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download OmniDocBench dataset with rate limit handling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-dir",
        default="data/benchmarks/omnidocbench",
        help="Output directory for dataset (default: data/benchmarks/omnidocbench)",
    )
    parser.add_argument(
        "--token", help="HuggingFace API token (default: read from .env)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=5, help="Maximum retry attempts (default: 5)"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=60,
        help="Initial retry delay in seconds (default: 60, uses exponential backoff)",
    )

    args = parser.parse_args()

    # Print header
    print("\n" + "=" * 70)
    print("OmniDocBench Dataset Downloader")
    print("=" * 70)
    print("Dataset: https://huggingface.co/datasets/opendatalab/OmniDocBench")
    print("Size: ~1.25 GB")
    print("License: CC-BY-NC-4.0 (Non-commercial evaluation only)")
    print("=" * 70 + "\n")

    # Download dataset
    success = download_omnidocbench(
        output_dir=args.output_dir,
        hf_token=args.token,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )

    if success:
        print("\n✓ Dataset download completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Dataset download failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
