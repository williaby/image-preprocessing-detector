"""Aggregate scorer for combining results across samples.

Collects metrics from individual samples and computes aggregate statistics.

"""

import sys
from pathlib import Path
from typing import Any

import numpy as np

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from image_preprocessing_detector.utils.datetime_compat import UTC


class AggregateScorer:
    """Aggregate scorer for benchmark results.

    Collects results from multiple samples and computes summary statistics.
    """

    def __init__(self, suite_name: str, task_type: str) -> None:
        """Initialize aggregate scorer.

        Args:
            suite_name: Name of the benchmark suite
            task_type: Type of task (iqa, layout, etc.)
        """
        self.suite_name = suite_name
        self.task_type = task_type
        self.results: list[dict[str, Any]] = []

    def add_result(self, sample_id: str, metrics: dict[str, Any]) -> None:
        """Add result for a single sample.

        Args:
            sample_id: Sample identifier
            metrics: Dictionary of metric name -> value
        """
        self.results.append({"sample_id": sample_id, "metrics": metrics})

    def compute_aggregates(self) -> dict[str, Any]:
        """Compute aggregate statistics across all samples.

        Returns:
            Dictionary with aggregate metrics
        """
        if not self.results:
            return {"error": "No results to aggregate"}

        # Collect all metric values
        metric_values: dict[str, list[float]] = {}

        for result in self.results:
            for metric_name, value in result["metrics"].items():
                # Skip nested dicts (like per_class_AP)
                if isinstance(value, int | float | np.number):
                    if metric_name not in metric_values:
                        metric_values[metric_name] = []
                    metric_values[metric_name].append(float(value))

        # Compute statistics
        aggregates = {}
        for metric_name, values in metric_values.items():
            arr = np.array(values)
            aggregates[metric_name] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "median": float(np.median(arr)),
                "count": len(arr),
            }

        aggregates["_meta"] = {
            "suite_name": self.suite_name,
            "task_type": self.task_type,
            "num_samples": len(self.results),
        }

        return aggregates

    def _is_lower_better(self, metric_name: str) -> bool:
        """Check if lower values are better for the given metric.

        Args:
            metric_name: Name of the metric

        Returns:
            True if lower values indicate better performance
        """
        lower_better_indicators = ("rmse", "mae", "error", "ber")
        return any(x in metric_name.lower() for x in lower_better_indicators)

    def _evaluate_target(
        self, metric_name: str, mean: float, target: float | None
    ) -> tuple[str, str]:
        """Evaluate a metric against its target.

        Args:
            metric_name: Name of the metric
            mean: Mean value of the metric
            target: Target value (or None if no target)

        Returns:
            Tuple of (target_str, status_str)
        """
        if target is None:
            return "—", "—"

        lower_is_better = self._is_lower_better(metric_name)
        passed = mean <= target if lower_is_better else mean >= target
        status = "✓ PASS" if passed else "✗ FAIL"
        return f"{target:.3f}", status

    def _format_metric_row(
        self,
        metric_name: str,
        stats: dict[str, Any],
        targets: dict[str, float] | None,
    ) -> str:
        """Format a single metric row for the summary table.

        Args:
            metric_name: Name of the metric
            stats: Statistics dictionary with mean, std, min, max
            targets: Optional targets dictionary

        Returns:
            Formatted table row string
        """
        mean = stats["mean"]
        target = targets.get(metric_name) if targets else None
        target_str, status = self._evaluate_target(metric_name, mean, target)

        return (
            f"| {metric_name} | {mean:.3f} | {stats['std']:.3f} | "
            f"{stats['min']:.3f} | {stats['max']:.3f} | {target_str} | {status} |"
        )

    def generate_summary(self, targets: dict[str, float] | None = None) -> str:
        """Generate human-readable summary.

        Args:
            targets: Optional dict of metric name -> target value

        Returns:
            Markdown-formatted summary
        """
        aggregates = self.compute_aggregates()
        meta = aggregates.pop("_meta", {})

        lines = [
            f"# Benchmark Summary: {self.suite_name}",
            "",
            f"**Task**: {self.task_type}",
            f"**Samples**: {meta.get('num_samples', 0)}",
            "",
            "## Metrics",
            "",
            "| Metric | Mean | Std | Min | Max | Target | Status |",
            "|--------|------|-----|-----|-----|--------|--------|",
        ]

        for metric_name, stats in aggregates.items():
            if isinstance(stats, dict):
                lines.append(self._format_metric_row(metric_name, stats, targets))

        return "\n".join(lines)

    def save_results(self, output_dir: Path) -> None:
        """Save results to disk.

        Args:
            output_dir: Directory to save results
        """
        import json
        from datetime import datetime

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save raw results
        results_path = output_dir / "results.json"
        with open(results_path, "w") as f:
            json.dump(
                {
                    "suite_name": self.suite_name,
                    "task_type": self.task_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "results": self.results,
                    "aggregates": self.compute_aggregates(),
                },
                f,
                indent=2,
            )

        # Save summary
        summary_path = output_dir / "summary.md"
        with open(summary_path, "w") as f:
            f.write(self.generate_summary())

    def __len__(self) -> int:
        """Return number of results."""
        return len(self.results)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AggregateScorer(suite={self.suite_name!r}, "
            f"task={self.task_type!r}, results={len(self)})"
        )
