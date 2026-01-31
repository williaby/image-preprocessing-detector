# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Fast augmentation pipeline using Albumentations.

This module provides a high-performance augmentation pipeline using Albumentations
for document image degradation. It's designed to be much faster than Augraphy
while providing complementary augmentation types.

Example:
    >>> from PIL import Image
    >>> from image_preprocessing_detector.synthetic.augmentation_fast import (
    ...     FastAugmentationPipeline,
    ...     AugmentationProfile,
    ... )
    >>> pipeline = FastAugmentationPipeline(seed=42)
    >>> image = Image.new("RGB", (1240, 1754), "white")
    >>> augmented, labels = pipeline.apply(image, profile=AugmentationProfile.MODERATE)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Check if albumentations is available
try:
    import albumentations as A
    from albumentations.core.transforms_interface import ImageOnlyTransform

    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    A = None  # type: ignore[assignment]


class AugmentationProfile(str, Enum):
    """Augmentation intensity profiles."""

    PRISTINE = "pristine"  # No augmentation
    LIGHT = "light"  # Subtle degradations
    MODERATE = "moderate"  # Noticeable but realistic degradations
    HEAVY = "heavy"  # Strong degradations


@dataclass
class FastIQALabels:
    """IQA labels from fast augmentation pipeline.

    These 8 dimensions align with the script_dataset_structure.md specification
    for training IQA models alongside script detection.

    Attributes:
        blur: Blur severity from Gaussian, motion, median blur (0-1)
        noise: Noise severity from sensor/paper texture noise (0-1)
        compression: JPEG compression artifact severity (0-1)
        ink_degradation: Ink bleed, fading, low ink effects (0-1)
        paper_degradation: Paper texture, stains, aging effects (0-1)
        geometric_distortion: Rotation, perspective warping (0-1)
        bleed_through: Show-through from reverse side (0-1)
        overall_quality: Composite quality score (0-1, higher is better)
    """

    blur: float = 0.0
    noise: float = 0.0
    compression: float = 0.0
    ink_degradation: float = 0.0
    paper_degradation: float = 0.0
    geometric_distortion: float = 0.0
    bleed_through: float = 0.0
    overall_quality: float = 1.0


# Profile severity ranges
PROFILE_PARAMS = {
    AugmentationProfile.PRISTINE: {
        "blur_limit": 0,
        "noise_var": (0, 0),
        "jpeg_quality": (95, 100),
        "brightness": 0.0,
        "contrast": 0.0,
        "rotate": 0,
        "perspective": 0.0,
    },
    AugmentationProfile.LIGHT: {
        "blur_limit": 3,
        "noise_var": (5, 15),
        "jpeg_quality": (75, 95),
        "brightness": 0.1,
        "contrast": 0.1,
        "rotate": 2,
        "perspective": 0.02,
    },
    AugmentationProfile.MODERATE: {
        "blur_limit": 5,
        "noise_var": (10, 30),
        "jpeg_quality": (50, 85),
        "brightness": 0.2,
        "contrast": 0.2,
        "rotate": 5,
        "perspective": 0.05,
    },
    AugmentationProfile.HEAVY: {
        "blur_limit": 7,
        "noise_var": (20, 50),
        "jpeg_quality": (30, 70),
        "brightness": 0.3,
        "contrast": 0.3,
        "rotate": 10,
        "perspective": 0.1,
    },
}


class FastAugmentationPipeline:
    """Fast augmentation pipeline using Albumentations.

    This pipeline provides document-relevant augmentations that are much faster
    than Augraphy while still creating realistic degradations:
    - Blur (motion, gaussian, median)
    - Noise (gaussian, speckle)
    - JPEG compression artifacts
    - Color/brightness variations (simulating scanner variations)
    - Geometric distortions (rotation, perspective)
    - Paper texture effects

    Args:
        seed: Random seed for reproducibility

    Example:
        >>> pipeline = FastAugmentationPipeline(seed=42)
        >>> image = Image.new("RGB", (1240, 1754), "white")
        >>> augmented, labels = pipeline.apply(image, AugmentationProfile.MODERATE)
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize the pipeline.

        Args:
            seed: Random seed for reproducibility
        """
        if not ALBUMENTATIONS_AVAILABLE:
            logger.warning(
                "Albumentations not available. Install with: uv sync --extra synthetic"
            )

        self._seed = seed
        self._rng = np.random.default_rng(seed)

    def _create_pipeline(
        self, profile: AugmentationProfile
    ) -> tuple[A.Compose | None, dict[str, float]]:
        """Create an Albumentations pipeline for the given profile.

        Args:
            profile: Augmentation intensity profile

        Returns:
            Tuple of (Albumentations Compose pipeline, severity dict)
        """
        if not ALBUMENTATIONS_AVAILABLE:
            return None, {}

        if profile == AugmentationProfile.PRISTINE:
            return None, {}

        params = PROFILE_PARAMS[profile]
        severities: dict[str, float] = {}

        transforms = []

        # Blur augmentations (randomly choose one type)
        blur_limit = params["blur_limit"]
        if blur_limit > 0:
            blur_choice = self._rng.choice(["gaussian", "motion", "median"])
            if blur_choice == "gaussian":
                transforms.append(A.GaussianBlur(blur_limit=(3, blur_limit), p=0.5))
            elif blur_choice == "motion":
                transforms.append(A.MotionBlur(blur_limit=blur_limit, p=0.5))
            else:
                # Median blur requires odd kernel size
                median_limit = blur_limit if blur_limit % 2 == 1 else blur_limit - 1
                transforms.append(A.MedianBlur(blur_limit=max(3, median_limit), p=0.5))
            severities["blur"] = blur_limit / 7.0  # Normalize to 0-1

        # Noise augmentations
        noise_var = params["noise_var"]
        if noise_var[1] > 0:
            transforms.append(
                A.GaussNoise(
                    std_range=(noise_var[0] / 255.0, noise_var[1] / 255.0), p=0.5
                )
            )
            severities["noise"] = noise_var[1] / 50.0

        # JPEG compression
        jpeg_quality = params["jpeg_quality"]
        if jpeg_quality[0] < 95:
            transforms.append(
                A.ImageCompression(
                    quality_range=jpeg_quality, compression_type="jpeg", p=0.6
                )
            )
            # Lower quality = higher severity
            severities["compression"] = (95 - jpeg_quality[0]) / 65.0

        # Ink degradation (brightness/contrast variations simulating faded ink)
        brightness = params["brightness"]
        contrast = params["contrast"]
        if brightness > 0 or contrast > 0:
            transforms.append(
                A.RandomBrightnessContrast(
                    brightness_limit=brightness, contrast_limit=contrast, p=0.5
                )
            )
            severities["ink_degradation"] = (brightness + contrast) / 0.6

        # Paper degradation (shadows, color shifts, aging effects)
        transforms.append(
            A.HueSaturationValue(
                hue_shift_limit=5, sat_shift_limit=10, val_shift_limit=10, p=0.3
            )
        )
        transforms.append(
            A.RandomShadow(
                shadow_roi=(0, 0, 1, 1),
                num_shadows_limit=(1, 2),
                shadow_dimension=5,
                p=0.2,
            )
        )
        # Track paper degradation severity based on profile
        paper_severity = {
            AugmentationProfile.LIGHT: 0.15,
            AugmentationProfile.MODERATE: 0.30,
            AugmentationProfile.HEAVY: 0.50,
        }
        severities["paper_degradation"] = paper_severity.get(profile, 0.0)

        # Geometric distortions
        rotate = params["rotate"]
        perspective = params["perspective"]
        if rotate > 0 or perspective > 0:
            if rotate > 0:
                transforms.append(
                    A.Rotate(
                        limit=rotate,
                        border_mode=0,  # cv2.BORDER_CONSTANT
                        fill=255,  # White fill
                        p=0.4,
                    )
                )
            if perspective > 0:
                transforms.append(
                    A.Perspective(
                        scale=(0.01, perspective), fit_output=True, fill=255, p=0.3
                    )
                )
            severities["geometric_distortion"] = (rotate / 10.0 + perspective / 0.1) / 2

        # Bleed-through simulation (limited in Albumentations - approximated with transparency)
        # For proper bleed-through, consider Augraphy's BleedThrough augmentation
        # Here we simulate with a very subtle posterize + noise combination
        if profile == AugmentationProfile.HEAVY:
            transforms.append(A.Posterize(num_bits=6, p=0.1))
            severities["bleed_through"] = 0.15
        else:
            severities["bleed_through"] = 0.0

        # Downscale/upscale for aliasing artifacts
        transforms.append(
            A.Downscale(
                scale_range=(0.7, 0.9),
                interpolation_pair={
                    "downscale": 0,  # INTER_NEAREST
                    "upscale": 0,  # INTER_NEAREST
                },
                p=0.2,
            )
        )

        pipeline = A.Compose(transforms)
        return pipeline, severities

    def apply(
        self,
        image: Image.Image,
        profile: AugmentationProfile = AugmentationProfile.MODERATE,
    ) -> tuple[Image.Image, FastIQALabels]:
        """Apply augmentation to an image.

        Args:
            image: Input PIL Image
            profile: Augmentation intensity profile

        Returns:
            Tuple of (augmented image, IQA labels)
        """
        if not ALBUMENTATIONS_AVAILABLE:
            return image, FastIQALabels(overall_quality=1.0)

        if profile == AugmentationProfile.PRISTINE:
            return image, FastIQALabels(overall_quality=1.0)

        # Create pipeline
        pipeline, severities = self._create_pipeline(profile)
        if pipeline is None:
            return image, FastIQALabels(overall_quality=1.0)

        # Convert to numpy array (RGB)
        img_array = np.array(image)

        # Apply augmentation
        try:
            augmented = pipeline(image=img_array)
            result_array = augmented["image"]
        except Exception as e:
            logger.warning("Augmentation failed: %s. Returning original.", e)
            return image, FastIQALabels(overall_quality=1.0)

        # Convert back to PIL
        result_image = Image.fromarray(result_array)

        # Calculate overall quality
        avg_severity = sum(severities.values()) / max(len(severities), 1)
        overall_quality = max(
            0.0, 1.0 - avg_severity * 0.5
        )  # Scale down severity impact

        # Create labels with all 8 IQA dimensions
        labels = FastIQALabels(
            blur=severities.get("blur", 0.0),
            noise=severities.get("noise", 0.0),
            compression=severities.get("compression", 0.0),
            ink_degradation=severities.get("ink_degradation", 0.0),
            paper_degradation=severities.get("paper_degradation", 0.0),
            geometric_distortion=severities.get("geometric_distortion", 0.0),
            bleed_through=severities.get("bleed_through", 0.0),
            overall_quality=overall_quality,
        )

        return result_image, labels


__all__ = [
    "ALBUMENTATIONS_AVAILABLE",
    "AugmentationProfile",
    "FastAugmentationPipeline",
    "FastIQALabels",
]
