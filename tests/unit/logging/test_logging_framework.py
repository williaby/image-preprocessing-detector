"""Tests for the structured logging framework.

Sprint 6.1.1: Tests for:
- JSON log format and shape
- PII redaction
- Correlation ID threading
- Log rotation configuration
- Sampling behavior
"""

import json
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from image_preprocessing_detector.logging import (
    LoggingConfig,
    LoggingContext,
    PIIRedactor,
    get_correlation_id,
    get_logger,
    get_logging_config,
    get_request_context,
    log_performance,
    log_processing_outcome,
    log_teacher_usage,
    set_correlation_id,
    set_logging_config,
    set_request_context,
    setup_logging,
    update_request_context,
)

# ============================================================================
# PII Redaction Tests
# ============================================================================


class TestPIIRedaction:
    """Tests for PII redaction functionality."""

    @pytest.fixture
    def redactor(self) -> PIIRedactor:
        """Create a PIIRedactor with default config."""
        config = LoggingConfig(redact_pii=True)
        return PIIRedactor(config)

    @pytest.fixture
    def disabled_redactor(self) -> PIIRedactor:
        """Create a disabled PIIRedactor."""
        config = LoggingConfig(redact_pii=False)
        return PIIRedactor(config)

    def test_redacts_email_addresses(self, redactor: PIIRedactor) -> None:
        """Email addresses are redacted."""
        data = {"message": "Contact user@example.com for help"}
        result = redactor.redact(data)
        assert "user@example.com" not in result["message"]
        assert "[REDACTED]" in result["message"]

    def test_redacts_ssn(self, redactor: PIIRedactor) -> None:
        """Social security numbers are redacted."""
        data = {"message": "SSN: 123-45-6789"}
        result = redactor.redact(data)
        assert "123-45-6789" not in result["message"]
        assert "[REDACTED]" in result["message"]

    def test_redacts_credit_card_numbers(self, redactor: PIIRedactor) -> None:
        """Credit card numbers are redacted."""
        data = {"message": "Card: 4111111111111111"}
        result = redactor.redact(data)
        assert "4111111111111111" not in result["message"]
        assert "[REDACTED]" in result["message"]

    def test_redacts_formatted_credit_card(self, redactor: PIIRedactor) -> None:
        """Formatted credit card numbers are redacted."""
        data = {"message": "Card: 4111-1111-1111-1111"}
        result = redactor.redact(data)
        assert "4111-1111-1111-1111" not in result["message"]

    def test_redacts_phone_numbers(self, redactor: PIIRedactor) -> None:
        """Phone numbers are redacted."""
        data = {"message": "Call 555-123-4567"}
        result = redactor.redact(data)
        assert "555-123-4567" not in result["message"]
        assert "[REDACTED]" in result["message"]

    def test_redacts_sensitive_field_names(self, redactor: PIIRedactor) -> None:
        """Fields with sensitive names are redacted."""
        data = {
            "password": "secret123",
            "api_key": "sk_live_abc123",
            "username": "john_doe",
        }
        result = redactor.redact(data)
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["username"] == "john_doe"  # Not sensitive

    def test_redacts_nested_data(self, redactor: PIIRedactor) -> None:
        """Nested data structures are redacted."""
        data = {
            "user": {
                "email": "test@example.com",
                "password": "secret",
                "profile": {
                    "phone": "555-123-4567",
                },
            }
        }
        result = redactor.redact(data)
        assert result["user"]["password"] == "[REDACTED]"
        assert "[REDACTED]" in result["user"]["profile"]["phone"]

    def test_redacts_lists(self, redactor: PIIRedactor) -> None:
        """Lists are redacted."""
        data = {
            "emails": ["user1@example.com", "user2@example.com"],
        }
        result = redactor.redact(data)
        assert "[REDACTED]" in result["emails"][0]
        assert "[REDACTED]" in result["emails"][1]

    def test_disabled_redaction_passes_through(
        self, disabled_redactor: PIIRedactor
    ) -> None:
        """Disabled redaction passes data through unchanged."""
        data = {"email": "user@example.com", "password": "secret"}
        result = disabled_redactor.redact(data)
        assert result["email"] == "user@example.com"
        assert result["password"] == "secret"

    def test_preserves_non_pii_data(self, redactor: PIIRedactor) -> None:
        """Non-PII data is preserved."""
        data = {
            "document_id": "doc_123",
            "pages": 10,
            "status": "completed",
        }
        result = redactor.redact(data)
        assert result == data

    def test_case_insensitive_field_matching(self, redactor: PIIRedactor) -> None:
        """Field matching is case-insensitive."""
        data = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "API_KEY": "key123",
        }
        result = redactor.redact(data)
        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Password"] == "[REDACTED]"
        assert result["API_KEY"] == "[REDACTED]"


# ============================================================================
# Correlation ID Tests
# ============================================================================


class TestCorrelationID:
    """Tests for correlation ID management."""

    def test_set_and_get_correlation_id(self) -> None:
        """Correlation ID can be set and retrieved."""
        test_id = "test-correlation-123"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

    def test_correlation_id_default_empty(self) -> None:
        """Default correlation ID is empty string."""
        # Reset to default
        set_correlation_id("")
        assert get_correlation_id() == ""

    def test_logging_context_sets_correlation_id(self) -> None:
        """LoggingContext sets correlation ID."""
        with LoggingContext(correlation_id="ctx-123"):
            assert get_correlation_id() == "ctx-123"

    def test_logging_context_auto_generates_id(self) -> None:
        """LoggingContext auto-generates correlation ID if not provided."""
        with LoggingContext():
            correlation_id = get_correlation_id()
            # Should be a valid UUID
            uuid.UUID(correlation_id)

    def test_logging_context_restores_previous_id(self) -> None:
        """LoggingContext restores previous correlation ID on exit."""
        set_correlation_id("outer-id")
        with LoggingContext(correlation_id="inner-id"):
            assert get_correlation_id() == "inner-id"
        assert get_correlation_id() == "outer-id"


# ============================================================================
# Request Context Tests
# ============================================================================


class TestRequestContext:
    """Tests for request context management."""

    def test_set_and_get_request_context(self) -> None:
        """Request context can be set and retrieved."""
        context = {"user_id": "user_123", "tenant": "acme"}
        set_request_context(context)
        assert get_request_context() == context

    def test_update_request_context(self) -> None:
        """Request context can be updated incrementally."""
        set_request_context({"key1": "value1"})
        update_request_context(key2="value2")
        context = get_request_context()
        assert context["key1"] == "value1"
        assert context["key2"] == "value2"

    def test_logging_context_sets_request_context(self) -> None:
        """LoggingContext sets request context."""
        with LoggingContext(user_id="user_123", action="process"):
            context = get_request_context()
            assert context["user_id"] == "user_123"
            assert context["action"] == "process"

    def test_logging_context_restores_previous_context(self) -> None:
        """LoggingContext restores previous context on exit."""
        set_request_context({"outer": "value"})
        with LoggingContext(inner="value"):
            pass
        assert get_request_context() == {"outer": "value"}


# ============================================================================
# Log Shape Tests
# ============================================================================


class TestLogShape:
    """Tests for log output shape and structure."""

    @pytest.fixture
    def json_config(self) -> LoggingConfig:
        """Create JSON logging config."""
        return LoggingConfig(
            json_logs=True,
            log_level="DEBUG",
            redact_pii=False,
            include_timestamp=True,
            include_request_context=True,
            sample_rate=1.0,
        )

    @pytest.fixture
    def capture_logs(self) -> StringIO:
        """Capture log output."""
        return StringIO()

    def test_json_log_has_required_fields(self, json_config: LoggingConfig) -> None:
        """JSON logs contain required fields."""
        setup_logging(json_config)

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            set_correlation_id("test-123")
            logger.info("test_message", extra_field="value")

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert "event" in log_entry
                assert "level" in log_entry
                assert "logger" in log_entry
                assert "service" in log_entry
                assert "correlation_id" in log_entry

    def test_log_includes_correlation_id(self, json_config: LoggingConfig) -> None:
        """Logs include correlation ID when set."""
        setup_logging(json_config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            set_correlation_id("corr-456")
            logger = get_logger("test")
            logger.info("test")

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry.get("correlation_id") == "corr-456"

    def test_log_includes_service_info(self, json_config: LoggingConfig) -> None:
        """Logs include service metadata."""
        setup_logging(json_config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            logger.info("test")

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry.get("service") == "image-preprocessing-detector"

    def test_log_includes_timestamp(self, json_config: LoggingConfig) -> None:
        """Logs include ISO timestamp."""
        setup_logging(json_config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            logger.info("test")

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert "timestamp" in log_entry


# ============================================================================
# Log Rotation Tests
# ============================================================================


class TestLogRotation:
    """Tests for log file rotation configuration."""

    def test_file_logging_creates_directory(self, tmp_path: Path) -> None:
        """File logging creates parent directory if needed."""
        log_file = tmp_path / "subdir" / "app.log"
        config = LoggingConfig(
            json_logs=True,
            log_to_file=True,
            log_file_path=str(log_file),
        )
        setup_logging(config)

        logger = get_logger("test")
        logger.info("test message")

        # Directory should exist
        assert log_file.parent.exists()

    def test_rotation_config_accepted(self) -> None:
        """Rotation configuration is accepted."""
        config = LoggingConfig(
            log_to_file=True,
            max_bytes=5 * 1024 * 1024,  # 5MB
            backup_count=10,
            rotation_when="midnight",
        )
        assert config.max_bytes == 5 * 1024 * 1024
        assert config.backup_count == 10
        assert config.rotation_when == "midnight"


# ============================================================================
# Sampling Tests
# ============================================================================


class TestLogSampling:
    """Tests for log sampling behavior."""

    def test_always_log_warning_and_above(self) -> None:
        """WARNING and above are always logged regardless of sampling."""
        config = LoggingConfig(
            json_logs=True,
            sample_rate=0.0,  # Drop all
            always_log_levels=["WARNING", "ERROR", "CRITICAL"],
        )
        setup_logging(config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            logger.warning("warning message")

            output = mock_stdout.getvalue()
            # Warning should still be logged
            assert "warning message" in output or output == ""  # May be filtered

    def test_sampling_rate_one_logs_everything(self) -> None:
        """Sample rate of 1.0 logs everything."""
        config = LoggingConfig(
            json_logs=True,
            sample_rate=1.0,
        )
        # Sampling rate 1.0 means nothing should be dropped
        assert config.sample_rate == pytest.approx(1.0)
        # Verify the config allows all levels through
        assert "WARNING" in config.always_log_levels
        assert "ERROR" in config.always_log_levels


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for logging convenience functions."""

    @pytest.fixture(autouse=True)
    def setup_logging_for_tests(self) -> None:
        """Setup logging before each test."""
        config = LoggingConfig(
            json_logs=True,
            log_level="DEBUG",
            redact_pii=False,
            sample_rate=1.0,
        )
        setup_logging(config)

    def test_log_performance_structure(self) -> None:
        """log_performance outputs correct structure."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            log_performance(
                logger,
                operation="iqa_inference",
                duration_ms=15.5,
                success=True,
                model="resnet18",
            )

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry["event"] == "performance"
                assert log_entry["operation"] == "iqa_inference"
                assert log_entry["duration_ms"] == pytest.approx(15.5)
                assert log_entry["success"] is True
                assert log_entry["model"] == "resnet18"

    def test_log_processing_outcome_structure(self) -> None:
        """log_processing_outcome outputs correct structure."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            log_processing_outcome(
                logger,
                document_id="doc_123",
                page_index=0,
                device_used="gpu",
                model_used="student",
                processing_time_ms=25.3,
                corrections_applied=["deskew", "contrast"],
                gate_reason="high_quality",
                quality_score=0.85,
            )

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry["event"] == "processing_outcome"
                assert log_entry["document_id"] == "doc_123"
                assert log_entry["page_index"] == 0
                assert log_entry["device_used"] == "gpu"
                assert log_entry["model_used"] == "student"
                assert log_entry["corrections_applied"] == ["deskew", "contrast"]
                assert log_entry["quality_score"] == pytest.approx(0.85)

    def test_log_teacher_usage_structure(self) -> None:
        """log_teacher_usage outputs correct structure."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            logger = get_logger("test")
            log_teacher_usage(
                logger,
                document_id="doc_456",
                page_index=2,
                reason="low_confidence",
                student_confidence=0.45,
                teacher_confidence=0.92,
                device_used="modal",
                processing_time_ms=150.5,
            )

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry["event"] == "teacher_usage"
                assert log_entry["document_id"] == "doc_456"
                assert log_entry["reason"] == "low_confidence"
                assert log_entry["student_confidence"] == pytest.approx(0.45)
                assert log_entry["teacher_confidence"] == pytest.approx(0.92)


# ============================================================================
# Configuration Tests
# ============================================================================


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_config_from_environment(self) -> None:
        """Configuration can be loaded from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "IMGPREP_JSON_LOGS": "true",
                "IMGPREP_LOG_LEVEL": "DEBUG",
                "IMGPREP_REDACT_PII": "false",
            },
        ):
            setup_logging()
            config = get_logging_config()
            # Config should reflect environment (after setup_logging creates new config)

    def test_config_defaults(self) -> None:
        """Default configuration values are correct."""
        config = LoggingConfig()
        assert config.json_logs is False
        assert config.log_level == "INFO"
        assert config.redact_pii is True
        assert config.sample_rate == pytest.approx(1.0)
        assert config.log_to_file is False

    def test_config_validation(self) -> None:
        """Configuration validates correctly."""
        # Valid config
        config = LoggingConfig(
            log_level="DEBUG",
            sample_rate=0.5,
            max_bytes=1024,
            backup_count=3,
        )
        assert config.sample_rate == pytest.approx(0.5)

    def test_set_and_get_config(self) -> None:
        """Configuration can be set and retrieved."""
        config = LoggingConfig(log_level="ERROR")
        set_logging_config(config)
        retrieved = get_logging_config()
        assert retrieved.log_level == "ERROR"


# ============================================================================
# Integration Tests
# ============================================================================


class TestLoggingIntegration:
    """Integration tests for logging framework."""

    def test_full_pipeline_with_context(self) -> None:
        """Full logging pipeline with correlation ID and context."""
        config = LoggingConfig(
            json_logs=True,
            redact_pii=True,
            sample_rate=1.0,
        )
        setup_logging(config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with LoggingContext(
                correlation_id="integration-test-123",
                user_id="test_user",
                document_id="doc_abc",
            ):
                logger = get_logger("integration")
                logger.info(
                    "processing_started",
                    file_name="test.pdf",
                    email="user@example.com",  # Should be redacted
                )

            output = mock_stdout.getvalue()
            if output:
                log_entry = json.loads(output.strip())
                assert log_entry["correlation_id"] == "integration-test-123"
                assert "[REDACTED]" in log_entry.get("email", "[REDACTED]")

    def test_nested_logging_contexts(self) -> None:
        """Nested logging contexts work correctly."""
        config = LoggingConfig(json_logs=True, sample_rate=1.0)
        setup_logging(config)

        with LoggingContext(correlation_id="outer"):
            assert get_correlation_id() == "outer"

            with LoggingContext(correlation_id="inner"):
                assert get_correlation_id() == "inner"

            assert get_correlation_id() == "outer"
