#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Audit layout labels across the metadata registry.

Scans all dataset metadata and generates a comprehensive report covering:
1. How many datasets have layout labels (and which don't)
2. What source schemas are represented
3. Per-dataset breakdown: schema, class distribution, avg elements/page
4. Cross-dataset canonical class coverage matrix
5. What % can be losslessly converted to DocLayNet
6. Inconsistencies (same dataset using multiple schemas)

Usage:
    # Generate audit report to stdout
    python scripts/audit_layout_labels.py \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json

    # Save report to file
    python scripts/audit_layout_labels.py \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --output report.txt

    # Verbose mode with debug logging
    python scripts/audit_layout_labels.py \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DatasetStats:
    """Statistics for a single dataset's layout labels.

    Attributes:
        dataset: Dataset name.
        total_files: Total metadata JSON files scanned.
        files_with_layout: Files that contain layout_detections.
        total_detections: Total bounding box annotations.
        class_counts: Counter of class_name values.
        canonical_counts: Counter of canonical_class values (if present).
        source_schemas: Set of source_schema values found.
        has_canonical: Whether canonical_class fields are populated.
        lossy_count: Number of detections flagged as lossy.
        lossless_count: Number of detections not flagged as lossy.
        detection_sources: Counter of detection source fields.
        errors: List of error descriptions.
    """

    dataset: str
    total_files: int = 0
    files_with_layout: int = 0
    total_detections: int = 0
    class_counts: Counter = field(default_factory=Counter)
    canonical_counts: Counter = field(default_factory=Counter)
    source_schemas: set[str] = field(default_factory=set)
    has_canonical: bool = False
    lossy_count: int = 0
    lossless_count: int = 0
    detection_sources: Counter = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)

    @property
    def avg_elements_per_page(self) -> float:
        """Average layout elements per page with detections."""
        if self.files_with_layout == 0:
            return 0.0
        return self.total_detections / self.files_with_layout

    @property
    def top_classes(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Return the top N most common classes."""
        return self.class_counts.most_common(top_n)

    @property
    def schema_label(self) -> str:
        """Concise schema label for reporting."""
        schemas = sorted(self.source_schemas)
        if not schemas:
            return "(auto-detect needed)"
        if len(schemas) == 1:
            return schemas[0]
        return f"MIXED: {', '.join(schemas)}"


@dataclass
class AuditReport:
    """Complete audit report across all datasets.

    Attributes:
        dataset_stats: Per-dataset statistics.
        datasets_without_layout: Datasets with no layout labels.
        total_datasets: Total datasets scanned.
    """

    dataset_stats: list[DatasetStats] = field(default_factory=list)
    datasets_without_layout: list[str] = field(default_factory=list)
    total_datasets: int = 0


# ---------------------------------------------------------------------------
# Metadata scanning
# ---------------------------------------------------------------------------


def _get_latest_enrichment_data(
    record: dict[str, Any],
) -> dict[str, Any] | None:
    """Get the latest enrichment version data from a metadata record.

    Args:
        record: Full metadata JSON record.

    Returns:
        The enrichment data dict from the latest version, or None.
    """
    versions = record.get("enrichment_versions", [])
    if not versions:
        return None

    current_ver = record.get("current_version", len(versions))
    for ver in versions:
        if ver.get("version") == current_ver:
            return ver.get("data")

    return versions[-1].get("data") if versions else None


def scan_dataset(
    dataset_dir: Path,
    dataset_name: str,
) -> DatasetStats:
    """Scan a single dataset directory for layout label statistics.

    Args:
        dataset_dir: Path to the dataset metadata directory.
        dataset_name: Name of the dataset.

    Returns:
        DatasetStats with aggregated statistics.
    """
    stats = DatasetStats(dataset=dataset_name)

    json_files = sorted(dataset_dir.glob("*.json"))
    stats.total_files = len(json_files)

    for json_path in json_files:
        try:
            with open(json_path, encoding="utf-8") as fh:
                record = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            stats.errors.append(f"Failed to read {json_path.name}: {exc}")
            continue

        enrichment = _get_latest_enrichment_data(record)
        if enrichment is None:
            continue

        detections = enrichment.get("layout_detections")
        if not detections:
            continue

        stats.files_with_layout += 1
        stats.total_detections += len(detections)

        for det in detections:
            class_name = det.get("class_name", "")
            if class_name:
                stats.class_counts[class_name] += 1

            canonical = det.get("canonical_class")
            if canonical:
                stats.has_canonical = True
                stats.canonical_counts[canonical] += 1

            source_schema = det.get("source_schema")
            if source_schema:
                stats.source_schemas.add(source_schema)

            is_lossy = det.get("is_lossy")
            if is_lossy is True:
                stats.lossy_count += 1
            elif is_lossy is False:
                stats.lossless_count += 1

            source = det.get("source", "")
            if source:
                stats.detection_sources[source] += 1

    return stats


def run_audit(metadata_dir: Path) -> AuditReport:
    """Run the full audit across all datasets in the registry.

    Args:
        metadata_dir: Root metadata registry directory.

    Returns:
        Complete AuditReport.
    """
    report = AuditReport()

    if not metadata_dir.is_dir():
        log.error("metadata_dir_not_found", path=str(metadata_dir))
        return report

    dataset_dirs = sorted(
        d for d in metadata_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    report.total_datasets = len(dataset_dirs)

    for dataset_dir in dataset_dirs:
        ds_name = dataset_dir.name
        log.info("scanning_dataset", dataset=ds_name)

        stats = scan_dataset(dataset_dir, ds_name)

        if stats.files_with_layout > 0:
            report.dataset_stats.append(stats)
        else:
            report.datasets_without_layout.append(ds_name)

    return report


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def _format_class_distribution(
    counts: Counter,
    total: int,
    top_n: int = 5,
) -> str:
    """Format a class distribution as a compact string.

    Args:
        counts: Counter of class names.
        total: Total count for percentage calculation.
        top_n: Number of top classes to show.

    Returns:
        Formatted string like "Text(45%), Title(12%), Table(8%)".
    """
    if not counts or total == 0:
        return "(none)"

    parts = []
    for cls, count in counts.most_common(top_n):
        pct = (count / total) * 100
        parts.append(f"{cls}({pct:.0f}%)")
    return ", ".join(parts)


def _build_coverage_matrix(
    dataset_stats: list[DatasetStats],
) -> dict[str, list[str]]:
    """Build canonical class -> datasets coverage mapping.

    Args:
        dataset_stats: List of per-dataset statistics.

    Returns:
        Dict mapping canonical class name to list of dataset names.
    """
    coverage: dict[str, list[str]] = defaultdict(list)

    for stats in dataset_stats:
        # Use canonical_counts if available, otherwise class_counts
        source = stats.canonical_counts if stats.has_canonical else stats.class_counts
        for cls in source:
            coverage[cls].append(stats.dataset)

    return dict(coverage)


def format_report(report: AuditReport) -> str:
    """Format the complete audit report as a readable string.

    Args:
        report: Complete AuditReport from run_audit().

    Returns:
        Multi-line formatted report string.
    """
    lines: list[str] = []

    # Header
    lines.append("Layout Label Audit Report")
    lines.append("=" * 60)
    lines.append("")

    datasets_with = len(report.dataset_stats)
    datasets_without = len(report.datasets_without_layout)
    total = report.total_datasets
    pct = (datasets_with / total * 100) if total > 0 else 0

    total_images = sum(s.files_with_layout for s in report.dataset_stats)
    total_annotations = sum(s.total_detections for s in report.dataset_stats)

    lines.append(
        f"Datasets with layout labels:    {datasets_with}/{total} ({pct:.1f}%)"
    )
    lines.append(f"Total images with detections:   ~{total_images:,}")
    lines.append(
        f"Total layout annotations:       ~{total_annotations:,} bounding boxes"
    )

    # Schema Distribution
    lines.append("")
    lines.append("Schema Distribution:")
    lines.append("-" * 40)

    schema_datasets: dict[str, list[DatasetStats]] = defaultdict(list)
    for stats in report.dataset_stats:
        label = stats.schema_label
        schema_datasets[label].append(stats)

    # Also count datasets with no schema detected
    no_schema_stats = [
        s for s in report.dataset_stats if not s.source_schemas and not s.has_canonical
    ]

    for schema_label, ds_list in sorted(schema_datasets.items()):
        ds_count = len(ds_list)
        img_count = sum(s.files_with_layout for s in ds_list)
        # Count unique classes in this schema
        all_classes: set[str] = set()
        for stats in ds_list:
            all_classes.update(stats.class_counts.keys())
        lines.append(
            f"  {schema_label:30s} "
            f"{ds_count} dataset(s), "
            f"{img_count:,} images, "
            f"{len(all_classes)} unique classes"
        )

    if no_schema_stats:
        lines.append(
            f"  {'(no schema detected)':30s} {len(no_schema_stats)} dataset(s)"
        )

    lines.append(f"  {'(none)':30s} {datasets_without} dataset(s)")

    # Per-Dataset Breakdown
    lines.append("")
    lines.append("Per-Dataset Breakdown:")
    lines.append("-" * 100)

    # Header row
    lines.append(
        f"  {'Dataset':<20s} | {'Schema':<18s} | "
        f"{'Images':>8s} | {'Avg Elem':>8s} | Top Classes"
    )
    lines.append(f"  {'-' * 20}-+-{'-' * 18}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 30}")

    for stats in sorted(
        report.dataset_stats,
        key=lambda s: s.files_with_layout,
        reverse=True,
    ):
        top_cls = _format_class_distribution(stats.class_counts, stats.total_detections)
        lines.append(
            f"  {stats.dataset:<20s} | "
            f"{stats.schema_label:<18s} | "
            f"{stats.files_with_layout:>8,} | "
            f"{stats.avg_elements_per_page:>8.1f} | "
            f"{top_cls}"
        )

    # Canonical Coverage Matrix
    coverage = _build_coverage_matrix(report.dataset_stats)
    if coverage:
        lines.append("")
        lines.append("Canonical Coverage (classes present across datasets):")
        lines.append("-" * 60)

        for cls, ds_names in sorted(
            coverage.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        ):
            lines.append(
                f"  {cls:<25s} {len(ds_names):>2} dataset(s): "
                f"{', '.join(sorted(ds_names))}"
            )

    # Lossless DocLayNet Conversion
    standardized_stats = [s for s in report.dataset_stats if s.has_canonical]
    if standardized_stats:
        lines.append("")
        lines.append("Lossless DocLayNet Conversion:")
        lines.append("-" * 60)

        for stats in sorted(
            standardized_stats,
            key=lambda s: s.lossless_count,
            reverse=True,
        ):
            total_classified = stats.lossless_count + stats.lossy_count
            if total_classified == 0:
                continue
            lossless_pct = stats.lossless_count / total_classified * 100
            lines.append(
                f"  {stats.dataset:<20s} "
                f"{lossless_pct:5.1f}% lossless "
                f"({stats.lossless_count:,} lossless, "
                f"{stats.lossy_count:,} lossy)"
            )

    # Inconsistencies
    inconsistent = [s for s in report.dataset_stats if len(s.source_schemas) > 1]
    if inconsistent:
        lines.append("")
        lines.append("Inconsistencies (multiple schemas in same dataset):")
        lines.append("-" * 60)
        for stats in inconsistent:
            lines.append(f"  {stats.dataset}: schemas = {sorted(stats.source_schemas)}")

    # Datasets WITHOUT layout labels
    if report.datasets_without_layout:
        lines.append("")
        lines.append(
            f"Datasets WITHOUT layout labels ({len(report.datasets_without_layout)}):"
        )
        lines.append("-" * 60)
        # Wrap at ~4 names per line
        chunk_size = 4
        names = sorted(report.datasets_without_layout)
        for i in range(0, len(names), chunk_size):
            chunk = names[i : i + chunk_size]
            lines.append(f"  {', '.join(chunk)}")

    # Errors
    all_errors = []
    for stats in report.dataset_stats:
        for err in stats.errors:
            all_errors.append(f"{stats.dataset}: {err}")

    if all_errors:
        lines.append("")
        lines.append(f"Errors ({len(all_errors)}):")
        lines.append("-" * 60)
        for err in all_errors[:20]:
            lines.append(f"  - {err}")
        if len(all_errors) > 20:
            lines.append(f"  ... and {len(all_errors) - 20} more")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit layout labels across the metadata registry. "
            "Generates a comprehensive report of label coverage, "
            "schema distribution, and conversion quality."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Print report to stdout\n"
            "  python scripts/audit_layout_labels.py \\\n"
            "      --metadata-dir /mnt/e/image_detection/"
            "metadata_registry/json\n\n"
            "  # Save report to file\n"
            "  python scripts/audit_layout_labels.py \\\n"
            "      --metadata-dir /mnt/e/image_detection/"
            "metadata_registry/json \\\n"
            "      --output report.txt"
        ),
    )

    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Root metadata registry directory (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report to file instead of stdout.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Audit a single dataset only (optional).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )

    return parser


def main() -> int:
    """Run the layout label audit.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging_level=10),
        )

    metadata_dir: Path = args.metadata_dir
    if not metadata_dir.is_dir():
        print(
            f"ERROR: Metadata directory not found: {metadata_dir}",
            file=sys.stderr,
        )
        return 1

    # If single dataset mode, create a temporary subdirectory scope
    if args.dataset:
        dataset_dir = metadata_dir / args.dataset
        if not dataset_dir.is_dir():
            print(
                f"ERROR: Dataset directory not found: {dataset_dir}",
                file=sys.stderr,
            )
            return 1

        log.info(
            "auditing_single_dataset",
            dataset=args.dataset,
        )
        stats = scan_dataset(dataset_dir, args.dataset)

        # Build a minimal report for single dataset
        report = AuditReport(total_datasets=1)
        if stats.files_with_layout > 0:
            report.dataset_stats.append(stats)
        else:
            report.datasets_without_layout.append(args.dataset)
    else:
        log.info("auditing_all_datasets", dir=str(metadata_dir))
        report = run_audit(metadata_dir)

    # Format and output
    report_text = format_report(report)

    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report_text)
            print(f"Report written to {args.output}")
        except OSError as exc:
            print(
                f"ERROR: Failed to write report: {exc}",
                file=sys.stderr,
            )
            return 1
    else:
        print(report_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
