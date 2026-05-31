"""Layout-Lite analyzer combining all detection functions."""

from typing import Any

import numpy as np

from image_preprocessing_detector.detection.layout_lite.background_detector import (
    detect_colorful_background,
)
from image_preprocessing_detector.detection.layout_lite.column_detector import (
    detect_column_count,
)
from image_preprocessing_detector.detection.layout_lite.figure_detector import (
    detect_figures,
)
from image_preprocessing_detector.detection.layout_lite.fuzzy_scan_detector import (
    detect_fuzzy_scan,
)
from image_preprocessing_detector.detection.layout_lite.table_detector import (
    detect_tables,
)
from image_preprocessing_detector.detection.layout_lite.watermark_detector import (
    detect_watermark,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class LayoutLiteAnalyzer:
    """Combines all layout-lite detection functions into unified analyzer.

    Runs all heuristic-based detections and populates PageLayoutSummary model.
    Optimized for speed (< 100ms per page on CPU).

    Args:
        enable_column_detection (bool): Enable column detection (default: True)
        enable_table_detection (bool): Enable table detection (default: True)
        enable_figure_detection (bool): Enable figure detection (default: True)
        enable_fuzzy_scan_detection (bool): Enable fuzzy scan detection (default: True)
        enable_watermark_detection (bool): Enable watermark detection (default: True)
        enable_colorful_bg_detection (bool): Enable colorful background detection (default: True)
    """

    def __init__(
        self,
        enable_column_detection: bool = True,
        enable_table_detection: bool = True,
        enable_figure_detection: bool = True,
        enable_fuzzy_scan_detection: bool = True,
        enable_watermark_detection: bool = True,
        enable_colorful_bg_detection: bool = True,
    ) -> None:
        self.enable_column_detection = enable_column_detection
        self.enable_table_detection = enable_table_detection
        self.enable_figure_detection = enable_figure_detection
        self.enable_fuzzy_scan_detection = enable_fuzzy_scan_detection
        self.enable_watermark_detection = enable_watermark_detection
        self.enable_colorful_bg_detection = enable_colorful_bg_detection

        logger.info(
            "LayoutLiteAnalyzer initialized",
            column=enable_column_detection,
            table=enable_table_detection,
            figure=enable_figure_detection,
            fuzzy=enable_fuzzy_scan_detection,
            watermark=enable_watermark_detection,
            colorful_bg=enable_colorful_bg_detection,
        )

    def analyze(self, image: np.ndarray) -> dict[str, Any]:
        """Run all enabled detections on an image.

        Args:
            image (np.ndarray): Input image (BGR format, from OpenCV)

        Returns:
            dict[str, Any]: Dictionary with all detection results

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Starting layout-lite analysis", image_shape=image.shape)

        results: dict[str, Any] = {}

        # Run column detection
        if self.enable_column_detection:
            results["column"] = detect_column_count(image)

        # Run table detection
        if self.enable_table_detection:
            results["table"] = detect_tables(image)

        # Run figure detection
        if self.enable_figure_detection:
            results["figure"] = detect_figures(image)

        # Run fuzzy scan detection
        if self.enable_fuzzy_scan_detection:
            results["fuzzy_scan"] = detect_fuzzy_scan(image)

        # Run watermark detection
        if self.enable_watermark_detection:
            results["watermark"] = detect_watermark(image)

        # Run colorful background detection
        if self.enable_colorful_bg_detection:
            results["colorful_background"] = detect_colorful_background(image)

        logger.info("Layout-lite analysis complete", num_detections=len(results))

        return results


def analyze_layout(image: np.ndarray) -> dict[str, Any]:
    """Convenience function for layout analysis with default settings.

    Args:
        image (np.ndarray): Input image (BGR format, from OpenCV)

    Returns:
        dict[str, Any]: Dictionary with all detection results

    Example:
        >>> import cv2
        >>> img = cv2.imread("document.jpg")
        >>> results = analyze_layout(img)
        >>> print(f"Column type: {results['column'].column_type}")
        >>> print(f"Has tables: {results['table'].has_tables}")
    """
    analyzer = LayoutLiteAnalyzer()
    return analyzer.analyze(image)
