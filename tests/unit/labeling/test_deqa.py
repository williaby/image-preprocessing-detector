"""Tests for DeQA-Doc labeling infrastructure.

This module tests the configuration, base classes, and factory function
for the DeQA multi-mode labeling system.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.labeling.deqa import (
    DATASET_CONFIGS,
    MODEL_REGISTRY,
    QUALITY_LEVELS,
    QUALITY_SCORES,
    CheckpointManager,
    ComparisonMetrics,
    DeQAConfig,
    DeQAInference,
    DeQAScore,
    InferenceMode,
    LabelAnalysis,
    LabelResult,
    ModelConfig,
    ModelSource,
    QualityDimension,
    VQualAScore,
    create_inference_engine,
)


class TestInferenceMode:
    """Tests for InferenceMode enum."""

    def test_all_modes_exist(self) -> None:
        """Test that all expected inference modes exist."""
        assert InferenceMode.SPECIALIST.value == "specialist"
        assert InferenceMode.SPECIALIST_TRUE.value == "specialist_true"
        assert InferenceMode.ENSEMBLE.value == "ensemble"
        assert InferenceMode.ENSEMBLE_TRUE.value == "ensemble_true"
        assert InferenceMode.VL.value == "vl"

    def test_mode_from_string(self) -> None:
        """Test creating mode from string value."""
        assert InferenceMode("specialist") == InferenceMode.SPECIALIST
        assert InferenceMode("ensemble") == InferenceMode.ENSEMBLE
        assert InferenceMode("vl") == InferenceMode.VL

    def test_mode_value_property(self) -> None:
        """Test mode value property."""
        assert InferenceMode.SPECIALIST.value == "specialist"
        assert InferenceMode.ENSEMBLE_TRUE.value == "ensemble_true"


class TestModelSource:
    """Tests for ModelSource enum."""

    def test_all_sources_exist(self) -> None:
        """Test that all expected model sources exist."""
        assert ModelSource.HUGGINGFACE.value == "huggingface"
        assert ModelSource.MODELSCOPE.value == "modelscope"
        assert ModelSource.LOCAL.value == "local"


class TestQualityDimension:
    """Tests for QualityDimension enum."""

    def test_all_dimensions_exist(self) -> None:
        """Test that all quality dimensions exist."""
        assert QualityDimension.OVERALL.value == "overall"
        assert QualityDimension.SHARPNESS.value == "sharpness"
        assert QualityDimension.COLOR.value == "color"


class TestQualityConstants:
    """Tests for quality level constants."""

    def test_quality_levels(self) -> None:
        """Test quality levels list."""
        assert QUALITY_LEVELS == ["excellent", "good", "fair", "poor", "bad"]

    def test_quality_scores(self) -> None:
        """Test quality scores list."""
        assert QUALITY_SCORES == [5.0, 4.0, 3.0, 2.0, 1.0]

    def test_levels_scores_same_length(self) -> None:
        """Test that levels and scores have same length."""
        assert len(QUALITY_LEVELS) == len(QUALITY_SCORES)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic model config creation."""
        config = ModelConfig(
            model_id="test-model",
            source=ModelSource.HUGGINGFACE,
            model_path="org/model",
            architecture="mplug_owl2",
            dimensions=[QualityDimension.OVERALL],
        )
        assert config.model_id == "test-model"
        assert config.source == ModelSource.HUGGINGFACE
        assert config.training_method is None
        assert config.resolution == 1024  # default

    def test_all_fields(self) -> None:
        """Test model config with all fields."""
        config = ModelConfig(
            model_id="diqa-overall",
            source=ModelSource.MODELSCOPE,
            model_path="zhalala/DeQA-Doc",
            architecture="mplug_owl2",
            dimensions=[QualityDimension.OVERALL],
            training_method="full",
            resolution=1024,
            pretrain_dataset="koniq-10k",
            checkpoint_subdir="deqa_0618_overall_norm_pair_1024",
            notes="Test model",
        )
        assert config.training_method == "full"
        assert config.pretrain_dataset == "koniq-10k"
        assert config.checkpoint_subdir is not None


class TestModelRegistry:
    """Tests for MODEL_REGISTRY."""

    def test_registry_not_empty(self) -> None:
        """Test that model registry has entries."""
        assert len(MODEL_REGISTRY) > 0

    def test_required_models_exist(self) -> None:
        """Test that required models are in registry."""
        required = [
            "deqa-score-mix3",
            "diqa-overall",
            "diqa-sharpness",
            "diqa-color",
        ]
        for model_id in required:
            assert model_id in MODEL_REGISTRY

    def test_all_entries_are_model_configs(self) -> None:
        """Test that all registry entries are ModelConfig instances."""
        for model_id, config in MODEL_REGISTRY.items():
            assert isinstance(config, ModelConfig)
            assert config.model_id == model_id

    def test_dimension_specialists(self) -> None:
        """Test dimension specialist configurations."""
        overall = MODEL_REGISTRY["diqa-overall"]
        assert QualityDimension.OVERALL in overall.dimensions
        assert overall.training_method == "full"

        sharpness = MODEL_REGISTRY["diqa-sharpness"]
        assert QualityDimension.SHARPNESS in sharpness.dimensions

        color = MODEL_REGISTRY["diqa-color"]
        assert QualityDimension.COLOR in color.dimensions


class TestDatasetConfigs:
    """Tests for DATASET_CONFIGS."""

    def test_configs_not_empty(self) -> None:
        """Test that dataset configs has entries."""
        assert len(DATASET_CONFIGS) > 0

    def test_required_datasets_exist(self) -> None:
        """Test that required datasets are configured."""
        required = ["diqa-5000", "smartdoc-qa"]
        for dataset in required:
            assert dataset in DATASET_CONFIGS

    def test_dataset_config_fields(self) -> None:
        """Test dataset config has required fields."""
        config = DATASET_CONFIGS["diqa-5000"]
        assert config.name == "diqa-5000"
        assert config.num_images == 5000
        assert config.priority == "CRITICAL"
        assert config.has_ground_truth is True


class TestDeQAConfig:
    """Tests for DeQAConfig dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic config creation."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)
        assert config.mode == InferenceMode.SPECIALIST
        assert config.device == "cuda:0"
        assert config.batch_size == 8

    def test_string_mode_conversion(self) -> None:
        """Test that string mode is converted to enum."""
        config = DeQAConfig(mode="specialist")  # type: ignore[arg-type]
        assert config.mode == InferenceMode.SPECIALIST

    def test_vl_mode_default_model(self) -> None:
        """Test VL mode gets default model."""
        config = DeQAConfig(mode=InferenceMode.VL)
        assert config.model_id == "deqa-score-mix3"

    def test_path_conversion(self) -> None:
        """Test string path is converted to Path."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST, output_dir="/tmp/test")  # type: ignore[arg-type]
        assert isinstance(config.output_dir, Path)
        assert str(config.output_dir) == "/tmp/test"

    def test_get_model_configs_specialist(self) -> None:
        """Test get_model_configs for specialist mode."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)
        models = config.get_model_configs()
        assert len(models) == 1
        assert models[0].model_id == "deqa-score-mix3"

    def test_get_model_configs_specialist_true(self) -> None:
        """Test get_model_configs for specialist_true mode."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST_TRUE)
        models = config.get_model_configs()
        assert len(models) == 3
        model_ids = {m.model_id for m in models}
        assert "diqa-overall" in model_ids
        assert "diqa-sharpness" in model_ids
        assert "diqa-color" in model_ids

    def test_get_model_configs_ensemble(self) -> None:
        """Test get_model_configs for ensemble mode."""
        config = DeQAConfig(mode=InferenceMode.ENSEMBLE)
        models = config.get_model_configs()
        assert len(models) == 5  # m0, m1, m3, Q0, Q1

    def test_get_model_configs_vl(self) -> None:
        """Test get_model_configs for vl mode."""
        config = DeQAConfig(mode=InferenceMode.VL, model_id="deqa-doc-mix")
        models = config.get_model_configs()
        assert len(models) == 1
        assert models[0].model_id == "deqa-doc-mix"

    def test_get_model_configs_vl_custom(self) -> None:
        """Test get_model_configs for vl mode with custom model."""
        config = DeQAConfig(mode=InferenceMode.VL, model_id="custom/my-model")
        models = config.get_model_configs()
        assert len(models) == 1
        assert models[0].model_id == "custom/my-model"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        config = DeQAConfig(
            mode=InferenceMode.SPECIALIST,
            device="cuda:1",
            batch_size=16,
        )
        data = config.to_dict()
        assert data["mode"] == "specialist"
        assert data["device"] == "cuda:1"
        assert data["batch_size"] == 16

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "mode": "ensemble",
            "device": "cuda:0",
            "batch_size": 4,
            "dimensions": ["overall", "sharpness"],
        }
        config = DeQAConfig.from_dict(data)
        assert config.mode == InferenceMode.ENSEMBLE
        assert config.batch_size == 4
        assert len(config.dimensions) == 2


class TestDeQAScore:
    """Tests for DeQAScore dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic score creation."""
        score = DeQAScore(
            dimension=QualityDimension.OVERALL,
            score=4.2,
        )
        assert score.dimension == QualityDimension.OVERALL
        assert score.score == 4.2
        assert score.logits == {}
        assert score.probs == {}

    def test_with_all_fields(self) -> None:
        """Test score with all fields."""
        score = DeQAScore(
            dimension=QualityDimension.SHARPNESS,
            score=3.5,
            logits={"excellent": 1.0, "good": 2.0},
            probs={"excellent": 0.3, "good": 0.7},
            model_id="diqa-sharpness",
        )
        assert score.logits["excellent"] == 1.0
        assert score.probs["good"] == 0.7
        assert score.model_id == "diqa-sharpness"

    def test_to_dict(self) -> None:
        """Test serialization."""
        score = DeQAScore(
            dimension=QualityDimension.COLOR,
            score=4.0,
            model_id="test",
        )
        data = score.to_dict()
        assert data["dimension"] == "color"
        assert data["score"] == 4.0

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "dimension": "overall",
            "score": 3.8,
            "logits": {"good": 1.5},
            "probs": {"good": 0.6},
            "model_id": "test-model",
        }
        score = DeQAScore.from_dict(data)
        assert score.dimension == QualityDimension.OVERALL
        assert score.score == 3.8
        assert score.model_id == "test-model"


class TestLabelResult:
    """Tests for LabelResult dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic result creation."""
        result = LabelResult(
            image_path="/path/to/image.jpg",
            dataset="diqa-5000",
            mode="specialist",
            scores={"overall": 4.0, "sharpness": 3.5},
        )
        assert result.image_path == "/path/to/image.jpg"
        assert result.dataset == "diqa-5000"
        assert result.scores["overall"] == 4.0
        assert result.timestamp != ""  # auto-set

    def test_auto_timestamp(self) -> None:
        """Test automatic timestamp generation."""
        result = LabelResult(
            image_path="/test.jpg",
            dataset="test",
            mode="vl",
            scores={},
        )
        # Timestamp should be ISO format
        assert "T" in result.timestamp

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        result = LabelResult(
            image_path="/test.jpg",
            dataset="test",
            mode="ensemble",
            scores={"overall": 4.0},
            probs={"overall": {"good": 0.8}},
        )
        data = result.to_dict()
        assert data["image"] == "/test.jpg"
        assert data["mode"] == "ensemble"

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        result = LabelResult(
            image_path="/test.jpg",
            dataset="test",
            mode="vl",
            scores={"overall": 4.0},
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["image"] == "/test.jpg"

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "image": "/test.jpg",
            "dataset": "diqa-5000",
            "mode": "specialist",
            "scores": {"overall": 3.5},
            "timestamp": "2025-01-01T00:00:00",
        }
        result = LabelResult.from_dict(data)
        assert result.image_path == "/test.jpg"
        assert result.scores["overall"] == 3.5


class TestDeQAInferenceBase:
    """Tests for DeQAInference base class."""

    def test_initialization(self) -> None:
        """Test base class initialization."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)

        # Create a concrete subclass for testing
        class TestInference(DeQAInference):
            def load_models(self, device: str | None = None) -> None:
                self._loaded = True

            def unload_models(self) -> None:
                self._loaded = False

            def predict(self, image: Any) -> dict[str, DeQAScore]:
                return {}

        engine = TestInference(config)
        assert engine.config == config
        assert not engine.is_loaded

    def test_is_loaded_property(self) -> None:
        """Test is_loaded property."""
        config = DeQAConfig(mode=InferenceMode.VL)

        class TestInference(DeQAInference):
            def load_models(self, device: str | None = None) -> None:
                self._loaded = True

            def unload_models(self) -> None:
                self._loaded = False

            def predict(self, image: Any) -> dict[str, DeQAScore]:
                return {}

        engine = TestInference(config)
        assert not engine.is_loaded
        engine.load_models()
        assert engine.is_loaded
        engine.unload_models()
        assert not engine.is_loaded

    def test_predict_batch_default(self) -> None:
        """Test default predict_batch implementation."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)

        class TestInference(DeQAInference):
            def load_models(self, device: str | None = None) -> None:
                pass

            def unload_models(self) -> None:
                pass

            def predict(self, image: Any) -> dict[str, DeQAScore]:
                return {
                    "overall": DeQAScore(
                        dimension=QualityDimension.OVERALL,
                        score=4.0,
                    )
                }

        engine = TestInference(config)
        # Create proper PIL Image objects for type safety
        from PIL import Image as PILImage

        mock_images = [PILImage.new("RGB", (100, 100)) for _ in range(3)]
        results = engine.predict_batch(mock_images)
        assert len(results) == 3
        assert all("overall" in r for r in results)

    def test_compute_score_from_probs(self) -> None:
        """Test score computation from probabilities."""
        probs = {
            "excellent": 0.2,
            "good": 0.5,
            "fair": 0.2,
            "poor": 0.1,
            "bad": 0.0,
        }
        score = DeQAInference.compute_score_from_probs(probs)
        # 0.2*5 + 0.5*4 + 0.2*3 + 0.1*2 + 0.0*1 = 1 + 2 + 0.6 + 0.2 = 3.8
        assert abs(score - 3.8) < 0.001

    def test_normalize_logits_to_probs(self) -> None:
        """Test logits to probability conversion."""
        logits = {
            "excellent": 1.0,
            "good": 2.0,
            "fair": 0.5,
            "poor": 0.0,
            "bad": -1.0,
        }
        probs = DeQAInference.normalize_logits_to_probs(logits)
        # Check probabilities sum to 1
        assert abs(sum(probs.values()) - 1.0) < 0.001
        # Check highest logit has highest probability
        assert probs["good"] > probs["excellent"] > probs["fair"]

    def test_expand_to_square_already_square(self) -> None:
        """Test expand_to_square with already square image."""
        # Create mock square image
        mock_image = MagicMock()
        mock_image.size = (100, 100)

        result = DeQAInference.expand_to_square(mock_image, (128, 128, 128))
        assert result is mock_image  # Should return same image

    def test_expand_to_square_wide_image(self) -> None:
        """Test expand_to_square with wide image."""
        from PIL import Image as PILImage

        # Create actual wide image
        wide_image = PILImage.new("RGB", (200, 100), (255, 0, 0))
        result = DeQAInference.expand_to_square(wide_image, (128, 128, 128))
        assert result.size == (200, 200)

    def test_expand_to_square_tall_image(self) -> None:
        """Test expand_to_square with tall image."""
        from PIL import Image as PILImage

        tall_image = PILImage.new("RGB", (100, 200), (255, 0, 0))
        result = DeQAInference.expand_to_square(tall_image, (128, 128, 128))
        assert result.size == (200, 200)

    def test_extract_level_logits(self) -> None:
        """Test extraction of level logits from tensor."""
        torch = pytest.importorskip("torch")

        # Mock logits tensor (sequence_len, vocab_size)
        logits = torch.randn(10, 100)
        token_ids = [10, 20, 30, 40, 50]  # Fake token IDs for 5 levels

        result = DeQAInference.extract_level_logits(logits, token_ids, index=-1)

        assert len(result) == 5
        assert all(level in result for level in QUALITY_LEVELS)

    def test_generate_label_result(self) -> None:
        """Test label result generation."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)

        class TestInference(DeQAInference):
            def load_models(self, device: str | None = None) -> None:
                pass

            def unload_models(self) -> None:
                pass

            def predict(self, image: Any) -> dict[str, DeQAScore]:
                return {}

        engine = TestInference(config)
        scores = {
            "overall": DeQAScore(
                dimension=QualityDimension.OVERALL,
                score=4.0,
                probs={"good": 0.8},
            )
        }
        result = engine.generate_label_result("/test.jpg", "diqa-5000", scores)
        assert result.image_path == "/test.jpg"
        assert result.dataset == "diqa-5000"
        assert result.mode == "specialist"
        assert result.scores["overall"] == 4.0


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_initialization(self) -> None:
        """Test checkpoint manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            manager = CheckpointManager(output_path)
            assert manager.output_path == output_path.resolve()
            assert manager.checkpoint_interval == 500

    def test_path_traversal_prevention(self) -> None:
        """Test that path traversal is prevented."""
        with pytest.raises(ValueError, match="Path traversal"):
            CheckpointManager(Path("../../../etc/passwd"))

    def test_add_result_and_save(self) -> None:
        """Test adding results and saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            manager = CheckpointManager(output_path, checkpoint_interval=2)

            # Add results
            for i in range(3):
                result = LabelResult(
                    image_path=f"/image{i}.jpg",
                    dataset="test",
                    mode="specialist",
                    scores={"overall": 4.0},
                )
                manager.add_result(result)

            # Finalize
            manager.finalize()

            # Check file exists and has content
            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
            assert len(lines) == 3

    def test_is_processed(self) -> None:
        """Test processed check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            manager = CheckpointManager(output_path)

            result = LabelResult(
                image_path="/test.jpg",
                dataset="test",
                mode="vl",
                scores={},
            )
            manager.add_result(result)

            assert manager.is_processed("/test.jpg")
            assert not manager.is_processed("/other.jpg")

    def test_checkpoint_save_and_load(self) -> None:
        """Test checkpoint save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.jsonl"
            manager = CheckpointManager(output_path, checkpoint_interval=1)

            # Add a result (triggers checkpoint at interval=1)
            result = LabelResult(
                image_path="/test.jpg",
                dataset="test",
                mode="specialist",
                scores={"overall": 4.0},
            )
            manager.add_result(result)

            # Create new manager and load checkpoint
            manager2 = CheckpointManager(output_path)
            count = manager2.load_checkpoint()
            assert count == 1
            assert manager2.is_processed("/test.jpg")


class TestVQualAScore:
    """Tests for VQualAScore dataclass."""

    def test_final_score_calculation(self) -> None:
        """Test final score is calculated correctly."""
        score = VQualAScore(
            overall_srcc=0.9,
            sharpness_srcc=0.8,
            color_srcc=0.7,
        )
        # 0.5*0.9 + 0.25*0.8 + 0.25*0.7 = 0.45 + 0.2 + 0.175 = 0.825
        assert abs(score.final_score - 0.825) < 0.001

    def test_to_dict(self) -> None:
        """Test serialization."""
        score = VQualAScore(
            overall_srcc=0.85,
            sharpness_srcc=0.75,
            color_srcc=0.80,
        )
        data = score.to_dict()
        assert "final_score" in data
        assert data["overall_srcc"] == 0.85


class TestComparisonMetrics:
    """Tests for ComparisonMetrics dataclass."""

    def test_basic_creation(self) -> None:
        """Test metrics creation."""
        metrics = ComparisonMetrics(
            dimension="overall",
            srcc=0.9,
            plcc=0.85,
            rmse=0.3,
            mae=0.25,
            sample_size=1000,
        )
        assert metrics.srcc == 0.9
        assert metrics.sample_size == 1000

    def test_to_dict(self) -> None:
        """Test serialization."""
        metrics = ComparisonMetrics(
            dimension="sharpness",
            srcc=0.8,
            plcc=0.75,
            rmse=0.4,
            mae=0.3,
            sample_size=500,
            method_a="specialist",
            method_b="ensemble",
        )
        data = metrics.to_dict()
        assert data["dimension"] == "sharpness"
        assert data["method_a"] == "specialist"


class TestLabelAnalysis:
    """Tests for LabelAnalysis dataclass."""

    def test_basic_creation(self) -> None:
        """Test analysis creation."""
        analysis = LabelAnalysis(
            dataset="diqa-5000",
            mode="specialist",
            num_samples=5000,
        )
        assert analysis.dataset == "diqa-5000"
        assert analysis.num_samples == 5000

    def test_with_stats(self) -> None:
        """Test analysis with statistics."""
        analysis = LabelAnalysis(
            dataset="test",
            mode="ensemble",
            num_samples=100,
            dimension_stats={
                "overall": {"mean": 3.5, "std": 0.8},
            },
        )
        assert analysis.dimension_stats["overall"]["mean"] == 3.5

    def test_to_dict(self) -> None:
        """Test serialization."""
        analysis = LabelAnalysis(
            dataset="test",
            mode="vl",
            num_samples=50,
        )
        data = analysis.to_dict()
        assert data["num_samples"] == 50


class TestCreateInferenceEngine:
    """Tests for create_inference_engine factory function."""

    def test_create_specialist_engine(self) -> None:
        """Test creating specialist inference engine."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST)
        with patch(
            "image_preprocessing_detector.labeling.deqa.specialist.SpecialistInference"
        ) as mock:
            mock.return_value = MagicMock()
            engine = create_inference_engine(config)
            mock.assert_called_once_with(config)
            assert engine is mock.return_value

    def test_create_specialist_true_engine(self) -> None:
        """Test creating specialist_true inference engine."""
        config = DeQAConfig(mode=InferenceMode.SPECIALIST_TRUE)
        with patch(
            "image_preprocessing_detector.labeling.deqa.specialist.SpecialistInference"
        ) as mock:
            mock.return_value = MagicMock()
            engine = create_inference_engine(config)
            mock.assert_called_once_with(config)
            assert engine is mock.return_value

    def test_create_ensemble_engine(self) -> None:
        """Test creating ensemble inference engine."""
        config = DeQAConfig(mode=InferenceMode.ENSEMBLE)
        with patch(
            "image_preprocessing_detector.labeling.deqa.ensemble.EnsembleInference"
        ) as mock:
            mock.return_value = MagicMock()
            engine = create_inference_engine(config)
            mock.assert_called_once_with(config)
            assert engine is mock.return_value

    def test_create_ensemble_true_engine(self) -> None:
        """Test creating ensemble_true inference engine."""
        config = DeQAConfig(mode=InferenceMode.ENSEMBLE_TRUE)
        with patch(
            "image_preprocessing_detector.labeling.deqa.ensemble.EnsembleInference"
        ) as mock:
            mock.return_value = MagicMock()
            engine = create_inference_engine(config)
            mock.assert_called_once_with(config)
            assert engine is mock.return_value

    def test_create_vl_engine(self) -> None:
        """Test creating vl inference engine."""
        config = DeQAConfig(mode=InferenceMode.VL)
        with patch(
            "image_preprocessing_detector.labeling.deqa.vl_single.VLSingleInference"
        ) as mock:
            mock.return_value = MagicMock()
            engine = create_inference_engine(config)
            mock.assert_called_once_with(config)
            assert engine is mock.return_value
