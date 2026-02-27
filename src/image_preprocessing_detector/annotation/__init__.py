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

# Module path constants for lazy imports
_ENRICHMENT_SUFFIX = ".enrichment"
_WORKFLOW_ORCHESTRATOR_SUFFIX = ".workflow.orchestrator"

# Lazy import mapping: name -> (module_path, attribute_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BatchProcessingError": (_ENRICHMENT_SUFFIX, "BatchProcessingError"),
    "EnrichmentError": (_ENRICHMENT_SUFFIX, "EnrichmentError"),
    "EnrichmentManager": (_ENRICHMENT_SUFFIX, "EnrichmentManager"),
    "EnrichmentProvider": (_ENRICHMENT_SUFFIX, "EnrichmentProvider"),
    "EnrichmentResult": (_ENRICHMENT_SUFFIX, "EnrichmentResult"),
    "InferenceError": (_ENRICHMENT_SUFFIX, "InferenceError"),
    "ProviderUnavailableError": (_ENRICHMENT_SUFFIX, "ProviderUnavailableError"),
    "QualityScoreProvider": (_ENRICHMENT_SUFFIX, "QualityScoreProvider"),
    "ValidationError": (_ENRICHMENT_SUFFIX, "ValidationError"),
    "AnnotationOrchestrator": (_WORKFLOW_ORCHESTRATOR_SUFFIX, "AnnotationOrchestrator"),
    "DatasetResult": (_WORKFLOW_ORCHESTRATOR_SUFFIX, "DatasetResult"),
    "OrchestrationResult": (_WORKFLOW_ORCHESTRATOR_SUFFIX, "OrchestrationResult"),
    "create_orchestrator": (_WORKFLOW_ORCHESTRATOR_SUFFIX, "create_orchestrator"),
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
