"""Labeling workstreams for document quality assessment.

Subpackages:

- **arena**: Model benchmarking arena for evaluation
- **domain**: Domain classification via LLMs
"""

from image_preprocessing_detector.labeling.model_spec import (
    ModelSource,
    ModelSpec,
    ModelVariant,
    RuntimeBackend,
)

__all__ = [
    "ModelSource",
    "ModelSpec",
    "ModelVariant",
    "RuntimeBackend",
]
