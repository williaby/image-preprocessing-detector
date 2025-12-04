"""Model loading and warmup utilities for API startup optimization.

This module provides functions to pre-load ML models during API startup
to eliminate first-request cold-start latency.
"""

# ruff: noqa: TRY300  # Early return pattern preferred for clarity

import time
from pathlib import Path
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


def load_student_model(device: str = "cpu") -> Any | None:
    """Load the student IQA model (ResNet-18).

    Args:
        device: Device to load model on ("cpu", "cuda", or "cuda:0").

    Returns:
        Loaded ONNX model session or None if loading fails.
    """
    try:
        import onnxruntime as ort

        model_path = Path("models/iqa/onnx/resnet18_student.onnx")

        if not model_path.exists():
            logger.warning(
                "student_model_not_found",
                path=str(model_path),
                message="Model file does not exist, will lazy load on first request",
            )
            return None

        # Configure session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        session_options.intra_op_num_threads = 4
        session_options.inter_op_num_threads = 4

        # Select execution provider
        if device.startswith("cuda"):
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        start_time = time.perf_counter()
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "student_model_loaded",
            device=device,
            providers=session.get_providers(),
            load_time_ms=f"{elapsed_ms:.1f}",
        )
        return session
    except ImportError:
        logger.warning(
            "onnxruntime_not_available",
            message="onnxruntime not installed, models will not be pre-loaded",
        )
        return None
    except Exception as e:
        logger.exception("student_model_load_failed", error=str(e))
        return None


def load_teacher_model(device: str = "cuda") -> Any | None:
    """Load the teacher IQA model (ResNet-50).

    Args:
        device: Device to load model on (typically "cuda" for GPU).

    Returns:
        Loaded ONNX model session or None if loading fails.
    """
    try:
        import onnxruntime as ort

        model_path = Path("models/iqa/onnx/resnet50_teacher_50epoch.onnx")

        if not model_path.exists():
            logger.warning(
                "teacher_model_not_found",
                path=str(model_path),
                message="Model file does not exist, will lazy load if needed",
            )
            return None

        # Configure session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        session_options.intra_op_num_threads = 4
        session_options.inter_op_num_threads = 4

        # Select execution provider (teacher typically requires GPU)
        if device.startswith("cuda"):
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            # Teacher on CPU is discouraged but allowed
            providers = ["CPUExecutionProvider"]
            logger.warning(
                "teacher_on_cpu",
                message="Loading teacher model on CPU may have high latency (>500ms)",
            )

        start_time = time.perf_counter()
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "teacher_model_loaded",
            device=device,
            providers=session.get_providers(),
            load_time_ms=f"{elapsed_ms:.1f}",
        )
        return session
    except ImportError:
        logger.warning(
            "onnxruntime_not_available",
            message="onnxruntime not installed, teacher model will not be pre-loaded",
        )
        return None
    except Exception as e:
        logger.exception("teacher_model_load_failed", error=str(e))
        return None


def warmup_models(
    student_model: Any | None,
    teacher_model: Any | None = None,
    warmup_iterations: int = 3,
) -> dict[str, float]:
    """Run warmup inference to avoid first-request latency penalty.

    Args:
        student_model: Loaded student model session.
        teacher_model: Optional loaded teacher model session.
        warmup_iterations: Number of warmup iterations per model.

    Returns:
        Dictionary with warmup timing statistics.
    """
    stats: dict[str, float] = {}

    # Create dummy input (typical image size: 224x224x3)
    rng = np.random.default_rng(seed=42)
    dummy_input = rng.standard_normal((1, 3, 224, 224)).astype(np.float32)

    # Warmup student model
    if student_model is not None:
        try:
            input_name = student_model.get_inputs()[0].name
            student_times = []

            for _ in range(warmup_iterations):
                start = time.perf_counter()
                _ = student_model.run(None, {input_name: dummy_input})
                student_times.append((time.perf_counter() - start) * 1000)

            stats["student_warmup_avg_ms"] = sum(student_times) / len(student_times)
            stats["student_warmup_min_ms"] = min(student_times)
            stats["student_warmup_max_ms"] = max(student_times)

            logger.info(
                "student_model_warmup_complete",
                iterations=warmup_iterations,
                avg_ms=f"{stats['student_warmup_avg_ms']:.1f}",
                min_ms=f"{stats['student_warmup_min_ms']:.1f}",
                max_ms=f"{stats['student_warmup_max_ms']:.1f}",
            )
        except Exception as e:
            logger.warning("student_warmup_failed", error=str(e))

    # Warmup teacher model
    if teacher_model is not None:
        try:
            input_name = teacher_model.get_inputs()[0].name
            teacher_times = []

            for _ in range(warmup_iterations):
                start = time.perf_counter()
                _ = teacher_model.run(None, {input_name: dummy_input})
                teacher_times.append((time.perf_counter() - start) * 1000)

            stats["teacher_warmup_avg_ms"] = sum(teacher_times) / len(teacher_times)
            stats["teacher_warmup_min_ms"] = min(teacher_times)
            stats["teacher_warmup_max_ms"] = max(teacher_times)

            logger.info(
                "teacher_model_warmup_complete",
                iterations=warmup_iterations,
                avg_ms=f"{stats['teacher_warmup_avg_ms']:.1f}",
                min_ms=f"{stats['teacher_warmup_min_ms']:.1f}",
                max_ms=f"{stats['teacher_warmup_max_ms']:.1f}",
            )
        except Exception as e:
            logger.warning("teacher_warmup_failed", error=str(e))

    return stats


def get_model_info(model: Any | None) -> dict[str, Any]:
    """Get metadata about a loaded ONNX model.

    Args:
        model: Loaded ONNX model session.

    Returns:
        Dictionary with model metadata.
    """
    if model is None:
        return {"loaded": False}

    try:
        return {
            "loaded": True,
            "providers": model.get_providers(),
            "input_names": [inp.name for inp in model.get_inputs()],
            "output_names": [out.name for out in model.get_outputs()],
            "input_shapes": [inp.shape for inp in model.get_inputs()],
        }
    except Exception as e:
        logger.warning("model_info_extraction_failed", error=str(e))
        return {"loaded": True, "error": str(e)}
