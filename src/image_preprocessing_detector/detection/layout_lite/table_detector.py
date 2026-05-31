"""Table detection using Hough line detection and grid pattern analysis."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    ANGLE_TOLERANCE,
    CANNY_HIGH_THRESHOLD,
    CANNY_LOW_THRESHOLD,
    DEFAULT_GRID_INTERSECTION_THRESHOLD,
    DEFAULT_MIN_HORIZONTAL_LINES,
    DEFAULT_MIN_VERTICAL_LINES,
    HOUGH_THRESHOLD,
    MAX_LINE_GAP,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    TableDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def _classify_lines(
    lines: np.ndarray,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Classify lines as horizontal or vertical based on angle.

    Args:
        lines (np.ndarray): Array of lines from HoughLinesP

    Returns:
        tuple[list[np.ndarray], list[np.ndarray]]: Tuple of (horizontal_lines, vertical_lines)"""
    horizontal_lines: list[np.ndarray] = []
    vertical_lines: list[np.ndarray] = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        angle = abs(np.degrees(np.arctan2(dy, dx)))

        # Normalize to [0, 90] range
        if angle > 90:
            angle = 180 - angle

        # Classify as horizontal (0°), vertical (90°), or diagonal
        if angle < ANGLE_TOLERANCE:
            horizontal_lines.append(line[0])
        elif angle > (90 - ANGLE_TOLERANCE):
            vertical_lines.append(line[0])

    return horizontal_lines, vertical_lines


def detect_tables(
    image: np.ndarray,
    min_horizontal_lines: int = DEFAULT_MIN_HORIZONTAL_LINES,
    min_vertical_lines: int = DEFAULT_MIN_VERTICAL_LINES,
    grid_intersection_threshold: float = DEFAULT_GRID_INTERSECTION_THRESHOLD,
) -> TableDetectionResult:
    """Detect tables using Hough line detection + grid pattern analysis.

    Algorithm:
    1. Convert to grayscale and apply edge detection
    2. Detect horizontal and vertical lines using Hough Line Transform
    3. Count lines meeting minimum length criteria
    4. Calculate grid score based on line intersections
    5. Threshold: >10 horizontal AND >5 vertical lines forming grid

    Args:
        image (np.ndarray): Input image (BGR format, from OpenCV)
        min_horizontal_lines (int): Minimum horizontal lines for table (default: 10)
        min_vertical_lines (int): Minimum vertical lines for table (default: 5)
        grid_intersection_threshold (float): Minimum intersection ratio for grid (default: 0.3)

    Returns:
        TableDetectionResult: TableDetectionResult with detection decision and line counts

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running table detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply edge detection
    edges = cv2.Canny(gray, CANNY_LOW_THRESHOLD, CANNY_HIGH_THRESHOLD, apertureSize=3)

    # Detect lines using Hough Line Transform
    # Use Probabilistic Hough Transform for line segments
    min_line_length = int(min(image.shape[:2]) * 0.1)  # 10% of smaller dimension

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=min_line_length,
        maxLineGap=MAX_LINE_GAP,
    )

    if lines is None:
        logger.debug("No lines detected")
        return TableDetectionResult(
            has_tables=False,
            confidence=0.9,
            num_horizontal_lines=0,
            num_vertical_lines=0,
            grid_score=0.0,
        )

    # Classify lines as horizontal or vertical
    horizontal_lines, vertical_lines = _classify_lines(lines)
    num_horizontal = len(horizontal_lines)
    num_vertical = len(vertical_lines)

    # Calculate grid score based on intersection potential
    # Simplified: ratio of minimum(h_lines, v_lines) to maximum
    if num_horizontal > 0 and num_vertical > 0:
        grid_score = min(num_horizontal, num_vertical) / max(
            num_horizontal, num_vertical
        )
    else:
        grid_score = 0.0

    # Detection logic: sufficient lines AND good grid pattern
    has_tables = (
        num_horizontal >= min_horizontal_lines
        and num_vertical >= min_vertical_lines
        and grid_score >= grid_intersection_threshold
    )

    confidence = min(0.95, grid_score + 0.5) if has_tables else 0.8

    logger.debug(
        "Table detection complete",
        has_tables=has_tables,
        num_horizontal=num_horizontal,
        num_vertical=num_vertical,
        grid_score=grid_score,
    )

    return TableDetectionResult(
        has_tables=has_tables,
        confidence=confidence,
        num_horizontal_lines=num_horizontal,
        num_vertical_lines=num_vertical,
        grid_score=grid_score,
    )
