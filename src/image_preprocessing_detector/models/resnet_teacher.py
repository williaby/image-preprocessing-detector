"""ResNet-50 Teacher Model for Image Quality Assessment.

This module implements a multi-head ResNet-50 architecture for document image
quality assessment. The teacher model is used selectively for high-risk pages
that require more accurate predictions.

Architecture:
    - Backbone: ResNet-50 (pretrained on ImageNet)
    - Multi-Head: 5 parallel heads for quality issue detection
        1. Blur detection
        2. Noise detection
        3. Skew detection
        4. Illumination (low contrast) detection
        5. Artifacts detection
    - Each head: FC → BatchNorm → ReLU → Dropout → Output (binary + confidence)

Performance Targets:
    - GPU inference: ≤30ms/page
    - CPU inference: Not recommended (use student model)
    - Accuracy: > 0.88 mAP on OHR-Bench

Usage:
    >>> model = ResNetTeacher(num_heads=5, dropout=0.2, pretrained=True)
    >>> output = model(images)  # Returns dict with per-head predictions
    >>> blur_logits = output["blur"]["logits"]
    >>> blur_confidence = output["blur"]["confidence"]
"""

from typing import Any, ClassVar

import torch
import torch.nn as nn
from torchvision.models import ResNet50_Weights, resnet50


class IQAHead(nn.Module):
    """Single head for quality issue detection.

    Each head performs binary classification (issue present/absent) and
    confidence scoring for a specific quality issue type.

    Args:
        in_features: Number of input features from backbone
        hidden_features: Number of hidden layer features (default: 512)
        dropout: Dropout probability (default: 0.2)
        head_name: Name of this head for logging/debugging
    """

    def __init__(
        self,
        in_features: int = 2048,
        hidden_features: int = 512,
        dropout: float = 0.2,
        head_name: str = "unnamed",
    ) -> None:
        super().__init__()
        self.head_name = head_name

        # Fully connected layer with BatchNorm and ReLU
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.bn1 = nn.BatchNorm1d(hidden_features)
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(p=dropout)

        # Output layer: 2 outputs (logit for classification, confidence score)
        self.fc2 = nn.Linear(hidden_features, 2)

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize layer weights using Xavier initialization."""
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.constant_(self.fc1.bias, 0.0)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.constant_(self.fc2.bias, 0.0)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through the head.

        Args:
            x: Input tensor of shape (batch_size, in_features)

        Returns:
            Dictionary containing:
                - logits: Binary classification logits (batch_size, 1)
                - confidence: Confidence scores (batch_size, 1)
        """
        # Hidden layer
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.dropout(x)

        # Output layer
        out = self.fc2(x)

        # Split into logits and confidence
        logits = out[:, 0:1]  # Binary classification logit
        confidence = torch.sigmoid(out[:, 1:2])  # Confidence in [0, 1]

        return {"logits": logits, "confidence": confidence}


class ResNetTeacher(nn.Module):
    """ResNet-50 Teacher Model with multi-head architecture for IQA.

    This is the high-capacity teacher model used for difficult/high-risk pages.
    It uses pretrained ResNet-50 as a backbone with 5 specialized heads for
    different quality issues.

    Args:
        num_heads: Number of quality assessment heads (default: 5)
        dropout: Dropout probability for heads (default: 0.2)
        pretrained: Whether to use ImageNet pretrained weights (default: True)
        freeze_backbone: Whether to freeze backbone weights (default: False)
        hidden_features: Hidden layer size for each head (default: 512)

    Attributes:
        backbone: ResNet-50 feature extractor
        heads: Dictionary of IQA heads (blur, noise, skew, illumination, artifacts)
    """

    # Define quality issue types
    ISSUE_TYPES: ClassVar[list[str]] = [
        "blur",
        "noise",
        "skew",
        "illumination",
        "artifacts",
    ]

    def __init__(
        self,
        num_heads: int = 5,
        dropout: float = 0.2,
        pretrained: bool = True,
        freeze_backbone: bool = False,
        hidden_features: int = 512,
    ) -> None:
        super().__init__()

        if num_heads != len(self.ISSUE_TYPES):
            raise ValueError(
                f"num_heads must be {len(self.ISSUE_TYPES)} "
                f"(one for each issue type: {self.ISSUE_TYPES})"
            )

        # Load pretrained ResNet-50 backbone
        if pretrained:
            weights = ResNet50_Weights.IMAGENET1K_V2
            self.backbone = resnet50(weights=weights)
        else:
            self.backbone = resnet50(weights=None)

        # Remove the final fully connected layer (we'll add our own heads)
        self.backbone_features = nn.Sequential(*list(self.backbone.children())[:-1])

        # Get the number of output features from ResNet-50 (2048)
        in_features = 2048

        # Optionally freeze backbone weights for transfer learning
        if freeze_backbone:
            for param in self.backbone_features.parameters():
                param.requires_grad = False

        # Create multi-head architecture
        self.heads = nn.ModuleDict()
        for issue_type in self.ISSUE_TYPES:
            self.heads[issue_type] = IQAHead(
                in_features=in_features,
                hidden_features=hidden_features,
                dropout=dropout,
                head_name=issue_type,
            )

        # Store configuration
        self.num_heads = num_heads
        self.dropout = dropout
        self.pretrained = pretrained
        self.freeze_backbone = freeze_backbone
        self.hidden_features = hidden_features

    def forward(self, x: torch.Tensor) -> dict[str, dict[str, torch.Tensor]]:
        """Forward pass through the model.

        Args:
            x: Input tensor of shape (batch_size, 3, H, W)
               Expected input: RGB images normalized with ImageNet stats

        Returns:
            Dictionary mapping issue type to head outputs:
                {
                    "blur": {"logits": tensor, "confidence": tensor},
                    "noise": {"logits": tensor, "confidence": tensor},
                    "skew": {"logits": tensor, "confidence": tensor},
                    "illumination": {"logits": tensor, "confidence": tensor},
                    "artifacts": {"logits": tensor, "confidence": tensor}
                }
        """
        # Extract features from backbone
        features = self.backbone_features(x)
        features = torch.flatten(features, 1)  # (batch_size, 2048)

        # Pass through each head
        outputs: dict[str, dict[str, torch.Tensor]] = {}
        for issue_type, head in self.heads.items():
            outputs[issue_type] = head(features)

        return outputs

    def get_model_info(self) -> dict[str, Any]:
        """Get model configuration information.

        Returns:
            Dictionary containing model configuration details
        """
        return {
            "architecture": "ResNet-50 Teacher",
            "num_heads": self.num_heads,
            "issue_types": self.ISSUE_TYPES,
            "dropout": self.dropout,
            "pretrained": self.pretrained,
            "freeze_backbone": self.freeze_backbone,
            "hidden_features": self.hidden_features,
            "backbone_features": 2048,
            "total_parameters": sum(p.numel() for p in self.parameters()),
            "trainable_parameters": sum(
                p.numel() for p in self.parameters() if p.requires_grad
            ),
        }

    def freeze_backbone_layers(self, num_layers: int = -1) -> None:
        """Freeze specific layers of the backbone for fine-tuning.

        Args:
            num_layers: Number of layers to freeze from the beginning.
                       -1 freezes all layers (default)
        """
        layers = list(self.backbone_features.children())
        if num_layers == -1:
            num_layers = len(layers)

        for _i, layer in enumerate(layers[:num_layers]):
            for param in layer.parameters():
                param.requires_grad = False

    def unfreeze_backbone_layers(self) -> None:
        """Unfreeze all backbone layers for full fine-tuning."""
        for param in self.backbone_features.parameters():
            param.requires_grad = True

    def get_predictions(
        self, x: torch.Tensor, threshold: float = 0.5
    ) -> dict[str, dict[str, Any]]:
        """Get binary predictions and confidence scores.

        Args:
            x: Input tensor of shape (batch_size, 3, H, W)
            threshold: Threshold for binary classification (default: 0.5)

        Returns:
            Dictionary with predictions for each issue type:
                {
                    "blur": {
                        "present": bool tensor,
                        "confidence": float tensor,
                        "logits": float tensor
                    },
                    ...
                }
        """
        outputs = self.forward(x)
        predictions = {}

        for issue_type, head_output in outputs.items():
            logits = head_output["logits"]
            confidence = head_output["confidence"]

            # Convert logits to probabilities
            probabilities = torch.sigmoid(logits)

            # Binary predictions based on threshold
            present = probabilities > threshold

            predictions[issue_type] = {
                "present": present,
                "probability": probabilities,
                "confidence": confidence,
                "logits": logits,
            }

        return predictions
