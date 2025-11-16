#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 2 IQA Training with GCS Artifact Storage - Example Integration.

This is a reference implementation showing how to integrate the new
GCS artifact storage and metadata generation system with Modal training.

Key Features:
- Automatic run ID generation with timestamps
- Complete metadata generation (commit, dataset, env, config, metrics)
- Structured GCS upload following canonical directory layout
- Reproducibility tracking for all training runs

Usage:
    modal run modal/train_phase2_iqa_example.py

Monitor:
    https://modal.com/apps

After Training:
    # List runs
    python scripts/promote_to_hf.py --list-runs \\
        --model resnet50_teacher

    # Promote to HF Hub
    python scripts/promote_to_hf.py \\
        --model resnet50_teacher \\
        --run-id 2025-11-15T01-20Z_run-abc123 \\
        --hf-repo williaby/doc-preproc-resnet50-teacher \\
        --version v1.0.0
"""
# bandit: noqa: B108
# ruff: noqa: DTZ005

import os
from datetime import datetime

import modal

# Create Modal app
stub = modal.App("iqa-phase2-training-example")

# Define container image with ALL required dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Core ML
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "timm>=0.9.0",
        # Data augmentation
        "albumentations>=1.3.0",
        # Monitoring
        "tensorboard>=2.14.0",
        # ML utils
        "scikit-learn>=1.3.0",
        # Configuration
        "pyyaml>=6.0",
        # GCS integration (REQUIRED for artifact storage)
        "google-cloud-storage>=2.10.0",
        # Export
        "onnx>=1.14.0",
    )
    # Copy source code into container
    .copy_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
    )
)

# GCS credentials (required for artifact upload)
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
    """Main training function with integrated artifact storage."""
    import base64
    import sys

    # Add source to Python path
    sys.path.insert(0, "/root")

    import timm
    import torch
    import torch.optim as optim
    from google.cloud import storage

    # Import our new utilities
    from image_preprocessing_detector.utils import (
        generate_run_id,
        generate_run_metadata,
        upload_run_to_gcs,
    )

    print("=" * 80)
    print("Phase 2 IQA Training - Modal with GCS Artifact Storage")
    print("=" * 80)

    # =========================================================================
    # STEP 1: Setup GCS Credentials
    # =========================================================================
    print("\n[1/9] Setting up GCS credentials...")
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        raise ValueError("GCP_SA_KEY environment variable not found in Modal secret")

    # Decode and save credentials
    import tempfile

    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")

    # Use tempfile for credentials (Modal container is isolated/ephemeral, but use tempfile for security)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
    ) as f:
        f.write(gcp_sa_key_json)
        f.flush()  # Ensure file is written before using f.name
        credentials_path = f.name

    os.chmod(credentials_path, 0o600)  # nosec B103 - Secure permissions for credentials file
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"✅ GCS credentials configured at {credentials_path}")

    # =========================================================================
    # STEP 2: Generate Run ID and Setup Output Directory
    # =========================================================================
    print("\n[2/9] Generating run ID and setting up output directory...")

    # Generate unique run ID with timestamp
    run_id = generate_run_id(prefix="iqa-phase2")
    print(f"Run ID: {run_id}")

    # Create output directory for all artifacts
    output_dir = "/root/output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # =========================================================================
    # STEP 3: Load Configuration
    # =========================================================================
    print("\n[3/9] Loading training configuration...")

    # Training configuration (normally loaded from GCS or YAML)
    config = {
        "model": {
            "architecture": "resnet50",
            "pretrained": True,
            "num_classes": 4,  # [blur, skew, contrast, noise]
            "input_size": 224,
            "dropout": 0.2,
        },
        "training": {
            "batch_size": 128,
            "epochs": 100,
            "learning_rate": 0.001,
            "weight_decay": 1e-4,
            "optimizer": "Adam",
            "scheduler": "CosineAnnealingLR",
        },
        "data": {
            "num_workers": 4,
            "pin_memory": True,
        },
    }

    print(f"Model: {config['model']['architecture']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")

    # =========================================================================
    # STEP 4: Create Model
    # =========================================================================
    print("\n[4/9] Creating model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = timm.create_model(
        config["model"]["architecture"],
        pretrained=config["model"]["pretrained"],
        num_classes=config["model"]["num_classes"],
        drop_rate=config["model"]["dropout"],
    )
    model = model.to(device)

    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {num_params:,}")

    # =========================================================================
    # STEP 5: Setup Optimizer and Scheduler
    # =========================================================================
    print("\n[5/9] Setting up optimizer and scheduler...")

    optimizer = optim.Adam(
        model.parameters(),
        lr=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )

    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["training"]["epochs"]
    )

    # =========================================================================
    # STEP 6: Training Loop (Placeholder)
    # =========================================================================
    print("\n[6/9] Training model...")

    # NOTE: Full training loop implementation deferred to dataset preparation
    # This example shows the checkpoint saving pattern

    start_time = datetime.now()
    best_val_acc = 0.0
    best_epoch = 0

    for epoch in range(config["training"]["epochs"]):
        print(f"\nEpoch {epoch + 1}/{config['training']['epochs']}")

        # TODO: Implement actual training loop
        # - Forward pass
        # - Loss calculation
        # - Backward pass
        # - Optimizer step

        # Simulated metrics for demonstration
        train_loss = 0.15
        val_loss = 0.18
        val_acc = 0.92

        # Track best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch

            # Save best checkpoint
            # nosec B614 - torch.save uses pickle, but saving our own trusted model
            checkpoint_path = f"{output_dir}/model_final.pth"
            torch.save(model.state_dict(), checkpoint_path)  # nosec
            print(f"✅ Saved best model (acc: {val_acc:.3f})")

        # Save periodic checkpoints
        if (epoch + 1) % 20 == 0:
            # nosec B614 - torch.save uses pickle, but saving our own trusted model
            checkpoint_path = f"{output_dir}/model_epoch_{epoch + 1}.pth"
            torch.save(  # nosec
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "val_acc": val_acc,
                },
                checkpoint_path,
            )
            print(f"✅ Saved checkpoint at epoch {epoch + 1}")

        scheduler.step()

    training_time = (datetime.now() - start_time).total_seconds()
    print(
        f"\n✅ Training complete! Best accuracy: {best_val_acc:.3f} at epoch {best_epoch}"
    )

    # =========================================================================
    # STEP 7: Generate Metadata Files
    # =========================================================================
    print("\n[7/9] Generating metadata files...")

    # Collect final metrics
    metrics = {
        "final_train_loss": train_loss,
        "final_val_loss": val_loss,
        "val_accuracy": best_val_acc,
        "val_macro_f1": 0.91,  # Would be calculated from validation
        "best_epoch": best_epoch,
        "total_epochs": config["training"]["epochs"],
        "training_time_seconds": training_time,
        "num_parameters": num_params,
    }

    # Generate all required metadata files
    metadata_files = generate_run_metadata(
        output_dir=output_dir,
        config=config,
        dataset_version="v1.2.0",  # From environment or config
        metrics=metrics,
        dataset_info={
            "num_train_samples": 35000,
            "num_val_samples": 5000,
            "labels": ["blur", "skew", "contrast", "noise"],
            "created": "2025-11-01T00:00:00Z",
        },
        repo_path="/root",  # Modal workspace
    )

    print(f"✅ Generated {len(metadata_files)} metadata files")
    for name, path in metadata_files.items():
        print(f"   - {name}: {os.path.basename(path)}")

    # =========================================================================
    # STEP 8: Upload Artifacts to GCS
    # =========================================================================
    print("\n[8/9] Uploading artifacts to GCS...")

    gcs_path = upload_run_to_gcs(
        local_dir=output_dir,
        bucket_name="rag-pipeline-models",
        project_name="image-preprocessing-detector",
        model_name="resnet50_teacher",
        run_id=run_id,
        verbose=True,
    )

    print("\n✅ Artifacts uploaded successfully!")
    print(f"GCS path: {gcs_path}")

    # =========================================================================
    # STEP 9: Export to ONNX (Optional)
    # =========================================================================
    print("\n[9/9] Exporting model to ONNX...")

    model.eval()
    dummy_input = torch.randn(
        1, 3, config["model"]["input_size"], config["model"]["input_size"]
    ).to(device)

    onnx_path = f"{output_dir}/best_model.onnx"
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=13,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )

    # Upload ONNX to GCS

    client = storage.Client()
    bucket = client.bucket("rag-pipeline-models")
    blob = bucket.blob(
        f"image-preprocessing-detector/resnet50_teacher/runs/{run_id}/best_model.onnx"
    )
    blob.upload_from_filename(onnx_path)

    print("✅ ONNX model exported and uploaded")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ Training Complete!")
    print("=" * 80)
    print(f"Run ID: {run_id}")
    print(f"Best Accuracy: {best_val_acc:.3f}")
    print(f"Training Time: {training_time:.1f}s")
    print(f"GCS Path: {gcs_path}")
    print()
    print("📋 Next Steps:")
    print("   1. Review metrics in GCS")
    print("   2. Validate model performance")
    print("   3. Promote to HF Hub: python scripts/promote_to_hf.py \\")
    print("         --model resnet50_teacher \\")
    print(f"         --run-id {run_id} \\")
    print("         --hf-repo williaby/doc-preproc-resnet50-teacher \\")
    print("         --version v1.0.0")
    print("=" * 80)

    return {
        "run_id": run_id,
        "gcs_path": gcs_path,
        "best_accuracy": best_val_acc,
        "training_time": training_time,
    }


@stub.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    print("Starting Phase 2 IQA training with GCS artifact storage...")
    print("Monitor progress at: https://modal.com/apps")
    print()

    result = train_iqa.remote()

    print("\n✅ Training job completed!")
    print(f"Run ID: {result['run_id']}")
    print(f"GCS Path: {result['gcs_path']}")
    print(f"Best Accuracy: {result['best_accuracy']:.3f}")


if __name__ == "__main__":
    print("Use: modal run modal/train_phase2_iqa_example.py")
