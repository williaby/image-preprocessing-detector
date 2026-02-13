"""Arena CLI for benchmark execution and leaderboard management.

This module provides the command-line interface for the Benchmarking Arena,
supporting model evaluation, leaderboard generation, and result validation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import structlog

from image_preprocessing_detector.labeling.arena.datasets.diqa5000 import (
    DIQA5000Dataset,
)
from image_preprocessing_detector.labeling.arena.inference.base import InferenceConfig
from image_preprocessing_detector.labeling.arena.leaderboard import (
    LeaderboardConfig,
    LeaderboardGenerator,
)
from image_preprocessing_detector.labeling.arena.runner import ArenaRunner, RunConfig
from image_preprocessing_detector.labeling.arena.schemas import (
    BenchmarkResult,
    ReproducibilityManifest,
)
from image_preprocessing_detector.labeling.model_spec import ModelSpec

logger = structlog.get_logger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def arena(ctx: click.Context, verbose: bool) -> None:
    r"""Benchmarking Arena - Model evaluation on DIQA-5000.

    The Arena provides standardized, repeatable evaluation of document
    quality assessment models.

    \b
    Example usage:
        arena run --model model.yaml --dataset /data/diqa5000
        arena leaderboard --results ./results --output ./leaderboard
        arena validate --manifest manifest.yaml
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(min_level=10),
        )


@arena.command()
@click.option(
    "--model",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to model spec YAML/JSON file",
)
@click.option(
    "--dataset",
    "-d",
    required=True,
    type=click.Path(exists=True),
    help="Path to DIQA-5000 dataset directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./arena_results",
    help="Output directory for results",
)
@click.option(
    "--split",
    "-s",
    type=click.Choice(["train", "val", "test"]),
    default="test",
    help="Dataset split to use",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=8,
    help="Batch size for inference",
)
@click.option(
    "--device",
    type=str,
    default="cuda",
    help="Device to run on (cpu, cuda, cuda:0)",
)
@click.option(
    "--seed",
    type=int,
    default=42,
    help="Random seed for reproducibility",
)
@click.option(
    "--max-samples",
    type=int,
    default=None,
    help="Maximum number of samples (for testing)",
)
@click.option(
    "--save-samples",
    is_flag=True,
    help="Save per-sample predictions",
)
@click.option(
    "--no-manifest",
    is_flag=True,
    help="Skip reproducibility manifest generation",
)
@click.pass_context
def run(
    ctx: click.Context,
    model: str,
    dataset: str,
    output: str,
    split: str,
    batch_size: int,
    device: str,
    seed: int,
    max_samples: int | None,
    save_samples: bool,
    no_manifest: bool,
) -> None:
    r"""Run benchmark evaluation on a model.

    \b
    Loads the model specification, runs inference on the DIQA-5000 test split,
    computes metrics (PLCC, SRCC, MAE, RMSE), and saves results.

    \b
    Example:
        arena run -m model.yaml -d /data/diqa5000 -o ./results
    """
    ctx.obj.get("verbose", False)

    click.echo(f"Loading model spec from: {model}")

    # Load model spec
    model_path = Path(model)
    if model_path.suffix in (".yaml", ".yml"):
        spec = ModelSpec.from_yaml(model_path)
    else:
        spec = ModelSpec.from_json(model_path)

    click.echo(f"Model: {spec.id} ({spec.variant.value})")

    # Load dataset
    click.echo(f"Loading dataset from: {dataset}")
    dataset_obj = DIQA5000Dataset(dataset, split=split)
    click.echo(
        f"Dataset: {dataset_obj.name}, Split: {split}, Samples: {len(dataset_obj)}"
    )

    # Create configs
    inference_config = InferenceConfig(
        batch_size=batch_size,
        device=device,
        seed=seed,
        deterministic=True,
    )

    run_config = RunConfig(
        output_dir=Path(output),
        save_sample_results=save_samples,
        save_manifest=not no_manifest,
        max_samples=max_samples,
    )

    # Run benchmark
    click.echo("\nStarting benchmark...")
    runner = ArenaRunner(inference_config, run_config)

    with click.progressbar(length=100, label="Running inference") as bar:
        result = runner.run(spec, dataset_obj)
        bar.update(100)

    # Display results
    click.echo("\n" + "=" * 60)

    if result.status.value == "completed":
        click.secho("Benchmark COMPLETED", fg="green", bold=True)
        click.echo(f"Run ID: {result.run_id}")
        click.echo(f"Duration: {result.execution.duration_seconds:.2f}s")
        click.echo(f"Samples: {result.dataset.num_samples}")

        click.echo("\nAggregate Metrics:")
        agg = result.metrics.get("aggregate", {})
        click.echo(f"  PLCC: {agg.get('plcc', 0):.4f}")
        click.echo(f"  SRCC: {agg.get('srcc', 0):.4f}")
        click.echo(f"  MAE:  {agg.get('mae', 0):.4f}")
        click.echo(f"  RMSE: {agg.get('rmse', 0):.4f}")

        click.echo(f"\nResults saved to: {output}")
    else:
        click.secho("Benchmark FAILED", fg="red", bold=True)
        click.echo(f"Error: {result.error_message}")
        sys.exit(1)


@arena.command()
@click.option(
    "--results",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Directory containing result JSON files",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./leaderboard",
    help="Output directory for leaderboard files",
)
@click.option(
    "--sort-by",
    type=str,
    default="aggregate.plcc",
    help="Metric to sort by (e.g., aggregate.plcc, overall.srcc)",
)
@click.option(
    "--title",
    type=str,
    default="DIQA-5000 Benchmark Leaderboard",
    help="Leaderboard title",
)
@click.option(
    "--format",
    "-f",
    "formats",
    type=click.Choice(["all", "markdown", "html", "json"]),
    default="all",
    help="Output format(s)",
)
@click.option(
    "--filter-variant",
    type=str,
    multiple=True,
    help="Filter by variant (can specify multiple)",
)
@click.option(
    "--max-entries",
    type=int,
    default=None,
    help="Maximum entries to show",
)
@click.pass_context
def leaderboard(
    _ctx: click.Context,
    results: str,
    output: str,
    sort_by: str,
    title: str,
    formats: str,
    filter_variant: tuple[str, ...],
    max_entries: int | None,
) -> None:
    r"""Generate leaderboard from benchmark results.

    \b
    Reads all result files from a directory, ranks models by the specified
    metric, and generates leaderboard reports in Markdown, HTML, and JSON.

    \b
    Example:
        arena leaderboard -r ./results -o ./leaderboard --sort-by aggregate.plcc
    """
    click.echo(f"Loading results from: {results}")

    config = LeaderboardConfig(
        title=title,
        sort_by=sort_by,
        filter_variant=list(filter_variant) if filter_variant else None,
        max_entries=max_entries,
    )

    generator = LeaderboardGenerator(config)
    count = generator.add_results_from_directory(results)

    click.echo(f"Loaded {count} results")

    if count == 0:
        click.secho("No valid results found", fg="yellow")
        sys.exit(1)

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if formats == "all":
        paths = generator.save_all(output_dir)
        click.echo("\nGenerated files:")
        for fmt, path in paths.items():
            click.echo(f"  {fmt}: {path}")
    else:
        if formats == "markdown":
            path = output_dir / "leaderboard.md"
            path.write_text(generator.to_markdown(), encoding="utf-8")
        elif formats == "html":
            path = output_dir / "leaderboard.html"
            generator.to_html(path)
        elif formats == "json":
            path = output_dir / "leaderboard.json"
            generator.to_json(path)
        else:
            msg = f"Unknown format: {formats}"
            raise click.ClickException(msg)

        click.echo(f"Generated: {path}")

    click.secho("\nLeaderboard generated successfully!", fg="green")


@arena.command()
@click.option(
    "--manifest",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to reproducibility manifest",
)
@click.option(
    "--result",
    "-r",
    type=click.Path(exists=True),
    help="Path to result file to validate against",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on any mismatch",
)
@click.pass_context
def validate(
    _ctx: click.Context,
    manifest: str,
    result: str | None,
    strict: bool,
) -> None:
    r"""Validate benchmark reproducibility.

    \b
    Checks that a manifest contains valid configuration and optionally
    verifies that a result file matches the manifest's expected hash.

    \b
    Example:
        arena validate -m manifest.yaml -r result.json
    """
    click.echo(f"Loading manifest: {manifest}")

    manifest_obj = ReproducibilityManifest.from_yaml(manifest)

    click.echo(f"Run ID: {manifest_obj.run_id}")
    click.echo(f"Created: {manifest_obj.created_at}")
    click.echo(f"Result Hash: {manifest_obj.result_hash}")

    # Validate manifest fields
    issues = []

    if not manifest_obj.model.get("spec"):
        issues.append("Missing model spec")

    if not manifest_obj.dataset.get("name"):
        issues.append("Missing dataset name")

    if not manifest_obj.seeds:
        issues.append("Missing seeds")

    # Validate against result if provided
    if result:
        click.echo(f"\nValidating against result: {result}")

        result_obj = BenchmarkResult.from_json(result)
        computed_hash = result_obj.compute_content_hash()

        click.echo(f"Computed Hash: {computed_hash}")

        if computed_hash == manifest_obj.result_hash:
            click.secho("Hash MATCH", fg="green")
        else:
            click.secho("Hash MISMATCH", fg="red")
            issues.append(
                f"Hash mismatch: expected {manifest_obj.result_hash}, got {computed_hash}"
            )

        # Check run IDs
        if result_obj.run_id != manifest_obj.run_id:
            click.secho("Run ID mismatch", fg="yellow")
            issues.append(
                f"Run ID mismatch: expected {manifest_obj.run_id}, got {result_obj.run_id}"
            )

    # Report issues
    if issues:
        click.echo(f"\n{len(issues)} issue(s) found:")
        for issue in issues:
            click.echo(f"  - {issue}")

        if strict:
            sys.exit(1)
    else:
        click.secho("\nValidation PASSED", fg="green", bold=True)


@arena.command()
@click.option(
    "--result",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to result JSON file",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "json", "table"]),
    default="summary",
    help="Output format",
)
@click.pass_context
def show(
    _ctx: click.Context,
    result: str,
    output_format: str,
) -> None:
    r"""Display benchmark result details.

    \b
    Example:
        arena show -r result_abc123.json
        arena show -r result.json -f table
    """
    result_obj = BenchmarkResult.from_json(result)

    if output_format == "json":
        click.echo(json.dumps(result_obj.to_dict(), indent=2, default=str))
        return

    click.echo("=" * 60)
    click.echo(f"Run ID: {result_obj.run_id}")
    click.echo(f"Status: {result_obj.status.value}")
    click.echo("=" * 60)

    click.echo(f"\nModel: {result_obj.model_spec.get('id', 'unknown')}")
    click.echo(f"Variant: {result_obj.model_spec.get('variant', 'base')}")
    click.echo(f"Source: {result_obj.model_spec.get('source', 'unknown')}")

    click.echo(f"\nDataset: {result_obj.dataset.name}")
    click.echo(f"Split: {result_obj.dataset.split}")
    click.echo(f"Samples: {result_obj.dataset.num_samples}")

    click.echo(f"\nDuration: {result_obj.execution.duration_seconds:.2f}s")
    click.echo(f"Hardware: {result_obj.execution.hardware}")

    if output_format == "table":
        click.echo("\nMetrics:")
        click.echo("-" * 60)
        click.echo(
            f"{'Dimension':<12} {'PLCC':>10} {'SRCC':>10} {'MAE':>10} {'RMSE':>10}"
        )
        click.echo("-" * 60)

        for dim in ["overall", "sharpness", "color", "aggregate"]:
            m = result_obj.metrics.get(dim, {})
            click.echo(
                f"{dim:<12} {m.get('plcc', 0):>10.4f} {m.get('srcc', 0):>10.4f} "
                f"{m.get('mae', 0):>10.4f} {m.get('rmse', 0):>10.4f}"
            )
    else:
        click.echo("\nAggregate Metrics:")
        agg = result_obj.metrics.get("aggregate", {})
        click.echo(f"  PLCC: {agg.get('plcc', 0):.4f}")
        click.echo(f"  SRCC: {agg.get('srcc', 0):.4f}")
        click.echo(f"  MAE:  {agg.get('mae', 0):.4f}")
        click.echo(f"  RMSE: {agg.get('rmse', 0):.4f}")


@arena.command()
@click.option(
    "--results",
    "-r",
    required=True,
    type=click.Path(exists=True),
    multiple=True,
    help="Result files to compare (specify multiple)",
)
@click.option(
    "--metric",
    "-m",
    type=str,
    default="aggregate.plcc",
    help="Metric to compare",
)
@click.pass_context
def compare(
    _ctx: click.Context,
    results: tuple[str, ...],
    metric: str,
) -> None:
    r"""Compare multiple benchmark results.

    \b
    Example:
        arena compare -r result1.json -r result2.json -m aggregate.plcc
    """
    if len(results) < 2:
        click.echo("Need at least 2 results to compare")
        sys.exit(1)

    click.echo(f"Comparing {len(results)} results by {metric}")
    click.echo("=" * 60)

    # Load results
    loaded: list[tuple[str, BenchmarkResult]] = []
    for path in results:
        try:
            r = BenchmarkResult.from_json(path)
            loaded.append((path, r))
        except Exception as e:
            click.echo(f"Failed to load {path}: {e}")

    # Extract metric value
    dimension, metric_name = metric.split(".")

    def get_metric(r: BenchmarkResult) -> float:
        return float(r.metrics.get(dimension, {}).get(metric_name, 0))

    # Sort by metric
    reverse = metric_name in ("plcc", "srcc")
    loaded.sort(key=lambda x: get_metric(x[1]), reverse=reverse)

    # Display comparison
    click.echo(f"\n{'Rank':<6} {'Model':<30} {metric:>15}")
    click.echo("-" * 55)

    for i, (_path, r) in enumerate(loaded, 1):
        model_id = r.model_spec.get("id", "unknown")
        if len(model_id) > 28:
            model_id = "..." + model_id[-25:]
        value = get_metric(r)
        click.echo(f"{i:<6} {model_id:<30} {value:>15.4f}")

    # Show delta between best and worst
    if len(loaded) >= 2:
        best = get_metric(loaded[0][1])
        worst = get_metric(loaded[-1][1])
        delta = abs(best - worst)
        click.echo(f"\nDelta (best - worst): {delta:.4f}")


def main() -> None:
    """Entry point for the Arena CLI."""
    arena()


if __name__ == "__main__":
    main()
