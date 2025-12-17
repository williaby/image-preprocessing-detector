"""Tests for ModelSpec schema."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from image_preprocessing_detector.labeling.model_spec import (
    ModelSource,
    ModelSpec,
    ModelSpecRegistry,
    ModelVariant,
    RuntimeBackend,
)


class TestModelSpec:
    """Tests for ModelSpec dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic spec creation."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="meta-llama/Llama-4-Maverick",
            revision="main",
        )
        assert spec.source == ModelSource.HUGGINGFACE
        assert spec.id == "meta-llama/Llama-4-Maverick"
        assert spec.revision == "main"
        assert spec.variant == ModelVariant.BASE
        assert spec.runtime == RuntimeBackend.TRANSFORMERS

    def test_string_enum_conversion(self) -> None:
        """Test that string enums are converted."""
        spec = ModelSpec(
            source="huggingface",  # type: ignore[arg-type]
            id="test/model",
            revision="v1.0",
            variant="int8",  # type: ignore[arg-type]
            runtime="vllm",  # type: ignore[arg-type]
        )
        assert spec.source == ModelSource.HUGGINGFACE
        assert spec.variant == ModelVariant.INT8
        assert spec.runtime == RuntimeBackend.VLLM

    def test_auto_created_at(self) -> None:
        """Test automatic created_at timestamp."""
        spec = ModelSpec(
            source=ModelSource.LOCAL,
            id="/path/to/model",
            revision="abc123",
        )
        assert spec.created_at is not None
        assert "T" in spec.created_at

    def test_spec_id_property(self) -> None:
        """Test spec_id generation."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="org/model-name",
            revision="abc123def456",
            variant=ModelVariant.INT4,
        )
        spec_id = spec.spec_id
        assert "huggingface:org/model-name:int4:abc123de" in spec_id

    def test_is_quantized(self) -> None:
        """Test is_quantized property."""
        base_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            variant=ModelVariant.BASE,
        )
        assert not base_spec.is_quantized

        int8_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            variant=ModelVariant.INT8,
        )
        assert int8_spec.is_quantized

        int4_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            variant=ModelVariant.INT4,
        )
        assert int4_spec.is_quantized

    def test_is_finetuned(self) -> None:
        """Test is_finetuned property."""
        base_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        assert not base_spec.is_finetuned

        ft_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            variant=ModelVariant.FINETUNED,
        )
        assert ft_spec.is_finetuned

    def test_is_api_model(self) -> None:
        """Test is_api_model property."""
        hf_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        assert not hf_spec.is_api_model

        api_spec = ModelSpec(
            source=ModelSource.API,
            id="gpt-4",
            revision="2024-01",
        )
        assert api_spec.is_api_model

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            quant_method="unsloth",
            quant_params={"bits": 4},
        )
        d = spec.to_dict()

        assert d["source"] == "huggingface"
        assert d["id"] == "test/model"
        assert d["revision"] == "main"
        assert d["quant_method"] == "unsloth"
        assert d["quant_params"] == {"bits": 4}

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "source": "huggingface",
            "id": "test/model",
            "revision": "v1.0",
            "variant": "int8",
        }
        spec = ModelSpec.from_dict(data)

        assert spec.source == ModelSource.HUGGINGFACE
        assert spec.id == "test/model"
        assert spec.variant == ModelVariant.INT8

    def test_from_dict_missing_required_raises(self) -> None:
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="Missing required field"):
            ModelSpec.from_dict({"source": "huggingface", "id": "test"})

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
            variant=ModelVariant.INT8,
            quant_method="unsloth",
        )

        json_str = spec.to_json()
        loaded = ModelSpec.from_json(json_str)

        assert loaded.source == spec.source
        assert loaded.id == spec.id
        assert loaded.variant == spec.variant
        assert loaded.quant_method == spec.quant_method

    def test_json_file_roundtrip(self) -> None:
        """Test JSON file serialization roundtrip."""
        spec = ModelSpec(
            source=ModelSource.LOCAL,
            id="/path/to/model",
            revision="v1.0",
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            spec.to_json(path)
            loaded = ModelSpec.from_json(path)

            assert loaded.id == spec.id
            assert loaded.revision == spec.revision
        finally:
            path.unlink(missing_ok=True)

    def test_yaml_roundtrip(self) -> None:
        """Test YAML serialization roundtrip."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)

        try:
            spec.to_yaml(path)
            loaded = ModelSpec.from_yaml(path)

            assert loaded.id == spec.id
            assert loaded.source == spec.source
        finally:
            path.unlink(missing_ok=True)

    def test_compute_content_hash(self) -> None:
        """Test content hash is deterministic."""
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        hash1 = spec.compute_content_hash()
        hash2 = spec.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_derive_quantized(self) -> None:
        """Test deriving quantized spec."""
        base_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        int4_spec = base_spec.derive_quantized(bits=4)

        assert int4_spec.variant == ModelVariant.INT4
        assert int4_spec.quant_method == "unsloth"
        assert int4_spec.base_model_ref == base_spec.spec_id
        assert "int4" in int4_spec.id

    def test_derive_finetuned(self) -> None:
        """Test deriving fine-tuned spec."""
        base_spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        ft_spec = base_spec.derive_finetuned(
            lora_adapter_path="/path/to/adapter",
            new_revision="ft-v1",
        )

        assert ft_spec.variant == ModelVariant.FINETUNED
        assert ft_spec.lora_adapter_path == "/path/to/adapter"
        assert ft_spec.base_model_ref == base_spec.spec_id


class TestModelSpecRegistry:
    """Tests for ModelSpecRegistry."""

    def test_add_and_get(self) -> None:
        """Test adding and retrieving specs."""
        registry = ModelSpecRegistry()

        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        spec_id = registry.add(spec)

        retrieved = registry.get(spec_id)
        assert retrieved is not None
        assert retrieved.id == spec.id

    def test_get_nonexistent_returns_none(self) -> None:
        """Test that getting nonexistent spec returns None."""
        registry = ModelSpecRegistry()
        assert registry.get("nonexistent") is None

    def test_custom_spec_id(self) -> None:
        """Test using custom spec ID."""
        registry = ModelSpecRegistry()

        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model",
            revision="main",
        )
        registry.add(spec, spec_id="custom_id")

        retrieved = registry.get("custom_id")
        assert retrieved is not None

    def test_list_specs(self) -> None:
        """Test listing specs with filters."""
        registry = ModelSpecRegistry()

        spec1 = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model1",
            revision="main",
            variant=ModelVariant.BASE,
        )
        spec2 = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model2",
            revision="main",
            variant=ModelVariant.INT8,
        )
        spec3 = ModelSpec(
            source=ModelSource.LOCAL,
            id="/path/to/model",
            revision="v1",
            variant=ModelVariant.INT4,
        )

        registry.add(spec1)
        registry.add(spec2)
        registry.add(spec3)

        # List all
        all_specs = registry.list_specs()
        assert len(all_specs) == 3

        # Filter by source
        hf_specs = registry.list_specs(source=ModelSource.HUGGINGFACE)
        assert len(hf_specs) == 2

        # Filter by variant
        base_specs = registry.list_specs(variant=ModelVariant.BASE)
        assert len(base_specs) == 1

    def test_save_and_load(self) -> None:
        """Test saving and loading registry."""
        registry = ModelSpecRegistry()

        spec1 = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="test/model1",
            revision="main",
        )
        spec2 = ModelSpec(
            source=ModelSource.LOCAL,
            id="/path/to/model",
            revision="v1",
        )

        registry.add(spec1, "spec1")
        registry.add(spec2, "spec2")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)

        try:
            registry.save(path)

            loaded = ModelSpecRegistry.load(path)
            assert len(loaded.specs) == 2
            assert loaded.get("spec1") is not None
            assert loaded.get("spec2") is not None
        finally:
            path.unlink(missing_ok=True)


class TestModelSource:
    """Tests for ModelSource enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert ModelSource.HUGGINGFACE.value == "huggingface"
        assert ModelSource.LOCAL.value == "local"
        assert ModelSource.API.value == "api"


class TestModelVariant:
    """Tests for ModelVariant enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert ModelVariant.BASE.value == "base"
        assert ModelVariant.INT8.value == "int8"
        assert ModelVariant.INT4.value == "int4"
        assert ModelVariant.FINETUNED.value == "finetuned"
        assert ModelVariant.MIXED.value == "mixed"


class TestRuntimeBackend:
    """Tests for RuntimeBackend enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert RuntimeBackend.TRANSFORMERS.value == "transformers"
        assert RuntimeBackend.VLLM.value == "vllm"
        assert RuntimeBackend.ONNXRUNTIME.value == "onnxruntime"
        assert RuntimeBackend.API.value == "api"
        assert RuntimeBackend.UNSLOTH.value == "unsloth"
