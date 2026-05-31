"""Centralized exception hierarchy for Image Preprocessing Detector.

This module provides a structured exception hierarchy for consistent error handling
across the application. All project-specific exceptions inherit from ProjectBaseError.

Exception Hierarchy:
    ProjectBaseError (base for all project exceptions)
    ├── ConfigurationError (configuration/settings issues)
    ├── ValidationError (input/data validation failures)
    ├── ResourceNotFoundError (missing resources/entities)
    ├── ExternalServiceError (third-party service failures)
    │   ├── ModelLoadError (ML model loading failures)
    │   └── StorageError (file/storage operation errors)
    ├── ImageProcessingError (image/PDF processing failures)
    │   ├── IngestionError (document ingestion failures)
    │   ├── DetectionError (IQA/text detection failures)
    │   └── CorrectionError (image correction failures)
    └── PipelineError (pipeline orchestration errors)

Usage:
    from image_preprocessing_detector.core.exceptions import (
        ValidationError,
        ImageProcessingError,
        ConfigurationError,
    )

    # Raise with context
    raise ValidationError("Invalid image format", field="input_file", value="document.xyz")

    # Handle in CLI/processing
    try:
        process_document(input_path)
    except ImageProcessingError as e:
        logger.error("Processing failed", error=str(e), details=e.details)
"""

from __future__ import annotations

from typing import Any


class ProjectBaseError(Exception):
    """Base exception for all Image Preprocessing Detector errors.

    All custom exceptions in the project should inherit from this class
    to enable unified error handling and logging.

    Args:
        message (str): Human-readable error description.
        details (dict[str, Any] | None): Additional context as key-value pairs.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ProjectBaseError("Something went wrong", error_code="ERR001")
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON serialization.

        Returns:
            dict[str, Any]: Dictionary with error details suitable for JSON serialization.
        """
        result: dict[str, Any] = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.error_code:
            result["code"] = self.error_code
        if self.details:
            result["details"] = self.details
        return result


class ConfigurationError(ProjectBaseError):
    """Configuration-related errors.

    Raised when there are issues with application configuration,
    environment variables, or settings validation.

    Example:
        >>> raise ConfigurationError(
        ...     "Missing required configuration",
        ...     details={"missing_keys": ["MODEL_PATH", "OUTPUT_DIR"]},
        ... )
    """


class ValidationError(ProjectBaseError):
    """Input validation errors.

    Raised when user input or data fails validation rules.
    Includes field-level error details for form validation.

    Args:
        message (str): Description of the validation failure.
        field (str | None): Name of the field that failed validation.
        value (Any): The invalid value (will be sanitized in logs).
        details (dict[str, Any] | None): Additional validation context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ValidationError(
        ...     "Invalid image format",
        ...     field="input_file",
        ...     value="document.xyz",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            # Truncate long values to avoid log bloat
            str_value = str(value)
            details["value"] = (
                str_value[:100] + "..." if len(str_value) > 100 else str_value
            )
        super().__init__(
            message, details=details, error_code=error_code or "VALIDATION_ERROR"
        )


class ResourceNotFoundError(ProjectBaseError):
    """Resource not found errors.

    Raised when a requested resource (file, model, record) cannot be found.

    Args:
        message (str): Description of what was not found.
        resource_type (str | None): Type of resource (e.g., "model", "document", "file").
        resource_id (str | None): Identifier of the missing resource.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ResourceNotFoundError(
        ...     "Model file not found",
        ...     resource_type="model",
        ...     resource_id="resnet18_iqa.onnx",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, details=details, error_code=error_code or "NOT_FOUND")


class ExternalServiceError(ProjectBaseError):
    """External service/dependency errors.

    Base class for errors from external services (storage, ML models, etc.).

    Args:
        message (str): Description of the service error.
        service_name (str | None): Name of the external service.
        status_code (int | None): HTTP status code if applicable.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ExternalServiceError(
        ...     "GCS upload failed",
        ...     service_name="Google Cloud Storage",
        ...     status_code=503,
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if service_name:
            details["service_name"] = service_name
        if status_code:
            details["status_code"] = status_code
        super().__init__(
            message, details=details, error_code=error_code or "EXTERNAL_SERVICE_ERROR"
        )


class ModelLoadError(ExternalServiceError):
    """ML model loading errors.

    Raised when ML model loading or initialization fails.

    Args:
        message (str): Description of the model loading error.
        model_name (str | None): Name of the model that failed to load.
        model_path (str | None): Path to the model file.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ModelLoadError(
        ...     "Failed to load IQA model",
        ...     model_name="resnet18_student",
        ...     model_path="/models/resnet18_iqa.onnx",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        model_name: str | None = None,
        model_path: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if model_name:
            details["model_name"] = model_name
        if model_path:
            details["model_path"] = model_path
        super().__init__(
            message,
            service_name="ml_model",
            details=details,
            error_code=error_code or "MODEL_LOAD_ERROR",
        )


class StorageError(ExternalServiceError):
    """Storage operation errors.

    Raised when file or storage operations fail.

    Args:
        message (str): Description of the storage error.
        operation (str | None): The storage operation that failed (read, write, delete).
        path (str | None): The file/storage path involved.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise StorageError(
        ...     "Failed to write output file",
        ...     operation="write",
        ...     path="/output/result.json",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        path: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if operation:
            details["operation"] = operation
        if path:
            details["path"] = path
        super().__init__(
            message,
            service_name="storage",
            details=details,
            error_code=error_code or "STORAGE_ERROR",
        )


class ImageProcessingError(ProjectBaseError):
    """Image/document processing errors.

    Base class for errors during image or PDF processing operations.

    Args:
        message (str): Description of the processing error.
        page_number (int | None): Page number where the error occurred.
        document_id (str | None): Identifier of the document being processed.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise ImageProcessingError(
        ...     "Failed to process page",
        ...     page_number=5,
        ...     document_id="doc_001",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        page_number: int | None = None,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if page_number is not None:
            details["page_number"] = page_number
        if document_id:
            details["document_id"] = document_id
        super().__init__(
            message, details=details, error_code=error_code or "PROCESSING_ERROR"
        )


class IngestionError(ImageProcessingError):
    """Document ingestion errors.

    Raised when document ingestion (PDF parsing, image loading) fails.

    Args:
        message (str): Description of the ingestion error.
        source_path (str | None): Path to the source file.
        page_number (int | None): Page number where ingestion failed.
        document_id (str | None): Identifier of the document.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise IngestionError(
        ...     "Failed to extract images from PDF",
        ...     source_path="corrupted.pdf",
        ...     page_number=3,
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        source_path: str | None = None,
        page_number: int | None = None,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if source_path:
            details["source_path"] = source_path
        super().__init__(
            message,
            page_number=page_number,
            document_id=document_id,
            details=details,
            error_code=error_code or "INGESTION_ERROR",
        )


class DetectionError(ImageProcessingError):
    """Detection/analysis errors.

    Raised when IQA detection or text detection fails.

    Args:
        message (str): Description of the detection error.
        detector_type (str | None): Type of detector that failed (iqa_classical, iqa_ml, text_gate).
        page_number (int | None): Page number where detection failed.
        document_id (str | None): Identifier of the document.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise DetectionError(
        ...     "IQA model inference failed",
        ...     detector_type="iqa_ml",
        ...     page_number=1,
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        detector_type: str | None = None,
        page_number: int | None = None,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if detector_type:
            details["detector_type"] = detector_type
        super().__init__(
            message,
            page_number=page_number,
            document_id=document_id,
            details=details,
            error_code=error_code or "DETECTION_ERROR",
        )


class CorrectionError(ImageProcessingError):
    """Image correction errors.

    Raised when image correction operations fail.

    Args:
        message (str): Description of the correction error.
        correction_type (str | None): Type of correction that failed (deskew, clahe, denoise).
        page_number (int | None): Page number where correction failed.
        document_id (str | None): Identifier of the document.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise CorrectionError(
        ...     "Deskew operation failed",
        ...     correction_type="deskew",
        ...     page_number=2,
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        correction_type: str | None = None,
        page_number: int | None = None,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if correction_type:
            details["correction_type"] = correction_type
        super().__init__(
            message,
            page_number=page_number,
            document_id=document_id,
            details=details,
            error_code=error_code or "CORRECTION_ERROR",
        )


class PipelineError(ProjectBaseError):
    """Pipeline orchestration errors.

    Raised when the document processing pipeline fails at a stage boundary.

    Args:
        message (str): Description of the pipeline error.
        stage (str | None): Pipeline stage that failed (ingestion, detection, correction, output).
        document_id (str | None): Identifier of the document.
        details (dict[str, Any] | None): Additional context.
        error_code (str | None): Machine-readable error code.

    Example:
        >>> raise PipelineError(
        ...     "Pipeline stage failed",
        ...     stage="detection",
        ...     document_id="doc_001",
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        details = details or {}
        if stage:
            details["stage"] = stage
        if document_id:
            details["document_id"] = document_id
        super().__init__(
            message, details=details, error_code=error_code or "PIPELINE_ERROR"
        )


# Export all exceptions
__all__ = [
    "ConfigurationError",
    "CorrectionError",
    "DetectionError",
    "ExternalServiceError",
    "ImageProcessingError",
    "IngestionError",
    "ModelLoadError",
    "PipelineError",
    "ProjectBaseError",
    "ResourceNotFoundError",
    "StorageError",
    "ValidationError",
]
