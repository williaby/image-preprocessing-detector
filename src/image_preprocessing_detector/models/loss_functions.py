"""Loss functions for multi-head IQA model training.

This module implements specialized loss functions for training the teacher model:
- Binary cross-entropy for issue presence/absence classification
- Mean squared error for confidence score regression
- Weighted combination of multiple loss components
- Per-head weighting to prioritize critical quality issues

The loss functions support multi-head architectures where each head predicts
both a binary classification (issue present/absent) and a confidence score.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812


class MultiHeadIQALoss(nn.Module):
    """Combined loss function for multi-head IQA model.

    This loss function combines:
    1. Binary Cross-Entropy (BCE) for classification (issue present/absent)
    2. Mean Squared Error (MSE) for confidence score regression

    The loss is computed per-head and then aggregated with configurable weights
    to prioritize more critical quality issues (e.g., blur, skew).

    Args:
        head_names: List of head names (e.g., ["blur", "noise", "skew", ...])
        classification_weight: Weight for classification loss (default: 1.0)
        confidence_weight: Weight for confidence regression loss (default: 0.5)
        head_weights: Optional per-head weights (default: equal weights)
        reduction: Reduction method: 'mean', 'sum', or 'none' (default: 'mean')

    Example:
        >>> loss_fn = MultiHeadIQALoss(
        ...     head_names=["blur", "noise", "skew"],
        ...     head_weights={"blur": 1.5, "noise": 1.0, "skew": 1.5},
        ... )
        >>> predictions = model(images)
        >>> loss = loss_fn(predictions, targets)
    """

    def __init__(
        self,
        head_names: list[str],
        classification_weight: float = 1.0,
        confidence_weight: float = 0.5,
        head_weights: dict[str, float] | None = None,
        reduction: str = "mean",
    ) -> None:
        super().__init__()

        self.head_names = head_names
        self.classification_weight = classification_weight
        self.confidence_weight = confidence_weight
        self.reduction = reduction

        # Set default head weights (equal for all heads)
        if head_weights is None:
            self.head_weights = dict.fromkeys(head_names, 1.0)
        else:
            # Validate that all heads have weights
            missing_heads = set(head_names) - set(head_weights.keys())
            if missing_heads:
                raise ValueError(
                    f"Missing weights for heads: {missing_heads}. "
                    f"Provide weights for all heads: {head_names}"
                )
            self.head_weights = head_weights

        # Loss functions
        self.bce_loss = nn.BCEWithLogitsLoss(reduction="none")
        self.mse_loss = nn.MSELoss(reduction="none")

    def forward(
        self,
        predictions: dict[str, dict[str, torch.Tensor]],
        targets: dict[str, dict[str, torch.Tensor]],
    ) -> dict[str, torch.Tensor | dict[str, torch.Tensor]]:
        """Compute the combined multi-head loss.

        Args:
            predictions: Model predictions, dict mapping head names to:
                {
                    "logits": tensor of shape (batch_size, 1),
                    "confidence": tensor of shape (batch_size, 1)
                }
            targets: Ground truth labels, dict mapping head names to:
                {
                    "labels": binary tensor of shape (batch_size, 1),
                    "confidence": tensor of shape (batch_size, 1)
                }

        Returns:
            Dictionary containing:
                - total_loss: Combined weighted loss
                - classification_loss: Total classification loss
                - confidence_loss: Total confidence regression loss
                - per_head_loss: Loss for each head
        """
        # Get device from first prediction tensor to ensure all tensors on same device
        first_head = self.head_names[0]
        device = predictions[first_head]["logits"].device

        total_classification_loss = torch.tensor(0.0, device=device)
        total_confidence_loss = torch.tensor(0.0, device=device)
        per_head_losses: dict[str, torch.Tensor] = {}

        # Compute loss for each head
        for head_name in self.head_names:
            if head_name not in predictions:
                raise ValueError(
                    f"Head '{head_name}' not found in predictions. "
                    f"Available heads: {list(predictions.keys())}"
                )
            if head_name not in targets:
                raise ValueError(
                    f"Head '{head_name}' not found in targets. "
                    f"Available heads: {list(targets.keys())}"
                )

            # Get predictions and targets for this head
            pred = predictions[head_name]
            target = targets[head_name]

            # Classification loss (BCE on logits)
            # Squeeze logits and labels from [batch, 1] to [batch]
            logits = pred["logits"].squeeze(-1)
            labels = target["labels"].float().squeeze(-1)
            cls_loss = self.bce_loss(logits, labels)

            # Confidence regression loss (MSE on confidence scores)
            # Squeeze confidence from [batch, 1] to [batch] to match target shape
            pred_confidence = pred["confidence"].squeeze(-1)
            target_confidence = target["confidence"].float().squeeze(-1)
            conf_loss = self.mse_loss(pred_confidence, target_confidence)

            # Apply reduction
            if self.reduction == "mean":
                cls_loss = cls_loss.mean()
                conf_loss = conf_loss.mean()
            elif self.reduction == "sum":
                cls_loss = cls_loss.sum()
                conf_loss = conf_loss.sum()

            # Weight by head importance
            head_weight = self.head_weights[head_name]

            # Combine classification and confidence losses
            head_loss = (
                self.classification_weight * cls_loss
                + self.confidence_weight * conf_loss
            ) * head_weight

            per_head_losses[head_name] = head_loss

            # Accumulate total losses
            total_classification_loss += cls_loss * head_weight
            total_confidence_loss += conf_loss * head_weight

        # Compute total loss
        total_loss = (
            self.classification_weight * total_classification_loss
            + self.confidence_weight * total_confidence_loss
        )

        # Normalize by number of heads
        num_heads = len(self.head_names)
        total_loss = total_loss / num_heads
        total_classification_loss = total_classification_loss / num_heads
        total_confidence_loss = total_confidence_loss / num_heads

        return {
            "total_loss": total_loss,
            "classification_loss": total_classification_loss,
            "confidence_loss": total_confidence_loss,
            "per_head_loss": per_head_losses,
        }

    def get_config(self) -> dict[str, Any]:
        """Get loss function configuration.

        Returns:
            Dictionary containing configuration parameters
        """
        return {
            "head_names": self.head_names,
            "classification_weight": self.classification_weight,
            "confidence_weight": self.confidence_weight,
            "head_weights": self.head_weights,
            "reduction": self.reduction,
        }


class FocalLoss(nn.Module):
    """Focal Loss for handling class imbalance.

    Focal Loss down-weights easy examples and focuses training on hard negatives.
    This is useful when certain quality issues are rare in the training data.

    Args:
        alpha: Weighting factor for positive class (default: 0.25)
        gamma: Focusing parameter (default: 2.0)
        reduction: Reduction method: 'mean', 'sum', or 'none' (default: 'mean')

    Reference:
        Lin et al. "Focal Loss for Dense Object Detection" (ICCV 2017)
    """

    def __init__(
        self, alpha: float = 0.25, gamma: float = 2.0, reduction: str = "mean"
    ) -> None:
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute focal loss.

        Args:
            logits: Predicted logits of shape (batch_size, 1)
            targets: Binary labels of shape (batch_size, 1)

        Returns:
            Focal loss value
        """
        # Convert logits to probabilities
        probs = torch.sigmoid(logits)

        # Compute binary cross-entropy
        bce_loss = F.binary_cross_entropy_with_logits(
            logits, targets.float(), reduction="none"
        )

        # Compute focal term: (1 - p_t)^gamma
        p_t = probs * targets + (1 - probs) * (1 - targets)
        focal_term = (1 - p_t) ** self.gamma

        # Compute alpha term
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)

        # Focal loss
        focal_loss = alpha_t * focal_term * bce_loss

        # Apply reduction
        if self.reduction == "mean":
            return focal_loss.mean()
        if self.reduction == "sum":
            return focal_loss.sum()
        return focal_loss


class WeightedMSELoss(nn.Module):
    """Weighted MSE Loss for confidence score regression.

    This loss function allows different weights for different confidence ranges,
    prioritizing accurate predictions for high-confidence cases.

    Args:
        weight_fn: Optional function that maps confidence values to weights
        reduction: Reduction method: 'mean', 'sum', or 'none' (default: 'mean')
    """

    def __init__(
        self,
        weight_fn: Callable[[torch.Tensor], torch.Tensor] | None = None,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        self.weight_fn = weight_fn
        self.reduction = reduction

    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute weighted MSE loss.

        Args:
            predictions: Predicted confidence scores of shape (batch_size, 1)
            targets: Target confidence scores of shape (batch_size, 1)

        Returns:
            Weighted MSE loss value
        """
        # Compute MSE
        mse = (predictions - targets) ** 2

        # Apply weights if provided
        if self.weight_fn is not None:
            weights = self.weight_fn(targets)
            mse = mse * weights

        # Apply reduction
        if self.reduction == "mean":
            return mse.mean()
        if self.reduction == "sum":
            return mse.sum()
        return mse


def compute_class_weights(
    labels: dict[str, torch.Tensor], num_classes: int = 2
) -> dict[str, torch.Tensor]:
    """Compute class weights for handling imbalanced datasets.

    Args:
        labels: Dictionary mapping head names to binary labels
        num_classes: Number of classes (default: 2 for binary)

    Returns:
        Dictionary mapping head names to class weights
    """
    class_weights = {}

    for head_name, head_labels in labels.items():
        # Count occurrences of each class
        unique, counts = torch.unique(head_labels, return_counts=True)

        # Compute inverse frequency weights
        total = counts.sum()
        weights = total / (num_classes * counts.float())

        # Create weight tensor indexed by class
        weight_tensor = torch.ones(num_classes)
        for class_idx, weight in zip(unique, weights, strict=False):
            weight_tensor[int(class_idx)] = weight

        class_weights[head_name] = weight_tensor

    return class_weights


class DistillationLoss(nn.Module):
    """Knowledge Distillation Loss for training student model from teacher.

    This loss function combines:
    1. Soft-target loss (KL Divergence): Student learns from teacher's soft predictions
    2. Hard-target loss (BCE): Student learns from ground truth labels
    3. Confidence distillation (MSE): Student mimics teacher's confidence scores

    The temperature parameter controls how much to soften the teacher's predictions.
    Higher temperature = softer distributions = more knowledge transfer from
    teacher's "dark knowledge" about class similarities.

    Args:
        head_names: List of head names (e.g., ["blur", "noise", "skew", ...])
        temperature: Softening temperature for KL divergence (default: 3.0)
        alpha: Weight for soft targets vs hard targets (default: 0.7)
               alpha=0.7 means 70% soft (teacher) + 30% hard (ground truth)
        confidence_weight: Weight for confidence distillation loss (default: 0.3)
        head_weights: Optional per-head weights (default: equal weights)

    Example:
        >>> teacher_model.eval()  # Freeze teacher
        >>> distill_loss = DistillationLoss(
        ...     head_names=["blur", "noise", "skew", "illumination", "artifacts"],
        ...     temperature=4.0,
        ...     alpha=0.7,
        ... )
        >>> with torch.no_grad():
        ...     teacher_preds = teacher_model(images)
        >>> student_preds = student_model(images)
        >>> loss = distill_loss(student_preds, teacher_preds, targets)

    Reference:
        Hinton et al. "Distilling the Knowledge in a Neural Network" (2015)
    """

    def __init__(
        self,
        head_names: list[str],
        temperature: float = 3.0,
        alpha: float = 0.7,
        confidence_weight: float = 0.3,
        head_weights: dict[str, float] | None = None,
    ) -> None:
        super().__init__()

        self.head_names = head_names
        self.temperature = temperature
        self.alpha = alpha
        self.confidence_weight = confidence_weight

        # Validate alpha
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be between 0 and 1, got {alpha}")

        # Set default head weights (equal for all heads)
        if head_weights is None:
            self.head_weights = dict.fromkeys(head_names, 1.0)
        else:
            missing_heads = set(head_names) - set(head_weights.keys())
            if missing_heads:
                raise ValueError(
                    f"Missing weights for heads: {missing_heads}. "
                    f"Provide weights for all heads: {head_names}"
                )
            self.head_weights = head_weights

        # Loss functions
        self.kl_loss = nn.KLDivLoss(reduction="batchmean")
        self.bce_loss = nn.BCEWithLogitsLoss(reduction="mean")
        self.mse_loss = nn.MSELoss(reduction="mean")

    def _compute_soft_targets_loss(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
    ) -> torch.Tensor:
        """Compute KL divergence loss between soft predictions.

        For binary classification, we create a 2-class distribution from logits:
        [P(negative), P(positive)] and compute KL divergence.

        Args:
            student_logits: Student model logits (batch_size,)
            teacher_logits: Teacher model logits (batch_size,)

        Returns:
            KL divergence loss scaled by T^2
        """
        temp = self.temperature

        # Convert binary logits to 2-class log-probabilities for student
        # P(pos) = sigmoid(logit), P(neg) = 1 - sigmoid(logit)
        student_pos = torch.sigmoid(student_logits / temp)
        student_neg = 1 - student_pos
        student_soft = torch.log(torch.stack([student_neg, student_pos], dim=-1) + 1e-8)

        # Convert binary logits to 2-class probabilities for teacher
        teacher_pos = torch.sigmoid(teacher_logits / temp)
        teacher_neg = 1 - teacher_pos
        teacher_soft = torch.stack([teacher_neg, teacher_pos], dim=-1)

        # KL divergence: KL(teacher || student)
        # Note: KLDivLoss expects log-probs for input, probs for target
        kl_loss = self.kl_loss(student_soft, teacher_soft)

        # Scale by T^2 as per Hinton et al.
        scaled_loss: torch.Tensor = kl_loss * (temp * temp)
        return scaled_loss

    def forward(
        self,
        student_predictions: dict[str, dict[str, torch.Tensor]],
        teacher_predictions: dict[str, dict[str, torch.Tensor]],
        targets: dict[str, dict[str, torch.Tensor]],
    ) -> dict[str, Any]:
        """Compute the combined distillation loss.

        Args:
            student_predictions: Student model predictions, dict mapping head names to:
                {
                    "logits": tensor of shape (batch_size, 1),
                    "confidence": tensor of shape (batch_size, 1)
                }
            teacher_predictions: Teacher model predictions (same structure)
            targets: Ground truth labels, dict mapping head names to:
                {
                    "labels": binary tensor of shape (batch_size,),
                    "confidence": tensor of shape (batch_size,)
                }

        Returns:
            Dictionary containing:
                - total_loss: Combined weighted loss
                - soft_loss: Total KL divergence loss (teacher → student)
                - hard_loss: Total BCE loss (ground truth → student)
                - confidence_loss: Total confidence MSE loss
                - per_head_loss: Loss breakdown for each head
        """
        # Get device from first prediction tensor
        first_head = self.head_names[0]
        device = student_predictions[first_head]["logits"].device

        total_soft_loss = torch.tensor(0.0, device=device)
        total_hard_loss = torch.tensor(0.0, device=device)
        total_conf_loss = torch.tensor(0.0, device=device)
        per_head_losses: dict[str, dict[str, torch.Tensor]] = {}

        for head_name in self.head_names:
            # Validate inputs
            if head_name not in student_predictions:
                raise ValueError(f"Head '{head_name}' not in student predictions")
            if head_name not in teacher_predictions:
                raise ValueError(f"Head '{head_name}' not in teacher predictions")
            if head_name not in targets:
                raise ValueError(f"Head '{head_name}' not in targets")

            # Get predictions and targets
            student_pred = student_predictions[head_name]
            teacher_pred = teacher_predictions[head_name]
            target = targets[head_name]

            # Extract tensors and squeeze to consistent shape
            student_logits = student_pred["logits"].squeeze(-1)
            teacher_logits = teacher_pred["logits"].squeeze(-1)
            student_conf = student_pred["confidence"].squeeze(-1)
            teacher_conf = teacher_pred["confidence"].squeeze(-1)
            labels = target["labels"].float()

            # 1. Soft-target loss (KL Divergence from teacher)
            soft_loss = self._compute_soft_targets_loss(student_logits, teacher_logits)

            # 2. Hard-target loss (BCE from ground truth)
            hard_loss = self.bce_loss(student_logits, labels)

            # 3. Confidence distillation (MSE from teacher's confidence)
            conf_loss = self.mse_loss(student_conf, teacher_conf)

            # Apply head weight
            head_weight = self.head_weights[head_name]

            # Store per-head losses
            per_head_losses[head_name] = {
                "soft_loss": soft_loss * head_weight,
                "hard_loss": hard_loss * head_weight,
                "confidence_loss": conf_loss * head_weight,
            }

            # Accumulate weighted losses
            total_soft_loss += soft_loss * head_weight
            total_hard_loss += hard_loss * head_weight
            total_conf_loss += conf_loss * head_weight

        # Normalize by number of heads
        num_heads = len(self.head_names)
        total_soft_loss = total_soft_loss / num_heads
        total_hard_loss = total_hard_loss / num_heads
        total_conf_loss = total_conf_loss / num_heads

        # Combine losses:
        # - alpha * soft_loss: Learn from teacher's soft predictions
        # - (1 - alpha) * hard_loss: Learn from ground truth labels
        # - confidence_weight * conf_loss: Mimic teacher's confidence
        classification_loss = (
            self.alpha * total_soft_loss + (1 - self.alpha) * total_hard_loss
        )
        total_loss = classification_loss + self.confidence_weight * total_conf_loss

        return {
            "total_loss": total_loss,
            "soft_loss": total_soft_loss,
            "hard_loss": total_hard_loss,
            "confidence_loss": total_conf_loss,
            "classification_loss": classification_loss,
            "per_head_loss": per_head_losses,
        }

    def get_config(self) -> dict[str, Any]:
        """Get loss function configuration.

        Returns:
            Dictionary containing configuration parameters
        """
        return {
            "head_names": self.head_names,
            "temperature": self.temperature,
            "alpha": self.alpha,
            "confidence_weight": self.confidence_weight,
            "head_weights": self.head_weights,
        }
