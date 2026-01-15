# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""HyperIQA++ Model Architecture.

Enhanced HyperIQA with 7 DocIQ and VQualA 2025 innovations:
1. High-resolution input (1600x1600) - DocIQ
2. Soft label distribution prediction - DeQA-Doc
3. Multi-scale feature fusion - DocIQ Component 2
4. Spatial attention - DocIQ-Simplified
5. PCGrad-compatible multi-task heads
6. NormInNormLoss optimization
7. Extended training protocol (60 epochs)

Target: 0.85 PLCC on DIQA-5000 test set
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import torch.nn as nn
import torch.nn.functional as F  # noqa: N812  # PyTorch convention

from image_preprocessing_detector.labeling.hyperiqa_plus_plus.modules import (
    MultiScaleFeatureFusion,
    SoftLabelHead,
    SpatialAttentionModule,
)

if TYPE_CHECKING:
    from torch import Tensor

logger = logging.getLogger(__name__)


class HyperIQAPlusPlus(nn.Module):
    """Enhanced HyperIQA with DocIQ and VQualA 2025 innovations.

    Architecture:
        Input (1600x1600)
        → ResNet-50 Multi-Scale Features
        → Feature Fusion Module
        → Spatial Attention
        → HyperNet (Content-Adaptive)
        → 3x Soft Label Heads (10 bins each)

    Outputs:
        - Overall quality: score + distribution
        - Sharpness: score + distribution
        - Color fidelity: score + distribution
        - Spatial attention map

    Training Protocol:
        Phase 1 (Epochs 1-10): Freeze backbone, train heads
        Phase 2 (Epochs 11-60): Full fine-tuning with step LR decay
    """

    def __init__(
        self,
        num_bins: int = 10,
        freeze_backbone_epochs: int = 10,
        use_pretrained: bool = True,
    ) -> None:
        """Initialize HyperIQA++ model.

        Args:
            num_bins: Number of quality bins for soft labels
            freeze_backbone_epochs: Number of epochs to freeze backbone
            use_pretrained: Whether to load pretrained HyperIQA weights
        """
        super().__init__()

        # Load pretrained HyperIQA backbone
        if use_pretrained:
            import pyiqa

            metric = pyiqa.create_metric("hyperiqa", device="cpu", as_loss=True)
            hyperiqa_model = metric.net

            # Extract components
            # PyIQA HyperIQA structure inspection

            # The model has 'res' attribute for ResNet, not 'backbone'
            if hasattr(hyperiqa_model, "res"):
                self.backbone = hyperiqa_model.res
            elif hasattr(hyperiqa_model, "backbone"):
                self.backbone = hyperiqa_model.backbone
            else:
                # HyperIQA IS the model itself - it's a HyperNet class
                # Use it directly as the backbone
                self.backbone = hyperiqa_model

            if hasattr(hyperiqa_model, "hypernet"):
                self.hypernet = hyperiqa_model.hypernet
            else:
                # Create simple hypernet if not found
                feature_dim = 2048
                self.hypernet = nn.Sequential(
                    nn.Linear(feature_dim, feature_dim),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                )

            # HyperIQA uses a custom FeatureListNet, not standard ResNet-50
            # We'll use HyperIQA for feature extraction, skip multi-scale fusion
            # to avoid architectural conflicts
            resnet_backbone = None  # Disable multi-scale fusion for HyperIQA

        else:
            # Create from scratch
            import torchvision.models as models

            resnet50 = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
            self.backbone = resnet50
            resnet_backbone = resnet50

            # Create basic hypernet
            feature_dim = 2048
            self.hypernet = nn.Sequential(
                nn.Linear(feature_dim, feature_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )

        # Enhancement 1: Multi-scale feature fusion (DocIQ Component 2)
        # Only use for models created from scratch, not pretrained HyperIQA
        self.feature_fusion: MultiScaleFeatureFusion | None
        if resnet_backbone is not None:
            self.feature_fusion = MultiScaleFeatureFusion(resnet_backbone)
            self.use_multiscale_fusion = True
        else:
            # For HyperIQA, use its own feature extraction
            self.feature_fusion = None
            self.use_multiscale_fusion = False
            logger.warning("Multi-scale fusion disabled (using HyperIQA features)")

        # Enhancement 2: Spatial attention (DocIQ-Simplified)
        self.spatial_attention = SpatialAttentionModule(in_channels=2048)

        # Enhancement 3: Soft label heads (DeQA-Doc innovation)
        self.head_overall = SoftLabelHead(embed_dim=2048, num_bins=num_bins)
        self.head_sharpness = SoftLabelHead(embed_dim=2048, num_bins=num_bins)
        self.head_color = SoftLabelHead(embed_dim=2048, num_bins=num_bins)

        self.freeze_backbone_epochs = freeze_backbone_epochs
        self._frozen = False

    def freeze_backbone(self) -> None:
        """Freeze backbone and hypernet for head warmup phase."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        if self.hypernet is not None:
            for param in self.hypernet.parameters():
                param.requires_grad = False
        if self.feature_fusion is not None:
            for param in self.feature_fusion.parameters():
                param.requires_grad = False
        self._frozen = True

    def unfreeze_backbone(self) -> None:
        """Unfreeze all parameters for full fine-tuning."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        if self.hypernet is not None:
            for param in self.hypernet.parameters():
                param.requires_grad = True
        if self.feature_fusion is not None:
            for param in self.feature_fusion.parameters():
                param.requires_grad = True
        self._frozen = False

    def forward(self, x: Tensor) -> dict[str, dict[str, Tensor] | Tensor]:
        """Forward pass with multi-scale fusion and spatial attention.

        Args:
            x: Input images [B, 3, H, W] where H, W are typically 1600

        Returns:
            Dictionary with keys:
                'overall': {'score', 'probs', 'logits'}
                'sharpness': {'score', 'probs', 'logits'}
                'color': {'score', 'probs', 'logits'}
                'attention_map': Spatial attention weights
        """
        if self.use_multiscale_fusion:
            # Multi-scale feature extraction and fusion (for from-scratch models)
            assert self.feature_fusion is not None  # Guaranteed by __init__
            fused_features = self.feature_fusion(x)  # [B, 2048, H', W']
        else:
            # Use HyperIQA's base_model (ResNet-50) for feature extraction
            # HyperIQA.base_model is a FeatureListNet that returns list of features
            if hasattr(self.backbone, "base_model"):
                # Extract features from base_model
                features = self.backbone.base_model(x)
                # FeatureListNet returns a list - take the last (deepest) features
                if isinstance(features, list):
                    fused_features = features[-1]  # Deepest features
                else:
                    fused_features = features
            else:
                # Fallback: call backbone directly
                features = self.backbone(x)
                # Reshape if needed to ensure spatial dimensions
                if isinstance(features, list):
                    fused_features = features[-1]
                elif len(features.shape) == 2:
                    # [B, D] → [B, D, 1, 1]
                    fused_features = features.view(features.size(0), -1, 1, 1)
                else:
                    fused_features = features

        # Apply spatial attention (layout-aware) if features are spatial
        if len(fused_features.shape) == 4:
            attended_features, attention_map = self.spatial_attention(fused_features)
            # Global average pooling
            features = F.adaptive_avg_pool2d(attended_features, (1, 1))
            features = features.flatten(1)  # [B, 2048]
        else:
            # Features are already flattened
            features = fused_features
            attention_map = None

        # Apply HyperNet for content-adaptive processing (if available)
        if self.hypernet is not None:
            hyper_features = self.hypernet(features)  # [B, 2048]
        else:
            hyper_features = features

        # Predict soft label distributions for each dimension
        overall_score, overall_probs, overall_logits = self.head_overall(hyper_features)
        sharpness_score, sharpness_probs, sharpness_logits = self.head_sharpness(
            hyper_features
        )
        color_score, color_probs, color_logits = self.head_color(hyper_features)

        return {
            "overall": {
                "score": overall_score,
                "probs": overall_probs,
                "logits": overall_logits,
            },
            "sharpness": {
                "score": sharpness_score,
                "probs": sharpness_probs,
                "logits": sharpness_logits,
            },
            "color": {
                "score": color_score,
                "probs": color_probs,
                "logits": color_logits,
            },
            "attention_map": attention_map,
        }

    def get_num_parameters(self) -> dict[str, int]:
        """Get parameter counts for each module.

        Returns:
            Dictionary with parameter counts
        """
        return {
            "backbone": sum(p.numel() for p in self.backbone.parameters()),
            "hypernet": sum(p.numel() for p in self.hypernet.parameters())
            if self.hypernet
            else 0,
            "feature_fusion": sum(p.numel() for p in self.feature_fusion.parameters())
            if self.feature_fusion
            else 0,
            "spatial_attention": sum(
                p.numel() for p in self.spatial_attention.parameters()
            ),
            "head_overall": sum(p.numel() for p in self.head_overall.parameters()),
            "head_sharpness": sum(p.numel() for p in self.head_sharpness.parameters()),
            "head_color": sum(p.numel() for p in self.head_color.parameters()),
            "total": sum(p.numel() for p in self.parameters()),
        }
