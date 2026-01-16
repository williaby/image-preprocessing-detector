# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Loss functions for HyperIQA++ training.

Implements:
- NormInNormLoss for 10x faster convergence
- KL Divergence for distribution matching
- Multi-task loss with PCGrad support
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812  # PyTorch convention

if TYPE_CHECKING:
    from torch import Tensor


class NormInNormLoss(nn.Module):
    """Norm-in-Norm loss for 10x faster convergence than MSE.

    Reference: Li et al., "Norm-in-Norm Loss with Faster Convergence
    and Better Performance for Image Quality Assessment", ACM MM 2020
    (arXiv:2008.03889)

    Key Insight:
        By normalizing predictions and targets to zero-mean, unit-variance,
        the loss directly optimizes for correlation (PLCC/SRCC) rather than
        absolute error. This leads to 10x faster convergence.

    Formula:
        L = ||normalize(pred) - normalize(target)||_p^q

    Optimal hyperparameters: p=1, q=2 (from paper experiments)
    """

    def __init__(self, p: float = 1.0, q: float = 2.0) -> None:
        """Initialize NormInNorm loss.

        Args:
            p: Inner norm power (default 1.0)
            q: Outer norm power (default 2.0)
        """
        super().__init__()
        self.p = p
        self.q = q

    def forward(self, pred: Tensor, target: Tensor) -> Tensor:
        """Compute NormInNorm loss.

        Args:
            pred: Predicted scores [B]
            target: Ground truth scores [B]

        Returns:
            NormInNorm loss (scalar)
        """
        # Zero-mean, unit-variance normalization
        pred_norm = self._normalize(pred)
        target_norm = self._normalize(target)

        # L_p^q loss
        diff = torch.abs(pred_norm - target_norm)
        return torch.pow(torch.pow(diff, self.p).mean(), self.q / self.p)

    def _normalize(self, x: Tensor) -> Tensor:
        """Normalize to zero-mean, unit-variance.

        Args:
            x: Input tensor [B]

        Returns:
            Normalized tensor [B]
        """
        return (x - x.mean()) / (x.std() + 1e-8)


class MultiTaskIQALoss(nn.Module):
    """Combined loss for multi-dimension IQA training.

    Combines:
        1. KL divergence for distribution matching (soft labels)
        2. NormInNorm for score prediction (correlation optimization)

    Supports PCGrad by returning per-dimension losses when requested.
    """

    def __init__(
        self,
        kl_weight: float = 0.5,
        norm_weight: float = 0.5,
        use_norm_in_norm: bool = True,
    ) -> None:
        """Initialize multi-task loss.

        Args:
            kl_weight: Weight for KL divergence loss
            norm_weight: Weight for NormInNorm/MSE loss
            use_norm_in_norm: If True, use NormInNorm; else use MSE
        """
        super().__init__()
        self.kl_weight = kl_weight
        self.norm_weight = norm_weight
        self.use_norm_in_norm = use_norm_in_norm

        self.kl_criterion = nn.KLDivLoss(reduction="batchmean")
        self.score_criterion: nn.Module  # Can be NormInNormLoss or MSELoss
        if use_norm_in_norm:
            self.score_criterion = NormInNormLoss(p=1.0, q=2.0)
        else:
            self.score_criterion = nn.MSELoss()

    def forward(
        self,
        predictions: dict[str, dict[str, Tensor]],
        targets: dict[str, dict[str, Tensor]],
        return_per_dim: bool = False,
    ) -> dict[str, Tensor] | list[Tensor]:
        """Compute multi-task loss.

        Args:
            predictions: Dict with keys ['overall', 'sharpness', 'color'],
                each containing {'score', 'probs', 'logits'}
            targets: Dict with keys ['overall', 'sharpness', 'color'],
                each containing {'mos', 'soft_labels'}
            return_per_dim: If True, return list of losses for PCGrad

        Returns:
            Either dict with loss breakdown or list of per-dimension losses
        """
        losses = {}

        for dim in ["overall", "sharpness", "color"]:
            pred = predictions[dim]
            target = targets[dim]

            # KL divergence on distributions
            kl_loss = self.kl_criterion(
                F.log_softmax(pred["logits"], dim=-1),
                target["soft_labels"],
            )

            # NormInNorm or MSE on scores
            score_loss = self.score_criterion(pred["score"], target["mos"])

            # Combined loss
            combined_loss = self.kl_weight * kl_loss + self.norm_weight * score_loss
            losses[f"loss_{dim}"] = combined_loss

        if return_per_dim:
            # Return list for PCGrad
            return [
                losses["loss_overall"],
                losses["loss_sharpness"],
                losses["loss_color"],
            ]

        # Return dict with breakdown
        losses["loss_total"] = sum(losses.values()) / 3
        return losses
