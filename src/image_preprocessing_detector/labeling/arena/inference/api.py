"""API inference backend for the Arena.

This backend runs inference through external API providers
(OpenAI, Google Gemini, etc.) for black-box model evaluation.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
import time
from typing import TYPE_CHECKING, Any, ClassVar

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


class APIBackend(InferenceBackend):
    """Inference backend for API-based models.

    Supports running inference through external API providers:
    - OpenAI (GPT-4V, GPT-4o)
    - Google (Gemini Pro Vision)
    - Anthropic (Claude 3)

    API credentials are loaded from environment variables.

    Example:
        >>> spec = ModelSpec(
        ...     source=ModelSource.API,
        ...     id="gpt-4o",
        ...     revision="2024-08-06",
        ...     api_version="2024-08-06",
        ... )
        >>> backend = APIBackend(provider="openai")
        >>> backend.load(spec, InferenceConfig())
        >>> prediction = backend.predict(image)
    """

    SUPPORTED_PROVIDERS: ClassVar[set[str]] = {"openai", "google", "anthropic"}

    # Prompt template for DIQA scoring
    DIQA_PROMPT = """Analyze this document image and provide quality scores.

Rate the following aspects on a scale from 0.0 to 1.0:
1. Overall quality (0.0 = very poor, 1.0 = excellent)
2. Sharpness (0.0 = very blurry, 1.0 = perfectly sharp)
3. Color fidelity (0.0 = poor colors/grayscale, 1.0 = accurate colors)

Respond ONLY with three decimal numbers separated by commas, like: 0.85, 0.72, 0.90
No other text or explanation."""

    def __init__(self, provider: str = "openai") -> None:
        """Initialize the API backend.

        Args:
            provider: API provider name (openai, google, anthropic).
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            msg = f"Unsupported provider: {provider}. Must be one of {self.SUPPORTED_PROVIDERS}"
            raise ValueError(msg)

        self._provider = provider
        self._client: Any = None
        self._spec: ModelSpec | None = None
        self._config: InferenceConfig | None = None
        self._model_info: dict[str, Any] = {}
        self._total_tokens = 0
        self._total_cost = 0.0

    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Initialize API client with credentials.

        Args:
            spec: Model specification with API model ID.
            config: Inference configuration.

        Raises:
            ModelLoadError: If API client cannot be initialized.
        """
        try:
            logger.info(
                "initializing_api_client",
                provider=self._provider,
                model_id=spec.id,
            )

            if self._provider == "openai":
                self._init_openai_client(spec)
            elif self._provider == "google":
                self._init_google_client(spec)
            elif self._provider == "anthropic":
                self._init_anthropic_client(spec)

            self._spec = spec
            self._config = config
            self._model_info = {
                "provider": self._provider,
                "model_id": spec.id,
                "api_version": spec.api_version,
            }

            logger.info(
                "api_client_initialized",
                provider=self._provider,
                model_id=spec.id,
            )

        except Exception as e:
            msg = f"Failed to initialize API client: {e}"
            raise ModelLoadError(msg) from e

    def _init_openai_client(self, _spec: ModelSpec) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                msg = "OPENAI_API_KEY environment variable not set"
                raise ModelLoadError(msg)

            self._client = OpenAI(api_key=api_key)

        except ImportError as e:
            msg = "openai library required for OpenAI backend"
            raise ModelLoadError(msg) from e

    def _init_google_client(self, spec: ModelSpec) -> None:
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai

            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                msg = "GOOGLE_API_KEY environment variable not set"
                raise ModelLoadError(msg)

            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(spec.id)

        except ImportError as e:
            msg = "google-generativeai library required for Google backend"
            raise ModelLoadError(msg) from e

    def _init_anthropic_client(self, _spec: ModelSpec) -> None:
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                msg = "ANTHROPIC_API_KEY environment variable not set"
                raise ModelLoadError(msg) from None

            self._client = Anthropic(api_key=api_key)

        except ImportError as e:
            msg = "anthropic library required for Anthropic backend"
            raise ModelLoadError(msg) from e

    def unload(self) -> None:
        """Clean up API client."""
        self._client = None
        self._spec = None
        self._config = None
        self._model_info = {}

        logger.info(
            "api_client_unloaded",
            total_tokens=self._total_tokens,
            total_cost=f"${self._total_cost:.4f}",
        )

    def is_loaded(self) -> bool:
        """Check if API client is initialized."""
        return self._client is not None

    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run inference on a single image via API."""
        if not self.is_loaded():
            msg = "API client not initialized"
            raise ModelNotLoadedError(msg)

        results = self.predict_batch([image])
        return results[0]

    def predict_batch(
        self,
        images: list[NDArray[np.uint8] | Image.Image],
    ) -> list[DIQAPrediction]:
        """Run inference on a batch of images via API.

        Note: API calls are made sequentially to respect rate limits.
        """
        if not self.is_loaded():
            msg = "API client not initialized"
            raise ModelNotLoadedError(msg)

        predictions = []

        for idx, img in enumerate(images):
            try:
                start_time = time.perf_counter()
                prediction = self._call_api(img, idx)
                prediction.inference_time_ms = (time.perf_counter() - start_time) * 1000
                predictions.append(prediction)

                # Rate limiting: small delay between calls
                if idx < len(images) - 1:
                    time.sleep(0.1)

            except Exception as e:
                logger.warning(
                    "api_call_failed",
                    image_idx=idx,
                    error=str(e),
                )
                # Return placeholder on failure
                predictions.append(
                    DIQAPrediction(
                        overall=0.5,
                        sharpness=0.5,
                        color=0.5,
                        image_id=f"api_{idx}",
                        inference_time_ms=0.0,
                    )
                )

        return predictions

    def _call_api(
        self, image: NDArray[np.uint8] | Image.Image, idx: int
    ) -> DIQAPrediction:
        """Make API call for a single image."""
        from PIL import Image as PILImage

        # Convert to PIL and then to base64
        if isinstance(image, np.ndarray):
            pil_image = PILImage.fromarray(image)
        else:
            pil_image = image

        # Resize if too large
        max_size = 1024
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size)

        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode()

        # Call appropriate provider
        if self._provider == "openai":
            return self._call_openai(image_b64, idx)
        if self._provider == "google":
            return self._call_google(pil_image, idx)
        if self._provider == "anthropic":
            return self._call_anthropic(image_b64, idx)
        msg = f"Unknown provider: {self._provider}"
        raise InferenceError(msg)

    def _call_openai(self, image_b64: str, idx: int) -> DIQAPrediction:
        """Call OpenAI API."""
        assert self._spec is not None  # Guaranteed by is_loaded() check
        response = self._client.chat.completions.create(
            model=self._spec.id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.DIQA_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=50,
            temperature=self._config.temperature if self._config else 0.0,
        )

        # Track usage
        if response.usage:
            self._total_tokens += response.usage.total_tokens
            # Approximate cost calculation
            self._total_cost += response.usage.total_tokens * 0.00001

        # Parse response
        return self._parse_response(response.choices[0].message.content, idx)

    def _call_google(self, image: Image.Image, idx: int) -> DIQAPrediction:
        """Call Google Gemini API."""
        response = self._client.generate_content([self.DIQA_PROMPT, image])
        return self._parse_response(response.text, idx)

    def _call_anthropic(self, image_b64: str, idx: int) -> DIQAPrediction:
        """Call Anthropic API."""
        assert self._spec is not None  # Guaranteed by is_loaded() check
        response = self._client.messages.create(
            model=self._spec.id,
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": self.DIQA_PROMPT},
                    ],
                }
            ],
        )

        # Track usage
        if hasattr(response, "usage"):
            self._total_tokens += (
                response.usage.input_tokens + response.usage.output_tokens
            )

        return self._parse_response(response.content[0].text, idx)

    def _parse_response(self, response_text: str, idx: int) -> DIQAPrediction:
        """Parse API response into DIQAPrediction."""
        try:
            # Extract numbers from response
            import re

            numbers = re.findall(r"[\d.]+", response_text)

            if len(numbers) >= 3:
                overall = float(numbers[0])
                sharpness = float(numbers[1])
                color = float(numbers[2])
            else:
                logger.warning(
                    "api_response_parse_failed",
                    response=response_text[:100],
                )
                overall = sharpness = color = 0.5

            return DIQAPrediction(
                overall=float(np.clip(overall, 0, 1)),
                sharpness=float(np.clip(sharpness, 0, 1)),
                color=float(np.clip(color, 0, 1)),
                image_id=f"api_{idx}",
            )

        except Exception as e:
            logger.warning(
                "api_response_parse_error",
                error=str(e),
                response=response_text[:100],
            )
            return DIQAPrediction(
                overall=0.5,
                sharpness=0.5,
                color=0.5,
                image_id=f"api_{idx}",
            )

    def get_provenance(self) -> ProvenanceInfo:
        """Get provenance information for API model."""
        if not self.is_loaded() or self._spec is None:
            msg = "API client not initialized"
            raise ModelNotLoadedError(msg)

        # API models don't have checksums, but we record the config
        config_str = f"{self._provider}:{self._spec.id}:{self._spec.api_version}"
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]

        return ProvenanceInfo(
            model_checksum=f"api:{self._provider}",
            config_hash=f"sha256:{config_hash}",
        )

    def get_model_info(self) -> dict[str, Any]:
        """Get metadata about the API model."""
        info = self._model_info.copy()
        info["total_tokens"] = self._total_tokens
        info["total_cost_usd"] = self._total_cost
        return info

    def get_usage_stats(self) -> dict[str, Any]:
        """Get API usage statistics.

        Returns:
            Dictionary with token counts and cost estimates.
        """
        return {
            "provider": self._provider,
            "model_id": self._spec.id if self._spec else None,
            "total_tokens": self._total_tokens,
            "estimated_cost_usd": self._total_cost,
        }
