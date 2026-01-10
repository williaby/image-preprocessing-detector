#!/usr/bin/env python3
"""Download OCR-Quality dataset images from HuggingFace.

This script downloads all 1000 images from the Aslan-mingye/OCR-Quality dataset
to the specified output directory for use in Stage 1 DeQA-Doc labeling.

Usage:
    python scripts/download_ocr_quality_images.py --output /mnt/e/image_detection/01_base_data/ocr_quality/pics
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://huggingface.co/datasets/Aslan-mingye/OCR-Quality/resolve/main/pics"
TOTAL_IMAGES = 1000
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_WORKERS = 5  # Conservative to avoid rate limiting


def download_image(index: int, output_dir: Path, session: requests.Session) -> tuple[int, bool, str]:
    """Download a single image with retry logic.

    Args:
        index: Image index (0-999)
        output_dir: Directory to save images
        session: Requests session for connection reuse

    Returns:
        Tuple of (index, success, error_message)
    """
    filename = f"{index}.png"
    url = f"{BASE_URL}/{filename}"
    output_path = output_dir / filename

    # Skip if already downloaded
    if output_path.exists() and output_path.stat().st_size > 0:
        return (index, True, "already exists")

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            return (index, True, "downloaded")

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limited
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            elif attempt == MAX_RETRIES - 1:
                return (index, False, str(e))

        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                return (index, False, str(e))
            time.sleep(RETRY_DELAY)

    return (index, False, "max retries exceeded")


def main():
    parser = argparse.ArgumentParser(description="Download OCR-Quality dataset images")
    parser.add_argument(
        "--output",
        type=str,
        default="/mnt/e/image_detection/01_base_data/ocr_quality/pics",
        help="Output directory for images"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help="Number of parallel download workers"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start index (for resuming)"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check existing files
    existing = sum(1 for f in output_dir.glob("*.png") if f.stat().st_size > 0)
    print(f"Found {existing} existing images in {output_dir}")

    # Create session for connection reuse
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; OCR-Quality-Downloader/1.0)"
    })

    # Download images
    indices = range(args.start, TOTAL_IMAGES)
    failed = []

    print(f"Downloading {TOTAL_IMAGES - args.start} images to {output_dir}...")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_image, i, output_dir, session): i
            for i in indices
        }

        with tqdm(total=len(futures), desc="Downloading") as pbar:
            for future in as_completed(futures):
                index, success, message = future.result()
                if not success and message != "already exists":
                    failed.append((index, message))
                pbar.update(1)

    # Report results
    final_count = sum(1 for f in output_dir.glob("*.png") if f.stat().st_size > 0)
    print(f"\nDownload complete: {final_count}/{TOTAL_IMAGES} images")

    if failed:
        print(f"\nFailed downloads ({len(failed)}):")
        for idx, msg in failed[:10]:
            print(f"  - {idx}.png: {msg}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")

    # Write manifest
    manifest_path = output_dir.parent / "download_manifest.txt"
    with open(manifest_path, "w") as f:
        f.write(f"OCR-Quality Dataset Download\n")
        f.write(f"============================\n")
        f.write(f"Total images: {TOTAL_IMAGES}\n")
        f.write(f"Downloaded: {final_count}\n")
        f.write(f"Failed: {len(failed)}\n")
        if failed:
            f.write(f"\nFailed files:\n")
            for idx, msg in failed:
                f.write(f"  {idx}.png: {msg}\n")

    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
