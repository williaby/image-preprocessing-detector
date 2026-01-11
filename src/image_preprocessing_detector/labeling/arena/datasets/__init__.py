"""Dataset adapters for Arena benchmarking.

This module provides dataset abstractions for loading and iterating
over benchmark datasets like DIQA-5000.
"""

from image_preprocessing_detector.labeling.arena.datasets.base import (
    BenchmarkDataset,
    DatasetSample,
    SyntheticDataset,
)

__all__ = [
    "BenchmarkDataset",
    "DatasetSample",
    "SyntheticDataset",
]
