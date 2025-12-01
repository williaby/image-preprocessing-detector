"""Language detection adapter for benchmarking.

Placeholder for fastText/py3langid integration (Phase 4).
"""

import logging
import time

import numpy as np

from scripts.omnidocbench_baseline.models.base import (
    BaseModel,
    ModelConfig,
    ModelPrediction,
)

logger = logging.getLogger(__name__)


class LanguageAdapter(BaseModel):
    """Adapter for language detection models.

    Status: Placeholder - Full implementation planned for Phase 4.
    """

    def __init__(self, config: ModelConfig):
        """Initialize adapter with configuration.

        Args:
            config: Model configuration from registry
        """
        super().__init__(config)
        self._model = None

    def load(self) -> None:
        """Load language detection model."""
        if self._is_loaded:
            return

        logger.warning(
            f"{self.config.name} is not yet implemented. Using placeholder predictions."
        )
        self._is_loaded = True

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Predict language from image.

        Note: Language detection typically requires OCR output,
        not raw images. This is a placeholder for integration.

        Args:
            image: Input image (BGR format)

        Returns:
            ModelPrediction with language predictions
        """
        if not self._is_loaded:
            self.load()

        start = time.perf_counter()

        # TODO: Implement actual language detection
        # This would typically:
        # 1. Run OCR to get text
        # 2. Run language detection on text
        logger.debug("Language adapter returning placeholder predictions")

        elapsed = (time.perf_counter() - start) * 1000

        return ModelPrediction(
            labels={
                "language": "unknown",
                "has_non_latin": False,
            },
            scores={
                "language_confidence": 0.0,
            },
            raw_output={"_placeholder": True},
            inference_time_ms=elapsed,
        )
