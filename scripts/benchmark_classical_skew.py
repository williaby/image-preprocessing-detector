"""Benchmark classical skew detection to establish baseline accuracy.

Runs the existing Hough + Projection Profile ensemble from iqa_classical.py
against a dataset with known ground-truth skew angles, computing MAE, SRCC,
PLCC, and 80th-percentile error to set the classical ceiling for comparison
with the ML-based SkewNet pipeline.

Usage:
    uv run python scripts/benchmark_classical_skew.py \
        --dataset-dir /path/to/skew_dataset \
        --report results/classical_skew_benchmark.json

Dataset format:
    The dataset directory should contain images with a corresponding
    labels.json file mapping filenames to ground-truth angles:
    {
        "image_001.png": {"angle": 2.3, "orientation": 0},
        "image_002.png": {"angle": -1.5, "orientation": 90},
        ...
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy import stats

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from image_preprocessing_detector.detection.iqa_classical import (
    SkewDetector,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkResult:
    """Aggregated benchmark metrics for classical skew detection.

    Attributes:
        total_images: Number of images processed.
        mae: Mean Absolute Error in degrees.
        rmse: Root Mean Squared Error in degrees.
        srcc: Spearman Rank Correlation Coefficient.
        plcc: Pearson Linear Correlation Coefficient.
        top80_error: 80th percentile absolute error.
        within_05_deg: Fraction of predictions within ±0.5 degrees.
        within_1_deg: Fraction of predictions within ±1.0 degrees.
        mean_latency_ms: Mean inference latency in milliseconds.
        p95_latency_ms: 95th percentile latency in milliseconds.
    """

    total_images: int
    mae: float
    rmse: float
    srcc: float
    plcc: float
    top80_error: float
    within_05_deg: float
    within_1_deg: float
    mean_latency_ms: float
    p95_latency_ms: float


@dataclass
class PerImageResult:
    """Per-image benchmark result.

    Attributes:
        filename: Image filename.
        gt_angle: Ground truth skew angle.
        pred_angle: Predicted skew angle.
        error: Absolute error in degrees.
        confidence: Detection confidence.
        method: Detection method used (hough/projection/ensemble).
        latency_ms: Inference time in milliseconds.
    """

    filename: str
    gt_angle: float
    pred_angle: float
    error: float
    confidence: float
    method: str
    latency_ms: float


@dataclass
class BenchmarkReport:
    """Full benchmark report with aggregate and per-image results.

    Attributes:
        metrics: Aggregated benchmark metrics.
        per_image: List of per-image results.
        config: Detector configuration used.
        dataset_path: Path to the dataset.
    """

    metrics: BenchmarkResult
    per_image: list[PerImageResult] = field(default_factory=list)
    config: dict[str, float] = field(default_factory=dict)
    dataset_path: str = ""


def load_labels(dataset_dir: Path) -> dict[str, dict[str, float]]:
    """Load ground-truth labels from labels.json.

    Args:
        dataset_dir: Path to dataset directory.

    Returns:
        Mapping of filename to label dict with 'angle' key.

    Raises:
        FileNotFoundError: If labels.json not found.
    """
    labels_path = dataset_dir / "labels.json"
    if not labels_path.exists():
        msg = f"Labels file not found: {labels_path}"
        raise FileNotFoundError(msg)

    with labels_path.open() as f:
        return json.load(f)


def run_benchmark(
    dataset_dir: Path,
    detector: SkewDetector,
) -> BenchmarkReport:
    """Run classical skew detection benchmark on a dataset.

    Args:
        dataset_dir: Path to dataset with images and labels.json.
        detector: Configured SkewDetector instance.

    Returns:
        BenchmarkReport with aggregate metrics and per-image results.
    """
    labels = load_labels(dataset_dir)

    gt_angles: list[float] = []
    pred_angles: list[float] = []
    errors: list[float] = []
    latencies: list[float] = []
    per_image_results: list[PerImageResult] = []

    total = len(labels)
    processed = 0

    for filename, label_data in labels.items():
        image_path = dataset_dir / filename
        if not image_path.exists():
            logger.warning("Image not found, skipping: %s", image_path)
            continue

        gt_angle = float(label_data["angle"])

        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning("Failed to read image, skipping: %s", image_path)
            continue

        start = time.perf_counter()
        result = detector.detect(image)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        error = abs(result.angle - gt_angle)

        gt_angles.append(gt_angle)
        pred_angles.append(result.angle)
        errors.append(error)
        latencies.append(elapsed_ms)

        per_image_results.append(
            PerImageResult(
                filename=filename,
                gt_angle=gt_angle,
                pred_angle=result.angle,
                error=error,
                confidence=result.confidence,
                method=result.method,
                latency_ms=elapsed_ms,
            )
        )

        processed += 1
        if processed % 100 == 0:
            logger.info("Processed %d / %d images", processed, total)

    if not gt_angles:
        msg = "No images were successfully processed"
        raise ValueError(msg)

    gt_arr = np.array(gt_angles)
    pred_arr = np.array(pred_angles)
    err_arr = np.array(errors)
    lat_arr = np.array(latencies)

    mae = float(np.mean(err_arr))
    rmse = float(np.sqrt(np.mean(err_arr**2)))
    top80 = float(np.percentile(err_arr, 80))
    within_05 = float(np.mean(err_arr <= 0.5))
    within_1 = float(np.mean(err_arr <= 1.0))

    srcc_val, _ = stats.spearmanr(gt_arr, pred_arr)
    plcc_val, _ = stats.pearsonr(gt_arr, pred_arr)

    metrics = BenchmarkResult(
        total_images=len(gt_angles),
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        srcc=round(float(srcc_val), 4),
        plcc=round(float(plcc_val), 4),
        top80_error=round(top80, 4),
        within_05_deg=round(within_05, 4),
        within_1_deg=round(within_1, 4),
        mean_latency_ms=round(float(np.mean(lat_arr)), 2),
        p95_latency_ms=round(float(np.percentile(lat_arr, 95)), 2),
    )

    config = {
        "threshold_low": detector.threshold_low,
        "threshold_medium": detector.threshold_medium,
        "threshold_high": detector.threshold_high,
        "min_line_length": float(detector.min_line_length),
        "max_line_gap": float(detector.max_line_gap),
    }

    return BenchmarkReport(
        metrics=metrics,
        per_image=per_image_results,
        config=config,
        dataset_path=str(dataset_dir),
    )


def save_report(report: BenchmarkReport, output_path: Path) -> None:
    """Save benchmark report to JSON.

    Args:
        report: Benchmark report to save.
        output_path: Path for the JSON output file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "metrics": asdict(report.metrics),
        "config": report.config,
        "dataset_path": report.dataset_path,
        "per_image_results": [asdict(r) for r in report.per_image],
    }

    with output_path.open("w") as f:
        json.dump(data, f, indent=2)

    logger.info("Report saved to %s", output_path)


def print_summary(report: BenchmarkReport) -> None:
    """Print a concise benchmark summary to stdout.

    Args:
        report: Benchmark report to summarize.
    """
    m = report.metrics
    print("\n=== Classical Skew Detection Benchmark ===")
    print(f"Dataset:     {report.dataset_path}")
    print(f"Images:      {m.total_images}")
    print(f"MAE:         {m.mae:.4f} deg")
    print(f"RMSE:        {m.rmse:.4f} deg")
    print(f"SRCC:        {m.srcc:.4f}")
    print(f"PLCC:        {m.plcc:.4f}")
    print(f"TOP80:       {m.top80_error:.4f} deg")
    print(f"Within 0.5d: {m.within_05_deg:.1%}")
    print(f"Within 1.0d: {m.within_1_deg:.1%}")
    print(
        f"Latency:     {m.mean_latency_ms:.1f} ms (mean), {m.p95_latency_ms:.1f} ms (p95)"
    )
    print("=" * 42)


def main() -> None:
    """Entry point for classical skew benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark classical skew detection (Hough + Projection Profile)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        required=True,
        help="Path to dataset with images and labels.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("results/classical_skew_benchmark.json"),
        help="Output path for benchmark report JSON",
    )
    parser.add_argument(
        "--threshold-low",
        type=float,
        default=0.5,
        help="Low severity threshold in degrees (default: 0.5)",
    )
    parser.add_argument(
        "--min-line-length",
        type=int,
        default=100,
        help="Minimum Hough line length (default: 100)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    detector = SkewDetector(
        threshold_low=args.threshold_low,
        min_line_length=args.min_line_length,
    )

    logger.info("Running benchmark on %s", args.dataset_dir)
    report = run_benchmark(args.dataset_dir, detector)

    print_summary(report)
    save_report(report, args.report)


if __name__ == "__main__":
    main()
