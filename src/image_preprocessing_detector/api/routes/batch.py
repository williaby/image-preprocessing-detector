"""Batch processing endpoints.

Sprint 5.2.3: Batch endpoints
- POST /batch - Submit batch processing job
- GET /batch/{job_id}/status - Get job status
- GET /batch/{job_id}/result - Get job results
"""

import asyncio
import tempfile
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from image_preprocessing_detector.api.config import get_api_settings
from image_preprocessing_detector.api.middleware import get_correlation_id
from image_preprocessing_detector.api.models import (
    BatchJobResult,
    BatchJobStatus,
    ErrorCode,
    ErrorResponse,
    ProcessingOptions,
    ProcessingResult,
    ProcessingStatus,
)
from image_preprocessing_detector.api.routes.process import (
    SUPPORTED_EXTENSIONS,
    process_document,
    validate_file,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


# In-memory job store (replace with Redis for production)
_job_store: dict[str, dict[str, Any]] = {}


def _get_job(job_id: str) -> dict[str, Any] | None:
    """Get a job from the store."""
    return _job_store.get(job_id)


def _update_job(job_id: str, updates: dict[str, Any]) -> None:
    """Update a job in the store."""
    if job_id in _job_store:
        _job_store[job_id].update(updates)
        _job_store[job_id]["updated_at"] = utc_now()


def _cleanup_old_jobs(max_age_hours: int = 24) -> int:
    """Remove jobs older than max_age_hours."""
    cutoff = utc_now() - timedelta(hours=max_age_hours)
    to_delete = [
        job_id
        for job_id, job in _job_store.items()
        if job.get("created_at", utc_now()) < cutoff
    ]
    for job_id in to_delete:
        del _job_store[job_id]
    return len(to_delete)


async def process_batch_job(
    job_id: str,
    files_data: list[tuple[str, bytes]],
    options: ProcessingOptions,
) -> None:
    """Background task to process batch job.

    Args:
        job_id: The job ID.
        files_data: List of (filename, content) tuples.
        options: Processing options.
    """
    logger.info("batch_job_started", job_id=job_id, num_files=len(files_data))

    results: list[ProcessingResult] = []
    errors: list[ErrorResponse] = []

    for idx, (filename, content) in enumerate(files_data):
        try:
            # Write to temp file
            ext = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                # Process the document
                result = await process_document(tmp_path, filename, options)
                results.append(result)
            finally:
                # Cleanup
                tmp_path.unlink(missing_ok=True)

            # Update progress
            _update_job(
                job_id,
                {
                    "processed_files": idx + 1,
                    "status": ProcessingStatus.PROCESSING,
                },
            )

        except Exception as e:
            logger.exception(
                "batch_file_failed", job_id=job_id, filename=filename, error=str(e)
            )
            errors.append(
                ErrorResponse(
                    error=ErrorCode.PROCESSING_FAILED,
                    message=f"Failed to process {filename}: {str(e)}",
                )
            )
            _update_job(
                job_id,
                {
                    "processed_files": idx + 1,
                    "failed_files": len(errors),
                },
            )

    # Calculate total processing time
    job = _get_job(job_id)
    start_time = job.get("start_time", time.perf_counter()) if job else time.perf_counter()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Update job with final results
    _update_job(
        job_id,
        {
            "status": ProcessingStatus.COMPLETED,
            "results": results,
            "errors": errors,
            "completed_at": utc_now(),
            "total_processing_time_ms": elapsed_ms,
        },
    )

    logger.info(
        "batch_job_completed",
        job_id=job_id,
        num_results=len(results),
        num_errors=len(errors),
        elapsed_ms=elapsed_ms,
    )


@router.post(
    "",
    response_model=BatchJobStatus,
    summary="Submit batch processing job",
    description="Upload multiple files for batch processing. Returns a job ID for tracking.",
    responses={
        200: {"description": "Batch job submitted successfully"},
        400: {"description": "Invalid request"},
    },
)
async def submit_batch_job(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Documents to process"),
    prefer_gpu: bool = True,
    enable_corrections: bool = True,
    enable_teacher: bool = False,
) -> BatchJobStatus | JSONResponse:
    """Submit a batch processing job.

    Args:
        background_tasks: FastAPI background tasks.
        files: List of files to process.
        prefer_gpu: Whether to prefer GPU.
        enable_corrections: Whether to enable corrections.
        enable_teacher: Whether to enable teacher model.

    Returns:
        BatchJobStatus with job ID and initial status.
    """
    settings = get_api_settings()
    correlation_id = get_correlation_id()

    logger.info(
        "batch_job_submitted",
        num_files=len(files),
        correlation_id=correlation_id,
    )

    # Validate batch size
    if len(files) > settings.max_batch_size:
        error = ErrorResponse(
            error=ErrorCode.INVALID_PARAMETERS,
            message=f"Batch size {len(files)} exceeds limit of {settings.max_batch_size}",
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error.model_dump(),
        )

    if len(files) == 0:
        error = ErrorResponse(
            error=ErrorCode.INVALID_PARAMETERS,
            message="No files provided",
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error.model_dump(),
        )

    # Validate each file and read content
    files_data: list[tuple[str, bytes]] = []
    for file in files:
        validation_error = validate_file(file, settings.max_file_size_mb)
        if validation_error:
            validation_error.correlation_id = correlation_id
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=validation_error.model_dump(),
            )

        content = await file.read()
        if len(content) == 0:
            error = ErrorResponse(
                error=ErrorCode.EMPTY_FILE,
                message=f"File {file.filename} is empty",
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error.model_dump(),
            )

        files_data.append((file.filename or "document", content))

    # Create job
    job_id = str(uuid.uuid4())
    now = utc_now()

    _job_store[job_id] = {
        "job_id": job_id,
        "status": ProcessingStatus.PENDING,
        "total_files": len(files_data),
        "processed_files": 0,
        "failed_files": 0,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "results": [],
        "errors": [],
        "start_time": time.perf_counter(),
    }

    # Create processing options
    options = ProcessingOptions(
        prefer_gpu=prefer_gpu,
        enable_corrections=enable_corrections,
        enable_teacher=enable_teacher,
    )

    # Schedule background processing
    background_tasks.add_task(process_batch_job, job_id, files_data, options)

    # Update status to processing
    _update_job(job_id, {"status": ProcessingStatus.PROCESSING})

    logger.info("batch_job_created", job_id=job_id, num_files=len(files_data))

    return BatchJobStatus(
        job_id=job_id,
        status=ProcessingStatus.PROCESSING,
        total_files=len(files_data),
        processed_files=0,
        failed_files=0,
        created_at=now,
        updated_at=now,
    )


@router.get(
    "/{job_id}/status",
    response_model=BatchJobStatus,
    summary="Get batch job status",
    description="Get the current status of a batch processing job.",
    responses={
        200: {"description": "Job status retrieved"},
        404: {"description": "Job not found"},
    },
)
async def get_batch_status(job_id: str) -> BatchJobStatus:
    """Get the status of a batch job.

    Args:
        job_id: The job ID.

    Returns:
        BatchJobStatus with current progress.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return BatchJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        failed_files=job["failed_files"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        completed_at=job.get("completed_at"),
    )


@router.get(
    "/{job_id}/result",
    response_model=BatchJobResult,
    summary="Get batch job results",
    description="Get the results of a completed batch processing job.",
    responses={
        200: {"description": "Job results retrieved"},
        404: {"description": "Job not found"},
        425: {"description": "Job not yet completed"},
    },
)
async def get_batch_result(
    job_id: str,
    offset: int = 0,
    limit: int = 100,
) -> BatchJobResult | JSONResponse:
    """Get the results of a batch job.

    Args:
        job_id: The job ID.
        offset: Pagination offset.
        limit: Maximum results to return.

    Returns:
        BatchJobResult with processing results.
    """
    job = _get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job["status"] not in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
        return JSONResponse(
            status_code=425,  # Too Early
            content={
                "detail": f"Job {job_id} is still processing",
                "status": job["status"].value,
                "progress": f"{job['processed_files']}/{job['total_files']}",
            },
        )

    # Paginate results
    results = job.get("results", [])
    paginated_results = results[offset : offset + limit]

    return BatchJobResult(
        job_id=job_id,
        status=job["status"],
        results=paginated_results,
        errors=job.get("errors", []),
        total_processing_time_ms=job.get("total_processing_time_ms", 0),
    )


@router.delete(
    "/{job_id}",
    summary="Delete batch job",
    description="Delete a batch job and its results.",
    responses={
        200: {"description": "Job deleted"},
        404: {"description": "Job not found"},
    },
)
async def delete_batch_job(job_id: str) -> dict[str, str]:
    """Delete a batch job.

    Args:
        job_id: The job ID.

    Returns:
        Confirmation message.
    """
    if job_id not in _job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    del _job_store[job_id]
    logger.info("batch_job_deleted", job_id=job_id)

    return {"message": f"Job {job_id} deleted"}
