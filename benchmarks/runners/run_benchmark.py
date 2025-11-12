"""Main benchmark runner.

Executes full benchmarks based on registry configuration.

Usage:
    python -m benchmarks.runners.run_benchmark --suite doclaynet-layout-full
    python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

SPDX-License-Identifier: Apache-2.0
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from benchmarks.adapters import load_adapter
from benchmarks.scorers.aggregate_scorer import AggregateScorer


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load benchmark registry from YAML.

    Args:
        registry_path: Path to registry.yml

    Returns:
        Registry dictionary
    """
    with open(registry_path) as f:
        return yaml.safe_load(f)


def get_suite_config(registry: dict[str, Any], suite_name: str) -> dict[str, Any]:
    """Get configuration for a specific suite.

    Args:
        registry: Registry dictionary
        suite_name: Name of the suite

    Returns:
        Suite configuration

    Raises:
        ValueError: If suite not found
    """
    for suite in registry["suites"]:
        if suite["name"] == suite_name:
            return suite

    available = [s["name"] for s in registry["suites"]]
    raise ValueError(f"Suite '{suite_name}' not found. Available suites: {available}")


def get_data_dir() -> Path:
    """Get data directory from environment or default.

    Returns:
        Path to data directory
    """
    data_dir = os.getenv("BENCHMARKS_DATA_DIR")
    if data_dir:
        return Path(data_dir)

    # Default to project root / data
    return project_root / "data" / "benchmarks"


def get_output_dir() -> Path:
    """Get output directory from environment or default.

    Returns:
        Path to output directory
    """
    output_dir = os.getenv("BENCHMARKS_OUTPUT_DIR")
    if output_dir:
        return Path(output_dir)

    # Default to project root / reports
    return project_root / "reports"


def run_iqa_benchmark(
    suite_config: dict[str, Any],
    adapter: Any,
    scorer: AggregateScorer,
) -> None:
    """Run IQA benchmark.

    Args:
        suite_config: Suite configuration
        adapter: Dataset adapter
        scorer: Result scorer
    """
    # Import and delegate to task plugin
    from benchmarks.tasks.iqa import run_iqa_benchmark as run_iqa_task

    run_iqa_task(adapter, suite_config, scorer)


def run_layout_benchmark(
    suite_config: dict[str, Any],
    adapter: Any,
    scorer: AggregateScorer,
) -> None:
    """Run layout detection benchmark.

    Args:
        suite_config: Suite configuration
        adapter: Dataset adapter
        scorer: Result scorer
    """
    print("Running layout detection benchmark")
    print(f"  Classes: {len(adapter.classes)}")

    # For now, this is a placeholder
    # Actual implementation would:
    # 1. Run inference with layout detection model
    # 2. Collect predictions
    # 3. Calculate mAP and per-class AP

    print("⚠ Layout benchmark not fully implemented yet (requires model inference)")
    print("  This is a placeholder that will be extended in Phase 2")


def run_benchmark(
    suite_name: str,
    registry_path: Path | None = None,
    output_dir: Path | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a benchmark suite.

    Args:
        suite_name: Name of the suite to run
        registry_path: Path to registry.yml (default: benchmarks/registry.yml)
        output_dir: Output directory for results
        data_dir: Data directory for datasets

    Returns:
        Dictionary with results
    """
    # Load registry
    if registry_path is None:
        registry_path = project_root / "benchmarks" / "registry.yml"
    registry = load_registry(registry_path)

    # Get suite configuration
    suite_config = get_suite_config(registry, suite_name)

    # Get directories
    if data_dir is None:
        data_dir = get_data_dir()
    if output_dir is None:
        output_dir = get_output_dir()

    print(f"=== Running Benchmark: {suite_name} ===")
    print(f"Task: {suite_config['task']}")
    print(f"Dataset: {suite_config['dataset']}")
    print(f"Split: {suite_config['split']}")
    print()

    # Load dataset adapter
    dataset_name = suite_config["dataset"]
    split = suite_config["split"]
    dataset_dir = data_dir / dataset_name

    print(f"Loading dataset from: {dataset_dir}")

    try:
        # Enable automatic generation for synthetic datasets
        download = dataset_name == "synthetic_iqa"

        adapter = load_adapter(
            dataset_name,
            data_dir=dataset_dir,
            split=split,
            download=download,
        )
    except Exception as e:
        print(f"✗ Failed to load dataset: {e}")
        return {"error": str(e)}

    # Check if this is a smoke test subset
    smoke_subset = suite_config.get("smoke_subset")
    if smoke_subset is not None and isinstance(smoke_subset, int):
        print(f"⚠ Using subset: {smoke_subset} samples")
        adapter = adapter.get_subset(smoke_subset, seed=registry["defaults"]["seed"])

    print(f"Loaded {len(adapter)} samples")
    print()

    # Initialize scorer
    scorer = AggregateScorer(suite_name, suite_config["task"])

    # Run task-specific benchmark
    task_type = suite_config["task"]

    if task_type == "iqa":
        run_iqa_benchmark(suite_config, adapter, scorer)
    elif task_type == "layout":
        run_layout_benchmark(suite_config, adapter, scorer)
    else:
        print(f"⚠ Task type '{task_type}' not implemented yet")
        return {"error": f"Task type '{task_type}' not implemented"}

    # Save results
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    suite_output_dir = output_dir / suite_name / timestamp
    scorer.save_results(suite_output_dir)

    print()
    print("=== Results ===")
    print(f"Saved to: {suite_output_dir}")
    print()
    print(scorer.generate_summary(targets=suite_config.get("target")))

    return scorer.compute_aggregates()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run benchmarks for image preprocessing detector"
    )
    parser.add_argument(
        "--suite",
        required=True,
        help="Name of the benchmark suite to run (from registry.yml)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        help="Path to registry.yml (default: benchmarks/registry.yml)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results (default: $BENCHMARKS_OUTPUT_DIR or reports/)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data directory for datasets (default: $BENCHMARKS_DATA_DIR or data/benchmarks/)",
    )

    args = parser.parse_args()

    try:
        results = run_benchmark(
            args.suite,
            registry_path=args.registry,
            output_dir=args.output_dir,
            data_dir=args.data_dir,
        )

        if "error" in results:
            print(f"\n✗ Benchmark failed: {results['error']}")
            return 1

        print("\n✓ Benchmark completed successfully")
        return 0

    except Exception as e:
        print(f"\n✗ Benchmark failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
