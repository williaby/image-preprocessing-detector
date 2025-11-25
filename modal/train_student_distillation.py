"""Modal training script for ResNet-18 Student Model via Knowledge Distillation.

This script trains the student model on Modal's GPU infrastructure using
knowledge distillation from the pre-trained teacher model.

Usage:
    # Run training in detached mode (recommended for long runs)
    poetry run modal run --detach modal/train_student_distillation.py

    # Monitor progress
    poetry run modal app logs <app-id> --follow

Features:
    - Downloads teacher checkpoint from GCS
    - Downloads 100K IQA dataset from GCS
    - Trains student via knowledge distillation
    - Uploads checkpoints to GCS periodically
    - Exports final model to ONNX format
"""

from __future__ import annotations

import json
import os
import sys
import tarfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import modal

if TYPE_CHECKING:
    from google.cloud.storage import Bucket

# =============================================================================
# Modal App Configuration
# =============================================================================

stub = modal.App("iqa-student-distillation")

# Create image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Core ML
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.24.0,<2.0.0",
        # Data processing
        "Pillow>=10.0.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",  # Required for schema validation
        # GCS
        "google-cloud-storage>=2.10.0",
        # Logging
        "tensorboard>=2.14.0",
        # Export
        "onnx>=1.14.0,<1.17.0",
    )
    # Copy source code
    .add_local_dir(
        "src/image_preprocessing_detector",
        "/root/image_preprocessing_detector",
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
        "configs/modal_student_distillation.yaml",
        "/root/configs/modal_student_distillation.yaml",
        copy=True,
    )
)


# =============================================================================
# Helper Functions (extracted to reduce cognitive complexity)
# =============================================================================


def _download_and_extract_dataset(
    gcs_bucket: Bucket,
    config: dict[str, Any],
    dataset_path: Path,
) -> None:
    """Download and extract the 100K dataset from GCS.

    Uses Python 3.12's safe extraction filter to prevent path traversal attacks.

    Args:
        gcs_bucket: GCS bucket client.
        config: Configuration dictionary.
        dataset_path: Local path to extract dataset to.
    """
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Download tar.gz archive
    tar_path = Path("/root/data/iqa_phase2_100k.tar.gz")
    tar_blob = gcs_bucket.blob(config["dataset"]["gcs_path"])

    print("Downloading tar.gz archive (~9 GB)...")
    start_time = time.time()
    tar_blob.download_to_filename(str(tar_path))
    download_time = time.time() - start_time
    print(f"✅ Downloaded in {download_time:.1f}s")

    # Extract archive using Python 3.12's safe filter
    print("Extracting archive...")
    start_time = time.time()

    with tarfile.open(tar_path, "r:gz") as tar:
        # Python 3.12+ filter='data' prevents path traversal and unsafe permissions
        tar.extractall(path=dataset_path.parent, filter="data")

    extract_time = time.time() - start_time
    print(f"✅ Extracted in {extract_time:.1f}s")

    # Clean up tar file
    tar_path.unlink()
    print("✅ Cleaned up tar.gz file")


def _run_training_loop(
    trainer: Any,
    train_loader: Any,
    val_loader: Any,
    student: Any,
    config: dict[str, Any],
    gcs_bucket: Bucket,
    checkpoint_dir: Path,
) -> tuple[float, float, int]:
    """Execute the main training loop with checkpoint uploads.

    Args:
        trainer: StudentTrainer instance.
        train_loader: Training data loader.
        val_loader: Validation data loader.
        student: Student model.
        config: Configuration dictionary.
        gcs_bucket: GCS bucket for checkpoint uploads.
        checkpoint_dir: Local checkpoint directory.

    Returns:
        Tuple of (val_loss, training_time, final_epoch).
    """
    checkpoint_interval = config["monitoring"].get("checkpoint_interval", 5)
    total_epochs = config["training"]["epochs"]

    if total_epochs < 1:
        msg = "training.epochs must be at least 1"
        raise ValueError(msg)

    start_time = time.time()
    val_loss = float("inf")
    trainer.epoch = 0
    epoch = -1

    try:
        for epoch in range(total_epochs):
            epoch_start = time.time()

            print(f"\n{'=' * 60}")
            print(f"EPOCH {epoch + 1}/{total_epochs}")
            print(f"{'=' * 60}")

            # Train one epoch
            train_metrics = trainer.train_epoch(train_loader)
            val_metrics = trainer.validate(val_loader)
            trainer.epoch = epoch + 1

            # Print epoch summary
            _print_epoch_summary(
                train_metrics, val_metrics, epoch_start, start_time, epoch, total_epochs
            )

            # Update best model tracking
            val_loss = val_metrics.get("loss", float("inf"))
            _update_best_model_tracking(trainer, val_loss)

            # Save and upload checkpoint at intervals
            if (epoch + 1) % checkpoint_interval == 0:
                _save_and_upload_checkpoint(
                    student, trainer, epoch, val_loss, checkpoint_dir, gcs_bucket
                )

            # Early stopping check
            if trainer.patience_counter >= trainer.early_stopping_patience:
                print(f"⚠️  Early stopping triggered at epoch {epoch + 1}")
                break

        training_time = time.time() - start_time
        print(f"\n✅ Training completed in {training_time / 3600:.2f} hours")
        print(f"Best validation loss: {trainer.best_val_loss:.4f}")

    except Exception as e:
        failed_epoch = epoch + 1 if epoch >= 0 else 0
        print(f"\n❌ Training failed at epoch {failed_epoch}: {e}")
        raise

    final_epoch = max(getattr(trainer, "epoch", 0), epoch + 1 if epoch >= 0 else 0)
    return val_loss, time.time() - start_time, final_epoch


def _print_epoch_summary(
    train_metrics: dict[str, float],
    val_metrics: dict[str, float],
    epoch_start: float,
    training_start: float,
    epoch: int,
    total_epochs: int,
) -> None:
    """Print summary metrics for the completed epoch."""
    epoch_time = time.time() - epoch_start
    elapsed = time.time() - training_start
    remaining = (elapsed / (epoch + 1)) * (total_epochs - epoch - 1)

    print(f"Train Loss: {train_metrics.get('loss', 0):.4f}")
    print(f"Val Loss: {val_metrics.get('loss', 0):.4f}")
    print(f"  Soft Loss: {val_metrics.get('soft_loss', 0):.4f}")
    print(f"  Hard Loss: {val_metrics.get('hard_loss', 0):.4f}")
    print(f"Epoch Time: {epoch_time / 60:.1f} min")
    print(f"Elapsed: {elapsed / 3600:.1f}h | Remaining: {remaining / 3600:.1f}h")


def _update_best_model_tracking(trainer: Any, val_loss: float) -> None:
    """Update trainer's best model tracking and patience counter."""
    if val_loss < trainer.best_val_loss:
        trainer.best_val_loss = val_loss
        trainer.patience_counter = 0
        print(f"✨ New best val_loss: {val_loss:.4f}")
    else:
        trainer.patience_counter += 1


def _save_and_upload_checkpoint(
    student: Any,
    trainer: Any,
    epoch: int,
    val_loss: float,
    checkpoint_dir: Path,
    gcs_bucket: Bucket,
) -> None:
    """Save checkpoint locally and upload to GCS."""
    import torch

    checkpoint_path = checkpoint_dir / f"student_checkpoint_epoch_{epoch + 1}.pth"
    torch.save(
        {
            "epoch": epoch + 1,
            "student_state_dict": student.state_dict(),
            "optimizer_state_dict": trainer.optimizer.state_dict(),
            "val_loss": val_loss,
            "best_val_loss": trainer.best_val_loss,
        },
        checkpoint_path,
    )
    print(f"💾 Saved checkpoint: {checkpoint_path.name}")

    # Upload to GCS
    gcs_checkpoint_path = f"checkpoints/phase2_student/{checkpoint_path.name}"
    blob = gcs_bucket.blob(gcs_checkpoint_path)
    blob.upload_from_filename(str(checkpoint_path))
    print(f"☁️  Uploaded to GCS: {gcs_checkpoint_path}")


def _export_onnx_model(
    student: Any,
    device: Any,
    gcs_bucket: Bucket,
) -> None:
    """Export student model to ONNX format and upload to GCS."""
    import torch

    student.eval()
    dummy_input = torch.randn(1, 3, 224, 224, device=device)

    onnx_path = Path("/root/models/resnet18_student.onnx")
    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        student,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["image"],
        output_names=["blur", "noise", "skew", "illumination", "artifacts"],
        dynamic_axes={
            "image": {0: "batch_size"},
            "blur": {0: "batch_size"},
            "noise": {0: "batch_size"},
            "skew": {0: "batch_size"},
            "illumination": {0: "batch_size"},
            "artifacts": {0: "batch_size"},
        },
        dynamo=False,
    )

    print(f"✅ Exported ONNX model: {onnx_path}")
    print(f"   Size: {onnx_path.stat().st_size / 1024 / 1024:.2f} MB")

    # Upload ONNX to GCS
    blob = gcs_bucket.blob("models/phase2_student/resnet18_student.onnx")
    blob.upload_from_filename(str(onnx_path))
    print("☁️  Uploaded ONNX to GCS")


@stub.function(
    image=image,
    gpu="L4",  # L4 24GB - better availability than T4, avoids preemption issues
    timeout=86400,  # 24 hours max
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
def train_student() -> None:
    """Main training function for student model distillation."""
    import torch

    # Add source to path
    sys.path.insert(0, "/root")

    from image_preprocessing_detector.models.loss_functions import DistillationLoss
    from image_preprocessing_detector.models.resnet_student import ResNetStudent
    from image_preprocessing_detector.models.resnet_teacher import ResNetTeacher
    from image_preprocessing_detector.training.student_trainer import StudentTrainer

    _print_training_banner()

    # Step 1: Load Configuration
    config = _load_config()

    # Step 2: Setup GCS Client
    _gcs_client, gcs_bucket = _setup_gcs_client(config)

    # Step 3: Download Teacher Checkpoint
    teacher_local_path = _download_teacher_checkpoint(gcs_bucket, config)

    # Step 4: Download Dataset
    dataset_path = Path("/root/data/training/iqa_phase2_100k")
    print("\n[4/10] Downloading 100K dataset from GCS...")
    _download_and_extract_dataset(gcs_bucket, config, dataset_path)

    # Step 5: Create Data Loaders
    train_loader, val_loader, batch_size = _create_data_loaders(
        dataset_path, config, torch
    )

    # Step 6: Load Teacher Model
    device, teacher, _teacher_checkpoint = _load_teacher_model(
        teacher_local_path, ResNetTeacher, torch
    )

    # Step 7: Create Student Model and Trainer
    student, trainer, teacher_params, student_params = _create_student_and_trainer(
        config,
        teacher,
        device,
        batch_size,
        ResNetStudent,
        DistillationLoss,
        StudentTrainer,
    )

    # Step 8: Training Loop
    checkpoint_dir = Path("/root/checkpoints/student")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print("\n[8/10] Starting training...")
    val_loss, training_time, final_epoch = _run_training_loop(
        trainer, train_loader, val_loader, student, config, gcs_bucket, checkpoint_dir
    )

    # Step 9: Save Final Checkpoint
    _save_final_checkpoint(
        student, trainer, val_loss, final_epoch, checkpoint_dir, gcs_bucket
    )

    # Step 10: Export to ONNX
    print("\n[10/10] Exporting to ONNX...")
    _export_onnx_model(student, device, gcs_bucket)

    # Save Training Summary
    _save_training_summary(
        config,
        trainer,
        final_epoch,
        training_time,
        teacher_params,
        student_params,
        gcs_bucket,
    )

    _print_completion_summary(
        config, trainer, training_time, teacher_params, student_params
    )


def _print_training_banner() -> None:
    """Print training banner."""
    print("=" * 80)
    print("Student Model Distillation Training")
    print("=" * 80)
    print(
        "Training ResNet-18 student from ResNet-50 teacher via knowledge distillation"
    )
    print("=" * 80)


def _load_config() -> dict[str, Any]:
    """Load configuration from YAML file."""
    import yaml

    print("\n[1/10] Loading configuration...")
    config_path = Path("/root/configs/modal_student_distillation.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    print(f"✅ Loaded config from {config_path}")
    print("Student architecture: resnet18")
    print(f"Teacher checkpoint: {config['teacher']['checkpoint_path']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")
    print(f"Temperature: {config['distillation']['temperature']}")
    print(f"Alpha: {config['distillation']['alpha']}")
    return config


def _setup_gcs_client(config: dict[str, Any]) -> tuple[Any, Bucket]:
    """Setup GCS client and return bucket."""
    from google.cloud import storage

    print("\n[2/10] Setting up GCS client...")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"
    gcs_client = storage.Client()
    gcs_bucket = gcs_client.bucket(config["storage"]["bucket"])
    print(f"✅ Connected to GCS bucket: {config['storage']['bucket']}")
    return gcs_client, gcs_bucket


def _download_teacher_checkpoint(gcs_bucket: Bucket, config: dict[str, Any]) -> Path:
    """Download teacher checkpoint from GCS."""
    print("\n[3/10] Downloading teacher checkpoint from GCS...")
    teacher_checkpoint_path = Path("/root/checkpoints/teacher")
    teacher_checkpoint_path.mkdir(parents=True, exist_ok=True)

    teacher_gcs_path = config["teacher"]["checkpoint_path"]
    teacher_local_path = teacher_checkpoint_path / "teacher_checkpoint.pth"

    blob = gcs_bucket.blob(teacher_gcs_path)
    blob.download_to_filename(str(teacher_local_path))
    print(f"✅ Downloaded teacher checkpoint: {teacher_local_path}")
    return teacher_local_path


def _create_data_loaders(
    dataset_path: Path,
    config: dict[str, Any],
    torch_module: Any,
) -> tuple[Any, Any, int]:
    """Create train and validation data loaders."""
    import torchvision.transforms as transforms
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset

    print("\n[5/10] Loading metadata and creating data loaders...")

    images_dir = dataset_path / "images"
    metadata_file = dataset_path / "metadata.json"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

    with open(metadata_file) as f:
        metadata = json.load(f)

    total_samples = metadata["total_samples"]
    samples = metadata["samples"]
    print(f"Total samples in metadata: {total_samples:,}")

    train_ratio = config["dataset"].get("train_split", 0.8)
    train_size = int(total_samples * train_ratio)
    train_samples = samples[:train_size]
    val_samples = samples[train_size:]
    print(f"Split: {len(train_samples):,} train / {len(val_samples):,} val")

    # Dataset class for pre-generated 100K dataset
    class IQA100KDataset(Dataset):
        """Dataset for pre-generated 100K IQA samples with metadata."""

        def __init__(self, samples_list: list, img_dir: Path, transform: Any = None):
            self.samples = samples_list
            self.images_dir = Path(img_dir)
            self.transform = transform

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> tuple[Any, Any]:
            sample = self.samples[idx]
            image_path = self.images_dir / sample["filename"]
            image = Image.open(image_path).convert("RGB")
            if self.transform:
                image = self.transform(image)

            labels = torch_module.tensor(
                [
                    sample["labels"]["blur"],
                    sample["labels"]["noise"],
                    sample["labels"]["skew"],
                    sample["labels"]["illumination"],
                    sample["labels"]["artifacts"],
                ],
                dtype=torch_module.float32,
            )
            return image, labels

    def collate_fn(batch: list) -> dict[str, Any]:
        """Convert batch to StudentTrainer format."""
        images = [img for img, _ in batch]
        labels_list = [lbl for _, lbl in batch]
        images_batch = torch_module.stack(images)
        labels_batch = torch_module.stack(labels_list)

        issue_types = ["blur", "noise", "skew", "illumination", "artifacts"]
        batch_dict: dict[str, Any] = {
            "image": images_batch,
            "labels": {},
            "confidence": {},
        }
        for idx, head_name in enumerate(issue_types):
            batch_dict["labels"][head_name] = labels_batch[:, idx]
            batch_dict["confidence"][head_name] = torch_module.ones_like(
                labels_batch[:, idx]
            )
        return batch_dict

    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_dataset = IQA100KDataset(train_samples, images_dir, transform=transform)
    val_dataset = IQA100KDataset(val_samples, images_dir, transform=transform)

    batch_size = config["training"]["batch_size"]
    num_workers = config["training"].get("num_workers", 4)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
        collate_fn=collate_fn,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn,
    )

    print(f"Train samples: {len(train_dataset):,}")
    print(f"Val samples: {len(val_dataset):,}")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"✅ Created DataLoaders (batch_size={batch_size})")

    return train_loader, val_loader, batch_size


def _load_teacher_model(
    teacher_local_path: Path,
    ResNetTeacher: type,  # noqa: N803
    torch_module: Any,
) -> tuple[Any, Any, dict[str, Any]]:
    """Load teacher model from checkpoint."""
    print("\n[6/10] Loading teacher model...")

    device = torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    teacher = ResNetTeacher(num_heads=5, dropout=0.2)
    # Security: Loading our own checkpoint from GCS; file source is trusted
    # weights_only=False required for full checkpoint (includes optimizer state)
    teacher_checkpoint = torch_module.load(
        teacher_local_path, map_location=device, weights_only=False
    )
    teacher.load_state_dict(teacher_checkpoint["model_state_dict"])
    teacher.eval()

    for param in teacher.parameters():
        param.requires_grad = False

    print(f"✅ Loaded teacher from epoch {teacher_checkpoint.get('epoch', 'unknown')}")
    print(f"   Teacher val_loss: {teacher_checkpoint.get('val_loss', 'unknown')}")
    print(
        f"   Teacher best_val_loss: {teacher_checkpoint.get('best_val_loss', 'unknown')}"
    )

    return device, teacher, teacher_checkpoint


def _create_student_and_trainer(
    config: dict[str, Any],
    teacher: Any,
    device: Any,
    batch_size: int,
    ResNetStudent: type,  # noqa: N803
    DistillationLoss: type,  # noqa: N803
    StudentTrainer: type,  # noqa: N803
) -> tuple[Any, Any, int, int]:
    """Create student model and trainer."""
    print("\n[7/10] Creating student model and trainer...")

    student = ResNetStudent(
        num_heads=5,
        hidden_features=config["student"].get("hidden_features", 256),
        dropout=config["student"].get("dropout", 0.2),
    )

    student_params = sum(p.numel() for p in student.parameters())
    teacher_params = sum(p.numel() for p in teacher.parameters())
    print(f"Student parameters: {student_params:,}")
    print(f"Teacher parameters: {teacher_params:,}")
    print(f"Compression ratio: {teacher_params / student_params:.2f}x")

    loss_fn = DistillationLoss(
        head_names=student.ISSUE_TYPES,
        temperature=config["distillation"]["temperature"],
        alpha=config["distillation"]["alpha"],
        confidence_weight=config["distillation"].get("confidence_weight", 0.3),
    )

    trainer_config = {
        "batch_size": batch_size,
        "epochs": config["training"]["epochs"],
        "learning_rate": config["training"]["learning_rate"],
        "weight_decay": config["training"].get("weight_decay", 0.01),
        "optimizer": config["training"].get("optimizer", "adamw"),
        "gradient_clip_norm": config["training"].get("gradient_clip_norm", 1.0),
        "early_stopping_patience": config["training"].get(
            "early_stopping_patience", 10
        ),
        "checkpoint_dir": "/root/checkpoints/student",
        "log_dir": "/root/logs/student",
        "save_interval_epochs": config["monitoring"].get("checkpoint_interval", 5),
        "log_interval": config["monitoring"].get("log_interval", 50),
        "mixed_precision": {"enabled": True},
        "scheduler": {
            "type": config["training"].get("scheduler", "cosine"),
            "min_lr": config["training"].get("min_lr", 1e-6),
        },
    }

    trainer = StudentTrainer(
        student_model=student,
        teacher_model=teacher,
        loss_fn=loss_fn,
        config=trainer_config,
        device=str(device),
    )

    print("✅ Created StudentTrainer")
    return student, trainer, teacher_params, student_params


def _save_final_checkpoint(
    student: Any,
    trainer: Any,
    val_loss: float,
    final_epoch: int,
    checkpoint_dir: Path,
    gcs_bucket: Bucket,
) -> None:
    """Save final checkpoint and upload to GCS."""
    import torch

    print("\n[9/10] Saving final checkpoint...")
    final_checkpoint = checkpoint_dir / "student_final.pth"
    torch.save(
        {
            "epoch": final_epoch,
            "student_state_dict": student.state_dict(),
            "optimizer_state_dict": trainer.optimizer.state_dict(),
            "val_loss": val_loss,
            "best_val_loss": trainer.best_val_loss,
            "training_history": trainer.training_history,
        },
        final_checkpoint,
    )

    blob = gcs_bucket.blob("checkpoints/phase2_student/student_final.pth")
    blob.upload_from_filename(str(final_checkpoint))
    print("✅ Uploaded final checkpoint to GCS")


def _save_training_summary(
    config: dict[str, Any],
    trainer: Any,
    final_epoch: int,
    training_time: float,
    teacher_params: int,
    student_params: int,
    gcs_bucket: Bucket,
) -> None:
    """Save training summary to GCS."""
    summary = {
        "model": "ResNetStudent",
        "architecture": "resnet18",
        "num_heads": 5,
        "training": {
            "epochs_completed": final_epoch,
            "best_val_loss": float(trainer.best_val_loss),
            "training_time_hours": training_time / 3600,
            "teacher_checkpoint": config["teacher"]["checkpoint_path"],
        },
        "distillation": {
            "temperature": config["distillation"]["temperature"],
            "alpha": config["distillation"]["alpha"],
        },
        "compression": {
            "teacher_params": teacher_params,
            "student_params": student_params,
            "ratio": teacher_params / student_params,
        },
    }

    summary_path = Path("/root/models/training_summary_student.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    blob = gcs_bucket.blob("models/phase2_student/training_summary_student.json")
    blob.upload_from_filename(str(summary_path))
    print("☁️  Uploaded training summary to GCS")


def _print_completion_summary(
    config: dict[str, Any],
    trainer: Any,
    training_time: float,
    teacher_params: int,
    student_params: int,
) -> None:
    """Print completion summary."""
    print("\n" + "=" * 80)
    print("🎉 Student Distillation Training Complete!")
    print("=" * 80)
    print(f"Best validation loss: {trainer.best_val_loss:.4f}")
    print(f"Total training time: {training_time / 3600:.2f} hours")
    print(f"Compression ratio: {teacher_params / student_params:.2f}x")
    print("\nOutputs uploaded to GCS:")
    print(
        f"  - Checkpoints: gs://{config['storage']['bucket']}/checkpoints/phase2_student/"
    )
    print(f"  - ONNX model: gs://{config['storage']['bucket']}/models/phase2_student/")


@stub.local_entrypoint()
def main() -> None:
    """Entry point for Modal CLI."""
    print("Starting Student Distillation Training...")
    print("Monitor progress at: https://modal.com/apps")
    print("Stream logs: modal app logs iqa-student-distillation --follow")
    train_student.remote()
