# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal training script for DocIQ-Replica (ResNet-50 + Layout Fusion) on DIQA-5000.

This script implements the two-phase DocIQ training protocol matching the
original paper methodology. DocIQ-Replica serves as the GENERALIST ANCHOR
for Track A, predicting all three DIQA quality dimensions with equal weighting.

Architecture:
    - 1600x1600 input resolution
    - Layout Fusion Downsampler with 11-class semantic masks
    - ResNet-50 backbone (ImageNet pretrained)
    - Multi-task head for quality prediction

Training Protocol (Section 4.4A3):
    - Phase 1 (15 epochs): Head warmup with frozen backbone, LR=1e-3
    - Phase 2 (45 epochs): Full fine-tuning with differential LRs
    - Total: 60 epochs (paper-aligned)
    - Loss weights: [0.34, 0.33, 0.33] (equal/generalist)

Usage:
    modal run -d modal/train_dociq_resnet50.py

Monitor:
    https://modal.com/apps
    modal app logs diqa-dociq-resnet50 --follow

Reference:
    - docs/planning/DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3
    - Original DocIQ paper architecture
"""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

import modal

# Constants
GCS_CREDENTIALS_PATH = "/root/.gcp/service-account.json"

# Create Modal app
app = modal.App("diqa-dociq-resnet50")

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
        # Deep learning
        "torch>=2.1.0",
        "torchvision>=0.16.0",
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
        # DocLayout-YOLO for layout masks
        "ultralytics>=8.0.0",
        "huggingface-hub>=0.20.0",
    )
    # Copy source code into container
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    # Copy config files for model_config.py
    .add_local_dir(
        local_path="configs",
        remote_path="/root/configs",
        copy=True,
    )
    # Copy pyproject.toml for project root detection
    .add_local_file(
        "pyproject.toml",
        "/root/pyproject.toml",
        copy=True,
    )
    # Copy GCS credentials
    .add_local_file(
        ".gcp/service-account.json",
        GCS_CREDENTIALS_PATH,
        copy=True,
    )
)


# Training configuration (paper-aligned)
TRAINING_CONFIG = {
    # Phase 1: Head warmup (frozen backbone)
    "phase1_epochs": 15,
    "phase1_lr": 1e-3,
    "phase1_warmup_epochs": 5,
    # Phase 2: Full fine-tuning
    "phase2_epochs": 45,
    "phase2_backbone_lr": 1e-5,
    "phase2_head_lr": 1e-4,
    "phase2_warmup_epochs": 3,
    # General training
    "batch_size": 4,  # Small batch due to 1600x1600 images
    "num_workers": 4,
    "weight_decay": 1e-4,
    "gradient_clip_norm": 1.0,
    "gradient_accumulation_steps": 4,  # Effective batch size = 16
    # Loss weights (generalist - equal weights)
    "loss_weights": {"overall": 0.34, "sharpness": 0.33, "color": 0.33},
    "mse_weight": 0.6,
    "rank_weight": 0.2,
    "focal_weight": 0.2,
    # Model
    "head_hidden_dim": 512,
    "head_dropout": 0.1,
    # Checkpoint
    "checkpoint_interval": 5,
    # Computed
    "total_epochs": 60,
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
        tar.extractall(path=target_dir, members=members, filter="data")

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
    mask_generator: Any,
) -> tuple[Any, Any]:
    """Create train/val dataloaders for DocIQ training.

    DIQA-5000 Dataset Structure:
        diqa-5000/
        ├── train/
        │   ├── train.csv
        │   ├── ori/  (original images)
        │   └── res/  (result/degraded images)
        ├── val/
        │   ├── val.csv
        │   ├── ori/
        │   └── res/

    CSV Format:
        res,ori,overall,sharpness,color_fidelity
        test_res_00001.jpg,test_ori_00001.jpg,3.76,3.653,3.707

    Args:
        root_dir: Dataset root directory.
        batch_size: Batch size.
        num_workers: Number of worker processes.
        phase: Training phase (1 or 2) - affects augmentation.
        mask_generator: LayoutMaskGenerator instance for generating masks.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    import csv

    import cv2
    import numpy as np
    import torch
    from torch.utils.data import DataLoader, Dataset

    class DocIQDataset(Dataset):
        """Dataset for DocIQ training with layout mask generation.

        Reads from CSV-based DIQA-5000 structure.
        """

        def __init__(
            self,
            split_dir: Path,
            csv_path: Path,
            mask_gen: Any,
            target_size: int = 1600,
            augment: bool = False,
        ) -> None:
            self.split_dir = split_dir
            self.mask_generator = mask_gen
            self.target_size = target_size
            self.augment = augment

            # Load labels from CSV
            self.samples: list[dict[str, Any]] = []

            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Use 'res' (degraded) images as the input
                    img_path = split_dir / "res" / row["res"]
                    if img_path.exists():
                        self.samples.append(
                            {
                                "image_path": img_path,
                                # Normalize MOS from 1-5 to 0-1
                                "overall": (float(row["overall"]) - 1) / 4.0,
                                "sharpness": (float(row["sharpness"]) - 1) / 4.0,
                                "color": (float(row["color_fidelity"]) - 1) / 4.0,
                            }
                        )

            print(f"Loaded {len(self.samples)} images from {csv_path.name}")

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, dict]:
            sample = self.samples[idx]

            # Load image
            image = cv2.imread(str(sample["image_path"]))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Resize to target size
            image = cv2.resize(
                image,
                (self.target_size, self.target_size),
                interpolation=cv2.INTER_LANCZOS4,
            )

            # Apply augmentation in Phase 2
            if self.augment:
                import albumentations

                transform = albumentations.Compose(
                    [
                        albumentations.HorizontalFlip(p=0.5),
                        albumentations.ShiftScaleRotate(
                            shift_limit=0.05,
                            scale_limit=0.1,
                            rotate_limit=5,
                            p=0.5,
                        ),
                        albumentations.RandomBrightnessContrast(
                            brightness_limit=0.1,
                            contrast_limit=0.1,
                            p=0.3,
                        ),
                    ]
                )
                image = transform(image=image)["image"]

            # Generate layout mask
            layout_mask = self.mask_generator.generate_mask(
                image,
                target_size=(self.target_size, self.target_size),
            )

            # Convert to tensors
            # Normalize RGB with ImageNet stats
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])

            image = image.astype(np.float32) / 255.0
            image = (image - mean) / std
            image_tensor = torch.from_numpy(image).permute(2, 0, 1).float()

            layout_tensor = torch.from_numpy(layout_mask).float()

            labels = {
                "overall": torch.tensor(sample["overall"]),
                "sharpness": torch.tensor(sample["sharpness"]),
                "color": torch.tensor(sample["color"]),
            }

            return image_tensor, layout_tensor, labels

    # DIQA-5000 structure: split_dir/{train,val}.csv + {ori,res}/ subdirs
    train_dir = root_dir / "train"
    val_dir = root_dir / "val"
    train_csv = train_dir / "train.csv"
    val_csv = val_dir / "val.csv"

    # Create datasets
    train_dataset = DocIQDataset(
        train_dir,
        train_csv,
        mask_generator,
        target_size=1600,
        augment=(phase == 2),  # Augment only in Phase 2
    )

    val_dataset = DocIQDataset(
        val_dir,
        val_csv,
        mask_generator,
        target_size=1600,
        augment=False,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader


def compute_validation_metrics(
    model: Any,
    val_loader: Any,
    device: str,
) -> dict[str, float]:
    """Compute validation metrics on validation set.

    Args:
        model: DocIQReplica model.
        val_loader: Validation dataloader.
        device: Device to run on.

    Returns:
        Dictionary of metrics (SRCC, PLCC, ECE per dimension).
    """
    import numpy as np
    import torch
    from scipy.stats import pearsonr, spearmanr

    model.eval()

    all_preds: dict[str, list[float]] = {"overall": [], "sharpness": [], "color": []}
    all_targets: dict[str, list[float]] = {"overall": [], "sharpness": [], "color": []}

    with torch.no_grad():
        for images, layouts, labels in val_loader:
            images = images.to(device)
            layouts = layouts.to(device)

            outputs = model(images, layouts)

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
        model: DocIQReplica model.
        optimizer: Optimizer.
        epoch: Current epoch.
        metrics: Validation metrics.
        phase: Training phase (1 or 2).
        checkpoint_dir: Directory to save checkpoints.

    Returns:
        Checkpoint metadata dictionary.
    """
    import torch

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


def run_training_epoch(
    model: Any,
    train_loader: Any,
    criterion: Any,
    optimizer: Any,
    scheduler: Any,
    device: str,
    accum_steps: int,
    gradient_clip_norm: float,
) -> float:
    """Run a single training epoch.

    Args:
        model: DocIQReplica model.
        train_loader: Training dataloader.
        criterion: Loss function.
        optimizer: Optimizer.
        scheduler: Learning rate scheduler.
        device: Device to run on.
        accum_steps: Gradient accumulation steps.
        gradient_clip_norm: Max gradient norm for clipping.

    Returns:
        Average training loss for the epoch.
    """
    import torch

    model.train()
    epoch_loss = 0.0
    num_batches = 0
    optimizer.zero_grad()

    for batch_idx, (images, layouts, labels) in enumerate(train_loader):
        images = images.to(device)
        layouts = layouts.to(device)
        labels = {k: v.to(device) for k, v in labels.items()}

        outputs = model(images, layouts)
        loss = criterion(outputs, labels)

        # Scale loss for gradient accumulation
        loss = loss / accum_steps
        loss.backward()

        # Step optimizer every accum_steps batches
        if (batch_idx + 1) % accum_steps == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        epoch_loss += loss.item() * accum_steps
        num_batches += 1

    return epoch_loss / num_batches


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
    gpu="A10G",  # 24GB VRAM - needed for 1600x1600 images
    memory=65536,  # 64GB system RAM
    timeout=43200,  # 12 hours (60 epochs)
    scaledown_window=300,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    image=image,
)
class DocIQTrainer:
    """Modal class for DocIQ ResNet-50 training on DIQA-5000."""

    @modal.enter()
    def setup(self) -> None:
        """Initialize environment on container start."""
        import sys

        # Add source code to path
        sys.path.insert(0, "/root")

        # Set GCS credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCS_CREDENTIALS_PATH

        print("DocIQ ResNet-50 Trainer initialized")

    @modal.method()
    def train(
        self,
        bucket_name: str = "image_detection_b",
    ) -> dict[str, Any]:
        """Run two-phase DocIQ training.

        Args:
            bucket_name: GCS bucket for dataset and model storage.

        Returns:
            Training results including best checkpoint metrics.
        """
        import math

        import torch

        # Import local modules
        from image_preprocessing_detector.labeling.finetuning.layout_fusion import (
            DocIQReplica,
            LayoutMaskGenerator,
            LayoutMaskGeneratorConfig,
        )
        from image_preprocessing_detector.labeling.finetuning.musiq_loss import (
            MUSIQSpecialistLoss,
        )

        config = TRAINING_CONFIG

        print("=" * 60)
        print("DocIQ ResNet-50 Training Configuration")
        print("=" * 60)
        print(f"Phase 1: {config['phase1_epochs']} epochs (frozen backbone)")
        print(f"Phase 2: {config['phase2_epochs']} epochs (full fine-tune)")
        print(f"Total: {config['total_epochs']} epochs")
        print(
            f"Batch size: {config['batch_size']} (effective: {config['batch_size'] * config['gradient_accumulation_steps']})"
        )
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

            # Initialize layout mask generator (with caching)
            print("\nInitializing Layout Mask Generator...")
            mask_cache_dir = Path(tmpdir) / "mask_cache"
            mask_generator = LayoutMaskGenerator(
                config=LayoutMaskGeneratorConfig(
                    cache_dir=str(mask_cache_dir),
                    device=device,
                )
            )

            # Create model
            print("\nLoading DocIQ ResNet-50 model...")
            model = DocIQReplica(
                freeze_backbone=True,  # Phase 1: frozen
                head_hidden_dim=config["head_hidden_dim"],
                head_dropout=config["head_dropout"],
                pretrained_backbone=True,
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
                mask_generator=mask_generator,
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
                mask_generator=mask_generator,
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
            best_ckpt_data = torch.load(best_ckpt["path"], weights_only=True)
            model.load_state_dict(best_ckpt_data["model_state_dict"])

            # ============ Export ============
            print("\n" + "=" * 60)
            print("Model Export")
            print("=" * 60)

            # Save final model
            final_model_path = checkpoint_dir / "dociq_resnet50_generalist.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "config": config,
                    "metrics": best_ckpt,
                },
                final_model_path,
            )
            print(f"Saved final model: {final_model_path.name}")

            # Export to ONNX
            onnx_path = checkpoint_dir / "dociq_resnet50_generalist.onnx"
            try:
                model.eval()
                dummy_rgb = torch.randn(1, 3, 1600, 1600, device=device)
                dummy_layout = torch.randn(1, 11, 1600, 1600, device=device)
                torch.onnx.export(
                    model,
                    (dummy_rgb, dummy_layout),
                    str(onnx_path),
                    export_params=True,
                    opset_version=17,
                    input_names=["rgb", "layout"],
                    output_names=["overall", "sharpness", "color"],
                    dynamic_axes={
                        "rgb": {0: "batch_size"},
                        "layout": {0: "batch_size"},
                    },
                )
                print(f"Exported ONNX model: {onnx_path.name}")
            except Exception as e:
                print(f"ONNX export failed: {e}")

            # Upload to GCS
            print("\nUploading to GCS...")
            gcs_model_path = "models/diqa/track_a_iqa/dociq_resnet50/v1.0.0"

            upload_to_gcs(
                final_model_path,
                bucket_name,
                f"{gcs_model_path}/model.pt",
            )

            if onnx_path.exists():
                upload_to_gcs(
                    onnx_path,
                    bucket_name,
                    f"{gcs_model_path}/model.onnx",
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
    trainer = DocIQTrainer()
    result = trainer.train.remote()
    print("\n" + "=" * 60)
    print("Training Complete")
    print("=" * 60)
    print(json.dumps(result, indent=2))
