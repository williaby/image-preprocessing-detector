"""Machine learning models for image quality assessment.

This module contains deep learning models for document image quality assessment:
- ResNet-50 Teacher Model: High-capacity model for difficult/high-risk cases
- ResNet-18 Student Model: Fast production model trained via knowledge distillation
- Multi-head architectures for quality issue detection
- Loss functions for training multi-head models
- Knowledge distillation loss for teacher-student training
"""

from image_preprocessing_detector.models.loss_functions import (
    DistillationLoss,
    FocalLoss,
    MultiHeadIQALoss,
    WeightedMSELoss,
    compute_class_weights,
)
from image_preprocessing_detector.models.resnet_student import (
    ResNetStudent,
    StudentIQAHead,
)
from image_preprocessing_detector.models.resnet_teacher import (
    IQAHead,
    ResNetTeacher,
)

__all__ = [
    "DistillationLoss",
    "FocalLoss",
    "IQAHead",
    "MultiHeadIQALoss",
    "ResNetStudent",
    "ResNetTeacher",
    "StudentIQAHead",
    "WeightedMSELoss",
    "compute_class_weights",
]
