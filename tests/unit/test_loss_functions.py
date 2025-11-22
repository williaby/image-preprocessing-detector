"""Unit tests for loss functions.

Tests cover:
- MultiHeadIQALoss with various configurations
- FocalLoss for class imbalance
- WeightedMSELoss for confidence regression
- Class weight computation
- Loss reduction methods
- Per-head loss weighting
"""

import pytest
import torch

from image_preprocessing_detector.models.loss_functions import (
    FocalLoss,
    MultiHeadIQALoss,
    WeightedMSELoss,
    compute_class_weights,
)


class TestMultiHeadIQALoss:
    """Test MultiHeadIQALoss function."""

    def test_loss_initialization(self) -> None:
        """Test loss function initialization."""
        head_names = ["blur", "noise", "skew"]
        loss_fn = MultiHeadIQALoss(
            head_names=head_names,
            classification_weight=1.0,
            confidence_weight=0.5,
        )

        assert loss_fn.head_names == head_names
        assert loss_fn.classification_weight == 1.0
        assert loss_fn.confidence_weight == 0.5
        assert len(loss_fn.head_weights) == 3

    def test_loss_with_custom_head_weights(self) -> None:
        """Test loss with custom per-head weights."""
        head_names = ["blur", "noise", "skew"]
        head_weights = {"blur": 1.5, "noise": 1.0, "skew": 1.5}

        loss_fn = MultiHeadIQALoss(head_names=head_names, head_weights=head_weights)

        assert loss_fn.head_weights == head_weights

    def test_missing_head_weights_raises_error(self) -> None:
        """Test that missing head weights raises error."""
        head_names = ["blur", "noise", "skew"]
        head_weights = {"blur": 1.5, "noise": 1.0}  # Missing 'skew'

        with pytest.raises(ValueError, match="Missing weights for heads"):
            MultiHeadIQALoss(head_names=head_names, head_weights=head_weights)

    def test_forward_pass_basic(self) -> None:
        """Test basic forward pass."""
        head_names = ["blur", "noise"]
        loss_fn = MultiHeadIQALoss(head_names=head_names)

        batch_size = 4

        # Create predictions
        predictions = {
            "blur": {
                "logits": torch.randn(batch_size, 1),
                "confidence": torch.sigmoid(torch.randn(batch_size, 1)),
            },
            "noise": {
                "logits": torch.randn(batch_size, 1),
                "confidence": torch.sigmoid(torch.randn(batch_size, 1)),
            },
        }

        # Create targets
        targets = {
            "blur": {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            },
            "noise": {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            },
        }

        # Compute loss
        loss_dict = loss_fn(predictions, targets)

        # Check output structure
        assert "total_loss" in loss_dict
        assert "classification_loss" in loss_dict
        assert "confidence_loss" in loss_dict
        assert "per_head_loss" in loss_dict

        # Check scalar losses
        assert loss_dict["total_loss"].ndim == 0  # Scalar
        assert loss_dict["classification_loss"].ndim == 0
        assert loss_dict["confidence_loss"].ndim == 0

        # Check per-head losses
        assert "blur" in loss_dict["per_head_loss"]
        assert "noise" in loss_dict["per_head_loss"]

        # Check losses are positive
        assert loss_dict["total_loss"].item() >= 0.0
        assert loss_dict["classification_loss"].item() >= 0.0
        assert loss_dict["confidence_loss"].item() >= 0.0

    def test_forward_pass_all_heads(self) -> None:
        """Test forward pass with all 5 heads."""
        head_names = ["blur", "noise", "skew", "illumination", "artifacts"]
        loss_fn = MultiHeadIQALoss(head_names=head_names)

        batch_size = 8

        # Create predictions and targets for all heads
        predictions = {}
        targets = {}

        for head_name in head_names:
            predictions[head_name] = {
                "logits": torch.randn(batch_size, 1),
                "confidence": torch.sigmoid(torch.randn(batch_size, 1)),
            }
            targets[head_name] = {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            }

        loss_dict = loss_fn(predictions, targets)

        # All heads should be in per_head_loss
        assert len(loss_dict["per_head_loss"]) == 5
        for head_name in head_names:
            assert head_name in loss_dict["per_head_loss"]

    def test_missing_head_in_predictions_raises_error(self) -> None:
        """Test that missing head in predictions raises error."""
        head_names = ["blur", "noise"]
        loss_fn = MultiHeadIQALoss(head_names=head_names)

        batch_size = 4

        # Predictions missing 'noise'
        predictions = {
            "blur": {
                "logits": torch.randn(batch_size, 1),
                "confidence": torch.sigmoid(torch.randn(batch_size, 1)),
            }
        }

        targets = {
            "blur": {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            },
            "noise": {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            },
        }

        with pytest.raises(ValueError, match="not found in predictions"):
            loss_fn(predictions, targets)

    def test_reduction_methods(self) -> None:
        """Test different reduction methods."""
        head_names = ["blur"]
        batch_size = 4

        predictions = {
            "blur": {
                "logits": torch.randn(batch_size, 1),
                "confidence": torch.sigmoid(torch.randn(batch_size, 1)),
            }
        }

        targets = {
            "blur": {
                "labels": torch.randint(0, 2, (batch_size, 1)),
                "confidence": torch.rand(batch_size, 1),
            }
        }

        # Test 'mean' reduction
        loss_fn_mean = MultiHeadIQALoss(head_names=head_names, reduction="mean")
        loss_mean = loss_fn_mean(predictions, targets)
        assert loss_mean["total_loss"].ndim == 0  # Scalar

        # Test 'sum' reduction
        loss_fn_sum = MultiHeadIQALoss(head_names=head_names, reduction="sum")
        loss_sum = loss_fn_sum(predictions, targets)
        assert loss_sum["total_loss"].ndim == 0  # Scalar

        # Sum should be larger than mean
        assert loss_sum["total_loss"].item() > loss_mean["total_loss"].item()

    def test_get_config(self) -> None:
        """Test loss configuration retrieval."""
        head_names = ["blur", "noise"]
        head_weights = {"blur": 1.5, "noise": 1.0}

        loss_fn = MultiHeadIQALoss(
            head_names=head_names,
            classification_weight=1.0,
            confidence_weight=0.5,
            head_weights=head_weights,
        )

        config = loss_fn.get_config()

        assert config["head_names"] == head_names
        assert config["classification_weight"] == 1.0
        assert config["confidence_weight"] == 0.5
        assert config["head_weights"] == head_weights

    def test_loss_gradients(self) -> None:
        """Test that loss computes valid gradients."""
        head_names = ["blur"]
        loss_fn = MultiHeadIQALoss(head_names=head_names)

        batch_size = 4

        # Create predictions with gradient tracking
        logits = torch.randn(batch_size, 1, requires_grad=True)
        confidence_logits = torch.randn(batch_size, 1, requires_grad=True)
        confidence = torch.sigmoid(confidence_logits)

        predictions = {"blur": {"logits": logits, "confidence": confidence}}

        targets = {
            "blur": {
                "labels": torch.randint(0, 2, (batch_size, 1)).float(),
                "confidence": torch.rand(batch_size, 1),
            }
        }

        loss_dict = loss_fn(predictions, targets)
        loss = loss_dict["total_loss"]

        # Backward pass
        loss.backward()

        # Check gradients exist on leaf tensors
        assert logits.grad is not None
        assert confidence_logits.grad is not None


class TestFocalLoss:
    """Test FocalLoss function."""

    def test_focal_loss_initialization(self) -> None:
        """Test focal loss initialization."""
        loss_fn = FocalLoss(alpha=0.25, gamma=2.0)

        assert loss_fn.alpha == 0.25
        assert loss_fn.gamma == 2.0

    def test_focal_loss_forward(self) -> None:
        """Test focal loss forward pass."""
        loss_fn = FocalLoss(alpha=0.25, gamma=2.0, reduction="mean")

        batch_size = 8
        logits = torch.randn(batch_size, 1)
        targets = torch.randint(0, 2, (batch_size, 1)).float()

        loss = loss_fn(logits, targets)

        # Check output is scalar
        assert loss.ndim == 0
        assert loss.item() >= 0.0

    def test_focal_loss_reduction_methods(self) -> None:
        """Test focal loss with different reduction methods."""
        batch_size = 8
        logits = torch.randn(batch_size, 1)
        targets = torch.randint(0, 2, (batch_size, 1)).float()

        # Mean reduction
        loss_mean = FocalLoss(reduction="mean")(logits, targets)
        assert loss_mean.ndim == 0

        # Sum reduction
        loss_sum = FocalLoss(reduction="sum")(logits, targets)
        assert loss_sum.ndim == 0

        # None reduction
        loss_none = FocalLoss(reduction="none")(logits, targets)
        assert loss_none.shape == (batch_size, 1)

    def test_focal_loss_vs_bce(self) -> None:
        """Test that focal loss differs from BCE."""
        batch_size = 8
        logits = torch.randn(batch_size, 1)
        targets = torch.randint(0, 2, (batch_size, 1)).float()

        focal = FocalLoss()(logits, targets)
        bce = torch.nn.functional.binary_cross_entropy_with_logits(
            logits, targets, reduction="mean"
        )

        # Focal loss should be different from BCE
        assert not torch.allclose(focal, bce)


class TestWeightedMSELoss:
    """Test WeightedMSELoss function."""

    def test_weighted_mse_initialization(self) -> None:
        """Test weighted MSE loss initialization."""
        loss_fn = WeightedMSELoss(reduction="mean")
        assert loss_fn.reduction == "mean"

    def test_weighted_mse_forward_no_weights(self) -> None:
        """Test weighted MSE without custom weights."""
        loss_fn = WeightedMSELoss(reduction="mean")

        batch_size = 8
        predictions = torch.rand(batch_size, 1)
        targets = torch.rand(batch_size, 1)

        loss = loss_fn(predictions, targets)

        # Check output is scalar
        assert loss.ndim == 0
        assert loss.item() >= 0.0

    def test_weighted_mse_with_weights(self) -> None:
        """Test weighted MSE with custom weight function."""

        def weight_fn(targets: torch.Tensor) -> torch.Tensor:
            # Higher weight for high confidence targets
            return targets * 2.0 + 0.5

        loss_fn = WeightedMSELoss(weight_fn=weight_fn, reduction="mean")

        batch_size = 8
        predictions = torch.rand(batch_size, 1)
        targets = torch.rand(batch_size, 1)

        loss_weighted = loss_fn(predictions, targets)

        # Compare with unweighted
        loss_unweighted = WeightedMSELoss()(predictions, targets)

        # Weighted should be different
        assert not torch.allclose(loss_weighted, loss_unweighted)

    def test_weighted_mse_reduction_methods(self) -> None:
        """Test weighted MSE with different reduction methods."""
        batch_size = 8
        predictions = torch.rand(batch_size, 1)
        targets = torch.rand(batch_size, 1)

        # Mean reduction
        loss_mean = WeightedMSELoss(reduction="mean")(predictions, targets)
        assert loss_mean.ndim == 0

        # Sum reduction
        loss_sum = WeightedMSELoss(reduction="sum")(predictions, targets)
        assert loss_sum.ndim == 0

        # None reduction
        loss_none = WeightedMSELoss(reduction="none")(predictions, targets)
        assert loss_none.shape == (batch_size, 1)


class TestComputeClassWeights:
    """Test compute_class_weights utility function."""

    def test_balanced_classes(self) -> None:
        """Test class weights for balanced dataset."""
        labels = {
            "blur": torch.tensor([0, 1, 0, 1, 0, 1, 0, 1]),  # Balanced
            "noise": torch.tensor([0, 0, 1, 1, 0, 0, 1, 1]),  # Balanced
        }

        weights = compute_class_weights(labels)

        # Balanced classes should have weight ~1.0
        assert "blur" in weights
        assert "noise" in weights

        # Weights should be close to 1.0 for balanced classes
        assert torch.allclose(weights["blur"], torch.ones(2), atol=0.1)

    def test_imbalanced_classes(self) -> None:
        """Test class weights for imbalanced dataset."""
        labels = {
            "blur": torch.tensor([0, 0, 0, 0, 0, 0, 0, 1]),  # 7:1 imbalance
        }

        weights = compute_class_weights(labels, num_classes=2)

        assert "blur" in weights
        assert len(weights["blur"]) == 2

        # Class 1 (minority) should have higher weight
        assert weights["blur"][1] > weights["blur"][0]

    def test_multiple_heads(self) -> None:
        """Test class weights for multiple heads."""
        labels = {
            "blur": torch.tensor([0, 1, 0, 1]),
            "noise": torch.tensor([0, 0, 0, 1]),
            "skew": torch.tensor([1, 1, 1, 1]),
        }

        weights = compute_class_weights(labels)

        assert len(weights) == 3
        assert "blur" in weights
        assert "noise" in weights
        assert "skew" in weights

        # Each head should have weights for 2 classes
        for head_weights in weights.values():
            assert len(head_weights) == 2

    def test_weights_are_positive(self) -> None:
        """Test that all weights are positive."""
        labels = {
            "blur": torch.randint(0, 2, (100,)),
            "noise": torch.randint(0, 2, (100,)),
        }

        weights = compute_class_weights(labels)

        for head_weights in weights.values():
            assert torch.all(head_weights > 0.0)
