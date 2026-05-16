"""Health and readiness endpoints.

Provides:
- /health - Basic liveness check
- /ready - Readiness check with dependency validation
- /version - API and model version information
"""

import sys
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from image_preprocessing_detector.api.config import get_api_settings
from image_preprocessing_detector.utils.datetime_compat import utc_now
from image_preprocessing_detector.utils.device_probe import (
    DeviceCapabilities,
    probe_device_capabilities,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="", tags=["health"])


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(description="Health status: healthy or unhealthy")
    timestamp: datetime = Field(description="Current server timestamp")
    uptime_seconds: float | None = Field(
        default=None, description="Server uptime in seconds"
    )


class ReadyResponse(BaseModel):
    """Response model for readiness check."""

    status: str = Field(description="Ready status: ready or not_ready")
    timestamp: datetime = Field(description="Current server timestamp")
    checks: dict[str, bool] = Field(description="Individual readiness check results")
    device: dict[str, Any] = Field(description="Available compute device information")


class VersionResponse(BaseModel):
    """Response model for version endpoint."""

    api_version: str = Field(description="API version string")
    python_version: str = Field(description="Python runtime version")
    pipeline_version: str = Field(description="Processing pipeline version")
    models: dict[str, str | None] = Field(description="Model version information")


# Server start time for uptime calculation
_server_start_time: datetime | None = None


def set_server_start_time() -> None:
    """Set the server start time (called on startup)."""
    global _server_start_time
    _server_start_time = utc_now()


def get_uptime_seconds() -> float | None:
    """Get server uptime in seconds."""
    if _server_start_time is None:
        return None
    return (utc_now() - _server_start_time).total_seconds()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description=(
        "Basic liveness probe for load balancers and orchestrators. "
        "Returns `healthy` whenever the process is responding, along with a "
        "server timestamp and (if startup completed) uptime in seconds. Does "
        "not perform dependency checks — use `/ready` for that."
    ),
    response_description="Server is alive; returns liveness status, timestamp, and uptime.",
    responses={
        200: {
            "description": "Server is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-01-15T10:30:00Z",
                        "uptime_seconds": 3600.5,
                    }
                }
            },
        },
        503: {"description": "Server is unhealthy"},
    },
)
async def health_check() -> HealthResponse:
    """Return liveness status of the API process.

    Used by container orchestrators (Kubernetes, Docker Swarm) and load
    balancers as a cheap liveness probe. Does NOT validate that downstream
    dependencies (models, GPU, configuration) are available; that is the
    responsibility of `/ready`.

    Returns:
        HealthResponse with status (`healthy`), current UTC timestamp, and
        uptime in seconds since application startup.
    """
    logger.debug("health_check_called")
    return HealthResponse(
        status="healthy",
        timestamp=utc_now(),
        uptime_seconds=get_uptime_seconds(),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description=(
        "Readiness probe that validates dependencies required to serve "
        "requests:\n\n"
        "- Device capability probe (GPU/CPU detection)\n"
        "- Classical IQA detector imports\n"
        "- Pydantic schema imports\n"
        "- Configuration loading\n\n"
        "Returns HTTP 200 with `status=ready` when all checks pass, or HTTP "
        "503 with `status=not_ready` and per-check details when any fail. "
        "Use this for Kubernetes readiness probes — failing readiness "
        "removes the pod from the service load balancer."
    ),
    response_description="Per-component readiness checks and detected device information.",
    responses={
        200: {
            "description": "Server is ready to accept requests",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "timestamp": "2025-01-15T10:30:00Z",
                        "checks": {
                            "device_probe": True,
                            "iqa_detectors": True,
                            "schema": True,
                            "configuration": True,
                        },
                        "device": {
                            "has_local_gpu": False,
                            "gpu_name": None,
                            "cpu_count": 8,
                            "modal_available": False,
                        },
                    }
                }
            },
        },
        503: {"description": "Server is not ready (one or more checks failed)"},
    },
)
async def readiness_check(response: Response) -> ReadyResponse:
    """Check if the server is ready to process requests.

    Validates:
    - Device capabilities (GPU/CPU availability)
    - Core module imports
    - Configuration validity

    Args:
        response: FastAPI response object for setting status code.

    Returns:
        ReadyResponse with detailed check results.
    """
    logger.debug("readiness_check_called")

    checks: dict[str, bool] = {}
    device_info: dict[str, Any] = {}

    # Check device capabilities
    try:
        caps: DeviceCapabilities = probe_device_capabilities()
        checks["device_probe"] = True
        device_info = {
            "has_local_gpu": caps.has_local_gpu,
            "gpu_name": caps.gpu_name,
            "cpu_count": caps.cpu_count,
            "modal_available": caps.modal_available,
        }
    except Exception as e:
        logger.warning("device_probe_failed", error=str(e))
        checks["device_probe"] = False
        device_info = {"error": str(e)}

    # Check core module imports
    try:
        from image_preprocessing_detector.detection.iqa_classical import BlurDetector

        _ = BlurDetector()
        checks["iqa_detectors"] = True
    except Exception as e:
        logger.warning("iqa_detector_import_failed", error=str(e))
        checks["iqa_detectors"] = False

    # Check schema module
    try:
        from image_preprocessing_detector.schema import DocumentMetadata

        _ = DocumentMetadata
        checks["schema"] = True
    except Exception as e:
        logger.warning("schema_import_failed", error=str(e))
        checks["schema"] = False

    # Check configuration
    try:
        settings = get_api_settings()
        checks["configuration"] = settings is not None
    except Exception as e:
        logger.warning("configuration_failed", error=str(e))
        checks["configuration"] = False

    # Determine overall ready status
    is_ready = all(checks.values())
    status_str = "ready" if is_ready else "not_ready"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning("readiness_check_failed", checks=checks)
    else:
        logger.debug("readiness_check_passed", checks=checks)

    return ReadyResponse(
        status=status_str,
        timestamp=utc_now(),
        checks=checks,
        device=device_info,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Version information",
    description=(
        "Return the running API version, Python runtime version, processing "
        "pipeline version, and the resolved on-disk filenames for any "
        "currently-installed ONNX models (teacher / student / layout). "
        "Useful for diagnostics, support requests, and verifying model "
        "rollouts in production."
    ),
    response_description="Version metadata for API, runtime, pipeline, and ML models.",
    responses={
        200: {
            "description": "Version metadata",
            "content": {
                "application/json": {
                    "example": {
                        "api_version": "0.1.0",
                        "python_version": "3.11.6",
                        "pipeline_version": "1.0.0",
                        "models": {
                            "teacher_model": "resnet50_teacher_50epoch",
                            "student_model": "resnet18_student",
                            "layout_model": None,
                        },
                    }
                }
            },
        },
    },
)
async def version_info() -> VersionResponse:
    """Get version information for the API and models.

    Returns:
        VersionResponse with version details.
    """
    logger.debug("version_info_called")

    settings = get_api_settings()

    # Get model versions (check if ONNX models exist)
    models: dict[str, str | None] = {
        "teacher_model": None,
        "student_model": None,
        "layout_model": None,
    }

    # Try to detect model versions from filesystem
    try:
        from pathlib import Path

        model_dir = Path("models/iqa/onnx")
        if model_dir.exists():  # Trivially fast exists check
            teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"
            student_path = model_dir / "resnet18_student.onnx"

            if teacher_path.exists():  # Trivially fast exists check
                models["teacher_model"] = "resnet50_teacher_50epoch"
            if student_path.exists():  # Trivially fast exists check
                models["student_model"] = "resnet18_student"
    except Exception as e:
        logger.debug("model_version_detection_failed", error=str(e))

    return VersionResponse(
        api_version=settings.version,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        pipeline_version="1.0.0",
        models=models,
    )
