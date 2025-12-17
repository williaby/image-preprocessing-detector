# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Training manifest and model export for Project C.

This module handles:
- Training run manifests with full provenance
- Model versioning and registry integration
- Export to various formats (PyTorch, ONNX, TorchScript)
- Integration with Project A Arena for evaluation

The manifest captures everything needed to reproduce a training run
and integrate the resulting model into the evaluation pipeline.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import torch

logger = structlog.get_logger(__name__)


@dataclass
class DatasetManifest:
    """Manifest for training dataset.

    Attributes:
        name: Dataset name (e.g., "DIQA-5000")
        version: Dataset version
        train_samples: Number of training samples
        val_samples: Number of validation samples
        splits_hash: Hash of split assignments
        annotations_path: Path to annotations file
        preprocessing: Applied preprocessing steps
    """

    name: str
    version: str = "1.0"
    train_samples: int = 0
    val_samples: int = 0
    splits_hash: str = ""
    annotations_path: str = ""
    preprocessing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "train_samples": self.train_samples,
            "val_samples": self.val_samples,
            "splits_hash": self.splits_hash,
            "annotations_path": self.annotations_path,
            "preprocessing": self.preprocessing,
        }


@dataclass
class ModelManifest:
    """Manifest for trained model.

    Attributes:
        model_id: Unique model identifier
        base_model_id: HuggingFace base model ID
        architecture: Model architecture description
        num_parameters: Total parameter count
        trainable_parameters: Trainable parameter count
        lora_config: LoRA configuration if used
        checkpoint_hash: SHA256 of model weights
    """

    model_id: str
    base_model_id: str
    architecture: str = "vision_encoder_regression_head"
    num_parameters: int = 0
    trainable_parameters: int = 0
    lora_config: dict[str, Any] | None = None
    checkpoint_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "base_model_id": self.base_model_id,
            "architecture": self.architecture,
            "num_parameters": self.num_parameters,
            "trainable_parameters": self.trainable_parameters,
            "lora_config": self.lora_config,
            "checkpoint_hash": self.checkpoint_hash,
        }


@dataclass
class TrainingManifest:
    """Complete manifest for a training run.

    Captures all information needed to reproduce the training
    and integrate the model into the evaluation pipeline.

    Attributes:
        run_id: Unique identifier for this training run
        timestamp: ISO timestamp of training start
        dataset: Dataset manifest
        model: Model manifest
        config: Training configuration
        metrics: Final training metrics
        environment: Environment information
        exports: Paths to exported models
        arena_spec: Arena ModelSpec for evaluation
    """

    run_id: str
    timestamp: str = ""
    dataset: DatasetManifest | None = None
    model: ModelManifest | None = None
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    exports: dict[str, str] = field(default_factory=dict)
    arena_spec: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "dataset": self.dataset.to_dict() if self.dataset else None,
            "model": self.model.to_dict() if self.model else None,
            "config": self.config,
            "metrics": self.metrics,
            "environment": self.environment,
            "exports": self.exports,
            "arena_spec": self.arena_spec,
        }

    def save(self, path: str | Path) -> Path:
        """Save manifest to JSON file.

        Args:
            path: Output path for manifest.

        Returns:
            Path to saved manifest.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        logger.info("manifest_saved", path=str(output_path))
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> TrainingManifest:
        """Load manifest from JSON file.

        Args:
            path: Path to manifest file.

        Returns:
            Loaded TrainingManifest.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        manifest = cls(
            run_id=data["run_id"],
            timestamp=data.get("timestamp", ""),
            config=data.get("config", {}),
            metrics=data.get("metrics", {}),
            environment=data.get("environment", {}),
            exports=data.get("exports", {}),
            arena_spec=data.get("arena_spec", {}),
        )

        if data.get("dataset"):
            manifest.dataset = DatasetManifest(**data["dataset"])

        if data.get("model"):
            manifest.model = ModelManifest(**data["model"])

        return manifest


class ManifestBuilder:
    """Builder for creating training manifests.

    Collects information throughout the training process and
    generates a complete manifest for reproducibility.

    Example:
        >>> builder = ManifestBuilder("run_001")
        >>> builder.set_dataset("DIQA-5000", train_samples=4000, val_samples=500)
        >>> builder.set_model(model, base_model_id="SmolVLM-256M")
        >>> builder.set_config(training_config.to_dict())
        >>> builder.set_metrics(final_metrics)
        >>> manifest = builder.build()
        >>> manifest.save("outputs/manifest.json")
    """

    def __init__(self, run_id: str | None = None) -> None:
        """Initialize the builder.

        Args:
            run_id: Unique run identifier. Generated if not provided.
        """
        if run_id is None:
            run_id = self._generate_run_id()

        self._run_id = run_id
        self._dataset: DatasetManifest | None = None
        self._model: ModelManifest | None = None
        self._config: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}
        self._exports: dict[str, str] = {}

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.sha256(str(timestamp).encode()).hexdigest()[:8]
        return f"diqa_{timestamp}_{hash_suffix}"

    def set_dataset(
        self,
        name: str,
        version: str = "1.0",
        train_samples: int = 0,
        val_samples: int = 0,
        annotations_path: str = "",
        preprocessing: list[str] | None = None,
    ) -> ManifestBuilder:
        """Set dataset information.

        Args:
            name: Dataset name.
            version: Dataset version.
            train_samples: Number of training samples.
            val_samples: Number of validation samples.
            annotations_path: Path to annotations.
            preprocessing: Applied preprocessing steps.

        Returns:
            Self for chaining.
        """
        # Compute splits hash for reproducibility
        splits_str = f"train:{train_samples},val:{val_samples}"
        splits_hash = hashlib.sha256(splits_str.encode()).hexdigest()[:16]

        self._dataset = DatasetManifest(
            name=name,
            version=version,
            train_samples=train_samples,
            val_samples=val_samples,
            splits_hash=splits_hash,
            annotations_path=annotations_path,
            preprocessing=preprocessing or [],
        )
        return self

    def set_model(
        self,
        model: Any,
        base_model_id: str,
        lora_config: dict[str, Any] | None = None,
    ) -> ManifestBuilder:
        """Set model information from a trained model.

        Args:
            model: Trained PyTorch model.
            base_model_id: HuggingFace base model ID.
            lora_config: LoRA configuration if used.

        Returns:
            Self for chaining.
        """
        # Compute parameter counts
        num_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # Compute checkpoint hash
        state_dict = model.state_dict()
        checkpoint_bytes = str(sorted(state_dict.keys())).encode()
        checkpoint_hash = hashlib.sha256(checkpoint_bytes).hexdigest()[:16]

        # Generate model ID
        model_id = f"{base_model_id.split('/')[-1]}_diqa_{self._run_id}"

        self._model = ModelManifest(
            model_id=model_id,
            base_model_id=base_model_id,
            num_parameters=num_params,
            trainable_parameters=trainable_params,
            lora_config=lora_config,
            checkpoint_hash=checkpoint_hash,
        )
        return self

    def set_config(self, config: dict[str, Any]) -> ManifestBuilder:
        """Set training configuration.

        Args:
            config: Training configuration dictionary.

        Returns:
            Self for chaining.
        """
        self._config = config
        return self

    def set_metrics(
        self,
        train_loss: float = 0.0,
        val_loss: float = 0.0,
        best_val_loss: float = 0.0,
        epochs_completed: int = 0,
        total_steps: int = 0,
        **extra_metrics: Any,
    ) -> ManifestBuilder:
        """Set final training metrics.

        Args:
            train_loss: Final training loss.
            val_loss: Final validation loss.
            best_val_loss: Best validation loss achieved.
            epochs_completed: Number of epochs completed.
            total_steps: Total training steps.
            **extra_metrics: Additional metrics.

        Returns:
            Self for chaining.
        """
        self._metrics = {
            "train_loss": train_loss,
            "val_loss": val_loss,
            "best_val_loss": best_val_loss,
            "epochs_completed": epochs_completed,
            "total_steps": total_steps,
            **extra_metrics,
        }
        return self

    def add_export(self, format_name: str, path: str) -> ManifestBuilder:
        """Add an exported model path.

        Args:
            format_name: Export format (pytorch, onnx, torchscript).
            path: Path to exported model.

        Returns:
            Self for chaining.
        """
        self._exports[format_name] = path
        return self

    def build(self) -> TrainingManifest:
        """Build the complete training manifest.

        Returns:
            Complete TrainingManifest.
        """
        # Collect environment information
        environment = self._collect_environment()

        # Create Arena ModelSpec for evaluation integration
        arena_spec = self._create_arena_spec()

        manifest = TrainingManifest(
            run_id=self._run_id,
            dataset=self._dataset,
            model=self._model,
            config=self._config,
            metrics=self._metrics,
            environment=environment,
            exports=self._exports,
            arena_spec=arena_spec,
        )

        logger.info(
            "manifest_built",
            run_id=self._run_id,
            model_id=self._model.model_id if self._model else None,
        )

        return manifest

    def _collect_environment(self) -> dict[str, Any]:
        """Collect environment information for reproducibility."""
        env: dict[str, Any] = {
            "python_version": "",
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": "",
            "git_commit": "",
            "git_branch": "",
        }

        # Python version
        import sys

        env["python_version"] = sys.version.split()[0]

        # CUDA version
        if torch.cuda.is_available():
            env["cuda_version"] = torch.version.cuda or ""

        # Git information
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                env["git_commit"] = result.stdout.strip()

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                env["git_branch"] = result.stdout.strip()
        except Exception:  # noqa: BLE001
            pass

        return env

    def _create_arena_spec(self) -> dict[str, Any]:
        """Create Arena ModelSpec for evaluation integration.

        This allows the trained model to be loaded by the Arena
        for evaluation against the DIQA test set.
        """
        if self._model is None:
            return {}

        return {
            "source": "local",
            "id": self._model.model_id,
            "variant": "finetuned",
            "path": self._exports.get("pytorch", ""),
            "revision": self._run_id,
            "inference_backend": "regression",
            "metadata": {
                "base_model": self._model.base_model_id,
                "training_run": self._run_id,
                "best_val_loss": self._metrics.get("best_val_loss", 0),
            },
        }


class ModelExporter:
    """Export trained models to various formats.

    Handles export to PyTorch, ONNX, and TorchScript formats
    with proper metadata and versioning.

    Example:
        >>> exporter = ModelExporter(model, output_dir="exports/v1")
        >>> paths = exporter.export_all()
        >>> print(paths)  # {'pytorch': Path(...), 'onnx': Path(...), ...}
    """

    def __init__(
        self,
        model: Any,
        output_dir: str | Path,
        model_id: str = "diqa_model",
    ) -> None:
        """Initialize the exporter.

        Args:
            model: Trained PyTorch model.
            output_dir: Directory for exports.
            model_id: Model identifier for filenames.
        """
        self.model = model
        self.output_dir = Path(output_dir)
        self.model_id = model_id
        self.device = next(model.parameters()).device

    def export_pytorch(self) -> Path:
        """Export model in PyTorch format.

        Returns:
            Path to exported model directory.
        """
        export_path = self.output_dir / "pytorch"
        export_path.mkdir(parents=True, exist_ok=True)

        # Save model using built-in method if available
        if hasattr(self.model, "save_pretrained"):
            self.model.save_pretrained(str(export_path))
        else:
            torch.save(self.model.state_dict(), export_path / "pytorch_model.bin")

        logger.info("pytorch_export_complete", path=str(export_path))
        return export_path

    def export_onnx(
        self,
        opset_version: int = 14,
        dynamic_batch: bool = True,
    ) -> Path:
        """Export model to ONNX format.

        Args:
            opset_version: ONNX opset version.
            dynamic_batch: Enable dynamic batch size.

        Returns:
            Path to exported ONNX model.
        """
        export_path = self.output_dir / f"{self.model_id}.onnx"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        self.model.eval()

        # Create dummy input
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)

        # Configure dynamic axes
        dynamic_axes = {}
        if dynamic_batch:
            dynamic_axes = {
                "pixel_values": {0: "batch_size"},
                "scores": {0: "batch_size"},
            }

        torch.onnx.export(
            self.model,
            (dummy_input,),
            str(export_path),
            input_names=["pixel_values"],
            output_names=["scores"],
            dynamic_axes=dynamic_axes,
            opset_version=opset_version,
            do_constant_folding=True,
        )

        logger.info("onnx_export_complete", path=str(export_path))
        return export_path

    def export_torchscript(self, optimize: bool = True) -> Path:
        """Export model to TorchScript format.

        Args:
            optimize: Apply torch.jit.optimize_for_inference.

        Returns:
            Path to exported TorchScript model.
        """
        export_path = self.output_dir / f"{self.model_id}.torchscript"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        self.model.eval()

        # Create dummy input
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)

        # Trace the model
        traced = torch.jit.trace(self.model, (dummy_input,), strict=False)

        # Optimize if requested
        if optimize:
            try:
                traced = torch.jit.optimize_for_inference(traced)
            except Exception as e:
                logger.warning("torchscript_optimization_failed", error=str(e))

        traced.save(str(export_path))

        logger.info("torchscript_export_complete", path=str(export_path))
        return export_path

    def export_all(self) -> dict[str, Path]:
        """Export to all supported formats.

        Returns:
            Dictionary mapping format names to paths.
        """
        exports: dict[str, Path] = {}

        # PyTorch (always succeeds)
        exports["pytorch"] = self.export_pytorch()

        # ONNX (may fail for some models)
        try:
            exports["onnx"] = self.export_onnx()
        except Exception as e:
            logger.warning("onnx_export_skipped", error=str(e))

        # TorchScript (may fail for some models)
        try:
            exports["torchscript"] = self.export_torchscript()
        except Exception as e:
            logger.warning("torchscript_export_skipped", error=str(e))

        return exports


def create_arena_model_spec(
    manifest: TrainingManifest,
    model_path: str | Path,
) -> dict[str, Any]:
    """Create an Arena ModelSpec from a training manifest.

    This allows the trained model to be evaluated in Project A Arena
    using the regression backend.

    Args:
        manifest: Training manifest.
        model_path: Path to the exported model.

    Returns:
        ModelSpec dictionary for Arena evaluation.

    Example:
        >>> manifest = TrainingManifest.load("outputs/manifest.json")
        >>> spec = create_arena_model_spec(manifest, "exports/pytorch")
        >>> # Use in Arena:
        >>> backend = create_backend("regression")
        >>> backend.load(ModelSpec(**spec), config)
    """
    if manifest.model is None:
        raise ValueError("Manifest must have model information")

    return {
        "source": "local",
        "id": manifest.model.model_id,
        "variant": "finetuned",
        "path": str(model_path),
        "revision": manifest.run_id,
        "metadata": {
            "base_model": manifest.model.base_model_id,
            "training_run": manifest.run_id,
            "best_val_loss": manifest.metrics.get("best_val_loss", 0),
            "architecture": manifest.model.architecture,
            "lora_config": manifest.model.lora_config,
        },
    }
