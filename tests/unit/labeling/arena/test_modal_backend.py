"""Tests for Modal inference backend."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from image_preprocessing_detector.labeling.arena.inference.base import (
    InferenceConfig,
    ModelNotLoadedError,
)
from image_preprocessing_detector.labeling.arena.inference.modal import (
    DEFAULT_DIQA_PROMPT,
    ModalBackend,
)
from image_preprocessing_detector.labeling.model_spec import (
    ModelSource,
    ModelSpec,
    ModelVariant,
)


class TestModalBackend:
    """Tests for ModalBackend class."""

    @pytest.fixture
    def model_spec(self) -> ModelSpec:
        """Create a test model spec."""
        return ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
            variant=ModelVariant.INT4,  # 4-bit quantized model
            revision="main",
        )

    @pytest.fixture
    def inference_config(self) -> InferenceConfig:
        """Create a test inference config."""
        return InferenceConfig(
            batch_size=4,
            device="modal",
            seed=42,
        )

    def test_initialization(self) -> None:
        """Test backend initialization."""
        backend = ModalBackend()

        assert backend._client is None
        assert backend._spec is None
        assert backend._config is None
        assert backend._prompt == DEFAULT_DIQA_PROMPT

    def test_custom_prompt(self) -> None:
        """Test backend with custom prompt."""
        custom_prompt = "Custom quality prompt"
        backend = ModalBackend(custom_prompt=custom_prompt)

        assert backend._prompt == custom_prompt

    def test_load_initializes_client(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test load initializes the Modal client."""
        backend = ModalBackend()
        backend.load(model_spec, inference_config)

        assert backend._client is not None
        assert backend._spec == model_spec
        assert backend._config == inference_config
        assert backend.is_loaded() is True

    def test_unload_clears_state(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test unload clears all state."""
        backend = ModalBackend()
        backend.load(model_spec, inference_config)
        backend.unload()

        assert backend._client is None
        assert backend._spec is None
        assert backend._config is None
        assert backend.is_loaded() is False

    def test_predict_requires_load(self) -> None:
        """Test predict raises when not loaded."""
        backend = ModalBackend()
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

        with pytest.raises(ModelNotLoadedError):
            backend.predict(image)

    def test_predict_batch_requires_load(self) -> None:
        """Test predict_batch raises when not loaded."""
        backend = ModalBackend()
        images = [np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)]

        with pytest.raises(ModelNotLoadedError):
            backend.predict_batch(images)

    def test_get_provenance_requires_load(self) -> None:
        """Test get_provenance raises when not loaded."""
        backend = ModalBackend()

        with pytest.raises(ModelNotLoadedError):
            backend.get_provenance()

    def test_predict_with_mock_mode(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test predict returns predictions in mock mode."""
        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            backend = ModalBackend()
            backend.load(model_spec, inference_config)

            image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            prediction = backend.predict(image)

            assert prediction is not None
            assert 0.0 <= prediction.overall <= 1.0
            assert 0.0 <= prediction.sharpness <= 1.0
            assert 0.0 <= prediction.color <= 1.0

    def test_predict_batch_with_mock_mode(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test predict_batch returns predictions in mock mode."""
        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            backend = ModalBackend()
            backend.load(model_spec, inference_config)

            images = [
                np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
                for _ in range(3)
            ]
            predictions = backend.predict_batch(images)

            assert len(predictions) == 3
            for pred in predictions:
                assert pred is not None
                assert 0.0 <= pred.overall <= 1.0

    def test_parse_vlm_response_standard_format(self) -> None:
        """Test parsing standard VLM response format."""
        backend = ModalBackend()

        response_text = """Overall: 0.75
Sharpness: 0.82
Color: 0.68"""

        scores = backend._parse_vlm_response(response_text)

        assert scores["overall"] == pytest.approx(0.75, abs=0.01)
        assert scores["sharpness"] == pytest.approx(0.82, abs=0.01)
        assert scores["color"] == pytest.approx(0.68, abs=0.01)

    def test_parse_vlm_response_with_extra_text(self) -> None:
        """Test parsing VLM response with extra explanatory text."""
        backend = ModalBackend()

        response_text = """Based on my analysis, I rate this document as follows:

Overall: 0.65
Sharpness: 0.78
Color: 0.52

The document shows moderate quality with some artifacts."""

        scores = backend._parse_vlm_response(response_text)

        assert scores["overall"] == pytest.approx(0.65, abs=0.01)
        assert scores["sharpness"] == pytest.approx(0.78, abs=0.01)
        assert scores["color"] == pytest.approx(0.52, abs=0.01)

    def test_parse_vlm_response_missing_values(self) -> None:
        """Test parsing VLM response with missing values uses defaults."""
        backend = ModalBackend()

        response_text = """Overall: 0.75"""

        scores = backend._parse_vlm_response(response_text)

        assert scores["overall"] == pytest.approx(0.75, abs=0.01)
        assert scores["sharpness"] == 0.5  # Default
        assert scores["color"] == 0.5  # Default

    def test_parse_vlm_response_clamps_values(self) -> None:
        """Test parsing VLM response clamps values to [0, 1]."""
        backend = ModalBackend()

        response_text = """Overall: 1.5
Sharpness: -0.2
Color: 0.8"""

        scores = backend._parse_vlm_response(response_text)

        assert scores["overall"] == 1.0  # Clamped
        assert scores["sharpness"] == 0.0  # Clamped
        assert scores["color"] == pytest.approx(0.8, abs=0.01)

    def test_parse_vlm_response_case_insensitive(self) -> None:
        """Test parsing VLM response is case-insensitive."""
        backend = ModalBackend()

        response_text = """OVERALL: 0.75
sharpness: 0.82
CoLoR: 0.68"""

        scores = backend._parse_vlm_response(response_text)

        assert scores["overall"] == pytest.approx(0.75, abs=0.01)
        assert scores["sharpness"] == pytest.approx(0.82, abs=0.01)
        assert scores["color"] == pytest.approx(0.68, abs=0.01)

    def test_get_model_info(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test get_model_info returns expected fields."""
        backend = ModalBackend()
        backend.load(model_spec, inference_config)

        info = backend.get_model_info()

        assert info["model_id"] == model_spec.id
        assert info["revision"] == model_spec.revision
        assert info["backend"] == "modal"
        assert "modal_stats" in info

    def test_get_provenance(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test get_provenance returns ProvenanceInfo."""
        backend = ModalBackend()
        backend.load(model_spec, inference_config)

        provenance = backend.get_provenance()

        assert provenance.model_checksum.startswith("modal-model:")
        assert provenance.config_hash.startswith("config:")

    def test_is_available(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test is_available returns client availability."""
        backend = ModalBackend()

        # Not loaded
        assert backend.is_available() is False

        # Load backend
        backend.load(model_spec, inference_config)
        assert backend.is_available() is True

    def test_accepts_pil_images(
        self, model_spec: ModelSpec, inference_config: InferenceConfig
    ) -> None:
        """Test backend accepts PIL Image input."""
        from PIL import Image as PILImage

        with patch.dict(os.environ, {"ARENA_MODAL_MOCK": "true"}):
            backend = ModalBackend()
            backend.load(model_spec, inference_config)

            # Create PIL Image
            pil_image = PILImage.new("RGB", (224, 224), color="red")
            prediction = backend.predict(pil_image)

            assert prediction is not None
            assert 0.0 <= prediction.overall <= 1.0


class TestCreateBackendModal:
    """Tests for create_backend with modal source."""

    def test_create_modal_backend(self) -> None:
        """Test create_backend creates ModalBackend."""
        from image_preprocessing_detector.labeling.arena.inference.base import (
            create_backend,
        )

        backend = create_backend("modal")

        assert isinstance(backend, ModalBackend)

    def test_create_backend_invalid_source(self) -> None:
        """Test create_backend raises for invalid source."""
        from image_preprocessing_detector.labeling.arena.inference.base import (
            create_backend,
        )

        with pytest.raises(ValueError, match="Unknown backend source"):
            create_backend("invalid")
