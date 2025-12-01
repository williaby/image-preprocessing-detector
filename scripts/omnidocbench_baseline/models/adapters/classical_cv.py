"""Classical Computer Vision adapter for IQA benchmarking.

Uses OpenCV-based heuristics for image quality assessment.
"""

import logging
import sys
import time
from pathlib import Path

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from scripts.omnidocbench_baseline.models.base import (
    IQAModel,
    ModelConfig,
    ModelPrediction,
    PageAttributeModel,
)

logger = logging.getLogger(__name__)


class ClassicalCVAdapter(PageAttributeModel, IQAModel):
    """Adapter for classical CV-based IQA and page attribute detection.

    Uses the existing layout_lite detectors from Project A.
    """

    def __init__(self, config: ModelConfig):
        """Initialize adapter with configuration.

        Args:
            config: Model configuration from registry
        """
        super().__init__(config)
        self._analyzer = None

    def load(self) -> None:
        """Load/initialize the analyzers."""
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
            logger.error(f"Failed to load classical CV modules: {e}")
            raise

    def predict_quality_scores(self, image: np.ndarray) -> dict[str, float]:
        """Predict IQA scores using classical CV methods.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict of quality scores
        """
        if not self._is_loaded:
            self.load()

        scores = {}

        # Blur detection using Laplacian variance
        try:
            import cv2

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Normalize to 0-1 (higher = more blurry)
            # Typical sharp images: var > 500, blurry: var < 100
            blur_score = max(0.0, min(1.0, 1.0 - (laplacian_var / 500.0)))
            scores["blur_score"] = blur_score

        except Exception as e:
            logger.warning(f"Blur detection failed: {e}")
            scores["blur_score"] = 0.5

        # Overall quality (inverse of blur for now)
        scores["overall_quality"] = 1.0 - scores.get("blur_score", 0.5)

        return scores

    def predict_attributes(self, image: np.ndarray) -> dict[str, bool]:
        """Predict page attributes using layout_lite analyzers.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict of attribute boolean values
        """
        if not self._is_loaded:
            self.load()

        # Run layout-lite analysis
        results = self._analyzer.analyze(image)

        attributes = {
            "fuzzy_scan": (
                results.get("fuzzy_scan").fuzzy_scan
                if results.get("fuzzy_scan")
                else False
            ),
            "watermark": (
                results.get("watermark").watermark
                if results.get("watermark")
                else False
            ),
            "colorful_background": (
                results.get("colorful_background").colorful_background
                if results.get("colorful_background")
                else False
            ),
        }

        return attributes

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run full prediction combining IQA and page attributes.

        Args:
            image: Input image (BGR format)

        Returns:
            ModelPrediction with scores and labels
        """
        start = time.perf_counter()

        # Get quality scores
        scores = self.predict_quality_scores(image)

        # Get page attributes
        attributes = self.predict_attributes(image)

        elapsed = (time.perf_counter() - start) * 1000

        return ModelPrediction(
            scores=scores,
            labels=attributes,
            confidences={
                # Use detection confidences if available
                "fuzzy_scan": 0.8 if attributes["fuzzy_scan"] else 0.2,
                "watermark": 0.8 if attributes["watermark"] else 0.2,
                "colorful_background": (
                    0.8 if attributes["colorful_background"] else 0.2
                ),
            },
            inference_time_ms=elapsed,
        )
