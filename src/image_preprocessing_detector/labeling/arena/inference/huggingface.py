"""HuggingFace inference backend for the Arena.

This backend loads and runs inference on models from the
HuggingFace Hub, including base, quantized, and fine-tuned variants.
"""

from __future__ import annotations

import hashlib
import time
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


class HuggingFaceBackend(InferenceBackend):
    """Inference backend for HuggingFace models.

    Supports loading models from HuggingFace Hub using transformers
    library, including:
    - Base models (FP16/FP32)
    - Quantized models (4-bit, 8-bit via bitsandbytes)
    - Fine-tuned models with LoRA adapters

    Example:
        >>> from image_preprocessing_detector.labeling import ModelSpec
        >>> spec = ModelSpec(
        ...     source=ModelSource.HUGGINGFACE,
        ...     id="meta-llama/Llama-4-Maverick",
        ...     revision="main",
        ... )
        >>> backend = HuggingFaceBackend()
        >>> backend.load(spec, InferenceConfig(device="cuda"))
        >>> prediction = backend.predict(image)
    """

    def __init__(self) -> None:
        """Initialize the HuggingFace backend."""
        self._model: Any = None
        self._processor: Any = None
        self._tokenizer: Any = None
        self._spec: ModelSpec | None = None
        self._config: InferenceConfig | None = None
        self._model_info: dict[str, Any] = {}

    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load a model from HuggingFace Hub.

        Args:
            spec: Model specification with HF repo and revision.
            config: Inference configuration.

        Raises:
            ModelLoadError: If model cannot be loaded.
        """
        try:
            import torch
            from transformers import AutoModel, AutoProcessor, AutoTokenizer

            logger.info(
                "loading_huggingface_model",
                model_id=spec.id,
                revision=spec.revision,
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

            # Load model with appropriate settings
            load_kwargs: dict[str, Any] = {
                "trust_remote_code": True,
                "revision": spec.revision,
            }

            # Handle quantization
            if spec.is_quantized:
                load_kwargs.update(self._get_quantization_config(spec))

            # Load model
            start_time = time.perf_counter()

            try:
                # Try loading as vision-language model first (revision= parameter provided)
                self._processor = AutoProcessor.from_pretrained(  # nosec B615
                    spec.id,
                    revision=spec.revision,
                    trust_remote_code=True,
                )
            except Exception:
                # Fall back to tokenizer (revision= parameter provided)
                self._tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                    spec.id,
                    revision=spec.revision,
                    trust_remote_code=True,
                )

            self._model = AutoModel.from_pretrained(spec.id, **load_kwargs)  # nosec B615

            # Move to device
            if device != "cpu" and not spec.is_quantized:
                self._model = self._model.to(device)

            # Set to evaluation mode
            self._model.eval()

            # Load LoRA adapter if fine-tuned
            if spec.is_finetuned and spec.lora_adapter_path:
                self._load_lora_adapter(spec.lora_adapter_path)

            load_time = time.perf_counter() - start_time

            self._spec = spec
            self._config = config
            self._model_info = {
                "model_id": spec.id,
                "revision": spec.revision,
                "variant": spec.variant.value,
                "device": device,
                "load_time_seconds": load_time,
                "num_parameters": self._count_parameters(),
            }

            logger.info(
                "model_loaded",
                model_id=spec.id,
                load_time_seconds=f"{load_time:.2f}",
                num_parameters=self._model_info["num_parameters"],
            )

        except ImportError as e:
            msg = f"Missing required dependency: {e}"
            raise ModelLoadError(msg) from e
        except Exception as e:
            msg = f"Failed to load model {spec.id}: {e}"
            raise ModelLoadError(msg) from e

    def _get_quantization_config(self, spec: ModelSpec) -> dict[str, Any]:
        """Get quantization configuration for model loading.

        Args:
            spec: Model specification with quantization info.

        Returns:
            Dictionary with quantization kwargs.
        """
        try:
            from transformers import BitsAndBytesConfig

            quant_params = spec.quant_params or {}
            bits = quant_params.get("bits", 8)

            if bits == 4:
                return {
                    "quantization_config": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype="float16",
                        bnb_4bit_quant_type="nf4",
                    ),
                    "device_map": "auto",
                }
            # 8-bit
            return {
                "quantization_config": BitsAndBytesConfig(load_in_8bit=True),
                "device_map": "auto",
            }

        except ImportError:
            logger.warning("bitsandbytes_not_available")
            return {}

    def _load_lora_adapter(self, adapter_path: str) -> None:
        """Load a LoRA adapter onto the base model.

        Args:
            adapter_path: Path or HF repo for the adapter.
        """
        try:
            from peft import PeftModel

            logger.info("loading_lora_adapter", adapter_path=adapter_path)
            self._model = PeftModel.from_pretrained(self._model, adapter_path)
            self._model.eval()

        except ImportError as e:
            msg = "PEFT library required for LoRA adapters"
            raise ModelLoadError(msg) from e

    def _count_parameters(self) -> int:
        """Count total model parameters."""
        if self._model is None:
            return 0
        return sum(p.numel() for p in self._model.parameters())

    def unload(self) -> None:
        """Unload the model and free resources."""
        if self._model is not None:
            try:
                import torch

                del self._model
                del self._processor
                del self._tokenizer

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            except Exception as e:
                logger.warning("unload_error", error=str(e))

        self._model = None
        self._processor = None
        self._tokenizer = None
        self._spec = None
        self._config = None
        self._model_info = {}

        logger.info("model_unloaded")

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._model is not None

    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run inference on a single image.

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
        """Run inference on a batch of images.

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
            pil_images = []
            for img in images:
                if isinstance(img, np.ndarray):
                    pil_images.append(PILImage.fromarray(img))
                else:
                    pil_images.append(img)

            # Process in batches
            for i in range(0, len(pil_images), batch_size):
                batch = pil_images[i : i + batch_size]
                batch_predictions = self._process_batch(batch)
                predictions.extend(batch_predictions)

            return predictions  # noqa: TRY300

        except Exception as e:
            msg = f"Inference failed: {e}"
            raise InferenceError(msg) from e

    def _process_batch(
        self,
        images: list[Image.Image],
    ) -> list[DIQAPrediction]:
        """Process a batch of images through the model.

        This is a placeholder implementation that generates
        deterministic pseudo-predictions. In production, this would
        call the actual model.

        Args:
            images: Batch of PIL Images.

        Returns:
            List of DIQAPrediction objects.
        """
        import torch

        predictions = []
        start_time = time.perf_counter()

        with torch.no_grad():
            for idx, image in enumerate(images):
                # Placeholder: Generate deterministic scores based on image
                # In production, this would run actual model inference
                img_array = np.array(image)

                # Use image statistics for deterministic pseudo-predictions
                # This maintains the interface while the actual model
                # integration is implemented
                mean_intensity = img_array.mean() / 255.0
                std_intensity = img_array.std() / 255.0

                # Deterministic mapping (placeholder)
                overall = float(
                    np.clip(0.5 + 0.3 * mean_intensity + 0.2 * std_intensity, 0, 1)
                )
                sharpness = float(np.clip(0.4 + 0.4 * std_intensity, 0, 1))
                color = float(np.clip(0.6 + 0.2 * mean_intensity, 0, 1))

                inference_time = (time.perf_counter() - start_time) * 1000 / (idx + 1)

                predictions.append(
                    DIQAPrediction(
                        overall=overall,
                        sharpness=sharpness,
                        color=color,
                        image_id=f"batch_{idx}",
                        inference_time_ms=inference_time,
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
            tokenizer_hash=self._compute_tokenizer_hash(),
            code_version=self._get_code_version(),
        )

    def _compute_model_checksum(self) -> str:
        """Compute a checksum of the model weights."""
        if self._model is None:
            return ""

        try:
            # Use model state dict for checksum
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
        """Compute a hash of the model configuration."""
        if self._model is None:
            return ""

        try:
            config = self._model.config.to_dict()
            config_str = str(sorted(config.items()))
            return f"sha256:{hashlib.sha256(config_str.encode()).hexdigest()[:16]}"

        except Exception:
            return ""

    def _compute_tokenizer_hash(self) -> str:
        """Compute a hash of the tokenizer."""
        tokenizer = self._tokenizer or (
            self._processor.tokenizer if self._processor else None
        )

        if tokenizer is None:
            return ""

        try:
            vocab = str(sorted(tokenizer.get_vocab().items()))
            return f"sha256:{hashlib.sha256(vocab.encode()).hexdigest()[:16]}"

        except Exception:
            return ""

    def _get_code_version(self) -> str:
        """Get the current code version from git."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return f"git:{result.stdout.strip()[:8]}"

        except Exception:  # noqa: S110
            pass

        return ""

    def get_model_info(self) -> dict[str, Any]:
        """Get metadata about the loaded model."""
        return self._model_info.copy()
