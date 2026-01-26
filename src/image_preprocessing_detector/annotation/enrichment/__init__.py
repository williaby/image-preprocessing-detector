# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Enrichment layer for the annotation system.

This module provides the enrichment infrastructure for deriving annotations
from images using ML models and other computational methods. It includes:

- Provider protocols for extensibility
- Manager for orchestrating multiple providers
- Error handling with structured exceptions
- Validation integration with schema validators
- Dead-letter queue for failed samples

Modules:
    errors: Structured exception classes
    manager: EnrichmentManager for orchestrating providers
    providers: Provider implementations (YOLO, SigLIP, etc.)

Example:
    >>> from image_preprocessing_detector.annotation.enrichment import (
    ...     EnrichmentManager,
    ...     EnrichmentResult,
    ... )
    >>> from image_preprocessing_detector.annotation.enrichment.providers.yolo import (
    ...     YOLOProvider,
    ... )
    >>>
    >>> # Create provider
    >>> yolo = YOLOProvider(model_path="checkpoints/yolo.pt")
    >>>
    >>> # Create manager
    >>> manager = EnrichmentManager(providers=[yolo])
    >>>
    >>> # Enrich images
    >>> results = manager.enrich_batch([Path("doc1.jpg"), Path("doc2.jpg")])
    >>> for result in results:
    ...     if result.success:
    ...         print(f"Success: {result.providers_used}")
    ...     else:
    ...         print(f"Errors: {result.errors}")
"""

from __future__ import annotations

from .errors import (
    BatchProcessingError,
    EnrichmentError,
    InferenceError,
    ProviderUnavailableError,
    ValidationError,
)
from .manager import EnrichmentManager, EnrichmentResult
from .providers import (
    EnrichmentProvider,
    QualityScoreProvider,
    SigLIPProvider,
    YOLOProvider,
)

__all__ = [
    "BatchProcessingError",
    "EnrichmentError",
    "EnrichmentManager",
    "EnrichmentProvider",
    "EnrichmentResult",
    "InferenceError",
    "ProviderUnavailableError",
    "QualityScoreProvider",
    "SigLIPProvider",
    "ValidationError",
    "YOLOProvider",
]
