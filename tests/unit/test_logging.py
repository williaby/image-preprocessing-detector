"""Tests for logging configuration."""

import logging
from unittest.mock import MagicMock, patch

from image_preprocessing_detector.utils.logging import (
    get_logger,
    log_performance,
    setup_logging,
)


class TestSetupLogging:
    """Test logging setup configuration."""

    @patch("image_preprocessing_detector.utils.logging.logging.basicConfig")
    @patch("image_preprocessing_detector.utils.logging.structlog.configure")
    def test_setup_logging_default(
        self, mock_structlog_configure: MagicMock, mock_basicConfig: MagicMock
    ) -> None:
        """Test setup_logging with default parameters."""
        setup_logging()

        # Verify basic config was called
        assert mock_basicConfig.called
        assert mock_basicConfig.call_args[1]["level"] == logging.INFO

        # Verify structlog was configured
        assert mock_structlog_configure.called

    @patch("image_preprocessing_detector.utils.logging.logging.basicConfig")
    @patch("image_preprocessing_detector.utils.logging.structlog.configure")
    def test_setup_logging_debug_level(
        self, mock_structlog_configure: MagicMock, mock_basicConfig: MagicMock
    ) -> None:
        """Test setup_logging with DEBUG level."""
        setup_logging(level="DEBUG")

        # Verify DEBUG level was set
        assert mock_basicConfig.call_args[1]["level"] == logging.DEBUG

    @patch("image_preprocessing_detector.utils.logging.logging.basicConfig")
    @patch("image_preprocessing_detector.utils.logging.structlog.configure")
    def test_setup_logging_json_mode(
        self, mock_structlog_configure: MagicMock, mock_basicConfig: MagicMock
    ) -> None:
        """Test setup_logging with JSON logging enabled."""
        setup_logging(json_logs=True)

        # Verify structlog was configured with JSON processor
        assert mock_structlog_configure.called
        call_kwargs = mock_structlog_configure.call_args[1]
        processors = call_kwargs["processors"]

        # Check that JSONRenderer is in processors
        assert any("JSONRenderer" in str(type(p)) for p in processors)

    @patch("image_preprocessing_detector.utils.logging.logging.basicConfig")
    @patch("image_preprocessing_detector.utils.logging.structlog.configure")
    def test_setup_logging_console_mode(
        self, mock_structlog_configure: MagicMock, mock_basicConfig: MagicMock
    ) -> None:
        """Test setup_logging with console logging (default)."""
        setup_logging(json_logs=False)

        # Verify structlog was configured with ConsoleRenderer
        assert mock_structlog_configure.called
        call_kwargs = mock_structlog_configure.call_args[1]
        processors = call_kwargs["processors"]

        # Check that ConsoleRenderer is in processors
        assert any("ConsoleRenderer" in str(type(p)) for p in processors)

    @patch("image_preprocessing_detector.utils.logging.logging.basicConfig")
    @patch("image_preprocessing_detector.utils.logging.structlog.configure")
    def test_setup_logging_no_timestamp(
        self, mock_structlog_configure: MagicMock, mock_basicConfig: MagicMock
    ) -> None:
        """Test setup_logging without timestamps."""
        setup_logging(include_timestamp=False)

        # Verify RichHandler was configured without timestamps
        assert mock_basicConfig.called


class TestGetLogger:
    """Test logger instance retrieval."""

    def test_get_logger_returns_logger(self) -> None:
        """Test get_logger returns a valid logger."""
        logger = get_logger("test_logger")

        assert logger is not None
        # Verify it's a structlog logger
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestLogPerformance:
    """Test performance logging utility."""

    def test_log_performance_success(self) -> None:
        """Test logging successful performance metrics."""
        mock_logger = MagicMock()

        log_performance(
            mock_logger,
            operation="test_operation",
            duration_ms=123.45,
            success=True,
            extra_field="value",
        )

        # Verify logger.info was called with correct arguments
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "performance"
        assert call_args[1]["operation"] == "test_operation"
        assert call_args[1]["duration_ms"] == 123.45
        assert call_args[1]["success"] is True
        assert call_args[1]["extra_field"] == "value"

    def test_log_performance_failure(self) -> None:
        """Test logging failed performance metrics."""
        mock_logger = MagicMock()

        log_performance(
            mock_logger, operation="failed_op", duration_ms=50.0, success=False
        )

        # Verify logger.info was called
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args

        assert call_args[1]["operation"] == "failed_op"
        assert call_args[1]["success"] is False

    def test_log_performance_rounds_duration(self) -> None:
        """Test that duration is rounded to 2 decimal places."""
        mock_logger = MagicMock()

        log_performance(
            mock_logger, operation="test_op", duration_ms=123.456789, success=True
        )

        # Verify duration was rounded
        call_args = mock_logger.info.call_args
        assert call_args[1]["duration_ms"] == 123.46  # Rounded to 2 decimals
