"""Fuzzy scan detection using blur and noise estimation."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    CLEAN_IMAGE_STD,
    DEFAULT_BLUR_THRESHOLD,
    DEFAULT_NOISE_THRESHOLD,
    GAUSSIAN_KERNEL_SIZE,
    SHARP_IMAGE_VARIANCE,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    FuzzyScanDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def detect_fuzzy_scan(
    image: np.ndarray,
    blur_threshold: float = DEFAULT_BLUR_THRESHOLD,
    noise_threshold: float = DEFAULT_NOISE_THRESHOLD,
) -> FuzzyScanDetectionResult:
    """Detect fuzzy scans using Laplacian variance + noise estimation.

    Algorithm:
    1. Calculate blur metric using Laplacian variance
    2. Estimate noise using high-frequency component analysis
    3. Normalize scores to 0-1 range
    4. Threshold: blur_score >0.7 AND noise_score >0.5

    Args:
        image (np.ndarray): Input image (BGR format, from OpenCV)
        blur_threshold (float): Minimum blur score for fuzzy scan (default: 0.7)
        noise_threshold (float): Minimum noise score for fuzzy scan (default: 0.5)

    Returns:
        FuzzyScanDetectionResult: FuzzyScanDetectionResult with detection decision and scores

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running fuzzy scan detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate blur metric using Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_var = laplacian.var()

    # Normalize blur score (inverse: lower variance = more blur)
    # Typical range: sharp images have variance >500, blurry <100
    blur_score = float(1.0 - min(1.0, laplacian_var / SHARP_IMAGE_VARIANCE))

    # Estimate noise using high-frequency components
    # Apply high-pass filter (difference from Gaussian blur)
    blurred = cv2.GaussianBlur(gray, GAUSSIAN_KERNEL_SIZE, 0)
    noise_image = cv2.absdiff(gray, blurred)

    # Calculate noise metric as standard deviation of noise image
    noise_std = float(np.std(noise_image))

    # Normalize noise score
    # Typical range: clean images have std <10, noisy >30
    noise_score = min(1.0, noise_std / CLEAN_IMAGE_STD)

    # Detection logic: both blur and noise exceed thresholds
    fuzzy_scan = (blur_score > blur_threshold) and (noise_score > noise_threshold)

    # Confidence based on how far above thresholds
    confidence = min(0.95, (blur_score + noise_score) / 2.0) if fuzzy_scan else 0.85

    logger.debug(
        "Fuzzy scan detection complete",
        fuzzy_scan=fuzzy_scan,
        blur_score=blur_score,
        noise_score=noise_score,
    )

    return FuzzyScanDetectionResult(
        fuzzy_scan=fuzzy_scan,
        confidence=confidence,
        blur_score=blur_score,
        noise_score=noise_score,
    )
