"""Project A: Benchmarking Arena for model evaluation.

This module provides a standardized, repeatable evaluation framework for
benchmarking document-quality models against the DIQA-5000 dataset.

The Arena is strictly evaluation-only - no training, fine-tuning, or
quantization is performed here.

Key Components:
    - ArenaRunner: Main benchmark execution engine
    - ArenaMetrics: PLCC, SRCC, MAE, RMSE calculations
    - Leaderboard: Report generation and ranking
    - InferenceBackend: Pluggable model inference

Example:
    >>> from image_preprocessing_detector.labeling import ModelSpec
    >>> from image_preprocessing_detector.labeling.arena import ArenaRunner, run_benchmark
    >>> from image_preprocessing_detector.labeling.arena.datasets.diqa5000 import DIQA5000Dataset
    >>>
    >>> spec = ModelSpec.from_yaml("model.yaml")
    >>> dataset = DIQA5000Dataset("/data/diqa5000", split="test")
    >>> runner = ArenaRunner()
    >>> result = runner.run(spec, dataset)
    >>> print(result.metrics)
"""

from image_preprocessing_detector.labeling.arena.inference.base import (
    InferenceBackend,
    InferenceConfig,
    InferenceError,
    ModelLoadError,
    ModelNotLoadedError,
    create_backend,
)
from image_preprocessing_detector.labeling.arena.metrics import (
    ArenaMetrics,
    DimensionMetrics,
    compare_models,
    compute_mae,
    compute_plcc,
    compute_rmse,
    compute_srcc,
)
from image_preprocessing_detector.labeling.arena.runner import (
    ArenaRunner,
    RunConfig,
    run_benchmark,
)
from image_preprocessing_detector.labeling.arena.schemas import (
    BenchmarkResult,
    DatasetInfo,
    DIQAGroundTruth,
    DIQAPrediction,
    ExecutionInfo,
    ProvenanceInfo,
    ReproducibilityManifest,
    RunStatus,
    SampleResult,
)

__all__ = [
    # Runner
    "ArenaRunner",
    "RunConfig",
    "run_benchmark",
    # Metrics
    "ArenaMetrics",
    "DimensionMetrics",
    "compare_models",
    "compute_mae",
    "compute_plcc",
    "compute_rmse",
    "compute_srcc",
    # Inference
    "InferenceBackend",
    "InferenceConfig",
    "InferenceError",
    "ModelLoadError",
    "ModelNotLoadedError",
    "create_backend",
    # Schemas
    "BenchmarkResult",
    "DatasetInfo",
    "DIQAGroundTruth",
    "DIQAPrediction",
    "ExecutionInfo",
    "ProvenanceInfo",
    "ReproducibilityManifest",
    "RunStatus",
    "SampleResult",
]
