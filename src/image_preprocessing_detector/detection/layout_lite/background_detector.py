"""Colorful background detection using color histogram and saturation analysis."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    DEFAULT_MIN_AVG_SATURATION,
    DEFAULT_MIN_UNIQUE_COLORS,
    HIST_H_BINS,
    HIST_S_BINS,
    HIST_V_BINS,
    SIGNIFICANT_COLOR_THRESHOLD,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    ColorfulBackgroundResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def detect_colorful_background(
    image: np.ndarray,
    min_unique_colors: int = DEFAULT_MIN_UNIQUE_COLORS,
    min_avg_saturation: float = DEFAULT_MIN_AVG_SATURATION,
) -> ColorfulBackgroundResult:
    """Detect colorful backgrounds using color histogram diversity + saturation analysis.

    Algorithm:
    1. Convert to HSV color space
    2. Calculate unique colors (histogram bins with significant counts)
    3. Calculate average saturation
    4. Threshold: unique_colors >100 AND avg_saturation >0.3

    Args:
        image: Input image (BGR format, from OpenCV)
        min_unique_colors: Minimum unique colors for colorful background (default: 100)
        min_avg_saturation: Minimum average saturation (default: 0.3)

    Returns:
        ColorfulBackgroundResult with detection decision and metrics

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running colorful background detection", image_shape=image.shape)

    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Calculate average saturation
    saturation_channel = hsv[:, :, 1]
    avg_saturation = np.mean(saturation_channel) / 255.0  # Normalize to 0-1

    # Calculate unique colors using 3D histogram
    # Reduce resolution to count "perceptually unique" colors
    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [HIST_H_BINS, HIST_S_BINS, HIST_V_BINS],
        [0, 180, 0, 256, 0, 256],
    )

    # Count bins with significant pixel counts (>0.1% of total pixels)
    total_pixels = image.shape[0] * image.shape[1]
    significant_threshold = total_pixels * SIGNIFICANT_COLOR_THRESHOLD

    unique_colors = np.count_nonzero(hist > significant_threshold)

    # Detection logic: diverse colors AND high saturation
    colorful_background = (
        unique_colors >= min_unique_colors and avg_saturation >= min_avg_saturation
    )

    # Confidence based on both metrics
    confidence = (
        min(0.95, (unique_colors / min_unique_colors + avg_saturation) / 2.0)
        if colorful_background
        else 0.85
    )

    logger.debug(
        "Colorful background detection complete",
        colorful_background=colorful_background,
        unique_colors=unique_colors,
        avg_saturation=avg_saturation,
    )

    return ColorfulBackgroundResult(
        colorful_background=colorful_background,
        confidence=confidence,
        unique_colors=unique_colors,
        avg_saturation=avg_saturation,
    )
