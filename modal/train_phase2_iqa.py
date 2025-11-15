"""Phase 2 IQA Training on Modal.

Multi-label CNN for Image Quality Assessment using ResNet18.

Model: ResNet18 (11.7M params)
Dataset: 50k document images with weak supervision labels
Task: Multi-label classification (6 quality issues)

Usage:
    modal run modal/train_phase2_iqa.py

Monitor:
    https://modal.com/apps

Architecture Decision: ADR-034 - ResNet18 for Phase 2 IQA
Supersedes: ADR-025 (MobileNetV3-Small, Colab constraints)
"""
# ruff: noqa: T201
# bandit: noqa: B108

import yaml

import modal

# Create Modal app
stub = modal.App("iqa-phase2-training")

# Define container image with all dependencies
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
    "pillow>=10.0.0",
    "opencv-python-headless>=4.8.0",
    "tqdm>=4.65.0",
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
    """Main training function - runs to completion without session timeouts."""
    import base64
    import os

    import timm
    import torch
    import torch.optim as optim
    from google.cloud import storage

    print("=" * 60)
    print("Phase 2 IQA Training - Modal (ResNet18)")
    print("=" * 60)
    print("Model: ResNet18 (ADR-034)")
    print("Previous: MobileNetV3-Small (ADR-025)")
    print("Reason: +3-4% mAP improvement for document IQA")
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

    # Set environment variable for GCS client
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print("✅ GCS credentials configured")

    # Load configuration from GCS
    print("\n[1/8] Loading configuration from GCS...")
    client = storage.Client()
    bucket = client.bucket("image_detection_b")

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

    # TODO: Download all image files (implement batched parallel download)
    print("TODO: Implement full dataset download (images)")

    # Create model - ResNet18 for IQA (ADR-034)
    print("\n[3/8] Creating ResNet18 model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Use ResNet18 from timm (supports pretrained ImageNet weights)
    model = timm.create_model(
        "resnet18",  # Changed from MobileNetV3-Small to ResNet18 (ADR-034)
        pretrained=True,
        num_classes=6,  # 6 quality issues: noise, blur, skew, perspective, low_contrast, orientation
    )
    model = model.to(device)

    num_params = sum(p.numel() for p in model.parameters())
    print(f"✅ ResNet18 loaded")
    print(f"   Parameters: {num_params:,} (11.7M)")
    print(f"   Pretrained: ImageNet1K_V1")
    print(f"   Output: 6-class multi-label")

    # Create optimizer - AdamW for ResNet18
    print("\n[4/8] Setting up optimizer and scheduler...")
    # ResNet18 benefits from slightly lower LR and higher weight decay
    optimizer = optim.AdamW(
        model.parameters(),
        lr=5e-5,  # Lower LR for ResNet18 (11.7M params vs 2.9M MobileNetV3)
        weight_decay=1e-4,  # Higher weight decay for regularization
        betas=(0.9, 0.999),
    )

    # Cosine annealing with warmup
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=30, eta_min=1e-6
    )

    print(f"✅ Optimizer: AdamW (lr=5e-5, weight_decay=1e-4)")
    print(f"✅ Scheduler: CosineAnnealingLR (30 epochs)")

    # TODO: Create data loaders
    print("\n[5/8] Creating data loaders...")
    print("TODO: Implement PyTorch DataLoader with Albumentations augmentation")

    # Training loop
    print("\n[6/8] Starting training...")
    for epoch in range(config["training"]["epochs"]):
        print(f"\nEpoch {epoch + 1}/{config['training']['epochs']}")

        # TODO: Implement training loop
        # - Forward pass
        # - Loss calculation
        # - Backward pass
        # - Optimizer step

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
    checkpoint_blob.upload_from_filename("/tmp/checkpoint.pth")

    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print("=" * 60)
    print("Model saved to: gs://image_detection_b/models/phase2_iqa/best_model.onnx")
    print(
        "Download with: gsutil cp gs://image_detection_b/models/phase2_iqa/best_model.onnx models/"
    )


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
