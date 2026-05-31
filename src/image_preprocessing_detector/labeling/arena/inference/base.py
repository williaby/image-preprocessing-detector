"""Base inference backend interface.

This module defines the abstract interface that all inference backends
must implement for consistent model evaluation in the Arena.
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from PIL import Image

    from image_preprocessing_detector.labeling.arena.schemas import (
        DIQAPrediction,
        ProvenanceInfo,
    )
    from image_preprocessing_detector.labeling.model_spec import ModelSpec


@dataclass
class InferenceConfig:
    """Configuration for inference execution.

    Attributes:
        batch_size (int): Number of images to process at once.
        device (str): Device to run inference on ("cpu", "cuda", "cuda:0").
        seed (int): Random seed for reproducibility.
        max_length (int): Maximum sequence length for text generation.
        temperature (float): Sampling temperature (for API models).
        deterministic (bool): Enforce deterministic execution.
        timeout_seconds (int): Timeout for inference operations.
        extra_params (dict[str, Any]): Additional backend-specific parameters.
    """

    batch_size: int = 8
    device: str = "cuda"
    seed: int = 42
    max_length: int = 512
    temperature: float = 0.0
    deterministic: bool = True
    timeout_seconds: int = 300
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "batch_size": self.batch_size,
            "device": self.device,
            "seed": self.seed,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "deterministic": self.deterministic,
            "timeout_seconds": self.timeout_seconds,
            "extra_params": self.extra_params,
        }


class InferenceBackend(ABC):
    """Abstract base class for model inference backends.

    All inference backends (HuggingFace, local, API) must implement
    this interface to enable plug-and-play model evaluation.

    The Arena uses this interface to:
    1. Load models from different sources
    2. Run deterministic inference
    3. Collect provenance information

    Example:
        >>> backend = HuggingFaceBackend()
        >>> backend.load(model_spec, config)
        >>> predictions = backend.predict_batch(images)
        >>> provenance = backend.get_provenance()
    """

    @abstractmethod
    def load(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load the model from the specification.

        Args:
            spec (ModelSpec): Model specification with source and identifiers.
            config (InferenceConfig): Inference configuration.

        Raises:
            ModelLoadError: If model cannot be loaded.
            IncompatibleModelError: If model is not compatible.
        """

    @abstractmethod
    def unload(self) -> None:
        """Unload the model and free resources.

        Should be called after inference is complete to free
        GPU memory and other resources.
        """

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded.

        Returns:
            bool:             True if model is loaded and ready for inference.
        """

    @abstractmethod
    def predict(self, image: NDArray[np.uint8] | Image.Image) -> DIQAPrediction:
        """Run inference on a single image.

        Args:
            image (NDArray[np.uint8] | Image.Image): Input image as numpy array (H, W, C) or PIL Image.

        Returns:
            DIQAPrediction:             DIQAPrediction with quality scores.

        Raises:
            InferenceError: If inference fails.
            ModelNotLoadedError: If model is not loaded.
        """

    @abstractmethod
    def predict_batch(
        self,
        images: list[NDArray[np.uint8] | Image.Image],
    ) -> list[DIQAPrediction]:
        """Run inference on a batch of images.

        Args:
            images (list[NDArray[np.uint8] | Image.Image]): List of input images.

        Returns:
            list[DIQAPrediction]:             List of DIQAPrediction objects.

        Raises:
            InferenceError: If inference fails.
            ModelNotLoadedError: If model is not loaded.
        """

    @abstractmethod
    def get_provenance(self) -> ProvenanceInfo:
        """Get provenance information for the loaded model.

        Returns:
            ProvenanceInfo:             ProvenanceInfo with checksums and metadata.

        Raises:
            ModelNotLoadedError: If model is not loaded.
        """

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get metadata about the loaded model.

        Returns:
            dict[str, Any]:             Dictionary with model information (name, size, etc.)
        """

    def warmup(self, num_iterations: int = 3, seed: int | None = None) -> None:
        """Run warmup inference to prime the model.

        Args:
            num_iterations (int): Number of warmup iterations.
            seed (int | None): Optional seed for reproducible dummy image generation.
        """
        if not self.is_loaded():
            return

        # Create dummy image for warmup
        rng = np.random.default_rng(seed)
        dummy_image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)

        for _ in range(num_iterations):
            with contextlib.suppress(Exception):
                _ = self.predict(dummy_image)


class ModelLoadError(Exception):
    """Raised when a model cannot be loaded."""


class IncompatibleModelError(Exception):
    """Raised when a model is not compatible with the backend."""


class InferenceError(Exception):
    """Raised when inference fails."""


class ModelNotLoadedError(Exception):
    """Raised when attempting inference without a loaded model."""


def create_backend(source: str, **kwargs: Any) -> InferenceBackend:
    """Factory function to create an inference backend.

    Args:
        source (str): Backend type ("huggingface", "local", "api")
        **kwargs (Any): Additional arguments passed to backend constructor.

    Returns:
        InferenceBackend:         Appropriate InferenceBackend instance.

    Raises:
        ValueError: If source is not recognized.

    Example:
        >>> backend = create_backend("huggingface")
        >>> backend = create_backend("api", provider="openai")
    """
    from image_preprocessing_detector.labeling.model_spec import ModelSource

    if source == ModelSource.HUGGINGFACE.value or source == "huggingface":
        from image_preprocessing_detector.labeling.arena.inference.huggingface import (
            HuggingFaceBackend,
        )

        return HuggingFaceBackend(**kwargs)

    if source == ModelSource.LOCAL.value or source == "local":
        from image_preprocessing_detector.labeling.arena.inference.local import (
            LocalBackend,
        )

        return LocalBackend(**kwargs)

    if source == ModelSource.API.value or source == "api":
        from image_preprocessing_detector.labeling.arena.inference.api import (
            APIBackend,
        )

        return APIBackend(**kwargs)

    if source == "modal":
        from image_preprocessing_detector.labeling.arena.inference.modal import (
            ModalBackend,
        )

        return ModalBackend(**kwargs)

    if source == "regression":
        from image_preprocessing_detector.labeling.arena.inference.regression import (
            RegressionBackend,
        )

        return RegressionBackend(**kwargs)

    msg = f"Unknown backend source: {source}. Must be 'huggingface', 'local', 'api', 'modal', or 'regression'"
    raise ValueError(msg)
