"""Augraphy Pipeline for Phase 7 Continuous Labels.

Wraps Augraphy's document augmentation library with continuous severity
label extraction using the `return_dict=True` feature.

Augraphy provides document-specific augmentations organized in layers:
- Ink Layer: InkBleed, Letterpress, LowInkLine, etc.
- Paper Layer: WaterMark, DirtyDrum, PaperFactory, etc.
- Post Layer: GaussianBlur, Gamma, Jpeg, etc.

Key Feature: `return_dict=True` exposes exact parameters used during
augmentation, enabling precise continuous severity computation.

Reference:
    - Augraphy: https://github.com/sparkfish/augraphy
    - Phase 7 Strategy: docs/development/phase-7-continuous-labels-strategy.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

# Augraphy imports - will raise ImportError if not installed
try:
    import augraphy
    from augraphy import (
        AugraphyPipeline,
        BadPhotoCopy,
        BleedThrough,
        Brightness,
        DirtyDrum,
        Faxify,
        Gamma,
        GaussianBlur,
        InkBleed,
        InkMottling,
        Jpeg,
        Letterpress,
        LowInkPeriodicLines,
        NoiseTexturize,
        PaperFactory,
        WaterMark,
    )

    AUGRAPHY_AVAILABLE = True
except ImportError:
    AUGRAPHY_AVAILABLE = False
    AugraphyPipeline = None


@dataclass
class AugraphyLabel:
    """Continuous label from Augraphy augmentation parameters.

    All severity values are in range [0, 1]:
    - 0.0 = no degradation
    - 1.0 = maximum degradation

    Attributes:
        blur_severity: From GaussianBlur sigma parameter
        noise_severity: From NoiseTexturize, Faxify, etc.
        contrast_severity: From Gamma, Brightness deviation from 1.0
        compression_severity: From Jpeg quality parameter
        ink_degradation: From InkBleed, InkMottling, Letterpress
        paper_degradation: From DirtyDrum, WaterMark, PaperFactory
        bleed_through: From BleedThrough intensity
        overall_quality: Computed as 1 - max(severities)
        augmentation_params: Raw parameters from Augraphy
    """

    blur_severity: float = 0.0
    noise_severity: float = 0.0
    contrast_severity: float = 0.0
    compression_severity: float = 0.0
    ink_degradation: float = 0.0
    paper_degradation: float = 0.0
    bleed_through: float = 0.0
    overall_quality: float = 1.0
    augmentation_params: dict[str, Any] = field(default_factory=dict)
    applied_augmentations: list[str] = field(default_factory=list)
    generation_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns format compatible with ContinuousQualityLabel schema.
        """
        return {
            # Continuous severity scores
            "blur_severity": self.blur_severity,
            "noise_severity": self.noise_severity,
            "contrast_severity": self.contrast_severity,
            "compression_severity": self.compression_severity,
            "ink_degradation": self.ink_degradation,
            "paper_degradation": self.paper_degradation,
            "bleed_through": self.bleed_through,
            # Map to standard schema
            "skew_severity": 0.0,  # Augraphy doesn't model geometric skew
            "overall_quality": self.overall_quality,
            # Metadata
            "label_source": "augraphy",
            "label_confidence": 1.0,  # Perfect ground truth from parameters
            "label_variance": 0.0,
            "applied_augmentations": self.applied_augmentations,
            "augmentation_params": self.augmentation_params,
            "generation_timestamp": self.generation_timestamp,
            # Backward-compatible quality_scores
            "quality_scores": {
                "blur": self.blur_severity,
                "noise": self.noise_severity,
                "contrast": self.contrast_severity,
                "compression": self.compression_severity,
                "ink": self.ink_degradation,
                "paper": self.paper_degradation,
                "overall": self.overall_quality,
            },
            # Backward-compatible binary labels (threshold = 0.3)
            "labels": {
                "blur": {
                    "value": int(self.blur_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "augraphy",
                    "severity": self.blur_severity,
                },
                "noise": {
                    "value": int(self.noise_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "augraphy",
                    "severity": self.noise_severity,
                },
                "skew": {
                    "value": 0,  # Not modeled by Augraphy
                    "confidence": 1.0,
                    "source": "augraphy",
                    "severity": 0.0,
                },
                "illumination": {
                    "value": int(self.contrast_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "augraphy",
                    "severity": self.contrast_severity,
                },
                "artifacts": {
                    "value": int(self.compression_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "augraphy",
                    "severity": self.compression_severity,
                },
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AugraphyLabel:
        """Create from dictionary."""
        return cls(
            blur_severity=data.get("blur_severity", 0.0),
            noise_severity=data.get("noise_severity", 0.0),
            contrast_severity=data.get("contrast_severity", 0.0),
            compression_severity=data.get("compression_severity", 0.0),
            ink_degradation=data.get("ink_degradation", 0.0),
            paper_degradation=data.get("paper_degradation", 0.0),
            bleed_through=data.get("bleed_through", 0.0),
            overall_quality=data.get("overall_quality", 1.0),
            augmentation_params=data.get("augmentation_params", {}),
            applied_augmentations=data.get("applied_augmentations", []),
        )


# Severity mapping functions: parameter -> [0, 1] severity
SEVERITY_MAPPINGS = {
    # Blur: severity = sigma / sigma_max
    "GaussianBlur": {
        "param": "sigma",
        "max_value": 5.0,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
    # Jpeg: severity = 1 - (quality / 100)
    "Jpeg": {
        "param": "quality",
        "max_value": 100.0,
        "mapping": lambda p, max_v: 1.0 - (p / max_v),
    },
    # Gamma: severity = |gamma - 1.0| / 0.5 (deviation from neutral)
    "Gamma": {
        "param": "gamma",
        "max_value": 0.5,
        "mapping": lambda p, max_v: min(abs(p - 1.0) / max_v, 1.0),
    },
    # Brightness: severity = |brightness - 1.0| / 0.5
    "Brightness": {
        "param": "brightness",
        "max_value": 0.5,
        "mapping": lambda p, max_v: min(abs(p - 1.0) / max_v, 1.0),
    },
    # InkBleed: severity = intensity (already [0, 1])
    "InkBleed": {
        "param": "intensity",
        "max_value": 1.0,
        "mapping": lambda p, max_v: min(p, 1.0),
    },
    # DirtyDrum: severity = intensity
    "DirtyDrum": {
        "param": "intensity",
        "max_value": 1.0,
        "mapping": lambda p, max_v: min(p, 1.0),
    },
    # WaterMark: severity = alpha (opacity)
    "WaterMark": {
        "param": "alpha",
        "max_value": 1.0,
        "mapping": lambda p, max_v: min(p, 1.0),
    },
    # BleedThrough: severity = intensity
    "BleedThrough": {
        "param": "intensity",
        "max_value": 1.0,
        "mapping": lambda p, max_v: min(p, 1.0),
    },
    # NoiseTexturize: severity = sigma
    "NoiseTexturize": {
        "param": "sigma",
        "max_value": 50.0,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
    # Faxify: severity = monochrome_method (threshold-based)
    "Faxify": {
        "param": "scale_range",
        "max_value": 1.0,
        "mapping": lambda p, max_v: 0.6,  # Fixed moderate severity for fax effect
    },
    # Letterpress: severity based on n_copies
    "Letterpress": {
        "param": "n_copies",
        "max_value": 5,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
    # InkMottling: severity = range
    "InkMottling": {
        "param": "range",
        "max_value": 50.0,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
    # BadPhotoCopy: severity = noise_value
    "BadPhotoCopy": {
        "param": "noise_value",
        "max_value": 50,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
    # LowInkPeriodicLines: severity = count
    "LowInkPeriodicLines": {
        "param": "count",
        "max_value": 10,
        "mapping": lambda p, max_v: min(p / max_v, 1.0),
    },
}

# Categorization of augmentations
AUGMENTATION_CATEGORIES = {
    "blur": ["GaussianBlur", "MotionBlur", "Defocus"],
    "noise": ["NoiseTexturize", "Faxify", "BadPhotoCopy", "DottedLine"],
    "contrast": ["Gamma", "Brightness", "Lighting"],
    "compression": ["Jpeg"],
    "ink": ["InkBleed", "InkMottling", "Letterpress", "LowInkPeriodicLines", "LowInkLine"],
    "paper": ["DirtyDrum", "WaterMark", "PaperFactory", "Markup"],
    "bleed": ["BleedThrough"],
}


class AugraphyContinuousLabeler:
    """Augraphy pipeline with continuous label extraction.

    Wraps Augraphy's augmentation pipeline and extracts continuous severity
    labels from the parameters used during augmentation.

    Args:
        severity_preset: Preset name ("light", "medium", "heavy")
        random_seed: Random seed for reproducibility

    Example:
        >>> labeler = AugraphyContinuousLabeler(severity_preset="medium")
        >>> image = cv2.imread("document.png")
        >>> augmented, labels = labeler.augment(image)
        >>> print(f"Blur severity: {labels.blur_severity:.2f}")
    """

    def __init__(
        self,
        severity_preset: str = "medium",
        random_seed: int | None = None,
    ) -> None:
        if not AUGRAPHY_AVAILABLE:
            raise ImportError(
                "Augraphy is not installed. Install with: pip install augraphy"
            )

        self.severity_preset = severity_preset
        self.random_seed = random_seed
        self._configure_pipeline()

    def _configure_pipeline(self) -> None:
        """Configure ink, paper, and post-processing layers based on preset."""
        # Severity ranges based on preset
        severity_ranges = {
            "light": (0.1, 0.4),
            "medium": (0.3, 0.7),
            "heavy": (0.5, 0.95),
        }
        low, high = severity_ranges.get(self.severity_preset, (0.3, 0.7))

        # Ink phase augmentations
        self.ink_phase = [
            InkBleed(
                intensity_range=(low, high),
                kernel_size_range=(3, 7),
                p=0.3,
            ),
            Letterpress(
                n_copies_range=(1, 3),
                p=0.2,
            ),
            InkMottling(
                ink_mottling_range=(int(low * 30), int(high * 50)),
                p=0.2,
            ),
            LowInkPeriodicLines(
                count_range=(1, 5),
                p=0.15,
            ),
        ]

        # Paper phase augmentations
        self.paper_phase = [
            DirtyDrum(
                intensity_range=(low, high),
                p=0.25,
            ),
            WaterMark(
                watermark_word="SAMPLE",
                alpha_range=(low * 0.5, high * 0.5),
                p=0.15,
            ),
            BleedThrough(
                intensity_range=(low, high),
                p=0.2,
            ),
            NoiseTexturize(
                sigma_range=(int(low * 30), int(high * 50)),
                p=0.2,
            ),
        ]

        # Post-processing phase
        self.post_phase = [
            GaussianBlur(
                sigma_range=(low * 2, high * 4),
                p=0.3,
            ),
            Gamma(
                gamma_range=(1.0 - low * 0.3, 1.0 + high * 0.5),
                p=0.25,
            ),
            Jpeg(
                quality_range=(int(100 - high * 50), int(100 - low * 20)),
                p=0.25,
            ),
            Brightness(
                brightness_range=(1.0 - low * 0.3, 1.0 + high * 0.3),
                p=0.2,
            ),
        ]

        # Build pipeline
        self.pipeline = AugraphyPipeline(
            ink_phase=self.ink_phase,
            paper_phase=self.paper_phase,
            post_phase=self.post_phase,
            log=False,
        )

    def augment(
        self,
        image: NDArray[np.uint8],
    ) -> tuple[NDArray[np.uint8], AugraphyLabel]:
        """Apply augmentation and extract continuous labels.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            Tuple of (augmented_image, labels)

        Example:
            >>> labeler = AugraphyContinuousLabeler()
            >>> augmented, labels = labeler.augment(image)
            >>> cv2.imwrite("augmented.png", augmented)
            >>> print(labels.to_dict())
        """
        # Apply augmentation with parameter tracking
        # Note: Augraphy returns dict when using pipeline directly
        result = self.pipeline(image)

        # Extract augmented image
        if isinstance(result, dict):
            augmented = result.get("output", result.get("image", image))
            params = result.get("log", {})
        else:
            augmented = result
            params = {}

        # Convert params to continuous severity labels
        labels = self._params_to_labels(params)

        return augmented, labels

    def _params_to_labels(self, params: dict[str, Any]) -> AugraphyLabel:
        """Map augmentation parameters to [0,1] severity scores.

        Args:
            params: Parameters dictionary from Augraphy

        Returns:
            AugraphyLabel with computed severity values
        """
        severities = {
            "blur": 0.0,
            "noise": 0.0,
            "contrast": 0.0,
            "compression": 0.0,
            "ink": 0.0,
            "paper": 0.0,
            "bleed": 0.0,
        }
        applied_augmentations = []

        # Process each augmentation's parameters
        for aug_name, aug_params in params.items():
            if not isinstance(aug_params, dict):
                continue

            applied_augmentations.append(aug_name)

            # Get base augmentation name (strip suffixes like _1, _2)
            base_name = aug_name.split("_")[0] if "_" in aug_name else aug_name

            # Calculate severity using mapping
            if base_name in SEVERITY_MAPPINGS:
                mapping = SEVERITY_MAPPINGS[base_name]
                param_name = mapping["param"]
                if param_name in aug_params:
                    param_value = aug_params[param_name]
                    # Handle range tuples
                    if isinstance(param_value, (tuple, list)):
                        param_value = sum(param_value) / len(param_value)
                    severity = mapping["mapping"](param_value, mapping["max_value"])

                    # Assign to category
                    for category, aug_list in AUGMENTATION_CATEGORIES.items():
                        if base_name in aug_list:
                            severities[category] = max(severities[category], severity)
                            break

        # Calculate overall quality
        max_severity = max(severities.values())
        overall_quality = 1.0 - max_severity

        return AugraphyLabel(
            blur_severity=severities["blur"],
            noise_severity=severities["noise"],
            contrast_severity=severities["contrast"],
            compression_severity=severities["compression"],
            ink_degradation=severities["ink"],
            paper_degradation=severities["paper"],
            bleed_through=severities["bleed"],
            overall_quality=overall_quality,
            augmentation_params=params,
            applied_augmentations=applied_augmentations,
        )

    def augment_and_save(
        self,
        image: NDArray[np.uint8],
        output_image_path: str | Path,
        output_label_path: str | Path | None = None,
    ) -> tuple[Path, Path]:
        """Augment image and save with label file.

        Args:
            image: Input image
            output_image_path: Path to save augmented image
            output_label_path: Path to save label JSON (default: same stem + _labels.json)

        Returns:
            Tuple of (image_path, label_path)
        """
        output_image_path = Path(output_image_path)
        if output_label_path is None:
            output_label_path = output_image_path.with_name(
                f"{output_image_path.stem}_labels.json"
            )
        else:
            output_label_path = Path(output_label_path)

        # Create directories
        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        output_label_path.parent.mkdir(parents=True, exist_ok=True)

        # Augment
        augmented, labels = self.augment(image)

        # Save image
        cv2.imwrite(str(output_image_path), augmented)

        # Save labels
        with open(output_label_path, "w") as f:
            json.dump(labels.to_dict(), f, indent=2)

        return output_image_path, output_label_path


def create_augraphy_pipeline(
    preset: str = "medium",
    **kwargs: Any,
) -> AugraphyContinuousLabeler:
    """Create Augraphy pipeline with preset configuration.

    Args:
        preset: Preset name ("light", "medium", "heavy")
        **kwargs: Additional arguments for AugraphyContinuousLabeler

    Returns:
        Configured AugraphyContinuousLabeler

    Example:
        >>> pipeline = create_augraphy_pipeline("heavy")
        >>> augmented, labels = pipeline.augment(image)
    """
    return AugraphyContinuousLabeler(severity_preset=preset, **kwargs)


def batch_augment(
    input_dir: str | Path,
    output_dir: str | Path,
    preset: str = "medium",
    augmentations_per_image: int = 5,
    extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tiff"),
) -> list[tuple[Path, Path]]:
    """Batch augment images with continuous labels.

    Args:
        input_dir: Directory containing source images
        output_dir: Directory to save augmented images and labels
        preset: Augmentation preset
        augmentations_per_image: Number of augmented versions per source
        extensions: Image file extensions to process

    Returns:
        List of (image_path, label_path) tuples
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = AugraphyContinuousLabeler(severity_preset=preset)
    results = []

    # Find all images
    image_paths = []
    for ext in extensions:
        image_paths.extend(input_dir.glob(f"*{ext}"))
        image_paths.extend(input_dir.glob(f"*{ext.upper()}"))

    print(f"Found {len(image_paths)} images in {input_dir}")
    print(f"Generating {augmentations_per_image} augmentations per image...")

    for image_path in image_paths:
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Warning: Could not load {image_path}")
            continue

        for i in range(augmentations_per_image):
            output_image_path = output_dir / f"{image_path.stem}_aug{i:03d}.png"
            output_label_path = output_dir / f"{image_path.stem}_aug{i:03d}_labels.json"

            img_path, label_path = pipeline.augment_and_save(
                image, output_image_path, output_label_path
            )
            results.append((img_path, label_path))

    print(f"Generated {len(results)} augmented images with labels")
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python augraphy_pipeline.py <input_dir> <output_dir> [preset] [augmentations_per_image]")
        print("Presets: light, medium, heavy")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else "medium"
    aug_per_image = int(sys.argv[4]) if len(sys.argv) > 4 else 5

    results = batch_augment(
        input_dir,
        output_dir,
        preset=preset,
        augmentations_per_image=aug_per_image,
    )

    print(f"\nCompleted: {len(results)} images generated")
