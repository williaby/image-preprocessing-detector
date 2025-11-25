"""Update README with latest benchmark results.

Automatically updates the benchmark comparison tables in benchmarks/README.md
with the latest results from the reports/ directory.

Usage:
    python -m benchmarks.runners.update_readme

"""

import json
import re
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


def load_latest_results(reports_dir: Path) -> dict[str, Any]:
    """Load the latest results from all benchmark suites.

    Args:
        reports_dir: Path to reports directory

    Returns:
        Dictionary mapping suite names to their latest results
    """
    results: dict[str, Any] = {}

    if not reports_dir.exists():
        print(f"⚠ Reports directory not found: {reports_dir}")
        return results

    # Find all suite directories
    for suite_dir in reports_dir.iterdir():
        if not suite_dir.is_dir():
            continue

        # Find latest timestamp directory
        timestamp_dirs = sorted(suite_dir.iterdir(), reverse=True)
        if not timestamp_dirs:
            continue

        latest_dir = timestamp_dirs[0]
        results_file = latest_dir / "results.json"

        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)
                results[suite_dir.name] = {
                    "timestamp": data.get("timestamp", "unknown"),
                    "aggregates": data.get("aggregates", {}),
                    "num_samples": data.get("aggregates", {})
                    .get("_meta", {})
                    .get("num_samples", 0),
                }

    return results


def format_metric(value: float | None, metric_name: str) -> str:
    """Format a metric value for display.

    Args:
        value: Metric value (or None if not available)
        metric_name: Name of the metric

    Returns:
        Formatted string
    """
    if value is None:
        return "TBD"

    # Different formatting based on metric type
    if (
        "correlation" in metric_name.lower()
        or "f1" in metric_name.lower()
        or "rmse" in metric_name.lower()
        or "mae" in metric_name.lower()
    ):
        return f"{value:.3f}"
    if "percentage" in metric_name.lower() or "rate" in metric_name.lower():
        return f"{value * 100:.1f}%"
    if "db" in metric_name.lower():
        return f"{value:.1f} dB"
    return f"{value:.2f}"


def get_status_icon(
    value: float | None, target: float, lower_is_better: bool = False
) -> str:
    """Get status icon based on value vs target.

    Args:
        value: Current value
        target: Target value
        lower_is_better: Whether lower values are better

    Returns:
        Status icon (✓, ✗, or 🔄)
    """
    if value is None:
        return "🔄"

    if lower_is_better:
        return "✓" if value <= target else "✗"
    return "✓" if value >= target else "✗"


def _format_target_string(
    metric_name: str, target: float | None, lower_is_better: bool
) -> str:
    """Format target value for display in metrics table.

    Args:
        metric_name: Name of the metric
        target: Target value (or None if no target)
        lower_is_better: Whether lower values are better

    Returns:
        Formatted target string
    """
    if target is None:
        return "—"

    metric_lower = metric_name.lower()
    comparator = "≤" if lower_is_better else "≥"

    if "percentage" in metric_lower or "rate" in metric_lower:
        return f"{comparator} {target * 100:.0f}%"
    if "degrees" in metric_lower:
        return f"{comparator} {target}°"
    if "db" in metric_lower:
        return f"≥ {target} dB"
    return f"{comparator} {target}"


def _get_metric_value(results: dict[str, Any], suite: str, key: str) -> float | None:
    """Extract metric value from results.

    Args:
        results: Benchmark results dictionary
        suite: Suite name
        key: Metric key

    Returns:
        Metric mean value or None if not found
    """
    if suite not in results:
        return None
    aggregates = results[suite].get("aggregates", {})
    if key not in aggregates:
        return None
    mean_value: float | None = aggregates[key].get("mean")
    return mean_value


def _determine_status(
    value: float | None,
    target: float | None,
    lower_is_better: bool,
    category: str,
) -> str:
    """Determine status icon for a metric.

    Args:
        value: Current metric value
        target: Target value
        lower_is_better: Whether lower is better
        category: Category name (for special handling)

    Returns:
        Status icon string
    """
    if value is None:
        return "⏳" if "Layout" in category else "🔄"
    if target is None:
        return "—"
    return get_status_icon(value, target, lower_is_better)


def _build_metric_row(
    category: str,
    metric_name: str,
    results: dict[str, Any],
    suite: str,
    key: str,
    target: float | None,
    lower_is_better: bool,
) -> str:
    """Build a single metric row for the table.

    Args:
        category: Category name
        metric_name: Metric name
        results: Benchmark results
        suite: Suite name
        key: Metric key
        target: Target value
        lower_is_better: Whether lower is better

    Returns:
        Formatted table row string
    """
    value = _get_metric_value(results, suite, key)
    target_str = _format_target_string(metric_name, target, lower_is_better)
    current_str = format_metric(value, metric_name)
    status = _determine_status(value, target, lower_is_better, category)

    return (
        f"| **{category}** | {metric_name} | {target_str} | {current_str} | {status} |"
    )


# Metrics configuration: category -> metric_name -> (suite, key, target, lower_is_better)
METRICS_CONFIG: dict[str, dict[str, tuple[str, str, float | None, bool]]] = {
    "IQA - Blur": {
        "Correlation (Pearson r)": (
            "synthetic-iqa-blur-full",
            "blur_correlation",
            0.85,
            False,
        ),
        "RMSE": ("synthetic-iqa-blur-full", "blur_rmse", 0.05, True),
    },
    "IQA - Skew": {
        "MAE (degrees)": ("synthetic-iqa-skew-full", "skew_mae", 0.5, True),
    },
    "IQA - Deskew": {
        "Success Rate": (
            "synthetic-iqa-skew-full",
            "deskew_success_rate",
            0.99,
            False,
        ),
    },
    "IQA - Noise": {
        "SNR Improvement": (
            "synthetic-iqa-noise-full",
            "snr_improvement",
            6.0,
            False,
        ),
    },
    "IQA - Quality": {
        "PSNR": ("synthetic-iqa-noise-full", "psnr", 30.0, False),
        "SSIM": ("synthetic-iqa-noise-full", "ssim", 0.9, False),
    },
    "IQA - Binarization": {
        "F-measure": ("synthetic-iqa-binarization-full", "f_measure", 0.95, False),
    },
    "Layout Detection": {
        "mAP@[.5:.95] (DocLayNet)": ("doclaynet-layout-full", "mAP", 0.80, False),
        "Per-class AP": ("doclaynet-layout-full", "per_class_AP", None, False),
    },
}


def update_quick_metrics_table(readme_content: str, results: dict[str, Any]) -> str:
    """Update the Quick Metrics Summary table.

    Args:
        readme_content: Current README content
        results: Latest benchmark results

    Returns:
        Updated README content
    """
    # Build new table
    new_rows = [
        "| Category | Metric | Target | Current | Status |",
        "|----------|--------|--------|---------|--------|",
    ]

    for category, metrics in METRICS_CONFIG.items():
        for metric_name, (suite, key, target, lower_is_better) in metrics.items():
            row = _build_metric_row(
                category, metric_name, results, suite, key, target, lower_is_better
            )
            new_rows.append(row)

    new_table = "\n".join(new_rows)

    # Replace table in README
    pattern = r"\| Category \| Metric \| Target \| Current \| Status \|.*?\n\n"
    replacement = new_table + "\n\n"

    return re.sub(pattern, replacement, readme_content, flags=re.DOTALL)


def update_last_updated(readme_content: str) -> str:
    """Update the 'Last Updated' timestamp.

    Args:
        readme_content: Current README content

    Returns:
        Updated README content
    """
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    pattern = r"\*\*Last Updated\*\*: \d{4}-\d{2}-\d{2}"
    replacement = f"**Last Updated**: {now}"

    return re.sub(pattern, replacement, readme_content)


def generate_summary_stats(results: dict[str, Any]) -> dict[str, Any]:
    """Generate summary statistics from results.

    Args:
        results: Latest benchmark results

    Returns:
        Summary statistics
    """
    total_suites = len(results)
    total_samples = sum(r.get("num_samples", 0) for r in results.values())

    # Count passed/failed metrics
    passed = 0
    total = 0

    for suite_name, suite_data in results.items():
        aggregates = suite_data.get("aggregates", {})
        for metric_name, metric_data in aggregates.items():
            if metric_name == "_meta":
                continue
            if isinstance(metric_data, dict) and "mean" in metric_data:
                total += 1
                # Simple heuristic: if mean > 0.5, consider it passing
                if metric_data["mean"] > 0.5:
                    passed += 1

    return {
        "total_suites": total_suites,
        "total_samples": total_samples,
        "passed_metrics": passed,
        "total_metrics": total,
    }


def main() -> int:
    """Main entry point."""
    print("=== Updating README with Latest Benchmark Results ===\n")

    # Paths
    readme_path = project_root / "benchmarks" / "README.md"
    reports_dir = project_root / "reports"

    if not readme_path.exists():
        print(f"✗ README not found: {readme_path}")
        return 1

    # Load latest results
    print(f"Loading results from: {reports_dir}")
    results = load_latest_results(reports_dir)

    if not results:
        print("⚠ No benchmark results found. Run benchmarks first:")
        print(
            "  python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full"
        )
        print("\nREADME will be updated with 'TBD' placeholders.")
    else:
        print(f"✓ Found results for {len(results)} suites:")
        for suite_name, suite_data in results.items():
            print(f"  - {suite_name}: {suite_data['num_samples']} samples")

    # Load current README
    with open(readme_path) as f:
        readme_content = f.read()

    # Update tables
    print("\nUpdating README sections...")
    readme_content = update_quick_metrics_table(readme_content, results)
    readme_content = update_last_updated(readme_content)

    # Write updated README
    with open(readme_path, "w") as f:
        f.write(readme_content)

    # Generate summary
    stats = generate_summary_stats(results)
    print("\n=== Summary ===")
    print(f"Total Suites: {stats['total_suites']}")
    print(f"Total Samples: {stats['total_samples']}")
    print(f"Metrics: {stats['passed_metrics']}/{stats['total_metrics']}")

    print(f"\n✓ README updated: {readme_path}")
    print("\nNext steps:")
    print("  1. Review changes: git diff benchmarks/README.md")
    print(
        "  2. Commit: git add benchmarks/README.md && git commit -m 'docs: Update benchmark results'"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
