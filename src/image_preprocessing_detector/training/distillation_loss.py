"""Knowledge distillation loss for teacher-student training.

This module implements the knowledge distillation loss function for training
a lightweight student model from a larger teacher model. The loss combines:

1. Soft target loss (KL divergence): Student learns from teacher's soft predictions
2. Hard target loss (BCE): Student learns from ground truth labels

The combined loss is:
    total_loss = alpha * soft_loss + (1 - alpha) * hard_loss

Where:
    - soft_loss: KL divergence between student and teacher logits (temperature-scaled)
    - hard_loss: Binary cross-entropy between student logits and ground truth
    - alpha: Weight parameter (typically 0.7, meaning 70% teacher, 30% ground truth)

Temperature Scaling:
    The temperature parameter (T) is used to soften the probability distributions,
    making the teacher's knowledge more informative. Higher temperature produces
    softer distributions. The KL divergence is scaled by T^2 to correct for the
    softening effect.

References:
    - Hinton et al. (2015): "Distilling the Knowledge in a Neural Network"
    - https://arxiv.org/abs/1503.02531
"""

# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

import torch
import torch.nn as nn

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class DistillationLoss(nn.Module):
    """Knowledge distillation loss for teacher-student training.

    Combines soft targets (teacher logits) and hard targets (ground truth labels)
    using temperature-scaled KL divergence and binary cross-entropy.

    Attributes:
        alpha: Weight for distillation loss (1-alpha for hard label loss)
        temperature: Temperature for softening distributions (default: 4.0)
        reduction: Reduction method for loss ('mean', 'sum', or 'none')
    """

    def __init__(
        self,
        alpha: float = 0.7,
        temperature: float = 4.0,
        reduction: str = "mean",
    ) -> None:
        """Initialize the distillation loss.

        Args:
            alpha: Weight for distillation loss (0.0-1.0). Default: 0.7 (70% teacher)
            temperature: Temperature for softening distributions. Default: 4.0
            reduction: Loss reduction method ('mean', 'sum', 'none'). Default: 'mean'

        Raises:
            ValueError: If alpha not in [0, 1] or temperature <= 0
        """
        super().__init__()

        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"Alpha must be in [0, 1], got {alpha}")
        if temperature <= 0:
            raise ValueError(f"Temperature must be > 0, got {temperature}")
        if reduction not in ("mean", "sum", "none"):
            raise ValueError(
                f"Reduction must be 'mean', 'sum', or 'none', got {reduction}"
            )

        self.alpha = alpha
        self.temperature = temperature
        self.reduction = reduction

        # Hard label loss (binary cross-entropy)
        self.hard_loss_fn = nn.BCEWithLogitsLoss(reduction=reduction)

        logger.info(
            "DistillationLoss initialized",
            alpha=alpha,
            temperature=temperature,
            reduction=reduction,
        )

    def forward(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        labels: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Compute the distillation loss.

        Args:
            student_logits: Student model logits (batch_size, num_classes)
            teacher_logits: Teacher model logits (batch_size, num_classes)
            labels: Ground truth labels (batch_size, num_classes), binary 0/1

        Returns:
            Dictionary containing:
                - 'total': Combined distillation loss
                - 'soft': Soft target loss (KL divergence)
                - 'hard': Hard target loss (BCE)
                - 'alpha': Alpha weight used

        Shape:
            - student_logits: (batch_size, num_classes)
            - teacher_logits: (batch_size, num_classes)
            - labels: (batch_size, num_classes)
            - Output: scalar tensors
        """
        # Validate input shapes
        if student_logits.shape != teacher_logits.shape:
            raise ValueError(
                f"Student and teacher logits must have same shape. "
                f"Got student={student_logits.shape}, teacher={teacher_logits.shape}"
            )
        if student_logits.shape != labels.shape:
            raise ValueError(
                f"Logits and labels must have same shape. "
                f"Got logits={student_logits.shape}, labels={labels.shape}"
            )

        # Soft target loss (KL divergence with temperature scaling)
        soft_loss = self._compute_soft_loss(student_logits, teacher_logits)

        # Hard target loss (binary cross-entropy)
        hard_loss = self.hard_loss_fn(student_logits, labels)

        # Combined loss
        total_loss = self.alpha * soft_loss + (1.0 - self.alpha) * hard_loss

        return {
            "total": total_loss,
            "soft": soft_loss,
            "hard": hard_loss,
            "alpha": torch.tensor(self.alpha, device=total_loss.device),
        }

    def _compute_soft_loss(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
    ) -> torch.Tensor:
        """Compute temperature-scaled KL divergence loss.

        For multi-label classification, we treat each class independently and
        compute KL divergence per class, then average.

        Args:
            student_logits: Student model logits (batch_size, num_classes)
            teacher_logits: Teacher model logits (batch_size, num_classes)

        Returns:
            KL divergence loss (scalar if reduction='mean', otherwise per-sample)
        """
        # Temperature-scaled softmax for binary classification per class
        # For binary classification, we use sigmoid instead of softmax
        # KL divergence for Bernoulli distributions:
        # KL(p||q) = p*log(p/q) + (1-p)*log((1-p)/(1-q))

        # Scale logits by temperature
        student_logits_scaled = student_logits / self.temperature
        teacher_logits_scaled = teacher_logits / self.temperature

        # Convert to probabilities
        student_probs = torch.sigmoid(student_logits_scaled)
        teacher_probs = torch.sigmoid(teacher_logits_scaled)

        # Compute KL divergence for Bernoulli distributions
        # Add epsilon for numerical stability
        eps = 1e-8
        kl_div = teacher_probs * torch.log(
            (teacher_probs + eps) / (student_probs + eps)
        ) + (1.0 - teacher_probs) * torch.log(
            (1.0 - teacher_probs + eps) / (1.0 - student_probs + eps)
        )

        # Scale by temperature squared (as per Hinton et al.)
        kl_div = kl_div * (self.temperature**2)

        # Apply reduction
        if self.reduction == "mean":
            return kl_div.mean()
        if self.reduction == "sum":
            return kl_div.sum()
        # 'none'
        return kl_div

    def __repr__(self) -> str:
        """String representation of the loss."""
        return (
            f"DistillationLoss(alpha={self.alpha}, "
            f"temperature={self.temperature}, "
            f"reduction='{self.reduction}')"
        )


def calculate_distillation_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    labels: torch.Tensor,
    alpha: float = 0.7,
    temperature: float = 4.0,
    reduction: str = "mean",
) -> dict[str, torch.Tensor]:
    """Functional interface for computing distillation loss.

    This is a convenience function that creates a DistillationLoss module
    and computes the loss in one call.

    Args:
        student_logits: Student model logits (batch_size, num_classes)
        teacher_logits: Teacher model logits (batch_size, num_classes)
        labels: Ground truth labels (batch_size, num_classes)
        alpha: Weight for distillation loss (default: 0.7)
        temperature: Temperature for softening (default: 4.0)
        reduction: Reduction method (default: 'mean')

    Returns:
        Dictionary containing 'total', 'soft', 'hard', and 'alpha' losses

    Example:
        >>> student_logits = torch.randn(32, 6)  # batch_size=32, num_classes=6
        >>> teacher_logits = torch.randn(32, 6)
        >>> labels = torch.randint(0, 2, (32, 6)).float()
        >>> loss_dict = calculate_distillation_loss(
        ...     student_logits, teacher_logits, labels
        ... )
        >>> total_loss = loss_dict["total"]
        >>> total_loss.backward()
    """
    loss_module = DistillationLoss(
        alpha=alpha,
        temperature=temperature,
        reduction=reduction,
    )
    result: dict[str, torch.Tensor] = loss_module(
        student_logits, teacher_logits, labels
    )
    return result
