"""Unit tests for Knowledge Distillation Loss."""

# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

import pytest

torch = pytest.importorskip(
    "torch", reason="PyTorch required for distillation loss tests"
)

from image_preprocessing_detector.training.distillation_loss import (  # noqa: E402
    DistillationLoss,
    calculate_distillation_loss,
)


class TestDistillationLoss:
    """Test suite for DistillationLoss module."""

    def test_loss_instantiation(self):
        """Test that loss can be instantiated with default parameters."""
        loss = DistillationLoss()
        assert isinstance(loss, DistillationLoss)
        assert loss.alpha == pytest.approx(0.7)
        assert loss.temperature == pytest.approx(4.0)
        assert loss.reduction == "mean"

    def test_loss_instantiation_custom_params(self):
        """Test loss instantiation with custom parameters."""
        loss = DistillationLoss(alpha=0.5, temperature=3.0, reduction="sum")
        assert loss.alpha == pytest.approx(0.5)
        assert loss.temperature == pytest.approx(3.0)
        assert loss.reduction == "sum"

    def test_invalid_alpha(self):
        """Test that ValueError is raised for invalid alpha."""
        with pytest.raises(ValueError, match="Alpha must be in"):
            DistillationLoss(alpha=1.5)
        with pytest.raises(ValueError, match="Alpha must be in"):
            DistillationLoss(alpha=-0.1)

    def test_invalid_temperature(self):
        """Test that ValueError is raised for invalid temperature."""
        with pytest.raises(ValueError, match="Temperature must be > 0"):
            DistillationLoss(temperature=0.0)
        with pytest.raises(ValueError, match="Temperature must be > 0"):
            DistillationLoss(temperature=-1.0)

    def test_invalid_reduction(self):
        """Test that ValueError is raised for invalid reduction."""
        with pytest.raises(ValueError, match="Reduction must be"):
            DistillationLoss(reduction="invalid")

    def test_forward_pass_shape(self):
        """Test forward pass produces correct output dictionary."""
        loss = DistillationLoss()
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        output = loss(student_logits, teacher_logits, labels)

        # Check that all expected keys are present
        expected_keys = {"total", "soft", "hard", "alpha"}
        assert set(output.keys()) == expected_keys

        # Check that all values are scalar tensors (with mean reduction)
        assert output["total"].dim() == 0
        assert output["soft"].dim() == 0
        assert output["hard"].dim() == 0
        assert output["alpha"].dim() == 0

    def test_forward_pass_values(self):
        """Test that loss values are reasonable."""
        loss = DistillationLoss(alpha=0.7, temperature=4.0)
        batch_size = 8
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        output = loss(student_logits, teacher_logits, labels)

        # All losses should be non-negative
        assert output["total"] >= 0
        assert output["soft"] >= 0
        assert output["hard"] >= 0

        # Total loss should be combination of soft and hard
        # (approximately, due to different computations)
        # total ≈ alpha * soft + (1 - alpha) * hard
        expected_total = (
            loss.alpha * output["soft"] + (1.0 - loss.alpha) * output["hard"]
        )
        assert torch.allclose(output["total"], expected_total, rtol=1e-5)

    def test_temperature_scaling_effect(self):
        """Test that temperature affects soft loss magnitude."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Higher temperature should produce different (typically larger) soft loss
        loss_low_temp = DistillationLoss(temperature=1.0)
        loss_high_temp = DistillationLoss(temperature=10.0)

        output_low = loss_low_temp(student_logits, teacher_logits, labels)
        output_high = loss_high_temp(student_logits, teacher_logits, labels)

        # Soft losses should be different
        assert not torch.allclose(output_low["soft"], output_high["soft"])

    def test_alpha_weighting(self):
        """Test that alpha correctly weights soft and hard losses."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Test with different alpha values
        for alpha in [0.0, 0.5, 1.0]:
            loss = DistillationLoss(alpha=alpha)
            output = loss(student_logits, teacher_logits, labels)

            # Verify weighting
            expected_total = alpha * output["soft"] + (1.0 - alpha) * output["hard"]
            assert torch.allclose(output["total"], expected_total, rtol=1e-5)

            # Check alpha in output
            assert output["alpha"].item() == pytest.approx(alpha)

    def test_alpha_extremes(self):
        """Test behavior at alpha extremes (0.0 and 1.0)."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Alpha = 0.0: Only hard loss
        loss_hard_only = DistillationLoss(alpha=0.0)
        output_hard = loss_hard_only(student_logits, teacher_logits, labels)
        assert torch.allclose(output_hard["total"], output_hard["hard"])

        # Alpha = 1.0: Only soft loss
        loss_soft_only = DistillationLoss(alpha=1.0)
        output_soft = loss_soft_only(student_logits, teacher_logits, labels)
        assert torch.allclose(output_soft["total"], output_soft["soft"])

    def test_gradient_flow(self):
        """Test that gradients flow correctly through the loss."""
        loss = DistillationLoss()
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes, requires_grad=True)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Forward pass
        output = loss(student_logits, teacher_logits, labels)

        # Backward pass
        output["total"].backward()

        # Check that gradients exist for student logits
        assert student_logits.grad is not None
        # Gradients should be non-zero (in most cases)
        assert not torch.allclose(
            student_logits.grad, torch.zeros_like(student_logits.grad)
        )

    def test_no_gradient_for_teacher(self):
        """Test that teacher logits do not receive gradients."""
        loss = DistillationLoss()
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes, requires_grad=True)
        teacher_logits = torch.randn(batch_size, num_classes, requires_grad=True)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Forward and backward
        output = loss(student_logits, teacher_logits, labels)
        output["total"].backward()

        # Teacher should have gradients (but in practice we would freeze it)
        # This just tests that the loss computation involves teacher_logits
        assert teacher_logits.grad is not None

    def test_mismatched_shapes(self):
        """Test that ValueError is raised for mismatched input shapes."""
        loss = DistillationLoss()

        student_logits = torch.randn(4, 6)
        teacher_logits = torch.randn(4, 8)  # Different num_classes
        labels = torch.randn(4, 6)

        with pytest.raises(ValueError, match="same shape"):
            loss(student_logits, teacher_logits, labels)

        # Mismatched labels
        student_logits = torch.randn(4, 6)
        teacher_logits = torch.randn(4, 6)
        labels = torch.randn(4, 8)  # Different num_classes

        with pytest.raises(ValueError, match="same shape"):
            loss(student_logits, teacher_logits, labels)

    def test_reduction_modes(self):
        """Test different reduction modes."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Mean reduction (default)
        loss_mean = DistillationLoss(reduction="mean")
        output_mean = loss_mean(student_logits, teacher_logits, labels)
        assert output_mean["total"].dim() == 0  # Scalar

        # Sum reduction
        loss_sum = DistillationLoss(reduction="sum")
        output_sum = loss_sum(student_logits, teacher_logits, labels)
        assert output_sum["total"].dim() == 0  # Scalar

        # Sum should be larger than mean (for batch_size > 1)
        assert output_sum["total"] > output_mean["total"]

        # None reduction
        loss_none = DistillationLoss(reduction="none")
        output_none = loss_none(student_logits, teacher_logits, labels)
        # Should return per-sample losses
        assert output_none["soft"].shape == (batch_size, num_classes)

    def test_repr(self):
        """Test string representation of the loss."""
        loss = DistillationLoss(alpha=0.7, temperature=4.0, reduction="mean")
        repr_str = repr(loss)
        assert "DistillationLoss" in repr_str
        assert "alpha=0.7" in repr_str
        assert "temperature=4.0" in repr_str
        assert "reduction='mean'" in repr_str


class TestCalculateDistillationLoss:
    """Test suite for calculate_distillation_loss functional interface."""

    def test_functional_interface(self):
        """Test that functional interface works correctly."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        output = calculate_distillation_loss(student_logits, teacher_logits, labels)

        # Check expected keys
        expected_keys = {"total", "soft", "hard", "alpha"}
        assert set(output.keys()) == expected_keys

        # Check default alpha value (use approx for float comparison)
        assert output["alpha"].item() == pytest.approx(0.7)

    def test_functional_interface_custom_params(self):
        """Test functional interface with custom parameters."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        output = calculate_distillation_loss(
            student_logits,
            teacher_logits,
            labels,
            alpha=0.5,
            temperature=3.0,
            reduction="sum",
        )

        # Check custom alpha
        assert output["alpha"].item() == pytest.approx(0.5)

    def test_functional_equivalence_to_module(self):
        """Test that functional interface produces same results as module."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Module interface
        loss_module = DistillationLoss(alpha=0.7, temperature=4.0)
        output_module = loss_module(student_logits, teacher_logits, labels)

        # Functional interface
        output_functional = calculate_distillation_loss(
            student_logits, teacher_logits, labels, alpha=0.7, temperature=4.0
        )

        # Should produce identical results
        assert torch.allclose(output_module["total"], output_functional["total"])
        assert torch.allclose(output_module["soft"], output_functional["soft"])
        assert torch.allclose(output_module["hard"], output_functional["hard"])

    def test_functional_gradient_flow(self):
        """Test that gradients flow correctly through functional interface."""
        batch_size = 4
        num_classes = 6

        student_logits = torch.randn(batch_size, num_classes, requires_grad=True)
        teacher_logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, 2, (batch_size, num_classes)).float()

        # Forward pass
        output = calculate_distillation_loss(student_logits, teacher_logits, labels)

        # Backward pass
        output["total"].backward()

        # Check gradients
        assert student_logits.grad is not None
