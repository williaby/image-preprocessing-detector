# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Conftest for benchmark tests.

Inherits fixtures from integration conftest for ML model availability.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.iqa_ml import MLIQADetector


def _is_onnxruntime_functional() -> bool:
    """Check if onnxruntime is properly installed and functional."""
    try:
        import onnxruntime as ort

        return hasattr(ort, "InferenceSession")
    except ImportError:
        return False


@pytest.fixture(scope="session")
def onnxruntime_available() -> bool:
    """Session-scoped fixture to check if onnxruntime is functional."""
    return _is_onnxruntime_functional()


@pytest.fixture
def onnx_models_available(onnxruntime_available: bool) -> bool:
    """Check if ONNX models and runtime are available."""
    if not onnxruntime_available:
        return False

    model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"
    return student_path.exists() and teacher_path.exists()
