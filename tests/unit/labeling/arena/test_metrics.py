"""Tests for arena metrics module."""

from __future__ import annotations

import numpy as np
import pytest

from image_preprocessing_detector.labeling.arena.metrics import (
    ArenaMetrics,
    DimensionMetrics,
    compare_models,
    compute_mae,
    compute_plcc,
    compute_rmse,
    compute_srcc,
)


class TestComputePLCC:
    """Tests for compute_plcc function."""

    def test_perfect_correlation(self) -> None:
        """Test PLCC with perfectly correlated data."""
        predictions = [0.1, 0.2, 0.3, 0.4, 0.5]
        ground_truth = [0.1, 0.2, 0.3, 0.4, 0.5]
        plcc = compute_plcc(predictions, ground_truth)
        assert plcc == pytest.approx(1.0, abs=1e-6)

    def test_negative_correlation(self) -> None:
        """Test PLCC with negative correlation."""
        predictions = [0.1, 0.2, 0.3, 0.4, 0.5]
        ground_truth = [0.5, 0.4, 0.3, 0.2, 0.1]
        plcc = compute_plcc(predictions, ground_truth)
        assert plcc == pytest.approx(-1.0, abs=1e-6)

    def test_no_correlation(self) -> None:
        """Test PLCC with uncorrelated data."""
        predictions = [0.1, 0.5, 0.2, 0.8, 0.3]
        ground_truth = [0.3, 0.3, 0.7, 0.2, 0.5]
        plcc = compute_plcc(predictions, ground_truth)
        assert -1.0 <= plcc <= 1.0

    def test_shape_mismatch_raises(self) -> None:
        """Test that shape mismatch raises ValueError."""
        predictions = [0.1, 0.2, 0.3]
        ground_truth = [0.1, 0.2]
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_plcc(predictions, ground_truth)

    def test_nan_values_raise(self) -> None:
        """Test that NaN values raise ValueError."""
        predictions = [0.1, np.nan, 0.3]
        ground_truth = [0.1, 0.2, 0.3]
        with pytest.raises(ValueError, match="contain NaN"):
            compute_plcc(predictions, ground_truth)

    def test_constant_array_returns_zero(self) -> None:
        """Test that constant arrays return 0."""
        predictions = [0.5, 0.5, 0.5]
        ground_truth = [0.1, 0.2, 0.3]
        plcc = compute_plcc(predictions, ground_truth)
        assert plcc == pytest.approx(0.0)

    def test_insufficient_samples_raises(self) -> None:
        """Test that less than 2 samples raises ValueError."""
        with pytest.raises(ValueError, match="Need at least 2"):
            compute_plcc([0.5], [0.5])


class TestComputeSRCC:
    """Tests for compute_srcc function."""

    def test_perfect_rank_correlation(self) -> None:
        """Test SRCC with perfectly ranked data."""
        predictions = [0.1, 0.2, 0.3, 0.4, 0.5]
        ground_truth = [0.2, 0.4, 0.6, 0.8, 1.0]
        srcc = compute_srcc(predictions, ground_truth)
        assert srcc == pytest.approx(1.0, abs=1e-6)

    def test_inverse_rank_correlation(self) -> None:
        """Test SRCC with inverse rankings."""
        predictions = [0.1, 0.2, 0.3, 0.4, 0.5]
        ground_truth = [0.5, 0.4, 0.3, 0.2, 0.1]
        srcc = compute_srcc(predictions, ground_truth)
        assert srcc == pytest.approx(-1.0, abs=1e-6)


class TestComputeMAE:
    """Tests for compute_mae function."""

    def test_zero_error(self) -> None:
        """Test MAE with identical arrays."""
        predictions = [0.1, 0.2, 0.3]
        ground_truth = [0.1, 0.2, 0.3]
        mae = compute_mae(predictions, ground_truth)
        assert mae == pytest.approx(0.0, abs=1e-10)

    def test_known_mae(self) -> None:
        """Test MAE with known values."""
        predictions = [0.1, 0.2, 0.3]
        ground_truth = [0.2, 0.3, 0.4]
        mae = compute_mae(predictions, ground_truth)
        assert mae == pytest.approx(0.1, abs=1e-6)


class TestComputeRMSE:
    """Tests for compute_rmse function."""

    def test_zero_error(self) -> None:
        """Test RMSE with identical arrays."""
        predictions = [0.1, 0.2, 0.3]
        ground_truth = [0.1, 0.2, 0.3]
        rmse = compute_rmse(predictions, ground_truth)
        assert rmse == pytest.approx(0.0, abs=1e-10)

    def test_known_rmse(self) -> None:
        """Test RMSE with known values."""
        predictions = [0.0, 0.0, 0.0]
        ground_truth = [0.1, 0.1, 0.1]
        rmse = compute_rmse(predictions, ground_truth)
        assert rmse == pytest.approx(0.1, abs=1e-6)


class TestDimensionMetrics:
    """Tests for DimensionMetrics dataclass."""

    def test_compute_from_arrays(self) -> None:
        """Test computing metrics from arrays."""
        predictions = [0.1, 0.2, 0.3, 0.4, 0.5]
        ground_truth = [0.15, 0.25, 0.35, 0.45, 0.55]

        metrics = DimensionMetrics.compute(predictions, ground_truth)

        assert metrics.num_samples == 5
        assert 0.9 <= metrics.plcc <= 1.0
        assert 0.9 <= metrics.srcc <= 1.0
        assert 0.0 <= metrics.mae <= 0.1
        assert 0.0 <= metrics.rmse <= 0.1

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        metrics = DimensionMetrics(
            plcc=0.95,
            srcc=0.93,
            mae=0.05,
            rmse=0.07,
            num_samples=100,
        )
        d = metrics.to_dict()

        assert d["plcc"] == pytest.approx(0.95)
        assert d["srcc"] == pytest.approx(0.93)
        assert d["mae"] == pytest.approx(0.05)
        assert d["rmse"] == pytest.approx(0.07)
        assert d["num_samples"] == 100


class TestArenaMetrics:
    """Tests for ArenaMetrics dataclass."""

    def test_compute_from_predictions(self) -> None:
        """Test computing full arena metrics."""
        predictions = {
            "overall": [0.1, 0.2, 0.3, 0.4],
            "sharpness": [0.2, 0.3, 0.4, 0.5],
            "color": [0.3, 0.4, 0.5, 0.6],
        }
        ground_truth = {
            "overall": [0.15, 0.25, 0.35, 0.45],
            "sharpness": [0.25, 0.35, 0.45, 0.55],
            "color": [0.35, 0.45, 0.55, 0.65],
        }

        metrics = ArenaMetrics.compute(predictions, ground_truth)

        assert metrics.overall.num_samples == 4
        assert metrics.sharpness.num_samples == 4
        assert metrics.color.num_samples == 4
        assert metrics.aggregate.num_samples == 4

    def test_aggregate_is_mean(self) -> None:
        """Test that aggregate metrics are means of dimensions."""
        overall = DimensionMetrics(
            plcc=0.9, srcc=0.8, mae=0.1, rmse=0.12, num_samples=10
        )
        sharpness = DimensionMetrics(
            plcc=0.8, srcc=0.7, mae=0.15, rmse=0.18, num_samples=10
        )
        color = DimensionMetrics(
            plcc=0.85, srcc=0.75, mae=0.12, rmse=0.15, num_samples=10
        )

        metrics = ArenaMetrics(overall=overall, sharpness=sharpness, color=color)

        assert metrics.aggregate.plcc == pytest.approx((0.9 + 0.8 + 0.85) / 3)
        assert metrics.aggregate.srcc == pytest.approx((0.8 + 0.7 + 0.75) / 3)
        assert metrics.aggregate.mae == pytest.approx((0.1 + 0.15 + 0.12) / 3)
        assert metrics.aggregate.rmse == pytest.approx((0.12 + 0.18 + 0.15) / 3)

    def test_missing_dimension_raises(self) -> None:
        """Test that missing dimensions raise KeyError."""
        predictions = {"overall": [0.1, 0.2], "sharpness": [0.2, 0.3]}
        ground_truth = {"overall": [0.1, 0.2], "sharpness": [0.2, 0.3]}

        with pytest.raises(KeyError, match="color"):
            ArenaMetrics.compute(predictions, ground_truth)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        predictions = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }
        ground_truth = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }

        metrics = ArenaMetrics.compute(predictions, ground_truth)
        d = metrics.to_dict()

        assert "overall" in d
        assert "sharpness" in d
        assert "color" in d
        assert "aggregate" in d

    def test_summary_string(self) -> None:
        """Test human-readable summary generation."""
        predictions = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }
        ground_truth = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }

        metrics = ArenaMetrics.compute(predictions, ground_truth)
        summary = metrics.summary()

        assert "Arena Metrics Summary" in summary
        assert "Overall" in summary
        assert "Sharpness" in summary
        assert "Color" in summary

    def test_to_markdown(self) -> None:
        """Test Markdown table generation."""
        predictions = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }
        ground_truth = {
            "overall": [0.1, 0.2, 0.3],
            "sharpness": [0.2, 0.3, 0.4],
            "color": [0.3, 0.4, 0.5],
        }

        metrics = ArenaMetrics.compute(predictions, ground_truth)
        md = metrics.to_markdown()

        assert "## Arena Metrics" in md
        assert "| Dimension |" in md
        assert "| Overall |" in md


class TestCompareModels:
    """Tests for compare_models function."""

    def test_ranking_by_plcc(self) -> None:
        """Test ranking models by PLCC."""
        metrics_a = ArenaMetrics(
            overall=DimensionMetrics(
                plcc=0.9, srcc=0.8, mae=0.1, rmse=0.12, num_samples=10
            ),
            sharpness=DimensionMetrics(
                plcc=0.85, srcc=0.75, mae=0.12, rmse=0.15, num_samples=10
            ),
            color=DimensionMetrics(
                plcc=0.88, srcc=0.78, mae=0.11, rmse=0.14, num_samples=10
            ),
        )
        metrics_b = ArenaMetrics(
            overall=DimensionMetrics(
                plcc=0.95, srcc=0.85, mae=0.08, rmse=0.10, num_samples=10
            ),
            sharpness=DimensionMetrics(
                plcc=0.92, srcc=0.82, mae=0.09, rmse=0.11, num_samples=10
            ),
            color=DimensionMetrics(
                plcc=0.93, srcc=0.83, mae=0.08, rmse=0.10, num_samples=10
            ),
        )

        results = {"model_a": metrics_a, "model_b": metrics_b}
        ranked = compare_models(results, sort_by="aggregate.plcc")

        # model_b should be first (higher PLCC)
        assert ranked[0][0] == "model_b"
        assert ranked[1][0] == "model_a"

    def test_ranking_by_mae(self) -> None:
        """Test ranking models by MAE (lower is better)."""
        metrics_a = ArenaMetrics(
            overall=DimensionMetrics(
                plcc=0.9, srcc=0.8, mae=0.05, rmse=0.07, num_samples=10
            ),
            sharpness=DimensionMetrics(
                plcc=0.85, srcc=0.75, mae=0.06, rmse=0.08, num_samples=10
            ),
            color=DimensionMetrics(
                plcc=0.88, srcc=0.78, mae=0.05, rmse=0.07, num_samples=10
            ),
        )
        metrics_b = ArenaMetrics(
            overall=DimensionMetrics(
                plcc=0.95, srcc=0.85, mae=0.10, rmse=0.12, num_samples=10
            ),
            sharpness=DimensionMetrics(
                plcc=0.92, srcc=0.82, mae=0.11, rmse=0.13, num_samples=10
            ),
            color=DimensionMetrics(
                plcc=0.93, srcc=0.83, mae=0.10, rmse=0.12, num_samples=10
            ),
        )

        results = {"model_a": metrics_a, "model_b": metrics_b}
        ranked = compare_models(results, sort_by="aggregate.mae")

        # model_a should be first (lower MAE)
        assert ranked[0][0] == "model_a"
        assert ranked[1][0] == "model_b"
