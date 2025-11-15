# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 2 IQA Training on Modal - ResNet Teacher-Student Architecture.

Multi-label CNN for Image Quality Assessment (Project A - RAG Pipeline).

This trains ML models to detect image quality issues (noise, blur, skew,
perspective, low contrast, orientation) for use in Document Quality Score (DQS)
calculation and pre-OCR risk assessment.

**Architecture Context:**
- Part of Project A (this repo) in the RAG Pipeline architecture
- Outputs feed into DQS calculation and routing recommendations
- NOT for layout detection (that's Project B - ocr-orchestrator)

**Teacher-Student Knowledge Distillation:**
- Teacher: ResNet-50 (high-capacity, selective inference on difficult cases)
- Student: ResNet-18 (production default, fast inference)
- Training Process:
  1. Train ResNet-50 teacher on full IQA dataset
  2. Distill knowledge to ResNet-18 student using soft labels
  3. Export both models (ONNX + TorchScript)
  4. Validate on OHR-Bench (document-specific IQA benchmark)

Usage:
    modal run modal/train_phase2_iqa.py

Monitor:
    https://modal.com/apps

Models:
    Teacher (ResNet-50): High accuracy, selective inference only
    Student (ResNet-18): Production default, optimized for CPU/GPU

NOTE: This script placeholder needs full implementation for teacher-student training.
      Current implementation is for single-model training (legacy MobileNetV3).
      See configs/modal_phase2_iqa.yaml for updated architecture configuration.
"""
# ruff: noqa: T201, S108, PTH101, PTH103
# Justification: Modal training script uses print for progress logging and /tmp for container-local storage
# mypy: ignore-errors
# Justification: Modal training placeholder script with incomplete implementation

import yaml  # type: ignore[import-untyped]

import modal

# Create Modal app
stub = modal.App("iqa-phase2-training")

# Define container image
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch>=2.1.0",
    "torchvision>=0.16.0",
    "timm>=0.9.0",
    "albumentations>=1.3.0",
    "tensorboard>=2.14.0",
    "scikit-learn>=1.3.0",
    "pyyaml>=6.0",
    "google-cloud-storage>=2.10.0",
    "onnx>=1.14.0",
)

# GCS credentials
gcs_secret = modal.Secret.from_name("gcs-credentials")


@stub.function(
    image=image,
    gpu="T4",
    cpu=8.0,
    memory=32768,
    timeout=86400,  # 24 hours
    secrets=[gcs_secret],
)
def train_iqa():
    """Main training function - ResNet teacher-student with knowledge distillation.

    NOTE: Current implementation is placeholder - needs update for:
    - ResNet-50 teacher training
    - ResNet-18 student distillation
    - Selective inference configuration
    - Device priority logic

    TODO: Implement full teacher-student training loop (Phase 2 implementation).
    """
    import base64
    import os

    import timm
    import torch
    import torch.optim as optim
    from google.cloud import storage

    print("=" * 60)
    print("Phase 2 IQA Training - Modal (Project A)")
    print("=" * 60)
    print("Training ML models for Image Quality Assessment")
    print("Outputs will be used for DQS calculation and routing metadata")
    print("=" * 60)

    # Setup GCS credentials from base64-encoded secret
    print("\n[0/8] Setting up GCS credentials...")
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        raise ValueError("GCP_SA_KEY environment variable not found in Modal secret")

    # Decode base64 and write to temp file for GCS client
    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")
    credentials_path = "/tmp/gcp-sa-key.json"
    with open(credentials_path, "w") as f:
        f.write(gcp_sa_key_json)

    # Set restrictive permissions (owner-only read/write)
    os.chmod(credentials_path, 0o600)

    # Set environment variable for GCS client
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print("✅ GCS credentials configured")

    # Load configuration from GCS
    print("\n[1/8] Loading configuration from GCS...")
    # Use environment variable for bucket name (defaults to image_detection_b)
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "image_detection_b")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    config_blob = bucket.blob("configs/modal_phase2_iqa.yaml")
    config_yaml = config_blob.download_as_text()
    config = yaml.safe_load(config_yaml)

    print(f"Model: {config['model']['architecture']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")

    # Download dataset to local cache (faster than GCS mounting)
    print("\n[2/8] Downloading dataset from GCS to local cache...")
    os.makedirs("/tmp/data", exist_ok=True)

    # Download dataset files (example - you'll need to implement full download)
    print("Downloading train/labels.json...")
    bucket.blob("datasets/iqa_phase2/train/labels.json").download_to_filename(
        "/tmp/data/train_labels.json"
    )

    print("Downloading validation labels...")
    bucket.blob("datasets/iqa_phase2/val/labels.json").download_to_filename(
        "/tmp/data/val_labels.json"
    )

    # NOTE: Image download implementation deferred to dataset preparation phase
    # This infrastructure PR establishes Modal setup; full dataset download
    # will be implemented when Phase 2 dataset generation is complete
    # TODO: Implement batched parallel download of ~35k training images from GCS
    print(
        "⚠️  Image download not yet implemented - deferred to dataset preparation phase"
    )

    # Create model
    print("\n[3/8] Creating model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = timm.create_model(
        config["model"]["architecture"],
        pretrained=config["model"]["pretrained"],
        num_classes=config["model"]["num_classes"],
        drop_rate=config["model"]["dropout"],
    )
    model = model.to(device)

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Create optimizer
    print("\n[4/8] Setting up optimizer and scheduler...")
    optimizer = optim.Adam(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )

    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["training"]["epochs"]
    )

    # NOTE: DataLoader implementation deferred to dataset preparation phase
    # This infrastructure PR establishes Modal GPU setup and GCS integration
    print("\n[5/8] Creating data loaders...")
    print("⚠️  DataLoader not yet implemented - deferred to dataset preparation phase")
    # TODO: Implement PyTorch DataLoader with:
    #   - Albumentations augmentation pipeline
    #   - Multi-label classification support
    #   - Efficient batching for T4 GPU (batch_size=128)

    # NOTE: Training loop implementation deferred to dataset preparation phase
    # Placeholder below demonstrates training structure and checkpoint saving
    print("\n[6/8] Starting training loop (placeholder)...")
    print("TODO: Implement full training loop with:")
    print("  - Multi-label classification (BCEWithLogitsLoss)")
    print("  - Albumentations augmentation pipeline")
    print("  - Per-class metrics (precision, recall, F1, ROC-AUC)")
    print("  - Calibration (ECE < 0.05 target)")
    print("  - Teacher-student training support (optional)")
    print()
    for epoch in range(config["training"]["epochs"]):
        print(f"\nEpoch {epoch + 1}/{config['training']['epochs']}")

        # TODO: Implement training loop
        # - Forward pass with mixed precision (AMP)
        # - BCEWithLogitsLoss for multi-label classification
        # - Backward pass with gradient clipping
        # - Optimizer step (AdamW with cosine annealing)
        # - Validation metrics (mAP, per-class F1)
        # - Temperature scaling for calibration

        # Save checkpoint every 5 epochs
        if (epoch + 1) % config["monitoring"]["checkpoint_interval"] == 0:
            print(f"Saving checkpoint at epoch {epoch + 1}...")
            checkpoint_path = f"/tmp/checkpoint_epoch_{epoch + 1}.pth"
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                },
                checkpoint_path,
            )

            # Upload checkpoint to GCS
            checkpoint_blob = bucket.blob(
                f"checkpoints/phase2_iqa/checkpoint_epoch_{epoch + 1}.pth"
            )
            checkpoint_blob.upload_from_filename(checkpoint_path)
            print("✅ Checkpoint uploaded to GCS")

        scheduler.step()

    # Save final checkpoint
    print("\nSaving final checkpoint...")
    final_checkpoint_path = "/tmp/final_checkpoint.pth"
    torch.save(
        {
            "epoch": config["training"]["epochs"],
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
        },
        final_checkpoint_path,
    )

    # Export to ONNX
    print("\n[7/8] Exporting model to ONNX...")
    model.eval()
    dummy_input = torch.randn(
        1, 3, config["model"]["input_size"], config["model"]["input_size"]
    ).to(device)

    onnx_path = "/tmp/best_model.onnx"
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )

    print(f"ONNX model saved to {onnx_path}")

    # Upload final model to GCS
    print("\n[8/8] Uploading final model to GCS...")
    model_blob = bucket.blob("models/phase2_iqa/best_model.onnx")
    model_blob.upload_from_filename(onnx_path)

    checkpoint_blob = bucket.blob("models/phase2_iqa/best_model.pth")
    checkpoint_blob.upload_from_filename(final_checkpoint_path)

    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print("=" * 60)
    print("Model saved to: gs://image_detection_b/models/phase2_iqa/best_model.onnx")
    print(
        "Download with: gsutil cp gs://image_detection_b/models/phase2_iqa/best_model.onnx models/"
    )
    print()
    print("Next steps:")
    print("1. Validate model metrics (mAP > 0.88, ECE < 0.05)")
    print("2. Integrate with DQS calculation pipeline")
    print("3. (Optional) Train student model for production optimization")
    print("4. Deploy for pre-OCR risk assessment and routing")


@stub.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    print("Starting Phase 2 IQA training on Modal...")
    print("Monitor progress at: https://modal.com/apps")
    print()

    train_iqa.remote()

    print("\n✅ Training job submitted successfully!")
    print("Check Modal dashboard for progress: https://modal.com/apps")


if __name__ == "__main__":
    # Allow running locally for testing
    print("Use: modal run modal/train_phase2_iqa.py")
