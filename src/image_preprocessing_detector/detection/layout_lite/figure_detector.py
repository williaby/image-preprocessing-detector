"""Figure detection using connected components with low text density."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    DEFAULT_MAX_TEXT_DENSITY,
    DEFAULT_MIN_FIGURE_AREA_RATIO,
    GRADIENT_THRESHOLD,
    MORPH_KERNEL_SIZE,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    FigureDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def detect_figures(
    image: np.ndarray,
    min_figure_area_ratio: float = DEFAULT_MIN_FIGURE_AREA_RATIO,
    max_text_density: float = DEFAULT_MAX_TEXT_DENSITY,
) -> FigureDetectionResult:
    """Detect figures using large connected components with low text density.

    Algorithm:
    1. Convert to grayscale and binarize
    2. Find connected components
    3. Filter components by area (>20% of page area)
    4. Calculate text density within each component
    5. Classify as figure if text density <5%

    Args:
        image: Input image (BGR format, from OpenCV)
        min_figure_area_ratio: Minimum area ratio for figure (default: 0.20 = 20%)
        max_text_density: Maximum text density for figure (default: 0.05 = 5%)

    Returns:
        FigureDetectionResult with detection decision and figure count

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running figure detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Binarize with Otsu's method
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Calculate page area
    page_area = image.shape[0] * image.shape[1]
    min_area = int(page_area * min_figure_area_ratio)

    # Find connected components
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    figure_count = 0
    largest_figure_area = 0

    # Analyze each component (skip background label 0)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]

        # Check if component is large enough
        if area < min_area:
            continue

        # Extract component region
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        # Calculate text density in this region
        # Use morphological gradient to detect text strokes
        region = gray[y : y + h, x : x + w]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_SIZE)
        gradient = cv2.morphologyEx(region, cv2.MORPH_GRADIENT, kernel)

        text_pixels = np.count_nonzero(gradient > GRADIENT_THRESHOLD)
        region_pixels = region.size
        text_density = text_pixels / region_pixels if region_pixels > 0 else 1.0

        # Classify as figure if low text density
        if text_density < max_text_density:
            figure_count += 1
            largest_figure_area = max(largest_figure_area, area)

    has_figures = figure_count > 0
    largest_area_ratio = largest_figure_area / page_area if page_area > 0 else 0.0

    # Confidence based on number of figures and area
    confidence = min(0.9, 0.6 + (figure_count * 0.1))

    logger.debug(
        "Figure detection complete",
        has_figures=has_figures,
        figure_count=figure_count,
        largest_area_ratio=largest_area_ratio,
    )

    return FigureDetectionResult(
        has_figures=has_figures,
        confidence=confidence,
        num_figures=figure_count,
        largest_figure_area_ratio=largest_area_ratio,
    )
