"""Shared fixtures for integration tests.

Provides common fixtures for ML IQA integration tests including:
- ONNX runtime availability checking
- Model path validation
- ML detector creation with proper skip handling
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.iqa_ml import MLIQADetector


def _is_onnxruntime_functional() -> bool:
    """Check if onnxruntime is properly installed and functional.

    Returns True only if onnxruntime can be imported AND has InferenceSession.
    This handles the case where a namespace package exists but the actual
    package is not installed.
    """
    try:
        import onnxruntime as ort

        # Check for essential attribute - handles namespace package edge case
        return hasattr(ort, "InferenceSession")
    except ImportError:
        return False


@pytest.fixture(scope="session")
def onnxruntime_available() -> bool:
    """Session-scoped fixture to check if onnxruntime is functional."""
    return _is_onnxruntime_functional()


@pytest.fixture
def onnx_models_available(onnxruntime_available: bool) -> bool:
    """Check if ONNX models and runtime are available.

    This fixture checks both:
    1. onnxruntime is properly installed and functional
    2. Required model files exist
    """
    if not onnxruntime_available:
        return False

    # parents[2] goes from tests/integration/conftest.py -> tests/integration -> tests -> root
    model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"
    return student_path.exists() and teacher_path.exists()


@pytest.fixture
def require_onnx_models(onnx_models_available: bool) -> None:
    """Fixture that skips test if ONNX models/runtime not available.

    Use this fixture to skip tests that require ML inference.
    """
    if not onnx_models_available:
        pytest.skip("ONNX models or runtime not available")


@pytest.fixture
def ml_detector(
    onnx_models_available: bool, onnxruntime_available: bool
) -> "MLIQADetector | None":
    """Create ML IQA detector with real models if available.

    Skips the test if onnxruntime is not functional or models are missing.
    """
    if not onnxruntime_available:
        pytest.skip("onnxruntime not properly installed")

    if not onnx_models_available:
        pytest.skip("ONNX models not available")

    # Import here to avoid import errors when onnxruntime is missing
    from image_preprocessing_detector.detection.iqa_ml import (
        Device,
        MLIQADetector,
    )

    # parents[2] goes from tests/integration/conftest.py -> tests/integration -> tests -> root
    model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
    student_path = model_dir / "resnet18_student.onnx"
    teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

    return MLIQADetector(
        student_model_path=student_path,
        teacher_model_path=teacher_path,
        device=Device.CPU,
        enable_modal_fallback=False,
    )
