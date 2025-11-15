"""Document-specific image augmentation pipeline for IQA training.

This module implements Albumentations-based augmentation for generating synthetic
quality issues in clean document images. Supports noise, blur, contrast, perspective,
orientation, and compression artifacts.

Phase 2 - Week 1: Data Collection & Augmentation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import albumentations as alb
import cv2
import numpy as np
from numpy.typing import NDArray


class DocumentAugmentationPipeline:
    """Document-specific augmentation pipeline for IQA training.

    Generates realistic quality issues in document images:
    - Noise (Gaussian, ISO, multiplicative)
    - Blur (Gaussian, motion, defocus)
    - Low contrast (brightness/contrast reduction)
    - Perspective distortion
    - Orientation (rotation)
    - Compression artifacts (JPEG)

    Args:
        augmentation_probability: Overall probability of applying augmentations (default: 1.0)
        noise_probability: Probability of adding noise (default: 0.20)
        blur_probability: Probability of adding blur (default: 0.15)
        contrast_probability: Probability of reducing contrast (default: 0.15)
        perspective_probability: Probability of perspective distortion (default: 0.10)
        orientation_probability: Probability of rotation (default: 0.05)
        compression_probability: Probability of JPEG compression (default: 0.10)
        random_seed: Random seed for reproducibility (default: None)

    Example:
        >>> pipeline = DocumentAugmentationPipeline()
        >>> image = cv2.imread("document.png")
        >>> augmented = pipeline(image)
        >>> params = pipeline.get_last_params()
    """

    def __init__(
        self,
        augmentation_probability: float = 1.0,
        noise_probability: float = 0.20,
        blur_probability: float = 0.15,
        contrast_probability: float = 0.15,
        perspective_probability: float = 0.10,
        orientation_probability: float = 0.05,
        compression_probability: float = 0.10,
        random_seed: int | None = None,
    ) -> None:
        """Initialize document augmentation pipeline."""
        self.noise_prob = noise_probability
        self.blur_prob = blur_probability
        self.contrast_prob = contrast_probability
        self.perspective_prob = perspective_probability
        self.orientation_prob = orientation_probability
        self.compression_prob = compression_probability

        # Build Albumentations pipeline
        self.transform = alb.Compose(
            [
                # Noise augmentations (20% probability)
                alb.OneOf(
                    [
                        alb.GaussNoise(
                            var_limit=(10.0, 50.0),
                            mean=0,
                            per_channel=True,
                            p=0.5,
                        ),
                        alb.ISONoise(
                            color_shift=(0.01, 0.05),
                            intensity=(0.1, 0.5),
                            p=0.3,
                        ),
                        alb.MultiplicativeNoise(
                            multiplier=(0.9, 1.1),
                            per_channel=True,
                            elementwise=True,
                            p=0.2,
                        ),
                    ],
                    p=noise_probability,
                ),
                # Blur augmentations (15% probability)
                alb.OneOf(
                    [
                        alb.GaussianBlur(
                            blur_limit=(3, 7),
                            sigma_limit=(0.1, 2.0),
                            p=0.4,
                        ),
                        alb.MotionBlur(
                            blur_limit=(3, 7),
                            allow_shifted=True,
                            p=0.3,
                        ),
                        alb.Defocus(
                            radius=(3, 7),
                            alias_blur=(0.1, 0.5),
                            p=0.2,
                        ),
                        alb.MedianBlur(
                            blur_limit=7,
                            p=0.1,
                        ),
                    ],
                    p=blur_probability,
                ),
                # Low contrast augmentations (15% probability)
                alb.OneOf(
                    [
                        alb.RandomBrightnessContrast(
                            brightness_limit=(-0.2, 0.1),
                            contrast_limit=(-0.3, 0.1),
                            p=0.5,
                        ),
                        alb.CLAHE(
                            clip_limit=(1.0, 2.0),
                            tile_grid_size=(8, 8),
                            p=0.3,
                        ),
                        alb.Equalize(
                            mode="cv",
                            by_channels=True,
                            p=0.2,
                        ),
                    ],
                    p=contrast_probability,
                ),
                # Perspective distortion (10% probability)
                alb.Perspective(
                    scale=(0.02, 0.10),
                    keep_size=True,
                    pad_mode=cv2.BORDER_CONSTANT,
                    pad_val=255,
                    fit_output=True,
                    p=perspective_probability,
                ),
                # Rotation (orientation issues) (5% probability)
                # Note: Only use small angles for skew, not full 180° rotation here
                alb.Rotate(
                    limit=10,  # ±10 degrees for skew
                    interpolation=cv2.INTER_LINEAR,
                    border_mode=cv2.BORDER_CONSTANT,
                    value=255,
                    p=orientation_probability,
                ),
                # Compression artifacts (10% probability)
                alb.ImageCompression(
                    quality_lower=50,
                    quality_upper=95,
                    p=compression_probability,
                ),
                # Downscale and upscale (simulates low-resolution scans)
                alb.Downscale(
                    scale_min=0.5,
                    scale_max=0.9,
                    interpolation=cv2.INTER_LINEAR,
                    p=0.20,
                ),
            ],
            p=augmentation_probability,
        )

        # Separate transform for large rotations (90/180/270°)
        self.orientation_transform = alb.Compose(
            [
                alb.RandomRotate90(
                    p=1.0
                ),  # Rotate by 90/180/270° with equal probability
            ],
            p=0.0,  # Controlled separately
        )

        self._last_params: dict[str, Any] = {}
        if random_seed is not None:
            import random
            import numpy as np

            random.seed(random_seed)
            np.random.seed(random_seed)

    def __call__(
        self,
        image: NDArray[np.uint8],
        apply_orientation: bool = False,
    ) -> NDArray[np.uint8]:
        """Apply augmentations to image.

        Args:
            image: Input image (H, W, C) in BGR format
            apply_orientation: If True, apply 90/180/270° rotation (default: False)

        Returns:
            Augmented image (H, W, C) in BGR format

        Example:
            >>> pipeline = DocumentAugmentationPipeline()
            >>> image = cv2.imread("document.png")
            >>> augmented = pipeline(image)
            >>> augmented_rotated = pipeline(image, apply_orientation=True)
        """
        # Apply main augmentations
        transformed = self.transform(image=image)
        augmented_image = transformed["image"]

        # Store parameters from last augmentation
        self._last_params = {
            "applied_transforms": [
                t.__class__.__name__
                for t in self.transform.transforms
                if hasattr(t, "p") and t.p > 0
            ],
            "augmentation_applied": True,
        }

        # Optionally apply large rotation (90/180/270°)
        if apply_orientation:
            rotated = self.orientation_transform(image=augmented_image)
            augmented_image = rotated["image"]
            self._last_params["orientation_applied"] = True
        else:
            self._last_params["orientation_applied"] = False

        return augmented_image

    def get_last_params(self) -> dict[str, Any]:
        """Get parameters from last augmentation.

        Returns:
            Dictionary containing:
            - applied_transforms: List of transform class names
            - main_augmentations: Albumentations parameters
            - orientation_applied: Whether orientation transform was applied
            - orientation_params: Orientation transform parameters (if applied)

        Example:
            >>> pipeline = DocumentAugmentationPipeline()
            >>> augmented = pipeline(image)
            >>> params = pipeline.get_last_params()
            >>> print(params["applied_transforms"])
        """
        return self._last_params

    def save_augmented_image(
        self,
        image: NDArray[np.uint8],
        output_path: str | Path,
        apply_orientation: bool = False,
    ) -> dict[str, Any]:
        """Apply augmentations and save image with metadata.

        Args:
            image: Input image (H, W, C) in BGR format
            output_path: Path to save augmented image
            apply_orientation: If True, apply 90/180/270° rotation (default: False)

        Returns:
            Dictionary with augmentation metadata and output path

        Example:
            >>> pipeline = DocumentAugmentationPipeline()
            >>> image = cv2.imread("document.png")
            >>> metadata = pipeline.save_augmented_image(
            ...     image, "augmented.png", apply_orientation=True
            ... )
        """
        # Apply augmentations
        augmented = self(image, apply_orientation=apply_orientation)

        # Save image
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), augmented)

        # Return metadata
        return {
            "output_path": str(output_path),
            "input_shape": image.shape,
            "output_shape": augmented.shape,
            "augmentation_params": self.get_last_params(),
        }


# Preset configurations for different use cases
PRESETS = {
    "light": {
        "noise_probability": 0.10,
        "blur_probability": 0.08,
        "contrast_probability": 0.08,
        "perspective_probability": 0.05,
        "orientation_probability": 0.02,
        "compression_probability": 0.05,
    },
    "medium": {  # Default (balanced)
        "noise_probability": 0.20,
        "blur_probability": 0.15,
        "contrast_probability": 0.15,
        "perspective_probability": 0.10,
        "orientation_probability": 0.05,
        "compression_probability": 0.10,
    },
    "heavy": {
        "noise_probability": 0.35,
        "blur_probability": 0.25,
        "contrast_probability": 0.25,
        "perspective_probability": 0.20,
        "orientation_probability": 0.10,
        "compression_probability": 0.20,
    },
}


def create_augmentation_pipeline(
    preset: str = "medium",
    **kwargs: Any,
) -> DocumentAugmentationPipeline:
    """Create augmentation pipeline with preset configuration.

    Args:
        preset: Preset name ("light", "medium", "heavy")
        **kwargs: Override specific parameters

    Returns:
        Configured DocumentAugmentationPipeline

    Example:
        >>> pipeline = create_augmentation_pipeline("heavy")
        >>> pipeline = create_augmentation_pipeline("medium", noise_probability=0.30)
    """
    if preset not in PRESETS:
        msg = f"Unknown preset: {preset}. Choose from {list(PRESETS.keys())}"
        raise ValueError(msg)

    config = PRESETS[preset].copy()
    config.update(kwargs)
    return DocumentAugmentationPipeline(**config)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 3:
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Load image
    image = cv2.imread(input_path)
    if image is None:
        sys.exit(1)

    # Apply augmentations
    pipeline = create_augmentation_pipeline("medium")
    metadata = pipeline.save_augmented_image(image, output_path)
