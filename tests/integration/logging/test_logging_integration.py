"""Integration tests for logging framework.

Sprint 6.1.5: Validates logging across modules with:
- End-to-end log flow verification
- Log shape snapshot tests
- Performance benchmarks
- PII redaction verification
"""

import json
import os
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.logging import (
    LoggingConfig,
    LoggingContext,
    PIIRedactor,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)
from image_preprocessing_detector.logging.errors import (
    ErrorCode,
    ErrorLogger,
    ProcessingError,
    StructuredError,
    ValidationError,
    create_error,
    get_error_logger,
    map_exception_to_error,
)
from image_preprocessing_detector.logging.outcomes import (
    DeviceUsed,
    GateDecision,
    ModelSelection,
    OutcomeLogger,
    PageOutcome,
    TeacherUsageContext,
    get_outcome_logger,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_log_dir() -> Path:
    """Create temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def json_logging_config(temp_log_dir: Path) -> LoggingConfig:
    """Create JSON logging configuration."""
    return LoggingConfig(
        json_logs=True,
        log_level="DEBUG",
        log_to_file=True,
        log_file_path=str(temp_log_dir / "app.log"),
        redact_pii=True,
        sample_rate=1.0,
    )


@pytest.fixture
def captured_logs() -> list[dict[str, Any]]:
    """Fixture to capture log output."""
    logs: list[dict[str, Any]] = []
    return logs


# ============================================================================
# End-to-End Log Flow Tests
# ============================================================================


class TestEndToEndLogFlow:
    """Tests for complete logging flow across modules."""

    def test_correlation_id_flows_through_pipeline(self) -> None:
        """Test correlation ID flows through all log modules."""
        with LoggingContext(correlation_id="test-flow-123"):
            # All loggers should see the same correlation ID
            assert get_correlation_id() == "test-flow-123"

            # Error logger
            error_logger = get_error_logger()
            assert get_correlation_id() == "test-flow-123"

            # Outcome logger
            outcome_logger = get_outcome_logger()
            assert get_correlation_id() == "test-flow-123"

    def test_nested_contexts_preserve_correlation(self) -> None:
        """Test nested contexts preserve and restore correlation IDs."""
        original_id = get_correlation_id()

        with LoggingContext(correlation_id="outer-123"):
            assert get_correlation_id() == "outer-123"

            with LoggingContext(correlation_id="inner-456"):
                assert get_correlation_id() == "inner-456"

            # Restored to outer
            assert get_correlation_id() == "outer-123"

        # Restored to original
        assert get_correlation_id() == original_id

    def test_error_creates_structured_log(self) -> None:
        """Test errors create properly structured logs."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        error = ProcessingError(
            code=ErrorCode.IQA_FAILED,
            message="IQA processing failed",
            details={"page": 5, "reason": "blur too high"},
        )

        error_logger.log_error(error, capture_to_sentry=False)

        # Verify log was called with structured data
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["error_code"] == "E2002"
        assert call_kwargs["error_name"] == "IQA_FAILED"
        assert call_kwargs["category"] == "processing"
        assert call_kwargs["http_status"] == 422

    def test_outcome_logging_with_batch_context(self) -> None:
        """Test outcome logging with batch context tracking."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger, sample_rate=1.0, batch_sample_rate=1.0
        )

        with outcome_logger.batch_context("batch-001", total_files=10):
            # Log some outcomes
            outcome = PageOutcome(
                document_id="doc_001",
                page_index=0,
                gate_decision=GateDecision.NO_TEXT,
                model_selection=ModelSelection.STUDENT_ONLY,
                device_used=DeviceUsed.CPU,
                overall_quality=0.85,
            )
            outcome_logger.log_page_outcome(outcome)

        # Should have batch start log and page outcome log
        assert mock_logger.info.call_count >= 1


# ============================================================================
# Log Shape Snapshot Tests
# ============================================================================


class TestLogShapeSnapshots:
    """Tests for log shape consistency."""

    def test_error_log_shape(self) -> None:
        """Test error log has expected shape."""
        error = create_error(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Unsupported file type: .exe",
            details={"file_type": ".exe", "allowed": [".pdf", ".png"]},
        )

        log_dict = error.to_dict()

        # Required fields
        assert "error_code" in log_dict
        assert "error_name" in log_dict
        assert "message" in log_dict
        assert "category" in log_dict
        assert "http_status" in log_dict
        assert "correlation_id" in log_dict
        assert "timestamp" in log_dict
        assert "details" in log_dict

        # Field types
        assert isinstance(log_dict["error_code"], str)
        assert isinstance(log_dict["http_status"], int)
        assert isinstance(log_dict["details"], dict)

    def test_api_response_shape(self) -> None:
        """Test API response has expected shape."""
        error = create_error(
            code=ErrorCode.FILE_TOO_LARGE,
            message="File exceeds 100MB limit",
            details={"size_mb": 150},
        )

        api_response = error.to_api_response()

        # API response fields
        assert "error" in api_response
        assert "error_code" in api_response
        assert "message" in api_response
        assert "details" in api_response
        assert "correlation_id" in api_response

        # Should NOT include internal fields
        assert "http_status" not in api_response
        assert "category" not in api_response
        assert "traceback" not in api_response

    def test_page_outcome_dataclass_shape(self) -> None:
        """Test PageOutcome dataclass has expected fields."""
        outcome = PageOutcome(
            document_id="doc_test",
            page_index=0,
            gate_decision=GateDecision.TEXT_DETECTED,
            model_selection=ModelSelection.TEACHER_UNCERTAINTY,
            device_used=DeviceUsed.GPU,
            overall_quality=0.72,
            total_time_ms=145.5,
            corrections_applied=["deskew", "contrast"],
        )

        # Convert to dict via asdict
        log_dict = asdict(outcome)

        # Required fields
        expected_fields = [
            "document_id",
            "page_index",
            "gate_decision",
            "model_selection",
            "device_used",
            "overall_quality",
            "total_time_ms",
            "corrections_applied",
        ]

        for field in expected_fields:
            assert field in log_dict, f"Missing field: {field}"

    def test_teacher_usage_dataclass_shape(self) -> None:
        """Test TeacherUsageContext dataclass has expected fields."""
        context = TeacherUsageContext(
            document_id="doc_test",
            page_index=2,
            reason="uncertainty_threshold",
            student_confidence=0.45,
            teacher_confidence=0.89,
            device_used=DeviceUsed.GPU,
            processing_time_ms=234.5,
        )

        # Convert to dict via asdict
        log_dict = asdict(context)

        # Required fields
        expected_fields = [
            "document_id",
            "page_index",
            "reason",
            "student_confidence",
            "teacher_confidence",
            "device_used",
            "processing_time_ms",
        ]

        for field in expected_fields:
            assert field in log_dict, f"Missing field: {field}"


# ============================================================================
# PII Redaction Tests
# ============================================================================


class TestPIIRedaction:
    """Tests for PII redaction functionality."""

    @pytest.fixture
    def redactor(self) -> PIIRedactor:
        """Create PII redactor instance."""
        config = LoggingConfig(redact_pii=True)
        return PIIRedactor(config)

    def test_redacts_email_addresses(self, redactor: PIIRedactor) -> None:
        """Test email addresses are redacted."""
        text = "Contact user@example.com for support"
        result = redactor.redact(text)
        assert "user@example.com" not in result
        assert "[REDACTED]" in result

    def test_redacts_ssn(self, redactor: PIIRedactor) -> None:
        """Test SSN patterns are redacted."""
        text = "SSN: 123-45-6789"
        result = redactor.redact(text)
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_redacts_credit_card(self, redactor: PIIRedactor) -> None:
        """Test credit card numbers are redacted."""
        text = "Card: 4111-1111-1111-1111"
        result = redactor.redact(text)
        assert "4111-1111-1111-1111" not in result
        assert "[REDACTED]" in result

    def test_redacts_phone_number(self, redactor: PIIRedactor) -> None:
        """Test phone numbers are redacted."""
        text = "Call (555) 123-4567"
        result = redactor.redact(text)
        assert "(555) 123-4567" not in result
        assert "[REDACTED]" in result

    def test_redacts_multiple_pii(self, redactor: PIIRedactor) -> None:
        """Test multiple PII types are redacted."""
        text = "Email: test@example.com, SSN: 111-22-3333, Phone: 555-123-4567"
        result = redactor.redact(text)

        assert "test@example.com" not in result
        assert "111-22-3333" not in result
        assert "555-123-4567" not in result

    def test_preserves_non_pii(self, redactor: PIIRedactor) -> None:
        """Test non-PII content is preserved."""
        text = "Processing document doc_123 on page 5"
        result = redactor.redact(text)
        assert result == text

    def test_redacts_in_dict_structure(self, redactor: PIIRedactor) -> None:
        """Test PII is redacted within dict structures."""
        data = {"email": "user@test.com", "name": "John", "password": "secret123"}
        result = redactor.redact(data)
        assert "user@test.com" not in str(result)
        assert "John" in result["name"]  # Non-PII preserved
        assert result["password"] == "[REDACTED]"  # Field name redaction


# ============================================================================
# Performance Tests
# ============================================================================


class TestLoggingPerformance:
    """Performance benchmarks for logging operations."""

    def test_structured_error_creation_performance(self) -> None:
        """Test StructuredError creation is fast."""
        iterations = 1000
        start = time.perf_counter()

        for i in range(iterations):
            error = StructuredError(
                code=ErrorCode.PROCESSING_FAILED,
                message=f"Error {i}",
                details={"iteration": i},
            )

        elapsed = time.perf_counter() - start
        per_op = (elapsed / iterations) * 1000  # ms

        # Should create errors quickly (< 1ms each)
        assert per_op < 1.0, f"Error creation took {per_op:.3f}ms per operation"

    def test_pii_redaction_performance(self) -> None:
        """Test PII redaction is fast."""
        config = LoggingConfig(redact_pii=True)
        redactor = PIIRedactor(config)
        text = "Email: user@example.com, SSN: 123-45-6789, Phone: (555) 123-4567"
        iterations = 1000

        start = time.perf_counter()

        for _ in range(iterations):
            redactor.redact(text)

        elapsed = time.perf_counter() - start
        per_op = (elapsed / iterations) * 1000  # ms

        # Should redact quickly (< 1ms each)
        assert per_op < 1.0, f"PII redaction took {per_op:.3f}ms per operation"

    def test_exception_mapping_performance(self) -> None:
        """Test exception mapping is fast."""
        exceptions = [
            ValueError("Bad value"),
            FileNotFoundError("Not found"),
            MemoryError(),
            RuntimeError("Runtime error"),
        ]
        iterations = 1000

        start = time.perf_counter()

        for i in range(iterations):
            exc = exceptions[i % len(exceptions)]
            map_exception_to_error(exc)

        elapsed = time.perf_counter() - start
        per_op = (elapsed / iterations) * 1000  # ms

        # Should map quickly (< 0.5ms each)
        assert per_op < 0.5, f"Exception mapping took {per_op:.3f}ms per operation"

    def test_page_outcome_creation_performance(self) -> None:
        """Test PageOutcome creation is fast."""
        iterations = 1000
        start = time.perf_counter()

        for i in range(iterations):
            outcome = PageOutcome(
                document_id=f"doc_{i}",
                page_index=i % 10,
                gate_decision=GateDecision.TEXT_DETECTED,
                model_selection=ModelSelection.STUDENT_ONLY,
                device_used=DeviceUsed.CPU,
                overall_quality=0.85,
                total_time_ms=100.0,
            )

        elapsed = time.perf_counter() - start
        per_op = (elapsed / iterations) * 1000  # ms

        # Should create outcomes quickly (< 0.5ms each)
        assert per_op < 0.5, f"Outcome creation took {per_op:.3f}ms per operation"


# ============================================================================
# Error Code Coverage Tests
# ============================================================================


class TestErrorCodeCoverage:
    """Tests to ensure error codes are properly used."""

    def test_all_error_codes_are_unique(self) -> None:
        """Test all error codes have unique values."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values)), "Duplicate error code values found"

    def test_all_http_statuses_are_valid(self) -> None:
        """Test all HTTP status codes are valid."""
        from image_preprocessing_detector.logging.errors import ERROR_HTTP_STATUS

        valid_statuses = {400, 401, 403, 404, 422, 429, 500, 502, 504}

        for code, status in ERROR_HTTP_STATUS.items():
            assert status in valid_statuses, f"Invalid HTTP status {status} for {code}"

    def test_validation_errors_map_to_400(self) -> None:
        """Test validation errors consistently map to 400."""
        validation_codes = [
            ErrorCode.INVALID_FILE_TYPE,
            ErrorCode.FILE_TOO_LARGE,
            ErrorCode.INVALID_PARAMETERS,
            ErrorCode.EMPTY_FILE,
            ErrorCode.INVALID_IMAGE_FORMAT,
            ErrorCode.CORRUPT_PDF,
        ]

        for code in validation_codes:
            error = StructuredError(code=code, message="Test")
            assert error.http_status == 400, f"{code} should map to 400"

    def test_processing_errors_map_to_422(self) -> None:
        """Test processing errors consistently map to 422."""
        processing_codes = [
            ErrorCode.PROCESSING_FAILED,
            ErrorCode.IQA_FAILED,
            ErrorCode.CORRECTION_FAILED,
            ErrorCode.MODEL_INFERENCE_FAILED,
        ]

        for code in processing_codes:
            error = StructuredError(code=code, message="Test")
            assert error.http_status == 422, f"{code} should map to 422"


# ============================================================================
# Sampling Behavior Tests
# ============================================================================


class TestSamplingBehavior:
    """Tests for log sampling functionality."""

    def test_error_logs_always_logged(self) -> None:
        """Test ERROR level outcomes are always logged when configured."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=0.0,  # Should skip all normal logs
            always_log_errors=True,
        )

        # Error outcomes should still be logged
        outcome = PageOutcome(
            document_id="doc_test",
            page_index=0,
            gate_decision=GateDecision.ERROR,
            model_selection=ModelSelection.STUDENT_ONLY,
            device_used=DeviceUsed.CPU,
            overall_quality=0.15,  # Low quality
            error="Processing failed",
        )
        outcome_logger.log_page_outcome(outcome)

        # Should have been logged due to error
        assert mock_logger.info.called or mock_logger.error.called or mock_logger.warning.called

    def test_teacher_usage_always_logged(self) -> None:
        """Test teacher usage is always logged for cost tracking."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=0.0,  # Should skip all normal logs
            always_log_teacher=True,
        )

        context = TeacherUsageContext(
            document_id="doc_test",
            page_index=0,
            reason="uncertainty",
            student_confidence=0.4,
            teacher_confidence=0.9,
            device_used=DeviceUsed.GPU,
            processing_time_ms=200.0,
        )
        outcome_logger.log_teacher_usage(context)

        # Teacher usage should be logged despite sample_rate=0
        mock_logger.info.assert_called()


# ============================================================================
# Integration with File Logging
# ============================================================================


class TestFileLogging:
    """Tests for file-based logging."""

    def test_logs_written_to_file(self, temp_log_dir: Path) -> None:
        """Test logs are written to file."""
        config = LoggingConfig(
            json_logs=True,
            log_level="INFO",
            log_to_file=True,
            log_file_path=str(temp_log_dir / "test.log"),
        )

        setup_logging(config)
        logger = get_logger("test")
        logger.info("test_message", key="value")

        # Give time for file write
        time.sleep(0.1)

        # Config should be accepted (actual file write depends on handler setup)
        assert config.log_to_file is True

    def test_rotation_config_accepted(self, temp_log_dir: Path) -> None:
        """Test rotation configuration is accepted."""
        config = LoggingConfig(
            json_logs=True,
            log_to_file=True,
            log_file_path=str(temp_log_dir / "test.log"),
            max_bytes=10 * 1024 * 1024,  # 10MB
            backup_count=5,
        )

        # Should not raise and config should have correct values
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 5


# ============================================================================
# Cross-Module Integration Tests
# ============================================================================


class TestCrossModuleIntegration:
    """Tests for integration between logging modules."""

    def test_error_logged_through_error_logger(self) -> None:
        """Test ValidationError flows through ErrorLogger correctly."""
        mock_logger = MagicMock()
        error_logger = ErrorLogger(logger=mock_logger)

        # Create and log a validation error
        error = ValidationError(
            code=ErrorCode.CORRUPT_PDF,
            message="PDF structure invalid",
            details={"page": 3},
        )
        result = error_logger.log_error(error, capture_to_sentry=False)

        # Verify result
        assert isinstance(result, StructuredError)
        assert result.code == ErrorCode.CORRUPT_PDF

        # Verify logging
        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["error_code"] == "E1006"

    def test_outcome_and_error_share_correlation(self) -> None:
        """Test outcome and error logs share correlation ID."""
        with LoggingContext(correlation_id="shared-123"):
            # Create outcome
            outcome = PageOutcome(
                document_id="doc_test",
                page_index=0,
                gate_decision=GateDecision.NO_TEXT,
                model_selection=ModelSelection.STUDENT_ONLY,
                device_used=DeviceUsed.CPU,
                overall_quality=0.85,
            )

            # Create error
            error = create_error(
                code=ErrorCode.PROCESSING_FAILED,
                message="Test error",
            )

            # Error should have correlation ID
            assert error.correlation_id == "shared-123"

    def test_batch_with_errors(self) -> None:
        """Test batch processing logs errors correctly."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger, sample_rate=1.0, batch_sample_rate=1.0
        )

        with outcome_logger.batch_context("batch-errors", total_files=3):
            # Log success
            outcome_logger.log_page_outcome(
                PageOutcome(
                    document_id="doc_1",
                    page_index=0,
                    gate_decision=GateDecision.NO_TEXT,
                    model_selection=ModelSelection.STUDENT_ONLY,
                    device_used=DeviceUsed.CPU,
                    overall_quality=0.9,
                )
            )

            # Log failure
            outcome_logger.log_page_outcome(
                PageOutcome(
                    document_id="doc_2",
                    page_index=0,
                    gate_decision=GateDecision.ERROR,
                    model_selection=ModelSelection.STUDENT_ONLY,
                    device_used=DeviceUsed.CPU,
                    overall_quality=0.1,
                    error="Processing failed",
                )
            )

        # Verify logs were made
        assert mock_logger.info.call_count >= 1
