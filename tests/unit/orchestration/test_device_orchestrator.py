# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for device orchestrator.

Tests device selection logic, budget enforcement, and fallback behavior.

Sprint 4.1.7: Selection Matrix Tests (Phase 4)
"""

import pytest

from image_preprocessing_detector.orchestration import (
    DeviceOrchestrator,
    DevicePolicyConfig,
    InferenceMode,
)
from image_preprocessing_detector.utils.device_probe import DeviceCapabilities


class TestDevicePolicyConfig:
    """Test device policy configuration validation."""

    def test_default_production_mode(self) -> None:
        """Test default configuration is production mode."""
        config = DevicePolicyConfig()
        assert config.mode == InferenceMode.PRODUCTION
        assert not config.allow_cpu_teacher
        assert config.enable_modal

    def test_qa_mode_allows_cpu_teacher(self) -> None:
        """Test QA mode configuration."""
        config = DevicePolicyConfig(mode=InferenceMode.QA, allow_cpu_teacher=True)
        assert config.mode == InferenceMode.QA
        assert config.allow_cpu_teacher

    def test_development_mode(self) -> None:
        """Test development mode configuration."""
        config = DevicePolicyConfig(
            mode=InferenceMode.DEVELOPMENT, allow_cpu_teacher=True
        )
        assert config.mode == InferenceMode.DEVELOPMENT
        assert config.allow_cpu_teacher

    def test_budget_validation_positive_monthly(self) -> None:
        """Test monthly budget must be positive."""
        with pytest.raises(ValueError, match="Monthly budget must be positive"):
            DevicePolicyConfig(teacher_budget_monthly_hours=0.0)

    def test_budget_validation_positive_per_doc(self) -> None:
        """Test per-document budget must be positive."""
        with pytest.raises(ValueError, match="Per-document budget must be positive"):
            DevicePolicyConfig(teacher_budget_per_doc=0)

    def test_budget_validation_positive_per_batch(self) -> None:
        """Test per-batch budget must be positive."""
        with pytest.raises(ValueError, match="Per-batch budget must be positive"):
            DevicePolicyConfig(teacher_budget_per_batch=0)

    def test_warning_cpu_teacher_in_production(self) -> None:
        """Test CPU teacher configuration in production mode (warning expected)."""
        # Note: structlog warnings go to stdout, not captured by caplog
        # This test validates the configuration is accepted (warning is logged internally)
        config = DevicePolicyConfig(
            mode=InferenceMode.PRODUCTION, allow_cpu_teacher=True
        )
        assert config.mode == InferenceMode.PRODUCTION
        assert config.allow_cpu_teacher

    def test_force_device_override(self) -> None:
        """Test force_device configuration."""
        config = DevicePolicyConfig(force_device="cuda")
        assert config.force_device == "cuda"

    def test_disable_teacher_flag(self) -> None:
        """Test disable_teacher configuration."""
        config = DevicePolicyConfig(disable_teacher=True)
        assert config.disable_teacher


class TestStudentDeviceSelection:
    """Test student model device selection logic."""

    def test_student_prefers_gpu(self) -> None:
        """Test student inference prefers local GPU."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        orchestrator = DeviceOrchestrator(capabilities=caps)
        choice = orchestrator.select_device_for_student()

        assert choice.device == "cuda"
        assert "Local GPU available" in choice.rationale
        assert "NVIDIA T4" in choice.rationale
        assert not choice.fallback_applied

    def test_student_fallback_to_cpu(self) -> None:
        """Test student falls back to CPU when no GPU available."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=16,
            modal_available=False,
            modal_workspace=None,
        )
        orchestrator = DeviceOrchestrator(capabilities=caps)
        choice = orchestrator.select_device_for_student()

        assert choice.device == "cpu"
        assert "CPU fallback" in choice.rationale
        assert "16 cores" in choice.rationale
        assert choice.fallback_applied

    def test_student_force_cpu_override(self) -> None:
        """Test force_device overrides student device selection."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(force_device="cpu")
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_student()

        assert choice.device == "cpu"
        assert "Forced to cpu" in choice.rationale
        assert not choice.fallback_applied

    def test_student_rejects_modal(self) -> None:
        """Test student cannot use Modal (not supported)."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        config = DevicePolicyConfig(force_device="modal")
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_student()

        assert choice.device is None
        assert "Modal not available for student" in choice.rationale
        assert "only supports local devices" in choice.blocked_reason

    def test_student_no_resources_raises(self) -> None:
        """Test RuntimeError when no compute resources available."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=0,  # Impossible in practice, but tests error path
            modal_available=False,
            modal_workspace=None,
        )
        orchestrator = DeviceOrchestrator(capabilities=caps)

        with pytest.raises(RuntimeError, match="No compute resources available"):
            orchestrator.select_device_for_student()


class TestTeacherDeviceSelection:
    """Test teacher model device selection logic."""

    def test_teacher_prefers_gpu_production(self) -> None:
        """Test teacher prefers local GPU in production mode."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA A10",
            gpu_memory_mb=24576,
            cpu_count=16,
            modal_available=True,
            modal_workspace="prod",
        )
        config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device == "cuda"
        assert "Local GPU available" in choice.rationale
        assert "NVIDIA A10" in choice.rationale
        assert not choice.fallback_applied

    def test_teacher_fallback_to_modal_production(self) -> None:
        """Test teacher falls back to Modal GPU in production."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=True,
            modal_workspace="prod",
        )
        config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device == "modal"
        assert "Modal GPU fallback" in choice.rationale
        assert "workspace: prod" in choice.rationale
        assert choice.fallback_applied
        assert choice.estimated_cost_usd > 0

    def test_teacher_blocks_cpu_production(self) -> None:
        """Test teacher blocks CPU in production mode."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=32,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device is None
        assert "CPU teacher blocked in production" in choice.rationale
        assert "Production mode blocks CPU teacher" in choice.blocked_reason

    def test_teacher_allows_cpu_qa_mode(self) -> None:
        """Test teacher allows CPU in QA mode."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=16,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(mode=InferenceMode.QA, allow_cpu_teacher=True)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device == "cpu"
        assert "CPU fallback in qa mode" in choice.rationale
        assert "(SLOW)" in choice.rationale
        assert choice.fallback_applied

    def test_teacher_disabled_globally(self) -> None:
        """Test teacher inference can be disabled globally."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        config = DevicePolicyConfig(disable_teacher=True)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device is None
        assert "Teacher inference disabled" in choice.rationale
        assert "Teacher globally disabled" in choice.blocked_reason

    def test_teacher_force_device_override(self) -> None:
        """Test force_device overrides teacher device selection."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        config = DevicePolicyConfig(force_device="modal")
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device == "modal"
        assert "Forced to modal" in choice.rationale

    def test_teacher_force_cpu_blocked_in_production(self) -> None:
        """Test force_device=cpu blocked in production mode."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION, force_device="cpu")
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher()

        assert choice.device is None
        assert "CPU teacher not allowed in production" in choice.rationale


class TestBudgetEnforcement:
    """Test budget enforcement for teacher inference."""

    def test_per_document_budget_exceeded(self) -> None:
        """Test per-document budget blocks teacher inference."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(teacher_budget_per_doc=3)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # First 3 pages should work
        for _ in range(3):
            choice = orchestrator.select_device_for_teacher(doc_id="doc1")
            assert choice.device == "cuda"
            orchestrator.record_teacher_inference("cuda", 100.0)

        # 4th page should be blocked
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        assert choice.device is None
        assert "Per-document teacher budget exceeded" in choice.rationale
        assert "3/3 pages in document" in choice.blocked_reason

    def test_per_batch_budget_exceeded(self) -> None:
        """Test per-batch budget blocks teacher inference."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(
            teacher_budget_per_doc=10, teacher_budget_per_batch=5
        )
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Process 5 pages across 2 documents
        for doc_idx in range(2):
            for _ in range(3):
                if orchestrator.budget.pages_processed_batch < 5:
                    choice = orchestrator.select_device_for_teacher(
                        doc_id=f"doc{doc_idx}"
                    )
                    if choice.device:
                        orchestrator.record_teacher_inference("cuda", 100.0)

        # 6th page should be blocked (batch limit)
        choice = orchestrator.select_device_for_teacher(doc_id="doc2")
        assert choice.device is None
        assert "Per-batch teacher budget exceeded" in choice.rationale
        assert "5/5 pages in batch" in choice.blocked_reason

    def test_monthly_modal_budget_exceeded(self) -> None:
        """Test monthly Modal GPU budget blocks teacher inference."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        config = DevicePolicyConfig(teacher_budget_monthly_hours=0.01)  # 36 seconds
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Simulate 40 seconds of Modal GPU usage
        for i in range(4):
            choice = orchestrator.select_device_for_teacher(doc_id=f"doc{i}")
            if choice.device == "modal":
                orchestrator.record_teacher_inference("modal", 10000.0)  # 10s each

        # Should exceed 36s budget
        choice = orchestrator.select_device_for_teacher(doc_id="doc5")
        assert choice.device is None
        assert "Monthly Modal GPU budget exceeded" in choice.rationale

    def test_budget_bypass_flag(self) -> None:
        """Test bypass_budget flag skips budget checks."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(teacher_budget_per_doc=1)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Exhaust budget
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        assert choice.device == "cuda"
        orchestrator.record_teacher_inference("cuda", 100.0)

        # Should be blocked
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        assert choice.device is None

        # bypass_budget should allow
        choice = orchestrator.select_device_for_teacher(
            doc_id="doc1", bypass_budget=True
        )
        assert choice.device == "cuda"

    def test_budget_reset_on_new_document(self) -> None:
        """Test per-document budget resets for new document."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(teacher_budget_per_doc=2)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Exhaust budget for doc1
        for _ in range(2):
            choice = orchestrator.select_device_for_teacher(doc_id="doc1")
            assert choice.device == "cuda"
            orchestrator.record_teacher_inference("cuda", 100.0)

        # doc1 should be blocked
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        assert choice.device is None

        # doc2 should have fresh budget
        choice = orchestrator.select_device_for_teacher(doc_id="doc2")
        assert choice.device == "cuda"

    def test_batch_budget_reset(self) -> None:
        """Test batch budget reset functionality."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(teacher_budget_per_batch=2)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Exhaust batch budget
        for i in range(2):
            orchestrator.select_device_for_teacher(doc_id=f"doc{i}")
            orchestrator.record_teacher_inference("cuda", 100.0)

        # Should be blocked
        choice = orchestrator.select_device_for_teacher(doc_id="doc3")
        assert choice.device is None

        # Reset batch budget
        orchestrator.reset_batch_budget()

        # Should work again
        choice = orchestrator.select_device_for_teacher(doc_id="doc3")
        assert choice.device == "cuda"


class TestBudgetStatusReporting:
    """Test budget status reporting."""

    def test_get_budget_status_initial(self) -> None:
        """Test budget status at initialization."""
        config = DevicePolicyConfig(
            teacher_budget_per_doc=10,
            teacher_budget_per_batch=100,
            teacher_budget_monthly_hours=5.0,
        )
        orchestrator = DeviceOrchestrator(config=config)
        status = orchestrator.get_budget_status()

        assert status["pages_processed_doc"] == 0
        assert status["pages_processed_batch"] == 0
        assert status["modal_gpu_hours_month"] == pytest.approx(0.0)
        assert status["documents_processed"] == 0
        assert status["doc_budget_remaining"] == 10
        assert status["batch_budget_remaining"] == 100
        assert status["monthly_hours_remaining"] == pytest.approx(5.0)

    def test_get_budget_status_after_usage(self) -> None:
        """Test budget status after teacher inference."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=16384,
            cpu_count=8,
            modal_available=False,
            modal_workspace=None,
        )
        config = DevicePolicyConfig(
            teacher_budget_per_doc=10, teacher_budget_per_batch=100
        )
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Process 3 pages
        for _ in range(3):
            orchestrator.select_device_for_teacher(doc_id="doc1")
            orchestrator.record_teacher_inference("cuda", 100.0)

        status = orchestrator.get_budget_status()
        assert status["pages_processed_doc"] == 3
        assert status["pages_processed_batch"] == 3
        assert status["documents_processed"] == 1
        assert status["doc_budget_remaining"] == 7
        assert status["batch_budget_remaining"] == 97

    def test_modal_gpu_hours_tracking(self) -> None:
        """Test Modal GPU hours are tracked correctly."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )
        config = DevicePolicyConfig(teacher_budget_monthly_hours=1.0)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)

        # Simulate 1800 seconds (0.5 hours) of Modal usage
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")
        assert choice.device == "modal"
        orchestrator.record_teacher_inference("modal", 1800000.0)  # 1800s in ms

        status = orchestrator.get_budget_status()
        assert status["modal_gpu_hours_month"] == pytest.approx(0.5, abs=0.01)
        assert status["monthly_hours_remaining"] == pytest.approx(0.5, abs=0.01)


class TestDeviceSelectionMatrix:
    """Test comprehensive device selection matrix (Sprint 4.1.7).

    Table-driven tests covering all device availability combinations
    and policy modes.
    """

    @pytest.mark.parametrize(
        ("has_gpu", "modal_available", "mode", "allow_cpu", "expected_student"),
        [
            # GPU available scenarios
            (True, False, InferenceMode.PRODUCTION, False, "cuda"),
            (True, True, InferenceMode.PRODUCTION, False, "cuda"),
            (True, False, InferenceMode.QA, True, "cuda"),
            (True, True, InferenceMode.QA, True, "cuda"),
            # No GPU, Modal available
            (False, True, InferenceMode.PRODUCTION, False, "cpu"),
            (False, True, InferenceMode.QA, True, "cpu"),
            # No GPU, no Modal
            (False, False, InferenceMode.PRODUCTION, False, "cpu"),
            (False, False, InferenceMode.QA, True, "cpu"),
        ],
    )
    def test_student_selection_matrix(
        self,
        has_gpu: bool,
        modal_available: bool,
        mode: InferenceMode,
        allow_cpu: bool,
        expected_student: str,
    ) -> None:
        """Test student device selection across all scenarios."""
        caps = DeviceCapabilities(
            has_local_gpu=has_gpu,
            gpu_name="NVIDIA T4" if has_gpu else None,
            gpu_memory_mb=16384 if has_gpu else None,
            cpu_count=8,
            modal_available=modal_available,
            modal_workspace="main" if modal_available else None,
        )
        config = DevicePolicyConfig(mode=mode, allow_cpu_teacher=allow_cpu)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_student()

        assert choice.device == expected_student

    @pytest.mark.parametrize(
        ("has_gpu", "modal_available", "mode", "allow_cpu", "expected_teacher"),
        [
            # Production mode - strict
            (True, False, InferenceMode.PRODUCTION, False, "cuda"),
            (True, True, InferenceMode.PRODUCTION, False, "cuda"),
            (False, True, InferenceMode.PRODUCTION, False, "modal"),
            (False, False, InferenceMode.PRODUCTION, False, None),  # Blocked
            # QA mode - permissive
            (True, False, InferenceMode.QA, True, "cuda"),
            (False, True, InferenceMode.QA, True, "modal"),
            (False, False, InferenceMode.QA, True, "cpu"),
            # QA mode without CPU teacher
            (False, False, InferenceMode.QA, False, None),
        ],
    )
    def test_teacher_selection_matrix(
        self,
        has_gpu: bool,
        modal_available: bool,
        mode: InferenceMode,
        allow_cpu: bool,
        expected_teacher: str | None,
    ) -> None:
        """Test teacher device selection across all scenarios."""
        caps = DeviceCapabilities(
            has_local_gpu=has_gpu,
            gpu_name="NVIDIA T4" if has_gpu else None,
            gpu_memory_mb=16384 if has_gpu else None,
            cpu_count=8,
            modal_available=modal_available,
            modal_workspace="main" if modal_available else None,
        )
        config = DevicePolicyConfig(mode=mode, allow_cpu_teacher=allow_cpu)
        orchestrator = DeviceOrchestrator(config=config, capabilities=caps)
        choice = orchestrator.select_device_for_teacher(doc_id="doc1")

        assert choice.device == expected_teacher
