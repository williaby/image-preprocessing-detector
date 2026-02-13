#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""
Generate metadata completeness report across all datasets.

Shows a consolidated view of:
- Record counts per dataset
- Field coverage/completeness percentages
- Missing metadata identification

Usage:
    python scripts/metadata_completeness_report.py
    python scripts/metadata_completeness_report.py --output report.csv
    python scripts/metadata_completeness_report.py --dataset doclaynet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq

# Paths
E_DRIVE_ROOT = Path("/mnt/e/image_detection")
METADATA_ROOT = E_DRIVE_ROOT / "metadata_registry"
SAMPLES_PARQUET = METADATA_ROOT / "samples.parquet"


# Field categories for reporting
FIELD_CATEGORIES = {
    "identity": ["sample_id", "file_hash", "dataset_name", "original_filename"],
    "file_info": ["width_px", "height_px", "file_size_bytes", "dpi", "format"],
    "quality_scores": ["diqa_mos", "ocr_quality_score", "smartdoc_mos"],
    "original_labels": [
        "writer_id",
        "transcription",
        "original_language_code",
        "original_script_name",
    ],
    "enrichment": [
        "enrichment_version",
        "enrichment_tier",
        "enrichment_source",
        "capture_method",
        "capture_confidence",
        "domain_level1",
        "resolution_category",
    ],
    "content_flags": [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_signature",
        "has_figure",
    ],
    "language_script": [
        "iso639_language",
        "iso15924_script",
        "script_family",
        "bcp47_tag",
    ],
    "text_scope": [
        "text_scope",
        "text_scope_content_type",
        "text_scope_estimated_chars",
        "text_scope_estimated_words",
    ],
    "paper_size": [
        "paper_size",
        "paper_size_standard",
        "paper_size_orientation",
    ],
    "dataset_source": ["dataset_short_code"],
    "element_counts": ["table_count", "formula_count"],
    "reproducibility": ["git_sha", "model_checkpoint", "script_version"],
    "annotations": [
        "doclaynet_annotations_json",
        "tablebank_annotations_json",
        "funsd_annotations_json",
        "layout_detections_json",
    ],
}


def load_parquet_as_pandas(parquet_path: Path):
    """Load parquet file into pandas DataFrame."""
    try:
        import importlib

        importlib.import_module("pandas")
        table = pq.read_table(parquet_path)
        return table.to_pandas()
    except ImportError:
        print("pandas not installed. Install with: uv pip install pandas")
        raise


def calculate_field_completeness(df, field: str) -> tuple[int, int, float]:
    """Calculate completeness for a single field.

    Returns:
        Tuple of (non_null_count, total_count, percentage)
    """
    total = len(df)
    if field not in df.columns:
        return 0, total, 0.0

    non_null = df[field].notna().sum()
    percentage = (non_null / total * 100) if total > 0 else 0.0
    return int(non_null), total, percentage


def generate_dataset_summary(df) -> dict:
    """Generate summary statistics per dataset."""
    summary = {}

    for dataset in df["dataset_name"].unique():
        dataset_df = df[df["dataset_name"] == dataset]
        count = len(dataset_df)

        # Calculate completeness for key fields
        field_completeness = {}
        for category, fields in FIELD_CATEGORIES.items():
            category_completeness = {}
            for field in fields:
                non_null, _, pct = calculate_field_completeness(dataset_df, field)
                if pct > 0:  # Only include non-empty fields
                    category_completeness[field] = {
                        "count": non_null,
                        "percentage": round(pct, 1),
                    }
            if category_completeness:
                field_completeness[category] = category_completeness

        summary[dataset] = {
            "record_count": count,
            "field_completeness": field_completeness,
        }

    return summary


def _print_field_completeness_section(df) -> None:
    """Print field completeness overview grouped by category."""
    print("\n" + "-" * 80)
    print("FIELD COMPLETENESS (% of records with non-null values)")
    print("-" * 80)

    for category, fields in FIELD_CATEGORIES.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for field_name in fields:
            non_null, total, pct = calculate_field_completeness(df, field_name)
            bar = "\u2588" * int(pct / 5) + "\u2591" * (20 - int(pct / 5))
            print(f"  {field_name:<35} {bar} {pct:>6.1f}% ({non_null:,}/{total:,})")


def _print_per_dataset_field_coverage(
    df,
    sorted_datasets: list,
    field_names: list[str],
    header_fmt: str,
    row_fmt: str,
    section_title: str,
    max_datasets: int = 0,
) -> None:
    """Print per-dataset field coverage table."""
    print("\n" + "-" * 80)
    print(section_title)
    print("-" * 80)
    print(header_fmt)
    print("-" * 61)

    items = sorted_datasets[:max_datasets] if max_datasets else sorted_datasets
    for dataset, _info in items:
        dataset_df = df[df["dataset_name"] == dataset]
        values = []
        for field_name in field_names:
            _, _, pct = calculate_field_completeness(dataset_df, field_name)
            values.append(f"{pct:>6.1f}%" if pct > 0 else "     -")
        print(row_fmt.format(dataset=dataset, values=values))

    if max_datasets and len(sorted_datasets) > max_datasets:
        print(f"  ... and {len(sorted_datasets) - max_datasets} more datasets")


def print_summary_table(df, summary: dict) -> None:
    """Print formatted summary table."""
    print("\n" + "=" * 80)
    print("METADATA COMPLETENESS REPORT")
    print("=" * 80)

    total_records = len(df)
    print(f"\nTotal Records: {total_records:,}")
    print(f"Total Datasets: {len(summary)}")

    # Dataset breakdown
    print("\n" + "-" * 80)
    print("RECORDS PER DATASET")
    print("-" * 80)
    print(f"{'Dataset':<30} {'Records':>12} {'% of Total':>12}")
    print("-" * 54)

    sorted_datasets = sorted(
        summary.items(), key=lambda x: x[1]["record_count"], reverse=True
    )
    for dataset, info in sorted_datasets:
        pct = info["record_count"] / total_records * 100
        print(f"{dataset:<30} {info['record_count']:>12,} {pct:>11.1f}%")

    _print_field_completeness_section(df)

    # Quality scores coverage
    quality_fields = ["diqa_mos", "ocr_quality_score", "smartdoc_mos"]
    _print_per_dataset_field_coverage(
        df,
        sorted_datasets,
        quality_fields,
        header_fmt=f"{'Dataset':<25} {'DIQA MOS':>12} {'OCR Quality':>12} {'SmartDoc':>12}",
        row_fmt="{dataset:<25} {values[0]:>12} {values[1]:>12} {values[2]:>12}",
        section_title="QUALITY SCORES COVERAGE BY DATASET",
    )

    # Content flags coverage
    content_fields = [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_signature",
        "has_figure",
    ]
    _print_per_dataset_field_coverage(
        df,
        sorted_datasets,
        content_fields,
        header_fmt=(
            f"{'Dataset':<20} {'Table':>8} {'Formula':>8}"
            f" {'Handwr':>8} {'Sig':>8} {'Figure':>8}"
        ),
        row_fmt=(
            "{dataset:<20} {values[0]:>8} {values[1]:>8}"
            " {values[2]:>8} {values[3]:>8} {values[4]:>8}"
        ),
        section_title="CONTENT FLAGS COVERAGE BY DATASET",
        max_datasets=15,
    )


def export_to_csv(df, output_path: Path) -> None:
    """Export the full metadata to CSV for spreadsheet viewing."""
    df.to_csv(output_path, index=False)
    print(f"\nExported {len(df):,} records to {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate metadata completeness report"
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=SAMPLES_PARQUET,
        help="Path to samples.parquet file",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Filter to specific dataset",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Export full metadata to CSV file",
    )
    parser.add_argument(
        "--show-columns",
        action="store_true",
        help="List all available columns",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON instead of formatted text",
    )
    args = parser.parse_args()

    if not args.parquet.exists():
        print(f"Parquet file not found: {args.parquet}")
        print("\nRun the following to generate metadata:")
        print("  python scripts/annotate_base_metadata.py --scan")
        return

    print(f"Loading metadata from: {args.parquet}")
    df = load_parquet_as_pandas(args.parquet)
    print(f"Loaded {len(df):,} records")

    if args.show_columns:
        print("\nAvailable columns:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2}. {col}")
        return

    if args.dataset:
        df = df[df["dataset_name"] == args.dataset]
        if len(df) == 0:
            print(f"No records found for dataset: {args.dataset}")
            print(f"\nAvailable datasets: {sorted(df['dataset_name'].unique())}")
            return
        print(f"Filtered to {len(df):,} records for dataset: {args.dataset}")

    summary = generate_dataset_summary(df)

    if args.json:
        # Build JSON-serializable results
        # Per-field coverage percentages grouped by FIELD_CATEGORIES
        field_coverage: dict[str, dict[str, dict[str, float | int]]] = {}
        for category, fields in FIELD_CATEGORIES.items():
            category_coverage: dict[str, dict[str, float | int]] = {}
            for field in fields:
                non_null, total, pct = calculate_field_completeness(df, field)
                category_coverage[field] = {
                    "non_null_count": non_null,
                    "total_count": total,
                    "percentage": round(pct, 1),
                }
            field_coverage[category] = category_coverage

        # Overall completeness score (average across all fields)
        all_percentages = []
        for category_fields in field_coverage.values():
            for stats in category_fields.values():
                all_percentages.append(stats["percentage"])
        overall_completeness = (
            round(sum(all_percentages) / len(all_percentages), 1)
            if all_percentages
            else 0.0
        )

        results = {
            "total_records": len(df),
            "total_datasets": len(summary),
            "per_dataset": summary,
            "field_coverage_by_category": field_coverage,
            "overall_completeness_score": overall_completeness,
        }
        print(json.dumps(results, indent=2, default=str))
        return

    print_summary_table(df, summary)

    if args.output:
        export_to_csv(df, args.output)

    # Print helpful next steps
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("• Export to CSV for spreadsheet viewing:")
    print("    python scripts/metadata_completeness_report.py --output metadata.csv")
    print("• Query with DuckDB for SQL-like access:")
    print(
        "    duckdb -c \"SELECT dataset_name, COUNT(*) FROM 'samples.parquet' GROUP BY 1\""
    )
    print("• Load in Python:")
    print("    import pandas as pd; df = pd.read_parquet('samples.parquet')")


if __name__ == "__main__":
    main()
