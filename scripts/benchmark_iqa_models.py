#!/usr/bin/env python3
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

        samples.append(
            {
                "id": sample.get("id", ""),
                "path": rel_path,
                "split": split,
                "mos_overall": float(mos_overall),
                "mos_sharpness": float(original_labels.get("mos_sharpness", 0)),
                "mos_color_fidelity": float(
                    original_labels.get("mos_color_fidelity", 0)
                ),
                "capture_type": capture_type,
            }
        )

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
            samples.append(
                {
                    "id": f"ohrbench_{idx:05d}",
                    "index": idx,
                    "quality_score": float(quality),
                    "category": item.get("category", "unknown"),
                }
            )
        log.info("Loaded %d OHR-Bench samples via HuggingFace datasets", len(samples))
        return samples
    except Exception as exc:
        log.warning("HuggingFace datasets load failed: %s", exc)

    # Fallback: try loading from image directory with CSV/JSON labels
    label_files = list(dataset_dir.glob("*.json")) + list(dataset_dir.glob("*.csv"))
    if not label_files:
        log.warning("No OHR-Bench label files found in %s", dataset_dir)
        return []

    log.warning(
        "OHR-Bench fallback loading not implemented for format: %s", label_files
    )
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
        log.error("pyiqa not installed. Run: uv add pyiqa")
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
def _create_classical_detectors() -> dict[str, Any]:
    """Create instances of all classical IQA detectors."""
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

    return {
        "blur": BlurDetector(),
        "noise": NoiseDetector(),
        "contrast": ContrastDetector(),
        "illumination": IlluminationDetector(),
        "jpeg_blockiness": JPEGBlockinessDetector(),
        "binarization": BinarizationQualityDetector(),
        "bleed_through": BleedThroughDetector(),
        "skew": SkewDetector(),
    }


def _extract_detector_score(result: Any) -> float:
    """Extract a 0-1 severity score from a detector result object."""
    if hasattr(result, "severity_score"):
        return float(result.severity_score)
    if hasattr(result, "score"):
        return float(result.score)
    if hasattr(result, "confidence"):
        return float(result.confidence)
    return 0.0


def _collect_detector_scores(
    images: list[np.ndarray],
    detectors: dict[str, Any],
    label: str = "Classical detectors",
) -> dict[str, list[float]]:
    """Run all detectors on all images and collect scores."""
    log.info("Running %d %s on %d images...", len(detectors), label, len(images))
    scores: dict[str, list[float]] = {name: [] for name in detectors}

    for idx, img in enumerate(images):
        if (idx + 1) % 500 == 0:
            log.info("  %s: %d/%d", label, idx + 1, len(images))

        for name, detector in detectors.items():
            try:
                result = detector.detect(img)
                scores[name].append(_extract_detector_score(result))
            except Exception:
                scores[name].append(0.0)

    return scores


def _compute_correlation_pair(
    arr_a: np.ndarray,
    arr_b: np.ndarray,
) -> tuple[float, float, float, float] | None:
    """Compute SRCC and PLCC for two arrays. Returns None if constant."""
    if np.std(arr_a) < 1e-8 or np.std(arr_b) < 1e-8:
        return None
    srcc_result = stats.spearmanr(arr_a, arr_b)
    plcc_result = stats.pearsonr(arr_a, arr_b)
    srcc_val = float(getattr(srcc_result, "statistic", srcc_result.correlation))
    plcc_val = float(getattr(plcc_result, "statistic", plcc_result[0]))
    return srcc_val, float(srcc_result.pvalue), plcc_val, float(plcc_result.pvalue)


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
    detectors = _create_classical_detectors()
    mos_dims = ["mos_overall", "mos_sharpness", "mos_color_fidelity"]
    detector_scores = _collect_detector_scores(images, detectors, "classical detectors")

    results: list[ClassicalResult] = []
    for det_name, det_scores in detector_scores.items():
        det_arr = np.array(det_scores)
        for mos_dim in mos_dims:
            gt_arr = np.array([s[mos_dim] for s in mos_scores])
            corr = _compute_correlation_pair(det_arr, gt_arr)
            if corr is None:
                continue
            srcc_val, srcc_pval, plcc_val, plcc_pval = corr
            results.append(
                ClassicalResult(
                    detector_name=det_name,
                    mos_dimension=mos_dim,
                    srcc=srcc_val,
                    srcc_pvalue=srcc_pval,
                    plcc=plcc_val,
                    plcc_pvalue=plcc_pval,
                    num_samples=len(det_scores),
                )
            )

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
def _compute_pairwise_srcc(
    scores: dict[str, list[float]],
    det_names: list[str],
) -> dict[str, dict[str, float]]:
    """Compute pairwise SRCC matrix between detector score arrays."""
    matrix: dict[str, dict[str, float]] = {}
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
                corr = _compute_correlation_pair(arr_a, arr_b)
                matrix[name_a][name_b] = round(corr[0], 4) if corr else 0.0

    return matrix


def compute_detector_intercorrelation(
    images: list[np.ndarray],
) -> dict[str, dict[str, float]]:
    """Compute inter-correlation matrix between classical detectors.

    Returns dict of {detector_a: {detector_b: srcc}} for all pairs.
    """
    detectors = _create_classical_detectors()
    log.info("Computing inter-correlation matrix for %d detectors...", len(detectors))
    scores = _collect_detector_scores(images, detectors, "Intercorrelation")
    return _compute_pairwise_srcc(scores, list(detectors.keys()))


def _load_diqa_images(
    metadata_path: Path,
    image_dir: Path,
    splits: list[str],
    limit: int,
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    """Load and filter DIQA-5000 images.

    Returns:
        Tuple of (images, valid_samples).
    """
    diqa_samples = load_diqa5000_metadata(metadata_path)
    diqa_samples = [s for s in diqa_samples if s["split"] in splits]
    log.info("Using %d DIQA-5000 samples (splits: %s)", len(diqa_samples), splits)

    if limit > 0:
        diqa_samples = diqa_samples[:limit]
        log.info("Limited to %d samples", len(diqa_samples))

    log.info("Loading DIQA-5000 images...")
    images: list[np.ndarray] = []
    valid_samples: list[dict[str, Any]] = []
    for sample in diqa_samples:
        img = load_diqa5000_image(sample, image_dir)
        if img is not None:
            images.append(img)
            valid_samples.append(sample)

    log.info("Loaded %d/%d DIQA-5000 images", len(images), len(diqa_samples))
    return images, valid_samples


def _run_and_save_classical(
    images: list[np.ndarray],
    mos_scores: list[dict[str, Any]],
    output_dir: Path,
    all_results: dict[str, Any],
) -> None:
    """Run classical detector benchmarks and save results."""
    log.info("=" * 60)
    log.info("CLASSICAL DETECTOR BENCHMARKS")
    log.info("=" * 60)

    classical_results = benchmark_classical_detectors(images, mos_scores)

    intercorr_images = images[:500] if len(images) > 500 else images
    intercorr_matrix = compute_detector_intercorrelation(intercorr_images)

    classical_output = {
        "timestamp": datetime.now(UTC).isoformat(),
        "num_images": len(images),
        "results": [asdict(r) for r in classical_results],
        "intercorrelation_matrix": intercorr_matrix,
    }

    classical_path = output_dir / "classical_correlations.json"
    with open(classical_path, "w") as fh:
        json.dump(classical_output, fh, indent=2)
    log.info("Classical results saved to %s", classical_path)

    all_results["classical"] = classical_output


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

    # Load DIQA-5000
    diqa_images, diqa_valid_samples = _load_diqa_images(
        args.diqa_metadata, args.diqa_dir, args.splits, args.limit
    )
    if not diqa_images:
        log.error("No DIQA-5000 images loaded, cannot benchmark")
        return 1

    diqa_gt_normalized = [(s["mos_overall"] - 1.0) / 4.0 for s in diqa_valid_samples]
    diqa_mos_scores = [
        {
            "mos_overall": s["mos_overall"],
            "mos_sharpness": s["mos_sharpness"],
            "mos_color_fidelity": s["mos_color_fidelity"],
        }
        for s in diqa_valid_samples
    ]

    # Phase 0a: Classical detector benchmarks
    if not args.skip_classical:
        _run_and_save_classical(
            diqa_images, diqa_mos_scores, args.output_dir, all_results
        )

    if args.classical_only:
        log.info("Classical-only mode, skipping pyiqa benchmarks")
        summary_path = args.output_dir / "summary_report.json"
        with open(summary_path, "w") as fh:
            json.dump(all_results, fh, indent=2)
        return 0

    # Phase 0b: PyIQA model benchmarks on DIQA-5000
    diqa_results = _run_pyiqa_benchmarks(
        "DIQA-5000",
        args.models,
        diqa_images,
        diqa_gt_normalized,
        args.device,
    )

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

    # Phase 0c: PyIQA model benchmarks on OHR-Bench
    if not args.skip_ohrbench:
        ohrbench_output = _run_ohrbench_benchmarks(
            args.ohrbench_dir,
            args.models,
            args.device,
            args.limit,
        )
        if ohrbench_output is not None:
            ohrbench_path = args.output_dir / "ohrbench_baselines.json"
            with open(ohrbench_path, "w") as fh:
                json.dump(ohrbench_output, fh, indent=2)
            log.info("OHR-Bench results saved to %s", ohrbench_path)
            all_results["ohrbench"] = ohrbench_output

    # Summary report
    _log_ranking_table(diqa_results)

    summary_path = args.output_dir / "summary_report.json"
    with open(summary_path, "w") as fh:
        json.dump(all_results, fh, indent=2, default=str)
    log.info("\nFull results saved to %s", summary_path)

    has_errors = any("error" in r for r in diqa_results)
    return 1 if has_errors else 0


def _run_pyiqa_benchmarks(
    dataset_label: str,
    model_names: list[str],
    images: list[np.ndarray],
    ground_truths: list[float],
    device: str,
) -> list[dict[str, Any]]:
    """Run pyiqa model benchmarks and return result dicts."""
    log.info("=" * 60)
    log.info("PYIQA MODEL BENCHMARKS - %s", dataset_label)
    log.info("=" * 60)

    results: list[dict[str, Any]] = []
    for model_name in model_names:
        try:
            result = benchmark_pyiqa_model(
                model_name=model_name,
                images=images,
                ground_truths=ground_truths,
                dataset_name=dataset_label.lower(),
                device=device,
            )
            results.append(result.to_summary())
        except Exception as exc:
            log.error("Failed to benchmark %s: %s", model_name, exc)
            results.append(
                {
                    "model_name": model_name,
                    "dataset": dataset_label.lower(),
                    "error": str(exc),
                }
            )
    return results


def _run_ohrbench_benchmarks(
    ohrbench_dir: Path,
    model_names: list[str],
    device: str,
    limit: int,
) -> dict[str, Any] | None:
    """Run pyiqa benchmarks on OHR-Bench. Returns output dict or None."""
    log.info("=" * 60)
    log.info("PYIQA MODEL BENCHMARKS - OHR-BENCH")
    log.info("=" * 60)

    ohrbench_samples = load_ohrbench_samples(ohrbench_dir)
    if not ohrbench_samples:
        log.warning("No OHR-Bench samples loaded, skipping")
        return None

    if limit > 0:
        ohrbench_samples = ohrbench_samples[:limit]

    ohrbench_ds = _load_ohrbench_dataset(ohrbench_dir)
    if ohrbench_ds is None:
        return None

    ohrbench_images, ohrbench_valid = _load_ohrbench_images(
        ohrbench_samples,
        ohrbench_ds,
    )
    log.info(
        "Loaded %d/%d OHR-Bench images",
        len(ohrbench_images),
        len(ohrbench_samples),
    )

    ohrbench_gt = [s["quality_score"] / 100.0 for s in ohrbench_valid]
    ohrbench_results = _run_pyiqa_benchmarks(
        "OHR-BENCH",
        model_names,
        ohrbench_images,
        ohrbench_gt,
        device,
    )

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": "ohr-bench",
        "num_images": len(ohrbench_images),
        "results": ohrbench_results,
    }


def _load_ohrbench_dataset(ohrbench_dir: Path) -> Any | None:
    """Load OHR-Bench HuggingFace dataset object."""
    log.info("Loading OHR-Bench images...")
    try:
        from datasets import load_from_disk

        return load_from_disk(str(ohrbench_dir))
    except Exception as exc:
        log.error("Cannot load OHR-Bench dataset: %s", exc)
        return None


def _load_ohrbench_images(
    samples: list[dict[str, Any]],
    dataset: Any,
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    """Load OHR-Bench images and return (images, valid_samples)."""
    images: list[np.ndarray] = []
    valid: list[dict[str, Any]] = []
    for sample in samples:
        img = load_ohrbench_image(sample, dataset)
        if img is not None:
            images.append(img)
            valid.append(sample)
    return images, valid


def _log_ranking_table(diqa_results: list[dict[str, Any]]) -> None:
    """Log the DIQA-5000 model ranking table."""
    log.info("=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)

    if not diqa_results:
        return

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


if __name__ == "__main__":
    sys.exit(main())
