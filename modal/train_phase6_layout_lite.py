# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 6 Layout-Lite Training on Modal - YOLOv8 Coarse Region Detection.

Coarse page-level layout attributes (NOT full semantic layout):
- Coarse regions: text_block, table_block, figure_block (3 classes)
- Page attributes: layout_type, has_tables, has_figures, etc.

NOTE: Full DocLayNet-style semantic layout detection is Project B's responsibility.
      This phase provides only coarse layout attributes for routing decisions.

Usage:
    modal run modal/train_phase6_layout_lite.py

Monitor:
    https://modal.com/apps
"""
# Justification: Modal training script uses print for progress logging and /tmp for container-local storage
# mypy: ignore-errors
# Justification: Modal training placeholder script with incomplete implementation

import yaml  # type: ignore[import-untyped]

import modal

# Create Modal app
stub = modal.App("layout-phase3-training")

# Define container image with YOLOv8
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "ultralytics>=8.0.0",
    "torch>=2.1.0",
    "torchvision>=0.16.0",
    "pyyaml>=6.0",
    "google-cloud-storage>=2.10.0",
    "onnx>=1.14.0",
)

# GCS credentials
gcs_secret = modal.Secret.from_name("gcs-credentials")


@stub.function(
    image=image,
    gpu="A10",  # A10 recommended (24GB) for YOLOv8
    cpu=16.0,
    memory=65536,
    timeout=259200,  # 72 hours (3 days)
    secrets=[gcs_secret],
)
def train_yolov8():
    """Main YOLOv8 training function - runs for days without interruption."""
    import base64
    import os

    from google.cloud import storage
    from ultralytics import YOLO

    print("=" * 60)
    print("Phase 3 YOLOv8 Layout Detection Training - Modal")
    print("=" * 60)

    # Setup GCS credentials from base64-encoded secret
    print("\n[0/6] Setting up GCS credentials...")
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        raise ValueError("GCP_SA_KEY environment variable not found in Modal secret")

    # Decode base64 and write to temp file for GCS client
    import tempfile

    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")

    # Use tempfile for credentials (Modal container is isolated/ephemeral, but use tempfile for security)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
    ) as f:
        f.write(gcp_sa_key_json)
        f.flush()  # Ensure file is written before using f.name
        credentials_path = f.name

    # Set restrictive permissions (owner-only read/write)
    os.chmod(credentials_path, 0o600)  # nosec B103 - Secure permissions for credentials file

    # Set environment variable for GCS client
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"✅ GCS credentials configured at {credentials_path}")

    # Create temporary directories for data and runs
    data_dir = tempfile.mkdtemp(prefix="yolo-data-")
    runs_dir = tempfile.mkdtemp(prefix="yolo-runs-")
    print(f"Data directory: {data_dir}")
    print(f"Runs directory: {runs_dir}")

    # Load configuration from GCS
    print("\n[1/6] Loading configuration from GCS...")
    # Use environment variable for bucket name (defaults to image_detection_b)
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "image_detection_b")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    config_blob = bucket.blob("configs/modal_phase3_yolov8.yaml")
    config_yaml = config_blob.download_as_text()
    config = yaml.safe_load(config_yaml)

    print(f"Model: {config['model']['architecture']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")

    # Download dataset.yaml from GCS
    print("\n[2/6] Downloading dataset.yaml from GCS...")

    dataset_yaml_blob = bucket.blob("datasets/layout_phase3/dataset.yaml")
    dataset_yaml_blob.download_to_filename(f"{data_dir}/dataset.yaml")

    # NOTE: Dataset download implementation deferred to Phase 3 dataset preparation
    # This infrastructure PR establishes Modal + GCS workflow
    print("\n[3/6] Downloading dataset from GCS to local cache...")
    print(
        "⚠️  Dataset download not yet implemented - deferred to Phase 3 dataset preparation"
    )
    # TODO: Implement full dataset download (gsutil or google-cloud-storage client)
    #   Example: gsutil -m cp -r gs://image_detection_b/datasets/layout_phase3/train {data_dir}/
    #   Verify directories exist before training: {data_dir}/train, {data_dir}/val
    # TODO: Add FileNotFoundError check to prevent silent failures

    # Initialize YOLOv8 model
    print("\n[4/6] Initializing YOLOv8 model...")
    model = YOLO(f"{config['model']['architecture']}.pt")

    print(f"Model: {config['model']['architecture']}")
    print(f"Classes: {config['model']['num_classes']}")

    # Train model
    print("\n[5/6] Starting training...")
    print("This will run for 50-80 hours - no session timeouts!")

    results = model.train(
        data=f"{data_dir}/dataset.yaml",
        epochs=config["training"]["epochs"],
        batch=config["training"]["batch_size"],
        imgsz=config["model"]["input_size"],
        device=0,  # GPU 0
        workers=config["data"]["num_workers"],
        optimizer=config["training"]["optimizer"],
        lr0=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
        warmup_epochs=config["training"]["warmup_epochs"],
        amp=config["training"]["mixed_precision"],
        save_period=config["monitoring"]["save_period"],
        project=runs_dir,
        name="layout_detection",
    )

    print("\n✅ Training complete!")
    print(f"Best mAP@0.5: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")

    # Export to ONNX
    print("\n[6/6] Exporting to ONNX...")
    onnx_path = model.export(format="onnx", imgsz=config["model"]["input_size"])

    # Upload trained model to GCS
    print("\nUploading model to GCS...")

    # Upload ONNX model
    model_blob = bucket.blob("models/phase3_yolov8/best_model.onnx")
    model_blob.upload_from_filename(onnx_path)

    # Upload PyTorch checkpoint
    checkpoint_blob = bucket.blob("models/phase3_yolov8/best.pt")
    checkpoint_path = f"{runs_dir}/layout_detection/weights/best.pt"
    checkpoint_blob.upload_from_filename(checkpoint_path)

    print("\n" + "=" * 60)
    print("✅ YOLOv8 training complete!")
    print("=" * 60)
    print("Model saved to: gs://image_detection_b/models/phase3_yolov8/")
    print(
        "Download with: gsutil cp gs://image_detection_b/models/phase3_yolov8/best_model.onnx models/"
    )


@stub.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    print("Starting Phase 3 YOLOv8 training on Modal...")
    print("Monitor progress at: https://modal.com/apps")
    print()

    train_yolov8.remote()

    print("\n✅ Training job submitted successfully!")
    print("Check Modal dashboard for progress: https://modal.com/apps")


if __name__ == "__main__":
    print("Use: modal run modal/train_phase3_yolov8.py")
