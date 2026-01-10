# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 7 MVP Training on Modal - Simplified ResNet-50 Teacher.

Trains on the 25K MVP dataset with continuous severity labels.

Dataset: gs://image_detection_b/datasets/phase7_mvp/
- phase7_mvp_train.tar.gz (17,469 samples, 602 MB)
- phase7_mvp_val.tar.gz (3,719 samples, 126 MB)
- phase7_mvp_test.tar.gz (3,812 samples, 130 MB)

Usage:
    # Default seed (42)
    modal run modal/train_phase7_mvp.py

    # Custom seed for reproducibility studies
    modal run modal/train_phase7_mvp.py --seed 123

    # Multi-seed training (run separately)
    modal run modal/train_phase7_mvp.py --seed 42
    modal run modal/train_phase7_mvp.py --seed 123
    modal run modal/train_phase7_mvp.py --seed 456

Monitor:
    modal app logs iqa-phase7-mvp --follow
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
stub = modal.App("iqa-phase7-mvp")

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
    )
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    .add_local_file("data/__init__.py", "/root/data/__init__.py", copy=True)
    .add_local_file("data/dataset.py", "/root/data/dataset.py", copy=True)
    .add_local_file("data/augmentation.py", "/root/data/augmentation.py", copy=True)
    .add_local_file("data/continuous_labels.py", "/root/data/continuous_labels.py", copy=True)
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)

gcs_secret = modal.Secret.from_name("gcs-credentials")
checkpoint_volume = modal.Volume.from_name("phase7-mvp-checkpoints", create_if_missing=True)


@dataclass
class MVPTrainingConfig:
    """Configuration for Phase 7 MVP training."""

    # Dataset
    gcs_bucket: str = "image_detection_b"
    gcs_prefix: str = "datasets/phase7_mvp"

    # Model (5 heads for compatibility)
    model_architecture: str = "resnet50"
    num_heads: int = 5
    dropout: float = 0.2
    pretrained: bool = True

    # Loss function - BCE + MSE combined
    loss_alpha: float = 0.6  # BCE weight
    loss_beta: float = 0.4   # MSE weight

    # Training
    epochs: int = 50  # Increased from 30 for better convergence
    batch_size: int = 64
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    seed: int = 42  # Random seed for reproducibility

    # Early stopping (Sprint 4: ECE + correlation targets per IDEAL_STATE_PROJECT_PLAN_v2)
    ece_target: float = 0.08  # Primary target: ECE < 0.08
    mae_target: float = 0.15  # Secondary target: Severity MAE < 0.15
    correlation_target: float = 0.70  # Correlation > 0.70 (relaxed from 0.85 for MVP)
    early_stop_patience: int = 10  # Stop if no improvement for N epochs
    num_ece_bins: int = 15  # Number of bins for ECE computation
    min_epochs: int = 10  # Minimum epochs before early stopping (prevent premature stop)

    # Output
    output_gcs_path: str = "gs://image_detection_b/models/phase7_mvp"


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility across all libraries."""
    import random

    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # For reproducibility on CUDA (may impact performance)
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


def compute_ece_numpy(
    predictions: Any,
    targets: Any,
    num_bins: int = 15,
) -> dict:
    """Compute Expected Calibration Error using numpy.

    ECE measures how well predicted probabilities match actual outcomes.
    Lower is better; target is < 0.08 for Sprint 4.

    Args:
        predictions: Predicted probabilities [0,1], shape (n_samples, n_classes)
        targets: True labels [0,1], shape (n_samples, n_classes)
        num_bins: Number of calibration bins

    Returns:
        Dictionary with macro_ece and per_head_ece
    """
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
            if i == num_bins - 1:
                in_bin = (preds_c >= lower) & (preds_c <= upper)
            else:
                in_bin = (preds_c >= lower) & (preds_c < upper)

            bin_size = in_bin.sum()
            if bin_size > 0:
                bin_accuracy = targs_c[in_bin].mean()
                bin_confidence = preds_c[in_bin].mean()
                ece += (bin_size / n_samples) * abs(bin_accuracy - bin_confidence)

        per_head_ece.append(ece)

    macro_ece = np.mean(per_head_ece)
    return {
        "macro_ece": float(macro_ece),
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


def prepare_mvp_dataset(bucket_name: str, gcs_prefix: str) -> Path:
    """Download and prepare MVP dataset."""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    dataset_dir = Path("/tmp/phase7_mvp")
    images_dir = dataset_dir / "images"

    # Check if already downloaded
    if (dataset_dir / "train_metadata.json").exists():
        with open(dataset_dir / "train_metadata.json") as f:
            train_count = len(json.load(f))
        image_count = len(list(images_dir.glob("*.jpg"))) if images_dir.exists() else 0
        if image_count > train_count * 0.9:
            print(f"Dataset already exists: {train_count} train, {image_count} images")
            return dataset_dir

    dataset_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    all_train_samples = []

    # Download train archive
    print("\n[Train]")
    download_and_extract(
        bucket_name,
        f"{gcs_prefix}/phase7_mvp_train.tar.gz",
        dataset_dir
    )

    # Move images and load metadata
    for _img in (dataset_dir / "images").glob("*.jpg"):
        # Already in place
        pass

    train_meta = dataset_dir / "train_metadata.json"
    if train_meta.exists():
        with open(train_meta) as f:
            all_train_samples = json.load(f)
        print(f"  Train samples: {len(all_train_samples)}")

    # Download val archive
    print("\n[Val]")
    download_and_extract(
        bucket_name,
        f"{gcs_prefix}/phase7_mvp_val.tar.gz",
        dataset_dir
    )

    val_meta = dataset_dir / "val_metadata.json"
    if val_meta.exists():
        with open(val_meta) as f:
            val_samples = json.load(f)
        print(f"  Val samples: {len(val_samples)}")

    # Download test archive
    print("\n[Test]")
    download_and_extract(
        bucket_name,
        f"{gcs_prefix}/phase7_mvp_test.tar.gz",
        dataset_dir
    )

    test_meta = dataset_dir / "test_metadata.json"
    if test_meta.exists():
        with open(test_meta) as f:
            test_samples = json.load(f)
        print(f"  Test samples: {len(test_samples)}")

    # Verify
    image_count = len(list(images_dir.glob("*.jpg")))
    print(f"\nTotal images: {image_count}")

    return dataset_dir


@stub.function(
    image=image,
    gpu="A10G",
    timeout=7200,  # 2 hours - 30 epochs takes ~1.5-2 hours
    secrets=[gcs_secret],
    volumes={"/checkpoints": checkpoint_volume},
)
def train_mvp(seed: int = 42):
    """Train ResNet-50 on MVP dataset.

    Args:
        seed: Random seed for reproducibility (default: 42)
    """
    import sys
    sys.path.insert(0, "/root")

    import albumentations as alb
    import timm
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from albumentations.pytorch import ToTensorV2
    from torch.utils.data import DataLoader

    from data.dataset import ContinuousIQADataset

    config = MVPTrainingConfig(seed=seed)

    # Set seeds for reproducibility
    set_seed(config.seed)

    print("=" * 60)
    print("PHASE 7 MVP TRAINING")
    print("=" * 60)
    print(f"Seed: {config.seed}")
    print(f"Model: {config.model_architecture}")
    print(f"Heads: {config.num_heads}")
    print(f"Epochs: {config.epochs}")
    print(f"Batch size: {config.batch_size}")
    print(f"Learning rate: {config.learning_rate}")

    # Prepare dataset
    print("\n📦 Preparing dataset...")
    dataset_dir = prepare_mvp_dataset(config.gcs_bucket, config.gcs_prefix)

    # Create transforms
    train_transform = alb.Compose([
        alb.Resize(384, 384),
        alb.HorizontalFlip(p=0.5),
        alb.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ToTensorV2(),
    ])

    val_transform = alb.Compose([
        alb.Resize(384, 384),
        alb.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ToTensorV2(),
    ])

    # Create datasets
    print("\n📊 Creating data loaders...")
    train_dataset = ContinuousIQADataset(dataset_dir, split="train", transform=train_transform)
    val_dataset = ContinuousIQADataset(dataset_dir, split="val", transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=4)

    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches: {len(val_loader)}")

    # Create model
    print("\n🏗️ Creating model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    backbone = timm.create_model(config.model_architecture, pretrained=config.pretrained, num_classes=0)
    feature_dim = backbone.num_features

    class MultiHeadIQA(nn.Module):
        def __init__(self, backbone, feature_dim, num_heads, dropout):
            super().__init__()
            self.backbone = backbone
            self.heads = nn.ModuleList([
                nn.Sequential(
                    nn.Dropout(dropout),
                    nn.Linear(feature_dim, 1),
                    nn.Sigmoid()
                )
                for _ in range(num_heads)
            ])

        def forward(self, x):
            features = self.backbone(x)
            outputs = [head(features) for head in self.heads]
            return torch.cat(outputs, dim=1)

    model = MultiHeadIQA(backbone, feature_dim, config.num_heads, config.dropout)
    model = model.to(device)

    # Loss and optimizer
    bce_loss = nn.BCELoss()
    mse_loss = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.epochs)

    # Training loop with ECE tracking (Sprint 4)
    print("\n🚀 Starting training...")
    print(f"ECE Target: {config.ece_target}")
    print(f"Early Stop Patience: {config.early_stop_patience}")

    best_val_loss = float("inf")
    best_ece = float("inf")
    best_mae = float("inf")
    best_correlation = float("-inf")
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
            outputs = model(images)

            # Combined loss
            loss = config.loss_alpha * bce_loss(outputs, labels) + config.loss_beta * mse_loss(outputs, labels)

            loss.backward()
            optimizer.step()

            train_loss += loss.item()

            if batch_idx % 50 == 0:
                print(f"  Epoch {epoch+1}/{config.epochs} | Batch {batch_idx}/{len(train_loader)} | Loss: {loss.item():.4f}")

        train_loss /= len(train_loader)

        # Validate with ECE computation
        model.eval()
        val_loss = 0.0
        all_predictions = []
        all_targets = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                loss = config.loss_alpha * bce_loss(outputs, labels) + config.loss_beta * mse_loss(outputs, labels)
                val_loss += loss.item()

                # Collect predictions for ECE
                all_predictions.append(outputs.cpu().numpy())
                all_targets.append(labels.cpu().numpy())

        val_loss /= len(val_loader)
        scheduler.step()

        # Compute ECE (Sprint 4 primary metric)
        import numpy as np
        from scipy import stats
        all_predictions = np.concatenate(all_predictions, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)
        ece_result = compute_ece_numpy(all_predictions, all_targets, config.num_ece_bins)
        current_ece = ece_result["macro_ece"]

        # Compute severity MAE
        severity_mae = np.abs(all_predictions - all_targets).mean()

        # Compute Pearson correlation (per head and macro)
        n_heads = all_predictions.shape[1]
        per_head_correlation = []
        for h in range(n_heads):
            corr, _ = stats.pearsonr(all_predictions[:, h], all_targets[:, h])
            per_head_correlation.append(float(corr) if not np.isnan(corr) else 0.0)
        macro_correlation = np.mean(per_head_correlation)

        # Log epoch results
        epoch_metrics = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "macro_ece": current_ece,
            "per_head_ece": ece_result["per_head_ece"],
            "severity_mae": float(severity_mae),
            "macro_correlation": float(macro_correlation),
            "per_head_correlation": per_head_correlation,
        }
        training_history.append(epoch_metrics)

        print(f"\nEpoch {epoch+1}/{config.epochs}:")
        print(f"  Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}")
        print(f"  📊 ECE={current_ece:.4f} (target: <{config.ece_target})")
        print(f"  📊 MAE={severity_mae:.4f} (target: <{config.mae_target})")
        print(f"  📊 Corr={macro_correlation:.4f} (target: >{config.correlation_target})")
        print(f"  Per-head ECE: {[f'{e:.4f}' for e in ece_result['per_head_ece']]}")
        print(f"  Per-head Corr: {[f'{c:.4f}' for c in per_head_correlation]}")

        # Check for improvement (track best metrics)
        improved = False
        if current_ece < best_ece:
            best_ece = current_ece
            improved = True

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            improved = True

        # Track best correlation and MAE for reporting
        if severity_mae < best_mae:
            best_mae = severity_mae
        if macro_correlation > best_correlation:
            best_correlation = macro_correlation

        if improved:
            epochs_without_improvement = 0
            # Save best model
            checkpoint_path = Path(f"/checkpoints/best_model_seed{config.seed}.pt")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "macro_ece": current_ece,
                "per_head_ece": ece_result["per_head_ece"],
                "severity_mae": float(severity_mae),
                "macro_correlation": float(macro_correlation),
                "per_head_correlation": per_head_correlation,
                "seed": config.seed,
                "config": config.__dict__,
            }, checkpoint_path)
            checkpoint_volume.commit()
            print(f"  ✅ Saved best model (ECE={current_ece:.4f}, MAE={severity_mae:.4f}, Corr={macro_correlation:.4f})")
        else:
            epochs_without_improvement += 1
            print(f"  ⚠️ No improvement for {epochs_without_improvement} epochs")

        # Early stopping checks - require ALL targets met AND minimum epochs
        ece_met = current_ece < config.ece_target
        mae_met = severity_mae < config.mae_target
        corr_met = macro_correlation > config.correlation_target
        min_epochs_met = (epoch + 1) >= config.min_epochs

        # Status indicators
        ece_status = "✅" if ece_met else "❌"
        mae_status = "✅" if mae_met else "❌"
        corr_status = "✅" if corr_met else "❌"
        print(f"  Status: ECE{ece_status} MAE{mae_status} Corr{corr_status}")

        # All three targets must be met for early stop (plus minimum epochs)
        if ece_met and mae_met and corr_met and min_epochs_met:
            print("\n🎯 ALL TARGETS ACHIEVED!")
            print(f"   ECE={current_ece:.4f} < {config.ece_target}")
            print(f"   MAE={severity_mae:.4f} < {config.mae_target}")
            print(f"   Corr={macro_correlation:.4f} > {config.correlation_target}")
            print("Stopping early - Sprint 4 objectives fully met!")
            break

        if epochs_without_improvement >= config.early_stop_patience:
            print(f"\n⏹️ Early stopping: No improvement for {config.early_stop_patience} epochs")
            break

    # Save training history
    history_path = Path(f"/checkpoints/training_history_seed{config.seed}.json")
    with open(history_path, "w") as f:
        json.dump(training_history, f, indent=2)
    checkpoint_volume.commit()

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Best ECE: {best_ece:.4f} (target: <{config.ece_target})")
    print(f"Best MAE: {best_mae:.4f} (target: <{config.mae_target})")
    print(f"Best Correlation: {best_correlation:.4f} (target: >{config.correlation_target})")
    print(f"Best Val Loss: {best_val_loss:.4f}")
    print(f"Epochs trained: {epoch + 1}/{config.epochs}")

    # Check all targets
    ece_met = best_ece < config.ece_target
    mae_met = best_mae < config.mae_target
    corr_met = best_correlation > config.correlation_target
    all_targets_met = ece_met and mae_met and corr_met

    print("\nTarget Status:")
    print(f"  ECE: {'✅' if ece_met else '❌'} ({best_ece:.4f} vs <{config.ece_target})")
    print(f"  MAE: {'✅' if mae_met else '❌'} ({best_mae:.4f} vs <{config.mae_target})")
    print(f"  Correlation: {'✅' if corr_met else '❌'} ({best_correlation:.4f} vs >{config.correlation_target})")
    print(f"\nSprint 4 ALL Targets Met: {'✅ YES' if all_targets_met else '❌ NO'}")

    return {
        "best_val_loss": best_val_loss,
        "best_ece": best_ece,
        "best_mae": best_mae,
        "best_correlation": best_correlation,
        "epochs_trained": epoch + 1,
        "ece_met": ece_met,
        "mae_met": mae_met,
        "corr_met": corr_met,
        "all_targets_met": all_targets_met,
        "seed": config.seed,
    }


@stub.local_entrypoint()
def main(seed: int = 42):
    """Entry point for modal run.

    Args:
        seed: Random seed for reproducibility (default: 42).
              Use different seeds (42, 123, 456) for uncertainty quantification.

    Sprint 4 Production Model Training (per PHASE7_IDEAL_STATE_PROJECT_PLAN_v2):
        - ECE Target: < 0.08
        - MAE Target: < 0.15
        - Correlation Target: > 0.70
        - Minimum 10 epochs before early stopping
    """
    print("=" * 60)
    print("PHASE 7 SPRINT 4: PRODUCTION MODEL TRAINING")
    print("=" * 60)
    print(f"Seed: {seed}")
    print("Targets (per IDEAL_STATE_PROJECT_PLAN_v2):")
    print("  ECE < 0.08")
    print("  MAE < 0.15")
    print("  Correlation > 0.70")
    print()

    result = train_mvp.remote(seed=seed)

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Seed: {result['seed']}")
    print(f"Epochs Trained: {result['epochs_trained']}")
    print()
    print("Metrics:")
    print(f"  ECE: {result['best_ece']:.4f} {'✅' if result['ece_met'] else '❌'}")
    print(f"  MAE: {result['best_mae']:.4f} {'✅' if result['mae_met'] else '❌'}")
    print(f"  Correlation: {result['best_correlation']:.4f} {'✅' if result['corr_met'] else '❌'}")
    print(f"  Val Loss: {result['best_val_loss']:.4f}")
    print()

    if result["all_targets_met"]:
        print("🎉 Sprint 4 COMPLETE - All production targets achieved!")
    else:
        print("⚠️ Sprint 4 targets not fully met:")
        if not result["ece_met"]:
            print(f"   - ECE {result['best_ece']:.4f} needs to be < 0.08")
        if not result["mae_met"]:
            print(f"   - MAE {result['best_mae']:.4f} needs to be < 0.15")
        if not result["corr_met"]:
            print(f"   - Correlation {result['best_correlation']:.4f} needs to be > 0.70")
        print("\nConsider:")
        print("   - More epochs (increase config.epochs)")
        print("   - Gaussian NLL loss (per plan recommendation)")
        print("   - Temperature scaling post-training")
