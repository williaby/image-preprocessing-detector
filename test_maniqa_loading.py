"""Test script to diagnose MANIQA model loading issue."""

import pyiqa
import torch
import torch.nn as nn
from einops import rearrange


class MANIQAMultiTask(nn.Module):
    """MANIQA wrapper with multi-task head for DIQA training."""

    def __init__(
        self,
        freeze_backbone: bool = False,
        head_hidden_dim: int = 384,
        head_dropout: float = 0.1,
    ) -> None:
        super().__init__()

        # Load pretrained MANIQA backbone
        metric = pyiqa.create_metric("maniqa", device="cpu", as_loss=True)
        self.backbone = metric.net
        self._rearrange = rearrange

        # Force single crop mode
        self.backbone.test_sample = 1

        feature_dim = 384  # MANIQA TABlock output dimension

        # Store captured features from hook
        self._captured_features: torch.Tensor | None = None

        # Register hook to capture features after swintransformer2
        def _capture_hook(
            _module: nn.Module, _input: tuple, output: torch.Tensor
        ) -> None:
            h = self.backbone.input_size  # 28
            x = self._rearrange(output, "b c h w -> b (h w) c", h=h, w=h)
            self._captured_features = x.mean(dim=1)  # [B, 384]

        self._hook_handle = self.backbone.swintransformer2.register_forward_hook(
            _capture_hook
        )

        # Multi-task head (shared layers)
        self.head = nn.Sequential(
            nn.Linear(feature_dim, head_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
            nn.Linear(head_hidden_dim, head_hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
        )

        # Dimension-specific output heads
        self.overall_head = nn.Linear(head_hidden_dim // 2, 1)
        self.sharpness_head = nn.Linear(head_hidden_dim // 2, 1)
        self.color_head = nn.Linear(head_hidden_dim // 2, 1)

        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False


# Create model
print("Creating model...")
model = MANIQAMultiTask()

# Load checkpoint
print("\nLoading checkpoint...")
checkpoint = torch.load(
    "/tmp/maniqa_checkpoint.pt", map_location="cpu", weights_only=False
)
state_dict = checkpoint["model_state_dict"]

# Get model's current state dict keys
model_keys = set(model.state_dict().keys())
checkpoint_keys = set(state_dict.keys())

# Find missing and unexpected keys
missing_keys = model_keys - checkpoint_keys
unexpected_keys = checkpoint_keys - model_keys

print(f"\nTotal model keys: {len(model_keys)}")
print(f"Total checkpoint keys: {len(checkpoint_keys)}")
print(f"\nMissing keys (in model but not checkpoint): {len(missing_keys)}")
if missing_keys and len(missing_keys) < 20:
    for key in sorted(missing_keys):
        print(f"  - {key}")

print(f"\nUnexpected keys (in checkpoint but not model): {len(unexpected_keys)}")
if unexpected_keys and len(unexpected_keys) < 20:
    for key in sorted(unexpected_keys):
        print(f"  - {key}")

# Try loading
print("\nAttempting to load state dict (strict=False)...")
result = model.load_state_dict(state_dict, strict=False)
print(f"Missing keys from load_state_dict: {len(result.missing_keys)}")
print(f"Unexpected keys from load_state_dict: {len(result.unexpected_keys)}")

# Check if head weights were loaded
print("\nChecking head weights:")
print(f"overall_head.weight loaded: {'overall_head.weight' in state_dict}")
print(f"sharpness_head.weight loaded: {'sharpness_head.weight' in state_dict}")
print(f"color_head.weight loaded: {'color_head.weight' in state_dict}")
