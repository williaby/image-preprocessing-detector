"""Shared classification metrics for Stream 3 benchmarks.

Provides classification, binary, and regression report functions used by
all benchmark scripts. Uses numpy only (no sklearn dependency).

Report Types:
    - ClassificationReport: Multi-class accuracy, macro/weighted F1, per-class P/R/F1,
      confusion matrix, Cohen's kappa
    - BinaryReport: Accuracy, precision, recall, F1, TP/FP/TN/FN, optional ROC-AUC
    - RegressionReport: PLCC, SRCC, MAE, RMSE (delegates to arena metrics)

Example:
    >>> from scripts.benchmarks.classification_metrics import (
    ...     compute_classification_report,
    ...     compute_binary_report,
    ...     save_benchmark_result,
    ... )
    >>> report = compute_classification_report(
    ...     y_true=[0, 1, 2, 0, 1],
    ...     y_pred=[0, 1, 1, 0, 2],
    ...     class_names=["a", "b", "c"],
    ... )
    >>> print(report["accuracy"])
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray


def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Compute precision, recall, and F1 from raw counts.

    Args:
        tp: True positives.
        fp: False positives.
        fn: False negatives.

    Returns:
        Tuple of (precision, recall, f1). Returns 0.0 for undefined metrics.
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )
    return precision, recall, f1


def compute_confusion_matrix(
    y_true: list[int] | NDArray[np.intp],
    y_pred: list[int] | NDArray[np.intp],
    num_classes: int,
) -> NDArray[np.intp]:
    """Compute confusion matrix from integer-encoded labels.

    Args:
        y_true: Ground truth labels (integer-encoded).
        y_pred: Predicted labels (integer-encoded).
        num_classes: Total number of classes.

    Returns:
        Confusion matrix of shape (num_classes, num_classes).
        Row i, column j = count of samples with true label i predicted as j.
    """
    y_t = np.asarray(y_true, dtype=np.intp).ravel()
    y_p = np.asarray(y_pred, dtype=np.intp).ravel()
    if len(y_t) != len(y_p):
        raise ValueError(
            f"y_true and y_pred must have the same length; "
            f"got {len(y_t)} and {len(y_p)}"
        )
    if num_classes <= 0:
        raise ValueError(f"num_classes must be >= 1; got {num_classes}")
    if y_t.size and (y_t.min() < 0 or y_t.max() >= num_classes):
        raise ValueError(
            f"y_true labels must be in [0, {num_classes}); "
            f"got min={y_t.min()}, max={y_t.max()}"
        )
    if y_p.size and (y_p.min() < 0 or y_p.max() >= num_classes):
        raise ValueError(
            f"y_pred labels must be in [0, {num_classes}); "
            f"got min={y_p.min()}, max={y_p.max()}"
        )
    matrix = np.zeros((num_classes, num_classes), dtype=np.intp)
    for true_label, pred_label in zip(y_t, y_p):
        matrix[true_label, pred_label] += 1
    return matrix


def compute_classification_report(
    y_true: list[int] | NDArray[np.intp],
    y_pred: list[int] | NDArray[np.intp],
    class_names: list[str],
) -> dict[str, Any]:
    """Compute multi-class classification metrics.

    Args:
        y_true: Ground truth labels (integer-encoded, 0-indexed).
        y_pred: Predicted labels (integer-encoded, 0-indexed).
        class_names: List of class names (index matches label encoding).

    Returns:
        Dictionary with:
            - accuracy: Overall accuracy.
            - macro_f1: Macro-averaged F1 (unweighted mean across classes).
            - weighted_f1: Weighted F1 (weighted by class support).
            - cohens_kappa: Cohen's kappa coefficient.
            - per_class: Dict mapping class name to {precision, recall, f1, support}.
            - confusion_matrix: Nested list (row=true, col=pred).
            - class_names: Copy of input class names.
            - num_samples: Total number of samples.
    """
    y_t = np.asarray(y_true, dtype=np.intp)
    y_p = np.asarray(y_pred, dtype=np.intp)
    num_classes = len(class_names)
    num_samples = len(y_t)

    cm = compute_confusion_matrix(y_t, y_p, num_classes)

    # Overall accuracy
    accuracy = float(np.sum(np.diag(cm))) / num_samples if num_samples > 0 else 0.0

    # Per-class metrics
    per_class: dict[str, dict[str, float | int]] = {}
    f1_scores: list[float] = []
    supports: list[int] = []

    for idx, name in enumerate(class_names):
        tp = int(cm[idx, idx])
        fp = int(np.sum(cm[:, idx]) - tp)
        fn = int(np.sum(cm[idx, :]) - tp)
        support = int(np.sum(cm[idx, :]))

        precision, recall, f1 = _precision_recall_f1(tp, fp, fn)
        per_class[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        f1_scores.append(f1)
        supports.append(support)

    # Macro F1
    macro_f1 = float(np.mean(f1_scores)) if f1_scores else 0.0

    # Weighted F1
    total_support = sum(supports)
    weighted_f1 = (
        sum(f * s for f, s in zip(f1_scores, supports)) / total_support
        if total_support > 0
        else 0.0
    )

    # Cohen's kappa
    cohens_kappa = _compute_cohens_kappa(cm, num_samples)

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "cohens_kappa": round(cohens_kappa, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
        "num_samples": num_samples,
    }


def _compute_cohens_kappa(cm: NDArray[np.intp], num_samples: int) -> float:
    """Compute Cohen's kappa from a confusion matrix.

    Args:
        cm: Confusion matrix (num_classes x num_classes).
        num_samples: Total sample count.

    Returns:
        Cohen's kappa coefficient in [-1, 1]. 1 = perfect agreement.
    """
    if num_samples == 0:
        return 0.0

    observed_agreement = float(np.sum(np.diag(cm))) / num_samples

    # Expected agreement under independence
    row_sums = np.sum(cm, axis=1).astype(np.float64)
    col_sums = np.sum(cm, axis=0).astype(np.float64)
    expected_agreement = float(np.sum(row_sums * col_sums)) / (num_samples**2)

    if expected_agreement == 1.0:
        return 1.0 if observed_agreement == 1.0 else 0.0

    return (observed_agreement - expected_agreement) / (1.0 - expected_agreement)


def compute_binary_report(
    y_true: list[int] | NDArray[np.intp],
    y_pred: list[int] | NDArray[np.intp],
    y_scores: list[float] | NDArray[np.floating] | None = None,
) -> dict[str, Any]:
    """Compute binary classification metrics.

    Labels: 0 = negative, 1 = positive.

    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_pred: Predicted binary labels (0 or 1).
        y_scores: Optional continuous scores for ROC-AUC computation.

    Returns:
        Dictionary with:
            - accuracy, precision, recall, f1
            - tp, fp, tn, fn counts
            - roc_auc (if y_scores provided, else None)
            - num_samples
    """
    y_t = np.asarray(y_true, dtype=np.intp)
    y_p = np.asarray(y_pred, dtype=np.intp)
    num_samples = len(y_t)

    tp = int(np.sum((y_t == 1) & (y_p == 1)))
    fp = int(np.sum((y_t == 0) & (y_p == 1)))
    tn = int(np.sum((y_t == 0) & (y_p == 0)))
    fn = int(np.sum((y_t == 1) & (y_p == 0)))

    accuracy = (tp + tn) / num_samples if num_samples > 0 else 0.0
    precision, recall, f1 = _precision_recall_f1(tp, fp, fn)

    roc_auc = None
    if y_scores is not None:
        roc_auc = _compute_roc_auc(y_t, np.asarray(y_scores, dtype=np.float64))

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "num_samples": num_samples,
    }


def _compute_roc_auc(
    y_true: NDArray[np.intp],
    y_scores: NDArray[np.floating],
) -> float:
    """Compute ROC-AUC using the trapezoidal rule.

    Args:
        y_true: Binary ground truth labels (0 or 1).
        y_scores: Continuous prediction scores.

    Returns:
        ROC-AUC value in [0, 1].
    """
    num_positive = int(np.sum(y_true == 1))
    num_negative = int(np.sum(y_true == 0))

    if num_positive == 0 or num_negative == 0:
        return 0.0

    # Sort by decreasing score
    sorted_indices = np.argsort(-y_scores)
    sorted_true = y_true[sorted_indices]

    # Compute TPR and FPR at each threshold
    tpr_points: list[float] = [0.0]
    fpr_points: list[float] = [0.0]
    tp_count = 0
    fp_count = 0

    for label in sorted_true:
        if label == 1:
            tp_count += 1
        else:
            fp_count += 1
        tpr_points.append(tp_count / num_positive)
        fpr_points.append(fp_count / num_negative)

    # Trapezoidal rule (np.trapz is compatible with numpy>=1.24; np.trapezoid requires 2.0+)
    tpr_arr = np.array(tpr_points)
    fpr_arr = np.array(fpr_points)
    auc = float(np.trapz(tpr_arr, fpr_arr))
    return auc


def compute_regression_report(
    y_true: list[float] | NDArray[np.floating],
    y_pred: list[float] | NDArray[np.floating],
) -> dict[str, Any]:
    """Compute regression metrics by delegating to arena metrics.

    Args:
        y_true: Ground truth continuous values.
        y_pred: Predicted continuous values.

    Returns:
        Dictionary with plcc, srcc, mae, rmse, num_samples.
    """
    from image_preprocessing_detector.labeling.arena.metrics import (
        compute_mae,
        compute_plcc,
        compute_rmse,
        compute_srcc,
    )

    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)

    return {
        "plcc": round(compute_plcc(y_p, y_t), 4),
        "srcc": round(compute_srcc(y_p, y_t), 4),
        "mae": round(compute_mae(y_p, y_t), 4),
        "rmse": round(compute_rmse(y_p, y_t), 4),
        "num_samples": len(y_t),
    }


def format_confusion_matrix(
    matrix: list[list[int]] | NDArray[np.intp],
    class_names: list[str],
) -> str:
    """Format confusion matrix as an ASCII table.

    Args:
        matrix: Confusion matrix (row=true, col=pred).
        class_names: Class names for row/column headers.

    Returns:
        Multi-line string with formatted confusion matrix.
    """
    mat = np.asarray(matrix)
    # Determine column widths
    max_name = max(len(n) for n in class_names)
    max_val = max(len(str(int(mat.max()))), 3) if mat.size > 0 else 3
    col_width = max(max_name, max_val) + 2

    lines: list[str] = []

    # Header row
    header = " " * (max_name + 2) + "".join(n.rjust(col_width) for n in class_names)
    lines.append(header)
    lines.append("-" * len(header))

    # Data rows
    for idx, name in enumerate(class_names):
        row_values = "".join(
            str(int(mat[idx, j])).rjust(col_width) for j in range(len(class_names))
        )
        lines.append(f"{name.rjust(max_name)}  {row_values}")

    return "\n".join(lines)


def collect_system_info() -> dict[str, str]:
    """Collect system information for benchmark reproducibility.

    Returns:
        Dictionary with platform, python version, opencv version.
    """
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "opencv": cv2.__version__,
        "numpy": np.__version__,
    }


def save_benchmark_result(
    result: dict[str, Any],
    output_dir: Path,
    detector_name: str,
) -> Path:
    """Save benchmark result to timestamped JSON file.

    Args:
        result: Benchmark result dictionary.
        output_dir: Directory to write the file to.
        detector_name: Detector name for filename.

    Returns:
        Path to the saved JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"{detector_name}_{timestamp}.json"
    output_path = output_dir / filename

    with open(output_path, "w") as fh:
        json.dump(result, fh, indent=2)

    return output_path


def compute_latency_stats(latencies_ms: list[float]) -> dict[str, float]:
    """Compute latency statistics from per-image timing measurements.

    Args:
        latencies_ms: List of per-image latencies in milliseconds.

    Returns:
        Dictionary with mean_ms, p50_ms, p95_ms, p99_ms, min_ms, max_ms.
    """
    if not latencies_ms:
        return {
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }

    arr = np.array(latencies_ms)
    return {
        "mean_ms": round(float(np.mean(arr)), 2),
        "p50_ms": round(float(np.median(arr)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "p99_ms": round(float(np.percentile(arr, 99)), 2),
        "min_ms": round(float(np.min(arr)), 2),
        "max_ms": round(float(np.max(arr)), 2),
    }
