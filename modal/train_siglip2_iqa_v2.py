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

import copy
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


def compute_vquala(
    srcc_overall: float, srcc_sharpness: float, srcc_color: float
) -> float:
    """Compute VQualA final score: 0.5*overall + 0.25*sharpness + 0.25*color."""
    return 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color


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
    import torch.nn as nn
    from PIL import Image, ImageOps
    from scipy.optimize import minimize_scalar
    from scipy.stats import spearmanr
    from torch.utils.data import DataLoader, Dataset
    from tqdm import tqdm
    from transformers import AutoModel, AutoProcessor

    # ========================================================================
    # PCGrad Implementation (Inline)
    # ========================================================================

    class PCGrad:
        """Projected Conflicting Gradients optimizer wrapper.

        Projects conflicting gradients to mitigate negative transfer in multi-task learning.
        Reference: Yu et al., "Gradient Surgery for Multi-Task Learning", NeurIPS 2020
        """

        def __init__(self, optimizer):
            self.optimizer = optimizer

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
                grads = []
                for group in self.optimizer.param_groups:
                    for p in group["params"]:
                        if p.grad is not None:
                            grads.append(p.grad.clone().flatten())
                        else:
                            grads.append(torch.zeros_like(p).flatten())
                task_grads.append(torch.cat(grads))

            projected_grads = self._project_gradients(task_grads)

            self.optimizer.zero_grad()
            offset = 0
            for group in self.optimizer.param_groups:
                for p in group["params"]:
                    numel = p.numel()
                    p.grad = projected_grads[offset : offset + numel].view_as(p)
                    offset += numel

        def _project_gradients(self, grads: list[torch.Tensor]) -> torch.Tensor:
            """Project gradients to remove conflicting components."""
            num_tasks = len(grads)
            projected = [g.clone() for g in grads]

            for i in range(num_tasks):
                for j in range(num_tasks):
                    if i != j:
                        dot = torch.dot(projected[i], grads[j])
                        if dot < 0:
                            projected[i] -= (
                                dot / (torch.dot(grads[j], grads[j]) + 1e-8)
                            ) * grads[j]

            return torch.stack(projected).mean(dim=0)

    # ========================================================================
    # EMA Implementation (TIER 2)
    # ========================================================================

    class EMA:
        """Exponential Moving Average for model weights."""

        def __init__(self, model: nn.Module, decay: float = 0.999):
            self.model = model
            self.decay = decay
            self.shadow = {}
            self.backup = {}

        def register(self):
            """Register current model parameters as shadow weights."""
            for name, param in self.model.named_parameters():
                if param.requires_grad:
                    self.shadow[name] = param.data.clone()

        def update(self):
            """Update shadow weights with EMA."""
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    new_average = (
                        1.0 - self.decay
                    ) * param.data + self.decay * self.shadow[name]
                    self.shadow[name] = new_average.clone()

        def apply_shadow(self):
            """Replace model weights with shadow weights for evaluation."""
            for name, param in self.model.named_parameters():
                if param.requires_grad and name in self.shadow:
                    self.backup[name] = param.data.clone()
                    param.data = self.shadow[name].clone()

        def restore(self):
            """Restore original model weights after evaluation."""
            for name, param in self.model.named_parameters():
                if name in self.backup:
                    param.data = self.backup[name].clone()
            self.backup = {}

    # ========================================================================
    # Configuration Setup
    # ========================================================================

    config = SigLIP2TrainingConfigV2(**(config_dict or {}))
    if test_mode:
        config.phase1_epochs = 1
        config.phase2_epochs = 1
        config.total_epochs = 2
        config.batch_size = 4
        config.gradient_accumulation_steps = 2
        config.use_ema = False
        print("[TEST MODE] Running quick validation with 2 epochs")

    print("=" * 70)
    print("SigLIP 2 IQA Training v2.0 (Tier 1+2+3 Improvements)")
    print("=" * 70)
    print(f"Model: {config.model_id} ({config.model_variant})")
    print(f"Max Patches: {config.max_num_patches} (up from 576)")
    print(f"Total Epochs: {config.total_epochs} (15 warmup + 60 fine-tuning)")
    print(
        f"Batch Size: {config.batch_size} x {config.gradient_accumulation_steps} = {config.batch_size * config.gradient_accumulation_steps}"
    )
    print("Scheduler: CosineAnnealingLR (replaces OneCycleLR)")
    print(f"LLRD: {config.use_llrd} (decay={config.llrd_decay})")
    print(f"PCGrad: {config.use_pcgrad}")
    print(f"Ranking Loss: {config.use_ranking_loss} (λ={config.ranking_loss_weight})")
    print(f"EMA: {config.use_ema} (starts epoch {config.ema_start_epoch})")
    print(f"Gradient Checkpointing: {config.use_gradient_checkpointing}")
    print(
        f"Mixed Precision: {config.use_mixed_precision} ({config.mixed_precision_dtype})"
    )
    print(f"Early Stopping Patience: {config.early_stopping_patience}")
    print(f"Target SRCC: {config.target_srcc}")
    print(f"Target VQualA: {config.target_vquala}")
    print("=" * 70)

    # ========================================================================
    # Mixed Precision Setup (TIER 3)
    # ========================================================================

    # Determine mixed precision dtype
    if config.use_mixed_precision:
        if (
            config.mixed_precision_dtype == "bfloat16"
            and torch.cuda.is_bf16_supported()
        ):
            amp_dtype = torch.bfloat16
            print("Mixed precision: BF16 enabled (recommended for A100)")
        else:
            amp_dtype = torch.float16
            print("Mixed precision: FP16 enabled")
        scaler = torch.amp.GradScaler("cuda") if amp_dtype == torch.float16 else None
    else:
        amp_dtype = torch.float32
        scaler = None
        print("Mixed precision: Disabled (FP32)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # ========================================================================
    # Loss Functions
    # ========================================================================

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
        """Margin ranking loss for direct SRCC optimization (TIER 2).

        Creates pairwise comparisons within a batch and optimizes for correct ranking.
        """

        def __init__(self, margin: float = 0.0):
            super().__init__()
            self.margin = margin
            self.loss_fn = nn.MarginRankingLoss(margin=margin)

        def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            # Create all pairs
            n = pred.size(0)
            if n < 2:
                return torch.tensor(0.0, device=pred.device)

            # Generate pairs
            idx_i, idx_j = torch.triu_indices(n, n, offset=1, device=pred.device)

            pred_i = pred[idx_i]
            pred_j = pred[idx_j]
            target_i = target[idx_i]
            target_j = target[idx_j]

            # y = +1 if target_i > target_j, else -1
            y = torch.sign(target_i - target_j)

            # Filter out ties (y == 0)
            mask = y != 0
            if mask.sum() == 0:
                return torch.tensor(0.0, device=pred.device)

            return self.loss_fn(pred_i[mask], pred_j[mask], y[mask])

    # ========================================================================
    # Model Definition
    # ========================================================================

    class SigLIP2DocumentIQAv2(nn.Module):
        """SigLIP 2 NaFlex with multi-task IQA heads + uncertainty (v2)."""

        def __init__(
            self,
            model_id: str = "google/siglip2-base-patch16-naflex",
            uncertainty: bool = True,
        ):
            super().__init__()

            self.backbone = AutoModel.from_pretrained(model_id)
            embed_dim = self.backbone.config.vision_config.hidden_size
            self.uncertainty = uncertainty

            head_output_dim = 2 if uncertainty else 1

            self.heads = nn.ModuleDict(
                {
                    "overall": self._make_head(embed_dim, head_output_dim),
                    "sharpness": self._make_head(embed_dim, head_output_dim),
                    "color": self._make_head(embed_dim, head_output_dim),
                }
            )

            # Calibration temperatures
            self.register_buffer("temp_overall", torch.tensor(1.0))
            self.register_buffer("temp_sharpness", torch.tensor(1.0))
            self.register_buffer("temp_color", torch.tensor(1.0))

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
            # SigLIP 2 uses vision_model.encoder.layers
            encoder = self.backbone.vision_model.encoder
            num_layers = len(encoder.layers)

            groups = []
            # Embeddings (deepest - lowest LR)
            groups.append(list(self.backbone.vision_model.embeddings.parameters()))

            # Encoder layers
            for layer in encoder.layers:
                groups.append(list(layer.parameters()))

            # Post layer norm
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

    # ========================================================================
    # LLRD Optimizer Setup (TIER 2)
    # ========================================================================

    def get_llrd_param_groups(
        model: SigLIP2DocumentIQAv2,
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

        # Heads get base LR
        param_groups.append(
            {
                "params": list(model.heads.parameters()),
                "lr": base_lr,
                "weight_decay": weight_decay,
                "name": "heads",
            }
        )

        # Backbone layers with LLRD
        layer_groups = model.get_layer_groups()
        num_layers = len(layer_groups)

        for i, params in enumerate(reversed(layer_groups)):
            # Layer 0 (shallowest) = base_lr * llrd_decay
            # Layer n (deepest) = base_lr * llrd_decay^(n+1)
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

    # ========================================================================
    # GCS Download Functions
    # ========================================================================

    def download_diqa5000_from_gcs(data_dir: Path) -> bool:
        """Download original DIQA-5000 dataset from GCS."""
        import os

        from google.cloud import storage

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

        marker_file = data_dir / ".download_complete"
        if marker_file.exists():
            all_csvs_exist = all(
                (data_dir / split / f"{split}.csv").exists()
                for split in DIQA5000_SPLITS
            )
            if all_csvs_exist:
                print("DIQA-5000 already downloaded and validated, skipping...")
                return True
            marker_file.unlink()

        print(f"Downloading DIQA-5000 from gs://{GCS_BUCKET}/{GCS_PREFIX}/")
        start_time = time.time()

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)

        data_dir.mkdir(parents=True, exist_ok=True)
        downloaded = 0

        for split in DIQA5000_SPLITS:
            split_dir = data_dir / split
            split_dir.mkdir(exist_ok=True)
            (split_dir / "res").mkdir(exist_ok=True)
            (split_dir / "ori").mkdir(exist_ok=True)

            prefix = f"{GCS_PREFIX}/{split}/"
            blobs = bucket.list_blobs(prefix=prefix)

            for blob in blobs:
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
                    print(f"  Downloaded {downloaded} files...")

        elapsed = time.time() - start_time
        print(f"Downloaded {downloaded} files in {elapsed:.1f}s")

        if downloaded < 100:
            print(f"ERROR: Only downloaded {downloaded} files, expected thousands!")
            return False

        for split in DIQA5000_SPLITS:
            csv_path = data_dir / split / f"{split}.csv"
            if not csv_path.exists():
                print(f"ERROR: Missing CSV at {csv_path}")
                return False
            print(f"  Verified: {csv_path}")

        marker_file.touch()
        return True

    # ========================================================================
    # Dataset
    # ========================================================================

    class DIQA5000Dataset(Dataset):
        """Original DIQA-5000 dataset with human MOS labels."""

        def __init__(
            self,
            split: str,
            data_dir: str | Path,
            processor: AutoProcessor,
            max_num_patches: int = 784,
            use_augmentation: bool = False,
            horizontal_flip_prob: float = 0.5,
            random_crop_prob: float = 0.3,
        ):
            import csv

            self.split = split
            self.data_dir = Path(data_dir)
            self.processor = processor
            self.max_num_patches = max_num_patches
            self.use_augmentation = use_augmentation and split == "train"
            self.horizontal_flip_prob = horizontal_flip_prob
            self.random_crop_prob = random_crop_prob
            self.samples = []

            split_dir = self.data_dir / split
            csv_path = split_dir / f"{split}.csv"
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

            print(f"  {split}: {len(self.samples)} samples loaded")

        def __len__(self) -> int:
            return len(self.samples)

        def _normalize_mos(self, score: float) -> float:
            """Normalize MOS score from 1-5 to 0-1 range."""
            return (score - 1.0) / 4.0

        def _apply_safe_augmentations(self, image: Image.Image) -> Image.Image:
            """Apply quality-preserving augmentations only."""
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

    # ========================================================================
    # Training Setup
    # ========================================================================

    print("\nLoading SigLIP 2 processor and model...")
    processor = AutoProcessor.from_pretrained(config.model_id)
    model = SigLIP2DocumentIQAv2(
        model_id=config.model_id,
        uncertainty=config.uncertainty,
    )

    # Enable gradient checkpointing (TIER 3) - must be done before moving to device
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

    # Download DIQA-5000
    print("\nDownloading DIQA-5000 dataset from GCS...")
    data_dir = Path("/data/diqa5000")
    download_diqa5000_from_gcs(data_dir)
    diqa5000_volume.commit()

    # Create datasets
    print("\nLoading DIQA-5000 dataset...")
    train_dataset = DIQA5000Dataset(
        split="train",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
        use_augmentation=config.use_augmentation,
        horizontal_flip_prob=config.horizontal_flip_prob,
        random_crop_prob=config.random_crop_prob,
    )
    val_dataset = DIQA5000Dataset(
        split="val",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
    )
    test_dataset = DIQA5000Dataset(
        split="test",
        data_dir=data_dir,
        processor=processor,
        max_num_patches=config.max_num_patches,
    )

    if test_mode:
        train_dataset.samples = train_dataset.samples[:50]
        val_dataset.samples = val_dataset.samples[:25]
        test_dataset.samples = test_dataset.samples[:25]

    def custom_collate_fn(batch):
        pixel_values = torch.stack([item["pixel_values"] for item in batch])
        spatial_shapes = torch.stack([item["spatial_shapes"] for item in batch])
        pixel_attention_mask = torch.stack(
            [item["pixel_attention_mask"] for item in batch]
        )
        labels = [item["labels"] for item in batch]
        image_ids = [item["image_id"] for item in batch]
        return {
            "pixel_values": pixel_values,
            "spatial_shapes": spatial_shapes,
            "pixel_attention_mask": pixel_attention_mask,
            "labels": labels,
            "image_ids": image_ids,
        }

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        collate_fn=custom_collate_fn,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=custom_collate_fn,
    )

    # Loss functions
    gnll_criterion = GaussianNLLLoss()
    nin_criterion = NormInNormLoss(p=1.0, q=2.0)
    ranking_criterion = MarginRankingLoss() if config.use_ranking_loss else None

    # ========================================================================
    # Training Loop
    # ========================================================================

    def compute_loss(
        outputs: dict,
        labels: list[dict],
        use_ranking: bool = False,
    ) -> tuple[torch.Tensor, list[torch.Tensor]]:
        """Compute combined loss for all dimensions."""
        losses = []

        for dim in ["overall", "sharpness", "color"]:
            target = torch.tensor(
                [lbl[dim] for lbl in labels], device=device, dtype=torch.float32
            )

            if config.uncertainty:
                pred = outputs[dim]
                # GaussianNLL for uncertainty
                gnll_loss = gnll_criterion(pred["mu"], pred["sigma_sq"], target)

                if use_ranking and ranking_criterion is not None:
                    # Ranking loss for SRCC
                    rank_loss = ranking_criterion(pred["mu"], target)
                    loss = gnll_loss + config.ranking_loss_weight * rank_loss
                else:
                    loss = gnll_loss
            else:
                pred_scores = outputs[dim]
                nin_loss = nin_criterion(pred_scores, target)

                if use_ranking and ranking_criterion is not None:
                    rank_loss = ranking_criterion(pred_scores, target)
                    loss = nin_loss + config.ranking_loss_weight * rank_loss
                else:
                    loss = nin_loss

            losses.append(loss)

        total_loss = sum(losses) / len(losses)
        return total_loss, losses

    def validate(loader: DataLoader, use_ema_model: bool = False) -> dict[str, float]:
        """Validate model and compute metrics."""
        model.eval()
        all_preds = {dim: [] for dim in ["overall", "sharpness", "color"]}
        all_labels = {dim: [] for dim in ["overall", "sharpness", "color"]}
        total_loss = 0.0

        with torch.no_grad():
            for batch in loader:
                pixel_values = batch["pixel_values"].to(device)
                spatial_shapes = batch["spatial_shapes"].to(device)
                labels_list = batch["labels"]

                # TIER 3: Mixed precision inference
                with torch.amp.autocast(
                    device_type="cuda",
                    dtype=amp_dtype,
                    enabled=config.use_mixed_precision,
                ):
                    outputs = model(pixel_values, spatial_shapes)
                    loss, _ = compute_loss(outputs, labels_list, use_ranking=False)

                total_loss += loss.item()

                for dim in ["overall", "sharpness", "color"]:
                    if config.uncertainty:
                        preds = outputs[dim]["mu"].cpu().numpy()
                    else:
                        preds = outputs[dim].cpu().numpy()

                    all_preds[dim].extend(preds)
                    all_labels[dim].extend([lbl[dim] for lbl in labels_list])

        import numpy as np

        srcc = {}
        for dim in ["overall", "sharpness", "color"]:
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

    # Training state
    history = []
    best_vquala = 0.0
    best_checkpoint = None
    patience_counter = 0

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize EMA (TIER 2)
    ema = EMA(model, decay=config.ema_decay) if config.use_ema else None

    # ========================================================================
    # Phase 1: Head Warmup (Frozen Backbone)
    # ========================================================================

    print("\n" + "=" * 70)
    print("Phase 1: Head Warmup (Frozen Backbone)")
    print("=" * 70)

    model.freeze_backbone()

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )

    if config.use_pcgrad:
        pcgrad_optimizer = PCGrad(optimizer)

    # CosineAnnealingLR for Phase 1 (TIER 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase1_epochs * len(train_loader),
        eta_min=config.min_lr,
    )

    for epoch in range(config.phase1_epochs):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0
        accum_steps = 0

        optimizer.zero_grad()

        for batch_idx, batch in enumerate(
            tqdm(
                train_loader, desc=f"Phase 1 - Epoch {epoch + 1}/{config.phase1_epochs}"
            )
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            # TIER 3: Mixed precision forward pass
            with torch.amp.autocast(
                device_type="cuda", dtype=amp_dtype, enabled=config.use_mixed_precision
            ):
                outputs = model(pixel_values, spatial_shapes)

                if config.use_pcgrad:
                    # PCGrad: separate losses per dimension
                    losses = []
                    for dim in ["overall", "sharpness", "color"]:
                        target = torch.tensor(
                            [lbl[dim] for lbl in labels_list],
                            device=device,
                            dtype=torch.float32,
                        )
                        if config.uncertainty:
                            loss = gnll_criterion(
                                outputs[dim]["mu"], outputs[dim]["sigma_sq"], target
                            )
                        else:
                            loss = nin_criterion(outputs[dim], target)
                        losses.append(loss / config.gradient_accumulation_steps)
                else:
                    loss, _ = compute_loss(
                        outputs, labels_list, use_ranking=config.use_ranking_loss
                    )
                    loss = loss / config.gradient_accumulation_steps

            # Backward pass (outside autocast, handles scaler for FP16)
            if config.use_pcgrad:
                pcgrad_optimizer.pc_backward(losses)
                train_loss += sum(loss_val.item() for loss_val in losses)
            else:
                if scaler is not None:
                    scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss += loss.item()

            accum_steps += 1

            # Gradient accumulation step
            if accum_steps >= config.gradient_accumulation_steps:
                if scaler is not None:
                    # FP16: unscale before clipping
                    scaler.unscale_(optimizer)

                if config.gradient_clip > 0:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), config.gradient_clip
                    )

                if config.use_pcgrad:
                    pcgrad_optimizer.step()
                elif scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()

                scheduler.step()
                optimizer.zero_grad()
                accum_steps = 0

        # Handle remaining gradients
        if accum_steps > 0:
            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
            optimizer.step()
            optimizer.zero_grad()

        train_loss = train_loss * config.gradient_accumulation_steps / len(train_loader)

        # Validation
        val_metrics = validate(val_loader)
        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        history.append(
            {
                "phase": 1,
                "epoch": epoch + 1,
                "train_loss": train_loss,
                **val_metrics,
                "lr": current_lr,
                "time": epoch_time,
            }
        )

        print(f"\nPhase 1 - Epoch {epoch + 1}/{config.phase1_epochs}:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
        print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
        print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
        print(f"  VQualA: {val_metrics['vquala']:.4f}")
        print(f"  LR: {current_lr:.2e}, Time: {epoch_time:.1f}s")

        if val_metrics["vquala"] > best_vquala:
            best_vquala = val_metrics["vquala"]
            best_checkpoint = {
                "epoch": epoch + 1,
                "phase": 1,
                "model_state_dict": model.state_dict(),
                "config": config.to_dict(),
                "metrics": val_metrics,
            }
            torch.save(best_checkpoint, output_dir / "siglip2_iqa_best.pt")
            print("  ✓ New best VQualA! Saved checkpoint.")
            patience_counter = 0
        else:
            patience_counter += 1

    # ========================================================================
    # Phase 2: Full Fine-Tuning with LLRD (TIER 2)
    # ========================================================================

    print("\n" + "=" * 70)
    print("Phase 2: Full Fine-Tuning with LLRD")
    print("=" * 70)

    model.unfreeze_backbone()

    # Create optimizer with LLRD (TIER 2)
    if config.use_llrd:
        param_groups = get_llrd_param_groups(
            model,
            base_lr=config.phase2_lr,
            llrd_decay=config.llrd_decay,
            weight_decay=config.weight_decay,
        )
        optimizer = torch.optim.AdamW(param_groups)
        print(f"  LLRD enabled: {len(param_groups)} parameter groups")
        for pg in param_groups[:3]:  # Print first few
            print(f"    {pg['name']}: lr={pg['lr']:.2e}")
        print("    ...")
    else:
        optimizer = torch.optim.AdamW(
            [
                {"params": model.backbone.parameters(), "lr": config.phase2_lr * 0.1},
                {"params": model.heads.parameters(), "lr": config.phase2_lr},
            ],
            weight_decay=config.weight_decay,
        )

    if config.use_pcgrad:
        pcgrad_optimizer = PCGrad(optimizer)

    # CosineAnnealingLR for Phase 2 (TIER 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase2_epochs * len(train_loader),
        eta_min=config.min_lr,
    )

    # Initialize EMA after Phase 1
    if ema is not None:
        ema.register()
        print("  EMA registered")

    for epoch in range(config.phase2_epochs):
        global_epoch = config.phase1_epochs + epoch + 1
        epoch_start = time.time()
        model.train()
        train_loss = 0.0
        accum_steps = 0

        optimizer.zero_grad()

        for batch_idx, batch in enumerate(
            tqdm(
                train_loader, desc=f"Phase 2 - Epoch {epoch + 1}/{config.phase2_epochs}"
            )
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            # TIER 3: Mixed precision forward pass
            with torch.amp.autocast(
                device_type="cuda", dtype=amp_dtype, enabled=config.use_mixed_precision
            ):
                outputs = model(pixel_values, spatial_shapes)

                # TIER 2: Use PCGrad with gradient accumulation
                if config.use_pcgrad:
                    losses = []
                    for dim in ["overall", "sharpness", "color"]:
                        target = torch.tensor(
                            [lbl[dim] for lbl in labels_list],
                            device=device,
                            dtype=torch.float32,
                        )
                        if config.uncertainty:
                            gnll_loss = gnll_criterion(
                                outputs[dim]["mu"], outputs[dim]["sigma_sq"], target
                            )
                            if config.use_ranking_loss:
                                rank_loss = ranking_criterion(
                                    outputs[dim]["mu"], target
                                )
                                loss = (
                                    gnll_loss + config.ranking_loss_weight * rank_loss
                                )
                            else:
                                loss = gnll_loss
                        else:
                            nin_loss = nin_criterion(outputs[dim], target)
                            if config.use_ranking_loss:
                                rank_loss = ranking_criterion(outputs[dim], target)
                                loss = nin_loss + config.ranking_loss_weight * rank_loss
                            else:
                                loss = nin_loss

                        losses.append(loss / config.gradient_accumulation_steps)
                else:
                    loss, _ = compute_loss(
                        outputs, labels_list, use_ranking=config.use_ranking_loss
                    )
                    loss = loss / config.gradient_accumulation_steps

            # Backward pass (outside autocast, handles scaler for FP16)
            if config.use_pcgrad:
                pcgrad_optimizer.pc_backward(losses)
                train_loss += sum(loss_val.item() for loss_val in losses)
            else:
                if scaler is not None:
                    scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss += loss.item()

            accum_steps += 1

            if accum_steps >= config.gradient_accumulation_steps:
                if scaler is not None:
                    # FP16: unscale before clipping
                    scaler.unscale_(optimizer)

                if config.gradient_clip > 0:
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), config.gradient_clip
                    )

                if config.use_pcgrad:
                    pcgrad_optimizer.step()
                elif scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()

                scheduler.step()
                optimizer.zero_grad()
                accum_steps = 0

                # EMA update (TIER 2)
                if ema is not None and global_epoch >= config.ema_start_epoch:
                    ema.update()

        # Handle remaining gradients
        if accum_steps > 0:
            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
            optimizer.step()
            optimizer.zero_grad()

        train_loss = train_loss * config.gradient_accumulation_steps / len(train_loader)

        # Validation (use EMA model if available and in EMA phase)
        if ema is not None and global_epoch >= config.ema_start_epoch:
            ema.apply_shadow()
            val_metrics = validate(val_loader, use_ema_model=True)
            ema.restore()
            print("  (EMA model used for validation)")
        else:
            val_metrics = validate(val_loader)

        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]["lr"]

        history.append(
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

        print(
            f"\nPhase 2 - Epoch {epoch + 1}/{config.phase2_epochs} (Global: {global_epoch}):"
        )
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
        print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
        print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
        print(f"  VQualA: {val_metrics['vquala']:.4f}")
        print(f"  LR: {current_lr:.2e}, Time: {epoch_time:.1f}s")

        if val_metrics["vquala"] > best_vquala:
            best_vquala = val_metrics["vquala"]

            # Save EMA weights if active
            if ema is not None and global_epoch >= config.ema_start_epoch:
                ema.apply_shadow()
                model_state = copy.deepcopy(model.state_dict())
                ema.restore()
            else:
                model_state = model.state_dict()

            best_checkpoint = {
                "epoch": global_epoch,
                "phase": 2,
                "model_state_dict": model_state,
                "config": config.to_dict(),
                "metrics": val_metrics,
                "ema_active": ema is not None
                and global_epoch >= config.ema_start_epoch,
            }
            torch.save(best_checkpoint, output_dir / "siglip2_iqa_best.pt")
            print("  ✓ New best VQualA! Saved checkpoint.")
            patience_counter = 0
        else:
            patience_counter += 1

        # Periodic checkpoint
        if (epoch + 1) % config.save_every_n_epochs == 0:
            checkpoint = {
                "epoch": global_epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "config": config.to_dict(),
                "metrics": val_metrics,
            }
            torch.save(checkpoint, output_dir / f"siglip2_iqa_epoch{global_epoch}.pt")

        # Early stopping
        if patience_counter >= config.early_stopping_patience:
            print(
                f"\nEarly stopping triggered after {patience_counter} epochs without improvement."
            )
            print(f"Best VQualA achieved: {best_vquala:.4f}")
            break

        # Log if target achieved
        if (
            val_metrics["vquala"] >= config.target_vquala
            and val_metrics["srcc_overall"] >= config.target_srcc
        ):
            print("  ✓ Target metrics achieved! Continuing to maximize performance...")

    # ========================================================================
    # Post-hoc Calibration
    # ========================================================================

    if config.uncertainty:
        print("\n" + "=" * 70)
        print("Post-hoc STD Scaling Calibration")
        print("=" * 70)

        import numpy as np

        best_state = torch.load(output_dir / "siglip2_iqa_best.pt")
        model.load_state_dict(best_state["model_state_dict"])
        model.eval()

        predictions = {dim: [] for dim in ["overall", "sharpness", "color"]}
        uncertainties = {dim: [] for dim in ["overall", "sharpness", "color"]}
        targets = {dim: [] for dim in ["overall", "sharpness", "color"]}

        with torch.no_grad():
            for batch in val_loader:
                pixel_values = batch["pixel_values"].to(device)
                spatial_shapes = batch["spatial_shapes"].to(device)
                labels_list = batch["labels"]

                # TIER 3: Mixed precision inference
                with torch.amp.autocast(
                    device_type="cuda",
                    dtype=amp_dtype,
                    enabled=config.use_mixed_precision,
                ):
                    outputs = model(pixel_values, spatial_shapes)

                for dim in ["overall", "sharpness", "color"]:
                    predictions[dim].extend(outputs[dim]["mu"].cpu().numpy())
                    uncertainties[dim].extend(outputs[dim]["sigma_sq"].cpu().numpy())
                    targets[dim].extend([lbl[dim] for lbl in labels_list])

        calibration_temps = {}
        for dim in ["overall", "sharpness", "color"]:
            preds = np.array(predictions[dim])
            uncerts = np.array(uncertainties[dim])
            targs = np.array(targets[dim])

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
            optimal_temperature = result.x
            calibration_temps[dim] = optimal_temperature

            srcc, _ = spearmanr(preds, targs)
            print(f"  {dim}: T={optimal_temperature:.3f}, SRCC={srcc:.4f}")

        model.set_calibration_temps(calibration_temps)
        best_checkpoint["model_state_dict"] = model.state_dict()
        best_checkpoint["calibration_temps"] = calibration_temps
        torch.save(best_checkpoint, output_dir / "siglip2_iqa_best.pt")
        print("  ✓ Saved calibrated model")

    # ========================================================================
    # Final Test Evaluation
    # ========================================================================

    print("\n" + "=" * 70)
    print("Final Evaluation on Test Set")
    print("=" * 70)

    best_state = torch.load(output_dir / "siglip2_iqa_best.pt")
    model.load_state_dict(best_state["model_state_dict"])

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        collate_fn=custom_collate_fn,
    )

    test_metrics = validate(test_loader)

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
        print("\n✓ TARGET ACHIEVED! Model ready for production.")
    else:
        print(f"\n✗ Target not achieved. Best VQualA: {best_vquala:.4f}")
        print(f"  Gap to target: {config.target_vquala - test_metrics['vquala']:.4f}")

    # ========================================================================
    # Save Results
    # ========================================================================

    results = {
        "config": config.to_dict(),
        "best_vquala": best_vquala,
        "test_results": {
            "srcc_overall": test_metrics["srcc_overall"],
            "srcc_sharpness": test_metrics["srcc_sharpness"],
            "srcc_color": test_metrics["srcc_color"],
            "vquala": test_metrics["vquala"],
        },
        "target_achieved": target_achieved,
        "history": history,
        "checkpoint_path": str(output_dir / "siglip2_iqa_best.pt"),
        "timestamp": datetime.now().isoformat(),
        "improvements": {
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
                f"MarginRankingLoss (λ={config.ranking_loss_weight})"
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
        },
    }

    if config.uncertainty:
        results["calibration_temps"] = calibration_temps

    results_path = output_dir / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print(f"Best checkpoint: {output_dir / 'siglip2_iqa_best.pt'}")

    results_volume.commit()

    return results


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
    print("=" * 70)
    print("SigLIP 2 IQA Training v2.0 (Tier 1+2+3 Improvements)")
    print("=" * 70)
    print(f"Test mode: {test}")
    print(f"Model: {model} ({MODEL_VARIANTS.get(model, 'unknown')})")
    print(f"Epochs: {epochs if not test else 2}")
    print(f"Batch size: {batch_size} x {accumulation} = {batch_size * accumulation}")
    print(f"Max patches: {max_patches}")
    print(f"LLRD: {not no_llrd}")
    print(f"Ranking Loss: {not no_ranking_loss}")
    print(f"PCGrad: {not no_pcgrad}")
    print(f"EMA: {not no_ema}")
    print(f"Uncertainty: {not no_uncertainty}")
    print(f"Gradient Checkpointing: {not no_gradient_checkpointing}")
    print(f"Mixed Precision: {not no_mixed_precision} ({'fp16' if fp16 else 'bf16'})")
    print("=" * 70)

    config = SigLIP2TrainingConfigV2(
        model_variant=model,
        total_epochs=epochs,
        phase1_epochs=min(15, epochs // 5),
        phase2_epochs=epochs - min(15, epochs // 5),
        batch_size=batch_size,
        gradient_accumulation_steps=accumulation,
        max_num_patches=max_patches,
        use_llrd=not no_llrd,
        use_ranking_loss=not no_ranking_loss,
        use_pcgrad=not no_pcgrad,
        use_ema=not no_ema,
        uncertainty=not no_uncertainty,
        use_gradient_checkpointing=not no_gradient_checkpointing,
        use_mixed_precision=not no_mixed_precision,
        mixed_precision_dtype="float16" if fp16 else "bfloat16",
    )

    result = train_siglip2_iqa_v2.remote(
        config_dict=config.to_dict(),
        test_mode=test,
    )

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
        print("\n✓ Model ready for production!")
        print("Next steps:")
        print("  1. Download checkpoint:")
        print(
            "     modal volume get siglip2-iqa-results /results/siglip2_v2/siglip2_iqa_best.pt ./checkpoints/"
        )
        print("  2. Run inference on new documents")
        print("  3. Consider training 400M variant for further gains")
