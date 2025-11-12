"""Aggregate scorer for combining results across samples.

Collects metrics from individual samples and computes aggregate statistics.

SPDX-License-Identifier: Apache-2.0
"""

from datetime import UTC
from pathlib import Path
from typing import Any

import numpy as np


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

    def generate_summary(self, targets: dict[str, float] | None = None) -> str:
        """Generate human-readable summary.

        Args:
            targets: Optional dict of metric name -> target value

        Returns:
            Markdown-formatted summary
        """
        aggregates = self.compute_aggregates()

        meta = aggregates.pop("_meta") if "_meta" in aggregates else {}

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
            if not isinstance(stats, dict):
                continue

            mean = stats["mean"]
            std = stats["std"]
            min_val = stats["min"]
            max_val = stats["max"]

            # Check against target
            target = targets.get(metric_name) if targets else None
            if target is not None:
                # Determine if lower or higher is better based on metric name
                lower_is_better = any(
                    x in metric_name.lower() for x in ["rmse", "mae", "error", "ber"]
                )
                if lower_is_better:
                    status = "✓ PASS" if mean <= target else "✗ FAIL"
                else:
                    status = "✓ PASS" if mean >= target else "✗ FAIL"
                target_str = f"{target:.3f}"
            else:
                status = "—"
                target_str = "—"

            lines.append(
                f"| {metric_name} | {mean:.3f} | {std:.3f} | {min_val:.3f} | "
                f"{max_val:.3f} | {target_str} | {status} |"
            )

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
