"""Perspective Correction — Fix perspective distortion in camera captures.

Uses Canny edge detection + contour approximation to find a quadrilateral
document boundary, then applies a perspective warp to rectify the image.

Safety guardrails:
- Skips if warping_score > 0.75 (extreme warping better handled by VLM)
- Returns original if quad detection fails (no valid 4-point contour)
- Requires minimum contour area (10% of image) to avoid noise matches
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Warping severity above which classical correction is skipped (-> VLM)
_WARPING_BLOCK_THRESHOLD = 0.75

# Minimum contour area as fraction of image area
_MIN_CONTOUR_AREA_RATIO = 0.10

# Canny edge detection thresholds
_CANNY_LOW = 50
_CANNY_HIGH = 150

# Gaussian blur kernel size for edge detection preprocessing
_BLUR_KERNEL = 5

# Error message
_INVALID_IMAGE_ERROR = "Invalid or empty image provided"


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as [top-left, top-right, bottom-right, bottom-left].

    Uses sum and difference of coordinates to determine corner positions.

    Args:
        pts (np.ndarray): Array of shape (4, 2) with unordered corner points.

    Returns:
        np.ndarray: Array of shape (4, 2) with ordered corner points.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()

    rect[0] = pts[np.argmin(s)]  # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]  # bottom-right: largest sum
    rect[1] = pts[np.argmin(diff)]  # top-right: smallest difference
    rect[3] = pts[np.argmax(diff)]  # bottom-left: largest difference

    return rect


class PerspectiveCorrector:
    """Correct perspective distortion in camera-captured document images.

    Pipeline:
    1. Check warping_score gate (skip if > 0.75)
    2. Convert to grayscale + Gaussian blur
    3. Canny edge detection
    4. Find contours, approximate to polygon
    5. Select best quadrilateral (4 corners, largest area)
    6. Order corners [TL, TR, BR, BL]
    7. Compute destination rectangle from max width/height
    8. Apply perspective transform

    Args:
        warping_block_threshold (float): Maximum warping score for classical
            correction. Above this, VLM should handle it.
        min_contour_area_ratio (float): Minimum contour area as fraction
            of image area to qualify as document boundary.

    Example:
        >>> corrector = PerspectiveCorrector()
        >>> result = corrector.correct(image, warping_score=0.5)
        >>> if result.applied:
        ...     rectified = result.corrected_image
    """

    def __init__(
        self,
        warping_block_threshold: float = _WARPING_BLOCK_THRESHOLD,
        min_contour_area_ratio: float = _MIN_CONTOUR_AREA_RATIO,
    ) -> None:
        self.warping_block_threshold = warping_block_threshold
        self.min_contour_area_ratio = min_contour_area_ratio

    def correct(
        self,
        image: np.ndarray,
        warping_score: float = 0.0,
    ) -> CorrectionResult:
        """Apply perspective correction.

        Args:
            image (np.ndarray): Input image (BGR format).
            warping_score (float): Detected warping severity (0-1) from Stream 2
                warping detector. Scores > 0.75 are blocked.

        Returns:
            CorrectionResult: CorrectionResult with corrected image and metadata.

        Raises:
            ValueError: If image is invalid or empty.
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        original_h, original_w = image.shape[:2]

        # Gate: skip extreme warping (VLM territory)
        if warping_score > self.warping_block_threshold:
            return CorrectionResult(
                corrected_image=image,
                applied=False,
                parameters=self._make_params(original_w, original_h),
                skipped_reason=(
                    f"Warping score {warping_score:.2f} exceeds threshold "
                    f"{self.warping_block_threshold} (VLM recommended)"
                ),
            )

        # Find document quadrilateral
        quad = self._find_document_quad(image)

        if quad is None:
            return CorrectionResult(
                corrected_image=image,
                applied=False,
                parameters=self._make_params(original_w, original_h),
                skipped_reason="No valid quadrilateral found",
            )

        # Order corners
        ordered = _order_points(quad.reshape(4, 2))

        # Compute output dimensions from the ordered quad
        dst_w, dst_h = self._compute_output_dimensions(ordered)

        # Destination rectangle
        dst = np.array(
            [
                [0, 0],
                [dst_w - 1, 0],
                [dst_w - 1, dst_h - 1],
                [0, dst_h - 1],
            ],
            dtype=np.float32,
        )

        # Perspective transform
        matrix = cv2.getPerspectiveTransform(ordered, dst)
        warped = cv2.warpPerspective(image, matrix, (dst_w, dst_h))

        logger.debug(
            "perspective_correction_applied",
            output_size=(dst_w, dst_h),
            warping_score=round(warping_score, 3),
        )

        return CorrectionResult(
            corrected_image=warped,
            applied=True,
            parameters=self._make_params(
                original_w,
                original_h,
                output_w=dst_w,
                output_h=dst_h,
                corners=ordered.tolist(),
            ),
        )

    def _find_document_quad(self, image: np.ndarray) -> np.ndarray | None:
        """Find the largest quadrilateral contour in the image.

        Args:
            image (np.ndarray): Input BGR image.

        Returns:
            np.ndarray | None: Array of 4 corner points, or None if not found.
        """
        original_h, original_w = image.shape[:2]
        min_area = original_h * original_w * self.min_contour_area_ratio

        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (_BLUR_KERNEL, _BLUR_KERNEL), 0)
        edges = cv2.Canny(blurred, _CANNY_LOW, _CANNY_HIGH)

        # Dilate edges to close gaps
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Sort by area descending
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for contour in contours[:5]:  # Check top 5 largest
            area = cv2.contourArea(contour)
            if area < min_area:
                break

            # Approximate to polygon
            peri = cv2.arcLength(contour, closed=True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, closed=True)

            if len(approx) == 4:
                return approx

        return None

    @staticmethod
    def _compute_output_dimensions(
        ordered: np.ndarray,
    ) -> tuple[int, int]:
        """Compute output width and height from ordered corner points.

        Args:
            ordered (np.ndarray): Array of shape (4, 2) with [TL, TR, BR, BL] corners.

        Returns:
            tuple[int, int]: Tuple of (width, height) for the output image.
        """
        tl, tr, br, bl = ordered

        # Width: max of top edge and bottom edge
        width_top = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        dst_w = max(int(width_top), int(width_bottom))

        # Height: max of left edge and right edge
        height_left = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)
        dst_h = max(int(height_left), int(height_right))

        return dst_w, dst_h

    @staticmethod
    def _make_params(
        original_w: int,
        original_h: int,
        output_w: int = 0,
        output_h: int = 0,
        corners: list[list[float]] | None = None,
    ) -> dict[str, Any]:
        """Build parameters dict for CorrectionResult."""
        return {
            "original_size": (original_w, original_h),
            "output_size": (output_w, output_h),
            "corners": corners,
        }


# Convenience function
def correct_perspective(
    image: np.ndarray,
    warping_score: float = 0.0,
) -> CorrectionResult:
    """Correct perspective distortion using default settings.

    Args:
        image (np.ndarray): Input image (BGR format).
        warping_score (float): Detected warping severity (0-1).

    Returns:
        CorrectionResult: CorrectionResult with corrected image.
    """
    return PerspectiveCorrector().correct(image, warping_score)


__all__ = [
    "PerspectiveCorrector",
    "correct_perspective",
]
