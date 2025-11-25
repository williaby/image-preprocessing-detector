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


def _resolve_hf_token(hf_token: str | None) -> str | None:
    """Resolve HuggingFace token from multiple sources.

    Args:
        hf_token: Explicit token if provided

    Returns:
        Resolved token or None if not found
    """
    if hf_token is not None:
        return hf_token

    token = load_token_from_env()
    if token is not None:
        return token

    return os.getenv("HF_TOKEN")


def _log_token_not_found() -> None:
    """Log error message when HuggingFace token is not found."""
    logger.error("No HuggingFace token found!")
    logger.error("Please either:")
    logger.error("  1. Add HF_TOKEN to .env file")
    logger.error("  2. Set HF_TOKEN environment variable")
    logger.error("  3. Pass --token argument")
    logger.error("\nGet your token at: https://huggingface.co/settings/tokens")


def _check_account_status(hf_token: str) -> None:
    """Check and log HuggingFace account status."""
    try:
        from huggingface_hub import HfApi

        api = HfApi(token=hf_token)
        user_info = api.whoami()
        logger.info(f"Logged in as: {user_info.get('name', 'Unknown')}")

        is_pro = user_info.get("isPro", False) or user_info.get("orgs", [])
        if is_pro:
            logger.info(
                "✓ PRO/Enterprise account detected - higher rate limits available"
            )
        else:
            logger.info(
                "Free tier account - using conservative rate limiting (5,000 req/5min)"
            )
    except Exception as e:
        logger.warning(f"Could not check account status: {e}")


def _is_rate_limit_error(error_msg: str) -> bool:
    """Check if an error message indicates a rate limit error."""
    error_lower = error_msg.lower()
    return any(
        indicator in error_lower
        for indicator in ("rate limit", "429", "too many requests")
    )


def _log_rate_limit_suggestions() -> None:
    """Log suggestions for handling rate limits."""
    logger.info("Consider:")
    logger.info("  1. Using a PRO account for higher limits (12,000 req/5min)")
    logger.info("  2. Running during off-peak hours")
    logger.info("  3. Downloading in smaller batches")


def _log_download_success(output_path: Path, dataset) -> None:
    """Log successful download information."""
    logger.info("\n" + "=" * 70)
    logger.info("✓ Download Complete!")
    logger.info("=" * 70)
    logger.info(f"Dataset saved to: {output_path.absolute()}")
    logger.info("\nDataset structure:")
    for split_name, split_dataset in dataset.items():
        logger.info(f"  {split_name}: {len(split_dataset)} rows")
        logger.info(f"    Features: {list(split_dataset.features.keys())}")

    logger.info(f"\nTotal size on disk: {get_directory_size(output_path):.2f} MB")
    logger.info("\nTo use this dataset:")
    logger.info("  from datasets import load_from_disk")
    logger.info(f"  dataset = load_from_disk('{output_path}')")


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
        from huggingface_hub import login

        from datasets import load_dataset
    except ImportError:
        logger.error("Required packages not found. Install with: uv sync --extra ml")
        logger.error("Or: pip install datasets huggingface-hub")
        return False

    # Resolve and validate token
    hf_token = _resolve_hf_token(hf_token)
    if not hf_token:
        _log_token_not_found()
        return False

    # Authenticate with HuggingFace
    logger.info("Authenticating with HuggingFace...")
    try:
        login(token=hf_token, add_to_git_credential=False)
        logger.info("✓ Authentication successful")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

    _check_account_status(hf_token)

    # Initialize rate limit handler and output directory
    rate_limiter = RateLimitHandler()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_path.absolute()}")

    # Download dataset with retries
    return _execute_download_with_retries(
        load_dataset, output_path, hf_token, rate_limiter, max_retries, retry_delay
    )


def _execute_download_with_retries(
    load_dataset,
    output_path: Path,
    hf_token: str,
    rate_limiter: RateLimitHandler,
    max_retries: int,
    retry_delay: int,
) -> bool:
    """Execute the download with retry logic.

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Download Attempt {attempt}/{max_retries}")
        logger.info(f"{'=' * 70}")
        logger.info("Dataset: opendatalab/OmniDocBench")
        logger.info("Size: ~1.25 GB (1,358 rows with images)")
        logger.info("This may take 10-30 minutes depending on connection speed...")
        logger.info("")

        rate_limiter.check_and_wait()

        try:
            dataset = load_dataset(  # nosec B615 - trusted dataset
                "opendatalab/OmniDocBench",
                cache_dir=str(output_path / ".cache"),
                token=hf_token,
                trust_remote_code=True,
            )

            logger.info(f"\nSaving dataset to: {output_path}")
            dataset.save_to_disk(str(output_path))
            _log_download_success(output_path, dataset)
            return True

        except Exception as e:
            should_continue = _handle_download_error(
                e, attempt, max_retries, retry_delay
            )
            if not should_continue:
                return False

    return False


def _handle_download_error(
    error: Exception, attempt: int, max_retries: int, retry_delay: int
) -> bool:
    """Handle download errors and determine if retry should continue.

    Returns:
        True if should continue retrying, False if should stop
    """
    error_msg = str(error)
    is_last_attempt = attempt >= max_retries

    if _is_rate_limit_error(error_msg):
        wait_time = retry_delay * (2 ** (attempt - 1))
        logger.warning(f"Rate limit hit on attempt {attempt}/{max_retries}")

        if is_last_attempt:
            logger.error("Max retries exceeded due to rate limiting")
            logger.error("Please try again later or upgrade to PRO account")
            return False

        logger.info(f"Waiting {wait_time}s before retry...")
        _log_rate_limit_suggestions()
        time.sleep(wait_time)
        return True

    # Other error
    logger.error(f"Download failed: {error}")
    if is_last_attempt:
        return False

    logger.info(f"Retrying in {retry_delay}s...")
    time.sleep(retry_delay)
    return True


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
