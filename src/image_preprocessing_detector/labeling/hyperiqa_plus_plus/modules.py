# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Core modules for HyperIQA++ architecture.

Implements DocIQ-inspired components:
- Multi-scale feature fusion from ResNet stages
- Spatial attention for layout-aware processing
- Soft label distribution heads
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812  # PyTorch convention

if TYPE_CHECKING:
    from torch import Tensor


class MultiScaleFeatureFusion(nn.Module):
    """Extract and fuse features from multiple ResNet-50 stages.

    DocIQ Innovation (Component 2): Quality assessment requires both
    low-level (edges, noise) and high-level (semantics, layout) features.

    ResNet-50 Stages:
        - Stage 1 (layer1/conv2_x): 256 channels - edges, textures
        - Stage 2 (layer2/conv3_x): 512 channels - patterns
        - Stage 3 (layer3/conv4_x): 1024 channels - structures
        - Stage 4 (layer4/conv5_x): 2048 channels - semantics

    Strategy:
        1. Extract features from all 4 stages
        2. Project to unified 512-dim space
        3. Resize to same spatial size
        4. Concatenate and fuse to 2048-dim output
    """

    def __init__(self, backbone_resnet50: nn.Module) -> None:
        """Initialize multi-scale feature fusion.

        Args:
            backbone_resnet50: Pretrained ResNet-50 backbone
        """
        super().__init__()
        self.backbone = backbone_resnet50

        # Projection layers to unified 512-dim
        self.proj1 = nn.Conv2d(256, 512, kernel_size=1)
        self.proj2 = nn.Conv2d(512, 512, kernel_size=1)
        self.proj3 = nn.Conv2d(1024, 512, kernel_size=1)
        self.proj4 = nn.Conv2d(2048, 512, kernel_size=1)

        # Fusion layer (512x4 → 2048)
        self.fusion = nn.Sequential(
            nn.Conv2d(512 * 4, 1024, kernel_size=1),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
            nn.Conv2d(1024, 2048, kernel_size=1),
            nn.BatchNorm2d(2048),
        )

    def forward(self, x: Tensor) -> Tensor:
        """Extract and fuse multi-scale features.

        Args:
            x: Input tensor [B, 3, H, W]

        Returns:
            Fused features [B, 2048, H', W']
        """
        features = []

        # Initial layers
        x = self.backbone.conv1(x)
        x = self.backbone.bn1(x)
        x = self.backbone.relu(x)
        x = self.backbone.maxpool(x)

        # Stage 1: 256 channels
        x = self.backbone.layer1(x)
        features.append(self.proj1(x))

        # Stage 2: 512 channels
        x = self.backbone.layer2(x)
        features.append(self.proj2(x))

        # Stage 3: 1024 channels
        x = self.backbone.layer3(x)
        features.append(self.proj3(x))

        # Stage 4: 2048 channels
        x = self.backbone.layer4(x)
        features.append(self.proj4(x))

        # Resize all to same spatial size (use first feature map as target)
        target_size = features[0].shape[2:]
        features = [
            F.interpolate(f, size=target_size, mode="bilinear", align_corners=False)
            for f in features
        ]

        # Concatenate and fuse
        fused = torch.cat(features, dim=1)  # [B, 512*4, H, W]
        return self.fusion(fused)  # [B, 2048, H, W]


class SpatialAttentionModule(nn.Module):
    """Learn to attend to important regions (typically text areas).

    Simplified alternative to DocIQ's layout fusion which requires external
    layout detection. This module learns through gradient optimization to
    focus on quality-critical regions.

    DocIQ Insight: Text regions require higher sharpness than backgrounds.
    The network learns to weight text-heavy regions more heavily.
    """

    def __init__(self, in_channels: int = 2048) -> None:
        """Initialize spatial attention module.

        Args:
            in_channels: Number of input channels (typically 2048 for ResNet-50)
        """
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 512, kernel_size=1)
        self.bn1 = nn.BatchNorm2d(512)
        self.conv2 = nn.Conv2d(512, 1, kernel_size=1)

    def forward(self, features: Tensor) -> tuple[Tensor, Tensor]:
        """Apply spatial attention to features.

        Args:
            features: Input features [B, C, H, W]

        Returns:
            Tuple of (attended_features, attention_map)
        """
        # Generate attention map
        attn = F.relu(self.bn1(self.conv1(features)))
        attn = torch.sigmoid(self.conv2(attn))  # [B, 1, H, W]

        # Apply attention (element-wise multiplication)
        attended_features = features * attn

        return attended_features, attn


class SoftLabelHead(nn.Module):
    """Predict probability distribution over quality bins.

    DeQA-Doc Innovation: Predicting score distributions outperforms
    scalar regression. Allows model to express uncertainty about
    ambiguous quality levels.

    Output:
        - Logits over num_bins quality bins
        - Softmax probabilities (distribution)
        - Expected value as final score
    """

    def __init__(self, embed_dim: int = 2048, num_bins: int = 10) -> None:
        """Initialize soft label head.

        Args:
            embed_dim: Input feature dimension
            num_bins: Number of quality bins for distribution
        """
        super().__init__()
        self.num_bins = num_bins

        self.head = nn.Sequential(
            nn.Linear(embed_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_bins),
        )

        # Bin centers for 1-5 MOS scale mapped to 10 bins
        # Example: 10 bins → [1.0, 1.44, 1.89, 2.33, 2.78, 3.22, 3.67, 4.11, 4.56, 5.0]
        self.register_buffer("bin_centers", torch.linspace(1.0, 5.0, num_bins))

    def forward(self, features: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        """Predict quality score distribution.

        Args:
            features: Input features [B, embed_dim]

        Returns:
            Tuple of (score, probs, logits):
                - score: Expected value from distribution [B]
                - probs: Softmax probabilities [B, num_bins]
                - logits: Raw logits [B, num_bins]
        """
        logits = self.head(features)  # [B, num_bins]
        probs = F.softmax(logits, dim=-1)  # Distribution

        # Expected value as final score
        # score = Σ(p_i x bin_center_i)
        score = (probs * self.bin_centers).sum(dim=-1)  # [B]

        return score, probs, logits
