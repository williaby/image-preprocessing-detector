"""Inference backends for the Benchmarking Arena.

This module provides model inference implementations for different
model sources: HuggingFace, local artifacts, API providers, and Modal.

All backends implement the same interface for plug-and-play
model swapping.
"""

from image_preprocessing_detector.labeling.arena.inference.base import (
    InferenceBackend,
    InferenceConfig,
    InferenceError,
    ModelLoadError,
    ModelNotLoadedError,
    create_backend,
)

__all__ = [
    "InferenceBackend",
    "InferenceConfig",
    "InferenceError",
    "ModelLoadError",
    "ModelNotLoadedError",
    "create_backend",
]
