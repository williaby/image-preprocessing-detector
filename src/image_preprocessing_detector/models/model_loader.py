"""Model loading utilities for API and worker preloading.

Provides functions to load, warmup, and inspect ResNet IQA models
for the FastAPI application lifespan and Celery worker initialization.

These functions wrap the lower-level ONNX Runtime session management
with a simplified interface suitable for application-level preloading.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default model directory relative to project root
_DEFAULT_MODEL_DIR = Path(__file__).parents[3] / "models" / "iqa" / "onnx"


def load_student_model(
    *,
    device: str = "cpu",
    model_dir: Path | None = None,
) -> Any:
    """Load the ResNet-18 student IQA model.

    Args:
        device: Target device ("cpu" or "cuda").
        model_dir: Directory containing ONNX model files.
            Defaults to ``models/iqa/onnx/`` relative to the project root.

    Returns:
        An ONNX Runtime InferenceSession, or ``None`` if the model
        file is not found or onnxruntime is unavailable.
    """
    model_dir = model_dir or _DEFAULT_MODEL_DIR
    model_path = model_dir / "resnet18_student.onnx"

    if not model_path.exists():
        logger.warning("Student model not found at %s", model_path)
        return None

    try:
        from image_preprocessing_detector.models.onnx_runtime import (
            ONNXModelRunner,
            ONNXSessionConfig,
        )

        provider = (
            "CUDAExecutionProvider" if device == "cuda" else "CPUExecutionProvider"
        )
        config = ONNXSessionConfig(provider=provider)
        runner = ONNXModelRunner(model_path=model_path, config=config)
    except Exception:
        logger.warning(
            "Failed to load student model from %s", model_path, exc_info=True
        )
        return None
    else:
        logger.info("Student model loaded from %s (device=%s)", model_path, device)
        return runner


def load_teacher_model(
    *,
    device: str = "cpu",
    model_dir: Path | None = None,
) -> Any:
    """Load the ResNet-50 teacher IQA model.

    Args:
        device: Target device ("cpu" or "cuda").
        model_dir: Directory containing ONNX model files.
            Defaults to ``models/iqa/onnx/`` relative to the project root.

    Returns:
        An ONNX Runtime InferenceSession, or ``None`` if the model
        file is not found or onnxruntime is unavailable.
    """
    model_dir = model_dir or _DEFAULT_MODEL_DIR
    model_path = model_dir / "resnet50_teacher_50epoch.onnx"

    if not model_path.exists():
        logger.warning("Teacher model not found at %s", model_path)
        return None

    try:
        from image_preprocessing_detector.models.onnx_runtime import (
            ONNXModelRunner,
            ONNXSessionConfig,
        )

        provider = (
            "CUDAExecutionProvider" if device == "cuda" else "CPUExecutionProvider"
        )
        config = ONNXSessionConfig(provider=provider)
        runner = ONNXModelRunner(model_path=model_path, config=config)
    except Exception:
        logger.warning(
            "Failed to load teacher model from %s", model_path, exc_info=True
        )
        return None
    else:
        logger.info("Teacher model loaded from %s (device=%s)", model_path, device)
        return runner


def warmup_models(
    student_model: Any | None = None,
    teacher_model: Any | None = None,
) -> dict[str, float]:
    """Run dummy inference to warm up loaded models.

    Args:
        student_model: Loaded student model (or ``None``).
        teacher_model: Loaded teacher model (or ``None``).

    Returns:
        Dictionary with warmup timing statistics (milliseconds).
    """
    import time

    import numpy as np

    stats: dict[str, float] = {}
    dummy_input = np.random.default_rng(0).random((1, 3, 224, 224), dtype=np.float32)

    if student_model is not None:
        try:
            start = time.perf_counter()
            if hasattr(student_model, "run"):
                student_model.run(dummy_input)
            elapsed = (time.perf_counter() - start) * 1000
            stats["student_warmup_ms"] = round(elapsed, 2)
            logger.info("Student warmup completed in %.1fms", elapsed)
        except Exception:
            logger.warning("Student warmup failed", exc_info=True)
            stats["student_warmup_ms"] = -1.0

    if teacher_model is not None:
        try:
            start = time.perf_counter()
            if hasattr(teacher_model, "run"):
                teacher_model.run(dummy_input)
            elapsed = (time.perf_counter() - start) * 1000
            stats["teacher_warmup_ms"] = round(elapsed, 2)
            logger.info("Teacher warmup completed in %.1fms", elapsed)
        except Exception:
            logger.warning("Teacher warmup failed", exc_info=True)
            stats["teacher_warmup_ms"] = -1.0

    return stats


def get_model_info(model: Any) -> dict[str, Any]:
    """Extract metadata from a loaded model.

    Args:
        model: A loaded model instance (ONNXModelRunner or similar).

    Returns:
        Dictionary with model metadata (name, device, input shape, etc.).
    """
    info: dict[str, Any] = {"type": type(model).__name__}

    if hasattr(model, "config"):
        config = model.config
        if hasattr(config, "model_path"):
            info["model_path"] = str(config.model_path)
        if hasattr(config, "device"):
            info["device"] = config.device

    if hasattr(model, "session"):
        session = model.session
        if hasattr(session, "get_inputs"):
            inputs = session.get_inputs()
            if inputs:
                info["input_name"] = inputs[0].name
                info["input_shape"] = inputs[0].shape

    return info
