"""SigLIP-based quality score prediction provider.

This module provides a SigLIP-based enrichment provider for document image
quality assessment. Uses a fine-tuned SigLIP model for MOS (Mean Opinion Score)
prediction with batch inference support for GPU efficiency.

The SigLIP model is designed for document quality assessment, predicting
quality scores that correlate with human perception of image quality issues
like blur, noise, contrast problems, and document degradation.

Classes:
    SigLIPProvider: Quality score prediction with batch processing

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.siglip import (
    ...     SigLIPProvider,
    ... )
    >>>
    >>> provider = SigLIPProvider(
    ...     model_path="checkpoints/siglip2-iqa",
    ...     batch_size=32,
    ... )
    >>>
    >>> if provider.is_available():
    ...     enrichment = provider.enrich(Path("document.jpg"))
    ...     print(f"Quality score: {enrichment.llm_predicted_mos}")
    ...     print(f"Confidence: {enrichment.llm_prediction_confidence}")
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "provider"
__l4_task__ = "iqa"
__l4_workstream__ = "WS3"
__l4_provides__ = "iqa_scores, quality_vector"


import logging
import warnings
from pathlib import Path
from typing import Any

from ...schemas.enrichment import EnrichmentData
from ..errors import InferenceError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class SigLIPProvider:
    """SigLIP provider for document image quality assessment.

    Wraps SigLIP model inference for document quality prediction.
    Provides batch processing for GPU efficiency and availability
    checking for robust operation.

    Quality scores are predicted in the MOS (Mean Opinion Score) range
    of 1.0-5.0, where:
    - 5.0 = Excellent quality, no visible degradation
    - 4.0 = Good quality, minor degradation
    - 3.0 = Fair quality, noticeable degradation
    - 2.0 = Poor quality, significant degradation
    - 1.0 = Bad quality, severe degradation

    Attributes:
        model_path: Path to SigLIP model checkpoint (HuggingFace format)
        batch_size: Batch size for inference
        device: Device to use ("cuda", "cpu", or None for auto-detect)
        min_confidence_threshold: Minimum confidence for predictions

    Design Notes:
        - Implements both EnrichmentProvider and QualityScoreProvider protocols
        - Lazy-loads model on first use to avoid startup overhead
        - Auto-detects GPU availability and falls back to CPU with warning
        - Uses transformers library for model loading and inference
    """

    # Model configuration constants
    DEFAULT_BATCH_SIZE: int = 32
    DEFAULT_MIN_CONFIDENCE: float = 0.5
    MODEL_NAME: str = "siglip_iqa"

    def __init__(
        self,
        model_path: Path | str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        device: str | None = None,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
    ):
        """Initialize SigLIPProvider.

        Args:
            model_path: Path to SigLIP model checkpoint (HuggingFace format).
                        Should contain config.json, model.safetensors, etc.
            batch_size: Batch size for inference (default: 32)
            device: Device to use (None for auto-detect, "cuda" or "cpu")
            min_confidence_threshold: Minimum confidence threshold (default: 0.5)
        """
        self.model_path = Path(model_path) if model_path else None
        self.batch_size = batch_size
        self._requested_device = device
        self.min_confidence_threshold = min_confidence_threshold

        # Lazy-loaded model components
        self._model: Any | None = None
        self._processor: Any | None = None

        # Cached state
        self._device: str | None = None
        self._device_available: bool | None = None

    @property
    def name(self) -> str:
        """Provider name for logging and provenance."""
        return self.MODEL_NAME

    @property
    def tier(self) -> str:
        """Enrichment tier (tier_2_model for ML inference)."""
        return "tier_2_model"

    @property
    def device(self) -> str:
        """Get device for inference (auto-detect if not specified).

        Auto-detection priority:
        1. Explicit device from constructor
        2. CUDA if available
        3. CPU with warning (SigLIP is slow on CPU)

        Returns:
            Device string ("cuda" or "cpu")
        """
        if self._device is not None:
            return self._device

        if self._requested_device is not None:
            self._device = self._requested_device
            return self._device

        # Auto-detect device
        try:
            import torch

            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info("SigLIP auto-detected CUDA device")
            else:
                self._device = "cpu"
                warnings.warn(
                    "SigLIP running on CPU - inference will be slow. "
                    "Consider using a GPU for production workloads.",
                    UserWarning,
                    stacklevel=2,
                )
                logger.warning("SigLIP falling back to CPU (no CUDA available)")
        except ImportError:
            self._device = "cpu"
            logger.warning("torch not installed, defaulting to CPU")

        return self._device

    def is_available(self) -> bool:
        """Check if SigLIP model is available.

        Checks:
        - Model checkpoint directory exists
        - Model contains required files (config.json, model.*)
        - Required dependencies installed (transformers, torch)
        - GPU available if device is "cuda"

        Returns:
            True if provider can be used
        """
        if self._device_available is not None:
            return self._device_available

        # Check model path exists
        if self.model_path is None:
            logger.debug("SigLIP model path not configured")
            self._device_available = False
            return False

        if not self.model_path.exists():
            logger.debug(f"SigLIP model not found at {self.model_path}")
            self._device_available = False
            return False

        # Check for required model files
        if self.model_path.is_dir():
            # HuggingFace format - check for config.json
            config_file = self.model_path / "config.json"
            if not config_file.exists():
                logger.debug(
                    f"SigLIP model config not found at {config_file}. "
                    "Expected HuggingFace format with config.json"
                )
                self._device_available = False
                return False

        # Check dependencies
        try:
            import torch
        except ImportError:
            logger.debug("torch not installed")
            self._device_available = False
            return False

        try:
            __import__("transformers")  # Check if transformers is installed
        except ImportError:
            logger.debug("transformers not installed")
            self._device_available = False
            return False

        # Check GPU if CUDA device requested
        if self._requested_device == "cuda" or (
            self._requested_device is None and self.device == "cuda"
        ):
            try:
                import torch

                if not torch.cuda.is_available():
                    logger.debug("CUDA requested but not available")
                    # Note: We don't fail here - we'll fall back to CPU
                    # Only fail if explicitly requested CUDA
                    if self._requested_device == "cuda":
                        self._device_available = False
                        return False
            except ImportError:
                logger.debug("torch not installed for CUDA check")
                if self._requested_device == "cuda":
                    self._device_available = False
                    return False

        self._device_available = True
        return True

    def supports(self, _image_path: Path) -> bool:
        """Check if this image should be processed.

        Currently processes all images. Could be extended to skip
        images that already have quality scores above a threshold.

        Args:
            _image_path: Path to image file (unused)

        Returns:
            True (processes all images by default)
        """
        return True

    def _ensure_loaded(self) -> None:
        """Lazy-load SigLIP model on first use.

        Uses HuggingFace transformers for model loading. The model
        is loaded in eval mode and moved to the target device.

        Raises:
            ProviderUnavailableError: If model cannot be loaded
        """
        if self._model is not None:
            return

        if not self.is_available():
            raise ProviderUnavailableError(
                self.name, f"Model not found at {self.model_path}"
            )

        try:
            from transformers import AutoModel, AutoProcessor

            logger.info(f"Loading SigLIP model from {self.model_path}")

            # Load processor and model (from LOCAL path, not remote download)
            self._processor = AutoProcessor.from_pretrained(  # nosec B615
                str(self.model_path),
                trust_remote_code=True,
            )
            model = AutoModel.from_pretrained(  # nosec B615
                str(self.model_path),
                trust_remote_code=True,
            )

            # Move to device and set eval mode
            model = model.to(self.device)
            model.eval()
            self._model = model

            logger.info(f"SigLIP model loaded on {self.device}")

        except ImportError as e:
            raise ProviderUnavailableError(self.name, f"Missing dependency: {e}") from e
        except Exception as e:
            raise ProviderUnavailableError(
                self.name, f"Model loading failed: {e}"
            ) from e

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image with quality score prediction.

        Args:
            image_path: Path to image file

        Returns:
            EnrichmentData with LLM quality scores populated:
            - llm_predicted_mos: MOS score (1.0-5.0)
            - llm_predicted_normalized: Normalized score (0.0-1.0)
            - llm_prediction_confidence: Prediction confidence (0.0-1.0)
            - llm_model_name: "siglip_iqa"

        Raises:
            InferenceError: If inference fails
            ProviderUnavailableError: If provider is not available
        """
        return self.enrich_batch([image_path])[0]

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images with batch inference.

        Batch processing provides significant performance benefits:
        - GPU batch inference is much faster than sequential
        - Model loading overhead is amortized across batch
        - Memory usage is more efficient

        Args:
            image_paths: List of image file paths

        Returns:
            List of EnrichmentData in same order as image_paths

        Raises:
            InferenceError: If batch inference fails
            ProviderUnavailableError: If provider is not available
        """
        # Short-circuit before loading model for empty batches
        if not image_paths:
            return []

        self._ensure_loaded()

        results: list[EnrichmentData] = []

        # Process in batches
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i : i + self.batch_size]

            try:
                batch_results = self._process_batch(batch_paths)
                results.extend(batch_results)
            except Exception as e:
                # On batch failure, re-raise as InferenceError
                logger.exception("SigLIP batch inference failed")
                raise InferenceError(self.name, len(batch_paths), e) from e

        return results

    def _process_batch(self, paths: list[Path]) -> list[EnrichmentData]:
        """Process a single batch through SigLIP.

        Args:
            paths: List of image paths in this batch

        Returns:
            List of EnrichmentData with quality scores
        """
        import torch
        from PIL import Image

        # Load and validate images
        images = []
        valid_indices = []

        for idx, path in enumerate(paths):
            try:
                img = Image.open(path).convert("RGB")
                images.append(img)
                valid_indices.append(idx)
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
                # Create placeholder for failed images
                images.append(Image.new("RGB", (224, 224), color=(128, 128, 128)))
                valid_indices.append(idx)

        # Preprocess images
        assert self._processor is not None
        inputs = self._processor(
            images=images,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run inference
        assert self._model is not None
        with torch.no_grad():
            outputs = self._model(**inputs)

            # Extract quality scores
            # Assumes model outputs logits that can be converted to scores
            # The exact output format depends on how the model was trained
            if hasattr(outputs, "logits"):
                logits = outputs.logits
            elif hasattr(outputs, "pooler_output"):
                # Use pooler output if no logits (e.g., for regression head)
                logits = outputs.pooler_output
            else:
                # Fallback to last hidden state mean pooling
                logits = outputs.last_hidden_state.mean(dim=1)

            # Convert to quality scores
            # For regression model: direct output is MOS
            # For classification: use softmax and weighted sum
            if logits.shape[-1] == 1:
                # Regression: direct MOS prediction
                mos_scores = logits.squeeze(-1)
                confidences = torch.ones_like(mos_scores)
            elif logits.shape[-1] == 5:
                # Classification: 5 quality classes (1-5)
                probs = torch.softmax(logits, dim=-1)
                # Weighted sum for MOS
                quality_levels = torch.arange(
                    1, 6, dtype=torch.float32, device=self.device
                )
                mos_scores = (probs * quality_levels).sum(dim=-1)
                # Confidence is max probability
                confidences = probs.max(dim=-1).values
            else:
                # Generic: normalize to 1-5 range
                mos_scores = torch.sigmoid(logits.mean(dim=-1)) * 4 + 1
                confidences = torch.ones(len(paths), device=self.device) * 0.5

        # Build results
        results: list[EnrichmentData] = []
        for mos, conf in zip(
            mos_scores.cpu().numpy(), confidences.cpu().numpy(), strict=True
        ):
            enrichment = EnrichmentData()

            # Clamp MOS to valid range
            mos_value = float(max(1.0, min(5.0, mos)))
            conf_value = float(max(0.0, min(1.0, conf)))

            # Set quality scores
            enrichment.llm_predicted_mos = mos_value
            enrichment.llm_predicted_normalized = (
                mos_value - 1.0
            ) / 4.0  # Map 1-5 to 0-1
            enrichment.llm_prediction_confidence = conf_value
            enrichment.llm_model_name = self.MODEL_NAME

            results.append(enrichment)

        return results

    def unload(self) -> None:
        """Unload model to free GPU memory.

        Call this when done with the provider to release GPU resources.
        The model will be reloaded on next inference call.
        """
        if self._model is not None:
            del self._model
            self._model = None

        if self._processor is not None:
            del self._processor
            self._processor = None

        # Clear CUDA cache if available
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass  # torch not installed; CUDA cache clearing not needed

        logger.info("SigLIP model unloaded")


__all__ = ["SigLIPProvider"]
