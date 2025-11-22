# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 2 IQA Training on Modal - ResNet Teacher Model on 100K Dataset.

Multi-label CNN for Image Quality Assessment (Project A - RAG Pipeline).

This trains the ResNet-50 teacher model to detect image quality issues (blur, noise,
skew, illumination, artifacts) for use in Document Quality Score (DQS) calculation
and pre-OCR risk assessment.

**100K Dataset Training**:
- Train ResNet-50 teacher model on pre-generated 100K dataset
- 13-dimensional balanced distribution across defect types, severity, DPI, etc.
- 70K train / 15K val / 15K test split
- 50 epochs, batch_size=128, Adam optimizer
- Target metrics: mAP > 0.88, per-class F1 > 0.85

Dataset:
    - Source: data/training/iqa_phase2_100k (tracked with DVC)
    - Size: ~40-50 GB, 100,000 samples
    - Format: images/ directory + metadata.json
    - GCS: gs://image_detection_b/.../iqa_phase2_100k/

Usage:
    modal run modal/train_phase2_iqa.py

Monitor:
    https://modal.com/apps
    modal app logs iqa-phase2-training --follow

Models:
    Teacher (ResNet-50): High-capacity model for 100K training
    Student (ResNet-18): Future distillation (Sprint 3.7+)
"""
# Justification: Modal training script uses print for progress logging and /tmp for container-local storage
# mypy: ignore-errors

import yaml  # type: ignore[import-untyped]

import modal

# Create Modal app
stub = modal.App("iqa-phase2-training")

# Define container image with source code and dependencies
# Force rebuild: 2025-11-18-100K-Dataset-DVC-Integration
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
        # Configuration
        "pyyaml>=6.0",
        # GCS integration (includes gsutil via gcloud SDK)
        "google-cloud-storage>=2.10.0",
        "gcsfs>=2023.1.0",  # For efficient GCS file operations
        # Export
        "onnx>=1.14.0",
        "onnxscript>=0.1.0",  # Required for torch.onnx.export in PyTorch 2.x
    )
    # Copy source code into container (copy=True bakes into image layer)
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    # Note: Dataset is downloaded directly from GCS at runtime (no DVC)
    # Copy GCS credentials configuration
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
    # Copy config file into container
    .add_local_file(
        "configs/modal_phase2_iqa.yaml",  # Production: 50 epochs
        "/root/configs/modal_phase2_iqa.yaml",
        copy=True,
    )
)

@stub.function(
    image=image,
    gpu="A10",  # A10 24GB - cost-optimized (~$1.10/hr), we only use ~6GB
    cpu=8.0,
    memory=32768,  # 32GB
    timeout=86400,  # 24 hours
)
def train_iqa():
    """Main training function - ResNet-50 teacher on 100K dataset.

    Implements complete training pipeline:
    1. Pull 100K dataset from GCS via DVC (~40-50GB)
    2. Load metadata and create train/val/test splits
    3. Initialize ResNet-50 teacher model
    4. Train with multi-label loss for 50 epochs
    5. Save checkpoints to GCS every 5 epochs
    6. Export final model to ONNX + TorchScript

    Expected runtime: 12-24 hours on T4 GPU
    Expected cost: ~$7-14 (or $0 with $30/month free tier)
    """
    import json
    import os
    import sys
    import time
    from pathlib import Path

    # Add source to Python path
    sys.path.insert(0, "/root")

    import torch
    from torch.utils.data import DataLoader

    # Import local modules
    from image_preprocessing_detector.models import MultiHeadIQALoss, ResNetTeacher
    from image_preprocessing_detector.training import TeacherTrainer

    print("=" * 80)
    print("Phase 2 IQA Training - 100K Dataset with 13-Dimensional Distribution")
    print("=" * 80)
    print("Training ResNet-50 teacher model for Image Quality Assessment")
    print("Dataset: 100K samples with balanced defect types, severity, DPI, etc.")
    print("Outputs will be used for DQS calculation and routing metadata")
    print("=" * 80)

    # =========================================================================
    # STEP 1: Load Configuration
    # =========================================================================
    print("\n[1/10] Loading configuration...")
    config_path = "/root/configs/modal_phase2_iqa.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    print(f"✅ Loaded config from {config_path}")
    print(f"Teacher architecture: {config['model']['teacher_architecture']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")
    print(f"Learning rate: {config['training']['learning_rate']}")

    # =========================================================================
    # STEP 2: Download Dataset from GCS (tar.gz archive for fast download)
    # =========================================================================
    print("\n[2/10] Downloading 100K dataset from GCS...")
    print("Dataset: ~9 GB tar.gz archive, 99,630 samples")
    print("Using single tar.gz archive for fast download (avoids 100K file timeout)...")

    import tarfile

    from google.cloud import storage

    # Configure GCS credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    # Create dataset directory
    dataset_dir = Path("/root/data/training/iqa_phase2_100k")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # GCS tar.gz location
    bucket_name = "image_detection_b"
    tar_blob_name = "image-preprocessing-detector/phase2/iqa_phase2_100k.tar.gz"
    tar_local_path = Path("/tmp/iqa_phase2_100k.tar.gz")

    print(f"Source: gs://{bucket_name}/{tar_blob_name}")
    print(f"Destination: {dataset_dir}")

    download_start = time.time()

    # Initialize GCS client and download tar.gz
    print("Downloading tar.gz archive (~9 GB)...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(tar_blob_name)
    blob.download_to_filename(str(tar_local_path))

    download_time = time.time() - download_start
    tar_size_gb = tar_local_path.stat().st_size / (1024**3)
    print(f"✅ Downloaded {tar_size_gb:.2f} GB in {download_time/60:.1f} minutes")

    # Extract tar.gz archive
    print("Extracting archive...")
    extract_start = time.time()
    with tarfile.open(tar_local_path, "r:gz") as tar:
        # Extract to parent directory (archive contains iqa_phase2_100k/ folder)
        tar.extractall(path=dataset_dir.parent)

    extract_time = time.time() - extract_start
    print(f"✅ Extracted in {extract_time/60:.1f} minutes")

    # Clean up tar.gz to save disk space
    tar_local_path.unlink()
    print("✅ Cleaned up tar.gz archive")

    total_time = time.time() - download_start
    print(f"✅ Dataset ready in {total_time/60:.1f} minutes total")

    # Verify dataset structure
    dataset_dir = Path("/root/data/training/iqa_phase2_100k")
    images_dir = dataset_dir / "images"
    metadata_file = dataset_dir / config['data']['metadata_file']

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

    # Count images
    num_images = len(list(images_dir.glob("*.jpg")))
    print(f"✅ Dataset verified: {num_images:,} images found")
    print(f"✅ Metadata file: {metadata_file}")

    # =========================================================================
    # STEP 3: Create Device and Model
    # =========================================================================
    print("\n[3/10] Creating model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Create ResNet-50 teacher model
    model = ResNetTeacher(
        num_heads=config['model']['num_classes'],
        dropout=config['model']['dropout'],
        pretrained=config['model']['pretrained'],
    )
    model = model.to(device)

    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {num_params:,}")

    # Create loss function
    loss_fn = MultiHeadIQALoss(head_names=model.ISSUE_TYPES)
    loss_fn = loss_fn.to(device)

    print("✅ Model and loss function created")

    # =========================================================================
    # STEP 4: Load Metadata and Create Splits
    # =========================================================================
    print("\n[4/10] Loading metadata and creating splits...")

    # Load metadata.json
    with open(metadata_file) as f:
        metadata = json.load(f)

    total_samples = metadata["total_samples"]
    samples = metadata["samples"]

    print(f"Total samples in metadata: {total_samples:,}")
    print(f"Loaded {len(samples):,} sample entries")

    # Create train/val/test splits based on config
    train_ratio = config['data']['train_split']
    val_ratio = config['data']['val_split']
    _test_ratio = config['data']['test_split']  # Read but calculated via remainder

    train_size = int(total_samples * train_ratio)
    val_size = int(total_samples * val_ratio)
    _test_size = total_samples - train_size - val_size

    train_samples = samples[:train_size]
    val_samples = samples[train_size:train_size + val_size]
    test_samples = samples[train_size + val_size:]

    print(f"Split: {len(train_samples):,} train / {len(val_samples):,} val / {len(test_samples):,} test")

    # =========================================================================
    # STEP 5: Create DataLoaders
    # =========================================================================
    print("\n[5/10] Creating data loaders...")

    # Import required libraries for dataset
    import torch
    import torchvision.transforms as tv_transforms
    from PIL import Image
    from torch.utils.data import Dataset

    # Simple dataset class for pre-generated 100K dataset
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

            # Extract labels (5 defect types: blur, noise, skew, illumination, artifacts)
            labels = torch.tensor([
                sample["labels"]["blur"],
                sample["labels"]["noise"],
                sample["labels"]["skew"],
                sample["labels"]["illumination"],
                sample["labels"]["artifacts"],
            ], dtype=torch.float32)

            return image, labels

    # Create transforms
    train_transform = tv_transforms.Compose([
        tv_transforms.Resize((224, 224)),
        tv_transforms.ToTensor(),
        tv_transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = tv_transforms.Compose([
        tv_transforms.Resize((224, 224)),
        tv_transforms.ToTensor(),
        tv_transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Create datasets
    train_dataset = IQA100KDataset(train_samples, images_dir, transform=train_transform)
    val_dataset = IQA100KDataset(val_samples, images_dir, transform=val_transform)

    print(f"Train samples: {len(train_dataset):,}")
    print(f"Val samples: {len(val_dataset):,}")

    # Custom collate function to convert tuple format to dict format
    def collate_fn(batch):
        """Convert (image, labels) tuple format to TeacherTrainer dict format."""
        images = []
        labels_list = []

        for image, labels in batch:
            images.append(image)
            labels_list.append(labels)

        # Stack into batched tensors
        images_batch = torch.stack(images)
        labels_batch = torch.stack(labels_list)

        # Convert to per-head format expected by TeacherTrainer
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

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
        num_workers=config['data']['num_workers'],
        pin_memory=config['data']['pin_memory'],
        collate_fn=collate_fn,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=config['data']['num_workers'],
        pin_memory=config['data']['pin_memory'],
        collate_fn=collate_fn,
    )

    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print("✅ Data loaders created")

    # =========================================================================
    # STEP 6: Create Trainer
    # =========================================================================
    print("\n[6/10] Creating trainer...")

    # Prepare trainer configuration
    trainer_config = {
        "batch_size": config['training']['batch_size'],
        "epochs": config['training']['epochs'],
        "learning_rate": config['training']['learning_rate'],
        "weight_decay": config['training']['weight_decay'],
        "optimizer": config['training']['optimizer'],
        "scheduler": {
            "type": config['training']['scheduler'],
        },
        "gradient_clip_norm": config['training']['gradient_clip_norm'],
        "early_stopping_patience": config['training']['early_stopping_patience'],
        "mixed_precision": {
            "enabled": config['training']['mixed_precision'],
        },
        "checkpoint_dir": "/tmp/checkpoints",
        "log_dir": "/tmp/logs",
        "save_interval_epochs": config['monitoring']['checkpoint_interval'],
        "keep_last_n": 3,
        "log_interval": config['monitoring']['log_interval'],
    }

    trainer = TeacherTrainer(model, loss_fn, trainer_config, device=str(device))
    print("✅ Trainer created")

    # =========================================================================
    # STEP 7: Run Training with Progress Logging
    # =========================================================================
    print("\n[7/10] Starting training...")
    print(f"Training for {config['training']['epochs']} epochs...")
    print(f"Checkpoint interval: every {config['monitoring']['checkpoint_interval']} epochs")
    print("Monitor progress at: https://modal.com/apps")
    print()

    # Initialize GCS client for incremental checkpoint uploads
    from google.cloud import storage
    storage_client = storage.Client()
    gcs_bucket = storage_client.bucket("image_detection_b")
    checkpoint_dir = Path("/tmp/checkpoints")
    checkpoint_interval = config['monitoring']['checkpoint_interval']

    start_time = time.time()
    total_epochs = config['training']['epochs']

    try:
        # Manual epoch loop for better progress visibility
        for epoch in range(total_epochs):
            epoch_start = time.time()

            # Print epoch header
            print(f"\n{'='*60}")
            print(f"EPOCH {epoch + 1}/{total_epochs}")
            print(f"{'='*60}")

            # Run single epoch training
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
            print(f"Epoch Time: {epoch_time/60:.1f} min")
            print(f"Elapsed: {elapsed/3600:.1f}h | Remaining: {remaining/3600:.1f}h")

            # Check for best model and save checkpoint
            val_loss = val_metrics.get('loss', float('inf'))
            if val_loss < trainer.best_val_loss:
                trainer.best_val_loss = val_loss
                print(f"✨ New best val_loss: {val_loss:.4f}")

            # Save and upload checkpoint at intervals
            if (epoch + 1) % checkpoint_interval == 0:
                checkpoint_path = checkpoint_dir / f"checkpoint_epoch_{epoch + 1}.pth"
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': trainer.optimizer.state_dict(),
                    'val_loss': val_loss,
                    'best_val_loss': trainer.best_val_loss,
                }, checkpoint_path)
                print(f"💾 Saved checkpoint: {checkpoint_path.name}")

                # Upload to GCS immediately
                blob = gcs_bucket.blob(f"checkpoints/phase2_iqa/{checkpoint_path.name}")
                blob.upload_from_filename(str(checkpoint_path))
                print(f"☁️  Uploaded to GCS: checkpoints/phase2_iqa/{checkpoint_path.name}")

            # Early stopping check
            if hasattr(trainer, 'early_stop') and trainer.early_stop:
                print(f"⚠️  Early stopping triggered at epoch {epoch + 1}")
                break

        training_time = time.time() - start_time
        print(f"\n✅ Training completed in {training_time/3600:.2f} hours")
        print(f"Best validation loss: {trainer.best_val_loss:.4f}")

    except Exception as e:
        print(f"\n❌ Training failed at epoch {epoch + 1}: {e}")
        raise

    # =========================================================================
    # STEP 8: Upload Final Checkpoints to GCS
    # =========================================================================
    print("\n[8/10] Uploading final checkpoints to GCS...")

    # Save final model
    final_checkpoint = checkpoint_dir / "checkpoint_final.pth"
    torch.save({
        'epoch': total_epochs,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': trainer.optimizer.state_dict(),
        'best_val_loss': trainer.best_val_loss,
    }, final_checkpoint)

    blob = gcs_bucket.blob(f"checkpoints/phase2_iqa/{final_checkpoint.name}")
    blob.upload_from_filename(str(final_checkpoint))
    print("✅ Uploaded final checkpoint to GCS")

    # =========================================================================
    # STEP 9: Export Model to ONNX
    # =========================================================================
    print("\n[9/10] Exporting model to ONNX...")

    model.eval()
    dummy_input = torch.randn(
        1, 3, config['model']['input_size'], config['model']['input_size']
    ).to(device)

    onnx_path = "/tmp/resnet50_teacher_baseline.onnx"
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )

    print(f"✅ ONNX model saved to {onnx_path}")

    # Upload ONNX model to GCS
    onnx_blob = gcs_bucket.blob("models/phase2_iqa/resnet50_teacher_baseline.onnx")
    onnx_blob.upload_from_filename(onnx_path)
    print("✅ ONNX model uploaded to GCS")

    # =========================================================================
    # STEP 10: Save Training Summary
    # =========================================================================
    print("\n[10/10] Saving training summary...")

    summary = {
        "model": "ResNet-50 Teacher",
        "sprint": "3.5.2",
        "run_type": "baseline",
        "config": config,
        "training_time_hours": training_time / 3600,
        "final_metrics": {
            "best_val_loss": float(trainer.best_val_loss),
            "best_epoch": trainer.epoch,
        },
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
    }

    summary_path = "/tmp/training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    summary_blob = gcs_bucket.blob("models/phase2_iqa/training_summary_baseline.json")
    summary_blob.upload_from_filename(summary_path)
    print("✅ Training summary saved to GCS")

    # =========================================================================
    # Final Report
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ Sprint 3.5.2 Baseline Training Complete!")
    print("=" * 80)
    print(f"Training time: {training_time/3600:.2f} hours")
    print(f"Best validation loss: {trainer.best_val_loss:.4f}")
    print(f"Best epoch: {trainer.epoch}")
    print()
    print("Artifacts saved to GCS:")
    print(f"  - Checkpoints: gs://{bucket_name}/checkpoints/phase2_iqa/")
    print(f"  - ONNX model: gs://{bucket_name}/models/phase2_iqa/resnet50_teacher_baseline.onnx")
    print(f"  - Summary: gs://{bucket_name}/models/phase2_iqa/training_summary_baseline.json")
    print()
    print("Next steps (Sprint 3.5.3):")
    print("  1. Download and analyze training curves")
    print("  2. Evaluate on test set")
    print("  3. Identify areas for hyperparameter tuning")
    print("=" * 80)


@stub.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    print("Starting Phase 2 IQA Baseline Training (Sprint 3.5.2)...")
    print("Monitor progress at: https://modal.com/apps")
    print("Stream logs: modal app logs iqa-phase2-training --follow")
    print()

    # Run training (will block until complete, but background bash keeps it alive)
    train_iqa.remote()

    print("\n✅ Training job completed!")
    print("Check Modal dashboard for final results: https://modal.com/apps")


if __name__ == "__main__":
    # Allow running locally for testing
    print("Use: modal run modal/train_phase2_iqa.py")
