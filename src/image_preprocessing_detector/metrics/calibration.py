# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Calibration metrics for Phase 7 continuous label model validation.

This module provides metrics to evaluate model calibration quality:
- Expected Calibration Error (ECE): Primary calibration metric
- Maximum Calibration Error (MCE): Worst-case calibration
- Reliability Diagram: Visualization of calibration quality

Well-calibrated models produce predicted probabilities that match
the true frequency of positive outcomes. For example, if a model
predicts 70% probability of blur, approximately 70% of such images
should actually have blur.

Phase 7 targets:
- Binary models (v1.0): ECE ~0.18
- Continuous models (v2.0): ECE <0.10 (target)

Reference:
    - Guo et al. "On Calibration of Modern Neural Networks" (ICML 2017)
    - Phase 7 Strategy: docs/planning/PROJECT_PLAN.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class CalibrationResult:
    """Result of calibration evaluation.

    Attributes:
        ece: Expected Calibration Error (weighted average over bins)
        mce: Maximum Calibration Error (worst bin)
        bin_accuracies: Accuracy per confidence bin
        bin_confidences: Mean confidence per bin
        bin_counts: Number of samples per bin
        num_bins: Number of bins used
        total_samples: Total number of samples evaluated
    """

    ece: float
    mce: float
    bin_accuracies: list[float]
    bin_confidences: list[float]
    bin_counts: list[int]
    num_bins: int
    total_samples: int
    per_class_ece: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ece": self.ece,
            "mce": self.mce,
            "bin_accuracies": self.bin_accuracies,
            "bin_confidences": self.bin_confidences,
            "bin_counts": self.bin_counts,
            "num_bins": self.num_bins,
            "total_samples": self.total_samples,
            "per_class_ece": self.per_class_ece,
        }


def compute_ece(
    predictions: NDArray[np.floating[Any]],
    labels: NDArray[np.floating[Any]],
    num_bins: int = 15,
    binary_threshold: float = 0.5,
) -> CalibrationResult:
    """Compute Expected Calibration Error (ECE).

    ECE measures the difference between predicted confidence and
    actual accuracy, averaged over confidence bins.

    ECE = sum_b (|B_b| / n) * |acc(B_b) - conf(B_b)|

    Where B_b is the set of predictions in bin b, acc is accuracy,
    and conf is mean confidence.

    Args:
        predictions: Predicted probabilities, shape (n_samples,) or (n_samples, n_classes)
        labels: True labels (continuous [0,1] or binary)
        num_bins: Number of confidence bins (default: 15)
        binary_threshold: Threshold for converting continuous labels (default: 0.5)

    Returns:
        CalibrationResult with ECE, MCE, and per-bin statistics

    Example:
        >>> preds = np.array([0.9, 0.8, 0.3, 0.2])
        >>> labels = np.array([1, 1, 0, 0])
        >>> result = compute_ece(preds, labels)
        >>> print(f"ECE: {result.ece:.4f}")
    """
    # Ensure 1D for single-class case
    predictions = np.asarray(predictions).flatten()
    labels = np.asarray(labels).flatten()

    # Convert continuous labels to binary
    binary_labels = (labels >= binary_threshold).astype(np.float64)

    n_samples = len(predictions)
    if n_samples == 0:
        return CalibrationResult(
            ece=0.0,
            mce=0.0,
            bin_accuracies=[],
            bin_confidences=[],
            bin_counts=[],
            num_bins=num_bins,
            total_samples=0,
        )

    # Create confidence bins
    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    bin_accuracies = []
    bin_confidences = []
    bin_counts = []

    ece = 0.0
    mce = 0.0

    for i in range(num_bins):
        # Find samples in this bin
        lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
        if i == num_bins - 1:
            # Include upper bound for last bin
            in_bin = (predictions >= lower) & (predictions <= upper)
        else:
            in_bin = (predictions >= lower) & (predictions < upper)

        bin_size = in_bin.sum()
        bin_counts.append(int(bin_size))

        if bin_size > 0:
            # Compute accuracy and confidence for this bin
            bin_accuracy = binary_labels[in_bin].mean()
            bin_confidence = predictions[in_bin].mean()

            bin_accuracies.append(float(bin_accuracy))
            bin_confidences.append(float(bin_confidence))

            # Update ECE (weighted by bin size)
            calibration_error = abs(bin_accuracy - bin_confidence)
            ece += (bin_size / n_samples) * calibration_error
            mce = max(mce, calibration_error)
        else:
            bin_accuracies.append(0.0)
            bin_confidences.append(0.0)

    return CalibrationResult(
        ece=float(ece),
        mce=float(mce),
        bin_accuracies=bin_accuracies,
        bin_confidences=bin_confidences,
        bin_counts=bin_counts,
        num_bins=num_bins,
        total_samples=n_samples,
    )


def compute_multiclass_ece(
    predictions: NDArray[np.floating[Any]],
    labels: NDArray[np.floating[Any]],
    class_names: list[str] | None = None,
    num_bins: int = 15,
    binary_threshold: float = 0.5,
) -> CalibrationResult:
    """Compute ECE for multi-class/multi-label predictions.

    Computes ECE for each class independently and returns both
    per-class ECE and macro-averaged ECE.

    Args:
        predictions: Predicted probabilities, shape (n_samples, n_classes)
        labels: True labels, shape (n_samples, n_classes)
        class_names: Optional list of class names for reporting
        num_bins: Number of confidence bins (default: 15)
        binary_threshold: Threshold for continuous labels (default: 0.5)

    Returns:
        CalibrationResult with per-class ECE in per_class_ece dict

    Example:
        >>> preds = np.array([[0.9, 0.2], [0.8, 0.7], [0.3, 0.1]])
        >>> labels = np.array([[1, 0], [1, 1], [0, 0]])
        >>> result = compute_multiclass_ece(preds, labels, ["blur", "noise"])
        >>> print(f"Macro ECE: {result.ece:.4f}")
        >>> print(f"Blur ECE: {result.per_class_ece['blur']:.4f}")
    """
    predictions = np.asarray(predictions)
    labels = np.asarray(labels)

    # Handle 1D case
    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, 1)
        labels = labels.reshape(-1, 1)

    n_samples, n_classes = predictions.shape

    if class_names is None:
        class_names = [f"class_{i}" for i in range(n_classes)]

    # Compute per-class ECE
    per_class_results: dict[str, CalibrationResult] = {}
    per_class_ece: dict[str, float] = {}

    for i, class_name in enumerate(class_names):
        result = compute_ece(
            predictions[:, i],
            labels[:, i],
            num_bins=num_bins,
            binary_threshold=binary_threshold,
        )
        per_class_results[class_name] = result
        per_class_ece[class_name] = result.ece

    # Compute macro-averaged ECE
    macro_ece = np.mean(list(per_class_ece.values()))

    # Aggregate bin statistics (use first class as representative)
    first_result = per_class_results[class_names[0]]

    return CalibrationResult(
        ece=float(macro_ece),
        mce=max(r.mce for r in per_class_results.values()),
        bin_accuracies=first_result.bin_accuracies,
        bin_confidences=first_result.bin_confidences,
        bin_counts=first_result.bin_counts,
        num_bins=num_bins,
        total_samples=n_samples,
        per_class_ece=per_class_ece,
    )


def compute_severity_metrics(
    predictions: NDArray[np.floating[Any]],
    targets: NDArray[np.floating[Any]],
) -> dict[str, float]:
    """Compute severity prediction metrics for continuous labels.

    Unlike binary classification metrics, these measure how well
    the model predicts the severity/magnitude of quality issues.

    Args:
        predictions: Predicted severities [0, 1], shape (n_samples,) or (n_samples, n_classes)
        targets: True severity values [0, 1]

    Returns:
        Dictionary with severity metrics:
        - severity_mae: Mean Absolute Error
        - severity_mse: Mean Squared Error
        - severity_rmse: Root Mean Squared Error
        - severity_correlation: Pearson correlation coefficient
    """
    predictions = np.asarray(predictions).flatten()
    targets = np.asarray(targets).flatten()

    # Basic error metrics
    mae = float(np.abs(predictions - targets).mean())
    mse = float(((predictions - targets) ** 2).mean())
    rmse = float(np.sqrt(mse))

    # Correlation (handle edge case of constant values)
    if np.std(predictions) < 1e-8 or np.std(targets) < 1e-8:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(predictions, targets)[0, 1])

    return {
        "severity_mae": mae,
        "severity_mse": mse,
        "severity_rmse": rmse,
        "severity_correlation": correlation,
    }


def generate_reliability_diagram_data(
    result: CalibrationResult,
) -> dict[str, Any]:
    """Generate data for plotting a reliability diagram.

    A reliability diagram plots predicted confidence (x-axis) against
    observed accuracy (y-axis). Perfect calibration = diagonal line.

    Args:
        result: CalibrationResult from compute_ece

    Returns:
        Dictionary with plot data:
        - bin_midpoints: X-axis values (confidence bin centers)
        - bin_accuracies: Y-axis values (observed accuracy)
        - bin_counts: Size of each bin (for bar widths)
        - perfect_calibration: Reference diagonal line
        - ece: ECE value for annotation
    """
    bin_width = 1.0 / result.num_bins
    bin_midpoints = [(i + 0.5) * bin_width for i in range(result.num_bins)]

    return {
        "bin_midpoints": bin_midpoints,
        "bin_accuracies": result.bin_accuracies,
        "bin_confidences": result.bin_confidences,
        "bin_counts": result.bin_counts,
        "bin_width": bin_width,
        "perfect_calibration": [[0, 0], [1, 1]],
        "ece": result.ece,
        "mce": result.mce,
    }


if __name__ == "__main__":
    # Example usage
    rng = np.random.default_rng(42)

    # Simulate well-calibrated predictions
    n_samples = 1000
    true_probs = rng.uniform(0, 1, n_samples)
    labels = (rng.random(n_samples) < true_probs).astype(float)
    predictions = true_probs + rng.normal(0, 0.1, n_samples)
    predictions = np.clip(predictions, 0, 1)

    result = compute_ece(predictions, labels)
    print("Well-calibrated model:")  # noqa: T201
    print(f"  ECE: {result.ece:.4f}")  # noqa: T201
    print(f"  MCE: {result.mce:.4f}")  # noqa: T201

    # Simulate overconfident predictions
    overconfident_preds = np.where(predictions > 0.5, 0.9, 0.1)
    result_overconf = compute_ece(overconfident_preds, labels)
    print("\nOverconfident model:")  # noqa: T201
    print(f"  ECE: {result_overconf.ece:.4f}")  # noqa: T201
    print(f"  MCE: {result_overconf.mce:.4f}")  # noqa: T201

    # Multi-class example
    multi_preds = np.column_stack([predictions, 1 - predictions])
    multi_labels = np.column_stack([labels, 1 - labels])
    multi_result = compute_multiclass_ece(multi_preds, multi_labels, ["blur", "noise"])
    print(f"\nMulti-class ECE: {multi_result.ece:.4f}")  # noqa: T201
    print(f"Per-class: {multi_result.per_class_ece}")  # noqa: T201
