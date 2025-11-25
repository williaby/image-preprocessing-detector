# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Extract representative test fixtures from benchmark datasets.

This script intelligently samples diverse documents from benchmark datasets
to create a small (<50MB) test fixture set for CI/CD testing.

Usage:
    poetry run python scripts/extract_test_fixtures.py --dataset doclaynet --count 5
    poetry run python scripts/extract_test_fixtures.py --all
    poetry run python scripts/extract_test_fixtures.py --dataset tablebank --criteria "complex,rotated"
"""

import argparse
import json
import random  # nosec B311 - used for non-cryptographic dataset sampling
import shutil
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"
FIXTURES_DIR = PROJECT_ROOT / "data" / "test_fixtures"

# Size constraints
MAX_TOTAL_SIZE_MB = 50
MB_TO_BYTES = 1024 * 1024

# Dataset-specific configurations
DATASET_CONFIGS = {
    "doclaynet": {
        "source_dir": BENCHMARKS_DIR / "doclaynet",
        "target_dir": FIXTURES_DIR / "doclaynet",
        "extensions": [".pdf"],
        "count": 5,
        "max_size_mb": 10,
        "criteria": [
            "simple_text",
            "tables_figures",
            "multi_column",
            "skewed",
            "low_contrast",
        ],
    },
    "tablebank": {
        "source_dir": BENCHMARKS_DIR / "tablebank",
        "target_dir": FIXTURES_DIR / "tablebank",
        "extensions": [".jpg", ".png"],
        "count": 5,
        "max_size_mb": 5,
        "criteria": [
            "simple_table",
            "complex_table",
            "rotated",
            "low_quality",
            "embedded_graphics",
        ],
    },
    "cocotext": {
        "source_dir": BENCHMARKS_DIR / "cocotext",
        "target_dir": FIXTURES_DIR / "cocotext",
        "extensions": [".jpg", ".png"],
        "count": 5,
        "max_size_mb": 3,
        "criteria": [
            "dense_text",
            "sparse_text",
            "varied_fonts",
            "handwritten",
            "low_contrast",
        ],
    },
    "wili_2018": {
        "source_dir": BENCHMARKS_DIR / "wili_2018",
        "target_dir": FIXTURES_DIR / "wili_2018",
        "extensions": [".txt"],
        "count": 10,
        "max_size_mb": 0.1,
        "criteria": ["en", "fr", "de", "es", "zh", "ar", "ru", "ja", "ko", "hi"],
    },
    "omnidocbench": {
        "source_dir": BENCHMARKS_DIR / "omnidocbench",
        "target_dir": FIXTURES_DIR / "omnidocbench",
        "extensions": [".jpg", ".png", ".pdf"],
        "count": 5,
        "max_size_mb": 10,
        "criteria": [
            "financial",
            "scientific",
            "invoice",
            "form_handwriting",
            "mixed_media",
        ],
    },
}


def get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    return path.stat().st_size / MB_TO_BYTES


def find_files_by_extension(directory: Path, extensions: list[str]) -> list[Path]:
    """Recursively find files with given extensions."""
    files = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    return files


def _filter_files_by_size(
    files: list[Path], max_individual_size_mb: float
) -> list[tuple[Path, float]]:
    """Filter and sort files by size.

    Args:
        files: List of file paths
        max_individual_size_mb: Maximum size per file in MB

    Returns:
        List of (path, size_mb) tuples sorted by size
    """
    files_with_size = [(f, get_file_size_mb(f)) for f in files]
    files_with_size.sort(key=lambda x: x[1])
    return [(f, s) for f, s in files_with_size if s <= max_individual_size_mb]


def _sample_from_quartiles(
    files_with_size: list[tuple[Path, float]], count: int, max_size_mb: float
) -> tuple[list[Path], float]:
    """Sample one file from each size quartile for diversity.

    Args:
        files_with_size: List of (path, size_mb) tuples
        count: Target number of files
        max_size_mb: Maximum total size

    Returns:
        Tuple of (sampled_paths, total_size)
    """
    quartile_size = len(files_with_size) // 4 if len(files_with_size) >= 4 else 1
    sampled: list[Path] = []
    total_size = 0.0

    for i in range(min(count, 4)):
        start_idx = i * quartile_size
        end_idx = (i + 1) * quartile_size if i < 3 else len(files_with_size)

        if start_idx >= len(files_with_size):
            break

        quartile_files = files_with_size[start_idx:end_idx]
        if not quartile_files:
            continue

        # nosec B311 - random used for non-cryptographic dataset sampling
        file_path, file_size = random.choice(quartile_files)  # nosec B311
        if total_size + file_size <= max_size_mb:
            sampled.append(file_path)
            total_size += file_size

    return sampled, total_size


def _fill_remaining_samples(
    files_with_size: list[tuple[Path, float]],
    sampled: list[Path],
    count: int,
    total_size: float,
    max_size_mb: float,
) -> tuple[list[Path], float]:
    """Fill remaining slots with random samples.

    Args:
        files_with_size: List of (path, size_mb) tuples
        sampled: Already sampled paths
        count: Target total count
        total_size: Current total size
        max_size_mb: Maximum total size

    Returns:
        Tuple of (updated_sampled, updated_total_size)
    """
    remaining = [(f, s) for f, s in files_with_size if f not in sampled]

    while len(sampled) < count and remaining:
        # nosec B311 - random used for non-cryptographic dataset sampling
        file_path, file_size = random.choice(remaining)  # nosec B311
        if total_size + file_size > max_size_mb:
            break
        sampled.append(file_path)
        total_size += file_size
        remaining.remove((file_path, file_size))

    return sampled, total_size


def sample_diverse_files(
    files: list[Path],
    count: int,
    max_size_mb: float,
    _criteria: list[str] | None = None,
) -> list[Path]:
    """Sample diverse files based on size distribution.

    Strategy:
    1. Sort files by size (prefer smaller files for fixtures)
    2. Sample from different size buckets for diversity
    3. Ensure total size < max_size_mb

    Args:
        files: List of candidate file paths
        count: Number of files to sample
        max_size_mb: Maximum total size in MB
        _criteria: Optional filtering criteria (reserved for future use)

    Returns:
        List of sampled file paths
    """
    if not files:
        return []

    max_individual_size_mb = max_size_mb / count
    files_with_size = _filter_files_by_size(files, max_individual_size_mb)

    if not files_with_size:
        logger.warning(
            "no_suitable_files",
            max_individual_size_mb=max_individual_size_mb,
            total_files=len(files),
        )
        return []

    sampled, total_size = _sample_from_quartiles(files_with_size, count, max_size_mb)
    sampled, total_size = _fill_remaining_samples(
        files_with_size, sampled, count, total_size, max_size_mb
    )

    logger.info(
        "sampled_files",
        count=len(sampled),
        total_size_mb=round(total_size, 2),
        max_size_mb=max_size_mb,
    )

    return sampled


def extract_fixtures_for_dataset(
    dataset: str,
    count: int | None = None,
    criteria: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, any]:
    """
    Extract test fixtures for a specific dataset.

    Args:
        dataset: Dataset name (doclaynet, tablebank, etc.)
        count: Number of files to extract (overrides config default)
        criteria: Optional filtering criteria
        dry_run: If True, only simulate extraction

    Returns:
        Dict with extraction results
    """
    if dataset not in DATASET_CONFIGS:
        raise ValueError(
            f"Unknown dataset: {dataset}. "
            f"Available: {', '.join(DATASET_CONFIGS.keys())}"
        )

    config = DATASET_CONFIGS[dataset]
    source_dir = config["source_dir"]
    target_dir = config["target_dir"]
    extensions = config["extensions"]
    file_count = count or config["count"]
    max_size_mb = config["max_size_mb"]

    logger.info(
        "extracting_fixtures",
        dataset=dataset,
        source_dir=str(source_dir),
        target_dir=str(target_dir),
        count=file_count,
        max_size_mb=max_size_mb,
    )

    # Check source directory exists
    if not source_dir.exists():
        logger.error("source_dir_not_found", source_dir=str(source_dir))
        return {
            "dataset": dataset,
            "status": "error",
            "message": f"Source directory not found: {source_dir}",
            "extracted": 0,
        }

    # Find candidate files
    candidate_files = find_files_by_extension(source_dir, extensions)
    logger.info("found_candidate_files", count=len(candidate_files))

    if not candidate_files:
        logger.warning("no_candidate_files", dataset=dataset)
        return {
            "dataset": dataset,
            "status": "warning",
            "message": "No candidate files found",
            "extracted": 0,
        }

    # Sample diverse files
    sampled_files = sample_diverse_files(
        candidate_files, file_count, max_size_mb, criteria
    )

    if not sampled_files:
        return {
            "dataset": dataset,
            "status": "warning",
            "message": "No suitable files found within size constraints",
            "extracted": 0,
        }

    # Extract files
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = {
            "dataset": dataset,
            "extracted_at": "2025-11-13",
            "count": len(sampled_files),
            "files": [],
        }

        for idx, source_file in enumerate(sampled_files, 1):
            # Create descriptive filename
            criterion_name = (
                config["criteria"][idx - 1]
                if idx <= len(config["criteria"])
                else f"sample_{idx}"
            )
            target_filename = f"{criterion_name}_{idx}{source_file.suffix}"
            target_path = target_dir / target_filename

            # Copy file
            shutil.copy2(source_file, target_path)

            file_size_mb = get_file_size_mb(target_path)
            logger.info(
                "extracted_file",
                source=source_file.name,
                target=target_filename,
                size_mb=round(file_size_mb, 2),
            )

            manifest["files"].append(
                {
                    "name": target_filename,
                    "source": str(source_file),
                    "size_mb": round(file_size_mb, 2),
                    "criterion": criterion_name,
                }
            )

        # Write manifest
        manifest_path = target_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(
            "extraction_complete",
            dataset=dataset,
            extracted=len(sampled_files),
            manifest=str(manifest_path),
        )

    return {
        "dataset": dataset,
        "status": "success",
        "extracted": len(sampled_files),
        "total_size_mb": round(sum(get_file_size_mb(f) for f in sampled_files), 2),
    }


def extract_all_fixtures(dry_run: bool = False) -> dict[str, any]:
    """Extract fixtures for all configured datasets."""
    results = {}
    total_size = 0.0

    for dataset in DATASET_CONFIGS:
        result = extract_fixtures_for_dataset(dataset, dry_run=dry_run)
        results[dataset] = result
        if result["status"] == "success":
            total_size += result.get("total_size_mb", 0)

    logger.info(
        "all_extractions_complete",
        datasets=len(results),
        total_size_mb=round(total_size, 2),
        max_size_mb=MAX_TOTAL_SIZE_MB,
    )

    if total_size > MAX_TOTAL_SIZE_MB:
        logger.warning(
            "size_limit_exceeded",
            total_size_mb=round(total_size, 2),
            max_size_mb=MAX_TOTAL_SIZE_MB,
        )

    return results


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract test fixtures from benchmark datasets"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(DATASET_CONFIGS.keys()),
        help="Specific dataset to extract",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract fixtures for all datasets",
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Number of files to extract (overrides config default)",
    )
    parser.add_argument(
        "--criteria",
        type=str,
        help="Comma-separated criteria for filtering",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate extraction without copying files",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List available datasets and exit",
    )

    args = parser.parse_args()

    # Setup structured logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    # List datasets
    if args.list_datasets:
        print("\nAvailable datasets:")
        for name, config in DATASET_CONFIGS.items():
            print(f"  - {name}: {config['count']} files, max {config['max_size_mb']}MB")
        return

    # Parse criteria
    criteria = None
    if args.criteria:
        criteria = [c.strip() for c in args.criteria.split(",")]

    # Extract fixtures
    if args.all:
        results = extract_all_fixtures(dry_run=args.dry_run)
        print("\nExtraction Summary:")
        for dataset, result in results.items():
            status_icon = "✓" if result["status"] == "success" else "✗"
            print(
                f"  {status_icon} {dataset}: "
                f"{result['extracted']} files, "
                f"{result.get('total_size_mb', 0):.2f} MB"
            )
    elif args.dataset:
        result = extract_fixtures_for_dataset(
            args.dataset,
            count=args.count,
            criteria=criteria,
            dry_run=args.dry_run,
        )
        print(f"\nExtraction result: {result}")
    else:
        parser.print_help()
        print("\nError: Must specify either --dataset or --all")


if __name__ == "__main__":
    main()
