"""Metrics modules for benchmarking framework."""

# Import submodules for convenience (use relative imports to avoid circular dependency)
from . import (
    detection_metrics,
    image_metrics,
)

__all__ = ["detection_metrics", "image_metrics"]
