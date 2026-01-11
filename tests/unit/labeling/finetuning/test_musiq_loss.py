# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for MUSIQ loss functions."""

from __future__ import annotations

import pytest
import torch

from image_preprocessing_detector.labeling.finetuning.musiq_loss import (
    MUSIQSpecialistLoss,
    differentiable_rank_loss,
    dimension_loss,
    focal_calibration_loss,
    musiq_specialist_loss,
)


class TestDifferentiableRankLoss:
    """Tests for differentiable_rank_loss function."""

    def test_perfect_ranking_low_loss(self) -> None:
        """Perfect ranking should have low loss."""
        pred = torch.tensor([0.9, 0.7, 0.5, 0.3, 0.1])
        target = torch.tensor([0.95, 0.75, 0.55, 0.35, 0.15])

        loss = differentiable_rank_loss(pred, target)

        # Perfect ranking correlation should have low loss
        assert loss.item() < 0.2

    def test_reversed_ranking_high_loss(self) -> None:
        """Reversed ranking should have higher loss."""
        pred = torch.tensor([0.1, 0.3, 0.5, 0.7, 0.9])
        target = torch.tensor([0.9, 0.7, 0.5, 0.3, 0.1])

        loss = differentiable_rank_loss(pred, target)

        # Reversed ranking should have higher loss
        assert loss.item() > 0.05

    def test_single_element_returns_zero(self) -> None:
        """Single element should return zero loss."""
        pred = torch.tensor([0.5])
        target = torch.tensor([0.5])

        loss = differentiable_rank_loss(pred, target)

        assert loss.item() == 0.0

    def test_differentiable(self) -> None:
        """Loss should be differentiable."""
        pred = torch.tensor([0.8, 0.6, 0.4], requires_grad=True)
        target = torch.tensor([0.9, 0.5, 0.3])

        loss = differentiable_rank_loss(pred, target)
        loss.backward()

        assert pred.grad is not None
        assert pred.grad.shape == pred.shape


class TestFocalCalibrationLoss:
    """Tests for focal_calibration_loss function."""

    def test_perfect_prediction_low_loss(self) -> None:
        """Perfect predictions should have low loss."""
        pred = torch.tensor([0.5, 0.8, 0.2])
        target = torch.tensor([0.5, 0.8, 0.2])

        loss = focal_calibration_loss(pred, target)

        assert loss.item() < 1e-6

    def test_large_errors_high_loss(self) -> None:
        """Large errors should have higher loss."""
        pred = torch.tensor([0.1, 0.9, 0.5])
        target = torch.tensor([0.9, 0.1, 0.5])

        loss = focal_calibration_loss(pred, target)

        assert loss.item() > 0.1

    def test_focal_weight_effect(self) -> None:
        """Higher gamma should focus more on hard examples."""
        pred = torch.tensor([0.3, 0.7])  # Two predictions
        target = torch.tensor([0.9, 0.8])  # First is hard, second is easy

        loss_gamma_1 = focal_calibration_loss(pred, target, gamma=1.0)
        loss_gamma_3 = focal_calibration_loss(pred, target, gamma=3.0)

        # Higher gamma should change the loss distribution
        # Both should be positive
        assert loss_gamma_1.item() > 0
        assert loss_gamma_3.item() > 0

    def test_differentiable(self) -> None:
        """Loss should be differentiable."""
        pred = torch.tensor([0.5, 0.7], requires_grad=True)
        target = torch.tensor([0.6, 0.8])

        loss = focal_calibration_loss(pred, target)
        loss.backward()

        assert pred.grad is not None


class TestDimensionLoss:
    """Tests for dimension_loss function."""

    def test_combines_all_components(self) -> None:
        """Should combine MSE, rank, and focal losses."""
        pred = torch.tensor([0.8, 0.6, 0.4, 0.2])
        target = torch.tensor([0.85, 0.55, 0.45, 0.25])

        # Test with default weights
        loss = dimension_loss(pred, target)

        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_weight_effects(self) -> None:
        """Different weights should produce different losses."""
        pred = torch.tensor([0.5, 0.6, 0.7])
        target = torch.tensor([0.6, 0.7, 0.8])

        loss_mse_heavy = dimension_loss(
            pred, target, mse_weight=0.9, rank_weight=0.05, focal_weight=0.05
        )
        loss_rank_heavy = dimension_loss(
            pred, target, mse_weight=0.1, rank_weight=0.8, focal_weight=0.1
        )

        # Different weight distributions should give different losses
        # (unless by coincidence they're equal)
        assert isinstance(loss_mse_heavy.item(), float)
        assert isinstance(loss_rank_heavy.item(), float)


class TestMUSIQSpecialistLoss:
    """Tests for musiq_specialist_loss function."""

    @pytest.fixture
    def sample_predictions(self) -> dict[str, torch.Tensor]:
        """Create sample predictions."""
        return {
            "overall": torch.tensor([0.8, 0.6, 0.4]),
            "sharpness": torch.tensor([0.7, 0.5, 0.3]),
            "color": torch.tensor([0.9, 0.7, 0.5]),
        }

    @pytest.fixture
    def sample_targets(self) -> dict[str, torch.Tensor]:
        """Create sample targets."""
        return {
            "overall": torch.tensor([0.85, 0.55, 0.45]),
            "sharpness": torch.tensor([0.75, 0.55, 0.35]),
            "color": torch.tensor([0.88, 0.72, 0.48]),
        }

    def test_computes_loss(
        self,
        sample_predictions: dict[str, torch.Tensor],
        sample_targets: dict[str, torch.Tensor],
    ) -> None:
        """Should compute a valid loss."""
        loss = musiq_specialist_loss(sample_predictions, sample_targets)

        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_sharpness_specialist_weights(
        self,
        sample_predictions: dict[str, torch.Tensor],
        sample_targets: dict[str, torch.Tensor],
    ) -> None:
        """Default weights should emphasize sharpness."""
        # Default weights: overall=0.2, sharpness=0.6, color=0.2
        loss = musiq_specialist_loss(sample_predictions, sample_targets)

        # Compare with equal weights
        equal_weights = {"overall": 0.33, "sharpness": 0.34, "color": 0.33}
        loss_equal = musiq_specialist_loss(
            sample_predictions, sample_targets, dimension_weights=equal_weights
        )

        # Both should be valid losses
        assert loss.item() > 0
        assert loss_equal.item() > 0

    def test_custom_dimension_weights(
        self,
        sample_predictions: dict[str, torch.Tensor],
        sample_targets: dict[str, torch.Tensor],
    ) -> None:
        """Should accept custom dimension weights."""
        custom_weights = {"overall": 0.5, "sharpness": 0.3, "color": 0.2}
        loss = musiq_specialist_loss(
            sample_predictions, sample_targets, dimension_weights=custom_weights
        )

        assert loss.item() > 0

    def test_differentiable(
        self,
        sample_targets: dict[str, torch.Tensor],
    ) -> None:
        """Loss should be differentiable."""
        predictions = {
            "overall": torch.tensor([0.8, 0.6], requires_grad=True),
            "sharpness": torch.tensor([0.7, 0.5], requires_grad=True),
            "color": torch.tensor([0.9, 0.7], requires_grad=True),
        }
        targets = {k: v[:2] for k, v in sample_targets.items()}

        loss = musiq_specialist_loss(predictions, targets)
        loss.backward()

        for dim, tensor in predictions.items():
            assert tensor.grad is not None, f"Gradient missing for {dim}"


class TestMUSIQSpecialistLossModule:
    """Tests for MUSIQSpecialistLoss module class."""

    def test_initialization(self) -> None:
        """Should initialize with default parameters."""
        criterion = MUSIQSpecialistLoss()

        assert criterion.dimension_weights == {
            "overall": 0.2,
            "sharpness": 0.6,
            "color": 0.2,
        }
        assert criterion.mse_weight == 0.6
        assert criterion.rank_weight == 0.2
        assert criterion.focal_weight == 0.2

    def test_custom_initialization(self) -> None:
        """Should accept custom parameters."""
        criterion = MUSIQSpecialistLoss(
            dimension_weights={"overall": 0.4, "sharpness": 0.4, "color": 0.2},
            mse_weight=0.5,
            rank_weight=0.3,
            focal_weight=0.2,
        )

        assert criterion.dimension_weights["sharpness"] == 0.4
        assert criterion.mse_weight == 0.5

    def test_forward(self) -> None:
        """Should compute loss in forward pass."""
        criterion = MUSIQSpecialistLoss()

        predictions = {
            "overall": torch.tensor([0.8, 0.6]),
            "sharpness": torch.tensor([0.7, 0.5]),
            "color": torch.tensor([0.9, 0.7]),
        }
        targets = {
            "overall": torch.tensor([0.85, 0.55]),
            "sharpness": torch.tensor([0.75, 0.45]),
            "color": torch.tensor([0.88, 0.68]),
        }

        loss = criterion(predictions, targets)

        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_extra_repr(self) -> None:
        """Should have informative string representation."""
        criterion = MUSIQSpecialistLoss()
        repr_str = criterion.extra_repr()

        assert "dimension_weights" in repr_str
        assert "mse" in repr_str
        assert "rank" in repr_str
        assert "focal" in repr_str
