"""Training utilities for deep learning models.

This module contains training loops, validation logic, and checkpointing
utilities for the teacher and student IQA models.
"""

from image_preprocessing_detector.training.teacher_trainer import TeacherTrainer

__all__ = ["TeacherTrainer"]
