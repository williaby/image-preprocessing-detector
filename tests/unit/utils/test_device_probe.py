"""Unit tests for device capability probing (Phase 4, Sprint 4.1.1)."""

import os
from unittest.mock import MagicMock, patch

import pytest

import image_preprocessing_detector.utils.device_probe as _dp_module
from image_preprocessing_detector.utils.device_probe import (
    DeviceCapabilities,
    clear_device_cache,
    get_recommended_device,
    probe_device_capabilities,
)


class TestDeviceCapabilities:
    """Test DeviceCapabilities dataclass."""

    def test_device_capabilities_creation(self) -> None:
        """Test DeviceCapabilities dataclass can be created."""
        caps = DeviceCapabilities(
            has_local_gpu=True,
            gpu_name="NVIDIA T4",
            gpu_memory_mb=15360,
            cpu_count=8,
            modal_available=True,
            modal_workspace="main",
        )

        assert caps.has_local_gpu is True
        assert caps.gpu_name == "NVIDIA T4"
        assert caps.gpu_memory_mb == 15360
        assert caps.cpu_count == 8
        assert caps.modal_available is True
        assert caps.modal_workspace == "main"

    def test_device_capabilities_cpu_only(self) -> None:
        """Test DeviceCapabilities for CPU-only system."""
        caps = DeviceCapabilities(
            has_local_gpu=False,
            gpu_name=None,
            gpu_memory_mb=None,
            cpu_count=4,
            modal_available=False,
            modal_workspace=None,
        )

        assert caps.has_local_gpu is False
        assert caps.gpu_name is None
        assert caps.gpu_memory_mb is None
        assert caps.cpu_count == 4
        assert caps.modal_available is False


class TestProbeDeviceCapabilities:
    """Test probe_device_capabilities function."""

    def setup_method(self) -> None:
        """Clear device cache before each test to ensure isolation."""
        clear_device_cache()

    def teardown_method(self) -> None:
        """Clear device cache after each test."""
        clear_device_cache()

    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "ort")
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_with_pytorch_gpu(
        self, mock_mp: MagicMock, mock_ort: MagicMock, mock_torch: MagicMock
    ) -> None:
        """Test device probing detects GPU via PyTorch."""
        # Mock PyTorch CUDA
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA A100"
        mock_device_props = MagicMock()
        mock_device_props.total_memory = 40 * 1024**3  # 40 GB
        mock_torch.cuda.get_device_properties.return_value = mock_device_props

        # Mock CPU
        mock_mp.cpu_count.return_value = 16

        # Mock no Modal
        with patch.dict(os.environ, {}, clear=True):
            caps = probe_device_capabilities()

        assert caps.has_local_gpu is True
        assert caps.gpu_name == "NVIDIA A100"
        assert caps.gpu_memory_mb == 40 * 1024  # 40 GB in MB
        assert caps.cpu_count == 16
        assert caps.modal_available is False

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort")
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_with_onnxruntime_gpu(
        self, mock_mp: MagicMock, mock_ort: MagicMock
    ) -> None:
        """Test device probing falls back to ONNX Runtime for GPU detection."""
        # Mock ONNX Runtime CUDA
        mock_ort.get_available_providers.return_value = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]

        # Mock CPU
        mock_mp.cpu_count.return_value = 8

        # Mock no Modal
        with patch.dict(os.environ, {}, clear=True):
            caps = probe_device_capabilities()

        assert caps.has_local_gpu is True
        assert caps.gpu_name == "CUDA (via ONNX Runtime)"
        assert caps.gpu_memory_mb is None  # ONNX Runtime doesn't expose memory
        assert caps.cpu_count == 8

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_cpu_only(self, mock_mp: MagicMock) -> None:
        """Test device probing on CPU-only system."""
        # Mock CPU
        mock_mp.cpu_count.return_value = 4

        # Mock no Modal
        with patch.dict(os.environ, {}, clear=True):
            caps = probe_device_capabilities()

        assert caps.has_local_gpu is False
        assert caps.gpu_name is None
        assert caps.gpu_memory_mb is None
        assert caps.cpu_count == 4
        assert caps.modal_available is False

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_with_modal_configured(self, mock_mp: MagicMock) -> None:
        """Test device probing detects Modal when configured."""
        # Mock CPU
        mock_mp.cpu_count.return_value = 4

        # Mock Modal configured
        modal_env = {
            "MODAL_TOKEN_ID": "mock-token-123",
            "MODAL_ENVIRONMENT": "production",
        }

        with patch.dict(os.environ, modal_env, clear=True):
            caps = probe_device_capabilities()

        assert caps.modal_available is True
        assert caps.modal_workspace == "production"

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_modal_default_workspace(self, mock_mp: MagicMock) -> None:
        """Test Modal uses default 'main' workspace if not specified."""
        # Mock CPU
        mock_mp.cpu_count.return_value = 4

        # Mock Modal with only token (no environment)
        modal_env = {"MODAL_TOKEN_ID": "mock-token-456"}

        with patch.dict(os.environ, modal_env, clear=True):
            caps = probe_device_capabilities()

        assert caps.modal_available is True
        assert caps.modal_workspace == "main"  # Default

    @patch.object(_dp_module, "logger")
    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_pytorch_cuda_exception(
        self, mock_mp: MagicMock, mock_torch: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test graceful handling when PyTorch CUDA detection fails."""
        # Mock PyTorch raising exception
        mock_torch.cuda.is_available.side_effect = RuntimeError("CUDA error")

        # Mock CPU
        mock_mp.cpu_count.return_value = 4

        with patch.dict(os.environ, {}, clear=True):
            caps = probe_device_capabilities()

        # Should fall back to CPU
        assert caps.has_local_gpu is False
        assert caps.cpu_count == 4

        # Verify warning was logged
        assert mock_logger.warning.called

    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "ort")
    @patch.object(_dp_module, "multiprocessing")
    def test_probe_caching(
        self, mock_mp: MagicMock, mock_ort: MagicMock, mock_torch: MagicMock
    ) -> None:
        """Test device capabilities are cached (probe runs once)."""
        # Mock PyTorch CUDA
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA T4"
        mock_device_props = MagicMock()
        mock_device_props.total_memory = 16 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = mock_device_props

        # Mock CPU
        mock_mp.cpu_count.return_value = 8

        with patch.dict(os.environ, {}, clear=True):
            # First call
            caps1 = probe_device_capabilities()

            # Second call (should be cached)
            caps2 = probe_device_capabilities()

        # Verify same object returned (cached)
        assert caps1 is caps2

        # Verify probe only ran once
        assert mock_torch.cuda.is_available.call_count == 1


class TestGetRecommendedDevice:
    """Test get_recommended_device function."""

    def setup_method(self) -> None:
        """Clear device cache before each test to ensure isolation."""
        clear_device_cache()

    def teardown_method(self) -> None:
        """Clear device cache after each test."""
        clear_device_cache()

    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "multiprocessing")
    def test_recommend_gpu_when_available(
        self, mock_mp: MagicMock, mock_torch: MagicMock
    ) -> None:
        """Test recommends GPU when available and preferred."""
        # Mock PyTorch CUDA
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA T4"
        mock_device_props = MagicMock()
        mock_device_props.total_memory = 16 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = mock_device_props
        mock_mp.cpu_count.return_value = 8

        with patch.dict(os.environ, {}, clear=True):
            device = get_recommended_device(prefer_gpu=True)

        assert device == "cuda"

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_recommend_cpu_when_no_gpu(self, mock_mp: MagicMock) -> None:
        """Test recommends CPU when no GPU available."""
        mock_mp.cpu_count.return_value = 4

        with patch.dict(os.environ, {}, clear=True):
            device = get_recommended_device(prefer_gpu=True)

        assert device == "cpu"

    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "multiprocessing")
    def test_recommend_cpu_when_gpu_not_preferred(
        self, mock_mp: MagicMock, mock_torch: MagicMock
    ) -> None:
        """Test recommends CPU when prefer_gpu=False."""
        # Mock PyTorch CUDA available but not preferred
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA T4"
        mock_device_props = MagicMock()
        mock_device_props.total_memory = 16 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = mock_device_props
        mock_mp.cpu_count.return_value = 8

        with patch.dict(os.environ, {}, clear=True):
            device = get_recommended_device(prefer_gpu=False)

        assert device == "cpu"

    @patch.object(_dp_module, "torch", None)
    @patch.object(_dp_module, "ort", None)
    @patch.object(_dp_module, "multiprocessing")
    def test_raise_error_when_cpu_fallback_disabled(self, mock_mp: MagicMock) -> None:
        """Test raises error when no GPU and CPU fallback disabled."""
        mock_mp.cpu_count.return_value = 4

        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(RuntimeError, match="No compute resources available"),
        ):
            get_recommended_device(prefer_gpu=True, allow_cpu_fallback=False)


class TestClearDeviceCache:
    """Test clear_device_cache function."""

    def setup_method(self) -> None:
        """Clear device cache before each test to ensure isolation."""
        clear_device_cache()

    def teardown_method(self) -> None:
        """Clear device cache after each test."""
        clear_device_cache()

    @patch.object(_dp_module, "torch")
    @patch.object(_dp_module, "multiprocessing")
    def test_clear_cache_forces_reprobe(
        self, mock_mp: MagicMock, mock_torch: MagicMock
    ) -> None:
        """Test clearing cache forces device re-probing."""
        # Mock PyTorch CUDA
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA T4"
        mock_device_props = MagicMock()
        mock_device_props.total_memory = 16 * 1024**3
        mock_torch.cuda.get_device_properties.return_value = mock_device_props
        mock_mp.cpu_count.return_value = 8

        with patch.dict(os.environ, {}, clear=True):
            # First call
            caps1 = probe_device_capabilities()
            assert mock_torch.cuda.is_available.call_count == 1

            # Clear cache
            clear_device_cache()

            # Second call (should re-probe)
            caps2 = probe_device_capabilities()
            assert mock_torch.cuda.is_available.call_count == 2

            # Verify different objects (not cached)
            assert caps1 is not caps2
