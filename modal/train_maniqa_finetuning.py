# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal training script for MANIQA fine-tuning on DIQA-5000.

MANIQA (Multi-dimension Attention Network for No-Reference IQA) is the best
performing model on DIQA-5000 benchmarks. This script implements a two-phase
fine-tuning protocol to adapt MANIQA for document-specific quality assessment.

Architecture:
    - 224x224 input resolution (MANIQA native)
    - ViT backbone with Swin Transformer blocks
    - Temporal attention blocks for quality regression
    - Multi-task head for 3 quality dimensions

Training Protocol:
    - Phase 1 (15 epochs): Head warmup with frozen backbone
    - Phase 2 (35 epochs): Full fine-tuning with differential LRs
    - Total: 50 epochs

Usage:
    modal run -d modal/train_maniqa_finetuning.py

Monitor:
    https://modal.com/apps
    modal app logs diqa-maniqa-finetuning --follow

Reference:
    - MANIQA: Multi-dimension Attention Network for No-Reference IQA (CVPR 2022)
    - Winner of NTIRE2022 NRIQA challenge
    - Best performer on DIQA-5000 benchmark (SRCC 0.55+)
"""

from __future__ import annotations

import json
import math
import os
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

import torch

import modal

# Constants
GCS_CREDENTIALS_PATH = "/root/.gcp/service-account.json"

# Create Modal app
app = modal.App("diqa-maniqa-finetuning")

# Define container image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    # Install system libraries required by OpenCV
    .apt_install(
        "libgl1-mesa-glx",
        "libglib2.0-0",
        "libsm6",
        "libxext6",
        "libxrender-dev",
    )
    .pip_install(
        # PyIQA for MANIQA backbone
        "pyiqa>=0.1.12",
        # Deep learning
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "timm>=0.9.0",  # Required for MANIQA ViT backbone
        "einops>=0.7.0",  # For tensor rearranging (MANIQA feature hook)
        # Image processing
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
        # Data augmentation
        "albumentations>=1.3.0",
        # Metrics
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        # Logging
        "structlog>=23.1.0",
        "rich>=13.0.0",
        # Export
        "onnx>=1.14.0",
        "onnxscript>=0.1.0",
        # GCS
        "google-cloud-storage>=2.10.0",
        "gcsfs>=2023.1.0",
        # Config
        "pyyaml>=6.0",
    )
    # Copy source code into container
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    # Copy GCS credentials
    .add_local_file(
        ".gcp/service-account.json",
        GCS_CREDENTIALS_PATH,
        copy=True,
    )
)


# Training configuration
TRAINING_CONFIG = {
    # Phase 1: Head warmup (frozen backbone)
    "phase1_epochs": 15,
    "phase1_lr": 1e-3,
    "phase1_warmup_epochs": 3,
    # Phase 2: Full fine-tuning
    "phase2_epochs": 35,
    "phase2_backbone_lr": 1e-6,  # Very low for pretrained ViT
    "phase2_head_lr": 1e-4,
    "phase2_warmup_epochs": 2,
    # General training
    "batch_size": 4,  # Small batch due to MANIQA memory usage (ViT + TABlock attention)
    "num_workers": 4,
    "weight_decay": 1e-4,
    "gradient_clip_norm": 1.0,
    "gradient_accumulation_steps": 8,  # Effective batch size = 32
    # Loss weights (generalist - balanced across all dimensions)
    "loss_weights": {"overall": 0.34, "sharpness": 0.33, "color": 0.33},
    "mse_weight": 0.6,
    "rank_weight": 0.2,
    "focal_weight": 0.2,
    # Model
    "input_size": 224,  # MANIQA native resolution
    "head_hidden_dim": 384,  # Match MANIQA embedding
    "head_dropout": 0.1,
    # Checkpoint
    "checkpoint_interval": 5,
    # Computed
    "total_epochs": 50,
}


def download_diqa5000(bucket_name: str, target_dir: Path) -> Path:
    """Download DIQA-5000 dataset from GCS.

    Args:
        bucket_name: GCS bucket name.
        target_dir: Local directory to extract dataset.

    Returns:
        Path to extracted dataset directory.
    """
    from google.cloud import storage

    target_dir.mkdir(parents=True, exist_ok=True)

    # Set GCS credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCS_CREDENTIALS_PATH

    print(f"Downloading DIQA-5000 from gs://{bucket_name}/datasets/diqa-5000/")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Download tarball
    tar_blob = bucket.blob("datasets/diqa-5000/diqa-5000.tar.gz")
    tar_path = target_dir / "diqa-5000.tar.gz"

    start = time.time()
    tar_blob.download_to_filename(str(tar_path))
    download_time = time.time() - start

    tar_size_gb = tar_path.stat().st_size / (1024**3)
    print(f"Downloaded {tar_size_gb:.2f} GB in {download_time:.1f}s")

    # Extract
    print("Extracting dataset...")
    extract_start = time.time()

    def is_within_directory(directory: Path, target: Path) -> bool:
        abs_directory = directory.resolve()
        abs_target = target.resolve()
        return str(abs_target).startswith(str(abs_directory))

    with tarfile.open(tar_path, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            member_path = target_dir / member.name
            if not is_within_directory(target_dir, member_path):
                raise ValueError(f"Path traversal detected: {member.name}")
        # nosec B202: Path traversal validation performed above
        tar.extractall(path=target_dir, members=members)

    extract_time = time.time() - extract_start
    print(f"Extracted in {extract_time:.1f}s")

    # Clean up tarball
    tar_path.unlink()

    return target_dir / "diqa-5000"


def create_dataloaders(
    root_dir: Path,
    batch_size: int,
    num_workers: int,
    phase: int,
    input_size: int = 224,
) -> tuple[Any, Any]:
    """Create train/val dataloaders for MANIQA training.

    Uses the shared DIQA5000 dataset infrastructure from musiq_dataset.py
    which properly handles the CSV-based DIQA-5000 structure.

    Args:
        root_dir: Dataset root directory.
        batch_size: Batch size.
        num_workers: Number of worker processes.
        phase: Training phase (1 or 2) - affects augmentation.
        input_size: Input image size for MANIQA.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
        create_dataloaders as create_diqa_dataloaders,
    )

    # Use the shared dataloader factory
    # This handles the CSV-based DIQA-5000 structure correctly
    return create_diqa_dataloaders(
        root_dir=root_dir,
        batch_size=batch_size,
        num_workers=num_workers,
        phase=phase,
        target_size=input_size,
    )


class MANIQAMultiTask(torch.nn.Module):
    """MANIQA wrapper with multi-task head for DIQA training.

    Uses pretrained MANIQA backbone with custom multi-task head
    for predicting overall, sharpness, and color quality scores.

    MANIQA Architecture Notes:
        - MANIQA has fc_score and fc_weight (not fc)
        - Feature dimension is 384 (from TABlock output)
        - fc_score: Sequential(Linear(384->384), ReLU, Dropout, Linear(384->1), ReLU)
        - fc_weight: Sequential(Linear(384->384), ReLU, Dropout, Linear(384->1), Sigmoid)

    Feature Extraction Strategy:
        We register a forward hook on swintransformer2 to capture the
        384-dim features before fc_score processing. The features are
        [B, H*W, 384] which we average-pool to [B, 384] for our multi-task head.
    """

    def __init__(
        self,
        freeze_backbone: bool = True,
        head_hidden_dim: int = 384,
        head_dropout: float = 0.1,
    ) -> None:
        """Initialize MANIQA with multi-task head.

        Args:
            freeze_backbone: Whether to freeze backbone initially.
            head_hidden_dim: Hidden dimension for multi-task head.
            head_dropout: Dropout for head.
        """
        import pyiqa
        import torch.nn as nn
        from einops import rearrange

        super().__init__()

        # Load pretrained MANIQA
        # Get the underlying model, not the metric wrapper
        metric = pyiqa.create_metric("maniqa", device="cpu", as_loss=True)
        self.backbone = metric.net
        self._rearrange = rearrange

        # CRITICAL: Force single crop mode to avoid patch dimension issues
        # MANIQA uses crop_num=1 for training but test_sample (default 20) for eval
        # This causes feature dimension mismatches. Force test_sample=1 for consistency.
        self.backbone.test_sample = 1

        # MANIQA feature dimension is 384 (from TABlock output)
        feature_dim = 384

        # Store captured features from hook and original batch size
        self._captured_features: torch.Tensor | None = None
        self._original_bsz: int = 0

        # Register hook to capture features after swintransformer2
        def _capture_hook(
            _module: torch.nn.Module, _input: tuple, output: torch.Tensor
        ) -> None:
            # Output is [B*num_patches, C, H, W] from swintransformer2
            # With test_sample=1, num_patches=1, so output is [B, C, H, W]
            # Rearrange to [B, H*W, C] then average pool to [B, C]
            h = self.backbone.input_size  # 28
            x = self._rearrange(output, "b c h w -> b (h w) c", h=h, w=h)
            self._captured_features = x.mean(dim=1)  # [B, 384]

        self._hook_handle = self.backbone.swintransformer2.register_forward_hook(
            _capture_hook
        )

        # Create multi-task head
        self.head = nn.Sequential(
            nn.Linear(feature_dim, head_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
            nn.Linear(head_hidden_dim, head_hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(head_dropout),
        )

        # Separate output heads for each dimension
        self.overall_head = nn.Linear(head_hidden_dim // 2, 1)
        self.sharpness_head = nn.Linear(head_hidden_dim // 2, 1)
        self.color_head = nn.Linear(head_hidden_dim // 2, 1)

        # Track backbone frozen state
        self._backbone_frozen = freeze_backbone
        if freeze_backbone:
            self._freeze_backbone()

    def _freeze_backbone(self) -> None:
        """Freeze all backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        self._backbone_frozen = True
        print("MANIQA backbone frozen")

    def unfreeze_backbone(self) -> None:
        """Unfreeze backbone parameters for Phase 2 training."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        self._backbone_frozen = False
        print("MANIQA backbone unfrozen")

    @property
    def is_backbone_frozen(self) -> bool:
        """Check if backbone is currently frozen."""
        return self._backbone_frozen

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through MANIQA with multi-task head.

        Uses a forward hook on swintransformer2 to capture 384-dim features
        before fc_score processing.

        Args:
            x: Input image tensor [B, 3, 224, 224].

        Returns:
            Dictionary with overall, sharpness, color scores.
        """
        # Run backbone forward (hook captures features)
        _ = self.backbone(x)

        # Get captured features [B, 384]
        features = self._captured_features
        assert features is not None, "Features not captured by hook"

        # Pass through multi-task head
        shared_features = self.head(features)

        # Get dimension-specific predictions
        overall = torch.sigmoid(self.overall_head(shared_features)).squeeze(-1)
        sharpness = torch.sigmoid(self.sharpness_head(shared_features)).squeeze(-1)
        color = torch.sigmoid(self.color_head(shared_features)).squeeze(-1)

        return {
            "overall": overall,
            "sharpness": sharpness,
            "color": color,
        }

    def get_backbone_params(self) -> list:
        """Get backbone parameters for optimizer groups."""
        return list(self.backbone.parameters())

    def get_head_params(self) -> list:
        """Get head parameters for optimizer groups."""
        params = list(self.head.parameters())
        params.extend(self.overall_head.parameters())
        params.extend(self.sharpness_head.parameters())
        params.extend(self.color_head.parameters())
        return params

    def get_trainable_params(self) -> int:
        """Get count of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_total_params(self) -> int:
        """Get total parameter count."""
        return sum(p.numel() for p in self.parameters())


def compute_validation_metrics(
    model: Any,
    val_loader: Any,
    device: str,
) -> dict[str, float]:
    """Compute validation metrics on validation set.

    Args:
        model: MANIQA model.
        val_loader: Validation dataloader.
        device: Device to run on.

    Returns:
        Dictionary of metrics (SRCC, PLCC, ECE per dimension).
    """
    import numpy as np
    from scipy.stats import pearsonr, spearmanr

    model.eval()

    all_preds: dict[str, list[float]] = {"overall": [], "sharpness": [], "color": []}
    all_targets: dict[str, list[float]] = {"overall": [], "sharpness": [], "color": []}

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)

            # Use mixed precision for inference too
            with torch.amp.autocast("cuda"):
                outputs = model(images)

            for dim in ["overall", "sharpness", "color"]:
                all_preds[dim].extend(outputs[dim].cpu().numpy().tolist())
                all_targets[dim].extend(labels[dim].numpy().tolist())

    metrics: dict[str, float] = {}

    for dim in ["overall", "sharpness", "color"]:
        pred = np.array(all_preds[dim])
        target = np.array(all_targets[dim])

        # SRCC
        srcc, _ = spearmanr(pred, target)
        metrics[f"srcc_{dim}"] = float(srcc)

        # PLCC
        plcc, _ = pearsonr(pred, target)
        metrics[f"plcc_{dim}"] = float(plcc)

        # Simple ECE approximation (binned calibration)
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for i in range(n_bins):
            in_bin = (pred >= bin_boundaries[i]) & (pred < bin_boundaries[i + 1])
            if np.sum(in_bin) > 0:
                avg_pred = np.mean(pred[in_bin])
                avg_target = np.mean(target[in_bin])
                ece += np.abs(avg_pred - avg_target) * np.mean(in_bin)
        metrics[f"ece_{dim}"] = float(ece)

    # Aggregate metrics
    metrics["srcc_mean"] = float(
        np.mean([metrics[f"srcc_{d}"] for d in ["overall", "sharpness", "color"]])
    )
    metrics["ece_mean"] = float(
        np.mean([metrics[f"ece_{d}"] for d in ["overall", "sharpness", "color"]])
    )

    model.train()
    return metrics


def run_training_epoch(
    model: Any,
    train_loader: Any,
    criterion: Any,
    optimizer: Any,
    scheduler: Any,
    device: str,
    accum_steps: int,
    gradient_clip_norm: float,
    scaler: Any = None,
) -> float:
    """Run a single training epoch with optional mixed precision.

    Args:
        model: MANIQA model.
        train_loader: Training dataloader.
        criterion: Loss function.
        optimizer: Optimizer.
        scheduler: Learning rate scheduler.
        device: Device to run on.
        accum_steps: Gradient accumulation steps.
        gradient_clip_norm: Max gradient norm for clipping.
        scaler: GradScaler for mixed precision (None for FP32).

    Returns:
        Average training loss for the epoch.
    """
    model.train()
    epoch_loss = 0.0
    num_batches = 0
    optimizer.zero_grad()

    use_amp = scaler is not None

    for batch_idx, (images, labels) in enumerate(train_loader):
        images = images.to(device)
        labels = {k: v.to(device) for k, v in labels.items()}

        # Mixed precision forward pass
        if use_amp:
            with torch.amp.autocast("cuda"):
                outputs = model(images)
                loss = criterion(outputs, labels)
        else:
            outputs = model(images)
            loss = criterion(outputs, labels)

        # Scale loss for gradient accumulation
        loss = loss / accum_steps

        # Backward pass
        if use_amp:
            scaler.scale(loss).backward()
        else:
            loss.backward()

        # Step optimizer every accum_steps batches
        if (batch_idx + 1) % accum_steps == 0:
            if use_amp:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
                optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        epoch_loss += loss.item() * accum_steps
        num_batches += 1

    return epoch_loss / num_batches


def save_checkpoint(
    model: Any,
    optimizer: Any,
    epoch: int,
    metrics: dict[str, float],
    phase: int,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    """Save training checkpoint.

    Args:
        model: MANIQA model.
        optimizer: Optimizer.
        epoch: Current epoch.
        metrics: Validation metrics.
        phase: Training phase (1 or 2).
        checkpoint_dir: Directory to save checkpoints.

    Returns:
        Checkpoint metadata dictionary.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = checkpoint_dir / f"checkpoint_phase{phase}_epoch{epoch:02d}.pt"

    torch.save(
        {
            "epoch": epoch,
            "phase": phase,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
        },
        checkpoint_path,
    )

    print(f"Saved checkpoint: {checkpoint_path.name}")

    return {
        "epoch": epoch,
        "phase": phase,
        "path": str(checkpoint_path),
        **metrics,
    }


def upload_to_gcs(
    local_path: Path,
    bucket_name: str,
    gcs_path: str,
) -> str:
    """Upload file or directory to GCS.

    Args:
        local_path: Local path to upload.
        bucket_name: GCS bucket name.
        gcs_path: GCS destination path.

    Returns:
        Full GCS URI.
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    if local_path.is_file():
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{bucket_name}/{gcs_path}"

    # Directory upload
    uploaded = []
    for file_path in local_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(local_path)
            blob_path = f"{gcs_path}/{relative_path}"
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(file_path))
            uploaded.append(blob_path)

    return f"gs://{bucket_name}/{gcs_path}/"


@app.cls(
    gpu="A10G",  # 24GB VRAM - sufficient for MANIQA
    memory=32768,  # 32GB system RAM
    timeout=21600,  # 6 hours (50 epochs)
    scaledown_window=300,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    image=image,
)
class MANIQATrainer:
    """Modal class for MANIQA fine-tuning on DIQA-5000."""

    @modal.enter()
    def setup(self) -> None:
        """Initialize environment on container start."""
        import sys

        # Add source code to path
        sys.path.insert(0, "/root")

        # Set GCS credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCS_CREDENTIALS_PATH

        print("MANIQA Trainer initialized")

    @modal.method()
    def train(
        self,
        bucket_name: str = "image_detection_b",
    ) -> dict[str, Any]:
        """Run two-phase MANIQA fine-tuning.

        Args:
            bucket_name: GCS bucket for dataset and model storage.

        Returns:
            Training results including best checkpoint metrics.
        """
        # Import local modules
        from image_preprocessing_detector.labeling.finetuning.musiq_loss import (
            MUSIQSpecialistLoss,
        )

        config = TRAINING_CONFIG

        print("=" * 60)
        print("MANIQA Fine-Tuning Configuration")
        print("=" * 60)
        print(f"Phase 1: {config['phase1_epochs']} epochs (frozen backbone)")
        print(f"Phase 2: {config['phase2_epochs']} epochs (full fine-tune)")
        print(f"Total: {config['total_epochs']} epochs")
        print(
            f"Batch size: {config['batch_size']} "
            f"(effective: {config['batch_size'] * config['gradient_accumulation_steps']})"
        )
        print(f"Input size: {config['input_size']}x{config['input_size']}")
        print(f"Loss weights: {config['loss_weights']}")
        print("=" * 60)

        # Set device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        # Download dataset
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_dir = download_diqa5000(bucket_name, Path(tmpdir))
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            checkpoint_dir.mkdir()

            # Create model
            print("\nLoading MANIQA model with multi-task head...")
            model = MANIQAMultiTask(
                freeze_backbone=True,  # Phase 1: frozen
                head_hidden_dim=config["head_hidden_dim"],
                head_dropout=config["head_dropout"],
            )
            model = model.to(device)

            print(f"Total parameters: {model.get_total_params():,}")
            print(f"Trainable parameters: {model.get_trainable_params():,}")

            # Create loss function (generalist weights)
            criterion = MUSIQSpecialistLoss(
                dimension_weights=config["loss_weights"],
                mse_weight=config["mse_weight"],
                rank_weight=config["rank_weight"],
                focal_weight=config["focal_weight"],
            )

            all_checkpoints: list[dict[str, Any]] = []
            accum_steps = config["gradient_accumulation_steps"]

            # Create GradScaler for mixed precision training
            scaler = torch.amp.GradScaler("cuda")
            print("Mixed precision training enabled (AMP)")

            # ============ PHASE 1: Head Warmup ============
            print("\n" + "=" * 60)
            print("PHASE 1: Head Warmup (Backbone Frozen)")
            print("=" * 60)

            # Create dataloaders for Phase 1
            train_loader, val_loader = create_dataloaders(
                root_dir=dataset_dir,
                batch_size=config["batch_size"],
                num_workers=config["num_workers"],
                phase=1,
                input_size=config["input_size"],
            )

            print(f"Train samples: {len(train_loader.dataset)}")
            print(f"Val samples: {len(val_loader.dataset)}")

            # Phase 1 optimizer (head only)
            optimizer = torch.optim.AdamW(
                model.get_head_params(),
                lr=config["phase1_lr"],
                weight_decay=config["weight_decay"],
            )

            # LR scheduler with warmup
            total_steps = config["phase1_epochs"] * len(train_loader)
            warmup_steps = config["phase1_warmup_epochs"] * len(train_loader)

            def lr_lambda(step: int) -> float:
                if step < warmup_steps:
                    return float(step) / float(max(1, warmup_steps))
                progress = float(step - warmup_steps) / float(
                    max(1, total_steps - warmup_steps)
                )
                return max(0.0, 0.5 * (1.0 + math.cos(progress * math.pi)))

            scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

            # Phase 1 training loop
            for epoch in range(config["phase1_epochs"]):
                avg_loss = run_training_epoch(
                    model=model,
                    train_loader=train_loader,
                    criterion=criterion,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    device=device,
                    accum_steps=accum_steps,
                    gradient_clip_norm=config["gradient_clip_norm"],
                    scaler=scaler,
                )

                # Validation
                metrics = compute_validation_metrics(model, val_loader, device)
                metrics["train_loss"] = avg_loss

                print(
                    f"Epoch {epoch + 1}/{config['phase1_epochs']} | "
                    f"Loss: {avg_loss:.4f} | "
                    f"SRCC_mean: {metrics['srcc_mean']:.4f} | "
                    f"ECE: {metrics['ece_mean']:.4f} | "
                    f"LR: {scheduler.get_last_lr()[0]:.2e}"
                )

                # Save checkpoint
                if (epoch + 1) % config["checkpoint_interval"] == 0:
                    ckpt = save_checkpoint(
                        model,
                        optimizer,
                        epoch + 1,
                        metrics,
                        phase=1,
                        checkpoint_dir=checkpoint_dir,
                    )
                    all_checkpoints.append(ckpt)

            # ============ PHASE 2: Full Fine-Tuning ============
            print("\n" + "=" * 60)
            print("PHASE 2: Full Fine-Tuning (Backbone Unfrozen)")
            print("=" * 60)

            # Unfreeze backbone
            model.unfreeze_backbone()
            print(
                f"Trainable parameters after unfreeze: {model.get_trainable_params():,}"
            )

            # Create dataloaders for Phase 2 (with augmentation)
            train_loader, val_loader = create_dataloaders(
                root_dir=dataset_dir,
                batch_size=config["batch_size"],
                num_workers=config["num_workers"],
                phase=2,
                input_size=config["input_size"],
            )

            # Phase 2 optimizer (differential LRs)
            optimizer = torch.optim.AdamW(
                [
                    {
                        "params": model.get_backbone_params(),
                        "lr": config["phase2_backbone_lr"],
                    },
                    {
                        "params": model.get_head_params(),
                        "lr": config["phase2_head_lr"],
                    },
                ],
                lr=config["phase2_head_lr"],  # Default LR (overridden by per-group LR)
                weight_decay=config["weight_decay"],
            )

            # LR scheduler with warmup
            total_steps = config["phase2_epochs"] * len(train_loader)
            warmup_steps = config["phase2_warmup_epochs"] * len(train_loader)
            scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

            # Phase 2 training loop
            for epoch in range(config["phase2_epochs"]):
                avg_loss = run_training_epoch(
                    model=model,
                    train_loader=train_loader,
                    criterion=criterion,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    device=device,
                    accum_steps=accum_steps,
                    gradient_clip_norm=config["gradient_clip_norm"],
                    scaler=scaler,
                )

                # Validation
                metrics = compute_validation_metrics(model, val_loader, device)
                metrics["train_loss"] = avg_loss

                total_epoch = config["phase1_epochs"] + epoch + 1
                print(
                    f"Epoch {total_epoch}/{config['total_epochs']} | "
                    f"Loss: {avg_loss:.4f} | "
                    f"SRCC_mean: {metrics['srcc_mean']:.4f} | "
                    f"ECE: {metrics['ece_mean']:.4f} | "
                    f"LR_bb: {optimizer.param_groups[0]['lr']:.2e}"
                )

                # Save checkpoint
                if (epoch + 1) % config["checkpoint_interval"] == 0:
                    ckpt = save_checkpoint(
                        model,
                        optimizer,
                        total_epoch,
                        metrics,
                        phase=2,
                        checkpoint_dir=checkpoint_dir,
                    )
                    all_checkpoints.append(ckpt)

            # ============ Checkpoint Selection ============
            print("\n" + "=" * 60)
            print("Checkpoint Selection")
            print("=" * 60)

            # Select best checkpoint based on mean SRCC
            best_ckpt = max(all_checkpoints, key=lambda x: x.get("srcc_mean", 0))

            print(f"Selected checkpoint: Epoch {best_ckpt['epoch']}")
            print(f"  SRCC_mean: {best_ckpt['srcc_mean']:.4f}")
            print(f"  SRCC_overall: {best_ckpt['srcc_overall']:.4f}")
            print(f"  SRCC_sharpness: {best_ckpt['srcc_sharpness']:.4f}")
            print(f"  SRCC_color: {best_ckpt['srcc_color']:.4f}")
            print(f"  ECE_mean: {best_ckpt['ece_mean']:.4f}")

            # Load best checkpoint
            best_ckpt_data = torch.load(best_ckpt["path"])
            model.load_state_dict(best_ckpt_data["model_state_dict"])

            # ============ Export ============
            print("\n" + "=" * 60)
            print("Model Export")
            print("=" * 60)

            # Save final model
            final_model_path = checkpoint_dir / "maniqa_finetuned.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "config": config,
                    "metrics": best_ckpt,
                },
                final_model_path,
            )
            print(f"Saved final model: {final_model_path.name}")

            # Upload to GCS
            print("\nUploading to GCS...")
            gcs_model_path = "models/diqa/track_a_iqa/maniqa/v1.0.0"

            upload_to_gcs(
                final_model_path,
                bucket_name,
                f"{gcs_model_path}/model.pt",
            )

            # Save config
            config_json_path = checkpoint_dir / "config.json"
            with open(config_json_path, "w") as f:
                json.dump(config, f, indent=2)
            upload_to_gcs(
                config_json_path,
                bucket_name,
                f"{gcs_model_path}/config.json",
            )

            # Save metrics
            metrics_path = checkpoint_dir / "metrics.json"
            with open(metrics_path, "w") as f:
                json.dump(best_ckpt, f, indent=2, default=str)
            upload_to_gcs(
                metrics_path,
                bucket_name,
                f"{gcs_model_path}/metrics.json",
            )

            print(f"\nModel uploaded to: gs://{bucket_name}/{gcs_model_path}/")

            return {
                "status": "success",
                "best_epoch": best_ckpt["epoch"],
                "srcc_mean": best_ckpt["srcc_mean"],
                "srcc_overall": best_ckpt["srcc_overall"],
                "srcc_sharpness": best_ckpt["srcc_sharpness"],
                "srcc_color": best_ckpt["srcc_color"],
                "ece_mean": best_ckpt["ece_mean"],
                "gcs_path": f"gs://{bucket_name}/{gcs_model_path}/",
            }


@app.local_entrypoint()
def main() -> None:
    """Local entrypoint for Modal run."""
    trainer = MANIQATrainer()
    result = trainer.train.remote()
    print("\n" + "=" * 60)
    print("Training Complete")
    print("=" * 60)
    print(json.dumps(result, indent=2))
