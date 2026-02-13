"""Train SigLIP 2 for Document IQA with Tier 1+2+3 Improvements.

Enhanced training script implementing consensus recommendations from 5 frontier models:
- Gemini 2.5 Pro, Gemini 3 Pro Preview, GPT-5.2, DeepSeek R1, Grok 4

TIER 1 IMPROVEMENTS (Unanimous - 5/5 models):
- CosineAnnealingLR scheduler (replaces OneCycleLR to prevent premature convergence)
- Gradient accumulation (4-8 steps for larger effective batch)
- Extended training: 75 epochs (15 warmup + 60 fine-tuning)
- Higher resolution: 784 patches (up from 576, based on research showing diminishing returns above 576-784)
- Increased early stopping patience: 20 epochs

TIER 2 IMPROVEMENTS (Strong agreement - 4-5/5 models):
- Layer-wise Learning Rate Decay (LLRD): 0.9 decay per layer
- MarginRankingLoss: Direct SRCC optimization via pairwise comparisons
- PCGrad re-enabled in Phase 2: With gradient accumulation for memory efficiency
- EMA (Exponential Moving Average): Applied in last 20 epochs for stability

TIER 3 IMPROVEMENTS (Memory/Speed optimizations):
- Gradient Checkpointing: Reduces memory usage by recomputing activations (~30% memory savings)
- Mixed Precision (BF16/FP16): 2x speed improvement with minimal quality impact
  - BF16 (default): Recommended for A100, no GradScaler needed
  - FP16: Fallback for older GPUs, uses GradScaler to prevent underflow

Reference:
- Planning doc: docs/planning/SIGLIP2_LARGE_400M_TRAINING_LOG.md
- Original script: modal/train_siglip2_iqa.py (v1.0)
- Research: tmp_cleanup/siglip_research.md Section 4.2.1 (resolution analysis)

Target: VQualA >= 0.92 (up from 0.886 achieved by v1.0)

Usage:
    # Quick test (2 epochs)
    uv run modal run modal/train_siglip2_iqa_v2.py --test

    # Full training with improved defaults (detached)
    uv run modal run --detach modal/train_siglip2_iqa_v2.py

    # Train 400M model
    uv run modal run --detach modal/train_siglip2_iqa_v2.py --model so400m

    # Train without mixed precision (debug)
    uv run modal run modal/train_siglip2_iqa_v2.py --no-mixed-precision

    # Use FP16 instead of BF16
    uv run modal run modal/train_siglip2_iqa_v2.py --fp16

    # Monitor logs
    modal app logs siglip2-iqa-training-v2 --follow
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import modal

# Modal app definition
app = modal.App("siglip2-iqa-training-v2")

# Volumes for persistent storage
results_volume = modal.Volume.from_name("siglip2-iqa-results", create_if_missing=True)
diqa5000_volume = modal.Volume.from_name("diqa5000-original", create_if_missing=True)

# GCS Configuration for DIQA-5000
GCS_BUCKET = "image_detection_b"
GCS_PREFIX = "datasets/diqa-5000-original"
DIQA5000_SPLITS = ["train", "val", "test"]

# S1192: Extract duplicate literal to constant
_BEST_MODEL_FILENAME = "siglip2_iqa_best.pt"

# IQA quality dimensions used across all heads
_IQA_DIMENSIONS = ("overall", "sharpness", "color")

# Model variants
MODEL_VARIANTS = {
    "base": "google/siglip2-base-patch16-naflex",  # 86M params
    "so400m": "google/siglip2-so400m-patch16-naflex",  # 400M params
}

# Docker image with all dependencies
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
        # GCS access
        "google-cloud-storage>=2.10.0",
        # Experiment tracking
        "wandb",
    )
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)


@dataclass
class SigLIP2TrainingConfigV2:
    """Enhanced training configuration with Tier 1+2 improvements."""

    # Model selection
    model_variant: str = "base"  # "base" (86M) or "so400m" (400M)
    model_id: str = field(default="", init=False)  # Set from variant

    # TIER 1: Resolution - increased from 576 to 784 (research shows diminishing returns above this)
    max_num_patches: int = 784
    uncertainty: bool = True

    # TIER 1: Extended training (15 warmup + 60 fine-tuning = 75 total)
    phase1_epochs: int = 15  # Warmup (frozen backbone)
    phase2_epochs: int = 60  # Fine-tuning (unfrozen)
    total_epochs: int = 75

    # TIER 1: Gradient accumulation (effective batch = batch_size * accumulation_steps)
    batch_size: int = 8  # Reduced due to higher resolution
    gradient_accumulation_steps: int = 4  # Effective batch 32

    # Learning rates
    phase1_lr: float = 2e-4  # Higher LR for heads only
    phase2_lr: float = 1e-4  # Adjusted for longer training
    min_lr: float = 1e-6  # Floor for cosine annealing

    # TIER 2: Layer-wise Learning Rate Decay (0.9 per layer)
    use_llrd: bool = True
    llrd_decay: float = 0.9  # Each layer gets 0.9x the LR of the layer above

    # Optimizer settings
    weight_decay: float = 0.01
    gradient_clip: float = 1.0

    # TIER 1: CosineAnnealingLR (replaces OneCycleLR)
    use_cosine_scheduler: bool = True

    # Multi-task learning
    use_pcgrad: bool = True  # TIER 2: Re-enabled with gradient accumulation

    # Loss functions
    use_norm_in_norm: bool = True  # Fast convergence
    use_ranking_loss: bool = True  # TIER 2: MarginRankingLoss
    ranking_loss_weight: float = 0.3  # Lambda for ranking loss

    # TIER 2: Exponential Moving Average
    use_ema: bool = True
    ema_decay: float = 0.999
    ema_start_epoch: int = 55  # Start EMA in last 20 epochs

    # Augmentation (quality-preserving only)
    use_augmentation: bool = True
    horizontal_flip_prob: float = 0.5
    random_crop_prob: float = 0.3

    # TIER 1: Increased early stopping patience
    early_stopping_patience: int = 20  # Up from 15
    save_every_n_epochs: int = 5
    keep_top_k: int = 3

    # TIER 3: Memory/Speed optimizations
    use_gradient_checkpointing: bool = True  # Recompute activations to save memory
    use_mixed_precision: bool = True  # BF16 for 2x speed
    mixed_precision_dtype: str = "bfloat16"  # "bfloat16" or "float16"

    # Target metrics
    target_srcc: float = 0.90
    target_vquala: float = 0.92

    # Output
    output_dir: str = "/results/siglip2_v2"

    def __post_init__(self):
        # Set model_id based on variant
        self.model_id = MODEL_VARIANTS.get(self.model_variant, MODEL_VARIANTS["base"])

        # Adjust batch size for larger models
        if self.model_variant == "so400m":
            self.batch_size = 4  # Reduced for 400M model
            self.gradient_accumulation_steps = 8  # Keep effective batch 32

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class EntrypointConfig:
    """Grouped parameters for the CLI entrypoint (S107: reduce parameter count)."""

    test: bool = False
    model: str = "base"
    epochs: int = 75
    batch_size: int = 8
    accumulation: int = 4
    max_patches: int = 784
    no_llrd: bool = False
    no_ranking_loss: bool = False
    no_pcgrad: bool = False
    no_ema: bool = False
    no_uncertainty: bool = False
    no_gradient_checkpointing: bool = False
    no_mixed_precision: bool = False
    fp16: bool = False

    def to_training_config(self) -> SigLIP2TrainingConfigV2:
        """Convert entrypoint flags to training config."""
        return SigLIP2TrainingConfigV2(
            model_variant=self.model,
            total_epochs=self.epochs,
            phase1_epochs=min(15, self.epochs // 5),
            phase2_epochs=self.epochs - min(15, self.epochs // 5),
            batch_size=self.batch_size,
            gradient_accumulation_steps=self.accumulation,
            max_num_patches=self.max_patches,
            use_llrd=not self.no_llrd,
            use_ranking_loss=not self.no_ranking_loss,
            use_pcgrad=not self.no_pcgrad,
            use_ema=not self.no_ema,
            uncertainty=not self.no_uncertainty,
            use_gradient_checkpointing=not self.no_gradient_checkpointing,
            use_mixed_precision=not self.no_mixed_precision,
            mixed_precision_dtype="float16" if self.fp16 else "bfloat16",
        )


def compute_vquala(
    srcc_overall: float, srcc_sharpness: float, srcc_color: float
) -> float:
    """Compute VQualA final score: 0.5*overall + 0.25*sharpness + 0.25*color."""
    return 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color


# ============================================================================
# Training helper dataclass to hold shared mutable state
# ============================================================================


@dataclass
class _TrainingState:
    """Mutable training state shared across helper functions."""

    history: list[dict[str, Any]] = field(default_factory=list)
    best_vquala: float = 0.0
    best_checkpoint: dict[str, Any] | None = None
    patience_counter: int = 0
    calibration_temps: dict[str, float] | None = None


@app.function(
    image=training_image,
    gpu="A100",  # A100 40GB for 400M model + higher resolution
    timeout=3600 * 48,  # 48 hours max for extended training
    secrets=[modal.Secret.from_name("gcs-credentials")],
    volumes={
        "/results": results_volume,
        "/data": diqa5000_volume,
    },
)
def train_siglip2_iqa_v2(
    config_dict: dict[str, Any] | None = None,
    test_mode: bool = False,
) -> dict[str, Any]:
    """Train SigLIP 2 for document IQA with Tier 1+2 improvements.

    Args:
        config_dict: Optional config overrides.
        test_mode: If True, run quick validation (2 epochs).

    Returns:
        Training results summary.
    """
    import torch

    config = _apply_test_mode_overrides(
        SigLIP2TrainingConfigV2(**(config_dict or {})), test_mode
    )
    _print_config_banner(config)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_dtype, scaler = _setup_mixed_precision(config, device)

    model, processor = _setup_model(config, device)
    train_loader, val_loader, test_dataset = _prepare_data(config, processor, test_mode)
    loss_fns = _create_loss_functions(config)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state = _TrainingState()

    _run_phase1_warmup(
        config,
        model,
        train_loader,
        val_loader,
        loss_fns,
        device,
        amp_dtype,
        scaler,
        output_dir,
        state,
    )
    _run_phase2_finetuning(
        config,
        model,
        train_loader,
        val_loader,
        loss_fns,
        device,
        amp_dtype,
        scaler,
        output_dir,
        state,
    )

    if config.uncertainty:
        _run_posthoc_calibration(
            config,
            model,
            val_loader,
            device,
            amp_dtype,
            output_dir,
            state,
        )

    test_metrics, target_achieved = _run_final_evaluation(
        config,
        model,
        test_dataset,
        device,
        amp_dtype,
        output_dir,
        state,
    )

    results = _save_training_results(
        config,
        state,
        test_metrics,
        target_achieved,
        output_dir,
    )

    results_volume.commit()
    return results


# ============================================================================
# Inline classes (must be defined at call site due to Modal serialization)
# These are created lazily inside helpers that need torch imports.
# ============================================================================


def _apply_test_mode_overrides(
    config: SigLIP2TrainingConfigV2, test_mode: bool
) -> SigLIP2TrainingConfigV2:
    """Apply test mode configuration overrides."""
    if test_mode:
        config.phase1_epochs = 1
        config.phase2_epochs = 1
        config.total_epochs = 2
        config.batch_size = 4
        config.gradient_accumulation_steps = 2
        config.use_ema = False
        print("[TEST MODE] Running quick validation with 2 epochs")
    return config


def _print_config_banner(config: SigLIP2TrainingConfigV2) -> None:
    """Print training configuration banner."""
    print("=" * 70)
    print("SigLIP 2 IQA Training v2.0 (Tier 1+2+3 Improvements)")
    print("=" * 70)
    print(f"Model: {config.model_id} ({config.model_variant})")
    print(f"Max Patches: {config.max_num_patches} (up from 576)")
    print(f"Total Epochs: {config.total_epochs} (15 warmup + 60 fine-tuning)")
    effective_batch = config.batch_size * config.gradient_accumulation_steps
    print(
        f"Batch Size: {config.batch_size} x {config.gradient_accumulation_steps}"
        f" = {effective_batch}"
    )
    print("Scheduler: CosineAnnealingLR (replaces OneCycleLR)")
    print(f"LLRD: {config.use_llrd} (decay={config.llrd_decay})")
    print(f"PCGrad: {config.use_pcgrad}")
    print(
        f"Ranking Loss: {config.use_ranking_loss} (lambda={config.ranking_loss_weight})"
    )
    print(f"EMA: {config.use_ema} (starts epoch {config.ema_start_epoch})")
    print(f"Gradient Checkpointing: {config.use_gradient_checkpointing}")
    print(
        f"Mixed Precision: {config.use_mixed_precision} ({config.mixed_precision_dtype})"
    )
    print(f"Early Stopping Patience: {config.early_stopping_patience}")
    print(f"Target SRCC: {config.target_srcc}")
    print(f"Target VQualA: {config.target_vquala}")
    print("=" * 70)


def _setup_mixed_precision(config: SigLIP2TrainingConfigV2, device: Any) -> tuple:
    """Configure mixed precision training dtype and optional GradScaler.

    Returns:
        Tuple of (amp_dtype, scaler_or_none).
    """
    import torch

    if not config.use_mixed_precision:
        print("Mixed precision: Disabled (FP32)")
        return torch.float32, None

    if config.mixed_precision_dtype == "bfloat16" and torch.cuda.is_bf16_supported():
        amp_dtype = torch.bfloat16
        print("Mixed precision: BF16 enabled (recommended for A100)")
    else:
        amp_dtype = torch.float16
        print("Mixed precision: FP16 enabled")

    scaler = torch.amp.GradScaler("cuda") if amp_dtype == torch.float16 else None

    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"VRAM: {vram_gb:.1f} GB")

    return amp_dtype, scaler


def _setup_model(config: SigLIP2TrainingConfigV2, device: Any) -> tuple:
    """Create and configure the SigLIP 2 model and processor.

    Returns:
        Tuple of (model, processor).
    """
    from transformers import AutoProcessor

    print("\nLoading SigLIP 2 processor and model...")
    processor = AutoProcessor.from_pretrained(config.model_id)

    model = _create_siglip2_model(config.model_id, config.uncertainty)

    if config.use_gradient_checkpointing:
        model.backbone.gradient_checkpointing_enable()
        print(
            "Gradient checkpointing: Enabled (saves memory by recomputing activations)"
        )

    model = model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    backbone_params = sum(p.numel() for p in model.backbone.parameters())
    head_params = total_params - backbone_params
    print(f"Total parameters: {total_params:,}")
    print(f"Backbone parameters: {backbone_params:,}")
    print(f"Head parameters: {head_params:,}")

    return model, processor


def _create_siglip2_model(model_id: str, uncertainty: bool) -> Any:
    """Instantiate SigLIP2DocumentIQAv2 model.

    This is separated so the class definition stays inside the Modal function scope.
    """
    import torch
    import torch.nn as nn
    from transformers import AutoModel

    class SigLIP2DocumentIQAv2(nn.Module):
        """SigLIP 2 NaFlex with multi-task IQA heads + uncertainty (v2)."""

        def __init__(
            self,
            mid: str = "google/siglip2-base-patch16-naflex",
            use_uncertainty: bool = True,
        ):
            super().__init__()
            self.backbone = AutoModel.from_pretrained(mid)
            embed_dim = self.backbone.config.vision_config.hidden_size
            self.uncertainty = use_uncertainty

            head_output_dim = 2 if use_uncertainty else 1
            self.heads = nn.ModuleDict(
                {
                    dim: self._make_head(embed_dim, head_output_dim)
                    for dim in _IQA_DIMENSIONS
                }
            )

            for dim in _IQA_DIMENSIONS:
                self.register_buffer(f"temp_{dim}", torch.tensor(1.0))

        def _make_head(self, in_dim: int, out_dim: int) -> nn.Module:
            return nn.Sequential(
                nn.Linear(in_dim, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, out_dim),
            )

        def freeze_backbone(self):
            for param in self.backbone.parameters():
                param.requires_grad = False

        def unfreeze_backbone(self):
            for param in self.backbone.parameters():
                param.requires_grad = True

        def get_layer_groups(self) -> list[list[nn.Parameter]]:
            """Get parameter groups for LLRD.

            Returns layers from deepest (earliest) to shallowest (latest).
            """
            encoder = self.backbone.vision_model.encoder
            # S1481: removed unused num_layers variable

            groups = []
            groups.append(list(self.backbone.vision_model.embeddings.parameters()))

            for layer in encoder.layers:
                groups.append(list(layer.parameters()))

            groups.append(list(self.backbone.vision_model.post_layernorm.parameters()))
            return groups

        def forward(
            self,
            pixel_values: torch.Tensor,
            spatial_shapes: torch.Tensor | None = None,
            _pixel_attention_mask: torch.Tensor | None = None,
        ) -> dict[str, dict | torch.Tensor]:
            outputs = self.backbone.get_image_features(
                pixel_values=pixel_values,
                spatial_shapes=spatial_shapes,
            )

            results = {}
            for head_name, head in self.heads.items():
                head_output = head(outputs)

                if self.uncertainty:
                    mu = head_output[:, 0]
                    log_sigma_sq = head_output[:, 1]
                    sigma_sq = torch.exp(log_sigma_sq)
                    temp = getattr(self, f"temp_{head_name}")
                    sigma_sq_calibrated = temp * sigma_sq
                    results[head_name] = {
                        "mu": mu,
                        "sigma_sq": sigma_sq_calibrated,
                        "logits": head_output,
                    }
                else:
                    results[head_name] = head_output.squeeze(-1)

            return results

        def set_calibration_temps(self, temps: dict[str, float]):
            for head_name, temp in temps.items():
                setattr(self, f"temp_{head_name}", torch.tensor(temp))

    return SigLIP2DocumentIQAv2(mid=model_id, use_uncertainty=uncertainty)


def _prepare_data(
    config: SigLIP2TrainingConfigV2,
    processor: Any,
    test_mode: bool,
) -> tuple:
    """Download dataset, create DataLoaders.

    Returns:
        Tuple of (train_loader, val_loader, test_dataset).
    """
    from torch.utils.data import DataLoader

    print("\nDownloading DIQA-5000 dataset from GCS...")
    data_dir = Path("/data/diqa5000")
    _download_diqa5000_from_gcs(data_dir)
    diqa5000_volume.commit()

    print("\nLoading DIQA-5000 dataset...")
    train_dataset = _create_diqa_dataset(
        split="train",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
        use_augmentation=config.use_augmentation,
        horizontal_flip_prob=config.horizontal_flip_prob,
        random_crop_prob=config.random_crop_prob,
    )
    val_dataset = _create_diqa_dataset(
        split="val",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
    )
    test_dataset = _create_diqa_dataset(
        split="test",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
    )

    if test_mode:
        train_dataset.samples = train_dataset.samples[:50]
        val_dataset.samples = val_dataset.samples[:25]
        test_dataset.samples = test_dataset.samples[:25]

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        collate_fn=_custom_collate_fn,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=_custom_collate_fn,
    )

    return train_loader, val_loader, test_dataset


def _create_diqa_dataset(
    split: str,
    data_dir: Path,
    processor: Any,
    max_num_patches: int = 784,
    use_augmentation: bool = False,
    horizontal_flip_prob: float = 0.5,
    random_crop_prob: float = 0.3,
) -> Any:
    """Create a DIQA5000Dataset instance (class defined inside for Modal serialization)."""
    import csv

    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class DIQA5000Dataset(Dataset):
        """Original DIQA-5000 dataset with human MOS labels."""

        def __init__(
            self,
            split_name: str,
            data_directory: Path,
            proc: Any,
            max_patches: int,
            augment: bool,
            h_flip_prob: float,
            crop_prob: float,
        ):
            self.split = split_name
            self.data_dir = data_directory
            self.processor = proc
            self.max_num_patches = max_patches
            self.use_augmentation = augment and split_name == "train"
            self.horizontal_flip_prob = h_flip_prob
            self.random_crop_prob = crop_prob
            self.samples: list[dict[str, Any]] = []

            split_dir = self.data_dir / split_name
            csv_path = split_dir / f"{split_name}.csv"
            res_dir = split_dir / "res"

            if not csv_path.exists():
                raise FileNotFoundError(f"CSV not found: {csv_path}")

            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_filename = row["res"]
                    image_path = res_dir / image_filename

                    if not image_path.exists():
                        continue

                    self.samples.append(
                        {
                            "image_path": str(image_path),
                            "image_id": image_filename.replace(".jpg", ""),
                            "overall": float(row["overall"]),
                            "sharpness": float(row["sharpness"]),
                            "color_fidelity": float(row["color_fidelity"]),
                        }
                    )

            print(f"  {split_name}: {len(self.samples)} samples loaded")

        def __len__(self) -> int:
            return len(self.samples)

        def _normalize_mos(self, score: float) -> float:
            return (score - 1.0) / 4.0

        def _apply_safe_augmentations(self, image: Image.Image) -> Image.Image:
            if random.random() < self.horizontal_flip_prob:
                image = ImageOps.mirror(image)

            if random.random() < self.random_crop_prob:
                w, h = image.size
                crop_scale = random.choice([0.8, 0.9, 1.0])
                new_w, new_h = int(w * crop_scale), int(h * crop_scale)
                if new_w > 0 and new_h > 0:
                    left = random.randint(0, max(0, w - new_w))
                    top = random.randint(0, max(0, h - new_h))
                    image = image.crop((left, top, left + new_w, top + new_h))
                    image = image.resize((w, h), Image.LANCZOS)

            return image

        def __getitem__(self, idx: int) -> dict[str, Any]:
            sample = self.samples[idx]
            image = Image.open(sample["image_path"]).convert("RGB")

            if self.use_augmentation:
                image = self._apply_safe_augmentations(image)

            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            labels = {
                "overall": self._normalize_mos(sample["overall"]),
                "sharpness": self._normalize_mos(sample["sharpness"]),
                "color": self._normalize_mos(sample["color_fidelity"]),
            }

            return {
                "pixel_values": inputs["pixel_values"].squeeze(0),
                "spatial_shapes": inputs["spatial_shapes"].squeeze(0),
                "pixel_attention_mask": inputs["pixel_attention_mask"].squeeze(0),
                "labels": labels,
                "image_id": sample["image_id"],
            }

    return DIQA5000Dataset(
        split_name=split,
        data_directory=data_dir,
        proc=processor,
        max_patches=max_num_patches,
        augment=use_augmentation,
        h_flip_prob=horizontal_flip_prob,
        crop_prob=random_crop_prob,
    )


def _custom_collate_fn(batch: list[dict]) -> dict[str, Any]:
    """Collate function for DIQA-5000 DataLoader."""
    import torch

    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    spatial_shapes = torch.stack([item["spatial_shapes"] for item in batch])
    pixel_attention_mask = torch.stack([item["pixel_attention_mask"] for item in batch])
    labels = [item["labels"] for item in batch]
    image_ids = [item["image_id"] for item in batch]
    return {
        "pixel_values": pixel_values,
        "spatial_shapes": spatial_shapes,
        "pixel_attention_mask": pixel_attention_mask,
        "labels": labels,
        "image_ids": image_ids,
    }


def _is_diqa5000_cached(data_dir: Path) -> bool:
    """Check if DIQA-5000 is already downloaded and valid."""
    marker_file = data_dir / ".download_complete"
    if not marker_file.exists():
        return False
    all_csvs_exist = all(
        (data_dir / split / f"{split}.csv").exists() for split in DIQA5000_SPLITS
    )
    if all_csvs_exist:
        print("DIQA-5000 already downloaded and validated, skipping...")
        return True
    marker_file.unlink()
    return False


def _download_gcs_split(bucket: Any, data_dir: Path, split: str) -> int:
    """Download a single split from GCS. Returns count of downloaded files."""
    split_dir = data_dir / split
    split_dir.mkdir(exist_ok=True)
    (split_dir / "res").mkdir(exist_ok=True)
    (split_dir / "ori").mkdir(exist_ok=True)

    prefix = f"{GCS_PREFIX}/{split}/"
    downloaded = 0
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        relative_path = blob.name[len(prefix) :]
        if not relative_path:
            continue
        local_file = split_dir / relative_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_file))
        downloaded += 1
        if downloaded % 500 == 0:
            print(f"  Downloaded {downloaded} files from {split}...")
    return downloaded


def _download_diqa5000_from_gcs(data_dir: Path) -> bool:
    """Download original DIQA-5000 dataset from GCS."""
    import os

    from google.cloud import storage

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    if _is_diqa5000_cached(data_dir):
        return True

    print(f"Downloading DIQA-5000 from gs://{GCS_BUCKET}/{GCS_PREFIX}/")
    start_time = time.time()

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    data_dir.mkdir(parents=True, exist_ok=True)

    downloaded = sum(
        _download_gcs_split(bucket, data_dir, split) for split in DIQA5000_SPLITS
    )

    print(f"Downloaded {downloaded} files in {time.time() - start_time:.1f}s")

    if downloaded < 100:
        print(f"ERROR: Only downloaded {downloaded} files, expected thousands!")
        return False

    for split in DIQA5000_SPLITS:
        csv_path = data_dir / split / f"{split}.csv"
        if not csv_path.exists():
            print(f"ERROR: Missing CSV at {csv_path}")
            return False
        print(f"  Verified: {csv_path}")

    (data_dir / ".download_complete").touch()
    return True


# ============================================================================
# Loss function helpers
# ============================================================================


def _create_loss_functions(config: SigLIP2TrainingConfigV2) -> dict[str, Any]:
    """Instantiate all loss functions used during training.

    Returns:
        Dict with keys 'gnll', 'nin', 'ranking' (ranking may be None).
    """
    import torch
    import torch.nn as nn

    class NormInNormLoss(nn.Module):
        """Norm-in-Norm loss for fast SRCC-aligned convergence."""

        def __init__(self, p: float = 1.0, q: float = 2.0):
            super().__init__()
            self.p = p
            self.q = q

        def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            pred_norm = (pred - pred.mean()) / (pred.std() + 1e-8)
            target_norm = (target - target.mean()) / (target.std() + 1e-8)
            diff = torch.abs(pred_norm - target_norm)
            return torch.pow(torch.pow(diff, self.p).mean(), self.q / self.p)

    class GaussianNLLLoss(nn.Module):
        """Gaussian Negative Log-Likelihood for uncertainty estimation."""

        def forward(
            self, mu: torch.Tensor, sigma_sq: torch.Tensor, target: torch.Tensor
        ) -> torch.Tensor:
            sigma_sq = torch.clamp(sigma_sq, min=1e-6)
            loss = 0.5 * torch.log(sigma_sq) + (target - mu) ** 2 / (2 * sigma_sq)
            return loss.mean()

    class MarginRankingLoss(nn.Module):
        """Margin ranking loss for direct SRCC optimization (TIER 2)."""

        def __init__(self, margin: float = 0.0):
            super().__init__()
            self.margin = margin
            self.loss_fn = nn.MarginRankingLoss(margin=margin)

        def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            n = pred.size(0)
            if n < 2:
                return torch.tensor(0.0, device=pred.device)

            idx_i, idx_j = torch.triu_indices(n, n, offset=1, device=pred.device)
            pred_i = pred[idx_i]
            pred_j = pred[idx_j]
            target_i = target[idx_i]
            target_j = target[idx_j]

            y = torch.sign(target_i - target_j)
            mask = y != 0
            if mask.sum() == 0:
                return torch.tensor(0.0, device=pred.device)

            return self.loss_fn(pred_i[mask], pred_j[mask], y[mask])

    return {
        "gnll": GaussianNLLLoss(),
        "nin": NormInNormLoss(p=1.0, q=2.0),
        "ranking": MarginRankingLoss() if config.use_ranking_loss else None,
    }


# ============================================================================
# PCGrad and EMA helpers
# ============================================================================


def _create_pcgrad_wrapper(optimizer: Any) -> Any:
    """Create PCGrad optimizer wrapper for gradient surgery."""
    import torch

    def _collect_grads(opt) -> torch.Tensor:
        """Collect flattened gradients from all optimizer param groups."""
        grads = []
        for group in opt.param_groups:
            for p in group["params"]:
                grads.append(
                    p.grad.clone().flatten()
                    if p.grad is not None
                    else torch.zeros_like(p).flatten()
                )
        return torch.cat(grads)

    def _apply_grads(opt, projected_grads: torch.Tensor) -> None:
        """Assign projected gradients back to parameters."""
        offset = 0
        for group in opt.param_groups:
            for p in group["params"]:
                numel = p.numel()
                p.grad = projected_grads[offset : offset + numel].view_as(p)
                offset += numel

    def _project_gradients(grads: list[torch.Tensor]) -> torch.Tensor:
        """Project gradients to remove conflicting components."""
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
        """Projected Conflicting Gradients optimizer wrapper.

        Reference: Yu et al., "Gradient Surgery for Multi-Task Learning", NeurIPS 2020
        """

        def __init__(self, opt):
            self.optimizer = opt

        @property
        def param_groups(self):
            return self.optimizer.param_groups

        def zero_grad(self):
            return self.optimizer.zero_grad()

        def step(self):
            return self.optimizer.step()

        def pc_backward(self, losses: list[torch.Tensor]):
            """Backward with gradient projection for conflicting tasks."""
            task_grads = []
            for i, loss in enumerate(losses):
                self.optimizer.zero_grad()
                loss.backward(retain_graph=(i < len(losses) - 1))
                task_grads.append(_collect_grads(self.optimizer))

            self.optimizer.zero_grad()
            _apply_grads(self.optimizer, _project_gradients(task_grads))

    return PCGrad(optimizer)


def _create_ema(model: Any, decay: float) -> Any:
    """Create an EMA (Exponential Moving Average) wrapper for model weights."""
    import torch.nn as nn

    class EMA:
        """Exponential Moving Average for model weights."""

        def __init__(self, mdl: nn.Module, ema_decay: float = 0.999):
            self.model = mdl
            self.decay = ema_decay
            self.shadow: dict[str, Any] = {}
            self.backup: dict[str, Any] = {}

        def register(self):
            for name, param in self.model.named_parameters():
                if param.requires_grad:
                    self.shadow[name] = param.data.clone()

        def update(self):
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    new_average = (
                        1.0 - self.decay
                    ) * param.data + self.decay * self.shadow[name]
                    self.shadow[name] = new_average.clone()

        def apply_shadow(self):
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    self.backup[name] = param.data.clone()
                    param.data = self.shadow[name].clone()

        def restore(self):
            for name, param in self.model.named_parameters():
                if name in self.backup:
                    param.data = self.backup[name].clone()
            self.backup = {}

    return EMA(mdl=model, ema_decay=decay)


# ============================================================================
# LLRD Optimizer Setup (TIER 2)
# ============================================================================


def _get_llrd_param_groups(
    model: Any,
    base_lr: float,
    llrd_decay: float,
    weight_decay: float,
) -> list[dict]:
    """Create parameter groups with layer-wise learning rate decay.

    Args:
        model: The model.
        base_lr: Base learning rate for heads.
        llrd_decay: Decay factor per layer (e.g., 0.9).
        weight_decay: Weight decay.

    Returns:
        Parameter groups for optimizer.
    """
    param_groups = []

    param_groups.append(
        {
            "params": list(model.heads.parameters()),
            "lr": base_lr,
            "weight_decay": weight_decay,
            "name": "heads",
        }
    )

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
# Training building blocks
# ============================================================================


def _compute_loss(
    outputs: dict,
    labels: list[dict],
    loss_fns: dict[str, Any],
    config: SigLIP2TrainingConfigV2,
    device: Any,
    use_ranking: bool = False,
) -> tuple:
    """Compute combined loss for all dimensions.

    Returns:
        Tuple of (total_loss, per_dimension_losses).
    """
    import torch

    losses = []

    for dim in _IQA_DIMENSIONS:
        target = torch.tensor(
            [lbl[dim] for lbl in labels], device=device, dtype=torch.float32
        )

        if config.uncertainty:
            pred = outputs[dim]
            gnll_loss = loss_fns["gnll"](pred["mu"], pred["sigma_sq"], target)

            if use_ranking and loss_fns["ranking"] is not None:
                rank_loss = loss_fns["ranking"](pred["mu"], target)
                loss = gnll_loss + config.ranking_loss_weight * rank_loss
            else:
                loss = gnll_loss
        else:
            pred_scores = outputs[dim]
            nin_loss = loss_fns["nin"](pred_scores, target)

            if use_ranking and loss_fns["ranking"] is not None:
                rank_loss = loss_fns["ranking"](pred_scores, target)
                loss = nin_loss + config.ranking_loss_weight * rank_loss
            else:
                loss = nin_loss

        losses.append(loss)

    total_loss = sum(losses) / len(losses)
    return total_loss, losses


def _compute_pcgrad_losses(
    outputs: dict,
    labels_list: list[dict],
    loss_fns: dict[str, Any],
    config: SigLIP2TrainingConfigV2,
    device: Any,
    use_ranking: bool = False,
) -> list:
    """Compute per-dimension losses for PCGrad backward.

    Returns:
        List of per-dimension loss tensors (already divided by accumulation steps).
    """
    import torch

    losses = []
    for dim in _IQA_DIMENSIONS:
        target = torch.tensor(
            [lbl[dim] for lbl in labels_list],
            device=device,
            dtype=torch.float32,
        )
        if config.uncertainty:
            gnll_loss = loss_fns["gnll"](
                outputs[dim]["mu"], outputs[dim]["sigma_sq"], target
            )
            if use_ranking and loss_fns["ranking"] is not None:
                rank_loss = loss_fns["ranking"](outputs[dim]["mu"], target)
                loss = gnll_loss + config.ranking_loss_weight * rank_loss
            else:
                loss = gnll_loss
        else:
            nin_loss = loss_fns["nin"](outputs[dim], target)
            if use_ranking and loss_fns["ranking"] is not None:
                rank_loss = loss_fns["ranking"](outputs[dim], target)
                loss = nin_loss + config.ranking_loss_weight * rank_loss
            else:
                loss = nin_loss

        losses.append(loss / config.gradient_accumulation_steps)

    return losses


def _backward_step(
    _config: SigLIP2TrainingConfigV2,
    pcgrad_optimizer: Any | None,
    scaler: Any | None,
    loss_or_losses: Any,
    is_pcgrad: bool,
) -> float:
    """Execute backward pass, returning accumulated loss value.

    Args:
        _config: Training config (reserved for future use).
        pcgrad_optimizer: PCGrad wrapper (or None).
        scaler: GradScaler for FP16 (or None).
        loss_or_losses: Either a single loss tensor or list of per-dim losses.
        is_pcgrad: Whether to use PCGrad backward.

    Returns:
        Scalar loss value for logging.
    """
    if is_pcgrad:
        pcgrad_optimizer.pc_backward(loss_or_losses)
        return sum(loss_val.item() for loss_val in loss_or_losses)

    if scaler is not None:
        scaler.scale(loss_or_losses).backward()
    else:
        loss_or_losses.backward()
    return loss_or_losses.item()


def _optimizer_step(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    optimizer: Any,
    pcgrad_optimizer: Any | None,
    scaler: Any | None,
    scheduler: Any,
) -> None:
    """Execute one optimizer step with gradient clipping and scaler handling."""
    import torch

    if scaler is not None:
        scaler.unscale_(optimizer)

    if config.gradient_clip > 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)

    if config.use_pcgrad and pcgrad_optimizer is not None:
        pcgrad_optimizer.step()
    elif scaler is not None:
        scaler.step(optimizer)
        scaler.update()
    else:
        optimizer.step()

    scheduler.step()
    optimizer.zero_grad()


def _flush_remaining_gradients(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    optimizer: Any,
    accum_steps: int,
) -> None:
    """Flush any accumulated gradients at end of epoch."""
    import torch

    if accum_steps > 0:
        if config.gradient_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
        optimizer.step()
        optimizer.zero_grad()


def _train_one_epoch(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    train_loader: Any,
    loss_fns: dict[str, Any],
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
) -> float:
    """Run one training epoch, return average train loss."""
    import torch
    from tqdm import tqdm

    model.train()
    train_loss = 0.0
    accum_steps = 0
    optimizer.zero_grad()

    desc = f"Phase {phase} - Epoch {phase_epoch}/{phase_total}"
    for _batch_idx, batch in enumerate(tqdm(train_loader, desc=desc)):
        pixel_values = batch["pixel_values"].to(device)
        spatial_shapes = batch["spatial_shapes"].to(device)
        labels_list = batch["labels"]

        with torch.amp.autocast(
            device_type="cuda", dtype=amp_dtype, enabled=config.use_mixed_precision
        ):
            outputs = model(pixel_values, spatial_shapes)

            if config.use_pcgrad:
                use_rank = config.use_ranking_loss if phase == 2 else False
                losses = _compute_pcgrad_losses(
                    outputs,
                    labels_list,
                    loss_fns,
                    config,
                    device,
                    use_ranking=use_rank,
                )
            else:
                loss, _ = _compute_loss(
                    outputs,
                    labels_list,
                    loss_fns,
                    config,
                    device,
                    use_ranking=config.use_ranking_loss,
                )
                loss = loss / config.gradient_accumulation_steps

        train_loss += _backward_step(
            config,
            pcgrad_optimizer,
            scaler,
            losses if config.use_pcgrad else loss,
            is_pcgrad=config.use_pcgrad,
        )

        accum_steps += 1

        if accum_steps >= config.gradient_accumulation_steps:
            _optimizer_step(
                config,
                model,
                optimizer,
                pcgrad_optimizer,
                scaler,
                scheduler,
            )
            accum_steps = 0

            if ema is not None and global_epoch >= config.ema_start_epoch:
                ema.update()

    _flush_remaining_gradients(config, model, optimizer, accum_steps)

    return train_loss * config.gradient_accumulation_steps / len(train_loader)


def _validate(
    model: Any,
    loader: Any,
    loss_fns: dict[str, Any],
    config: SigLIP2TrainingConfigV2,
    device: Any,
    amp_dtype: Any,
) -> dict[str, float]:
    """Validate model and compute metrics."""
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    model.eval()
    all_preds = {dim: [] for dim in _IQA_DIMENSIONS}
    all_labels = {dim: [] for dim in _IQA_DIMENSIONS}
    total_loss = 0.0

    with torch.no_grad():
        for batch in loader:
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            with torch.amp.autocast(
                device_type="cuda",
                dtype=amp_dtype,
                enabled=config.use_mixed_precision,
            ):
                outputs = model(pixel_values, spatial_shapes)
                loss, _ = _compute_loss(
                    outputs,
                    labels_list,
                    loss_fns,
                    config,
                    device,
                    use_ranking=False,
                )

            total_loss += loss.item()

            for dim in _IQA_DIMENSIONS:
                if config.uncertainty:
                    preds = outputs[dim]["mu"].cpu().numpy()
                else:
                    preds = outputs[dim].cpu().numpy()

                all_preds[dim].extend(preds)
                all_labels[dim].extend([lbl[dim] for lbl in labels_list])

    srcc = {}
    for dim in _IQA_DIMENSIONS:
        srcc[dim], _ = spearmanr(all_preds[dim], all_labels[dim])
        if np.isnan(srcc[dim]):
            srcc[dim] = 0.0

    vquala = compute_vquala(srcc["overall"], srcc["sharpness"], srcc["color"])

    return {
        "loss": total_loss / len(loader),
        "srcc_overall": srcc["overall"],
        "srcc_sharpness": srcc["sharpness"],
        "srcc_color": srcc["color"],
        "vquala": vquala,
    }


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
    """Print epoch training metrics."""
    epoch_label = f"Phase {phase} - Epoch {phase_epoch}/{phase_total}"
    if global_epoch is not None:
        epoch_label += f" (Global: {global_epoch})"
    print(f"\n{epoch_label}:")
    print(f"  Train Loss: {train_loss:.4f}")
    print(f"  Val Loss: {val_metrics['loss']:.4f}")
    print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
    print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
    print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
    print(f"  VQualA: {val_metrics['vquala']:.4f}")
    print(f"  LR: {current_lr:.2e}, Time: {epoch_time:.1f}s")


def _update_best_checkpoint(
    model: Any,
    val_metrics: dict[str, float],
    epoch: int,
    phase: int,
    config: SigLIP2TrainingConfigV2,
    output_dir: Path,
    state: _TrainingState,
    ema: Any | None = None,
    ema_active: bool = False,
) -> None:
    """Check if current metrics are best and save checkpoint if so."""
    import copy

    import torch

    if val_metrics["vquala"] <= state.best_vquala:
        state.patience_counter += 1
        return

    state.best_vquala = val_metrics["vquala"]

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
    }
    if ema_active:
        state.best_checkpoint["ema_active"] = True

    torch.save(state.best_checkpoint, output_dir / _BEST_MODEL_FILENAME)
    print("  -> New best VQualA! Saved checkpoint.")
    state.patience_counter = 0


# ============================================================================
# Phase orchestrators
# ============================================================================


def _run_phase1_warmup(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    train_loader: Any,
    val_loader: Any,
    loss_fns: dict[str, Any],
    device: Any,
    amp_dtype: Any,
    scaler: Any | None,
    output_dir: Path,
    state: _TrainingState,
) -> None:
    """Phase 1: Head warmup with frozen backbone."""
    import torch

    print("\n" + "=" * 70)
    print("Phase 1: Head Warmup (Frozen Backbone)")
    print("=" * 70)

    model.freeze_backbone()

    # S6973: Pass lr and weight_decay explicitly
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )

    pcgrad_optimizer = _create_pcgrad_wrapper(optimizer) if config.use_pcgrad else None

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase1_epochs * len(train_loader),
        eta_min=config.min_lr,
    )

    for epoch in range(config.phase1_epochs):
        epoch_start = time.time()

        train_loss = _train_one_epoch(
            config,
            model,
            train_loader,
            loss_fns,
            optimizer,
            pcgrad_optimizer,
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

        val_metrics = _validate(model, val_loader, loss_fns, config, device, amp_dtype)
        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        state.history.append(
            {
                "phase": 1,
                "epoch": epoch + 1,
                "train_loss": train_loss,
                **val_metrics,
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
            val_metrics=val_metrics,
            current_lr=current_lr,
            epoch_time=epoch_time,
        )

        _update_best_checkpoint(
            model,
            val_metrics,
            epoch=epoch + 1,
            phase=1,
            config=config,
            output_dir=output_dir,
            state=state,
        )


def _run_phase2_finetuning(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    train_loader: Any,
    val_loader: Any,
    loss_fns: dict[str, Any],
    device: Any,
    amp_dtype: Any,
    scaler: Any | None,
    output_dir: Path,
    state: _TrainingState,
) -> None:
    """Phase 2: Full fine-tuning with LLRD."""
    import torch

    print("\n" + "=" * 70)
    print("Phase 2: Full Fine-Tuning with LLRD")
    print("=" * 70)

    model.unfreeze_backbone()

    optimizer = _create_phase2_optimizer(config, model)
    pcgrad_optimizer = _create_pcgrad_wrapper(optimizer) if config.use_pcgrad else None

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

    for epoch in range(config.phase2_epochs):
        global_epoch = config.phase1_epochs + epoch + 1
        epoch_start = time.time()

        train_loss = _train_one_epoch(
            config,
            model,
            train_loader,
            loss_fns,
            optimizer,
            pcgrad_optimizer,
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

        val_metrics = _validate_with_optional_ema(
            model,
            val_loader,
            loss_fns,
            config,
            device,
            amp_dtype,
            ema,
            global_epoch,
        )

        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        state.history.append(
            {
                "phase": 2,
                "epoch": global_epoch,
                "train_loss": train_loss,
                **val_metrics,
                "lr": current_lr,
                "time": epoch_time,
                "ema_active": ema is not None
                and global_epoch >= config.ema_start_epoch,
            }
        )

        _log_epoch_metrics(
            phase=2,
            phase_epoch=epoch + 1,
            phase_total=config.phase2_epochs,
            global_epoch=global_epoch,
            train_loss=train_loss,
            val_metrics=val_metrics,
            current_lr=current_lr,
            epoch_time=epoch_time,
        )

        ema_active = ema is not None and global_epoch >= config.ema_start_epoch
        _update_best_checkpoint(
            model,
            val_metrics,
            epoch=global_epoch,
            phase=2,
            config=config,
            output_dir=output_dir,
            state=state,
            ema=ema,
            ema_active=ema_active,
        )

        _save_periodic_checkpoint(
            config,
            model,
            optimizer,
            val_metrics,
            global_epoch,
            epoch,
            output_dir,
        )

        if state.patience_counter >= config.early_stopping_patience:
            print(
                f"\nEarly stopping triggered after {state.patience_counter}"
                " epochs without improvement."
            )
            print(f"Best VQualA achieved: {state.best_vquala:.4f}")
            break

        if (
            val_metrics["vquala"] >= config.target_vquala
            and val_metrics["srcc_overall"] >= config.target_srcc
        ):
            print("  -> Target metrics achieved! Continuing to maximize performance...")


def _create_phase2_optimizer(config: SigLIP2TrainingConfigV2, model: Any) -> Any:
    """Create optimizer for Phase 2 with optional LLRD."""
    import torch

    # S6973: Pass lr and weight_decay explicitly to all optimizer constructors
    if config.use_llrd:
        param_groups = _get_llrd_param_groups(
            model,
            base_lr=config.phase2_lr,
            llrd_decay=config.llrd_decay,
            weight_decay=config.weight_decay,
        )
        optimizer = torch.optim.AdamW(
            param_groups,
            lr=config.phase2_lr,
            weight_decay=config.weight_decay,
        )
        print(f"  LLRD enabled: {len(param_groups)} parameter groups")
        for pg in param_groups[:3]:
            print(f"    {pg['name']}: lr={pg['lr']:.2e}")
        print("    ...")
    else:
        optimizer = torch.optim.AdamW(
            [
                {"params": model.backbone.parameters(), "lr": config.phase2_lr * 0.1},
                {"params": model.heads.parameters(), "lr": config.phase2_lr},
            ],
            lr=config.phase2_lr,
            weight_decay=config.weight_decay,
        )

    return optimizer


def _validate_with_optional_ema(
    model: Any,
    val_loader: Any,
    loss_fns: dict[str, Any],
    config: SigLIP2TrainingConfigV2,
    device: Any,
    amp_dtype: Any,
    ema: Any | None,
    global_epoch: int,
) -> dict[str, float]:
    """Validate using EMA weights if available and in EMA phase."""
    if ema is not None and global_epoch >= config.ema_start_epoch:
        ema.apply_shadow()
        val_metrics = _validate(model, val_loader, loss_fns, config, device, amp_dtype)
        ema.restore()
        print("  (EMA model used for validation)")
    else:
        val_metrics = _validate(model, val_loader, loss_fns, config, device, amp_dtype)
    return val_metrics


def _save_periodic_checkpoint(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    optimizer: Any,
    val_metrics: dict[str, float],
    global_epoch: int,
    phase_epoch: int,
    output_dir: Path,
) -> None:
    """Save periodic checkpoint every N epochs."""
    import torch

    if (phase_epoch + 1) % config.save_every_n_epochs == 0:
        checkpoint = {
            "epoch": global_epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config.to_dict(),
            "metrics": val_metrics,
        }
        torch.save(checkpoint, output_dir / f"siglip2_iqa_epoch{global_epoch}.pt")


def _run_posthoc_calibration(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    val_loader: Any,
    device: Any,
    amp_dtype: Any,
    output_dir: Path,
    state: _TrainingState,
) -> None:
    """Post-hoc STD scaling calibration on validation set."""
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    print("\n" + "=" * 70)
    print("Post-hoc STD Scaling Calibration")
    print("=" * 70)

    best_state = torch.load(output_dir / _BEST_MODEL_FILENAME, weights_only=True)
    model.load_state_dict(best_state["model_state_dict"])
    model.eval()

    predictions = {dim: [] for dim in _IQA_DIMENSIONS}
    uncertainties = {dim: [] for dim in _IQA_DIMENSIONS}
    targets = {dim: [] for dim in _IQA_DIMENSIONS}

    with torch.no_grad():
        for batch in val_loader:
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            with torch.amp.autocast(
                device_type="cuda",
                dtype=amp_dtype,
                enabled=config.use_mixed_precision,
            ):
                outputs = model(pixel_values, spatial_shapes)

            for dim in _IQA_DIMENSIONS:
                predictions[dim].extend(outputs[dim]["mu"].cpu().numpy())
                uncertainties[dim].extend(outputs[dim]["sigma_sq"].cpu().numpy())
                targets[dim].extend([lbl[dim] for lbl in labels_list])

    calibration_temps = {}
    for dim in _IQA_DIMENSIONS:
        preds = np.array(predictions[dim])
        uncerts = np.array(uncertainties[dim])
        targs = np.array(targets[dim])

        optimal_temp = _find_optimal_temperature(preds, uncerts, targs)
        calibration_temps[dim] = optimal_temp

        srcc, _ = spearmanr(preds, targs)
        print(f"  {dim}: T={optimal_temp:.3f}, SRCC={srcc:.4f}")

    model.set_calibration_temps(calibration_temps)
    state.best_checkpoint["model_state_dict"] = model.state_dict()
    state.best_checkpoint["calibration_temps"] = calibration_temps
    state.calibration_temps = calibration_temps

    torch.save(state.best_checkpoint, output_dir / _BEST_MODEL_FILENAME)
    print("  -> Saved calibrated model")


def _find_optimal_temperature(preds: Any, uncerts: Any, targs: Any) -> float:
    """Find optimal calibration temperature via NLL minimization."""
    import numpy as np
    from scipy.optimize import minimize_scalar

    def negative_log_likelihood(
        temperature, _uncerts=uncerts, _targs=targs, _preds=preds
    ):
        scaled_sigma_sq = temperature * _uncerts
        return np.mean(
            0.5 * np.log(scaled_sigma_sq + 1e-8)
            + (_targs - _preds) ** 2 / (2 * scaled_sigma_sq + 1e-8)
        )

    result = minimize_scalar(
        negative_log_likelihood, bounds=(0.1, 10.0), method="bounded"
    )
    return result.x


def _run_final_evaluation(
    config: SigLIP2TrainingConfigV2,
    model: Any,
    test_dataset: Any,
    device: Any,
    amp_dtype: Any,
    output_dir: Path,
    state: _TrainingState,
) -> tuple[dict[str, float], bool]:
    """Evaluate best model on test set.

    Returns:
        Tuple of (test_metrics, target_achieved).
    """
    import torch
    from torch.utils.data import DataLoader

    print("\n" + "=" * 70)
    print("Final Evaluation on Test Set")
    print("=" * 70)

    best_state = torch.load(output_dir / _BEST_MODEL_FILENAME, weights_only=True)
    model.load_state_dict(best_state["model_state_dict"])

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        collate_fn=_custom_collate_fn,
    )

    loss_fns = _create_loss_functions(config)
    test_metrics = _validate(model, test_loader, loss_fns, config, device, amp_dtype)

    print("\nTest Set Results:")
    print(f"  SRCC Overall:   {test_metrics['srcc_overall']:.4f}")
    print(f"  SRCC Sharpness: {test_metrics['srcc_sharpness']:.4f}")
    print(f"  SRCC Color:     {test_metrics['srcc_color']:.4f}")
    print(f"  VQualA:         {test_metrics['vquala']:.4f}")

    target_achieved = (
        test_metrics["srcc_overall"] >= config.target_srcc
        and test_metrics["vquala"] >= config.target_vquala
    )

    if target_achieved:
        print("\n-> TARGET ACHIEVED! Model ready for production.")
    else:
        print(f"\n-> Target not achieved. Best VQualA: {state.best_vquala:.4f}")
        print(f"  Gap to target: {config.target_vquala - test_metrics['vquala']:.4f}")

    return test_metrics, target_achieved


def _save_training_results(
    config: SigLIP2TrainingConfigV2,
    state: _TrainingState,
    test_metrics: dict[str, float],
    target_achieved: bool,
    output_dir: Path,
) -> dict[str, Any]:
    """Serialize training results to JSON and return results dict."""
    results: dict[str, Any] = {
        "config": config.to_dict(),
        "best_vquala": state.best_vquala,
        "test_results": {
            "srcc_overall": test_metrics["srcc_overall"],
            "srcc_sharpness": test_metrics["srcc_sharpness"],
            "srcc_color": test_metrics["srcc_color"],
            "vquala": test_metrics["vquala"],
        },
        "target_achieved": target_achieved,
        "history": state.history,
        "checkpoint_path": str(output_dir / _BEST_MODEL_FILENAME),
        "timestamp": datetime.now().isoformat(),
        "improvements": _build_improvements_summary(config),
    }

    if state.calibration_temps is not None:
        results["calibration_temps"] = state.calibration_temps

    results_path = output_dir / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print(f"Best checkpoint: {output_dir / _BEST_MODEL_FILENAME}")

    return results


def _build_improvements_summary(
    config: SigLIP2TrainingConfigV2,
) -> dict[str, list[str]]:
    """Build the improvements summary dict for results output."""
    return {
        "tier1": [
            "CosineAnnealingLR (replaces OneCycleLR)",
            f"Gradient accumulation ({config.gradient_accumulation_steps} steps)",
            f"Extended training ({config.total_epochs} epochs)",
            f"Higher resolution ({config.max_num_patches} patches)",
            f"Early stopping patience ({config.early_stopping_patience})",
        ],
        "tier2": [
            f"LLRD ({config.llrd_decay} decay per layer)"
            if config.use_llrd
            else "LLRD disabled",
            f"MarginRankingLoss (lambda={config.ranking_loss_weight})"
            if config.use_ranking_loss
            else "Ranking loss disabled",
            "PCGrad re-enabled" if config.use_pcgrad else "PCGrad disabled",
            f"EMA (start epoch {config.ema_start_epoch})"
            if config.use_ema
            else "EMA disabled",
        ],
        "tier3": [
            "Gradient checkpointing"
            if config.use_gradient_checkpointing
            else "Gradient checkpointing disabled",
            f"Mixed precision ({config.mixed_precision_dtype})"
            if config.use_mixed_precision
            else "Mixed precision disabled",
        ],
    }


# ============================================================================
# CLI Entrypoint
# ============================================================================


@app.local_entrypoint()
def main(
    test: bool = False,
    model: str = "base",
    epochs: int = 75,
    batch_size: int = 8,
    accumulation: int = 4,
    max_patches: int = 784,
    no_llrd: bool = False,
    no_ranking_loss: bool = False,
    no_pcgrad: bool = False,
    no_ema: bool = False,
    no_uncertainty: bool = False,
    no_gradient_checkpointing: bool = False,
    no_mixed_precision: bool = False,
    fp16: bool = False,
):
    """Train SigLIP 2 for document IQA with Tier 1+2+3 improvements.

    Args:
        test: Run quick test mode (2 epochs).
        model: Model variant ("base" for 86M, "so400m" for 400M).
        epochs: Total training epochs.
        batch_size: Training batch size.
        accumulation: Gradient accumulation steps.
        max_patches: NaFlex max_num_patches.
        no_llrd: Disable layer-wise learning rate decay.
        no_ranking_loss: Disable margin ranking loss.
        no_pcgrad: Disable PCGrad optimizer.
        no_ema: Disable EMA.
        no_uncertainty: Disable uncertainty output.
        no_gradient_checkpointing: Disable gradient checkpointing (TIER 3).
        no_mixed_precision: Disable mixed precision (TIER 3).
        fp16: Use FP16 instead of BF16 for mixed precision (TIER 3).
    """
    # Note: Modal local_entrypoint requires individual parameters, so we
    # convert to EntrypointConfig internally for config creation.
    ep_config = EntrypointConfig(
        test=test,
        model=model,
        epochs=epochs,
        batch_size=batch_size,
        accumulation=accumulation,
        max_patches=max_patches,
        no_llrd=no_llrd,
        no_ranking_loss=no_ranking_loss,
        no_pcgrad=no_pcgrad,
        no_ema=no_ema,
        no_uncertainty=no_uncertainty,
        no_gradient_checkpointing=no_gradient_checkpointing,
        no_mixed_precision=no_mixed_precision,
        fp16=fp16,
    )

    _print_entrypoint_banner(ep_config)

    config = ep_config.to_training_config()
    result = train_siglip2_iqa_v2.remote(
        config_dict=config.to_dict(),
        test_mode=test,
    )

    _print_training_summary(result)


def _print_entrypoint_banner(ep_config: EntrypointConfig) -> None:
    """Print entrypoint configuration banner."""
    print("=" * 70)
    print("SigLIP 2 IQA Training v2.0 (Tier 1+2+3 Improvements)")
    print("=" * 70)
    print(f"Test mode: {ep_config.test}")
    print(
        f"Model: {ep_config.model} ({MODEL_VARIANTS.get(ep_config.model, 'unknown')})"
    )
    print(f"Epochs: {ep_config.epochs if not ep_config.test else 2}")
    effective = ep_config.batch_size * ep_config.accumulation
    print(
        f"Batch size: {ep_config.batch_size} x {ep_config.accumulation} = {effective}"
    )
    print(f"Max patches: {ep_config.max_patches}")
    print(f"LLRD: {not ep_config.no_llrd}")
    print(f"Ranking Loss: {not ep_config.no_ranking_loss}")
    print(f"PCGrad: {not ep_config.no_pcgrad}")
    print(f"EMA: {not ep_config.no_ema}")
    print(f"Uncertainty: {not ep_config.no_uncertainty}")
    print(f"Gradient Checkpointing: {not ep_config.no_gradient_checkpointing}")
    precision_label = "fp16" if ep_config.fp16 else "bf16"
    print(f"Mixed Precision: {not ep_config.no_mixed_precision} ({precision_label})")
    print("=" * 70)


def _print_training_summary(result: dict[str, Any]) -> None:
    """Print final training summary after remote execution."""
    print("\n" + "=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print(f"Best VQualA: {result['best_vquala']:.4f}")
    print(f"Test SRCC Overall: {result['test_results']['srcc_overall']:.4f}")
    print(f"Test VQualA: {result['test_results']['vquala']:.4f}")
    print(f"Target Achieved: {result['target_achieved']}")
    print(f"\nCheckpoint: {result['checkpoint_path']}")

    print("\nImprovements applied:")
    for tier, items in result.get("improvements", {}).items():
        print(f"  {tier.upper()}:")
        for item in items:
            print(f"    - {item}")

    if result["target_achieved"]:
        print("\n-> Model ready for production!")
        print("Next steps:")
        print("  1. Download checkpoint:")
        print(
            "     modal volume get siglip2-iqa-results"
            f" /results/siglip2_v2/{_BEST_MODEL_FILENAME} ./checkpoints/"
        )
        print("  2. Run inference on new documents")
        print("  3. Consider training 400M variant for further gains")
