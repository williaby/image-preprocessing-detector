#!/usr/bin/env python3
"""
Modular Benchmark Runner for OmniDocBench Evaluation.

Supports running any model from the registry against OmniDocBench,
with versioned result tracking for comparison.

Usage:
    # Run single model
    python scripts/omnidocbench_baseline/benchmark_runner.py --model classical_cv_baseline

    # Run model group
    python scripts/omnidocbench_baseline/benchmark_runner.py --group all_iqa_baselines

    # Run with sample limit
    python scripts/omnidocbench_baseline/benchmark_runner.py --model resnet18_student_baseline --limit 100

    # Compare multiple models
    python scripts/omnidocbench_baseline/benchmark_runner.py \\
        --models classical_cv_baseline,resnet18_student_baseline,resnet50_teacher_baseline
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.omnidocbench_baseline.models import ModelRegistry, load_model
from scripts.omnidocbench_baseline.models.base import BaseModel, ModelPrediction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Dataset Loading
# =============================================================================


def load_omnidocbench_dataset(token: str | None = None) -> Any:
    """Load OmniDocBench from HuggingFace.

    Args:
        token: HuggingFace API token

    Returns:
        HuggingFace Dataset object
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets library required. Install with: pip install datasets")
        sys.exit(1)

    logger.info("Loading OmniDocBench from HuggingFace...")
    token = token or os.getenv("HF_TOKEN")

    dataset = load_dataset(
        "opendatalab/OmniDocBench",
        token=token,
        trust_remote_code=True,
    )
    return dataset["train"]


def extract_ground_truth(record: dict[str, Any]) -> dict[str, Any]:
    """Extract ground truth from OmniDocBench record.

    Args:
        record: Dataset record

    Returns:
        Ground truth dict
    """
    page_info = record.get("page_info", {})
    layout_dets = record.get("layout_dets", [])
    page_attr = page_info.get("page_attribute", {})

    # Layout type mapping
    LAYOUT_MAPPING = {
        "single_column": "single_column",
        "double_column": "multi_column",
        "three_column": "three_column",
        "1andmore_column": "complex",
        "other_layout": "complex",
    }

    # Element categories
    TABLE_CATS = {"table"}
    FIGURE_CATS = {"figure", "figure_caption"}
    FORMULA_CATS = {"equation_isolated", "equation_caption"}

    categories = [det.get("category_type", "") for det in layout_dets if det]

    return {
        "layout_type": LAYOUT_MAPPING.get(
            page_attr.get("layout", "other_layout"), "unknown"
        ),
        "has_tables": sum(1 for c in categories if c in TABLE_CATS) > 0,
        "has_figures": sum(1 for c in categories if c in FIGURE_CATS) > 0,
        "has_dense_math": sum(1 for c in categories if c in FORMULA_CATS) >= 3,
        "fuzzy_scan": page_attr.get("fuzzy_scan", False),
        "watermark": page_attr.get("watermark", False),
        "colorful_background": page_attr.get("colorful_backgroud", False),  # typo in dataset
        "language": page_attr.get("language", "unknown"),
        "data_source": page_attr.get("data_source", "unknown"),
    }


def load_image_from_record(record: dict[str, Any]) -> np.ndarray | None:
    """Load image from dataset record.

    Args:
        record: Dataset record

    Returns:
        Image as BGR numpy array
    """
    try:
        import cv2
        from PIL import Image

        if "image" in record and record["image"] is not None:
            pil_image = record["image"]
            if isinstance(pil_image, Image.Image):
                rgb_array = np.array(pil_image)
                if len(rgb_array.shape) == 2:
                    return cv2.cvtColor(rgb_array, cv2.COLOR_GRAY2BGR)
                elif rgb_array.shape[2] == 4:
                    return cv2.cvtColor(rgb_array, cv2.COLOR_RGBA2BGR)
                else:
                    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        return None
    except Exception as e:
        logger.warning(f"Failed to load image: {e}")
        return None


# =============================================================================
# Metrics Calculation
# =============================================================================


def calculate_binary_metrics(y_true: list[bool], y_pred: list[bool]) -> dict[str, float]:
    """Calculate metrics for binary classification."""
    if len(y_true) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}

    tp = sum(1 for gt, pred in zip(y_true, y_pred) if gt and pred)
    fp = sum(1 for gt, pred in zip(y_true, y_pred) if not gt and pred)
    fn = sum(1 for gt, pred in zip(y_true, y_pred) if gt and not pred)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": sum(y_true),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def calculate_correlation(scores: list[float], labels: list[bool]) -> float:
    """Calculate point-biserial correlation between scores and binary labels."""
    if len(scores) < 2 or len(set(labels)) < 2:
        return 0.0

    try:
        from scipy.stats import pointbiserialr
        corr, _ = pointbiserialr(labels, scores)
        return corr if not np.isnan(corr) else 0.0
    except ImportError:
        # Fallback: simple correlation
        label_floats = [1.0 if l else 0.0 for l in labels]
        return float(np.corrcoef(scores, label_floats)[0, 1])


# =============================================================================
# Benchmark Execution
# =============================================================================


def run_benchmark(
    model: BaseModel,
    dataset: Any,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run benchmark for a single model.

    Args:
        model: Model adapter to evaluate
        dataset: OmniDocBench dataset
        limit: Maximum samples to evaluate

    Returns:
        Benchmark results dict
    """
    logger.info(f"Running benchmark for {model.config.full_name}")

    # Load model
    model.load()

    # Determine which attributes to evaluate
    benchmarkable = set(model.benchmarkable_attributes)
    binary_attrs = ["fuzzy_scan", "watermark", "colorful_background",
                    "has_tables", "has_figures", "has_dense_math"]
    eval_binary = [a for a in binary_attrs if a in benchmarkable]

    # Collections for metrics
    collections: dict[str, dict[str, list]] = {
        attr: {"y_true": [], "y_pred": [], "scores": []}
        for attr in eval_binary
    }
    layout_true: list[str] = []
    layout_pred: list[str] = []
    inference_times: list[float] = []

    # Process samples
    total = len(dataset) if limit is None else min(limit, len(dataset))
    processed = 0
    errors = 0
    start_time = time.time()

    for idx in range(total):
        if idx % 50 == 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            logger.info(f"Processing {idx}/{total} ({rate:.1f} samples/sec)")

        try:
            # Load image and ground truth
            image = load_image_from_record(dataset[idx])
            if image is None:
                errors += 1
                continue

            gt = extract_ground_truth(dataset[idx])

            # Run prediction
            pred = model.predict(image)
            inference_times.append(pred.inference_time_ms)

            # Collect binary attribute results
            for attr in eval_binary:
                gt_val = gt.get(attr, False)
                pred_val = pred.get_binary_prediction(attr)
                score = pred.get_score(attr, pred.get_score("blur_score", 0.5))

                collections[attr]["y_true"].append(gt_val)
                collections[attr]["y_pred"].append(pred_val)
                collections[attr]["scores"].append(score)

            # Collect layout results
            if "layout_type" in benchmarkable:
                layout_true.append(gt.get("layout_type", "unknown"))
                layout_pred.append(pred.labels.get("layout_type", "unknown"))

            processed += 1

        except Exception as e:
            logger.warning(f"Error at sample {idx}: {e}")
            errors += 1

    # Calculate metrics
    elapsed = time.time() - start_time

    results: dict[str, Any] = {
        "model": {
            "id": model.config.model_id,
            "name": model.config.name,
            "version": model.config.version,
            "type": model.config.model_type,
        },
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_samples": total,
            "processed": processed,
            "errors": errors,
            "elapsed_seconds": elapsed,
            "samples_per_second": processed / elapsed if elapsed > 0 else 0,
        },
        "performance": {
            "mean_inference_ms": np.mean(inference_times) if inference_times else 0,
            "p50_inference_ms": np.percentile(inference_times, 50) if inference_times else 0,
            "p95_inference_ms": np.percentile(inference_times, 95) if inference_times else 0,
        },
        "binary_attributes": {},
        "correlations": {},
    }

    # Binary attribute metrics
    f1_scores = []
    for attr in eval_binary:
        data = collections[attr]
        if data["y_true"]:
            metrics = calculate_binary_metrics(data["y_true"], data["y_pred"])
            results["binary_attributes"][attr] = metrics
            if metrics["support"] > 0:
                f1_scores.append(metrics["f1"])

            # Calculate correlation for IQA models
            if data["scores"] and attr == "fuzzy_scan":
                corr = calculate_correlation(data["scores"], data["y_true"])
                results["correlations"][f"{attr}_score_correlation"] = corr

    # Layout metrics
    if layout_true and "layout_type" in benchmarkable:
        accuracy = sum(1 for gt, pred in zip(layout_true, layout_pred) if gt == pred) / len(layout_true)
        results["layout"] = {"accuracy": accuracy}

    # Summary
    results["summary"] = {
        "mean_f1": np.mean(f1_scores) if f1_scores else 0.0,
        "evaluated_attributes": eval_binary,
    }

    # Unload model
    model.unload()

    return results


# =============================================================================
# Results Management
# =============================================================================


def save_results(
    results: dict[str, Any],
    output_dir: Path,
    model_id: str,
) -> Path:
    """Save benchmark results to JSON.

    Args:
        results: Benchmark results
        output_dir: Output directory
        model_id: Model identifier

    Returns:
        Path to saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Include timestamp in filename for versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{model_id}_{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Saved results to {filepath}")

    # Also save/update latest symlink
    latest_path = output_dir / f"{model_id}_latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    return filepath


def print_results_summary(results: dict[str, Any]) -> None:
    """Print human-readable results summary."""
    model = results["model"]
    meta = results["metadata"]
    perf = results["performance"]
    summary = results["summary"]

    print("\n" + "=" * 70)
    print(f"BENCHMARK RESULTS: {model['name']} (v{model['version']})")
    print("=" * 70)
    print(f"\nSamples: {meta['processed']} | Errors: {meta['errors']}")
    print(f"Time: {meta['elapsed_seconds']:.1f}s | Rate: {meta['samples_per_second']:.1f}/sec")
    print(f"Inference: {perf['mean_inference_ms']:.1f}ms (p50), {perf['p95_inference_ms']:.1f}ms (p95)")

    print("\nBinary Attribute Detection:")
    for attr, metrics in results.get("binary_attributes", {}).items():
        status = "✅" if metrics["f1"] >= 0.85 else "❌"
        print(f"  {status} {attr:25s}: F1={metrics['f1']:.3f} P={metrics['precision']:.3f} R={metrics['recall']:.3f}")

    if results.get("correlations"):
        print("\nScore Correlations:")
        for name, corr in results["correlations"].items():
            print(f"  {name}: {corr:.3f}")

    if results.get("layout"):
        print(f"\nLayout Classification: Accuracy={results['layout']['accuracy']:.3f}")

    print(f"\nMean F1: {summary['mean_f1']:.3f}")
    print("=" * 70)


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run OmniDocBench benchmark for specified models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Single model ID to evaluate",
    )
    parser.add_argument(
        "--models",
        type=str,
        help="Comma-separated list of model IDs",
    )
    parser.add_argument(
        "--group",
        type=str,
        help="Model group ID from registry",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmarks/omnidocbench_results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of samples",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="HuggingFace API token",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="List available model groups and exit",
    )

    args = parser.parse_args()

    # Initialize registry
    registry = ModelRegistry()

    # List modes
    if args.list_models:
        print("\nAvailable Models:")
        for status in ["active", "planned"]:
            models = registry.list_models(status=status)
            if models:
                print(f"\n  [{status.upper()}]")
                for mid in models:
                    cfg = registry.get_config(mid)
                    print(f"    {mid}: {cfg.name} (v{cfg.version})")
        return 0

    if args.list_groups:
        print("\nAvailable Model Groups:")
        for gid in registry.list_groups():
            models = registry.get_group_models(gid)
            print(f"  {gid}: {models}")
        return 0

    # Determine models to evaluate
    model_ids: list[str] = []

    if args.model:
        model_ids = [args.model]
    elif args.models:
        model_ids = [m.strip() for m in args.models.split(",")]
    elif args.group:
        model_ids = registry.get_group_models(args.group)
        if not model_ids:
            print(f"Error: Model group '{args.group}' not found")
            return 1
    else:
        # Default: run classical CV baseline
        model_ids = ["classical_cv_baseline"]

    print(f"\nModels to evaluate: {model_ids}")

    # Load dataset
    dataset = load_omnidocbench_dataset(args.token)

    # Run benchmarks
    all_results: list[dict[str, Any]] = []

    for model_id in model_ids:
        try:
            model = load_model(model_id, registry)
            results = run_benchmark(model, dataset, limit=args.limit)
            save_results(results, args.output, model_id)
            print_results_summary(results)
            all_results.append(results)

        except Exception as e:
            logger.error(f"Failed to benchmark {model_id}: {e}")
            continue

    # Save combined results if multiple models
    if len(all_results) > 1:
        combined = {
            "timestamp": datetime.now().isoformat(),
            "models": [r["model"] for r in all_results],
            "comparison": {
                r["model"]["id"]: {
                    "mean_f1": r["summary"]["mean_f1"],
                    "binary_attributes": r.get("binary_attributes", {}),
                }
                for r in all_results
            },
        }
        combined_path = args.output / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(combined_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, default=str)
        logger.info(f"Saved comparison to {combined_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
