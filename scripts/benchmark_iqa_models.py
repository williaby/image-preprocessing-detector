#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Benchmark NR-IQA models on document datasets (DIQA-5000 + OHR-Bench).

Phase 0 of the IQA Soft Label Generation Pipeline. Establishes actual SRCC/PLCC
baselines for all candidate NR-IQA models on document images, replacing
assumptions with measured data.

Models benchmarked:
  - pyiqa: topiq_nr, maniqa, dbcnn, hyperiqa, musiq, clipiqa+, liqe, niqe, brisque
  - classical: 8 existing detectors from iqa_classical.py

Outputs:
  - results/iqa_benchmarks/diqa5000_baselines.json
  - results/iqa_benchmarks/ohrbench_baselines.json
  - results/iqa_benchmarks/classical_correlations.json
  - results/iqa_benchmarks/summary_report.json

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/benchmark_iqa_models.py

    # Specific models only:
    PYTHONPATH=... uv run python3 scripts/benchmark_iqa_models.py \
        --models topiq_nr maniqa dbcnn

    # DIQA-5000 only (skip OHR-Bench):
    PYTHONPATH=... uv run python3 scripts/benchmark_iqa_models.py --skip-ohrbench

    # Classical detectors only:
    PYTHONPATH=... uv run python3 scripts/benchmark_iqa_models.py --classical-only

    # Quick mode (first 200 images per dataset):
    PYTHONPATH=... uv run python3 scripts/benchmark_iqa_models.py --limit 200
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
DIQA_METADATA_PATH = REGISTRY_DIR / "json" / "diqa-5000_metadata.json"
DIQA_DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
OHRBENCH_DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/ohr-bench")
OUTPUT_DIR = Path("results/iqa_benchmarks")

# Default pyiqa models to benchmark
DEFAULT_PYIQA_MODELS = [
    "topiq_nr",
    "maniqa",
    "dbcnn",
    "hyperiqa",
    "musiq",
    "clipiqa+",
    "liqe",
    "niqe",
    "brisque",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ModelResult:
    """Results for a single model on a single dataset."""

    model_name: str
    dataset: str
    srcc: float
    srcc_pvalue: float
    plcc: float
    plcc_pvalue: float
    mae: float
    rmse: float
    num_images: int
    mean_latency_ms: float
    total_time_s: float
    predictions: list[float] = field(default_factory=list)
    ground_truths: list[float] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        """Return summary dict without raw predictions."""
        return {
            "model_name": self.model_name,
            "dataset": self.dataset,
            "srcc": round(self.srcc, 4),
            "srcc_pvalue": self.srcc_pvalue,
            "plcc": round(self.plcc, 4),
            "plcc_pvalue": self.plcc_pvalue,
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "num_images": self.num_images,
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "total_time_s": round(self.total_time_s, 1),
        }


@dataclass
class ClassicalResult:
    """Correlation results for a classical detector dimension."""

    detector_name: str
    mos_dimension: str
    srcc: float
    srcc_pvalue: float
    plcc: float
    plcc_pvalue: float
    num_samples: int


# ---------------------------------------------------------------------------
# DIQA-5000 data loading
# ---------------------------------------------------------------------------
def load_diqa5000_metadata(
    metadata_path: Path,
) -> list[dict[str, Any]]:
    """Load DIQA-5000 metadata with MOS scores.

    Returns list of dicts with keys: id, path, split, mos_overall,
    mos_sharpness, mos_color_fidelity, capture_type.
    """
    log.info("Loading DIQA-5000 metadata from %s", metadata_path)
    with open(metadata_path) as fh:
        metadata = json.load(fh)

    samples = []
    for sample in metadata.get("samples", []):
        original_labels = sample.get("original_labels", {})
        source = sample.get("source", {})

        mos_overall = original_labels.get("mos_overall")
        if mos_overall is None:
            continue

        rel_path = source.get("original_path", "")
        split = source.get("split", "unknown")
        capture_type = "ori" if "/ori/" in rel_path else "res"

        samples.append({
            "id": sample.get("id", ""),
            "path": rel_path,
            "split": split,
            "mos_overall": float(mos_overall),
            "mos_sharpness": float(original_labels.get("mos_sharpness", 0)),
            "mos_color_fidelity": float(
                original_labels.get("mos_color_fidelity", 0)
            ),
            "capture_type": capture_type,
        })

    log.info("Loaded %d DIQA-5000 samples with MOS scores", len(samples))
    return samples


def load_diqa5000_image(
    sample: dict[str, Any],
    dataset_dir: Path,
) -> np.ndarray | None:
    """Load a DIQA-5000 image as BGR numpy array."""
    img_path = dataset_dir / sample["path"]
    if not img_path.exists():
        return None
    img = cv2.imread(str(img_path))
    return img


# ---------------------------------------------------------------------------
# OHR-Bench data loading
# ---------------------------------------------------------------------------
def load_ohrbench_samples(
    dataset_dir: Path,
) -> list[dict[str, Any]]:
    """Load OHR-Bench images with quality scores from Arrow metadata.

    Returns list of dicts with keys: id, path, quality_score, category.
    """
    log.info("Loading OHR-Bench from %s", dataset_dir)

    # OHR-Bench stores data in HuggingFace Arrow format
    # Try loading via datasets library first
    try:
        from datasets import load_from_disk

        ds = load_from_disk(str(dataset_dir))
        samples = []
        for idx, item in enumerate(ds):
            quality = item.get("quality_score")
            if quality is None:
                continue
            samples.append({
                "id": f"ohrbench_{idx:05d}",
                "index": idx,
                "quality_score": float(quality),
                "category": item.get("category", "unknown"),
            })
        log.info("Loaded %d OHR-Bench samples via HuggingFace datasets", len(samples))
        return samples
    except Exception as exc:
        log.warning("HuggingFace datasets load failed: %s", exc)

    # Fallback: try loading from image directory with CSV/JSON labels
    label_files = list(dataset_dir.glob("*.json")) + list(dataset_dir.glob("*.csv"))
    if not label_files:
        log.warning("No OHR-Bench label files found in %s", dataset_dir)
        return []

    log.warning("OHR-Bench fallback loading not implemented for format: %s", label_files)
    return []


def load_ohrbench_image(
    sample: dict[str, Any],
    dataset: Any,
) -> np.ndarray | None:
    """Load an OHR-Bench image from the HuggingFace dataset object."""
    try:
        idx = sample["index"]
        pil_image = dataset[idx]["image"]
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return img
    except Exception as exc:
        log.debug("Failed to load OHR-Bench image %s: %s", sample["id"], exc)
        return None


# ---------------------------------------------------------------------------
# PyIQA model benchmarking
# ---------------------------------------------------------------------------
def benchmark_pyiqa_model(
    model_name: str,
    images: list[np.ndarray],
    ground_truths: list[float],
    dataset_name: str,
    device: str = "cpu",
) -> ModelResult:
    """Benchmark a single pyiqa model on a list of images.

    Args:
        model_name: pyiqa model identifier (e.g., "topiq_nr")
        images: List of BGR numpy arrays
        ground_truths: Corresponding quality scores (normalized 0-1)
        dataset_name: Name for logging
        device: torch device string

    Returns:
        ModelResult with correlation metrics and latency
    """
    import torch

    try:
        import pyiqa
    except ImportError:
        log.error(
            "pyiqa not installed. Run: uv add pyiqa"
        )
        raise

    log.info("Benchmarking %s on %s (%d images)", model_name, dataset_name, len(images))

    # Create pyiqa metric
    try:
        metric = pyiqa.create_metric(model_name, device=torch.device(device))
    except Exception as exc:
        log.error("Failed to create pyiqa metric '%s': %s", model_name, exc)
        return ModelResult(
            model_name=model_name,
            dataset=dataset_name,
            srcc=0.0,
            srcc_pvalue=1.0,
            plcc=0.0,
            plcc_pvalue=1.0,
            mae=float("inf"),
            rmse=float("inf"),
            num_images=0,
            mean_latency_ms=0.0,
            total_time_s=0.0,
        )

    predictions = []
    latencies = []

    for img in images:
        # Convert BGR numpy -> RGB tensor for pyiqa
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_tensor = (
            torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        )
        img_tensor = img_tensor.to(device)

        start = time.perf_counter()
        with torch.no_grad():
            score = metric(img_tensor)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        predictions.append(float(score.cpu().item()))
        latencies.append(elapsed_ms)

    # Compute correlations
    preds_arr = np.array(predictions)
    gt_arr = np.array(ground_truths)

    srcc_result = stats.spearmanr(preds_arr, gt_arr)
    plcc_result = stats.pearsonr(preds_arr, gt_arr)

    # Handle scipy version differences for statistic access
    srcc_val = float(getattr(srcc_result, "statistic", srcc_result.correlation))
    srcc_pval = float(srcc_result.pvalue)
    plcc_val = float(getattr(plcc_result, "statistic", plcc_result[0]))
    plcc_pval = float(plcc_result.pvalue)

    mae = float(np.mean(np.abs(preds_arr - gt_arr)))
    rmse = float(np.sqrt(np.mean((preds_arr - gt_arr) ** 2)))

    result = ModelResult(
        model_name=model_name,
        dataset=dataset_name,
        srcc=srcc_val,
        srcc_pvalue=srcc_pval,
        plcc=plcc_val,
        plcc_pvalue=plcc_pval,
        mae=mae,
        rmse=rmse,
        num_images=len(images),
        mean_latency_ms=float(np.mean(latencies)),
        total_time_s=sum(latencies) / 1000.0,
        predictions=predictions,
        ground_truths=list(ground_truths),
    )

    log.info(
        "  %s on %s: SRCC=%.4f, PLCC=%.4f, MAE=%.4f, latency=%.1fms/img",
        model_name,
        dataset_name,
        result.srcc,
        result.plcc,
        result.mae,
        result.mean_latency_ms,
    )
    return result


# ---------------------------------------------------------------------------
# Classical detector benchmarking
# ---------------------------------------------------------------------------
def benchmark_classical_detectors(
    images: list[np.ndarray],
    mos_scores: list[dict[str, float]],
) -> list[ClassicalResult]:
    """Benchmark classical IQA detectors against MOS scores.

    Computes SRCC/PLCC for each classical detector dimension against
    each available MOS dimension (overall, sharpness, color_fidelity).

    Args:
        images: BGR numpy arrays
        mos_scores: List of dicts with mos_overall, mos_sharpness, mos_color_fidelity

    Returns:
        List of ClassicalResult for each (detector, mos_dim) pair
    """
    from image_preprocessing_detector.detection.iqa_classical import (
        BinarizationQualityDetector,
        BleedThroughDetector,
        BlurDetector,
        ContrastDetector,
        IlluminationDetector,
        JPEGBlockinessDetector,
        NoiseDetector,
        SkewDetector,
    )

    detectors = {
        "blur": BlurDetector(),
        "noise": NoiseDetector(),
        "contrast": ContrastDetector(),
        "illumination": IlluminationDetector(),
        "jpeg_blockiness": JPEGBlockinessDetector(),
        "binarization": BinarizationQualityDetector(),
        "bleed_through": BleedThroughDetector(),
        "skew": SkewDetector(),
    }

    mos_dims = ["mos_overall", "mos_sharpness", "mos_color_fidelity"]

    # Collect detector scores for all images
    log.info("Running 8 classical detectors on %d images...", len(images))
    detector_scores: dict[str, list[float]] = {name: [] for name in detectors}

    for idx, img in enumerate(images):
        if (idx + 1) % 500 == 0:
            log.info("  Classical detectors: %d/%d", idx + 1, len(images))

        for name, detector in detectors.items():
            try:
                result = detector.detect(img)
                # Extract severity score (0-1)
                if hasattr(result, "severity_score"):
                    score = float(result.severity_score)
                elif hasattr(result, "score"):
                    score = float(result.score)
                elif hasattr(result, "confidence"):
                    score = float(result.confidence)
                else:
                    score = 0.0
                detector_scores[name].append(score)
            except Exception:
                detector_scores[name].append(0.0)

    # Compute correlations for each (detector, mos_dim) pair
    results: list[ClassicalResult] = []
    for det_name, det_scores in detector_scores.items():
        det_arr = np.array(det_scores)
        for mos_dim in mos_dims:
            gt_arr = np.array([s[mos_dim] for s in mos_scores])

            # Skip if constant values
            if np.std(det_arr) < 1e-8 or np.std(gt_arr) < 1e-8:
                continue

            srcc_result = stats.spearmanr(det_arr, gt_arr)
            plcc_result = stats.pearsonr(det_arr, gt_arr)

            srcc_val = float(
                getattr(srcc_result, "statistic", srcc_result.correlation)
            )
            plcc_val = float(getattr(plcc_result, "statistic", plcc_result[0]))

            results.append(ClassicalResult(
                detector_name=det_name,
                mos_dimension=mos_dim,
                srcc=srcc_val,
                srcc_pvalue=float(srcc_result.pvalue),
                plcc=plcc_val,
                plcc_pvalue=float(plcc_result.pvalue),
                num_samples=len(det_scores),
            ))

    # Log summary
    for r in results:
        if r.mos_dimension == "mos_overall":
            log.info(
                "  Classical %s vs %s: SRCC=%.4f, PLCC=%.4f",
                r.detector_name,
                r.mos_dimension,
                r.srcc,
                r.plcc,
            )

    return results


# ---------------------------------------------------------------------------
# Inter-correlation matrix for classical detectors
# ---------------------------------------------------------------------------
def compute_detector_intercorrelation(
    images: list[np.ndarray],
) -> dict[str, dict[str, float]]:
    """Compute inter-correlation matrix between classical detectors.

    Returns dict of {detector_a: {detector_b: srcc}} for all pairs.
    """
    from image_preprocessing_detector.detection.iqa_classical import (
        BinarizationQualityDetector,
        BleedThroughDetector,
        BlurDetector,
        ContrastDetector,
        IlluminationDetector,
        JPEGBlockinessDetector,
        NoiseDetector,
        SkewDetector,
    )

    detectors = {
        "blur": BlurDetector(),
        "noise": NoiseDetector(),
        "contrast": ContrastDetector(),
        "illumination": IlluminationDetector(),
        "jpeg_blockiness": JPEGBlockinessDetector(),
        "binarization": BinarizationQualityDetector(),
        "bleed_through": BleedThroughDetector(),
        "skew": SkewDetector(),
    }

    log.info("Computing inter-correlation matrix for %d detectors...", len(detectors))
    scores: dict[str, list[float]] = {name: [] for name in detectors}

    for idx, img in enumerate(images):
        if (idx + 1) % 500 == 0:
            log.info("  Intercorrelation: %d/%d", idx + 1, len(images))

        for name, detector in detectors.items():
            try:
                result = detector.detect(img)
                if hasattr(result, "severity_score"):
                    score = float(result.severity_score)
                elif hasattr(result, "score"):
                    score = float(result.score)
                elif hasattr(result, "confidence"):
                    score = float(result.confidence)
                else:
                    score = 0.0
                scores[name].append(score)
            except Exception:
                scores[name].append(0.0)

    # Compute pairwise SRCC
    matrix: dict[str, dict[str, float]] = {}
    det_names = list(detectors.keys())
    for i, name_a in enumerate(det_names):
        matrix[name_a] = {}
        for j, name_b in enumerate(det_names):
            if i == j:
                matrix[name_a][name_b] = 1.0
            elif j < i:
                matrix[name_a][name_b] = matrix[name_b][name_a]
            else:
                arr_a = np.array(scores[name_a])
                arr_b = np.array(scores[name_b])
                if np.std(arr_a) < 1e-8 or np.std(arr_b) < 1e-8:
                    matrix[name_a][name_b] = 0.0
                else:
                    result = stats.spearmanr(arr_a, arr_b)
                    matrix[name_a][name_b] = round(
                        float(
                            getattr(result, "statistic", result.correlation)
                        ),
                        4,
                    )

    return matrix


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """Run IQA model benchmarks on document datasets."""
    parser = argparse.ArgumentParser(
        description="Benchmark NR-IQA models on document datasets"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_PYIQA_MODELS,
        help="pyiqa model names to benchmark",
    )
    parser.add_argument(
        "--skip-ohrbench",
        action="store_true",
        help="Skip OHR-Bench benchmarking",
    )
    parser.add_argument(
        "--classical-only",
        action="store_true",
        help="Only run classical detector benchmarks",
    )
    parser.add_argument(
        "--skip-classical",
        action="store_true",
        help="Skip classical detector benchmarks",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit images per dataset (0=all)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Torch device (cpu, cuda, cuda:0)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for results",
    )
    parser.add_argument(
        "--diqa-metadata",
        type=Path,
        default=DIQA_METADATA_PATH,
        help="Path to DIQA-5000 metadata JSON",
    )
    parser.add_argument(
        "--diqa-dir",
        type=Path,
        default=DIQA_DATASET_DIR,
        help="Path to DIQA-5000 image directory",
    )
    parser.add_argument(
        "--ohrbench-dir",
        type=Path,
        default=OHRBENCH_DATASET_DIR,
        help="Path to OHR-Bench directory",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "val"],
        help="DIQA-5000 splits to use (default: train val)",
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "config": {
            "models": args.models,
            "device": args.device,
            "limit": args.limit,
            "splits": args.splits,
        },
    }

    # -----------------------------------------------------------------------
    # Load DIQA-5000
    # -----------------------------------------------------------------------
    diqa_samples = load_diqa5000_metadata(args.diqa_metadata)
    diqa_samples = [s for s in diqa_samples if s["split"] in args.splits]
    log.info("Using %d DIQA-5000 samples (splits: %s)", len(diqa_samples), args.splits)

    if args.limit > 0:
        diqa_samples = diqa_samples[: args.limit]
        log.info("Limited to %d samples", len(diqa_samples))

    # Load images
    log.info("Loading DIQA-5000 images...")
    diqa_images: list[np.ndarray] = []
    diqa_valid_samples: list[dict[str, Any]] = []
    for sample in diqa_samples:
        img = load_diqa5000_image(sample, args.diqa_dir)
        if img is not None:
            diqa_images.append(img)
            diqa_valid_samples.append(sample)

    log.info("Loaded %d/%d DIQA-5000 images", len(diqa_images), len(diqa_samples))

    # Normalize MOS to 0-1 for pyiqa comparison
    diqa_gt_normalized = [
        (s["mos_overall"] - 1.0) / 4.0 for s in diqa_valid_samples
    ]
    diqa_mos_scores = [
        {
            "mos_overall": s["mos_overall"],
            "mos_sharpness": s["mos_sharpness"],
            "mos_color_fidelity": s["mos_color_fidelity"],
        }
        for s in diqa_valid_samples
    ]

    # -----------------------------------------------------------------------
    # Phase 0a: Classical detector benchmarks
    # -----------------------------------------------------------------------
    if not args.skip_classical:
        log.info("=" * 60)
        log.info("CLASSICAL DETECTOR BENCHMARKS")
        log.info("=" * 60)

        classical_results = benchmark_classical_detectors(
            diqa_images, diqa_mos_scores
        )

        # Inter-correlation matrix (use subset for speed)
        intercorr_images = diqa_images[:500] if len(diqa_images) > 500 else diqa_images
        intercorr_matrix = compute_detector_intercorrelation(intercorr_images)

        classical_output = {
            "timestamp": datetime.now(UTC).isoformat(),
            "num_images": len(diqa_images),
            "results": [asdict(r) for r in classical_results],
            "intercorrelation_matrix": intercorr_matrix,
        }

        classical_path = args.output_dir / "classical_correlations.json"
        with open(classical_path, "w") as fh:
            json.dump(classical_output, fh, indent=2)
        log.info("Classical results saved to %s", classical_path)

        all_results["classical"] = classical_output

    if args.classical_only:
        log.info("Classical-only mode, skipping pyiqa benchmarks")
        summary_path = args.output_dir / "summary_report.json"
        with open(summary_path, "w") as fh:
            json.dump(all_results, fh, indent=2)
        return 0

    # -----------------------------------------------------------------------
    # Phase 0b: PyIQA model benchmarks on DIQA-5000
    # -----------------------------------------------------------------------
    log.info("=" * 60)
    log.info("PYIQA MODEL BENCHMARKS - DIQA-5000")
    log.info("=" * 60)

    diqa_results: list[dict[str, Any]] = []
    for model_name in args.models:
        try:
            result = benchmark_pyiqa_model(
                model_name=model_name,
                images=diqa_images,
                ground_truths=diqa_gt_normalized,
                dataset_name="diqa-5000",
                device=args.device,
            )
            diqa_results.append(result.to_summary())
        except Exception as exc:
            log.error("Failed to benchmark %s: %s", model_name, exc)
            diqa_results.append({
                "model_name": model_name,
                "dataset": "diqa-5000",
                "error": str(exc),
            })

    diqa_output = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": "diqa-5000",
        "splits": args.splits,
        "num_images": len(diqa_images),
        "results": diqa_results,
    }

    diqa_path = args.output_dir / "diqa5000_baselines.json"
    with open(diqa_path, "w") as fh:
        json.dump(diqa_output, fh, indent=2)
    log.info("DIQA-5000 results saved to %s", diqa_path)

    all_results["diqa5000"] = diqa_output

    # -----------------------------------------------------------------------
    # Phase 0c: PyIQA model benchmarks on OHR-Bench
    # -----------------------------------------------------------------------
    if not args.skip_ohrbench:
        log.info("=" * 60)
        log.info("PYIQA MODEL BENCHMARKS - OHR-BENCH")
        log.info("=" * 60)

        ohrbench_samples = load_ohrbench_samples(args.ohrbench_dir)

        if ohrbench_samples:
            if args.limit > 0:
                ohrbench_samples = ohrbench_samples[: args.limit]

            # Load OHR-Bench images
            log.info("Loading OHR-Bench images...")
            try:
                from datasets import load_from_disk

                ohrbench_ds = load_from_disk(str(args.ohrbench_dir))
            except Exception as exc:
                log.error("Cannot load OHR-Bench dataset: %s", exc)
                ohrbench_ds = None

            if ohrbench_ds is not None:
                ohrbench_images: list[np.ndarray] = []
                ohrbench_valid: list[dict[str, Any]] = []
                for sample in ohrbench_samples:
                    img = load_ohrbench_image(sample, ohrbench_ds)
                    if img is not None:
                        ohrbench_images.append(img)
                        ohrbench_valid.append(sample)

                log.info(
                    "Loaded %d/%d OHR-Bench images",
                    len(ohrbench_images),
                    len(ohrbench_samples),
                )

                # Normalize OHR-Bench 0-100 to 0-1
                ohrbench_gt = [s["quality_score"] / 100.0 for s in ohrbench_valid]

                ohrbench_results: list[dict[str, Any]] = []
                for model_name in args.models:
                    try:
                        result = benchmark_pyiqa_model(
                            model_name=model_name,
                            images=ohrbench_images,
                            ground_truths=ohrbench_gt,
                            dataset_name="ohr-bench",
                            device=args.device,
                        )
                        ohrbench_results.append(result.to_summary())
                    except Exception as exc:
                        log.error("Failed %s on OHR-Bench: %s", model_name, exc)
                        ohrbench_results.append({
                            "model_name": model_name,
                            "dataset": "ohr-bench",
                            "error": str(exc),
                        })

                ohrbench_output = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "dataset": "ohr-bench",
                    "num_images": len(ohrbench_images),
                    "results": ohrbench_results,
                }

                ohrbench_path = args.output_dir / "ohrbench_baselines.json"
                with open(ohrbench_path, "w") as fh:
                    json.dump(ohrbench_output, fh, indent=2)
                log.info("OHR-Bench results saved to %s", ohrbench_path)

                all_results["ohrbench"] = ohrbench_output
        else:
            log.warning("No OHR-Bench samples loaded, skipping")

    # -----------------------------------------------------------------------
    # Summary report
    # -----------------------------------------------------------------------
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)

    # Print ranking table
    if diqa_results:
        log.info("\nDIQA-5000 Model Ranking (by SRCC):")
        log.info("%-15s  %8s  %8s  %10s", "Model", "SRCC", "PLCC", "Latency(ms)")
        log.info("-" * 50)
        ranked = sorted(
            [r for r in diqa_results if "error" not in r],
            key=lambda r: abs(r["srcc"]),
            reverse=True,
        )
        for r in ranked:
            log.info(
                "%-15s  %8.4f  %8.4f  %10.1f",
                r["model_name"],
                r["srcc"],
                r["plcc"],
                r["mean_latency_ms"],
            )

    summary_path = args.output_dir / "summary_report.json"
    with open(summary_path, "w") as fh:
        json.dump(all_results, fh, indent=2, default=str)
    log.info("\nFull results saved to %s", summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
