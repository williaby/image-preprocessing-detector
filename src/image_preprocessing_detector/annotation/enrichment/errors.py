"""Structured exception classes for enrichment operations.

This module provides a hierarchy of exception classes for handling enrichment
failures with detailed context and cause tracking.

Exception Hierarchy:
    EnrichmentError (base)
    ├── InferenceError - ML inference failures
    ├── ProviderUnavailableError - Provider not available
    ├── ValidationError - Enrichment data validation failures
    └── BatchProcessingError - Batch processing failures

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.errors import (
    ...     InferenceError,
    ...     ProviderUnavailableError,
    ... )
    >>>
    >>> try:
    ...     # Run inference
    ...     result = provider.enrich(image_path)
    ... except InferenceError as e:
    ...     print(f"Inference failed: {e}")
    ...     print(f"Provider: {e.provider_name}")
    ...     print(f"Cause: {e.cause}")
"""

from __future__ import annotations

from pathlib import Path


class EnrichmentError(Exception):
    """Base class for all enrichment errors.

    Attributes:
        message: Human-readable error message
        cause: Original exception that caused this error (if any)
    """

    def __init__(self, message: str, cause: Exception | None = None):
        """Initialize EnrichmentError.

        Args:
            message: Error message describing what went wrong
            cause: Original exception that caused this error
        """
        self.cause = cause
        super().__init__(message)


class InferenceError(EnrichmentError):
    """ML inference failed during enrichment.

    Raised when a provider encounters an error during model inference,
    such as CUDA out of memory, model loading failure, or inference timeout.

    Attributes:
        provider_name: Name of the provider that failed
        batch_size: Size of the batch being processed
        cause: Original exception
    """

    def __init__(self, provider_name: str, batch_size: int, cause: Exception):
        """Initialize InferenceError.

        Args:
            provider_name: Name of the provider (e.g., "doclayout_yolo")
            batch_size: Number of images in the batch
            cause: Original exception from inference
        """
        self.provider_name = provider_name
        self.batch_size = batch_size
        message = (
            f"Inference failed for provider '{provider_name}' "
            f"(batch_size={batch_size}): {cause}"
        )
        super().__init__(message, cause)


class ProviderUnavailableError(EnrichmentError):
    """ML provider is not available.

    Raised when a provider cannot be initialized or used, such as when
    GPU is required but not available, model checkpoint is missing, or
    dependencies are not installed.

    Attributes:
        provider_name: Name of the provider
        reason: Why the provider is unavailable
    """

    def __init__(self, provider_name: str, reason: str):
        """Initialize ProviderUnavailableError.

        Args:
            provider_name: Name of the provider (e.g., "siglip_iqa")
            reason: Explanation of why the provider is unavailable
        """
        self.provider_name = provider_name
        self.reason = reason
        message = f"Provider '{provider_name}' is unavailable: {reason}"
        super().__init__(message)


class ValidationError(EnrichmentError):
    """Enrichment data failed validation.

    Raised when enriched data does not pass schema validation,
    such as confidence scores out of range, invalid bounding boxes,
    or missing required fields.

    Attributes:
        errors: List of validation error messages
        warnings: List of validation warning messages
    """

    def __init__(self, errors: list[str], warnings: list[str] | None = None):
        """Initialize ValidationError.

        Args:
            errors: List of validation error messages
            warnings: List of non-fatal warning messages
        """
        self.errors = errors
        self.warnings = warnings or []
        message = f"Validation failed with {len(errors)} error(s): {errors[0]}"
        super().__init__(message)


class BatchProcessingError(EnrichmentError):
    """Batch processing encountered errors.

    Raised when batch processing completes but some images failed to process.
    Contains details about which images failed and why.

    Attributes:
        total_count: Total number of images in batch
        failed_count: Number of images that failed
        failed_paths: Paths to images that failed
        partial_results: Successfully processed results (if any)
    """

    def __init__(
        self,
        total_count: int,
        failed_count: int,
        failed_paths: list[Path],
        partial_results: list | None = None,
    ):
        """Initialize BatchProcessingError.

        Args:
            total_count: Total images in the batch
            failed_count: Number that failed processing
            failed_paths: List of paths that failed
            partial_results: Any successfully processed results
        """
        self.total_count = total_count
        self.failed_count = failed_count
        self.failed_paths = failed_paths
        self.partial_results = partial_results or []
        message = f"Batch processing failed: {failed_count}/{total_count} images failed"
        super().__init__(message)


__all__ = [
    "BatchProcessingError",
    "EnrichmentError",
    "InferenceError",
    "ProviderUnavailableError",
    "ValidationError",
]
