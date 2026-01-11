# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Loss functions for MUSIQ multi-task fine-tuning.

This module implements the loss functions for DIQA fine-tuning as specified
in DIQA-5000_Pseudo_Labels_v2.md Section 4.3:

Loss = 0.6 * MSE + 0.2 * RankLoss + 0.2 * FocalCalibrationLoss

Components:
- MSE: Standard mean squared error for point prediction
- RankLoss: Differentiable ranking loss for SRCC optimization
- FocalCalibrationLoss: Focal loss variant for ECE improvement

Reference: docs/planning/MUSIQ_FINETUNING_PLAN.md Section 3.2
"""

from __future__ import annotations

import torch
import torch.nn.functional as functional
from torch import Tensor


def differentiable_rank_loss(
    pred: Tensor,
    target: Tensor,
    margin: float = 0.1,
) -> Tensor:
    """Pairwise ranking loss for SRCC optimization.

    This loss encourages the model to preserve the relative ordering
    of quality scores, which directly optimizes for Spearman's rank
    correlation coefficient (SRCC).

    Args:
        pred: Predicted scores of shape [batch].
        target: Target scores of shape [batch].
        margin: Margin for ranking loss.

    Returns:
        Scalar rank loss tensor.

    Example:
        >>> pred = torch.tensor([0.8, 0.6, 0.4])
        >>> target = torch.tensor([0.9, 0.5, 0.3])
        >>> loss = differentiable_rank_loss(pred, target)
    """
    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, dtype=pred.dtype)

    # Create pairwise differences: pred_diff[i,j] = pred[i] - pred[j]
    pred_diff = pred.unsqueeze(1) - pred.unsqueeze(0)
    target_diff = target.unsqueeze(1) - target.unsqueeze(0)

    # Soft ranking: use tanh as smooth approximation of sign function
    # Scale factor of 10 makes it sharper but still differentiable
    target_sign = torch.tanh(target_diff * 10)
    pred_sign = torch.tanh(pred_diff * 10)

    # Margin ranking loss: penalize when pred order doesn't match target order
    # If target_sign and pred_sign have same sign, product is positive -> loss is small
    # If opposite signs, product is negative -> loss is large
    loss = functional.relu(margin - target_sign * pred_sign)

    # Mask out diagonal (comparing element with itself)
    batch_size = pred.size(0)
    mask = 1 - torch.eye(batch_size, device=pred.device, dtype=pred.dtype)

    # Return mean over all valid pairs
    return (loss * mask).sum() / mask.sum().clamp(min=1)


def focal_calibration_loss(
    pred: Tensor,
    target: Tensor,
    gamma: float = 2.0,
) -> Tensor:
    """Focal loss variant for calibration.

    This loss gives higher weight to harder examples (larger errors),
    which helps reduce Expected Calibration Error (ECE) by focusing
    learning on poorly calibrated predictions.

    Args:
        pred: Predicted scores of shape [batch] in [0, 1].
        target: Target scores of shape [batch] in [0, 1].
        gamma: Focal loss gamma parameter (higher = more focus on hard examples).

    Returns:
        Scalar focal calibration loss tensor.

    Example:
        >>> pred = torch.tensor([0.8, 0.3, 0.5])
        >>> target = torch.tensor([0.9, 0.2, 0.7])
        >>> loss = focal_calibration_loss(pred, target, gamma=2.0)
    """
    # Compute absolute error
    error = (pred - target).abs()

    # Confidence = 1 - error (higher confidence for smaller errors)
    # Clamp to avoid numerical issues
    confidence = (1.0 - error).clamp(min=0.0, max=1.0)

    # Focal weighting: (1 - confidence)^gamma
    # Hard examples (low confidence) get higher weight
    focal_weight = (1 - confidence) ** gamma

    # Weighted squared error
    return (focal_weight * error**2).mean()


def dimension_loss(
    pred: Tensor,
    target: Tensor,
    mse_weight: float = 0.6,
    rank_weight: float = 0.2,
    focal_weight: float = 0.2,
    rank_margin: float = 0.1,
    focal_gamma: float = 2.0,
) -> Tensor:
    """Combined loss for a single quality dimension.

    Combines MSE, rank loss, and focal calibration loss with
    configurable weights as specified in Section 4.3.

    Args:
        pred: Predicted scores of shape [batch].
        target: Target scores of shape [batch].
        mse_weight: Weight for MSE component (default 0.6).
        rank_weight: Weight for rank loss component (default 0.2).
        focal_weight: Weight for focal calibration component (default 0.2).
        rank_margin: Margin for rank loss.
        focal_gamma: Gamma for focal loss.

    Returns:
        Scalar combined loss tensor.
    """
    # MSE component
    mse = functional.mse_loss(pred, target)

    # Rank loss component (for SRCC)
    rank = differentiable_rank_loss(pred, target, margin=rank_margin)

    # Focal calibration component (for ECE)
    focal = focal_calibration_loss(pred, target, gamma=focal_gamma)

    return mse_weight * mse + rank_weight * rank + focal_weight * focal


def musiq_specialist_loss(
    predictions: dict[str, Tensor],
    targets: dict[str, Tensor],
    dimension_weights: dict[str, float] | None = None,
    mse_weight: float = 0.6,
    rank_weight: float = 0.2,
    focal_weight: float = 0.2,
) -> Tensor:
    """Weighted multi-task loss for sharpness specialist.

    Computes combined loss across all three DIQA dimensions with
    specialist weighting that emphasizes sharpness.

    Default weights for sharpness specialist (Section 4.4A1):
    - Overall: 0.2 (secondary)
    - Sharpness: 0.6 (PRIMARY)
    - Color: 0.2 (secondary)

    Args:
        predictions: Dictionary with keys 'overall', 'sharpness', 'color',
            each containing predicted scores of shape [batch].
        targets: Dictionary with same structure containing target scores.
        dimension_weights: Weights for each dimension. If None, uses
            sharpness specialist defaults.
        mse_weight: Weight for MSE in dimension loss.
        rank_weight: Weight for rank loss in dimension loss.
        focal_weight: Weight for focal loss in dimension loss.

    Returns:
        Scalar total loss tensor.

    Example:
        >>> predictions = {
        ...     "overall": torch.tensor([0.8, 0.6]),
        ...     "sharpness": torch.tensor([0.7, 0.5]),
        ...     "color": torch.tensor([0.9, 0.4]),
        ... }
        >>> targets = {
        ...     "overall": torch.tensor([0.85, 0.55]),
        ...     "sharpness": torch.tensor([0.75, 0.45]),
        ...     "color": torch.tensor([0.88, 0.42]),
        ... }
        >>> loss = musiq_specialist_loss(predictions, targets)
    """
    # Default sharpness specialist weights
    if dimension_weights is None:
        dimension_weights = {
            "overall": 0.2,
            "sharpness": 0.6,
            "color": 0.2,
        }

    total_loss = torch.tensor(0.0, device=next(iter(predictions.values())).device)

    for dim in ["overall", "sharpness", "color"]:
        pred = predictions[dim]
        target = targets[dim]

        # Compute combined dimension loss
        dim_loss = dimension_loss(
            pred,
            target,
            mse_weight=mse_weight,
            rank_weight=rank_weight,
            focal_weight=focal_weight,
        )

        # Apply specialist weighting
        total_loss = total_loss + dimension_weights[dim] * dim_loss

    return total_loss


class MUSIQSpecialistLoss(torch.nn.Module):
    """Module wrapper for MUSIQ specialist loss.

    This class wraps the loss function for use in training loops
    and provides a consistent interface.

    Attributes:
        dimension_weights: Weights for each quality dimension.
        mse_weight: Weight for MSE component.
        rank_weight: Weight for rank loss component.
        focal_weight: Weight for focal calibration component.

    Example:
        >>> criterion = MUSIQSpecialistLoss(
        ...     dimension_weights={"overall": 0.2, "sharpness": 0.6, "color": 0.2}
        ... )
        >>> loss = criterion(predictions, targets)
    """

    def __init__(
        self,
        dimension_weights: dict[str, float] | None = None,
        mse_weight: float = 0.6,
        rank_weight: float = 0.2,
        focal_weight: float = 0.2,
    ) -> None:
        """Initialize loss module.

        Args:
            dimension_weights: Weights for each dimension.
            mse_weight: Weight for MSE component.
            rank_weight: Weight for rank loss component.
            focal_weight: Weight for focal calibration component.
        """
        super().__init__()

        # Store weights as buffers (not parameters)
        if dimension_weights is None:
            dimension_weights = {"overall": 0.2, "sharpness": 0.6, "color": 0.2}

        self.dimension_weights = dimension_weights
        self.mse_weight = mse_weight
        self.rank_weight = rank_weight
        self.focal_weight = focal_weight

    def forward(
        self,
        predictions: dict[str, Tensor],
        targets: dict[str, Tensor],
    ) -> Tensor:
        """Compute loss.

        Args:
            predictions: Dictionary of predicted scores.
            targets: Dictionary of target scores.

        Returns:
            Scalar loss tensor.
        """
        return musiq_specialist_loss(
            predictions,
            targets,
            dimension_weights=self.dimension_weights,
            mse_weight=self.mse_weight,
            rank_weight=self.rank_weight,
            focal_weight=self.focal_weight,
        )

    def extra_repr(self) -> str:
        """String representation of loss configuration."""
        return (
            f"dimension_weights={self.dimension_weights}, "
            f"mse={self.mse_weight}, rank={self.rank_weight}, focal={self.focal_weight}"
        )
