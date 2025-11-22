"""Column detection using projection profile analysis."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    DEFAULT_MIN_COLUMN_GAP,
    DEFAULT_MIN_COLUMN_WIDTH,
    VALLEY_THRESHOLD,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    ColumnDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def detect_column_count(
    image: np.ndarray,
    min_column_gap: int = DEFAULT_MIN_COLUMN_GAP,
    min_column_width: int = DEFAULT_MIN_COLUMN_WIDTH,
) -> ColumnDetectionResult:
    """Detect column layout using projection profile analysis + connected component clustering.

    Algorithm:
    1. Convert to grayscale and binarize
    2. Compute horizontal projection profile (sum pixels along vertical axis)
    3. Find valleys (low-density regions) indicating column gaps
    4. Cluster valleys into column boundaries
    5. Classify as single/multi/three_column/complex

    Args:
        image: Input image (BGR format, from OpenCV)
        min_column_gap: Minimum gap width between columns in pixels (default: 30)
        min_column_width: Minimum column width in pixels (default: 100)

    Returns:
        ColumnDetectionResult with column type and boundaries

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running column detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Binarize with Otsu's method (invert so text is white)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Compute horizontal projection profile (sum along vertical axis)
    h_projection = np.sum(binary, axis=0)  # Shape: (width,)

    # Normalize projection
    h_projection = h_projection / (binary.shape[0] * 255.0)  # Normalize to 0-1

    # Find valleys (potential column gaps) using threshold
    valleys = h_projection < VALLEY_THRESHOLD

    # Find continuous valley regions
    column_boundaries = []
    in_valley = False
    valley_start = 0

    for x in range(len(valleys)):
        if valleys[x] and not in_valley:
            # Start of valley
            in_valley = True
            valley_start = x
        elif not valleys[x] and in_valley:
            # End of valley
            valley_width = x - valley_start
            if valley_width >= min_column_gap:
                # Record valley center as column boundary
                boundary = valley_start + valley_width // 2
                column_boundaries.append(int(boundary))
            in_valley = False

    # Add edges as implicit boundaries
    all_boundaries = [0, *column_boundaries, binary.shape[1]]
    all_boundaries = sorted(set(all_boundaries))

    # Calculate column widths
    column_widths = []
    for i in range(len(all_boundaries) - 1):
        width = all_boundaries[i + 1] - all_boundaries[i]
        if width >= min_column_width:
            column_widths.append(width)

    num_columns = len(column_widths)

    # Classify column type
    if num_columns <= 1:
        column_type = "single_column"
        confidence = 0.9
    elif num_columns == 2:
        column_type = "multi_column"
        confidence = 0.85
    elif num_columns == 3:
        column_type = "three_column"
        confidence = 0.8
    else:
        column_type = "complex"
        confidence = 0.7

    logger.debug(
        "Column detection complete",
        column_type=column_type,
        num_columns=num_columns,
        confidence=confidence,
    )

    return ColumnDetectionResult(
        column_type=column_type,
        confidence=confidence,
        num_columns=num_columns,
        column_boundaries=column_boundaries,
    )
