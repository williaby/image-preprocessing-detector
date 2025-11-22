"""Machine learning models for image quality assessment.

This module contains deep learning models for document image quality assessment:
- ResNet-50 Teacher Model: High-capacity model for difficult/high-risk cases
- ResNet-18 Student Model: Fast production model (to be implemented)
- Multi-head architectures for quality issue detection
- Loss functions for training multi-head models
"""

from image_preprocessing_detector.models.loss_functions import (
    FocalLoss,
    MultiHeadIQALoss,
    WeightedMSELoss,
    compute_class_weights,
)
from image_preprocessing_detector.models.resnet_teacher import (
    IQAHead,
    ResNetTeacher,
)

__all__ = [
    "FocalLoss",
    "IQAHead",
    "MultiHeadIQALoss",
    "ResNetTeacher",
    "WeightedMSELoss",
    "compute_class_weights",
]
