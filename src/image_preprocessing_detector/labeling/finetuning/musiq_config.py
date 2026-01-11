# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Configuration for MUSIQ fine-tuning.

This module defines configuration classes for MUSIQ multi-task fine-tuning
on DIQA-5000, including:
- Training hyperparameters (two-phase protocol)
- Loss weights (sharpness specialist)
- Checkpoint selection (weighted SRCC + ECE scoring)
- LR scheduling (warmup + cosine decay)

Aligned with:
- DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1
- docs/planning/MUSIQ_FINETUNING_PLAN.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MUSIQTrainingConfig:
    """Complete configuration for MUSIQ fine-tuning.

    Aligned with DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1 and
    consensus recommendations (warmup + cosine decay LR schedule).

    Attributes:
        head_hidden_dim: Hidden dimension for multi-task head.
        dropout: Dropout probability for head.
        phase1_epochs: Number of epochs for Phase 1 (head warmup).
        phase1_lr: Learning rate for Phase 1.
        phase1_warmup_epochs: Warmup epochs for Phase 1.
        phase1_freeze_backbone: Whether to freeze backbone in Phase 1.
        phase2_epochs: Number of epochs for Phase 2 (full fine-tune).
        phase2_backbone_lr: Backbone learning rate for Phase 2.
        phase2_head_lr: Head learning rate for Phase 2.
        phase2_warmup_epochs: Warmup epochs for Phase 2.
        batch_size: Training batch size.
        weight_decay: AdamW weight decay.
        gradient_clip_norm: Max gradient norm for clipping.
        loss_weights: Per-dimension loss weights.
        checkpoint_preset: Checkpoint selection preset name.
        checkpoint_interval: Epochs between checkpoints.
        early_stopping_patience: Epochs without improvement before stopping.
        early_stopping_metric: Metric to monitor for early stopping.
        lr_schedule: LR schedule type.
    """

    # Model architecture
    head_hidden_dim: int = 256
    dropout: float = 0.1

    # Phase 1: Head warmup
    phase1_epochs: int = 10
    phase1_lr: float = 1e-3
    phase1_warmup_epochs: int = 2  # Linear warmup per consensus
    phase1_freeze_backbone: bool = True

    # Phase 2: Full fine-tuning
    phase2_epochs: int = 20
    phase2_backbone_lr: float = 1e-5
    phase2_head_lr: float = 1e-4
    phase2_warmup_epochs: int = 3  # Linear warmup per consensus

    # Training
    batch_size: int = 32
    gradient_accumulation_steps: int = 1  # Effective batch = batch_size * this
    weight_decay: float = 1e-4
    gradient_clip_norm: float = 1.0
    num_workers: int = 4

    # Loss weights (sharpness specialist)
    loss_weights: dict[str, float] = field(
        default_factory=lambda: {
            "overall": 0.2,
            "sharpness": 0.6,
            "color": 0.2,
        }
    )

    # Loss component weights
    mse_weight: float = 0.6
    rank_weight: float = 0.2
    focal_weight: float = 0.2

    # Checkpoint selection (Weighted SRCC + ECE scoring)
    checkpoint_preset: str = "balanced"  # 70% SRCC, 30% ECE, +-0.02 band
    checkpoint_interval: int = 5

    # Early stopping
    early_stopping_patience: int = 10
    early_stopping_metric: str = "srcc_sharpness"

    # LR schedule
    lr_schedule: str = "warmup_cosine"  # Per consensus recommendations

    # Data augmentation
    use_augmentation: bool = True

    @property
    def total_epochs(self) -> int:
        """Total number of training epochs."""
        return self.phase1_epochs + self.phase2_epochs

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "head_hidden_dim": self.head_hidden_dim,
            "dropout": self.dropout,
            "phase1_epochs": self.phase1_epochs,
            "phase1_lr": self.phase1_lr,
            "phase1_warmup_epochs": self.phase1_warmup_epochs,
            "phase1_freeze_backbone": self.phase1_freeze_backbone,
            "phase2_epochs": self.phase2_epochs,
            "phase2_backbone_lr": self.phase2_backbone_lr,
            "phase2_head_lr": self.phase2_head_lr,
            "phase2_warmup_epochs": self.phase2_warmup_epochs,
            "batch_size": self.batch_size,
            "weight_decay": self.weight_decay,
            "gradient_clip_norm": self.gradient_clip_norm,
            "num_workers": self.num_workers,
            "loss_weights": self.loss_weights,
            "mse_weight": self.mse_weight,
            "rank_weight": self.rank_weight,
            "focal_weight": self.focal_weight,
            "checkpoint_preset": self.checkpoint_preset,
            "checkpoint_interval": self.checkpoint_interval,
            "early_stopping_patience": self.early_stopping_patience,
            "early_stopping_metric": self.early_stopping_metric,
            "lr_schedule": self.lr_schedule,
            "use_augmentation": self.use_augmentation,
            "total_epochs": self.total_epochs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MUSIQTrainingConfig:
        """Create configuration from dictionary."""
        # Remove computed properties
        data = {k: v for k, v in data.items() if k != "total_epochs"}
        return cls(**data)


# Checkpoint selection presets from Section 4.5
CHECKPOINT_PRESETS: dict[str, dict[str, float]] = {
    "srcc_dominant": {"srcc_weight": 0.8, "ece_weight": 0.2, "srcc_band": 0.015},
    "balanced": {"srcc_weight": 0.7, "ece_weight": 0.3, "srcc_band": 0.02},
    "calibration_aware": {"srcc_weight": 0.6, "ece_weight": 0.4, "srcc_band": 0.025},
}


def get_checkpoint_preset(name: str) -> dict[str, float]:
    """Get checkpoint selection preset by name.

    Args:
        name: Preset name ('srcc_dominant', 'balanced', 'calibration_aware').

    Returns:
        Dictionary with srcc_weight, ece_weight, srcc_band.

    Raises:
        ValueError: If preset name is not recognized.
    """
    if name not in CHECKPOINT_PRESETS:
        valid = ", ".join(CHECKPOINT_PRESETS.keys())
        raise ValueError(f"Unknown checkpoint preset '{name}'. Valid options: {valid}")
    return CHECKPOINT_PRESETS[name]


def compute_checkpoint_score(
    checkpoint: dict[str, float],
    specialty: str,
    best_srcc: float,
    srcc_weight: float = 0.7,
    ece_weight: float = 0.3,
    srcc_band: float = 0.02,
) -> float:
    """Compute weighted score for checkpoint selection.

    Within the SRCC band, we allow trading small SRCC losses for ECE gains.
    Outside the band, checkpoints are excluded.

    Args:
        checkpoint: Checkpoint metrics dict with srcc_{dim} and ece_mean keys.
        specialty: Dimension to optimize ('overall', 'sharpness', 'color', 'mean').
        best_srcc: Best SRCC value among all checkpoints.
        srcc_weight: Weight for SRCC component (default 0.7).
        ece_weight: Weight for ECE component (default 0.3).
        srcc_band: SRCC tolerance band (default 0.02).

    Returns:
        Combined score (higher is better), or -inf if outside band.
    """
    srcc = checkpoint[f"srcc_{specialty}"]
    ece = checkpoint["ece_mean"]

    # Exclude checkpoints outside SRCC band
    if srcc < best_srcc - srcc_band:
        return float("-inf")

    # Normalize SRCC: 0 = band floor, 1 = best
    # This makes small SRCC differences within band less dramatic
    srcc_normalized = (srcc - (best_srcc - srcc_band)) / max(srcc_band, 1e-6)

    # Normalize ECE: assume ECE range [0, 0.15], invert so lower is better
    # Clamped to [0, 1] range
    ece_normalized = max(0, min(1, 1 - (ece / 0.15)))

    return srcc_weight * srcc_normalized + ece_weight * ece_normalized


def select_best_checkpoint(
    checkpoints: list[dict[str, float]],
    specialty: str,
    srcc_weight: float = 0.7,
    ece_weight: float = 0.3,
    srcc_band: float = 0.02,
) -> dict[str, float]:
    """Select checkpoint using weighted SRCC + ECE scoring.

    Within the SRCC band (default +-0.02 from best), checkpoints compete on
    a weighted score. This allows giving up a little SRCC (e.g., 0.01) for
    a significant ECE improvement (e.g., 0.05 -> 0.03).

    Args:
        checkpoints: List of checkpoint metrics dicts.
        specialty: Dimension to optimize ('overall', 'sharpness', 'color', 'mean').
        srcc_weight: Weight for SRCC in combined score (default 0.7).
        ece_weight: Weight for ECE in combined score (default 0.3).
        srcc_band: SRCC tolerance band from best (default 0.02).

    Returns:
        Best checkpoint based on weighted score.

    Raises:
        ValueError: If no valid checkpoints found.
    """
    if not checkpoints:
        raise ValueError("No checkpoints provided")

    # Find best SRCC
    best_srcc = max(c[f"srcc_{specialty}"] for c in checkpoints)

    # Score all checkpoints
    scored = [
        (
            c,
            compute_checkpoint_score(
                c, specialty, best_srcc, srcc_weight, ece_weight, srcc_band
            ),
        )
        for c in checkpoints
    ]

    # Filter out excluded checkpoints and sort by score
    valid = [(c, s) for c, s in scored if s > float("-inf")]

    if not valid:
        raise ValueError("No checkpoints within SRCC band")

    valid.sort(key=lambda x: x[1], reverse=True)

    return valid[0][0]


@dataclass
class CheckpointMetrics:
    """Metrics tracked for each checkpoint.

    Attributes:
        epoch: Training epoch number.
        phase: Training phase (1 or 2).
        train_loss: Training loss.
        srcc_overall: SRCC for overall dimension.
        srcc_sharpness: SRCC for sharpness dimension.
        srcc_color: SRCC for color dimension.
        srcc_mean: Mean SRCC across dimensions.
        ece_overall: ECE for overall dimension.
        ece_sharpness: ECE for sharpness dimension.
        ece_color: ECE for color dimension.
        ece_mean: Mean ECE across dimensions.
        plcc_overall: PLCC for overall dimension.
        plcc_sharpness: PLCC for sharpness dimension.
        plcc_color: PLCC for color dimension.
    """

    epoch: int
    phase: int
    train_loss: float

    # SRCC metrics
    srcc_overall: float
    srcc_sharpness: float
    srcc_color: float
    srcc_mean: float

    # ECE metrics
    ece_overall: float
    ece_sharpness: float
    ece_color: float
    ece_mean: float

    # PLCC metrics
    plcc_overall: float = 0.0
    plcc_sharpness: float = 0.0
    plcc_color: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for checkpoint selection."""
        return {
            "epoch": self.epoch,
            "phase": self.phase,
            "train_loss": self.train_loss,
            "srcc_overall": self.srcc_overall,
            "srcc_sharpness": self.srcc_sharpness,
            "srcc_color": self.srcc_color,
            "srcc_mean": self.srcc_mean,
            "ece_overall": self.ece_overall,
            "ece_sharpness": self.ece_sharpness,
            "ece_color": self.ece_color,
            "ece_mean": self.ece_mean,
            "plcc_overall": self.plcc_overall,
            "plcc_sharpness": self.plcc_sharpness,
            "plcc_color": self.plcc_color,
        }
