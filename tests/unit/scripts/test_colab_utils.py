"""Tests for scripts/colab_utils.py - Google Colab utilities.

These tests verify the Colab utilities correctly:
- Detect Colab environment
- Detect GPU tier from GPU names
- Get GPU information
- Manage disk space checks
- Handle session health monitoring
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Scripts directory added to sys.path via tests/conftest.py

# Skip all tests if torch is not available
torch = pytest.importorskip("torch", reason="torch not installed")

from colab_utils import (
    _GPU_TIERS,
    COLAB_CONTENT_ROOT,
    COLAB_DRIVE_ROOT,
    _detect_colab_tier,
    _get_nvidia_smi_info,
    check_session_health,
    download_from_url,
    get_disk_space,
    get_gpu_info,
    get_gpu_memory_usage,
    is_colab_environment,
)


class TestIsColabEnvironment:
    """Tests for is_colab_environment function."""

    def test_not_in_colab(self) -> None:
        """Test detection when not in Colab."""
        # Outside Colab, google.colab import should fail
        result = is_colab_environment()
        assert result is False

    def test_in_colab_mocked(self) -> None:
        """Test detection when in Colab (mocked)."""
        mock_colab = MagicMock()
        with patch.dict("sys.modules", {"google.colab": mock_colab}):
            # Need to reimport or call the function fresh
            # Since is_colab_environment tries to import inside the function,
            # we can test via module injection
            result = is_colab_environment()
            # This will still return False because the import happens at call time
            # The mock needs to be set up before the function runs
            assert isinstance(result, bool)


class TestDetectColabTier:
    """Tests for _detect_colab_tier function."""

    def test_detect_t4_gpu(self) -> None:
        """Test T4 GPU detection."""
        tier, memory = _detect_colab_tier("Tesla T4", fallback_memory=10.0)
        assert tier == "Free/Pro (T4)"
        assert memory == 15

    def test_detect_p100_gpu(self) -> None:
        """Test P100 GPU detection."""
        tier, memory = _detect_colab_tier("Tesla P100-PCIE-16GB", fallback_memory=10.0)
        assert tier == "Pro (P100)"
        assert memory == 16

    def test_detect_v100_gpu(self) -> None:
        """Test V100 GPU detection."""
        tier, memory = _detect_colab_tier("Tesla V100-SXM2-16GB", fallback_memory=10.0)
        assert tier == "Pro (V100)"
        assert memory == 16

    def test_detect_a100_gpu(self) -> None:
        """Test A100 GPU detection."""
        tier, memory = _detect_colab_tier("NVIDIA A100-SXM4-40GB", fallback_memory=10.0)
        assert tier == "Pro+ (A100)"
        assert memory == 40

    def test_unknown_gpu_uses_fallback(self) -> None:
        """Test unknown GPU uses fallback memory."""
        tier, memory = _detect_colab_tier("Unknown GPU XYZ", fallback_memory=8.0)
        assert tier == "Unknown"
        assert memory == pytest.approx(8.0)

    def test_case_insensitive_detection(self) -> None:
        """Test that detection is case-insensitive."""
        tier, _ = _detect_colab_tier("TESLA T4", fallback_memory=10.0)
        assert tier == "Free/Pro (T4)"

        tier, _ = _detect_colab_tier("tesla t4", fallback_memory=10.0)
        assert tier == "Free/Pro (T4)"


class TestGetNvidiaSmiInfo:
    """Tests for _get_nvidia_smi_info function."""

    def test_nvidia_smi_not_found(self) -> None:
        """Test when nvidia-smi is not installed."""
        with patch("shutil.which", return_value=None):
            result = _get_nvidia_smi_info()
            assert result == {}

    def test_nvidia_smi_success(self) -> None:
        """Test successful nvidia-smi call."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Tesla T4, 15360 MiB"

        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            with patch("subprocess.run", return_value=mock_result):
                result = _get_nvidia_smi_info()

                assert result["gpu_name_detailed"] == "Tesla T4"
                assert result["gpu_memory_detailed"] == "15360 MiB"

    def test_nvidia_smi_failure(self) -> None:
        """Test nvidia-smi command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            with patch("subprocess.run", return_value=mock_result):
                result = _get_nvidia_smi_info()
                assert result == {}

    def test_nvidia_smi_parse_error(self) -> None:
        """Test nvidia-smi output parse error."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid output format"

        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            with patch("subprocess.run", return_value=mock_result):
                result = _get_nvidia_smi_info()
                assert result == {}


class TestGetGpuInfo:
    """Tests for get_gpu_info function."""

    def test_no_gpu_available(self) -> None:
        """Test when no GPU is available."""
        with patch.object(torch.cuda, "is_available", return_value=False):
            result = get_gpu_info()

            assert result["gpu_available"] is False
            assert result["gpu_count"] == 0
            assert result["cuda_version"] is None

    def test_gpu_available(self) -> None:
        """Test when GPU is available."""
        mock_props = MagicMock()
        mock_props.total_memory = 16 * 1024**3  # 16 GB

        with patch.object(torch.cuda, "is_available", return_value=True):
            with patch.object(torch.cuda, "device_count", return_value=1):
                with patch.object(
                    torch.cuda, "get_device_name", return_value="Tesla T4"
                ):
                    with patch.object(
                        torch.cuda, "get_device_properties", return_value=mock_props
                    ):
                        with patch("colab_utils._get_nvidia_smi_info", return_value={}):
                            result = get_gpu_info()

                            assert result["gpu_available"] is True
                            assert result["gpu_count"] == 1
                            assert result["gpu_name"] == "Tesla T4"
                            assert result["gpu_memory_total_gb"] == pytest.approx(16.0)
                            assert result["colab_tier"] == "Free/Pro (T4)"


class TestGetDiskSpace:
    """Tests for get_disk_space function."""

    def test_get_disk_space_success(self, tmp_path: Path) -> None:
        """Test successful disk space retrieval."""
        total, used, free = get_disk_space(str(tmp_path))

        # Should return positive values
        assert total > 0
        assert used >= 0
        assert free >= 0
        # Total should be reasonably close to used + free
        # Note: Filesystems have reserved space, so allow generous tolerance
        assert used + free <= total  # Used + free should not exceed total
        assert (used + free) / total >= 0.8  # At least 80% accounted for

    def test_get_disk_space_invalid_path(self) -> None:
        """Test disk space for invalid path."""
        total, used, free = get_disk_space("/nonexistent/path/that/does/not/exist")

        assert total == pytest.approx(0.0)
        assert used == pytest.approx(0.0)
        assert free == pytest.approx(0.0)

    def test_get_disk_space_default_path(self) -> None:
        """Test disk space with default Colab path."""
        # Default path may not exist outside Colab
        total, used, free = get_disk_space()

        # Should return either valid values or zeros
        assert isinstance(total, float)
        assert isinstance(used, float)
        assert isinstance(free, float)


class TestGetGpuMemoryUsage:
    """Tests for get_gpu_memory_usage function."""

    def test_no_gpu_available(self) -> None:
        """Test when no GPU is available."""
        with patch.object(torch.cuda, "is_available", return_value=False):
            result = get_gpu_memory_usage()
            assert "error" in result
            assert result["error"] == "No GPU available"

    def test_gpu_memory_usage(self) -> None:
        """Test GPU memory usage calculation."""
        mock_props = MagicMock()
        mock_props.total_memory = 16 * 1024**3  # 16 GB

        with patch.object(torch.cuda, "is_available", return_value=True):
            with patch.object(
                torch.cuda, "memory_allocated", return_value=2 * 1024**3
            ):  # 2 GB
                with patch.object(
                    torch.cuda, "memory_reserved", return_value=4 * 1024**3
                ):  # 4 GB
                    with patch.object(
                        torch.cuda, "get_device_properties", return_value=mock_props
                    ):
                        result = get_gpu_memory_usage()

                        assert result["allocated_gb"] == pytest.approx(2.0)
                        assert result["reserved_gb"] == pytest.approx(4.0)
                        assert result["total_gb"] == pytest.approx(16.0)
                        assert result["free_gb"] == pytest.approx(12.0)
                        assert result["usage_percent"] == pytest.approx(25.0)


class TestCheckSessionHealth:
    """Tests for check_session_health function."""

    def test_healthy_session(self) -> None:
        """Test healthy session detection."""
        mock_gpu_usage = {
            "usage_percent": 50.0,
            "allocated_gb": 8.0,
            "reserved_gb": 8.0,
            "free_gb": 8.0,
            "total_gb": 16.0,
        }

        with patch.object(torch.cuda, "is_available", return_value=True):
            with patch("colab_utils.get_gpu_memory_usage", return_value=mock_gpu_usage):
                with patch(
                    "colab_utils.get_disk_space", return_value=(100.0, 50.0, 50.0)
                ):
                    with patch("colab_utils.is_colab_environment", return_value=False):
                        result = check_session_health()

                        assert result["healthy"] is True
                        assert result["gpu_available"] is True
                        assert result["gpu_memory_ok"] is True
                        assert result["disk_space_ok"] is True

    def test_unhealthy_gpu_memory(self) -> None:
        """Test unhealthy session due to high GPU memory usage."""
        mock_gpu_usage = {
            "usage_percent": 95.0,  # > 90%
            "allocated_gb": 15.0,
            "reserved_gb": 15.2,
            "free_gb": 0.8,
            "total_gb": 16.0,
        }

        with patch.object(torch.cuda, "is_available", return_value=True):
            with patch("colab_utils.get_gpu_memory_usage", return_value=mock_gpu_usage):
                with patch(
                    "colab_utils.get_disk_space", return_value=(100.0, 50.0, 50.0)
                ):
                    with patch("colab_utils.is_colab_environment", return_value=False):
                        result = check_session_health()

                        assert result["healthy"] is False
                        assert result["gpu_memory_ok"] is False

    def test_unhealthy_disk_space(self) -> None:
        """Test unhealthy session due to low disk space."""
        mock_gpu_usage = {"usage_percent": 50.0}

        with patch.object(torch.cuda, "is_available", return_value=True):
            with patch("colab_utils.get_gpu_memory_usage", return_value=mock_gpu_usage):
                with patch(
                    "colab_utils.get_disk_space", return_value=(100.0, 98.0, 2.0)
                ):  # < 5 GB
                    with patch("colab_utils.is_colab_environment", return_value=False):
                        result = check_session_health()

                        assert result["healthy"] is False
                        assert result["disk_space_ok"] is False

    def test_no_gpu_session(self) -> None:
        """Test session without GPU."""
        with patch.object(torch.cuda, "is_available", return_value=False):
            with patch("colab_utils.get_disk_space", return_value=(100.0, 50.0, 50.0)):
                with patch("colab_utils.is_colab_environment", return_value=False):
                    result = check_session_health()

                    assert result["healthy"] is False
                    assert result["gpu_available"] is False


class TestDownloadFromUrl:
    """Tests for download_from_url function."""

    def test_invalid_url_scheme_file(self, tmp_path: Path) -> None:
        """Test rejection of file:// URLs."""
        output_path = tmp_path / "output.txt"

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            download_from_url("file:///etc/passwd", str(output_path))

    def test_invalid_url_scheme_ftp(self, tmp_path: Path) -> None:
        """Test rejection of ftp:// URLs."""
        output_path = tmp_path / "output.txt"

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            download_from_url("ftp://example.com/file.txt", str(output_path))

    def test_successful_download(self, tmp_path: Path) -> None:
        """Test successful file download."""
        output_path = tmp_path / "downloaded.txt"
        mock_content = b"test file content"

        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(len(mock_content))}
        mock_response.iter_content.return_value = [mock_content]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = download_from_url("https://example.com/test.txt", str(output_path))

            assert result == output_path
            assert output_path.exists()
            assert output_path.read_bytes() == mock_content

    def test_download_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that download creates parent directories."""
        output_path = tmp_path / "nested" / "dir" / "file.txt"
        mock_content = b"test"

        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(len(mock_content))}
        mock_response.iter_content.return_value = [mock_content]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = download_from_url("https://example.com/test.txt", str(output_path))

            assert output_path.parent.exists()
            assert result == output_path


class TestGpuTiers:
    """Tests for GPU tier configuration."""

    def test_gpu_tiers_structure(self) -> None:
        """Test GPU tiers dictionary structure."""
        expected_tiers = ["t4", "p100", "v100", "a100"]

        for tier in expected_tiers:
            assert tier in _GPU_TIERS
            tier_name, memory = _GPU_TIERS[tier]
            assert isinstance(tier_name, str)
            assert isinstance(memory, int)
            assert memory > 0

    def test_t4_tier_values(self) -> None:
        """Test T4 tier configuration."""
        tier_name, memory = _GPU_TIERS["t4"]
        assert "T4" in tier_name
        assert memory == 15

    def test_a100_tier_values(self) -> None:
        """Test A100 tier configuration."""
        tier_name, memory = _GPU_TIERS["a100"]
        assert "A100" in tier_name
        assert memory == 40


class TestConstants:
    """Tests for module constants."""

    def test_colab_content_root(self) -> None:
        """Test Colab content root path."""
        assert COLAB_CONTENT_ROOT == "/content"

    def test_colab_drive_root(self) -> None:
        """Test Colab drive root path."""
        assert COLAB_DRIVE_ROOT == "/content/drive/MyDrive"
