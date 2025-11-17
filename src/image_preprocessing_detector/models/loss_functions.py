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
        total_classification_loss = torch.tensor(0.0)
        total_confidence_loss = torch.tensor(0.0)
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
            logits = pred["logits"]
            labels = target["labels"].float()
            cls_loss = self.bce_loss(logits, labels)

            # Confidence regression loss (MSE on confidence scores)
            pred_confidence = pred["confidence"]
            target_confidence = target["confidence"].float()
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
