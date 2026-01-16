# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal training script for HyperIQA++ on DIQA-5000.

Enhanced HyperIQA with 7 DocIQ and VQualA 2025 innovations for 0.85 PLCC target.

Architecture:
    - HyperIQA ResNet-50 + HyperNet backbone
    - Multi-scale feature fusion (DocIQ Component 2)
    - Spatial attention (layout-aware)
    - Soft label distribution heads (DeQA-Doc)
    - 1600x1600 high-resolution input

Training Protocol:
    - Phase 1 (Epochs 1-10): Head warmup with frozen backbone
    - Phase 2 (Epochs 11-60): Full fine-tuning with step LR decay
    - Total: 60 epochs (DocIQ protocol)

Usage:
    # Full training (recommended: detached mode)
    modal run --detach modal/train_hyperiqa_plus_plus.py

    # Quick test run (2 epochs)
    modal run modal/train_hyperiqa_plus_plus.py --test

    # Resume from checkpoint
    modal run modal/train_hyperiqa_plus_plus.py --resume

Expected Performance:
    - Target: PLCC 0.85, SRCC 0.78 on DIQA-5000 test
    - VQualA Score: 0.80+

References:
    - DocIQ: arXiv:2509.17012
    - DeQA-Doc: arXiv:2507.12796
    - NormInNormLoss: arXiv:2008.03889
    - HyperIQA: CVPR 2020
"""

from __future__ import annotations

import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import modal

if TYPE_CHECKING:
    from torch.utils.data import DataLoader

# ============================================================================
# Modal Configuration
# ============================================================================

app = modal.App("hyperiqa-plus-plus-training")

# Volumes
data_volume = modal.Volume.from_name("stage2-training-data", create_if_missing=True)
checkpoint_volume = modal.Volume.from_name(
    "hyperiqa-checkpoints", create_if_missing=True
)

# Docker image with dependencies
training_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        # Core ML
        "torch==2.5.1",
        "torchvision==0.20.1",
        "timm>=1.0.0",
        # IQA
        "pyiqa>=0.1.12",  # For pretrained HyperIQA weights
        # Training utilities
        "scipy>=1.14.1",
        "scikit-learn>=1.3.0",
        "tqdm>=4.67.0",
        # Image processing
        "pillow>=11.0.0",
        "opencv-python-headless>=4.8.0",
        # Data validation & settings
        "pydantic>=2.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        # Logging
        "structlog>=24.4.0",
        "tensorboard>=2.18.0",
        "rich>=13.5.0",
        # PDF processing
        "pymupdf>=1.23.0",
        # Utilities
        "click>=8.1.0",
        "huggingface-hub>=0.20.0",
        "gitpython>=3.1.45",
        "pywavelets>=1.4.0",
        "defusedxml>=0.7.1",
        "fonttools>=4.60.2",
        "werkzeug>=3.1.5",
        "urllib3>=2.6.3",
        "filelock>=3.20.1",
        # GCS
        "google-cloud-storage>=2.19.0",
    )
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
)


# ============================================================================
# Training Configuration
# ============================================================================


@dataclass
class TrainingConfig:
    """HyperIQA++ training configuration (DocIQ-aligned)."""

    # Model
    num_bins: int = 10
    freeze_backbone_epochs: int = 10

    # Phase 1: Head warmup (epochs 1-10)
    phase1_epochs: int = 10
    phase1_lr: float = 2e-4
    phase1_batch_size: int = 16

    # Phase 2: Full fine-tuning (epochs 11-60)
    phase2_epochs: int = 50
    phase2_lr_backbone: float = 2e-5  # 10x lower for pretrained
    phase2_lr_hypernet: float = 1e-4
    phase2_lr_heads: float = 2e-4
    phase2_batch_size: int = 2  # Heavily reduced for 1600x1600 + full unfrozen model
    gradient_accumulation_steps: int = 6  # Effective batch size = 2 * 6 = 12

    # DocIQ LR schedule
    lr_schedule: str = "step"
    lr_step_size: int = 10  # Decay every 10 epochs
    lr_gamma: float = 0.6  # LR *= 0.6 per step

    # Optimization
    weight_decay: float = 1e-4
    gradient_clip_norm: float = 1.0
    use_pcgrad: bool = True

    # Loss weights
    kl_weight: float = 0.5
    norm_weight: float = 0.5
    use_norm_in_norm: bool = True

    # Data
    image_size: tuple[int, int] = (1600, 1600)  # DocIQ protocol
    num_workers: int = 4

    # Checkpointing
    save_every_n_epochs: int = 5
    save_top_k: int = 3
    early_stopping_patience: int = 10

    # Targets
    target_srcc: float = 0.78
    target_plcc: float = 0.85
    target_vquala: float = 0.80

    @property
    def total_epochs(self) -> int:
        """Total training epochs."""
        return self.phase1_epochs + self.phase2_epochs


# ============================================================================
# GCS Download Utility
# ============================================================================


def download_diqa5000_from_gcs(target_dir: Path) -> Path:
    """Download DIQA-5000 dataset from GCS.

    Dataset location: gs://image_detection_b/datasets/diqa-5000/diqa-5000.tar.gz

    Args:
        target_dir: Local directory to extract dataset

    Returns:
        Path to extracted DIQA-5000 directory
    """
    import base64
    import os
    import tempfile

    from google.cloud import storage

    target_dir.mkdir(parents=True, exist_ok=True)

    # Materialize GCS credentials from Modal Secret
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        gcp_sa_key_json = base64.b64decode(gcp_sa_key).decode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
        ) as f:
            f.write(gcp_sa_key_json)
            f.flush()
            credentials_path = f.name
        os.chmod(credentials_path, 0o600)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        msg = (
            "GCS credentials not configured. Set Modal Secret 'gcs-credentials' "
            "with GCP_SA_KEY environment variable."
        )
        raise FileNotFoundError(msg)

    bucket_name = "image_detection_b"
    gcs_path = "datasets/diqa-5000/diqa-5000.tar.gz"

    print(f"Downloading DIQA-5000 from gs://{bucket_name}/{gcs_path}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Download tarball
    tar_blob = bucket.blob(gcs_path)
    tar_path = target_dir / "diqa-5000.tar.gz"

    start = time.time()
    tar_blob.download_to_filename(str(tar_path))
    download_time = time.time() - start

    tar_size_gb = tar_path.stat().st_size / (1024**3)
    print(f"✅ Downloaded {tar_size_gb:.2f} GB in {download_time:.1f}s")

    # Extract dataset
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
                msg = f"Path traversal detected: {member.name}"
                raise ValueError(msg)
        # nosec B202: Path traversal validation performed above
        tar.extractall(path=target_dir, members=members, filter="data")

    extract_time = time.time() - extract_start
    print(f"✅ Extracted in {extract_time:.1f}s")

    # Clean up tarball
    tar_path.unlink()

    dataset_path = target_dir / "diqa-5000"
    print(f"Dataset ready at: {dataset_path}")

    return dataset_path


# ============================================================================
# Training Functions
# ============================================================================


def create_dataloaders(
    root_dir: Path,
    config: TrainingConfig,
    phase: int,
) -> tuple[DataLoader, DataLoader]:
    """Create train/val dataloaders for HyperIQA++ training.

    Args:
        root_dir: DIQA-5000 root directory
        config: Training configuration
        phase: Training phase (1 or 2)

    Returns:
        Tuple of (train_loader, val_loader)
    """
    from torch.utils.data import DataLoader

    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
        DIQA5000HighResDataset,
    )

    batch_size = (
        config.phase1_batch_size if phase == 1 else config.phase2_batch_size
    )

    train_dataset = DIQA5000HighResDataset(
        root_dir=root_dir,
        split="train",
        image_size=config.image_size,
        num_bins=config.num_bins,
        augment=True,
    )

    val_dataset = DIQA5000HighResDataset(
        root_dir=root_dir,
        split="val",
        image_size=config.image_size,
        num_bins=config.num_bins,
        augment=False,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader


def setup_optimizer_with_pcgrad(
    model,
    config: TrainingConfig,
    phase: int,
):
    """Setup optimizer with optional PCGrad wrapper.

    Args:
        model: HyperIQA++ model
        config: Training configuration
        phase: Training phase (1 or 2)

    Returns:
        Optimizer (wrapped with PCGrad if enabled)
    """
    import torch

    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.pcgrad import PCGrad

    if phase == 1:
        # Phase 1: Heads only (backbone frozen)
        param_groups = [
            {"params": model.head_overall.parameters(), "lr": config.phase1_lr},
            {"params": model.head_sharpness.parameters(), "lr": config.phase1_lr},
            {"params": model.head_color.parameters(), "lr": config.phase1_lr},
        ]
    else:
        # Phase 2: Differential learning rates
        param_groups = [
            {
                "params": model.backbone.parameters(),
                "lr": config.phase2_lr_backbone,
            },
        ]

        if model.hypernet is not None:
            param_groups.append({
                "params": model.hypernet.parameters(),
                "lr": config.phase2_lr_hypernet,
            })

        if model.feature_fusion is not None:
            param_groups.append({
                "params": model.feature_fusion.parameters(),
                "lr": config.phase2_lr_heads,
            })

        param_groups.extend([
            {
                "params": model.spatial_attention.parameters(),
                "lr": config.phase2_lr_heads,
            },
            {
                "params": model.head_overall.parameters(),
                "lr": config.phase2_lr_heads,
            },
            {
                "params": model.head_sharpness.parameters(),
                "lr": config.phase2_lr_heads,
            },
            {
                "params": model.head_color.parameters(),
                "lr": config.phase2_lr_heads,
            },
        ])

    optimizer = torch.optim.AdamW(param_groups, weight_decay=config.weight_decay)

    if config.use_pcgrad:
        optimizer = PCGrad(optimizer)
        print("✅ PCGrad optimizer enabled (gradient conflict mitigation)")

    return optimizer


def setup_scheduler(optimizer, config: TrainingConfig):
    """Setup step decay LR scheduler (DocIQ protocol).

    DocIQ: Step decay every 10 epochs with 0.6 factor

    Args:
        optimizer: PyTorch optimizer (possibly PCGrad-wrapped)
        config: Training configuration

    Returns:
        Learning rate scheduler
    """
    import torch

    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.pcgrad import PCGrad

    # If optimizer is PCGrad-wrapped, pass the underlying optimizer
    base_optimizer = optimizer._optimizer if isinstance(optimizer, PCGrad) else optimizer

    return torch.optim.lr_scheduler.StepLR(
        base_optimizer,
        step_size=config.lr_step_size,
        gamma=config.lr_gamma,
    )


def train_step(
    model,
    batch: dict,
    optimizer,
    criterion,
    use_pcgrad: bool,
    gradient_clip: float,
) -> dict[str, float]:
    """Single training step with PCGrad support.

    Args:
        model: HyperIQA++ model
        batch: Batch dictionary with pixel_values and targets
        optimizer: Optimizer (possibly PCGrad-wrapped)
        criterion: Multi-task loss function
        use_pcgrad: Whether to use PCGrad backward
        gradient_clip: Max gradient norm for clipping

    Returns:
        Loss dictionary
    """
    import torch

    optimizer.zero_grad()

    # Forward pass
    outputs = model(batch["pixel_values"])

    # Compute losses
    if use_pcgrad:
        # Get separate losses for each dimension (for PCGrad)
        losses = criterion(outputs, batch["targets"], return_per_dim=True)

        # PCGrad backward (projects conflicting gradients)
        optimizer.pc_backward(losses)

        # Aggregate for logging
        loss_dict = {
            "loss_overall": losses[0].item(),
            "loss_sharpness": losses[1].item(),
            "loss_color": losses[2].item(),
            "loss_total": sum(losses).item() / 3,
        }
    else:
        # Standard multi-task loss
        loss_dict = criterion(outputs, batch["targets"])
        loss_dict["loss_total"].backward()

        # Convert to items for logging
        loss_dict = {k: v.item() for k, v in loss_dict.items()}

    # Gradient clipping
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=gradient_clip)

    optimizer.step()

    return loss_dict


def train_step_accumulate(
    model,
    batch: dict,
    criterion,
    accumulation_steps: int,
    current_step: int,
) -> dict[str, float]:
    """Single training step for gradient accumulation (no optimizer step).

    Args:
        model: HyperIQA++ model
        batch: Batch dictionary with pixel_values and targets
        criterion: Multi-task loss function
        accumulation_steps: Number of steps to accumulate
        current_step: Current step within accumulation (0-indexed)

    Returns:
        Loss dictionary (scaled losses)
    """

    # Forward pass
    outputs = model(batch["pixel_values"])

    # Compute losses (standard multi-task, not PCGrad for accumulation)
    loss_dict = criterion(outputs, batch["targets"])

    # Scale loss by accumulation steps
    scaled_loss = loss_dict["loss_total"] / accumulation_steps
    scaled_loss.backward()

    # Return unscaled losses for logging
    return {k: v.item() for k, v in loss_dict.items()}


def validate(
    model,
    val_loader: DataLoader,
    device: str,
) -> dict[str, float]:
    """Validation with SRCC/PLCC computation.

    Args:
        model: HyperIQA++ model
        val_loader: Validation dataloader
        device: Device to run on

    Returns:
        Validation metrics dictionary
    """
    import numpy as np
    import torch
    from scipy.stats import pearsonr, spearmanr

    model.eval()

    predictions = {"overall": [], "sharpness": [], "color": []}
    targets = {"overall": [], "sharpness": [], "color": []}

    with torch.no_grad():
        for batch in val_loader:
            pixel_values = batch["pixel_values"].to(device)
            outputs = model(pixel_values)

            for dim in ["overall", "sharpness", "color"]:
                predictions[dim].extend(outputs[dim]["score"].cpu().numpy())
                targets[dim].extend(batch["targets"][dim]["mos"].cpu().numpy())

    # Compute metrics
    metrics = {}
    for dim in ["overall", "sharpness", "color"]:
        preds = np.array(predictions[dim])
        targs = np.array(targets[dim])

        srcc, _ = spearmanr(preds, targs)
        plcc, _ = pearsonr(preds, targs)
        mae = np.abs(preds - targs).mean()

        metrics[f"{dim}_srcc"] = float(srcc) if not np.isnan(srcc) else 0.0
        metrics[f"{dim}_plcc"] = float(plcc) if not np.isnan(plcc) else 0.0
        metrics[f"{dim}_mae"] = float(mae)

    # VQualA final score
    metrics["vquala_score"] = (
        0.5 * metrics["overall_srcc"]
        + 0.25 * metrics["sharpness_srcc"]
        + 0.25 * metrics["color_srcc"]
    )

    return metrics


@app.function(
    image=training_image,
    gpu="A10G",  # 24GB VRAM required for 1600x1600 + batch size 12
    timeout=60 * 60 * 24,  # 24 hours max
    volumes={
        "/data": data_volume,
        "/checkpoints": checkpoint_volume,
    },
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
def train_hyperiqa_plus_plus(
    test_mode: bool = False,
    resume_from: str | None = None,
) -> dict[str, Any]:
    """Train HyperIQA++ on DIQA-5000.

    Args:
        test_mode: If True, run quick 2-epoch test
        resume_from: Checkpoint ID to resume from

    Returns:
        Training results summary
    """
    import torch
    from tqdm import tqdm

    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.loss import (
        MultiTaskIQALoss,
    )
    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.model import (
        HyperIQAPlusPlus,
    )

    # Load configuration
    config = TrainingConfig()

    if test_mode:
        config.phase1_epochs = 1
        config.phase2_epochs = 1
        config.phase1_batch_size = 4
        config.phase2_batch_size = 4
        print("[TEST MODE] Running quick 2-epoch validation")

    print("=" * 70)
    print("HyperIQA++ Training on DIQA-5000")
    print("=" * 70)
    print(f"Total epochs: {config.total_epochs}")
    print(f"Phase 1 (Head warmup): {config.phase1_epochs} epochs")
    print(f"Phase 2 (Full finetuning): {config.phase2_epochs} epochs")
    print(f"Image size: {config.image_size[0]}x{config.image_size[1]}")
    print(f"Target PLCC: {config.target_plcc}")
    print(f"Target SRCC: {config.target_srcc}")
    print(f"Target VQualA: {config.target_vquala}")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )

    # Download DIQA-5000 dataset
    print("\n📦 Downloading DIQA-5000 dataset...")
    dataset_path = download_diqa5000_from_gcs(Path("/data/diqa-5000"))
    data_volume.commit()

    # Create model
    print("\n🏗️  Creating HyperIQA++ model...")
    model = HyperIQAPlusPlus(
        num_bins=config.num_bins,
        freeze_backbone_epochs=config.freeze_backbone_epochs,
        use_pretrained=True,
    )
    model = model.to(device)

    # Print model statistics
    param_counts = model.get_num_parameters()
    print(f"Total parameters: {param_counts['total']:,}")
    print(f"  Backbone: {param_counts['backbone']:,}")
    print(f"  HyperNet: {param_counts['hypernet']:,}")
    print(f"  Feature Fusion: {param_counts['feature_fusion']:,}")
    print(f"  Spatial Attention: {param_counts['spatial_attention']:,}")
    print(f"  Heads: {param_counts['head_overall'] * 3:,}")

    # Create loss function
    criterion = MultiTaskIQALoss(
        kl_weight=config.kl_weight,
        norm_weight=config.norm_weight,
        use_norm_in_norm=config.use_norm_in_norm,
    )

    # Training history
    history = {
        "train_loss": [],
        "val_metrics": [],
        "best_vquala": 0.0,
        "best_epoch": 0,
    }

    # Check for resume from checkpoint
    resume_epoch = 0
    best_checkpoint = Path("/checkpoints/hyperiqa_plus_plus_best.pt")
    if resume_from or best_checkpoint.exists():
        checkpoint_to_load = best_checkpoint
        if checkpoint_to_load.exists():
            print(f"\n📂 Loading checkpoint: {checkpoint_to_load}")
            checkpoint = torch.load(checkpoint_to_load, map_location=device, weights_only=False)
            model.load_state_dict(checkpoint["model_state_dict"])
            resume_epoch = checkpoint.get("epoch", 10)
            val_metrics = checkpoint.get("val_metrics", {})
            history["best_vquala"] = val_metrics.get("vquala_score", 0.0)
            history["best_epoch"] = resume_epoch
            print(f"✅ Resumed from epoch {resume_epoch}")
            print(f"   Best VQualA so far: {history['best_vquala']:.4f}")
        else:
            print(f"⚠️  Checkpoint not found: {checkpoint_to_load}")

    # Skip Phase 1 if already completed
    skip_phase1 = resume_epoch >= config.phase1_epochs

    # ========================================================================
    # PHASE 1: Head Warmup (Epochs 1-10)
    # ========================================================================

    if skip_phase1:
        print("\n" + "=" * 70)
        print("PHASE 1: HEAD WARMUP (SKIPPED - Already Completed)")
        print("=" * 70)
        print(f"Resuming from epoch {resume_epoch} (Phase 1 complete)")
    else:
        print("\n" + "=" * 70)
        print("PHASE 1: HEAD WARMUP (Frozen Backbone)")
        print("=" * 70)

        model.freeze_backbone()

        train_loader, val_loader = create_dataloaders(dataset_path, config, phase=1)
        print(f"Train samples: {len(train_loader.dataset)}")  # type: ignore[arg-type]
        print(f"Val samples: {len(val_loader.dataset)}")  # type: ignore[arg-type]
        print(f"Batch size: {config.phase1_batch_size}")

        optimizer = setup_optimizer_with_pcgrad(model, config, phase=1)
        scheduler = setup_scheduler(optimizer, config)

        for epoch in range(1, config.phase1_epochs + 1):
            model.train()

            # Training loop
            train_losses = []
            pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{config.phase1_epochs}")

            for batch in pbar:
                batch["pixel_values"] = batch["pixel_values"].to(device)
                for dim in ["overall", "sharpness", "color"]:
                    batch["targets"][dim]["mos"] = batch["targets"][dim]["mos"].to(
                        device
                    )
                    batch["targets"][dim]["soft_labels"] = batch["targets"][dim][
                        "soft_labels"
                    ].to(device)

                loss_dict = train_step(
                    model,
                    batch,
                    optimizer,
                    criterion,
                    config.use_pcgrad,
                    config.gradient_clip_norm,
                )

                train_losses.append(loss_dict["loss_total"])
                pbar.set_postfix({"loss": f"{loss_dict['loss_total']:.4f}"})

            scheduler.step()

            # Validation
            val_metrics = validate(model, val_loader, device)

            # Log epoch results
            avg_train_loss = sum(train_losses) / len(train_losses)
            history["train_loss"].append(avg_train_loss)
            history["val_metrics"].append(val_metrics)

            print(f"\nEpoch {epoch} Summary:")
            print(f"  Train Loss: {avg_train_loss:.4f}")
            print(f"  Val SRCC: Overall={val_metrics['overall_srcc']:.4f}, "
                  f"Sharpness={val_metrics['sharpness_srcc']:.4f}, "
                  f"Color={val_metrics['color_srcc']:.4f}")
            print(f"  Val PLCC: Overall={val_metrics['overall_plcc']:.4f}")
            print(f"  VQualA Score: {val_metrics['vquala_score']:.4f}")

            # Track best model
            if val_metrics["vquala_score"] > history["best_vquala"]:
                history["best_vquala"] = val_metrics["vquala_score"]
                history["best_epoch"] = epoch

        print(f"\n✅ Phase 1 Complete - Best VQualA: {history['best_vquala']:.4f} "
              f"(Epoch {history['best_epoch']})")

    # ========================================================================
    # PHASE 2: Full Fine-Tuning (Epochs 11-60)
    # ========================================================================

    print("\n" + "=" * 70)
    print("PHASE 2: FULL FINE-TUNING (Unfrozen Backbone)")
    print("=" * 70)

    model.unfreeze_backbone()

    # Note: Gradient checkpointing disabled - causes inplace ReLU conflicts with timm ResNet
    # Instead using very small batch size (2) with gradient accumulation (6x)
    print("⚠️  Gradient checkpointing disabled (inplace ReLU conflict)")
    print("   Using batch_size=2 with 6x accumulation instead")

    train_loader, val_loader = create_dataloaders(dataset_path, config, phase=2)
    effective_batch = config.phase2_batch_size * config.gradient_accumulation_steps
    print(f"Batch size: {config.phase2_batch_size} "
          f"(effective: {effective_batch} with {config.gradient_accumulation_steps}x accumulation)")

    # Phase 2 uses standard optimizer with gradient accumulation (not PCGrad)
    # PCGrad doesn't work well with gradient accumulation
    base_optimizer = torch.optim.AdamW(
        [
            {"params": model.backbone.parameters(), "lr": config.phase2_lr_backbone},
            {"params": model.spatial_attention.parameters(), "lr": config.phase2_lr_heads},
            {"params": model.head_overall.parameters(), "lr": config.phase2_lr_heads},
            {"params": model.head_sharpness.parameters(), "lr": config.phase2_lr_heads},
            {"params": model.head_color.parameters(), "lr": config.phase2_lr_heads},
        ],
        weight_decay=config.weight_decay,
    )
    # Add hypernet if it exists
    if model.hypernet is not None:
        base_optimizer.add_param_group({
            "params": model.hypernet.parameters(),
            "lr": config.phase2_lr_hypernet,
        })
    optimizer = base_optimizer
    scheduler = setup_scheduler(optimizer, config)
    print("⚠️  Using standard optimizer for Phase 2 (gradient accumulation enabled)")

    patience_counter = 0
    best_checkpoint_path = None
    accum_steps = config.gradient_accumulation_steps

    for epoch in range(
        config.phase1_epochs + 1, config.phase1_epochs + config.phase2_epochs + 1
    ):
        model.train()

        # Training loop with gradient accumulation
        train_losses = []
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{config.total_epochs}")

        optimizer.zero_grad()
        accumulated_loss = 0.0

        for batch_idx, batch in enumerate(pbar):
            batch["pixel_values"] = batch["pixel_values"].to(device)
            for dim in ["overall", "sharpness", "color"]:
                batch["targets"][dim]["mos"] = batch["targets"][dim]["mos"].to(
                    device
                )
                batch["targets"][dim]["soft_labels"] = batch["targets"][dim][
                    "soft_labels"
                ].to(device)

            loss_dict = train_step_accumulate(
                model,
                batch,
                criterion,
                accum_steps,
                batch_idx % accum_steps,
            )

            accumulated_loss += loss_dict["loss_total"]

            # Step optimizer every accum_steps batches
            if (batch_idx + 1) % accum_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), max_norm=config.gradient_clip_norm
                )
                optimizer.step()
                optimizer.zero_grad()

                avg_loss = accumulated_loss / accum_steps
                train_losses.append(avg_loss)
                pbar.set_postfix({"loss": f"{avg_loss:.4f}"})
                accumulated_loss = 0.0

        # Handle remaining batches
        if accumulated_loss > 0:
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), max_norm=config.gradient_clip_norm
            )
            optimizer.step()
            optimizer.zero_grad()
            remaining = len(train_loader) % accum_steps
            if remaining > 0:
                train_losses.append(accumulated_loss / remaining)

        scheduler.step()

        # Validation
        val_metrics = validate(model, val_loader, device)

        # Log epoch results
        avg_train_loss = sum(train_losses) / len(train_losses)
        history["train_loss"].append(avg_train_loss)
        history["val_metrics"].append(val_metrics)

        print(f"\nEpoch {epoch} Summary:")
        print(f"  Train Loss: {avg_train_loss:.4f}")
        print(
            f"  Val SRCC: Overall={val_metrics['overall_srcc']:.4f}, "
            f"Sharpness={val_metrics['sharpness_srcc']:.4f}, "
            f"Color={val_metrics['color_srcc']:.4f}"
        )
        print(f"  Val PLCC: Overall={val_metrics['overall_plcc']:.4f}")
        print(f"  VQualA Score: {val_metrics['vquala_score']:.4f}")

        # Save checkpoint
        if epoch % config.save_every_n_epochs == 0:
            checkpoint_path = f"/checkpoints/hyperiqa_plus_plus_epoch{epoch}.pt"
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_metrics": val_metrics,
                    "config": config,
                },
                checkpoint_path,
            )
            checkpoint_volume.commit()
            print(f"💾 Checkpoint saved: {checkpoint_path}")

        # Track best model
        if val_metrics["vquala_score"] > history["best_vquala"]:
            history["best_vquala"] = val_metrics["vquala_score"]
            history["best_epoch"] = epoch
            patience_counter = 0

            # Save best checkpoint
            best_checkpoint_path = "/checkpoints/hyperiqa_plus_plus_best.pt"
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_metrics": val_metrics,
                    "config": config,
                },
                best_checkpoint_path,
            )
            checkpoint_volume.commit()
            print(f"⭐ New best model! VQualA: {val_metrics['vquala_score']:.4f}")
        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= config.early_stopping_patience:
            print(
                f"\n⚠️  Early stopping triggered (patience={config.early_stopping_patience})"
            )
            break

    # ========================================================================
    # Final Summary
    # ========================================================================

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"Best VQualA Score: {history['best_vquala']:.4f} (Epoch {history['best_epoch']})")
    print(f"Best checkpoint: {best_checkpoint_path}")

    # Return results
    return {
        "best_vquala": history["best_vquala"],
        "best_epoch": history["best_epoch"],
        "final_val_metrics": history["val_metrics"][-1],
        "checkpoint_path": best_checkpoint_path,
        "config": config.__dict__,
    }


# ============================================================================
# CLI Entry Points
# ============================================================================


@app.local_entrypoint()
def main(test: bool = False, resume: bool = False):
    """Main entry point for local CLI.

    Args:
        test: Run in test mode (2 epochs)
        resume: Resume from latest checkpoint
    """
    resume_from = None
    if resume:
        # Find latest checkpoint
        # This would require checkpoint discovery logic
        print("⚠️  Resume not implemented yet")

    # Run training
    results = train_hyperiqa_plus_plus.remote(
        test_mode=test,
        resume_from=resume_from,
    )

    print("\n🎉 Training finished!")
    print(f"Best VQualA Score: {results['best_vquala']:.4f}")
    print(f"Best Epoch: {results['best_epoch']}")
