"""Test MANIQA model inference to diagnose prediction issue."""

import subprocess

import pyiqa
import torch
import torch.nn as nn
from einops import rearrange
from PIL import Image
from torchvision import transforms

# Download a test image
subprocess.run(
    [
        "gsutil",
        "cp",
        "gs://assured-oss-457903-diqa5000/test/res/01_ANMCRB.jpg",
        "/tmp/test_image.jpg",
    ],
    check=True,
    capture_output=True,
)


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

        feature_dim = 384

        self._captured_features: torch.Tensor | None = None

        def _capture_hook(
            _module: nn.Module, _input: tuple, output: torch.Tensor
        ) -> None:
            h = self.backbone.input_size
            x = self._rearrange(output, "b c h w -> b (h w) c", h=h, w=h)
            self._captured_features = x.mean(dim=1)

        self._hook_handle = self.backbone.swintransformer2.register_forward_hook(
            _capture_hook
        )

        self.head = nn.Sequential(
            nn.Linear(feature_dim, head_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
            nn.Linear(head_hidden_dim, head_hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
        )

        self.overall_head = nn.Linear(head_hidden_dim // 2, 1)
        self.sharpness_head = nn.Linear(head_hidden_dim // 2, 1)
        self.color_head = nn.Linear(head_hidden_dim // 2, 1)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        _ = self.backbone(x)
        features = self._captured_features
        assert features is not None
        shared_features = self.head(features)
        overall = torch.sigmoid(self.overall_head(shared_features)).squeeze(-1)
        sharpness = torch.sigmoid(self.sharpness_head(shared_features)).squeeze(-1)
        color = torch.sigmoid(self.color_head(shared_features)).squeeze(-1)
        return {
            "overall": overall,
            "sharpness": sharpness,
            "color": color,
        }


# Create and load model
print("Loading model...")
model = MANIQAMultiTask()
checkpoint = torch.load(
    "/tmp/maniqa_checkpoint.pt", map_location="cpu", weights_only=False
)
model.load_state_dict(checkpoint["model_state_dict"], strict=False)
model.eval()

# Load and preprocess image
print("\nLoading test image...")
image = Image.open("/tmp/test_image.jpg").convert("RGB")
preprocess = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)
input_tensor = preprocess(image).unsqueeze(0)

# Run inference
print("\nRunning inference...")
with torch.inference_mode():
    outputs = model(input_tensor)

print("\nRaw model outputs (sigmoid, [0, 1] range):")
print(f"  overall:   {outputs['overall'].item():.4f}")
print(f"  sharpness: {outputs['sharpness'].item():.4f}")
print(f"  color:     {outputs['color'].item():.4f}")

print("\nScaled to [1, 5] range (× 4.0 + 1.0):")
print(f"  overall:   {outputs['overall'].item() * 4.0 + 1.0:.4f}")
print(f"  sharpness: {outputs['sharpness'].item() * 4.0 + 1.0:.4f}")
print(f"  color:     {outputs['color'].item() * 4.0 + 1.0:.4f}")

# Check if outputs are reasonable
if all(0.0 <= outputs[k].item() <= 1.0 for k in ["overall", "sharpness", "color"]):
    print("\n✓ Outputs are in valid [0, 1] range")
else:
    print("\n✗ WARNING: Outputs are outside [0, 1] range!")
