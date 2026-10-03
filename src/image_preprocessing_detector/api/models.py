"""API request and response models.

Defines Pydantic models for:
- Processing requests and responses
- Batch job requests and responses
- Error responses
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Status of a processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(str, Enum):
    """Structured error codes for API responses."""

    # Validation errors (400)
    INVALID_FILE_TYPE = "invalid_file_type"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_PARAMETERS = "invalid_parameters"
    EMPTY_FILE = "empty_file"

    # Processing errors (422)
    PROCESSING_FAILED = "processing_failed"
    CORRUPT_FILE = "corrupt_file"
    UNSUPPORTED_FORMAT = "unsupported_format"

    # Server errors (500)
    INTERNAL_ERROR = "internal_error"
    GPU_UNAVAILABLE = "gpu_unavailable"
    MODEL_LOAD_FAILED = "model_load_failed"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Auth errors (401/403)
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: ErrorCode = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
    correlation_id: str | None = Field(
        default=None, description="Request correlation ID for debugging"
    )


class ProcessingOptions(BaseModel):
    """Options for document processing."""

    prefer_gpu: bool = Field(default=True, description="Prefer GPU for processing")
    enable_corrections: bool = Field(
        default=True, description="Apply automatic corrections"
    )
    enable_teacher: bool = Field(
        default=False, description="Enable teacher model inference"
    )
    dpi_threshold: int = Field(
        default=300, description="Minimum DPI threshold for upscaling"
    )


class IQAScoreSummary(BaseModel):
    """Summary of IQA scores."""

    blur_score: float | None = Field(default=None, description="Blur quality score")
    noise_score: float | None = Field(default=None, description="Noise quality score")
    contrast_score: float | None = Field(
        default=None, description="Contrast quality score"
    )
    skew_angle: float | None = Field(default=None, description="Detected skew angle")


class DQSSummary(BaseModel):
    """Summary of Document Quality Score."""

    degradation_score: float = Field(description="Overall degradation score (0-1)")
    structural_complexity_score: float = Field(
        description="Structural complexity score (0-1)"
    )
    pre_ocr_risk: float | None = Field(
        default=None, description="Pre-OCR risk score (0-1)"
    )


class PageSummary(BaseModel):
    """Summary of a single page analysis."""

    page_index: int = Field(description="Page index (0-based)")
    width_px: int = Field(description="Page width in pixels")
    height_px: int = Field(description="Page height in pixels")
    issues_detected: int = Field(default=0, description="Number of issues detected")
    corrections_applied: int = Field(
        default=0, description="Number of corrections applied"
    )
    iqa_scores: IQAScoreSummary | None = Field(
        default=None, description="IQA score summary"
    )


class ProcessingResult(BaseModel):
    """Result of document processing."""

    document_id: str = Field(description="Unique document identifier")
    file_name: str = Field(description="Original file name")
    num_pages: int = Field(description="Number of pages processed")
    pages_truncated: int = Field(
        default=0,
        description=(
            "Number of pages dropped because the document exceeded the "
            "API's max_pdf_pages_per_request cap. Zero means the result "
            "covers the full document. Non-zero means analysis is "
            "partial - re-submit with smaller documents or contact the "
            "operator to raise the cap."
        ),
    )
    pdf_type: str | None = Field(
        default=None,
        description="Detected PDF type (image_only, born_digital, hybrid)",
    )
    dqs: DQSSummary | None = Field(default=None, description="Document Quality Score")
    ocr_routing_recommendation: str | None = Field(
        default=None, description="Recommended OCR routing strategy"
    )
    pages: list[PageSummary] = Field(
        default_factory=list, description="Per-page summaries"
    )
    processing_time_ms: float = Field(description="Total processing time in ms")
    device_used: str = Field(description="Device used for processing (cpu/gpu)")


class ProcessResponse(BaseModel):
    """Response for single document processing."""

    status: ProcessingStatus = Field(description="Processing status")
    result: ProcessingResult | None = Field(
        default=None, description="Processing result (if completed)"
    )
    metadata_url: str | None = Field(
        default=None, description="URL to full metadata JSON"
    )
    corrected_images_url: str | None = Field(
        default=None, description="URL to corrected images"
    )
    error: ErrorResponse | None = Field(
        default=None, description="Error details (if failed)"
    )


# Batch processing models


class BatchJobRequest(BaseModel):
    """Request to create a batch processing job."""

    options: ProcessingOptions = Field(
        default_factory=ProcessingOptions, description="Processing options"
    )


class BatchJobStatus(BaseModel):
    """Status of a batch processing job."""

    job_id: str = Field(description="Unique job identifier")
    status: ProcessingStatus = Field(description="Job status")
    total_files: int = Field(description="Total files in batch")
    processed_files: int = Field(default=0, description="Files processed so far")
    failed_files: int = Field(default=0, description="Files that failed processing")
    created_at: datetime = Field(description="Job creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )
    estimated_completion: datetime | None = Field(
        default=None, description="Estimated completion time"
    )


class BatchJobResult(BaseModel):
    """Result of a batch processing job."""

    job_id: str = Field(description="Unique job identifier")
    status: ProcessingStatus = Field(description="Job status")
    results: list[ProcessingResult] = Field(
        default_factory=list, description="Processing results"
    )
    errors: list[ErrorResponse] = Field(
        default_factory=list, description="Processing errors"
    )
    total_processing_time_ms: float = Field(description="Total processing time")
