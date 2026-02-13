"""Train unified SkewNet (MobileNetV4-Conv-S, 3 heads) on Modal L4.

Architecture: MobileNetV4-Conv-S backbone with 3 heads:
    1. Orientation classification (4-class: 0/90/180/270)
    2. Skew bin classification (42 non-uniform bins)
    3. Skew regression (SmoothL1 residual within bin)

Key design decisions (5-model consensus):
    - SmoothL1 regression loss (stable, directly optimizes MAE)
    - Per-bin residual clamping (matches bin half-widths)
    - 224x224 input (standard MobileNet, 3x faster than 384)
    - L4 GPU (sufficient for 2.7M params, avoids T4 preemption)
    - Tar cached on Volume (single file); extracted to /tmp at train start
    - Checkpoint resume support for interrupted runs
    - lr=5e-4 (conservative start, Grok 4 recommendation)
    - Separate synthetic vs natural validation metrics (Gemini 3 insight)
    - Gradient clipping max_norm=1.0 (DeepSeek R1 recommendation)

Training plan:
    - Epochs 1-30: Standard training with AdamW + OneCycleLR
    - Epochs 31-50: QAT (Quantization Aware Training) for INT8 export
    - Early stopping: patience 10 on validation MAE
    - Loss: 0.2*CE_orient + 0.3*CE_bins + 0.5*SmoothL1_regression
    - Target: MAE < 0.5 deg short-term (iterate toward < 0.2 deg)

Usage:
    # First time: prepare dataset (downloads tar from GCS, no GPU)
    uv run modal run modal/train_skew_estimator.py --prepare-data

    # Quick test (2 epochs on small subset)
    uv run modal run modal/train_skew_estimator.py --test

    # Full training (detached)
    uv run modal run --detach modal/train_skew_estimator.py

    # Resume from checkpoint
    uv run modal run --detach modal/train_skew_estimator.py --resume RUN_ID
"""

from __future__ import annotations

import json
import subprocess  # nosec B404
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import modal

if TYPE_CHECKING:
    import torch

# ---------------------------------------------------------------------------
# Modal app setup
# ---------------------------------------------------------------------------

app = modal.App("skew-estimator-training")

data_volume = modal.Volume.from_name("skew-training-data", create_if_missing=True)
results_volume = modal.Volume.from_name(
    "skew-estimator-results", create_if_missing=True
)

gcs_secret = modal.Secret.from_name("gcs-credentials")

# GCS bucket for training data archive
GCS_BUCKET = "image_detection_b"
GCS_TAR_BLOB = "skew_training.tar"

# Common file name constants (S1192: avoid duplicate string literals)
LABELS_FILE = "labels.json"

training_image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch==2.5.1",
    "torchvision==0.20.1",
    "numpy<2.0",
    "Pillow>=11.0.0",
    "timm>=1.0.0",
    "albumentations>=1.3.0",
    "scikit-learn>=1.3.0",
    "google-cloud-storage>=2.10.0",
    "onnx>=1.14.0",
    "onnxruntime>=1.17.0",
    "scipy>=1.11.0",
)


# ---------------------------------------------------------------------------
# Training config
# ---------------------------------------------------------------------------


@dataclass
class TrainingConfig:
    """Training hyperparameters.

    Attributes:
        epochs: Total training epochs.
        batch_size: Batch size per GPU.
        learning_rate: Peak learning rate for OneCycleLR.
        warmup_epochs: LR warmup period.
        qat_start_epoch: Epoch to begin QAT.
        loss_weights: Multi-task loss weight dict.
        patience: Early stopping patience.
        critical_zone_weight: Extra weight for |angle| < 2 deg samples.
        input_size: Model input spatial size (224 standard for MobileNet).
        backbone: timm backbone name.
        pretrained: Use ImageNet pretrained weights.
        num_workers: DataLoader workers.
        test_mode: If True, run only 2 epochs with tiny subset.
    """

    epochs: int = 50
    batch_size: int = 128
    learning_rate: float = 5e-4
    warmup_epochs: int = 5
    qat_start_epoch: int = 30
    loss_weights: dict[str, float] = field(
        default_factory=lambda: {
            "orientation": 0.2,
            "skew_classification": 0.3,
            "skew_regression": 0.5,
        }
    )
    patience: int = 10
    critical_zone_weight: float = 2.0
    input_size: int = 224
    backbone: str = "mobilenetv4_conv_small"
    pretrained: bool = True
    num_workers: int = 4
    test_mode: bool = False


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


def build_skew_dataset(
    data_dir: str,
    split: str,
    input_size: int = 224,
    augment: bool = False,
) -> torch.utils.data.Dataset:
    """Build a skew training dataset from image directory + labels.json.

    Expected structure::

        data_dir/{split}/images/*.jpg
        data_dir/{split}/labels.json  # {filename: {angle, orientation, ...}}

    Args:
        data_dir: Root dataset directory.
        split: 'train', 'val', or 'test'.
        input_size: Image resize target.
        augment: Apply training augmentations.

    Returns:
        PyTorch Dataset instance.
    """
    import torch
    from PIL import Image
    from torch.utils.data import Dataset
    from torchvision import transforms

    split_dir = Path(data_dir) / split
    images_dir = split_dir / "images"
    labels_path = split_dir / LABELS_FILE

    with labels_path.open() as f:
        all_labels = json.load(f)

    # Filter labels to only include images that exist on disk
    existing_images = {p.name for p in images_dir.iterdir() if p.is_file()}
    labels = {k: v for k, v in all_labels.items() if k in existing_images}
    if len(labels) < len(all_labels):
        print(
            f"  [{split}] Filtered labels: {len(labels)}/{len(all_labels)}"
            " (images on disk)"
        )

    if augment:
        transform = transforms.Compose(
            [
                transforms.RandomResizedCrop(input_size, scale=(0.85, 1.0)),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
    else:
        transform = transforms.Compose(
            [
                transforms.Resize((input_size, input_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

    orient_map = {0: 0, 90: 1, 180: 2, 270: 3}

    class SkewDataset(Dataset):  # type: ignore[type-arg]
        def __init__(self) -> None:
            self.filenames = list(labels.keys())
            self.labels = labels

        def __len__(self) -> int:
            return len(self.filenames)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            fname = self.filenames[idx]
            label = self.labels[fname]

            img_path = images_dir / fname
            img = Image.open(img_path).convert("RGB")
            img_tensor = transform(img)

            angle = float(label["angle"])
            orientation = int(label.get("orientation", 0))

            # Track source type for per-domain metrics
            source_type = label.get("source_type", "synthetic")
            is_natural = 1 if source_type == "natural_scan" else 0

            return {
                "image": img_tensor,
                "angle": torch.tensor(angle, dtype=torch.float32),
                "orientation": torch.tensor(
                    orient_map.get(orientation, 0), dtype=torch.long
                ),
                "is_natural": torch.tensor(is_natural, dtype=torch.long),
                "filename": fname,
            }

    return SkewDataset()


# ---------------------------------------------------------------------------
# Data preparation (CPU only, no GPU needed)
# ---------------------------------------------------------------------------


@app.function(
    image=training_image,
    volumes={"/data": data_volume},
    secrets=[gcs_secret],
    timeout=3600,
)
def prepare_dataset() -> dict[str, Any]:
    """Download tar archive from GCS and cache on persistent Modal Volume.

    Caches the tar file itself (single 2GB file) on the Volume.
    Extraction to /tmp happens at training time — fast and avoids
    committing 90K small files to the Volume.

    Returns:
        Dict with download stats.
    """
    tar_on_volume = Path("/data/skew_training.tar")

    if tar_on_volume.exists():
        size_gb = tar_on_volume.stat().st_size / (1024**3)
        print(f"Tar already on volume: {size_gb:.2f} GB. Skipping download.")
        return {"status": "already_exists", "size_gb": round(size_gb, 2)}

    _setup_gcs_credentials()

    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_TAR_BLOB)

    print(f"Downloading gs://{GCS_BUCKET}/{GCS_TAR_BLOB} to volume...")
    start = time.monotonic()
    tar_on_volume.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(tar_on_volume))
    size_gb = tar_on_volume.stat().st_size / (1024**3)
    dl_time = time.monotonic() - start
    print(f"Downloaded {size_gb:.2f} GB in {dl_time:.0f}s")

    data_volume.commit()
    print("Tar committed to volume (single file, fast commit)")

    return {
        "status": "downloaded",
        "download_seconds": round(dl_time),
        "size_gb": round(size_gb, 2),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auto_batch_size(backbone: str, input_size: int) -> int:
    """Select batch size for L4 24GB VRAM based on model + resolution.

    Empirical lookup to avoid OOM while maximizing throughput.
    """
    is_large = "large" in backbone
    is_medium = "medium" in backbone

    if is_large:
        # ~31M params, heavy
        return 32 if input_size <= 224 else 16
    if is_medium:
        # ~8.4M params
        if input_size <= 224:
            return 64
        if input_size <= 320:
            return 32
        return 16
    # conv_small / conv_small_050 (~1-2.5M params)
    if input_size <= 224:
        return 128
    if input_size <= 320:
        return 96
    return 64


def _benchmark_cpu_inference(
    model: torch.nn.Module,
    config: TrainingConfig,
    _run_id: str,
) -> dict[str, float]:
    """Time CPU inference for the trained model.

    Runs 50 iterations (single image) after warmup and reports
    mean, p50, p95, and p99 latencies in milliseconds.

    Returns:
        Dict with cpu_mean_ms, cpu_p50_ms, cpu_p95_ms, cpu_p99_ms.
    """
    import time

    import torch

    model.eval()
    model.cpu()
    dummy = torch.randn(1, 3, config.input_size, config.input_size)

    # Warmup
    with torch.no_grad():
        for _ in range(5):
            model(dummy)

    # Timed runs
    times_ms: list[float] = []
    with torch.no_grad():
        for _ in range(50):
            start = time.perf_counter()
            model(dummy)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed_ms)

    times_ms.sort()
    n = len(times_ms)
    result = {
        "cpu_mean_ms": round(sum(times_ms) / n, 2),
        "cpu_p50_ms": round(times_ms[n // 2], 2),
        "cpu_p95_ms": round(times_ms[int(n * 0.95)], 2),
        "cpu_p99_ms": round(times_ms[int(n * 0.99)], 2),
        "backbone": config.backbone,
        "input_size": config.input_size,
    }
    print(
        f"CPU inference: mean={result['cpu_mean_ms']:.1f}ms "
        f"p50={result['cpu_p50_ms']:.1f}ms "
        f"p95={result['cpu_p95_ms']:.1f}ms"
    )
    return result


# ---------------------------------------------------------------------------
# Training helper functions
# ---------------------------------------------------------------------------


def _build_skew_config(
    test: bool, backbone: str, input_size: int, epochs: int, batch_size: int
) -> TrainingConfig:
    """Build TrainingConfig with CLI overrides applied."""
    config = TrainingConfig(test_mode=test)
    if test:
        config.epochs = 2
        config.batch_size = 8
        config.warmup_epochs = 0

    if backbone:
        config.backbone = backbone
    if input_size > 0:
        config.input_size = input_size
    if epochs > 0:
        config.epochs = epochs
    if batch_size > 0:
        config.batch_size = batch_size
    elif not test:
        config.batch_size = _auto_batch_size(config.backbone, config.input_size)

    return config


def _load_skew_data(test: bool) -> str:
    """Load or download training data. Returns data_dir path."""
    if test:
        data_dir = "/tmp/skew_test"  # nosec B108
        _download_gcs_individual(data_dir, test_mode=True)
        return data_dir

    data_dir = "/tmp/skew_training"  # nosec B108
    labels_check = Path(data_dir) / "train" / LABELS_FILE

    if not labels_check.exists():
        tar_on_volume = Path("/data/skew_training.tar")
        if not tar_on_volume.exists():
            msg = (
                "Tar archive not found on volume. "
                "Run with --prepare-data first:\n"
                "  uv run modal run modal/train_skew_estimator.py --prepare-data"
            )
            raise FileNotFoundError(msg)

        print(f"Extracting tar from volume to {data_dir}...")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        start_extract = time.monotonic()
        subprocess.run(  # nosec B603 B607
            ["tar", "xf", str(tar_on_volume), "-C", data_dir],
            check=True,
        )
        print(f"Extracted in {time.monotonic() - start_extract:.0f}s")

    img_dir = Path(data_dir) / "train" / "images"
    count = sum(1 for f in img_dir.iterdir() if f.is_file())
    print(f"Dataset ready: {count:,} train images")
    return data_dir


def _build_skew_model(config: TrainingConfig, num_bins: int, device: Any) -> tuple:
    """Build SkewEstimatorNet and return (model_instance, model_class)."""
    import timm
    import torch
    import torch.nn as nn

    class SkewEstimatorNet(nn.Module):
        """MobileNetV4-Conv-S with 3 heads for skew estimation."""

        def __init__(self) -> None:
            super().__init__()
            self.backbone = timm.create_model(
                config.backbone,
                pretrained=config.pretrained,
                num_classes=0,
                global_pool="avg",
            )
            with torch.no_grad():
                dummy = torch.randn(2, 3, config.input_size, config.input_size)
                feat_dim = self.backbone(dummy).shape[-1]

            self.orientation_head = nn.Sequential(
                nn.Dropout(p=0.2), nn.Linear(feat_dim, 4)
            )
            self.skew_bin_head = nn.Sequential(
                nn.Dropout(p=0.2), nn.Linear(feat_dim, num_bins)
            )
            self.skew_regression_head = nn.Sequential(
                nn.Dropout(p=0.1),
                nn.Linear(feat_dim, 128),
                nn.ReLU(inplace=True),
                nn.Linear(128, 1),
            )

        def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
            features = self.backbone(x)
            return {
                "orientation_logits": self.orientation_head(features),
                "skew_bin_logits": self.skew_bin_head(features),
                "skew_regression": self.skew_regression_head(features),
            }

    model = SkewEstimatorNet().to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    return model, SkewEstimatorNet


def _build_skew_loaders(data_dir: str, config: TrainingConfig) -> tuple:
    """Build train and val DataLoaders."""
    from torch.utils.data import DataLoader

    train_dataset = build_skew_dataset(
        data_dir, "train", config.input_size, augment=True
    )
    val_dataset = build_skew_dataset(data_dir, "val", config.input_size, augment=False)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )
    return train_loader, val_loader


def _build_skew_optimizer(
    model: Any, config: TrainingConfig, steps_per_epoch: int
) -> tuple:
    """Build optimizer and OneCycleLR scheduler."""
    import torch

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=0.01
    )
    total_steps = config.epochs * steps_per_epoch
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=config.learning_rate,
        total_steps=max(1, total_steps),
        pct_start=min(config.warmup_epochs / max(config.epochs, 1), 0.3),
        anneal_strategy="cos",
    )
    return optimizer, scheduler


def _maybe_resume_skew(model, optimizer, scheduler, resume_run_id, device):
    """Load checkpoint if resuming. Returns state dict."""
    import torch

    state = {
        "start_epoch": 0,
        "best_val_mae": float("inf"),
        "patience_counter": 0,
        "history": [],
        "run_id": resume_run_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    if not resume_run_id:
        return state

    ckpt_path = f"/results/{resume_run_id}/last_checkpoint.pt"
    if not Path(ckpt_path).exists():
        print(f"WARNING: Checkpoint not found at {ckpt_path}, starting fresh")
        return state

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"], strict=False)
    try:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    except (ValueError, KeyError):
        print("  Optimizer/scheduler state mismatch (QAT), resetting")
    state["start_epoch"] = ckpt["epoch"] + 1
    state["best_val_mae"] = ckpt["best_val_mae"]
    state["patience_counter"] = ckpt.get("patience_counter", 0)
    state["history"] = ckpt.get("history", [])
    print(
        f"Resumed from epoch {state['start_epoch']} (best MAE={state['best_val_mae']:.4f})"
    )
    return state


def _run_skew_training_loop(
    model,
    train_loader,
    val_loader,
    optimizer,
    scheduler,
    config,
    bin_centers_tensor,
    bin_half_widths_tensor,
    device,
    test,
    state,
):
    """Execute the training loop and return updated state."""
    import torch
    import torch.nn.functional as F

    run_id = state["run_id"]
    best_val_mae = state["best_val_mae"]
    patience_counter = state["patience_counter"]
    history = state["history"]

    for epoch in range(state["start_epoch"], config.epochs):
        model.train()

        # QAT transition
        if epoch == config.qat_start_epoch and not test:
            print(f"Epoch {epoch}: Enabling QAT")
            model.cpu()
            model.qconfig = torch.ao.quantization.get_default_qat_qconfig("x86")  # type: ignore[attr-defined]
            torch.ao.quantization.prepare_qat(model, inplace=True)
            model.to(device)

        train_loss_sum = 0.0
        train_samples = 0

        for batch in train_loader:
            images = batch["image"].to(device)
            angles = batch["angle"].to(device)
            orientations = batch["orientation"].to(device)

            with torch.no_grad():
                diffs = (angles.unsqueeze(1) - bin_centers_tensor.unsqueeze(0)).abs()
                bin_labels = diffs.argmin(dim=1)

            outputs = model(images)

            orient_loss = F.cross_entropy(outputs["orientation_logits"], orientations)
            bin_loss = F.cross_entropy(outputs["skew_bin_logits"], bin_labels)

            gt_bin_centers = bin_centers_tensor[bin_labels]
            target_residuals = angles - gt_bin_centers
            pred_residuals = outputs["skew_regression"].squeeze(-1)
            per_sample_loss = F.smooth_l1_loss(
                pred_residuals, target_residuals, reduction="none"
            )

            weights = torch.ones_like(angles)
            weights[angles.abs() < 2.0] = config.critical_zone_weight
            reg_loss = (per_sample_loss * weights).mean()

            total_loss = (
                config.loss_weights["orientation"] * orient_loss
                + config.loss_weights["skew_classification"] * bin_loss
                + config.loss_weights["skew_regression"] * reg_loss
            )

            optimizer.zero_grad()
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            train_loss_sum += total_loss.item() * images.size(0)
            train_samples += images.size(0)

        avg_train_loss = train_loss_sum / max(train_samples, 1)
        val_metrics = _evaluate(
            model, val_loader, bin_centers_tensor, bin_half_widths_tensor, device
        )
        val_mae = val_metrics["mae"]

        history.append(
            {
                "epoch": epoch,
                "train_loss": round(avg_train_loss, 5),
                "val_mae": round(val_mae, 4),
                "val_srcc": round(val_metrics["srcc"], 4),
                "val_orient_acc": round(val_metrics["orient_acc"], 4),
                "val_within_05": round(val_metrics["within_05"], 4),
                "val_synth_mae": round(val_metrics["synth_mae"], 4),
                "val_natural_mae": round(val_metrics["natural_mae"], 4),
                "lr": optimizer.param_groups[0]["lr"],
            }
        )

        domain_info = ""
        if val_metrics["natural_count"] > 0:
            domain_info = f" | synth={val_metrics['synth_mae']:.3f} nat={val_metrics['natural_mae']:.3f}"

        print(
            f"Epoch {epoch:3d}/{config.epochs} | loss={avg_train_loss:.4f} | "
            f"MAE={val_mae:.3f} | SRCC={val_metrics['srcc']:.3f} | "
            f"orient_acc={val_metrics['orient_acc']:.3f} | within_0.5={val_metrics['within_05']:.3f}"
            f"{domain_info}"
        )

        ckpt_dir = Path(f"/results/{run_id}")
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "best_val_mae": best_val_mae,
                "patience_counter": patience_counter,
                "history": history,
                "config": asdict(config),
            },
            str(ckpt_dir / "last_checkpoint.pt"),
        )

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            patience_counter = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_mae": val_mae,
                    "config": asdict(config),
                },
                str(ckpt_dir / "best_model.pt"),
            )
            print(f"  -> Saved best model (MAE={val_mae:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= config.patience and not test:
                print(f"Early stopping at epoch {epoch} (patience={config.patience})")
                break

        results_volume.commit()

    state["best_val_mae"] = best_val_mae
    state["patience_counter"] = patience_counter
    state["history"] = history
    return state


def _run_skew_post_training(
    skew_estimator_cls,
    data_dir,
    config,
    bin_centers,
    bin_half_widths,
    bin_centers_tensor,
    bin_half_widths_tensor,
    device,
    state,
):
    """Post-training: test eval, ONNX export, benchmark, save results."""
    import torch

    run_id = state["run_id"]

    eval_model = skew_estimator_cls().to(device)
    best_ckpt_path = f"/results/{run_id}/best_model.pt"
    if Path(best_ckpt_path).exists():
        ckpt = torch.load(best_ckpt_path, map_location=device, weights_only=True)
        eval_model.load_state_dict(ckpt["model_state_dict"])

    test_metrics = _run_test_evaluation(
        eval_model,
        data_dir,
        config,
        bin_centers,
        bin_half_widths,
        bin_centers_tensor,
        bin_half_widths_tensor,
        device,
        run_id,
    )

    fp32_path = _export_onnx(eval_model, config, run_id)
    cpu_bench = _benchmark_cpu_inference(eval_model, config, run_id)

    history_path = f"/results/{run_id}/training_history.json"
    with open(history_path, "w") as f:
        json.dump(
            {
                "config": asdict(config),
                "history": state["history"],
                "best_val_mae": state["best_val_mae"],
                "test_metrics": test_metrics,
                "cpu_benchmark": cpu_bench,
                "bin_centers": bin_centers,
                "bin_half_widths": bin_half_widths,
                "run_id": run_id,
            },
            f,
            indent=2,
        )

    results_volume.commit()

    return {
        "run_id": run_id,
        "best_val_mae": state["best_val_mae"],
        "test_metrics": test_metrics,
        "cpu_benchmark": cpu_bench,
        "epochs_trained": len(state["history"]),
        "fp32_onnx": fp32_path,
    }


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


@app.function(
    image=training_image,
    gpu="L4",
    timeout=14400,  # 4 hours (no download overhead, pure training)
    volumes={
        "/data": data_volume,
        "/results": results_volume,
    },
    secrets=[gcs_secret],  # Needed for test mode GCS fallback
)
def train(
    test: bool = False,
    resume_run_id: str = "",
    backbone: str = "",
    input_size: int = 0,
    epochs: int = 0,
    batch_size: int = 0,
) -> dict[str, Any]:
    """Run SkewNet training on cached dataset.

    Requires ``prepare_dataset()`` to have been run first (or uses
    GCS individual-file fallback for test mode).

    Args:
        test: Run quick 2-epoch test with small subset.
        resume_run_id: Resume from a previous run's checkpoint.
        backbone: Override timm backbone name (ablation).
        input_size: Override input resolution (ablation).
        epochs: Override epoch count (ablation).
        batch_size: Override batch size.

    Returns:
        Dict with training metrics and model paths.
    """
    import torch

    config = _build_skew_config(test, backbone, input_size, epochs, batch_size)

    print(f"Training config: epochs={config.epochs}, batch={config.batch_size}")
    print(f"Backbone: {config.backbone} @ {config.input_size}px")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    data_dir = _load_skew_data(test)

    bin_centers = _compute_bin_centers()
    bin_half_widths = _compute_bin_half_widths()
    num_bins = len(bin_centers)
    print(f"Bin config: {num_bins} bins")

    device = torch.device("cuda")
    model, skew_estimator_cls = _build_skew_model(config, num_bins, device)

    train_loader, val_loader = _build_skew_loaders(data_dir, config)

    optimizer, scheduler = _build_skew_optimizer(model, config, len(train_loader))

    bin_centers_tensor = torch.tensor(bin_centers, dtype=torch.float32, device=device)
    bin_half_widths_tensor = torch.tensor(
        bin_half_widths, dtype=torch.float32, device=device
    )

    train_state = _maybe_resume_skew(model, optimizer, scheduler, resume_run_id, device)

    train_state = _run_skew_training_loop(
        model,
        train_loader,
        val_loader,
        optimizer,
        scheduler,
        config,
        bin_centers_tensor,
        bin_half_widths_tensor,
        device,
        test,
        train_state,
    )

    return _run_skew_post_training(
        skew_estimator_cls,
        data_dir,
        config,
        bin_centers,
        bin_half_widths,
        bin_centers_tensor,
        bin_half_widths_tensor,
        device,
        train_state,
    )


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------


def _evaluate(
    model: torch.nn.Module,
    loader: torch.utils.data.DataLoader,
    bin_centers_tensor: torch.Tensor,
    bin_half_widths_tensor: torch.Tensor,
    device: torch.device,
) -> dict[str, float]:
    """Evaluate model on a data loader.

    Returns:
        Dict with overall and per-domain (synthetic/natural) metrics:
        mae, srcc, orient_acc, within_05, synth_mae, natural_mae.
    """
    import numpy as np
    import torch
    from scipy import stats as sp_stats

    model.eval()
    all_gt: list[float] = []
    all_pred: list[float] = []
    all_errors: list[float] = []
    synth_errors: list[float] = []
    natural_errors: list[float] = []
    orient_correct = 0
    orient_total = 0

    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device)
            angles = batch["angle"].to(device)
            orientations = batch["orientation"].to(device)
            is_natural = batch["is_natural"].to(device)

            outputs = model(images)

            # Orientation accuracy
            orient_preds = outputs["orientation_logits"].argmax(dim=1)
            orient_correct += (orient_preds == orientations).sum().item()
            orient_total += orientations.size(0)

            # Skew prediction with per-bin residual clamping
            bin_preds = outputs["skew_bin_logits"].argmax(dim=1)
            residuals = outputs["skew_regression"].squeeze(-1)

            pred_half_widths = bin_half_widths_tensor[bin_preds]
            clamped_residuals = torch.clamp(
                residuals, -pred_half_widths, pred_half_widths
            )
            pred_bin_centers = bin_centers_tensor[bin_preds]
            pred_angles = pred_bin_centers + clamped_residuals

            errors = (pred_angles - angles).abs()

            all_gt.extend(angles.cpu().tolist())
            all_pred.extend(pred_angles.cpu().tolist())
            all_errors.extend(errors.cpu().tolist())

            # Per-domain error tracking
            nat_mask = is_natural == 1
            syn_mask = is_natural == 0
            if nat_mask.any():
                natural_errors.extend(errors[nat_mask].cpu().tolist())
            if syn_mask.any():
                synth_errors.extend(errors[syn_mask].cpu().tolist())

    mae = float(np.mean(all_errors)) if all_errors else float("inf")
    orient_acc = orient_correct / max(orient_total, 1)

    srcc = 0.0
    if len(all_gt) > 2:
        srcc, _ = sp_stats.spearmanr(all_gt, all_pred)

    within_05 = float(np.mean(np.array(all_errors) <= 0.5)) if all_errors else 0.0

    synth_mae = float(np.mean(synth_errors)) if synth_errors else float("nan")
    natural_mae = float(np.mean(natural_errors)) if natural_errors else float("nan")

    return {
        "mae": mae,
        "srcc": float(srcc),
        "orient_acc": orient_acc,
        "within_05": within_05,
        "synth_mae": synth_mae,
        "natural_mae": natural_mae,
        "synth_count": len(synth_errors),
        "natural_count": len(natural_errors),
    }


def _run_test_evaluation(
    model: torch.nn.Module,
    data_dir: str,
    config: TrainingConfig,
    _bin_centers: list[float],
    _bin_half_widths: list[float],
    bin_centers_tensor: torch.Tensor,
    bin_half_widths_tensor: torch.Tensor,
    device: torch.device,
    _run_id: str,
) -> dict[str, Any]:
    """Run test set evaluation using best checkpoint.

    Returns:
        Dict with test metrics, or empty dict if no test set.
    """
    from torch.utils.data import DataLoader

    test_dir = Path(data_dir) / "test"
    if not (test_dir / LABELS_FILE).exists():
        print("\nNo test set found, skipping test evaluation.")
        return {}

    print("\nEvaluating on test set...")

    # Model should already have best checkpoint loaded by caller
    # (handles QAT/non-QAT mismatch by using a fresh model)
    model.to(device)

    test_dataset = build_skew_dataset(
        data_dir, "test", config.input_size, augment=False
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    metrics = _evaluate(
        model, test_loader, bin_centers_tensor, bin_half_widths_tensor, device
    )

    test_metrics = {
        "test_mae": round(metrics["mae"], 4),
        "test_srcc": round(metrics["srcc"], 4),
        "test_orient_acc": round(metrics["orient_acc"], 4),
        "test_within_05": round(metrics["within_05"], 4),
        "test_synth_mae": round(metrics["synth_mae"], 4),
        "test_natural_mae": round(metrics["natural_mae"], 4),
        "test_synth_count": metrics["synth_count"],
        "test_natural_count": metrics["natural_count"],
        "test_samples": metrics["synth_count"] + metrics["natural_count"],
    }

    domain_info = ""
    if metrics["natural_count"] > 0:
        domain_info = (
            f" | synth={metrics['synth_mae']:.3f} nat={metrics['natural_mae']:.3f}"
        )

    print(
        f"  Test MAE={metrics['mae']:.3f} | SRCC={metrics['srcc']:.3f} | "
        f"orient_acc={metrics['orient_acc']:.3f} | "
        f"within_0.5={metrics['within_05']:.3f}"
        f"{domain_info}"
    )

    return test_metrics


def _export_onnx(
    model: torch.nn.Module,
    config: TrainingConfig,
    run_id: str,
) -> str:
    """Export model to ONNX FP32 format.

    Args:
        model: Trained model.
        config: Training config.
        run_id: Run identifier for output path.

    Returns:
        Path to the exported ONNX file.
    """
    import torch

    print("Exporting ONNX model...")
    model.eval()
    model.cpu()

    dummy = torch.randn(1, 3, config.input_size, config.input_size)

    fp32_path = f"/results/{run_id}/skew_estimator_fp32.onnx"
    Path(fp32_path).parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy,
        fp32_path,
        opset_version=17,
        input_names=["input"],
        output_names=[
            "orientation_logits",
            "skew_bin_logits",
            "skew_regression",
        ],
        dynamic_axes={
            "input": {0: "batch_size"},
            "orientation_logits": {0: "batch_size"},
            "skew_bin_logits": {0: "batch_size"},
            "skew_regression": {0: "batch_size"},
        },
    )
    print(f"FP32 ONNX saved to {fp32_path}")
    return fp32_path


# ---------------------------------------------------------------------------
# GCS download helpers
# ---------------------------------------------------------------------------


def _setup_gcs_credentials() -> None:
    """Configure GCS credentials from Modal secret environment variable."""
    import base64
    import os
    import tempfile

    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key_b64:
        gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
        ) as f:
            f.write(gcp_sa_key_json)
            f.flush()
            credentials_path = f.name
        os.chmod(credentials_path, 0o600)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        print("  GCS credentials configured from GCP_SA_KEY")
    else:
        print("  WARNING: GCP_SA_KEY not found, trying default credentials")


def _download_gcs_individual(data_dir: str, test_mode: bool = False) -> None:
    """Download dataset as individual files from GCS (test mode fallback).

    For production use, prefer ``prepare_dataset()`` which downloads a
    single tar archive.

    Args:
        data_dir: Local directory to download dataset into.
        test_mode: If True, download only 100 images per split.
    """
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google.cloud import storage

    _setup_gcs_credentials()

    local_root = Path(data_dir)
    local_root.mkdir(parents=True, exist_ok=True)

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    gcs_prefix = "skew_training/"
    total_downloaded = 0

    for split in ["train", "val", "test"]:
        split_prefix = f"{gcs_prefix}{split}/"
        local_split = local_root / split
        local_images = local_split / "images"
        local_images.mkdir(parents=True, exist_ok=True)

        # Download labels.json
        labels_blob = bucket.blob(f"{split_prefix}labels.json")
        labels_local = local_split / LABELS_FILE
        if labels_blob.exists():
            labels_blob.download_to_filename(str(labels_local))
            print(f"  Downloaded {split}/labels.json")
        else:
            print(f"  WARNING: {split}/labels.json not found in GCS")
            continue

        # Download images
        blobs = list(bucket.list_blobs(prefix=f"{split_prefix}images/"))
        image_blobs = [b for b in blobs if b.name.endswith((".jpg", ".png"))]

        if test_mode:
            image_blobs = image_blobs[:100]
            print(f"  [TEST] Limiting {split} to {len(image_blobs)} images")

        def _download_blob(blob: Any, _images_dir: Path = local_images) -> str:
            filename = os.path.basename(blob.name)
            local_path = _images_dir / filename
            if not local_path.exists():
                blob.download_to_filename(str(local_path))
            return filename

        downloaded = 0
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = {executor.submit(_download_blob, b): b for b in image_blobs}
            for future in as_completed(futures):
                future.result()
                downloaded += 1
                if downloaded % 5000 == 0:
                    print(f"  [{split}] Downloaded {downloaded}/{len(image_blobs)}")

        total_downloaded += downloaded
        print(f"  [{split}] Complete: {downloaded} images")

    print(f"GCS download complete: {total_downloaded} images total")


# ---------------------------------------------------------------------------
# Bin configuration
# ---------------------------------------------------------------------------


def _compute_bin_centers() -> list[float]:
    """Compute non-uniform bin centers matching skew_estimation.yaml.

    Zones:
        - Extreme: [-45, -15] and [15, 45] at 5.0 deg width (6 bins each)
        - Moderate: [-15, -5] and [5, 15] at 2.0 deg width (5 bins each)
        - Critical: [-5, 5] at 0.5 deg width (20 bins)

    Returns:
        List of 42 bin centers ordered from -45 to +45 degrees.
    """
    centers: list[float] = []
    for start, _end, width, count in _BIN_ZONES:
        for i in range(count):
            centers.append(round(start + (i + 0.5) * width, 4))
    return centers


def _compute_bin_half_widths() -> list[float]:
    """Compute per-bin half-widths for residual clamping.

    Each bin's regression residual is clamped to [-half_width, +half_width]
    at inference time. This ensures the regression head can cover the full
    range within each bin without bleeding into adjacent bins.

    Returns:
        List of 42 half-widths matching the bin centers.
    """
    half_widths: list[float] = []
    for _start, _end, width, count in _BIN_ZONES:
        for _ in range(count):
            half_widths.append(width / 2.0)
    return half_widths


# Zone definitions: (start_deg, end_deg, bin_width, num_bins)
_BIN_ZONES = [
    (-45.0, -15.0, 5.0, 6),  # extreme_neg
    (-15.0, -5.0, 2.0, 5),  # moderate_neg
    (-5.0, 5.0, 0.5, 20),  # critical
    (5.0, 15.0, 2.0, 5),  # moderate_pos
    (15.0, 45.0, 5.0, 6),  # extreme_pos
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@app.local_entrypoint()
def main(
    test: bool = False,
    prepare_data: bool = False,
    resume: str = "",
    backbone: str = "",
    input_size: int = 0,
    epochs: int = 0,
    batch_size: int = 0,
) -> None:
    """CLI entry point for Modal training.

    Args:
        test: Run quick 2-epoch test mode.
        prepare_data: Download dataset to persistent volume (run once).
        resume: Resume from a previous run ID.
        backbone: Override timm backbone (e.g. mobilenetv4_conv_medium).
        input_size: Override input resolution (e.g. 384).
        epochs: Override epoch count (e.g. 10 for ablation).
        batch_size: Override batch size (auto-scaled if omitted).
    """
    if prepare_data:
        print("Caching tar archive on Modal volume...")
        result = prepare_dataset.remote()
        print(f"  Status: {result['status']}")
        if "size_gb" in result:
            print(f"  Size: {result['size_gb']} GB")
    else:
        print("Starting SkewNet training on Modal...")
        if backbone or input_size or epochs:
            bk = backbone or "mobilenetv4_conv_small"
            sz = input_size or 224
            ep = epochs or 50
            print(f"  Ablation: {bk} @ {sz}px, {ep} epochs")

        result = train.remote(
            test=test,
            resume_run_id=resume,
            backbone=backbone,
            input_size=input_size,
            epochs=epochs,
            batch_size=batch_size,
        )
        print("\nTraining complete!")
        print(f"  Run ID: {result['run_id']}")
        print(f"  Best val MAE: {result['best_val_mae']:.4f}")
        print(f"  Epochs: {result['epochs_trained']}")
        print(f"  ONNX: {result['fp32_onnx']}")
        if result.get("cpu_benchmark"):
            cb = result["cpu_benchmark"]
            print(
                f"  CPU latency: mean={cb['cpu_mean_ms']:.1f}ms "
                f"p50={cb['cpu_p50_ms']:.1f}ms "
                f"p95={cb['cpu_p95_ms']:.1f}ms"
            )
        if result.get("test_metrics"):
            tm = result["test_metrics"]
            print(f"  Test MAE: {tm['test_mae']:.4f}")
            print(f"  Test SRCC: {tm['test_srcc']:.4f}")
            print(f"  Test orient acc: {tm['test_orient_acc']:.4f}")
            print(f"  Test within 0.5 deg: {tm['test_within_05']:.4f}")
            if tm.get("test_natural_count", 0) > 0:
                print(f"  Test synth MAE: {tm['test_synth_mae']:.4f}")
                print(f"  Test natural MAE: {tm['test_natural_mae']:.4f}")
