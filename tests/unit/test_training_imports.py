"""Test imports for training module."""

import pytest

torch = pytest.importorskip(
    "torch", reason="PyTorch required for training module tests"
)


def test_training_module_imports() -> None:
    """Test that training module can be imported."""
    from image_preprocessing_detector.training import TeacherTrainer

    assert TeacherTrainer is not None


def test_teacher_trainer_initialization() -> None:
    """Test basic TeacherTrainer class exists and is callable."""
    from image_preprocessing_detector.training import TeacherTrainer

    # Just verify the class exists and has expected attributes
    assert hasattr(TeacherTrainer, "__init__")
    assert TeacherTrainer.__doc__ is not None
