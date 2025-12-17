"""Leaderboard generator for Arena benchmark results.

This module generates human-readable leaderboards in Markdown and HTML
formats, supporting filtering by model family, variant type, and metric.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from image_preprocessing_detector.labeling.arena.metrics import (
    ArenaMetrics,
)
from image_preprocessing_detector.labeling.arena.schemas import BenchmarkResult
from image_preprocessing_detector.utils.datetime_compat import UTC

logger = structlog.get_logger(__name__)


@dataclass
class LeaderboardEntry:
    """Single entry in the leaderboard.

    Attributes:
        rank: Position in the leaderboard.
        model_name: Display name for the model.
        model_id: Full model identifier.
        variant: Model variant (base, int8, int4, finetuned).
        metrics: ArenaMetrics for this model.
        run_id: Benchmark run identifier.
        timestamp: When the benchmark was run.
        metadata: Additional metadata.
    """

    rank: int
    model_name: str
    model_id: str
    variant: str
    metrics: ArenaMetrics
    run_id: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rank": self.rank,
            "model_name": self.model_name,
            "model_id": self.model_id,
            "variant": self.variant,
            "metrics": self.metrics.to_dict(),
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class LeaderboardConfig:
    """Configuration for leaderboard generation.

    Attributes:
        title: Leaderboard title.
        description: Optional description text.
        sort_by: Metric to sort by (e.g., "aggregate.plcc").
        filter_variant: Only include specific variants.
        filter_family: Only include specific model families.
        max_entries: Maximum number of entries to show.
        show_timestamps: Whether to show run timestamps.
        show_run_ids: Whether to show run IDs.
        decimal_places: Number of decimal places for metrics.
    """

    title: str = "DIQA-5000 Benchmark Leaderboard"
    description: str | None = None
    sort_by: str = "aggregate.plcc"
    filter_variant: list[str] | None = None
    filter_family: list[str] | None = None
    max_entries: int | None = None
    show_timestamps: bool = True
    show_run_ids: bool = False
    decimal_places: int = 4


class LeaderboardGenerator:
    """Generate leaderboards from benchmark results.

    Example:
        >>> generator = LeaderboardGenerator()
        >>> generator.add_result(result1)
        >>> generator.add_result(result2)
        >>> markdown = generator.to_markdown()
        >>> generator.to_html("leaderboard.html")
    """

    def __init__(self, config: LeaderboardConfig | None = None) -> None:
        """Initialize the generator.

        Args:
            config: Leaderboard configuration.
        """
        self._config = config or LeaderboardConfig()
        self._results: dict[str, BenchmarkResult] = {}
        self._entries: list[LeaderboardEntry] = []

    @property
    def config(self) -> LeaderboardConfig:
        """Get the current configuration."""
        return self._config

    def add_result(
        self, result: BenchmarkResult, _model_name: str | None = None
    ) -> None:
        """Add a benchmark result to the leaderboard.

        Args:
            result: BenchmarkResult to add.
            _model_name: Optional display name (defaults to model_id). Reserved for future use.
        """
        if result.status.value != "completed":
            logger.warning(
                "skipping_incomplete_result",
                run_id=result.run_id,
                status=result.status.value,
            )
            return

        model_id = result.model_spec.get("id", "unknown")
        self._results[result.run_id] = result

        logger.debug(
            "added_result",
            run_id=result.run_id,
            model_id=model_id,
        )

    def add_results_from_directory(self, directory: Path | str) -> int:
        """Load all results from a directory.

        Args:
            directory: Directory containing result JSON files.

        Returns:
            Number of results loaded.
        """
        directory = Path(directory)
        count = 0

        for json_file in directory.glob("result_*.json"):
            try:
                result = BenchmarkResult.from_json(json_file)
                self.add_result(result)
                count += 1
            except Exception as e:
                logger.warning(
                    "failed_to_load_result",
                    path=str(json_file),
                    error=str(e),
                )

        logger.info("loaded_results", count=count, directory=str(directory))
        return count

    def _build_entries(self) -> list[LeaderboardEntry]:
        """Build and sort leaderboard entries."""
        entries: list[LeaderboardEntry] = []

        for run_id, result in self._results.items():
            # Apply filters
            variant = result.model_spec.get("variant", "base")
            if (
                self._config.filter_variant
                and variant not in self._config.filter_variant
            ):
                continue

            model_id = result.model_spec.get("id", "unknown")
            if self._config.filter_family:
                family_match = any(f in model_id for f in self._config.filter_family)
                if not family_match:
                    continue

            # Reconstruct ArenaMetrics from dict
            try:
                metrics = self._reconstruct_metrics(result.metrics)
            except Exception as e:
                logger.warning(
                    "failed_to_reconstruct_metrics",
                    run_id=run_id,
                    error=str(e),
                )
                continue

            # Extract model name from ID
            model_name = self._extract_model_name(model_id)

            entry = LeaderboardEntry(
                rank=0,  # Will be set after sorting
                model_name=model_name,
                model_id=model_id,
                variant=variant,
                metrics=metrics,
                run_id=run_id,
                timestamp=result.execution.timestamp,
                metadata={
                    "hardware": result.execution.hardware,
                    "duration_seconds": result.execution.duration_seconds,
                    "num_samples": result.dataset.num_samples,
                },
            )
            entries.append(entry)

        # Sort entries
        entries = self._sort_entries(entries)

        # Assign ranks
        for i, entry in enumerate(entries, 1):
            entry.rank = i

        # Apply max_entries limit
        if self._config.max_entries:
            entries = entries[: self._config.max_entries]

        return entries

    def _reconstruct_metrics(self, metrics_dict: dict[str, Any]) -> ArenaMetrics:
        """Reconstruct ArenaMetrics from dictionary."""
        from image_preprocessing_detector.labeling.arena.metrics import DimensionMetrics

        def make_dim(d: dict[str, Any]) -> DimensionMetrics:
            return DimensionMetrics(
                plcc=d["plcc"],
                srcc=d["srcc"],
                mae=d["mae"],
                rmse=d["rmse"],
                num_samples=d.get("num_samples", 0),
            )

        return ArenaMetrics(
            overall=make_dim(metrics_dict["overall"]),
            sharpness=make_dim(metrics_dict["sharpness"]),
            color=make_dim(metrics_dict["color"]),
        )

    def _sort_entries(self, entries: list[LeaderboardEntry]) -> list[LeaderboardEntry]:
        """Sort entries by the configured metric."""
        dimension, metric = self._config.sort_by.split(".")

        # Higher is better for correlation, lower for error
        reverse = metric in ("plcc", "srcc")

        def get_value(entry: LeaderboardEntry) -> float:
            dim_metrics = getattr(entry.metrics, dimension)
            return getattr(dim_metrics, metric)

        return sorted(entries, key=get_value, reverse=reverse)

    def _extract_model_name(self, model_id: str) -> str:
        """Extract a display name from model ID."""
        # Handle HuggingFace format: org/model-name
        if "/" in model_id:
            return model_id.split("/")[-1]
        # Handle path format
        return Path(model_id).stem

    def to_markdown(self, config: LeaderboardConfig | None = None) -> str:
        """Generate Markdown leaderboard.

        Args:
            config: Optional config override.

        Returns:
            Markdown formatted leaderboard.
        """
        cfg = config or self._config
        entries = self._build_entries()
        dp = cfg.decimal_places

        lines = [
            f"# {cfg.title}",
            "",
        ]

        if cfg.description:
            lines.extend([cfg.description, ""])

        lines.extend(
            [
                f"*Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
                f"*Sort: {cfg.sort_by} (higher is better for correlation, lower for error)*",
                "",
            ]
        )

        # Summary table
        lines.extend(
            [
                "## Rankings",
                "",
                "| Rank | Model | Variant | PLCC | SRCC | MAE | RMSE |",
                "|------|-------|---------|------|------|-----|------|",
            ]
        )

        for entry in entries:
            agg = entry.metrics.aggregate
            lines.append(
                f"| {entry.rank} | {entry.model_name} | {entry.variant} | "
                f"{agg.plcc:.{dp}f} | {agg.srcc:.{dp}f} | "
                f"{agg.mae:.{dp}f} | {agg.rmse:.{dp}f} |"
            )

        # Detailed metrics per dimension
        lines.extend(
            [
                "",
                "## Detailed Metrics",
                "",
            ]
        )

        for entry in entries:
            lines.extend(
                [
                    f"### {entry.rank}. {entry.model_name}",
                    "",
                    f"- **Model ID**: `{entry.model_id}`",
                    f"- **Variant**: {entry.variant}",
                ]
            )

            if cfg.show_run_ids:
                lines.append(f"- **Run ID**: `{entry.run_id}`")

            if cfg.show_timestamps:
                lines.append(f"- **Timestamp**: {entry.timestamp}")

            lines.extend(
                [
                    "",
                    "| Dimension | PLCC | SRCC | MAE | RMSE |",
                    "|-----------|------|------|-----|------|",
                    f"| Overall | {entry.metrics.overall.plcc:.{dp}f} | "
                    f"{entry.metrics.overall.srcc:.{dp}f} | "
                    f"{entry.metrics.overall.mae:.{dp}f} | "
                    f"{entry.metrics.overall.rmse:.{dp}f} |",
                    f"| Sharpness | {entry.metrics.sharpness.plcc:.{dp}f} | "
                    f"{entry.metrics.sharpness.srcc:.{dp}f} | "
                    f"{entry.metrics.sharpness.mae:.{dp}f} | "
                    f"{entry.metrics.sharpness.rmse:.{dp}f} |",
                    f"| Color | {entry.metrics.color.plcc:.{dp}f} | "
                    f"{entry.metrics.color.srcc:.{dp}f} | "
                    f"{entry.metrics.color.mae:.{dp}f} | "
                    f"{entry.metrics.color.rmse:.{dp}f} |",
                    f"| **Aggregate** | **{entry.metrics.aggregate.plcc:.{dp}f}** | "
                    f"**{entry.metrics.aggregate.srcc:.{dp}f}** | "
                    f"**{entry.metrics.aggregate.mae:.{dp}f}** | "
                    f"**{entry.metrics.aggregate.rmse:.{dp}f}** |",
                    "",
                ]
            )

        return "\n".join(lines)

    def to_html(
        self,
        output_path: Path | str | None = None,
        config: LeaderboardConfig | None = None,
    ) -> str:
        """Generate HTML leaderboard.

        Args:
            output_path: Optional path to save HTML file.
            config: Optional config override.

        Returns:
            HTML formatted leaderboard.
        """
        cfg = config or self._config
        entries = self._build_entries()
        dp = cfg.decimal_places

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cfg.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4a90d9;
            padding-bottom: 10px;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #4a90d9;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .rank-1 {{
            background: linear-gradient(90deg, #ffd700 0%, transparent 100%);
        }}
        .rank-2 {{
            background: linear-gradient(90deg, #c0c0c0 0%, transparent 100%);
        }}
        .rank-3 {{
            background: linear-gradient(90deg, #cd7f32 0%, transparent 100%);
        }}
        .variant {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .variant-base {{ background: #e3f2fd; color: #1565c0; }}
        .variant-int8 {{ background: #e8f5e9; color: #2e7d32; }}
        .variant-int4 {{ background: #fff3e0; color: #e65100; }}
        .variant-finetuned {{ background: #f3e5f5; color: #7b1fa2; }}
        .metric {{
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.95em;
        }}
        .metric-good {{ color: #2e7d32; }}
        .metric-bad {{ color: #c62828; }}
        .details {{
            margin-top: 30px;
        }}
        .model-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .model-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .model-info {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <h1>{cfg.title}</h1>
    <div class="meta">
        Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}<br>
        Sort: {cfg.sort_by}
    </div>
"""

        if cfg.description:
            html += f"    <p>{cfg.description}</p>\n"

        # Main rankings table
        html += """
    <h2>Rankings</h2>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Variant</th>
                <th>PLCC</th>
                <th>SRCC</th>
                <th>MAE</th>
                <th>RMSE</th>
            </tr>
        </thead>
        <tbody>
"""

        for entry in entries:
            agg = entry.metrics.aggregate
            rank_class = f"rank-{entry.rank}" if entry.rank <= 3 else ""
            variant_class = f"variant-{entry.variant}"

            html += f"""            <tr class="{rank_class}">
                <td><strong>{entry.rank}</strong></td>
                <td>{entry.model_name}</td>
                <td><span class="variant {variant_class}">{entry.variant}</span></td>
                <td class="metric">{agg.plcc:.{dp}f}</td>
                <td class="metric">{agg.srcc:.{dp}f}</td>
                <td class="metric">{agg.mae:.{dp}f}</td>
                <td class="metric">{agg.rmse:.{dp}f}</td>
            </tr>
"""

        html += """        </tbody>
    </table>

    <div class="details">
        <h2>Detailed Results</h2>
"""

        # Detailed model cards
        for entry in entries:
            html += f"""
        <div class="model-card">
            <h3>{entry.rank}. {entry.model_name}</h3>
            <div class="model-info">
                <strong>Model ID:</strong> <code>{entry.model_id}</code><br>
                <strong>Variant:</strong> <span class="variant variant-{entry.variant}">{entry.variant}</span>
"""

            if cfg.show_run_ids:
                html += f"                <br><strong>Run ID:</strong> <code>{entry.run_id}</code>\n"

            if cfg.show_timestamps:
                html += f"                <br><strong>Timestamp:</strong> {entry.timestamp}\n"

            html += """            </div>
            <table>
                <thead>
                    <tr>
                        <th>Dimension</th>
                        <th>PLCC</th>
                        <th>SRCC</th>
                        <th>MAE</th>
                        <th>RMSE</th>
                    </tr>
                </thead>
                <tbody>
"""

            for dim_name, dim_metrics in [
                ("Overall", entry.metrics.overall),
                ("Sharpness", entry.metrics.sharpness),
                ("Color", entry.metrics.color),
                ("Aggregate", entry.metrics.aggregate),
            ]:
                style = "font-weight: bold;" if dim_name == "Aggregate" else ""
                html += f"""                    <tr style="{style}">
                        <td>{dim_name}</td>
                        <td class="metric">{dim_metrics.plcc:.{dp}f}</td>
                        <td class="metric">{dim_metrics.srcc:.{dp}f}</td>
                        <td class="metric">{dim_metrics.mae:.{dp}f}</td>
                        <td class="metric">{dim_metrics.rmse:.{dp}f}</td>
                    </tr>
"""

            html += """                </tbody>
            </table>
        </div>
"""

        html += """    </div>
</body>
</html>
"""

        if output_path:
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info("html_saved", path=str(output_path))

        return html

    def to_json(self, output_path: Path | str | None = None) -> str:
        """Export leaderboard as JSON.

        Args:
            output_path: Optional path to save JSON file.

        Returns:
            JSON string representation.
        """
        entries = self._build_entries()

        data = {
            "title": self._config.title,
            "generated_at": datetime.now(UTC).isoformat(),
            "sort_by": self._config.sort_by,
            "entries": [entry.to_dict() for entry in entries],
        }

        json_str = json.dumps(data, indent=2, default=str)

        if output_path:
            Path(output_path).write_text(json_str, encoding="utf-8")
            logger.info("json_saved", path=str(output_path))

        return json_str

    def save_all(
        self,
        output_dir: Path | str,
        basename: str = "leaderboard",
    ) -> dict[str, Path]:
        """Save leaderboard in all formats.

        Args:
            output_dir: Directory to save files.
            basename: Base filename (without extension).

        Returns:
            Dict mapping format to file path.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}

        # Markdown
        md_path = output_dir / f"{basename}.md"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        paths["markdown"] = md_path

        # HTML
        html_path = output_dir / f"{basename}.html"
        self.to_html(html_path)
        paths["html"] = html_path

        # JSON
        json_path = output_dir / f"{basename}.json"
        self.to_json(json_path)
        paths["json"] = json_path

        logger.info(
            "leaderboard_saved",
            output_dir=str(output_dir),
            formats=list(paths.keys()),
        )

        return paths


def generate_leaderboard(
    results_dir: Path | str,
    output_dir: Path | str,
    sort_by: str = "aggregate.plcc",
    title: str = "DIQA-5000 Benchmark Leaderboard",
    filter_variant: list[str] | None = None,
) -> dict[str, Path]:
    """Convenience function to generate leaderboard from results directory.

    Args:
        results_dir: Directory containing result JSON files.
        output_dir: Directory to save leaderboard files.
        sort_by: Metric to sort by.
        title: Leaderboard title.
        filter_variant: Optional variant filter.

    Returns:
        Dict mapping format to file path.

    Example:
        >>> paths = generate_leaderboard(
        ...     results_dir="./results",
        ...     output_dir="./leaderboard",
        ...     sort_by="aggregate.plcc",
        ... )
        >>> print(f"HTML: {paths['html']}")
    """
    config = LeaderboardConfig(
        title=title,
        sort_by=sort_by,
        filter_variant=filter_variant,
    )

    generator = LeaderboardGenerator(config)
    generator.add_results_from_directory(results_dir)

    return generator.save_all(output_dir)
