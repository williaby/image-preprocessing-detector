"""Tests for error taxonomy and Sentry integration.

Sprint 6.1.3: Tests for error codes, exception mapping, and Sentry integration
in both disabled and enabled modes.
"""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.logging.errors import (
    ERROR_CATEGORIES,
    ERROR_HTTP_STATUS,
    AppError,
    AuthenticationError,
    ErrorCategory,
    ErrorCode,
    ErrorLogger,
    InfrastructureError,
    ProcessingError,
    RateLimitError,
    SentryIntegration,
    StructuredError,
    ValidationError,
    create_error,
    get_error_logger,
    map_exception_to_error,
)

# ============================================================================
# Error Code Tests
# ============================================================================


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_validation_error_codes_exist(self) -> None:
        """Test validation error codes are defined."""
        assert ErrorCode.INVALID_FILE_TYPE.value == "E1001"
        assert ErrorCode.FILE_TOO_LARGE.value == "E1002"
        assert ErrorCode.INVALID_PARAMETERS.value == "E1003"
        assert ErrorCode.EMPTY_FILE.value == "E1004"
        assert ErrorCode.INVALID_IMAGE_FORMAT.value == "E1005"
        assert ErrorCode.CORRUPT_PDF.value == "E1006"

    def test_processing_error_codes_exist(self) -> None:
        """Test processing error codes are defined."""
        assert ErrorCode.PROCESSING_FAILED.value == "E2001"
        assert ErrorCode.IQA_FAILED.value == "E2002"
        assert ErrorCode.CORRECTION_FAILED.value == "E2003"
        assert ErrorCode.MODEL_INFERENCE_FAILED.value == "E2008"

    def test_infrastructure_error_codes_exist(self) -> None:
        """Test infrastructure error codes are defined."""
        assert ErrorCode.GPU_UNAVAILABLE.value == "E3001"
        assert ErrorCode.MODEL_LOAD_FAILED.value == "E3002"
        assert ErrorCode.MEMORY_EXHAUSTED.value == "E3003"
        assert ErrorCode.MODAL_CONNECTION_FAILED.value == "E3006"

    def test_authentication_error_codes_exist(self) -> None:
        """Test authentication error codes are defined."""
        assert ErrorCode.UNAUTHORIZED.value == "E4001"
        assert ErrorCode.INVALID_API_KEY.value == "E4002"
        assert ErrorCode.FORBIDDEN.value == "E4004"

    def test_rate_limit_error_codes_exist(self) -> None:
        """Test rate limiting error codes are defined."""
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "E5001"
        assert ErrorCode.QUOTA_EXCEEDED.value == "E5002"

    def test_internal_error_codes_exist(self) -> None:
        """Test internal error codes are defined."""
        assert ErrorCode.INTERNAL_ERROR.value == "E9001"
        assert ErrorCode.UNEXPECTED_ERROR.value == "E9002"
        assert ErrorCode.ASSERTION_FAILED.value == "E9003"

    def test_error_code_is_string_enum(self) -> None:
        """Test ErrorCode is a string enum."""
        assert isinstance(ErrorCode.PROCESSING_FAILED, str)
        assert ErrorCode.PROCESSING_FAILED == "E2001"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Test all error categories are defined."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.PROCESSING.value == "processing"
        assert ErrorCategory.INFRASTRUCTURE.value == "infrastructure"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.RATE_LIMITING.value == "rate_limiting"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.EXTERNAL_SERVICE.value == "external_service"
        assert ErrorCategory.INTERNAL.value == "internal"


class TestErrorMappings:
    """Tests for error code mappings."""

    def test_all_error_codes_have_category(self) -> None:
        """Test all error codes are mapped to a category."""
        for code in ErrorCode:
            assert code in ERROR_CATEGORIES, f"Missing category for {code}"

    def test_all_error_codes_have_http_status(self) -> None:
        """Test all error codes are mapped to HTTP status."""
        for code in ErrorCode:
            assert code in ERROR_HTTP_STATUS, f"Missing HTTP status for {code}"

    def test_validation_errors_return_400(self) -> None:
        """Test validation errors map to 400 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.INVALID_FILE_TYPE] == 400
        assert ERROR_HTTP_STATUS[ErrorCode.FILE_TOO_LARGE] == 400
        assert ERROR_HTTP_STATUS[ErrorCode.INVALID_PARAMETERS] == 400

    def test_processing_errors_return_422(self) -> None:
        """Test processing errors map to 422 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.PROCESSING_FAILED] == 422
        assert ERROR_HTTP_STATUS[ErrorCode.IQA_FAILED] == 422

    def test_auth_errors_return_401_or_403(self) -> None:
        """Test authentication errors map to 401/403 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.UNAUTHORIZED] == 401
        assert ERROR_HTTP_STATUS[ErrorCode.FORBIDDEN] == 403
        assert ERROR_HTTP_STATUS[ErrorCode.INVALID_API_KEY] == 403

    def test_rate_limit_errors_return_429(self) -> None:
        """Test rate limit errors map to 429 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.RATE_LIMIT_EXCEEDED] == 429
        assert ERROR_HTTP_STATUS[ErrorCode.QUOTA_EXCEEDED] == 429

    def test_infrastructure_errors_return_500(self) -> None:
        """Test infrastructure errors map to 500 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.GPU_UNAVAILABLE] == 500
        assert ERROR_HTTP_STATUS[ErrorCode.MODEL_LOAD_FAILED] == 500

    def test_external_service_errors_return_502_or_504(self) -> None:
        """Test external service errors map to 502/504 status."""
        assert ERROR_HTTP_STATUS[ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE] == 502
        assert ERROR_HTTP_STATUS[ErrorCode.EXTERNAL_SERVICE_TIMEOUT] == 504


# ============================================================================
# Structured Error Tests
# ============================================================================


class TestStructuredError:
    """Tests for StructuredError dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic error creation."""
        error = StructuredError(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Invalid file type",
        )
        assert error.code == ErrorCode.INVALID_FILE_TYPE
        assert error.message == "Invalid file type"
        assert error.category == ErrorCategory.VALIDATION
        assert error.http_status == 400

    def test_category_auto_populated(self) -> None:
        """Test category is auto-populated from code."""
        error = StructuredError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Processing failed",
        )
        assert error.category == ErrorCategory.PROCESSING

    def test_http_status_auto_populated(self) -> None:
        """Test HTTP status is auto-populated from code."""
        error = StructuredError(
            code=ErrorCode.UNAUTHORIZED,
            message="Not authorized",
        )
        assert error.http_status == 401

    def test_correlation_id_from_context(self) -> None:
        """Test correlation ID comes from context."""
        from image_preprocessing_detector.logging import set_correlation_id

        # Set correlation ID in context
        set_correlation_id("test-correlation-123")

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal error",
        )
        assert error.correlation_id == "test-correlation-123"

        # Clean up
        set_correlation_id("")

    def test_correlation_id_empty_when_no_context(self) -> None:
        """Test correlation ID is empty string when no context set."""
        from image_preprocessing_detector.logging import set_correlation_id

        # Ensure no correlation ID set
        set_correlation_id("")

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal error",
        )
        # Default is empty string when no context
        assert error.correlation_id == ""

    def test_timestamp_generated(self) -> None:
        """Test timestamp is generated."""
        before = datetime.now(UTC)
        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal error",
        )
        after = datetime.now(UTC)

        assert before <= error.timestamp <= after

    def test_details_stored(self) -> None:
        """Test details are stored."""
        error = StructuredError(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Invalid file",
            details={"file_type": "exe", "expected": ["pdf", "png"]},
        )
        assert error.details["file_type"] == "exe"
        assert error.details["expected"] == ["pdf", "png"]

    def test_exception_stored(self) -> None:
        """Test exception is stored."""
        original = ValueError("Bad value")
        error = StructuredError(
            code=ErrorCode.INVALID_PARAMETERS,
            message="Invalid params",
            exception=original,
        )
        assert error.exception is original

    def test_to_dict_basic(self) -> None:
        """Test to_dict conversion."""
        error = StructuredError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Processing failed",
            details={"page": 5},
        )
        result = error.to_dict()

        assert result["error_code"] == "E2001"
        assert result["error_name"] == "PROCESSING_FAILED"
        assert result["message"] == "Processing failed"
        assert result["category"] == "processing"
        assert result["http_status"] == 422
        assert result["details"] == {"page": 5}
        assert "correlation_id" in result
        assert "timestamp" in result

    def test_to_dict_excludes_traceback_by_default(self) -> None:
        """Test traceback is excluded by default."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error = StructuredError(
                code=ErrorCode.INVALID_PARAMETERS,
                message="Error",
                exception=e,
            )

        result = error.to_dict()
        assert "traceback" not in result

    def test_to_dict_includes_traceback_when_requested(self) -> None:
        """Test traceback is included when requested."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error = StructuredError(
                code=ErrorCode.INVALID_PARAMETERS,
                message="Error",
                exception=e,
            )

        result = error.to_dict(include_traceback=True)
        assert "traceback" in result
        assert "ValueError" in result["traceback"]

    def test_to_api_response(self) -> None:
        """Test API response format."""
        error = StructuredError(
            code=ErrorCode.FILE_TOO_LARGE,
            message="File exceeds maximum size",
            details={"size_mb": 150, "max_mb": 100},
        )
        result = error.to_api_response()

        assert result["error"] == "file_too_large"
        assert result["error_code"] == "E1002"
        assert result["message"] == "File exceeds maximum size"
        assert result["details"]["size_mb"] == 150
        assert "correlation_id" in result
        assert "http_status" not in result  # Not in API response


# ============================================================================
# Exception Classes Tests
# ============================================================================


class TestAppError:
    """Tests for AppError base class."""

    def test_basic_creation(self) -> None:
        """Test basic error creation."""
        error = AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Something went wrong",
        )
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_with_details(self) -> None:
        """Test error with details."""
        error = AppError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Failed",
            details={"reason": "timeout"},
        )
        assert error.details == {"reason": "timeout"}

    def test_to_structured_error(self) -> None:
        """Test conversion to StructuredError."""
        error = AppError(
            code=ErrorCode.GPU_UNAVAILABLE,
            message="No GPU available",
            details={"requested": "cuda:0"},
        )
        structured = error.to_structured_error()

        assert isinstance(structured, StructuredError)
        assert structured.code == ErrorCode.GPU_UNAVAILABLE
        assert structured.message == "No GPU available"
        assert structured.details == {"requested": "cuda:0"}
        assert structured.exception is error

    def test_is_exception(self) -> None:
        """Test AppError is an Exception."""
        error = AppError(ErrorCode.INTERNAL_ERROR, "Test")
        assert isinstance(error, Exception)

        with pytest.raises(AppError):
            raise error


class TestValidationError:
    """Tests for ValidationError."""

    def test_default_code(self) -> None:
        """Test default error code."""
        error = ValidationError(message="Invalid input")
        assert error.code == ErrorCode.INVALID_PARAMETERS

    def test_custom_code(self) -> None:
        """Test custom error code."""
        error = ValidationError(
            code=ErrorCode.CORRUPT_PDF,
            message="PDF is corrupted",
        )
        assert error.code == ErrorCode.CORRUPT_PDF

    def test_is_app_error(self) -> None:
        """Test ValidationError is an AppError."""
        error = ValidationError()
        assert isinstance(error, AppError)


class TestProcessingError:
    """Tests for ProcessingError."""

    def test_default_code(self) -> None:
        """Test default error code."""
        error = ProcessingError(message="Processing failed")
        assert error.code == ErrorCode.PROCESSING_FAILED

    def test_custom_code(self) -> None:
        """Test custom error code."""
        error = ProcessingError(
            code=ErrorCode.IQA_FAILED,
            message="IQA failed",
        )
        assert error.code == ErrorCode.IQA_FAILED


class TestInfrastructureError:
    """Tests for InfrastructureError."""

    def test_default_code(self) -> None:
        """Test default error code."""
        error = InfrastructureError(message="Infrastructure error")
        assert error.code == ErrorCode.INTERNAL_ERROR

    def test_custom_code(self) -> None:
        """Test custom error code."""
        error = InfrastructureError(
            code=ErrorCode.MODAL_CONNECTION_FAILED,
            message="Cannot connect to Modal",
        )
        assert error.code == ErrorCode.MODAL_CONNECTION_FAILED


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_default_code(self) -> None:
        """Test default error code."""
        error = AuthenticationError(message="Auth required")
        assert error.code == ErrorCode.UNAUTHORIZED

    def test_custom_code(self) -> None:
        """Test custom error code."""
        error = AuthenticationError(
            code=ErrorCode.EXPIRED_API_KEY,
            message="API key expired",
        )
        assert error.code == ErrorCode.EXPIRED_API_KEY


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default_code(self) -> None:
        """Test default error code."""
        error = RateLimitError(message="Rate limit exceeded")
        assert error.code == ErrorCode.RATE_LIMIT_EXCEEDED

    def test_custom_code(self) -> None:
        """Test custom error code."""
        error = RateLimitError(
            code=ErrorCode.QUOTA_EXCEEDED,
            message="Monthly quota exceeded",
        )
        assert error.code == ErrorCode.QUOTA_EXCEEDED


# ============================================================================
# Exception Mapping Tests
# ============================================================================


class TestExceptionMapping:
    """Tests for exception to error code mapping."""

    def test_file_not_found_maps_correctly(self) -> None:
        """Test FileNotFoundError mapping."""
        error = map_exception_to_error(FileNotFoundError("file.pdf"))
        assert error.code == ErrorCode.INVALID_FILE_TYPE

    def test_permission_error_maps_correctly(self) -> None:
        """Test PermissionError mapping."""
        error = map_exception_to_error(PermissionError("Access denied"))
        assert error.code == ErrorCode.FORBIDDEN

    def test_memory_error_maps_correctly(self) -> None:
        """Test MemoryError mapping."""
        error = map_exception_to_error(MemoryError())
        assert error.code == ErrorCode.MEMORY_EXHAUSTED

    def test_timeout_error_maps_correctly(self) -> None:
        """Test TimeoutError mapping."""
        error = map_exception_to_error(TimeoutError("Operation timed out"))
        assert error.code == ErrorCode.TIMEOUT

    def test_value_error_maps_correctly(self) -> None:
        """Test ValueError mapping."""
        error = map_exception_to_error(ValueError("Bad value"))
        assert error.code == ErrorCode.INVALID_PARAMETERS

    def test_assertion_error_maps_correctly(self) -> None:
        """Test AssertionError mapping."""
        error = map_exception_to_error(AssertionError("Assertion failed"))
        assert error.code == ErrorCode.ASSERTION_FAILED

    def test_unmapped_exception_returns_unexpected(self) -> None:
        """Test unmapped exceptions return UNEXPECTED_ERROR."""
        error = map_exception_to_error(KeyboardInterrupt())
        assert error.code == ErrorCode.UNEXPECTED_ERROR

    def test_app_error_returns_structured_error(self) -> None:
        """Test AppError returns its structured error."""
        app_error = ValidationError(
            code=ErrorCode.CORRUPT_PDF,
            message="PDF corrupted",
            details={"page": 5},
        )
        error = map_exception_to_error(app_error)

        assert error.code == ErrorCode.CORRUPT_PDF
        assert error.message == "PDF corrupted"
        assert error.details == {"page": 5}

    def test_exception_message_preserved(self) -> None:
        """Test exception message is preserved."""
        error = map_exception_to_error(ValueError("Specific error message"))
        assert error.message == "Specific error message"


# ============================================================================
# Sentry Integration Tests - Disabled Mode
# ============================================================================


class TestSentryDisabled:
    """Tests for Sentry integration when disabled."""

    def setup_method(self) -> None:
        """Reset Sentry state before each test."""
        SentryIntegration._initialized = False
        SentryIntegration._enabled = False

    def test_is_enabled_returns_false_when_not_initialized(self) -> None:
        """Test is_enabled returns False when not initialized."""
        assert SentryIntegration.is_enabled() is False

    def test_initialize_returns_false_without_env_var(self) -> None:
        """Test initialization returns False without env var."""
        with patch.dict(os.environ, {}, clear=True):
            result = SentryIntegration.initialize()
            assert result is False
            assert SentryIntegration._initialized is True
            assert SentryIntegration._enabled is False

    def test_initialize_returns_false_with_false_env_var(self) -> None:
        """Test initialization returns False with IMGPREP_SENTRY_ENABLED=false."""
        with patch.dict(os.environ, {"IMGPREP_SENTRY_ENABLED": "false"}, clear=True):
            result = SentryIntegration.initialize()
            assert result is False
            assert SentryIntegration.is_enabled() is False

    def test_initialize_returns_false_without_dsn(self) -> None:
        """Test initialization returns False without DSN."""
        with patch.dict(os.environ, {"IMGPREP_SENTRY_ENABLED": "true"}, clear=True):
            result = SentryIntegration.initialize()
            assert result is False

    def test_capture_error_returns_none_when_disabled(self) -> None:
        """Test capture_error returns None when disabled."""
        SentryIntegration._initialized = True
        SentryIntegration._enabled = False

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Test error",
        )
        result = SentryIntegration.capture_error(error)
        assert result is None

    def test_add_breadcrumb_does_nothing_when_disabled(self) -> None:
        """Test add_breadcrumb does nothing when disabled."""
        SentryIntegration._initialized = True
        SentryIntegration._enabled = False

        # Should not raise
        SentryIntegration.add_breadcrumb(
            message="Test breadcrumb",
            category="test",
        )

    def test_set_user_does_nothing_when_disabled(self) -> None:
        """Test set_user does nothing when disabled."""
        SentryIntegration._initialized = True
        SentryIntegration._enabled = False

        # Should not raise
        SentryIntegration.set_user("user123", email="test@example.com")


# ============================================================================
# Sentry Integration Tests - Enabled Mode
# ============================================================================


class TestSentryEnabled:
    """Tests for Sentry integration when enabled."""

    def setup_method(self) -> None:
        """Reset Sentry state before each test."""
        SentryIntegration._initialized = False
        SentryIntegration._enabled = False

    def test_initialize_succeeds_with_valid_config(self) -> None:
        """Test initialization succeeds with valid configuration."""
        mock_sentry = MagicMock()
        mock_logging_integration = MagicMock()
        mock_sentry.integrations.logging.LoggingIntegration = mock_logging_integration

        with (
            patch.dict(
                os.environ,
                {
                    "IMGPREP_SENTRY_ENABLED": "true",
                    "SENTRY_DSN": "https://test@sentry.io/123",
                },
                clear=True,
            ),
            patch.dict(
                "sys.modules",
                {
                    "sentry_sdk": mock_sentry,
                    "sentry_sdk.integrations.logging": MagicMock(
                        LoggingIntegration=mock_logging_integration
                    ),
                },
            ),
        ):
            result = SentryIntegration.initialize()

            assert result is True
            assert SentryIntegration.is_enabled() is True
            mock_sentry.init.assert_called_once()

    def test_initialize_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        mock_sentry = MagicMock()
        mock_logging_integration = MagicMock()

        with (
            patch.dict(
                os.environ,
                {"IMGPREP_SENTRY_ENABLED": "true"},
                clear=True,
            ),
            patch.dict(
                "sys.modules",
                {
                    "sentry_sdk": mock_sentry,
                    "sentry_sdk.integrations.logging": MagicMock(
                        LoggingIntegration=mock_logging_integration
                    ),
                },
            ),
        ):
            SentryIntegration.initialize(
                dsn="https://custom@sentry.io/456",
                environment="production",
                release="1.0.0",
                sample_rate=0.5,
                traces_sample_rate=0.2,
            )

            call_kwargs = mock_sentry.init.call_args[1]
            assert call_kwargs["dsn"] == "https://custom@sentry.io/456"
            assert call_kwargs["environment"] == "production"
            assert call_kwargs["release"] == "1.0.0"
            assert call_kwargs["sample_rate"] == 0.5
            assert call_kwargs["traces_sample_rate"] == 0.2

    def test_capture_error_with_structured_error(self) -> None:
        """Test capture_error with StructuredError."""
        mock_sentry = MagicMock()

        SentryIntegration._initialized = True
        SentryIntegration._enabled = True

        original_exc = ValueError("Original error")
        error = StructuredError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Processing failed",
            details={"page": 5},
            exception=original_exc,
        )

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            SentryIntegration.capture_error(error, extra={"context": "test"})

            mock_sentry.set_context.assert_called_once()
            mock_sentry.set_tag.assert_called()
            mock_sentry.capture_exception.assert_called_once_with(original_exc)

    def test_capture_error_without_exception(self) -> None:
        """Test capture_error with StructuredError without exception."""
        mock_sentry = MagicMock()

        SentryIntegration._initialized = True
        SentryIntegration._enabled = True

        error = StructuredError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Processing failed",
        )

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            SentryIntegration.capture_error(error)

            mock_sentry.capture_message.assert_called_once_with(
                "Processing failed", level="error"
            )

    def test_capture_error_with_plain_exception(self) -> None:
        """Test capture_error with plain Exception."""
        mock_sentry = MagicMock()

        SentryIntegration._initialized = True
        SentryIntegration._enabled = True

        exc = RuntimeError("Runtime error")

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            SentryIntegration.capture_error(exc)

            mock_sentry.capture_exception.assert_called_once_with(exc)

    def test_add_breadcrumb_when_enabled(self) -> None:
        """Test add_breadcrumb when Sentry is enabled."""
        mock_sentry = MagicMock()

        SentryIntegration._initialized = True
        SentryIntegration._enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            SentryIntegration.add_breadcrumb(
                message="User clicked button",
                category="ui",
                level="info",
                data={"button_id": "submit"},
            )

            mock_sentry.add_breadcrumb.assert_called_once_with(
                category="ui",
                message="User clicked button",
                data={"button_id": "submit"},
                level="info",
            )

    def test_set_user_when_enabled(self) -> None:
        """Test set_user when Sentry is enabled."""
        mock_sentry = MagicMock()

        SentryIntegration._initialized = True
        SentryIntegration._enabled = True

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            SentryIntegration.set_user(
                "user123", email="test@example.com", name="Test User"
            )

            mock_sentry.set_user.assert_called_once_with(
                {"id": "user123", "email": "test@example.com", "name": "Test User"}
            )

    def test_initialize_handles_import_error(self) -> None:
        """Test initialization handles missing sentry-sdk."""
        import builtins

        # Reset state
        SentryIntegration._initialized = False
        SentryIntegration._enabled = False

        with patch.dict(
            os.environ,
            {
                "IMGPREP_SENTRY_ENABLED": "true",
                "SENTRY_DSN": "https://test@sentry.io/123",
            },
            clear=True,
        ):
            # Simulate import error by making the import raise
            original_import = builtins.__import__

            def raise_import_error(name, *args, **kwargs):
                if "sentry_sdk" in name:
                    raise ImportError("No module named 'sentry_sdk'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=raise_import_error):
                result = SentryIntegration.initialize()
                assert result is False
                assert SentryIntegration._enabled is False


# ============================================================================
# Error Logger Tests
# ============================================================================


class TestErrorLogger:
    """Tests for ErrorLogger class."""

    def setup_method(self) -> None:
        """Reset Sentry state before each test."""
        SentryIntegration._initialized = False
        SentryIntegration._enabled = False

    def test_basic_creation(self) -> None:
        """Test basic logger creation."""
        logger = ErrorLogger()
        assert logger.logger is not None

    def test_with_custom_logger(self) -> None:
        """Test with custom logger."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)
        assert error_logger.logger is mock_logger

    def test_log_error_with_structured_error(self) -> None:
        """Test logging a StructuredError."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error = StructuredError(
            code=ErrorCode.PROCESSING_FAILED,
            message="Processing failed",
            details={"page": 5},
        )
        result = error_logger.log_error(error, capture_to_sentry=False)

        assert result is error
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["error_code"] == "E2001"
        assert call_kwargs["category"] == "processing"

    def test_log_error_with_exception(self) -> None:
        """Test logging a plain exception."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        exc = ValueError("Bad value")
        result = error_logger.log_error(exc, capture_to_sentry=False)

        assert result.code == ErrorCode.INVALID_PARAMETERS
        assert result.message == "Bad value"
        mock_logger.error.assert_called_once()

    def test_log_error_with_context(self) -> None:
        """Test logging with additional context."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Error",
        )
        error_logger.log_error(
            error,
            context={"request_id": "abc123"},
            capture_to_sentry=False,
        )

        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["request_id"] == "abc123"

    @patch.object(SentryIntegration, "capture_error")
    def test_log_error_captures_to_sentry_by_default(
        self, mock_capture: MagicMock
    ) -> None:
        """Test error is captured to Sentry by default."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Error",
        )
        error_logger.log_error(error)

        mock_capture.assert_called_once()

    @patch.object(SentryIntegration, "capture_error")
    def test_log_error_skips_sentry_when_disabled(
        self, mock_capture: MagicMock
    ) -> None:
        """Test Sentry capture is skipped when disabled."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Error",
        )
        error_logger.log_error(error, capture_to_sentry=False)

        mock_capture.assert_not_called()

    def test_log_warning(self) -> None:
        """Test logging a warning."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error_logger.log_warning(
            message="This is a warning",
            code=ErrorCode.GPU_UNAVAILABLE,
            context={"fallback": "cpu"},
        )

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["message"] == "This is a warning"
        assert call_kwargs["error_code"] == "E3001"
        assert call_kwargs["fallback"] == "cpu"

    def test_log_warning_without_code(self) -> None:
        """Test logging a warning without error code."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error_logger.log_warning(message="Generic warning")

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_code"] is None


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_error_logger(self) -> None:
        """Test get_error_logger returns ErrorLogger."""
        logger = get_error_logger()
        assert isinstance(logger, ErrorLogger)

    def test_create_error_basic(self) -> None:
        """Test create_error basic usage."""
        error = create_error(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Invalid file type",
        )
        assert isinstance(error, StructuredError)
        assert error.code == ErrorCode.INVALID_FILE_TYPE
        assert error.message == "Invalid file type"

    def test_create_error_with_details(self) -> None:
        """Test create_error with details."""
        error = create_error(
            code=ErrorCode.FILE_TOO_LARGE,
            message="File too large",
            details={"size_mb": 150, "max_mb": 100},
        )
        assert error.details["size_mb"] == 150
        assert error.details["max_mb"] == 100

    def test_create_error_with_exception(self) -> None:
        """Test create_error with original exception."""
        original = ValueError("Original")
        error = create_error(
            code=ErrorCode.INVALID_PARAMETERS,
            message="Invalid params",
            exception=original,
        )
        assert error.exception is original


# ============================================================================
# Integration Tests
# ============================================================================


class TestErrorTaxonomyIntegration:
    """Integration tests for error taxonomy."""

    def test_full_error_flow(self) -> None:
        """Test complete error flow from creation to API response."""
        # Create validation error
        error = ValidationError(
            code=ErrorCode.CORRUPT_PDF,
            message="PDF is corrupted at page 5",
            details={"page": 5, "error_type": "invalid_xref"},
        )

        # Convert to structured
        structured = error.to_structured_error()

        # Verify structure
        assert structured.code == ErrorCode.CORRUPT_PDF
        assert structured.category == ErrorCategory.VALIDATION
        assert structured.http_status == 400

        # Convert to API response
        api_response = structured.to_api_response()

        assert api_response["error"] == "corrupt_pdf"
        assert api_response["error_code"] == "E1006"
        assert api_response["details"]["page"] == 5
        assert "correlation_id" in api_response

    def test_exception_chain_preserved(self) -> None:
        """Test exception chain is preserved."""
        try:
            try:
                raise ValueError("Root cause")
            except ValueError as e:
                raise ProcessingError(
                    code=ErrorCode.IQA_FAILED,
                    message="IQA failed due to invalid input",
                    details={"cause": str(e)},
                ) from e
        except ProcessingError as p:
            structured = p.to_structured_error()

            assert structured.code == ErrorCode.IQA_FAILED
            assert "Root cause" in structured.details["cause"]

    def test_all_exception_types_work(self) -> None:
        """Test all custom exception types work correctly."""
        exceptions = [
            ValidationError(message="Validation"),
            ProcessingError(message="Processing"),
            InfrastructureError(message="Infrastructure"),
            AuthenticationError(message="Auth"),
            RateLimitError(message="Rate limit"),
        ]

        for exc in exceptions:
            structured = exc.to_structured_error()
            assert structured is not None
            assert structured.code is not None
            assert structured.http_status > 0
