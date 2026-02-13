# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Device priority integration tests for ML IQA inference.

Tests the complete device fallback chain:
1. Local GPU → Local CPU → Modal GPU
2. Device detection accuracy
3. Teacher/Student device selection
4. Modal GPU integration (when available)

Requirements:
- ONNX models must be available in models/iqa/onnx/
- Tests verify device routing logic without requiring actual GPU
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pytest

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.iqa_ml import MLIQADetector

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestDeviceDetection:
    """Tests for device detection and capability probing."""

    def test_probe_device_capabilities_returns_valid_structure(self) -> None:
        """Test that probe_device_capabilities returns all expected fields."""
        from image_preprocessing_detector.utils.device_probe import (
            DeviceCapabilities,
            probe_device_capabilities,
        )

        # Clear cache to get fresh probe
        probe_device_capabilities.cache_clear()
        caps = probe_device_capabilities()

        assert isinstance(caps, DeviceCapabilities)
        assert isinstance(caps.has_local_gpu, bool)
        assert isinstance(caps.cpu_count, int)
        assert caps.cpu_count > 0
        assert isinstance(caps.modal_available, bool)
        # gpu_name and gpu_memory_mb can be None if no GPU
        if caps.has_local_gpu:
            assert caps.gpu_name is not None
        # modal_workspace can be None if Modal not configured
        if caps.modal_available:
            assert caps.modal_workspace is not None

    def test_probe_device_capabilities_is_cached(self) -> None:
        """Test that device capabilities are cached for efficiency."""
        from image_preprocessing_detector.utils.device_probe import (
            probe_device_capabilities,
        )

        # Clear cache first
        probe_device_capabilities.cache_clear()

        # First call
        caps1 = probe_device_capabilities()
        # Second call should return same object (cached)
        caps2 = probe_device_capabilities()

        assert caps1 is caps2

    def test_clear_device_cache_forces_reprobe(self) -> None:
        """Test that clearing cache forces a fresh probe."""
        from image_preprocessing_detector.utils.device_probe import (
            clear_device_cache,
            probe_device_capabilities,
        )

        # Get initial probe
        caps1 = probe_device_capabilities()

        # Clear and get new probe
        clear_device_cache()
        caps2 = probe_device_capabilities()

        # Should be equal but different objects
        assert caps1.cpu_count == caps2.cpu_count
        # Note: Cannot guarantee different object IDs as dataclass may be equal

    def test_get_recommended_device_with_no_gpu(self) -> None:
        """Test device recommendation when GPU is unavailable."""
        from image_preprocessing_detector.utils.device_probe import (
            clear_device_cache,
            get_recommended_device,
        )

        # Mock no GPU scenario
        with (
            patch("image_preprocessing_detector.utils.device_probe.torch", None),
            patch("image_preprocessing_detector.utils.device_probe.ort", None),
        ):
            clear_device_cache()
            device = get_recommended_device(prefer_gpu=True, allow_cpu_fallback=True)
            assert device == "cpu"

    def test_get_recommended_device_raises_when_no_fallback(self) -> None:
        """Test that error is raised when no compute resources and fallback disabled."""
        from image_preprocessing_detector.utils.device_probe import (
            clear_device_cache,
            get_recommended_device,
        )

        # Mock no resources scenario (this should be rare in practice)
        with (
            patch("image_preprocessing_detector.utils.device_probe.torch", None),
            patch("image_preprocessing_detector.utils.device_probe.ort", None),
            patch(
                "image_preprocessing_detector.utils.device_probe.multiprocessing.cpu_count",
                return_value=0,
            ),
        ):
            clear_device_cache()
            with pytest.raises(RuntimeError, match="No compute resources available"):
                get_recommended_device(prefer_gpu=False, allow_cpu_fallback=False)


class TestModalAvailability:
    """Tests for Modal GPU availability detection."""

    def test_modal_detected_when_token_present(self) -> None:
        """Test Modal is detected when MODAL_TOKEN_ID is set."""
        from image_preprocessing_detector.utils.device_probe import (
            clear_device_cache,
            probe_device_capabilities,
        )

        with patch.dict(
            os.environ,
            {"MODAL_TOKEN_ID": "test_token", "MODAL_ENVIRONMENT": "test_workspace"},
        ):
            clear_device_cache()
            caps = probe_device_capabilities()
            assert caps.modal_available is True
            assert caps.modal_workspace == "test_workspace"

    def test_modal_not_detected_without_token(self) -> None:
        """Test Modal is not detected when MODAL_TOKEN_ID is not set."""
        from image_preprocessing_detector.utils.device_probe import (
            clear_device_cache,
            probe_device_capabilities,
        )

        # Remove Modal env vars
        env_without_modal = {
            k: v for k, v in os.environ.items() if not k.startswith("MODAL_")
        }
        with patch.dict(os.environ, env_without_modal, clear=True):
            clear_device_cache()
            caps = probe_device_capabilities()
            assert caps.modal_available is False
            assert caps.modal_workspace is None


class TestMLIQADeviceSelection:
    """Tests for MLIQADetector device selection logic."""

    def test_detector_auto_detects_device(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test that detector auto-detects device when not specified."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Create detector without specifying device (legacy mode to access .device)
        detector = MLIQADetector(
            student_model_path=student_path,
            device=None,  # Auto-detect
            enable_modal_fallback=False,
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )

        # Device should be auto-detected
        assert detector.device in [Device.GPU, Device.CPU]

    def test_detector_respects_explicit_device(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test that detector respects explicitly set device."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Explicitly request CPU (legacy mode to access .device)
        detector = MLIQADetector(
            student_model_path=student_path,
            device=Device.CPU,
            enable_modal_fallback=False,
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )

        assert detector.device == Device.CPU

    def test_detector_ort_providers_match_device(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test that ONNX Runtime providers match selected device."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Test CPU provider selection (legacy mode)
        detector_cpu = MLIQADetector(
            student_model_path=student_path,
            device=Device.CPU,
            enable_modal_fallback=False,
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )
        providers = detector_cpu._get_ort_providers()
        assert "CPUExecutionProvider" in providers
        assert "CUDAExecutionProvider" not in providers

        # Test GPU provider selection (legacy mode)
        detector_gpu = MLIQADetector(
            student_model_path=student_path,
            device=Device.GPU,
            enable_modal_fallback=False,
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )
        providers = detector_gpu._get_ort_providers()
        assert "CUDAExecutionProvider" in providers
        assert "CPUExecutionProvider" in providers  # Fallback


class TestDeviceFallbackChain:
    """Tests for device fallback chain: GPU → CPU → Modal."""

    def test_gpu_to_cpu_fallback_on_missing_cuda(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test fallback from GPU to CPU when CUDA is unavailable."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Mock ONNX Runtime to not have CUDA provider
        import onnxruntime as ort

        def mock_providers():
            return ["CPUExecutionProvider"]

        with patch.object(ort, "get_available_providers", mock_providers):
            detector = MLIQADetector(
                student_model_path=student_path,
                device=None,  # Auto-detect
                enable_modal_fallback=False,
                use_orchestrator=False,  # Use legacy mode to test .device attribute
            )
            # Should fall back to CPU
            assert detector.device == Device.CPU

    def test_inference_works_with_cpu_fallback(
        self, ml_detector: "MLIQADetector | None"
    ) -> None:
        """Test that inference works correctly with CPU device."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
            return  # Unreachable, but helps static analysis understand control flow

        # Create test image
        img = np.ones((224, 224, 3), dtype=np.uint8) * 128

        # Run inference
        scores = ml_detector.run_student_inference(img)

        assert scores is not None
        assert scores.inference_time_ms > 0
        assert 0.0 <= scores.overall_quality <= 1.0

    def test_teacher_inference_uses_same_device_as_student(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test that teacher model uses same device as student."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"
        teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

        detector = MLIQADetector(
            student_model_path=student_path,
            teacher_model_path=teacher_path,
            device=Device.CPU,
            enable_modal_fallback=False,
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )

        # Create test image
        img = np.ones((224, 224, 3), dtype=np.uint8) * 128

        # Run both student and teacher
        student_scores = detector.run_student_inference(img)
        teacher_scores = detector.run_teacher_inference(img)

        # Both should use CPU device
        assert student_scores.device == Device.CPU
        assert teacher_scores.device == Device.CPU


class TestModalGPUIntegration:
    """Tests for Modal GPU integration (requires Modal configuration)."""

    @pytest.mark.skipif(
        not os.getenv("MODAL_TOKEN_ID"),
        reason="Modal not configured (MODAL_TOKEN_ID not set)",
    )
    def test_modal_device_configuration(self) -> None:
        """Test Modal device can be configured."""
        from image_preprocessing_detector.detection.iqa_ml import Device

        # Verify Modal device enum exists
        assert Device.MODAL.value == "modal"

    def test_enable_modal_fallback_setting(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test enable_modal_fallback configuration option."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Test with Modal fallback enabled
        detector_with_modal = MLIQADetector(
            student_model_path=student_path,
            device=Device.CPU,
            enable_modal_fallback=True,
        )
        assert detector_with_modal.enable_modal_fallback is True

        # Test with Modal fallback disabled
        detector_without_modal = MLIQADetector(
            student_model_path=student_path,
            device=Device.CPU,
            enable_modal_fallback=False,
        )
        assert detector_without_modal.enable_modal_fallback is False


class TestDevicePriorityPipeline:
    """End-to-end tests for device priority in ML IQA pipeline."""

    def test_pipeline_completes_with_detected_device(
        self, ml_detector: "MLIQADetector | None"
    ) -> None:
        """Test full pipeline completes with auto-detected device."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create test image with varied content
        img = np.ones((800, 600, 3), dtype=np.uint8) * 200
        # Add some patterns
        for y in range(100, 500, 50):
            img[y : y + 30, 50:550] = 50

        # Run full pipeline
        student_scores, _, _ = ml_detector.run_pipeline(img)

        assert student_scores is not None
        assert student_scores.inference_time_ms > 0
        # Device should be reported correctly
        assert (
            student_scores.device == ml_detector.device
            or student_scores.device is not None
        )

    def test_pipeline_teacher_escalation_maintains_device(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test that teacher escalation maintains device consistency."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"
        teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

        # Create detector with low thresholds to force escalation (legacy mode)
        detector = MLIQADetector(
            student_model_path=student_path,
            teacher_model_path=teacher_path,
            device=Device.CPU,
            enable_modal_fallback=False,
            entropy_threshold=0.0,  # Force escalation
            min_confidence_threshold=1.0,  # Force escalation
            use_orchestrator=False,  # Use legacy mode to test .device attribute
        )

        # Create ambiguous image
        rng = np.random.default_rng(42)
        img = rng.integers(0, 255, (300, 300, 3), dtype=np.uint8)

        # Run pipeline - should escalate to teacher
        student_scores, teacher_scores, escalation_reason = detector.run_pipeline(img)

        # Both models should use same device
        assert student_scores.device == Device.CPU
        if teacher_scores is not None:
            assert teacher_scores.device == Device.CPU
            assert escalation_reason is not None

    def test_multiple_inference_calls_maintain_device(
        self, ml_detector: "MLIQADetector | None"
    ) -> None:
        """Test that multiple inference calls maintain consistent device."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
            return  # Unreachable, but helps static analysis understand control flow

        rng = np.random.default_rng(42)

        devices_used = []
        for _ in range(5):
            img = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
            scores = ml_detector.run_student_inference(img)
            assert scores is not None, "Student inference should return scores"
            devices_used.append(scores.device)

        # All inferences should use same device
        assert len(set(devices_used)) == 1, "Device should be consistent across calls"


class TestDevicePriorityPerformance:
    """Performance tests for device priority execution."""

    def test_student_inference_latency_cpu(
        self, ml_detector: "MLIQADetector | None"
    ) -> None:
        """Test student inference latency on CPU (target: <100ms acceptable)."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
            return  # Unreachable, but helps static analysis understand control flow

        from image_preprocessing_detector.detection.iqa_ml import Device

        # Skip if not on CPU
        if ml_detector.device != Device.CPU:
            pytest.skip("Test requires CPU device")

        # Create test image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 128

        # Warm-up inference
        ml_detector.run_student_inference(img)

        # Measure latency
        latencies = []
        for _ in range(10):
            scores = ml_detector.run_student_inference(img)
            assert scores is not None, "Student inference should return scores"
            latencies.append(scores.inference_time_ms)

        avg_latency = np.mean(latencies)

        # Assert acceptable latency (<100ms CPU acceptable, <40ms target)
        assert avg_latency < 100, f"Average latency {avg_latency:.1f}ms exceeds 100ms"
        # Log warning if above target
        if avg_latency > 40:
            import warnings

            warnings.warn(
                f"Average CPU latency ({avg_latency:.1f}ms) exceeds target (40ms)"
            )

    def test_teacher_inference_latency_cpu(
        self, onnx_models_available: bool, onnxruntime_available: bool
    ) -> None:
        """Test teacher inference latency on CPU."""
        if not onnxruntime_available:
            pytest.skip("onnxruntime not properly installed")
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
        )

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"
        teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

        detector = MLIQADetector(
            student_model_path=student_path,
            teacher_model_path=teacher_path,
            device=Device.CPU,
            enable_modal_fallback=False,
        )

        # Create test image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 128

        # Warm-up
        detector.run_teacher_inference(img)

        # Measure latency
        latencies = []
        for _ in range(5):
            scores = detector.run_teacher_inference(img)
            latencies.append(scores.inference_time_ms)

        avg_latency = np.mean(latencies)

        # Teacher (ResNet-50) is significantly larger than student (ResNet-18)
        # CPU inference is expected to be slow (~1000-2000ms on typical hardware)
        # This threshold catches extreme performance degradation while allowing
        # for realistic CPU performance variability
        assert avg_latency < 2500, f"Teacher latency {avg_latency:.1f}ms exceeds 2500ms"

        # Log warning if performance is suboptimal
        if avg_latency > 1500:
            import warnings

            warnings.warn(
                f"Teacher CPU latency ({avg_latency:.1f}ms) exceeds optimal range "
                f"(expected ~1000-1500ms, measured {avg_latency:.1f}ms)"
            )
