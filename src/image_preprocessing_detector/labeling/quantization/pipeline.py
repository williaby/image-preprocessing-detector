# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Quantization pipeline for Project B.

This module provides the main quantization orchestration for converting
full-precision models to INT8/INT4 variants.

Supported Backends:
    - bitsandbytes: NVIDIA GPU quantization (llm.int8, nf4)
    - auto-gptq: GPTQ quantization
    - autoawq: AWQ quantization
    - gguf: llama.cpp compatible format

Pipeline Flow:
    ModelSpec → Load Model → Select Recipe → Quantize → Package → Export
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from image_preprocessing_detector.labeling.model_spec import ModelSpec

logger = structlog.get_logger(__name__)


class QuantizationBackend(Enum):
    """Supported quantization backends."""

    BITSANDBYTES = "bitsandbytes"
    GPTQ = "gptq"
    AWQ = "awq"
    GGUF = "gguf"


class QuantizationType(Enum):
    """Quantization precision types."""

    INT8 = "int8"
    INT4 = "int4"
    NF4 = "nf4"  # Normal float 4-bit (bitsandbytes)
    FP4 = "fp4"  # Float 4-bit


@dataclass
class QuantizationConfig:
    """Configuration for quantization.

    Attributes:
        bits: Target bit precision (8 or 4)
        backend: Quantization backend to use
        quant_type: Specific quantization type
        group_size: Group size for quantization (GPTQ/AWQ)
        use_double_quant: Enable double quantization (bitsandbytes)
        compute_dtype: Compute dtype for quantized operations
        calibration_samples: Number of samples for calibration (GPTQ/AWQ)
        block_size: Block size for calibration
        trust_remote_code: Trust remote code from HuggingFace
    """

    bits: int = 4
    backend: QuantizationBackend = QuantizationBackend.BITSANDBYTES
    quant_type: QuantizationType = QuantizationType.NF4
    group_size: int = 128
    use_double_quant: bool = True
    compute_dtype: str = "float16"
    calibration_samples: int = 128
    block_size: int = 128
    trust_remote_code: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "bits": self.bits,
            "backend": self.backend.value,
            "quant_type": self.quant_type.value,
            "group_size": self.group_size,
            "use_double_quant": self.use_double_quant,
            "compute_dtype": self.compute_dtype,
            "calibration_samples": self.calibration_samples,
            "block_size": self.block_size,
            "trust_remote_code": self.trust_remote_code,
        }


@dataclass
class QuantizationResult:
    """Result of quantization operation.

    Attributes:
        success: Whether quantization succeeded
        output_path: Path to quantized model
        original_size_mb: Original model size in MB
        quantized_size_mb: Quantized model size in MB
        compression_ratio: Compression ratio achieved
        config: Quantization configuration used
        checksum: SHA256 checksum of output
        error: Error message if failed
        metadata: Additional metadata
    """

    success: bool
    output_path: str = ""
    original_size_mb: float = 0.0
    quantized_size_mb: float = 0.0
    compression_ratio: float = 0.0
    config: QuantizationConfig | None = None
    checksum: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output_path": self.output_path,
            "original_size_mb": self.original_size_mb,
            "quantized_size_mb": self.quantized_size_mb,
            "compression_ratio": self.compression_ratio,
            "config": self.config.to_dict() if self.config else None,
            "checksum": self.checksum,
            "error": self.error,
            "metadata": self.metadata,
        }


class QuantizationPipeline:
    """Main quantization pipeline for Project B.

    Orchestrates the quantization process from model loading through
    artifact packaging.

    Example:
        >>> from image_preprocessing_detector.labeling import ModelSpec, ModelSource
        >>> spec = ModelSpec(
        ...     source=ModelSource.HUGGINGFACE,
        ...     id="HuggingFaceTB/SmolVLM-256M-Instruct",
        ...     revision="main",
        ... )
        >>> pipeline = QuantizationPipeline()
        >>> result = pipeline.quantize(spec, bits=4, output_dir="./artifacts")
        >>> print(f"Compression: {result.compression_ratio:.1f}x")
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        device: str = "auto",
    ) -> None:
        """Initialize the pipeline.

        Args:
            cache_dir: Directory for caching models.
            device: Device for quantization ("auto", "cuda", "cpu").
        """
        self.cache_dir = (
            Path(cache_dir) if cache_dir else Path.home() / ".cache" / "diqa_quant"
        )
        self.device = device

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "quantization_pipeline_initialized",
            cache_dir=str(self.cache_dir),
            device=device,
        )

    def quantize(
        self,
        spec: ModelSpec,
        bits: int = 4,
        output_dir: str | Path = "./quantized",
        config: QuantizationConfig | None = None,
    ) -> QuantizationResult:
        """Quantize a model to the specified precision.

        Args:
            spec: Model specification.
            bits: Target bit precision (4 or 8).
            output_dir: Output directory for quantized model.
            config: Quantization configuration (optional).

        Returns:
            QuantizationResult with status and paths.
        """
        # Create default config if not provided
        if config is None:
            config = self._create_default_config(bits)

        logger.info(
            "quantization_started",
            model_id=spec.id,
            bits=bits,
            backend=config.backend.value,
        )

        try:
            # Select backend handler
            if config.backend == QuantizationBackend.BITSANDBYTES:
                result = self._quantize_bitsandbytes(spec, config, output_dir)
            elif config.backend == QuantizationBackend.GPTQ:
                result = self._quantize_gptq(spec, config, output_dir)
            elif config.backend == QuantizationBackend.AWQ:
                result = self._quantize_awq(spec, config, output_dir)
            elif config.backend == QuantizationBackend.GGUF:
                result = self._quantize_gguf(spec, config, output_dir)
            else:
                msg = f"Unsupported backend: {config.backend}"
                raise ValueError(msg)  # noqa: TRY301

            # Package the result
            if result.success:
                self._package_artifact(result, spec, config)

            logger.info(
                "quantization_complete",
                model_id=spec.id,
                success=result.success,
                compression=f"{result.compression_ratio:.1f}x",
            )

            return result  # noqa: TRY300

        except Exception as e:
            logger.exception("quantization_failed", model_id=spec.id, error=str(e))
            return QuantizationResult(
                success=False,
                error=str(e),
                config=config,
            )

    def _create_default_config(self, bits: int) -> QuantizationConfig:
        """Create default configuration for given bit precision."""
        if bits == 8:
            return QuantizationConfig(
                bits=8,
                backend=QuantizationBackend.BITSANDBYTES,
                quant_type=QuantizationType.INT8,
                use_double_quant=False,
            )
        # 4-bit default
        return QuantizationConfig(
            bits=4,
            backend=QuantizationBackend.BITSANDBYTES,
            quant_type=QuantizationType.NF4,
            use_double_quant=True,
        )

    def _quantize_bitsandbytes(
        self,
        spec: ModelSpec,
        config: QuantizationConfig,
        output_dir: str | Path,
    ) -> QuantizationResult:
        """Quantize using bitsandbytes backend.

        Args:
            spec: Model specification.
            config: Quantization configuration.
            output_dir: Output directory.

        Returns:
            QuantizationResult.
        """
        import torch
        from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get original model size
        original_size = self._estimate_model_size(spec.id)

        # Configure quantization
        if config.bits == 4:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=getattr(torch, config.compute_dtype),
                bnb_4bit_use_double_quant=config.use_double_quant,
                bnb_4bit_quant_type=config.quant_type.value,
            )
        else:
            bnb_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )

        # Load and quantize model
        logger.info("loading_model_for_quantization", model_id=spec.id)

        model = AutoModel.from_pretrained(
            spec.id,
            quantization_config=bnb_config,
            device_map="auto" if self.device == "auto" else self.device,
            trust_remote_code=config.trust_remote_code,
        )

        # Save quantized model
        model_output = output_path / "model"
        model.save_pretrained(str(model_output))

        # Save tokenizer if available
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                spec.id,
                trust_remote_code=config.trust_remote_code,
            )
            tokenizer.save_pretrained(str(model_output))
        except Exception as e:
            logger.warning("tokenizer_save_failed", error=str(e))

        # Calculate sizes
        quantized_size = self._calculate_directory_size(model_output)
        compression_ratio = original_size / quantized_size if quantized_size > 0 else 0

        # Compute checksum
        checksum = self._compute_checksum(model_output)

        return QuantizationResult(
            success=True,
            output_path=str(model_output),
            original_size_mb=original_size,
            quantized_size_mb=quantized_size,
            compression_ratio=compression_ratio,
            config=config,
            checksum=checksum,
            metadata={
                "quantization_backend": "bitsandbytes",
                "device": self.device,
            },
        )

    def _quantize_gptq(
        self,
        spec: ModelSpec,
        config: QuantizationConfig,
        output_dir: str | Path,
    ) -> QuantizationResult:
        """Quantize using GPTQ backend.

        Args:
            spec: Model specification.
            config: Quantization configuration.
            output_dir: Output directory.

        Returns:
            QuantizationResult.
        """
        try:
            from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
            from transformers import AutoTokenizer
        except ImportError:
            return QuantizationResult(
                success=False,
                error="auto-gptq not installed. Run: pip install auto-gptq",
                config=config,
            )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get original model size
        original_size = self._estimate_model_size(spec.id)

        # Configure GPTQ
        gptq_config = BaseQuantizeConfig(
            bits=config.bits,
            group_size=config.group_size,
            desc_act=True,
        )

        # Load tokenizer for calibration
        tokenizer = AutoTokenizer.from_pretrained(
            spec.id,
            trust_remote_code=config.trust_remote_code,
        )

        # Load model
        logger.info("loading_model_for_gptq", model_id=spec.id)
        model = AutoGPTQForCausalLM.from_pretrained(
            spec.id,
            quantize_config=gptq_config,
            trust_remote_code=config.trust_remote_code,
        )

        # Generate calibration data
        calibration_data = self._generate_calibration_data(
            tokenizer,
            num_samples=config.calibration_samples,
        )

        # Quantize
        logger.info("running_gptq_quantization", num_calibration=len(calibration_data))
        model.quantize(calibration_data)

        # Save
        model_output = output_path / "model"
        model.save_quantized(str(model_output))
        tokenizer.save_pretrained(str(model_output))

        # Calculate sizes
        quantized_size = self._calculate_directory_size(model_output)
        compression_ratio = original_size / quantized_size if quantized_size > 0 else 0

        checksum = self._compute_checksum(model_output)

        return QuantizationResult(
            success=True,
            output_path=str(model_output),
            original_size_mb=original_size,
            quantized_size_mb=quantized_size,
            compression_ratio=compression_ratio,
            config=config,
            checksum=checksum,
            metadata={
                "quantization_backend": "gptq",
                "calibration_samples": config.calibration_samples,
            },
        )

    def _quantize_awq(
        self,
        spec: ModelSpec,
        config: QuantizationConfig,
        output_dir: str | Path,
    ) -> QuantizationResult:
        """Quantize using AWQ backend.

        Args:
            spec: Model specification.
            config: Quantization configuration.
            output_dir: Output directory.

        Returns:
            QuantizationResult.
        """
        try:
            from awq import AutoAWQForCausalLM
            from transformers import AutoTokenizer
        except ImportError:
            return QuantizationResult(
                success=False,
                error="autoawq not installed. Run: pip install autoawq",
                config=config,
            )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        original_size = self._estimate_model_size(spec.id)

        # Configure AWQ
        awq_config = {
            "w_bit": config.bits,
            "q_group_size": config.group_size,
            "zero_point": True,
            "version": "GEMM",
        }

        # Load model
        logger.info("loading_model_for_awq", model_id=spec.id)
        model = AutoAWQForCausalLM.from_pretrained(
            spec.id,
            trust_remote_code=config.trust_remote_code,
        )

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            spec.id,
            trust_remote_code=config.trust_remote_code,
        )

        # Quantize
        logger.info("running_awq_quantization")
        model.quantize(tokenizer, quant_config=awq_config)

        # Save
        model_output = output_path / "model"
        model.save_quantized(str(model_output))
        tokenizer.save_pretrained(str(model_output))

        quantized_size = self._calculate_directory_size(model_output)
        compression_ratio = original_size / quantized_size if quantized_size > 0 else 0

        checksum = self._compute_checksum(model_output)

        return QuantizationResult(
            success=True,
            output_path=str(model_output),
            original_size_mb=original_size,
            quantized_size_mb=quantized_size,
            compression_ratio=compression_ratio,
            config=config,
            checksum=checksum,
            metadata={
                "quantization_backend": "awq",
            },
        )

    def _quantize_gguf(
        self,
        _spec: ModelSpec,
        config: QuantizationConfig,
        _output_dir: str | Path,
    ) -> QuantizationResult:
        """Quantize to GGUF format for llama.cpp.

        Args:
            spec: Model specification.
            config: Quantization configuration.
            output_dir: Output directory.

        Returns:
            QuantizationResult.
        """
        # GGUF conversion requires llama.cpp tools
        # This is a placeholder that would call convert.py and quantize tools
        return QuantizationResult(
            success=False,
            error="GGUF quantization requires llama.cpp tools. Use llama.cpp convert.py directly.",
            config=config,
        )

    def _generate_calibration_data(
        self,
        _tokenizer: Any,
        num_samples: int = 128,
    ) -> list[str]:
        """Generate calibration data for GPTQ/AWQ.

        Uses a simple dataset of common text patterns for calibration.
        """
        # Simple calibration prompts
        base_prompts = [
            "The quick brown fox jumps over the lazy dog.",
            "In a galaxy far, far away, there was a brave hero.",
            "Machine learning is transforming how we build software.",
            "The document quality is measured by several factors.",
            "Image processing involves multiple computational steps.",
            "Natural language understanding requires deep learning.",
            "The weather today is sunny with clear skies.",
            "Data science combines statistics and programming.",
        ]

        # Expand to required number of samples
        calibration_data = []
        for i in range(num_samples):
            prompt = base_prompts[i % len(base_prompts)]
            # Add variation
            if i > len(base_prompts):
                prompt = f"Sample {i}: {prompt}"
            calibration_data.append(prompt)

        return calibration_data

    def _estimate_model_size(self, model_id: str) -> float:
        """Estimate model size in MB from HuggingFace."""
        try:
            from huggingface_hub import model_info

            info = model_info(model_id)
            # Convert safetensors/bin sizes to MB
            total_bytes = sum(
                s.size
                for s in (info.siblings or [])
                if s.rfilename.endswith((".safetensors", ".bin"))
            )
            return total_bytes / (1024 * 1024)
        except Exception:
            return 0.0

    def _calculate_directory_size(self, path: Path) -> float:
        """Calculate total size of directory in MB."""
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)

    def _compute_checksum(self, path: Path) -> str:
        """Compute SHA256 checksum of model files."""
        hasher = hashlib.sha256()

        # Hash all model files
        for f in sorted(path.rglob("*.safetensors")):
            with open(f, "rb") as file:
                for chunk in iter(lambda: file.read(8192), b""):
                    hasher.update(chunk)

        # Also check .bin files
        for f in sorted(path.rglob("*.bin")):
            with open(f, "rb") as file:
                for chunk in iter(lambda: file.read(8192), b""):
                    hasher.update(chunk)

        return hasher.hexdigest()[:16]

    def _package_artifact(
        self,
        result: QuantizationResult,
        spec: ModelSpec,
        config: QuantizationConfig,
    ) -> None:
        """Package quantized model with metadata."""
        if not result.output_path:
            return

        output_path = Path(result.output_path)

        # Create artifact metadata
        metadata = {
            "artifact_type": "quantized_model",
            "created_at": datetime.now(UTC).isoformat(),
            "source_model": {
                "id": spec.id,
                "revision": spec.revision,
                "source": spec.source.value,
            },
            "quantization": config.to_dict(),
            "result": {
                "original_size_mb": result.original_size_mb,
                "quantized_size_mb": result.quantized_size_mb,
                "compression_ratio": result.compression_ratio,
                "checksum": result.checksum,
            },
            "arena_spec": {
                "source": "local",
                "id": f"{spec.id.split('/')[-1]}-{config.bits}bit",
                "variant": "int8" if config.bits == 8 else "int4",
                "path": str(output_path),
                "revision": result.checksum[:8],
            },
        }

        # Write metadata
        metadata_path = output_path / "quantization_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("artifact_packaged", path=str(output_path))
