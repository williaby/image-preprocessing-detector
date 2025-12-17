"""Labeling workstreams for LLM-based document quality assessment.

This package contains three interconnected workstreams:

- **arena**: Project A - Benchmarking Arena for model evaluation
- **quantization**: Project B - Unsloth quantization pipeline
- **finetuning**: Project C - DIQA-5000 fine-tuning

All workstreams share a common ModelSpec schema for plug-and-play model swapping.
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
