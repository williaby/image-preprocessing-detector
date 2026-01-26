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

# Re-export enrichment for convenience
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

# Import orchestrator and factory from workflow module
from .workflow.orchestrator import (
    AnnotationOrchestrator,
    DatasetResult,
    OrchestrationResult,
    create_orchestrator,
)

# Version tracking
__version__ = "0.1.0"
SCHEMA_VERSION = "2.1"

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
