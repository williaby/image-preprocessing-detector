#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Unified Model Benchmark Runner for IQA Model Evaluation.

This script runs a model through all benchmarks needed to populate the
IQA_MODEL_BENCHMARK_TRACKER.csv. It captures:

1. Phase7 MVP metrics: Spearman, Pearson, MAE, RMSE, ENCE, MCE
2. Per-degradation breakdown: Blur, Noise, Compression, Contrast correlations
3. DIQA-5000 metrics: SRCC, PLCC with 95% confidence intervals
4. OCR correlation metrics (if SmartDoc-QA available)
5. Cross-dataset SRCC gap

Usage:
    # Run full benchmark suite
    python scripts/run_model_benchmark.py \\
        --model-path models/resnet50_teacher.pt \\
        --model-name "ResNet50_Teacher_v3" \\
        --model-type "deep_learning" \\
        --source "Ours"

    # Quick benchmark (Phase7 MVP only)
    python scripts/run_model_benchmark.py \\
        --model-path models/resnet50_teacher.pt \\
        --model-name "ResNet50_Teacher_v3" \\
        --quick

    # Update CSV tracker
    python scripts/run_model_benchmark.py \\
        --model-path models/resnet50_teacher.pt \\
        --model-name "ResNet50_Teacher_v3" \\
        --update-csv

Output:
    - JSON results file in data/benchmarks/
    - Optional CSV update to benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from scipy import stats
from torch.utils.data import DataLoader

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark run."""

    model_path: Path
    model_name: str
    model_type: Literal["deep_learning", "classical", "vision_language"]
    source: Literal["Ours", "PyIQA", "OpenCV"]

    # Dataset paths
    phase7_mvp_path: Path = Path("data/phase7_mvp/02_splits")
    diqa5000_path: Path = Path("data/benchmarks/diqa-5000")
    smartdoc_qa_path: Path = Path(
        "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa"
    )

    # Evaluation settings
    batch_size: int = 64
    num_workers: int = 4
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    num_bootstrap: int = 1000
    num_ece_bins: int = 15

    # Output
    output_dir: Path = Path("data/benchmarks")
    update_csv: bool = False
    csv_path: Path = Path("benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv")

    # Benchmark selection
    run_phase7: bool = True
    run_diqa5000: bool = True
    run_ocr_correlation: bool = False  # Requires SmartDoc-QA
    quick_mode: bool = False  # Phase7 only, no bootstrap


@dataclass
class HeadMetrics:
    """Metrics for a single prediction head."""

    name: str
    spearman: float
    pearson: float
    mae: float
    rmse: float
    ece: float = 0.0
    ence: float = 0.0
    mce: float = 0.0
    num_samples: int = 0
    uncertainty_correlation: float | None = (
        None  # Correlation between uncertainty and error
    )


@dataclass
class DatasetResults:
    """Results for a single dataset evaluation."""

    dataset: str
    num_samples: int
    inference_time_ms: float
    macro_spearman: float
    macro_pearson: float
    macro_mae: float
    macro_rmse: float
    macro_ece: float = 0.0
    macro_ence: float = 0.0
    macro_mce: float = 0.0
    srcc_ci_lower: float | None = None
    srcc_ci_upper: float | None = None
    per_head_metrics: list[HeadMetrics] = field(default_factory=list)
    supports_uncertainty: bool = False  # Whether model provides uncertainty estimates
    macro_uncertainty_correlation: float | None = (
        None  # Mean uncertainty-error correlation
    )


@dataclass
class BenchmarkResults:
    """Complete benchmark results for a model."""

    model_name: str
    model_type: str
    source: str
    timestamp: str
    device: str
    phase7_results: DatasetResults | None = None
    diqa5000_results: DatasetResults | None = None
    ocr_correlation: dict[str, float] | None = None
    cross_dataset_gap: float | None = None
    training_seeds: str = "42"
    notes: str = ""


def compute_ence(
    predictions: NDArray[np.floating[Any]],
    uncertainties: NDArray[np.floating[Any]],
    targets: NDArray[np.floating[Any]],
    num_bins: int = 15,
) -> dict[str, float]:
    """Compute Expected Normalized Calibration Error for regression.

    ENCE measures whether predicted uncertainty (σ) matches actual error.
    This is the correct calibration metric for regression (ECE is for classification).

    Args:
        predictions: Model mean predictions, shape (N,)
        uncertainties: Model predicted std, shape (N,)
        targets: Ground truth values, shape (N,)
        num_bins: Number of calibration bins

    Returns:
        Dictionary with ence, mce, and per-bin statistics
    """
    predictions = np.asarray(predictions).flatten()
    uncertainties = np.asarray(uncertainties).flatten()
    targets = np.asarray(targets).flatten()

    n_samples = len(predictions)
    if n_samples == 0:
        return {"ence": 0.0, "mce": 0.0}

    # Sort by predicted uncertainty
    sorted_idx = np.argsort(uncertainties)
    predictions = predictions[sorted_idx]
    uncertainties = uncertainties[sorted_idx]
    targets = targets[sorted_idx]

    # Bin by uncertainty percentiles
    bin_size = n_samples // num_bins
    ence = 0.0
    mce = 0.0
    bin_errors = []

    for i in range(num_bins):
        start = i * bin_size
        end = start + bin_size if i < num_bins - 1 else n_samples

        bin_preds = predictions[start:end]
        bin_uncert = uncertainties[start:end]
        bin_targets = targets[start:end]

        if len(bin_preds) == 0:
            continue

        # RMV: Root Mean Variance (expected uncertainty)
        rmv = np.sqrt(np.mean(bin_uncert**2))

        # RMSE: Root Mean Squared Error (actual error)
        rmse = np.sqrt(np.mean((bin_preds - bin_targets) ** 2))

        # Normalized calibration error for this bin
        if rmv > 1e-8:
            bin_error = np.abs(rmv - rmse) / rmv
        else:
            bin_error = np.abs(rmse)

        bin_errors.append(bin_error)
        ence += bin_error

    ence = ence / num_bins if num_bins > 0 else 0.0
    mce = max(bin_errors) if bin_errors else 0.0

    return {"ence": float(ence), "mce": float(mce)}


def compute_bootstrap_ci(
    predictions: NDArray[np.floating[Any]],
    targets: NDArray[np.floating[Any]],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Compute bootstrap confidence interval for Spearman correlation.

    Args:
        predictions: Model predictions, shape (N,)
        targets: Ground truth values, shape (N,)
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (mean_srcc, ci_lower, ci_upper)
    """
    predictions = np.asarray(predictions).flatten()
    targets = np.asarray(targets).flatten()

    n = len(predictions)
    srcc_samples = []

    rng = np.random.default_rng(42)
    for _ in range(n_bootstrap):
        idx = rng.choice(n, n, replace=True)
        srcc, _ = stats.spearmanr(predictions[idx], targets[idx])
        if not np.isnan(srcc):
            srcc_samples.append(srcc)

    if not srcc_samples:
        return 0.0, 0.0, 0.0

    mean_srcc = np.mean(srcc_samples)
    alpha = 1 - confidence
    ci_lower = np.percentile(srcc_samples, alpha / 2 * 100)
    ci_upper = np.percentile(srcc_samples, (1 - alpha / 2) * 100)

    return float(mean_srcc), float(ci_lower), float(ci_upper)


def compute_ece_for_regression(
    predictions: NDArray[np.floating[Any]],
    targets: NDArray[np.floating[Any]],
    num_bins: int = 15,
) -> dict[str, float]:
    """Compute ECE adapted for regression (treats predictions as confidence).

    For regression, we bin by prediction magnitude and check if predictions
    match target magnitudes within each bin.

    Args:
        predictions: Predicted severities [0,1], shape (N,)
        targets: True severities [0,1], shape (N,)
        num_bins: Number of calibration bins

    Returns:
        Dictionary with ece and mce values
    """
    predictions = np.asarray(predictions).flatten()
    targets = np.asarray(targets).flatten()

    n_samples = len(predictions)
    if n_samples == 0:
        return {"ece": 0.0, "mce": 0.0}

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    mce = 0.0

    for i in range(num_bins):
        lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
        if i == num_bins - 1:
            in_bin = (predictions >= lower) & (predictions <= upper)
        else:
            in_bin = (predictions >= lower) & (predictions < upper)

        bin_size = in_bin.sum()
        if bin_size > 0:
            # Mean prediction and mean target in this bin
            bin_pred_mean = predictions[in_bin].mean()
            bin_target_mean = targets[in_bin].mean()

            calibration_error = abs(bin_pred_mean - bin_target_mean)
            ece += (bin_size / n_samples) * calibration_error
            mce = max(mce, calibration_error)

    return {"ece": float(ece), "mce": float(mce)}


def load_model(config: BenchmarkConfig) -> torch.nn.Module:
    """Load trained model from checkpoint.

    Args:
        config: Benchmark configuration with model path

    Returns:
        Loaded PyTorch model in eval mode
    """
    import timm
    import torch.nn as nn

    # Load checkpoint
    # S6985: weights_only=False required to load config dict from checkpoint
    checkpoint = torch.load(  # nosec B614
        config.model_path, map_location=config.device, weights_only=False
    )

    # Determine model architecture from checkpoint or config
    model_config = checkpoint.get("config", {})
    # Support both teacher (model_architecture) and student (student_architecture) configs
    architecture = model_config.get(
        "model_architecture", model_config.get("student_architecture", "resnet50")
    )
    num_heads = model_config.get("num_heads", 5)
    dropout = model_config.get("dropout", 0.2)

    # Create model
    backbone = timm.create_model(architecture, pretrained=False, num_classes=0)
    feature_dim = backbone.num_features

    # Check if this is a Gaussian head model (production) or simple head model (MVP)
    state_dict = checkpoint["model_state_dict"]
    is_gaussian = any("mu_head" in k for k in state_dict.keys())

    if is_gaussian:
        # Gaussian head architecture for uncertainty estimation
        # Infer dimensions from state_dict
        shared_dim = state_dict["heads.0.shared.0.weight"].shape[0]
        sub_head_dim = state_dict["heads.0.mu_head.0.weight"].shape[0]

        class GaussianHead(nn.Module):
            """Gaussian head for uncertainty estimation."""

            def __init__(self, in_features: int, hidden_dim: int, sub_dim: int) -> None:
                super().__init__()
                self.shared = nn.Sequential(
                    nn.Linear(in_features, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                )
                self.mu_head = nn.Sequential(
                    nn.Linear(hidden_dim, sub_dim),
                    nn.ReLU(),
                    nn.Linear(sub_dim, 1),
                    nn.Sigmoid(),
                )
                self.log_var_head = nn.Sequential(
                    nn.Linear(hidden_dim, sub_dim),
                    nn.ReLU(),
                    nn.Linear(sub_dim, 1),
                )

            def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
                shared = self.shared(x)
                mu = self.mu_head(shared)
                log_var = self.log_var_head(shared)
                return mu, log_var

        class GaussianMultiHeadIQA(nn.Module):
            def __init__(
                self,
                backbone: nn.Module,
                feature_dim: int,
                num_heads: int,
                hidden_dim: int,
                sub_dim: int,
            ) -> None:
                super().__init__()
                self.backbone = backbone
                self.heads = nn.ModuleList(
                    [
                        GaussianHead(feature_dim, hidden_dim, sub_dim)
                        for _ in range(num_heads)
                    ]
                )
                self.supports_uncertainty = True

            def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
                features = self.backbone(x)
                mus = []
                log_vars = []
                for head in self.heads:
                    mu, log_var = head(features)
                    mus.append(mu)
                    log_vars.append(log_var)
                return torch.cat(mus, dim=1), torch.cat(log_vars, dim=1)

        model = GaussianMultiHeadIQA(
            backbone, feature_dim, num_heads, shared_dim, sub_head_dim
        )
    else:
        # Simple head architecture for MVP models

        class MultiHeadIQA(nn.Module):
            def __init__(
                self,
                backbone: nn.Module,
                feature_dim: int,
                num_heads: int,
                dropout: float,
            ) -> None:
                super().__init__()
                self.backbone = backbone
                self.heads = nn.ModuleList(
                    [
                        nn.Sequential(
                            nn.Dropout(dropout),
                            nn.Linear(feature_dim, 1),
                            nn.Sigmoid(),
                        )
                        for _ in range(num_heads)
                    ]
                )
                self.supports_uncertainty = False

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                features = self.backbone(x)
                outputs = [head(features) for head in self.heads]
                return torch.cat(outputs, dim=1)

        model = MultiHeadIQA(backbone, feature_dim, num_heads, dropout)

    model.load_state_dict(state_dict)
    model = model.to(config.device)
    model.eval()

    return model


class Phase7MVPDataset(torch.utils.data.Dataset):
    """Dataset for Phase7 MVP benchmark evaluation.

    Loads images from the Phase7 MVP dataset with severity scores.
    Uses the {split}_metadata.json format with images in 01_augmented/images/.

    Args:
        data_dir: Path to phase7_mvp directory (containing 02_splits/)
        split: Dataset split ("train", "val", "test")
        transform: Optional albumentations transform
    """

    # Label dimensions in order: blur, noise, compression, contrast, geometric
    SEVERITY_KEYS = [
        "blur_severity",
        "noise_severity",
        "compression_severity",
        "contrast_severity",
        "skew_severity",
    ]

    def __init__(
        self,
        data_dir: str | Path,
        split: str = "test",
        transform: Any = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.split = split
        self.transform = transform

        # Load metadata
        metadata_file = self.data_dir / "02_splits" / f"{split}_metadata.json"
        if not metadata_file.exists():
            msg = f"Metadata file not found: {metadata_file}"
            raise FileNotFoundError(msg)

        with open(metadata_file) as f:
            self.samples = json.load(f)

        # Images are in 01_augmented/images/
        self.images_dir = self.data_dir / "01_augmented" / "images"

        print(f"Loaded {len(self.samples)} samples from {split} split")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]

        # Load image
        image_path = self.images_dir / sample["filename"]
        image = np.array(Image.open(image_path).convert("RGB"))

        # Extract severity scores
        severity_scores = sample.get("severity_scores", {})
        labels = [float(severity_scores.get(key, 0.0)) for key in self.SEVERITY_KEYS]

        # Apply transform
        if self.transform is not None:
            transformed = self.transform(image=image)
            image = transformed["image"]

        labels_tensor = torch.tensor(labels, dtype=torch.float32)
        return image, labels_tensor


def create_phase7_dataloader(
    config: BenchmarkConfig, split: str = "test"
) -> DataLoader:
    """Create dataloader for Phase7 MVP dataset.

    Args:
        config: Benchmark configuration
        split: Dataset split ("train", "val", "test")

    Returns:
        PyTorch DataLoader
    """
    import albumentations as albu
    from albumentations.pytorch import ToTensorV2

    # Get input resolution from model checkpoint config
    # S6985: weights_only=False required to load config dict from checkpoint
    checkpoint = torch.load(  # nosec B614
        config.model_path, map_location="cpu", weights_only=False
    )
    model_config = checkpoint.get("config", {})
    input_resolution = model_config.get("input_resolution", 384)

    transform = albu.Compose(
        [
            albu.Resize(input_resolution, input_resolution),
            albu.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ]
    )

    dataset = Phase7MVPDataset(config.phase7_mvp_path, split=split, transform=transform)

    return DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )


def evaluate_phase7(
    model: torch.nn.Module,
    config: BenchmarkConfig,
) -> DatasetResults:
    """Evaluate model on Phase7 MVP dataset.

    Computes all metrics for the Phase7 MVP columns in the tracker.

    Args:
        model: Trained IQA model
        config: Benchmark configuration

    Returns:
        DatasetResults with all Phase7 metrics
    """
    print("\n" + "=" * 60)
    print("PHASE 7 MVP EVALUATION")
    print("=" * 60)

    loader = create_phase7_dataloader(config, split="test")
    print(f"Test samples: {len(loader.dataset)}")  # type: ignore[arg-type]
    print(f"Batch size: {config.batch_size}")
    print(f"Device: {config.device}")

    # Head names in order
    head_names = ["blur", "noise", "compression", "contrast", "geometric"]

    all_predictions: list[list[float]] = [[] for _ in range(5)]
    all_targets: list[list[float]] = [[] for _ in range(5)]
    all_uncertainties: list[list[float]] = [[] for _ in range(5)]
    inference_times: list[float] = []

    # Check if model supports uncertainty estimation
    supports_uncertainty = getattr(model, "supports_uncertainty", False)
    if supports_uncertainty:
        print("Model supports uncertainty estimation (Gaussian heads)")

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(config.device)
            labels = labels.cpu().numpy()

            start_time = time.perf_counter()
            output = model(images)
            inference_times.append((time.perf_counter() - start_time) * 1000)

            if supports_uncertainty:
                # Gaussian model returns (mu, log_var)
                mu, log_var = output
                outputs = mu.cpu().numpy()
                # Convert log_var to std (uncertainty)
                uncertainties = np.sqrt(np.exp(log_var.cpu().numpy()))
            else:
                outputs = output.cpu().numpy()
                uncertainties = None

            for h in range(5):
                all_predictions[h].extend(outputs[:, h].tolist())
                all_targets[h].extend(labels[:, h].tolist())
                if uncertainties is not None:
                    all_uncertainties[h].extend(uncertainties[:, h].tolist())

    # Convert to numpy
    predictions_np = [np.array(p) for p in all_predictions]
    targets_np = [np.array(t) for t in all_targets]
    uncertainties_np = (
        [np.array(u) for u in all_uncertainties] if supports_uncertainty else None
    )

    # Compute per-head metrics
    per_head_metrics: list[HeadMetrics] = []
    for h, name in enumerate(head_names):
        preds = predictions_np[h]
        targs = targets_np[h]

        # Correlation metrics
        spearman, _ = stats.spearmanr(preds, targs)
        pearson, _ = stats.pearsonr(preds, targs)

        # Error metrics
        mae = float(np.abs(preds - targs).mean())
        rmse = float(np.sqrt(((preds - targs) ** 2).mean()))

        # Calibration metrics
        ece_result = compute_ece_for_regression(preds, targs, config.num_ece_bins)

        # For ENCE, use real uncertainty if available, otherwise use proxy
        if uncertainties_np is not None:
            uncertainty = uncertainties_np[h]
        else:
            # Proxy uncertainty for models without uncertainty estimation
            uncertainty = np.abs(preds - 0.5) + 0.1
        ence_result = compute_ence(
            preds,
            uncertainty,
            targs,
            config.num_ece_bins,
        )

        # Compute uncertainty-error correlation (only for models with real uncertainty)
        unc_corr: float | None = None
        if uncertainties_np is not None:
            errors = np.abs(preds - targs)
            unc_corr_val, _ = stats.spearmanr(uncertainty, errors)
            unc_corr = float(unc_corr_val) if not np.isnan(unc_corr_val) else None

        head_metrics = HeadMetrics(
            name=name,
            spearman=float(spearman) if not np.isnan(spearman) else 0.0,
            pearson=float(pearson) if not np.isnan(pearson) else 0.0,
            mae=mae,
            rmse=rmse,
            ece=ece_result["ece"],
            ence=ence_result["ence"],
            mce=ece_result["mce"],
            num_samples=len(preds),
            uncertainty_correlation=unc_corr,
        )
        per_head_metrics.append(head_metrics)

        print(f"\n{name}:")
        print(f"  SRCC={head_metrics.spearman:.4f}, PLCC={head_metrics.pearson:.4f}")
        print(f"  MAE={head_metrics.mae:.4f}, RMSE={head_metrics.rmse:.4f}")
        print(f"  ECE={head_metrics.ece:.4f}, ENCE={head_metrics.ence:.4f}")
        if unc_corr is not None:
            print(f"  Uncertainty-Error Corr={unc_corr:.4f}")

    # Compute macro metrics
    macro_spearman = np.mean([m.spearman for m in per_head_metrics])
    macro_pearson = np.mean([m.pearson for m in per_head_metrics])
    macro_mae = np.mean([m.mae for m in per_head_metrics])
    macro_rmse = np.mean([m.rmse for m in per_head_metrics])
    macro_ece = np.mean([m.ece for m in per_head_metrics])
    macro_ence = np.mean([m.ence for m in per_head_metrics])
    macro_mce = max(m.mce for m in per_head_metrics)

    # Compute macro uncertainty correlation (only for models with real uncertainty)
    macro_unc_corr: float | None = None
    if supports_uncertainty:
        unc_corrs = [
            m.uncertainty_correlation
            for m in per_head_metrics
            if m.uncertainty_correlation is not None
        ]
        if unc_corrs:
            macro_unc_corr = float(np.mean(unc_corrs))

    avg_inference_ms = np.mean(inference_times) / config.batch_size

    print("\n[MACRO METRICS]")
    print(f"  SRCC={macro_spearman:.4f}, PLCC={macro_pearson:.4f}")
    print(f"  MAE={macro_mae:.4f}, RMSE={macro_rmse:.4f}")
    print(f"  ECE={macro_ece:.4f}, ENCE={macro_ence:.4f}, MCE={macro_mce:.4f}")
    if macro_unc_corr is not None:
        print(f"  Uncertainty-Error Correlation={macro_unc_corr:.4f}")
    print(f"  Inference: {avg_inference_ms:.2f}ms/sample")

    return DatasetResults(
        dataset="phase7_mvp",
        num_samples=len(loader.dataset),  # type: ignore[arg-type]
        inference_time_ms=avg_inference_ms,
        macro_spearman=float(macro_spearman),
        macro_pearson=float(macro_pearson),
        macro_mae=float(macro_mae),
        macro_rmse=float(macro_rmse),
        macro_ece=float(macro_ece),
        macro_ence=float(macro_ence),
        macro_mce=float(macro_mce),
        per_head_metrics=per_head_metrics,
        supports_uncertainty=supports_uncertainty,
        macro_uncertainty_correlation=macro_unc_corr,
    )


def evaluate_diqa5000(
    model: torch.nn.Module,
    config: BenchmarkConfig,
) -> DatasetResults | None:
    """Evaluate model on DIQA-5000 dataset.

    DIQA-5000 has human MOS (Mean Opinion Score) annotations.
    We compute SRCC and PLCC with 95% confidence intervals.

    Args:
        model: Trained IQA model
        config: Benchmark configuration

    Returns:
        DatasetResults with DIQA-5000 metrics, or None if dataset unavailable
    """
    print("\n" + "=" * 60)
    print("DIQA-5000 EVALUATION")
    print("=" * 60)

    if not config.diqa5000_path.exists():
        print(f"DIQA-5000 not found at {config.diqa5000_path}")
        print("Skipping DIQA-5000 evaluation")
        return None

    # Check for test split - DIQA-5000 uses CSV format
    test_dir = config.diqa5000_path / "test"
    annotations_file = test_dir / "test.csv"

    if not test_dir.exists() or not annotations_file.exists():
        print("DIQA-5000 test split not properly configured")
        print(f"  Expected: {annotations_file}")
        return None

    import albumentations as albu
    from albumentations.pytorch import ToTensorV2

    # Load annotations from CSV
    # Format: res,ori,overall,sharpness,color_fidelity
    annotations = []
    with open(annotations_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            annotations.append(
                {
                    "image_name": row["res"],  # Use distorted (res) images
                    "mos": float(row["overall"]),  # Use overall quality score
                }
            )

    print(f"DIQA-5000 test annotations: {len(annotations)} samples")

    # Get input resolution from model checkpoint config
    # S6985: weights_only=False required to load config dict from checkpoint
    checkpoint = torch.load(  # nosec B614
        config.model_path, map_location="cpu", weights_only=False
    )
    model_config = checkpoint.get("config", {})
    input_resolution = model_config.get("input_resolution", 384)

    transform = albu.Compose(
        [
            albu.Resize(input_resolution, input_resolution),
            albu.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ]
    )

    # Collect predictions and MOS scores
    all_predictions: list[float] = []
    all_mos: list[float] = []
    inference_times: list[float] = []

    # Check if model supports uncertainty estimation
    supports_uncertainty = getattr(model, "supports_uncertainty", False)

    # Images are in test/res/ subdirectory
    images_dir = test_dir / "res"

    with torch.no_grad():
        for sample in annotations:
            image_path = images_dir / sample["image_name"]
            if not image_path.exists():
                continue

            # Load and preprocess image
            image = np.array(Image.open(image_path).convert("RGB"))
            transformed = transform(image=image)
            image_tensor = transformed["image"].unsqueeze(0).to(config.device)

            # Predict
            start_time = time.perf_counter()
            output = model(image_tensor)
            inference_times.append((time.perf_counter() - start_time) * 1000)

            # Handle Gaussian vs simple model outputs
            if supports_uncertainty:
                mu, _ = output
                outputs = mu.cpu().numpy()[0]
            else:
                outputs = output.cpu().numpy()[0]

            # Average across heads as degradation score
            # Our models output degradation/severity (higher = worse quality)
            degradation_score = float(outputs.mean())
            all_predictions.append(degradation_score)
            all_mos.append(sample["mos"])

    if len(all_predictions) < 100:
        print(f"Insufficient samples: {len(all_predictions)}")
        return None

    predictions_np = np.array(all_predictions)
    mos_np = np.array(all_mos)

    # Convert degradation scores to quality scores for correlation
    # Our models: higher = more degradation = worse quality
    # MOS: higher = better quality
    # So we invert our predictions: quality = 1 - degradation
    quality_predictions = 1.0 - predictions_np

    # Compute correlations using quality predictions
    srcc, _ = stats.spearmanr(quality_predictions, mos_np)
    plcc, _ = stats.pearsonr(quality_predictions, mos_np)

    # Bootstrap CI using quality predictions
    if config.quick_mode:
        ci_lower, ci_upper = srcc - 0.05, srcc + 0.05
    else:
        _, ci_lower, ci_upper = compute_bootstrap_ci(
            quality_predictions, mos_np, config.num_bootstrap
        )

    avg_inference_ms = np.mean(inference_times)

    print("\n[DIQA-5000 RESULTS]")
    print(f"  Samples: {len(all_predictions)}")
    print(f"  SRCC: {srcc:.4f} (95% CI: {ci_lower:.4f} - {ci_upper:.4f})")
    print(f"  PLCC: {plcc:.4f}")
    print(f"  Inference: {avg_inference_ms:.2f}ms/sample")

    return DatasetResults(
        dataset="diqa5000",
        num_samples=len(all_predictions),
        inference_time_ms=avg_inference_ms,
        macro_spearman=float(srcc) if not np.isnan(srcc) else 0.0,
        macro_pearson=float(plcc) if not np.isnan(plcc) else 0.0,
        macro_mae=0.0,  # Not applicable for MOS comparison
        macro_rmse=0.0,
        srcc_ci_lower=float(ci_lower),
        srcc_ci_upper=float(ci_upper),
    )


def evaluate_smartdoc_qa_ocr(
    model: torch.nn.Module,
    config: BenchmarkConfig,
) -> dict[str, float] | None:
    """Evaluate OCR correlation on SmartDoc-QA dataset.

    SmartDoc-QA contains document images with Tesseract OCR accuracy scores.
    We correlate IQA predictions with character accuracy (CACC) and word
    accuracy (WACC) to validate IQA scores predict OCR performance.

    Args:
        model: Trained IQA model
        config: Benchmark configuration

    Returns:
        Dictionary with OCR correlation metrics:
        - cer_correlation: Spearman correlation with character error rate
        - wer_correlation: Spearman correlation with word error rate
        - ranking_agreement: Overlap between worst IQA and worst OCR images
    """
    print("\n" + "=" * 60)
    print("SMARTDOC-QA OCR CORRELATION EVALUATION")
    print("=" * 60)

    if config.smartdoc_qa_path is None or not config.smartdoc_qa_path.exists():
        print(f"SmartDoc-QA not found at {config.smartdoc_qa_path}")
        print("Skipping OCR correlation evaluation")
        return None

    dataset_root = config.smartdoc_qa_path / "Dataset SmartDoc-QA"
    if not dataset_root.exists():
        print(f"SmartDoc-QA dataset root not found: {dataset_root}")
        return None

    import albumentations as albu
    from albumentations.pytorch import ToTensorV2
    import re

    # Get input resolution from model checkpoint config
    # S6985: weights_only=False required to load config dict from checkpoint
    checkpoint = torch.load(  # nosec B614
        config.model_path, map_location="cpu", weights_only=False
    )
    model_config = checkpoint.get("config", {})
    input_resolution = model_config.get("input_resolution", 384)

    transform = albu.Compose(
        [
            albu.Resize(input_resolution, input_resolution),
            albu.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ]
    )

    def parse_ocr_accuracy(filepath: Path) -> float | None:
        """Parse character/word accuracy from SmartDoc-QA OCR report."""
        if not filepath.exists():
            return None
        try:
            content = filepath.read_text()
            # Look for "XX.XX%  Accuracy" pattern

            match = re.search(r"(\d+\.\d+)%\s{1,10}Accuracy", content)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    # Collect samples from both phones
    all_predictions: list[float] = []
    all_cacc: list[float] = []  # Character accuracy
    all_wacc: list[float] = []  # Word accuracy

    # Check if model supports uncertainty estimation
    supports_uncertainty = getattr(model, "supports_uncertainty", False)

    phones = ["Nokia_phone", "Samsung_phone"]

    for phone in phones:
        phone_dir = dataset_root / "Captured_Images" / phone
        images_dir = phone_dir / "Images"
        cacc_dir = phone_dir / "OCR_Accuracy_Tesseract"

        if not images_dir.exists():
            continue

        image_files = list(images_dir.glob("*.jpg"))
        print(f"  {phone}: {len(image_files)} images")

        with torch.no_grad():
            for img_path in image_files:
                # Get OCR accuracy files
                base_name = img_path.stem
                cacc_file = cacc_dir / f"{base_name}.cacc.txt"
                wacc_file = cacc_dir / f"{base_name}.wacc.txt"

                cacc = parse_ocr_accuracy(cacc_file)
                wacc = parse_ocr_accuracy(wacc_file)

                if cacc is None or wacc is None:
                    continue

                # Load and preprocess image
                try:
                    image = np.array(Image.open(img_path).convert("RGB"))
                    transformed = transform(image=image)
                    image_tensor = transformed["image"].unsqueeze(0).to(config.device)

                    # Predict
                    output = model(image_tensor)

                    # Handle Gaussian vs simple model outputs
                    if supports_uncertainty:
                        mu, _ = output
                        outputs = mu.cpu().numpy()[0]
                    else:
                        outputs = output.cpu().numpy()[0]

                    quality_score = float(outputs.mean())

                    all_predictions.append(quality_score)
                    all_cacc.append(cacc)
                    all_wacc.append(wacc)
                except Exception:
                    continue

    if len(all_predictions) < 50:
        print(f"Insufficient samples: {len(all_predictions)}")
        return None

    predictions_np = np.array(all_predictions)
    cacc_np = np.array(all_cacc)
    wacc_np = np.array(all_wacc)

    # Our models output degradation scores (higher = more degradation = worse quality)
    # Error rates: higher = worse OCR performance
    # Therefore: higher degradation should correlate with higher error rate
    # This means we want POSITIVE correlation between degradation and error
    # To report in standard IQA format (higher quality = lower error), we invert our predictions
    quality_predictions = 1.0 - predictions_np

    # Compute correlations: quality vs accuracy (both: higher = better)
    # This gives positive correlation if model correctly identifies quality issues
    cer_corr, _ = stats.spearmanr(quality_predictions, cacc_np)
    wer_corr, _ = stats.spearmanr(quality_predictions, wacc_np)

    # Ranking agreement: do worst quality images have worst OCR?
    n_samples = len(predictions_np)
    n_worst = max(1, n_samples // 10)  # Bottom 10%

    # Highest degradation = worst quality
    iqa_worst_idx = np.argsort(predictions_np)[-n_worst:]
    # Lowest accuracy = worst OCR
    ocr_worst_idx = np.argsort(cacc_np)[:n_worst]

    ranking_agreement = len(set(iqa_worst_idx) & set(ocr_worst_idx)) / n_worst

    print("\n[SMARTDOC-QA OCR CORRELATION]")
    print(f"  Samples: {len(all_predictions)}")
    print(f"  CER Correlation: {cer_corr:.4f}")
    print(f"  WER Correlation: {wer_corr:.4f}")
    print(f"  Ranking Agreement (10%): {ranking_agreement:.4f}")

    return {
        "cer": float(cer_corr) if not np.isnan(cer_corr) else 0.0,
        "wer": float(wer_corr) if not np.isnan(wer_corr) else 0.0,
        "ranking": float(ranking_agreement),
    }


def compute_cross_dataset_gap(
    phase7_results: DatasetResults | None,
    diqa5000_results: DatasetResults | None,
) -> float | None:
    """Compute cross-dataset SRCC gap.

    Gap = In-distribution SRCC - Cross-distribution SRCC
    Lower is better (indicates good generalization).

    Args:
        phase7_results: Phase7 MVP evaluation results
        diqa5000_results: DIQA-5000 evaluation results

    Returns:
        Cross-dataset gap, or None if either dataset unavailable
    """
    if phase7_results is None or diqa5000_results is None:
        return None

    gap = phase7_results.macro_spearman - diqa5000_results.macro_spearman
    return float(gap)


def update_csv_tracker(results: BenchmarkResults, config: BenchmarkConfig) -> None:
    """Update the IQA_MODEL_BENCHMARK_TRACKER.csv with new results.

    Args:
        results: Complete benchmark results
        config: Benchmark configuration with CSV path
    """
    if not config.csv_path.exists():
        print(f"CSV tracker not found: {config.csv_path}")
        return

    # Read existing CSV
    with open(config.csv_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    # Prepare new row data
    new_data = {
        "Model": results.model_name,
        "Type": results.model_type,
        "Source": results.source,
        "Status": "evaluated",
    }

    # Phase7 MVP metrics
    if results.phase7_results:
        p7 = results.phase7_results
        new_data.update(
            {
                "Phase7_MVP_Spearman": f"{p7.macro_spearman:.3f}",
                "Phase7_MVP_Pearson": f"{p7.macro_pearson:.3f}",
                "Phase7_MVP_MAE": f"{p7.macro_mae:.3f}",
                "Phase7_MVP_RMSE": f"{p7.macro_rmse:.3f}",
                "Phase7_MVP_ENCE": f"{p7.macro_ence:.3f}",
                "Phase7_MVP_MCE": f"{p7.macro_mce:.3f}",
            }
        )

        # Per-degradation breakdown
        for head in p7.per_head_metrics:
            if head.name == "blur":
                new_data["Blur_Spearman"] = f"{head.spearman:.3f}"
            elif head.name == "noise":
                new_data["Noise_Spearman"] = f"{head.spearman:.3f}"
            elif head.name == "compression":
                new_data["Compress_Spearman"] = f"{head.spearman:.3f}"
            elif head.name == "contrast":
                new_data["Contrast_Spearman"] = f"{head.spearman:.3f}"

        new_data["Inference_ms"] = f"{p7.inference_time_ms:.1f}"

    # DIQA-5000 metrics
    if results.diqa5000_results:
        d5 = results.diqa5000_results
        new_data.update(
            {
                "DIQA5000_SRCC": f"{d5.macro_spearman:.3f}",
                "DIQA5000_PLCC": f"{d5.macro_pearson:.3f}",
                "DIQA5000_SRCC_CI_Lower": (
                    f"{d5.srcc_ci_lower:.3f}" if d5.srcc_ci_lower else "pending"
                ),
                "DIQA5000_SRCC_CI_Upper": (
                    f"{d5.srcc_ci_upper:.3f}" if d5.srcc_ci_upper else "pending"
                ),
            }
        )

    # Cross-dataset gap
    if results.cross_dataset_gap is not None:
        new_data["CrossDataset_SRCC_Gap"] = f"{results.cross_dataset_gap:.3f}"

    # OCR correlation (if available)
    if results.ocr_correlation:
        new_data.update(
            {
                "OCR_CER_Correlation": f"{results.ocr_correlation.get('cer', 0):.3f}",
                "OCR_WER_Correlation": f"{results.ocr_correlation.get('wer', 0):.3f}",
                "OCR_Ranking_Agreement": f"{results.ocr_correlation.get('ranking', 0):.3f}",
            }
        )

    new_data["Training_Seeds"] = results.training_seeds
    new_data["Notes"] = results.notes

    # Find existing row or append
    model_found = False
    for i, row in enumerate(rows):
        if row.get("Model") == results.model_name:
            rows[i].update(new_data)
            model_found = True
            break

    if not model_found:
        # Add as new row
        new_row = dict.fromkeys(fieldnames, "pending")
        new_row.update(new_data)
        rows.append(new_row)

    # Write back to CSV
    with open(config.csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Updated CSV tracker: {config.csv_path}")


def save_results(results: BenchmarkResults, config: BenchmarkConfig) -> Path:
    """Save benchmark results to JSON file.

    Args:
        results: Complete benchmark results
        config: Benchmark configuration

    Returns:
        Path to saved JSON file
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to dict for serialization
    results_dict = {
        "model_name": results.model_name,
        "model_type": results.model_type,
        "source": results.source,
        "timestamp": results.timestamp,
        "device": results.device,
        "training_seeds": results.training_seeds,
        "notes": results.notes,
    }

    if results.phase7_results:
        p7 = results.phase7_results
        results_dict["phase7_mvp"] = {
            "num_samples": p7.num_samples,
            "inference_time_ms": p7.inference_time_ms,
            "macro_metrics": {
                "spearman": p7.macro_spearman,
                "pearson": p7.macro_pearson,
                "mae": p7.macro_mae,
                "rmse": p7.macro_rmse,
                "ece": p7.macro_ece,
                "ence": p7.macro_ence,
                "mce": p7.macro_mce,
            },
            "per_head_metrics": [asdict(h) for h in p7.per_head_metrics],
        }

    if results.diqa5000_results:
        d5 = results.diqa5000_results
        results_dict["diqa5000"] = {
            "num_samples": d5.num_samples,
            "inference_time_ms": d5.inference_time_ms,
            "srcc": d5.macro_spearman,
            "plcc": d5.macro_pearson,
            "srcc_ci_lower": d5.srcc_ci_lower,
            "srcc_ci_upper": d5.srcc_ci_upper,
        }

    if results.cross_dataset_gap is not None:
        results_dict["cross_dataset_gap"] = results.cross_dataset_gap

    if results.ocr_correlation:
        results_dict["ocr_correlation"] = results.ocr_correlation

    # Save to file
    output_file = (
        config.output_dir
        / f"{results.model_name.lower().replace(' ', '_')}_benchmark_results.json"
    )
    with open(output_file, "w") as f:
        json.dump(results_dict, f, indent=2)

    print(f"\n✅ Saved results to: {output_file}")
    return output_file


def run_benchmark(config: BenchmarkConfig) -> BenchmarkResults:
    """Run complete benchmark suite for a model.

    Args:
        config: Benchmark configuration

    Returns:
        Complete benchmark results
    """
    print("=" * 60)
    print("IQA MODEL BENCHMARK SUITE")
    print("=" * 60)
    print(f"Model: {config.model_name}")
    print(f"Type: {config.model_type}")
    print(f"Source: {config.source}")
    print(f"Model path: {config.model_path}")
    print(f"Device: {config.device}")
    print(f"Quick mode: {config.quick_mode}")

    # Load model
    print("\n📦 Loading model...")
    model = load_model(config)
    print("✅ Model loaded successfully")

    # Initialize results
    results = BenchmarkResults(
        model_name=config.model_name,
        model_type=config.model_type,
        source=config.source,
        timestamp=datetime.now(UTC).isoformat(),
        device=config.device,
    )

    # Run Phase7 MVP evaluation
    if config.run_phase7:
        results.phase7_results = evaluate_phase7(model, config)

    # Run DIQA-5000 evaluation
    if config.run_diqa5000 and not config.quick_mode:
        results.diqa5000_results = evaluate_diqa5000(model, config)

    # Run OCR correlation evaluation
    if config.run_ocr_correlation and not config.quick_mode:
        results.ocr_correlation = evaluate_smartdoc_qa_ocr(model, config)

    # Compute cross-dataset gap
    results.cross_dataset_gap = compute_cross_dataset_gap(
        results.phase7_results, results.diqa5000_results
    )

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    if results.phase7_results:
        p7 = results.phase7_results
        print("\nPhase7 MVP:")
        print(f"  Macro SRCC: {p7.macro_spearman:.4f}")
        print(f"  Macro PLCC: {p7.macro_pearson:.4f}")
        print(f"  Macro MAE: {p7.macro_mae:.4f}")
        print(f"  Macro ENCE: {p7.macro_ence:.4f}")

    if results.diqa5000_results:
        d5 = results.diqa5000_results
        print("\nDIQA-5000:")
        print(
            f"  SRCC: {d5.macro_spearman:.4f} ({d5.srcc_ci_lower:.4f} - {d5.srcc_ci_upper:.4f})"
        )
        print(f"  PLCC: {d5.macro_pearson:.4f}")

    if results.cross_dataset_gap is not None:
        gap_status = "✅" if results.cross_dataset_gap < 0.10 else "⚠️"
        print(f"\nCross-Dataset Gap: {results.cross_dataset_gap:.4f} {gap_status}")

    if results.ocr_correlation:
        ocr = results.ocr_correlation
        cer_status = "✅" if ocr.get("cer", 0) > 0.70 else "⚠️"
        print("\nOCR Correlation (SmartDoc-QA):")
        print(f"  CER Correlation: {ocr.get('cer', 0):.4f} {cer_status}")
        print(f"  WER Correlation: {ocr.get('wer', 0):.4f}")
        print(f"  Ranking Agreement: {ocr.get('ranking', 0):.4f}")

    return results


def main() -> None:
    """Main entry point for benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Unified Model Benchmark Runner for IQA Model Evaluation"
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        required=True,
        help="Path to model checkpoint (.pt file)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        required=True,
        help="Model name for tracking (e.g., 'ResNet50_Teacher_v3')",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="deep_learning",
        choices=["deep_learning", "classical", "vision_language"],
        help="Model type category",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="Ours",
        choices=["Ours", "PyIQA", "OpenCV"],
        help="Model source",
    )
    parser.add_argument(
        "--phase7-path",
        type=Path,
        default=Path("data/phase7_mvp/02_splits"),
        help="Path to Phase7 MVP dataset",
    )
    parser.add_argument(
        "--diqa5000-path",
        type=Path,
        default=Path("data/benchmarks/diqa-5000"),
        help="Path to DIQA-5000 dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmarks"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for inference",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: Phase7 only, no bootstrap CI",
    )
    parser.add_argument(
        "--update-csv",
        action="store_true",
        help="Update the benchmark tracker CSV",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=Path("benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv"),
        help="Path to benchmark tracker CSV",
    )
    parser.add_argument(
        "--training-seeds",
        type=str,
        default="42",
        help="Training seeds used (comma-separated)",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Notes about this model/evaluation",
    )
    parser.add_argument(
        "--ocr-correlation",
        action="store_true",
        help="Run OCR correlation evaluation using SmartDoc-QA dataset",
    )
    parser.add_argument(
        "--smartdoc-qa-path",
        type=Path,
        default=Path("/mnt/e/image_detection/02_benchmark_only/smartdoc-qa"),
        help="Path to SmartDoc-QA dataset",
    )

    args = parser.parse_args()

    config = BenchmarkConfig(
        model_path=args.model_path,
        model_name=args.model_name,
        model_type=args.model_type,
        source=args.source,
        phase7_mvp_path=args.phase7_path,
        diqa5000_path=args.diqa5000_path,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        quick_mode=args.quick,
        update_csv=args.update_csv,
        csv_path=args.csv_path,
        run_ocr_correlation=args.ocr_correlation,
        smartdoc_qa_path=args.smartdoc_qa_path,
    )

    # Run benchmarks
    results = run_benchmark(config)
    results.training_seeds = args.training_seeds
    results.notes = args.notes

    # Save results
    save_results(results, config)

    # Update CSV if requested
    if config.update_csv:
        update_csv_tracker(results, config)

    print("\n🎉 Benchmark complete!")


if __name__ == "__main__":
    main()
