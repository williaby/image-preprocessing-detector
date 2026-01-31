# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Augraphy-based document augmentation for synthetic training data.

This module provides controlled document degradation using Augraphy
augmenters with ground truth IQA label generation.

Key Features:
    - 4 degradation profiles (pristine, mild, moderate, severe)
    - 8 IQA dimensions mapped to Augraphy augmenters
    - Ground truth label generation for training
    - Reproducible degradation via seed control

IQA Dimensions:
    - blur: Motion blur, defocus blur, Gaussian blur
    - noise: Gaussian noise, salt-pepper noise
    - compression: JPEG artifacts
    - ink_degradation: Faint text, broken characters
    - paper_degradation: Yellowing, foxing, staining
    - geometric_distortion: Skew, perspective, page curl
    - bleed_through: Show-through from page reverse
    - overall_quality: Composite quality score

Example:
    >>> from image_preprocessing_detector.synthetic.augmentation import (
    ...     AugmentationPipeline,
    ...     DegradationProfile,
    ... )
    >>> pipeline = AugmentationPipeline()
    >>> degraded_image, iqa_labels = pipeline.apply(
    ...     image, profile=DegradationProfile.MODERATE
    ... )
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image

from image_preprocessing_detector.synthetic.schema_adapter import IQALabels

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Monkey-patch sklearn.datasets.make_blobs to fix Augraphy 8.x bug
# Augraphy passes lists instead of tuples for center_box parameter
def _patch_make_blobs() -> None:
    """Patch make_blobs to accept lists for center_box parameter."""
    try:
        from sklearn import datasets

        original_make_blobs = datasets.make_blobs

        def patched_make_blobs(*args: Any, **kwargs: Any) -> Any:
            # Convert center_box from list to tuple if needed
            if "center_box" in kwargs and isinstance(kwargs["center_box"], list):
                kwargs["center_box"] = tuple(kwargs["center_box"])
            return original_make_blobs(*args, **kwargs)

        datasets.make_blobs = patched_make_blobs
        logger.debug("Patched sklearn.datasets.make_blobs for Augraphy compatibility")
    except ImportError:
        pass  # sklearn not installed, patch not needed


_patch_make_blobs()

# Try to import Augraphy - it's an optional dependency
# Updated for augraphy 8.x API
try:
    from augraphy import (
        AugraphyPipeline,
        BadPhotoCopy,
        BleedThrough,
        BookBinding,
        ColorPaper,
        DirtyDrum,
        Faxify,
        Folding,
        InkBleed,
        Jpeg,
        LowInkPeriodicLines,
        NoiseTexturize,
        SubtleNoise,
    )

    AUGRAPHY_AVAILABLE = True
except ImportError:
    AUGRAPHY_AVAILABLE = False
    logger.warning("Augraphy not available. Install with: uv sync --extra synthetic")


class DegradationProfile(str, Enum):
    """Predefined degradation intensity profiles."""

    PRISTINE = "pristine"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    FAST = "fast"  # Fast augmentation using only quick augmenters


# Slow augmenters to skip in FAST mode (these are computationally expensive)
SLOW_AUGMENTERS: set[str] = {"book_binding", "folding", "bleed_through"}


# Severity ranges for each profile (min, max)
PROFILE_SEVERITY_RANGES: dict[DegradationProfile, tuple[float, float]] = {
    DegradationProfile.PRISTINE: (0.0, 0.05),
    DegradationProfile.MILD: (0.1, 0.3),
    DegradationProfile.MODERATE: (0.3, 0.6),
    DegradationProfile.SEVERE: (0.6, 0.95),
    DegradationProfile.FAST: (0.2, 0.5),  # Moderate severity with fast augmenters only
}


@dataclass
class AugmenterConfig:
    """Configuration for a single augmenter.

    Attributes:
        name: Human-readable augmenter name
        iqa_dimension: Which IQA dimension this affects
        weight: Contribution weight to the dimension (0-1)
        params: Dictionary of parameter ranges
    """

    name: str
    iqa_dimension: str
    weight: float
    params: dict[str, Any]


# Augmenter configurations mapping to IQA dimensions
# Updated for augraphy 8.x API
AUGMENTER_CONFIGS: list[AugmenterConfig] = [
    # Blur augmenters - using BadPhotoCopy for blur-like effects
    AugmenterConfig(
        name="bad_photocopy",
        iqa_dimension="blur",
        weight=1.0,
        params={"noise_type": 2, "noise_iteration": (1, 2)},
    ),
    # Noise augmenters
    AugmenterConfig(
        name="subtle_noise",
        iqa_dimension="noise",
        weight=0.5,
        params={"subtle_range": (5, 35)},
    ),
    AugmenterConfig(
        name="noise_texturize",
        iqa_dimension="noise",
        weight=0.5,
        params={"sigma_range": (1, 5), "turbulence_range": (1, 3)},
    ),
    # Compression artifacts
    AugmenterConfig(
        name="jpeg_compression",
        iqa_dimension="compression",
        weight=1.0,
        params={"quality_range": (30, 95)},
    ),
    # Ink degradation
    AugmenterConfig(
        name="low_ink_periodic",
        iqa_dimension="ink_degradation",
        weight=0.5,
        params={"count_range": (2, 10), "period_range": (10, 30)},
    ),
    AugmenterConfig(
        name="ink_bleed",
        iqa_dimension="ink_degradation",
        weight=0.5,
        params={"intensity_range": (0.1, 0.5)},
    ),
    # Paper degradation
    AugmenterConfig(
        name="color_paper",
        iqa_dimension="paper_degradation",
        weight=0.4,
        params={"hue_range": (20, 40), "saturation_range": (10, 40)},
    ),
    AugmenterConfig(
        name="dirty_drum",
        iqa_dimension="paper_degradation",
        weight=0.6,
        params={"line_width_range": (1, 4), "line_concentration": 0.1},
    ),
    # Geometric distortion
    AugmenterConfig(
        name="book_binding",
        iqa_dimension="geometric_distortion",
        weight=0.5,
        params={"radius_range": (50, 200)},
    ),
    AugmenterConfig(
        name="folding",
        iqa_dimension="geometric_distortion",
        weight=0.5,
        params={"fold_count": (1, 3)},
    ),
    # Bleed-through
    AugmenterConfig(
        name="bleed_through",
        iqa_dimension="bleed_through",
        weight=1.0,
        params={"intensity_range": (0.1, 0.4)},
    ),
]


def _pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array.

    Args:
        image: PIL Image

    Returns:
        Numpy array in BGR format (for OpenCV/Augraphy compatibility)
    """
    rgb = np.array(image)
    if len(rgb.shape) == 2:
        # Grayscale
        return np.stack([rgb, rgb, rgb], axis=-1)
    if rgb.shape[2] == 4:
        # RGBA - drop alpha
        rgb = rgb[:, :, :3]
    # Convert RGB to BGR for Augraphy
    return rgb[:, :, ::-1]


def _numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image.

    Args:
        array: Numpy array in BGR format

    Returns:
        PIL Image in RGB format
    """
    if len(array.shape) == 2:
        return Image.fromarray(array)
    # Convert BGR to RGB
    rgb = array[:, :, ::-1]
    return Image.fromarray(rgb)


class AugmentationPipeline:
    """Applies controlled degradation to document images.

    Uses Augraphy augmenters with configurable profiles to generate
    realistic document degradations with ground truth IQA labels.
    """

    def __init__(
        self,
        seed: int | None = None,
        enable_all_dimensions: bool = True,
    ) -> None:
        """Initialize the augmentation pipeline.

        Args:
            seed: Random seed for reproducibility
            enable_all_dimensions: Whether to potentially use all IQA dimensions
        """
        self.seed = seed
        self.enable_all_dimensions = enable_all_dimensions
        self._rng = random.Random(seed)

        if not AUGRAPHY_AVAILABLE:
            logger.error(
                "Augraphy not available. Augmentation will return original images."
            )

    def _scale_params(
        self,
        config: AugmenterConfig,
        severity: float,
    ) -> dict[str, Any]:
        """Scale augmenter parameters based on severity.

        Args:
            config: Augmenter configuration
            severity: Severity level (0-1)

        Returns:
            Scaled parameter dictionary
        """
        scaled: dict[str, Any] = {}

        for key, value in config.params.items():
            if isinstance(value, tuple) and len(value) == 2:
                # Interpolate between min and max based on severity
                min_val, max_val = value
                if isinstance(min_val, int) and isinstance(max_val, int):
                    scaled_val = int(min_val + (max_val - min_val) * severity)
                else:
                    scaled_val = min_val + (max_val - min_val) * severity
                scaled[key] = scaled_val
            else:
                scaled[key] = value

        return scaled

    def _create_augmenter(
        self,
        config: AugmenterConfig,
        severity: float,
    ) -> Any | None:
        """Create an Augraphy augmenter instance.

        Updated for augraphy 8.x API.

        Args:
            config: Augmenter configuration
            severity: Severity level (0-1)

        Returns:
            Augraphy augmenter instance or None
        """
        if not AUGRAPHY_AVAILABLE:
            return None

        params = self._scale_params(config, severity)

        try:
            if config.name == "bad_photocopy":
                # BadPhotoCopy provides blur-like degradation effects
                noise_iter = params.get("noise_iteration", 1)
                if isinstance(noise_iter, tuple):
                    noise_iter = noise_iter[1]
                return BadPhotoCopy(
                    noise_type=2,
                    noise_iteration=(1, max(1, int(noise_iter))),
                    p=1.0,
                )

            if config.name == "subtle_noise":
                return SubtleNoise(
                    subtle_range=int(severity * 30) + 5,  # Range 5-35 based on severity
                    p=1.0,
                )

            if config.name == "noise_texturize":
                # NoiseTexturize replaces SaltPepperNoise
                sigma = params.get("sigma_range", 3)
                if isinstance(sigma, tuple):
                    sigma = sigma[1]
                return NoiseTexturize(
                    sigma_range=(1, max(1, int(sigma))),
                    turbulence_range=(1, 3),
                    p=1.0,
                )

            if config.name == "jpeg_compression":
                quality = params.get("quality_range", 70)
                if isinstance(quality, tuple):
                    quality = quality[0]
                return Jpeg(quality_range=(max(10, int(quality)), 95), p=1.0)

            if config.name == "low_ink_periodic":
                count = params.get("count_range", 5)
                period = params.get("period_range", 20)
                if isinstance(count, tuple):
                    count = count[1]
                if isinstance(period, tuple):
                    period = period[1]
                return LowInkPeriodicLines(
                    count_range=(1, max(1, int(count))),
                    period_range=(10, max(11, int(period))),
                    p=1.0,
                )

            if config.name == "ink_bleed":
                # InkBleed replaces InkMottling
                intensity = params.get("intensity_range", 0.3)
                if isinstance(intensity, tuple):
                    intensity = intensity[1]
                return InkBleed(
                    intensity_range=(0.1, max(0.11, float(intensity))),
                    p=1.0,
                )

            if config.name == "color_paper":
                hue = params.get("hue_range", 30)
                sat = params.get("saturation_range", 25)
                return ColorPaper(
                    hue_range=(20, max(21, int(hue))),
                    saturation_range=(10, max(11, int(sat))),
                    p=1.0,
                )

            if config.name == "dirty_drum":
                # DirtyDrum replaces Stains
                line_width = params.get("line_width_range", 2)
                if isinstance(line_width, tuple):
                    line_width = line_width[1]
                return DirtyDrum(
                    line_width_range=(1, max(2, int(line_width))),
                    line_concentration=0.1,
                    p=1.0,
                )

            if config.name == "book_binding":
                radius = params.get("radius_range", 100)
                if isinstance(radius, tuple):
                    radius = radius[1]
                return BookBinding(
                    radius_range=(30, max(31, int(radius))),
                    p=1.0,
                )

            if config.name == "folding":
                count = params.get("fold_count", 2)
                if isinstance(count, tuple):
                    count = count[1]
                return Folding(
                    fold_count=max(1, int(count)),
                    p=1.0,
                )

            if config.name == "bleed_through":
                intensity = params.get("intensity_range", 0.2)
                if isinstance(intensity, tuple):
                    intensity = intensity[1]
                return BleedThrough(
                    intensity_range=(0.1, max(0.11, float(intensity))),
                    p=1.0,
                )

        except Exception as e:
            logger.warning("Failed to create augmenter %s: %s", config.name, e)
            return None

        return None

    def _select_augmenters(
        self,
        profile: DegradationProfile,
        custom_severities: dict[str, float] | None = None,
    ) -> tuple[list[Any], dict[str, float]]:
        """Select augmenters based on profile.

        Args:
            profile: Degradation profile
            custom_severities: Optional custom severities per dimension

        Returns:
            Tuple of (augmenter list, severity dict per IQA dimension)
        """
        if not AUGRAPHY_AVAILABLE:
            return [], {}

        min_sev, max_sev = PROFILE_SEVERITY_RANGES[profile]
        augmenters: list[Any] = []
        severities: dict[str, float] = {
            "blur": 0.0,
            "noise": 0.0,
            "compression": 0.0,
            "ink_degradation": 0.0,
            "paper_degradation": 0.0,
            "geometric_distortion": 0.0,
            "bleed_through": 0.0,
        }

        if profile == DegradationProfile.PRISTINE:
            # No augmentation for pristine
            return [], severities

        for config in AUGMENTER_CONFIGS:
            # Skip slow augmenters in FAST mode
            if profile == DegradationProfile.FAST and config.name in SLOW_AUGMENTERS:
                continue

            # Random chance to include this augmenter
            if self._rng.random() > 0.6:
                continue

            # Determine severity
            if custom_severities and config.iqa_dimension in custom_severities:
                severity = custom_severities[config.iqa_dimension]
            else:
                severity = self._rng.uniform(min_sev, max_sev)

            # Create augmenter
            aug = self._create_augmenter(config, severity)
            if aug:
                augmenters.append(aug)
                # Update severity tracking (weighted by config weight)
                current = severities[config.iqa_dimension]
                severities[config.iqa_dimension] = max(
                    current, severity * config.weight
                )

        return augmenters, severities

    def apply(
        self,
        image: Image.Image,
        profile: DegradationProfile = DegradationProfile.MODERATE,
        custom_severities: dict[str, float] | None = None,
    ) -> tuple[Image.Image, IQALabels]:
        """Apply degradation to an image.

        Args:
            image: Input PIL Image
            profile: Degradation profile to use
            custom_severities: Optional custom severities per IQA dimension

        Returns:
            Tuple of (degraded image, IQA labels)
        """
        if not AUGRAPHY_AVAILABLE:
            # Return original with pristine labels
            return image, IQALabels(overall_quality=1.0)

        # Select augmenters
        augmenters, severities = self._select_augmenters(profile, custom_severities)

        if not augmenters:
            # Pristine - return original
            return image, IQALabels(overall_quality=1.0)

        # Convert to numpy
        img_array = _pil_to_numpy(image)

        # Create Augraphy pipeline
        try:
            pipeline = AugraphyPipeline(
                ink_phase=augmenters[: len(augmenters) // 2] or [],
                paper_phase=augmenters[len(augmenters) // 2 :] or [],
                post_phase=[],
            )

            # Apply augmentation
            augmented = pipeline(img_array)

        except Exception as e:
            logger.warning("Augmentation failed: %s. Returning original.", e)
            return image, IQALabels(overall_quality=1.0)

        # Convert back to PIL
        result_image = _numpy_to_pil(augmented)

        # Calculate overall quality (inverse of average severity)
        avg_severity = sum(severities.values()) / len(severities)
        overall_quality = max(0.0, 1.0 - avg_severity)

        # Create IQA labels
        iqa_labels = IQALabels(
            blur=severities.get("blur", 0.0),
            noise=severities.get("noise", 0.0),
            compression=severities.get("compression", 0.0),
            ink_degradation=severities.get("ink_degradation", 0.0),
            paper_degradation=severities.get("paper_degradation", 0.0),
            geometric_distortion=severities.get("geometric_distortion", 0.0),
            bleed_through=severities.get("bleed_through", 0.0),
            overall_quality=overall_quality,
        )

        return result_image, iqa_labels

    def apply_specific_degradations(
        self,
        image: Image.Image,
        degradations: list[str],
        severity: float = 0.5,
    ) -> tuple[Image.Image, IQALabels]:
        """Apply specific degradation types.

        Args:
            image: Input PIL Image
            degradations: List of degradation names to apply
            severity: Severity level (0-1)

        Returns:
            Tuple of (degraded image, IQA labels)
        """
        custom_severities: dict[str, float] = {}

        # Map requested degradations to IQA dimensions
        degradation_to_dimension = {
            "blur": "blur",
            "motion_blur": "blur",
            "defocus_blur": "blur",
            "gaussian_blur": "blur",
            "noise": "noise",
            "gaussian_noise": "noise",
            "salt_pepper": "noise",
            "compression": "compression",
            "jpeg_artifacts": "compression",
            "ink": "ink_degradation",
            "faint_text": "ink_degradation",
            "paper": "paper_degradation",
            "yellowing": "paper_degradation",
            "stains": "paper_degradation",
            "geometric": "geometric_distortion",
            "skew": "geometric_distortion",
            "perspective": "geometric_distortion",
            "bleed_through": "bleed_through",
        }

        for deg in degradations:
            if deg in degradation_to_dimension:
                dimension = degradation_to_dimension[deg]
                custom_severities[dimension] = severity

        return self.apply(
            image,
            profile=DegradationProfile.MODERATE,
            custom_severities=custom_severities,
        )


__all__ = [
    "AUGMENTER_CONFIGS",
    "AUGRAPHY_AVAILABLE",
    "PROFILE_SEVERITY_RANGES",
    "AugmentationPipeline",
    "AugmenterConfig",
    "DegradationProfile",
]
