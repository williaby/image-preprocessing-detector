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

import base64
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

# Common file name constants (S1192: avoid duplicate string literals)
BEST_MODEL_FILE = "siglip2_iqa_best.pt"

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
    # Note: PCGrad installed inline in the training function due to non-standard package structure
    # Note: GCS credentials are injected at runtime via Modal secret (gcs-credentials),
    # NOT baked into the image. The _download_diqa5000_from_gcs function writes the
    # secret-provided GCP_SA_KEY env var to a temp file at container start.
)


@dataclass
class SigLIP2TrainingConfig:
    """Training configuration for SigLIP 2 IQA model."""

    # Model
    model_id: str = "google/siglip2-base-patch16-naflex"
    max_num_patches: int = (
        576  # Critical hyperparameter (default 256 leaves performance on table)
    )
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


def compute_vquala(
    srcc_overall: float, srcc_sharpness: float, srcc_color: float
) -> float:
    """Compute VQualA final score: 0.5*overall + 0.25*sharpness + 0.25*color."""
    return 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color


# IQA quality dimensions used across all heads
_IQA_DIMS = ("overall", "sharpness", "color")


def _create_siglip2_model(config: SigLIP2TrainingConfig, device: Any) -> tuple:
    """Create SigLIP 2 model and processor.

    Returns:
        Tuple of (model, processor).
    """
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoProcessor

    class SigLIP2DocumentIQA(nn.Module):
        """SigLIP 2 NaFlex with multi-task IQA regression heads + uncertainty."""

        def __init__(self, model_id, uncertainty=True):
            super().__init__()
            self.backbone = AutoModel.from_pretrained(model_id)
            embed_dim = self.backbone.config.vision_config.hidden_size
            self.uncertainty = uncertainty
            head_output_dim = 2 if uncertainty else 1
            self.heads = nn.ModuleDict(
                {dim: self._make_head(embed_dim, head_output_dim) for dim in _IQA_DIMS}
            )
            for dim in _IQA_DIMS:
                self.register_buffer(f"temp_{dim}", torch.tensor(1.0))

        def _make_head(self, in_dim, out_dim):
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
            self, pixel_values, spatial_shapes=None, _pixel_attention_mask=None
        ):
            outputs = self.backbone.get_image_features(
                pixel_values=pixel_values, spatial_shapes=spatial_shapes
            )
            results = {}
            for head_name, head in self.heads.items():
                head_output = head(outputs)
                if self.uncertainty:
                    mu = head_output[:, 0]
                    log_sigma_sq = head_output[:, 1]
                    sigma_sq = torch.exp(log_sigma_sq)
                    temp = getattr(self, f"temp_{head_name}")
                    results[head_name] = {
                        "mu": mu,
                        "sigma_sq": temp * sigma_sq,
                        "logits": head_output,
                    }
                else:
                    results[head_name] = head_output.squeeze(-1)
            return results

        def set_calibration_temps(self, temps):
            for head_name, temp in temps.items():
                setattr(self, f"temp_{head_name}", torch.tensor(temp))

    print("\nLoading SigLIP 2 processor and model...")
    processor = AutoProcessor.from_pretrained(config.model_id)
    model = SigLIP2DocumentIQA(model_id=config.model_id, uncertainty=config.uncertainty)
    model = model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    backbone_params = sum(p.numel() for p in model.backbone.parameters())
    print(f"Total parameters: {total_params:,}")
    print(f"Backbone parameters: {backbone_params:,}")
    print(f"Head parameters: {total_params - backbone_params:,}")

    return model, processor


def _create_loss_fn(config: SigLIP2TrainingConfig) -> Any:
    """Create appropriate loss function based on config."""
    import torch.nn as nn

    class NormInNormLoss(nn.Module):
        def __init__(self, p=1.0, q=2.0):
            super().__init__()
            self.p, self.q = p, q

        def forward(self, pred, target):
            pred_norm = (pred - pred.mean()) / (pred.std() + 1e-8)
            target_norm = (target - target.mean()) / (target.std() + 1e-8)
            diff = (pred_norm - target_norm).abs()
            return diff.pow(self.p).mean().pow(self.q / self.p)

    class GaussianNLLLoss(nn.Module):
        def forward(self, mu, sigma_sq, target):
            import torch

            sigma_sq = torch.clamp(sigma_sq, min=1e-6)
            return (
                0.5 * torch.log(sigma_sq) + (target - mu) ** 2 / (2 * sigma_sq)
            ).mean()

    if config.uncertainty:
        return GaussianNLLLoss()
    if config.use_norm_in_norm:
        return NormInNormLoss(p=1.0, q=2.0)
    return nn.MSELoss()


def _create_pcgrad_wrapper_v1(optimizer: Any) -> Any:
    """Create PCGrad optimizer wrapper (v1 inline implementation)."""
    import torch

    class PCGrad:
        def __init__(self, opt):
            self.optimizer = opt
            self._reduction = "mean"

        @property
        def param_groups(self):
            return self.optimizer.param_groups

        def zero_grad(self):
            return self.optimizer.zero_grad()

        def step(self):
            return self.optimizer.step()

        def pc_backward(self, losses):
            task_grads = []
            for i, loss in enumerate(losses):
                self.optimizer.zero_grad()
                loss.backward(retain_graph=(i < len(losses) - 1))
                grads = []
                for group in self.optimizer.param_groups:
                    for p in group["params"]:
                        grads.append(
                            p.grad.clone().flatten()
                            if p.grad is not None
                            else torch.zeros_like(p).flatten()
                        )
                task_grads.append(torch.cat(grads))

            projected = _project(task_grads)
            self.optimizer.zero_grad()
            offset = 0
            for group in self.optimizer.param_groups:
                for p in group["params"]:
                    numel = p.numel()
                    p.grad = projected[offset : offset + numel].view_as(p)
                    offset += numel

    def _project(grads):
        projected = [g.clone() for g in grads]
        for i in range(len(grads)):
            for j in range(len(grads)):
                if i != j:
                    dot = torch.dot(projected[i], grads[j])
                    if dot < 0:
                        projected[i] -= (
                            dot / (torch.dot(grads[j], grads[j]) + 1e-8)
                        ) * grads[j]
        return torch.stack(projected).mean(dim=0)

    return PCGrad(optimizer)


def _setup_gcs_credentials() -> tuple[str | None, str | None]:
    """Write GCS credentials from Modal secret env var to a temp file.

    The Modal secret (gcs-credentials) injects GCP_SA_KEY as a base64-encoded
    service account JSON. We write it to a temp file at runtime so the GCS
    client can authenticate without baking credentials into the container image.

    Returns:
        Tuple of (credentials_path, prior_env_value). credentials_path is None
        if GCP_SA_KEY is not set. prior_env_value is the previous value of
        GOOGLE_APPLICATION_CREDENTIALS (None if it was not set).
    """
    import os
    import tempfile

    prior = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key:
        # Credentials may already be set via another mechanism
        return None, prior

    sa_json = base64.b64decode(gcp_sa_key).decode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as cred_file:
        cred_file.write(sa_json)
        credentials_path = cred_file.name

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return credentials_path, prior


def _download_diqa5000_from_gcs(data_dir: Path) -> bool:
    """Download original DIQA-5000 dataset from GCS.

    Uses credentials from Modal secret (GCP_SA_KEY env var) written to a
    temporary file at runtime. The temp file is cleaned up after use.

    Returns:
        True if download succeeded (or cache is valid), False on failure.
    """
    from google.cloud import storage

    # Write Modal secret credentials to temp file at runtime
    credentials_path, prior_creds = _setup_gcs_credentials()

    try:
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
            for blob in bucket.list_blobs(prefix=prefix):
                if blob.name.endswith("/"):
                    continue
                relative_path = blob.name[len(prefix) :]
                if not relative_path:
                    continue
                local_file = split_dir / relative_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    blob.download_to_filename(str(local_file))
                    downloaded += 1
                except Exception as exc:
                    print(f"  ERROR downloading {blob.name}: {exc}")
                    raise
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

    finally:
        import os

        # Clean up temp credentials file to avoid leaving sensitive data on disk
        if credentials_path:
            cred = Path(credentials_path)
            if cred.exists():
                cred.unlink()
        # Restore the original GOOGLE_APPLICATION_CREDENTIALS value
        if prior_creds is not None:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = prior_creds
        elif credentials_path is not None:
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


def _prepare_datasets(
    config: SigLIP2TrainingConfig, processor: Any, test_mode: bool
) -> tuple:
    """Download data, create datasets and loaders.

    Returns:
        Tuple of (train_loader, val_loader, test_dataset, collate_fn).
    """
    import torch
    from torch.utils.data import DataLoader

    data_dir = Path("/data/diqa5000")
    print("\nDownloading DIQA-5000 dataset from GCS...")
    if not _download_diqa5000_from_gcs(data_dir):
        raise RuntimeError(
            "Failed to download DIQA-5000 dataset from GCS. "
            "Check GCS bucket access and network connectivity."
        )
    diqa5000_volume.commit()

    print("\nLoading DIQA-5000 dataset...")
    train_dataset = _create_diqa_dataset(
        "train",
        data_dir,
        processor,
        config.max_num_patches,
        config.use_augmentation,
        config.horizontal_flip_prob,
        config.random_crop_prob,
    )
    val_dataset = _create_diqa_dataset(
        "val", data_dir, processor, config.max_num_patches
    )
    test_dataset = _create_diqa_dataset(
        "test", data_dir, processor, config.max_num_patches
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
        return {
            "pixel_values": pixel_values,
            "spatial_shapes": spatial_shapes,
            "pixel_attention_mask": pixel_attention_mask,
            "labels": [item["labels"] for item in batch],
            "image_ids": [item["image_id"] for item in batch],
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

    return train_loader, val_loader, test_dataset, custom_collate_fn


def _create_diqa_dataset(
    split: str,
    data_dir: Path,
    processor: Any,
    max_num_patches: int = 576,
    use_augmentation: bool = False,
    horizontal_flip_prob: float = 0.5,
    random_crop_prob: float = 0.3,
) -> Any:
    """Create a DIQA5000 Dataset instance."""
    import csv

    from PIL import Image, ImageOps
    from torch.utils.data import Dataset

    class DIQA5000Dataset(Dataset):
        def __init__(
            self,
            split_name,
            data_directory,
            proc,
            max_patches,
            augment,
            h_flip_prob,
            crop_prob,
        ):
            self.split = split_name
            self.data_dir = Path(data_directory)
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
                    image_path = res_dir / row["res"]
                    if not image_path.exists():
                        continue
                    self.samples.append(
                        {
                            "image_path": str(image_path),
                            "image_id": row["res"].replace(".jpg", ""),
                            "overall": float(row["overall"]),
                            "sharpness": float(row["sharpness"]),
                            "color_fidelity": float(row["color_fidelity"]),
                        }
                    )
            print(f"  {split_name}: {len(self.samples)} samples loaded")

        def __len__(self):
            return len(self.samples)

        def _normalize_mos(self, score):
            return (score - 1.0) / 4.0

        def _apply_safe_augmentations(self, image):
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

        def __getitem__(self, idx):
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
        split,
        data_dir,
        processor,
        max_num_patches,
        use_augmentation,
        horizontal_flip_prob,
        random_crop_prob,
    )


def _compute_loss_v1(outputs, labels, criterion, config, device):
    """Compute loss for all IQA dimensions."""
    import torch

    losses = []
    for dim in _IQA_DIMS:
        target = torch.tensor(
            [lbl[dim] for lbl in labels], device=device, dtype=torch.float32
        )
        if config.uncertainty:
            loss = criterion(outputs[dim]["mu"], outputs[dim]["sigma_sq"], target)
        else:
            loss = criterion(outputs[dim], target)
        losses.append(loss)
    return sum(losses) / len(losses), losses


def _validate_v1(model, loader, criterion, config, device):
    """Validate model and compute SRCC metrics."""
    import numpy as np
    import torch
    from scipy.stats import spearmanr

    model.eval()
    all_preds = {dim: [] for dim in _IQA_DIMS}
    all_labels = {dim: [] for dim in _IQA_DIMS}
    total_loss = 0.0

    with torch.no_grad():
        for batch in loader:
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]
            outputs = model(pixel_values, spatial_shapes)
            loss, _ = _compute_loss_v1(outputs, labels_list, criterion, config, device)
            total_loss += loss.item()

            for dim in _IQA_DIMS:
                preds = (
                    outputs[dim]["mu"].cpu().numpy()
                    if config.uncertainty
                    else outputs[dim].cpu().numpy()
                )
                all_preds[dim].extend(preds)
                all_labels[dim].extend([lbl[dim] for lbl in labels_list])

    srcc = {}
    for dim in _IQA_DIMS:
        srcc[dim], _ = spearmanr(all_preds[dim], all_labels[dim])
        if np.isnan(srcc[dim]):
            srcc[dim] = 0.0

    return {
        "loss": total_loss / len(loader),
        "srcc_overall": srcc["overall"],
        "srcc_sharpness": srcc["sharpness"],
        "srcc_color": srcc["color"],
        "vquala": compute_vquala(srcc["overall"], srcc["sharpness"], srcc["color"]),
    }


def _run_phase1(config, model, train_loader, val_loader, criterion, device, state):
    """Phase 1: Head Warmup with frozen backbone."""
    import torch
    from tqdm import tqdm

    print("\n" + "=" * 70)
    print("Phase 1: Head Warmup (Frozen Backbone)")
    print("=" * 70)

    model.freeze_backbone()
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )
    pcgrad_optimizer = (
        _create_pcgrad_wrapper_v1(optimizer) if config.use_pcgrad else None
    )
    active_optimizer = pcgrad_optimizer or optimizer

    for epoch in range(config.phase1_epochs):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0

        for batch in tqdm(
            train_loader, desc=f"Phase 1 - Epoch {epoch + 1}/{config.phase1_epochs}"
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            active_optimizer.zero_grad()
            outputs = model(pixel_values, spatial_shapes)

            if pcgrad_optimizer:
                losses = []
                for dim in _IQA_DIMS:
                    target = torch.tensor(
                        [lbl[dim] for lbl in labels_list],
                        device=device,
                        dtype=torch.float32,
                    )
                    if config.uncertainty:
                        loss = criterion(
                            outputs[dim]["mu"], outputs[dim]["sigma_sq"], target
                        )
                    else:
                        loss = criterion(outputs[dim], target)
                    losses.append(loss)
                pcgrad_optimizer.pc_backward(losses)
                train_loss += sum(loss_i.item() for loss_i in losses) / len(losses)
            else:
                loss, _ = _compute_loss_v1(
                    outputs, labels_list, criterion, config, device
                )
                loss.backward()
                train_loss += loss.item()

            if config.gradient_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
            active_optimizer.step()

        train_loss /= len(train_loader)
        val_metrics = _validate_v1(model, val_loader, criterion, config, device)
        epoch_time = time.time() - epoch_start

        state["history"].append(
            {
                "phase": 1,
                "epoch": epoch + 1,
                "train_loss": train_loss,
                **val_metrics,
                "lr": config.phase1_lr,
                "time": epoch_time,
            }
        )

        _log_epoch(
            1,
            epoch + 1,
            config.phase1_epochs,
            train_loss,
            val_metrics,
            config.phase1_lr,
            epoch_time,
        )
        _update_best(model, val_metrics, epoch + 1, 1, config, state)


def _run_phase2(config, model, train_loader, val_loader, criterion, device, state):
    """Phase 2: Full Fine-Tuning with different LR for backbone vs heads."""
    import torch
    from tqdm import tqdm

    print("\n" + "=" * 70)
    print("Phase 2: Full Fine-Tuning")
    print("=" * 70)

    model.unfreeze_backbone()
    base_optimizer = torch.optim.AdamW(
        [
            {
                "params": model.backbone.parameters(),
                "lr": config.phase2_lr * config.backbone_lr_multiplier,
            },
            {"params": model.heads.parameters(), "lr": config.phase2_lr},
        ],
        lr=config.phase2_lr,
        weight_decay=config.weight_decay,
    )

    if config.use_onecycle:
        from torch.optim.lr_scheduler import OneCycleLR

        scheduler = OneCycleLR(
            base_optimizer,
            max_lr=[config.phase2_lr * config.backbone_lr_multiplier, config.phase2_lr],
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
            train_loader, desc=f"Phase 2 - Epoch {epoch + 1}/{config.phase2_epochs}"
        ):
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]

            base_optimizer.zero_grad()
            outputs = model(pixel_values, spatial_shapes)
            loss, _ = _compute_loss_v1(outputs, labels_list, criterion, config, device)
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

        val_metrics = _validate_v1(model, val_loader, criterion, config, device)
        epoch_time = time.time() - epoch_start
        current_lr = base_optimizer.param_groups[0]["lr"]
        global_epoch = config.phase1_epochs + epoch + 1

        state["history"].append(
            {
                "phase": 2,
                "epoch": global_epoch,
                "train_loss": train_loss,
                **val_metrics,
                "lr": current_lr,
                "time": epoch_time,
            }
        )

        _log_epoch(
            2,
            epoch + 1,
            config.phase2_epochs,
            train_loss,
            val_metrics,
            current_lr,
            epoch_time,
        )
        _update_best(model, val_metrics, global_epoch, 2, config, state)

        if (epoch + 1) % config.save_every_n_epochs == 0:
            torch.save(
                {
                    "epoch": global_epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": base_optimizer.state_dict(),
                    "config": config.to_dict(),
                    "metrics": val_metrics,
                },
                Path(config.output_dir) / f"siglip2_iqa_epoch{global_epoch}.pt",
            )

        if state["patience_counter"] >= config.early_stopping_patience:
            print(
                f"\nEarly stopping triggered after {state['patience_counter']} epochs without improvement."
            )
            print(f"Best VQualA achieved: {state['best_vquala']:.4f}")
            break

        if (
            val_metrics["vquala"] >= config.target_vquala
            and val_metrics["srcc_overall"] >= config.target_srcc
        ):
            print("  -> Target metrics achieved! Continuing to maximize performance...")


def _log_epoch(phase, epoch, total, train_loss, val_metrics, lr, epoch_time):
    """Print epoch training metrics."""
    print(f"\nPhase {phase} - Epoch {epoch}/{total}:")
    print(f"  Train Loss: {train_loss:.4f}")
    print(f"  Val Loss: {val_metrics['loss']:.4f}")
    print(f"  SRCC Overall: {val_metrics['srcc_overall']:.4f}")
    print(f"  SRCC Sharpness: {val_metrics['srcc_sharpness']:.4f}")
    print(f"  SRCC Color: {val_metrics['srcc_color']:.4f}")
    print(f"  VQualA: {val_metrics['vquala']:.4f}")
    print(f"  LR: {lr:.2e}, Time: {epoch_time:.1f}s")


def _update_best(model, val_metrics, epoch, phase, config, state):
    """Update best checkpoint if VQualA improved."""
    import torch

    if val_metrics["vquala"] > state["best_vquala"]:
        state["best_vquala"] = val_metrics["vquala"]
        state["best_checkpoint"] = {
            "epoch": epoch,
            "phase": phase,
            "model_state_dict": model.state_dict(),
            "config": config.to_dict(),
            "metrics": val_metrics,
        }
        torch.save(state["best_checkpoint"], Path(config.output_dir) / BEST_MODEL_FILE)
        print("  -> New best VQualA! Saved checkpoint.")
        state["patience_counter"] = 0
    else:
        state["patience_counter"] += 1


def _run_calibration(config, model, val_loader, device, state):
    """Post-hoc STD scaling calibration on validation set."""
    import numpy as np
    import torch
    from scipy.optimize import minimize_scalar
    from scipy.stats import spearmanr

    print("\n" + "=" * 70)
    print("Post-hoc STD Scaling Calibration")
    print("=" * 70)

    output_dir = Path(config.output_dir)
    best_state = torch.load(output_dir / BEST_MODEL_FILE, weights_only=True)
    model.load_state_dict(best_state["model_state_dict"])
    model.eval()

    predictions = {dim: [] for dim in _IQA_DIMS}
    uncertainties = {dim: [] for dim in _IQA_DIMS}
    targets = {dim: [] for dim in _IQA_DIMS}

    with torch.no_grad():
        for batch in val_loader:
            pixel_values = batch["pixel_values"].to(device)
            spatial_shapes = batch["spatial_shapes"].to(device)
            labels_list = batch["labels"]
            outputs = model(pixel_values, spatial_shapes)
            for dim in _IQA_DIMS:
                predictions[dim].extend(outputs[dim]["mu"].cpu().numpy())
                uncertainties[dim].extend(outputs[dim]["sigma_sq"].cpu().numpy())
                targets[dim].extend([lbl[dim] for lbl in labels_list])

    def _make_nll(preds_arr, uncerts_arr, targs_arr):
        def nll(temp):
            s = temp * uncerts_arr
            return float(
                np.mean(
                    0.5 * np.log(s + 1e-8)
                    + (targs_arr - preds_arr) ** 2 / (2 * s + 1e-8)
                )
            )

        return nll

    calibration_temps = {}
    for dim in _IQA_DIMS:
        preds_arr = np.array(predictions[dim])
        uncerts_arr = np.array(uncertainties[dim])
        targs_arr = np.array(targets[dim])
        result = minimize_scalar(
            _make_nll(preds_arr, uncerts_arr, targs_arr),
            bounds=(0.1, 10.0),
            method="bounded",
        )
        calibration_temps[dim] = result.x
        srcc, _ = spearmanr(preds_arr, targs_arr)
        print(f"  {dim}: T={result.x:.3f}, SRCC={srcc:.4f}")

    model.set_calibration_temps(calibration_temps)
    state["best_checkpoint"]["model_state_dict"] = model.state_dict()
    state["best_checkpoint"]["calibration_temps"] = calibration_temps
    state["calibration_temps"] = calibration_temps
    torch.save(state["best_checkpoint"], output_dir / BEST_MODEL_FILE)
    print("  -> Saved calibrated model")


def _run_test_eval(config, model, test_dataset, criterion, device, collate_fn, state):
    """Evaluate best model on test set and return results."""
    import torch
    from torch.utils.data import DataLoader

    print("\n" + "=" * 70)
    print("Final Evaluation on Test Set")
    print("=" * 70)

    output_dir = Path(config.output_dir)
    best_state = torch.load(output_dir / BEST_MODEL_FILE, weights_only=True)
    model.load_state_dict(best_state["model_state_dict"])

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        collate_fn=collate_fn,
    )
    test_metrics = _validate_v1(model, test_loader, criterion, config, device)

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
        print("\n-> TARGET ACHIEVED! Model ready for pseudo-label generation.")
    else:
        print(f"\n-> Target not achieved. Best VQualA: {state['best_vquala']:.4f}")

    return test_metrics, target_achieved


def _save_results(config, state, test_metrics, target_achieved):
    """Serialize training results to JSON and return results dict."""
    output_dir = Path(config.output_dir)
    results: dict[str, Any] = {
        "config": config.to_dict(),
        "best_vquala": state["best_vquala"],
        "test_results": {
            "srcc_overall": test_metrics["srcc_overall"],
            "srcc_sharpness": test_metrics["srcc_sharpness"],
            "srcc_color": test_metrics["srcc_color"],
            "vquala": test_metrics["vquala"],
        },
        "target_achieved": target_achieved,
        "history": state["history"],
        "checkpoint_path": str(output_dir / BEST_MODEL_FILE),
        "timestamp": datetime.now().isoformat(),
    }
    if state.get("calibration_temps"):
        results["calibration_temps"] = state["calibration_temps"]

    results_path = output_dir / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print(f"Best checkpoint: {output_dir / BEST_MODEL_FILE}")
    return results


@app.function(
    image=training_image,
    gpu="A10G",
    timeout=3600 * 24,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    volumes={"/results": results_volume, "/data": diqa5000_volume},
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
    print(f"PCGrad: {config.use_pcgrad}")
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

    model, processor = _create_siglip2_model(config, device)
    criterion = _create_loss_fn(config)
    train_loader, val_loader, test_dataset, collate_fn = _prepare_datasets(
        config, processor, test_mode
    )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {
        "history": [],
        "best_vquala": 0.0,
        "best_checkpoint": None,
        "patience_counter": 0,
    }

    _run_phase1(config, model, train_loader, val_loader, criterion, device, state)
    _run_phase2(config, model, train_loader, val_loader, criterion, device, state)

    if config.uncertainty:
        _run_calibration(config, model, val_loader, device, state)

    test_metrics, target_achieved = _run_test_eval(
        config, model, test_dataset, criterion, device, collate_fn, state
    )

    results = _save_results(config, state, test_metrics, target_achieved)
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
        print(
            "     modal volume get siglip2-iqa-results /results/siglip2/siglip2_iqa_best.pt ./checkpoints/"
        )
        print("  2. Generate pseudo-labels for other datasets")
        print("  3. Rebuild Stage 2 with consistent labels")
