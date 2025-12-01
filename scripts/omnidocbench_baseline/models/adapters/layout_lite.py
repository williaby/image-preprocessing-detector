"""Layout-Lite adapter for layout detection benchmarking.

Uses classical CV heuristics for coarse layout detection.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from scripts.omnidocbench_baseline.models.base import (
    LayoutModel,
    ModelConfig,
    ModelPrediction,
)

logger = logging.getLogger(__name__)


class LayoutLiteAdapter(LayoutModel):
    """Adapter for layout-lite heuristic-based layout detection.

    Uses Project A's layout_lite module for column, table, and figure detection.
    """

    def __init__(self, config: ModelConfig):
        """Initialize adapter with configuration.

        Args:
            config: Model configuration from registry
        """
        super().__init__(config)
        self._analyzer = None

    def load(self) -> None:
        """Load/initialize the layout analyzer."""
        if self._is_loaded:
            return

        try:
            from image_preprocessing_detector.detection.layout_lite import (
                LayoutLiteAnalyzer,
            )

            self._analyzer = LayoutLiteAnalyzer()
            self._is_loaded = True
            logger.info(f"Loaded {self.config.name}")

        except ImportError as e:
            logger.error(f"Failed to load layout_lite modules: {e}")
            raise

    def predict_layout(self, image: np.ndarray) -> dict[str, Any]:
        """Predict layout attributes using heuristics.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict with layout_type and presence flags
        """
        if not self._is_loaded:
            self.load()

        # Run layout-lite analysis
        results = self._analyzer.analyze(image)

        # Map column detection to layout type
        column_result = results.get("column")
        if column_result:
            col_type = column_result.column_type
            if col_type == "single":
                layout_type = "single_column"
            elif col_type == "double":
                layout_type = "multi_column"
            elif col_type == "triple":
                layout_type = "three_column"
            else:
                layout_type = "complex"
        else:
            layout_type = "unknown"

        # Extract presence flags
        layout = {
            "layout_type": layout_type,
            "has_tables": (
                results.get("table").has_tables if results.get("table") else False
            ),
            "has_figures": (
                results.get("figure").has_figures if results.get("figure") else False
            ),
            "has_dense_math": False,  # Not implemented in layout-lite
            "has_handwriting": False,  # Not implemented in layout-lite
        }

        # Add detection counts for analysis
        if results.get("table"):
            layout["_table_count"] = results["table"].table_count
        if results.get("figure"):
            layout["_figure_count"] = results["figure"].figure_count

        return layout

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

        # Separate internal fields
        scores = {}
        labels = {}

        for key, value in layout.items():
            if key.startswith("_"):
                scores[key[1:]] = float(value)  # Remove underscore prefix
            elif isinstance(value, bool):
                labels[key] = value
            elif key == "layout_type":
                labels[key] = value

        return ModelPrediction(
            scores=scores,
            labels=labels,
            raw_output=layout,
            inference_time_ms=elapsed,
        )
