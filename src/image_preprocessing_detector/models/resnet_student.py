"""ResNet-18 Student Model for Image Quality Assessment.

This module implements a lightweight multi-head ResNet-18 architecture that learns
from the ResNet-50 teacher model via knowledge distillation. The student model
provides faster inference while maintaining acceptable accuracy.

Architecture:
    - Backbone: ResNet-18 (pretrained on ImageNet, ~4x smaller than ResNet-50)
    - Multi-Head: 5 parallel heads for quality issue detection (same as teacher)
        1. Blur detection
        2. Noise detection
        3. Skew detection
        4. Illumination (low contrast) detection
        5. Artifacts detection
    - Each head: FC → BatchNorm → ReLU → Dropout → Output (binary + confidence)

Performance Targets:
    - GPU inference: ≤10ms/page (target), ≤25ms (acceptable)
    - CPU inference: ≤40ms/page (target), ≤100ms (acceptable)
    - Accuracy: Within 5% of teacher mAP after distillation

Model Size Comparison:
    - ResNet-50 (Teacher): ~25M parameters, ~100MB
    - ResNet-18 (Student): ~11M parameters, ~45MB

Usage:
    >>> student = ResNetStudent(num_heads=5, dropout=0.2, pretrained=True)
    >>> output = student(images)  # Returns dict with per-head predictions
    >>> blur_logits = output["blur"]["logits"]
    >>> blur_confidence = output["blur"]["confidence"]
"""

from typing import ClassVar

import torch
import torch.nn as nn
from torchvision.models import ResNet18_Weights, resnet18


class StudentIQAHead(nn.Module):
    """Single head for quality issue detection (student version).

    Identical structure to teacher's IQAHead for compatibility during distillation.

    Args:
        in_features: Number of input features from backbone (512 for ResNet-18)
        hidden_features: Number of hidden layer features (default: 256, smaller than teacher)
        dropout: Dropout probability (default: 0.2)
        head_name: Name of this head for logging/debugging
    """

    def __init__(
        self,
        in_features: int,
        hidden_features: int = 256,
        dropout: float = 0.2,
        head_name: str = "unknown",
    ) -> None:
        super().__init__()

        self.head_name = head_name

        # Classification branch: predicts presence/absence of issue
        self.classifier = nn.Sequential(
            nn.Linear(in_features, hidden_features),
            nn.BatchNorm1d(hidden_features),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_features, 1),  # Binary classification logit
        )

        # Confidence branch: predicts confidence score
        self.confidence_head = nn.Sequential(
            nn.Linear(in_features, hidden_features),
            nn.BatchNorm1d(hidden_features),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_features, 1),
            nn.Sigmoid(),  # Confidence between 0 and 1
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through the head.

        Args:
            x: Feature tensor of shape (batch_size, in_features)

        Returns:
            Dictionary with:
                - logits: Classification logits (batch_size, 1)
                - confidence: Confidence scores (batch_size, 1)
        """
        logits = self.classifier(x)
        confidence = self.confidence_head(x)
        return {"logits": logits, "confidence": confidence}


class ResNetStudent(nn.Module):
    """ResNet-18 Student Model for multi-head IQA classification.

    This lightweight model is trained via knowledge distillation from the
    ResNet-50 teacher model. It provides faster inference suitable for
    production deployment while maintaining acceptable accuracy.

    Args:
        num_heads: Number of classification heads (default: 5)
        hidden_features: Hidden layer size for heads (default: 256)
        dropout: Dropout probability (default: 0.2)
        pretrained: Whether to use ImageNet pretrained weights (default: True)

    Attributes:
        ISSUE_TYPES: Class variable listing the quality issue types
        backbone: ResNet-18 feature extractor
        heads: ModuleDict containing the classification heads
    """

    # Quality issue types - must match teacher model
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
        hidden_features: int = 256,
        dropout: float = 0.2,
        pretrained: bool = True,
    ) -> None:
        super().__init__()

        self.num_heads = num_heads
        self.hidden_features = hidden_features
        self.dropout = dropout

        # Validate num_heads
        if num_heads != len(self.ISSUE_TYPES):
            raise ValueError(
                f"num_heads ({num_heads}) must match number of "
                f"ISSUE_TYPES ({len(self.ISSUE_TYPES)})"
            )

        # Load pretrained ResNet-18 backbone
        if pretrained:
            weights = ResNet18_Weights.IMAGENET1K_V1
            base_model = resnet18(weights=weights)
        else:
            base_model = resnet18(weights=None)

        # Extract backbone layers (everything except final FC)
        # ResNet-18 output features: 512 (vs 2048 for ResNet-50)
        self.backbone = nn.Sequential(
            base_model.conv1,
            base_model.bn1,
            base_model.relu,
            base_model.maxpool,
            base_model.layer1,
            base_model.layer2,
            base_model.layer3,
            base_model.layer4,
        )

        # Global average pooling
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))

        # Feature dimension from ResNet-18
        self.feature_dim = 512

        # Create classification heads (one per issue type)
        self.heads = nn.ModuleDict(
            {
                issue_type: StudentIQAHead(
                    in_features=self.feature_dim,
                    hidden_features=hidden_features,
                    dropout=dropout,
                    head_name=issue_type,
                )
                for issue_type in self.ISSUE_TYPES
            }
        )

    def forward(self, x: torch.Tensor) -> dict[str, dict[str, torch.Tensor]]:
        """Forward pass through the model.

        Args:
            x: Input tensor of shape (batch_size, 3, H, W)
               Expected input: 224x224 RGB images, normalized

        Returns:
            Dictionary mapping issue types to their predictions:
            {
                "blur": {"logits": tensor, "confidence": tensor},
                "noise": {"logits": tensor, "confidence": tensor},
                ...
            }
        """
        # Extract features through backbone
        features = self.backbone(x)

        # Global average pooling: (B, 512, H, W) -> (B, 512, 1, 1)
        features = self.global_pool(features)

        # Flatten: (B, 512, 1, 1) -> (B, 512)
        features = features.view(features.size(0), -1)

        # Pass through each head
        outputs = {}
        for issue_type, head in self.heads.items():
            outputs[issue_type] = head(features)

        return outputs

    def get_feature_extractor(self) -> nn.Module:
        """Get the backbone feature extractor.

        Returns:
            Sequential module containing backbone + pooling
        """
        return nn.Sequential(self.backbone, self.global_pool, nn.Flatten())

    def freeze_backbone(self) -> None:
        """Freeze backbone weights for fine-tuning heads only."""
        for param in self.backbone.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self) -> None:
        """Unfreeze backbone weights for full fine-tuning."""
        for param in self.backbone.parameters():
            param.requires_grad = True

    def count_parameters(self) -> dict[str, int]:
        """Count model parameters.

        Returns:
            Dictionary with parameter counts for backbone and heads
        """
        backbone_params = sum(p.numel() for p in self.backbone.parameters())
        head_params = sum(p.numel() for p in self.heads.parameters())
        total_params = sum(p.numel() for p in self.parameters())

        return {
            "backbone": backbone_params,
            "heads": head_params,
            "total": total_params,
            "trainable": sum(p.numel() for p in self.parameters() if p.requires_grad),
        }

    @classmethod
    def from_teacher_config(
        cls,
        teacher_model: nn.Module,
        hidden_features: int = 256,
        dropout: float | None = None,
    ) -> "ResNetStudent":
        """Create student model with configuration matching teacher.

        Args:
            teacher_model: Teacher model to match configuration with
            hidden_features: Hidden layer size (default: 256, smaller than teacher)
            dropout: Dropout rate (default: use teacher's dropout)

        Returns:
            ResNetStudent instance configured to match teacher
        """
        if dropout is None:
            # Try to get dropout from teacher, ensure it's a float
            dropout = float(getattr(teacher_model, "dropout", 0.2))

        return cls(
            num_heads=len(cls.ISSUE_TYPES),
            hidden_features=hidden_features,
            dropout=dropout,
            pretrained=True,
        )
