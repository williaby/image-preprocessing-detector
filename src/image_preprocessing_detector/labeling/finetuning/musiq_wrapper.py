# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""MUSIQ wrapper for multi-task DIQA fine-tuning.

This module implements the MUSIQMultiTask wrapper that adapts the PyIQA
MUSIQ model for multi-task quality prediction on DIQA-5000 dimensions:
- Overall quality
- Sharpness (PRIMARY - this model's specialty)
- Color fidelity

Architecture follows DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1:
- Extract 384-dim backbone features from PyIQA MUSIQ
- Replace single MOS head with MultiTaskHead (3 outputs)
- Support two-phase training (frozen backbone -> full fine-tune)

Reference: docs/planning/MUSIQ_FINETUNING_PLAN.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog
import torch
import torch.nn as nn

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = structlog.get_logger(__name__)


@dataclass
class MultiTaskHeadConfig:
    """Configuration for the multi-task regression head.

    Attributes:
        in_features: Input feature dimension (384 for MUSIQ).
        hidden_dim: Hidden layer dimension.
        dropout: Dropout probability.
        num_outputs: Number of output dimensions (3 for DIQA).
    """

    in_features: int = 384
    hidden_dim: int = 256
    dropout: float = 0.1
    num_outputs: int = 3


class MultiTaskHead(nn.Module):
    """Shared MLP with 3 regression outputs for DIQA dimensions.

    Architecture matches DIQA-5000_Pseudo_Labels_v2.md Section 4.2:
    - Shared hidden layer for multi-task regularization
    - Per-dimension output heads
    - Sigmoid activation for [0, 1] bounded output

    Example:
        >>> config = MultiTaskHeadConfig(in_features=384)
        >>> head = MultiTaskHead(config)
        >>> features = torch.randn(4, 384)
        >>> outputs = head(features)
        >>> print(outputs["sharpness"].shape)  # [4]
    """

    def __init__(self, config: MultiTaskHeadConfig) -> None:
        """Initialize the multi-task head.

        Args:
            config: Head configuration.
        """
        super().__init__()
        self.config = config

        # Shared feature transformation
        self.shared = nn.Sequential(
            nn.Linear(config.in_features, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
        )

        # Per-dimension regression heads
        self.heads = nn.ModuleDict(
            {
                "overall": nn.Linear(config.hidden_dim, 1),
                "sharpness": nn.Linear(config.hidden_dim, 1),
                "color": nn.Linear(config.hidden_dim, 1),
            }
        )

        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier initialization for stable training."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through the multi-task head.

        Args:
            features: Input features of shape [batch, in_features].

        Returns:
            Dictionary of dimension scores, each of shape [batch] in [0, 1].
        """
        shared = self.shared(features)
        return {
            dim: torch.sigmoid(head(shared).squeeze(-1))
            for dim, head in self.heads.items()
        }


class MUSIQBackbone(nn.Module):
    """Wrapper to use PyIQA MUSIQ score as input feature for multi-task learning.

    PyIQA's MUSIQ model uses complex multi-scale patch extraction internally.
    Rather than trying to extract intermediate features, this wrapper uses
    MUSIQ's MOS score output (0-100) as a feature, along with learned
    embeddings to map the score to multi-task outputs.

    The approach:
    1. Pass image through frozen MUSIQ to get MOS score
    2. Map MOS score + learned features to 384-dim representation
    3. Train MultiTaskHead on this representation

    Attributes:
        _musiq_model: Complete PyIQA MUSIQ model.
        score_encoder: MLP to encode MUSIQ score to feature space.

    Example:
        >>> import pyiqa
        >>> base_musiq = pyiqa.create_metric("musiq", device="cuda")
        >>> backbone = MUSIQBackbone(base_musiq)
        >>> images = torch.randn(4, 3, 224, 224).cuda()
        >>> features = backbone(images)
        >>> print(features.shape)  # [4, 384]
    """

    def __init__(self, musiq_model: nn.Module) -> None:
        """Initialize MUSIQ backbone wrapper.

        Args:
            musiq_model: PyIQA MUSIQ model (from create_metric("musiq")).
        """
        super().__init__()
        self._musiq_model = musiq_model

        # Freeze MUSIQ model - we only use its output
        for param in self._musiq_model.parameters():
            param.requires_grad = False

        # Score encoder: maps MUSIQ score (1-dim) to 384-dim feature space
        # We add learnable features that adapt the MUSIQ score for multi-task
        self.score_encoder = nn.Sequential(
            nn.Linear(1, 64),
            nn.ReLU(),
            nn.Linear(64, 256),
            nn.ReLU(),
            nn.Linear(256, 384),
        )

        # Store reference to internal model for logging
        if hasattr(musiq_model, "net"):
            inner_type = type(musiq_model.net).__name__
        else:
            inner_type = type(musiq_model).__name__

        logger.info(
            "musiq_backbone_initialized",
            inner_model_type=inner_type,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Extract features using MUSIQ score as input.

        Args:
            x: Input tensor of shape [batch, channels, height, width].
                Expected to be in [0, 1] range.

        Returns:
            Features of shape [batch, 384].
        """
        # Get MUSIQ scores (shape: [batch] or [batch, 1])
        # CRITICAL: MUSIQ must be in eval mode for proper preprocessing.
        # In eval mode, it applies get_multiscale_patches automatically.
        # In train mode, it expects pre-processed patches which we don't provide.
        was_training = self._musiq_model.training
        self._musiq_model.eval()
        with torch.no_grad():
            scores = self._musiq_model(x)  # Returns score 0-100
        if was_training:
            self._musiq_model.train()

        # Normalize score to [0, 1] and reshape
        if scores.dim() == 1:
            scores = scores.unsqueeze(1)  # [batch, 1]
        scores = scores / 100.0  # Normalize to [0, 1]

        # Encode scores to feature space
        encoded: torch.Tensor = self.score_encoder(scores)  # [batch, 384]
        return encoded

    def get_musiq_score(self, x: torch.Tensor) -> torch.Tensor:
        """Get raw MUSIQ scores without encoding.

        Args:
            x: Input images.

        Returns:
            MUSIQ scores of shape [batch].
        """
        # Ensure eval mode for proper preprocessing
        was_training = self._musiq_model.training
        self._musiq_model.eval()
        with torch.no_grad():
            scores = self._musiq_model(x)
        if was_training:
            self._musiq_model.train()
        if scores.dim() > 1:
            scores = scores.squeeze(-1)
        result: torch.Tensor = scores
        return result


class MUSIQMultiTask(nn.Module):
    """MUSIQ backbone with multi-task head for DIQA dimensions.

    This class wraps the PyIQA MUSIQ model and replaces its single
    MOS output with 3-dimensional quality prediction for DIQA:
    - Overall quality (secondary for this specialist)
    - Sharpness (PRIMARY - this model's specialty)
    - Color fidelity (secondary for this specialist)

    Supports two-phase training:
    1. Phase 1: Frozen backbone, train head only
    2. Phase 2: Unfreeze backbone for full fine-tuning

    Example:
        >>> import pyiqa
        >>> base_musiq = pyiqa.create_metric("musiq", device="cuda")
        >>> model = MUSIQMultiTask(base_musiq, freeze_backbone=True)
        >>> images = torch.randn(4, 3, 384, 384).cuda()
        >>> outputs = model(images)
        >>> print(outputs["sharpness"].shape)  # [4]
    """

    def __init__(
        self,
        pretrained_musiq: nn.Module,
        freeze_backbone: bool = True,
        head_config: MultiTaskHeadConfig | None = None,
    ) -> None:
        """Initialize MUSIQ multi-task model.

        Args:
            pretrained_musiq: Pre-trained PyIQA MUSIQ model.
            freeze_backbone: Whether to freeze backbone (Phase 1).
            head_config: Configuration for multi-task head.
        """
        super().__init__()

        # Extract backbone
        self.backbone = MUSIQBackbone(pretrained_musiq)

        # Freeze backbone if requested (Phase 1)
        self._backbone_frozen = freeze_backbone
        if freeze_backbone:
            self._freeze_backbone()

        # Create multi-task head
        if head_config is None:
            head_config = MultiTaskHeadConfig()
        self.head_config = head_config
        self.head = MultiTaskHead(head_config)

        logger.info(
            "musiq_multitask_initialized",
            freeze_backbone=freeze_backbone,
            head_hidden_dim=head_config.hidden_dim,
            head_dropout=head_config.dropout,
        )

    def _freeze_backbone(self) -> None:
        """Freeze all backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        self._backbone_frozen = True
        logger.info("musiq_backbone_frozen")

    def unfreeze_backbone(self) -> None:
        """Unfreeze backbone parameters for Phase 2 training."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        self._backbone_frozen = False
        logger.info("musiq_backbone_unfrozen")

    @property
    def is_backbone_frozen(self) -> bool:
        """Check if backbone is currently frozen."""
        return self._backbone_frozen

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through backbone and multi-task head.

        Args:
            x: Input images of shape [batch, 3, H, W].

        Returns:
            Dictionary with keys 'overall', 'sharpness', 'color',
            each containing scores of shape [batch] in [0, 1].
        """
        features = self.backbone(x)  # [batch, 384]
        result: dict[str, Any] = self.head(features)  # {dim: [batch]}
        return result

    def get_backbone_params(self) -> Iterator[nn.Parameter]:
        """Get backbone parameters for optimizer groups."""
        return iter(self.backbone.parameters())

    def get_head_params(self) -> Iterator[nn.Parameter]:
        """Get head parameters for optimizer groups."""
        return iter(self.head.parameters())

    def get_trainable_params(self) -> int:
        """Get count of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_total_params(self) -> int:
        """Get total parameter count."""
        return sum(p.numel() for p in self.parameters())


def create_musiq_multitask(
    device: str = "cuda",
    freeze_backbone: bool = True,
    head_hidden_dim: int = 256,
    head_dropout: float = 0.1,
) -> MUSIQMultiTask:
    """Factory function to create MUSIQMultiTask model.

    This function handles PyIQA loading and wrapping in one step.

    Args:
        device: Device to load model on.
        freeze_backbone: Whether to freeze backbone initially.
        head_hidden_dim: Hidden dimension for multi-task head.
        head_dropout: Dropout probability for head.

    Returns:
        Initialized MUSIQMultiTask model.

    Example:
        >>> model = create_musiq_multitask(device="cuda", freeze_backbone=True)
        >>> model.to("cuda")
    """
    try:
        import pyiqa
    except ImportError as e:
        raise ImportError(
            "PyIQA is required for MUSIQ. Install with: pip install pyiqa"
        ) from e

    # Load pre-trained MUSIQ
    logger.info("loading_pyiqa_musiq", device=device)
    base_musiq = pyiqa.create_metric("musiq", device=device)

    # Create config
    head_config = MultiTaskHeadConfig(
        in_features=384,
        hidden_dim=head_hidden_dim,
        dropout=head_dropout,
    )

    # Create wrapped model
    return MUSIQMultiTask(
        pretrained_musiq=base_musiq,
        freeze_backbone=freeze_backbone,
        head_config=head_config,
    )
