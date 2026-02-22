"""Train SigLIP 2 Multi-Task Teacher for Document Analysis.

Extends the SigLIP2-IQA model (86M params) with five new detection heads
for multi-task document analysis: script detection, document source classification,
orientation detection, shadow severity, and warping severity.

Architecture:
    SigLIP2 ViT-B/16 (768-dim shared features) → 8 task heads
    - IQA (existing): overall, sharpness, color (regression w/ uncertainty)
    - Classification (new): script (19-class), source (3-class), orientation (4-class)
    - Regression (new): shadow, warping (w/ uncertainty)

Training Strategy:
    Phase 1 (frozen backbone): Train only new detection heads (IQA heads frozen)
    Phase 2 (optional): Unfreeze backbone with low LR, PCGrad for gradient surgery

Reference:
    - IQA base: modal/train_siglip2_iqa_v2.py
    - Plan: docs/planning/STREAM_4_IMPLEMENTATION_PLAN.md
    - Requirements: docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md

Usage:
    # Quick test (2 epochs, synthetic data)
    uv run modal run modal/train_siglip2_multitask.py --test

    # Phase 1 training (frozen backbone, new heads only)
    uv run modal run --detach modal/train_siglip2_multitask.py --phase 1 --epochs 15

    # Full training (both phases)
    uv run modal run --detach modal/train_siglip2_multitask.py

    # Monitor logs
    modal app logs siglip2-multitask-training --follow
"""

from __future__ import annotations

import base64
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import modal

# ============================================================================
# Modal infrastructure
# ============================================================================

app = modal.App("siglip2-multitask-training")

# Persistent volumes
results_volume = modal.Volume.from_name(
    "siglip2-multitask-results", create_if_missing=True
)
datasets_volume = modal.Volume.from_name("multitask-datasets", create_if_missing=True)

# GCS bucket for dataset storage
GCS_BUCKET = "image_detection_b"

# Docker image with all ML dependencies
training_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        # Core ML
        "torch==2.5.1",
        "torchvision==0.20.1",
        "numpy<2.0",
        "Pillow>=11.0.0",
        # SigLIP 2 support
        "transformers>=4.51.0",
        "accelerate>=1.0.0",
        # Statistics
        "scipy",
        "scikit-learn",
        # Utilities
        "tqdm",
        "pydantic>=2.0",
        "pyyaml",
        # GCS access
        "google-cloud-storage>=2.10.0",
        # Experiment tracking
        "wandb",
    )
)

# ============================================================================
# Constants and task definitions
# ============================================================================

# Model variants
MODEL_VARIANTS = {
    "base": "google/siglip2-base-patch16-naflex",  # 86M backbone
    "so400m": "google/siglip2-so400m-patch16-naflex",  # 400M backbone
}

# Script ML classes (matches config/script_ml_classes.yaml exactly)
SCRIPT_ML_CLASSES = (
    "LATN",
    "CYRL",
    "GREK",
    "ARAB",
    "HEBR",
    "DEVA",
    "BENG",
    "TAML",
    "TELU",
    "HANS",
    "HANT",
    "JPAN",
    "KORE",
    "THAI",
    "TIBT",
    "INDIC_OTHER",
    "SE_ASIAN_OTHER",
    "OTHER",
    "UNKNOWN",
)

# Reverse lookup: class name → index
SCRIPT_CLASS_TO_IDX = {cls: i for i, cls in enumerate(SCRIPT_ML_CLASSES)}

# Source classes (matches CaptureMethod enum)
SOURCE_CLASSES = ("scanned", "camera", "born_digital")
SOURCE_CLASS_TO_IDX = {cls: i for i, cls in enumerate(SOURCE_CLASSES)}

# Orientation classes (degrees)
ORIENTATION_CLASSES = (0, 90, 180, 270)
ORIENTATION_TO_IDX = {deg: i for i, deg in enumerate(ORIENTATION_CLASSES)}

# IQA quality dimensions (must match train_siglip2_iqa_v2.py)
IQA_DIMENSIONS = ("overall", "sharpness", "color")

# Task group definitions
IQA_TASKS = IQA_DIMENSIONS
CLASSIFICATION_TASKS = ("script", "source", "orientation")
REGRESSION_TASKS = ("shadow", "warping")
ALL_TASKS = IQA_TASKS + CLASSIFICATION_TASKS + REGRESSION_TASKS

# Head architecture configurations
HEAD_CONFIGS: dict[str, dict[str, Any]] = {
    # IQA heads (existing): 768→256→ReLU→Dropout(0.3)→2 [mu, sigma_sq]
    "overall": {
        "hidden_dim": 256,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    "sharpness": {
        "hidden_dim": 256,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    "color": {
        "hidden_dim": 256,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    # Script: 768→256→ReLU→Dropout(0.3)→19 [logits]
    "script": {
        "hidden_dim": 256,
        "output_dim": len(SCRIPT_ML_CLASSES),
        "dropout": 0.3,
        "type": "classification",
    },
    # Source: 768→64→ReLU→3 [logits]
    "source": {
        "hidden_dim": 64,
        "output_dim": len(SOURCE_CLASSES),
        "dropout": 0.0,
        "type": "classification",
    },
    # Orientation: 768→64→ReLU→4 [logits]
    "orientation": {
        "hidden_dim": 64,
        "output_dim": len(ORIENTATION_CLASSES),
        "dropout": 0.0,
        "type": "classification",
    },
    # Shadow: 768→64→ReLU→2 [mu, sigma] (severity regression)
    "shadow": {
        "hidden_dim": 64,
        "output_dim": 2,
        "dropout": 0.0,
        "type": "regression_uncertainty",
    },
    # Warping: 768→64→ReLU→2 [mu, sigma] (severity regression)
    "warping": {
        "hidden_dim": 64,
        "output_dim": 2,
        "dropout": 0.0,
        "type": "regression_uncertainty",
    },
}

# Best model checkpoint filename
_BEST_MODEL_FILENAME = "siglip2_multitask_best.pt"

# ============================================================================
# Training configuration
# ============================================================================


@dataclass
class MultiTaskTrainingConfig:
    """Multi-task teacher training configuration.

    Two-phase training strategy:
    - Phase 1: Frozen backbone + frozen IQA heads → train new detection heads
    - Phase 2: Unfreeze all with differential LR (backbone 0.1x, IQA 0.01x)
    """

    # Model selection
    model_variant: str = "base"
    model_id: str = field(default="", init=False)
    max_num_patches: int = 784

    # Class counts (derived from constants above)
    num_script_classes: int = len(SCRIPT_ML_CLASSES)
    num_source_classes: int = len(SOURCE_CLASSES)
    num_orientation_classes: int = len(ORIENTATION_CLASSES)

    # Phase 1: Frozen backbone, train new heads
    phase1_epochs: int = 15
    phase1_lr: float = 2e-4
    freeze_backbone_phase1: bool = True
    freeze_iqa_phase1: bool = True

    # Phase 2: Unfrozen backbone with low LR
    phase2_epochs: int = 30
    phase2_lr: float = 1e-5
    backbone_lr_multiplier: float = 0.1
    iqa_lr_multiplier: float = 0.01
    run_phase2: bool = True

    # Total epochs (computed from phases)
    total_epochs: int = 45

    # Batch and gradient accumulation
    batch_size: int = 8
    gradient_accumulation_steps: int = 4

    # Learning rate bounds
    min_lr: float = 1e-6

    # LLRD (Layer-wise Learning Rate Decay)
    use_llrd: bool = True
    llrd_decay: float = 0.9

    # Optimizer
    weight_decay: float = 0.01
    gradient_clip: float = 1.0

    # Scheduler
    use_cosine_scheduler: bool = True

    # Multi-task learning
    use_pcgrad: bool = True
    task_weights: dict[str, float] = field(
        default_factory=lambda: {
            "overall": 1.0,
            "sharpness": 1.0,
            "color": 1.0,
            "script": 1.0,
            "source": 0.5,
            "orientation": 0.5,
            "shadow": 0.3,
            "warping": 0.3,
        }
    )

    # EMA (Exponential Moving Average)
    use_ema: bool = True
    ema_decay: float = 0.999
    ema_start_epoch: int = 35

    # Data augmentation (quality-preserving)
    use_augmentation: bool = True
    horizontal_flip_prob: float = 0.5
    random_crop_prob: float = 0.3

    # Early stopping
    early_stopping_patience: int = 20
    save_every_n_epochs: int = 5
    keep_top_k: int = 3

    # Mixed precision
    use_gradient_checkpointing: bool = True
    use_mixed_precision: bool = True
    mixed_precision_dtype: str = "bfloat16"

    # Pretrained IQA checkpoint for initialization
    pretrained_iqa_checkpoint: str | None = None

    # Target metrics (Phase E evaluation thresholds)
    iqa_vquala_floor: float = 0.86
    target_script_accuracy: float = 0.85
    target_orientation_accuracy: float = 0.95
    target_source_accuracy: float = 0.90
    target_shadow_mae: float = 0.12
    target_warping_mae: float = 0.12

    # Output directory
    output_dir: str = "/results/siglip2_multitask"

    # GCS dataset prefixes
    gcs_script_prefix: str = "datasets/script_training"
    gcs_source_prefix: str = "datasets/source_training"
    gcs_orientation_prefix: str = "datasets/orientation_training"
    gcs_shadow_prefix: str = "datasets/shadow_training"
    gcs_warping_prefix: str = "datasets/warping_training"
    gcs_iqa_prefix: str = "datasets/diqa-5000-original"

    def __post_init__(self) -> None:
        self.model_id = MODEL_VARIANTS.get(self.model_variant, MODEL_VARIANTS["base"])
        self.total_epochs = self.phase1_epochs + (
            self.phase2_epochs if self.run_phase2 else 0
        )
        if self.model_variant == "so400m":
            self.batch_size = 4
            self.gradient_accumulation_steps = 8

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dict for checkpointing."""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


# ============================================================================
# Model
# ============================================================================


def _create_multitask_model(
    model_id: str,
    head_configs: dict[str, dict[str, Any]] | None = None,
    pretrained_iqa_path: str | None = None,
) -> Any:
    """Create SigLIP2MultiTaskTeacher model.

    Classes are defined inside this function for Modal serialization
    (class definitions must be in the same scope as the Modal function).

    Args:
        model_id: HuggingFace model ID for the backbone.
        head_configs: Per-head architecture configs. Defaults to HEAD_CONFIGS.
        pretrained_iqa_path: Path to pretrained IQA v2 checkpoint.

    Returns:
        SigLIP2MultiTaskTeacher model instance.
    """
    import torch
    import torch.nn as nn
    from transformers import AutoModel

    configs = head_configs or HEAD_CONFIGS

    class SigLIP2MultiTaskTeacher(nn.Module):
        """SigLIP2 backbone with multi-task IQA + detection heads.

        Architecture:
            SigLIP2 ViT-B/16 (768-dim) → 8 task heads
            - IQA: overall, sharpness, color (256-dim hidden, uncertainty)
            - Script: 19-class (256-dim hidden, dropout 0.3)
            - Source: 3-class (64-dim hidden)
            - Orientation: 4-class (64-dim hidden)
            - Shadow: regression w/ uncertainty (64-dim hidden)
            - Warping: regression w/ uncertainty (64-dim hidden)

        Total: ~88M params (86M backbone + ~2M heads)
        """

        def __init__(
            self,
            mid: str = "google/siglip2-base-patch16-naflex",
            hconfigs: dict[str, dict[str, Any]] | None = None,
        ) -> None:
            super().__init__()
            self.backbone = AutoModel.from_pretrained(mid)
            embed_dim: int = self.backbone.config.vision_config.hidden_size
            hc = hconfigs or configs

            # All heads in a single ModuleDict for checkpoint compatibility
            # IQA heads (overall, sharpness, color) match train_siglip2_iqa_v2.py keys
            self.heads = nn.ModuleDict()
            self._head_types: dict[str, str] = {}

            for name, cfg in hc.items():
                self.heads[name] = self._make_head(
                    embed_dim,
                    cfg["hidden_dim"],
                    cfg["output_dim"],
                    cfg.get("dropout", 0.0),
                )
                self._head_types[name] = cfg["type"]

            # Calibration temperature buffers for uncertainty heads
            for name, cfg in hc.items():
                if cfg["type"] == "regression_uncertainty":
                    self.register_buffer(f"temp_{name}", torch.tensor(1.0))

            # Xavier init for NEW heads (non-IQA); IQA heads get loaded from checkpoint
            for name in CLASSIFICATION_TASKS + REGRESSION_TASKS:
                if name in self.heads:
                    self._xavier_init_module(self.heads[name])

        @staticmethod
        def _make_head(
            in_dim: int,
            hidden_dim: int,
            out_dim: int,
            dropout: float = 0.0,
        ) -> nn.Module:
            """Build a task head: Linear→ReLU→[Dropout]→Linear."""
            layers: list[nn.Module] = [
                nn.Linear(in_dim, hidden_dim),
                nn.ReLU(),
            ]
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            layers.append(nn.Linear(hidden_dim, out_dim))
            return nn.Sequential(*layers)

        @staticmethod
        def _xavier_init_module(module: nn.Module) -> None:
            """Apply Xavier uniform initialization to Linear layers."""
            for m in module.modules():
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    if m.bias is not None:
                        nn.init.zeros_(m.bias)

        def load_iqa_checkpoint(self, path: str) -> None:
            """Load pretrained IQA backbone + heads from v2 checkpoint.

            Loads backbone weights and IQA heads (overall, sharpness, color).
            New detection heads retain their Xavier initialization.
            Uses strict=False so new head keys are simply missing (not errors).

            Args:
                path: Path to v2 IQA checkpoint file.
            """
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            state_dict = ckpt.get("model_state_dict", ckpt)
            missing, unexpected = self.load_state_dict(state_dict, strict=False)

            loaded_backbone = sum(1 for k in state_dict if k.startswith("backbone."))
            loaded_heads = sum(1 for k in state_dict if k.startswith("heads."))

            print(
                f"IQA checkpoint loaded: {loaded_backbone} backbone keys, "
                f"{loaded_heads} head keys"
            )
            print(f"Missing keys (new heads, expected): {len(missing)}")
            if unexpected:
                print(f"Unexpected keys: {len(unexpected)}")

        def freeze_backbone(self) -> None:
            """Freeze all backbone parameters."""
            for param in self.backbone.parameters():
                param.requires_grad = False

        def unfreeze_backbone(self) -> None:
            """Unfreeze all backbone parameters."""
            for param in self.backbone.parameters():
                param.requires_grad = True

        def freeze_iqa_heads(self) -> None:
            """Freeze IQA heads to protect existing performance."""
            for task in IQA_TASKS:
                if task in self.heads:
                    for param in self.heads[task].parameters():
                        param.requires_grad = False

        def unfreeze_iqa_heads(self) -> None:
            """Unfreeze IQA heads for joint fine-tuning."""
            for task in IQA_TASKS:
                if task in self.heads:
                    for param in self.heads[task].parameters():
                        param.requires_grad = True

        def get_layer_groups(self) -> list[list[nn.Parameter]]:
            """Get backbone parameter groups for LLRD.

            Returns layers from deepest (earliest) to shallowest (latest),
            matching the order expected by _get_llrd_param_groups.
            """
            encoder = self.backbone.vision_model.encoder
            groups: list[list[nn.Parameter]] = []
            groups.append(list(self.backbone.vision_model.embeddings.parameters()))
            for layer in encoder.layers:
                groups.append(list(layer.parameters()))
            groups.append(list(self.backbone.vision_model.post_layernorm.parameters()))
            return groups

        def get_head_param_groups(
            self,
            base_lr: float,
            iqa_lr_multiplier: float = 0.01,
            weight_decay: float = 0.01,
        ) -> list[dict[str, Any]]:
            """Get head parameter groups with differential LR.

            IQA heads get base_lr * iqa_lr_multiplier (protect IQA perf).
            New detection heads get full base_lr.

            Args:
                base_lr: Base learning rate for new heads.
                iqa_lr_multiplier: LR multiplier for IQA heads.
                weight_decay: Weight decay for all head params.

            Returns:
                List of optimizer param group dicts.
            """
            groups: list[dict[str, Any]] = []

            # IQA heads: reduced LR to protect existing performance
            iqa_params: list[nn.Parameter] = []
            for task in IQA_TASKS:
                if task in self.heads:
                    iqa_params.extend(self.heads[task].parameters())
            if iqa_params:
                groups.append(
                    {
                        "params": iqa_params,
                        "lr": base_lr * iqa_lr_multiplier,
                        "weight_decay": weight_decay,
                        "name": "iqa_heads",
                    }
                )

            # New detection heads: full base LR
            detection_params: list[nn.Parameter] = []
            for task in CLASSIFICATION_TASKS + REGRESSION_TASKS:
                if task in self.heads:
                    detection_params.extend(self.heads[task].parameters())
            if detection_params:
                groups.append(
                    {
                        "params": detection_params,
                        "lr": base_lr,
                        "weight_decay": weight_decay,
                        "name": "detection_heads",
                    }
                )

            return groups

        def forward(
            self,
            pixel_values: torch.Tensor,
            spatial_shapes: torch.Tensor | None = None,
            tasks: list[str] | None = None,
        ) -> dict[str, dict[str, torch.Tensor] | torch.Tensor]:
            """Forward pass through backbone and selected task heads.

            Args:
                pixel_values: Batch of images [B, C, H, W].
                spatial_shapes: NaFlex spatial shapes (optional).
                tasks: Subset of tasks to run. None runs all heads.

            Returns:
                Dict mapping task name to output:
                - regression_uncertainty: {"mu", "sigma_sq", "logits"}
                - classification: raw logit tensor [B, num_classes]
            """
            features = self.backbone.get_image_features(
                pixel_values=pixel_values,
                spatial_shapes=spatial_shapes,
            )

            active_tasks = list(self.heads.keys()) if tasks is None else tasks
            results: dict[str, dict[str, torch.Tensor] | torch.Tensor] = {}

            for task_name in active_tasks:
                if task_name not in self.heads:
                    continue

                head_output = self.heads[task_name](features)
                head_type = self._head_types.get(task_name, "classification")

                if head_type == "regression_uncertainty":
                    mu = head_output[:, 0]
                    log_sigma_sq = head_output[:, 1]
                    sigma_sq = torch.exp(log_sigma_sq)
                    temp = getattr(self, f"temp_{task_name}")
                    results[task_name] = {
                        "mu": mu,
                        "sigma_sq": temp * sigma_sq,
                        "logits": head_output,
                    }
                elif head_type == "classification":
                    results[task_name] = head_output
                else:
                    results[task_name] = head_output.squeeze(-1)

            return results

        def set_calibration_temps(self, temps: dict[str, float]) -> None:
            """Set post-hoc calibration temperatures for uncertainty heads."""
            for head_name, temp_val in temps.items():
                attr_name = f"temp_{head_name}"
                if hasattr(self, attr_name):
                    setattr(self, attr_name, torch.tensor(temp_val))

    model = SigLIP2MultiTaskTeacher(mid=model_id)
    if pretrained_iqa_path:
        model.load_iqa_checkpoint(pretrained_iqa_path)

    return model


# ============================================================================
# Dataset loaders
# ============================================================================


def _create_script_dataset(
    data_dir: Path,
    processor: Any,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
) -> Any:
    """Create script detection dataset from manifest.

    Expected directory structure:
        data_dir/
            manifest.json   # [{"image_path": "...", "script_class": "LATN"}, ...]
            images/         # image files

    Args:
        data_dir: Root directory containing manifest and images.
        processor: SigLIP2 image processor.
        max_num_patches: Maximum NaFlex patches.
        use_augmentation: Enable training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class ScriptDataset(Dataset):
        """Script detection dataset: image → 19-class script label."""

        def __init__(
            self,
            root: Path,
            proc: Any,
            max_patches: int,
            augment: bool,
        ) -> None:
            self.root = root
            self.processor = proc
            self.max_num_patches = max_patches
            self.use_augmentation = augment
            self.samples: list[dict[str, Any]] = []

            manifest_path = root / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest not found: {manifest_path}")

            with open(manifest_path) as f:
                raw_samples = json.load(f)

            for entry in raw_samples:
                script_class = entry["script_class"]
                if script_class not in SCRIPT_CLASS_TO_IDX:
                    continue
                image_path = root / entry["image_path"]
                if not image_path.exists():
                    continue
                self.samples.append(
                    {
                        "image_path": str(image_path),
                        "script_idx": SCRIPT_CLASS_TO_IDX[script_class],
                        "script_class": script_class,
                        "image_id": Path(entry["image_path"]).stem,
                    }
                )

            print(f"  ScriptDataset: {len(self.samples)} samples loaded")

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            if self.use_augmentation:
                if random.random() < 0.5:
                    image = ImageOps.mirror(image)

            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": {"script": sample["script_idx"]},
                "task_masks": {"script": 1},
                "image_id": sample["image_id"],
            }

    return ScriptDataset(
        root=data_dir,
        proc=processor,
        max_patches=max_num_patches,
        augment=use_augmentation,
    )


def _create_source_dataset(
    data_dir: Path,
    processor: Any,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
) -> Any:
    """Create document source classification dataset.

    Expected manifest: [{"image_path": "...", "source_class": "scanned"}, ...]
    Classes: scanned, camera, born_digital

    Args:
        data_dir: Root directory containing manifest and images.
        processor: SigLIP2 image processor.
        max_num_patches: Maximum NaFlex patches.
        use_augmentation: Enable training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class DocumentSourceDataset(Dataset):
        """Document source dataset: image → 3-class source label."""

        def __init__(
            self,
            root: Path,
            proc: Any,
            max_patches: int,
            augment: bool,
        ) -> None:
            self.root = root
            self.processor = proc
            self.max_num_patches = max_patches
            self.use_augmentation = augment
            self.samples: list[dict[str, Any]] = []

            manifest_path = root / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest not found: {manifest_path}")

            with open(manifest_path) as f:
                raw_samples = json.load(f)

            for entry in raw_samples:
                source_class = entry["source_class"]
                if source_class not in SOURCE_CLASS_TO_IDX:
                    continue
                image_path = root / entry["image_path"]
                if not image_path.exists():
                    continue
                self.samples.append(
                    {
                        "image_path": str(image_path),
                        "source_idx": SOURCE_CLASS_TO_IDX[source_class],
                        "image_id": Path(entry["image_path"]).stem,
                    }
                )

            print(f"  DocumentSourceDataset: {len(self.samples)} samples")

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            if self.use_augmentation:
                if random.random() < 0.5:
                    image = ImageOps.mirror(image)

            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": {"source": sample["source_idx"]},
                "task_masks": {"source": 1},
                "image_id": sample["image_id"],
            }

    return DocumentSourceDataset(
        root=data_dir,
        proc=processor,
        max_patches=max_num_patches,
        augment=use_augmentation,
    )


def _create_orientation_dataset(
    data_dir: Path,
    processor: Any,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
) -> Any:
    """Create orientation detection dataset.

    Expected manifest: [{"image_path": "...", "orientation": 90}, ...]
    Classes: 0, 90, 180, 270 (degrees)

    Args:
        data_dir: Root directory containing manifest and images.
        processor: SigLIP2 image processor.
        max_num_patches: Maximum NaFlex patches.
        use_augmentation: Enable training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    from PIL import Image
    from torch.utils.data import Dataset

    class OrientationDataset(Dataset):
        """Orientation dataset: image → 4-class orientation label."""

        def __init__(
            self,
            root: Path,
            proc: Any,
            max_patches: int,
            augment: bool,
        ) -> None:
            self.root = root
            self.processor = proc
            self.max_num_patches = max_patches
            self.use_augmentation = augment
            self.samples: list[dict[str, Any]] = []

            manifest_path = root / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest not found: {manifest_path}")

            with open(manifest_path) as f:
                raw_samples = json.load(f)

            for entry in raw_samples:
                orientation = entry["orientation"]
                if orientation not in ORIENTATION_TO_IDX:
                    continue
                image_path = root / entry["image_path"]
                if not image_path.exists():
                    continue
                self.samples.append(
                    {
                        "image_path": str(image_path),
                        "orientation_idx": ORIENTATION_TO_IDX[orientation],
                        "image_id": Path(entry["image_path"]).stem,
                    }
                )

            print(f"  OrientationDataset: {len(self.samples)} samples")

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            # No horizontal flip for orientation — would invalidate labels
            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": {"orientation": sample["orientation_idx"]},
                "task_masks": {"orientation": 1},
                "image_id": sample["image_id"],
            }

    return OrientationDataset(
        root=data_dir,
        proc=processor,
        max_patches=max_num_patches,
        augment=use_augmentation,
    )


def _create_shadow_warping_dataset(
    data_dir: Path,
    processor: Any,
    task_name: str,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
) -> Any:
    """Create shadow or warping severity regression dataset.

    Expected manifest: [{"image_path": "...", "severity": 0.45}, ...]
    Severity is a continuous 0-1 float (0 = none, 1 = extreme).

    Args:
        data_dir: Root directory containing manifest and images.
        processor: SigLIP2 image processor.
        task_name: Either "shadow" or "warping".
        max_num_patches: Maximum NaFlex patches.
        use_augmentation: Enable training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class SeverityRegressionDataset(Dataset):
        """Shadow/warping severity regression: image → 0-1 severity score."""

        def __init__(
            self,
            root: Path,
            proc: Any,
            task: str,
            max_patches: int,
            augment: bool,
        ) -> None:
            self.root = root
            self.processor = proc
            self.task = task
            self.max_num_patches = max_patches
            self.use_augmentation = augment
            self.samples: list[dict[str, Any]] = []

            manifest_path = root / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Manifest not found: {manifest_path}")

            with open(manifest_path) as f:
                raw_samples = json.load(f)

            for entry in raw_samples:
                severity = float(entry["severity"])
                image_path = root / entry["image_path"]
                if not image_path.exists():
                    continue
                self.samples.append(
                    {
                        "image_path": str(image_path),
                        "severity": severity,
                        "image_id": Path(entry["image_path"]).stem,
                    }
                )

            print(f"  SeverityRegressionDataset({task}): {len(self.samples)} samples")

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            if self.use_augmentation:
                if random.random() < 0.5:
                    image = ImageOps.mirror(image)

            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": {self.task: sample["severity"]},
                "task_masks": {self.task: 1},
                "image_id": sample["image_id"],
            }

    return SeverityRegressionDataset(
        root=data_dir,
        proc=processor,
        task=task_name,
        max_patches=max_num_patches,
        augment=use_augmentation,
    )


def _validate_manifest_no_ood(samples: list[dict[str, Any]]) -> None:
    """Reject any manifest that contains OOD-reserved samples.

    OOD images are exclusively reserved for final hold-out evaluation and must
    never appear in training or validation manifests.  If any sample carries
    ``split_type='ood'`` the entire training run is aborted before the model
    sees a single batch.

    Args:
        samples: Flat list of manifest sample dicts loaded from JSON.

    Raises:
        ValueError: If one or more samples have ``split_type='ood'``.
    """
    ood_items = [
        s.get("image_path", "?") for s in samples if s.get("split_type") == "ood"
    ]
    if ood_items:
        raise ValueError(
            f"MANIFEST VALIDATION FAILED: {len(ood_items)} items have split_type='ood'. "
            f"OOD images must never be used for training or validation. "
            f"First 5 offenders: {ood_items[:5]}"
        )


def _create_multitask_dataset(
    manifest_path: Path,
    data_root: Path,
    processor: Any,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
) -> Any:
    """Create unified multi-task dataset from merged manifest.

    Each manifest entry has an image path and one or more task labels.
    Missing tasks are handled via per-sample task masks.

    Expected manifest format:
        [
            {
                "image_path": "images/img001.jpg",
                "script": "LATN",
                "source": "scanned",
                "overall": 3.5,
                "sharpness": 4.0,
                "color": 3.8
            },
            {
                "image_path": "images/img002.jpg",
                "orientation": 90,
                "shadow": 0.35
            }
        ]

    Args:
        manifest_path: Path to unified manifest JSON.
        data_root: Root directory for resolving image paths.
        processor: SigLIP2 image processor.
        max_num_patches: Maximum NaFlex patches.
        use_augmentation: Enable training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class MultiTaskDataset(Dataset):
        """Unified multi-task dataset with per-sample task masking.

        Each sample may have labels for any subset of the 8 tasks.
        Labels are converted to indices (classification) or normalized
        floats (regression). A task mask tensor indicates which labels
        are present for loss masking.
        """

        def __init__(
            self,
            manifest: Path,
            root: Path,
            proc: Any,
            max_patches: int,
            augment: bool,
        ) -> None:
            self.root = root
            self.processor = proc
            self.max_num_patches = max_patches
            self.use_augmentation = augment
            self.samples: list[dict[str, Any]] = []

            if not manifest.exists():
                raise FileNotFoundError(f"Manifest not found: {manifest}")

            with open(manifest) as f:
                raw_samples = json.load(f)

            _validate_manifest_no_ood(raw_samples)

            for entry in raw_samples:
                image_path = root / entry["image_path"]
                if not image_path.exists():
                    continue

                sample: dict[str, Any] = {
                    "image_path": str(image_path),
                    "image_id": Path(entry["image_path"]).stem,
                    "labels": {},
                    "task_masks": {},
                }

                # Parse classification labels
                if "script" in entry:
                    cls = entry["script"]
                    if cls in SCRIPT_CLASS_TO_IDX:
                        sample["labels"]["script"] = SCRIPT_CLASS_TO_IDX[cls]
                        sample["task_masks"]["script"] = 1

                if "source" in entry:
                    cls = entry["source"]
                    if cls in SOURCE_CLASS_TO_IDX:
                        sample["labels"]["source"] = SOURCE_CLASS_TO_IDX[cls]
                        sample["task_masks"]["source"] = 1

                if "orientation" in entry:
                    deg = entry["orientation"]
                    if deg in ORIENTATION_TO_IDX:
                        sample["labels"]["orientation"] = ORIENTATION_TO_IDX[deg]
                        sample["task_masks"]["orientation"] = 1

                # Parse IQA regression labels (MOS scores, normalized to 0-1)
                for iqa_dim in IQA_DIMENSIONS:
                    if iqa_dim in entry:
                        sample["labels"][iqa_dim] = self._normalize_mos(
                            float(entry[iqa_dim])
                        )
                        sample["task_masks"][iqa_dim] = 1

                # Parse severity regression labels (already 0-1)
                for reg_task in ("shadow", "warping"):
                    if reg_task in entry:
                        sample["labels"][reg_task] = float(entry[reg_task])
                        sample["task_masks"][reg_task] = 1

                # Only keep samples with at least one label
                if sample["task_masks"]:
                    self.samples.append(sample)

            # Log task distribution
            task_counts: dict[str, int] = {}
            for s in self.samples:
                for task in s["task_masks"]:
                    task_counts[task] = task_counts.get(task, 0) + 1
            print(f"  MultiTaskDataset: {len(self.samples)} total samples")
            for task, count in sorted(task_counts.items()):
                print(f"    {task}: {count} samples")

        @staticmethod
        def _normalize_mos(score: float) -> float:
            """Normalize MOS from [1, 5] to [0, 1]."""
            return (score - 1.0) / 4.0

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            # Augmentations (skip for orientation-only samples)
            if self.use_augmentation:
                has_orientation = "orientation" in sample["task_masks"]
                if not has_orientation and random.random() < 0.5:
                    image = ImageOps.mirror(image)

            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": sample["labels"],
                "task_masks": sample["task_masks"],
                "image_id": sample["image_id"],
            }

    return MultiTaskDataset(
        manifest=manifest_path,
        root=data_root,
        proc=processor,
        max_patches=max_num_patches,
        augment=use_augmentation,
    )


# ============================================================================
# Collate function
# ============================================================================


def _multitask_collate_fn(batch: list[dict[str, Any]]) -> dict[str, Any]:
    """Collate multi-task batch with per-task label and mask tensors.

    Classification labels use 0 as default (masked out by task_masks).
    Regression labels use 0.0 as default (masked out by task_masks).

    Returns:
        Dict with pixel_values, spatial_shapes, pixel_attention_mask,
        labels (dict of tensors), task_masks (dict of tensors), image_ids.
    """
    import torch

    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    spatial_shapes = torch.stack([item["spatial_shapes"] for item in batch])
    pixel_attention_mask = torch.stack([item["pixel_attention_mask"] for item in batch])

    labels: dict[str, Any] = {}
    task_masks: dict[str, Any] = {}

    for task in ALL_TASKS:
        values: list[int | float] = []
        masks: list[float] = []

        for item in batch:
            if task in item["labels"]:
                values.append(item["labels"][task])
                masks.append(1.0)
            else:
                values.append(0 if task in CLASSIFICATION_TASKS else 0.0)
                masks.append(0.0)

        if task in CLASSIFICATION_TASKS:
            labels[task] = torch.tensor(values, dtype=torch.long)
        else:
            labels[task] = torch.tensor(values, dtype=torch.float32)
        task_masks[task] = torch.tensor(masks, dtype=torch.float32)

    return {
        "pixel_values": pixel_values,
        "spatial_shapes": spatial_shapes,
        "pixel_attention_mask": pixel_attention_mask,
        "labels": labels,
        "task_masks": task_masks,
        "image_ids": [item["image_id"] for item in batch],
    }


# ============================================================================
# GCS credential helpers (reused pattern from train_siglip2_iqa_v2.py)
# ============================================================================


def _setup_gcs_credentials() -> tuple[str | None, str | None]:
    """Write GCS credentials from Modal secret env var to a temp file.

    The Modal secret (gcs-credentials) injects GCP_SA_KEY as a base64-encoded
    service account JSON. Written to a temp file at runtime.

    Returns:
        Tuple of (credentials_path, prior_env_value).
    """
    import os
    import tempfile

    prior = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key:
        return None, prior

    sa_json = base64.b64decode(gcp_sa_key).decode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as cred_file:
        cred_file.write(sa_json)
        credentials_path = cred_file.name

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return credentials_path, prior


def _cleanup_gcs_credentials(
    credentials_path: str | None, prior_creds: str | None
) -> None:
    """Clean up temp credentials file and restore env var."""
    import os

    if credentials_path:
        cred = Path(credentials_path)
        if cred.exists():
            cred.unlink()

    if prior_creds is not None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = prior_creds
    elif credentials_path is not None:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


# ============================================================================
# Loss functions
# ============================================================================


def _create_multitask_loss(
    task_weights: dict[str, float] | None = None,
) -> Any:
    """Create multi-task loss with per-task weighting and missing-label masking.

    Classification tasks use CrossEntropy, regression tasks use GaussianNLL.
    IQA tasks use NormInNorm + GaussianNLL.

    Args:
        task_weights: Per-task loss weight multipliers.

    Returns:
        MultiTaskLoss module instance.
    """
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    weights = task_weights or {
        "overall": 1.0,
        "sharpness": 1.0,
        "color": 1.0,
        "script": 1.0,
        "source": 0.5,
        "orientation": 0.5,
        "shadow": 0.3,
        "warping": 0.3,
    }

    class GaussianNLLLoss(nn.Module):
        """Gaussian Negative Log-Likelihood for uncertainty estimation."""

        def forward(
            self,
            mu: torch.Tensor,
            sigma_sq: torch.Tensor,
            target: torch.Tensor,
        ) -> torch.Tensor:
            sigma_sq = torch.clamp(sigma_sq, min=1e-6)
            return 0.5 * torch.log(sigma_sq) + (target - mu) ** 2 / (2 * sigma_sq)

    class NormInNormLoss(nn.Module):
        """Norm-in-Norm loss for fast SRCC-aligned convergence."""

        def __init__(self, p: float = 1.0, q: float = 2.0) -> None:
            super().__init__()
            self.p = p
            self.q = q

        def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            pred_norm = (pred - pred.mean()) / (pred.std() + 1e-8)
            target_norm = (target - target.mean()) / (target.std() + 1e-8)
            diff = torch.abs(pred_norm - target_norm)
            return torch.pow(torch.pow(diff, self.p).mean(), self.q / self.p)

    class MultiTaskLoss(nn.Module):
        """Combined loss with per-task weighting and missing-label masking.

        Handles three loss types:
        - Classification: CrossEntropyLoss (script, source, orientation)
        - IQA regression: GaussianNLL + NormInNorm (overall, sharpness, color)
        - Severity regression: GaussianNLL (shadow, warping)
        """

        def __init__(self, task_wts: dict[str, float]) -> None:
            super().__init__()
            self.task_weights = task_wts
            self.gnll = GaussianNLLLoss()
            self.nin = NormInNormLoss()

        def forward(
            self,
            predictions: dict[str, dict[str, torch.Tensor] | torch.Tensor],
            targets: dict[str, torch.Tensor],
            task_masks: dict[str, torch.Tensor],
        ) -> tuple[torch.Tensor, dict[str, float]]:
            """Compute weighted sum of per-task losses.

            Args:
                predictions: Model outputs per task.
                targets: Ground truth labels per task.
                task_masks: Binary masks (1=has label, 0=missing).

            Returns:
                Tuple of (total_loss, per_task_loss_dict).
            """
            total_loss = torch.tensor(0.0, device=self._get_device(targets))
            loss_dict: dict[str, float] = {}

            for task_name in predictions:
                if task_name not in targets:
                    continue

                mask = task_masks.get(task_name)
                if mask is not None and mask.sum() == 0:
                    continue

                pred = predictions[task_name]
                target = targets[task_name]

                if task_name in CLASSIFICATION_TASKS:
                    raw_loss = F.cross_entropy(pred, target, reduction="none")
                elif task_name in IQA_TASKS:
                    gnll_loss = self.gnll(pred["mu"], pred["sigma_sq"], target)
                    nin_loss = self.nin(pred["mu"], target)
                    raw_loss = gnll_loss + nin_loss
                else:
                    raw_loss = self.gnll(pred["mu"], pred["sigma_sq"], target)

                if mask is not None:
                    masked_loss = (raw_loss * mask).sum() / (mask.sum() + 1e-8)
                else:
                    masked_loss = raw_loss.mean()

                weight = self.task_weights.get(task_name, 1.0)
                total_loss = total_loss + weight * masked_loss
                loss_dict[task_name] = masked_loss.item()

            return total_loss, loss_dict

        @staticmethod
        def _get_device(
            targets: dict[str, torch.Tensor],
        ) -> torch.device:
            for t in targets.values():
                return t.device
            return torch.device("cpu")

    return MultiTaskLoss(task_wts=weights)


# ============================================================================
# PCGrad optimizer wrapper (reused from train_siglip2_iqa_v2.py)
# ============================================================================


def _create_pcgrad_wrapper(optimizer: Any) -> Any:
    """Create PCGrad optimizer wrapper for gradient surgery.

    Projects conflicting gradients across tasks to reduce
    negative transfer in multi-task learning.

    Reference: Yu et al., "Gradient Surgery for Multi-Task Learning", NeurIPS 2020
    """
    import torch

    def _collect_grads(opt: Any) -> torch.Tensor:
        grads: list[torch.Tensor] = []
        for group in opt.param_groups:
            for p in group["params"]:
                grads.append(
                    p.grad.clone().flatten()
                    if p.grad is not None
                    else torch.zeros_like(p).flatten()
                )
        return torch.cat(grads)

    def _apply_grads(opt: Any, projected_grads: torch.Tensor) -> None:
        offset = 0
        for group in opt.param_groups:
            for p in group["params"]:
                numel = p.numel()
                p.grad = projected_grads[offset : offset + numel].view_as(p)
                offset += numel

    def _project_gradients(grads: list[torch.Tensor]) -> torch.Tensor:
        projected = [g.clone() for g in grads]
        for i in range(len(grads)):
            for j in range(len(grads)):
                if i == j:
                    continue
                dot = torch.dot(projected[i], grads[j])
                if dot < 0:
                    projected[i] -= (
                        dot / (torch.dot(grads[j], grads[j]) + 1e-8)
                    ) * grads[j]
        return torch.stack(projected).mean(dim=0)

    class PCGrad:
        """Projected Conflicting Gradients optimizer wrapper."""

        def __init__(self, opt: Any) -> None:
            self.optimizer = opt

        @property
        def param_groups(self) -> list[dict[str, Any]]:
            return self.optimizer.param_groups

        def zero_grad(self) -> None:
            self.optimizer.zero_grad()

        def step(self) -> None:
            self.optimizer.step()

        def pc_backward(self, losses: list[torch.Tensor]) -> None:
            """Backward with gradient projection for conflicting tasks."""
            task_grads: list[torch.Tensor] = []
            for i, loss in enumerate(losses):
                self.optimizer.zero_grad()
                loss.backward(retain_graph=(i < len(losses) - 1))
                task_grads.append(_collect_grads(self.optimizer))

            self.optimizer.zero_grad()
            _apply_grads(self.optimizer, _project_gradients(task_grads))

    return PCGrad(optimizer)


# ============================================================================
# EMA wrapper (reused from train_siglip2_iqa_v2.py)
# ============================================================================


def _create_ema(model: Any, decay: float) -> Any:
    """Create Exponential Moving Average wrapper for model weights."""
    import torch.nn as nn

    class EMA:
        """Exponential Moving Average for model weights."""

        def __init__(self, mdl: nn.Module, ema_decay: float = 0.999) -> None:
            self.model = mdl
            self.decay = ema_decay
            self.shadow: dict[str, Any] = {}
            self.backup: dict[str, Any] = {}

        def register(self) -> None:
            for name, param in self.model.named_parameters():
                if param.requires_grad:
                    self.shadow[name] = param.data.clone()

        def update(self) -> None:
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    new_avg = (
                        1.0 - self.decay
                    ) * param.data + self.decay * self.shadow[name]
                    self.shadow[name] = new_avg.clone()

        def apply_shadow(self) -> None:
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    self.backup[name] = param.data.clone()
                    param.data = self.shadow[name].clone()

        def restore(self) -> None:
            for name, param in self.model.named_parameters():
                if name in self.backup:
                    param.data = self.backup[name].clone()
            self.backup = {}

    return EMA(mdl=model, ema_decay=decay)


# ============================================================================
# LLRD setup (extended from train_siglip2_iqa_v2.py for multi-task heads)
# ============================================================================


def _get_llrd_param_groups(
    model: Any,
    base_lr: float,
    llrd_decay: float,
    weight_decay: float,
    iqa_lr_multiplier: float = 0.01,
) -> list[dict[str, Any]]:
    """Create parameter groups with layer-wise learning rate decay.

    Head groups: detection heads at base_lr, IQA heads at base_lr * iqa_mult.
    Backbone layers: decayed from base_lr by llrd_decay per layer depth.

    Args:
        model: SigLIP2MultiTaskTeacher instance.
        base_lr: Base learning rate for detection heads.
        llrd_decay: Decay factor per backbone layer.
        weight_decay: Weight decay.
        iqa_lr_multiplier: LR multiplier for IQA heads.

    Returns:
        Parameter groups for optimizer.
    """
    param_groups: list[dict[str, Any]] = []

    # Head param groups with differential LR
    param_groups.extend(
        model.get_head_param_groups(base_lr, iqa_lr_multiplier, weight_decay)
    )

    # Backbone layers with LLRD
    layer_groups = model.get_layer_groups()
    num_layers = len(layer_groups)

    for i, params in enumerate(reversed(layer_groups)):
        layer_lr = base_lr * (llrd_decay ** (i + 1))
        param_groups.append(
            {
                "params": params,
                "lr": layer_lr,
                "weight_decay": weight_decay,
                "name": f"backbone_layer_{num_layers - 1 - i}",
            }
        )

    return param_groups


# ============================================================================
# Training epoch and validation
# ============================================================================

_BEST_MODEL_FILENAME = "best_model.pt"


@dataclass
class _TrainingState:
    """Mutable training state for checkpoint tracking."""

    best_metric: float = 0.0
    patience_counter: int = 0
    best_checkpoint: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)


def _train_one_epoch(
    config: MultiTaskTrainingConfig,
    model: Any,
    train_loader: Any,
    loss_fn: Any,
    optimizer: Any,
    pcgrad_optimizer: Any | None,
    scheduler: Any,
    scaler: Any | None,
    device: Any,
    amp_dtype: Any,
    ema: Any | None,
    global_epoch: int,
    phase: int,
    phase_epoch: int,
    phase_total: int,
) -> tuple[float, dict[str, float]]:
    """Run one training epoch.

    Returns:
        Tuple of (average loss, per-task loss dict).
    """
    import torch
    from tqdm import tqdm

    model.train()
    total_loss = 0.0
    accum_steps = 0
    task_loss_accum: dict[str, float] = {}
    optimizer.zero_grad()

    desc = f"Phase {phase} - Epoch {phase_epoch}/{phase_total}"
    for _batch_idx, batch in enumerate(tqdm(train_loader, desc=desc)):
        pixel_values = batch["pixel_values"].to(device)
        spatial_shapes = batch["spatial_shapes"].to(device)
        targets = {k: v.to(device) for k, v in batch["labels"].items()}
        task_masks = {k: v.to(device) for k, v in batch["task_masks"].items()}

        with torch.amp.autocast(
            device_type="cuda",
            dtype=amp_dtype,
            enabled=config.use_mixed_precision,
        ):
            outputs = model(pixel_values, spatial_shapes)

            if config.use_pcgrad:
                # PCGrad: compute separate per-task losses for gradient surgery
                per_task_losses = _compute_pcgrad_task_losses(
                    loss_fn,
                    outputs,
                    targets,
                    task_masks,
                )
                for tname, tval in per_task_losses.items():
                    task_loss_accum[tname] = (
                        task_loss_accum.get(tname, 0.0) + tval.item()
                    )
                pcgrad_optimizer.pc_backward(list(per_task_losses.values()))
                batch_loss = sum(v.item() for v in per_task_losses.values())
            else:
                loss, per_task = loss_fn(outputs, targets, task_masks)
                loss = loss / config.gradient_accumulation_steps
                if scaler is not None:
                    scaler.scale(loss).backward()
                else:
                    loss.backward()
                batch_loss = loss.item() * config.gradient_accumulation_steps
                for tname, tval in per_task.items():
                    task_loss_accum[tname] = task_loss_accum.get(tname, 0.0) + tval

        total_loss += batch_loss
        accum_steps += 1

        if accum_steps >= config.gradient_accumulation_steps:
            if scaler is not None:
                scaler.unscale_(optimizer)
            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    config.gradient_clip,
                )
            if config.use_pcgrad and pcgrad_optimizer is not None:
                pcgrad_optimizer.step()
            elif scaler is not None:
                scaler.step(optimizer)
                scaler.update()
            else:
                optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            accum_steps = 0

            if ema is not None and global_epoch >= config.ema_start_epoch:
                ema.update()

    # Flush remaining accumulated gradients
    if accum_steps > 0:
        if config.gradient_clip > 0:
            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                config.gradient_clip,
            )
        optimizer.step()
        optimizer.zero_grad()

    n_batches = max(len(train_loader), 1)
    avg_task_losses = {k: v / n_batches for k, v in task_loss_accum.items()}
    return total_loss / n_batches, avg_task_losses


def _compute_pcgrad_task_losses(
    loss_fn: Any,
    outputs: dict[str, Any],
    targets: dict[str, Any],
    task_masks: dict[str, Any],
) -> dict[str, Any]:
    """Compute individual per-task losses for PCGrad backward.

    Returns dict of task_name -> scalar loss tensor (with grad).
    """
    import torch
    import torch.nn.functional as func

    task_losses: dict[str, Any] = {}
    for task_name in ALL_TASKS:
        if task_name not in outputs or task_name not in targets:
            continue
        mask = task_masks.get(task_name)
        if mask is not None and mask.sum() == 0:
            continue

        pred = outputs[task_name]
        target = targets[task_name]

        if task_name in CLASSIFICATION_TASKS:
            raw = func.cross_entropy(pred, target, reduction="none")
        elif task_name in IQA_TASKS:
            raw = loss_fn.gnll(pred["mu"], pred["sigma_sq"], target)
            raw = raw + loss_fn.nin(pred["mu"], target)
        else:
            raw = loss_fn.gnll(pred["mu"], pred["sigma_sq"], target)

        if mask is not None:
            task_loss = (raw * mask).sum() / (mask.sum() + 1e-8)
        else:
            task_loss = raw.mean()

        weight = loss_fn.task_weights.get(task_name, 1.0)
        task_losses[task_name] = weight * task_loss

    if not task_losses:
        task_losses["dummy"] = torch.tensor(0.0, requires_grad=True)
    return task_losses


def _validate(
    model: Any,
    val_loader: Any,
    loss_fn: Any,
    config: MultiTaskTrainingConfig,
    device: Any,
    amp_dtype: Any,
) -> dict[str, float]:
    """Validate model and compute per-task metrics.

    Returns dict with:
    - val_loss: total validation loss
    - script_accuracy, source_accuracy, orientation_accuracy
    - shadow_mae, warping_mae
    - iqa_srcc_overall, iqa_srcc_sharpness, iqa_srcc_color, iqa_vquala
    """
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    model.eval()
    total_loss = 0.0
    n_batches = 0

    # Accumulators for classification
    cls_correct: dict[str, int] = dict.fromkeys(CLASSIFICATION_TASKS, 0)
    cls_total: dict[str, int] = dict.fromkeys(CLASSIFICATION_TASKS, 0)

    # Accumulators for regression
    reg_abs_errors: dict[str, list[float]] = {task: [] for task in REGRESSION_TASKS}

    # Accumulators for IQA (SRCC)
    iqa_preds: dict[str, list[float]] = {dim: [] for dim in IQA_TASKS}
    iqa_labels: dict[str, list[float]] = {dim: [] for dim in IQA_TASKS}

    with torch.no_grad():
        for batch in val_loader:
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            targets = {k: v.to(device) for k, v in batch["labels"].items()}
            task_masks = {k: v.to(device) for k, v in batch["task_masks"].items()}

            with torch.amp.autocast(
                device_type="cuda",
                dtype=amp_dtype,
                enabled=config.use_mixed_precision,
            ):
                outputs = model(pixel_values, spatial_shapes)
                loss, _ = loss_fn(outputs, targets, task_masks)

            total_loss += loss.item()
            n_batches += 1

            # Classification accuracy
            for task in CLASSIFICATION_TASKS:
                if task not in outputs or task not in targets:
                    continue
                mask = task_masks.get(task)
                if mask is not None:
                    valid = mask.bool()
                    if valid.sum() == 0:
                        continue
                    preds = outputs[task][valid].argmax(dim=-1)
                    labels = targets[task][valid]
                else:
                    preds = outputs[task].argmax(dim=-1)
                    labels = targets[task]
                cls_correct[task] += (preds == labels).sum().item()
                cls_total[task] += labels.numel()

            # Regression MAE
            for task in REGRESSION_TASKS:
                if task not in outputs or task not in targets:
                    continue
                mask = task_masks.get(task)
                pred_mu = outputs[task]["mu"]
                target_val = targets[task]
                if mask is not None:
                    valid = mask.bool()
                    if valid.sum() == 0:
                        continue
                    pred_mu = pred_mu[valid]
                    target_val = target_val[valid]
                abs_err = (pred_mu - target_val).abs().cpu().tolist()
                reg_abs_errors[task].extend(abs_err)

            # IQA SRCC
            for dim in IQA_TASKS:
                if dim not in outputs or dim not in targets:
                    continue
                mask = task_masks.get(dim)
                pred_mu = outputs[dim]["mu"]
                target_val = targets[dim]
                if mask is not None:
                    valid = mask.bool()
                    if valid.sum() == 0:
                        continue
                    pred_mu = pred_mu[valid]
                    target_val = target_val[valid]
                iqa_preds[dim].extend(pred_mu.cpu().tolist())
                iqa_labels[dim].extend(target_val.cpu().tolist())

    metrics: dict[str, float] = {
        "val_loss": total_loss / max(n_batches, 1),
    }

    # Classification accuracy
    for task in CLASSIFICATION_TASKS:
        acc = cls_correct[task] / max(cls_total[task], 1)
        metrics[f"{task}_accuracy"] = acc

    # Regression MAE
    for task in REGRESSION_TASKS:
        errs = reg_abs_errors[task]
        metrics[f"{task}_mae"] = float(np.mean(errs)) if errs else 0.0

    # IQA SRCC + VQualA
    for dim in IQA_TASKS:
        if len(iqa_preds[dim]) >= 2:
            srcc_val, _ = spearmanr(iqa_preds[dim], iqa_labels[dim])
            if np.isnan(srcc_val):
                srcc_val = 0.0
        else:
            srcc_val = 0.0
        metrics[f"iqa_srcc_{dim}"] = srcc_val

    metrics["iqa_vquala"] = (
        0.5 * metrics.get("iqa_srcc_overall", 0.0)
        + 0.3 * metrics.get("iqa_srcc_sharpness", 0.0)
        + 0.2 * metrics.get("iqa_srcc_color", 0.0)
    )

    return metrics


def _log_epoch_metrics(
    phase: int,
    phase_epoch: int,
    phase_total: int,
    global_epoch: int | None,
    train_loss: float,
    val_metrics: dict[str, float],
    current_lr: float,
    epoch_time: float,
) -> None:
    """Print epoch metrics."""
    label = f"Phase {phase} - Epoch {phase_epoch}/{phase_total}"
    if global_epoch is not None:
        label += f" (Global: {global_epoch})"
    print(f"\n{label}:")
    print(f"  Train Loss: {train_loss:.4f}")
    print(f"  Val Loss: {val_metrics['val_loss']:.4f}")

    for task in CLASSIFICATION_TASKS:
        key = f"{task}_accuracy"
        if key in val_metrics:
            print(f"  {task} acc: {val_metrics[key]:.4f}")

    for task in REGRESSION_TASKS:
        key = f"{task}_mae"
        if key in val_metrics:
            print(f"  {task} MAE: {val_metrics[key]:.4f}")

    vquala = val_metrics.get("iqa_vquala", 0.0)
    print(f"  IQA VQualA: {vquala:.4f}")
    print(f"  LR: {current_lr:.2e}, Time: {epoch_time:.1f}s")


def _update_best_checkpoint(
    model: Any,
    val_metrics: dict[str, float],
    epoch: int,
    phase: int,
    config: MultiTaskTrainingConfig,
    output_dir: Path,
    state: _TrainingState,
    ema: Any | None = None,
    ema_active: bool = False,
) -> None:
    """Save checkpoint if composite metric improves.

    Composite = mean of normalized per-task metrics:
    - Classification accuracy (higher is better)
    - 1 - regression MAE (lower MAE is better, clamp 0-1)
    - IQA VQualA
    """
    import copy

    import torch

    # Composite score: mean of all task metrics
    scores: list[float] = []
    for task in CLASSIFICATION_TASKS:
        key = f"{task}_accuracy"
        if key in val_metrics:
            scores.append(val_metrics[key])
    for task in REGRESSION_TASKS:
        key = f"{task}_mae"
        if key in val_metrics:
            scores.append(max(0.0, 1.0 - val_metrics[key]))
    vquala = val_metrics.get("iqa_vquala", 0.0)
    if vquala > 0:
        scores.append(vquala)

    composite = sum(scores) / max(len(scores), 1)

    if composite <= state.best_metric:
        state.patience_counter += 1
        return

    state.best_metric = composite
    state.patience_counter = 0

    if ema is not None and ema_active:
        ema.apply_shadow()
        model_state = copy.deepcopy(model.state_dict())
        ema.restore()
    else:
        model_state = model.state_dict()

    state.best_checkpoint = {
        "epoch": epoch,
        "phase": phase,
        "model_state_dict": model_state,
        "config": config.to_dict(),
        "metrics": val_metrics,
        "composite_score": composite,
    }
    if ema_active:
        state.best_checkpoint["ema_active"] = True

    torch.save(state.best_checkpoint, output_dir / _BEST_MODEL_FILENAME)
    print(f"  -> New best composite={composite:.4f}! Saved checkpoint.")


def _check_go_nogo(
    val_metrics: dict[str, float],
    config: MultiTaskTrainingConfig,
) -> tuple[bool, list[str]]:
    """Check Phase 2 Go/No-Go criteria after Phase 1.

    Returns:
        Tuple of (needs_phase2, list of failing criteria).
    """
    failures: list[str] = []
    thresholds = {
        "script_accuracy": config.target_script_accuracy,
        "source_accuracy": config.target_source_accuracy,
        "orientation_accuracy": config.target_orientation_accuracy,
    }
    mae_thresholds = {
        "shadow_mae": config.target_shadow_mae,
        "warping_mae": config.target_warping_mae,
    }

    for key, target in thresholds.items():
        actual = val_metrics.get(key, 0.0)
        if actual < target:
            failures.append(f"{key}={actual:.4f} < {target}")

    for key, target in mae_thresholds.items():
        actual = val_metrics.get(key, 1.0)
        if actual > target:
            failures.append(f"{key}={actual:.4f} > {target}")

    return len(failures) > 0, failures


# ============================================================================
# Phase orchestrators
# ============================================================================


def _run_phase1(
    config: MultiTaskTrainingConfig,
    model: Any,
    train_loader: Any,
    val_loader: Any,
    loss_fn: Any,
    device: Any,
    amp_dtype: Any,
    scaler: Any | None,
    output_dir: Path,
    state: _TrainingState,
) -> dict[str, float]:
    """Phase 1: Frozen backbone + IQA heads, train new detection heads only.

    Returns:
        Final validation metrics.
    """
    import time

    import torch

    print("\n" + "=" * 70)
    print("Phase 1: Train Detection Heads (Frozen Backbone + IQA)")
    print("=" * 70)

    model.freeze_backbone()
    model.freeze_iqa_heads()

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )
    pcgrad_opt = _create_pcgrad_wrapper(optimizer) if config.use_pcgrad else None

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase1_epochs * len(train_loader),
        eta_min=config.min_lr,
    )

    last_metrics: dict[str, float] = {}
    for epoch in range(config.phase1_epochs):
        epoch_start = time.time()

        train_loss, _ = _train_one_epoch(
            config,
            model,
            train_loader,
            loss_fn,
            optimizer,
            pcgrad_opt,
            scheduler,
            scaler,
            device,
            amp_dtype,
            ema=None,
            global_epoch=epoch + 1,
            phase=1,
            phase_epoch=epoch + 1,
            phase_total=config.phase1_epochs,
        )

        last_metrics = _validate(
            model,
            val_loader,
            loss_fn,
            config,
            device,
            amp_dtype,
        )
        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        state.history.append(
            {
                "phase": 1,
                "epoch": epoch + 1,
                "train_loss": train_loss,
                **last_metrics,
                "lr": current_lr,
                "time": epoch_time,
            }
        )

        _log_epoch_metrics(
            phase=1,
            phase_epoch=epoch + 1,
            phase_total=config.phase1_epochs,
            global_epoch=None,
            train_loss=train_loss,
            val_metrics=last_metrics,
            current_lr=current_lr,
            epoch_time=epoch_time,
        )

        _update_best_checkpoint(
            model,
            last_metrics,
            epoch=epoch + 1,
            phase=1,
            config=config,
            output_dir=output_dir,
            state=state,
        )

        if state.patience_counter >= config.early_stopping_patience:
            print(f"  Early stopping at epoch {epoch + 1}")
            break

    return last_metrics


def _run_phase2(
    config: MultiTaskTrainingConfig,
    model: Any,
    train_loader: Any,
    val_loader: Any,
    loss_fn: Any,
    device: Any,
    amp_dtype: Any,
    scaler: Any | None,
    output_dir: Path,
    state: _TrainingState,
) -> dict[str, float]:
    """Phase 2: Unfreeze backbone with differential LR + EMA.

    Returns:
        Final validation metrics.
    """
    import time

    import torch

    print("\n" + "=" * 70)
    print("Phase 2: Full Fine-Tuning (Unfrozen Backbone + LLRD)")
    print("=" * 70)

    model.unfreeze_backbone()
    model.unfreeze_iqa_heads()

    if config.use_llrd:
        param_groups = _get_llrd_param_groups(
            model,
            config.phase2_lr,
            config.llrd_decay,
            config.weight_decay,
            config.iqa_lr_multiplier,
        )
    else:
        param_groups = model.get_head_param_groups(
            config.phase2_lr,
            config.iqa_lr_multiplier,
            config.weight_decay,
        )
        param_groups.append(
            {
                "params": list(model.backbone.parameters()),
                "lr": config.phase2_lr * config.backbone_lr_multiplier,
                "weight_decay": config.weight_decay,
                "name": "backbone",
            }
        )

    optimizer = torch.optim.AdamW(param_groups)
    pcgrad_opt = _create_pcgrad_wrapper(optimizer) if config.use_pcgrad else None

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase2_epochs * len(train_loader),
        eta_min=config.min_lr,
    )

    ema = None
    if config.use_ema:
        ema = _create_ema(model, decay=config.ema_decay)
        ema.register()
        print("  EMA registered")

    state.patience_counter = 0  # Reset for phase 2
    last_metrics: dict[str, float] = {}

    for epoch in range(config.phase2_epochs):
        global_epoch = config.phase1_epochs + epoch + 1
        epoch_start = time.time()
        ema_active = ema is not None and global_epoch >= config.ema_start_epoch

        train_loss, _ = _train_one_epoch(
            config,
            model,
            train_loader,
            loss_fn,
            optimizer,
            pcgrad_opt,
            scheduler,
            scaler,
            device,
            amp_dtype,
            ema=ema,
            global_epoch=global_epoch,
            phase=2,
            phase_epoch=epoch + 1,
            phase_total=config.phase2_epochs,
        )

        # Validate with EMA weights if active
        if ema_active:
            ema.apply_shadow()
        last_metrics = _validate(
            model,
            val_loader,
            loss_fn,
            config,
            device,
            amp_dtype,
        )
        if ema_active:
            ema.restore()

        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        state.history.append(
            {
                "phase": 2,
                "epoch": global_epoch,
                "train_loss": train_loss,
                **last_metrics,
                "lr": current_lr,
                "time": epoch_time,
            }
        )

        _log_epoch_metrics(
            phase=2,
            phase_epoch=epoch + 1,
            phase_total=config.phase2_epochs,
            global_epoch=global_epoch,
            train_loss=train_loss,
            val_metrics=last_metrics,
            current_lr=current_lr,
            epoch_time=epoch_time,
        )

        _update_best_checkpoint(
            model,
            last_metrics,
            epoch=global_epoch,
            phase=2,
            config=config,
            output_dir=output_dir,
            state=state,
            ema=ema,
            ema_active=ema_active,
        )

        if state.patience_counter >= config.early_stopping_patience:
            print(f"  Early stopping at epoch {epoch + 1}")
            break

    return last_metrics


def _setup_data_loaders(
    config: MultiTaskTrainingConfig,
    processor: Any,
    data_dir: Path,
    test_mode: bool = False,
) -> tuple[Any, Any]:
    """Create train and val data loaders from multi-task manifest.

    Args:
        config: Training configuration.
        processor: SigLIP2 image processor.
        data_dir: Root data directory.
        test_mode: If True, use small subset.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    import torch
    from torch.utils.data import DataLoader

    manifest_path = data_dir / "multitask_manifest.json"
    max_num_patches = config.max_num_patches

    train_ds = _create_multitask_dataset(
        manifest_path=data_dir / "train_manifest.json",
        data_root=data_dir,
        processor=processor,
        max_num_patches=max_num_patches,
        augment=True,
    )
    val_ds = _create_multitask_dataset(
        manifest_path=data_dir / "val_manifest.json",
        data_root=data_dir,
        processor=processor,
        max_num_patches=max_num_patches,
        augment=False,
    )

    if test_mode:
        # Subset for quick testing
        n_train = min(32, len(train_ds))
        n_val = min(16, len(val_ds))
        train_ds = torch.utils.data.Subset(train_ds, range(n_train))
        val_ds = torch.utils.data.Subset(val_ds, range(n_val))
        print(f"  [TEST] train={n_train}, val={n_val}")

    train_loader = DataLoader(
        train_ds,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        collate_fn=_multitask_collate_fn,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=config.batch_size * 2,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=_multitask_collate_fn,
    )

    print(f"  Train: {len(train_ds)} samples, {len(train_loader)} batches")
    print(f"  Val: {len(val_ds)} samples, {len(val_loader)} batches")
    return train_loader, val_loader


# ============================================================================
# Main training function
# ============================================================================


@app.function(
    image=training_image,
    gpu="A100",
    timeout=3600 * 48,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    volumes={
        "/results": results_volume,
        "/data": datasets_volume,
    },
)
def train_siglip2_multitask(
    config_dict: dict[str, Any] | None = None,
    test_mode: bool = False,
) -> dict[str, Any]:
    """Train SigLIP 2 multi-task teacher model.

    Two-phase training:
    1. Frozen backbone + IQA heads - train new detection heads only
    2. (Optional) Unfreeze everything with differential LR + LLRD + EMA

    Args:
        config_dict: Optional config overrides.
        test_mode: If True, run quick validation with synthetic data.

    Returns:
        Training results summary.
    """
    import torch
    from transformers import AutoProcessor

    config = MultiTaskTrainingConfig(**(config_dict or {}))
    if test_mode:
        config.phase1_epochs = 1
        config.phase2_epochs = 1
        config.total_epochs = 2
        config.batch_size = 4
        config.gradient_accumulation_steps = 2
        config.use_ema = False
        config.run_phase2 = False
        print("[TEST MODE] Running quick validation")

    print("=" * 70)
    print("SigLIP 2 Multi-Task Teacher Training")
    print("=" * 70)
    print(f"Model: {config.model_id}")
    print(
        f"Tasks: {len(ALL_TASKS)} ({len(IQA_TASKS)} IQA + "
        f"{len(CLASSIFICATION_TASKS)} classification + "
        f"{len(REGRESSION_TASKS)} regression)"
    )
    print(f"Phase 1: {config.phase1_epochs} epochs (frozen backbone)")
    if config.run_phase2:
        print(f"Phase 2: {config.phase2_epochs} epochs (unfrozen)")
    print(f"PCGrad: {config.use_pcgrad}")
    print(f"LLRD: {config.use_llrd} (decay={config.llrd_decay})")
    print(f"Mixed Precision: {config.use_mixed_precision}")
    print("=" * 70)

    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"VRAM: {vram_gb:.1f} GB")

    # GCS credentials
    _setup_gcs_credentials()

    # Model
    model = _create_multitask_model(
        model_id=config.model_id,
        pretrained_iqa_path=config.pretrained_iqa_checkpoint,
    )
    model = model.to(device)

    if config.use_gradient_checkpointing:
        model.backbone.gradient_checkpointing_enable()
        print("  Gradient checkpointing enabled")

    total_params = sum(p.numel() for p in model.parameters())
    backbone_params = sum(p.numel() for p in model.backbone.parameters())
    head_params = total_params - backbone_params
    print(f"\nTotal parameters: {total_params:,}")
    print(f"Backbone parameters: {backbone_params:,}")
    print(f"Head parameters: {head_params:,}")

    # Processor and data
    processor = AutoProcessor.from_pretrained(config.model_id)
    data_dir = Path("/data")
    train_loader, val_loader = _setup_data_loaders(
        config,
        processor,
        data_dir,
        test_mode,
    )

    # Loss function
    loss_fn = _create_multitask_loss(config.task_weights)
    loss_fn = loss_fn.to(device)

    # Mixed precision setup
    amp_dtype = torch.bfloat16 if config.use_mixed_precision else torch.float32
    scaler = None
    if config.use_mixed_precision and amp_dtype == torch.float16:
        scaler = torch.amp.GradScaler("cuda")

    # Output directory
    output_dir = Path("/results") / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    state = _TrainingState()

    # Phase 1: Frozen backbone, train detection heads
    if config.phase1_epochs > 0:
        phase1_metrics = _run_phase1(
            config,
            model,
            train_loader,
            val_loader,
            loss_fn,
            device,
            amp_dtype,
            scaler,
            output_dir,
            state,
        )
    else:
        phase1_metrics = {}

    # Go/No-Go check
    needs_phase2 = config.run_phase2
    if phase1_metrics and config.run_phase2:
        needs_p2, failures = _check_go_nogo(phase1_metrics, config)
        if not needs_p2:
            print("\n*** All Go/No-Go criteria PASSED — Phase 2 optional ***")
            print("  Running Phase 2 anyway for potential improvement.")
        else:
            print(f"\n*** Go/No-Go FAILURES: {len(failures)} ***")
            for f in failures:
                print(f"  - {f}")
            print("  Proceeding to Phase 2.")

    # Phase 2: Full fine-tuning
    if needs_phase2 and config.phase2_epochs > 0:
        phase2_metrics = _run_phase2(
            config,
            model,
            train_loader,
            val_loader,
            loss_fn,
            device,
            amp_dtype,
            scaler,
            output_dir,
            state,
        )
    else:
        phase2_metrics = {}

    # Save final training history
    final_metrics = phase2_metrics or phase1_metrics
    history_path = output_dir / "training_history.json"
    with open(history_path, "w") as fp:
        json.dump(state.history, fp, indent=2, default=str)

    # Commit results volume
    results_volume.commit()

    result = {
        "status": "training_complete",
        "total_params": total_params,
        "head_params": head_params,
        "best_composite": state.best_metric,
        "best_checkpoint": str(output_dir / _BEST_MODEL_FILENAME),
        "final_metrics": final_metrics,
        "config": config.to_dict(),
        "timestamp": datetime.now().isoformat(),
    }
    print(f"\n{'=' * 70}")
    print("Training Complete!")
    print(f"Best composite: {state.best_metric:.4f}")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 70}")
    return result


# ============================================================================
# Local entrypoint
# ============================================================================


@app.local_entrypoint()
def main(
    test: bool = False,
    phase: int = 0,
    epochs: int = 0,
    batch_size: int = 8,
    model: str = "base",
    no_pcgrad: bool = False,
    no_llrd: bool = False,
    no_phase2: bool = False,
    iqa_checkpoint: str = "",
) -> None:
    """Launch multi-task teacher training on Modal.

    Args:
        test: Run quick test with synthetic data.
        phase: Train specific phase only (1 or 2). 0 = both.
        epochs: Override total epochs.
        batch_size: Override batch size.
        model: Model variant ("base" or "so400m").
        no_pcgrad: Disable PCGrad gradient surgery.
        no_llrd: Disable layer-wise learning rate decay.
        no_phase2: Skip Phase 2 (frozen backbone only).
        iqa_checkpoint: Path to pretrained IQA v2 checkpoint.
    """
    config_overrides: dict[str, Any] = {
        "model_variant": model,
        "batch_size": batch_size,
        "use_pcgrad": not no_pcgrad,
        "use_llrd": not no_llrd,
        "run_phase2": not no_phase2,
    }

    if epochs > 0:
        if phase == 1:
            config_overrides["phase1_epochs"] = epochs
            config_overrides["run_phase2"] = False
        elif phase == 2:
            config_overrides["phase2_epochs"] = epochs
            config_overrides["phase1_epochs"] = 0
        else:
            config_overrides["phase1_epochs"] = min(15, epochs // 3)
            config_overrides["phase2_epochs"] = (
                epochs - config_overrides["phase1_epochs"]
            )

    if iqa_checkpoint:
        config_overrides["pretrained_iqa_checkpoint"] = iqa_checkpoint

    result = train_siglip2_multitask.remote(
        config_dict=config_overrides,
        test_mode=test,
    )
    print(f"\nTraining result: {json.dumps(result, indent=2, default=str)}")


# ============================================================================
# Module exports (for import by other scripts)
# ============================================================================

__all__ = [
    "ALL_TASKS",
    "CLASSIFICATION_TASKS",
    "HEAD_CONFIGS",
    "IQA_DIMENSIONS",
    "IQA_TASKS",
    "MODEL_VARIANTS",
    "ORIENTATION_CLASSES",
    "ORIENTATION_TO_IDX",
    "REGRESSION_TASKS",
    "SCRIPT_CLASS_TO_IDX",
    "SCRIPT_ML_CLASSES",
    "SOURCE_CLASSES",
    "SOURCE_CLASS_TO_IDX",
    "MultiTaskTrainingConfig",
    "app",
]
