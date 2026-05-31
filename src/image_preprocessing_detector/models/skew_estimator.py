"""Unified SkewNet model: MobileNetV4-Conv-S with 3 heads for deskew.

Architecture (4-model consensus: Gemini 2.5 Pro, Gemini 3 Pro Preview,
DeepSeek R1, Grok 4):

    Document Image (384x384)
        |
    [MobileNetV4-Conv-S Backbone] (~5M params)
        |
        +---> Head 1: Orientation (4-class: 0/90/180/270)
        |
        +---> Head 2: Skew Bins (42-class, non-uniform)
        |
        +---> Head 3: Skew Regression (residual + uncertainty)

Inference: bin_center + residual = final angle.
Training: QAT starts at epoch 30 for INT8 ONNX export.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    import numpy as np
    import torch
    import torch.nn as nn

    from image_preprocessing_detector.models.onnx_runtime import ONNXModelRunner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Non-uniform bin configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BinZone:
    """One contiguous zone of uniform-width bins.

    Attributes:
        name (str): Human-readable zone name.
        start (float): Left edge of the zone in degrees.
        end (float): Right edge of the zone in degrees.
        width (float): Width of each bin in degrees.
        count (int): Number of bins in this zone.
    """

    name: str
    start: float
    end: float
    width: float
    count: int


@dataclass(frozen=True)
class BinConfig:
    """Full non-uniform bin layout built from config YAML.

    The bins are ordered from most-negative to most-positive:
        extreme_neg | moderate_neg | critical | moderate_pos | extreme_pos

    Attributes:
        zones (tuple[BinZone, ...]): Ordered list of bin zones (neg-to-pos).
        total_bins (int): Sum of all zone counts (must equal 42 by default).
        centers (tuple[float, ...]): Precomputed center of every bin, indexed 0..total_bins-1.
        half_widths (tuple[float, ...]): Per-bin half-widths for residual clamping.
        max_residual (float): Legacy global max residual (use half_widths instead).
    """

    zones: tuple[BinZone, ...]
    total_bins: int
    centers: tuple[float, ...]
    half_widths: tuple[float, ...]
    max_residual: float

    @staticmethod
    def from_yaml(config_path: str | Path | None = None) -> BinConfig:
        """Build BinConfig from the skew_estimation.yaml config file.

        Args:
            config_path (str | Path | None): Path to config YAML. If None, uses default location.

        Returns:
            BinConfig: Populated BinConfig with precomputed bin centers.
        """
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parents[3] / "config" / "skew_estimation.yaml"
            )
        else:
            config_path = Path(config_path)

        with config_path.open() as f:
            cfg = yaml.safe_load(f)

        skew_cfg = cfg["skew"]
        raw_zones = skew_cfg["bins"]

        # Sort zones by start angle (ascending) so bins go neg -> pos
        sorted_zones = sorted(raw_zones, key=lambda z: z["start"])

        zones: list[BinZone] = []
        centers: list[float] = []
        half_widths: list[float] = []

        for z in sorted_zones:
            zone = BinZone(
                name=z["zone"],
                start=z["start"],
                end=z["end"],
                width=z["width"],
                count=z["count"],
            )
            zones.append(zone)

            for i in range(zone.count):
                center = zone.start + (i + 0.5) * zone.width
                centers.append(round(center, 4))
                half_widths.append(zone.width / 2.0)

        total = sum(z.count for z in zones)
        max_residual = float(skew_cfg["regression"]["max_residual"])

        return BinConfig(
            zones=tuple(zones),
            total_bins=total,
            centers=tuple(centers),
            half_widths=tuple(half_widths),
            max_residual=max_residual,
        )

    def angle_to_bin(self, angle: float) -> int:
        """Map a continuous angle to the nearest bin index.

        Args:
            angle (float): Skew angle in degrees.

        Returns:
            int: Bin index (0-based).
        """
        best_idx = 0
        best_dist = float("inf")
        for i, c in enumerate(self.centers):
            dist = abs(angle - c)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def bin_to_angle(self, bin_idx: int, residual: float = 0.0) -> float:
        """Convert bin index + regression residual to a continuous angle.

        Uses per-bin half-width clamping: critical bins (0.5 deg width) clamp
        to +/-0.25, moderate bins (2.0 deg) to +/-1.0, extreme bins (5.0 deg)
        to +/-2.5.

        Args:
            bin_idx (int): Bin index (0-based).
            residual (float): Regression residual in degrees, clamped per-bin.

        Returns:
            float: Final angle in degrees.
        """
        hw = self.half_widths[bin_idx]
        clamped = max(-hw, min(hw, residual))
        return self.centers[bin_idx] + clamped


# ---------------------------------------------------------------------------
# Model output dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkewEstimation:
    """Output of the SkewNet model for a single image.

    Attributes:
        orientation_class (int): Predicted orientation (0, 90, 180, 270 degrees).
        orientation_confidence (float): Softmax confidence for orientation.
        skew_bin (int): Predicted bin index (0..41).
        skew_bin_confidence (float): Softmax max probability for bin classification.
        skew_residual (float): Fine regression residual in degrees.
        skew_uncertainty (float): Predicted variance (sigma_sq) from GaussianNLL.
        final_angle (float): Combined angle = bin_center + residual.
    """

    orientation_class: int
    orientation_confidence: float
    skew_bin: int
    skew_bin_confidence: float
    skew_residual: float
    skew_uncertainty: float
    final_angle: float


# ---------------------------------------------------------------------------
# PyTorch model definition (for training)
# ---------------------------------------------------------------------------


def _build_skew_estimator(
    backbone_name: str = "mobilenetv4_conv_small",
    pretrained: bool = True,
    num_orientation_classes: int = 4,
    num_skew_bins: int = 42,
    predict_uncertainty: bool = True,
) -> nn.Module:
    """Build the unified 3-head SkewNet model using timm backbone.

    This function is called during training. For inference, use
    ONNXModelRunner with the exported ONNX model.

    Args:
        backbone_name (str): timm model name for the backbone.
        pretrained (bool): Whether to load ImageNet pretrained weights.
        num_orientation_classes (int): Number of orientation classes (default 4).
        num_skew_bins (int): Number of non-uniform skew bins (default 42).
        predict_uncertainty (bool): If True, regression head outputs (mu, sigma_sq).

    Returns:
        nn.Module: nn.Module with 3 output heads.
    """
    import timm
    import torch.nn as nn

    class SkewEstimatorNet(nn.Module):
        """Unified 3-head deskew model.

        Forward pass returns a dict with:
            orientation_logits: [B, num_orientation_classes]
            skew_bin_logits: [B, num_skew_bins]
            skew_regression: [B, 2] if uncertainty else [B, 1]
        """

        def __init__(self) -> None:
            super().__init__()

            # Backbone: MobileNetV4-Conv-S features
            self.backbone = timm.create_model(
                backbone_name,
                pretrained=pretrained,
                num_classes=0,  # Remove default classifier
                global_pool="avg",
            )
            feature_dim: int = int(self.backbone.num_features)  # type: ignore[arg-type]  # timm stubs type as Tensor|Module but is int at runtime

            # Head 1: Orientation classification
            self.orientation_head = nn.Sequential(
                nn.Dropout(p=0.2),
                nn.Linear(feature_dim, num_orientation_classes),
            )

            # Head 2: Skew bin classification (non-uniform)
            self.skew_bin_head = nn.Sequential(
                nn.Dropout(p=0.2),
                nn.Linear(feature_dim, num_skew_bins),
            )

            # Head 3: Skew regression (residual within bin)
            regression_out = 2 if predict_uncertainty else 1
            self.skew_regression_head = nn.Sequential(
                nn.Dropout(p=0.1),
                nn.Linear(feature_dim, 128),
                nn.ReLU(inplace=True),
                nn.Linear(128, regression_out),
            )

            self._predict_uncertainty = predict_uncertainty

        def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
            """Forward pass through backbone and all 3 heads.

            Args:
                x (torch.Tensor): Input tensor [B, 3, H, W].

            Returns:
                dict[str, torch.Tensor]: Dict with orientation_logits, skew_bin_logits,
                skew_regression tensors.
            """
            features = self.backbone(x)

            orientation_logits = self.orientation_head(features)
            skew_bin_logits = self.skew_bin_head(features)
            skew_regression = self.skew_regression_head(features)

            return {
                "orientation_logits": orientation_logits,
                "skew_bin_logits": skew_bin_logits,
                "skew_regression": skew_regression,
            }

    return SkewEstimatorNet()


# ---------------------------------------------------------------------------
# Loss computation
# ---------------------------------------------------------------------------


def compute_skew_loss(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    bin_config: BinConfig,
    loss_weights: dict[str, float] | None = None,
    critical_zone_weight: float = 2.0,
) -> torch.Tensor:
    """Compute multi-task loss for SkewNet training.

    Args:
        outputs (dict[str, torch.Tensor]): Model outputs dict from forward pass.
        targets (dict[str, torch.Tensor]): Dict with keys:
            orientation_labels: [B] long tensor (0-3)
            skew_bin_labels: [B] long tensor (0-41)
            skew_angle_labels: [B] float tensor (ground truth angle)
        bin_config (BinConfig): Non-uniform bin configuration.
        loss_weights (dict[str, float] | None): Dict with orientation, skew_classification,
            skew_regression weights. Defaults to plan values.
        critical_zone_weight (float): Extra weight for samples in |angle| < 2 deg.

    Returns:
        torch.Tensor: Weighted total loss scalar.
    """
    import torch
    import torch.nn.functional as functional

    if loss_weights is None:
        loss_weights = {
            "orientation": 0.2,
            "skew_classification": 0.3,
            "skew_regression": 0.5,
        }

    # Loss 1: Orientation CE
    orientation_loss = functional.cross_entropy(
        outputs["orientation_logits"],
        targets["orientation_labels"],
    )

    # Loss 2: Skew bin CE
    skew_bin_loss = functional.cross_entropy(
        outputs["skew_bin_logits"],
        targets["skew_bin_labels"],
    )

    # Loss 3: Skew regression (residual within bin)
    # Compute target residual = gt_angle - bin_center[gt_bin]
    gt_bins = targets["skew_bin_labels"]
    gt_angles = targets["skew_angle_labels"]

    bin_centers_tensor = torch.tensor(
        bin_config.centers,
        dtype=gt_angles.dtype,
        device=gt_angles.device,
    )
    gt_bin_centers = bin_centers_tensor[gt_bins]
    target_residuals = gt_angles - gt_bin_centers

    regression_out = outputs["skew_regression"]

    pred_mu = regression_out[:, 0]
    uncertainty_mode = regression_out.shape[-1] == 2

    # Gaussian reweighting for critical zone (|angle| < 2 deg)
    # Apply higher weight to samples where |gt_angle| < 2
    with torch.no_grad():
        sample_weights = torch.ones_like(gt_angles)
        critical_mask = gt_angles.abs() < 2.0
        sample_weights[critical_mask] = critical_zone_weight

    # Re-weight the regression loss
    if uncertainty_mode:
        pred_log_var = regression_out[:, 1]
        per_sample = 0.5 * (
            pred_log_var
            + (target_residuals - pred_mu) ** 2 / (pred_log_var.exp() + 1e-6)
        )
    else:
        per_sample = functional.smooth_l1_loss(
            pred_mu, target_residuals, reduction="none"
        )

    weighted_regression = (per_sample * sample_weights).mean()

    return (
        loss_weights["orientation"] * orientation_loss
        + loss_weights["skew_classification"] * skew_bin_loss
        + loss_weights["skew_regression"] * weighted_regression
    )


# ---------------------------------------------------------------------------
# ONNX export utility
# ---------------------------------------------------------------------------


def export_to_onnx(
    model: nn.Module,
    output_path: str | Path,
    input_size: int = 384,
    opset_version: int = 17,
) -> Path:
    """Export trained SkewNet to ONNX format.

    Args:
        model (nn.Module): Trained SkewEstimatorNet model (on CPU).
        output_path (str | Path): Destination ONNX file path.
        input_size (int): Input spatial dimension (default 384).
        opset_version (int): ONNX opset version (default 17).

    Returns:
        Path: Path to the exported ONNX file.
    """
    import torch

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model.eval()
    dummy_input = torch.randn(1, 3, input_size, input_size)

    torch.onnx.export(
        model,
        (dummy_input,),
        str(output_path),
        opset_version=opset_version,
        input_names=["input"],
        output_names=[
            "orientation_logits",
            "skew_bin_logits",
            "skew_regression",
        ],
        dynamic_axes={
            "input": {0: "batch_size"},
            "orientation_logits": {0: "batch_size"},
            "skew_bin_logits": {0: "batch_size"},
            "skew_regression": {0: "batch_size"},
        },
    )

    logger.info("ONNX model exported to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# ONNX inference wrapper (decode raw ONNX outputs)
# ---------------------------------------------------------------------------


@dataclass
class SkewEstimatorInference:
    """High-level inference wrapper that decodes ONNX outputs into SkewEstimation.

    Uses ONNXModelRunner for the actual ONNX Runtime session and adds
    pre/post-processing (resize, normalize, softmax, bin→angle decode).

    Attributes:
        model_path (Path): Path to the ONNX model file.
        bin_config (BinConfig): Non-uniform bin configuration.
        input_size (int): Input spatial dimension (default 384).
        orientation_classes (tuple[int, ...]): Orientation angle values (default: [0, 90, 180, 270]).
    """

    model_path: Path
    bin_config: BinConfig = field(default_factory=BinConfig.from_yaml)
    input_size: int = 384
    orientation_classes: tuple[int, ...] = (0, 90, 180, 270)
    _runner: ONNXModelRunner | None = field(default=None, init=False, repr=False)

    def _ensure_runner(self) -> ONNXModelRunner:
        """Lazily initialize the ONNX model runner.

        Returns:
            ONNXModelRunner: Active ONNXModelRunner instance.
        """
        if self._runner is not None:
            return self._runner

        from image_preprocessing_detector.models.onnx_runtime import (
            ONNXModelRunner,
            ONNXSessionConfig,
        )

        config = ONNXSessionConfig()
        self._runner = ONNXModelRunner(model_path=self.model_path, config=config)
        return self._runner

    def predict(self, image: np.ndarray) -> SkewEstimation:
        """Run inference on a single image.

        Args:
            image (np.ndarray): Input image (BGR uint8 from OpenCV, any size).

        Returns:
            SkewEstimation: SkewEstimation with orientation, skew angle, and uncertainty.
        """
        import numpy as np

        input_tensor = self._preprocess(image)
        runner = self._ensure_runner()
        outputs = runner.run(input_tensor)

        # Unpack the three output heads from ONNX inference
        orientation_logits = outputs[0][0]
        skew_bin_logits = outputs[1][0]
        skew_regression = outputs[2][0]

        # Softmax for orientation
        orientation_probs = _softmax(orientation_logits)
        orientation_idx = int(np.argmax(orientation_probs))
        orientation_conf = float(orientation_probs[orientation_idx])

        # Softmax for skew bins
        skew_bin_probs = _softmax(skew_bin_logits)
        skew_bin_idx = int(np.argmax(skew_bin_probs))
        skew_bin_conf = float(skew_bin_probs[skew_bin_idx])

        # Regression residual and uncertainty
        residual = float(skew_regression[0])
        uncertainty = (
            float(math.exp(skew_regression[1])) if len(skew_regression) > 1 else 0.0
        )

        # Decode final angle
        final_angle = self.bin_config.bin_to_angle(skew_bin_idx, residual)

        return SkewEstimation(
            orientation_class=self.orientation_classes[orientation_idx],
            orientation_confidence=orientation_conf,
            skew_bin=skew_bin_idx,
            skew_bin_confidence=skew_bin_conf,
            skew_residual=residual,
            skew_uncertainty=uncertainty,
            final_angle=final_angle,
        )

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize and normalize image to model input format.

        Args:
            image (np.ndarray): BGR uint8 image of any size.

        Returns:
            np.ndarray: Float32 tensor [1, 3, H, W] normalized with ImageNet stats.
        """
        import cv2
        import numpy as np

        sz = self.input_size
        resized = cv2.resize(image, (sz, sz), interpolation=cv2.INTER_LINEAR)

        # BGR -> RGB, uint8 -> float32 [0,1]
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (rgb - mean) / std

        # HWC -> CHW, add batch dim
        tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
        return tensor.astype(np.float32)

    def close(self) -> None:
        """Release the ONNX session."""
        if self._runner is not None:
            self._runner.close()
            self._runner = None


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax over a 1-D array.

    Args:
        logits (np.ndarray): Raw logit values.

    Returns:
        np.ndarray: Probability distribution summing to 1.
    """
    import numpy as np

    shifted = logits - np.max(logits)
    exp_vals = np.exp(shifted)
    result: np.ndarray = exp_vals / np.sum(exp_vals)
    return result
