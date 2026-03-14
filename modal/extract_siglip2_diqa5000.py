"""Extract SigLIP2 multi-task predictions and embeddings for full DIQA-5000 dataset.

Runs SigLIP2MultiTaskDetector on all 5,000 DIQA-5000 images (train/val/test)
to extract embeddings, IQA predictions, classification outputs, and severity
scores. Fits a new OOD detector on train+val embeddings and calibrates on test.

Outputs:
    - Per-split JSONL files with all predictions (no embeddings)
    - Per-split NPZ files with 768-dim embeddings
    - Fitted OOD detector (ood_detector_v2.npz)
    - Summary metrics JSON (SRCC/PLCC/MAE per split + OOD stats)

Usage:
    # Quick test (5 images per split)
    uv run modal run modal/extract_siglip2_diqa5000.py --limit 5

    # Full extraction (detached)
    uv run modal run --detach modal/extract_siglip2_diqa5000.py

    # Single split only
    uv run modal run modal/extract_siglip2_diqa5000.py --split test --limit 10

    # Monitor logs
    uv run modal app logs siglip2-diqa5000-extraction --follow
"""

from __future__ import annotations

import base64
import time
from datetime import timezone
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Modal app definition
# ---------------------------------------------------------------------------

app = modal.App("siglip2-diqa5000-extraction")

# Persistent volumes
# Checkpoint is on siglip2-iqa-results at siglip2/siglip2_iqa_best.pt
# (dociq-checkpoints volume exists but is empty)
checkpoint_volume = modal.Volume.from_name(
    "siglip2-iqa-results", create_if_missing=True
)
output_volume = modal.Volume.from_name(
    "siglip2-diqa5000-outputs", create_if_missing=True
)
diqa5000_volume = modal.Volume.from_name("diqa5000-original", create_if_missing=True)

# GCS configuration (matches train_siglip2_iqa_v2.py)
GCS_BUCKET = "image_detection_b"
GCS_PREFIX = "datasets/diqa-5000-original"
DIQA5000_SPLITS = ("train", "val", "test")
EXPECTED_COUNTS = {"train": 3500, "val": 500, "test": 1000}

# Checkpoint path within volume (saved by train_siglip2_iqa_v2.py)
CHECKPOINT_SUBPATH = "siglip2/siglip2_iqa_best.pt"

# Container image with all dependencies + source code
extraction_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "torchvision==0.20.1",
        "numpy<2.0",
        "Pillow>=11.0.0",
        "transformers>=4.51.0,<5.0",
        "accelerate>=1.0.0",
        "scipy",
        "scikit-learn>=1.3.0",
        "opencv-python-headless",
        "google-cloud-storage>=2.10.0",
        "pydantic>=2.0",
        "pydantic-settings>=2.0.0",
        "structlog>=23.1.0",
        "rich>=13.5.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "tqdm",
    )
    .add_local_dir("src", "/app/src")
)

# GCS credentials secret
gcs_secret = modal.Secret.from_name("gcs-credentials")


# ---------------------------------------------------------------------------
# GCS download helpers (adapted from train_siglip2_iqa_v2.py)
# ---------------------------------------------------------------------------


def _setup_gcs_credentials() -> str | None:
    """Decode GCS credentials from Modal secret and write to temp file."""
    import os
    import tempfile

    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key:
        print("Warning: GCP_SA_KEY not set, trying default credentials")
        return None

    sa_json = base64.b64decode(gcp_sa_key).decode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as cred_file:
        cred_file.write(sa_json)
        credentials_path = cred_file.name

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"GCS credentials configured at {credentials_path}")
    return credentials_path


def _is_diqa5000_cached(data_dir: Path) -> bool:
    """Check if all splits are already downloaded."""
    marker = data_dir / ".download_complete"
    if not marker.exists():
        return False
    all_csvs = all(
        (data_dir / split / f"{split}.csv").exists() for split in DIQA5000_SPLITS
    )
    if all_csvs:
        print("DIQA-5000 already cached, skipping download...")
        return True
    marker.unlink()
    return False


def _download_gcs_split(bucket: object, data_dir: Path, split: str) -> int:
    """Download a single split from GCS. Returns count of downloaded files."""
    split_dir = data_dir / split
    split_dir.mkdir(exist_ok=True)
    (split_dir / "res").mkdir(exist_ok=True)

    prefix = f"{GCS_PREFIX}/{split}/"
    downloaded = 0
    for blob in bucket.list_blobs(prefix=prefix):  # type: ignore[attr-defined]
        if blob.name.endswith("/"):
            continue
        relative_path = blob.name[len(prefix) :]
        if not relative_path:
            continue
        # Only download CSV and res/ images (skip ori/ to save time)
        if not (relative_path.endswith(".csv") or relative_path.startswith("res/")):
            continue
        local_file = split_dir / relative_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_file))
        downloaded += 1
        if downloaded % 500 == 0:
            print(f"  Downloaded {downloaded} files from {split}...")
    return downloaded


def _download_diqa5000(data_dir: Path) -> None:
    """Download DIQA-5000 dataset from GCS (all splits)."""
    from google.cloud import storage

    _setup_gcs_credentials()

    if _is_diqa5000_cached(data_dir):
        return

    print(f"Downloading DIQA-5000 from gs://{GCS_BUCKET}/{GCS_PREFIX}/")
    start = time.time()

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    data_dir.mkdir(parents=True, exist_ok=True)

    total = sum(_download_gcs_split(bucket, data_dir, s) for s in DIQA5000_SPLITS)
    elapsed = time.time() - start
    print(f"Downloaded {total} files in {elapsed:.1f}s")

    # Validate
    for split in DIQA5000_SPLITS:
        csv_path = data_dir / split / f"{split}.csv"
        if not csv_path.exists():
            msg = f"Missing CSV: {csv_path}"
            raise FileNotFoundError(msg)

    (data_dir / ".download_complete").touch()


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------


@app.function(
    gpu="L4",
    timeout=3600,
    memory=16384,
    image=extraction_image,
    volumes={
        "/checkpoints": checkpoint_volume,
        "/outputs": output_volume,
        "/data": diqa5000_volume,
    },
    secrets=[gcs_secret],
)
def extract_all_splits(
    limit: int | None = None,
    splits: list[str] | None = None,
) -> dict:
    """Extract SigLIP2 predictions and embeddings for all DIQA-5000 splits.

    Args:
        limit: Max images per split (for testing). None = all images.
        splits: Which splits to process. None = all.

    Returns:
        Summary metrics dict.
    """
    import csv
    import json
    import sys

    import cv2
    import numpy as np

    # Add source package to path (/app/src/image_preprocessing_detector/)
    sys.path.insert(0, "/app/src")

    # Save original np.array before import (openlid_integration monkey-patches it)
    _original_np_array = np.array

    from image_preprocessing_detector.detection.siglip2_multitask import (
        SigLIP2MultiTaskConfig,
        SigLIP2MultiTaskDetector,
    )

    # Restore np.array — the openlid monkey-patch breaks scipy/sklearn
    np.array = _original_np_array

    # 1. Download dataset
    data_dir = Path("/data/diqa5000")
    _download_diqa5000(data_dir)
    diqa5000_volume.commit()

    # 2. Load model
    checkpoint_path = f"/checkpoints/{CHECKPOINT_SUBPATH}"
    if not Path(checkpoint_path).exists():
        # Search for any .pt files in the volume
        available = list(Path("/checkpoints").rglob("*.pt"))
        msg = f"Checkpoint not found at {checkpoint_path}. Available: {[str(p) for p in available]}"
        raise FileNotFoundError(msg)

    print(f"Loading model from {checkpoint_path}...")
    config = SigLIP2MultiTaskConfig(device="cuda:0")
    detector = SigLIP2MultiTaskDetector(
        checkpoint_path=checkpoint_path,
        config=config,
    )

    # 3. Process each split
    target_splits = list(splits or DIQA5000_SPLITS)
    all_metrics: dict = {}
    output_dir = Path("/outputs")
    embeddings_dir = output_dir / "embeddings"
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    for split in target_splits:
        print(f"\n{'=' * 60}")
        print(f"Processing {split} split")
        print(f"{'=' * 60}")

        # Load ground truth
        csv_path = data_dir / split / f"{split}.csv"
        gt_data: dict[str, dict[str, float]] = {}
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                gt_data[row["res"]] = {
                    "overall": float(row["overall"]),
                    "sharpness": float(row["sharpness"]),
                    "color_fidelity": float(row["color_fidelity"]),
                }

        image_names_sorted = sorted(gt_data.keys())
        if limit:
            image_names_sorted = image_names_sorted[:limit]

        n_images = len(image_names_sorted)
        expected = EXPECTED_COUNTS.get(split, 0)
        if not limit and n_images != expected:
            print(f"Warning: Expected {expected} images, found {n_images}")

        # Range verification on first 5 images
        if split == target_splits[0]:
            print("\nRange verification (first 5 images)...")
            for img_name in image_names_sorted[:5]:
                img_path = data_dir / split / "res" / img_name
                img_bgr = cv2.imread(str(img_path))
                if img_bgr is None:
                    print(f"  FAILED to read: {img_path}")
                    continue
                pred = detector.predict(img_bgr, return_embedding=True)
                gt = gt_data[img_name]
                mu = pred.iqa_overall.mu
                rescaled = mu * 4.0 + 1.0
                print(
                    f"  {img_name}: mu={mu:.4f} -> MOS={rescaled:.3f} "
                    f"(GT={gt['overall']:.3f}), "
                    f"emb_shape={pred.embedding.shape if pred.embedding is not None else 'None'}"
                )
                if pred.embedding is not None:
                    assert pred.embedding.shape == (768,), (
                        f"Unexpected embedding shape: {pred.embedding.shape}"
                    )
                    assert not np.any(np.isnan(pred.embedding)), "NaN in embedding"
            print("Range verification passed.\n")

        # Run inference
        records: list[dict] = []
        embeddings: list[np.ndarray] = []
        processed_names: list[str] = []
        inference_times: list[float] = []

        for idx, img_name in enumerate(image_names_sorted):
            img_path = data_dir / split / "res" / img_name
            img_bgr = cv2.imread(str(img_path))
            if img_bgr is None:
                print(f"Warning: Failed to read {img_path}, skipping")
                continue

            pred = detector.predict(img_bgr, return_embedding=True)

            record = {
                "image": img_name,
                "split": split,
                "iqa_overall_mu": float(pred.iqa_overall.mu),
                "iqa_overall_sigma_sq": float(pred.iqa_overall.sigma_sq),
                "iqa_sharpness_mu": float(pred.iqa_sharpness.mu),
                "iqa_sharpness_sigma_sq": float(pred.iqa_sharpness.sigma_sq),
                "iqa_color_mu": float(pred.iqa_color.mu),
                "iqa_color_sigma_sq": float(pred.iqa_color.sigma_sq),
                "script_prediction": pred.script.predicted_class,
                "script_confidence": float(pred.script.confidence),
                "script_distribution": {
                    k: float(v) for k, v in pred.script.distribution.items()
                },
                "source_prediction": pred.source.predicted_class,
                "source_confidence": float(pred.source.confidence),
                "orientation_degrees": pred.orientation_degrees,
                "orientation_confidence": float(pred.orientation.confidence),
                "shadow_severity": float(pred.shadow.value),
                "shadow_sigma_sq": float(pred.shadow.sigma_sq),
                "warping_severity": float(pred.warping.value),
                "warping_sigma_sq": float(pred.warping.sigma_sq),
                "inference_time_ms": float(pred.inference_time_ms),
            }
            records.append(record)
            if pred.embedding is not None:
                embeddings.append(pred.embedding)
            processed_names.append(img_name)
            inference_times.append(pred.inference_time_ms)

            if (idx + 1) % 100 == 0:
                print(f"  [{idx + 1}/{n_images}] Processed {img_name}")

        print(
            f"Completed {split}: {len(records)} records, {len(embeddings)} embeddings"
        )

        # Save JSONL
        jsonl_path = output_dir / f"siglip2_diqa5000_{split}.jsonl"
        with open(jsonl_path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in records)
        print(f"Saved {jsonl_path}")

        # Save embeddings NPZ
        embeddings_arr = np.array(embeddings, dtype=np.float32)
        assert not np.any(np.isnan(embeddings_arr)), f"NaN found in {split} embeddings"
        npz_path = embeddings_dir / f"{split}.npz"
        np.savez_compressed(
            npz_path,
            embeddings=embeddings_arr,
            image_names=np.array(processed_names),
        )
        print(f"Saved {npz_path} (shape: {embeddings_arr.shape})")

        # Compute metrics (rescale from [0,1] to [1,5])
        split_metrics: dict = {"n": len(records)}
        for dim, gt_key in [
            ("overall", "overall"),
            ("sharpness", "sharpness"),
            ("color", "color_fidelity"),
        ]:
            gt_vals = [gt_data[name][gt_key] for name in processed_names]
            pred_vals = [r[f"iqa_{dim}_mu"] * 4.0 + 1.0 for r in records]

            if len(gt_vals) >= 3:
                gt_arr = np.asarray(gt_vals, dtype=np.float64)
                pred_arr = np.asarray(pred_vals, dtype=np.float64)

                # PLCC (Pearson) — np.corrcoef
                plcc = float(np.corrcoef(gt_arr, pred_arr)[0, 1])

                # SRCC (Spearman) — rank then Pearson
                def _rankdata(x: np.ndarray) -> np.ndarray:
                    order = np.argsort(x)
                    ranks = np.empty_like(order, dtype=np.float64)
                    ranks[order] = np.arange(1, len(x) + 1, dtype=np.float64)
                    return ranks

                gt_ranks = _rankdata(gt_arr)
                pred_ranks = _rankdata(pred_arr)
                srcc = float(np.corrcoef(gt_ranks, pred_ranks)[0, 1])

                mae = float(np.mean(np.abs(gt_arr - pred_arr)))
                split_metrics[f"{dim}_srcc"] = srcc
                split_metrics[f"{dim}_plcc"] = plcc
                split_metrics[f"{dim}_mae"] = mae

        # Weighted SRCC
        if all(f"{d}_srcc" in split_metrics for d in ("overall", "sharpness", "color")):
            split_metrics["wsrcc"] = (
                0.5 * split_metrics["overall_srcc"]
                + 0.25 * split_metrics["sharpness_srcc"]
                + 0.25 * split_metrics["color_srcc"]
            )

        if inference_times:
            split_metrics["mean_inference_ms"] = float(np.mean(inference_times))

        all_metrics[split] = split_metrics
        print(f"Metrics for {split}: {json.dumps(split_metrics, indent=2)}")

    output_volume.commit()

    return {
        "splits": all_metrics,
        "checkpoint": Path(checkpoint_path).name,
    }


# ---------------------------------------------------------------------------
# OOD detector fitting
# ---------------------------------------------------------------------------


@app.function(
    timeout=600,
    memory=8192,
    image=extraction_image,
    volumes={
        "/outputs": output_volume,
    },
)
def fit_ood_detector() -> dict:
    """Fit OOD detector on train+val embeddings, calibrate on test.

    Returns:
        OOD detector statistics.
    """
    import json
    import sys
    from datetime import datetime

    import numpy as np

    sys.path.insert(0, "/app/src")

    # Save original np.array before import (openlid_integration monkey-patches it)
    _original_np_array = np.array

    from image_preprocessing_detector.detection.ood_detector import (
        EmbeddingOODDetector,
    )

    # Restore np.array — the openlid monkey-patch breaks scipy/sklearn
    np.array = _original_np_array

    output_dir = Path("/outputs")
    embeddings_dir = output_dir / "embeddings"

    # Load embeddings
    train_data = np.load(embeddings_dir / "train.npz")
    val_data = np.load(embeddings_dir / "val.npz")
    test_data = np.load(embeddings_dir / "test.npz")

    train_emb = train_data["embeddings"]
    val_emb = val_data["embeddings"]
    test_emb = test_data["embeddings"]

    print(f"Train embeddings: {train_emb.shape}")
    print(f"Val embeddings: {val_emb.shape}")
    print(f"Test embeddings: {test_emb.shape}")

    # Fit on train + val
    fit_emb = np.concatenate([train_emb, val_emb])
    print(f"Fitting OOD detector on {fit_emb.shape[0]} embeddings...")

    detector = EmbeddingOODDetector.from_embeddings(fit_emb, threshold_percentile=95.0)

    # Calibrate on train+val (for self-consistency check)
    fit_results = detector.score_batch(fit_emb)
    fit_distances = np.array([r.mahalanobis_distance for r in fit_results])

    # Calibrate on test
    test_results = detector.score_batch(test_emb)
    test_distances = np.array([r.mahalanobis_distance for r in test_results])

    ood_stats = {
        "fit_n": len(fit_emb),
        "fit_splits": ["train", "val"],
        "train_val_median_distance": float(np.median(fit_distances)),
        "train_val_p95": float(np.percentile(fit_distances, 95)),
        "train_val_p99": float(np.percentile(fit_distances, 99)),
        "test_median_distance": float(np.median(test_distances)),
        "test_p95": float(np.percentile(test_distances, 95)),
        "test_p99": float(np.percentile(test_distances, 99)),
        "test_n_ood": int(sum(1 for r in test_results if r.is_ood)),
        "threshold": float(detector.threshold),
    }

    print("\nOOD Detector Statistics:")
    print(f"  Fit on: {ood_stats['fit_n']} samples")
    print(
        f"  Train+Val: median={ood_stats['train_val_median_distance']:.2f}, "
        f"p95={ood_stats['train_val_p95']:.2f}, p99={ood_stats['train_val_p99']:.2f}"
    )
    print(
        f"  Test: median={ood_stats['test_median_distance']:.2f}, "
        f"p95={ood_stats['test_p95']:.2f}, p99={ood_stats['test_p99']:.2f}"
    )
    print(f"  Test OOD flagged: {ood_stats['test_n_ood']}/{len(test_results)}")

    # Save OOD detector
    detector_path = output_dir / "ood_detector_v2.npz"
    detector.save(str(detector_path))
    print(f"Saved OOD detector to {detector_path}")

    # Load extraction metrics if available and build summary
    summary: dict = {
        "checkpoint": CHECKPOINT_SUBPATH,
        "model_id": "google/siglip2-base-patch16-naflex",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "ood_detector": ood_stats,
    }

    # Try to merge split metrics from JSONL record counts
    for split in DIQA5000_SPLITS:
        jsonl_path = output_dir / f"siglip2_diqa5000_{split}.jsonl"
        if jsonl_path.exists():
            n_lines = sum(1 for _ in open(jsonl_path))
            summary.setdefault("splits", {})[split] = {"n_records": n_lines}

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {summary_path}")

    output_volume.commit()

    return ood_stats


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


@app.local_entrypoint()
def main(
    limit: int = 0,
    split: str = "",
):
    """Run SigLIP2 extraction on DIQA-5000.

    Args:
        limit: Max images per split (0 = all).
        split: Single split to process (empty = all).
    """
    import json

    effective_limit = limit if limit > 0 else None
    splits = [split] if split else None

    if effective_limit:
        print(f"Running with limit={effective_limit} images per split")
    if splits:
        print(f"Processing splits: {splits}")

    # Step 1: Extract predictions + embeddings
    print("\n" + "=" * 70)
    print("STEP 1: Extract SigLIP2 predictions and embeddings")
    print("=" * 70)
    extraction_result = extract_all_splits.remote(
        limit=effective_limit,
        splits=splits,
    )
    print(f"\nExtraction result:\n{json.dumps(extraction_result, indent=2)}")

    # Step 2: Fit OOD detector (only if all splits were processed)
    if splits is None or set(splits) >= {"train", "val", "test"}:
        print("\n" + "=" * 70)
        print("STEP 2: Fit OOD detector on train+val, calibrate on test")
        print("=" * 70)
        ood_result = fit_ood_detector.remote()
        print(f"\nOOD result:\n{json.dumps(ood_result, indent=2)}")
    else:
        print(f"\nSkipping OOD detector fitting (need all splits, got {splits})")

    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print("\nDownload outputs with:")
    print(
        "  uv run modal volume get siglip2-diqa5000-outputs / ./siglip2_diqa5000_outputs/"
    )
