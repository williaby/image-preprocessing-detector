"""Tests for DeQA analysis module.

This module tests the metrics computation, label comparison,
and analysis functions.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from image_preprocessing_detector.labeling.deqa.analysis import (
    analyze_label_set,
    compare_label_sets,
    compare_to_ground_truth,
    compute_plcc,
    compute_rmse,
    compute_srcc,
    compute_vquala_score,
    generate_comparison_report,
    load_labels,
)


class TestComputeSRCC:
    """Tests for SRCC computation."""

    def test_perfect_correlation(self) -> None:
        """Test SRCC with perfect correlation."""
        scores_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        scores_b = [1.0, 2.0, 3.0, 4.0, 5.0]
        srcc = compute_srcc(scores_a, scores_b)
        assert abs(srcc - 1.0) < 0.001

    def test_inverse_correlation(self) -> None:
        """Test SRCC with inverse correlation."""
        scores_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        scores_b = [5.0, 4.0, 3.0, 2.0, 1.0]
        srcc = compute_srcc(scores_a, scores_b)
        assert abs(srcc - (-1.0)) < 0.001

    def test_no_correlation(self) -> None:
        """Test SRCC with uncorrelated data."""
        scores_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        scores_b = [3.0, 1.0, 5.0, 2.0, 4.0]
        srcc = compute_srcc(scores_a, scores_b)
        assert -0.5 < srcc < 0.5

    def test_insufficient_samples(self) -> None:
        """Test SRCC returns 0 for insufficient samples."""
        assert abs(compute_srcc([1.0], [1.0])) < 1e-9
        assert abs(compute_srcc([], [])) < 1e-9

    def test_with_ties(self) -> None:
        """Test SRCC handles ties."""
        scores_a = [1.0, 2.0, 2.0, 3.0, 4.0]
        scores_b = [1.0, 2.5, 2.5, 3.0, 4.0]
        srcc = compute_srcc(scores_a, scores_b)
        assert srcc > 0.9  # Should still be highly correlated


class TestComputePLCC:
    """Tests for PLCC computation."""

    def test_perfect_correlation(self) -> None:
        """Test PLCC with perfect linear correlation."""
        scores_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        scores_b = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x
        plcc = compute_plcc(scores_a, scores_b)
        assert abs(plcc - 1.0) < 0.001

    def test_inverse_correlation(self) -> None:
        """Test PLCC with inverse correlation."""
        scores_a = [1.0, 2.0, 3.0, 4.0, 5.0]
        scores_b = [10.0, 8.0, 6.0, 4.0, 2.0]
        plcc = compute_plcc(scores_a, scores_b)
        assert abs(plcc - (-1.0)) < 0.001

    def test_insufficient_samples(self) -> None:
        """Test PLCC returns 0 for insufficient samples."""
        assert abs(compute_plcc([1.0], [1.0])) < 1e-9
        assert abs(compute_plcc([], [])) < 1e-9


class TestComputeRMSE:
    """Tests for RMSE computation."""

    def test_identical_scores(self) -> None:
        """Test RMSE is 0 for identical scores."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        rmse = compute_rmse(scores, scores)
        assert abs(rmse) < 0.001

    def test_known_rmse(self) -> None:
        """Test RMSE with known difference."""
        scores_a = [1.0, 2.0, 3.0]
        scores_b = [2.0, 3.0, 4.0]  # All differ by 1.0
        rmse = compute_rmse(scores_a, scores_b)
        assert abs(rmse - 1.0) < 0.001

    def test_empty_lists(self) -> None:
        """Test RMSE handles empty lists."""
        rmse = compute_rmse([], [])
        assert abs(rmse) < 1e-9


class TestLoadLabels:
    """Tests for load_labels function."""

    def test_load_valid_jsonl(self) -> None:
        """Test loading valid JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            label_file = Path(tmpdir) / "labels.jsonl"
            labels_data = [
                {"image": "img1.jpg", "scores": {"overall": 4.0}},
                {"image": "img2.jpg", "scores": {"overall": 3.5}},
            ]
            with open(label_file, "w") as f:
                f.writelines(json.dumps(label) + "\n" for label in labels_data)

            # Change to tmpdir to make relative path work
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                labels = load_labels(Path("labels.jsonl"))
                assert len(labels) == 2
                assert labels[0]["image"] == "img1.jpg"
            finally:
                os.chdir(old_cwd)

    def test_path_traversal_prevention(self) -> None:
        """Test that path traversal is prevented."""
        with pytest.raises(ValueError, match="Path traversal"):
            load_labels(Path("../../../etc/passwd"))

    def test_file_not_found(self) -> None:
        """Test FileNotFoundError for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(FileNotFoundError):
                    load_labels(Path("nonexistent.jsonl"))
            finally:
                os.chdir(old_cwd)


class TestAnalyzeLabelSet:
    """Tests for analyze_label_set function."""

    def test_basic_analysis(self) -> None:
        """Test basic label set analysis."""
        labels = [
            {
                "dataset": "test-dataset",
                "mode": "specialist",
                "scores": {"overall": 4.0, "sharpness": 3.5},
            },
            {
                "dataset": "test-dataset",
                "mode": "specialist",
                "scores": {"overall": 3.5, "sharpness": 4.0},
            },
            {
                "dataset": "test-dataset",
                "mode": "specialist",
                "scores": {"overall": 4.5, "sharpness": 3.0},
            },
        ]
        analysis = analyze_label_set(labels)
        assert analysis.dataset == "test-dataset"
        assert analysis.mode == "specialist"
        assert analysis.num_samples == 3
        assert "overall" in analysis.dimension_stats
        assert "sharpness" in analysis.dimension_stats

    def test_analysis_statistics(self) -> None:
        """Test that statistics are computed correctly."""
        labels = [
            {"scores": {"overall": 3.0}},
            {"scores": {"overall": 4.0}},
            {"scores": {"overall": 5.0}},
        ]
        analysis = analyze_label_set(labels)
        stats = analysis.dimension_stats["overall"]
        assert abs(stats["mean"] - 4.0) < 0.001
        assert abs(stats["min"] - 3.0) < 1e-9
        assert abs(stats["max"] - 5.0) < 1e-9

    def test_empty_labels(self) -> None:
        """Test analysis of empty label set."""
        analysis = analyze_label_set([])
        assert analysis.num_samples == 0


class TestCompareLabelSets:
    """Tests for compare_label_sets function."""

    def test_identical_labels(self) -> None:
        """Test comparing identical label sets."""
        labels = [
            {"image": "img1.jpg", "scores": {"overall": 4.0}},
            {"image": "img2.jpg", "scores": {"overall": 3.5}},
        ]
        metrics = compare_label_sets(labels, labels)
        assert "overall" in metrics
        assert abs(metrics["overall"].srcc - 1.0) < 0.001
        assert abs(metrics["overall"].rmse) < 0.001

    def test_different_labels(self) -> None:
        """Test comparing different label sets."""
        labels_a = [
            {"image": "img1.jpg", "scores": {"overall": 4.0, "sharpness": 3.5}},
            {"image": "img2.jpg", "scores": {"overall": 3.0, "sharpness": 4.5}},
        ]
        labels_b = [
            {"image": "img1.jpg", "scores": {"overall": 4.2, "sharpness": 3.3}},
            {"image": "img2.jpg", "scores": {"overall": 2.8, "sharpness": 4.7}},
        ]
        metrics = compare_label_sets(labels_a, labels_b, "method_a", "method_b")
        assert "overall" in metrics
        assert "sharpness" in metrics
        assert metrics["overall"].method_a == "method_a"
        assert metrics["overall"].method_b == "method_b"


class TestCompareToGroundTruth:
    """Tests for compare_to_ground_truth function."""

    def test_compare_to_gt(self) -> None:
        """Test comparison against ground truth."""
        predictions = [
            {
                "image": "img1.jpg",
                "scores": {"overall": 4.0, "sharpness": 3.5, "color": 4.2},
            },
            {
                "image": "img2.jpg",
                "scores": {"overall": 3.0, "sharpness": 4.5, "color": 3.8},
            },
            {
                "image": "img3.jpg",
                "scores": {"overall": 5.0, "sharpness": 2.5, "color": 4.0},
            },
        ]
        ground_truth = [
            {
                "image": "img1.jpg",
                "scores": {"overall": 4.1, "sharpness": 3.4, "color": 4.3},
            },
            {
                "image": "img2.jpg",
                "scores": {"overall": 3.1, "sharpness": 4.6, "color": 3.7},
            },
            {
                "image": "img3.jpg",
                "scores": {"overall": 4.9, "sharpness": 2.6, "color": 4.1},
            },
        ]
        metrics = compare_to_ground_truth(predictions, ground_truth)
        assert "overall" in metrics
        assert "sharpness" in metrics
        assert "color" in metrics
        # With very similar values, SRCCs should be high
        assert metrics["overall"].srcc > 0.9


class TestComputeVQualAScore:
    """Tests for compute_vquala_score function."""

    def test_compute_vquala_score(self) -> None:
        """Test VQualA score computation from metrics."""
        predictions = [
            {
                "image": "img1.jpg",
                "scores": {"overall": 4.0, "sharpness": 3.5, "color": 4.2},
            },
            {
                "image": "img2.jpg",
                "scores": {"overall": 3.0, "sharpness": 4.5, "color": 3.8},
            },
            {
                "image": "img3.jpg",
                "scores": {"overall": 5.0, "sharpness": 2.5, "color": 4.0},
            },
        ]
        ground_truth = [
            {
                "image": "img1.jpg",
                "scores": {"overall": 4.1, "sharpness": 3.4, "color": 4.3},
            },
            {
                "image": "img2.jpg",
                "scores": {"overall": 3.1, "sharpness": 4.6, "color": 3.7},
            },
            {
                "image": "img3.jpg",
                "scores": {"overall": 4.9, "sharpness": 2.6, "color": 4.1},
            },
        ]
        metrics = compare_to_ground_truth(predictions, ground_truth)
        vquala = compute_vquala_score(metrics)
        assert vquala is not None
        assert vquala.overall_srcc > 0.9
        assert vquala.final_score > 0.8

    def test_missing_dimensions(self) -> None:
        """Test VQualA score with missing dimensions."""
        labels = [
            {"image": "img1.jpg", "scores": {"overall": 4.0}},
            {"image": "img2.jpg", "scores": {"overall": 3.0}},
        ]
        metrics = compare_label_sets(labels, labels)
        # Only has "overall", missing sharpness and color
        vquala = compute_vquala_score(metrics)
        assert vquala is None


class TestGenerateComparisonReport:
    """Tests for generate_comparison_report function."""

    def test_report_generation(self) -> None:
        """Test report generation."""
        specialist_labels = [
            {
                "image": "img1.jpg",
                "dataset": "test",
                "mode": "specialist",
                "scores": {"overall": 4.0},
            },
            {
                "image": "img2.jpg",
                "dataset": "test",
                "mode": "specialist",
                "scores": {"overall": 3.5},
            },
        ]
        ensemble_labels = [
            {
                "image": "img1.jpg",
                "dataset": "test",
                "mode": "ensemble",
                "scores": {"overall": 4.1},
            },
            {
                "image": "img2.jpg",
                "dataset": "test",
                "mode": "ensemble",
                "scores": {"overall": 3.6},
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            report = generate_comparison_report(
                specialist_labels,
                ensemble_labels,
                output_path=output_path,
            )

            # Check report was created
            assert output_path.exists()

            # Check report content
            assert "DeQA Label Comparison Report" in report
            assert "Specialist" in report
            assert "Ensemble" in report


class TestVQualAScoreIntegration:
    """Integration tests for VQualA scoring."""

    def test_realistic_scoring(self) -> None:
        """Test with realistic score distributions."""
        # Simulate realistic predictions and ground truth
        rng = np.random.default_rng(42)
        n_samples = 100

        # Generate correlated scores (simulating good predictions)
        gt_overall = rng.uniform(2.0, 5.0, n_samples)
        gt_sharpness = rng.uniform(2.0, 5.0, n_samples)
        gt_color = rng.uniform(2.0, 5.0, n_samples)

        # Add noise to predictions
        pred_overall = gt_overall + rng.normal(0, 0.2, n_samples)
        pred_sharpness = gt_sharpness + rng.normal(0, 0.3, n_samples)
        pred_color = gt_color + rng.normal(0, 0.25, n_samples)

        # Create label format
        predictions = [
            {
                "image": f"img{i}.jpg",
                "scores": {
                    "overall": float(pred_overall[i]),
                    "sharpness": float(pred_sharpness[i]),
                    "color": float(pred_color[i]),
                },
            }
            for i in range(n_samples)
        ]
        ground_truth = [
            {
                "image": f"img{i}.jpg",
                "scores": {
                    "overall": float(gt_overall[i]),
                    "sharpness": float(gt_sharpness[i]),
                    "color": float(gt_color[i]),
                },
            }
            for i in range(n_samples)
        ]

        metrics = compare_to_ground_truth(predictions, ground_truth)
        vquala = compute_vquala_score(metrics)

        # With low noise, correlations should be high
        assert vquala is not None
        assert vquala.overall_srcc > 0.8
        assert vquala.sharpness_srcc > 0.7
        assert vquala.color_srcc > 0.7
        assert vquala.final_score > 0.75
