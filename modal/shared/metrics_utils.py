"""Metrics utilities for Modal applications.

Provides correlation metrics, bootstrapped confidence intervals,
and result formatting shared across benchmark scripts.
"""

from __future__ import annotations

from typing import Any


def bootstrap_correlation_ci(
    gt_values: list[float],
    pred_values: list[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> dict[str, dict[str, float]]:
    """Compute bootstrapped confidence intervals for PLCC and SRCC.

    Args:
        gt_values: Ground truth values.
        pred_values: Predicted values.
        n_bootstrap: Number of bootstrap iterations.
        confidence: Confidence level (default 95%).

    Returns:
        Dictionary with PLCC and SRCC confidence intervals.
    """
    import numpy as np
    from scipy import stats

    n = len(gt_values)
    gt_arr = np.array(gt_values)
    pred_arr = np.array(pred_values)

    plcc_samples = []
    srcc_samples = []

    rng = np.random.default_rng(seed=42)  # Reproducible bootstrapping

    for _ in range(n_bootstrap):
        indices = rng.choice(n, size=n, replace=True)
        gt_boot = gt_arr[indices]
        pred_boot = pred_arr[indices]

        # Skip if constant values (correlation undefined)
        if np.std(gt_boot) > 0 and np.std(pred_boot) > 0:
            plcc, _ = stats.pearsonr(gt_boot, pred_boot)
            srcc, _ = stats.spearmanr(gt_boot, pred_boot)
            plcc_samples.append(plcc)
            srcc_samples.append(srcc)

    alpha = 1 - confidence
    lower_pct = (alpha / 2) * 100
    upper_pct = (1 - alpha / 2) * 100

    return {
        "plcc_ci": {
            "lower": float(np.percentile(plcc_samples, lower_pct)),
            "upper": float(np.percentile(plcc_samples, upper_pct)),
        },
        "srcc_ci": {
            "lower": float(np.percentile(srcc_samples, lower_pct)),
            "upper": float(np.percentile(srcc_samples, upper_pct)),
        },
    }


def _extract_dim_values(
    successful: list[dict[str, Any]], dim: str
) -> tuple[list[float], list[float]]:
    """Extract ground truth and predicted values for a single dimension."""
    gt_values: list[float] = []
    pred_values: list[float] = []
    for r in successful:
        gt = r["ground_truth"].get(dim)
        pred = r["predicted"].get(dim) if r["predicted"] else None
        if gt is not None and pred is not None:
            gt_values.append(gt)
            pred_values.append(pred)
    return gt_values, pred_values


def _compute_dim_metrics(
    gt_values: list[float], pred_values: list[float]
) -> dict[str, Any]:
    """Compute correlation metrics for a single quality dimension."""
    from scipy import stats

    n = len(gt_values)
    if n < 3:
        return {
            "plcc": None,
            "srcc": None,
            "mae": None,
            "rmse": None,
            "num_valid": n,
            "error": "Insufficient valid predictions",
        }

    plcc, _ = stats.pearsonr(gt_values, pred_values)
    srcc, _ = stats.spearmanr(gt_values, pred_values)
    mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / n
    mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / n
    rmse = mse**0.5

    result: dict[str, Any] = {
        "plcc": plcc,
        "srcc": srcc,
        "mae": mae,
        "rmse": rmse,
        "num_valid": n,
    }

    if n >= 30:
        ci = bootstrap_correlation_ci(gt_values, pred_values)
        result["plcc_ci_lower"] = ci["plcc_ci"]["lower"]
        result["plcc_ci_upper"] = ci["plcc_ci"]["upper"]
        result["srcc_ci_lower"] = ci["srcc_ci"]["lower"]
        result["srcc_ci_upper"] = ci["srcc_ci"]["upper"]

    return result


def compute_metrics(
    results: list[dict[str, Any]],
    model_id: str,
    model_load_time: float,
    inference_times: list[float],
) -> dict[str, Any]:
    """Compute benchmark metrics from results including bootstrapped CIs.

    Args:
        results: List of inference results with success, ground_truth, predicted.
        model_id: Identifier for the model being benchmarked.
        model_load_time: Time taken to load the model in seconds.
        inference_times: List of inference times in milliseconds.

    Returns:
        Dictionary with comprehensive metrics including timing and correlations.
    """
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(results) if results else 0,
    }

    if inference_times:
        metrics["timing"] = {
            "mean_ms": sum(inference_times) / len(inference_times),
            "min_ms": min(inference_times),
            "max_ms": max(inference_times),
            "total_s": sum(inference_times) / 1000,
            "model_load_s": model_load_time,
        }

    for dim in ["overall", "sharpness", "color"]:
        gt_values, pred_values = _extract_dim_values(successful, dim)
        metrics[dim] = _compute_dim_metrics(gt_values, pred_values)

    return metrics


def print_results(metrics: dict[str, Any]) -> None:
    """Print benchmark results in a formatted table.

    Args:
        metrics: Dictionary of metrics from compute_metrics.
    """
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {metrics['model_id']}")
    print(
        f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)"
    )
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print("\nTiming:")
        print(f"  Mean inference: {t['mean_ms']:.0f}ms")
        print(f"  Total inference: {t['total_s']:.1f}s")
        print(f"  Model load: {t['model_load_s']:.1f}s")

    for dim in ["overall", "sharpness", "color"]:
        if dim in metrics and metrics[dim].get("plcc") is not None:
            m = metrics[dim]
            print(f"\n{dim.capitalize()}:")
            # Print PLCC with CI if available
            if "plcc_ci_lower" in m:
                print(
                    f"  PLCC: {m['plcc']:.4f} [{m['plcc_ci_lower']:.4f}, {m['plcc_ci_upper']:.4f}]"
                )
            else:
                print(f"  PLCC: {m['plcc']:.4f}")
            # Print SRCC with CI if available
            if "srcc_ci_lower" in m:
                print(
                    f"  SRCC: {m['srcc']:.4f} [{m['srcc_ci_lower']:.4f}, {m['srcc_ci_upper']:.4f}]"
                )
            else:
                print(f"  SRCC: {m['srcc']:.4f}")
            print(f"  MAE:  {m['mae']:.4f}")
            print(f"  RMSE: {m['rmse']:.4f}")
            print(f"  Valid predictions: {m['num_valid']}")
