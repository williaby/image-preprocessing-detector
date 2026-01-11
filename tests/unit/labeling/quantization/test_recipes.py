# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for quantization recipes."""

from __future__ import annotations

import pytest

from image_preprocessing_detector.labeling.quantization.pipeline import (
    QuantizationBackend,
    QuantizationType,
)
from image_preprocessing_detector.labeling.quantization.recipes import (
    ALL_RECIPES,
    INT4_NF4_BALANCED_RECIPE,
    INT8_SPEED_RECIPE,
    ModelFamily,
    QuantizationRecipe,
    RecipeOptimization,
    create_custom_recipe,
    detect_model_family,
    get_recipe,
    list_recipes,
    recommend_recipe,
)


class TestAllRecipes:
    """Tests for recipe registry."""

    def test_recipes_exist(self):
        """Test that recipes are registered."""
        assert len(ALL_RECIPES) > 0

    def test_all_recipes_valid(self):
        """Test all recipes have valid configuration."""
        for name, recipe in ALL_RECIPES.items():
            assert isinstance(recipe, QuantizationRecipe)
            assert recipe.name == name
            assert recipe.bits in (4, 8)
            assert recipe.config is not None
            assert len(recipe.model_families) > 0

    def test_int8_recipes_exist(self):
        """Test INT8 recipes are available."""
        int8_recipes = [r for r in ALL_RECIPES.values() if r.bits == 8]
        assert len(int8_recipes) >= 2

    def test_int4_recipes_exist(self):
        """Test INT4 recipes are available."""
        int4_recipes = [r for r in ALL_RECIPES.values() if r.bits == 4]
        assert len(int4_recipes) >= 4


class TestGetRecipe:
    """Tests for get_recipe function."""

    def test_get_existing_recipe(self):
        """Test getting an existing recipe."""
        recipe = get_recipe("int8-speed")
        assert recipe.name == "int8-speed"
        assert recipe.bits == 8

    def test_get_nonexistent_recipe(self):
        """Test getting a nonexistent recipe raises error."""
        with pytest.raises(KeyError, match="not found"):
            get_recipe("nonexistent-recipe")


class TestListRecipes:
    """Tests for list_recipes function."""

    def test_list_all_recipes(self):
        """Test listing all recipes."""
        recipes = list_recipes()
        assert len(recipes) == len(ALL_RECIPES)

    def test_filter_by_bits(self):
        """Test filtering by bit precision."""
        int4_recipes = list_recipes(bits=4)
        assert all(r.bits == 4 for r in int4_recipes)

        int8_recipes = list_recipes(bits=8)
        assert all(r.bits == 8 for r in int8_recipes)

    def test_filter_by_optimization(self):
        """Test filtering by optimization target."""
        speed_recipes = list_recipes(optimization=RecipeOptimization.SPEED)
        assert all(r.optimization == RecipeOptimization.SPEED for r in speed_recipes)

    def test_filter_by_model_family(self):
        """Test filtering by model family."""
        smolvlm_recipes = list_recipes(model_family=ModelFamily.SMOLVLM)
        assert all(ModelFamily.SMOLVLM in r.model_families for r in smolvlm_recipes)

    def test_multiple_filters(self):
        """Test filtering by multiple criteria."""
        recipes = list_recipes(
            bits=4,
            optimization=RecipeOptimization.BALANCED,
        )
        assert all(r.bits == 4 for r in recipes)
        assert all(r.optimization == RecipeOptimization.BALANCED for r in recipes)


class TestDetectModelFamily:
    """Tests for detect_model_family function."""

    def test_detect_smolvlm(self):
        """Test detecting SmolVLM family."""
        family = detect_model_family("HuggingFaceTB/SmolVLM-256M-Instruct")
        assert family == ModelFamily.SMOLVLM

    def test_detect_qwen(self):
        """Test detecting Qwen family."""
        family = detect_model_family("Qwen/Qwen2-VL-7B-Instruct")
        assert family == ModelFamily.QWEN

    def test_detect_llama(self):
        """Test detecting LLaMA family."""
        family = detect_model_family("meta-llama/Llama-3.1-8B-Instruct")
        assert family == ModelFamily.LLAMA

    def test_detect_mistral(self):
        """Test detecting Mistral family."""
        family = detect_model_family("mistralai/Mistral-7B-Instruct-v0.1")
        assert family == ModelFamily.MISTRAL

    def test_detect_phi(self):
        """Test detecting Phi family."""
        family = detect_model_family("microsoft/phi-3-mini-4k-instruct")
        assert family == ModelFamily.PHI

    def test_detect_generic(self):
        """Test detecting generic/unknown family."""
        family = detect_model_family("unknown-org/random-model")
        assert family == ModelFamily.GENERIC


class TestRecommendRecipe:
    """Tests for recommend_recipe function."""

    def test_recommend_for_smolvlm(self):
        """Test recommending recipe for SmolVLM."""
        recipe = recommend_recipe(
            "HuggingFaceTB/SmolVLM-256M-Instruct",
            bits=4,
        )
        # Should get SmolVLM-specific recipe
        assert recipe.bits == 4
        assert ModelFamily.SMOLVLM in recipe.model_families

    def test_recommend_for_qwen(self):
        """Test recommending recipe for Qwen."""
        recipe = recommend_recipe(
            "Qwen/Qwen2-VL-7B-Instruct",
            bits=4,
        )
        assert recipe.bits == 4

    def test_recommend_int8(self):
        """Test recommending INT8 recipe."""
        recipe = recommend_recipe(
            "HuggingFaceTB/SmolVLM-256M-Instruct",
            bits=8,
        )
        assert recipe.bits == 8

    def test_recommend_with_vram_constraint(self):
        """Test recommendation with VRAM constraint."""
        recipe = recommend_recipe(
            "generic-model",
            bits=4,
            available_vram_gb=3.0,
        )
        assert recipe.min_vram_gb <= 3.0

    def test_recommend_speed_optimized(self):
        """Test recommending speed-optimized recipe."""
        recipe = recommend_recipe(
            "generic-model",
            bits=4,
            optimization=RecipeOptimization.SPEED,
        )
        # Should prioritize speed
        assert recipe is not None


class TestCreateCustomRecipe:
    """Tests for create_custom_recipe function."""

    def test_create_basic_recipe(self):
        """Test creating a basic custom recipe."""
        recipe = create_custom_recipe(
            name="my-custom",
            bits=4,
            backend=QuantizationBackend.BITSANDBYTES,
            quant_type=QuantizationType.NF4,
        )

        assert recipe.name == "my-custom"
        assert recipe.bits == 4
        assert recipe.config.backend == QuantizationBackend.BITSANDBYTES

    def test_create_with_extra_config(self):
        """Test creating recipe with extra config options."""
        recipe = create_custom_recipe(
            name="custom-gptq",
            bits=4,
            backend=QuantizationBackend.GPTQ,
            quant_type=QuantizationType.INT4,
            group_size=64,
            calibration_samples=256,
        )

        assert recipe.config.group_size == 64
        assert recipe.config.calibration_samples == 256


class TestQuantizationRecipe:
    """Tests for QuantizationRecipe dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        recipe_dict = INT8_SPEED_RECIPE.to_dict()

        assert recipe_dict["name"] == "int8-speed"
        assert recipe_dict["bits"] == 8
        assert "config" in recipe_dict
        assert "model_families" in recipe_dict

    def test_expected_values(self):
        """Test expected performance values are reasonable."""
        for recipe in ALL_RECIPES.values():
            # Speedup should be positive
            assert recipe.expected_speedup > 0

            # Quality loss should be non-negative
            assert recipe.expected_quality_loss >= 0

            # VRAM should be positive
            assert recipe.min_vram_gb > 0

    def test_int4_higher_speedup_than_int8(self):
        """Test INT4 generally has higher speedup than INT8."""
        # This is expected behavior for most cases
        assert (
            INT4_NF4_BALANCED_RECIPE.expected_speedup
            >= INT8_SPEED_RECIPE.expected_speedup
        )
