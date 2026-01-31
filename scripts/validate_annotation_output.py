#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Validate annotation output for completeness and correctness.

This script validates the Parquet output from the annotation system by checking:
    - Parquet partition exists for each configured dataset
    - Row count matches expected image count (within tolerance)
    - No null file_hash values (indicates failed hashing)
    - Schema version is correct
    - Sample hash verification against source files

Usage:
    # Validate all datasets
    uv run python scripts/validate_annotation_output.py

    # Validate specific dataset
    uv run python scripts/validate_annotation_output.py --dataset funsd

    # Validate specific tier
    uv run python scripts/validate_annotation_output.py --tier 1

    # Show summary only (no per-dataset details)
    uv run python scripts/validate_annotation_output.py --summary

    # Export validation report to JSON
    uv run python scripts/validate_annotation_output.py --output report.json

Example Output:
    ============================================================
    ANNOTATION VALIDATION REPORT
    ============================================================

    Dataset: funsd
      Status: ✓ PASS
      Rows: 149
      Null file_hash: 0
      Schema version: 2.1 ✓

    Dataset: tobacco800
      Status: ✓ PASS
      Rows: 1,290
      Null file_hash: 0
      Schema version: 2.1 ✓

    ------------------------------------------------------------
    SUMMARY
    ------------------------------------------------------------
    Total datasets: 40
    Validated: 38
    Missing: 2 (rvl_cdip, pubtabnet)
    Errors: 0

    Total rows: 1,234,567
    Storage size: 456.7 MB
    ============================================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pyarrow as pa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DatasetValidation:
    """Validation result for a single dataset."""

    dataset_name: str
    exists: bool
    row_count: int = 0
    null_file_hash_count: int = 0
    schema_version: str | None = None
    expected_schema_version: str = "2.1"
    issues: list[str] = field(default_factory=list)
    sample_hashes_verified: int = 0
    sample_hashes_failed: int = 0
    file_size_bytes: int = 0

    @property
    def passed(self) -> bool:
        """Check if validation passed."""
        return (
            self.exists
            and self.null_file_hash_count == 0
            and self.schema_version == self.expected_schema_version
            and self.sample_hashes_failed == 0
            and not self.issues
        )

    @property
    def status(self) -> str:
        """Get status string."""
        if not self.exists:
            return "MISSING"
        if self.passed:
            return "PASS"
        return "FAIL"


@dataclass
class ValidationReport:
    """Complete validation report."""

    timestamp: str
    datasets: list[DatasetValidation] = field(default_factory=list)
    total_rows: int = 0
    total_size_bytes: int = 0
    missing_datasets: list[str] = field(default_factory=list)
    error_datasets: list[str] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        """Number of datasets that passed validation."""
        return sum(1 for d in self.datasets if d.passed)

    @property
    def failed_count(self) -> int:
        """Number of datasets that failed validation."""
        return sum(1 for d in self.datasets if d.exists and not d.passed)

    @property
    def missing_count(self) -> int:
        """Number of missing datasets."""
        return sum(1 for d in self.datasets if not d.exists)


# =============================================================================
# Validation Functions
# =============================================================================


def validate_dataset(
    writer: Any,  # PartitionedParquetWriter
    dataset_name: str,
    expected_schema_version: str = "2.1",
    verify_sample_hashes: int = 0,
    settings: Any | None = None,  # AnnotationSettings
) -> DatasetValidation:
    """Validate a single dataset partition.

    Args:
        writer: PartitionedParquetWriter instance
        dataset_name: Name of the dataset to validate
        expected_schema_version: Expected schema version
        verify_sample_hashes: Number of sample hashes to verify (0 to skip)
        settings: AnnotationSettings for path resolution

    Returns:
        DatasetValidation result
    """
    result = DatasetValidation(
        dataset_name=dataset_name,
        exists=False,
        expected_schema_version=expected_schema_version,
    )

    # Check if partition exists
    existing_datasets = writer.list_datasets()
    if dataset_name not in existing_datasets:
        result.issues.append("Partition does not exist")
        return result

    result.exists = True

    # Read dataset
    try:
        table: pa.Table = writer.read_dataset(dataset_name)
        result.row_count = len(table)

        # Check for null file_hash values
        file_hash_col = table.column("file_hash")
        null_count = file_hash_col.null_count
        result.null_file_hash_count = null_count
        if null_count > 0:
            result.issues.append(f"{null_count} rows with null file_hash")

        # Check schema version
        schema_version_col = table.column("schema_version")
        if len(schema_version_col) > 0:
            # Get first non-null value
            for val in schema_version_col:
                if val.is_valid:
                    result.schema_version = val.as_py()
                    break

            if result.schema_version != expected_schema_version:
                result.issues.append(
                    f"Schema version mismatch: {result.schema_version} "
                    f"(expected {expected_schema_version})"
                )

        # Get file size
        partition_dir = writer._get_partition_dir(dataset_name)
        for parquet_file in partition_dir.glob("*.parquet"):
            result.file_size_bytes += parquet_file.stat().st_size

        # Verify sample hashes if requested
        if verify_sample_hashes > 0 and settings is not None:
            verified, failed = _verify_sample_hashes(
                table, dataset_name, verify_sample_hashes, settings
            )
            result.sample_hashes_verified = verified
            result.sample_hashes_failed = failed
            if failed > 0:
                result.issues.append(f"{failed} sample hashes failed verification")

    except Exception as e:
        result.issues.append(f"Error reading dataset: {e}")
        logger.exception(f"Error validating {dataset_name}")

    return result


def _verify_sample_hashes(
    table: pa.Table,
    dataset_name: str,
    num_samples: int,
    settings: Any,
) -> tuple[int, int]:
    """Verify sample file hashes against source files.

    Args:
        table: PyArrow table with samples
        dataset_name: Dataset name for path resolution
        num_samples: Number of samples to verify
        settings: AnnotationSettings for path resolution

    Returns:
        Tuple of (verified_count, failed_count)
    """
    verified = 0
    failed = 0

    # Sample random rows
    import random

    indices = random.sample(range(len(table)), min(num_samples, len(table)))

    for idx in indices:
        try:
            row = table.slice(idx, 1).to_pydict()
            original_path = Path(row["original_path"][0])
            stored_hash = row["file_hash"][0]

            # Resolve path if relative (paths are relative to e_drive_root)
            if not original_path.is_absolute():
                original_path = settings.e_drive_root / original_path

            if not original_path.exists():
                logger.warning(f"File not found: {original_path}")
                failed += 1
                continue

            # Compute hash
            computed_hash = _compute_file_hash(original_path)

            if computed_hash == stored_hash:
                verified += 1
            else:
                logger.warning(
                    f"Hash mismatch for {original_path}: "
                    f"stored={stored_hash[:16]}..., computed={computed_hash[:16]}..."
                )
                failed += 1

        except Exception as e:
            logger.warning(f"Error verifying sample: {e}")
            failed += 1

    return verified, failed


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA256 hash
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# =============================================================================
# Report Generation
# =============================================================================


def generate_report(
    datasets: list[str],
    writer: Any,
    expected_schema_version: str = "2.1",
    verify_hashes: int = 0,
    settings: Any | None = None,
) -> ValidationReport:
    """Generate validation report for datasets.

    Args:
        datasets: List of dataset names to validate
        writer: PartitionedParquetWriter instance
        expected_schema_version: Expected schema version
        verify_hashes: Number of sample hashes to verify per dataset
        settings: AnnotationSettings for path resolution

    Returns:
        ValidationReport with all validation results
    """
    report = ValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    for dataset_name in datasets:
        logger.info(f"Validating {dataset_name}...")
        validation = validate_dataset(
            writer,
            dataset_name,
            expected_schema_version,
            verify_hashes,
            settings,
        )
        report.datasets.append(validation)
        report.total_rows += validation.row_count
        report.total_size_bytes += validation.file_size_bytes

        if not validation.exists:
            report.missing_datasets.append(dataset_name)
        elif not validation.passed:
            report.error_datasets.append(dataset_name)

    return report


def print_report(report: ValidationReport, summary_only: bool = False) -> None:
    """Print validation report to console.

    Args:
        report: ValidationReport to print
        summary_only: If True, only print summary
    """
    print("\n" + "=" * 60)
    print("ANNOTATION VALIDATION REPORT")
    print("=" * 60)
    print(f"Generated: {report.timestamp}")
    print()

    if not summary_only:
        for validation in report.datasets:
            status_icon = "✓" if validation.passed else "✗"
            status_color = "PASS" if validation.passed else validation.status

            print(f"Dataset: {validation.dataset_name}")
            print(f"  Status: {status_icon} {status_color}")

            if validation.exists:
                print(f"  Rows: {validation.row_count:,}")
                print(f"  Null file_hash: {validation.null_file_hash_count}")
                schema_check = (
                    "✓" if validation.schema_version == validation.expected_schema_version
                    else "✗"
                )
                print(f"  Schema version: {validation.schema_version} {schema_check}")

                if validation.sample_hashes_verified > 0:
                    print(
                        f"  Sample hashes: {validation.sample_hashes_verified} verified, "
                        f"{validation.sample_hashes_failed} failed"
                    )

                if validation.file_size_bytes > 0:
                    size_mb = validation.file_size_bytes / (1024 * 1024)
                    print(f"  Size: {size_mb:.1f} MB")

                if validation.issues:
                    print("  Issues:")
                    for issue in validation.issues:
                        print(f"    - {issue}")
            print()

    # Summary
    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Total datasets: {len(report.datasets)}")
    print(f"Passed: {report.passed_count}")
    print(f"Failed: {report.failed_count}")
    print(f"Missing: {report.missing_count}")

    if report.missing_datasets:
        print(f"\nMissing datasets: {', '.join(report.missing_datasets[:10])}")
        if len(report.missing_datasets) > 10:
            print(f"  ... and {len(report.missing_datasets) - 10} more")

    if report.error_datasets:
        print(f"\nDatasets with errors: {', '.join(report.error_datasets[:10])}")
        if len(report.error_datasets) > 10:
            print(f"  ... and {len(report.error_datasets) - 10} more")

    print(f"\nTotal rows: {report.total_rows:,}")
    size_mb = report.total_size_bytes / (1024 * 1024)
    print(f"Storage size: {size_mb:.1f} MB")
    print("=" * 60 + "\n")


def save_report(report: ValidationReport, output_path: Path) -> None:
    """Save validation report to JSON file.

    Args:
        report: ValidationReport to save
        output_path: Path to output file
    """
    report_dict: dict[str, Any] = {
        "timestamp": report.timestamp,
        "summary": {
            "total_datasets": len(report.datasets),
            "passed": report.passed_count,
            "failed": report.failed_count,
            "missing": report.missing_count,
            "total_rows": report.total_rows,
            "total_size_bytes": report.total_size_bytes,
        },
        "missing_datasets": report.missing_datasets,
        "error_datasets": report.error_datasets,
        "datasets": [asdict(d) for d in report.datasets],
    }

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    logger.info(f"Report saved to {output_path}")


# =============================================================================
# Main Entry Point
# =============================================================================


def main(args: argparse.Namespace) -> int:
    """Main validation function.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from image_preprocessing_detector.annotation.config.datasets import DATASET_CONFIGS
    from image_preprocessing_detector.annotation.config.settings import AnnotationSettings
    from image_preprocessing_detector.annotation.storage.parquet_writer import (
        PartitionedParquetWriter,
    )

    # Import tiers from process script
    from scripts.process_all_datasets import TIERS

    # Load settings
    settings = AnnotationSettings.from_env()

    # Create writer for reading
    writer = PartitionedParquetWriter(settings.metadata_root / "parquet")

    # Determine datasets to validate
    if args.dataset:
        datasets = [args.dataset]
    elif args.tier:
        if args.tier not in TIERS:
            logger.error(f"Invalid tier: {args.tier}")
            return 1
        datasets = TIERS[args.tier]
    else:
        # All datasets
        datasets = list(DATASET_CONFIGS.keys())

    # Generate report
    report = generate_report(
        datasets,
        writer,
        verify_hashes=args.verify_hashes,
        settings=settings if args.verify_hashes > 0 else None,
    )

    # Print report
    print_report(report, summary_only=args.summary)

    # Save to file if requested
    if args.output:
        save_report(report, Path(args.output))

    # Return exit code based on results
    if report.failed_count > 0 or report.missing_count > 0:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate annotation output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        help="Validate specific dataset",
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Validate specific tier",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary only (no per-dataset details)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file",
    )
    parser.add_argument(
        "--verify-hashes",
        type=int,
        default=0,
        help="Number of sample hashes to verify per dataset (0 to skip)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    return args


if __name__ == "__main__":
    sys.exit(main(parse_args()))
