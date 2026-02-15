#!/usr/bin/env python3
"""Cross-dataset portfolio analytics dashboard.

Reads all screening and scorecard artifacts to build a per-field coverage
heatmap across the full dataset portfolio. Identifies systemic gaps and
produces CSV, HTML, and JSON outputs.

Usage::

    # Generate all output formats
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/portfolio_analytics.py --format all

    # CSV only
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/portfolio_analytics.py --format csv

    # Custom output directory
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/portfolio_analytics.py --format html --output-dir results/
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DatasetFieldCoverage:
    """Per-field pass rates for a single dataset.

    Attributes:
        dataset: Canonical dataset name.
        grade: Current scorecard grade.
        overall_score: Current overall score.
        field_pass_rates: Mapping of field_name to pass rate (0-100).
        total_samples: Number of samples audited.
    """

    dataset: str
    grade: str = "?"
    overall_score: float = 0.0
    field_pass_rates: dict[str, float] = field(default_factory=dict)
    total_samples: int = 0


@dataclass
class FieldStatistics:
    """Aggregate statistics for a single field across all datasets.

    Attributes:
        field_name: Name of the prescreening field.
        mean_pass_rate: Mean pass rate across datasets.
        min_pass_rate: Minimum pass rate.
        max_pass_rate: Maximum pass rate.
        std_dev: Standard deviation of pass rates.
        datasets_below_75: Number of datasets with pass rate < 75%.
        datasets_at_100: Number of datasets with 100% pass rate.
        total_datasets: Number of datasets with data for this field.
    """

    field_name: str
    mean_pass_rate: float = 0.0
    min_pass_rate: float = 0.0
    max_pass_rate: float = 0.0
    std_dev: float = 0.0
    datasets_below_75: int = 0
    datasets_at_100: int = 0
    total_datasets: int = 0


@dataclass
class PortfolioAnalytics:
    """Complete portfolio analytics result.

    Attributes:
        generated_at: ISO timestamp of generation.
        total_datasets: Number of datasets analyzed.
        datasets: Per-dataset coverage data.
        field_stats: Aggregate field statistics.
        grade_distribution: Count per grade letter.
        systemic_gaps: Fields failing in >N datasets.
    """

    generated_at: str = ""
    total_datasets: int = 0
    datasets: list[DatasetFieldCoverage] = field(default_factory=list)
    field_stats: list[FieldStatistics] = field(default_factory=list)
    grade_distribution: dict[str, int] = field(default_factory=dict)
    systemic_gaps: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_dataset_coverage(
    dataset_dir: Path,
) -> DatasetFieldCoverage | None:
    """Load field coverage for a single dataset from its result directory.

    Args:
        dataset_dir: Path to the dataset's results directory.

    Returns:
        DatasetFieldCoverage or None if no screening data.
    """
    screening_path = dataset_dir / "automated_screening.json"
    scorecard_path = dataset_dir / "scorecard.json"

    if not screening_path.exists():
        return None

    with screening_path.open(encoding="utf-8") as f:
        screening = json.load(f)

    coverage = DatasetFieldCoverage(
        dataset=dataset_dir.name,
        total_samples=screening.get("total_samples", 0),
    )

    # Extract pass rates
    per_field = screening.get("per_field_results", {})
    for field_name, field_data in per_field.items():
        fail_rate = field_data.get("fail_rate_pct", 0.0)
        coverage.field_pass_rates[field_name] = round(100.0 - fail_rate, 2)

    # Merge scorecard grade if available
    if scorecard_path.exists():
        with scorecard_path.open(encoding="utf-8") as f:
            scorecard = json.load(f)
        coverage.grade = scorecard.get("grade", "?")
        coverage.overall_score = scorecard.get("overall_score", 0.0)

    return coverage


def load_all_coverage(*, results_dir: Path | None = None) -> list[DatasetFieldCoverage]:
    """Load field coverage for all datasets.

    Args:
        results_dir: Override results directory.

    Returns:
        Sorted list of DatasetFieldCoverage.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    datasets: list[DatasetFieldCoverage] = []

    for ds_dir in sorted(base.iterdir()):
        if not ds_dir.is_dir() or ds_dir.name.startswith("."):
            continue
        coverage = load_dataset_coverage(ds_dir)
        if coverage:
            datasets.append(coverage)

    return datasets


# ---------------------------------------------------------------------------
# Analytics computation
# ---------------------------------------------------------------------------
def compute_field_statistics(
    datasets: list[DatasetFieldCoverage],
) -> list[FieldStatistics]:
    """Compute aggregate statistics per field across all datasets.

    Args:
        datasets: List of per-dataset coverage data.

    Returns:
        Sorted list of FieldStatistics (worst fields first).
    """
    # Collect all field names
    all_fields: set[str] = set()
    for ds in datasets:
        all_fields.update(ds.field_pass_rates.keys())

    stats: list[FieldStatistics] = []
    for field_name in sorted(all_fields):
        rates = [
            ds.field_pass_rates[field_name]
            for ds in datasets
            if field_name in ds.field_pass_rates
        ]
        if not rates:
            continue

        fs = FieldStatistics(
            field_name=field_name,
            mean_pass_rate=round(statistics.mean(rates), 2),
            min_pass_rate=round(min(rates), 2),
            max_pass_rate=round(max(rates), 2),
            std_dev=round(statistics.stdev(rates), 2) if len(rates) > 1 else 0.0,
            datasets_below_75=sum(1 for r in rates if r < 75.0),
            datasets_at_100=sum(1 for r in rates if abs(r - 100.0) < 1e-9),
            total_datasets=len(rates),
        )
        stats.append(fs)

    # Sort by mean pass rate ascending (worst first)
    stats.sort(key=lambda s: s.mean_pass_rate)
    return stats


def compute_grade_distribution(
    datasets: list[DatasetFieldCoverage],
) -> dict[str, int]:
    """Count datasets per grade letter.

    Args:
        datasets: List of per-dataset coverage data.

    Returns:
        Dict mapping grade letter to count.
    """
    dist: dict[str, int] = {}
    for ds in datasets:
        dist[ds.grade] = dist.get(ds.grade, 0) + 1
    return dict(sorted(dist.items()))


def identify_systemic_gaps(
    field_stats: list[FieldStatistics],
    *,
    min_failing_datasets: int = 3,
    threshold: float = 75.0,
) -> list[dict[str, Any]]:
    """Find fields that fail across multiple datasets.

    Args:
        field_stats: Computed field statistics.
        min_failing_datasets: Minimum datasets below threshold to flag.
        threshold: Pass rate threshold.

    Returns:
        List of gap descriptions.
    """
    gaps: list[dict[str, Any]] = []
    for fs in field_stats:
        if fs.datasets_below_75 >= min_failing_datasets:
            gaps.append(
                {
                    "field": fs.field_name,
                    "datasets_below_threshold": fs.datasets_below_75,
                    "mean_pass_rate": fs.mean_pass_rate,
                    "min_pass_rate": fs.min_pass_rate,
                }
            )
    return gaps


def build_portfolio_analytics(*, results_dir: Path | None = None) -> PortfolioAnalytics:
    """Build complete portfolio analytics.

    Args:
        results_dir: Override results directory.

    Returns:
        PortfolioAnalytics with all computed data.
    """
    datasets = load_all_coverage(results_dir=results_dir)
    field_stats = compute_field_statistics(datasets)
    grade_dist = compute_grade_distribution(datasets)
    gaps = identify_systemic_gaps(field_stats)

    return PortfolioAnalytics(
        generated_at=datetime.now(UTC).isoformat(),
        total_datasets=len(datasets),
        datasets=datasets,
        field_stats=field_stats,
        grade_distribution=grade_dist,
        systemic_gaps=gaps,
    )


# ---------------------------------------------------------------------------
# Output: CSV
# ---------------------------------------------------------------------------
def generate_csv(analytics: PortfolioAnalytics) -> str:
    """Generate CSV heatmap of per-field pass rates.

    Args:
        analytics: Computed portfolio analytics.

    Returns:
        CSV string content.
    """
    if not analytics.datasets:
        return ""

    # Collect all field names in consistent order
    all_fields = sorted({f for ds in analytics.datasets for f in ds.field_pass_rates})

    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["dataset", "grade", "score", "samples", *all_fields])

    # Data rows
    for ds in sorted(analytics.datasets, key=lambda d: d.dataset):
        row = [ds.dataset, ds.grade, f"{ds.overall_score:.1f}", str(ds.total_samples)]
        for field_name in all_fields:
            rate = ds.field_pass_rates.get(field_name)
            row.append(f"{rate:.1f}" if rate is not None else "")
        writer.writerow(row)

    # Summary row
    summary_row = ["MEAN", "", "", ""]
    for fs in analytics.field_stats:
        if fs.field_name in all_fields:
            idx = all_fields.index(fs.field_name)
            while len(summary_row) <= idx + 4:
                summary_row.append("")
            summary_row[idx + 4] = f"{fs.mean_pass_rate:.1f}"
    writer.writerow(summary_row)

    return output.getvalue()


# ---------------------------------------------------------------------------
# Output: HTML
# ---------------------------------------------------------------------------
def _rate_to_color(rate: float | None) -> str:
    """Convert a pass rate to a CSS color.

    Args:
        rate: Pass rate (0-100) or None.

    Returns:
        CSS color string.
    """
    if rate is None:
        return "#cccccc"
    if rate >= 95.0:
        return "#27ae60"  # green
    if rate >= 75.0:
        return "#f39c12"  # yellow/orange
    if rate >= 50.0:
        return "#e67e22"  # orange
    return "#e74c3c"  # red


def generate_html(analytics: PortfolioAnalytics) -> str:
    """Generate self-contained HTML heatmap.

    Args:
        analytics: Computed portfolio analytics.

    Returns:
        HTML string content.
    """
    if not analytics.datasets:
        return "<html><body><p>No data.</p></body></html>"

    all_fields = sorted({f for ds in analytics.datasets for f in ds.field_pass_rates})

    lines: list[str] = []
    lines.append("<!DOCTYPE html>")
    lines.append("<html><head>")
    lines.append("<meta charset='utf-8'>")
    lines.append("<title>Portfolio Analytics Heatmap</title>")
    lines.append("<style>")
    lines.append("body { font-family: monospace; font-size: 12px; margin: 20px; }")
    lines.append("h1 { font-size: 18px; }")
    lines.append("table { border-collapse: collapse; }")
    lines.append(
        "th, td { border: 1px solid #ddd; padding: 4px 8px; text-align: center; }"
    )
    lines.append("th { background: #2c3e50; color: white; font-size: 11px; }")
    lines.append(".dataset-name { text-align: left; font-weight: bold; }")
    lines.append(".grade { font-weight: bold; }")
    lines.append(".summary { background: #34495e; color: white; font-weight: bold; }")
    lines.append("</style>")
    lines.append("</head><body>")
    lines.append(
        f"<h1>Portfolio Analytics Heatmap ({analytics.total_datasets} datasets)</h1>"
    )
    lines.append(f"<p>Generated: {analytics.generated_at}</p>")

    # Grade distribution
    lines.append("<p>Grade distribution: ")
    for grade, count in sorted(analytics.grade_distribution.items()):
        lines.append(f"{grade}={count} ")
    lines.append("</p>")

    # Systemic gaps
    if analytics.systemic_gaps:
        lines.append("<h2>Systemic Gaps</h2><ul>")
        for gap in analytics.systemic_gaps:
            lines.append(
                f"<li><b>{gap['field']}</b>: below 75% in "
                f"{gap['datasets_below_threshold']} datasets "
                f"(mean {gap['mean_pass_rate']:.1f}%)</li>"
            )
        lines.append("</ul>")

    # Heatmap table
    lines.append("<table>")
    lines.append("<tr><th>Dataset</th><th>Grade</th><th>Score</th>")
    for field_name in all_fields:
        # Abbreviate long names
        short = field_name.replace("_", " ").title()
        if len(short) > 15:
            short = field_name[:12] + "..."
        lines.append(f"<th>{short}</th>")
    lines.append("</tr>")

    for ds in sorted(analytics.datasets, key=lambda d: d.overall_score, reverse=True):
        lines.append(f"<tr><td class='dataset-name'>{ds.dataset}</td>")
        lines.append(f"<td class='grade'>{ds.grade}</td>")
        lines.append(f"<td>{ds.overall_score:.1f}</td>")
        for field_name in all_fields:
            rate = ds.field_pass_rates.get(field_name)
            color = _rate_to_color(rate)
            val = f"{rate:.0f}" if rate is not None else "-"
            lines.append(f"<td style='background:{color};color:white'>{val}</td>")
        lines.append("</tr>")

    # Mean row
    lines.append("<tr class='summary'><td>MEAN</td><td></td><td></td>")
    field_stat_map = {fs.field_name: fs for fs in analytics.field_stats}
    for field_name in all_fields:
        fs = field_stat_map.get(field_name)
        val = f"{fs.mean_pass_rate:.0f}" if fs else "-"
        lines.append(f"<td>{val}</td>")
    lines.append("</tr>")

    lines.append("</table>")
    lines.append("</body></html>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output: JSON
# ---------------------------------------------------------------------------
def generate_json(analytics: PortfolioAnalytics) -> dict[str, Any]:
    """Generate JSON analytics output.

    Args:
        analytics: Computed portfolio analytics.

    Returns:
        JSON-serializable dict.
    """
    return {
        "generated_at": analytics.generated_at,
        "total_datasets": analytics.total_datasets,
        "grade_distribution": analytics.grade_distribution,
        "systemic_gaps": analytics.systemic_gaps,
        "field_statistics": [
            {
                "field": fs.field_name,
                "mean": fs.mean_pass_rate,
                "min": fs.min_pass_rate,
                "max": fs.max_pass_rate,
                "std_dev": fs.std_dev,
                "below_75_count": fs.datasets_below_75,
                "at_100_count": fs.datasets_at_100,
                "total_datasets": fs.total_datasets,
            }
            for fs in analytics.field_stats
        ],
        "datasets": [
            {
                "dataset": ds.dataset,
                "grade": ds.grade,
                "score": ds.overall_score,
                "samples": ds.total_samples,
                "field_pass_rates": ds.field_pass_rates,
            }
            for ds in analytics.datasets
        ],
    }


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------
def write_outputs(
    analytics: PortfolioAnalytics,
    *,
    output_dir: Path | None = None,
    formats: set[str] | None = None,
) -> list[Path]:
    """Write analytics outputs in requested formats.

    Args:
        analytics: Computed portfolio analytics.
        output_dir: Output directory path.
        formats: Set of formats to generate ("csv", "html", "json", "all").

    Returns:
        List of written file paths.
    """
    out_dir = output_dir or AUDIT_RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if formats is None or "all" in formats:
        formats = {"csv", "html", "json"}

    written: list[Path] = []

    if "csv" in formats:
        csv_path = out_dir / "portfolio_heatmap.csv"
        csv_path.write_text(generate_csv(analytics), encoding="utf-8")
        written.append(csv_path)
        log.info("CSV written to %s", csv_path)

    if "html" in formats:
        html_path = out_dir / "portfolio_heatmap.html"
        html_path.write_text(generate_html(analytics), encoding="utf-8")
        written.append(html_path)
        log.info("HTML written to %s", html_path)

    if "json" in formats:
        json_path = out_dir / "portfolio_analytics.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(generate_json(analytics), f, indent=2, ensure_ascii=False)
        written.append(json_path)
        log.info("JSON written to %s", json_path)

    return written


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------
def print_summary(analytics: PortfolioAnalytics) -> None:
    """Print analytics summary to console.

    Args:
        analytics: Computed portfolio analytics.
    """
    print(f"\n{'=' * 65}")
    print("Portfolio Analytics Summary")
    print(f"{'=' * 65}")
    print(f"  Total datasets: {analytics.total_datasets}")
    print(f"  Grade distribution: {analytics.grade_distribution}")
    print()

    if analytics.systemic_gaps:
        print("  Systemic gaps (field below 75% in 3+ datasets):")
        for gap in analytics.systemic_gaps:
            print(
                f"    {gap['field']}: {gap['datasets_below_threshold']} datasets, "
                f"mean {gap['mean_pass_rate']:.1f}%"
            )
        print()

    print("  Field statistics (sorted by mean, worst first):")
    for fs in analytics.field_stats[:10]:
        print(
            f"    {fs.field_name:30s}  "
            f"mean={fs.mean_pass_rate:5.1f}%  "
            f"min={fs.min_pass_rate:5.1f}%  "
            f"<75%={fs.datasets_below_75:2d}  "
            f"100%={fs.datasets_at_100:2d}/{fs.total_datasets}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI entry point for portfolio analytics.

    Args:
        argv: Command-line arguments. Uses sys.argv if None.

    Returns:
        Exit code (always 0).
    """
    parser = argparse.ArgumentParser(
        description="Cross-dataset portfolio analytics dashboard."
    )
    parser.add_argument(
        "--format",
        choices=["csv", "html", "json", "all"],
        default="all",
        help="Output format (default: all).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory path.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Override results directory.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=75.0,
        help="Gap threshold for systemic analysis (default: 75.0).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress console output.")

    args = parser.parse_args(argv)

    analytics = build_portfolio_analytics(results_dir=args.results_dir)

    if not args.quiet:
        print_summary(analytics)

    formats = {"all"} if args.format == "all" else {args.format}
    write_outputs(
        analytics,
        output_dir=args.output_dir or args.results_dir,
        formats=formats,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
