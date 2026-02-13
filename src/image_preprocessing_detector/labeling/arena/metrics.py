"""Arena metrics for DIQA-5000 evaluation.

This module provides deterministic accuracy metrics aligned with DIQA-5000
and DocIQ conventions. All metrics are computed per dimension and as
macro-averaged summaries.

Metrics:
    - PLCC: Pearson Linear Correlation Coefficient
    - SRCC: Spearman Rank Correlation Coefficient
    - MAE: Mean Absolute Error
    - RMSE: Root Mean Squared Error

Note:
    Project A computes deterministic accuracy metrics ONLY.
    No uncertainty, confidence, or probabilistic metrics are included.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import ArrayLike
from scipy import stats

# Type alias for values that can be converted to arrays
ArrayInput: TypeAlias = ArrayLike | Sequence[float] | list[float]  # noqa: UP040

# Common error messages (S1192: avoid duplicate string literals)
NAN_INPUTS_MSG = "Inputs contain NaN values"


def compute_plcc(
    predictions: ArrayLike,
    ground_truth: ArrayLike,
) -> float:
    """Compute Pearson Linear Correlation Coefficient.

    PLCC measures the linear correlation between predicted and ground truth
    values. A value of 1 indicates perfect positive correlation.

    Args:
        predictions: Model predictions as array-like.
        ground_truth: Ground truth values as array-like.

    Returns:
        PLCC value in range [-1, 1]. Higher is better.

    Raises:
        ValueError: If inputs have different lengths or contain NaN.

    Example:
        >>> preds = [0.8, 0.6, 0.9, 0.5]
        >>> gt = [0.85, 0.55, 0.92, 0.48]
        >>> plcc = compute_plcc(preds, gt)
        >>> print(f"PLCC: {plcc:.4f}")
    """
    preds = np.asarray(predictions, dtype=np.float64)
    gt = np.asarray(ground_truth, dtype=np.float64)

    if preds.shape != gt.shape:
        msg = f"Shape mismatch: predictions {preds.shape} vs ground_truth {gt.shape}"
        raise ValueError(msg)

    if np.isnan(preds).any() or np.isnan(gt).any():
        msg = NAN_INPUTS_MSG
        raise ValueError(msg)

    if len(preds) < 2:
        msg = "Need at least 2 samples to compute correlation"
        raise ValueError(msg)

    # Handle constant arrays (no variance)
    if np.std(preds) == 0 or np.std(gt) == 0:
        return 0.0

    correlation_and_pvalue = stats.pearsonr(preds, gt)
    return float(correlation_and_pvalue[0])


def compute_srcc(
    predictions: ArrayLike,
    ground_truth: ArrayLike,
) -> float:
    """Compute Spearman Rank Correlation Coefficient.

    SRCC measures the monotonic relationship between predicted and ground
    truth rankings. It is robust to outliers and non-linear relationships.

    Args:
        predictions: Model predictions as array-like.
        ground_truth: Ground truth values as array-like.

    Returns:
        SRCC value in range [-1, 1]. Higher is better.

    Raises:
        ValueError: If inputs have different lengths or contain NaN.

    Example:
        >>> preds = [0.8, 0.6, 0.9, 0.5]
        >>> gt = [0.85, 0.55, 0.92, 0.48]
        >>> srcc = compute_srcc(preds, gt)
        >>> print(f"SRCC: {srcc:.4f}")
    """
    preds = np.asarray(predictions, dtype=np.float64)
    gt = np.asarray(ground_truth, dtype=np.float64)

    if preds.shape != gt.shape:
        msg = f"Shape mismatch: predictions {preds.shape} vs ground_truth {gt.shape}"
        raise ValueError(msg)

    if np.isnan(preds).any() or np.isnan(gt).any():
        msg = NAN_INPUTS_MSG
        raise ValueError(msg)

    if len(preds) < 2:
        msg = "Need at least 2 samples to compute correlation"
        raise ValueError(msg)

    # Handle constant arrays (no variance)
    if np.std(preds) == 0 or np.std(gt) == 0:
        return 0.0

    correlation_and_pvalue = stats.spearmanr(preds, gt)
    return float(correlation_and_pvalue.statistic)


def compute_mae(
    predictions: ArrayLike,
    ground_truth: ArrayLike,
) -> float:
    """Compute Mean Absolute Error.

    MAE measures the average absolute difference between predictions
    and ground truth. Lower values indicate better performance.

    Args:
        predictions: Model predictions as array-like.
        ground_truth: Ground truth values as array-like.

    Returns:
        MAE value >= 0. Lower is better.

    Raises:
        ValueError: If inputs have different lengths or contain NaN.

    Example:
        >>> preds = [0.8, 0.6, 0.9, 0.5]
        >>> gt = [0.85, 0.55, 0.92, 0.48]
        >>> mae = compute_mae(preds, gt)
        >>> print(f"MAE: {mae:.4f}")
    """
    preds = np.asarray(predictions, dtype=np.float64)
    gt = np.asarray(ground_truth, dtype=np.float64)

    if preds.shape != gt.shape:
        msg = f"Shape mismatch: predictions {preds.shape} vs ground_truth {gt.shape}"
        raise ValueError(msg)

    if np.isnan(preds).any() or np.isnan(gt).any():
        msg = NAN_INPUTS_MSG
        raise ValueError(msg)

    return float(np.mean(np.abs(preds - gt)))


def compute_rmse(
    predictions: ArrayLike,
    ground_truth: ArrayLike,
) -> float:
    """Compute Root Mean Squared Error.

    RMSE measures the square root of the average squared difference
    between predictions and ground truth. It penalizes larger errors
    more heavily than MAE.

    Args:
        predictions: Model predictions as array-like.
        ground_truth: Ground truth values as array-like.

    Returns:
        RMSE value >= 0. Lower is better.

    Raises:
        ValueError: If inputs have different lengths or contain NaN.

    Example:
        >>> preds = [0.8, 0.6, 0.9, 0.5]
        >>> gt = [0.85, 0.55, 0.92, 0.48]
        >>> rmse = compute_rmse(preds, gt)
        >>> print(f"RMSE: {rmse:.4f}")
    """
    preds = np.asarray(predictions, dtype=np.float64)
    gt = np.asarray(ground_truth, dtype=np.float64)

    if preds.shape != gt.shape:
        msg = f"Shape mismatch: predictions {preds.shape} vs ground_truth {gt.shape}"
        raise ValueError(msg)

    if np.isnan(preds).any() or np.isnan(gt).any():
        msg = NAN_INPUTS_MSG
        raise ValueError(msg)

    return float(np.sqrt(np.mean((preds - gt) ** 2)))


@dataclass
class DimensionMetrics:
    """Metrics for a single DIQA dimension.

    Attributes:
        plcc: Pearson Linear Correlation Coefficient [-1, 1]
        srcc: Spearman Rank Correlation Coefficient [-1, 1]
        mae: Mean Absolute Error [0, inf)
        rmse: Root Mean Squared Error [0, inf)
        num_samples: Number of samples used for computation
    """

    plcc: float
    srcc: float
    mae: float
    rmse: float
    num_samples: int = 0

    def to_dict(self) -> dict[str, float | int]:
        """Convert to dictionary representation."""
        return {
            "plcc": self.plcc,
            "srcc": self.srcc,
            "mae": self.mae,
            "rmse": self.rmse,
            "num_samples": self.num_samples,
        }

    @classmethod
    def compute(
        cls,
        predictions: ArrayLike,
        ground_truth: ArrayLike,
    ) -> DimensionMetrics:
        """Compute all metrics for a dimension.

        Args:
            predictions: Model predictions.
            ground_truth: Ground truth values.

        Returns:
            DimensionMetrics with all computed values.
        """
        preds = np.asarray(predictions)
        gt = np.asarray(ground_truth)

        return cls(
            plcc=compute_plcc(preds, gt),
            srcc=compute_srcc(preds, gt),
            mae=compute_mae(preds, gt),
            rmse=compute_rmse(preds, gt),
            num_samples=len(preds),
        )


@dataclass
class ArenaMetrics:
    """Complete arena metrics for DIQA-5000 evaluation.

    Contains metrics per dimension and macro-averaged aggregates.
    This is the primary output of a benchmark run.

    Attributes:
        overall: Metrics for overall quality dimension
        sharpness: Metrics for sharpness dimension
        color: Metrics for color fidelity dimension
        aggregate: Macro-averaged metrics across dimensions

    Example:
        >>> metrics = ArenaMetrics.compute(predictions, ground_truth)
        >>> print(f"Overall PLCC: {metrics.overall.plcc:.4f}")
        >>> print(f"Aggregate SRCC: {metrics.aggregate.srcc:.4f}")
    """

    overall: DimensionMetrics
    sharpness: DimensionMetrics
    color: DimensionMetrics
    aggregate: DimensionMetrics = field(init=False)

    def __post_init__(self) -> None:
        """Compute aggregate metrics after initialization."""
        self.aggregate = DimensionMetrics(
            plcc=float(
                np.mean([self.overall.plcc, self.sharpness.plcc, self.color.plcc])
            ),
            srcc=float(
                np.mean([self.overall.srcc, self.sharpness.srcc, self.color.srcc])
            ),
            mae=float(np.mean([self.overall.mae, self.sharpness.mae, self.color.mae])),
            rmse=float(
                np.mean([self.overall.rmse, self.sharpness.rmse, self.color.rmse])
            ),
            num_samples=self.overall.num_samples,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization."""
        return {
            "overall": self.overall.to_dict(),
            "sharpness": self.sharpness.to_dict(),
            "color": self.color.to_dict(),
            "aggregate": self.aggregate.to_dict(),
        }

    @classmethod
    def compute(
        cls,
        predictions: dict[str, ArrayInput],
        ground_truth: dict[str, ArrayInput],
    ) -> ArenaMetrics:
        """Compute arena metrics from predictions and ground truth.

        Args:
            predictions: Dict with keys "overall", "sharpness", "color"
                        mapping to prediction arrays.
            ground_truth: Dict with keys "overall", "sharpness", "color"
                         mapping to ground truth arrays.

        Returns:
            ArenaMetrics with all dimensions computed.

        Raises:
            KeyError: If required dimension keys are missing.

        Example:
            >>> preds = {
            ...     "overall": [0.8, 0.6, 0.9],
            ...     "sharpness": [0.7, 0.5, 0.8],
            ...     "color": [0.9, 0.7, 0.85],
            ... }
            >>> gt = {
            ...     "overall": [0.85, 0.55, 0.92],
            ...     "sharpness": [0.72, 0.48, 0.78],
            ...     "color": [0.88, 0.68, 0.83],
            ... }
            >>> metrics = ArenaMetrics.compute(preds, gt)
        """
        required_keys = {"overall", "sharpness", "color"}

        for key in required_keys:
            if key not in predictions:
                msg = f"Missing prediction key: {key}"
                raise KeyError(msg)
            if key not in ground_truth:
                msg = f"Missing ground_truth key: {key}"
                raise KeyError(msg)

        return cls(
            overall=DimensionMetrics.compute(
                predictions["overall"],
                ground_truth["overall"],
            ),
            sharpness=DimensionMetrics.compute(
                predictions["sharpness"],
                ground_truth["sharpness"],
            ),
            color=DimensionMetrics.compute(
                predictions["color"],
                ground_truth["color"],
            ),
        )

    def summary(self) -> str:
        """Generate a human-readable summary of metrics.

        Returns:
            Formatted string with metrics table.
        """
        lines = [
            "Arena Metrics Summary",
            "=" * 60,
            "",
            f"{'Dimension':<12} {'PLCC':>8} {'SRCC':>8} {'MAE':>8} {'RMSE':>8}",
            "-" * 60,
            (
                f"{'Overall':<12} {self.overall.plcc:>8.4f} {self.overall.srcc:>8.4f} "
                f"{self.overall.mae:>8.4f} {self.overall.rmse:>8.4f}"
            ),
            (
                f"{'Sharpness':<12} {self.sharpness.plcc:>8.4f} {self.sharpness.srcc:>8.4f} "
                f"{self.sharpness.mae:>8.4f} {self.sharpness.rmse:>8.4f}"
            ),
            (
                f"{'Color':<12} {self.color.plcc:>8.4f} {self.color.srcc:>8.4f} "
                f"{self.color.mae:>8.4f} {self.color.rmse:>8.4f}"
            ),
            "-" * 60,
            (
                f"{'Aggregate':<12} {self.aggregate.plcc:>8.4f} {self.aggregate.srcc:>8.4f} "
                f"{self.aggregate.mae:>8.4f} {self.aggregate.rmse:>8.4f}"
            ),
            "",
            f"Samples: {self.overall.num_samples}",
        ]
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Generate Markdown-formatted metrics table.

        Returns:
            Markdown table string suitable for reports.
        """
        lines = [
            "## Arena Metrics",
            "",
            "| Dimension | PLCC | SRCC | MAE | RMSE |",
            "|-----------|------|------|-----|------|",
            (
                f"| Overall | {self.overall.plcc:.4f} | {self.overall.srcc:.4f} | "
                f"{self.overall.mae:.4f} | {self.overall.rmse:.4f} |"
            ),
            (
                f"| Sharpness | {self.sharpness.plcc:.4f} | {self.sharpness.srcc:.4f} | "
                f"{self.sharpness.mae:.4f} | {self.sharpness.rmse:.4f} |"
            ),
            (
                f"| Color | {self.color.plcc:.4f} | {self.color.srcc:.4f} | "
                f"{self.color.mae:.4f} | {self.color.rmse:.4f} |"
            ),
            (
                f"| **Aggregate** | **{self.aggregate.plcc:.4f}** | **{self.aggregate.srcc:.4f}** | "
                f"**{self.aggregate.mae:.4f}** | **{self.aggregate.rmse:.4f}** |"
            ),
            "",
            f"*Samples: {self.overall.num_samples}*",
        ]
        return "\n".join(lines)


def compare_models(
    results: dict[str, ArenaMetrics],
    sort_by: str = "aggregate.plcc",
) -> list[tuple[str, ArenaMetrics]]:
    """Compare multiple models and rank by specified metric.

    Args:
        results: Dict mapping model names to ArenaMetrics.
        sort_by: Metric to sort by in format "dimension.metric".
                E.g., "aggregate.plcc", "overall.srcc", "sharpness.mae".

    Returns:
        List of (model_name, metrics) tuples sorted by metric.
        For correlation metrics (PLCC, SRCC), higher is better.
        For error metrics (MAE, RMSE), lower is better.

    Example:
        >>> results = {
        ...     "model_a": metrics_a,
        ...     "model_b": metrics_b,
        ... }
        >>> ranked = compare_models(results, sort_by="aggregate.plcc")
        >>> print(f"Best model: {ranked[0][0]}")
    """
    dimension, metric = sort_by.split(".")

    # Determine sort order (higher is better for correlation, lower for error)
    reverse = metric in ("plcc", "srcc")

    def get_value(item: tuple[str, ArenaMetrics]) -> float:
        _, metrics = item
        dim_metrics = getattr(metrics, dimension)
        return float(getattr(dim_metrics, metric))

    return sorted(results.items(), key=get_value, reverse=reverse)
