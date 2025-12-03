"""Tests for prediction/correction outcome logging.

Sprint 6.1.2: Tests for:
- Per-page outcome logging
- Sampling behavior in single and batch modes
- Teacher usage context
- Batch summaries
"""

from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.logging.outcomes import (
    DeviceUsed,
    GateDecision,
    ModelSelection,
    OutcomeLogger,
    PageOutcome,
    TeacherUsageContext,
    get_outcome_logger,
    timed_operation,
)

# ============================================================================
# PageOutcome Tests
# ============================================================================


class TestPageOutcome:
    """Tests for PageOutcome dataclass."""

    def test_default_values(self) -> None:
        """PageOutcome has sensible defaults."""
        outcome = PageOutcome(
            document_id="doc_123",
            page_index=0,
            gate_decision=GateDecision.TEXT_DETECTED,
        )
        assert outcome.document_id == "doc_123"
        assert outcome.page_index == 0
        assert outcome.model_selection == ModelSelection.STUDENT_ONLY
        assert outcome.device_used == DeviceUsed.CPU
        assert outcome.corrections_applied == []
        assert outcome.error is None

    def test_full_outcome(self) -> None:
        """PageOutcome can be fully populated."""
        outcome = PageOutcome(
            document_id="doc_456",
            page_index=5,
            gate_decision=GateDecision.TEXT_DETECTED,
            gate_confidence=0.95,
            gate_metrics={"stroke_density": 0.3, "edge_density": 0.4},
            model_selection=ModelSelection.TEACHER_UNCERTAINTY,
            student_confidence=0.6,
            teacher_confidence=0.92,
            device_used=DeviceUsed.GPU,
            quality_scores={"blur": 0.85, "noise": 0.90},
            overall_quality=0.87,
            corrections_applied=["deskew", "contrast"],
            corrections_rejected=["sharpen"],
            gate_time_ms=5.2,
            iqa_time_ms=15.3,
            correction_time_ms=8.1,
            total_time_ms=28.6,
        )
        assert outcome.teacher_confidence == pytest.approx(0.92)
        assert len(outcome.corrections_applied) == 2


# ============================================================================
# OutcomeLogger Tests
# ============================================================================


class TestOutcomeLogger:
    """Tests for OutcomeLogger class."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def outcome_logger(self, mock_logger: MagicMock) -> OutcomeLogger:
        """Create an outcome logger with mock."""
        return OutcomeLogger(
            logger=mock_logger,
            sample_rate=1.0,
            batch_sample_rate=1.0,
        )

    def test_logs_page_outcome(
        self, outcome_logger: OutcomeLogger, mock_logger: MagicMock
    ) -> None:
        """Page outcomes are logged."""
        outcome = PageOutcome(
            document_id="doc_123",
            page_index=0,
            gate_decision=GateDecision.TEXT_DETECTED,
            overall_quality=0.85,
        )
        outcome_logger.log_page_outcome(outcome)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "page_outcome"
        assert call_args[1]["document_id"] == "doc_123"
        assert call_args[1]["page_index"] == 0

    def test_logs_teacher_usage(
        self, outcome_logger: OutcomeLogger, mock_logger: MagicMock
    ) -> None:
        """Teacher usage context is logged."""
        context = TeacherUsageContext(
            document_id="doc_456",
            page_index=2,
            reason="low_confidence",
            student_confidence=0.45,
            teacher_confidence=0.92,
            device_used=DeviceUsed.MODAL,
            processing_time_ms=150.5,
        )
        outcome_logger.log_teacher_usage(context)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "teacher_usage"
        assert call_args[1]["reason"] == "low_confidence"

    def test_logs_blocked_teacher(
        self, outcome_logger: OutcomeLogger, mock_logger: MagicMock
    ) -> None:
        """Blocked teacher usage is logged as warning."""
        context = TeacherUsageContext(
            document_id="doc_789",
            page_index=0,
            reason="explicit_request",
            student_confidence=0.75,
            blocked=True,
            blocked_reason="no_gpu_available",
        )
        outcome_logger.log_teacher_usage(context)

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "teacher_blocked"
        assert call_args[1]["blocked"] is True

    def test_logs_gate_decision(
        self, outcome_logger: OutcomeLogger, mock_logger: MagicMock
    ) -> None:
        """Gate decisions are logged."""
        outcome_logger.log_gate_decision(
            document_id="doc_123",
            page_index=0,
            decision=GateDecision.TEXT_DETECTED,
            confidence=0.95,
            metrics={"stroke_density": 0.3},
            processing_time_ms=5.2,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "gate_decision"

    def test_logs_correction_outcome(
        self, outcome_logger: OutcomeLogger, mock_logger: MagicMock
    ) -> None:
        """Correction outcomes are logged."""
        outcome_logger.log_correction_outcome(
            document_id="doc_123",
            page_index=0,
            correction_type="deskew",
            applied=True,
            reason="skew_detected",
            before_score=0.65,
            after_score=0.85,
            processing_time_ms=12.3,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "correction_outcome"
        assert call_args[1]["improvement"] == pytest.approx(0.2)


# ============================================================================
# Sampling Tests
# ============================================================================


class TestSampling:
    """Tests for log sampling behavior."""

    def test_sample_rate_zero_drops_logs(self) -> None:
        """Sample rate 0 drops all non-critical logs."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=0.0,
            always_log_errors=False,
            always_log_teacher=False,
        )

        outcome = PageOutcome(
            document_id="doc_123",
            page_index=0,
            gate_decision=GateDecision.TEXT_DETECTED,
        )
        outcome_logger.log_page_outcome(outcome)

        mock_logger.info.assert_not_called()

    def test_always_logs_errors(self) -> None:
        """Errors are always logged regardless of sampling."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=0.0,
            always_log_errors=True,
        )

        outcome = PageOutcome(
            document_id="doc_123",
            page_index=0,
            gate_decision=GateDecision.ERROR,
            error="Processing failed",
        )
        outcome_logger.log_page_outcome(outcome)

        mock_logger.info.assert_called_once()

    def test_always_logs_teacher_usage(self) -> None:
        """Teacher usage is always logged regardless of sampling."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=0.0,
            always_log_teacher=True,
        )

        outcome = PageOutcome(
            document_id="doc_123",
            page_index=0,
            gate_decision=GateDecision.TEXT_DETECTED,
            model_selection=ModelSelection.TEACHER_UNCERTAINTY,
        )
        outcome_logger.log_page_outcome(outcome)

        mock_logger.info.assert_called_once()

    def test_batch_mode_uses_batch_sample_rate(self) -> None:
        """Batch mode uses lower sample rate."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=1.0,
            batch_sample_rate=0.0,  # Drop all in batch
            always_log_errors=False,
            always_log_teacher=False,
        )

        with outcome_logger.batch_context("batch_001", total_files=10):
            outcome = PageOutcome(
                document_id="doc_123",
                page_index=0,
                gate_decision=GateDecision.TEXT_DETECTED,
            )
            outcome_logger.log_page_outcome(outcome)

        # Page outcome should be dropped, but batch start/complete logged
        # Filter for page_outcome calls specifically
        page_outcome_calls = [
            c for c in mock_logger.info.call_args_list if c[0][0] == "page_outcome"
        ]
        assert len(page_outcome_calls) == 0


# ============================================================================
# Batch Context Tests
# ============================================================================


class TestBatchContext:
    """Tests for batch processing context."""

    def test_batch_context_logs_start_and_complete(self) -> None:
        """Batch context logs start and completion."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(logger=mock_logger, sample_rate=1.0)

        with outcome_logger.batch_context("batch_001", total_files=5):
            pass

        # Should have batch_started and batch_completed
        events = [c[0][0] for c in mock_logger.info.call_args_list]
        assert "batch_started" in events
        assert "batch_completed" in events

    def test_batch_context_tracks_outcomes(self) -> None:
        """Batch context tracks outcomes for summary."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=1.0,
            batch_sample_rate=1.0,
        )

        with outcome_logger.batch_context("batch_002", total_files=2):
            for i in range(3):
                outcome = PageOutcome(
                    document_id=f"doc_{i}",
                    page_index=0,
                    gate_decision=GateDecision.TEXT_DETECTED,
                    overall_quality=0.8 + i * 0.05,
                )
                outcome_logger.log_page_outcome(outcome)

        # Check batch_completed has summary
        batch_completed_calls = [
            c for c in mock_logger.info.call_args_list if c[0][0] == "batch_completed"
        ]
        assert len(batch_completed_calls) == 1

        summary = batch_completed_calls[0][1]
        assert summary["total_pages"] == 3

    def test_batch_summary_includes_aggregates(self) -> None:
        """Batch summary includes aggregate statistics."""
        mock_logger = MagicMock()
        outcome_logger = OutcomeLogger(
            logger=mock_logger,
            sample_rate=1.0,
            batch_sample_rate=1.0,
        )

        with outcome_logger.batch_context("batch_003", total_files=2):
            # One with teacher, one without
            outcome1 = PageOutcome(
                document_id="doc_1",
                page_index=0,
                gate_decision=GateDecision.TEXT_DETECTED,
                model_selection=ModelSelection.STUDENT_ONLY,
                device_used=DeviceUsed.CPU,
                overall_quality=0.8,
                corrections_applied=["deskew"],
            )
            outcome2 = PageOutcome(
                document_id="doc_2",
                page_index=0,
                gate_decision=GateDecision.NO_TEXT,
                model_selection=ModelSelection.TEACHER_UNCERTAINTY,
                device_used=DeviceUsed.GPU,
                overall_quality=0.7,
                corrections_applied=["contrast", "deskew"],
            )
            outcome_logger.log_page_outcome(outcome1)
            outcome_logger.log_page_outcome(outcome2)

        batch_completed_calls = [
            c for c in mock_logger.info.call_args_list if c[0][0] == "batch_completed"
        ]
        summary = batch_completed_calls[0][1]

        assert summary["total_pages"] == 2
        assert summary["teacher_count"] == 1
        assert "gate_decisions" in summary
        assert "device_distribution" in summary
        assert "correction_counts" in summary


# ============================================================================
# Timing Context Tests
# ============================================================================


class TestTimedOperation:
    """Tests for timed_operation context manager."""

    def test_records_duration(self) -> None:
        """Timed operation records duration."""
        with timed_operation("test_op", log_on_complete=False) as result:
            pass  # Quick operation

        assert result.duration_ms >= 0
        assert result.success is True
        assert result.error is None

    def test_records_errors(self) -> None:
        """Timed operation records errors."""
        with pytest.raises(ValueError):
            with timed_operation("failing_op", log_on_complete=False) as result:
                raise ValueError("Test error")

        assert result.success is False
        assert result.error == "Test error"
        assert result.duration_ms >= 0

    def test_logs_on_complete(self) -> None:
        """Timed operation logs on completion."""
        mock_logger = MagicMock()

        with timed_operation(
            "logged_op",
            logger=mock_logger,
            log_on_complete=True,
            extra_context="value",
        ) as result:
            pass

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "operation_timed"
        assert call_args[1]["operation"] == "logged_op"
        assert call_args[1]["extra_context"] == "value"


# ============================================================================
# Enum Tests
# ============================================================================


class TestEnums:
    """Tests for outcome enums."""

    def test_gate_decision_values(self) -> None:
        """GateDecision has expected values."""
        assert GateDecision.TEXT_DETECTED.value == "text_detected"
        assert GateDecision.NO_TEXT.value == "no_text"
        assert GateDecision.AMBIGUOUS.value == "ambiguous"
        assert GateDecision.ERROR.value == "error"

    def test_model_selection_values(self) -> None:
        """ModelSelection has expected values."""
        assert ModelSelection.STUDENT_ONLY.value == "student_only"
        assert ModelSelection.TEACHER_REQUESTED.value == "teacher_requested"
        assert ModelSelection.TEACHER_UNCERTAINTY.value == "teacher_uncertainty"
        assert ModelSelection.TEACHER_DISCREPANCY.value == "teacher_discrepancy"

    def test_device_used_values(self) -> None:
        """DeviceUsed has expected values."""
        assert DeviceUsed.CPU.value == "cpu"
        assert DeviceUsed.GPU.value == "gpu"
        assert DeviceUsed.CUDA.value == "cuda"
        assert DeviceUsed.MODAL.value == "modal"
        assert DeviceUsed.MPS.value == "mps"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestGetOutcomeLogger:
    """Tests for get_outcome_logger factory."""

    def test_creates_logger_with_defaults(self) -> None:
        """Factory creates logger with default config."""
        logger = get_outcome_logger()
        assert logger is not None
        assert logger.sample_rate == pytest.approx(1.0)  # Default from LoggingConfig

    def test_accepts_custom_rates(self) -> None:
        """Factory accepts custom sample rates."""
        logger = get_outcome_logger(sample_rate=0.5, batch_sample_rate=0.1)
        assert logger.sample_rate == pytest.approx(0.5)
        assert logger.batch_sample_rate == pytest.approx(0.1)
