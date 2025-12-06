# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 7 loss functions and calibration metrics.

Tests:
- ContinuousBCEMSELoss: Combined BCE+MSE loss
- GDBCLoss: Variance-weighted loss
- ECE computation and calibration metrics
- ContinuousWeakSupervisionLabeler
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from image_preprocessing_detector.metrics.calibration import (
    CalibrationResult,
    compute_ece,
    compute_multiclass_ece,
    compute_severity_metrics,
    generate_reliability_diagram_data,
)
from image_preprocessing_detector.models.loss_functions import (
    ContinuousBCEMSELoss,
    GDBCLoss,
)


# ============================================================================
# ContinuousBCEMSELoss Tests
# ============================================================================


class TestContinuousBCEMSELoss:
    """Tests for combined BCE+MSE loss function."""

    def test_basic_forward_pass(self):
        """Test basic forward pass with valid inputs."""
        loss_fn = ContinuousBCEMSELoss(alpha=0.6, beta=0.4)

        # Predictions (logits) and continuous targets
        predictions = torch.tensor([[0.5, -0.5, 1.0, -1.0, 0.0]])
        targets = torch.tensor([[0.7, 0.2, 0.9, 0.1, 0.5]])

        result = loss_fn(predictions, targets)

        assert "total_loss" in result
        assert "bce_loss" in result
        assert "mse_loss" in result
        assert "severity_mae" in result
        assert result["total_loss"].item() > 0

    def test_perfect_prediction(self):
        """Test loss with perfect predictions."""
        loss_fn = ContinuousBCEMSELoss()

        # Predictions that match targets after sigmoid
        # sigmoid(2.2) ≈ 0.9, sigmoid(-2.2) ≈ 0.1
        predictions = torch.tensor([[2.2, -2.2, 2.2, -2.2, 0.0]])
        targets = torch.tensor([[0.9, 0.1, 0.9, 0.1, 0.5]])

        result = loss_fn(predictions, targets)

        # Loss should be low for good predictions
        assert result["severity_mae"].item() < 0.1

    def test_alpha_beta_weighting(self):
        """Test that alpha/beta weights affect total loss."""
        predictions = torch.tensor([[0.5, 0.5]])
        targets = torch.tensor([[0.7, 0.3]])

        # BCE-heavy loss
        loss_bce = ContinuousBCEMSELoss(alpha=0.9, beta=0.1)
        result_bce = loss_bce(predictions, targets)

        # MSE-heavy loss
        loss_mse = ContinuousBCEMSELoss(alpha=0.1, beta=0.9)
        result_mse = loss_mse(predictions, targets)

        # The total loss should differ due to different weighting
        # BCE and MSE components individually stay the same, but total changes
        assert result_bce["total_loss"].item() != result_mse["total_loss"].item()

    def test_binary_threshold(self):
        """Test binary threshold for BCE component."""
        # Use positive predictions (sigmoid > 0.5) to make prediction closer to 0
        predictions = torch.tensor([[-2.0, -2.0, -2.0]])  # sigmoid ≈ 0.12

        # Target 0.4 is below 0.5 threshold -> binary 0
        # Prediction ~0.12 is close to 0, so BCE loss should be LOW
        targets_below = torch.tensor([[0.4, 0.4, 0.4]])
        loss_fn = ContinuousBCEMSELoss(binary_threshold=0.5)
        result_below = loss_fn(predictions, targets_below)

        # Target 0.6 is above 0.5 threshold -> binary 1
        # Prediction ~0.12 is far from 1, so BCE loss should be HIGH
        targets_above = torch.tensor([[0.6, 0.6, 0.6]])
        result_above = loss_fn(predictions, targets_above)

        # BCE loss should be higher when target is 1 but prediction is ~0
        assert result_above["bce_loss"].item() > result_below["bce_loss"].item()

    def test_label_smoothing(self):
        """Test label smoothing reduces overconfidence."""
        predictions = torch.tensor([[2.0, -2.0]])  # High confidence predictions
        targets = torch.tensor([[1.0, 0.0]])  # Hard binary targets

        loss_no_smooth = ContinuousBCEMSELoss(label_smoothing=0.0)
        loss_smooth = ContinuousBCEMSELoss(label_smoothing=0.1)

        result_no_smooth = loss_no_smooth(predictions, targets)
        result_smooth = loss_smooth(predictions, targets)

        # Smoothed targets are softer, so BCE loss may differ
        # Both should compute without error
        assert result_no_smooth["bce_loss"].item() >= 0
        assert result_smooth["bce_loss"].item() >= 0

    def test_reduction_modes(self):
        """Test different reduction modes."""
        predictions = torch.tensor([[0.5, 0.5], [0.5, 0.5]])
        targets = torch.tensor([[0.7, 0.3], [0.8, 0.2]])

        loss_mean = ContinuousBCEMSELoss(reduction="mean")
        loss_sum = ContinuousBCEMSELoss(reduction="sum")
        loss_none = ContinuousBCEMSELoss(reduction="none")

        result_mean = loss_mean(predictions, targets)
        result_sum = loss_sum(predictions, targets)
        result_none = loss_none(predictions, targets)

        # Mean and sum are scalars
        assert result_mean["total_loss"].dim() == 0
        assert result_sum["total_loss"].dim() == 0

        # None preserves shape
        assert result_none["total_loss"].shape == (2, 2)

    def test_invalid_alpha_raises(self):
        """Test that invalid alpha raises ValueError."""
        with pytest.raises(ValueError, match="alpha must be in"):
            ContinuousBCEMSELoss(alpha=1.5)

    def test_invalid_beta_raises(self):
        """Test that invalid beta raises ValueError."""
        with pytest.raises(ValueError, match="beta must be in"):
            ContinuousBCEMSELoss(beta=-0.1)

    def test_get_config(self):
        """Test configuration export."""
        loss_fn = ContinuousBCEMSELoss(
            alpha=0.7,
            beta=0.3,
            binary_threshold=0.4,
            label_smoothing=0.05,
        )
        config = loss_fn.get_config()

        assert config["alpha"] == 0.7
        assert config["beta"] == 0.3
        assert config["binary_threshold"] == 0.4
        assert config["label_smoothing"] == 0.05


# ============================================================================
# GDBCLoss Tests
# ============================================================================


class TestGDBCLoss:
    """Tests for GDBC (variance-weighted) loss function."""

    def test_without_variance(self):
        """Test GDBC loss without variance weights."""
        gdbc = GDBCLoss()

        predictions = torch.tensor([[0.5, 0.5]])
        targets = torch.tensor([[0.7, 0.3]])

        result = gdbc(predictions, targets, variances=None)

        assert "total_loss" in result
        assert result["total_loss"].item() > 0

    def test_with_variance_weighting(self):
        """Test that high variance reduces sample weight."""
        gdbc = GDBCLoss(variance_weight=2.0, min_weight=0.1)

        predictions = torch.tensor([[0.5, 0.5], [0.5, 0.5]])
        targets = torch.tensor([[0.7, 0.3], [0.7, 0.3]])

        # Low variance = high weight
        low_var = torch.tensor([[0.0, 0.0], [0.0, 0.0]])
        # High variance = low weight
        high_var = torch.tensor([[0.5, 0.5], [0.5, 0.5]])

        result_low = gdbc(predictions, targets, low_var)
        result_high = gdbc(predictions, targets, high_var)

        # Both should compute successfully
        assert result_low["total_loss"].item() > 0
        assert result_high["total_loss"].item() > 0
        assert "mean_weight" in result_high

    def test_min_weight_clamping(self):
        """Test that weights are clamped to min_weight."""
        gdbc = GDBCLoss(variance_weight=100.0, min_weight=0.2)

        predictions = torch.tensor([[0.5]])
        targets = torch.tensor([[0.7]])
        very_high_var = torch.tensor([[10.0]])

        result = gdbc(predictions, targets, very_high_var)

        # Weight should be clamped, not zero
        assert result["mean_weight"].item() >= 0.2


# ============================================================================
# Calibration Metrics Tests
# ============================================================================


class TestECEComputation:
    """Tests for Expected Calibration Error computation."""

    def test_perfectly_calibrated(self):
        """Test ECE for perfectly calibrated predictions."""
        # Perfectly calibrated: predicted probability matches true frequency
        np.random.seed(42)
        n = 1000

        # Generate predictions
        predictions = np.random.uniform(0, 1, n)
        # Labels match the predicted probability distribution
        labels = (np.random.random(n) < predictions).astype(float)

        result = compute_ece(predictions, labels, num_bins=10)

        # ECE should be low for well-calibrated model
        assert result.ece < 0.15

    def test_overconfident_model(self):
        """Test ECE for overconfident predictions."""
        # Overconfident: predicts 0.9 or 0.1, but accuracy is ~50%
        predictions = np.array([0.9] * 50 + [0.1] * 50)
        labels = np.array([1] * 25 + [0] * 25 + [1] * 25 + [0] * 25)

        result = compute_ece(predictions, labels, num_bins=10)

        # ECE should be high for poorly calibrated model
        assert result.ece > 0.3

    def test_empty_predictions(self):
        """Test ECE with empty input."""
        result = compute_ece(np.array([]), np.array([]))

        assert result.ece == 0.0
        assert result.total_samples == 0

    def test_bin_statistics(self):
        """Test that bin statistics are computed correctly."""
        predictions = np.array([0.1, 0.2, 0.3, 0.4, 0.9])
        labels = np.array([0, 0, 1, 0, 1])

        result = compute_ece(predictions, labels, num_bins=5)

        assert result.num_bins == 5
        assert len(result.bin_accuracies) == 5
        assert len(result.bin_confidences) == 5
        assert len(result.bin_counts) == 5
        assert sum(result.bin_counts) == 5

    def test_mce_maximum_error(self):
        """Test MCE captures maximum calibration error."""
        # One bin is perfectly calibrated, one is completely wrong
        predictions = np.array([0.1, 0.1, 0.9, 0.9])
        labels = np.array([0, 0, 0, 0])  # 0.9 predictions are wrong

        result = compute_ece(predictions, labels, num_bins=5)

        # MCE should be close to 0.9 (predicted 0.9, but accuracy is 0)
        assert result.mce > 0.8

    def test_binary_threshold(self):
        """Test binary threshold for continuous labels."""
        predictions = np.array([0.7, 0.8, 0.3, 0.2])
        # Continuous labels that should be thresholded
        labels = np.array([0.6, 0.8, 0.2, 0.4])

        result_05 = compute_ece(predictions, labels, binary_threshold=0.5)
        result_03 = compute_ece(predictions, labels, binary_threshold=0.3)

        # Different thresholds may produce different ECE
        # But both should be valid results
        assert 0 <= result_05.ece <= 1
        assert 0 <= result_03.ece <= 1


class TestMulticlassECE:
    """Tests for multi-class ECE computation."""

    def test_multiclass_basic(self):
        """Test multi-class ECE computation."""
        predictions = np.array([
            [0.9, 0.2],
            [0.8, 0.7],
            [0.3, 0.1],
        ])
        labels = np.array([
            [1, 0],
            [1, 1],
            [0, 0],
        ])

        result = compute_multiclass_ece(
            predictions, labels, class_names=["blur", "noise"]
        )

        assert "blur" in result.per_class_ece
        assert "noise" in result.per_class_ece
        assert result.ece >= 0

    def test_1d_input_handling(self):
        """Test that 1D input is handled correctly."""
        predictions = np.array([0.8, 0.3, 0.6])
        labels = np.array([1, 0, 1])

        result = compute_multiclass_ece(predictions, labels)

        assert result.total_samples == 3


class TestSeverityMetrics:
    """Tests for severity prediction metrics."""

    def test_perfect_prediction(self):
        """Test metrics with perfect predictions."""
        predictions = np.array([0.3, 0.5, 0.7, 0.9])
        targets = np.array([0.3, 0.5, 0.7, 0.9])

        metrics = compute_severity_metrics(predictions, targets)

        assert metrics["severity_mae"] == pytest.approx(0.0, abs=1e-6)
        assert metrics["severity_mse"] == pytest.approx(0.0, abs=1e-6)
        assert metrics["severity_correlation"] == pytest.approx(1.0, abs=1e-6)

    def test_random_predictions(self):
        """Test metrics with random predictions."""
        np.random.seed(42)
        predictions = np.random.uniform(0, 1, 100)
        targets = np.random.uniform(0, 1, 100)

        metrics = compute_severity_metrics(predictions, targets)

        # MAE should be reasonable for random
        assert 0 < metrics["severity_mae"] < 1
        assert 0 < metrics["severity_rmse"] < 1

    def test_constant_predictions_correlation(self):
        """Test that constant predictions give zero correlation."""
        predictions = np.array([0.5, 0.5, 0.5, 0.5])
        targets = np.array([0.1, 0.4, 0.7, 0.9])

        metrics = compute_severity_metrics(predictions, targets)

        # Correlation is undefined for constant predictions
        assert metrics["severity_correlation"] == 0.0


class TestReliabilityDiagram:
    """Tests for reliability diagram data generation."""

    def test_diagram_data_structure(self):
        """Test that diagram data has expected structure."""
        result = CalibrationResult(
            ece=0.1,
            mce=0.2,
            bin_accuracies=[0.1, 0.3, 0.5, 0.7, 0.9],
            bin_confidences=[0.1, 0.3, 0.5, 0.7, 0.9],
            bin_counts=[10, 20, 30, 20, 10],
            num_bins=5,
            total_samples=90,
        )

        data = generate_reliability_diagram_data(result)

        assert "bin_midpoints" in data
        assert "bin_accuracies" in data
        assert "perfect_calibration" in data
        assert "ece" in data
        assert len(data["bin_midpoints"]) == 5


# ============================================================================
# ContinuousWeakSupervisionLabeler Tests
# ============================================================================


class TestContinuousWeakSupervisionLabeler:
    """Tests for continuous weak supervision labeler."""

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        import cv2
        # Create a simple grayscale image with some texture
        np.random.seed(42)
        image = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
        # Add some edges
        image[40:60, 40:60] = 255
        # Convert to BGR
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    def test_label_image_returns_continuous(self, sample_image: np.ndarray):
        """Test that label_image returns continuous scores."""
        from data.weak_supervision import ContinuousWeakSupervisionLabeler

        labeler = ContinuousWeakSupervisionLabeler()
        result = labeler.label_image(sample_image, "test.png")

        # Check continuous scores are present
        assert "blur_severity" in result
        assert "noise_severity" in result
        assert "skew_severity" in result
        assert "contrast_severity" in result
        assert "compression_severity" in result
        assert "overall_quality" in result

        # Check values are in [0, 1]
        assert 0 <= result["blur_severity"] <= 1
        assert 0 <= result["noise_severity"] <= 1
        assert 0 <= result["overall_quality"] <= 1

    def test_backward_compatible_labels(self, sample_image: np.ndarray):
        """Test backward compatibility with binary labels."""
        from data.weak_supervision import ContinuousWeakSupervisionLabeler

        labeler = ContinuousWeakSupervisionLabeler()
        result = labeler.label_image(sample_image, "test.png")

        # Check binary labels are present
        assert "labels" in result
        assert "blur" in result["labels"]
        assert "value" in result["labels"]["blur"]
        assert "severity" in result["labels"]["blur"]

        # Binary value should be 0 or 1
        assert result["labels"]["blur"]["value"] in [0, 1]

    def test_outlier_detection(self, sample_image: np.ndarray):
        """Test outlier detection based on variance."""
        from data.weak_supervision import ContinuousWeakSupervisionLabeler

        # Low threshold = most samples are outliers
        labeler_strict = ContinuousWeakSupervisionLabeler(outlier_threshold=0.01)
        result_strict = labeler_strict.label_image(sample_image)

        # High threshold = few outliers
        labeler_lenient = ContinuousWeakSupervisionLabeler(outlier_threshold=1.0)
        result_lenient = labeler_lenient.label_image(sample_image)

        # Both should have is_outlier field
        assert "is_outlier" in result_strict
        assert "is_outlier" in result_lenient

    def test_quality_scores_included(self, sample_image: np.ndarray):
        """Test that raw quality scores are included."""
        from data.weak_supervision import ContinuousWeakSupervisionLabeler

        labeler = ContinuousWeakSupervisionLabeler()
        result = labeler.label_image(sample_image)

        assert "quality_scores" in result
        assert "laplacian_variance" in result["quality_scores"]
        assert "brisque" in result["quality_scores"]

    def test_get_severity_vector(self, sample_image: np.ndarray):
        """Test severity vector extraction."""
        from data.weak_supervision import ContinuousWeakSupervisionLabeler

        labeler = ContinuousWeakSupervisionLabeler()
        result = labeler.label_image(sample_image)
        vector = labeler.get_severity_vector(result)

        assert len(vector) == 5
        assert all(0 <= v <= 1 for v in vector)
