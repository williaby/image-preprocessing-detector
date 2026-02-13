# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal inference backend for the Arena.

This backend runs VLM inference on Modal's serverless GPU infrastructure,
enabling cloud-based evaluation without local GPU requirements.

Features:
- Serverless GPU inference (T4/A10)
- Circuit breaker for resilience
- Automatic model caching in Modal volumes
- Batch inference support
"""

from __future__ import annotations

import hashlib
import re
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
from image_preprocessing_detector.labeling.arena.modal_client import (
    ArenaInferenceRequest,
    ArenaModalClient,
    CircuitBreakerConfig,
)
from image_preprocessing_detector.labeling.arena.schemas import (
    DIQAPrediction,
    ProvenanceInfo,
)

if TYPE_CHECKING:
    from PIL import Image

    from image_preprocessing_detector.labeling.model_spec import ModelSpec

logger = structlog.get_logger(__name__)

# Default prompt for DIQA assessment
DEFAULT_DIQA_PROMPT = """Analyze this document image and rate its quality on a scale of 0.0 to 1.0 for each dimension:

1. Overall Quality: General quality considering all aspects
2. Sharpness: Text and image clarity, focus
3. Color: Color reproduction accuracy and balance

Respond ONLY with three numbers in this exact format:
Overall: X.XX
Sharpness: X.XX
Color: X.XX

Be precise and consistent. A score of 1.0 means perfect quality, 0.0 means unusable."""


class ModalBackend(InferenceBackend):
    """Inference backend for Modal serverless GPU.

    Runs VLM inference on Modal's cloud infrastructure, providing:
    - Access to high-end GPUs (T4, A10, A100)
    - No local GPU requirements
    - Automatic model caching
    - Resilient inference with circuit breaker

    Example:
        >>> from image_preprocessing_detector.labeling import ModelSpec, ModelSource
        >>> spec = ModelSpec(
        ...     source=ModelSource.HUGGINGFACE,
        ...     id="unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
        ... )
        >>> backend = ModalBackend()
        >>> backend.load(spec, InferenceConfig(device="modal"))
        >>> prediction = backend.predict(image)
    """

    def __init__(
        self,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
        custom_prompt: str | None = None,
    ) -> None:
        """Initialize the Modal backend.

        Args:
            circuit_breaker_config: Configuration for circuit breaker.
            custom_prompt: Custom prompt for DIQA assessment (optional).
        """
        self._client: ArenaModalClient | None = None
        self._spec: ModelSpec | None = None
        self._config: InferenceConfig | None = None
        self._model_info: dict[str, Any] = {}
        self._prompt = custom_prompt or DEFAULT_DIQA_PROMPT
        self._circuit_breaker_config = circuit_breaker_config

    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Initialize Modal client for the model.

        Note: Modal loads models lazily on first inference, so this
        mainly validates configuration and sets up the client.

        Args:
            spec: Model specification.
            config: Inference configuration.

        Raises:
            ModelLoadError: If Modal client cannot be initialized.
        """
        try:
            logger.info(
                "initializing_modal_backend",
                model_id=spec.id,
                device=config.device,
            )

            # Initialize the Modal client
            self._client = ArenaModalClient(
                config=self._circuit_breaker_config,
            )

            self._spec = spec
            self._config = config
            self._model_info = {
                "model_id": spec.id,
                "revision": spec.revision,
                "variant": spec.variant.value,
                "device": "modal-gpu",
                "backend": "modal",
            }

            logger.info(
                "modal_backend_initialized",
                model_id=spec.id,
            )

        except Exception as e:
            msg = f"Failed to initialize Modal backend for {spec.id}: {e}"
            raise ModelLoadError(msg) from e

    def unload(self) -> None:
        """Unload the model and reset client."""
        if self._client is not None:
            self._client.reset()

        self._client = None
        self._spec = None
        self._config = None
        self._model_info = {}

        logger.info("modal_backend_unloaded")

    def is_loaded(self) -> bool:
        """Check if the backend is initialized."""
        return self._client is not None and self._spec is not None

    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run inference on a single image via Modal.

        Args:
            image: Input image as numpy array or PIL Image.

        Returns:
            DIQAPrediction with quality scores.

        Raises:
            ModelNotLoadedError: If backend is not initialized.
            InferenceError: If inference fails.
        """
        if not self.is_loaded():
            msg = "Modal backend not initialized. Call load() first."
            raise ModelNotLoadedError(msg)

        results = self.predict_batch([image])
        return results[0]

    def predict_batch(
        self,
        images: list[NDArray[np.uint8] | Image.Image],
    ) -> list[DIQAPrediction]:
        """Run inference on a batch of images via Modal.

        Args:
            images: List of input images.

        Returns:
            List of DIQAPrediction objects.

        Raises:
            ModelNotLoadedError: If backend is not initialized.
            InferenceError: If all inferences fail.
        """
        if not self.is_loaded() or self._client is None or self._spec is None:
            msg = "Modal backend not initialized. Call load() first."
            raise ModelNotLoadedError(msg)

        from PIL import Image as PILImage

        try:
            predictions: list[DIQAPrediction] = []
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
            msg = f"Modal inference failed: {e}"
            raise InferenceError(msg) from e

    def _process_batch(
        self,
        images: list[Image.Image],
        start_idx: int = 0,
    ) -> list[DIQAPrediction]:
        """Process a batch of images through Modal.

        Args:
            images: Batch of PIL Images.
            start_idx: Starting index for image IDs.

        Returns:
            List of DIQAPrediction objects.
        """
        if self._client is None or self._spec is None:
            return []

        predictions: list[DIQAPrediction] = []

        # Create requests for batch
        requests = [
            ArenaInferenceRequest(
                image=img,
                prompt=self._prompt,
                model_id=self._spec.id,
                max_new_tokens=self._config.max_length if self._config else 256,
                temperature=self._config.temperature if self._config else 0.1,
                request_id=f"batch_{start_idx + idx}",
            )
            for idx, img in enumerate(images)
        ]

        # Execute batch inference
        start_time = time.perf_counter()
        responses = self._client.batch_predict(requests)

        for idx, (request, response) in enumerate(
            zip(requests, responses, strict=False)
        ):
            if response is None:
                # Inference failed, use fallback scores
                logger.warning(
                    "modal_inference_failed",
                    image_id=request.request_id,
                    fallback="default_scores",
                )
                predictions.append(
                    DIQAPrediction(
                        overall=0.5,
                        sharpness=0.5,
                        color=0.5,
                        image_id=request.request_id or f"modal_{start_idx + idx}",
                        inference_time_ms=0.0,
                    )
                )
            else:
                # Parse VLM response to extract scores
                scores = self._parse_vlm_response(response.text)

                predictions.append(
                    DIQAPrediction(
                        overall=scores.get("overall", 0.5),
                        sharpness=scores.get("sharpness", 0.5),
                        color=scores.get("color", 0.5),
                        image_id=request.request_id or f"modal_{start_idx + idx}",
                        inference_time_ms=response.inference_time_ms,
                    )
                )

        total_time = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "modal_batch_complete",
            batch_size=len(images),
            total_time_ms=f"{total_time:.1f}",
        )

        return predictions

    def _parse_vlm_response(self, response_text: str) -> dict[str, float]:
        """Parse VLM response text to extract quality scores.

        Expected format:
            Overall: 0.75
            Sharpness: 0.82
            Color: 0.68

        Args:
            response_text: Raw text from VLM.

        Returns:
            Dictionary with overall, sharpness, color scores.
        """
        scores: dict[str, float] = {
            "overall": 0.5,
            "sharpness": 0.5,
            "color": 0.5,
        }

        # Pattern to match "Dimension: X.XX" format (case-insensitive)
        # Supports optional negative sign for clamping
        patterns = {
            "overall": r"overall[:\s]+(-?\d+\.?\d*)",
            "sharpness": r"sharpness[:\s]+(-?\d+\.?\d*)",
            "color": r"color[:\s]+(-?\d+\.?\d*)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    # Clamp to [0, 1] range
                    scores[key] = max(0.0, min(1.0, value))
                except ValueError:
                    pass  # regex matched non-numeric text; skip dimension

        return scores

    def get_provenance(self) -> ProvenanceInfo:
        """Get provenance information for the model.

        Returns:
            ProvenanceInfo with checksums and metadata.

        Raises:
            ModelNotLoadedError: If backend is not initialized.
        """
        if not self.is_loaded() or self._spec is None:
            msg = "Modal backend not initialized"
            raise ModelNotLoadedError(msg)

        return ProvenanceInfo(
            model_checksum=self._compute_model_checksum(),
            config_hash=self._compute_config_hash(),
            tokenizer_hash="",  # Not available for Modal backend
            code_version=self._get_code_version(),
        )

    def _compute_model_checksum(self) -> str:
        """Compute a checksum identifier for the model."""
        if self._spec is None:
            return ""

        # Use model ID and revision as pseudo-checksum
        identifier = f"{self._spec.id}@{self._spec.revision or 'main'}"
        hash_obj = hashlib.sha256(identifier.encode())
        return f"modal-model:{hash_obj.hexdigest()[:16]}"

    def _compute_config_hash(self) -> str:
        """Compute a hash of the configuration."""
        if self._config is None:
            return ""

        config_str = str(self._config.to_dict())
        hash_obj = hashlib.sha256(config_str.encode())
        return f"config:{hash_obj.hexdigest()[:16]}"

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
        """Get metadata about the model."""
        info = self._model_info.copy()

        # Add Modal client stats if available
        if self._client is not None:
            info["modal_stats"] = self._client.get_stats()

        return info

    def is_available(self) -> bool:
        """Check if Modal service is available.

        Returns:
            True if circuit breaker allows requests.
        """
        if self._client is None:
            return False
        return self._client.is_available()
