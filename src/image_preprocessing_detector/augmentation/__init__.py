"""Data augmentation and synthetic degradation modules.

This package provides tools for generating synthetic document degradations
to augment training data for IQA (Image Quality Assessment) models.

Modules:
    genalog_config: Configuration schemas for Genalog degradation parameters
    genalog_degrader: Wrapper for Microsoft Genalog synthetic degradation

Phase 2 Week 1: Genalog Integration
- Synthetic degradation generation for IQA training data
- Controllable degradation parameters (blur, noise, bleed-through)
- Sensitivity analysis support for threshold tuning
"""

from image_preprocessing_detector.augmentation.genalog_config import (
    BleedThroughConfig,
    BlurConfig,
    DegradationConfig,
    MorphologicalConfig,
    MorphologicalOperation,
    SaltPepperConfig,
)
from image_preprocessing_detector.augmentation.genalog_degrader import (
    GenalogDegrader,
    create_default_degrader,
)

__all__ = [
    "BleedThroughConfig",
    "BlurConfig",
    "DegradationConfig",
    "GenalogDegrader",
    "MorphologicalConfig",
    "MorphologicalOperation",
    "SaltPepperConfig",
    "create_default_degrader",
]
