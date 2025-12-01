#!/usr/bin/env python3
"""
Benchmark Results Comparison Utility.

Compares model performance across versions to track improvement over baseline.
Generates comparison reports showing delta metrics for Project A attributes.

Usage:
    # Compare specific models
    python scripts/omnidocbench_baseline/compare_results.py \\
        --models classical_cv_baseline,resnet18_student_v1,resnet18_student_v2

    # Compare against baseline
    python scripts/omnidocbench_baseline/compare_results.py \\
        --baseline classical_cv_baseline \\
        --compare resnet18_student_v1

    # Track progression
    python scripts/omnidocbench_baseline/compare_results.py \\
        --progression resnet18_student

    # Generate markdown report
    python scripts/omnidocbench_baseline/compare_results.py \\
        --models classical_cv_baseline,resnet18_student_v1 \\
        --output-format markdown
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default results directory
DEFAULT_RESULTS_DIR = Path("docs/benchmarks/omnidocbench_results")

# Project A target metrics
PROJECT_A_TARGETS = {
    "fuzzy_scan": {"f1": 0.85, "correlation": 0.70},
    "watermark": {"f1": 0.85},
    "colorful_background": {"f1": 0.85},
    "has_tables": {"f1": 0.85},
    "has_figures": {"f1": 0.85},
    "has_dense_math": {"f1": 0.85},
    "layout_type": {"accuracy": 0.80},
    "overall": {"mean_f1": 0.80},
}


def load_results(model_id: str, results_dir: Path) -> dict[str, Any] | None:
    """Load latest results for a model.

    Args:
        model_id: Model identifier
        results_dir: Results directory

    Returns:
        Results dict or None if not found
    """
    # Try latest file first
    latest_path = results_dir / f"{model_id}_latest.json"
    if latest_path.exists():
        with open(latest_path, encoding="utf-8") as f:
            return json.load(f)

    # Try to find any timestamped file
    pattern = f"{model_id}_*.json"
    files = sorted(results_dir.glob(pattern), reverse=True)
    if files:
        with open(files[0], encoding="utf-8") as f:
            return json.load(f)

    return None


def calculate_delta(
    baseline: float, current: float, higher_is_better: bool = True
) -> dict[str, Any]:
    """Calculate improvement delta between baseline and current.

    Args:
        baseline: Baseline metric value
        current: Current metric value
        higher_is_better: Whether higher values indicate improvement

    Returns:
        Dict with absolute delta, relative improvement, and direction
    """
    absolute = current - baseline
    relative = (absolute / baseline * 100) if baseline != 0 else 0

    if higher_is_better:
        improved = absolute > 0
    else:
        improved = absolute < 0

    return {
        "baseline": baseline,
        "current": current,
        "absolute_delta": absolute,
        "relative_delta_pct": relative,
        "improved": improved,
        "direction": "↑" if improved else "↓" if absolute != 0 else "→",
    }


def compare_models(
    baseline_results: dict[str, Any],
    current_results: dict[str, Any],
) -> dict[str, Any]:
    """Compare two model results.

    Args:
        baseline_results: Baseline model results
        current_results: Current model results

    Returns:
        Comparison dict with deltas for each metric
    """
    comparison = {
        "baseline_model": baseline_results["model"],
        "current_model": current_results["model"],
        "timestamp": datetime.now().isoformat(),
        "binary_attributes": {},
        "correlations": {},
        "performance": {},
        "summary": {},
    }

    # Compare binary attributes
    baseline_attrs = baseline_results.get("binary_attributes", {})
    current_attrs = current_results.get("binary_attributes", {})

    all_attrs = set(baseline_attrs.keys()) | set(current_attrs.keys())

    for attr in all_attrs:
        baseline_f1 = baseline_attrs.get(attr, {}).get("f1", 0.0)
        current_f1 = current_attrs.get(attr, {}).get("f1", 0.0)

        delta = calculate_delta(baseline_f1, current_f1)
        delta["target"] = PROJECT_A_TARGETS.get(attr, {}).get("f1", 0.85)
        delta["target_met"] = current_f1 >= delta["target"]

        comparison["binary_attributes"][attr] = delta

    # Compare correlations (for IQA models)
    baseline_corrs = baseline_results.get("correlations", {})
    current_corrs = current_results.get("correlations", {})

    for corr_name in set(baseline_corrs.keys()) | set(current_corrs.keys()):
        baseline_val = baseline_corrs.get(corr_name, 0.0)
        current_val = current_corrs.get(corr_name, 0.0)

        delta = calculate_delta(baseline_val, current_val)
        comparison["correlations"][corr_name] = delta

    # Compare performance
    baseline_perf = baseline_results.get("performance", {})
    current_perf = current_results.get("performance", {})

    for metric in ["mean_inference_ms", "p95_inference_ms"]:
        baseline_val = baseline_perf.get(metric, 0.0)
        current_val = current_perf.get(metric, 0.0)

        # For latency, lower is better
        delta = calculate_delta(baseline_val, current_val, higher_is_better=False)
        comparison["performance"][metric] = delta

    # Summary metrics
    baseline_mean_f1 = baseline_results.get("summary", {}).get("mean_f1", 0.0)
    current_mean_f1 = current_results.get("summary", {}).get("mean_f1", 0.0)

    comparison["summary"]["mean_f1"] = calculate_delta(
        baseline_mean_f1, current_mean_f1
    )
    comparison["summary"]["mean_f1"]["target"] = PROJECT_A_TARGETS["overall"]["mean_f1"]
    comparison["summary"]["mean_f1"]["target_met"] = (
        current_mean_f1 >= PROJECT_A_TARGETS["overall"]["mean_f1"]
    )

    # Count improvements
    improvements = sum(
        1
        for attr_delta in comparison["binary_attributes"].values()
        if attr_delta["improved"]
    )
    regressions = sum(
        1
        for attr_delta in comparison["binary_attributes"].values()
        if not attr_delta["improved"] and attr_delta["absolute_delta"] != 0
    )

    comparison["summary"]["improvements"] = improvements
    comparison["summary"]["regressions"] = regressions
    comparison["summary"]["net_improvement"] = improvements - regressions

    return comparison


def generate_comparison_table(comparison: dict[str, Any]) -> str:
    """Generate ASCII comparison table.

    Args:
        comparison: Comparison dict

    Returns:
        Formatted table string
    """
    lines = []

    baseline = comparison["baseline_model"]
    current = comparison["current_model"]

    lines.append("=" * 90)
    lines.append(
        f"COMPARISON: {baseline['name']} (v{baseline['version']}) → {current['name']} (v{current['version']})"
    )
    lines.append("=" * 90)

    # Binary attributes table
    lines.append("\nBinary Attribute Detection:")
    lines.append("-" * 90)
    lines.append(
        f"{'Attribute':<25} {'Baseline':>10} {'Current':>10} {'Delta':>10} {'Relative':>10} {'Target':>8}"
    )
    lines.append("-" * 90)

    for attr, delta in comparison["binary_attributes"].items():
        status = "✅" if delta["target_met"] else "❌"
        direction = delta["direction"]
        lines.append(
            f"{attr:<25} {delta['baseline']:>10.3f} {delta['current']:>10.3f} "
            f"{direction}{abs(delta['absolute_delta']):>8.3f} {delta['relative_delta_pct']:>9.1f}% "
            f"{status}{delta['target']:>6.2f}"
        )

    # Correlations
    if comparison.get("correlations"):
        lines.append("\nScore Correlations:")
        lines.append("-" * 90)
        for name, delta in comparison["correlations"].items():
            direction = delta["direction"]
            lines.append(
                f"  {name:<40} {delta['baseline']:>8.3f} → {delta['current']:>8.3f} "
                f"({direction}{abs(delta['absolute_delta']):.3f})"
            )

    # Performance
    lines.append("\nPerformance:")
    lines.append("-" * 90)
    for metric, delta in comparison["performance"].items():
        direction = delta["direction"]
        # For latency, ↓ is good
        status = "✅" if delta["improved"] else "❌"
        lines.append(
            f"  {metric:<30} {delta['baseline']:>8.1f}ms → {delta['current']:>8.1f}ms "
            f"({direction}{abs(delta['absolute_delta']):.1f}ms) {status}"
        )

    # Summary
    summary = comparison["summary"]
    mean_f1_delta = summary["mean_f1"]
    lines.append("\nSummary:")
    lines.append("-" * 90)
    lines.append(
        f"  Mean F1: {mean_f1_delta['baseline']:.3f} → {mean_f1_delta['current']:.3f} "
        f"({mean_f1_delta['direction']}{abs(mean_f1_delta['absolute_delta']):.3f})"
    )
    lines.append(
        f"  Improvements: {summary['improvements']} | Regressions: {summary['regressions']}"
    )
    lines.append(f"  Net Improvement: {summary['net_improvement']:+d}")
    lines.append(
        f"  Target Met: {'✅' if mean_f1_delta['target_met'] else '❌'} (>= {mean_f1_delta['target']:.2f})"
    )

    lines.append("=" * 90)

    return "\n".join(lines)


def generate_markdown_report(
    comparison: dict[str, Any],
    include_project_a_context: bool = True,
) -> str:
    """Generate markdown comparison report.

    Args:
        comparison: Comparison dict
        include_project_a_context: Include Project A scope context

    Returns:
        Markdown formatted report
    """
    lines = []

    baseline = comparison["baseline_model"]
    current = comparison["current_model"]

    lines.append("# Model Comparison Report")
    lines.append("")
    lines.append(f"**Baseline**: {baseline['name']} (v{baseline['version']})")
    lines.append(f"**Current**: {current['name']} (v{current['version']})")
    lines.append(f"**Generated**: {comparison['timestamp']}")
    lines.append("")

    if include_project_a_context:
        lines.append("## Project A Evaluation Scope")
        lines.append("")
        lines.append("This comparison evaluates metrics within Project A's scope:")
        lines.append(
            "- Page attributes: `fuzzy_scan`, `watermark`, `colorful_background`"
        )
        lines.append(
            "- Element presence: `has_tables`, `has_figures`, `has_dense_math`"
        )
        lines.append("- Layout classification (not shown if not evaluated)")
        lines.append("")
        lines.append(
            "**NOT evaluated** (Project B scope): OCR, table structure, formula recognition, reading order"
        )
        lines.append("")

    # Summary
    summary = comparison["summary"]
    mean_f1 = summary["mean_f1"]

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(
        f"| Mean F1 Change | {mean_f1['baseline']:.3f} → {mean_f1['current']:.3f} ({mean_f1['direction']}{abs(mean_f1['absolute_delta']):.3f}) |"
    )
    lines.append(f"| Improvements | {summary['improvements']} |")
    lines.append(f"| Regressions | {summary['regressions']} |")
    lines.append(
        f"| Target Met | {'✅' if mean_f1['target_met'] else '❌'} (>= {mean_f1['target']:.2f}) |"
    )
    lines.append("")

    # Detailed results
    lines.append("## Binary Attribute Detection")
    lines.append("")
    lines.append("| Attribute | Baseline | Current | Δ | Relative | Target |")
    lines.append("|-----------|----------|---------|---|----------|--------|")

    for attr, delta in comparison["binary_attributes"].items():
        status = "✅" if delta["target_met"] else "❌"
        lines.append(
            f"| {attr} | {delta['baseline']:.3f} | {delta['current']:.3f} | "
            f"{delta['direction']}{abs(delta['absolute_delta']):.3f} | "
            f"{delta['relative_delta_pct']:+.1f}% | {status} {delta['target']:.2f} |"
        )

    lines.append("")

    # Correlations
    if comparison.get("correlations"):
        lines.append("## IQA Score Correlations")
        lines.append("")
        lines.append("| Correlation | Baseline | Current | Δ |")
        lines.append("|-------------|----------|---------|---|")

        for name, delta in comparison["correlations"].items():
            lines.append(
                f"| {name} | {delta['baseline']:.3f} | {delta['current']:.3f} | "
                f"{delta['direction']}{abs(delta['absolute_delta']):.3f} |"
            )
        lines.append("")

    # Performance
    lines.append("## Performance")
    lines.append("")
    lines.append("| Metric | Baseline | Current | Δ | Status |")
    lines.append("|--------|----------|---------|---|--------|")

    for metric, delta in comparison["performance"].items():
        status = "✅ Faster" if delta["improved"] else "❌ Slower"
        lines.append(
            f"| {metric} | {delta['baseline']:.1f}ms | {delta['current']:.1f}ms | "
            f"{delta['direction']}{abs(delta['absolute_delta']):.1f}ms | {status} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Generated by Project A OmniDocBench Benchmark Comparison*")

    return "\n".join(lines)


def track_progression(
    model_prefix: str,
    results_dir: Path,
) -> dict[str, Any]:
    """Track progression of a model through versions.

    Args:
        model_prefix: Model ID prefix (e.g., "resnet18_student")
        results_dir: Results directory

    Returns:
        Progression tracking dict
    """
    # Find all versions
    pattern = f"{model_prefix}*.json"
    files = sorted(results_dir.glob(pattern))

    versions: list[dict[str, Any]] = []
    for f in files:
        if "_latest" in f.name:
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
                versions.append(
                    {
                        "file": f.name,
                        "model": data.get("model", {}),
                        "summary": data.get("summary", {}),
                        "binary_attributes": data.get("binary_attributes", {}),
                        "timestamp": data.get("metadata", {}).get("timestamp", ""),
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")

    # Sort by version
    versions.sort(key=lambda x: x["model"].get("version", "0.0.0"))

    return {
        "model_prefix": model_prefix,
        "versions": versions,
        "progression": [
            {
                "version": v["model"].get("version", "?"),
                "mean_f1": v["summary"].get("mean_f1", 0.0),
                "timestamp": v["timestamp"],
            }
            for v in versions
        ],
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare OmniDocBench benchmark results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--baseline",
        type=str,
        help="Baseline model ID for comparison",
    )
    parser.add_argument(
        "--compare",
        type=str,
        help="Model ID to compare against baseline",
    )
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of model IDs to compare",
    )
    parser.add_argument(
        "--progression",
        type=str,
        help="Track progression for model prefix (e.g., resnet18_student)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory containing benchmark results",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for report",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    # Progression tracking mode
    if args.progression:
        progression = track_progression(args.progression, args.results_dir)

        print(f"\nProgression for {args.progression}:")
        print("-" * 50)
        for p in progression["progression"]:
            print(f"  v{p['version']}: Mean F1 = {p['mean_f1']:.3f}")
        print("-" * 50)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(progression, f, indent=2)
            print(f"Saved to {args.output}")

        return 0

    # Comparison mode
    if args.baseline and args.compare:
        baseline_results = load_results(args.baseline, args.results_dir)
        current_results = load_results(args.compare, args.results_dir)

        if not baseline_results:
            print(f"Error: No results found for baseline '{args.baseline}'")
            return 1
        if not current_results:
            print(f"Error: No results found for '{args.compare}'")
            return 1

        comparison = compare_models(baseline_results, current_results)

    elif args.models:
        model_ids = [m.strip() for m in args.models.split(",")]
        if len(model_ids) < 2:
            print("Error: --models requires at least 2 model IDs")
            return 1

        # Use first as baseline, last as current
        baseline_results = load_results(model_ids[0], args.results_dir)
        current_results = load_results(model_ids[-1], args.results_dir)

        if not baseline_results:
            print(f"Error: No results found for '{model_ids[0]}'")
            return 1
        if not current_results:
            print(f"Error: No results found for '{model_ids[-1]}'")
            return 1

        comparison = compare_models(baseline_results, current_results)

    else:
        print("Error: Specify --baseline and --compare, or --models, or --progression")
        return 1

    # Generate output
    if args.output_format == "text":
        output = generate_comparison_table(comparison)
    elif args.output_format == "markdown":
        output = generate_markdown_report(comparison)
    else:
        output = json.dumps(comparison, indent=2, default=str)

    # Print or save
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved report to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
