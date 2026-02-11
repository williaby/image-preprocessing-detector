# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Modular metadata annotation system for Project A.

This package provides a refactored, modular implementation of the metadata
annotation system, replacing the monolithic `annotate_base_metadata.py` script.

Architecture:
    - schemas/: Pydantic/dataclass models for metadata layers
    - config/: Externalized configuration and dataset registries
    - integrity/: Hashing, atomic writes, and data integrity utilities
    - parsers/: Dataset-specific label parsers
    - enrichment/: ML provider integration for weak labeling
    - storage/: JSON and Parquet output writers
    - workflow/: Pipeline orchestration and progress tracking

Quick Start:
    >>> from image_preprocessing_detector.annotation import create_orchestrator
    >>> orchestrator = create_orchestrator()
    >>> result = orchestrator.process_dataset("diqa-5000")
    >>> print(f"Processed {result.samples_processed} samples")

Factory Pattern:
    The package uses dependency injection via `create_orchestrator()` to avoid
    global mutable state and improve testability.

Breaking Changes:
    - Sample IDs now use full-file SHA256 hashing (not 64KB partial)
    - All existing sample IDs will change upon migration
    - See CHANGELOG.md for migration guide
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enrichment import (
        BatchProcessingError,
        EnrichmentError,
        EnrichmentManager,
        EnrichmentProvider,
        EnrichmentResult,
        InferenceError,
        ProviderUnavailableError,
        QualityScoreProvider,
        ValidationError,
    )
    from .workflow.orchestrator import (
        AnnotationOrchestrator,
        DatasetResult,
        OrchestrationResult,
        create_orchestrator,
    )

# Version tracking
__version__ = "0.1.0"
SCHEMA_VERSION = "2.1"

# Lazy import mapping: name -> (module_path, attribute_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BatchProcessingError": (".enrichment", "BatchProcessingError"),
    "EnrichmentError": (".enrichment", "EnrichmentError"),
    "EnrichmentManager": (".enrichment", "EnrichmentManager"),
    "EnrichmentProvider": (".enrichment", "EnrichmentProvider"),
    "EnrichmentResult": (".enrichment", "EnrichmentResult"),
    "InferenceError": (".enrichment", "InferenceError"),
    "ProviderUnavailableError": (".enrichment", "ProviderUnavailableError"),
    "QualityScoreProvider": (".enrichment", "QualityScoreProvider"),
    "ValidationError": (".enrichment", "ValidationError"),
    "AnnotationOrchestrator": (".workflow.orchestrator", "AnnotationOrchestrator"),
    "DatasetResult": (".workflow.orchestrator", "DatasetResult"),
    "OrchestrationResult": (".workflow.orchestrator", "OrchestrationResult"),
    "create_orchestrator": (".workflow.orchestrator", "create_orchestrator"),
}


def __getattr__(name: str) -> object:
    """Lazy import for heavy annotation submodules.

    This avoids importing enrichment, workflow, config, integrity, and storage
    modules at package init time, which would pull in filelock, pyarrow,
    google-cloud-storage, and other heavy dependencies not needed by modules
    that only import lightweight subpackages like annotation.schemas.enums.
    """
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path, __package__)
        return getattr(module, attr_name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "SCHEMA_VERSION",
    "AnnotationOrchestrator",
    "BatchProcessingError",
    "DatasetResult",
    "EnrichmentError",
    "EnrichmentManager",
    "EnrichmentProvider",
    "EnrichmentResult",
    "InferenceError",
    "OrchestrationResult",
    "ProviderUnavailableError",
    "QualityScoreProvider",
    "ValidationError",
    "__version__",
    "create_orchestrator",
]
