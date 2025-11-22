"""Training utilities for deep learning models.

This module contains training loops, validation logic, and checkpointing
utilities for the teacher and student IQA models.
- TeacherTrainer: Training loop for ResNet-50 teacher model
- StudentTrainer: Knowledge distillation training for ResNet-18 student model
"""

from image_preprocessing_detector.training.student_trainer import StudentTrainer
from image_preprocessing_detector.training.teacher_trainer import TeacherTrainer

__all__ = ["StudentTrainer", "TeacherTrainer"]
