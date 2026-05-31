"""Border Removal — Crop scanner/camera borders from document images.

Uses Otsu thresholding + morphological closing to find the document region,
then crops to the largest contour's bounding rectangle.

Safety guardrail: if the detected crop area is less than 70% of the
original image area, the original image is returned unchanged (prevents
catastrophic over-cropping on images without clear borders).
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Safety threshold: crop must retain at least this fraction of original area
_MIN_AREA_RATIO = 0.70

# Morphological kernel size for closing gaps in the document boundary
_MORPH_KERNEL_SIZE = 15

# Error message
_INVALID_IMAGE_ERROR = "Invalid or empty image provided"


class BorderRemover:
    """Remove scanner/camera borders from document images.

    Pipeline:
    1. Convert to grayscale
    2. Otsu threshold to separate document from background
    3. Morphological close to fill small gaps in document boundary
    4. Find contours, select largest by area
    5. Crop to bounding rectangle of largest contour
    6. Guardrail: reject crop if area < 70% of original

    Args:
        min_area_ratio (float): Minimum ratio of crop area to original area.
            If crop is smaller, the original image is returned.
        morph_kernel_size (int): Size of the morphological closing kernel.

    Example:
        >>> remover = BorderRemover()
        >>> result = remover.correct(image)
        >>> if result.applied:
        ...     cropped = result.corrected_image
    """

    def __init__(
        self,
        min_area_ratio: float = _MIN_AREA_RATIO,
        morph_kernel_size: int = _MORPH_KERNEL_SIZE,
    ) -> None:
        self.min_area_ratio = min_area_ratio
        self.morph_kernel_size = morph_kernel_size

    def correct(self, image: np.ndarray) -> CorrectionResult:
        """Remove borders from the image.

        Args:
            image (np.ndarray): Input image (BGR or grayscale).

        Returns:
            CorrectionResult: CorrectionResult with cropped image and metadata.

        Raises:
            ValueError: If image is invalid or empty.
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        original_h, original_w = image.shape[:2]
        original_area = original_h * original_w

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Otsu threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological closing to connect fragmented document edges
        kernel = np.ones((self.morph_kernel_size, self.morph_kernel_size), np.uint8)
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return CorrectionResult(
                corrected_image=image,
                applied=False,
                parameters=self._make_params(original_w, original_h),
                skipped_reason="No contours found",
            )

        # Select largest contour by area
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        crop_area = w * h

        # Safety guardrail: reject if crop is too small
        area_ratio = crop_area / original_area
        if area_ratio < self.min_area_ratio:
            logger.debug(
                "border_removal_skipped",
                area_ratio=round(area_ratio, 3),
                threshold=self.min_area_ratio,
                reason="Crop area too small",
            )
            return CorrectionResult(
                corrected_image=image,
                applied=False,
                parameters=self._make_params(
                    original_w, original_h, x, y, w, h, area_ratio
                ),
                skipped_reason=(
                    f"Crop area ratio {area_ratio:.3f} below "
                    f"threshold {self.min_area_ratio}"
                ),
            )

        # Apply crop
        cropped = image[y : y + h, x : x + w]

        logger.debug(
            "border_removal_applied",
            crop_x=x,
            crop_y=y,
            crop_w=w,
            crop_h=h,
            area_ratio=round(area_ratio, 3),
        )

        return CorrectionResult(
            corrected_image=cropped,
            applied=True,
            parameters=self._make_params(
                original_w, original_h, x, y, w, h, area_ratio
            ),
        )

    @staticmethod
    def _make_params(
        original_w: int,
        original_h: int,
        crop_x: int = 0,
        crop_y: int = 0,
        crop_w: int = 0,
        crop_h: int = 0,
        area_ratio: float = 0.0,
    ) -> dict[str, Any]:
        """Build parameters dict for CorrectionResult."""
        return {
            "original_size": (original_w, original_h),
            "crop_rect": (crop_x, crop_y, crop_w, crop_h),
            "area_ratio": round(area_ratio, 4),
        }


# Convenience function
def remove_borders(
    image: np.ndarray,
    min_area_ratio: float = _MIN_AREA_RATIO,
) -> CorrectionResult:
    """Remove borders using default settings.

    Args:
        image (np.ndarray): Input image (BGR or grayscale).
        min_area_ratio (float): Minimum ratio of crop area to original.

    Returns:
        CorrectionResult: CorrectionResult with cropped image.
    """
    return BorderRemover(min_area_ratio=min_area_ratio).correct(image)


__all__ = [
    "BorderRemover",
    "remove_borders",
]
