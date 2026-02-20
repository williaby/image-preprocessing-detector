# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Phase 3 DocLayout-YOLO Training on Modal.

Layout Detection (tables, images, handwriting, formulas) using DocLayout-YOLO.
DocLayout-YOLO is based on YOLOv10 with document-specific optimizations.

Reference: https://github.com/opendatalab/DocLayout-YOLO

Model Selection:
    Models are configured in: configs/models/doclayout_yolo.yaml
    Change `active_model` to switch between:
    - docstructbench: General-purpose (default)
    - d4la_scratch: D4LA trained from scratch
    - d4la_pretrained: Best performance (DocSynth300K pre-trained)

Usage:
    modal run modal/train_phase3_doclayout_yolo.py

Monitor:
    https://modal.com/apps
"""

import tempfile
from pathlib import Path
from typing import Any

import yaml

import modal

# Create Modal app
stub = modal.App("layout-phase3-training")

# Define container image with DocLayout-YOLO (YOLOv10-based)
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "doclayout-yolo",
    "torch>=2.1.0",
    "torchvision>=0.16.0",
    "pyyaml>=6.0",
    "google-cloud-storage>=2.10.0",
    "onnx>=1.14.0",
    "huggingface_hub",
)

# GCS credentials
gcs_secret = modal.Secret.from_name("gcs-credentials")


def download_gcs_directory(bucket: Any, prefix: str, destination: Path) -> None:
    """Download all objects under a GCS prefix into a destination directory.

    Uses string slicing on a normalized prefix (with trailing slash) to compute
    relative paths instead of Path.relative_to(), which can raise ValueError when
    blob names share a string prefix but differ at the path-segment level
    (e.g. ".../trainval/..." when prefix is ".../train").
    """
    destination.mkdir(parents=True, exist_ok=True)
    # Normalize prefix to ensure it ends with exactly one slash so that blob
    # names with the same string prefix but different path segments are handled
    # correctly (avoids ValueError from Path.relative_to on mismatched segments).
    normalized_prefix = prefix.rstrip("/") + "/"
    for blob in bucket.list_blobs(prefix=normalized_prefix):
        if blob.name.endswith("/"):
            continue
        if not blob.name.startswith(normalized_prefix):
            continue
        if ".." in blob.name:
            raise ValueError(f"Path traversal detected in blob name: {blob.name}")
        relative_name = blob.name[len(normalized_prefix) :]
        if not relative_name:
            continue
        relative_path = Path(relative_name)
        target_path = (destination / relative_path).resolve()
        if not target_path.is_relative_to(destination.resolve()):
            raise ValueError(f"Path escapes destination: {target_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target_path))


@stub.function(
    image=image,
    gpu="A10",  # A10 recommended (24GB) for DocLayout-YOLO
    cpu=16.0,
    memory=65536,
    timeout=345600,  # 96 hours (4 days) to cover 50-80h training runs
    secrets=[gcs_secret],
)
def train_doclayout_yolo() -> None:
    """Main DocLayout-YOLO training function - runs for days without interruption."""
    import base64
    import os

    from doclayout_yolo import YOLOv10
    from google.cloud import storage

    print("=" * 60)
    print("Phase 3 DocLayout-YOLO Layout Detection Training - Modal")
    print("=" * 60)

    base_tmp_dir = Path(tempfile.gettempdir()) / "layout_phase3"
    data_dir = base_tmp_dir / "data"
    runs_dir = base_tmp_dir / "runs"
    base_tmp_dir.mkdir(parents=True, exist_ok=True)

    # Setup GCS credentials from base64-encoded secret
    print("\n[0/6] Setting up GCS credentials...")
    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        raise ValueError("GCP_SA_KEY environment variable not found in Modal secret")

    # Decode base64 and write to temp file for GCS client
    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")
    credentials_path = base_tmp_dir / "gcp-sa-key.json"
    with open(credentials_path, "w") as f:
        f.write(gcp_sa_key_json)

    # Set environment variable for GCS client
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
    print("✅ GCS credentials configured")

    # Load configuration from GCS
    print("\n[1/6] Loading configuration from GCS...")
    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    # Load central model config (single source of truth for model selection)
    model_config_blob = bucket.blob("configs/models/doclayout_yolo.yaml")
    model_config_yaml = model_config_blob.download_as_text()
    model_config = yaml.safe_load(model_config_yaml)

    # Get active model from central config
    active_model_key = model_config["active_model"]
    active_model = model_config["models"][active_model_key]

    print(f"Active model: {active_model_key}")
    print(f"HuggingFace ID: {active_model['huggingface_id']}")
    print(f"Recommended image size: {active_model['recommended_image_size']}")

    # Load platform-specific training config
    config_blob = bucket.blob("configs/modal_phase3_doclayout_yolo.yaml")
    config_yaml = config_blob.download_as_text()
    config = yaml.safe_load(config_yaml)

    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Epochs: {config['training']['epochs']}")

    # Download dataset.yaml from GCS
    print("\n[2/6] Downloading dataset.yaml from GCS...")
    data_dir.mkdir(parents=True, exist_ok=True)

    dataset_yaml_blob = bucket.blob("datasets/layout_phase3/dataset.yaml")
    dataset_yaml_blob.download_to_filename(str(data_dir / "dataset.yaml"))

    # Download dataset to local cache (you'll need to implement full download)
    print("\n[3/6] Downloading dataset from GCS to local cache...")
    download_gcs_directory(bucket, "datasets/layout_phase3/train", data_dir / "train")
    download_gcs_directory(bucket, "datasets/layout_phase3/val", data_dir / "val")

    # Initialize DocLayout-YOLO model from Hugging Face
    print("\n[4/6] Initializing DocLayout-YOLO model...")

    # Use model from central config (single source of truth)
    pretrained_model = active_model["huggingface_id"]
    model = YOLOv10.from_pretrained(pretrained_model)

    # Use image size from central config (model-specific recommendation)
    input_size = active_model["recommended_image_size"]

    print(f"Pre-trained model: {pretrained_model}")
    print(f"Input size: {input_size}")
    print(f"Classes: {config['model']['num_classes']}")

    # Train model
    print("\n[5/6] Starting training...")
    print("This will run for 50-80 hours - no session timeouts!")

    results = model.train(
        data=str(data_dir / "dataset.yaml"),
        epochs=config["training"]["epochs"],
        batch=config["training"]["batch_size"],
        imgsz=input_size,  # From central model config
        device=0,  # GPU 0
        workers=config["data"]["num_workers"],
        optimizer=config["training"]["optimizer"],
        lr0=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
        warmup_epochs=config["training"]["warmup_epochs"],
        amp=config["training"]["mixed_precision"],
        save_period=config["monitoring"]["save_period"],
        project=str(runs_dir),
        name="layout_detection",
    )

    print("\n✅ Training complete!")
    print(f"Best mAP@0.5: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")

    # Export to ONNX
    print("\n[6/6] Exporting to ONNX...")
    onnx_path = model.export(format="onnx", imgsz=input_size)

    # Upload trained model to GCS
    print("\nUploading model to GCS...")

    # Upload ONNX model
    model_blob = bucket.blob("models/phase3_doclayout_yolo/best_model.onnx")
    model_blob.upload_from_filename(onnx_path)

    # Upload PyTorch checkpoint
    checkpoint_blob = bucket.blob("models/phase3_doclayout_yolo/best.pt")
    checkpoint_blob.upload_from_filename(runs_dir / "layout_detection/weights/best.pt")

    print("\n" + "=" * 60)
    print("✅ DocLayout-YOLO training complete!")
    print("=" * 60)
    print("Model saved to: gs://image_detection_b/models/phase3_doclayout_yolo/")
    print(
        "Download with: gsutil cp gs://image_detection_b/models/phase3_doclayout_yolo/best_model.onnx models/"
    )


@stub.local_entrypoint()
def main() -> None:
    """Entry point when running via `modal run`."""
    print("Starting Phase 3 DocLayout-YOLO training on Modal...")
    print("Monitor progress at: https://modal.com/apps")
    print()

    train_doclayout_yolo.remote()

    print("\n✅ Training job submitted successfully!")
    print("Check Modal dashboard for progress: https://modal.com/apps")


if __name__ == "__main__":
    print("Use: modal run modal/train_phase3_doclayout_yolo.py")
