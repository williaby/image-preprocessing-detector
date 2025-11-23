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

import os
import sys
import tarfile
import time
from pathlib import Path

import modal

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


@stub.function(
    image=image,
    gpu="L4",  # L4 24GB - better availability than T4, avoids preemption issues
    timeout=86400,  # 24 hours max
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
def train_student():
    """Main training function for student model distillation."""
    import torch
    import yaml
    from google.cloud import storage
    from torch.utils.data import DataLoader

    # Add source to path
    sys.path.insert(0, "/root")

    from image_preprocessing_detector.models.loss_functions import DistillationLoss
    from image_preprocessing_detector.models.resnet_student import ResNetStudent
    from image_preprocessing_detector.models.resnet_teacher import ResNetTeacher
    from image_preprocessing_detector.training.student_trainer import StudentTrainer

    print("=" * 80)
    print("Student Model Distillation Training")
    print("=" * 80)
    print(
        "Training ResNet-18 student from ResNet-50 teacher via knowledge distillation"
    )
    print("=" * 80)

    # =========================================================================
    # STEP 1: Load Configuration
    # =========================================================================
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

    # =========================================================================
    # STEP 2: Setup GCS Client
    # =========================================================================
    print("\n[2/10] Setting up GCS client...")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"
    gcs_client = storage.Client()
    gcs_bucket = gcs_client.bucket(config["storage"]["bucket"])
    print(f"✅ Connected to GCS bucket: {config['storage']['bucket']}")

    # =========================================================================
    # STEP 3: Download Teacher Checkpoint
    # =========================================================================
    print("\n[3/10] Downloading teacher checkpoint from GCS...")

    teacher_checkpoint_path = Path("/root/checkpoints/teacher")
    teacher_checkpoint_path.mkdir(parents=True, exist_ok=True)

    teacher_gcs_path = config["teacher"]["checkpoint_path"]
    teacher_local_path = teacher_checkpoint_path / "teacher_checkpoint.pth"

    blob = gcs_bucket.blob(teacher_gcs_path)
    blob.download_to_filename(str(teacher_local_path))
    print(f"✅ Downloaded teacher checkpoint: {teacher_local_path}")

    # =========================================================================
    # STEP 4: Download Dataset
    # =========================================================================
    print("\n[4/10] Downloading 100K dataset from GCS...")

    dataset_path = Path("/root/data/training/iqa_phase2_100k")
    dataset_path.mkdir(parents=True, exist_ok=True)

    # Download tar.gz archive
    tar_path = Path("/root/data/iqa_phase2_100k.tar.gz")
    tar_blob = gcs_bucket.blob(config["dataset"]["gcs_path"])

    print("Downloading tar.gz archive (~9 GB)...")
    start_time = time.time()
    tar_blob.download_to_filename(str(tar_path))
    download_time = time.time() - start_time
    print(f"✅ Downloaded in {download_time:.1f}s")

    # Extract archive
    print("Extracting archive...")
    start_time = time.time()

    def safe_extract(tar_file: tarfile.TarFile, target_dir: Path) -> None:
        target_dir = target_dir.resolve()
        for member in tar_file.getmembers():
            member_path = (target_dir / member.name).resolve()
            if not str(member_path).startswith(str(target_dir)):
                raise RuntimeError(
                    f"Unsafe path detected in archive member: {member.name}"
                )
        tar_file.extractall(path=target_dir)

    with tarfile.open(tar_path, "r:gz") as tar:
        safe_extract(tar, dataset_path.parent)

    extract_time = time.time() - start_time
    print(f"✅ Extracted in {extract_time:.1f}s")

    # Clean up tar file
    tar_path.unlink()
    print("✅ Cleaned up tar.gz file")

    # =========================================================================
    # STEP 5: Load Metadata and Create Splits
    # =========================================================================
    print("\n[5/10] Loading metadata and creating data loaders...")

    import json

    import torchvision.transforms as transforms
    from PIL import Image
    from torch.utils.data import Dataset

    # Find dataset files
    images_dir = dataset_path / "images"
    metadata_file = dataset_path / "metadata.json"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

    # Load metadata.json
    with open(metadata_file) as f:
        metadata = json.load(f)

    total_samples = metadata["total_samples"]
    samples = metadata["samples"]
    print(f"Total samples in metadata: {total_samples:,}")

    # Create train/val splits
    train_ratio = config["dataset"].get("train_split", 0.8)

    train_size = int(total_samples * train_ratio)

    train_samples = samples[:train_size]
    val_samples = samples[train_size:]

    print(f"Split: {len(train_samples):,} train / {len(val_samples):,} val")

    # Dataset class for pre-generated 100K dataset
    class IQA100KDataset(Dataset):
        """Dataset for pre-generated 100K IQA samples with metadata."""

        def __init__(self, samples, images_dir, transform=None):
            self.samples = samples
            self.images_dir = Path(images_dir)
            self.transform = transform

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            sample = self.samples[idx]

            # Load image
            image_path = self.images_dir / sample["filename"]
            image = Image.open(image_path).convert("RGB")

            # Apply transforms
            if self.transform:
                image = self.transform(image)

            # Extract labels (5 defect types)
            labels = torch.tensor(
                [
                    sample["labels"]["blur"],
                    sample["labels"]["noise"],
                    sample["labels"]["skew"],
                    sample["labels"]["illumination"],
                    sample["labels"]["artifacts"],
                ],
                dtype=torch.float32,
            )

            return image, labels

    # Custom collate function for StudentTrainer format
    def collate_fn(batch):
        """Convert (image, labels) tuple format to StudentTrainer dict format."""
        images = []
        labels_list = []

        for image, labels in batch:
            images.append(image)
            labels_list.append(labels)

        # Stack into batched tensors
        images_batch = torch.stack(images)
        labels_batch = torch.stack(labels_list)

        # Convert to per-head format expected by StudentTrainer
        issue_types = ["blur", "noise", "skew", "illumination", "artifacts"]
        batch_dict = {
            "image": images_batch,
            "labels": {},
            "confidence": {},
        }

        # Split labels tensor into per-head format
        for idx, head_name in enumerate(issue_types):
            batch_dict["labels"][head_name] = labels_batch[:, idx]
            # Use full confidence (1.0) for all labels
            batch_dict["confidence"][head_name] = torch.ones_like(labels_batch[:, idx])

        return batch_dict

    # Create transforms
    train_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    val_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    # Create datasets
    train_dataset = IQA100KDataset(train_samples, images_dir, transform=train_transform)
    val_dataset = IQA100KDataset(val_samples, images_dir, transform=val_transform)

    print(f"Train samples: {len(train_dataset):,}")
    print(f"Val samples: {len(val_dataset):,}")

    # Create dataloaders
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

    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"✅ Created DataLoaders (batch_size={batch_size})")

    # =========================================================================
    # STEP 6: Load Teacher Model
    # =========================================================================
    print("\n[6/10] Loading teacher model...")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Create and load teacher
    teacher = ResNetTeacher(num_heads=5, dropout=0.2)
    teacher_checkpoint = torch.load(teacher_local_path, map_location=device)
    teacher.load_state_dict(teacher_checkpoint["model_state_dict"])
    teacher.eval()

    # Freeze teacher
    for param in teacher.parameters():
        param.requires_grad = False

    print(f"✅ Loaded teacher from epoch {teacher_checkpoint.get('epoch', 'unknown')}")
    print(f"   Teacher val_loss: {teacher_checkpoint.get('val_loss', 'unknown')}")
    print(
        f"   Teacher best_val_loss: {teacher_checkpoint.get('best_val_loss', 'unknown')}"
    )

    # =========================================================================
    # STEP 7: Create Student Model and Trainer
    # =========================================================================
    print("\n[7/10] Creating student model and trainer...")

    # Create student
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

    # Create distillation loss
    loss_fn = DistillationLoss(
        head_names=student.ISSUE_TYPES,
        temperature=config["distillation"]["temperature"],
        alpha=config["distillation"]["alpha"],
        confidence_weight=config["distillation"].get("confidence_weight", 0.3),
    )

    # Create trainer config
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

    # Create trainer
    trainer = StudentTrainer(
        student_model=student,
        teacher_model=teacher,
        loss_fn=loss_fn,
        config=trainer_config,
        device=str(device),
    )

    print("✅ Created StudentTrainer")

    # =========================================================================
    # STEP 8: Training Loop with GCS Uploads
    # =========================================================================
    print("\n[8/10] Starting training...")

    checkpoint_dir = Path("/root/checkpoints/student")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_interval = config["monitoring"].get("checkpoint_interval", 5)

    start_time = time.time()
    total_epochs = config["training"]["epochs"]
    val_loss = float("inf")

    if total_epochs < 1:
        raise ValueError("training.epochs must be at least 1")

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

            # Update trainer state
            trainer.epoch = epoch + 1

            epoch_time = time.time() - epoch_start
            elapsed = time.time() - start_time
            remaining = (elapsed / (epoch + 1)) * (total_epochs - epoch - 1)

            # Print epoch summary
            print(f"Train Loss: {train_metrics.get('loss', 0):.4f}")
            print(f"Val Loss: {val_metrics.get('loss', 0):.4f}")
            print(f"  Soft Loss: {val_metrics.get('soft_loss', 0):.4f}")
            print(f"  Hard Loss: {val_metrics.get('hard_loss', 0):.4f}")
            print(f"Epoch Time: {epoch_time / 60:.1f} min")
            print(
                f"Elapsed: {elapsed / 3600:.1f}h | Remaining: {remaining / 3600:.1f}h"
            )

            # Check for best model
            val_loss = val_metrics.get("loss", float("inf"))
            if val_loss < trainer.best_val_loss:
                trainer.best_val_loss = val_loss
                trainer.patience_counter = 0
                print(f"✨ New best val_loss: {val_loss:.4f}")
            else:
                trainer.patience_counter += 1

            # Save and upload checkpoint at intervals
            if (epoch + 1) % checkpoint_interval == 0:
                checkpoint_path = (
                    checkpoint_dir / f"student_checkpoint_epoch_{epoch + 1}.pth"
                )
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
                gcs_checkpoint_path = (
                    f"checkpoints/phase2_student/{checkpoint_path.name}"
                )
                blob = gcs_bucket.blob(gcs_checkpoint_path)
                blob.upload_from_filename(str(checkpoint_path))
                print(f"☁️  Uploaded to GCS: {gcs_checkpoint_path}")

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

    # =========================================================================
    # STEP 9: Save Final Checkpoint
    # =========================================================================
    print("\n[9/10] Saving final checkpoint...")

    final_epoch = max(getattr(trainer, "epoch", 0), epoch + 1 if epoch >= 0 else 0)
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

    # Upload final checkpoint
    blob = gcs_bucket.blob("checkpoints/phase2_student/student_final.pth")
    blob.upload_from_filename(str(final_checkpoint))
    print("✅ Uploaded final checkpoint to GCS")

    # =========================================================================
    # STEP 10: Export to ONNX
    # =========================================================================
    print("\n[10/10] Exporting to ONNX...")

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

    # Save training summary
    import json

    summary = {
        "model": "ResNetStudent",
        "architecture": "resnet18",
        "num_heads": 5,
        "training": {
            "epochs_completed": epoch + 1,
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
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    blob = gcs_bucket.blob("models/phase2_student/training_summary_student.json")
    blob.upload_from_filename(str(summary_path))
    print("☁️  Uploaded training summary to GCS")

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
def main():
    """Entry point for Modal CLI."""
    print("Starting Student Distillation Training...")
    print("Monitor progress at: https://modal.com/apps")
    print("Stream logs: modal app logs iqa-student-distillation --follow")
    train_student.remote()
