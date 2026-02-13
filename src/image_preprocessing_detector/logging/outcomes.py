"""Prediction and correction outcome logging.

Sprint 6.1.2: Provides:
- Per-page outcome logging with sampling
- Teacher usage context logging
- Batch mode volume control
- Structured outcome events for analytics
"""

import random
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from image_preprocessing_detector.logging import (
    get_logger,
    get_logging_config,
)

# ============================================================================
# Outcome Data Classes
# ============================================================================


class GateDecision(StrEnum):
    """Text gate decision outcomes."""

    TEXT_DETECTED = "text_detected"
    NO_TEXT = "no_text"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class ModelSelection(StrEnum):
    """Model selection outcomes."""

    STUDENT_ONLY = "student_only"
    TEACHER_REQUESTED = "teacher_requested"
    TEACHER_UNCERTAINTY = "teacher_uncertainty"
    TEACHER_DISCREPANCY = "teacher_discrepancy"
    TEACHER_HIGH_RISK = "teacher_high_risk"


class DeviceUsed(StrEnum):
    """Device used for inference."""

    CPU = "cpu"
    GPU = "gpu"
    CUDA = "cuda"
    MODAL = "modal"
    MPS = "mps"


@dataclass
class PageOutcome:
    """Outcome data for a single page."""

    document_id: str
    page_index: int

    # Gate decision
    gate_decision: GateDecision
    gate_confidence: float = 0.0
    gate_metrics: dict[str, float] = field(default_factory=dict)

    # Model selection
    model_selection: ModelSelection = ModelSelection.STUDENT_ONLY
    student_confidence: float = 0.0
    teacher_confidence: float | None = None

    # Device
    device_used: DeviceUsed = DeviceUsed.CPU

    # Quality scores
    quality_scores: dict[str, float] = field(default_factory=dict)
    overall_quality: float = 0.0

    # Corrections
    corrections_applied: list[str] = field(default_factory=list)
    corrections_rejected: list[str] = field(default_factory=list)

    # Timing
    gate_time_ms: float = 0.0
    iqa_time_ms: float = 0.0
    correction_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Errors
    error: str | None = None


@dataclass
class TeacherUsageContext:
    """Context for teacher model usage."""

    document_id: str
    page_index: int
    reason: str
    student_confidence: float
    teacher_confidence: float | None = None
    device_used: DeviceUsed = DeviceUsed.GPU
    processing_time_ms: float | None = None
    blocked: bool = False
    blocked_reason: str | None = None


# ============================================================================
# Outcome Logger
# ============================================================================


class OutcomeLogger:
    """Logs processing outcomes with sampling support."""

    def __init__(
        self,
        logger: Any | None = None,
        sample_rate: float = 1.0,
        batch_sample_rate: float = 0.1,
        always_log_errors: bool = True,
        always_log_teacher: bool = True,
    ) -> None:
        """Initialize outcome logger.

        Args:
            logger: Structlog logger instance.
            sample_rate: Sampling rate for single document mode (0.0-1.0).
            batch_sample_rate: Sampling rate for batch mode (typically lower).
            always_log_errors: Always log errors regardless of sampling.
            always_log_teacher: Always log teacher usage regardless of sampling.
        """
        self.logger = logger or get_logger(__name__)
        self.sample_rate = sample_rate
        self.batch_sample_rate = batch_sample_rate
        self.always_log_errors = always_log_errors
        self.always_log_teacher = always_log_teacher

        # Batch mode tracking
        self._batch_mode = False
        self._batch_id: str | None = None
        self._batch_outcomes: list[PageOutcome] = []

    def _should_log(self, is_error: bool = False, is_teacher: bool = False) -> bool:
        """Determine if this event should be logged based on sampling."""
        if is_error and self.always_log_errors:
            return True
        if is_teacher and self.always_log_teacher:
            return True

        rate = self.batch_sample_rate if self._batch_mode else self.sample_rate
        return random.random() < rate  # nosec B311

    def log_page_outcome(self, outcome: PageOutcome) -> None:
        """Log a page processing outcome.

        Args:
            outcome: Page outcome data.
        """
        is_error = outcome.error is not None
        is_teacher = outcome.model_selection != ModelSelection.STUDENT_ONLY

        if not self._should_log(is_error=is_error, is_teacher=is_teacher):
            return

        self.logger.info(
            "page_outcome",
            document_id=outcome.document_id,
            page_index=outcome.page_index,
            gate_decision=outcome.gate_decision.value,
            gate_confidence=round(outcome.gate_confidence, 4),
            model_selection=outcome.model_selection.value,
            student_confidence=round(outcome.student_confidence, 4),
            teacher_confidence=(
                round(outcome.teacher_confidence, 4)
                if outcome.teacher_confidence is not None
                else None
            ),
            device_used=outcome.device_used.value,
            overall_quality=round(outcome.overall_quality, 4),
            quality_scores={k: round(v, 4) for k, v in outcome.quality_scores.items()},
            corrections_applied=outcome.corrections_applied,
            corrections_rejected=outcome.corrections_rejected,
            gate_time_ms=round(outcome.gate_time_ms, 2),
            iqa_time_ms=round(outcome.iqa_time_ms, 2),
            correction_time_ms=round(outcome.correction_time_ms, 2),
            total_time_ms=round(outcome.total_time_ms, 2),
            error=outcome.error,
            batch_mode=self._batch_mode,
            batch_id=self._batch_id,
        )

        # Track in batch
        if self._batch_mode:
            self._batch_outcomes.append(outcome)

    def log_teacher_usage(self, context: TeacherUsageContext) -> None:
        """Log teacher model usage context.

        Args:
            context: Teacher usage context.
        """
        if context.blocked:
            log_method = self.logger.warning
            event = "teacher_blocked"
        else:
            log_method = self.logger.info
            event = "teacher_usage"

        log_method(
            event,
            document_id=context.document_id,
            page_index=context.page_index,
            reason=context.reason,
            student_confidence=round(context.student_confidence, 4),
            teacher_confidence=(
                round(context.teacher_confidence, 4)
                if context.teacher_confidence is not None
                else None
            ),
            device_used=context.device_used.value,
            processing_time_ms=(
                round(context.processing_time_ms, 2)
                if context.processing_time_ms is not None
                else None
            ),
            blocked=context.blocked,
            blocked_reason=context.blocked_reason,
        )

    def log_gate_decision(
        self,
        document_id: str,
        page_index: int,
        decision: GateDecision,
        confidence: float,
        metrics: dict[str, float],
        processing_time_ms: float,
    ) -> None:
        """Log text gate decision.

        Args:
            document_id: Document identifier.
            page_index: Page number.
            decision: Gate decision.
            confidence: Decision confidence.
            metrics: Gate metrics (stroke density, edge density, etc.).
            processing_time_ms: Processing time.
        """
        if not self._should_log():
            return

        self.logger.info(
            "gate_decision",
            document_id=document_id,
            page_index=page_index,
            decision=decision.value,
            confidence=round(confidence, 4),
            metrics={k: round(v, 4) for k, v in metrics.items()},
            processing_time_ms=round(processing_time_ms, 2),
        )

    def log_correction_outcome(
        self,
        document_id: str,
        page_index: int,
        correction_type: str,
        applied: bool,
        reason: str,
        before_score: float | None = None,
        after_score: float | None = None,
        processing_time_ms: float | None = None,
    ) -> None:
        """Log correction application outcome.

        Args:
            document_id: Document identifier.
            page_index: Page number.
            correction_type: Type of correction (deskew, contrast, etc.).
            applied: Whether correction was applied.
            reason: Reason for decision.
            before_score: Quality score before correction.
            after_score: Quality score after correction.
            processing_time_ms: Processing time.
        """
        if not self._should_log():
            return

        self.logger.info(
            "correction_outcome",
            document_id=document_id,
            page_index=page_index,
            correction_type=correction_type,
            applied=applied,
            reason=reason,
            before_score=round(before_score, 4) if before_score is not None else None,
            after_score=round(after_score, 4) if after_score is not None else None,
            improvement=(
                round(after_score - before_score, 4)
                if before_score is not None and after_score is not None
                else None
            ),
            processing_time_ms=(
                round(processing_time_ms, 2) if processing_time_ms is not None else None
            ),
        )

    @contextmanager
    def batch_context(
        self, batch_id: str, total_files: int
    ) -> Generator["OutcomeLogger", None, None]:
        """Context manager for batch processing mode.

        Args:
            batch_id: Unique batch identifier.
            total_files: Total number of files in batch.

        Yields:
            Self with batch mode enabled.
        """
        self._batch_mode = True
        self._batch_id = batch_id
        self._batch_outcomes = []

        self.logger.info(
            "batch_started",
            batch_id=batch_id,
            total_files=total_files,
            sample_rate=self.batch_sample_rate,
        )

        start_time = time.perf_counter()

        try:
            yield self
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log batch summary
            self._log_batch_summary(duration_ms)

            self._batch_mode = False
            self._batch_id = None
            self._batch_outcomes = []

    def _log_batch_summary(self, duration_ms: float) -> None:
        """Log summary of batch processing."""
        if not self._batch_outcomes:
            self.logger.info(
                "batch_completed",
                batch_id=self._batch_id,
                total_pages=0,
                duration_ms=round(duration_ms, 2),
            )
            return

        # Calculate aggregates
        total_pages = len(self._batch_outcomes)
        error_count = sum(1 for o in self._batch_outcomes if o.error is not None)
        teacher_count = sum(
            1
            for o in self._batch_outcomes
            if o.model_selection != ModelSelection.STUDENT_ONLY
        )

        avg_quality = sum(o.overall_quality for o in self._batch_outcomes) / total_pages
        avg_time = sum(o.total_time_ms for o in self._batch_outcomes) / total_pages

        # Gate decision distribution
        gate_decisions: dict[str, int] = {}
        for o in self._batch_outcomes:
            gate_decisions[o.gate_decision.value] = (
                gate_decisions.get(o.gate_decision.value, 0) + 1
            )

        # Device distribution
        device_distribution: dict[str, int] = {}
        for o in self._batch_outcomes:
            device_distribution[o.device_used.value] = (
                device_distribution.get(o.device_used.value, 0) + 1
            )

        # Correction stats
        all_corrections: list[str] = []
        for o in self._batch_outcomes:
            all_corrections.extend(o.corrections_applied)

        correction_counts: dict[str, int] = {}
        for c in all_corrections:
            correction_counts[c] = correction_counts.get(c, 0) + 1

        self.logger.info(
            "batch_completed",
            batch_id=self._batch_id,
            total_pages=total_pages,
            error_count=error_count,
            teacher_count=teacher_count,
            teacher_percentage=round(teacher_count / total_pages * 100, 1),
            avg_quality=round(avg_quality, 4),
            avg_processing_time_ms=round(avg_time, 2),
            gate_decisions=gate_decisions,
            device_distribution=device_distribution,
            correction_counts=correction_counts,
            duration_ms=round(duration_ms, 2),
        )


# ============================================================================
# Convenience Functions
# ============================================================================


def get_outcome_logger(
    sample_rate: float | None = None,
    batch_sample_rate: float | None = None,
) -> OutcomeLogger:
    """Get an outcome logger with configuration from environment.

    Args:
        sample_rate: Override sample rate for single docs.
        batch_sample_rate: Override sample rate for batches.

    Returns:
        Configured OutcomeLogger.
    """
    config = get_logging_config()

    return OutcomeLogger(
        logger=get_logger("outcomes"),
        sample_rate=sample_rate or config.sample_rate,
        batch_sample_rate=batch_sample_rate or config.sample_rate * 0.1,
    )


# ============================================================================
# Timing Context Manager
# ============================================================================


@dataclass
class TimingResult:
    """Result of a timed operation."""

    duration_ms: float
    success: bool
    error: str | None = None


@contextmanager
def timed_operation(
    operation_name: str,
    logger: Any | None = None,
    log_on_complete: bool = True,
    **context: Any,
) -> Generator[TimingResult, None, None]:
    """Context manager for timing operations.

    Args:
        operation_name: Name of the operation.
        logger: Logger instance.
        log_on_complete: Log when operation completes.
        **context: Additional context for logging.

    Yields:
        TimingResult that will be populated on exit.
    """
    result = TimingResult(duration_ms=0.0, success=False)
    start_time = time.perf_counter()

    try:
        yield result
        result.success = True
    except Exception as e:
        result.error = str(e)
        raise
    finally:
        result.duration_ms = (time.perf_counter() - start_time) * 1000

        if log_on_complete and logger:
            logger.info(
                "operation_timed",
                operation=operation_name,
                duration_ms=round(result.duration_ms, 2),
                success=result.success,
                error=result.error,
                **context,
            )
