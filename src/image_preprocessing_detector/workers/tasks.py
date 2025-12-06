# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Celery tasks for document processing.

This module defines Celery tasks for:
- Single document processing
- Batch document processing
- IQA analysis with ML models

Phase 4 Integration - Week 17 Sprint 4.3.5
"""

import base64
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from image_preprocessing_detector.orchestration import (
    DeviceOrchestrator,
    DevicePolicyConfig,
    InferenceMode,
    ModalClient,
)
from image_preprocessing_detector.utils.log_config import get_logger
from image_preprocessing_detector.workers.celery_app import celery_app

logger = get_logger(__name__)


class IQATask(Task):
    """Base task class with lazy model loading and device orchestration.

    Sprint 4.3.5: Device-priority routing integrated into Celery tasks.
    """

    _student_session: Any = None
    _teacher_session: Any = None
    _orchestrator: DeviceOrchestrator | None = None
    _modal_client: ModalClient | None = None

    @property
    def student_session(self) -> Any:
        """Lazily load student model session."""
        if self._student_session is None:
            try:
                from image_preprocessing_detector.models.model_loader import (
                    load_student_model,
                )

                self._student_session = load_student_model()
                logger.info("Student model loaded in worker")
            except Exception as e:
                logger.warning("Failed to load student model", error=str(e))
        return self._student_session

    @property
    def teacher_session(self) -> Any:
        """Lazily load teacher model session."""
        if self._teacher_session is None:
            try:
                from image_preprocessing_detector.models.model_loader import (
                    load_teacher_model,
                )

                self._teacher_session = load_teacher_model()
                logger.info("Teacher model loaded in worker")
            except Exception as e:
                logger.warning("Failed to load teacher model", error=str(e))
        return self._teacher_session

    @property
    def orchestrator(self) -> DeviceOrchestrator:
        """Lazily initialize device orchestrator."""
        if self._orchestrator is None:
            # Get inference mode from environment (default: production)
            mode_str = os.getenv("IMGPREP_INFERENCE_MODE", "production").lower()
            mode = InferenceMode(mode_str)

            # Create device policy config from environment
            config = DevicePolicyConfig(
                mode=mode,
                allow_cpu_teacher=os.getenv(
                    "IMGPREP_ALLOW_CPU_TEACHER", "false"
                ).lower()
                == "true",
                enable_modal=os.getenv("IMGPREP_ENABLE_MODAL", "true").lower()
                == "true",
                modal_timeout_ms=int(os.getenv("IMGPREP_MODAL_TIMEOUT_MS", "5000")),
                teacher_budget_per_doc=int(
                    os.getenv("IMGPREP_TEACHER_BUDGET_PER_DOC", "10")
                ),
                teacher_budget_per_batch=int(
                    os.getenv("IMGPREP_TEACHER_BUDGET_PER_BATCH", "100")
                ),
                disable_teacher=os.getenv("IMGPREP_DISABLE_TEACHER", "false").lower()
                == "true",
            )

            self._orchestrator = DeviceOrchestrator(config=config)
            logger.info(
                "DeviceOrchestrator initialized in worker", mode=mode, config=config
            )

        return self._orchestrator

    @property
    def modal_client(self) -> ModalClient:
        """Lazily initialize Modal client for teacher inference."""
        if self._modal_client is None:
            self._modal_client = ModalClient()
            logger.info("ModalClient initialized in worker")
        return self._modal_client


@celery_app.task(
    bind=True,
    base=IQATask,
    name="image_preprocessing_detector.workers.tasks.run_iqa_analysis",
    queue="gpu",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    soft_time_limit=120,
    time_limit=180,
)
def run_iqa_analysis(
    self: IQATask,
    image_b64: str,
    request_id: str | None = None,
    enable_teacher: bool = False,  # noqa: ARG001 - reserved for future use
    doc_id: str | None = None,
) -> dict[str, Any]:
    """Run IQA analysis on an image with device-priority routing.

    Args:
        self: Task instance (bound by Celery)
        image_b64: Base64-encoded image data
        request_id: Optional request identifier
        enable_teacher: Whether to enable teacher model fallback
        doc_id: Document ID for budget tracking

    Returns:
        Dictionary with IQA scores and metadata including device selection
    """
    start_time = time.perf_counter()
    doc_id = doc_id or request_id or "unknown"

    try:
        # Decode image
        image_bytes = base64.b64decode(image_b64)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)

        import cv2

        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            msg = "Failed to decode image"
            raise ValueError(msg)  # noqa: TRY301

        # Preprocess for model
        preprocessed = _preprocess_image(image)

        # Select device for student inference
        device_choice = self.orchestrator.select_device_for_student()

        logger.debug(
            "Device selected for student",
            device=device_choice.device,
            rationale=device_choice.rationale,
            request_id=request_id,
        )

        # Run student inference on selected device
        session = self.student_session
        if session is None:
            msg = "Student model not available"
            raise RuntimeError(msg)  # noqa: TRY301

        input_name = session.get_inputs()[0].name
        output_names = [out.name for out in session.get_outputs()]
        outputs = session.run(output_names, {input_name: preprocessed})

        # Postprocess
        scores, confidences = _postprocess_outputs(
            dict(zip(output_names, outputs, strict=False))
        )

        # Calculate overall quality
        overall = (
            scores.get("blur_score", 0.0) * 0.25
            + scores.get("noise_score", 0.0) * 0.20
            + scores.get("contrast_score", 0.0) * 0.25
            + scores.get("skew_score", 0.0) * 0.15
            + scores.get("compression_score", 0.0) * 0.15
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = {
            "request_id": request_id,
            "model": "student",
            "device": device_choice.device,
            "device_rationale": device_choice.rationale,
            "scores": scores,
            "confidences": confidences,
            "overall_quality": overall,
            "inference_time_ms": round(elapsed_ms, 2),
            "worker_id": self.request.hostname if self.request else None,
        }

        logger.info(
            "IQA analysis complete",
            request_id=request_id,
            device=device_choice.device,
            overall_quality=round(overall, 3),
            inference_time_ms=round(elapsed_ms, 2),
        )

    except SoftTimeLimitExceeded:
        logger.warning("IQA analysis soft time limit exceeded", request_id=request_id)
        raise
    except Exception as e:
        logger.exception("IQA analysis failed", request_id=request_id, error=str(e))
        raise self.retry(exc=e) from e
    else:
        return result


@celery_app.task(
    bind=True,
    name="image_preprocessing_detector.workers.tasks.process_single_document",
    queue="default",
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=180,
    time_limit=240,
)
def process_single_document(
    self: Task,
    file_content_b64: str,
    filename: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process a single document.

    Args:
        self: Task instance (bound by Celery)
        file_content_b64: Base64-encoded file content
        filename: Original filename
        options: Processing options

    Returns:
        Dictionary with processing results
    """
    start_time = time.perf_counter()
    options = options or {}

    try:
        # Decode file content
        file_content = base64.b64decode(file_content_b64)

        # Write to temp file
        ext = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = Path(tmp_file.name)

        try:
            # Import processing logic
            # For now, return basic metadata
            result = {
                "filename": filename,
                "file_size": len(file_content),
                "file_type": ext,
                "status": "completed",
                "processing_time_ms": round(
                    (time.perf_counter() - start_time) * 1000, 2
                ),
            }

            # Try to extract page count for PDFs
            if ext == ".pdf":
                try:
                    import fitz

                    with fitz.open(tmp_path) as doc:
                        result["page_count"] = len(doc)
                except Exception:
                    # PDF parsing failed, continue without page count
                    logger.debug("Failed to extract PDF page count", filename=filename)

            logger.info(
                "Document processed",
                filename=filename,
                processing_time_ms=result["processing_time_ms"],
            )

            return result

        finally:
            # Cleanup temp file
            tmp_path.unlink(missing_ok=True)

    except SoftTimeLimitExceeded:
        logger.warning(
            "Document processing soft time limit exceeded", filename=filename
        )
        return {
            "filename": filename,
            "status": "timeout",
            "error": "Processing time limit exceeded",
        }
    except Exception as e:
        logger.exception("Document processing failed", filename=filename, error=str(e))
        raise self.retry(exc=e) from e


@celery_app.task(
    bind=True,
    name="image_preprocessing_detector.workers.tasks.process_batch_documents",
    queue="batch",
    soft_time_limit=600,
    time_limit=900,
)
def process_batch_documents(
    self: Task,
    files_data: list[dict[str, str]],
    options: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Process a batch of documents.

    Args:
        self: Task instance (bound by Celery)
        files_data: List of {"filename": str, "content_b64": str} dicts
        options: Processing options
        job_id: Optional job identifier

    Returns:
        Dictionary with batch results
    """
    start_time = time.perf_counter()
    options = options or {}

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, file_data in enumerate(files_data):
        filename = file_data.get("filename", f"document_{idx}")
        content_b64 = file_data.get("content_b64", "")

        try:
            # Process individual document synchronously
            result = process_single_document.apply(
                args=(content_b64, filename, options)
            ).get(timeout=180)
            results.append(result)

            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx + 1,
                    "total": len(files_data),
                    "status": f"Processing {filename}",
                },
            )

        except Exception as e:
            logger.exception(
                "Batch file failed", job_id=job_id, filename=filename, error=str(e)
            )
            errors.append(
                {
                    "filename": filename,
                    "error": str(e),
                }
            )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    batch_result = {
        "job_id": job_id,
        "total_files": len(files_data),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "total_processing_time_ms": round(elapsed_ms, 2),
        "avg_time_per_file_ms": round(elapsed_ms / len(files_data), 2)
        if files_data
        else 0,
    }

    logger.info(
        "Batch processing complete",
        job_id=job_id,
        total=len(files_data),
        successful=len(results),
        failed=len(errors),
        elapsed_ms=round(elapsed_ms, 2),
    )

    return batch_result


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """Preprocess image for model input.

    Args:
        image: Input image (BGR format, HxWx3)

    Returns:
        Preprocessed tensor (1x3x224x224, float32)
    """
    import cv2

    # Resize to 224x224
    resized = cv2.resize(image, (224, 224), interpolation=cv2.INTER_LINEAR)

    # Convert BGR → RGB
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # Normalize: [0, 255] → [0, 1]
    normalized = rgb.astype(np.float32) / 255.0

    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (normalized - mean) / std

    # Transpose: HWC → CHW
    transposed = np.transpose(normalized, (2, 0, 1))

    # Add batch dimension
    return np.expand_dims(transposed, axis=0)


def _postprocess_outputs(
    outputs: dict[str, np.ndarray],
) -> tuple[dict[str, float], dict[str, float]]:
    """Postprocess model outputs to scores.

    Args:
        outputs: Raw model outputs

    Returns:
        Tuple of (scores, confidences)
    """
    head_names = ["blur", "noise", "contrast", "skew", "compression"]
    scores = {}
    confidences = {}

    for i, head_name in enumerate(head_names):
        output_key = f"head_{i}"
        if output_key in outputs:
            logits = outputs[output_key][0]
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            scores[f"{head_name}_score"] = float(probs[1])
            confidences[head_name] = float(np.max(probs))

    return scores, confidences
