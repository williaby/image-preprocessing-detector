# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal Application for Traditional IQA Model Benchmarking on DIQA-5000.

Benchmarks CNN-based models that directly regress quality scores from image features.

Available Benchmarks:
    - ResNet50-ImageNet-IQA: ResNet50 backbone + IQA head
    - ResNet34-ImageNet-IQA: ResNet34 backbone + IQA head
    - ResNet18-ImageNet-IQA: ResNet18 backbone + IQA head
    - ConvNeXt-Tiny-ImageNet-IQA: ConvNeXt-Tiny backbone + IQA head
    - EfficientNet-B4-ImageNet-IQA: EfficientNet-B4 backbone + IQA head
    - Swin-Tiny-ImageNet-IQA: Swin Transformer Tiny + IQA head
    - CLIP-ViT-B-32-IQA: CLIP-based quality assessment via text prompts
    - PyIQA metrics: musiq, niqe, brisque, clipiqa, maniqa, topiq_nr

Usage:
    # Run individual benchmarks
    modal run modal/arena_iqa_benchmark.py::run_resnet50_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_resnet34_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_resnet18_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_convnext_tiny_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_efficientnet_b4_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_swin_tiny_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_clip_iqa_benchmark --num-samples 10
    modal run modal/arena_iqa_benchmark.py::run_pyiqa_benchmark --metric-name musiq --num-samples 10

    # Run full dataset (1000 samples, detached)
    modal run -d modal/arena_iqa_benchmark.py::run_resnet50_benchmark
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import modal

# Import shared utilities
from modal.shared import (
    DATASET_CACHE_DIR,
    compute_metrics,
    download_dataset_from_gcs,
    gcs_secret,
    print_results,
    setup_gcs_credentials,
)
from modal.shared import (
    arena_data_volume as data_volume,
)
from modal.shared import (
    arena_model_volume as model_volume,
)
from modal.shared import (
    load_diqa5000_dataset as load_dataset,
)

# Create Modal app
app = modal.App("arena-iqa-benchmark")


# =============================================================================
# ResNet50-based IQA Benchmark (Pre-trained on ImageNet, fine-tuned for IQA)
# =============================================================================

resnet_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "timm>=0.9.0",
        "numpy>=1.24.0",
    )
)


@app.function(
    image=resnet_image,
    gpu="T4",  # Smaller model, T4 is sufficient
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_resnet50_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with ResNet50-based IQA model.

    Uses a ResNet50 backbone to extract features and regress quality scores.
    This is a simple baseline that predicts overall quality only.
    """
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import ResNet50_Weights, resnet50

    model_id = "ResNet50-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # Create simple IQA model using ResNet50 features
    print("\nLoading model: ResNet50 + IQA Head")
    model_start = time.time()

    class ResNetIQA(nn.Module):
        """Simple ResNet50-based IQA model."""

        def __init__(self):
            super().__init__()
            # Load pretrained ResNet50
            self.backbone = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
            # Replace classifier with IQA head (3 outputs: overall, sharpness, color)
            num_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Sequential(
                nn.Linear(num_features, 512),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(512, 3),  # 3 quality dimensions
                nn.Sigmoid(),  # Output in [0, 1], scale to [1, 5]
            )

        def forward(self, x):
            out = self.backbone(x)
            # Scale from [0, 1] to [1, 5]
            return out * 4.0 + 1.0

    model = ResNetIQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Image preprocessing (ImageNet normalization)
    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and preprocess image
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# ResNet34-based IQA Benchmark
# =============================================================================


@app.function(
    image=resnet_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_resnet34_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with ResNet34-based IQA model."""
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import ResNet34_Weights, resnet34

    model_id = "ResNet34-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    print("\nLoading model: ResNet34 + IQA Head")
    model_start = time.time()

    class ResNet34IQA(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = resnet34(weights=ResNet34_Weights.IMAGENET1K_V1)
            num_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Sequential(
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(256, 3),
                nn.Sigmoid(),
            )

        def forward(self, x):
            out = self.backbone(x)
            return out * 4.0 + 1.0

    model = ResNet34IQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# ResNet18-based IQA Benchmark
# =============================================================================


@app.function(
    image=resnet_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_resnet18_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with ResNet18-based IQA model."""
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import ResNet18_Weights, resnet18

    model_id = "ResNet18-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    print("\nLoading model: ResNet18 + IQA Head")
    model_start = time.time()

    class ResNet18IQA(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
            num_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Sequential(
                nn.Linear(num_features, 128),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(128, 3),
                nn.Sigmoid(),
            )

        def forward(self, x):
            out = self.backbone(x)
            return out * 4.0 + 1.0

    model = ResNet18IQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# ConvNeXt-Tiny IQA Benchmark
# =============================================================================


@app.function(
    image=resnet_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_convnext_tiny_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with ConvNeXt-Tiny IQA model."""
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny

    model_id = "ConvNeXt-Tiny-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    print("\nLoading model: ConvNeXt-Tiny + IQA Head")
    model_start = time.time()

    class ConvNeXtTinyIQA(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
            num_features = self.backbone.classifier[2].in_features
            self.backbone.classifier[2] = nn.Sequential(
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(256, 3),
                nn.Sigmoid(),
            )

        def forward(self, x):
            out = self.backbone(x)
            return out * 4.0 + 1.0

    model = ConvNeXtTinyIQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# EfficientNet-B4 IQA Benchmark
# =============================================================================


@app.function(
    image=resnet_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_efficientnet_b4_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with EfficientNet-B4 IQA model."""
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import EfficientNet_B4_Weights, efficientnet_b4

    model_id = "EfficientNet-B4-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    print("\nLoading model: EfficientNet-B4 + IQA Head")
    model_start = time.time()

    class EfficientNetB4IQA(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = efficientnet_b4(
                weights=EfficientNet_B4_Weights.IMAGENET1K_V1
            )
            num_features = self.backbone.classifier[1].in_features
            self.backbone.classifier[1] = nn.Sequential(
                nn.Linear(num_features, 512),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(512, 3),
                nn.Sigmoid(),
            )

        def forward(self, x):
            out = self.backbone(x)
            return out * 4.0 + 1.0

    model = EfficientNetB4IQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # EfficientNet-B4 expects 380x380 input
    preprocess = transforms.Compose(
        [
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# Swin-Tiny IQA Benchmark
# =============================================================================


@app.function(
    image=resnet_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_swin_tiny_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with Swin-Tiny IQA model."""
    import torch
    import torch.nn as nn
    from PIL import Image
    from torchvision import transforms
    from torchvision.models import Swin_T_Weights, swin_t

    model_id = "Swin-Tiny-ImageNet-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    print("\nLoading model: Swin-Tiny + IQA Head")
    model_start = time.time()

    class SwinTinyIQA(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = swin_t(weights=Swin_T_Weights.IMAGENET1K_V1)
            num_features = self.backbone.head.in_features
            self.backbone.head = nn.Sequential(
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(256, 3),
                nn.Sigmoid(),
            )

        def forward(self, x):
            out = self.backbone(x)
            return out * 4.0 + 1.0

    model = SwinTinyIQA().to(device)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Swin-T expects 224x224 input
    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                output = model(input_tensor)
                scores = output.squeeze().cpu().numpy()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = {
                "overall": float(scores[0]),
                "sharpness": float(scores[1]),
                "color": float(scores[2]),
            }

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# CLIP-IQA Benchmark (CLIP-based quality assessment)
# =============================================================================

clip_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "transformers>=4.46.0",
        "open-clip-torch>=2.24.0",
    )
)


@app.function(
    image=clip_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_clip_iqa_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with CLIP-based IQA.

    Uses CLIP to compute similarity between image and quality-related text prompts.
    """
    import open_clip
    import torch
    from PIL import Image

    model_id = "CLIP-ViT-B-32-IQA"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # Load CLIP model
    print("\nLoading model: CLIP ViT-B-32")
    model_start = time.time()

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    model = model.to(device)
    model.eval()

    tokenizer = open_clip.get_tokenizer("ViT-B-32")

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Quality prompts for CLIP
    quality_prompts = {
        "overall": [
            "a high quality document image",
            "a low quality document image",
        ],
        "sharpness": [
            "a sharp clear document image",
            "a blurry unfocused document image",
        ],
        "color": [
            "a document with accurate colors",
            "a document with distorted faded colors",
        ],
    }

    # Pre-encode text prompts
    text_features = {}
    for dim, prompts in quality_prompts.items():
        tokens = tokenizer(prompts).to(device)
        with torch.inference_mode():
            features = model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
        text_features[dim] = features

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and preprocess image
            image = Image.open(sample["image_path"]).convert("RGB")
            image_input = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                image_features = model.encode_image(image_input)
                image_features = image_features / image_features.norm(
                    dim=-1, keepdim=True
                )

            predicted = {}
            for dim, txt_feat in text_features.items():
                # Compute similarity with high/low quality prompts
                similarity = (image_features @ txt_feat.T).squeeze()
                # Convert to probability of being high quality
                probs = torch.softmax(similarity * 100, dim=0)
                high_quality_prob = probs[0].item()
                # Scale to [1, 5]
                predicted[dim] = high_quality_prob * 4.0 + 1.0

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# PyIQA Benchmark (Collection of traditional IQA metrics)
# =============================================================================

pyiqa_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "pyiqa>=0.1.10",
        "opencv-python-headless>=4.8.0",
    )
)


@app.function(
    image=pyiqa_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_pyiqa_benchmark(
    metric_name: str = "musiq", num_samples: int = 0
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with PyIQA metrics.

    Available metrics: musiq, niqe, brisque, clipiqa, maniqa, topiq_nr, etc.
    """
    import pyiqa
    import torch
    from PIL import Image
    from torchvision import transforms

    model_id = f"PyIQA-{metric_name}"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # Load PyIQA metric
    print(f"\nLoading metric: {metric_name}")
    model_start = time.time()

    iqa_metric = pyiqa.create_metric(metric_name, device=device)

    # Check if metric is lower-better or higher-better
    lower_better = (
        iqa_metric.lower_better if hasattr(iqa_metric, "lower_better") else False
    )
    print(f"Metric type: {'lower is better' if lower_better else 'higher is better'}")

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Image preprocessing
    preprocess = transforms.Compose(
        [
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
        ]
    )

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []
    raw_scores = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and preprocess image
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                score = iqa_metric(input_tensor).item()

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)
            raw_scores.append(score)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "raw_score": score,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "raw_score": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Normalize scores to [1, 5] range
    successful_scores = [
        r["raw_score"] for r in results if r["success"] and r["raw_score"] is not None
    ]
    if successful_scores:
        min_score = min(successful_scores)
        max_score = max(successful_scores)
        score_range = max_score - min_score if max_score > min_score else 1.0

        for r in results:
            if r["success"] and r["raw_score"] is not None:
                normalized = (r["raw_score"] - min_score) / score_range
                if lower_better:
                    normalized = 1.0 - normalized
                scaled = normalized * 4.0 + 1.0
                r["predicted"] = {
                    "overall": scaled,
                    "sharpness": scaled,  # Single metric applied to all dimensions
                    "color": scaled,
                }
            else:
                r["predicted"] = None

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# Fine-tuned MUSIQ Benchmark (Custom trained on DIQA-5000)
# =============================================================================

finetuned_musiq_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "pyiqa>=0.1.10",
        "opencv-python-headless>=4.8.0",
    )
)


@app.function(
    image=finetuned_musiq_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_finetuned_musiq_benchmark(
    model_version: str = "v1.0.0",
    num_samples: int = 0,
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with fine-tuned MUSIQ model.

    This benchmarks the custom MUSIQ Sharpness Specialist trained on DIQA-5000.
    The model uses MUSIQ backbone with multi-task head for sharpness prediction.

    Args:
        model_version: Model version to load from GCS (default: v1.0.0).
        num_samples: Number of samples to evaluate (0 = all).

    Returns:
        Benchmark metrics and sample results.
    """
    import pyiqa
    import torch
    import torch.nn as nn
    from google.cloud import storage
    from PIL import Image
    from torchvision import transforms

    model_id = f"MUSIQ-Sharpness-Specialist-{model_version}"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # ========== Define Model Architecture ==========
    # Must match training architecture from musiq_wrapper.py

    class MultiTaskHead(nn.Module):
        """Multi-task head for DIQA dimensions."""

        def __init__(
            self, in_features: int = 384, hidden_dim: int = 256, dropout: float = 0.1
        ):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.heads = nn.ModuleDict(
                {
                    "overall": nn.Linear(hidden_dim, 1),
                    "sharpness": nn.Linear(hidden_dim, 1),
                    "color": nn.Linear(hidden_dim, 1),
                }
            )

        def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
            shared = self.shared(features)
            return {
                dim: torch.sigmoid(head(shared).squeeze(-1))
                for dim, head in self.heads.items()
            }

    class MUSIQBackbone(nn.Module):
        """MUSIQ score encoder backbone."""

        def __init__(self, musiq_model: nn.Module):
            super().__init__()
            self._musiq_model = musiq_model
            for param in self._musiq_model.parameters():
                param.requires_grad = False
            self.score_encoder = nn.Sequential(
                nn.Linear(1, 64),
                nn.ReLU(),
                nn.Linear(64, 256),
                nn.ReLU(),
                nn.Linear(256, 384),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            self._musiq_model.eval()
            with torch.no_grad():
                scores = self._musiq_model(x)
            if scores.dim() == 1:
                scores = scores.unsqueeze(1)
            scores = scores / 100.0
            return self.score_encoder(scores)

    class MUSIQMultiTask(nn.Module):
        """Full MUSIQ multi-task model."""

        def __init__(
            self,
            pretrained_musiq: nn.Module,
            hidden_dim: int = 256,
            dropout: float = 0.1,
        ):
            super().__init__()
            self.backbone = MUSIQBackbone(pretrained_musiq)
            self.head = MultiTaskHead(
                in_features=384, hidden_dim=hidden_dim, dropout=dropout
            )

        def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
            features = self.backbone(x)
            return self.head(features)

    # ========== Load Model from GCS ==========
    print(f"\nLoading fine-tuned MUSIQ model: {model_version}")
    model_start = time.time()

    # Setup GCS credentials
    setup_gcs_credentials()

    # Download model checkpoint
    gcs_path = f"models/diqa/track_a_iqa/musiq/{model_version}/model.pt"
    local_model_path = Path("/models/musiq_finetuned.pt")
    local_model_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading from gs://image_detection_b/{gcs_path}...")
    client = storage.Client()
    bucket = client.bucket("image_detection_b")
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(str(local_model_path))
    print(
        f"Downloaded model checkpoint ({local_model_path.stat().st_size / 1024:.1f} KB)"
    )

    # Load base MUSIQ from PyIQA
    base_musiq = pyiqa.create_metric("musiq", device=device)

    # Create model with same architecture as training
    model = MUSIQMultiTask(base_musiq, hidden_dim=256, dropout=0.1)
    model = model.to(device)

    # Load trained weights
    checkpoint = torch.load(
        str(local_model_path), map_location=device, weights_only=False
    )
    if "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict, strict=False)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Image preprocessing
    preprocess = transforms.Compose(
        [
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
        ]
    )

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and preprocess image
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                outputs = model(input_tensor)
                # Model outputs are in [0, 1], scale to [1, 5] for comparison
                predicted = {
                    "overall": outputs["overall"].item() * 4.0 + 1.0,
                    "sharpness": outputs["sharpness"].item() * 4.0 + 1.0,
                    "color": outputs["color"].item() * 4.0 + 1.0,
                }

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics for MUSIQ Sharpness Specialist
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# Fine-tuned MANIQA Benchmark (Custom trained on DIQA-5000)
# =============================================================================

finetuned_maniqa_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "pyiqa>=0.1.12",
        "opencv-python-headless>=4.8.0",
        "einops>=0.7.0",  # Required for MANIQA feature hook
        "timm>=0.9.0",  # Required for MANIQA ViT backbone
    )
)


@app.function(
    image=finetuned_maniqa_image,
    gpu="T4",
    timeout=3600,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,
)
def run_finetuned_maniqa_benchmark(
    model_version: str = "v1.0.0",
    num_samples: int = 0,
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with fine-tuned MANIQA model.

    This benchmarks the custom MANIQA model trained on DIQA-5000.
    The model uses MANIQA backbone with multi-task head for predicting
    overall, sharpness, and color quality dimensions.

    Architecture (from train_maniqa_finetuning.py):
        - MANIQA backbone (ViT + Swin Transformer + TABlocks)
        - Forward hook on swintransformer2 to capture 384-dim features
        - Multi-task head with shared layers + dimension-specific outputs
        - Sigmoid activation for [0, 1] output range

    Training Protocol:
        - Phase 1: 15 epochs with frozen backbone
        - Phase 2: 35 epochs with differential LRs
        - Loss: MSE (0.6) + RankLoss (0.2) + FocalLoss (0.2)

    Args:
        model_version: Model version to load from GCS (default: v1.0.0).
        num_samples: Number of samples to evaluate (0 = all 1000).

    Returns:
        Benchmark metrics with confidence intervals and sample results.
    """
    import pyiqa
    import torch
    import torch.nn as nn
    from einops import rearrange
    from google.cloud import storage
    from PIL import Image
    from torchvision import transforms

    model_id = f"MANIQA-DIQA5000-Finetuned-{model_version}"

    print("=" * 60)
    print(f"Arena IQA Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("Running on CPU")

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # ========== Define Model Architecture ==========
    # Must match training architecture from train_maniqa_finetuning.py

    class MANIQAMultiTask(nn.Module):
        """MANIQA wrapper with multi-task head for DIQA training.

        Uses pretrained MANIQA backbone with custom multi-task head
        for predicting overall, sharpness, and color quality scores.
        """

        def __init__(
            self,
            freeze_backbone: bool = False,
            head_hidden_dim: int = 384,
            head_dropout: float = 0.1,
        ) -> None:
            super().__init__()

            # Load pretrained MANIQA backbone
            metric = pyiqa.create_metric("maniqa", device="cpu", as_loss=True)
            self.backbone = metric.net
            self._rearrange = rearrange

            # Force single crop mode
            self.backbone.test_sample = 1

            feature_dim = 384  # MANIQA TABlock output dimension

            # Store captured features from hook
            self._captured_features: torch.Tensor | None = None

            # Register hook to capture features after swintransformer2
            def _capture_hook(
                _module: nn.Module, _input: tuple, output: torch.Tensor
            ) -> None:
                h = self.backbone.input_size  # 28
                x = self._rearrange(output, "b c h w -> b (h w) c", h=h, w=h)
                self._captured_features = x.mean(dim=1)  # [B, 384]

            self._hook_handle = self.backbone.swintransformer2.register_forward_hook(
                _capture_hook
            )

            # Multi-task head (shared layers)
            self.head = nn.Sequential(
                nn.Linear(feature_dim, head_hidden_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(head_dropout),
                nn.Linear(head_hidden_dim, head_hidden_dim // 2),
                nn.ReLU(inplace=True),
                nn.Dropout(head_dropout),
            )

            # Dimension-specific output heads
            self.overall_head = nn.Linear(head_hidden_dim // 2, 1)
            self.sharpness_head = nn.Linear(head_hidden_dim // 2, 1)
            self.color_head = nn.Linear(head_hidden_dim // 2, 1)

            if freeze_backbone:
                for param in self.backbone.parameters():
                    param.requires_grad = False

        def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
            # Run backbone forward (hook captures features)
            _ = self.backbone(x)

            features = self._captured_features
            assert features is not None, "Features not captured by hook"

            # Pass through multi-task head
            shared_features = self.head(features)

            # Get dimension-specific predictions
            overall = torch.sigmoid(self.overall_head(shared_features)).squeeze(-1)
            sharpness = torch.sigmoid(self.sharpness_head(shared_features)).squeeze(-1)
            color = torch.sigmoid(self.color_head(shared_features)).squeeze(-1)

            return {
                "overall": overall,
                "sharpness": sharpness,
                "color": color,
            }

    # ========== Load Model from GCS ==========
    print(f"\nLoading fine-tuned MANIQA model: {model_version}")
    model_start = time.time()

    # Setup GCS credentials
    setup_gcs_credentials()

    # Download model checkpoint
    gcs_path = f"models/diqa/track_a_iqa/maniqa/{model_version}/model.pt"
    local_model_path = Path("/models/maniqa_finetuned.pt")
    local_model_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading from gs://image_detection_b/{gcs_path}...")
    client = storage.Client()
    bucket = client.bucket("image_detection_b")
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(str(local_model_path))
    model_size_mb = local_model_path.stat().st_size / (1024 * 1024)
    print(f"Downloaded model checkpoint ({model_size_mb:.1f} MB)")

    # Create model with same architecture as training
    model = MANIQAMultiTask(
        freeze_backbone=False,  # Not training, doesn't matter
        head_hidden_dim=384,
        head_dropout=0.1,
    )
    model = model.to(device)

    # Load trained weights
    checkpoint = torch.load(
        str(local_model_path), map_location=device, weights_only=False
    )
    if "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        print(f"Loaded checkpoint from epoch {checkpoint.get('epoch', 'unknown')}")
        if "val_metrics" in checkpoint:
            val_metrics = checkpoint["val_metrics"]
            print(f"Training val_loss: {val_metrics.get('val_loss', 'N/A'):.4f}")
            print(f"Training SRCC_mean: {val_metrics.get('srcc_mean', 'N/A'):.4f}")
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict, strict=False)
    model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Image preprocessing (MANIQA uses 224x224 input)
    preprocess = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and preprocess image
            image = Image.open(sample["image_path"]).convert("RGB")
            input_tensor = preprocess(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                outputs = model(input_tensor)
                # Model outputs are in [0, 1], scale to [1, 5] for comparison
                predicted = {
                    "overall": outputs["overall"].item() * 4.0 + 1.0,
                    "sharpness": outputs["sharpness"].item() * 4.0 + 1.0,
                    "color": outputs["color"].item() * 4.0 + 1.0,
                }

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics for MANIQA fine-tuned
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}
