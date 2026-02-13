# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Device orchestration for ML inference routing.

This module implements the core device-priority execution logic:
- Student inference: Local GPU → Local CPU (always allowed)
- Teacher inference: Local GPU → Modal GPU → BLOCK CPU (production mode)
- Budget enforcement for Modal GPU usage
- Device selection rationale logging

Sprint 4.1.1: Device Orchestrator Class (Phase 4)
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from image_preprocessing_detector.utils.device_probe import (
    DeviceCapabilities,
    probe_device_capabilities,
)
from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)


class InferenceMode(StrEnum):
    """Execution mode for inference (affects device policy)."""

    PRODUCTION = "production"  # Strict: Block CPU teacher, enforce budgets
    QA = "qa"  # Permissive: Allow CPU teacher with warnings
    DEVELOPMENT = "development"  # Permissive: Allow all devices


@dataclass
class DevicePolicyConfig:
    """Configuration for device selection policy.

    Attributes:
        mode: Inference mode (production/qa/development)
        allow_cpu_teacher: Allow teacher inference on CPU (QA/dev only)
        enable_modal: Enable Modal GPU fallback
        modal_timeout_ms: Modal request timeout in milliseconds
        modal_max_retries: Maximum retry attempts for Modal
        teacher_budget_per_doc: Max teacher pages per document
        teacher_budget_per_batch: Max teacher pages per batch
        teacher_budget_monthly_hours: Monthly Modal GPU hours budget
        force_device: Force specific device (override priority logic)
        disable_teacher: Completely disable teacher inference
    """

    mode: InferenceMode = InferenceMode.PRODUCTION
    allow_cpu_teacher: bool = False
    enable_modal: bool = True
    modal_timeout_ms: int = 5000
    modal_max_retries: int = 3
    teacher_budget_per_doc: int = 10
    teacher_budget_per_batch: int = 100
    teacher_budget_monthly_hours: float = 10.0
    force_device: Literal["cuda", "cpu", "modal"] | None = None
    disable_teacher: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.mode == InferenceMode.PRODUCTION and self.allow_cpu_teacher:
            logger.warning(
                "CPU teacher allowed in production mode - performance impact expected"
            )
        if self.teacher_budget_monthly_hours <= 0:
            msg = "Monthly budget must be positive"
            raise ValueError(msg)
        if self.teacher_budget_per_doc <= 0:
            msg = "Per-document budget must be positive"
            raise ValueError(msg)
        if self.teacher_budget_per_batch <= 0:
            msg = "Per-batch budget must be positive"
            raise ValueError(msg)


@dataclass
class DeviceChoice:
    """Device selection result with rationale.

    Attributes:
        device: Selected device ("cuda", "cpu", "modal", or None)
        rationale: Human-readable explanation of choice
        fallback_applied: Whether fallback logic was used
        blocked_reason: Reason device was blocked (if applicable)
        estimated_cost_usd: Estimated cost for Modal inference (0 for local)
    """

    device: Literal["cuda", "cpu", "modal"] | None
    rationale: str
    fallback_applied: bool = False
    blocked_reason: str | None = None
    estimated_cost_usd: float = 0.0


@dataclass
class BudgetTracker:
    """Track teacher inference budget usage.

    Attributes:
        pages_processed_doc: Pages processed in current document
        pages_processed_batch: Pages processed in current batch
        modal_gpu_hours_month: Modal GPU hours used this month
        documents_processed: Total documents processed
    """

    pages_processed_doc: int = 0
    pages_processed_batch: int = 0
    modal_gpu_hours_month: float = 0.0
    documents_processed: int = 0
    _current_doc_id: str | None = field(default=None, repr=False)

    def reset_document(self, doc_id: str) -> None:
        """Reset per-document counters for new document.

        Args:
            doc_id: Unique document identifier
        """
        if self._current_doc_id != doc_id:
            self.pages_processed_doc = 0
            self._current_doc_id = doc_id
            self.documents_processed += 1

    def reset_batch(self) -> None:
        """Reset per-batch counters."""
        self.pages_processed_batch = 0

    def record_teacher_usage(
        self,
        device: Literal["cuda", "cpu", "modal"],
        inference_time_ms: float,
    ) -> None:
        """Record teacher inference for budget tracking.

        Args:
            device: Device used for inference
            inference_time_ms: Inference latency in milliseconds
        """
        self.pages_processed_doc += 1
        self.pages_processed_batch += 1

        if device == "modal":
            # Convert milliseconds to hours
            gpu_hours = inference_time_ms / (1000 * 3600)
            self.modal_gpu_hours_month += gpu_hours


class DeviceOrchestrator:
    """Orchestrate device selection for ML inference routing.

    This class implements the device-priority execution logic defined in
    Phase 4 of the project plan:

    Student inference:
      - Local GPU (preferred) → Local CPU (always allowed)

    Teacher inference:
      - Production mode: Local GPU → Modal GPU → BLOCK CPU
      - QA/Dev mode: Local GPU → Modal GPU → CPU (with warning)

    Budget enforcement:
      - Per-document page caps
      - Per-batch page caps
      - Monthly Modal GPU hours cap

    Example:
        >>> config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION)
        >>> orchestrator = DeviceOrchestrator(config)
        >>> choice = orchestrator.select_device_for_student()
        >>> print(f"Student device: {choice.device}")
        >>> choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        >>> if choice.device:
        ...     print(f"Teacher device: {choice.device}")
        ... else:
        ...     print(f"Teacher blocked: {choice.blocked_reason}")
    """

    def __init__(
        self,
        config: DevicePolicyConfig | None = None,
        capabilities: DeviceCapabilities | None = None,
    ) -> None:
        """Initialize device orchestrator.

        Args:
            config: Device policy configuration (default: production mode)
            capabilities: Pre-probed device capabilities (default: auto-probe)
        """
        self.config = config or DevicePolicyConfig()
        self.capabilities = capabilities or probe_device_capabilities()
        self.budget = BudgetTracker()

        logger.info(
            "DeviceOrchestrator initialized",
            mode=self.config.mode.value,
            has_local_gpu=self.capabilities.has_local_gpu,
            modal_available=self.capabilities.modal_available,
            cpu_count=self.capabilities.cpu_count,
        )

    def select_device_for_student(self) -> DeviceChoice:
        """Select device for student model inference.

        Student inference always follows simple priority:
        1. Local GPU (preferred)
        2. Local CPU (always allowed fallback)

        Returns:
            DeviceChoice with selected device and rationale

        Raises:
            RuntimeError: If no compute resources available (should never happen)
        """
        # Force device override
        if self.config.force_device:
            if self.config.force_device == "modal":
                return DeviceChoice(
                    device=None,
                    rationale="Modal not available for student inference",
                    blocked_reason="Student inference only supports local devices",
                )
            return DeviceChoice(
                device=self.config.force_device,
                rationale=f"Forced to {self.config.force_device} by configuration",
                fallback_applied=False,
            )

        # Prefer GPU if available
        if self.capabilities.has_local_gpu:
            return DeviceChoice(
                device="cuda",
                rationale=f"Local GPU available ({self.capabilities.gpu_name})",
                fallback_applied=False,
            )

        # CPU fallback (always allowed for student)
        if self.capabilities.cpu_count > 0:
            return DeviceChoice(
                device="cpu",
                rationale=f"CPU fallback ({self.capabilities.cpu_count} cores)",
                fallback_applied=True,
            )

        # Should never reach here
        msg = "No compute resources available for student inference"
        raise RuntimeError(msg)

    def select_device_for_teacher(
        self,
        doc_id: str | None = None,
        bypass_budget: bool = False,
    ) -> DeviceChoice:
        """Select device for teacher model inference.

        Teacher inference follows strict priority rules:
        - Production: Local GPU → Modal GPU → BLOCK CPU
        - QA/Dev: Local GPU → Modal GPU → CPU (with warning)

        Budget enforcement:
        - Per-document page caps
        - Per-batch page caps
        - Monthly Modal GPU hours cap

        Args:
            doc_id: Document identifier for budget tracking
            bypass_budget: Skip budget checks (for admin/testing)

        Returns:
            DeviceChoice with selected device and rationale
            (device=None if teacher is blocked)
        """
        # Teacher disabled globally
        if self.config.disable_teacher:
            return DeviceChoice(
                device=None,
                rationale="Teacher inference disabled by configuration",
                blocked_reason="Teacher globally disabled",
            )

        # Force device override
        if self.config.force_device:
            if self.config.force_device == "cpu" and not self.config.allow_cpu_teacher:
                return DeviceChoice(
                    device=None,
                    rationale="CPU teacher not allowed in production mode",
                    blocked_reason="CPU teacher blocked by policy",
                )
            return DeviceChoice(
                device=self.config.force_device,
                rationale=f"Forced to {self.config.force_device} by configuration",
                fallback_applied=False,
            )

        # Budget enforcement
        if not bypass_budget and doc_id:
            self.budget.reset_document(doc_id)

            if self.budget.pages_processed_doc >= self.config.teacher_budget_per_doc:
                return DeviceChoice(
                    device=None,
                    rationale="Per-document teacher budget exceeded",
                    blocked_reason=(
                        f"Processed {self.budget.pages_processed_doc}/"
                        f"{self.config.teacher_budget_per_doc} pages in document"
                    ),
                )

            if (
                self.budget.pages_processed_batch
                >= self.config.teacher_budget_per_batch
            ):
                return DeviceChoice(
                    device=None,
                    rationale="Per-batch teacher budget exceeded",
                    blocked_reason=(
                        f"Processed {self.budget.pages_processed_batch}/"
                        f"{self.config.teacher_budget_per_batch} pages in batch"
                    ),
                )

            if (
                self.budget.modal_gpu_hours_month
                >= self.config.teacher_budget_monthly_hours
            ):
                return DeviceChoice(
                    device=None,
                    rationale="Monthly Modal GPU budget exceeded",
                    blocked_reason=(
                        f"Used {self.budget.modal_gpu_hours_month:.2f}/"
                        f"{self.config.teacher_budget_monthly_hours} GPU hours"
                    ),
                )

        # Priority 1: Local GPU
        if self.capabilities.has_local_gpu:
            return DeviceChoice(
                device="cuda",
                rationale=f"Local GPU available ({self.capabilities.gpu_name})",
                fallback_applied=False,
            )

        # Priority 2: Modal GPU (if enabled and available)
        if self.config.enable_modal and self.capabilities.modal_available:
            # Estimate Modal cost (T4 GPU: ~$0.60/hour)
            estimated_cost = 0.0001  # ~$0.0001 per inference (100ms @ $0.60/hr)
            return DeviceChoice(
                device="modal",
                rationale=f"Modal GPU fallback (workspace: {self.capabilities.modal_workspace})",
                fallback_applied=True,
                estimated_cost_usd=estimated_cost,
            )

        # Priority 3: CPU (only in QA/Dev mode)
        if self.config.allow_cpu_teacher and self.capabilities.cpu_count > 0:
            logger.warning(
                "Teacher inference on CPU - significant performance impact",
                mode=self.config.mode.value,
                cpu_count=self.capabilities.cpu_count,
            )
            return DeviceChoice(
                device="cpu",
                rationale=f"CPU fallback in {self.config.mode.value} mode (SLOW)",
                fallback_applied=True,
            )

        # Production mode: Block CPU teacher
        if self.config.mode == InferenceMode.PRODUCTION:
            return DeviceChoice(
                device=None,
                rationale="No GPU available and CPU teacher blocked in production",
                blocked_reason="Production mode blocks CPU teacher inference",
            )

        # Fallthrough: No devices available
        return DeviceChoice(
            device=None,
            rationale="No compute resources available for teacher inference",
            blocked_reason="No GPU available and CPU teacher not enabled",
        )

    def record_teacher_inference(
        self,
        device: Literal["cuda", "cpu", "modal"],
        inference_time_ms: float,
    ) -> None:
        """Record teacher inference for budget tracking.

        Args:
            device: Device used for inference
            inference_time_ms: Inference latency in milliseconds
        """
        self.budget.record_teacher_usage(device, inference_time_ms)

        logger.debug(
            "Teacher inference recorded",
            device=device,
            latency_ms=inference_time_ms,
            doc_pages=self.budget.pages_processed_doc,
            batch_pages=self.budget.pages_processed_batch,
            modal_gpu_hours=self.budget.modal_gpu_hours_month,
        )

    def get_budget_status(self) -> dict[str, float | int]:
        """Get current budget usage statistics.

        Returns:
            Dictionary with budget usage metrics
        """
        return {
            "pages_processed_doc": self.budget.pages_processed_doc,
            "pages_processed_batch": self.budget.pages_processed_batch,
            "modal_gpu_hours_month": self.budget.modal_gpu_hours_month,
            "documents_processed": self.budget.documents_processed,
            "teacher_budget_per_doc": self.config.teacher_budget_per_doc,
            "teacher_budget_per_batch": self.config.teacher_budget_per_batch,
            "teacher_budget_monthly_hours": self.config.teacher_budget_monthly_hours,
            "doc_budget_remaining": max(
                0,
                self.config.teacher_budget_per_doc - self.budget.pages_processed_doc,
            ),
            "batch_budget_remaining": max(
                0,
                self.config.teacher_budget_per_batch
                - self.budget.pages_processed_batch,
            ),
            "monthly_hours_remaining": max(
                0,
                self.config.teacher_budget_monthly_hours
                - self.budget.modal_gpu_hours_month,
            ),
        }

    def reset_batch_budget(self) -> None:
        """Reset per-batch budget counters."""
        self.budget.reset_batch()
        logger.info("Batch budget reset", status=self.get_budget_status())
