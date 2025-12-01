"""Model adapters for different model types.

Each adapter implements the BaseModel interface for a specific
model type (Classical CV, ResNet, YOLO, etc.).
"""

from scripts.omnidocbench_baseline.models.adapters.classical_cv import (
    ClassicalCVAdapter,
)
from scripts.omnidocbench_baseline.models.adapters.layout_lite import (
    LayoutLiteAdapter,
)

__all__ = [
    "ClassicalCVAdapter",
    "LayoutLiteAdapter",
]
