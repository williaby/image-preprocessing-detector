"""Project B: Quantization Factory using Unsloth.

This module provides standardized quantization of candidate models into
8-bit and 4-bit variants with consistent packaging and metadata.

The Quantization Factory is transformation-only - no benchmarking or
training is performed here.

Key Components:
    - QuantizationPipeline: Main quantization orchestration
    - QuantizationRecipe: Model-family-specific recipes
    - ArtifactPackager: Standardized artifact packaging

Example:
    >>> from image_preprocessing_detector.labeling import ModelSpec
    >>> from image_preprocessing_detector.labeling.quantization import QuantizationPipeline
    >>>
    >>> spec = ModelSpec.from_yaml("base_model.yaml")
    >>> pipeline = QuantizationPipeline()
    >>> artifact = pipeline.quantize(spec, bits=8, output_dir="./artifacts/")
"""

__all__: list[str] = []
