"""Modal Application Definition for Image Detection Project.

Provides GPU training functions for Phase 2 (IQA) and Phase 3 (Layout Detection).

Usage:
    modal run modal/app.py::hello_gpu        # Test GPU access
    modal run modal/train_phase2_iqa.py      # Run Phase 2 training
    modal run modal/train_phase3_yolov8.py   # Run Phase 3 training
"""
# ruff: noqa: T201

import modal

# Create Modal app
stub = modal.App("image-detection")

# Define common ML image with all dependencies
ml_image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch>=2.1.0",
    "torchvision>=0.16.0",
    "timm>=0.9.0",
    "ultralytics>=8.0.0",  # YOLOv8
    "albumentations>=1.3.0",
    "tensorboard>=2.14.0",
    "scikit-learn>=1.3.0",
    "pyyaml>=6.0",
    "google-cloud-storage>=2.10.0",
    "onnx>=1.14.0",
    "onnxruntime>=1.16.0",
)

# GCS credentials secret (base64-encoded service account key)
# User creates this with: modal secret create gcs-credentials GCP_SA_KEY="<base64-string>"
gcs_secret = modal.Secret.from_name("gcs-credentials")

# Persistent storage volumes for caching
dataset_volume = modal.NetworkFileSystem.from_name("datasets", create_if_missing=True)
checkpoint_volume = modal.NetworkFileSystem.from_name(
    "checkpoints", create_if_missing=True
)


@stub.function(
    image=ml_image,
    gpu="T4",
    timeout=3600,
    secrets=[gcs_secret],
)
def hello_gpu():
    """Test GPU access - verify Modal setup is working."""
    import torch

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ Hello from Modal GPU: {gpu_name}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"PyTorch Version: {torch.__version__}")
        return {"gpu": gpu_name, "cuda": torch.version.cuda}
    print("❌ No GPU available")
    return {"error": "No GPU available"}


if __name__ == "__main__":
    # Run hello_gpu test when app is run directly
    with stub.run():
        result = hello_gpu.remote()
        print(f"Result: {result}")
