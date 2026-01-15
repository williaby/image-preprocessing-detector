# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal benchmark script for HyperIQA++ on DIQA-5000 test set.

Evaluates the trained HyperIQA++ model on the held-out test set and
generates benchmark metrics for comparison.

Usage:
    modal run modal/benchmark_hyperiqa_plus_plus.py

Output:
    - PLCC, SRCC, MAE for overall, sharpness, color dimensions
    - VQualA composite score
    - Results appended to docs/benchmarks/diqa5000_benchmark_results.csv
"""

from __future__ import annotations

import tarfile
import time
from dataclasses import dataclass
from pathlib import Path

import modal

# ============================================================================
# Modal Configuration
# ============================================================================

app = modal.App("hyperiqa-plus-plus-benchmark")

# Volumes
data_volume = modal.Volume.from_name("diqa5000-original", create_if_missing=False)
checkpoint_volume = modal.Volume.from_name("hyperiqa-checkpoints", create_if_missing=True)

# Docker image with dependencies
benchmark_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        # Core ML
        "torch==2.5.1",
        "torchvision==0.20.1",
        "timm>=1.0.0",
        # IQA
        "pyiqa>=0.1.12",
        # Stats
        "scipy>=1.14.1",
        "scikit-learn>=1.3.0",
        "numpy>=1.26.0",
        "tqdm>=4.67.0",
        # Image processing
        "pillow>=11.0.0",
        "opencv-python-headless>=4.8.0",
        # Data validation
        "pydantic>=2.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        # PDF processing
        "pymupdf>=1.23.0",
        # Utilities
        "click>=8.1.0",
        "huggingface-hub>=0.20.0",
        "gitpython>=3.1.45",
        "pywavelets>=1.4.0",
        "defusedxml>=0.7.1",
        "google-cloud-storage",
        "rich>=13.5.0",
        "structlog>=24.4.0",
    )
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/src/image_preprocessing_detector",
    )
    .add_local_file(
        local_path="modal/train_hyperiqa_plus_plus.py",
        remote_path="/root/modal/train_hyperiqa_plus_plus.py",
    )
)

GCS_SECRET = modal.Secret.from_name("gcs-credentials")


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    image_size: tuple[int, int] = (1600, 1600)
    num_bins: int = 10
    batch_size: int = 4
    num_workers: int = 4


def download_dataset_from_gcs(target_dir: Path) -> Path:
    """Download DIQA-5000 dataset from GCS."""
    import os

    from google.cloud import storage

    target_dir.mkdir(parents=True, exist_ok=True)

    # Set GCS credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    bucket_name = "image_detection_b"
    gcs_path = "datasets/diqa-5000/diqa-5000.tar.gz"

    print(f"Downloading DIQA-5000 from gs://{bucket_name}/{gcs_path}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Download tarball
    tar_blob = bucket.blob(gcs_path)
    tar_path = target_dir / "diqa-5000.tar.gz"

    start = time.time()
    tar_blob.download_to_filename(str(tar_path))
    download_time = time.time() - start

    tar_size_gb = tar_path.stat().st_size / (1024**3)
    print(f"Downloaded {tar_size_gb:.2f} GB in {download_time:.1f}s")

    # Extract dataset
    print("Extracting dataset...")
    extract_start = time.time()

    def is_within_directory(directory: Path, target: Path) -> bool:
        abs_directory = directory.resolve()
        abs_target = target.resolve()
        return str(abs_target).startswith(str(abs_directory))

    with tarfile.open(tar_path, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            member_path = target_dir / member.name
            if not is_within_directory(target_dir, member_path):
                msg = f"Path traversal detected: {member.name}"
                raise ValueError(msg)
        tar.extractall(path=target_dir, members=members, filter="data")

    extract_time = time.time() - extract_start
    print(f"Extracted in {extract_time:.1f}s")

    # Clean up tarball
    tar_path.unlink()

    dataset_path = target_dir / "diqa-5000"
    print(f"Dataset ready at: {dataset_path}")

    return dataset_path


@app.function(
    image=benchmark_image,
    gpu="A10G",
    timeout=1800,  # 30 minutes
    secrets=[GCS_SECRET],
    volumes={
        "/data": data_volume,
        "/checkpoints": checkpoint_volume,
    },
)
def benchmark_hyperiqa_plus_plus() -> dict:
    """Run benchmark on DIQA-5000 test set."""
    import sys

    # Add source to path
    sys.path.insert(0, "/root/src")
    sys.path.insert(0, "/root/modal")  # For loading checkpoint with TrainingConfig

    import numpy as np
    import torch
    from scipy.stats import pearsonr, spearmanr
    from torch.utils.data import DataLoader
    from tqdm import tqdm

    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
        DIQA5000HighResDataset,
    )
    from image_preprocessing_detector.labeling.hyperiqa_plus_plus.model import (
        HyperIQAPlusPlus,
    )

    config = BenchmarkConfig()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Check for dataset - use volume mount path
    data_dir = Path("/data/diqa5000")
    if not data_dir.exists():
        print(f"Dataset not found at {data_dir}, checking alternatives...")
        alt_dir = Path("/data/diqa-5000")
        if alt_dir.exists():
            data_dir = alt_dir
        else:
            print("Listing /data contents:")
            import os
            for item in os.listdir("/data"):
                print(f"  {item}")
            raise FileNotFoundError(f"Dataset not found at {data_dir}")

    # Load checkpoint
    checkpoint_path = Path("/checkpoints/hyperiqa_plus_plus_best.pt")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    print(f"Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    # Create model
    print("Creating model...")
    model = HyperIQAPlusPlus(
        num_bins=config.num_bins,
        freeze_backbone_epochs=10,
        use_pretrained=True,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    print(f"Model loaded from epoch {checkpoint['epoch']}")

    # Create test dataloader
    print("Loading test dataset...")
    test_dataset = DIQA5000HighResDataset(
        root_dir=data_dir,
        split="test",
        image_size=config.image_size,
        num_bins=config.num_bins,
        augment=False,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    print(f"Test set: {len(test_dataset)} samples")

    # Collect predictions and targets
    all_preds = {"overall": [], "sharpness": [], "color": []}
    all_targets = {"overall": [], "sharpness": [], "color": []}

    inference_times = []

    print("Running inference on test set...")
    with torch.no_grad():
        for batch in tqdm(test_loader, desc="Benchmarking"):
            images = batch["pixel_values"].to(device)
            targets = batch["targets"]

            # Time inference
            start_time = time.time()
            outputs = model(images)
            inference_times.append(time.time() - start_time)

            # Collect predictions and targets
            for dim in ["overall", "sharpness", "color"]:
                pred_scores = outputs[dim]["score"].cpu().numpy()
                target_scores = targets[dim]["mos"].numpy()

                all_preds[dim].extend(pred_scores)
                all_targets[dim].extend(target_scores)

    # Calculate metrics
    results = {
        "model_id": "HyperIQA-Plus-Plus-DIQA5000-v1.0.0",
        "model_type": "hyperiqa_finetuned",
        "benchmark_date": time.strftime("%Y-%m-%d"),
        "num_samples": len(test_dataset),
        "success_rate": 1.0,
    }

    print("\n" + "=" * 60)
    print("DIQA-5000 Test Set Benchmark Results")
    print("=" * 60)

    for dim in ["overall", "sharpness", "color"]:
        preds = np.array(all_preds[dim])
        targets = np.array(all_targets[dim])

        # Pearson Linear Correlation Coefficient
        plcc, _ = pearsonr(preds, targets)

        # Spearman Rank Correlation Coefficient
        srcc, _ = spearmanr(preds, targets)

        # Mean Absolute Error
        mae = np.mean(np.abs(preds - targets))

        # Root Mean Square Error
        rmse = np.sqrt(np.mean((preds - targets) ** 2))

        # Bootstrap confidence intervals (95%)
        n_bootstrap = 1000
        plcc_samples = []
        srcc_samples = []

        rng = np.random.default_rng(42)
        for _ in range(n_bootstrap):
            indices = rng.choice(len(preds), size=len(preds), replace=True)
            boot_preds = preds[indices]
            boot_targets = targets[indices]
            plcc_boot, _ = pearsonr(boot_preds, boot_targets)
            srcc_boot, _ = spearmanr(boot_preds, boot_targets)
            plcc_samples.append(plcc_boot)
            srcc_samples.append(srcc_boot)

        plcc_ci = np.percentile(plcc_samples, [2.5, 97.5])
        srcc_ci = np.percentile(srcc_samples, [2.5, 97.5])

        # Store results
        results[f"{dim}_plcc"] = plcc
        results[f"{dim}_plcc_ci_lower"] = plcc_ci[0]
        results[f"{dim}_plcc_ci_upper"] = plcc_ci[1]
        results[f"{dim}_srcc"] = srcc
        results[f"{dim}_srcc_ci_lower"] = srcc_ci[0]
        results[f"{dim}_srcc_ci_upper"] = srcc_ci[1]
        results[f"{dim}_mae"] = mae
        results[f"{dim}_rmse"] = rmse

        print(f"\n{dim.upper()} Dimension:")
        print(f"  PLCC: {plcc:.4f} [{plcc_ci[0]:.4f}, {plcc_ci[1]:.4f}]")
        print(f"  SRCC: {srcc:.4f} [{srcc_ci[0]:.4f}, {srcc_ci[1]:.4f}]")
        print(f"  MAE:  {mae:.4f}")
        print(f"  RMSE: {rmse:.4f}")

    # Calculate VQualA composite score
    vquala_score = (
        results["overall_plcc"] * 0.4 +
        results["sharpness_plcc"] * 0.3 +
        results["color_plcc"] * 0.3
    )
    results["vquala_score"] = vquala_score

    # Inference timing
    avg_inference_ms = np.mean(inference_times) * 1000 / config.batch_size
    total_inference_s = sum(inference_times)

    results["inference_mean_ms"] = avg_inference_ms
    results["inference_total_s"] = total_inference_s
    results["model_load_s"] = 0  # Not tracked separately
    results["gpu_type"] = "A10G"
    results["notes"] = "HyperIQA++ with 7 DocIQ/VQualA innovations fine-tuned on DIQA-5000"

    print(f"\n{'=' * 60}")
    print(f"VQualA Score: {vquala_score:.4f}")
    print(f"Avg Inference: {avg_inference_ms:.1f}ms/image")
    print(f"Total Inference: {total_inference_s:.1f}s")
    print("=" * 60)

    return results


@app.local_entrypoint()
def main():
    """Run benchmark and save results."""
    import csv
    from pathlib import Path

    print("Starting HyperIQA++ benchmark on DIQA-5000 test set...")

    # Run benchmark on Modal
    results = benchmark_hyperiqa_plus_plus.remote()

    # Display results
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)

    for key, value in results.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # Append to CSV
    csv_path = Path("docs/benchmarks/diqa5000_benchmark_results.csv")
    if csv_path.exists():
        # Read existing headers
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

        # Add any missing headers
        for key in results:
            if key not in headers:
                headers.append(key)

        # Append row
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow(results)

        print(f"\nResults appended to {csv_path}")
    else:
        print(f"\nWarning: {csv_path} not found, results not saved to CSV")

    return results
