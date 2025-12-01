"""Model adapters for OmniDocBench benchmarking.

This module provides a unified interface for different model types
(Classical CV, ResNet, YOLO, etc.) to enable fair comparison and
version tracking.

Usage:
    from scripts.omnidocbench_baseline.models import load_model, ModelRegistry

    # Load a specific model
    model = load_model("resnet18_student_v1")
    predictions = model.predict(image)

    # List available models
    registry = ModelRegistry()
    print(registry.list_models())
"""

from scripts.omnidocbench_baseline.models.base import (
    BaseModel,
    IQAModel,
    LayoutModel,
    ModelPrediction,
)
from scripts.omnidocbench_baseline.models.registry import (
    ModelRegistry,
    load_model,
    load_model_group,
)

__all__ = [
    "BaseModel",
    "IQAModel",
    "LayoutModel",
    "ModelPrediction",
    "ModelRegistry",
    "load_model",
    "load_model_group",
]
