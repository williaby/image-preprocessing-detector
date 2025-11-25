# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Device capability probing for compute resource selection.

This module provides hardware detection for:
- Local GPU (CUDA via ONNX Runtime or PyTorch)
- CPU cores
- Modal serverless GPU availability

Used by Phase 4 device-priority execution to route ML inference to
optimal compute resources: Local GPU → Modal GPU → CPU (with guards).
"""

import multiprocessing
import os
import types
from dataclasses import dataclass
from functools import lru_cache

from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)

# Optional dependencies
try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Type annotation for conditional import (suppress Ruff SIM105, MyPy no-redef)
torch: types.ModuleType | None = None
try:  # noqa: SIM105
    import torch  # type: ignore[no-redef,unused-ignore]
except ImportError:
    pass


@dataclass
class DeviceCapabilities:
    """Available compute resources for ML inference.

    Attributes:
        has_local_gpu: True if CUDA GPU available locally
        gpu_name: GPU device name (e.g., "NVIDIA T4", "CUDA (via ONNX Runtime)")
        gpu_memory_mb: Total GPU memory in megabytes
        cpu_count: Number of CPU cores available
        modal_available: True if Modal credentials configured
        modal_workspace: Modal environment/workspace name
    """

    has_local_gpu: bool
    gpu_name: str | None
    gpu_memory_mb: int | None
    cpu_count: int
    modal_available: bool
    modal_workspace: str | None


@lru_cache(maxsize=1)
def probe_device_capabilities() -> DeviceCapabilities:
    """Probe available compute resources (cached for efficiency).

    Detection priority:
    1. PyTorch CUDA (most reliable GPU detection)
    2. ONNX Runtime CUDAExecutionProvider
    3. CPU cores (always available)
    4. Modal availability (env vars: MODAL_TOKEN_ID, MODAL_ENVIRONMENT)

    This function is cached to avoid redundant hardware probes.
    Subsequent calls return the same result.

    Returns:
        DeviceCapabilities with detected hardware

    Example:
        >>> caps = probe_device_capabilities()
        >>> if caps.has_local_gpu:
        ...     print(f"GPU: {caps.gpu_name} ({caps.gpu_memory_mb} MB)")
        >>> else:
        ...     print(f"CPU only: {caps.cpu_count} cores")
    """
    # Detect GPU via PyTorch (primary method)
    has_gpu = False
    gpu_name = None
    gpu_memory_mb = None

    if torch is not None:
        try:
            if torch.cuda.is_available():
                has_gpu = True
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory_mb = torch.cuda.get_device_properties(0).total_memory // (
                    1024**2
                )
                logger.info(
                    "GPU detected via PyTorch",
                    gpu_name=gpu_name,
                    memory_mb=gpu_memory_mb,
                )
        except Exception as e:
            logger.warning("PyTorch CUDA detection failed", error=str(e))

    # Fallback to ONNX Runtime GPU detection
    if not has_gpu and ort is not None:
        try:
            providers = ort.get_available_providers()
            if "CUDAExecutionProvider" in providers:
                has_gpu = True
                gpu_name = "CUDA (via ONNX Runtime)"
                # ONNX Runtime doesn't expose GPU memory, use None
                gpu_memory_mb = None
                logger.info(
                    "GPU detected via ONNX Runtime", provider="CUDAExecutionProvider"
                )
        except Exception as e:
            logger.warning("ONNX Runtime GPU detection failed", error=str(e))

    # Detect CPU cores
    cpu_count = multiprocessing.cpu_count()

    # Detect Modal availability
    modal_available = False
    modal_workspace = None

    modal_token = os.getenv("MODAL_TOKEN_ID")
    modal_env = os.getenv("MODAL_ENVIRONMENT", "main")

    if modal_token:
        modal_available = True
        modal_workspace = modal_env
        logger.info("Modal available", workspace=modal_workspace)
    else:
        logger.debug("Modal not configured (MODAL_TOKEN_ID not set)")

    return DeviceCapabilities(
        has_local_gpu=has_gpu,
        gpu_name=gpu_name,
        gpu_memory_mb=gpu_memory_mb,
        cpu_count=cpu_count,
        modal_available=modal_available,
        modal_workspace=modal_workspace,
    )


def get_recommended_device(
    prefer_gpu: bool = True,
    allow_cpu_fallback: bool = True,
) -> str:
    """Get recommended device based on availability.

    Args:
        prefer_gpu: Prefer GPU if available (default: True)
        allow_cpu_fallback: Allow CPU if GPU unavailable (default: True)

    Returns:
        Device string: "cuda" or "cpu"

    Raises:
        RuntimeError: If no compute resources available (CPU fallback disabled)

    Example:
        >>> device = get_recommended_device(prefer_gpu=True)
        >>> print(f"Using device: {device}")
    """
    caps = probe_device_capabilities()

    if prefer_gpu and caps.has_local_gpu:
        return "cuda"
    if allow_cpu_fallback and caps.cpu_count > 0:
        return "cpu"
    raise RuntimeError("No compute resources available")


def clear_device_cache() -> None:
    """Clear cached device capabilities (for testing/debugging).

    Forces re-probing on next call to probe_device_capabilities().
    Useful when testing device detection logic or when hardware changes.
    """
    probe_device_capabilities.cache_clear()
