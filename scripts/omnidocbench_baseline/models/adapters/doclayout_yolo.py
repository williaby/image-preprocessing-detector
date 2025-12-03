"""DocLayout-YOLO adapter for layout detection benchmarking.

Placeholder for DocLayout-YOLO integration (Phase 6).
"""

import logging
import time
from typing import Any

import numpy as np

from scripts.omnidocbench_baseline.models.base import (
    LayoutModel,
    ModelConfig,
    ModelPrediction,
)

logger = logging.getLogger(__name__)


class DocLayoutYOLOAdapter(LayoutModel):
    """Adapter for DocLayout-YOLO layout detection.

    Status: Placeholder - Full implementation planned for Phase 6.
    """

    def __init__(self, config: ModelConfig):
        """Initialize adapter with configuration.

        Args:
            config: Model configuration from registry
        """
        super().__init__(config)
        self._model = None

    def load(self) -> None:
        """Load DocLayout-YOLO model."""
        if self._is_loaded:
            return

        logger.warning(
            f"{self.config.name} is not yet implemented. Using placeholder predictions."
        )
        self._is_loaded = True

    def predict_layout(self, image: np.ndarray) -> dict[str, Any]:
        """Predict layout using DocLayout-YOLO.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict with layout predictions
        """
        if not self._is_loaded:
            self.load()

        # TODO: Implement actual DocLayout-YOLO inference
        # For now, return placeholder values
        logger.debug("DocLayout-YOLO returning placeholder predictions")

        return {
            "layout_type": "unknown",
            "has_tables": False,
            "has_figures": False,
            "has_dense_math": False,
            "has_handwriting": False,
            "_placeholder": True,
        }

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run layout prediction.

        Args:
            image: Input image (BGR format)

        Returns:
            ModelPrediction with layout attributes
        """
        start = time.perf_counter()

        layout = self.predict_layout(image)
        elapsed = (time.perf_counter() - start) * 1000

        labels = {
            k: v
            for k, v in layout.items()
            if isinstance(v, bool | str) and not k.startswith("_")
        }

        return ModelPrediction(
            labels=labels,
            raw_output=layout,
            inference_time_ms=elapsed,
        )
