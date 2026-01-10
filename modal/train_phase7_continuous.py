# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 7 Continuous Label Training on Modal - ResNet Teacher with BCE+MSE Loss.

This trains the ResNet-50 teacher model on continuous severity labels [0, 1]
instead of binary labels, enabling:
- Improved model calibration (ECE target: <0.10)
- Severity-aware predictions (mild vs severe defects)
- Better DQS scores for routing decisions

**Phase 7 Training Configuration**:
- Combined BCE+MSE loss (alpha=0.6, beta=0.4)
- ECE-based early stopping
- 50 epochs, batch_size=128, AdamW optimizer
- Target metrics: ECE < 0.10, severity MAE < 0.18, F1 > 0.82

Dataset:
    - Source: data/training/iqa_phase7_continuous (150K samples)
    - Format: ContinuousQualityLabel JSON schema
    - GCS: gs://image_detection_b/training/iqa_phase7_150k_continuous/

Usage:
    modal run modal/train_phase7_continuous.py

Monitor:
    https://modal.com/apps
    modal app logs iqa-phase7-continuous --follow

Reference:
    Phase 7 Strategy: docs/planning/PROJECT_PLAN.md (Sprint 7.2.3)
"""
# Justification: Modal training script uses print for progress logging
# mypy: ignore-errors

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import modal

# Create Modal app
stub = modal.App("iqa-phase7-continuous")

# Define container image with source code and dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Deep learning
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "timm>=0.9.0",
        # Data augmentation
        "albumentations>=1.3.0",
        # Image processing
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
        # Monitoring
        "tensorboard>=2.14.0",
        # ML utils
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        # Configuration
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        # GCS integration
        "google-cloud-storage>=2.10.0",
        "gcsfs>=2023.1.0",
        # Export
        "onnx>=1.14.0",
        "onnxscript>=0.1.0",
    )
    # Copy source code into container
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    # Copy data module for continuous labels
    .add_local_dir(
        local_path="data",
        remote_path="/root/data",
        copy=True,
    )
    # Copy GCS credentials
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)

# Secrets for GCS access
gcs_secret = modal.Secret.from_name("gcs-credentials")

# Volumes for persistent storage
training_volume = modal.Volume.from_name("phase7-training-data", create_if_missing=True)
checkpoint_volume = modal.Volume.from_name("phase7-checkpoints", create_if_missing=True)


@dataclass
class Phase7TrainingConfig:
    """Configuration for Phase 7 continuous label training."""

    # Dataset
    dataset_gcs_path: str = "gs://image_detection_b/training/iqa_phase7_150k_continuous"
    train_split_ratio: float = 0.70
    val_split_ratio: float = 0.15
    test_split_ratio: float = 0.15

    # Model
    model_architecture: str = "resnet50"
    num_heads: int = 5
    dropout: float = 0.2
    pretrained: bool = True

    # Loss function (Phase 7: BCE+MSE)
    loss_alpha: float = 0.6  # BCE weight
    loss_beta: float = 0.4  # MSE weight
    binary_threshold: float = 0.5
    label_smoothing: float = 0.0

    # Training
    epochs: int = 50
    batch_size: int = 128
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    optimizer: str = "adamw"
    gradient_clip_norm: float = 1.0

    # Scheduler
    scheduler_type: str = "cosine"
    min_lr: float = 1e-6

    # Early stopping (Phase 7: ECE-based)
    use_ece_early_stopping: bool = True
    target_ece: float = 0.10
    early_stopping_patience: int = 10

    # Mixed precision
    use_amp: bool = True

    # Checkpointing
    save_interval_epochs: int = 5
    keep_last_n: int = 3

    # Logging
    log_interval: int = 50

    # Output
    output_gcs_path: str = "gs://image_detection_b/models/phase7"
    export_onnx: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dataset_gcs_path": self.dataset_gcs_path,
            "model_architecture": self.model_architecture,
            "num_heads": self.num_heads,
            "dropout": self.dropout,
            "loss_alpha": self.loss_alpha,
            "loss_beta": self.loss_beta,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "use_ece_early_stopping": self.use_ece_early_stopping,
            "target_ece": self.target_ece,
            "use_amp": self.use_amp,
        }


def download_dataset_from_gcs(gcs_path: str, local_path: Path) -> Path:
    """Download dataset from GCS to local storage.

    Args:
        gcs_path: GCS path (gs://bucket/path)
        local_path: Local destination directory

    Returns:
        Path to local dataset directory
    """
    from google.cloud import storage

    print(f"Downloading dataset from {gcs_path}")
    start_time = time.time()

    # Parse GCS path
    bucket_name = gcs_path.replace("gs://", "").split("/")[0]
    prefix = "/".join(gcs_path.replace("gs://", "").split("/")[1:])

    # Download
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    local_path.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for blob in blobs:
        relative_path = blob.name[len(prefix) :].lstrip("/")
        if not relative_path:
            continue

        local_file = local_path / relative_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_file))
        downloaded += 1

        if downloaded % 1000 == 0:
            print(f"  Downloaded {downloaded} files...")

    elapsed = time.time() - start_time
    print(f"Downloaded {downloaded} files in {elapsed:.1f}s")

    return local_path


def upload_to_gcs(local_path: Path, gcs_path: str) -> None:
    """Upload file or directory to GCS.

    Args:
        local_path: Local file or directory
        gcs_path: GCS destination path
    """
    from google.cloud import storage

    bucket_name = gcs_path.replace("gs://", "").split("/")[0]
    prefix = "/".join(gcs_path.replace("gs://", "").split("/")[1:])

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    if local_path.is_file():
        blob = bucket.blob(prefix)
        blob.upload_from_filename(str(local_path))
        print(f"Uploaded {local_path} to {gcs_path}")
    else:
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(local_path)
                blob_path = f"{prefix}/{relative}"
                blob = bucket.blob(blob_path)
                blob.upload_from_filename(str(file_path))
        print(f"Uploaded directory {local_path} to {gcs_path}")


@stub.function(
    image=image,
    gpu="T4",
    timeout=86400,  # 24 hours
    secrets=[gcs_secret],
    volumes={
        "/data": training_volume,
        "/checkpoints": checkpoint_volume,
    },
)
def train_phase7_teacher(
    config_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train ResNet-50 teacher model with Phase 7 continuous labels.

    Args:
        config_override: Optional dict to override default config values

    Returns:
        Dictionary with training results and metrics
    """
    import sys

    sys.path.insert(0, "/root")

    import torch

    # Import our modules
    from image_preprocessing_detector.models.loss_functions import ContinuousBCEMSELoss
    from image_preprocessing_detector.models.resnet_teacher import ResNetTeacher
    from image_preprocessing_detector.training.continuous_trainer import (
        ContinuousTeacherTrainer,
    )

    # Build configuration
    config = Phase7TrainingConfig()
    if config_override:
        for key, value in config_override.items():
            if hasattr(config, key):
                setattr(config, key, value)

    print("=" * 60)
    print("Phase 7 Continuous Label Training")
    print("=" * 60)
    print(f"Configuration: {json.dumps(config.to_dict(), indent=2)}")

    # Set up paths
    data_dir = Path("/data/phase7_dataset")
    checkpoint_dir = Path("/checkpoints/phase7")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Download dataset
    download_dataset_from_gcs(config.dataset_gcs_path, data_dir)

    # Create data loaders
    print("\nCreating data loaders...")
    from data.dataset import create_continuous_data_loaders

    train_loader, val_loader, test_loader = create_continuous_data_loaders(
        data_dir=data_dir,
        batch_size=config.batch_size,
        num_workers=4,
        label_type="continuous",
        return_variance=False,  # GDBC not used in initial training
    )

    print(f"Train samples: {len(train_loader.dataset)}")
    print(f"Val samples: {len(val_loader.dataset)}")
    print(f"Test samples: {len(test_loader.dataset)}")

    # Create model
    print("\nCreating model...")
    model = ResNetTeacher(
        num_heads=config.num_heads,
        dropout=config.dropout,
        pretrained=config.pretrained,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name()}")

    # Create loss function
    loss_fn = ContinuousBCEMSELoss(
        alpha=config.loss_alpha,
        beta=config.loss_beta,
        binary_threshold=config.binary_threshold,
        label_smoothing=config.label_smoothing,
    )

    # Create trainer
    trainer_config = {
        "batch_size": config.batch_size,
        "epochs": config.epochs,
        "learning_rate": config.learning_rate,
        "weight_decay": config.weight_decay,
        "optimizer": config.optimizer,
        "gradient_clip_norm": config.gradient_clip_norm,
        "scheduler": {"type": config.scheduler_type, "min_lr": config.min_lr},
        "use_ece_early_stopping": config.use_ece_early_stopping,
        "target_ece": config.target_ece,
        "early_stopping_patience": config.early_stopping_patience,
        "mixed_precision": {"enabled": config.use_amp},
        "checkpoint_dir": str(checkpoint_dir),
        "log_dir": str(checkpoint_dir / "logs"),
        "save_interval_epochs": config.save_interval_epochs,
        "keep_last_n": config.keep_last_n,
        "log_interval": config.log_interval,
    }

    trainer = ContinuousTeacherTrainer(
        model=model,
        loss_fn=loss_fn,
        config=trainer_config,
        device=str(device),
    )

    # Train
    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60)

    start_time = time.time()
    results = trainer.train(train_loader, val_loader)
    training_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)
    print(f"Training time: {training_time / 3600:.2f} hours")
    print(f"Best validation loss: {results['best_val_loss']:.4f}")
    print(f"Best ECE: {results['best_ece']:.4f}")
    print(f"Target ECE achieved: {results['target_ece_achieved']}")

    # Evaluate on test set
    print("\nEvaluating on test set...")
    test_metrics = trainer.validate(test_loader)
    print(f"Test Loss: {test_metrics['loss']:.4f}")
    print(f"Test ECE: {test_metrics['ece']:.4f}")
    print(f"Test Severity MAE: {test_metrics['severity_mae']:.4f}")

    # Export to ONNX if configured
    if config.export_onnx:
        print("\nExporting model to ONNX...")
        onnx_path = checkpoint_dir / "resnet50_teacher_continuous_v2.onnx"

        model.eval()
        model.to("cpu")

        dummy_input = torch.randn(1, 3, 224, 224)

        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            input_names=["image"],
            output_names=[f"head_{i}" for i in range(config.num_heads)],
            dynamic_axes={"image": {0: "batch_size"}},
            opset_version=17,
        )
        print(f"Saved ONNX model: {onnx_path}")

    # Upload results to GCS
    print("\nUploading results to GCS...")
    upload_to_gcs(checkpoint_dir, config.output_gcs_path)

    # Save training summary
    summary = {
        "phase": 7,
        "model_version": "continuous_v2.0",
        "config": config.to_dict(),
        "results": {
            "best_val_loss": results["best_val_loss"],
            "best_ece": results["best_ece"],
            "target_ece_achieved": results["target_ece_achieved"],
            "total_epochs": results["total_epochs"],
            "training_time_hours": training_time / 3600,
        },
        "test_metrics": {
            "loss": test_metrics["loss"],
            "ece": test_metrics["ece"],
            "severity_mae": test_metrics["severity_mae"],
            "severity_correlation": test_metrics["severity_correlation"],
        },
    }

    summary_path = checkpoint_dir / "training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("Phase 7 Training Summary")
    print("=" * 60)
    print(json.dumps(summary, indent=2))

    return summary


@stub.local_entrypoint()
def main(
    epochs: int = 50,
    batch_size: int = 128,
    learning_rate: float = 1e-4,
    target_ece: float = 0.10,
):
    """Run Phase 7 continuous label training.

    Args:
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Initial learning rate
        target_ece: Target Expected Calibration Error
    """
    config_override = {
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "target_ece": target_ece,
    }

    print("Launching Phase 7 continuous label training on Modal...")
    result = train_phase7_teacher.remote(config_override)
    print("\nTraining complete!")
    print(f"Results: {json.dumps(result, indent=2)}")
