#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Convert HuggingFace datasets in parquet format to image files.

Handles datasets with images stored in parquet format, including:
- ohr-bench (IQA benchmark)
- cocotext (scene text detection)
- iam_handwriting (handwriting corpus)
- docsynth300k (synthetic documents)
- mobile_receipts (receipt images)

Usage:
    # Convert specific dataset
    python scripts/convert_parquet_to_images.py --dataset ohr-bench --format png

    # Convert with chunked processing (for large datasets)
    python scripts/convert_parquet_to_images.py --dataset docsynth300k --format png --chunked --chunk_size 50000

    # Specify custom paths
    python scripts/convert_parquet_to_images.py --dataset ohr-bench --output /path/to/output --format png

    # Dry run to check dataset structure
    python scripts/convert_parquet_to_images.py --dataset ohr-bench --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from datasets import concatenate_datasets, load_dataset
    from PIL import Image
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: uv add datasets pillow")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default paths
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")
BENCHMARK_PATH = Path("/mnt/e/image_detection/02_benchmark_only")

# Dataset configurations
DATASET_CONFIGS = {
    "ohr-bench": {
        "hf_name": "opendatalab/ohr-bench",
        "output_dir": BENCHMARK_PATH / "ohr_bench",
        "image_column": "image",
        "format": "png",
        "description": "OHR-Bench IQA benchmark dataset",
    },
    "cocotext": {
        "hf_name": "wulipc/cc-ocr",
        "output_dir": BASE_DATA_PATH / "language/cocotext",
        "image_column": "image",
        "format": "jpg",
        "description": "COCO-Text scene text detection dataset",
        "split": "doc_parsing",  # Use doc_parsing split
    },
    "iam_handwriting": {
        "hf_name": "Teklia/IAM-line",  # IAM handwriting dataset
        "output_dir": BASE_DATA_PATH / "handwriting/iam_handwriting",
        "image_column": "image",
        "format": "png",
        "description": "IAM Handwriting Database",
    },
    "docsynth300k": {
        "hf_name": "jordyvl/docsynth300k",  # DocSynth synthetic documents
        "output_dir": BASE_DATA_PATH / "synthetic/docsynth300k",
        "image_column": "image",
        "format": "png",
        "description": "DocSynth 300K synthetic documents",
    },
    "mobile_receipts": {
        "hf_name": "naver-clova-ix/cord-v2",  # CORD receipt dataset
        "output_dir": BASE_DATA_PATH / "receipts/mobile_receipts",
        "image_column": "image",
        "format": "jpg",
        "description": "Mobile receipt images",
    },
}


def _load_hf_dataset(
    config: dict[str, Any],
) -> tuple[Any, Any, int]:
    """Load a HuggingFace dataset and flatten splits if needed.

    Args:
        config: Dataset configuration dict.

    Returns:
        Tuple of (original_dataset, all_data_iterable, total_samples).
    """
    load_kwargs = {}
    if "split" in config:
        load_kwargs["name"] = config["split"]

    dataset = load_dataset(config["hf_name"], **load_kwargs)

    if isinstance(dataset, dict):
        logger.info(f"Dataset splits: {list(dataset.keys())}")
        for split_name, split_data in dataset.items():
            logger.info(f"  {split_name}: {len(split_data)} samples")
        all_data = concatenate_datasets(list(dataset.values()))
        total_samples = len(all_data)
    else:
        all_data = dataset
        total_samples = len(dataset)

    return dataset, all_data, total_samples


def convert_dataset_to_images(
    dataset_name: str,
    output_dir: Path | None = None,
    image_format: str = "png",
    chunked: bool = False,
    chunk_size: int = 50000,
    workers: int = 4,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Convert a HuggingFace dataset from parquet to image files.

    Args:
        dataset_name: Name of dataset (must be in DATASET_CONFIGS)
        output_dir: Output directory (default from config)
        image_format: Output format (png, jpg)
        chunked: Process in chunks (for large datasets)
        chunk_size: Number of images per chunk
        workers: Number of parallel workers (not yet implemented)
        dry_run: Only analyze dataset without converting

    Returns:
        Dictionary with conversion statistics
    """
    if dataset_name not in DATASET_CONFIGS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. "
            f"Available: {list(DATASET_CONFIGS.keys())}"
        )

    config = DATASET_CONFIGS[dataset_name]
    output_dir = output_dir or config["output_dir"]
    image_format = image_format or config["format"]
    image_column = config["image_column"]

    logger.info(f"Loading dataset: {config['hf_name']}")
    logger.info(f"Description: {config['description']}")

    stats: dict[str, Any] = {
        "dataset": dataset_name,
        "found": 0,
        "converted": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        dataset, all_data, total_samples = _load_hf_dataset(config)
        stats["found"] = total_samples
        logger.info(f"Total samples to process: {total_samples}")

        if dry_run:
            logger.info("[DRY RUN] Would convert images to:")
            logger.info(f"  Output: {output_dir}")
            logger.info(f"  Format: {image_format}")
            logger.info(f"  Chunked: {chunked}")
            if chunked:
                num_chunks = (total_samples + chunk_size - 1) // chunk_size
                logger.info(f"  Chunks: {num_chunks} x {chunk_size} images")
            return stats

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

        data_source = dataset if not isinstance(dataset, dict) else all_data
        if chunked:
            logger.info(f"Processing in chunks of {chunk_size}")
            _convert_chunked(
                data_source, output_dir, image_column, image_format, chunk_size, stats
            )
        else:
            _convert_standard(
                data_source, output_dir, image_column, image_format, stats
            )

        logger.info(
            f"Conversion complete: "
            f"{stats['converted']} converted, "
            f"{stats['skipped']} skipped, "
            f"{stats['errors']} errors"
        )

    except Exception as e:
        logger.error(f"Error loading/converting dataset: {e}")
        stats["error"] = str(e)

    return stats


def _convert_standard(
    dataset: Any,
    output_dir: Path,
    image_column: str,
    image_format: str,
    stats: dict[str, Any],
) -> None:
    """Standard conversion (all at once)."""
    for idx, sample in enumerate(dataset):
        _convert_sample(sample, idx, output_dir, image_column, image_format, stats)

        if stats["converted"] % 1000 == 0 and stats["converted"] > 0:
            logger.info(
                f"Progress: {stats['converted']}/{stats['found']} "
                f"({stats['converted'] / stats['found'] * 100:.1f}%)"
            )


def _convert_chunked(
    dataset: Any,
    output_dir: Path,
    image_column: str,
    image_format: str,
    chunk_size: int,
    stats: dict[str, Any],
) -> None:
    """Chunked conversion (process in batches)."""
    total = stats["found"]
    num_chunks = (total + chunk_size - 1) // chunk_size

    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, total)

        logger.info(
            f"Processing chunk {chunk_idx + 1}/{num_chunks} "
            f"(samples {start_idx}-{end_idx})"
        )

        # Create chunk subdirectory
        chunk_dir = output_dir / f"chunk_{chunk_idx:04d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)

        for idx in range(start_idx, end_idx):
            sample = dataset[idx]
            _convert_sample(
                sample,
                idx,
                chunk_dir,
                image_column,
                image_format,
                stats,
            )

        logger.info(
            f"Chunk {chunk_idx + 1} complete: {end_idx - start_idx} images processed"
        )


def _decode_image_data(
    image_data: Any,
    idx: int,
) -> Image.Image | None:
    """Decode image data from various formats to a PIL Image.

    Args:
        image_data: Image data in any supported format (PIL Image, str, bytes, dict).
        idx: Sample index for error reporting.

    Returns:
        PIL Image, or None if decoding failed.
    """
    if isinstance(image_data, Image.Image):
        return image_data

    if isinstance(image_data, str):
        import base64

        try:
            if image_data.startswith("data:image"):
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
            return Image.open(BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"Failed to decode base64 image at index {idx}: {e}")
            return None

    if isinstance(image_data, bytes):
        return Image.open(BytesIO(image_data))

    if isinstance(image_data, dict) and "bytes" in image_data:
        return Image.open(BytesIO(image_data["bytes"]))

    logger.warning(f"Unknown image data type at index {idx}: {type(image_data)}")
    return None


def _save_image_to_disk(
    image: Image.Image,
    output_path: Path,
    image_format: str,
) -> None:
    """Convert mode if needed and save a PIL Image to disk.

    Args:
        image: PIL Image to save.
        output_path: Destination file path.
        image_format: Output format string (png, jpg, jpeg).
    """
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    save_kwargs: dict[str, Any] = {}
    save_format = image_format.upper()
    if save_format == "JPG":
        save_format = "JPEG"

    if image_format.lower() in ("jpg", "jpeg"):
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True

    image.save(output_path, format=save_format, **save_kwargs)


def _convert_sample(
    sample: dict[str, Any],
    idx: int,
    output_dir: Path,
    image_column: str,
    image_format: str,
    stats: dict[str, Any],
) -> None:
    """Convert a single sample."""
    try:
        image_data = sample.get(image_column)
        if image_data is None:
            logger.warning(f"No image data at index {idx}")
            stats["errors"] += 1
            return

        image = _decode_image_data(image_data, idx)
        if image is None:
            stats["errors"] += 1
            return

        image_id = sample.get("image_id", sample.get("id", idx))
        output_path = output_dir / f"{image_id:08d}.{image_format}"

        if output_path.exists():
            stats["skipped"] += 1
            return

        _save_image_to_disk(image, output_path, image_format)
        stats["converted"] += 1

    except Exception as e:
        logger.error(f"Error converting sample {idx}: {e}")
        stats["errors"] += 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert HuggingFace parquet datasets to images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=list(DATASET_CONFIGS.keys()),
        help="Dataset to convert",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default from config)",
    )
    parser.add_argument(
        "--format",
        choices=["png", "jpg", "jpeg"],
        help="Output image format (default from config)",
    )
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="Process in chunks (for large datasets >100K images)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50000,
        help="Images per chunk (default: 50000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze dataset without converting",
    )

    args = parser.parse_args()

    stats = convert_dataset_to_images(
        dataset_name=args.dataset,
        output_dir=args.output,
        image_format=args.format,
        chunked=args.chunked,
        chunk_size=args.chunk_size,
        workers=args.workers,
        dry_run=args.dry_run,
    )

    if "error" in stats:
        logger.error(f"Conversion failed: {stats['error']}")
        return 1

    logger.info(f"Final stats: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
