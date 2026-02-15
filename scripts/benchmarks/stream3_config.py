"""Stream 3 benchmark configuration: thresholds, dataset paths, output dirs.

Provides Go/No-Go thresholds for each detector, dataset path resolution,
and output directory management for Stream 3 benchmarking scripts.

Example:
    >>> from scripts.benchmarks.stream3_config import (
    ...     THRESHOLDS,
    ...     resolve_dataset_path,
    ...     BENCHMARK_OUTPUT_DIR,
    ... )
    >>> threshold = THRESHOLDS["script_detection"]
    >>> print(threshold.target)  # 0.80
    >>> path = resolve_dataset_path("sd7k")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from image_preprocessing_detector.annotation.config.datasets import (
    DATASET_CONFIGS,
    DatasetConfig,
    get_dataset_path,
)
from image_preprocessing_detector.annotation.config.settings import AnnotationSettings

BENCHMARK_OUTPUT_DIR = Path("results/stream3_benchmarks")

# Default data root (overridable via --data-dir CLI arg)
DEFAULT_DATA_DIR = Path("/mnt/e/image_detection")


@dataclass(frozen=True)
class BenchmarkThreshold:
    """Go/No-Go threshold for a single detector benchmark.

    Attributes:
        detector_name: Human-readable detector name.
        metric: Primary metric used for Go/No-Go decision (e.g., "accuracy", "f1").
        target: Minimum acceptable value for the metric.
        dataset: Primary evaluation dataset name.
        ml_action: Recommended action if threshold is not met.
    """

    detector_name: str
    metric: str
    target: float
    dataset: str
    ml_action: str


THRESHOLDS: dict[str, BenchmarkThreshold] = {
    "script_detection": BenchmarkThreshold(
        detector_name="ScriptDetectorHeuristic",
        metric="accuracy",
        target=0.80,
        dataset="mlt19",
        ml_action="Train SigLIP2 script head (Stream 4)",
    ),
    "document_source": BenchmarkThreshold(
        detector_name="DocumentSourceClassifier",
        metric="accuracy",
        target=0.85,
        dataset="smartdoc-qa",
        ml_action="Train ML document source classifier",
    ),
    "orientation": BenchmarkThreshold(
        detector_name="OrientationDetector",
        metric="accuracy",
        target=0.85,
        dataset="synth_multiscript_v3",
        ml_action="Train MobileNetV4 orientation head",
    ),
    "shadow": BenchmarkThreshold(
        detector_name="ShadowDetector",
        metric="f1",
        target=0.85,
        dataset="sd7k",
        ml_action="Extend ML IQA with shadow head",
    ),
    "warping": BenchmarkThreshold(
        detector_name="WarpingDetector",
        metric="f1",
        target=0.80,
        dataset="anyphotodoc6300",
        ml_action="Extend ML IQA with warping head",
    ),
    "handwriting": BenchmarkThreshold(
        detector_name="HandwritingDetector",
        metric="f1",
        target=0.75,
        dataset="cocotext",
        ml_action="Train handwriting detection head",
    ),
}


def resolve_dataset_path(
    dataset_name: str,
    data_dir: Path | None = None,
) -> Path:
    """Resolve full filesystem path for a dataset.

    Looks up the dataset in DATASET_CONFIGS and combines with the data root.

    Args:
        dataset_name: Canonical dataset name (key in DATASET_CONFIGS).
        data_dir: Override data root directory. Uses DEFAULT_DATA_DIR if None.

    Returns:
        Full path to the dataset directory.

    Raises:
        KeyError: If dataset_name is not in DATASET_CONFIGS.
    """
    if dataset_name not in DATASET_CONFIGS:
        msg = f"Unknown dataset: {dataset_name}. Available: {sorted(DATASET_CONFIGS.keys())}"
        raise KeyError(msg)

    config: DatasetConfig = DATASET_CONFIGS[dataset_name]
    root = data_dir if data_dir is not None else DEFAULT_DATA_DIR
    settings = AnnotationSettings(e_drive_root=root)
    return get_dataset_path(config, settings)


def ensure_output_dir(output_dir: Path | None = None) -> Path:
    """Create and return the benchmark output directory.

    Args:
        output_dir: Override output directory. Uses BENCHMARK_OUTPUT_DIR if None.

    Returns:
        Path to the output directory (created if it doesn't exist).
    """
    target = output_dir if output_dir is not None else BENCHMARK_OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target
