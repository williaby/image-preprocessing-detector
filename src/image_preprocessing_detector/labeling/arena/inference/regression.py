"""Regression inference backend for fine-tuned DIQA models.

This backend handles models with regression heads that output direct
numeric tensors [overall, sharpness, color] instead of text responses.

Used for evaluating Project C fine-tuned teacher models.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog
from numpy.typing import NDArray

from image_preprocessing_detector.labeling.arena.inference.base import (
    InferenceBackend,
    InferenceConfig,
    InferenceError,
    ModelLoadError,
    ModelNotLoadedError,
)
from image_preprocessing_detector.labeling.arena.schemas import (
    DIQAPrediction,
    ProvenanceInfo,
)
from image_preprocessing_detector.utils.path_security import validate_safe_path

if TYPE_CHECKING:
    from PIL import Image

    from image_preprocessing_detector.labeling.model_spec import ModelSpec

logger = structlog.get_logger(__name__)


class RegressionBackend(InferenceBackend):
    """Inference backend for regression head models.

    This backend loads models that have been fine-tuned with a regression
    head (Project C output) and directly output [overall, sharpness, color]
    tensors without text generation.

    Architecture:
        Vision Encoder → Pooled Embedding → Regression Head → [3 scores]

    Example:
        >>> spec = ModelSpec(
        ...     source=ModelSource.LOCAL,
        ...     id="diqa-teacher-v1",
        ...     variant=ModelVariant.FINETUNED,
        ... )
        >>> backend = RegressionBackend()
        >>> backend.load(spec, InferenceConfig(device="cuda"))
        >>> prediction = backend.predict(image)
        >>> print(prediction.overall, prediction.sharpness, prediction.color)
    """

    def __init__(self) -> None:
        """Initialize the regression backend."""
        self._model: Any = None
        self._processor: Any = None
        self._spec: ModelSpec | None = None
        self._config: InferenceConfig | None = None
        self._model_info: dict[str, Any] = {}
        self._device: str = "cpu"

    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load a regression head model.

        Args:
            spec: Model specification with path to fine-tuned model.
            config: Inference configuration.

        Raises:
            ModelLoadError: If model cannot be loaded.
        """
        try:
            import torch

            logger.info(
                "loading_regression_model",
                model_id=spec.id,
                device=config.device,
            )

            # Set seeds for reproducibility
            if config.deterministic:
                torch.manual_seed(config.seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(config.seed)

            # Determine device
            device = config.device
            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("cuda_not_available", fallback="cpu")
                device = "cpu"
            self._device = device

            start_time = time.perf_counter()

            # Load the model based on source
            self._load_model_from_spec(spec, config)

            load_time = time.perf_counter() - start_time

            self._spec = spec
            self._config = config
            self._model_info = {
                "model_id": spec.id,
                "revision": spec.revision,
                "variant": spec.variant.value,
                "device": device,
                "load_time_seconds": load_time,
                "output_type": "regression",
                "num_outputs": 3,
            }

            logger.info(
                "regression_model_loaded",
                model_id=spec.id,
                load_time_seconds=f"{load_time:.2f}",
            )

        except ImportError as e:
            msg = f"Missing required dependency: {e}"
            raise ModelLoadError(msg) from e
        except Exception as e:
            msg = f"Failed to load regression model {spec.id}: {e}"
            raise ModelLoadError(msg) from e

    def _load_model_from_spec(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load model based on specification source.

        Args:
            spec: Model specification.
            config: Inference configuration.
        """
        from image_preprocessing_detector.labeling.model_spec import ModelSource

        if spec.source == ModelSource.LOCAL:
            self._load_local_model(spec, config)
        elif spec.source == ModelSource.HUGGINGFACE:
            self._load_huggingface_model(spec, config)
        else:
            msg = f"Unsupported source for regression backend: {spec.source}"
            raise ModelLoadError(msg)

    def _load_local_model(self, spec: ModelSpec, _config: InferenceConfig) -> None:
        """Load model from local path.

        Args:
            spec: Model specification with local path.
            _config: Inference configuration (unused).
        """
        import torch

        # Reject traversal patterns (".." etc.) in spec.id and use the
        # resolved absolute path for the literal-path check below.
        # NOTE: like LocalBackend, this literal-path branch does NOT
        # constrain to a model-registry root — operators are trusted
        # to supply explicit absolute paths in this Arena tooling.
        # The `checkpoints/` fallback further down IS constrained via
        # `allowed_base=checkpoints_base`. If callers ever start
        # supplying spec.id from an untrusted boundary (HTTP API,
        # public CLI flag), pass `allowed_base=<models_root>` here.
        #
        # We intentionally do NOT pass `must_exist=True` here (unlike
        # LocalBackend.load): a non-existent literal path is the
        # signal that triggers the `checkpoints/` fallback below.
        try:
            model_path = validate_safe_path(spec.id)
        except (ValueError, TypeError) as exc:
            # TypeError defends against a non-str spec.id (e.g.
            # accidentally None or a Path that Pydantic didn't
            # coerce); ValueError catches traversal-pattern rejects.
            msg = f"Invalid model path: {spec.id!r}"
            raise ModelLoadError(msg) from exc

        if not model_path.exists():
            # Try as relative to checkpoints directory; constrain the
            # resolved path to stay within ./checkpoints to prevent escape.
            checkpoints_base = Path("checkpoints").resolve()
            try:
                model_path = validate_safe_path(
                    checkpoints_base / spec.id,
                    allowed_base=checkpoints_base,
                    must_exist=True,
                )
            except (ValueError, FileNotFoundError) as exc:
                msg = f"Model path not found: {spec.id}"
                raise ModelLoadError(msg) from exc

        # Load the complete model (base + regression head)
        if (model_path / "pytorch_model.bin").exists():
            state_dict = torch.load(
                model_path / "pytorch_model.bin",
                map_location=self._device,
                weights_only=True,
            )
            # Model architecture must be defined or loaded
            self._model = self._create_model_from_state_dict(state_dict, spec)
        elif (model_path / "model.safetensors").exists():
            from safetensors.torch import load_file

            state_dict = load_file(model_path / "model.safetensors")
            self._model = self._create_model_from_state_dict(state_dict, spec)
        else:
            msg = f"No model weights found in {model_path}"
            raise ModelLoadError(msg)

        # Load processor if available
        if (model_path / "processor_config.json").exists():
            from transformers import AutoProcessor

            self._processor = AutoProcessor.from_pretrained(  # nosec B615
                model_path,
                trust_remote_code=True,
            )

    def _load_huggingface_model(
        self, spec: ModelSpec, _config: InferenceConfig
    ) -> None:
        """Load regression model from HuggingFace.

        This assumes the model has been uploaded with the regression head
        as part of a custom model class.

        Args:
            spec: Model specification.
            _config: Inference configuration (unused).
        """
        from transformers import AutoModel, AutoProcessor

        # For regression models, we expect a custom model class
        # that includes the regression head (revision= parameter provided)
        self._processor = AutoProcessor.from_pretrained(  # nosec B615
            spec.id,
            revision=spec.revision,
            trust_remote_code=True,
        )

        self._model = AutoModel.from_pretrained(  # nosec B615
            spec.id,
            revision=spec.revision,
            trust_remote_code=True,
        )

        if self._device != "cpu":
            self._model = self._model.to(self._device)

        self._model.eval()

    def _create_model_from_state_dict(
        self, state_dict: dict[str, Any], spec: ModelSpec
    ) -> Any:
        """Create model architecture and load weights.

        Args:
            state_dict: Model state dictionary.
            spec: Model specification.

        Returns:
            Loaded model.
        """
        try:
            from image_preprocessing_detector.labeling.finetuning.regression_head import (
                DIQARegressionModel,
            )
        except ImportError as e:
            msg = (
                "DIQARegressionModel requires the labeling.finetuning package, "
                "which was removed in the Phase 2/7 cleanup. "
                "Use HuggingFace-hosted models instead of local state dicts."
            )
            raise ModelLoadError(msg) from e

        # Determine base model from spec or state dict
        # Use quant_params for extra model metadata (if not available, use defaults)
        extra_params = spec.quant_params or {}
        base_model_id = extra_params.get(
            "base_model", "HuggingFaceTB/SmolVLM-256M-Instruct"
        )

        model = DIQARegressionModel(base_model_id=base_model_id)
        model.load_state_dict(state_dict)

        if self._device != "cpu":
            model = model.to(self._device)

        model.eval()
        return model

    def unload(self) -> None:
        """Unload the model and free resources."""
        if self._model is not None:
            try:
                import torch

                del self._model
                del self._processor

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            except Exception as e:
                logger.warning("unload_error", error=str(e))

        self._model = None
        self._processor = None
        self._spec = None
        self._config = None
        self._model_info = {}

        logger.info("regression_model_unloaded")

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._model is not None

    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run regression inference on a single image.

        Args:
            image: Input image as numpy array or PIL Image.

        Returns:
            DIQAPrediction with quality scores.

        Raises:
            ModelNotLoadedError: If model is not loaded.
            InferenceError: If inference fails.
        """
        if not self.is_loaded():
            msg = "Model not loaded. Call load() first."
            raise ModelNotLoadedError(msg)

        results = self.predict_batch([image])
        return results[0]

    def predict_batch(
        self,
        images: list[NDArray[np.uint8] | Image.Image],
    ) -> list[DIQAPrediction]:
        """Run regression inference on a batch of images.

        Args:
            images: List of input images.

        Returns:
            List of DIQAPrediction objects.

        Raises:
            ModelNotLoadedError: If model is not loaded.
            InferenceError: If inference fails.
        """
        if not self.is_loaded():
            msg = "Model not loaded. Call load() first."
            raise ModelNotLoadedError(msg)

        try:
            from PIL import Image as PILImage

            predictions = []
            batch_size = self._config.batch_size if self._config else 8

            # Convert numpy arrays to PIL Images
            pil_images: list[PILImage.Image] = []
            for img in images:
                if isinstance(img, np.ndarray):
                    pil_images.append(PILImage.fromarray(img))
                else:
                    pil_images.append(img)

            # Process in batches
            for i in range(0, len(pil_images), batch_size):
                batch = pil_images[i : i + batch_size]
                batch_predictions = self._process_batch(batch, start_idx=i)
                predictions.extend(batch_predictions)

            return predictions  # noqa: TRY300

        except Exception as e:
            msg = f"Regression inference failed: {e}"
            raise InferenceError(msg) from e

    def _process_batch(
        self,
        images: list[Image.Image],
        start_idx: int = 0,
    ) -> list[DIQAPrediction]:
        """Process a batch of images through the regression model.

        Args:
            images: Batch of PIL Images.
            start_idx: Starting index for image IDs.

        Returns:
            List of DIQAPrediction objects.
        """
        import torch

        predictions = []
        start_time = time.perf_counter()

        # Prepare inputs
        if self._processor is not None:
            inputs = self._processor(images=images, return_tensors="pt")
            if self._device != "cpu":
                inputs = {
                    k: v.to(self._device) if hasattr(v, "to") else v
                    for k, v in inputs.items()
                }
        else:
            # Fallback: basic preprocessing
            from torchvision import transforms

            transform = transforms.Compose(
                [
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            # ToTensor() returns Tensor for PIL Images; type annotation helps type checker
            tensors: list[torch.Tensor] = [transform(img) for img in images]
            inputs = {"pixel_values": torch.stack(tensors)}
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self._model(**inputs)

            # Handle different output formats
            if hasattr(outputs, "logits"):
                scores = outputs.logits
            elif isinstance(outputs, torch.Tensor):
                scores = outputs
            else:
                scores = outputs.get("scores", outputs.get("logits"))

            # Ensure scores are in [0, 1] range
            scores = (
                torch.sigmoid(scores)
                if scores.min() < 0 or scores.max() > 1
                else scores
            )
            scores = scores.cpu().numpy()

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Create predictions
        for idx, score_row in enumerate(scores):
            predictions.append(
                DIQAPrediction(
                    overall=float(np.clip(score_row[0], 0.0, 1.0)),
                    sharpness=float(np.clip(score_row[1], 0.0, 1.0)),
                    color=float(np.clip(score_row[2], 0.0, 1.0)),
                    image_id=f"regression_{start_idx + idx}",
                    inference_time_ms=elapsed_ms / len(scores),
                )
            )

        return predictions

    def get_provenance(self) -> ProvenanceInfo:
        """Get provenance information for the loaded model.

        Returns:
            ProvenanceInfo with checksums and metadata.

        Raises:
            ModelNotLoadedError: If model is not loaded.
        """
        if not self.is_loaded() or self._spec is None:
            msg = "Model not loaded"
            raise ModelNotLoadedError(msg)

        return ProvenanceInfo(
            model_checksum=self._compute_model_checksum(),
            config_hash=self._compute_config_hash(),
            tokenizer_hash="",
            code_version=self._get_code_version(),
        )

    def _compute_model_checksum(self) -> str:
        """Compute a checksum of the model weights."""
        if self._model is None:
            return ""

        try:
            state_dict = self._model.state_dict()
            hash_obj = hashlib.sha256()

            for key in sorted(state_dict.keys()):
                tensor = state_dict[key]
                hash_obj.update(key.encode())
                hash_obj.update(tensor.cpu().numpy().tobytes())

            return f"sha256:{hash_obj.hexdigest()[:16]}"

        except Exception as e:
            logger.warning("checksum_computation_failed", error=str(e))
            return ""

    def _compute_config_hash(self) -> str:
        """Compute a hash of the configuration."""
        if self._config is None:
            return ""

        config_str = str(self._config.to_dict())
        return f"sha256:{hashlib.sha256(config_str.encode()).hexdigest()[:16]}"

    def _get_code_version(self) -> str:
        """Get the current code version from git."""
        try:
            import subprocess  # nosec B404

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],  # noqa: S607  # nosec B603, B607
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return f"git:{result.stdout.strip()[:8]}"

        except Exception:  # noqa: S110  # nosec B110
            pass

        return ""

    def get_model_info(self) -> dict[str, Any]:
        """Get metadata about the loaded model."""
        return self._model_info.copy()
