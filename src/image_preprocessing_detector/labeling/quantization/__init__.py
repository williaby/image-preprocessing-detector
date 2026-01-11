"""Project B: Quantization Factory.

This module provides standardized quantization of candidate models into
INT8 and INT4 variants with consistent packaging and metadata.

The Quantization Factory is transformation-only - no benchmarking or
training is performed here.

Supported Backends:
    - bitsandbytes: NVIDIA GPU quantization (llm.int8, nf4)
    - auto-gptq: GPTQ quantization
    - autoawq: AWQ quantization

Key Components:
    - QuantizationPipeline: Main quantization orchestration
    - QuantizationRecipe: Pre-configured model-family recipes
    - QuantizationConfig: Fine-grained configuration
    - recommend_recipe: Auto-select best recipe for a model

Example:
    >>> from image_preprocessing_detector.labeling import ModelSpec, ModelSource
    >>> from image_preprocessing_detector.labeling.quantization import (
    ...     QuantizationPipeline,
    ...     recommend_recipe,
    ... )
    >>>
    >>> spec = ModelSpec(
    ...     source=ModelSource.HUGGINGFACE,
    ...     id="HuggingFaceTB/SmolVLM-256M-Instruct",
    ...     revision="main",
    ... )
    >>> recipe = recommend_recipe(spec.id, bits=4)
    >>> pipeline = QuantizationPipeline()
    >>> result = pipeline.quantize(spec, bits=4, config=recipe.config)
    >>> print(f"Compression: {result.compression_ratio:.1f}x")
"""

from image_preprocessing_detector.labeling.quantization.pipeline import (
    QuantizationBackend,
    QuantizationConfig,
    QuantizationPipeline,
    QuantizationResult,
    QuantizationType,
)
from image_preprocessing_detector.labeling.quantization.recipes import (
    ALL_RECIPES,
    ModelFamily,
    QuantizationRecipe,
    RecipeOptimization,
    create_custom_recipe,
    detect_model_family,
    get_recipe,
    list_recipes,
    recommend_recipe,
)

__all__ = [
    # Recipes
    "ALL_RECIPES",
    "ModelFamily",
    # Pipeline
    "QuantizationBackend",
    "QuantizationConfig",
    "QuantizationPipeline",
    "QuantizationRecipe",
    "QuantizationResult",
    "QuantizationType",
    "RecipeOptimization",
    "create_custom_recipe",
    "detect_model_family",
    "get_recipe",
    "list_recipes",
    "recommend_recipe",
]
