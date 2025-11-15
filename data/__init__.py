"""Data collection, augmentation, and labeling utilities for Phase 2.

This package contains modules for:
- augmentation.py: Albumentations-based document augmentation
- weak_supervision.py: Automatic labeling using image quality metrics
- dataset.py: PyTorch Dataset classes for training
"""

from data.augmentation import (
    PRESETS,
    DocumentAugmentationPipeline,
    create_augmentation_pipeline,
)

__all__ = [
    "PRESETS",
    "DocumentAugmentationPipeline",
    "create_augmentation_pipeline",
]
