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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


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


def aggregate_to_csv(results: list[dict[str, Any]], output_path: Path) -> None:
    """Generate CSV aggregate report.

    Args:
        results: List of benchmark results
        output_path: Path to output CSV file
    """
    if not results:
        print("⚠ No results to aggregate")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as csvfile:
        # Determine all metric names
        all_metrics = set()
        for result in results:
            for metric_name in result["aggregates"]:
                if metric_name != "_meta":
                    all_metrics.add(metric_name)

        all_metrics = sorted(all_metrics)

        # CSV headers
        headers = ["suite", "timestamp", "task_type", "samples"] + all_metrics

        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        # Write rows
        for result in results:
            row = {
                "suite": result["suite_name"],
                "timestamp": result["timestamp"],
                "task_type": result["task_type"],
                "samples": result["num_samples"],
            }

            # Add metric values
            for metric_name in all_metrics:
                if metric_name in result["aggregates"]:
                    metric_data = result["aggregates"][metric_name]
                    if isinstance(metric_data, dict):
                        row[metric_name] = metric_data.get("mean", "")
                    else:
                        row[metric_name] = metric_data
                else:
                    row[metric_name] = ""

            writer.writerow(row)

    print(f"✓ CSV aggregate saved: {output_path}")


def aggregate_to_markdown(results: list[dict[str, Any]], output_path: Path) -> None:
    """Generate Markdown aggregate report.

    Args:
        results: List of benchmark results
        output_path: Path to output Markdown file
    """
    if not results:
        print("⚠ No results to aggregate")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Benchmark Aggregate Report",
        "",
        f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Runs**: {len(results)}",
        "",
    ]

    # Group by suite
    suites = {}
    for result in results:
        suite_name = result["suite_name"]
        if suite_name not in suites:
            suites[suite_name] = []
        suites[suite_name].append(result)

    # Generate section for each suite
    for suite_name, suite_results in sorted(suites.items()):
        lines.append(f"## {suite_name}")
        lines.append("")

        # Get latest result
        latest = suite_results[0]
        lines.append(f"**Latest Run**: {latest['timestamp']}")
        lines.append(f"**Task Type**: {latest['task_type']}")
        lines.append(f"**Samples**: {latest['num_samples']}")
        lines.append("")

        # Metrics table
        lines.append("### Metrics")
        lines.append("")
        lines.append("| Metric | Mean | Std | Min | Max |")
        lines.append("|--------|------|-----|-----|-----|")

        for metric_name, metric_data in latest["aggregates"].items():
            if metric_name == "_meta":
                continue

            if isinstance(metric_data, dict):
                mean = metric_data.get("mean", "—")
                std = metric_data.get("std", "—")
                min_val = metric_data.get("min", "—")
                max_val = metric_data.get("max", "—")

                # Format values
                if isinstance(mean, (int, float)):
                    mean = f"{mean:.3f}"
                    std = f"{std:.3f}" if isinstance(std, (int, float)) else std
                    min_val = (
                        f"{min_val:.3f}"
                        if isinstance(min_val, (int, float))
                        else min_val
                    )
                    max_val = (
                        f"{max_val:.3f}"
                        if isinstance(max_val, (int, float))
                        else max_val
                    )

                lines.append(
                    f"| {metric_name} | {mean} | {std} | {min_val} | {max_val} |"
                )

        lines.append("")

        # Historical trend (if multiple runs)
        if len(suite_results) > 1:
            lines.append("### Historical Trend")
            lines.append("")
            lines.append("| Timestamp | Samples | Key Metrics |")
            lines.append("|-----------|---------|-------------|")

            for hist_result in suite_results[:5]:  # Show last 5 runs
                timestamp = hist_result["timestamp"]
                samples = hist_result["num_samples"]

                # Get first 2 metrics as preview
                key_metrics = []
                for i, (metric_name, metric_data) in enumerate(
                    hist_result["aggregates"].items()
                ):
                    if i >= 2 or metric_name == "_meta":
                        continue
                    if isinstance(metric_data, dict):
                        mean = metric_data.get("mean", "—")
                        if isinstance(mean, (int, float)):
                            key_metrics.append(f"{metric_name}: {mean:.3f}")

                metrics_str = ", ".join(key_metrics) if key_metrics else "—"
                lines.append(f"| {timestamp} | {samples} | {metrics_str} |")

            lines.append("")

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
