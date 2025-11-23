"""Watermark detection using FFT low-frequency analysis."""

import cv2
import numpy as np

from image_preprocessing_detector.detection.layout_lite.constants import (
    DEFAULT_LOW_FREQ_THRESHOLD,
    FREQ_CENTER_SIZE_RATIO,
    WATERMARK_OPACITY_NORMALIZER,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    WatermarkDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


def detect_watermark(
    image: np.ndarray,
    low_freq_threshold: float = DEFAULT_LOW_FREQ_THRESHOLD,
) -> WatermarkDetectionResult:
    """Detect watermarks using low-frequency component analysis (FFT) + opacity detection.

    Algorithm:
    1. Convert to grayscale
    2. Apply 2D Fourier Transform (FFT)
    3. Analyze low-frequency energy (center of frequency spectrum)
    4. Calculate opacity score from intensity variations
    5. Threshold: low-frequency energy >threshold

    Args:
        image: Input image (BGR format, from OpenCV)
        low_freq_threshold: Minimum low-frequency energy for watermark (default: 0.15)

    Returns:
        WatermarkDetectionResult with detection decision and metrics

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running watermark detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply 2D FFT
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)

    # Calculate magnitude spectrum
    magnitude_spectrum = np.abs(f_shift)

    # Analyze low-frequency components (center region)
    h, w = magnitude_spectrum.shape
    center_size = min(h, w) // FREQ_CENTER_SIZE_RATIO  # 10% of dimension

    center_y, center_x = h // 2, w // 2
    low_freq_region = magnitude_spectrum[
        center_y - center_size : center_y + center_size,
        center_x - center_size : center_x + center_size,
    ]

    # Calculate low-frequency energy as ratio to total energy
    low_freq_energy = np.sum(low_freq_region) / np.sum(magnitude_spectrum)

    # Calculate opacity score from intensity variations
    # Watermarks typically have semi-transparent, uniform intensity
    gray_std = float(np.std(gray))
    opacity_score = 1.0 - min(1.0, gray_std / WATERMARK_OPACITY_NORMALIZER)

    # Detection logic: high low-frequency energy indicates watermark
    watermark = low_freq_energy > low_freq_threshold

    # Confidence based on energy level and opacity
    confidence = min(0.9, low_freq_energy * 3.0) if watermark else 0.85

    logger.debug(
        "Watermark detection complete",
        watermark=watermark,
        low_freq_energy=low_freq_energy,
        opacity_score=opacity_score,
    )

    return WatermarkDetectionResult(
        watermark=watermark,
        confidence=confidence,
        low_freq_energy=low_freq_energy,
        opacity_score=opacity_score,
    )
