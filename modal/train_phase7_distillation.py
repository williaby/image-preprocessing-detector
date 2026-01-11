# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 7 Knowledge Distillation - ResNet-50 Teacher → ResNet-18 Student.

Sprint 5: Train lightweight ResNet-18 student model via knowledge distillation
from the Phase 7 production ResNet-50 teacher with Gaussian NLL/uncertainty heads.

Key Architecture:
- Teacher: ResNet-50 (2048 features) → 5 UncertaintyHeads (μ + log_var)
- Student: ResNet-18 (512 features) → 5 UncertaintyHeads (μ + log_var)

Distillation Loss:
- 70% soft targets: MSE between teacher and student severity predictions (μ)
- 30% hard targets: Gaussian NLL on ground truth labels
- Optional: KL divergence on uncertainty distributions

Success Criteria (per PHASE7_IDEAL_STATE_PROJECT_PLAN_v2):
- ResNet-18 ECE within +0.03 of ResNet-50 (teacher ECE=0.0214, so student < 0.0514)
- CPU latency < 60ms/page (8-core)
- Model size < 50MB (quantized)

Usage:
    modal run modal/train_phase7_distillation.py

Monitor:
    modal app logs iqa-phase7-distillation --follow

Reference:
    PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 2.3, 8.2 Phase 3
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
stub = modal.App("iqa-phase7-distillation")

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
        "onnx>=1.14.0",
        "onnxscript>=0.1.0",
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
# Mount both production and distillation checkpoint volumes
production_volume = modal.Volume.from_name(
    "phase7-production-checkpoints", create_if_missing=True
)
distillation_volume = modal.Volume.from_name(
    "phase7-distillation-checkpoints", create_if_missing=True
)


@dataclass
class DistillationConfig:
    """Configuration for Phase 7 Knowledge Distillation."""

    # Dataset (same as production training)
    gcs_bucket: str = "image_detection_b"
    gcs_prefix: str = "datasets/phase7_mvp"

    # Teacher (ResNet-50 from production)
    teacher_architecture: str = "resnet50"
    teacher_checkpoint: str = "production_model_seed42.pt"
    teacher_feature_dim: int = 2048

    # Student model - ResNet-18 architecture
    student_architecture: str = "resnet18"
    student_feature_dim: int = 512

    # Common
    num_heads: int = 5  # blur, noise, compression, contrast, geometric
    dropout: float = 0.3
    pretrained: bool = True

    # Resolution (same as teacher)
    input_resolution: int = 384

    # Distillation parameters
    distillation_alpha: float = 0.7  # Weight for soft targets (teacher predictions)
    temperature: float = 2.0  # Temperature for soft targets
    hard_loss_weight: float = 0.3  # Weight for hard targets (ground truth)

    # Training
    epochs: int = 50  # Fewer epochs needed for distillation
    batch_size: int = 48  # Larger batch for student (smaller model)
    learning_rate: float = 3e-4  # Higher LR for student
    weight_decay: float = 0.02
    warmup_epochs: int = 3
    min_lr: float = 1e-6
    gradient_clip: float = 1.0
    seed: int = 42

    # Success criteria (relative to teacher)
    teacher_ece: float = 0.0214  # From production training
    ece_tolerance: float = 0.03  # Student ECE < teacher + tolerance
    mae_target: float = 0.12  # Slightly relaxed from teacher's 0.0953
    correlation_target: float = 0.75  # Relaxed from 0.80
    early_stop_patience: int = 10
    num_ece_bins: int = 15
    min_epochs: int = 10


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    import random  # nosec B311 - used for ML reproducibility, not cryptographic

    import numpy as np
    import torch

    random.seed(seed)  # nosec B311
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
        tar.extractall(path=extract_path, members=members, filter="data")


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

    dataset_dir = Path("/tmp/phase7_distillation")  # nosec B108 - Modal container isolation
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
    volumes={
        "/production_checkpoints": production_volume,
        "/distillation_checkpoints": distillation_volume,
    },
)
def train_distillation(seed: int = 42) -> dict[str, Any]:
    """Train ResNet-18 student via knowledge distillation from ResNet-50 teacher."""
    import albumentations as alb
    import numpy as np
    import timm
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from albumentations.pytorch import ToTensorV2
    from PIL import Image
    from scipy import stats
    from torch.utils.data import DataLoader, Dataset

    print("=" * 60)
    print("PHASE 7 KNOWLEDGE DISTILLATION")
    print("Teacher: ResNet-50 (production, Gaussian NLL)")
    print("Student: ResNet-18 (lightweight)")
    print("=" * 60)

    config = DistillationConfig(seed=seed)
    set_seed(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # =========================================================================
    # Model Definitions (shared architecture, different backbones)
    # =========================================================================

    class UncertaintyHead(nn.Module):
        """Single head that outputs mean (mu) and log variance (log_var)."""

        def __init__(
            self, in_features: int, hidden_dim: int = 256, dropout: float = 0.3
        ):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.mu_head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),  # Output in [0, 1]
            )
            self.log_var_head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),  # Unbounded log variance
            )

        def forward(self, x):
            shared = self.shared(x)
            mu = self.mu_head(shared)
            log_var = self.log_var_head(shared)
            return mu, log_var

    class UncertaintyIQAModel(nn.Module):
        """IQA model with separate uncertainty heads for each defect type."""

        def __init__(
            self,
            backbone,
            feature_dim: int,
            num_heads: int,
            dropout: float,
            hidden_dim: int = 256,
        ):
            super().__init__()
            self.backbone = backbone
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.heads = nn.ModuleList(
                [
                    UncertaintyHead(feature_dim, hidden_dim, dropout)
                    for _ in range(num_heads)
                ]
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

    # =========================================================================
    # Load Teacher Model
    # =========================================================================

    print("\n🎓 Loading Teacher Model (ResNet-50)...")
    teacher_checkpoint_path = Path(
        f"/production_checkpoints/{config.teacher_checkpoint}"
    )

    if not teacher_checkpoint_path.exists():
        raise FileNotFoundError(
            f"Teacher checkpoint not found: {teacher_checkpoint_path}"
        )

    teacher_backbone = timm.create_model(
        config.teacher_architecture, pretrained=False, num_classes=0
    )
    teacher = UncertaintyIQAModel(
        teacher_backbone,
        config.teacher_feature_dim,
        config.num_heads,
        config.dropout,
        hidden_dim=256,
    )

    # Load teacher weights
    checkpoint = torch.load(  # nosec B614
        teacher_checkpoint_path, map_location=device, weights_only=False
    )
    teacher.load_state_dict(checkpoint["model_state_dict"])
    teacher = teacher.to(device)
    teacher.eval()

    # Freeze teacher
    for param in teacher.parameters():
        param.requires_grad = False

    teacher_params = sum(p.numel() for p in teacher.parameters())
    print(f"  Teacher loaded from epoch {checkpoint.get('epoch', 'unknown')}")
    print(f"  Teacher ECE: {checkpoint.get('macro_ece', config.teacher_ece):.4f}")
    print(f"  Teacher MAE: {checkpoint.get('severity_mae', 'unknown')}")
    print(f"  Teacher Correlation: {checkpoint.get('macro_correlation', 'unknown')}")
    print(f"  Teacher parameters: {teacher_params:,}")

    # Update config with actual teacher ECE
    if "macro_ece" in checkpoint:
        config.teacher_ece = checkpoint["macro_ece"]

    # =========================================================================
    # Create Student Model
    # =========================================================================

    print("\n📚 Creating Student Model (ResNet-18)...")
    student_backbone = timm.create_model(
        config.student_architecture, pretrained=config.pretrained, num_classes=0
    )
    student = UncertaintyIQAModel(
        student_backbone,
        config.student_feature_dim,
        config.num_heads,
        config.dropout,
        hidden_dim=128,  # Smaller hidden dim for student
    )
    student = student.to(device)

    student_params = sum(p.numel() for p in student.parameters())
    compression_ratio = teacher_params / student_params
    print(f"  Student parameters: {student_params:,}")
    print(f"  Compression ratio: {compression_ratio:.2f}x")

    # =========================================================================
    # Dataset
    # =========================================================================

    print("\n📥 Downloading dataset...")
    dataset_dir = prepare_dataset(config.gcs_bucket, config.gcs_prefix)

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
            img_path = self.images_dir / sample["filename"]
            image = np.array(Image.open(img_path).convert("RGB"))

            if self.transform:
                transformed = self.transform(image=image)
                image = transformed["image"]

            severity = sample.get("severity_scores", {})
            skew = severity.get("skew_severity", 0.0)
            perspective = severity.get("perspective_severity", 0.0)
            geometric = max(skew, perspective)

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

    # =========================================================================
    # Distillation Loss
    # =========================================================================

    class DistillationLoss(nn.Module):
        """Combined loss for knowledge distillation with uncertainty heads.

        Loss = alpha * soft_loss + (1 - alpha) * hard_loss

        Where:
        - soft_loss: MSE between teacher and student severity predictions
        - hard_loss: Gaussian NLL between student predictions and ground truth
        """

        def __init__(
            self,
            alpha: float = 0.7,
            temperature: float = 2.0,
            var_min: float = 1e-4,
            var_max: float = 10.0,
        ):
            super().__init__()
            self.alpha = alpha
            self.temperature = temperature
            self.var_min = var_min
            self.var_max = var_max

        def forward(
            self, student_mu, student_log_var, teacher_mu, _teacher_log_var, targets
        ):
            # Soft loss: MSE between teacher and student severity predictions
            # Scale by temperature squared (as in Hinton et al.)
            soft_loss = nn.functional.mse_loss(student_mu, teacher_mu) * (
                self.temperature**2
            )

            # Hard loss: Gaussian NLL for student on ground truth
            var = torch.exp(student_log_var).clamp(self.var_min, self.var_max)
            hard_loss = 0.5 * (torch.log(var) + ((targets - student_mu) ** 2) / var)
            hard_loss = hard_loss.mean()

            # Combined loss
            total_loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss

            return {
                "total": total_loss,
                "soft": soft_loss,
                "hard": hard_loss,
            }

    loss_fn = DistillationLoss(
        alpha=config.distillation_alpha,
        temperature=config.temperature,
    )
    optimizer = optim.AdamW(
        student.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
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

    # =========================================================================
    # Training Loop
    # =========================================================================

    print("\n🚀 Starting DISTILLATION training...")
    print(f"Teacher ECE: {config.teacher_ece:.4f}")
    print(f"Student ECE target: < {config.teacher_ece + config.ece_tolerance:.4f}")
    print(f"Distillation alpha: {config.distillation_alpha} (soft targets)")
    print(f"Hard loss weight: {1 - config.distillation_alpha}")

    best_val_loss = float("inf")
    best_ece = float("inf")
    best_mae = float("inf")
    best_correlation = float("-inf")
    epochs_without_improvement = 0
    training_history = []

    for epoch in range(config.epochs):
        # Train
        student.train()
        train_loss = 0.0
        train_soft_loss = 0.0
        train_hard_loss = 0.0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)

            # Get teacher predictions (no grad)
            with torch.no_grad():
                teacher_mu, teacher_log_var = teacher(images)

            # Get student predictions
            optimizer.zero_grad()
            student_mu, student_log_var = student(images)

            # Compute distillation loss
            losses = loss_fn(
                student_mu, student_log_var, teacher_mu, teacher_log_var, labels
            )
            loss = losses["total"]

            # Gradient clipping
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), config.gradient_clip)
            optimizer.step()

            train_loss += loss.item()
            train_soft_loss += losses["soft"].item()
            train_hard_loss += losses["hard"].item()

            if batch_idx % 50 == 0:
                print(
                    f"  Epoch {epoch + 1}/{config.epochs} | Batch {batch_idx}/{len(train_loader)} | "
                    f"Loss: {loss.item():.4f} (soft: {losses['soft'].item():.4f}, hard: {losses['hard'].item():.4f})"
                )

        train_loss /= len(train_loader)
        train_soft_loss /= len(train_loader)
        train_hard_loss /= len(train_loader)
        scheduler.step()

        # Validate
        student.eval()
        val_loss = 0.0
        all_mu = []
        all_var = []
        all_targets = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)

                student_mu, student_log_var = student(images)
                teacher_mu, teacher_log_var = teacher(images)

                losses = loss_fn(
                    student_mu, student_log_var, teacher_mu, teacher_log_var, labels
                )
                val_loss += losses["total"].item()

                all_mu.append(student_mu.cpu().numpy())
                all_var.append(torch.exp(student_log_var).cpu().numpy())
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

        # Pearson correlation
        per_head_correlation = []
        for h in range(config.num_heads):
            corr, _ = stats.pearsonr(all_mu[:, h], all_targets[:, h])
            per_head_correlation.append(float(corr) if not np.isnan(corr) else 0.0)
        macro_correlation = np.mean(per_head_correlation)

        # Log metrics
        epoch_metrics = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "train_soft_loss": train_soft_loss,
            "train_hard_loss": train_hard_loss,
            "val_loss": val_loss,
            "macro_ece": current_ece,
            "per_head_ece": ece_result["per_head_ece"],
            "severity_mae": float(severity_mae),
            "macro_correlation": float(macro_correlation),
            "per_head_correlation": per_head_correlation,
            "mean_variance": float(all_var.mean()),
            "learning_rate": scheduler.get_last_lr()[0],
        }
        training_history.append(epoch_metrics)

        # ECE gap from teacher
        ece_gap = current_ece - config.teacher_ece

        print(f"\nEpoch {epoch + 1}/{config.epochs}:")
        print(
            f"  Train Loss={train_loss:.4f} (soft={train_soft_loss:.4f}, hard={train_hard_loss:.4f})"
        )
        print(f"  Val Loss={val_loss:.4f}")
        print(
            f"  📊 ECE={current_ece:.4f} (teacher: {config.teacher_ece:.4f}, gap: {ece_gap:+.4f})"
        )
        print(f"  📊 MAE={severity_mae:.4f} (target: <{config.mae_target})")
        print(
            f"  📊 Corr={macro_correlation:.4f} (target: >{config.correlation_target})"
        )

        # Track best metrics
        improved = False
        if current_ece < best_ece:
            best_ece = current_ece
            improved = True
        if severity_mae < best_mae:
            best_mae = severity_mae
        if macro_correlation > best_correlation:
            best_correlation = macro_correlation

        if improved or val_loss < best_val_loss:
            if val_loss < best_val_loss:
                best_val_loss = val_loss
            epochs_without_improvement = 0

            # Save checkpoint
            checkpoint_path = Path(
                f"/distillation_checkpoints/student_model_seed{config.seed}.pt"
            )
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": student.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "macro_ece": current_ece,
                    "per_head_ece": ece_result["per_head_ece"],
                    "severity_mae": float(severity_mae),
                    "macro_correlation": float(macro_correlation),
                    "teacher_ece": config.teacher_ece,
                    "ece_gap": ece_gap,
                    "seed": config.seed,
                    "config": {
                        "student_architecture": config.student_architecture,
                        "input_resolution": config.input_resolution,
                        "num_heads": config.num_heads,
                        "distillation_alpha": config.distillation_alpha,
                        "temperature": config.temperature,
                    },
                },
                checkpoint_path,
            )
            distillation_volume.commit()
            print(f"  ✅ Saved checkpoint (ECE={current_ece:.4f}, gap={ece_gap:+.4f})")
        else:
            epochs_without_improvement += 1
            print(f"  ⚠️ No improvement for {epochs_without_improvement} epochs")

        # Status
        ece_target = config.teacher_ece + config.ece_tolerance
        ece_met = current_ece < ece_target
        mae_met = severity_mae < config.mae_target
        corr_met = macro_correlation > config.correlation_target
        min_epochs_met = (epoch + 1) >= config.min_epochs

        print(
            f"  Status: ECE{'✅' if ece_met else '❌'} MAE{'✅' if mae_met else '❌'} Corr{'✅' if corr_met else '❌'}"
        )

        # Early stopping
        if ece_met and mae_met and corr_met and min_epochs_met:
            print("\n🎯 DISTILLATION TARGETS ACHIEVED!")
            print(
                f"   Student ECE={current_ece:.4f} < {ece_target:.4f} (teacher + {config.ece_tolerance})"
            )
            print(f"   MAE={severity_mae:.4f} < {config.mae_target}")
            print(f"   Corr={macro_correlation:.4f} > {config.correlation_target}")
            break

        if epochs_without_improvement >= config.early_stop_patience:
            print(
                f"\n⏹️ Early stopping: No improvement for {config.early_stop_patience} epochs"
            )
            break

    # Save training history
    history_path = Path(
        f"/distillation_checkpoints/distillation_history_seed{config.seed}.json"
    )
    with open(history_path, "w") as f:
        json.dump(training_history, f, indent=2)
    distillation_volume.commit()

    # =========================================================================
    # Export to ONNX
    # =========================================================================

    print("\n📦 Exporting to ONNX...")
    student.eval()

    # Create a wrapper that returns only mu for inference
    class StudentInference(nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, x):
            mu, log_var = self.model(x)
            # Return mu (severity predictions) and variance (uncertainty)
            var = torch.exp(log_var)
            return mu, var

    inference_model = StudentInference(student).to(device)
    dummy_input = torch.randn(
        1, 3, config.input_resolution, config.input_resolution, device=device
    )

    onnx_path = Path(
        f"/distillation_checkpoints/resnet18_student_seed{config.seed}.onnx"
    )
    torch.onnx.export(
        inference_model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["image"],
        output_names=["severity", "uncertainty"],
        dynamic_axes={
            "image": {0: "batch_size"},
            "severity": {0: "batch_size"},
            "uncertainty": {0: "batch_size"},
        },
    )
    distillation_volume.commit()

    onnx_size_mb = onnx_path.stat().st_size / (1024**2)
    print(f"  ONNX model size: {onnx_size_mb:.2f} MB")

    # =========================================================================
    # Final Summary
    # =========================================================================

    print("\n" + "=" * 60)
    print("DISTILLATION COMPLETE")
    print("=" * 60)
    print(f"Teacher: {config.teacher_architecture} ({teacher_params:,} params)")
    print(f"Student: {config.student_architecture} ({student_params:,} params)")
    print(f"Compression: {compression_ratio:.2f}x")
    print(f"ONNX size: {onnx_size_mb:.2f} MB")
    print()
    print(f"Teacher ECE: {config.teacher_ece:.4f}")
    print(f"Student ECE: {best_ece:.4f} (gap: {best_ece - config.teacher_ece:+.4f})")
    print(f"Student MAE: {best_mae:.4f}")
    print(f"Student Correlation: {best_correlation:.4f}")
    print(f"Epochs trained: {epoch + 1}/{config.epochs}")

    ece_target = config.teacher_ece + config.ece_tolerance
    all_met = (
        best_ece < ece_target
        and best_mae < config.mae_target
        and best_correlation > config.correlation_target
    )

    if all_met:
        print("\n✅ STUDENT MODEL READY FOR DEPLOYMENT")
    else:
        print("\n⚠️ Some targets not met - review training history")

    return {
        "seed": config.seed,
        "teacher_architecture": config.teacher_architecture,
        "student_architecture": config.student_architecture,
        "teacher_params": teacher_params,
        "student_params": student_params,
        "compression_ratio": compression_ratio,
        "onnx_size_mb": onnx_size_mb,
        "epochs_trained": epoch + 1,
        "teacher_ece": config.teacher_ece,
        "best_student_ece": best_ece,
        "ece_gap": best_ece - config.teacher_ece,
        "best_mae": best_mae,
        "best_correlation": best_correlation,
        "all_targets_met": all_met,
        "checkpoint_path": str(checkpoint_path),
        "onnx_path": str(onnx_path),
    }


@stub.local_entrypoint()
def main(seed: int = 42):
    """Run distillation training."""
    print(f"Starting Phase 7 DISTILLATION training (seed={seed})...")
    result = train_distillation.remote(seed=seed)
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
