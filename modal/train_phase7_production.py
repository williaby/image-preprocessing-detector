# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 7 Production Training on Modal - ResNet-50 with Gaussian NLL.

This is the FULL PRODUCTION training script, not a baseline check.

Key differences from MVP baseline (train_phase7_mvp.py):
1. Gaussian NLL loss for uncertainty-aware predictions
2. Dual-head architecture: mean (severity) + variance (uncertainty)
3. Calibration-aware training with uncertainty correlation tracking
4. Extended training (100 epochs vs 50)

Dataset: gs://image_detection_b/datasets/phase7_mvp/
- phase7_mvp_train.tar.gz (17,469 samples, 602 MB)
- phase7_mvp_val.tar.gz (3,719 samples, 126 MB)
- phase7_mvp_test.tar.gz (3,812 samples, 130 MB)

Usage:
    # Production training (recommended)
    modal run modal/train_phase7_production.py

    # Custom seed for ensemble
    modal run modal/train_phase7_production.py --seed 42
    modal run modal/train_phase7_production.py --seed 123
    modal run modal/train_phase7_production.py --seed 456

Monitor:
    modal app logs iqa-phase7-production --follow

Reference:
    PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 5.1, 6.2 Phase 2
"""
# mypy: ignore-errors

import json
import os
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import modal

# Create Modal app
stub = modal.App("iqa-phase7-production")

# Container image
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "timm>=0.9.0",
        "albumentations>=1.3.0",
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
        "tensorboard>=2.14.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "google-cloud-storage>=2.10.0",
        "structlog>=23.1.0",
        "rich>=13.0.0",
        "scipy>=1.10.0",
    )
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    .add_local_file("data/__init__.py", "/root/data/__init__.py", copy=True)
    .add_local_file("data/dataset.py", "/root/data/dataset.py", copy=True)
    .add_local_file("data/augmentation.py", "/root/data/augmentation.py", copy=True)
    .add_local_file(
        "data/continuous_labels.py", "/root/data/continuous_labels.py", copy=True
    )
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)

gcs_secret = modal.Secret.from_name("gcs-credentials")
checkpoint_volume = modal.Volume.from_name(
    "phase7-production-checkpoints", create_if_missing=True
)


@dataclass
class ProductionTrainingConfig:
    """Configuration for Phase 7 Production training with Gaussian NLL."""

    # Dataset
    gcs_bucket: str = "image_detection_b"
    gcs_prefix: str = "datasets/phase7_mvp"

    # Model Architecture (with uncertainty heads)
    model_architecture: str = "resnet50"
    num_heads: int = 5  # blur, noise, compression, contrast, geometric
    dropout: float = 0.3  # Increased for uncertainty calibration
    pretrained: bool = True

    # Resolution (CRITICAL: 384 preserves JPEG blocks)
    input_resolution: int = 384

    # Loss Function: Gaussian NLL (production)
    loss_type: str = "gaussian_nll"
    var_clamp_min: float = 1e-4
    var_clamp_max: float = 10.0

    # Training (extended for production)
    epochs: int = 100
    batch_size: int = 32  # Reduced due to 384x384 resolution
    learning_rate: float = 1e-4
    weight_decay: float = 0.02
    warmup_epochs: int = 5
    min_lr: float = 1e-6
    gradient_clip: float = 1.0
    seed: int = 42

    # Early Stopping Targets (per IDEAL_STATE_PROJECT_PLAN_v2)
    ece_target: float = 0.08  # Primary: ECE < 0.08
    mae_target: float = 0.15  # Secondary: Severity MAE < 0.15
    correlation_target: float = 0.85  # Production target: > 0.85
    uncertainty_correlation_target: float = (
        0.50  # Uncertainty should correlate with error
    )
    early_stop_patience: int = 15
    num_ece_bins: int = 15
    min_epochs: int = 20  # More epochs before early stopping

    # Output
    output_gcs_path: str = "gs://image_detection_b/models/phase7_production"


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    import random

    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def safe_extract_tar(tar_path: Path, extract_path: Path) -> None:
    """Safely extract tar.gz with path traversal protection."""

    def is_within_directory(directory: Path, target: Path) -> bool:
        abs_directory = directory.resolve()
        abs_target = target.resolve()
        return str(abs_target).startswith(str(abs_directory))

    with tarfile.open(tar_path, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            member_path = extract_path / member.name
            if not is_within_directory(extract_path, member_path):
                raise ValueError(f"Path traversal detected: {member.name}")
        tar.extractall(path=extract_path, members=members)


def compute_ece_numpy(predictions, targets, num_bins: int = 15):
    """Compute Expected Calibration Error."""
    import numpy as np

    predictions = np.asarray(predictions)
    targets = np.asarray(targets)

    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, 1)
        targets = targets.reshape(-1, 1)

    n_samples, n_classes = predictions.shape
    per_head_ece = []

    for c in range(n_classes):
        preds_c = predictions[:, c]
        targs_c = targets[:, c]
        ece = 0.0
        bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)

        for i in range(num_bins):
            lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
            in_bin = (
                (preds_c >= lower) & (preds_c < upper)
                if i < num_bins - 1
                else (preds_c >= lower) & (preds_c <= upper)
            )
            bin_size = in_bin.sum()
            if bin_size > 0:
                bin_accuracy = targs_c[in_bin].mean()
                bin_confidence = preds_c[in_bin].mean()
                ece += (bin_size / n_samples) * abs(bin_accuracy - bin_confidence)

        per_head_ece.append(ece)

    return {
        "macro_ece": float(np.mean(per_head_ece)),
        "per_head_ece": [float(e) for e in per_head_ece],
    }


def download_and_extract(bucket_name: str, blob_name: str, extract_dir: Path) -> None:
    """Download and extract a tar.gz from GCS."""
    from google.cloud import storage

    print(f"Downloading: gs://{bucket_name}/{blob_name}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tar_path = Path(tmp.name)

    start = time.time()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(str(tar_path))

    size_mb = tar_path.stat().st_size / (1024**2)
    elapsed = time.time() - start
    print(f"  Downloaded {size_mb:.1f} MB in {elapsed:.1f}s")

    print("  Extracting...")
    safe_extract_tar(tar_path, extract_dir)
    tar_path.unlink()
    print("  Done!")


def prepare_dataset(bucket_name: str, gcs_prefix: str) -> Path:
    """Download and prepare dataset."""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    dataset_dir = Path("/tmp/phase7_production")
    images_dir = dataset_dir / "images"

    if (dataset_dir / "train_metadata.json").exists():
        with open(dataset_dir / "train_metadata.json") as f:
            train_count = len(json.load(f))
        image_count = len(list(images_dir.glob("*.jpg"))) if images_dir.exists() else 0
        if image_count > train_count * 0.9:
            print(f"Dataset exists: {train_count} train, {image_count} images")
            return dataset_dir

    dataset_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    for split in ["train", "val", "test"]:
        print(f"\n[{split.upper()}]")
        download_and_extract(
            bucket_name, f"{gcs_prefix}/phase7_mvp_{split}.tar.gz", dataset_dir
        )

        meta_path = dataset_dir / f"{split}_metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                samples = json.load(f)
            print(f"  {split} samples: {len(samples)}")

    return dataset_dir


@stub.function(
    image=image,
    gpu="A10G",
    timeout=7200,  # 2 hours
    secrets=[gcs_secret],
    volumes={"/checkpoints": checkpoint_volume},
)
def train_production(seed: int = 42) -> dict[str, Any]:
    """Train Phase 7 production model with Gaussian NLL.

    This is the FULL PRODUCTION training, not a baseline check.
    """
    import albumentations as alb
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from albumentations.pytorch import ToTensorV2
    from PIL import Image
    from scipy import stats
    from torch.utils.data import DataLoader, Dataset

    print("=" * 60)
    print("PHASE 7 PRODUCTION TRAINING")
    print("Loss: Gaussian NLL (uncertainty-aware)")
    print("Architecture: ResNet-50 with mean + variance heads")
    print("=" * 60)

    config = ProductionTrainingConfig(seed=seed)
    set_seed(config.seed)
    print(f"\nSeed: {config.seed}")
    print(f"Resolution: {config.input_resolution}x{config.input_resolution}")
    print(f"Epochs: {config.epochs}")
    print(f"Batch Size: {config.batch_size}")
    print(
        f"Targets: ECE<{config.ece_target}, MAE<{config.mae_target}, Corr>{config.correlation_target}"
    )

    # Download dataset
    print("\n📥 Downloading dataset...")
    dataset_dir = prepare_dataset(config.gcs_bucket, config.gcs_prefix)

    # Transforms for 384x384 resolution
    res = config.input_resolution
    train_transform = alb.Compose(
        [
            alb.RandomResizedCrop(size=(res, res), scale=(0.5, 1.0)),
            alb.HorizontalFlip(p=0.5),
            alb.ColorJitter(
                brightness=0.1, contrast=0.1, saturation=0.0, hue=0.0, p=0.3
            ),
            alb.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ]
    )

    val_transform = alb.Compose(
        [
            alb.Resize(height=res, width=res),
            alb.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ]
    )

    # Dataset class
    class Phase7Dataset(Dataset):
        def __init__(self, dataset_dir: Path, split: str, transform=None):
            self.dataset_dir = dataset_dir
            self.images_dir = dataset_dir / "images"
            self.transform = transform

            with open(dataset_dir / f"{split}_metadata.json") as f:
                self.samples = json.load(f)
            print(f"  {split}: {len(self.samples)} samples")

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            sample = self.samples[idx]
            # Key is "filename" not "image"
            img_path = self.images_dir / sample["filename"]

            image = np.array(Image.open(img_path).convert("RGB"))

            if self.transform:
                transformed = self.transform(image=image)
                image = transformed["image"]

            # Extract severity scores from nested dict
            severity = sample.get("severity_scores", {})

            # Geometric severity is combination of skew + perspective
            skew = severity.get("skew_severity", 0.0)
            perspective = severity.get("perspective_severity", 0.0)
            geometric = max(skew, perspective)  # Use max as proxy for geometric

            labels = torch.tensor(
                [
                    severity.get("blur_severity", 0.0),
                    severity.get("noise_severity", 0.0),
                    severity.get("compression_severity", 0.0),
                    severity.get("contrast_severity", 0.0),
                    geometric,
                ],
                dtype=torch.float32,
            )

            return image, labels

    # Create datasets
    print("\n📦 Creating datasets...")
    train_dataset = Phase7Dataset(dataset_dir, "train", train_transform)
    val_dataset = Phase7Dataset(dataset_dir, "val", val_transform)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
    )

    # Build model with uncertainty heads
    print("\n🔧 Building model with uncertainty heads...")
    import timm

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    backbone = timm.create_model(
        config.model_architecture, pretrained=config.pretrained, num_classes=0
    )
    feature_dim = backbone.num_features
    print(f"Backbone: {config.model_architecture}, features: {feature_dim}")

    class UncertaintyHead(nn.Module):
        """Single head that outputs mean (mu) and log variance (log_var)."""

        def __init__(self, in_features: int, dropout: float = 0.3):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.mu_head = nn.Sequential(
                nn.Linear(256, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),  # Output in [0, 1]
            )
            self.log_var_head = nn.Sequential(
                nn.Linear(256, 64),
                nn.ReLU(),
                nn.Linear(64, 1),  # Unbounded log variance
            )

        def forward(self, x):
            shared = self.shared(x)
            mu = self.mu_head(shared)
            log_var = self.log_var_head(shared)
            return mu, log_var

    class UncertaintyIQAModel(nn.Module):
        """ResNet-50 with separate uncertainty heads for each defect type."""

        def __init__(self, backbone, feature_dim: int, num_heads: int, dropout: float):
            super().__init__()
            self.backbone = backbone
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.heads = nn.ModuleList(
                [UncertaintyHead(feature_dim, dropout) for _ in range(num_heads)]
            )

        def forward(self, x):
            features = self.backbone(x)
            if features.dim() == 4:
                features = self.pool(features).flatten(1)

            mus = []
            log_vars = []
            for head in self.heads:
                mu, log_var = head(features)
                mus.append(mu)
                log_vars.append(log_var)

            return torch.cat(mus, dim=1), torch.cat(log_vars, dim=1)

    model = UncertaintyIQAModel(backbone, feature_dim, config.num_heads, config.dropout)
    model = model.to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Gaussian NLL Loss
    class GaussianNLLLoss(nn.Module):
        def __init__(
            self, eps: float = 1e-6, var_min: float = 1e-4, var_max: float = 10.0
        ):
            super().__init__()
            self.eps = eps
            self.var_min = var_min
            self.var_max = var_max

        def forward(self, mu, log_var, target):
            var = torch.exp(log_var).clamp(self.var_min, self.var_max)
            nll = 0.5 * (torch.log(var) + ((target - mu) ** 2) / var)
            return nll.mean()

    loss_fn = GaussianNLLLoss(
        var_min=config.var_clamp_min, var_max=config.var_clamp_max
    )
    optimizer = optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )

    # Cosine annealing with warmup
    def lr_lambda(epoch):
        if epoch < config.warmup_epochs:
            return epoch / config.warmup_epochs
        return (
            config.min_lr / config.learning_rate
            + (1 - config.min_lr / config.learning_rate)
            * (
                1
                + np.cos(
                    np.pi
                    * (epoch - config.warmup_epochs)
                    / (config.epochs - config.warmup_epochs)
                )
            )
            / 2
        )

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # Training loop
    print("\n🚀 Starting PRODUCTION training...")
    print("Loss: Gaussian NLL")
    print(
        f"Targets: ECE<{config.ece_target}, MAE<{config.mae_target}, Corr>{config.correlation_target}"
    )
    print(f"Uncertainty correlation target: >{config.uncertainty_correlation_target}")

    best_val_loss = float("inf")
    best_ece = float("inf")
    best_mae = float("inf")
    best_correlation = float("-inf")
    best_uncertainty_corr = float("-inf")
    epochs_without_improvement = 0
    training_history = []

    for epoch in range(config.epochs):
        # Train
        model.train()
        train_loss = 0.0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            mu, log_var = model(images)
            loss = loss_fn(mu, log_var, labels)

            # Gradient clipping
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
            optimizer.step()

            train_loss += loss.item()

            if batch_idx % 50 == 0:
                print(
                    f"  Epoch {epoch + 1}/{config.epochs} | Batch {batch_idx}/{len(train_loader)} | Loss: {loss.item():.4f}"
                )

        train_loss /= len(train_loader)
        scheduler.step()

        # Validate
        model.eval()
        val_loss = 0.0
        all_mu = []
        all_var = []
        all_targets = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                mu, log_var = model(images)
                loss = loss_fn(mu, log_var, labels)
                val_loss += loss.item()

                all_mu.append(mu.cpu().numpy())
                all_var.append(torch.exp(log_var).cpu().numpy())
                all_targets.append(labels.cpu().numpy())

        val_loss /= len(val_loader)

        # Compute metrics
        all_mu = np.concatenate(all_mu, axis=0)
        all_var = np.concatenate(all_var, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)

        # ECE
        ece_result = compute_ece_numpy(all_mu, all_targets, config.num_ece_bins)
        current_ece = ece_result["macro_ece"]

        # MAE
        severity_mae = np.abs(all_mu - all_targets).mean()

        # Pearson correlation (per head and macro)
        per_head_correlation = []
        for h in range(config.num_heads):
            corr, _ = stats.pearsonr(all_mu[:, h], all_targets[:, h])
            per_head_correlation.append(float(corr) if not np.isnan(corr) else 0.0)
        macro_correlation = np.mean(per_head_correlation)

        # Uncertainty-error correlation (key metric for Gaussian NLL)
        errors = (all_mu - all_targets) ** 2
        uncertainty_correlations = []
        for h in range(config.num_heads):
            corr, _ = stats.pearsonr(all_var[:, h], errors[:, h])
            uncertainty_correlations.append(float(corr) if not np.isnan(corr) else 0.0)
        uncertainty_corr = np.mean(uncertainty_correlations)

        # Log metrics
        epoch_metrics = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "macro_ece": current_ece,
            "per_head_ece": ece_result["per_head_ece"],
            "severity_mae": float(severity_mae),
            "macro_correlation": float(macro_correlation),
            "per_head_correlation": per_head_correlation,
            "uncertainty_correlation": float(uncertainty_corr),
            "per_head_uncertainty_corr": uncertainty_correlations,
            "mean_variance": float(all_var.mean()),
            "learning_rate": scheduler.get_last_lr()[0],
        }
        training_history.append(epoch_metrics)

        print(f"\nEpoch {epoch + 1}/{config.epochs}:")
        print(f"  Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}")
        print(f"  📊 ECE={current_ece:.4f} (target: <{config.ece_target})")
        print(f"  📊 MAE={severity_mae:.4f} (target: <{config.mae_target})")
        print(
            f"  📊 Corr={macro_correlation:.4f} (target: >{config.correlation_target})"
        )
        print(
            f"  📊 Uncertainty-Error Corr={uncertainty_corr:.4f} (target: >{config.uncertainty_correlation_target})"
        )
        print(f"  Mean Variance: {all_var.mean():.6f}")

        # Track best metrics
        improved = False
        if current_ece < best_ece:
            best_ece = current_ece
            improved = True
        if severity_mae < best_mae:
            best_mae = severity_mae
        if macro_correlation > best_correlation:
            best_correlation = macro_correlation
        if uncertainty_corr > best_uncertainty_corr:
            best_uncertainty_corr = uncertainty_corr

        if improved or val_loss < best_val_loss:
            if val_loss < best_val_loss:
                best_val_loss = val_loss
            epochs_without_improvement = 0

            # Save checkpoint
            checkpoint_path = Path(
                f"/checkpoints/production_model_seed{config.seed}.pt"
            )
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "macro_ece": current_ece,
                    "per_head_ece": ece_result["per_head_ece"],
                    "severity_mae": float(severity_mae),
                    "macro_correlation": float(macro_correlation),
                    "uncertainty_correlation": float(uncertainty_corr),
                    "seed": config.seed,
                    "config": config.__dict__,
                    "loss_type": "gaussian_nll",
                },
                checkpoint_path,
            )
            checkpoint_volume.commit()
            print(
                f"  ✅ Saved checkpoint (ECE={current_ece:.4f}, Corr={macro_correlation:.4f})"
            )
        else:
            epochs_without_improvement += 1
            print(f"  ⚠️ No improvement for {epochs_without_improvement} epochs")

        # Status
        ece_met = current_ece < config.ece_target
        mae_met = severity_mae < config.mae_target
        corr_met = macro_correlation > config.correlation_target
        unc_met = uncertainty_corr > config.uncertainty_correlation_target
        min_epochs_met = (epoch + 1) >= config.min_epochs

        print(
            f"  Status: ECE{'✅' if ece_met else '❌'} MAE{'✅' if mae_met else '❌'} Corr{'✅' if corr_met else '❌'} Unc{'✅' if unc_met else '❌'}"
        )

        # Early stopping (all targets + minimum epochs)
        if ece_met and mae_met and corr_met and unc_met and min_epochs_met:
            print("\n🎯 ALL PRODUCTION TARGETS ACHIEVED!")
            print(f"   ECE={current_ece:.4f} < {config.ece_target}")
            print(f"   MAE={severity_mae:.4f} < {config.mae_target}")
            print(f"   Corr={macro_correlation:.4f} > {config.correlation_target}")
            print(
                f"   Uncertainty Corr={uncertainty_corr:.4f} > {config.uncertainty_correlation_target}"
            )
            break

        if epochs_without_improvement >= config.early_stop_patience:
            print(
                f"\n⏹️ Early stopping: No improvement for {config.early_stop_patience} epochs"
            )
            break

    # Save training history
    history_path = Path(f"/checkpoints/production_history_seed{config.seed}.json")
    with open(history_path, "w") as f:
        json.dump(training_history, f, indent=2)
    checkpoint_volume.commit()

    # Final summary
    print("\n" + "=" * 60)
    print("PRODUCTION TRAINING COMPLETE")
    print("=" * 60)
    print("Loss Type: Gaussian NLL (uncertainty-aware)")
    print(f"Best ECE: {best_ece:.4f} (target: <{config.ece_target})")
    print(f"Best MAE: {best_mae:.4f} (target: <{config.mae_target})")
    print(
        f"Best Correlation: {best_correlation:.4f} (target: >{config.correlation_target})"
    )
    print(
        f"Best Uncertainty Corr: {best_uncertainty_corr:.4f} (target: >{config.uncertainty_correlation_target})"
    )
    print(f"Epochs trained: {epoch + 1}/{config.epochs}")

    all_met = (
        best_ece < config.ece_target
        and best_mae < config.mae_target
        and best_correlation > config.correlation_target
    )

    if all_met:
        print("\n✅ PRODUCTION MODEL READY FOR DEPLOYMENT")
    else:
        print("\n⚠️ Some targets not met - review training history")

    return {
        "seed": config.seed,
        "loss_type": "gaussian_nll",
        "epochs_trained": epoch + 1,
        "best_ece": best_ece,
        "best_mae": best_mae,
        "best_correlation": best_correlation,
        "best_uncertainty_corr": best_uncertainty_corr,
        "all_targets_met": all_met,
        "checkpoint_path": str(checkpoint_path),
    }


@stub.local_entrypoint()
def main(seed: int = 42):
    """Run production training."""
    print(f"Starting Phase 7 PRODUCTION training (seed={seed})...")
    result = train_production.remote(seed=seed)
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
