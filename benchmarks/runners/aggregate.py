"""Aggregate benchmark results across multiple runs.

Combines results from multiple benchmark suites and generates comparative
reports in CSV and Markdown formats.

Usage:
    python -m benchmarks.runners.aggregate --out reports/aggregate.csv
    python -m benchmarks.runners.aggregate --format markdown

"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from image_preprocessing_detector.utils.datetime_compat import (
    UTC,
    datetime,
)

NO_RESULTS_MESSAGE = "⚠ No results to aggregate"


def load_all_results(reports_dir: Path) -> list[dict[str, Any]]:
    """Load all benchmark results from reports directory.

    Args:
        reports_dir: Path to reports directory

    Returns:
        List of result dictionaries
    """
    all_results = []

    if not reports_dir.exists():
        return all_results

    for suite_dir in reports_dir.iterdir():
        if not suite_dir.is_dir():
            continue

        suite_name = suite_dir.name

        # Process all timestamp directories
        for timestamp_dir in suite_dir.iterdir():
            if not timestamp_dir.is_dir():
                continue

            results_file = timestamp_dir / "results.json"
            if not results_file.exists():
                continue

            with open(results_file) as f:
                data = json.load(f)

            all_results.append(
                {
                    "suite_name": suite_name,
                    "timestamp": data.get("timestamp", timestamp_dir.name),
                    "task_type": data.get("task_type", "unknown"),
                    "num_samples": data.get("aggregates", {})
                    .get("_meta", {})
                    .get("num_samples", 0),
                    "aggregates": data.get("aggregates", {}),
                }
            )

    # Sort by timestamp (descending)
    all_results.sort(key=lambda x: x["timestamp"], reverse=True)

    return all_results


def collect_metric_names(results: list[dict[str, Any]]) -> list[str]:
    """Collect sorted metric names from aggregated results."""
    metrics = set()
    for result in results:
        metrics.update(name for name in result["aggregates"] if name != "_meta")
    return sorted(metrics)


def build_csv_row(result: dict[str, Any], metric_names: list[str]) -> dict[str, Any]:
    """Construct a CSV row for a single benchmark result."""
    row = {
        "suite": result["suite_name"],
        "timestamp": result["timestamp"],
        "task_type": result["task_type"],
        "samples": result["num_samples"],
    }

    for metric_name in metric_names:
        metric_data = result["aggregates"].get(metric_name, "")
        if isinstance(metric_data, dict):
            row[metric_name] = metric_data.get("mean", "")
        else:
            row[metric_name] = metric_data
    return row


def aggregate_to_csv(results: list[dict[str, Any]], output_path: Path) -> None:
    """Generate CSV aggregate report.

    Args:
        results: List of benchmark results
        output_path: Path to output CSV file
    """
    if not results:
        print(NO_RESULTS_MESSAGE)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as csvfile:
        all_metrics = collect_metric_names(results)
        headers = ["suite", "timestamp", "task_type", "samples"] + list(all_metrics)

        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        # Write rows
        for result in results:
            writer.writerow(build_csv_row(result, all_metrics))

    print(f"✓ CSV aggregate saved: {output_path}")


def format_metric_value(value: Any) -> str:
    """Format metric value for markdown output."""
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    if value in (None, "—"):
        return "—"
    return str(value)


def group_results_by_suite(
    results: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group aggregated results by suite name."""
    suites: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        suites.setdefault(result["suite_name"], []).append(result)
    return suites


def metrics_table_lines(aggregates: dict[str, Any]) -> list[str]:
    """Render markdown lines for the metrics table of the latest run."""
    lines = [
        "### Metrics",
        "",
        "| Metric | Mean | Std | Min | Max |",
        "|--------|------|-----|-----|-----|",
    ]

    for metric_name, metric_data in aggregates.items():
        if metric_name == "_meta":
            continue

        if isinstance(metric_data, dict):
            mean = format_metric_value(metric_data.get("mean", "—"))
            std = format_metric_value(metric_data.get("std", "—"))
            min_val = format_metric_value(metric_data.get("min", "—"))
            max_val = format_metric_value(metric_data.get("max", "—"))
        else:
            mean = format_metric_value(metric_data)
            std = min_val = max_val = "—"

        lines.append(f"| {metric_name} | {mean} | {std} | {min_val} | {max_val} |")
    lines.append("")
    return lines


def format_key_metrics_preview(aggregates: dict[str, Any]) -> str:
    """Generate a short preview of up to two key metrics for history rows."""
    previews = []
    for metric_name, metric_data in aggregates.items():
        if metric_name == "_meta":
            continue
        if isinstance(metric_data, dict):
            mean = metric_data.get("mean", "—")
            if isinstance(mean, (int, float)):
                previews.append(f"{metric_name}: {mean:.3f}")
        if len(previews) == 2:
            break
    return ", ".join(previews) if previews else "—"


def historical_trend_lines(
    suite_results: list[dict[str, Any]],
) -> list[str]:
    """Render markdown lines for the historical trend section."""
    if len(suite_results) <= 1:
        return []

    lines = [
        "### Historical Trend",
        "",
        "| Timestamp | Samples | Key Metrics |",
        "|-----------|---------|-------------|",
    ]

    for hist_result in suite_results[:5]:
        timestamp = hist_result["timestamp"]
        samples = hist_result["num_samples"]
        metrics_str = format_key_metrics_preview(hist_result["aggregates"])
        lines.append(f"| {timestamp} | {samples} | {metrics_str} |")

    lines.append("")
    return lines


def aggregate_to_markdown(results: list[dict[str, Any]], output_path: Path) -> None:
    """Generate Markdown aggregate report.

    Args:
        results: List of benchmark results
        output_path: Path to output Markdown file
    """
    if not results:
        print(NO_RESULTS_MESSAGE)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Benchmark Aggregate Report",
        "",
        f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Runs**: {len(results)}",
        "",
    ]

    suites = group_results_by_suite(results)

    for suite_name, suite_results in sorted(suites.items()):
        lines.append(f"## {suite_name}")
        lines.append("")

        latest = suite_results[0]
        lines.append(f"**Latest Run**: {latest['timestamp']}")
        lines.append(f"**Task Type**: {latest['task_type']}")
        lines.append(f"**Samples**: {latest['num_samples']}")
        lines.append("")

        lines.extend(metrics_table_lines(latest["aggregates"]))
        lines.extend(historical_trend_lines(suite_results))

    # Write file
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✓ Markdown aggregate saved: {output_path}")


def aggregate_to_json(results: list[dict[str, Any]], output_path: Path) -> None:
    """Generate JSON aggregate report.

    Args:
        results: List of benchmark results
        output_path: Path to output JSON file
    """
    if not results:
        print("⚠ No results to aggregate")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    aggregate = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_runs": len(results),
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(aggregate, f, indent=2)

    print(f"✓ JSON aggregate saved: {output_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Aggregate benchmark results across multiple runs"
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output path (default: reports/aggregate.[format])",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "markdown", "json", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=project_root / "reports",
        help="Reports directory (default: reports/)",
    )

    args = parser.parse_args()

    print("=== Aggregating Benchmark Results ===\n")

    # Load all results
    print(f"Loading results from: {args.reports_dir}")
    results = load_all_results(args.reports_dir)

    if not results:
        print("✗ No benchmark results found")
        print("\nRun benchmarks first:")
        print(
            "  python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full"
        )
        return 1

    print(f"✓ Found {len(results)} benchmark runs")

    # Group by suite
    suites = {}
    for result in results:
        suite_name = result["suite_name"]
        suites[suite_name] = suites.get(suite_name, 0) + 1

    print("\nResults by suite:")
    for suite, count in sorted(suites.items()):
        print(f"  - {suite}: {count} run(s)")

    print()

    # Generate outputs
    if args.format in ["csv", "all"]:
        output_path = args.out or (project_root / "reports" / "aggregate.csv")
        aggregate_to_csv(results, output_path)

    if args.format in ["markdown", "all"]:
        output_path = args.out or (project_root / "reports" / "aggregate.md")
        aggregate_to_markdown(results, output_path)

    if args.format in ["json", "all"]:
        output_path = args.out or (project_root / "reports" / "aggregate.json")
        aggregate_to_json(results, output_path)

    print("\n✓ Aggregation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
