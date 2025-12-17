"""Shared ModelSpec schema for cross-project compatibility.

This module defines the unified model specification used across all three
labeling workstreams:

- Project A: Benchmarking Arena
- Project B: Unsloth Quantization
- Project C: Fine-Tuning

The ModelSpec enables plug-and-play model swapping with complete provenance
tracking for reproducibility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ModelSource(str, Enum):
    """Source location for model artifacts."""

    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    API = "api"


class ModelVariant(str, Enum):
    """Model variant type."""

    BASE = "base"
    INT8 = "int8"
    INT4 = "int4"
    FINETUNED = "finetuned"
    MIXED = "mixed"  # Mixed precision quantization


class RuntimeBackend(str, Enum):
    """Inference runtime backend."""

    TRANSFORMERS = "transformers"
    VLLM = "vllm"
    ONNXRUNTIME = "onnxruntime"
    API = "api"
    UNSLOTH = "unsloth"
    TENSORRT = "tensorrt"


@dataclass
class ModelSpec:
    """Unified model specification for all labeling workstreams.

    This schema enables plug-and-play model swapping across:
    - Project A (Benchmarking Arena)
    - Project B (Unsloth Quantization)
    - Project C (Fine-Tuning)

    Attributes:
        source: Where the model comes from (huggingface, local, api)
        id: Model identifier (HF repo, local path, or API model name)
        revision: Version identifier (commit hash, tag, or build ID)
        variant: Type of model variant (base, int8, int4, finetuned)
        runtime: Inference backend to use
        checksum: SHA256 hash of model weights for verification
        config_hash: Hash of model configuration
        tokenizer_hash: Hash of tokenizer files
        api_version: Version string for API models
        api_params: Parameters for API calls (temperature, max_tokens, etc.)
        quant_method: Quantization method used (unsloth, bitsandbytes, etc.)
        quant_params: Quantization parameters (bits, group_size, etc.)
        lora_adapter_path: Path to LoRA adapter weights
        base_model_ref: Reference to base model this was derived from
        notes: Additional notes or metadata

    Example:
        >>> spec = ModelSpec(
        ...     source=ModelSource.HUGGINGFACE,
        ...     id="meta-llama/Llama-4-Maverick",
        ...     revision="main",
        ...     variant=ModelVariant.BASE,
        ...     runtime=RuntimeBackend.TRANSFORMERS,
        ... )
        >>> spec.to_dict()
        {'source': 'huggingface', 'id': 'meta-llama/Llama-4-Maverick', ...}
    """

    source: ModelSource
    id: str  # HF repo, local path, or API model name
    revision: str  # Commit hash, tag, or build ID
    variant: ModelVariant = ModelVariant.BASE
    runtime: RuntimeBackend = RuntimeBackend.TRANSFORMERS

    # Provenance tracking (mandatory for reproducibility)
    checksum: str | None = None  # SHA256 of model weights
    config_hash: str | None = None  # Hash of model config
    tokenizer_hash: str | None = None  # Hash of tokenizer

    # API-specific fields
    api_version: str | None = None
    api_params: dict[str, Any] | None = None

    # Quantization metadata (Project B)
    quant_method: str | None = None  # e.g., "unsloth", "bitsandbytes"
    quant_params: dict[str, Any] | None = None  # e.g., {"bits": 4, "group_size": 128}

    # Fine-tuning metadata (Project C)
    lora_adapter_path: str | None = None
    base_model_ref: str | None = None  # Reference to base model spec ID

    # Additional metadata
    notes: str | None = None
    created_at: str | None = None
    created_by: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize fields after initialization."""
        # Convert string enums if needed
        if isinstance(self.source, str):
            self.source = ModelSource(self.source)
        if isinstance(self.variant, str):
            self.variant = ModelVariant(self.variant)
        if isinstance(self.runtime, str):
            self.runtime = RuntimeBackend(self.runtime)

        # Set created_at if not provided
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def spec_id(self) -> str:
        """Generate a unique identifier for this spec.

        Format: {source}:{id}:{variant}:{revision_short}
        """
        revision_short = self.revision[:8] if len(self.revision) > 8 else self.revision
        return f"{self.source.value}:{self.id}:{self.variant.value}:{revision_short}"

    @property
    def is_quantized(self) -> bool:
        """Check if this is a quantized model."""
        return self.variant in (ModelVariant.INT4, ModelVariant.INT8, ModelVariant.MIXED)

    @property
    def is_finetuned(self) -> bool:
        """Check if this is a fine-tuned model."""
        return self.variant == ModelVariant.FINETUNED

    @property
    def is_api_model(self) -> bool:
        """Check if this is an API-based model."""
        return self.source == ModelSource.API

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON/YAML storage.

        Returns:
            Dictionary representation of the ModelSpec.
        """
        return {
            "source": self.source.value,
            "id": self.id,
            "revision": self.revision,
            "variant": self.variant.value,
            "runtime": self.runtime.value,
            "checksum": self.checksum,
            "config_hash": self.config_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "api_version": self.api_version,
            "api_params": self.api_params,
            "quant_method": self.quant_method,
            "quant_params": self.quant_params,
            "lora_adapter_path": self.lora_adapter_path,
            "base_model_ref": self.base_model_ref,
            "notes": self.notes,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelSpec:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation of a ModelSpec.

        Returns:
            ModelSpec instance.

        Raises:
            ValueError: If required fields are missing.
        """
        required_fields = ["source", "id", "revision"]
        for field_name in required_fields:
            if field_name not in data:
                msg = f"Missing required field: {field_name}"
                raise ValueError(msg)

        return cls(
            source=ModelSource(data["source"]),
            id=data["id"],
            revision=data["revision"],
            variant=ModelVariant(data.get("variant", "base")),
            runtime=RuntimeBackend(data.get("runtime", "transformers")),
            checksum=data.get("checksum"),
            config_hash=data.get("config_hash"),
            tokenizer_hash=data.get("tokenizer_hash"),
            api_version=data.get("api_version"),
            api_params=data.get("api_params"),
            quant_method=data.get("quant_method"),
            quant_params=data.get("quant_params"),
            lora_adapter_path=data.get("lora_adapter_path"),
            base_model_ref=data.get("base_model_ref"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            created_by=data.get("created_by"),
        )

    def to_json(self, path: Path | str | None = None, indent: int = 2) -> str:
        """Serialize to JSON string or file.

        Args:
            path: Optional path to write JSON file.
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        json_str = json.dumps(self.to_dict(), indent=indent, default=str)

        if path is not None:
            Path(path).write_text(json_str, encoding="utf-8")

        return json_str

    @classmethod
    def from_json(cls, source: Path | str) -> ModelSpec:
        """Load from JSON file or string.

        Args:
            source: Path to JSON file or JSON string.

        Returns:
            ModelSpec instance.
        """
        path = Path(source)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            # Assume it's a JSON string
            data = json.loads(source)  # type: ignore[arg-type]

        return cls.from_dict(data)

    def to_yaml(self, path: Path | str | None = None) -> str:
        """Serialize to YAML string or file.

        Args:
            path: Optional path to write YAML file.

        Returns:
            YAML string representation.
        """
        yaml_str = yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

        if path is not None:
            Path(path).write_text(yaml_str, encoding="utf-8")

        return yaml_str

    @classmethod
    def from_yaml(cls, source: Path | str) -> ModelSpec:
        """Load from YAML file or string.

        Args:
            source: Path to YAML file or YAML string.

        Returns:
            ModelSpec instance.
        """
        path = Path(source)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            # Assume it's a YAML string
            data = yaml.safe_load(source)  # type: ignore[arg-type]

        return cls.from_dict(data)

    def compute_content_hash(self) -> str:
        """Compute a hash of the spec content for comparison.

        Returns:
            SHA256 hash of the spec's core content.
        """
        # Include only fields that affect model behavior
        content = {
            "source": self.source.value,
            "id": self.id,
            "revision": self.revision,
            "variant": self.variant.value,
            "runtime": self.runtime.value,
            "quant_method": self.quant_method,
            "quant_params": self.quant_params,
            "lora_adapter_path": self.lora_adapter_path,
            "base_model_ref": self.base_model_ref,
        }
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def derive_quantized(
        self,
        bits: int,
        quant_method: str = "unsloth",
        quant_params: dict[str, Any] | None = None,
        new_revision: str | None = None,
        new_id: str | None = None,
    ) -> ModelSpec:
        """Create a new ModelSpec for a quantized version of this model.

        Args:
            bits: Quantization bits (4 or 8).
            quant_method: Quantization method used.
            quant_params: Additional quantization parameters.
            new_revision: New revision string for the quantized model.
            new_id: New model ID (defaults to original with suffix).

        Returns:
            New ModelSpec for the quantized variant.
        """
        variant = ModelVariant.INT4 if bits == 4 else ModelVariant.INT8

        return ModelSpec(
            source=self.source,
            id=new_id or f"{self.id}-int{bits}",
            revision=new_revision or f"{self.revision}-int{bits}",
            variant=variant,
            runtime=RuntimeBackend.UNSLOTH,
            quant_method=quant_method,
            quant_params=quant_params or {"bits": bits},
            base_model_ref=self.spec_id,
            notes=f"Quantized from {self.spec_id} using {quant_method}",
        )

    def derive_finetuned(
        self,
        lora_adapter_path: str,
        new_revision: str,
        new_id: str | None = None,
    ) -> ModelSpec:
        """Create a new ModelSpec for a fine-tuned version of this model.

        Args:
            lora_adapter_path: Path to LoRA adapter weights.
            new_revision: New revision string for the fine-tuned model.
            new_id: New model ID (defaults to original with suffix).

        Returns:
            New ModelSpec for the fine-tuned variant.
        """
        return ModelSpec(
            source=self.source,
            id=new_id or f"{self.id}-finetuned",
            revision=new_revision,
            variant=ModelVariant.FINETUNED,
            runtime=self.runtime,
            lora_adapter_path=lora_adapter_path,
            base_model_ref=self.spec_id,
            notes=f"Fine-tuned from {self.spec_id}",
        )


@dataclass
class ModelSpecRegistry:
    """Registry for managing multiple ModelSpecs.

    Provides methods for loading, storing, and querying model specifications.
    """

    specs: dict[str, ModelSpec] = field(default_factory=dict)
    registry_path: Path | None = None

    def add(self, spec: ModelSpec, spec_id: str | None = None) -> str:
        """Add a ModelSpec to the registry.

        Args:
            spec: ModelSpec to add.
            spec_id: Optional custom ID (defaults to spec.spec_id).

        Returns:
            The ID used to store the spec.
        """
        key = spec_id or spec.spec_id
        self.specs[key] = spec
        return key

    def get(self, spec_id: str) -> ModelSpec | None:
        """Get a ModelSpec by ID.

        Args:
            spec_id: The spec identifier.

        Returns:
            ModelSpec if found, None otherwise.
        """
        return self.specs.get(spec_id)

    def list_specs(
        self,
        source: ModelSource | None = None,
        variant: ModelVariant | None = None,
    ) -> list[str]:
        """List spec IDs, optionally filtered.

        Args:
            source: Filter by source type.
            variant: Filter by variant type.

        Returns:
            List of matching spec IDs.
        """
        results = []
        for spec_id, spec in self.specs.items():
            if source is not None and spec.source != source:
                continue
            if variant is not None and spec.variant != variant:
                continue
            results.append(spec_id)
        return results

    def save(self, path: Path | str | None = None) -> None:
        """Save registry to YAML file.

        Args:
            path: Path to save to (uses registry_path if not provided).
        """
        save_path = Path(path) if path else self.registry_path
        if save_path is None:
            msg = "No path provided and registry_path not set"
            raise ValueError(msg)

        data = {"specs": {k: v.to_dict() for k, v in self.specs.items()}}
        save_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path | str) -> ModelSpecRegistry:
        """Load registry from YAML file.

        Args:
            path: Path to load from.

        Returns:
            ModelSpecRegistry instance.
        """
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        registry = cls(registry_path=path)
        for spec_id, spec_data in data.get("specs", {}).items():
            registry.specs[spec_id] = ModelSpec.from_dict(spec_data)

        return registry
