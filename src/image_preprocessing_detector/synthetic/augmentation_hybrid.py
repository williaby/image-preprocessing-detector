# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Hybrid augmentation pipeline combining Augraphy and Albumentations.

This module provides a hybrid augmentation approach that leverages the
strengths of both libraries:

- **Augraphy**: Realistic document-specific effects (bleed-through, ink bleed,
  paper aging) that cannot be simulated with generic augmentation
- **Albumentations**: Fast general-purpose effects (blur, noise, compression,
  geometric distortion) that are ~10x faster

The pipeline applies Augraphy effects FIRST (document-realistic), then
Albumentations (fast general), and merges IQA labels from both sources.

Example:
    >>> from PIL import Image
    >>> from image_preprocessing_detector.synthetic.augmentation_hybrid import (
    ...     HybridAugmentationPipeline,
    ...     HybridProfile,
    ... )
    >>> pipeline = HybridAugmentationPipeline(seed=42)
    >>> image = Image.new("RGB", (1240, 1754), "white")
    >>> augmented, labels = pipeline.apply(image, profile=HybridProfile.MODERATE)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from PIL import Image

from image_preprocessing_detector.synthetic.schema_adapter import IQALabels

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Check if both libraries are available
try:
    from augraphy import BleedThrough, BookBinding, ColorPaper, DirtyDrum, InkBleed

    AUGRAPHY_AVAILABLE = True
except ImportError:
    AUGRAPHY_AVAILABLE = False
    logger.warning("Augraphy not available for hybrid mode")

try:
    import albumentations as A  # noqa: N812

    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    logger.warning("Albumentations not available for hybrid mode")

HYBRID_AVAILABLE = AUGRAPHY_AVAILABLE and ALBUMENTATIONS_AVAILABLE


class HybridProfile(StrEnum):
    """Hybrid augmentation intensity profiles."""

    PRISTINE = "pristine"  # No augmentation
    LIGHT = "light"  # Subtle degradations
    MODERATE = "moderate"  # Noticeable but realistic degradations
    HEAVY = "heavy"  # Strong degradations
    AGED = "aged"  # Document aging effects (yellowing, foxing, contrast)
    HISTORICAL = "historical"  # Heavy aging (yellowing, foxing, staining, ink fade)


# Augraphy-specific severity ranges for document effects
AUGRAPHY_SEVERITY_RANGES = {
    HybridProfile.PRISTINE: (0.0, 0.0),
    HybridProfile.LIGHT: (0.1, 0.3),
    HybridProfile.MODERATE: (0.3, 0.6),
    HybridProfile.HEAVY: (0.6, 0.9),
    HybridProfile.AGED: (0.3, 0.6),  # Similar to moderate but paper-focused
    HybridProfile.HISTORICAL: (0.5, 0.85),  # Similar to heavy but paper-focused
}

# Albumentations params by profile (same as augmentation_fast.py)
ALBUMENTATIONS_PARAMS = {
    HybridProfile.PRISTINE: {
        "blur_limit": 0,
        "noise_var": (0, 0),
        "jpeg_quality": (95, 100),
        "rotate": 0,
        "perspective": 0.0,
    },
    HybridProfile.LIGHT: {
        "blur_limit": 3,
        "noise_var": (5, 15),
        "jpeg_quality": (75, 95),
        "rotate": 2,
        "perspective": 0.02,
    },
    HybridProfile.MODERATE: {
        "blur_limit": 5,
        "noise_var": (10, 30),
        "jpeg_quality": (50, 85),
        "rotate": 5,
        "perspective": 0.05,
    },
    HybridProfile.HEAVY: {
        "blur_limit": 7,
        "noise_var": (20, 50),
        "jpeg_quality": (30, 70),
        "rotate": 10,
        "perspective": 0.1,
    },
    HybridProfile.AGED: {
        "blur_limit": 3,  # Mild blur (age doesn't mean blurry)
        "noise_var": (5, 20),  # Light sensor noise
        "jpeg_quality": (60, 90),  # Mild compression
        "rotate": 2,  # Slight misalignment
        "perspective": 0.02,
    },
    HybridProfile.HISTORICAL: {
        "blur_limit": 5,  # Moderate blur (old scanner/camera)
        "noise_var": (10, 35),  # Moderate noise
        "jpeg_quality": (40, 75),  # Moderate compression
        "rotate": 5,  # Scanner misalignment
        "perspective": 0.05,
    },
}


@dataclass
class HybridIQALabels:
    """IQA labels from hybrid augmentation pipeline.

    Attributes:
        blur: From Albumentations (0-1)
        noise: From Albumentations (0-1)
        compression: From Albumentations (0-1)
        ink_degradation: From Augraphy InkBleed/DirtyDrum (0-1)
        paper_degradation: From Augraphy ColorPaper/BookBinding (0-1)
        geometric_distortion: From Albumentations (0-1)
        bleed_through: From Augraphy BleedThrough (0-1) - TRUE simulation
        overall_quality: Composite quality score (0-1, higher is better)
        augraphy_applied: Whether Augraphy effects were applied
        albumentations_applied: Whether Albumentations effects were applied
    """

    blur: float = 0.0
    noise: float = 0.0
    compression: float = 0.0
    ink_degradation: float = 0.0
    paper_degradation: float = 0.0
    geometric_distortion: float = 0.0
    bleed_through: float = 0.0
    overall_quality: float = 1.0
    augraphy_applied: bool = False
    albumentations_applied: bool = False


def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to BGR numpy array for Augraphy."""
    rgb = np.array(image)
    if len(rgb.shape) == 2:
        return np.stack([rgb, rgb, rgb], axis=-1)
    if rgb.shape[2] == 4:
        rgb = rgb[:, :, :3]
    return rgb[:, :, ::-1]


def _bgr_to_pil(array: np.ndarray) -> Image.Image:
    """Convert BGR numpy array to PIL Image."""
    if len(array.shape) == 2:
        return Image.fromarray(array)
    rgb = array[:, :, ::-1]
    return Image.fromarray(rgb)


class HybridAugmentationPipeline:
    """Hybrid augmentation combining Augraphy + Albumentations.

    This pipeline uses:
    - **Augraphy** for document-specific effects:
      - BleedThrough (true bleed-through simulation)
      - InkBleed, DirtyDrum (ink degradation)
      - ColorPaper, BookBinding (paper degradation)

    - **Albumentations** for fast general effects:
      - GaussianBlur, MotionBlur (blur)
      - GaussNoise (noise)
      - ImageCompression (JPEG artifacts)
      - Rotate, Perspective (geometric distortion)

    The pipeline applies Augraphy FIRST, then Albumentations, which is
    important because:
    1. Document effects should come before scanning/capture effects
    2. Augraphy's BleedThrough needs a clean image to simulate properly

    Args:
        seed: Random seed for reproducibility
        augraphy_probability: Probability of applying Augraphy effects (default 0.7)
        albumentations_probability: Probability of applying Albumentations effects (default 1.0)
    """

    def __init__(
        self,
        seed: int | None = None,
        augraphy_probability: float = 0.7,
        albumentations_probability: float = 1.0,
    ) -> None:
        """Initialize the hybrid pipeline.

        Args:
            seed: Random seed for reproducibility
            augraphy_probability: Chance to apply Augraphy document effects
            albumentations_probability: Chance to apply Albumentations effects
        """
        self._seed = seed
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)
        self._augraphy_prob = augraphy_probability
        self._albumentations_prob = albumentations_probability

        if not HYBRID_AVAILABLE:
            logger.warning(
                "Hybrid augmentation requires both Augraphy and Albumentations. "
                "Install with: uv sync --extra synthetic"
            )

    def _apply_augraphy_phase(
        self,
        image: Image.Image,
        profile: HybridProfile,
    ) -> tuple[Image.Image, dict[str, float]]:
        """Apply Augraphy document-specific effects.

        This applies ONLY the effects that Augraphy does uniquely well:
        - BleedThrough (true simulation, not approximation)
        - InkBleed, DirtyDrum (realistic ink degradation)
        - ColorPaper, BookBinding (paper aging effects)

        Args:
            image: Input PIL Image
            profile: Degradation profile

        Returns:
            Tuple of (augmented image, severity dict)
        """
        severities = {
            "ink_degradation": 0.0,
            "paper_degradation": 0.0,
            "bleed_through": 0.0,
        }

        if not AUGRAPHY_AVAILABLE or profile == HybridProfile.PRISTINE:
            return image, severities

        # Skip Augraphy based on probability
        if self._rng.random() > self._augraphy_prob:
            return image, severities

        min_sev, max_sev = AUGRAPHY_SEVERITY_RANGES[profile]
        augmenters: list[Any] = []

        # BleedThrough - the key unique effect from Augraphy
        if self._rng.random() < 0.5:
            severity = self._rng.uniform(min_sev, max_sev)
            intensity = 0.1 + severity * 0.3  # Range: 0.1 to 0.4
            try:
                augmenters.append(
                    BleedThrough(
                        intensity_range=(intensity * 0.8, intensity),
                        p=1.0,
                    )
                )
                severities["bleed_through"] = severity
            except Exception as e:
                logger.debug("Failed to create BleedThrough: %s", e)

        # InkBleed for ink degradation
        if self._rng.random() < 0.4:
            severity = self._rng.uniform(min_sev, max_sev)
            intensity = 0.1 + severity * 0.3
            try:
                augmenters.append(
                    InkBleed(
                        intensity_range=(intensity * 0.5, intensity),
                        p=1.0,
                    )
                )
                severities["ink_degradation"] = max(
                    severities["ink_degradation"], severity * 0.6
                )
            except Exception as e:
                logger.debug("Failed to create InkBleed: %s", e)

        # DirtyDrum for ink degradation (printer artifacts)
        if self._rng.random() < 0.3:
            severity = self._rng.uniform(min_sev, max_sev)
            line_width = int(1 + severity * 3)
            try:
                augmenters.append(
                    DirtyDrum(
                        line_width_range=(1, max(2, line_width)),
                        line_concentration=0.05 + severity * 0.1,
                        p=1.0,
                    )
                )
                severities["ink_degradation"] = max(
                    severities["ink_degradation"], severity * 0.4
                )
            except Exception as e:
                logger.debug("Failed to create DirtyDrum: %s", e)

        # ColorPaper for paper aging
        if self._rng.random() < 0.4:
            severity = self._rng.uniform(min_sev, max_sev)
            hue = int(20 + severity * 20)
            sat = int(10 + severity * 20)
            try:
                augmenters.append(
                    ColorPaper(
                        hue_range=(15, hue),
                        saturation_range=(5, sat),
                        p=1.0,
                    )
                )
                severities["paper_degradation"] = max(
                    severities["paper_degradation"], severity * 0.5
                )
            except Exception as e:
                logger.debug("Failed to create ColorPaper: %s", e)

        # BookBinding for paper curvature
        if self._rng.random() < 0.2:
            severity = self._rng.uniform(min_sev, max_sev)
            radius = int(50 + severity * 150)
            try:
                augmenters.append(
                    BookBinding(
                        radius_range=(30, radius),
                        p=1.0,
                    )
                )
                severities["paper_degradation"] = max(
                    severities["paper_degradation"], severity * 0.5
                )
            except Exception as e:
                logger.debug("Failed to create BookBinding: %s", e)

        if not augmenters:
            return image, severities

        # Apply augmenters sequentially
        img_array = _pil_to_bgr(image)

        for aug in augmenters:
            try:
                img_array = aug(img_array)
            except Exception as e:
                logger.warning("Augraphy augmenter failed: %s", e)

        return _bgr_to_pil(img_array), severities

    def _apply_aging_effects(
        self,
        image: Image.Image,
        profile: HybridProfile,
    ) -> tuple[Image.Image, dict[str, float]]:
        """Apply document aging effects (yellowing, foxing, contrast reduction).

        These effects simulate the physical degradation of paper and ink over time.
        Applied in addition to standard Augraphy/Albumentations for AGED/HISTORICAL profiles.

        Args:
            image: Input PIL Image
            profile: Must be AGED or HISTORICAL

        Returns:
            Tuple of (aged image, severity dict)
        """
        severities = {"paper_degradation": 0.0, "ink_degradation": 0.0}

        if profile not in (HybridProfile.AGED, HybridProfile.HISTORICAL):
            return image, severities

        img_array = np.array(image, dtype=np.float32)

        # Yellowing: shift color balance toward warm tones
        if profile == HybridProfile.AGED:
            yellow_strength = self._rng.uniform(0.03, 0.08)
        else:  # HISTORICAL
            yellow_strength = self._rng.uniform(0.08, 0.18)

        # Add yellow tint (increase R slightly, increase G slightly, decrease B)
        img_array[:, :, 0] = np.clip(img_array[:, :, 0] + yellow_strength * 255, 0, 255)
        img_array[:, :, 1] = np.clip(
            img_array[:, :, 1] + yellow_strength * 0.7 * 255, 0, 255
        )
        img_array[:, :, 2] = np.clip(
            img_array[:, :, 2] - yellow_strength * 0.5 * 255, 0, 255
        )

        # Contrast reduction (aged documents lose contrast)
        if profile == HybridProfile.AGED:
            contrast_factor = self._rng.uniform(0.85, 0.95)
        else:
            contrast_factor = self._rng.uniform(0.70, 0.85)
        mean_val = img_array.mean()
        img_array = mean_val + contrast_factor * (img_array - mean_val)
        img_array = np.clip(img_array, 0, 255)

        # Foxing spots (brown spots from mold/oxidation) - HISTORICAL only or light for AGED
        num_spots = 0
        if profile == HybridProfile.HISTORICAL:
            num_spots = self._rng.randint(5, 20)
        elif profile == HybridProfile.AGED and self._rng.random() < 0.4:
            num_spots = self._rng.randint(1, 5)

        h, w = img_array.shape[:2]
        for _ in range(num_spots):
            cx = self._rng.randint(0, w - 1)
            cy = self._rng.randint(0, h - 1)
            radius = self._rng.randint(3, 15)
            intensity = self._rng.uniform(0.3, 0.7)

            y_coords, x_coords = np.ogrid[
                max(0, cy - radius) : min(h, cy + radius),
                max(0, cx - radius) : min(w, cx + radius),
            ]
            dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
            spot_mask = dist < radius

            # Brown foxing color
            spot_color = np.array([165, 120, 70], dtype=np.float32)
            region = img_array[
                max(0, cy - radius) : min(h, cy + radius),
                max(0, cx - radius) : min(w, cx + radius),
            ]
            region[spot_mask] = (
                region[spot_mask] * (1 - intensity) + spot_color * intensity
            )

        # Ink fading for HISTORICAL
        if profile == HybridProfile.HISTORICAL and self._rng.random() < 0.6:
            fade = self._rng.uniform(0.05, 0.15)
            # Fade toward paper color (lighter)
            img_array = img_array + fade * (255 - img_array)
            severities["ink_degradation"] = fade * 3  # Scale to 0-0.45 range

        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        result = Image.fromarray(img_array)

        severities["paper_degradation"] = yellow_strength * 3 + num_spots * 0.02
        severities["paper_degradation"] = min(1.0, severities["paper_degradation"])

        return result, severities

    def _apply_albumentations_phase(
        self,
        image: Image.Image,
        profile: HybridProfile,
    ) -> tuple[Image.Image, dict[str, float]]:
        """Apply Albumentations fast general effects.

        This applies effects that Albumentations does well:
        - Blur (GaussianBlur, MotionBlur)
        - Noise (GaussNoise)
        - Compression (ImageCompression)
        - Geometric distortion (Rotate, Perspective)

        Args:
            image: Input PIL Image
            profile: Augmentation profile

        Returns:
            Tuple of (augmented image, severity dict)
        """
        severities = {
            "blur": 0.0,
            "noise": 0.0,
            "compression": 0.0,
            "geometric_distortion": 0.0,
        }

        if not ALBUMENTATIONS_AVAILABLE or profile == HybridProfile.PRISTINE:
            return image, severities

        # Skip Albumentations based on probability
        if self._rng.random() > self._albumentations_prob:
            return image, severities

        params = ALBUMENTATIONS_PARAMS[profile]
        transforms = []

        # Blur
        blur_limit = cast(int, params["blur_limit"])
        if blur_limit > 0:
            blur_choice = self._np_rng.choice(["gaussian", "motion"])
            if blur_choice == "gaussian":
                transforms.append(A.GaussianBlur(blur_limit=(3, blur_limit), p=0.5))
            else:
                transforms.append(A.MotionBlur(blur_limit=blur_limit, p=0.5))
            severities["blur"] = blur_limit / 7.0

        # Noise
        noise_var = cast(tuple[int, int], params["noise_var"])
        if noise_var[1] > 0:
            transforms.append(
                A.GaussNoise(
                    std_range=(noise_var[0] / 255.0, noise_var[1] / 255.0), p=0.5
                )
            )
            severities["noise"] = noise_var[1] / 50.0

        # Compression
        jpeg_quality = cast(tuple[int, int], params["jpeg_quality"])
        if jpeg_quality[0] < 95:
            transforms.append(
                A.ImageCompression(
                    quality_range=jpeg_quality,
                    compression_type="jpeg",
                    p=0.6,
                )
            )
            severities["compression"] = (95 - jpeg_quality[0]) / 65.0

        # Geometric distortion
        rotate = cast(int, params["rotate"])
        perspective = cast(float, params["perspective"])
        if rotate > 0:
            transforms.append(A.Rotate(limit=rotate, border_mode=0, fill=255, p=0.4))
        if perspective > 0:
            transforms.append(
                A.Perspective(
                    scale=(0.01, perspective), fit_output=True, fill=255, p=0.3
                )
            )
        if rotate > 0 or perspective > 0:
            severities["geometric_distortion"] = (rotate / 10.0 + perspective / 0.1) / 2

        if not transforms:
            return image, severities

        # Apply pipeline
        pipeline = A.Compose(transforms)
        img_array = np.array(image)

        try:
            result = pipeline(image=img_array)
            result_array = result["image"]
        except Exception as e:
            logger.warning("Albumentations failed: %s", e)
            return image, severities

        return Image.fromarray(result_array), severities

    def apply(
        self,
        image: Image.Image,
        profile: HybridProfile = HybridProfile.MODERATE,
    ) -> tuple[Image.Image, IQALabels]:
        """Apply hybrid augmentation to an image.

        Pipeline order:
        1. Augraphy (document effects: bleed-through, ink, paper)
        2. Albumentations (capture effects: blur, noise, compression, geometric)

        Args:
            image: Input PIL Image
            profile: Augmentation intensity profile

        Returns:
            Tuple of (augmented image, IQA labels)
        """
        if not HYBRID_AVAILABLE:
            return image, IQALabels(overall_quality=1.0)

        if profile == HybridProfile.PRISTINE:
            return image, IQALabels(overall_quality=1.0)

        # Phase 1: Augraphy document effects
        aug_image, aug_severities = self._apply_augraphy_phase(image, profile)
        augraphy_applied = any(v > 0 for v in aug_severities.values())

        # Phase 1.5: Document aging effects (AGED/HISTORICAL profiles only)
        if profile in (HybridProfile.AGED, HybridProfile.HISTORICAL):
            aug_image, aging_severities = self._apply_aging_effects(aug_image, profile)
            for key, value in aging_severities.items():
                aug_severities[key] = max(aug_severities.get(key, 0.0), value)

        # Phase 2: Albumentations capture effects
        result_image, alb_severities = self._apply_albumentations_phase(
            aug_image, profile
        )
        albumentations_applied = any(v > 0 for v in alb_severities.values())

        # Merge severities
        all_severities = {
            "blur": alb_severities.get("blur", 0.0),
            "noise": alb_severities.get("noise", 0.0),
            "compression": alb_severities.get("compression", 0.0),
            "ink_degradation": aug_severities.get("ink_degradation", 0.0),
            "paper_degradation": aug_severities.get("paper_degradation", 0.0),
            "geometric_distortion": alb_severities.get("geometric_distortion", 0.0),
            "bleed_through": aug_severities.get("bleed_through", 0.0),
        }

        # Calculate overall quality using max severity (not average)
        # This ensures severe defects properly reduce quality
        # (e.g., blur=1.0 should give quality ~0, not 0.93)
        max_severity = max(all_severities.values()) if all_severities else 0.0
        overall_quality = max(0.0, 1.0 - max_severity)

        # Create IQALabels (compatible with generator)
        labels = IQALabels(
            blur=all_severities["blur"],
            noise=all_severities["noise"],
            compression=all_severities["compression"],
            ink_degradation=all_severities["ink_degradation"],
            paper_degradation=all_severities["paper_degradation"],
            geometric_distortion=all_severities["geometric_distortion"],
            bleed_through=all_severities["bleed_through"],
            overall_quality=overall_quality,
        )

        if augraphy_applied or albumentations_applied:
            logger.debug(
                "Hybrid augmentation: augraphy=%s, albumentations=%s, bleed_through=%.2f",
                augraphy_applied,
                albumentations_applied,
                all_severities["bleed_through"],
            )

        return result_image, labels


__all__ = [
    "HYBRID_AVAILABLE",
    "HybridAugmentationPipeline",
    "HybridIQALabels",
    "HybridProfile",
]
