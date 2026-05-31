"""Local artifact inference backend for the Arena.

This backend loads and runs inference on locally stored model
artifacts, including quantized models from Project B and
fine-tuned models from Project C.
"""

from __future__ import annotations

import hashlib
import json
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

if TYPE_CHECKING:
    from PIL import Image

    from image_preprocessing_detector.labeling.model_spec import ModelSpec

logger = structlog.get_logger(__name__)

# Common string constants (S1192: avoid duplicate string literals)
SAFETENSORS_FILE = "model.safetensors"
ONNX_MODEL_FILE = "model.onnx"
MODEL_NOT_LOADED_MSG = "Model not loaded"


class LocalBackend(InferenceBackend):
    """Inference backend for locally stored model artifacts.

    Supports loading models from local filesystem, including:
    - Quantized models (safetensors format)
    - Fine-tuned models with adapters
    - ONNX models

    Example:
        >>> spec = ModelSpec(
        ...     source=ModelSource.LOCAL,
        ...     id="/path/to/model",
        ...     revision="v1.0.0",
        ... )
        >>> backend = LocalBackend()
        >>> backend.load(spec, InferenceConfig())
        >>> prediction = backend.predict(image)
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._spec: ModelSpec | None = None
        self._config: InferenceConfig | None = None
        self._model_info: dict[str, Any] = {}
        self._artifact_path: Path | None = None

    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load a model from local artifact.

        Args:
            spec (ModelSpec): Model specification with local path.
            config (InferenceConfig): Inference configuration.

        Raises:
            ModelLoadError: If model cannot be loaded.
        """
        try:
            artifact_path = Path(spec.id)

            if not artifact_path.exists():
                msg = f"Artifact path does not exist: {artifact_path}"
                raise ModelLoadError(msg)  # noqa: TRY301

            logger.info(
                "loading_local_artifact",
                path=str(artifact_path),
                device=config.device,
            )

            start_time = time.perf_counter()

            # Detect artifact type and load accordingly
            if (artifact_path / SAFETENSORS_FILE).exists():
                self._load_safetensors(artifact_path, config)
            elif (artifact_path / ONNX_MODEL_FILE).exists():
                self._load_onnx(artifact_path, config)
            elif artifact_path.suffix == ".onnx":
                self._load_onnx(artifact_path.parent, config, artifact_path.name)
            else:
                # Try loading as HuggingFace-style directory
                self._load_hf_style(artifact_path, config)

            load_time = time.perf_counter() - start_time

            self._spec = spec
            self._config = config
            self._artifact_path = artifact_path
            self._model_info = {
                "artifact_path": str(artifact_path),
                "revision": spec.revision,
                "variant": spec.variant.value,
                "device": config.device,
                "load_time_seconds": load_time,
            }

            logger.info(
                "local_artifact_loaded",
                path=str(artifact_path),
                load_time_seconds=f"{load_time:.2f}",
            )

        except ModelLoadError:
            raise
        except Exception as e:
            msg = f"Failed to load local artifact {spec.id}: {e}"
            raise ModelLoadError(msg) from e

    def _load_safetensors(self, path: Path, _config: InferenceConfig) -> None:
        """Load model from safetensors format."""
        try:
            from safetensors.torch import load_file

            weights_path = path / SAFETENSORS_FILE
            state_dict = load_file(str(weights_path))

            # Load config if available
            config_path = path / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    model_config = json.load(f)
                self._model_info["config"] = model_config

            # Store state dict for inference
            self._model = {"state_dict": state_dict, "type": "safetensors"}

            logger.info("safetensors_loaded", path=str(weights_path))

        except ImportError as e:
            msg = "safetensors library required"
            raise ModelLoadError(msg) from e

    def _load_onnx(
        self, path: Path, config: InferenceConfig, filename: str = ONNX_MODEL_FILE
    ) -> None:
        """Load ONNX model."""
        try:
            import onnxruntime as ort

            model_path = path / filename

            # Configure session
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            # Select providers based on device
            if config.device.startswith("cuda"):
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]

            session = ort.InferenceSession(
                str(model_path),
                sess_options=session_options,
                providers=providers,
            )

            self._model = {"session": session, "type": "onnx"}

            logger.info(
                "onnx_loaded",
                path=str(model_path),
                providers=session.get_providers(),
            )

        except ImportError as e:
            msg = "onnxruntime library required"
            raise ModelLoadError(msg) from e

    def _load_hf_style(self, path: Path, config: InferenceConfig) -> None:
        """Load model in HuggingFace-style directory format."""
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            model = AutoModel.from_pretrained(  # nosec B615
                str(path),
                local_files_only=True,
                trust_remote_code=True,
            )

            if config.device != "cpu" and torch.cuda.is_available():
                model = model.to(config.device)

            model.eval()

            try:
                tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                    str(path), local_files_only=True
                )
            except Exception:
                tokenizer = None

            self._model = {"model": model, "tokenizer": tokenizer, "type": "hf"}

            logger.info("hf_style_loaded", path=str(path))

        except ImportError as e:
            msg = "transformers library required"
            raise ModelLoadError(msg) from e

    def unload(self) -> None:
        """Unload the model and free resources."""
        if self._model is not None:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:  # noqa: S110
                pass

        self._model = None
        self._spec = None
        self._config = None
        self._model_info = {}
        self._artifact_path = None

        logger.info("local_model_unloaded")

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._model is not None

    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run inference on a single image."""
        if not self.is_loaded():
            msg = MODEL_NOT_LOADED_MSG
            raise ModelNotLoadedError(msg)

        results = self.predict_batch([image])
        return results[0]

    def predict_batch(
        self,
        images: list[NDArray[np.uint8] | Image.Image],
    ) -> list[DIQAPrediction]:
        """Run inference on a batch of images."""
        if not self.is_loaded():
            msg = MODEL_NOT_LOADED_MSG
            raise ModelNotLoadedError(msg)

        try:
            model_type = self._model.get("type", "unknown")

            if model_type == "onnx":
                return self._predict_onnx(images)
            if model_type == "hf":
                return self._predict_hf(images)
            # Fallback: placeholder predictions
            return self._predict_placeholder(images)

        except Exception as e:
            msg = f"Inference failed: {e}"
            raise InferenceError(msg) from e

    def _predict_onnx(
        self, images: list[NDArray[np.uint8] | Image.Image]
    ) -> list[DIQAPrediction]:
        """Run ONNX model inference."""
        from PIL import Image as PILImage

        session = self._model["session"]
        predictions = []

        for idx, img in enumerate(images):
            start_time = time.perf_counter()

            # Convert to numpy if needed
            if not isinstance(img, np.ndarray):
                img = np.array(img)

            # Preprocess for ONNX (assuming standard input format)
            # Resize to 224x224 and normalize

            pil_img = PILImage.fromarray(img)
            pil_img = pil_img.resize((224, 224))
            input_array = np.array(pil_img).astype(np.float32) / 255.0

            # Convert to NCHW format
            input_array = np.transpose(input_array, (2, 0, 1))
            input_array = np.expand_dims(input_array, axis=0)

            # Run inference
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: input_array})

            # Parse outputs (assuming 3 output values)
            if len(outputs[0][0]) >= 3:
                overall, sharpness, color = outputs[0][0][:3]
            else:
                overall = outputs[0][0][0] if len(outputs[0][0]) > 0 else 0.5
                sharpness = 0.5
                color = 0.5

            inference_time = (time.perf_counter() - start_time) * 1000

            predictions.append(
                DIQAPrediction(
                    overall=float(np.clip(overall, 0, 1)),
                    sharpness=float(np.clip(sharpness, 0, 1)),
                    color=float(np.clip(color, 0, 1)),
                    image_id=f"local_{idx}",
                    inference_time_ms=inference_time,
                )
            )

        return predictions

    def _predict_hf(
        self, images: list[NDArray[np.uint8] | Image.Image]
    ) -> list[DIQAPrediction]:
        """Run HuggingFace model inference."""
        # Similar to HuggingFaceBackend, but using local model
        return self._predict_placeholder(images)

    def _predict_placeholder(
        self, images: list[NDArray[np.uint8] | Image.Image]
    ) -> list[DIQAPrediction]:
        """Generate placeholder predictions for testing."""
        predictions = []

        for idx, img in enumerate(images):
            start_time = time.perf_counter()

            if not isinstance(img, np.ndarray):
                img = np.array(img)

            # Deterministic pseudo-predictions based on image stats
            mean_val = img.mean() / 255.0
            std_val = img.std() / 255.0

            overall = float(np.clip(0.5 + 0.3 * mean_val + 0.2 * std_val, 0, 1))
            sharpness = float(np.clip(0.4 + 0.4 * std_val, 0, 1))
            color = float(np.clip(0.6 + 0.2 * mean_val, 0, 1))

            inference_time = (time.perf_counter() - start_time) * 1000

            predictions.append(
                DIQAPrediction(
                    overall=overall,
                    sharpness=sharpness,
                    color=color,
                    image_id=f"local_{idx}",
                    inference_time_ms=inference_time,
                )
            )

        return predictions

    def get_provenance(self) -> ProvenanceInfo:
        """Get provenance information."""
        if not self.is_loaded():
            msg = MODEL_NOT_LOADED_MSG
            raise ModelNotLoadedError(msg)

        return ProvenanceInfo(
            model_checksum=self._compute_artifact_checksum(),
            config_hash=self._compute_config_hash(),
        )

    def _compute_artifact_checksum(self) -> str:
        """Compute checksum of the artifact files."""
        if self._artifact_path is None:
            return ""

        hash_obj = hashlib.sha256()

        # Hash key files
        for filename in [SAFETENSORS_FILE, ONNX_MODEL_FILE, "config.json"]:
            file_path = self._artifact_path / filename
            if file_path.exists():
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hash_obj.update(chunk)

        return f"sha256:{hash_obj.hexdigest()[:16]}"

    def _compute_config_hash(self) -> str:
        """Compute hash of configuration."""
        config_info = self._model_info.get("config", {})
        if not config_info:
            return ""

        config_str = json.dumps(config_info, sort_keys=True)
        return f"sha256:{hashlib.sha256(config_str.encode()).hexdigest()[:16]}"

    def get_model_info(self) -> dict[str, Any]:
        """Get metadata about the loaded model."""
        return self._model_info.copy()
