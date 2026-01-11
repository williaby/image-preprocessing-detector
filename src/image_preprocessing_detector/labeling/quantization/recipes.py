# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Quantization recipes for different model families.

This module provides pre-configured quantization recipes optimized for
specific model architectures and use cases.

Recipe Categories:
    - Speed-optimized: Maximize inference throughput
    - Quality-optimized: Minimize accuracy degradation
    - Memory-optimized: Minimize VRAM usage
    - Balanced: Good trade-off between all factors

Model Family Support:
    - LLaMA/LLaMA-2/LLaMA-3
    - Qwen/Qwen2
    - Mistral/Mixtral
    - Phi-2/Phi-3
    - SmolVLM
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from image_preprocessing_detector.labeling.quantization.pipeline import (
    QuantizationBackend,
    QuantizationConfig,
    QuantizationType,
)

logger = structlog.get_logger(__name__)


class RecipeOptimization(Enum):
    """Optimization target for recipe."""

    SPEED = "speed"
    QUALITY = "quality"
    MEMORY = "memory"
    BALANCED = "balanced"


class ModelFamily(Enum):
    """Supported model families."""

    LLAMA = "llama"
    QWEN = "qwen"
    MISTRAL = "mistral"
    PHI = "phi"
    SMOLVLM = "smolvlm"
    GENERIC = "generic"


@dataclass
class QuantizationRecipe:
    """Pre-configured quantization recipe.

    Attributes:
        name: Recipe name
        description: Recipe description
        bits: Target bit precision
        config: Full quantization configuration
        model_families: Compatible model families
        optimization: Optimization target
        expected_speedup: Expected inference speedup vs FP16
        expected_quality_loss: Expected quality degradation (%)
        min_vram_gb: Minimum VRAM required
    """

    name: str
    description: str
    bits: int
    config: QuantizationConfig
    model_families: list[ModelFamily]
    optimization: RecipeOptimization
    expected_speedup: float = 1.0
    expected_quality_loss: float = 0.0
    min_vram_gb: float = 4.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "bits": self.bits,
            "config": self.config.to_dict(),
            "model_families": [f.value for f in self.model_families],
            "optimization": self.optimization.value,
            "expected_speedup": self.expected_speedup,
            "expected_quality_loss": self.expected_quality_loss,
            "min_vram_gb": self.min_vram_gb,
        }


# =============================================================================
# INT8 Recipes
# =============================================================================

INT8_SPEED_RECIPE = QuantizationRecipe(
    name="int8-speed",
    description="INT8 quantization optimized for inference speed",
    bits=8,
    config=QuantizationConfig(
        bits=8,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.INT8,
        use_double_quant=False,
        compute_dtype="float16",
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.PHI,
        ModelFamily.SMOLVLM,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.SPEED,
    expected_speedup=1.5,
    expected_quality_loss=0.5,
    min_vram_gb=8.0,
)

INT8_QUALITY_RECIPE = QuantizationRecipe(
    name="int8-quality",
    description="INT8 quantization optimized for minimal quality loss",
    bits=8,
    config=QuantizationConfig(
        bits=8,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.INT8,
        use_double_quant=False,
        compute_dtype="float32",  # Higher precision compute
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.PHI,
        ModelFamily.SMOLVLM,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.QUALITY,
    expected_speedup=1.3,
    expected_quality_loss=0.2,
    min_vram_gb=10.0,
)


# =============================================================================
# INT4 Recipes (bitsandbytes NF4)
# =============================================================================

INT4_NF4_BALANCED_RECIPE = QuantizationRecipe(
    name="int4-nf4-balanced",
    description="NF4 quantization with double quantization for balanced performance",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.NF4,
        use_double_quant=True,
        compute_dtype="float16",
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.PHI,
        ModelFamily.SMOLVLM,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.BALANCED,
    expected_speedup=2.0,
    expected_quality_loss=1.5,
    min_vram_gb=4.0,
)

INT4_NF4_MEMORY_RECIPE = QuantizationRecipe(
    name="int4-nf4-memory",
    description="NF4 quantization optimized for minimal VRAM usage",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.NF4,
        use_double_quant=True,
        compute_dtype="float16",
        group_size=64,  # Smaller groups = less memory
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.PHI,
        ModelFamily.SMOLVLM,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.MEMORY,
    expected_speedup=1.8,
    expected_quality_loss=2.0,
    min_vram_gb=3.0,
)


# =============================================================================
# INT4 Recipes (GPTQ)
# =============================================================================

INT4_GPTQ_QUALITY_RECIPE = QuantizationRecipe(
    name="int4-gptq-quality",
    description="GPTQ quantization for best 4-bit quality",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.GPTQ,
        quant_type=QuantizationType.INT4,
        group_size=128,
        calibration_samples=256,  # More samples = better calibration
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.QUALITY,
    expected_speedup=2.2,
    expected_quality_loss=1.0,
    min_vram_gb=6.0,
)

INT4_GPTQ_SPEED_RECIPE = QuantizationRecipe(
    name="int4-gptq-speed",
    description="GPTQ quantization optimized for inference speed",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.GPTQ,
        quant_type=QuantizationType.INT4,
        group_size=32,  # Smaller groups = faster inference
        calibration_samples=128,
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.SPEED,
    expected_speedup=2.5,
    expected_quality_loss=2.0,
    min_vram_gb=5.0,
)


# =============================================================================
# INT4 Recipes (AWQ)
# =============================================================================

INT4_AWQ_BALANCED_RECIPE = QuantizationRecipe(
    name="int4-awq-balanced",
    description="AWQ quantization for balanced quality and speed",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.AWQ,
        quant_type=QuantizationType.INT4,
        group_size=128,
    ),
    model_families=[
        ModelFamily.LLAMA,
        ModelFamily.QWEN,
        ModelFamily.MISTRAL,
        ModelFamily.GENERIC,
    ],
    optimization=RecipeOptimization.BALANCED,
    expected_speedup=2.3,
    expected_quality_loss=1.2,
    min_vram_gb=5.0,
)


# =============================================================================
# Model-Family Specific Recipes
# =============================================================================

SMOLVLM_INT4_RECIPE = QuantizationRecipe(
    name="smolvlm-int4",
    description="INT4 recipe optimized for SmolVLM models",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.NF4,
        use_double_quant=True,
        compute_dtype="float16",
        trust_remote_code=True,
    ),
    model_families=[ModelFamily.SMOLVLM],
    optimization=RecipeOptimization.BALANCED,
    expected_speedup=2.0,
    expected_quality_loss=1.5,
    min_vram_gb=2.0,  # SmolVLM is already small
)

QWEN_VL_INT4_RECIPE = QuantizationRecipe(
    name="qwen-vl-int4",
    description="INT4 recipe optimized for Qwen-VL models",
    bits=4,
    config=QuantizationConfig(
        bits=4,
        backend=QuantizationBackend.BITSANDBYTES,
        quant_type=QuantizationType.NF4,
        use_double_quant=True,
        compute_dtype="bfloat16",  # Qwen prefers bfloat16
        trust_remote_code=True,
    ),
    model_families=[ModelFamily.QWEN],
    optimization=RecipeOptimization.BALANCED,
    expected_speedup=2.0,
    expected_quality_loss=1.5,
    min_vram_gb=4.0,
)


# =============================================================================
# Recipe Registry
# =============================================================================

ALL_RECIPES: dict[str, QuantizationRecipe] = {
    # INT8
    "int8-speed": INT8_SPEED_RECIPE,
    "int8-quality": INT8_QUALITY_RECIPE,
    # INT4 bitsandbytes
    "int4-nf4-balanced": INT4_NF4_BALANCED_RECIPE,
    "int4-nf4-memory": INT4_NF4_MEMORY_RECIPE,
    # INT4 GPTQ
    "int4-gptq-quality": INT4_GPTQ_QUALITY_RECIPE,
    "int4-gptq-speed": INT4_GPTQ_SPEED_RECIPE,
    # INT4 AWQ
    "int4-awq-balanced": INT4_AWQ_BALANCED_RECIPE,
    # Model-specific
    "smolvlm-int4": SMOLVLM_INT4_RECIPE,
    "qwen-vl-int4": QWEN_VL_INT4_RECIPE,
}


def get_recipe(name: str) -> QuantizationRecipe:
    """Get a quantization recipe by name.

    Args:
        name: Recipe name.

    Returns:
        QuantizationRecipe.

    Raises:
        KeyError: If recipe not found.
    """
    if name not in ALL_RECIPES:
        available = ", ".join(ALL_RECIPES.keys())
        msg = f"Recipe '{name}' not found. Available: {available}"
        raise KeyError(msg)
    return ALL_RECIPES[name]


def list_recipes(
    bits: int | None = None,
    optimization: RecipeOptimization | None = None,
    model_family: ModelFamily | None = None,
) -> list[QuantizationRecipe]:
    """List recipes matching criteria.

    Args:
        bits: Filter by bit precision.
        optimization: Filter by optimization target.
        model_family: Filter by compatible model family.

    Returns:
        List of matching recipes.
    """
    results = []

    for recipe in ALL_RECIPES.values():
        # Filter by bits
        if bits is not None and recipe.bits != bits:
            continue

        # Filter by optimization
        if optimization is not None and recipe.optimization != optimization:
            continue

        # Filter by model family
        if model_family is not None and model_family not in recipe.model_families:
            continue

        results.append(recipe)

    return results


def detect_model_family(model_id: str) -> ModelFamily:
    """Detect model family from model ID.

    Args:
        model_id: HuggingFace model ID.

    Returns:
        Detected ModelFamily.
    """
    model_lower = model_id.lower()

    if "smolvlm" in model_lower:
        return ModelFamily.SMOLVLM

    if "qwen" in model_lower:
        return ModelFamily.QWEN

    if "llama" in model_lower or "meta-llama" in model_lower:
        return ModelFamily.LLAMA

    if "mistral" in model_lower or "mixtral" in model_lower:
        return ModelFamily.MISTRAL

    if "phi" in model_lower:
        return ModelFamily.PHI

    return ModelFamily.GENERIC


def recommend_recipe(
    model_id: str,
    bits: int = 4,
    optimization: RecipeOptimization = RecipeOptimization.BALANCED,
    available_vram_gb: float | None = None,
) -> QuantizationRecipe:
    """Recommend a quantization recipe for a model.

    Args:
        model_id: HuggingFace model ID.
        bits: Target bit precision.
        optimization: Optimization target.
        available_vram_gb: Available VRAM in GB (for filtering).

    Returns:
        Recommended QuantizationRecipe.

    Example:
        >>> recipe = recommend_recipe(
        ...     "HuggingFaceTB/SmolVLM-256M-Instruct",
        ...     bits=4,
        ...     optimization=RecipeOptimization.BALANCED,
        ... )
        >>> print(recipe.name)  # "smolvlm-int4"
    """
    model_family = detect_model_family(model_id)

    # Try model-specific recipe first
    model_specific = list_recipes(
        bits=bits,
        optimization=optimization,
        model_family=model_family,
    )

    if model_specific:
        # Filter by VRAM if specified
        if available_vram_gb is not None:
            model_specific = [
                r for r in model_specific if r.min_vram_gb <= available_vram_gb
            ]

        if model_specific:
            # Prefer model-specific over generic
            for recipe in model_specific:
                if len(recipe.model_families) == 1:
                    logger.info(
                        "recipe_recommended",
                        recipe=recipe.name,
                        model_id=model_id,
                        reason="model_specific",
                    )
                    return recipe

            # Return first match
            recipe = model_specific[0]
            logger.info(
                "recipe_recommended",
                recipe=recipe.name,
                model_id=model_id,
                reason="family_match",
            )
            return recipe

    # Fall back to generic recipes
    generic = list_recipes(bits=bits, optimization=optimization)

    if available_vram_gb is not None:
        generic = [r for r in generic if r.min_vram_gb <= available_vram_gb]

    if generic:
        recipe = generic[0]
        logger.info(
            "recipe_recommended",
            recipe=recipe.name,
            model_id=model_id,
            reason="generic_fallback",
        )
        return recipe

    # Ultimate fallback
    fallback = INT4_NF4_BALANCED_RECIPE if bits == 4 else INT8_SPEED_RECIPE
    logger.warning(
        "recipe_fallback",
        recipe=fallback.name,
        model_id=model_id,
        reason="no_match_found",
    )
    return fallback


def create_custom_recipe(
    name: str,
    bits: int,
    backend: QuantizationBackend,
    quant_type: QuantizationType,
    optimization: RecipeOptimization = RecipeOptimization.BALANCED,
    **config_kwargs: Any,
) -> QuantizationRecipe:
    """Create a custom quantization recipe.

    Args:
        name: Recipe name.
        bits: Target bit precision.
        backend: Quantization backend.
        quant_type: Quantization type.
        optimization: Optimization target.
        **config_kwargs: Additional QuantizationConfig arguments.

    Returns:
        Custom QuantizationRecipe.

    Example:
        >>> recipe = create_custom_recipe(
        ...     name="my-custom-int4",
        ...     bits=4,
        ...     backend=QuantizationBackend.BITSANDBYTES,
        ...     quant_type=QuantizationType.NF4,
        ...     use_double_quant=True,
        ...     group_size=64,
        ... )
    """
    config = QuantizationConfig(
        bits=bits,
        backend=backend,
        quant_type=quant_type,
        **config_kwargs,
    )

    return QuantizationRecipe(
        name=name,
        description=f"Custom {bits}-bit recipe using {backend.value}",
        bits=bits,
        config=config,
        model_families=[ModelFamily.GENERIC],
        optimization=optimization,
    )
