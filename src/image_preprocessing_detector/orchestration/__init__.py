# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Device orchestration for ML inference routing.

This module provides device-priority execution for routing ML inference to
optimal compute resources based on availability and performance requirements.

Phase 4: Device-Priority Execution & Production Hardening
"""

from image_preprocessing_detector.orchestration.device_orchestrator import (
    DeviceChoice,
    DeviceOrchestrator,
    DevicePolicyConfig,
    InferenceMode,
)
from image_preprocessing_detector.orchestration.modal_client import (
    CircuitBreakerConfig,
    CircuitState,
    ModalClient,
    ModalInferenceRequest,
    ModalInferenceResponse,
)

__all__ = [
    "CircuitBreakerConfig",
    "CircuitState",
    "DeviceChoice",
    "DeviceOrchestrator",
    "DevicePolicyConfig",
    "InferenceMode",
    "ModalClient",
    "ModalInferenceRequest",
    "ModalInferenceResponse",
]
