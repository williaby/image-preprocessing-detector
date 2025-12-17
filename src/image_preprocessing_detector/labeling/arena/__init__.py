"""Project A: Benchmarking Arena for model evaluation.

This module provides a standardized, repeatable evaluation framework for
benchmarking document-quality models against the DIQA-5000 dataset.

The Arena is strictly evaluation-only - no training, fine-tuning, or
quantization is performed here.

Key Components:
    - ArenaRunner: Main benchmark execution engine
    - ArenaMetrics: PLCC, SRCC, MAE, RMSE calculations
    - Leaderboard: Report generation and ranking

Example:
    >>> from image_preprocessing_detector.labeling import ModelSpec
    >>> from image_preprocessing_detector.labeling.arena import ArenaRunner
    >>>
    >>> spec = ModelSpec.from_yaml("model.yaml")
    >>> runner = ArenaRunner()
    >>> result = runner.run(spec, dataset="diqa5000", split="test")
    >>> print(result.metrics)
"""

from image_preprocessing_detector.labeling.arena.metrics import (
    ArenaMetrics,
    compute_mae,
    compute_plcc,
    compute_rmse,
    compute_srcc,
)

__all__ = [
    "ArenaMetrics",
    "compute_mae",
    "compute_plcc",
    "compute_rmse",
    "compute_srcc",
]
