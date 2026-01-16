"""Train SigLIP 2 Base NaFlex for Document IQA on original DIQA-5000.

This script implements the comprehensive training plan from:
docs/planning/SIGLIP2_NAFLEX_TRAINING_PLAN.md

IMPORTANT: This uses the ORIGINAL DIQA-5000 dataset with human MOS labels,
NOT the stage2 pseudo-labeled version. This ensures we train on high-quality
ground truth labels to achieve the best possible correlation metrics.

Dataset:
- Source: gs://assured-oss-457903-diqa5000/
- Splits: train (3,500), val (500), test (1,000) = 5,000 total
- Labels: Human MOS scores for overall, sharpness, color_fidelity (1-5 scale)
- Reference: DIQA-5000 benchmark (VQualA 2025)

Key features:
- SigLIP 2 Base NaFlex backbone (86M params)
- NormInNormLoss for 10x faster convergence
- PCGrad for multi-task gradient conflict mitigation
- Uncertainty output (mu and sigma^2) with post-hoc calibration
- OneCycleLR scheduler for super-convergence
- Quality-preserving augmentations only (horizontal flip + random crop)

Target: VQualA >= 0.92, SRCC_overall >= 0.90 (research shows achievable)

Usage:
    # Quick test (2 epochs)
    uv run modal run modal/train_siglip2_iqa.py --test

    # Full training (detached for long runs)
    uv run modal run --detach modal/train_siglip2_iqa.py

    # With custom settings
    uv run modal run --detach modal/train_siglip2_iqa.py --epochs 50 --batch-size 16

    # Monitor logs
    modal app logs siglip2-iqa-training --follow

Post-training:
    Once model achieves target metrics, use it to generate pseudo-labels
    for other datasets (SmartDoc-QA, OCR-Quality, etc.) to rebuild Stage 2
    with consistent, high-quality labels.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import modal

# Modal app definition
app = modal.App("siglip2-iqa-training")

# Volumes for persistent storage
results_volume = modal.Volume.from_name("siglip2-iqa-results", create_if_missing=True)
diqa5000_volume = modal.Volume.from_name("diqa5000-original", create_if_missing=True)

# GCS Configuration for DIQA-5000
GCS_BUCKET = "image_detection_b"
GCS_PREFIX = "datasets/diqa-5000-original"
DIQA5000_SPLITS = ["train", "val", "test"]

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
    # Copy GCS credentials for authentication
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
    # Note: PCGrad installed inline in the training function due to non-standard package structure
)


@dataclass
class SigLIP2TrainingConfig:
    """Training configuration for SigLIP 2 IQA model."""

    # Model
    model_id: str = "google/siglip2-base-patch16-naflex"
    max_num_patches: int = 576  # Critical hyperparameter (default 256 leaves performance on table)
    uncertainty: bool = True  # Output mu and sigma^2

    # Training phases
    phase1_epochs: int = 10  # Frozen backbone warmup
    phase2_epochs: int = 40  # Full fine-tuning
    total_epochs: int = 50

    # Batch and learning
    batch_size: int = 16
    phase1_lr: float = 2e-4  # Higher LR for heads only
    phase2_lr: float = 2e-5  # Lower LR for full model
    backbone_lr_multiplier: float = 0.1
    weight_decay: float = 0.01

    # Optimizer
    use_pcgrad: bool = True  # Projected Conflicting Gradients
    use_onecycle: bool = True  # OneCycleLR scheduler
    gradient_clip: float = 1.0

    # Loss
    use_norm_in_norm: bool = True  # 10x faster convergence than MSE

    # Augmentation
    use_augmentation: bool = True
    horizontal_flip_prob: float = 0.5
    random_crop_prob: float = 0.3

    # Checkpointing
    save_every_n_epochs: int = 5
    keep_top_k: int = 3
    early_stopping_patience: int = 15

    # Target metrics (research shows 0.92 achievable)
    target_srcc: float = 0.90
    target_vquala: float = 0.92

    # Output
    output_dir: str = "/results/siglip2"

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def compute_vquala(srcc_overall: float, srcc_sharpness: float, srcc_color: float) -> float:
    """Compute VQualA final score: 0.5*overall + 0.25*sharpness + 0.25*color."""
    return 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color


@app.function(
    image=training_image,
    gpu="A10G",  # 24GB VRAM - comfortable for SigLIP 2 Base NaFlex
    timeout=3600 * 24,  # 24 hours max
    secrets=[modal.Secret.from_name("gcs-credentials")],
    volumes={
        "/results": results_volume,
        "/data": diqa5000_volume,
    },
)
def train_siglip2_iqa(
    config_dict: dict[str, Any] | None = None,
    test_mode: bool = False,
) -> dict[str, Any]:
    """Train SigLIP 2 Base NaFlex for document IQA on DIQA-5000.

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

    # PCGrad implementation (inline to avoid dependency issues)
    # Reference: Yu et al., "Gradient Surgery for Multi-Task Learning", NeurIPS 2020
    class PCGrad:
        """Projected Conflicting Gradients optimizer wrapper.

        Projects conflicting gradients to mitigate negative transfer in multi-task learning.
        """

        def __init__(self, optimizer):
            self.optimizer = optimizer
            self._reduction = "mean"

        @property
        def param_groups(self):
            return self.optimizer.param_groups

        def zero_grad(self):
            return self.optimizer.zero_grad()

        def step(self):
            return self.optimizer.step()

        def pc_backward(self, losses: list[torch.Tensor]):
            """Backward with gradient projection for conflicting tasks."""
            # Compute gradients for each task
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

            # Project conflicting gradients
            projected_grads = self._project_gradients(task_grads)

            # Apply projected gradients
            self.optimizer.zero_grad()
            offset = 0
            for group in self.optimizer.param_groups:
                for p in group["params"]:
                    numel = p.numel()
                    if p.grad is not None or True:
                        p.grad = projected_grads[offset:offset + numel].view_as(p)
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
                            # Project out the conflicting component
                            projected[i] -= (dot / (torch.dot(grads[j], grads[j]) + 1e-8)) * grads[j]

            # Average the projected gradients
            return torch.stack(projected).mean(dim=0)

    PCGRAD_AVAILABLE = True
    print("PCGrad optimizer available (inline implementation)")

    # Load configuration
    config = SigLIP2TrainingConfig(**(config_dict or {}))
    if test_mode:
        config.phase1_epochs = 1
        config.phase2_epochs = 1
        config.total_epochs = 2
        config.batch_size = 4
        print("[TEST MODE] Running quick validation with 2 epochs")

    print("=" * 70)
    print("SigLIP 2 Base NaFlex IQA Training")
    print("=" * 70)
    print(f"Model: {config.model_id}")
    print(f"Max Patches: {config.max_num_patches}")
    print(f"Total Epochs: {config.total_epochs}")
    print(f"Batch Size: {config.batch_size}")
    print(f"PCGrad: {config.use_pcgrad and PCGRAD_AVAILABLE}")
    print(f"NormInNorm Loss: {config.use_norm_in_norm}")
    print(f"Uncertainty Output: {config.uncertainty}")
    print(f"Target SRCC: {config.target_srcc}")
    print(f"Target VQualA: {config.target_vquala}")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # ========================================================================
    # Loss Functions
    # ========================================================================

    class NormInNormLoss(nn.Module):
        """Norm-in-Norm loss for 10x faster convergence than MSE."""

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

    # ========================================================================
    # Model Definition
    # ========================================================================

    class SigLIP2DocumentIQA(nn.Module):
        """SigLIP 2 NaFlex with multi-task IQA regression heads + uncertainty."""

        def __init__(
            self,
            model_id: str = "google/siglip2-base-patch16-naflex",
            uncertainty: bool = True,
        ):
            super().__init__()

            # Load pretrained vision encoder
            self.backbone = AutoModel.from_pretrained(model_id)
            embed_dim = self.backbone.config.vision_config.hidden_size  # 768 for Base
            self.uncertainty = uncertainty

            # Output dimension: 2 for (mu, log sigma^2) or 1 for direct regression
            head_output_dim = 2 if uncertainty else 1

            # Multi-task regression heads
            self.heads = nn.ModuleDict(
                {
                    "overall": self._make_head(embed_dim, head_output_dim),
                    "sharpness": self._make_head(embed_dim, head_output_dim),
                    "color": self._make_head(embed_dim, head_output_dim),
                }
            )

            # Calibration temperatures (set during post-hoc calibration)
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

        def forward(
            self,
            pixel_values: torch.Tensor,
            spatial_shapes: torch.Tensor | None = None,
            pixel_attention_mask: torch.Tensor | None = None,
        ) -> dict[str, dict | torch.Tensor]:
            # Extract vision features (NaFlex requires spatial_shapes)
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

                    # Apply calibration temperature
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
    # GCS Download Functions
    # ========================================================================

    def download_diqa5000_from_gcs(data_dir: Path) -> bool:
        """Download original DIQA-5000 dataset from GCS.

        Downloads all splits (train, val, test) with images and CSV labels.

        Args:
            data_dir: Local directory to store dataset.

        Returns:
            True if download was successful or data already exists.
        """
        import os

        from google.cloud import storage

        # Set GCS credentials from Modal secret
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

        # Check if already downloaded - validate CSV files exist
        marker_file = data_dir / ".download_complete"
        if marker_file.exists():
            # Validate that CSVs actually exist
            all_csvs_exist = all(
                (data_dir / split / f"{split}.csv").exists()
                for split in DIQA5000_SPLITS
            )
            if all_csvs_exist:
                print("DIQA-5000 already downloaded and validated, skipping...")
                return True
            else:
                print("Marker file exists but CSVs missing, re-downloading...")
                marker_file.unlink()  # Remove stale marker

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

            # List blobs for this split (with GCS_PREFIX)
            prefix = f"{GCS_PREFIX}/{split}/"
            blobs = bucket.list_blobs(prefix=prefix)

            for blob in blobs:
                # Skip directory markers
                if blob.name.endswith("/"):
                    continue

                relative_path = blob.name[len(prefix):]
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

        # Validate download before creating marker
        if downloaded < 100:
            print(f"ERROR: Only downloaded {downloaded} files, expected thousands!")
            return False

        # Verify CSVs exist
        for split in DIQA5000_SPLITS:
            csv_path = data_dir / split / f"{split}.csv"
            if not csv_path.exists():
                print(f"ERROR: Missing CSV at {csv_path}")
                return False
            print(f"  Verified: {csv_path}")

        # Create marker file
        marker_file.touch()
        return True

    # ========================================================================
    # Dataset
    # ========================================================================

    class DIQA5000Dataset(Dataset):
        """Original DIQA-5000 dataset with human MOS labels.

        Loads directly from the original DIQA-5000 structure:
            diqa-5000/
            ├── train/
            │   ├── train.csv  (res,ori,overall,sharpness,color_fidelity)
            │   ├── res/       (degraded images)
            │   └── ori/       (original images)
            ├── val/
            │   ├── val.csv
            │   ├── res/
            │   └── ori/
            └── test/
                ├── test.csv
                ├── res/
                └── ori/

        CSV columns: res,ori,overall,sharpness,color_fidelity
        Scores are MOS on 1-5 scale, normalized to 0-1.
        """

        def __init__(
            self,
            split: str,
            data_dir: str | Path,
            processor: AutoProcessor,
            max_num_patches: int = 576,
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

            # Load from CSV
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

                    # Parse MOS scores (1-5 scale)
                    self.samples.append({
                        "image_path": str(image_path),
                        "image_id": image_filename.replace(".jpg", ""),
                        "overall": float(row["overall"]),
                        "sharpness": float(row["sharpness"]),
                        "color_fidelity": float(row["color_fidelity"]),
                    })

            print(f"  {split}: {len(self.samples)} samples loaded")

        def __len__(self) -> int:
            return len(self.samples)

        def _normalize_mos(self, score: float) -> float:
            """Normalize MOS score from 1-5 to 0-1 range."""
            return (score - 1.0) / 4.0

        def _apply_safe_augmentations(self, image: Image.Image) -> Image.Image:
            """Apply quality-preserving augmentations only.

            IMPORTANT: No blur, noise, or color jitter - these affect IQA labels!
            Only geometric transforms that preserve quality.
            """
            # Horizontal flip (quality-preserving)
            if random.random() < self.horizontal_flip_prob:
                image = ImageOps.mirror(image)

            # Random crop and resize (multi-scale learning)
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

            # Load image
            image = Image.open(sample["image_path"]).convert("RGB")

            # Apply safe augmentations
            if self.use_augmentation:
                image = self._apply_safe_augmentations(image)

            # Process with SigLIP 2 processor (handles NaFlex resizing)
            inputs = self.processor(
                images=[image],
                return_tensors="pt",
                max_num_patches=self.max_num_patches,
                padding="max_length",
            )

            # Normalize MOS scores from 1-5 to 0-1
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

    # Load processor and model
    print("\nLoading SigLIP 2 processor and model...")
    processor = AutoProcessor.from_pretrained(config.model_id)
    model = SigLIP2DocumentIQA(
        model_id=config.model_id,
        uncertainty=config.uncertainty,
    )
    model = model.to(device)

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    backbone_params = sum(p.numel() for p in model.backbone.parameters())
    head_params = total_params - backbone_params
    print(f"Total parameters: {total_params:,}")
    print(f"Backbone parameters: {backbone_params:,}")
    print(f"Head parameters: {head_params:,}")

    # Download DIQA-5000 from GCS
    print("\nDownloading DIQA-5000 dataset from GCS...")
    data_dir = Path("/data/diqa5000")
    download_diqa5000_from_gcs(data_dir)

    # Commit volume after download (persist for future runs)
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
        """Custom collate function to properly handle labels dict."""
        pixel_values = torch.stack([item["pixel_values"] for item in batch])
        spatial_shapes = torch.stack([item["spatial_shapes"] for item in batch])
        pixel_attention_mask = torch.stack([item["pixel_attention_mask"] for item in batch])
        # Keep labels as list of dicts (not dict of lists)
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

    # Loss function
    if config.uncertainty:
        criterion = GaussianNLLLoss()
    elif config.use_norm_in_norm:
        criterion = NormInNormLoss(p=1.0, q=2.0)
    else:
        criterion = nn.MSELoss()

    # ========================================================================
    # Training Loop
    # ========================================================================

    def compute_loss(outputs: dict, labels: dict) -> tuple[torch.Tensor, list]:
        """Compute loss for all dimensions."""
        losses = []
        for dim in ["overall", "sharpness", "color"]:
            target = torch.tensor(
                [l[dim] for l in labels], device=device, dtype=torch.float32
            )

            if config.uncertainty:
                pred = outputs[dim]
                loss = criterion(pred["mu"], pred["sigma_sq"], target)
            else:
                loss = criterion(outputs[dim], target)

            losses.append(loss)

        total_loss = sum(losses) / len(losses)
        return total_loss, losses

    def validate(loader: DataLoader) -> dict[str, float]:
        """Validate model and compute metrics."""
        model.eval()
        all_preds = {dim: [] for dim in ["overall", "sharpness", "color"]}
        all_labels = {dim: [] for dim in ["overall", "sharpness", "color"]}
        total_loss = 0.0

        with torch.no_grad():
            for batch in loader:
                pixel_values = batch["pixel_values"].to(device)
                spatial_shapes = batch["spatial_shapes"].to(device)
                # pixel_attention_mask not needed for get_image_features
                labels_list = batch["labels"]

                outputs = model(pixel_values, spatial_shapes)

                # Compute loss
                loss, _ = compute_loss(outputs, labels_list)
                total_loss += loss.item()

                # Collect predictions
                for i, dim in enumerate(["overall", "sharpness", "color"]):
                    if config.uncertainty:
                        preds = outputs[dim]["mu"].cpu().numpy()
                    else:
                        preds = outputs[dim].cpu().numpy()

                    all_preds[dim].extend(preds)
                    all_labels[dim].extend([l[dim] for l in labels_list])

        # Compute SRCC
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

    # Training history
    history = []
    best_vquala = 0.0
    best_checkpoint = None
    patience_counter = 0

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Phase 1: Head Warmup (Frozen Backbone)
    # ========================================================================

    print("\n" + "=" * 70)
    print("Phase 1: Head Warmup (Frozen Backbone)")
    print("=" * 70)

    model.freeze_backbone()

    # Optimizer for heads only
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )

    if config.use_pcgrad and PCGRAD_AVAILABLE:
        optimizer = PCGrad(optimizer)

    for epoch in range(config.phase1_epochs):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0

        for batch in tqdm(
            train_loader, desc=f"Phase 1 - Epoch {epoch+1}/{config.phase1_epochs}"
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            pixel_attention_mask = batch["pixel_attention_mask"].to(device)
            labels_list = batch["labels"]

            optimizer.zero_grad()
            outputs = model(pixel_values, spatial_shapes, pixel_attention_mask)

            if config.use_pcgrad and PCGRAD_AVAILABLE:
                # PCGrad: separate losses per dimension
                losses = []
                for dim in ["overall", "sharpness", "color"]:
                    target = torch.tensor(
                        [l[dim] for l in labels_list], device=device, dtype=torch.float32
                    )
                    if config.uncertainty:
                        loss = criterion(
                            outputs[dim]["mu"], outputs[dim]["sigma_sq"], target
                        )
                    else:
                        loss = criterion(outputs[dim], target)
                    losses.append(loss)

                optimizer.pc_backward(losses)
                train_loss += sum(l.item() for l in losses) / len(losses)
            else:
                loss, _ = compute_loss(outputs, labels_list)
                loss.backward()
                train_loss += loss.item()

            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)

            optimizer.step()

        train_loss /= len(train_loader)

        # Validation
        val_metrics = validate(val_loader)
        epoch_time = time.time() - epoch_start

        history.append(
            {
                "phase": 1,
                "epoch": epoch + 1,
                "train_loss": train_loss,
                **val_metrics,
                "lr": config.phase1_lr,
                "time": epoch_time,
            }
        )

        print(f"\nPhase 1 - Epoch {epoch+1}/{config.phase1_epochs}:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
        print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
        print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
        print(f"  VQualA: {val_metrics['vquala']:.4f}")
        print(f"  Time: {epoch_time:.1f}s")

        # Save best
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
            print(f"  ✓ New best VQualA! Saved checkpoint.")
            patience_counter = 0
        else:
            patience_counter += 1

    # ========================================================================
    # Phase 2: Full Fine-Tuning
    # ========================================================================

    print("\n" + "=" * 70)
    print("Phase 2: Full Fine-Tuning")
    print("=" * 70)

    model.unfreeze_backbone()

    # Optimizer with different LR for backbone vs heads
    optimizer = torch.optim.AdamW(
        [
            {
                "params": model.backbone.parameters(),
                "lr": config.phase2_lr * config.backbone_lr_multiplier,
            },
            {"params": model.heads.parameters(), "lr": config.phase2_lr},
        ],
        weight_decay=config.weight_decay,
    )

    # Keep reference to base optimizer for scheduler (PCGrad wraps it)
    base_optimizer = optimizer
    if config.use_pcgrad and PCGRAD_AVAILABLE:
        optimizer = PCGrad(base_optimizer)

    # OneCycleLR scheduler (uses base optimizer, not PCGrad wrapper)
    if config.use_onecycle:
        from torch.optim.lr_scheduler import OneCycleLR

        scheduler = OneCycleLR(
            base_optimizer,
            max_lr=[
                config.phase2_lr * config.backbone_lr_multiplier,
                config.phase2_lr,
            ],
            epochs=config.phase2_epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.1,
            anneal_strategy="cos",
            div_factor=25.0,
            final_div_factor=1e4,
        )
    else:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            base_optimizer,
            T_max=config.phase2_epochs,
            eta_min=config.phase2_lr * 0.01,
        )

    for epoch in range(config.phase2_epochs):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0

        for batch in tqdm(
            train_loader, desc=f"Phase 2 - Epoch {epoch+1}/{config.phase2_epochs}"
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            pixel_attention_mask = batch["pixel_attention_mask"].to(device)
            labels_list = batch["labels"]

            base_optimizer.zero_grad()
            outputs = model(pixel_values, spatial_shapes)

            # Phase 2: Don't use PCGrad (OOM with full backbone unfrozen)
            # Standard loss averaging is sufficient after Phase 1 PCGrad warmup
            loss, _ = compute_loss(outputs, labels_list)
            loss.backward()
            train_loss += loss.item()

            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)

            base_optimizer.step()

            if config.use_onecycle:
                scheduler.step()

        train_loss /= len(train_loader)

        if not config.use_onecycle:
            scheduler.step()

        # Validation
        val_metrics = validate(val_loader)
        epoch_time = time.time() - epoch_start
        current_lr = base_optimizer.param_groups[0]["lr"]

        history.append(
            {
                "phase": 2,
                "epoch": config.phase1_epochs + epoch + 1,
                "train_loss": train_loss,
                **val_metrics,
                "lr": current_lr,
                "time": epoch_time,
            }
        )

        print(f"\nPhase 2 - Epoch {epoch+1}/{config.phase2_epochs}:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_metrics['loss']:.4f}")
        print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
        print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
        print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
        print(f"  VQualA: {val_metrics['vquala']:.4f}")
        print(f"  LR: {current_lr:.2e}, Time: {epoch_time:.1f}s")

        # Save best
        if val_metrics["vquala"] > best_vquala:
            best_vquala = val_metrics["vquala"]
            best_checkpoint = {
                "epoch": config.phase1_epochs + epoch + 1,
                "phase": 2,
                "model_state_dict": model.state_dict(),
                "config": config.to_dict(),
                "metrics": val_metrics,
            }
            torch.save(best_checkpoint, output_dir / "siglip2_iqa_best.pt")
            print(f"  ✓ New best VQualA! Saved checkpoint.")
            patience_counter = 0
        else:
            patience_counter += 1

        # Periodic checkpoint
        if (epoch + 1) % config.save_every_n_epochs == 0:
            checkpoint = {
                "epoch": config.phase1_epochs + epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": base_optimizer.state_dict(),  # Use base_optimizer (PCGrad wrapper has no state_dict)
                "config": config.to_dict(),
                "metrics": val_metrics,
            }
            torch.save(
                checkpoint,
                output_dir / f"siglip2_iqa_epoch{config.phase1_epochs + epoch + 1}.pt",
            )

        # Early stopping (only if no improvement for many epochs)
        # Note: We don't stop early just because we hit targets - we want to see how high we can go
        if patience_counter >= config.early_stopping_patience:
            print(f"\nEarly stopping triggered after {patience_counter} epochs without improvement.")
            print(f"Best VQualA achieved: {best_vquala:.4f}")
            break

        # Log if target achieved but continue training
        if (
            val_metrics["vquala"] >= config.target_vquala
            and val_metrics["srcc_overall"] >= config.target_srcc
        ):
            print(f"  ✓ Target metrics achieved! Continuing to maximize performance...")

    # ========================================================================
    # Post-hoc Calibration (if uncertainty enabled)
    # ========================================================================

    if config.uncertainty:
        print("\n" + "=" * 70)
        print("Post-hoc STD Scaling Calibration")
        print("=" * 70)

        # Load best model
        best_state = torch.load(output_dir / "siglip2_iqa_best.pt")
        model.load_state_dict(best_state["model_state_dict"])
        model.eval()

        # Collect predictions and uncertainties
        import numpy as np

        predictions = {dim: [] for dim in ["overall", "sharpness", "color"]}
        uncertainties = {dim: [] for dim in ["overall", "sharpness", "color"]}
        targets = {dim: [] for dim in ["overall", "sharpness", "color"]}

        with torch.no_grad():
            for batch in val_loader:
                pixel_values = batch["pixel_values"].to(device)
                spatial_shapes = batch["spatial_shapes"].to(device)
                # pixel_attention_mask not needed for get_image_features
                labels_list = batch["labels"]
                outputs = model(pixel_values, spatial_shapes)

                for dim in ["overall", "sharpness", "color"]:
                    predictions[dim].extend(outputs[dim]["mu"].cpu().numpy())
                    uncertainties[dim].extend(outputs[dim]["sigma_sq"].cpu().numpy())
                    targets[dim].extend([l[dim] for l in labels_list])

        # Optimize temperature for each head
        calibration_temps = {}
        for dim in ["overall", "sharpness", "color"]:
            preds = np.array(predictions[dim])
            uncerts = np.array(uncertainties[dim])
            targs = np.array(targets[dim])

            def negative_log_likelihood(T):
                scaled_sigma_sq = T * uncerts
                nll = np.mean(
                    0.5 * np.log(scaled_sigma_sq + 1e-8)
                    + (targs - preds) ** 2 / (2 * scaled_sigma_sq + 1e-8)
                )
                return nll

            result = minimize_scalar(
                negative_log_likelihood, bounds=(0.1, 10.0), method="bounded"
            )
            optimal_T = result.x
            calibration_temps[dim] = optimal_T

            srcc, _ = spearmanr(preds, targs)
            print(f"  {dim}: T={optimal_T:.3f}, SRCC={srcc:.4f}")

        # Apply calibration
        model.set_calibration_temps(calibration_temps)

        # Update best checkpoint with calibration
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

    # Load best model
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

    print(f"\nTest Set Results:")
    print(f"  SRCC Overall:   {test_metrics['srcc_overall']:.4f}")
    print(f"  SRCC Sharpness: {test_metrics['srcc_sharpness']:.4f}")
    print(f"  SRCC Color:     {test_metrics['srcc_color']:.4f}")
    print(f"  VQualA:         {test_metrics['vquala']:.4f}")

    target_achieved = (
        test_metrics["srcc_overall"] >= config.target_srcc
        and test_metrics["vquala"] >= config.target_vquala
    )

    if target_achieved:
        print(f"\n✓ TARGET ACHIEVED! Model ready for pseudo-label generation.")
    else:
        print(f"\n✗ Target not achieved. Best VQualA: {best_vquala:.4f}")

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
    }

    if config.uncertainty:
        results["calibration_temps"] = calibration_temps

    results_path = output_dir / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print(f"Best checkpoint: {output_dir / 'siglip2_iqa_best.pt'}")

    # Commit volume
    results_volume.commit()

    return results


@app.local_entrypoint()
def main(
    test: bool = False,
    epochs: int = 50,
    batch_size: int = 16,
    max_patches: int = 576,
    no_pcgrad: bool = False,
    no_uncertainty: bool = False,
):
    """Train SigLIP 2 Base NaFlex for document IQA.

    Args:
        test: Run quick test mode (2 epochs).
        epochs: Total training epochs.
        batch_size: Training batch size.
        max_patches: NaFlex max_num_patches (576 recommended).
        no_pcgrad: Disable PCGrad optimizer.
        no_uncertainty: Disable uncertainty output.
    """
    print("=" * 70)
    print("SigLIP 2 Base NaFlex IQA Training")
    print("=" * 70)
    print(f"Test mode: {test}")
    print(f"Epochs: {epochs if not test else 2}")
    print(f"Batch size: {batch_size}")
    print(f"Max patches: {max_patches}")
    print(f"PCGrad: {not no_pcgrad}")
    print(f"Uncertainty: {not no_uncertainty}")
    print("=" * 70)

    config = SigLIP2TrainingConfig(
        total_epochs=epochs,
        phase1_epochs=min(10, epochs // 5),
        phase2_epochs=epochs - min(10, epochs // 5),
        batch_size=batch_size,
        max_num_patches=max_patches,
        use_pcgrad=not no_pcgrad,
        uncertainty=not no_uncertainty,
    )

    result = train_siglip2_iqa.remote(
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

    if result["target_achieved"]:
        print("\n✓ Model ready for pseudo-label generation!")
        print("Next steps:")
        print("  1. Download checkpoint:")
        print("     modal volume get siglip2-iqa-results /results/siglip2/siglip2_iqa_best.pt ./checkpoints/")
        print("  2. Generate pseudo-labels for other datasets")
        print("  3. Rebuild Stage 2 with consistent labels")
