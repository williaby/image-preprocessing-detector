# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Modular metadata annotation system for Project A.

This package provides a refactored, modular implementation of the metadata
annotation system, replacing the monolithic `annotate_base_metadata.py` script.

Architecture:
    - schemas/: Pydantic/dataclass models for metadata layers
    - config/: Externalized configuration and dataset registries
    - integrity/: Hashing, atomic writes, and data integrity utilities
    - parsers/: Dataset-specific label parsers (Phase 2)
    - enrichment/: ML provider integration for weak labeling (Phase 2)
    - storage/: JSON and Parquet output writers (Phase 2)
    - workflow/: Pipeline orchestration and progress tracking (Phase 2)

Quick Start:
    >>> from image_preprocessing_detector.annotation import create_orchestrator
    >>> orchestrator = create_orchestrator()
    >>> result = orchestrator.process_dataset("diqa-5000")

Factory Pattern:
    The package uses dependency injection via `create_orchestrator()` to avoid
    global mutable state and improve testability.

Breaking Changes:
    - Sample IDs now use full-file SHA256 hashing (not 64KB partial)
    - All existing sample IDs will change upon migration
    - See CHANGELOG.md for migration guide
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config.settings import AnnotationSettings

# Version tracking
__version__ = "0.1.0"
SCHEMA_VERSION = "2.1"

# Lazy imports for public API - populated as modules are implemented
# Phase 1: schemas, config, integrity
# Phase 2+: parsers, enrichment, storage, workflow


def create_orchestrator(
    settings: AnnotationSettings | None = None,
) -> AnnotationOrchestrator:
    """Factory function to create annotation orchestrator.

    Creates a fully-configured orchestrator with dependency injection,
    avoiding global mutable state.

    Args:
        settings: Configuration settings. If None, loads from environment.

    Returns:
        Configured AnnotationOrchestrator instance.

    Example:
        >>> orchestrator = create_orchestrator()
        >>> orchestrator.process_dataset("diqa-5000")

        >>> # With custom settings
        >>> from annotation.config import AnnotationSettings
        >>> settings = AnnotationSettings(batch_size=200)
        >>> orchestrator = create_orchestrator(settings)
    """
    from .config.settings import AnnotationSettings

    if settings is None:
        settings = AnnotationSettings.from_env()

    # Stub implementation - will be expanded in Phase 2
    return AnnotationOrchestrator(settings=settings)


class AnnotationOrchestrator:
    """Coordinates multi-dataset annotation workflows.

    This is a stub implementation for Phase 1. Full implementation
    will be added in Phase 2 with parser registry, enrichment providers,
    and storage backends.
    """

    def __init__(self, settings: AnnotationSettings) -> None:
        """Initialize orchestrator with settings.

        Args:
            settings: Configuration settings for annotation.
        """
        self.settings = settings

    def process_dataset(self, dataset_name: str) -> dict[str, Any]:
        """Process a single dataset.

        Stub implementation for Phase 1.

        Args:
            dataset_name: Name of dataset to process.

        Returns:
            Processing result dictionary.

        Raises:
            NotImplementedError: Full implementation in Phase 2.
        """
        raise NotImplementedError(
            "Full dataset processing will be implemented in Phase 2. "
            f"Dataset requested: {dataset_name}"
        )


__all__ = [
    "SCHEMA_VERSION",
    # Orchestrator
    "AnnotationOrchestrator",
    # Version info
    "__version__",
    # Factory
    "create_orchestrator",
]
