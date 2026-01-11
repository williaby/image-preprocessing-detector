# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal training script for MUSIQ fine-tuning on DIQA-5000.

This script implements the two-phase MUSIQ fine-tuning protocol for the
sharpness specialist role in the DIQA pseudo-labeling ensemble.

Training Protocol (Section 4.4A1):
- Phase 1 (10 epochs): Head warmup with frozen backbone, LR=1e-3
- Phase 2 (20 epochs): Full fine-tuning with differential LRs

Usage:
    modal run modal/train_musiq_finetuning.py

Monitor:
    https://modal.com/apps
    modal app logs diqa-musiq-finetuning --follow

Reference:
    - docs/planning/MUSIQ_FINETUNING_PLAN.md
    - docs/planning/DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1
"""
# Justification: Modal training script uses print for progress logging

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import modal

# Create Modal app
app = modal.App("diqa-musiq-finetuning")

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
        # PyIQA for MUSIQ backbone
        "pyiqa>=0.1.12",
        # Deep learning
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        # Data augmentation
        "albumentations>=1.3.0",
        # Image processing
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
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
        "/root/.gcp/service-account.json",
        copy=True,
    )
    # Copy config file
    .add_local_file(
        "configs/musiq_finetuning.yaml",
        "/root/configs/musiq_finetuning.yaml",
        copy=True,
    )
)


def download_diqa5000(bucket_name: str, target_dir: Path) -> Path:
    """Download DIQA-5000 dataset from GCS.

    Args:
        bucket_name: GCS bucket name.
        target_dir: Local directory to extract dataset.

    Returns:
        Path to extracted dataset directory.
    """
    import tarfile

    from google.cloud import storage

    target_dir.mkdir(parents=True, exist_ok=True)

    # Set GCS credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

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

        tar.extractall(path=target_dir, members=members, filter="data")

    extract_time = time.time() - extract_start
    print(f"Extracted in {extract_time:.1f}s")

    # Clean up tarball
    tar_path.unlink()

    return target_dir / "diqa-5000"


def compute_validation_metrics(
    model: Any,
    val_loader: Any,
    device: str,
) -> dict[str, float]:
    """Compute validation metrics on validation set.

    Args:
        model: MUSIQ model.
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
        for images, labels in val_loader:
            images = images.to(device)

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
        model: MUSIQ model.
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
    gpu="A10G",  # 24GB VRAM - needed for MUSIQ multi-scale patches
    memory=65536,  # 64GB system RAM for dataset + multi-scale processing
    timeout=14400,  # 4 hours
    scaledown_window=300,
    secrets=[modal.Secret.from_name("gcs-credentials")],
    image=image,
)
class MUSIQTrainer:
    """Modal class for MUSIQ fine-tuning on DIQA-5000."""

    @modal.enter()
    def setup(self) -> None:
        """Initialize environment on container start."""
        import sys

        # Add source code to path
        sys.path.insert(0, "/root")

        # Set GCS credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

        print("MUSIQ Trainer initialized")

    @modal.method()
    def train(
        self,
        bucket_name: str = "image_detection_b",
        config_path: str = "/root/configs/musiq_finetuning.yaml",
    ) -> dict[str, Any]:
        """Run two-phase MUSIQ fine-tuning.

        Args:
            bucket_name: GCS bucket for dataset and model storage.
            config_path: Path to YAML configuration file.

        Returns:
            Training results including best checkpoint metrics.
        """
        import torch
        import yaml

        # Import local modules
        from image_preprocessing_detector.labeling.finetuning.musiq_config import (
            MUSIQTrainingConfig,
            get_checkpoint_preset,
            select_best_checkpoint,
        )
        from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
            create_dataloaders,
        )
        from image_preprocessing_detector.labeling.finetuning.musiq_loss import (
            MUSIQSpecialistLoss,
        )
        from image_preprocessing_detector.labeling.finetuning.musiq_wrapper import (
            create_musiq_multitask,
        )

        # Load configuration
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        config = MUSIQTrainingConfig.from_dict(config_dict)

        print("=" * 60)
        print("MUSIQ Fine-Tuning Configuration")
        print("=" * 60)
        print(f"Phase 1: {config.phase1_epochs} epochs (frozen backbone)")
        print(f"Phase 2: {config.phase2_epochs} epochs (full fine-tune)")
        print(f"Batch size: {config.batch_size}")
        print(f"Loss weights: {config.loss_weights}")
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
            print("\nLoading MUSIQ model...")
            model = create_musiq_multitask(
                device=device,
                freeze_backbone=config.phase1_freeze_backbone,
                head_hidden_dim=config.head_hidden_dim,
                head_dropout=config.dropout,
            )
            model = model.to(device)

            print(f"Total parameters: {model.get_total_params():,}")
            print(f"Trainable parameters: {model.get_trainable_params():,}")

            # Create loss function
            criterion = MUSIQSpecialistLoss(
                dimension_weights=config.loss_weights,
                mse_weight=config.mse_weight,
                rank_weight=config.rank_weight,
                focal_weight=config.focal_weight,
            )

            all_checkpoints: list[dict[str, Any]] = []

            # ============ PHASE 1: Head Warmup ============
            print("\n" + "=" * 60)
            print("PHASE 1: Head Warmup (Backbone Frozen)")
            print("=" * 60)

            # Create dataloaders for Phase 1
            train_loader, val_loader = create_dataloaders(
                root_dir=dataset_dir,
                batch_size=config.batch_size,
                num_workers=config.num_workers,
                phase=1,
            )

            print(f"Train samples: {len(train_loader.dataset)}")
            print(f"Val samples: {len(val_loader.dataset)}")

            # Phase 1 optimizer (head only)
            optimizer = torch.optim.AdamW(
                model.get_head_params(),
                lr=config.phase1_lr,
                weight_decay=config.weight_decay,
            )

            # LR scheduler with warmup
            total_steps = config.phase1_epochs * len(train_loader)
            warmup_steps = config.phase1_warmup_epochs * len(train_loader)

            def lr_lambda(step: int) -> float:
                if step < warmup_steps:
                    return float(step) / float(max(1, warmup_steps))
                progress = float(step - warmup_steps) / float(
                    max(1, total_steps - warmup_steps)
                )
                return max(
                    0.0, 0.5 * (1.0 + __import__("math").cos(progress * 3.14159))
                )

            scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

            # Gradient accumulation for memory efficiency
            accum_steps = getattr(config, "gradient_accumulation_steps", 1)

            # Phase 1 training loop
            for epoch in range(config.phase1_epochs):
                model.train()
                epoch_loss = 0.0
                num_batches = 0
                optimizer.zero_grad()

                for batch_idx, (images, labels) in enumerate(train_loader):
                    images = images.to(device)
                    labels = {k: v.to(device) for k, v in labels.items()}

                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    # Scale loss for gradient accumulation
                    loss = loss / accum_steps
                    loss.backward()

                    # Step optimizer every accum_steps batches
                    if (batch_idx + 1) % accum_steps == 0:
                        # Gradient clipping
                        torch.nn.utils.clip_grad_norm_(
                            model.parameters(), config.gradient_clip_norm
                        )
                        optimizer.step()
                        scheduler.step()
                        optimizer.zero_grad()

                    epoch_loss += loss.item() * accum_steps  # Rescale for logging
                    num_batches += 1

                avg_loss = epoch_loss / num_batches

                # Validation
                metrics = compute_validation_metrics(model, val_loader, device)
                metrics["train_loss"] = avg_loss

                print(
                    f"Epoch {epoch + 1}/{config.phase1_epochs} | "
                    f"Loss: {avg_loss:.4f} | "
                    f"SRCC_sharp: {metrics['srcc_sharpness']:.4f} | "
                    f"ECE: {metrics['ece_mean']:.4f} | "
                    f"LR: {scheduler.get_last_lr()[0]:.2e}"
                )

                # Save checkpoint
                if (epoch + 1) % config.checkpoint_interval == 0:
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
            if config.phase2_epochs <= 0:
                print("\n" + "=" * 60)
                print("PHASE 2: SKIPPED (phase2_epochs = 0)")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("PHASE 2: Full Fine-Tuning (Backbone Unfrozen)")
                print("=" * 60)

                # Unfreeze backbone
                model.unfreeze_backbone()
                print(
                    f"Trainable parameters after unfreeze: "
                    f"{model.get_trainable_params():,}"
                )

                # Create dataloaders for Phase 2 (with augmentation)
                train_loader, val_loader = create_dataloaders(
                    root_dir=dataset_dir,
                    batch_size=config.batch_size,
                    num_workers=config.num_workers,
                    phase=2,
                )

                # Phase 2 optimizer (differential LRs)
                optimizer = torch.optim.AdamW(
                    [
                        {
                            "params": model.get_backbone_params(),
                            "lr": config.phase2_backbone_lr,
                        },
                        {
                            "params": model.get_head_params(),
                            "lr": config.phase2_head_lr,
                        },
                    ],
                    weight_decay=config.weight_decay,
                )

                # LR scheduler with warmup
                total_steps = config.phase2_epochs * len(train_loader)
                warmup_steps = config.phase2_warmup_epochs * len(train_loader)

                scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

                # Phase 2 training loop
                for epoch in range(config.phase2_epochs):
                    model.train()
                    epoch_loss = 0.0
                    num_batches = 0
                    optimizer.zero_grad()

                    for batch_idx, (images, labels) in enumerate(train_loader):
                        images = images.to(device)
                        labels = {k: v.to(device) for k, v in labels.items()}

                        outputs = model(images)
                        loss = criterion(outputs, labels)
                        # Scale loss for gradient accumulation
                        loss = loss / accum_steps
                        loss.backward()

                        # Step optimizer every accum_steps batches
                        if (batch_idx + 1) % accum_steps == 0:
                            # Gradient clipping
                            torch.nn.utils.clip_grad_norm_(
                                model.parameters(), config.gradient_clip_norm
                            )
                            optimizer.step()
                            scheduler.step()
                            optimizer.zero_grad()

                        epoch_loss += loss.item() * accum_steps
                        num_batches += 1

                    avg_loss = epoch_loss / num_batches

                    # Validation
                    metrics = compute_validation_metrics(model, val_loader, device)
                    metrics["train_loss"] = avg_loss

                    total_epoch = config.phase1_epochs + epoch + 1
                    print(
                        f"Epoch {total_epoch}/{config.total_epochs} | "
                        f"Loss: {avg_loss:.4f} | "
                        f"SRCC_sharp: {metrics['srcc_sharpness']:.4f} | "
                        f"ECE: {metrics['ece_mean']:.4f} | "
                        f"LR_bb: {optimizer.param_groups[0]['lr']:.2e}"
                    )

                    # Save checkpoint
                    if (epoch + 1) % config.checkpoint_interval == 0:
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

            preset = get_checkpoint_preset(config.checkpoint_preset)
            best_ckpt = select_best_checkpoint(
                all_checkpoints,
                specialty="sharpness",
                **preset,
            )

            print(f"Selected checkpoint: Epoch {best_ckpt['epoch']}")
            print(f"  SRCC_sharpness: {best_ckpt['srcc_sharpness']:.4f}")
            print(f"  SRCC_overall: {best_ckpt['srcc_overall']:.4f}")
            print(f"  ECE_mean: {best_ckpt['ece_mean']:.4f}")

            # Load best checkpoint
            best_ckpt_data = torch.load(best_ckpt["path"], weights_only=True)
            model.load_state_dict(best_ckpt_data["model_state_dict"])

            # ============ Export ============
            print("\n" + "=" * 60)
            print("Model Export")
            print("=" * 60)

            # Save final model
            final_model_path = checkpoint_dir / "musiq_sharpness_specialist.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "config": config.to_dict(),
                    "metrics": best_ckpt,
                },
                final_model_path,
            )
            print(f"Saved final model: {final_model_path.name}")

            # Export to ONNX
            onnx_path = checkpoint_dir / "musiq_sharpness_specialist.onnx"
            try:
                model.eval()
                dummy_input = torch.randn(1, 3, 384, 384, device=device)
                torch.onnx.export(
                    model,
                    dummy_input,
                    str(onnx_path),
                    export_params=True,
                    opset_version=17,
                    input_names=["image"],
                    output_names=["overall", "sharpness", "color"],
                    dynamic_axes={
                        "image": {0: "batch_size", 2: "height", 3: "width"},
                    },
                )
                print(f"Exported ONNX model: {onnx_path.name}")
            except Exception as e:
                print(f"ONNX export failed: {e}")

            # Upload to GCS
            print("\nUploading to GCS...")
            gcs_model_path = "models/diqa/track_a_iqa/musiq/v1.0.0"

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
                json.dump(config.to_dict(), f, indent=2)
            upload_to_gcs(
                config_json_path,
                bucket_name,
                f"{gcs_model_path}/config.json",
            )

            # Save metrics
            metrics_path = checkpoint_dir / "metrics.json"
            with open(metrics_path, "w") as f:
                json.dump(best_ckpt, f, indent=2)
            upload_to_gcs(
                metrics_path,
                bucket_name,
                f"{gcs_model_path}/metrics.json",
            )

            print(f"\nModel uploaded to: gs://{bucket_name}/{gcs_model_path}/")

            return {
                "status": "success",
                "best_epoch": best_ckpt["epoch"],
                "srcc_sharpness": best_ckpt["srcc_sharpness"],
                "srcc_overall": best_ckpt["srcc_overall"],
                "srcc_color": best_ckpt["srcc_color"],
                "ece_mean": best_ckpt["ece_mean"],
                "gcs_path": f"gs://{bucket_name}/{gcs_model_path}/",
            }


@app.local_entrypoint()
def main() -> None:
    """Local entrypoint for Modal run."""
    trainer = MUSIQTrainer()
    result = trainer.train.remote()
    print("\n" + "=" * 60)
    print("Training Complete")
    print("=" * 60)
    print(json.dumps(result, indent=2))
