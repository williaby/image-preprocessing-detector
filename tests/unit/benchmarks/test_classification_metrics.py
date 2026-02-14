"""Unit tests for Stream 3 classification metrics module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmarks.classification_metrics import (
    _compute_roc_auc,
    _precision_recall_f1,
    compute_binary_report,
    compute_classification_report,
    compute_confusion_matrix,
    compute_latency_stats,
    compute_regression_report,
    format_confusion_matrix,
    save_benchmark_result,
)

# =============================================================================
# Precision / Recall / F1
# =============================================================================


class TestPrecisionRecallF1:
    """Tests for the _precision_recall_f1 helper."""

    def test_perfect_scores(self) -> None:
        p, r, f = _precision_recall_f1(tp=10, fp=0, fn=0)
        assert p == 1.0
        assert r == 1.0
        assert f == 1.0

    def test_zero_tp(self) -> None:
        p, r, f = _precision_recall_f1(tp=0, fp=5, fn=5)
        assert p == 0.0
        assert r == 0.0
        assert f == 0.0

    def test_all_zeros(self) -> None:
        p, r, f = _precision_recall_f1(tp=0, fp=0, fn=0)
        assert p == 0.0
        assert r == 0.0
        assert f == 0.0

    def test_partial_scores(self) -> None:
        # tp=6, fp=2, fn=4 -> precision=6/8=0.75, recall=6/10=0.6, f1=2*0.75*0.6/1.35
        p, r, f = _precision_recall_f1(tp=6, fp=2, fn=4)
        assert p == pytest.approx(0.75)
        assert r == pytest.approx(0.6)
        assert f == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))


# =============================================================================
# Confusion Matrix
# =============================================================================


class TestConfusionMatrix:
    """Tests for compute_confusion_matrix."""

    def test_perfect_predictions(self) -> None:
        y_true = [0, 1, 2, 0, 1, 2]
        y_pred = [0, 1, 2, 0, 1, 2]
        cm = compute_confusion_matrix(y_true, y_pred, num_classes=3)
        expected = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(cm, expected)

    def test_all_wrong(self) -> None:
        y_true = [0, 0, 0]
        y_pred = [1, 1, 1]
        cm = compute_confusion_matrix(y_true, y_pred, num_classes=2)
        assert cm[0, 0] == 0  # TP for class 0
        assert cm[0, 1] == 3  # class 0 predicted as 1

    def test_empty_inputs(self) -> None:
        cm = compute_confusion_matrix([], [], num_classes=2)
        expected = np.zeros((2, 2), dtype=np.intp)
        np.testing.assert_array_equal(cm, expected)

    def test_single_class(self) -> None:
        cm = compute_confusion_matrix([0, 0, 0], [0, 0, 0], num_classes=1)
        assert cm[0, 0] == 3


# =============================================================================
# Classification Report
# =============================================================================


class TestClassificationReport:
    """Tests for compute_classification_report."""

    def test_perfect_classification(self) -> None:
        y_true = [0, 1, 2, 0, 1, 2]
        y_pred = [0, 1, 2, 0, 1, 2]
        report = compute_classification_report(y_true, y_pred, ["a", "b", "c"])

        assert report["accuracy"] == 1.0
        assert report["macro_f1"] == 1.0
        assert report["weighted_f1"] == 1.0
        assert report["cohens_kappa"] == 1.0
        assert report["num_samples"] == 6

    def test_known_misclassifications(self) -> None:
        # 3 classes, 6 samples, 4 correct
        y_true = [0, 1, 2, 0, 1, 2]
        y_pred = [0, 1, 1, 0, 2, 2]
        report = compute_classification_report(y_true, y_pred, ["a", "b", "c"])

        assert report["accuracy"] == pytest.approx(4 / 6, abs=0.001)
        assert report["num_samples"] == 6
        # Class "a" is perfect
        assert report["per_class"]["a"]["f1"] == 1.0
        # Class "b": tp=1, fp=1(true=2,pred=1), fn=1(true=1,pred=2)
        assert report["per_class"]["b"]["precision"] == pytest.approx(0.5, abs=0.01)
        assert report["per_class"]["b"]["recall"] == pytest.approx(0.5, abs=0.01)

    def test_confusion_matrix_shape(self) -> None:
        y_true = [0, 1, 2]
        y_pred = [0, 1, 2]
        report = compute_classification_report(y_true, y_pred, ["x", "y", "z"])
        cm = report["confusion_matrix"]
        assert len(cm) == 3
        assert len(cm[0]) == 3

    def test_class_names_preserved(self) -> None:
        names = ["latin", "cjk", "arabic"]
        report = compute_classification_report([0, 1, 2], [0, 1, 2], names)
        assert report["class_names"] == names

    def test_single_class_all_correct(self) -> None:
        report = compute_classification_report([0, 0, 0], [0, 0, 0], ["only"])
        assert report["accuracy"] == 1.0
        assert report["macro_f1"] == 1.0


# =============================================================================
# Cohen's Kappa
# =============================================================================


class TestCohensKappa:
    """Tests for Cohen's kappa via classification report."""

    def test_perfect_agreement(self) -> None:
        report = compute_classification_report([0, 1, 0, 1], [0, 1, 0, 1], ["a", "b"])
        assert report["cohens_kappa"] == 1.0

    def test_random_agreement(self) -> None:
        # When agreement matches chance, kappa ~ 0
        # Balanced predictions matching class priors
        y_true = [0, 0, 1, 1]
        y_pred = [0, 1, 0, 1]  # 50% accuracy on balanced = chance
        report = compute_classification_report(y_true, y_pred, ["a", "b"])
        assert report["cohens_kappa"] == pytest.approx(0.0, abs=0.01)


# =============================================================================
# Binary Report
# =============================================================================


class TestBinaryReport:
    """Tests for compute_binary_report."""

    def test_perfect_binary(self) -> None:
        y_true = [0, 0, 1, 1, 1]
        y_pred = [0, 0, 1, 1, 1]
        report = compute_binary_report(y_true, y_pred)

        assert report["accuracy"] == 1.0
        assert report["precision"] == 1.0
        assert report["recall"] == 1.0
        assert report["f1"] == 1.0
        assert report["tp"] == 3
        assert report["tn"] == 2
        assert report["fp"] == 0
        assert report["fn"] == 0

    def test_all_false_positives(self) -> None:
        y_true = [0, 0, 0]
        y_pred = [1, 1, 1]
        report = compute_binary_report(y_true, y_pred)

        assert report["precision"] == 0.0
        assert report["recall"] == 0.0  # No positives in truth
        assert report["fp"] == 3
        assert report["tp"] == 0

    def test_with_scores_roc_auc(self) -> None:
        y_true = [0, 0, 1, 1]
        y_pred = [0, 0, 1, 1]
        y_scores = [0.1, 0.3, 0.7, 0.9]
        report = compute_binary_report(y_true, y_pred, y_scores=y_scores)

        assert report["roc_auc"] is not None
        # Perfect separation -> AUC = 1.0
        assert report["roc_auc"] == pytest.approx(1.0, abs=0.01)

    def test_without_scores_no_auc(self) -> None:
        report = compute_binary_report([0, 1], [0, 1])
        assert report["roc_auc"] is None

    def test_counts_sum_to_total(self) -> None:
        y_true = [0, 1, 0, 1, 1, 0]
        y_pred = [1, 1, 0, 0, 1, 0]
        report = compute_binary_report(y_true, y_pred)
        total = report["tp"] + report["fp"] + report["tn"] + report["fn"]
        assert total == report["num_samples"]


# =============================================================================
# ROC-AUC
# =============================================================================


class TestROCAUC:
    """Tests for _compute_roc_auc."""

    def test_perfect_separation(self) -> None:
        y_true = np.array([0, 0, 1, 1], dtype=np.intp)
        y_scores = np.array([0.1, 0.2, 0.8, 0.9])
        auc = _compute_roc_auc(y_true, y_scores)
        assert auc == pytest.approx(1.0, abs=0.01)

    def test_random_scores(self) -> None:
        # With enough samples, random scores -> AUC ~0.5
        rng = np.random.default_rng(42)
        y_true = np.array([0] * 500 + [1] * 500, dtype=np.intp)
        y_scores = rng.random(1000)
        auc = _compute_roc_auc(y_true, y_scores)
        assert auc == pytest.approx(0.5, abs=0.1)

    def test_no_positives_returns_zero(self) -> None:
        y_true = np.array([0, 0, 0], dtype=np.intp)
        y_scores = np.array([0.1, 0.5, 0.9])
        auc = _compute_roc_auc(y_true, y_scores)
        assert auc == 0.0

    def test_no_negatives_returns_zero(self) -> None:
        y_true = np.array([1, 1, 1], dtype=np.intp)
        y_scores = np.array([0.1, 0.5, 0.9])
        auc = _compute_roc_auc(y_true, y_scores)
        assert auc == 0.0


# =============================================================================
# Regression Report
# =============================================================================


class TestRegressionReport:
    """Tests for compute_regression_report."""

    def test_perfect_predictions(self) -> None:
        y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_pred = [1.0, 2.0, 3.0, 4.0, 5.0]
        report = compute_regression_report(y_true, y_pred)

        assert report["plcc"] == pytest.approx(1.0, abs=0.001)
        assert report["srcc"] == pytest.approx(1.0, abs=0.001)
        assert report["mae"] == pytest.approx(0.0, abs=0.001)
        assert report["rmse"] == pytest.approx(0.0, abs=0.001)
        assert report["num_samples"] == 5

    def test_linear_offset(self) -> None:
        y_true = [1.0, 2.0, 3.0, 4.0]
        y_pred = [2.0, 3.0, 4.0, 5.0]  # Constant offset of 1.0
        report = compute_regression_report(y_true, y_pred)

        assert report["plcc"] == pytest.approx(1.0, abs=0.001)
        assert report["mae"] == pytest.approx(1.0, abs=0.001)


# =============================================================================
# Format Confusion Matrix
# =============================================================================


class TestFormatConfusionMatrix:
    """Tests for format_confusion_matrix."""

    def test_basic_format(self) -> None:
        matrix = [[5, 1], [2, 4]]
        result = format_confusion_matrix(matrix, ["pos", "neg"])
        assert "pos" in result
        assert "neg" in result
        assert "5" in result
        assert "4" in result

    def test_single_class(self) -> None:
        result = format_confusion_matrix([[10]], ["only"])
        assert "10" in result
        assert "only" in result


# =============================================================================
# Save Benchmark Result
# =============================================================================


class TestSaveBenchmarkResult:
    """Tests for save_benchmark_result."""

    def test_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = {"accuracy": 0.95, "num_samples": 100}
            path = save_benchmark_result(result, Path(tmpdir), "test_detector")
            assert path.exists()
            assert path.suffix == ".json"
            assert "test_detector" in path.name

            loaded = json.loads(path.read_text())
            assert loaded["accuracy"] == 0.95

    def test_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub" / "dir"
            result = {"x": 1}
            path = save_benchmark_result(result, nested, "det")
            assert path.exists()


# =============================================================================
# Latency Stats
# =============================================================================


class TestLatencyStats:
    """Tests for compute_latency_stats."""

    def test_basic_stats(self) -> None:
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_latency_stats(latencies)

        assert stats["mean_ms"] == pytest.approx(30.0)
        assert stats["p50_ms"] == pytest.approx(30.0)
        assert stats["min_ms"] == pytest.approx(10.0)
        assert stats["max_ms"] == pytest.approx(50.0)

    def test_empty_returns_zeros(self) -> None:
        stats = compute_latency_stats([])
        assert stats["mean_ms"] == 0.0
        assert stats["p50_ms"] == 0.0

    def test_single_value(self) -> None:
        stats = compute_latency_stats([42.0])
        assert stats["mean_ms"] == 42.0
        assert stats["p50_ms"] == 42.0
        assert stats["p95_ms"] == 42.0
