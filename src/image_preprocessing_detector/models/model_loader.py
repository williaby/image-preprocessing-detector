"""Model loading utilities for API and worker preloading.

Provides functions to load, warmup, and inspect ResNet IQA models
for the FastAPI application lifespan and Celery worker initialization.

These functions wrap the lower-level ONNX Runtime session management
with a simplified interface suitable for application-level preloading.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)

# Default model directory relative to this package's models/ directory
_DEFAULT_MODEL_DIR = Path(__file__).parent / "onnx"

_VALID_DEVICES = {"cpu", "cuda"}


def _load_model(
    *,
    model_filename: str,
    label: str,
    device: str,
    model_dir: Path | None,
) -> Any:
    """Load an ONNX IQA model.

    Args:
        model_filename: ONNX model filename (e.g., ``resnet18_student.onnx``).
        label: Human-readable label for log messages (e.g., ``"Student"``).
        device: Target device (``"cpu"`` or ``"cuda"``).
        model_dir: Directory containing ONNX model files.
            Defaults to ``models/iqa/onnx/`` relative to the project root.

    Returns:
        An ``ONNXModelRunner`` instance, or ``None`` if the model
        file is not found or onnxruntime is unavailable.
    """
    device = device.lower()
    if device not in _VALID_DEVICES:
        logger.warning(
            "Unknown device %r for %s model, falling back to cpu", device, label
        )
        device = "cpu"

    model_dir = model_dir or _DEFAULT_MODEL_DIR
    model_path = model_dir / model_filename

    if not model_path.exists():
        logger.warning("%s model not found at %s", label, model_path)
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
    except (ValueError, OSError, ImportError) as exc:
        logger.warning("Failed to load %s model from %s: %s", label, model_path, exc)
        return None
    else:
        logger.info("%s model loaded from %s (device=%s)", label, model_path, device)
        return runner


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
        An ``ONNXModelRunner`` instance, or ``None`` if the model
        file is not found or onnxruntime is unavailable.
    """
    return _load_model(
        model_filename="resnet18_student.onnx",
        label="Student",
        device=device,
        model_dir=model_dir,
    )


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
        An ``ONNXModelRunner`` instance, or ``None`` if the model
        file is not found or onnxruntime is unavailable.
    """
    return _load_model(
        model_filename="resnet50_teacher_50epoch.onnx",
        label="Teacher",
        device=device,
        model_dir=model_dir,
    )


def _warmup_single_model(
    model: Any,
    label: str,
    dummy_input: Any,
) -> float:
    """Run dummy inference on a single model and return elapsed time in ms.

    Returns:
        Elapsed time in milliseconds, or -1.0 on failure.
    """
    import time

    try:
        if not hasattr(model, "run"):
            logger.warning("%s model has no 'run' method, skipping warmup", label)
            return -1.0
        start = time.perf_counter()
        model.run(dummy_input)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s warmup completed in %.1fms", label, elapsed)
        return round(elapsed, 2)
    except Exception:
        logger.warning("%s warmup failed", label, exc_info=True)
        return -1.0


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
    import numpy as np

    stats: dict[str, float] = {}
    dummy_input = np.random.default_rng(0).random((1, 3, 224, 224), dtype=np.float32)

    if student_model is not None:
        stats["student_warmup_ms"] = _warmup_single_model(
            student_model, "Student", dummy_input
        )

    if teacher_model is not None:
        stats["teacher_warmup_ms"] = _warmup_single_model(
            teacher_model, "Teacher", dummy_input
        )

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
