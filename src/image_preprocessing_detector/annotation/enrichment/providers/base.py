# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Base protocols for enrichment providers.

This module defines the protocols that all enrichment providers must implement.
Providers are responsible for deriving annotations from images using ML models
or other computational methods.

Protocols:
    - EnrichmentProvider: Base provider protocol
    - QualityScoreProvider: Continuous quality score prediction

Design Principles:
    1. Protocol-based: Use typing.Protocol for extensibility
    2. Stateless: Providers should not maintain internal state between calls
    3. Batch-aware: All providers support batch inference
    4. Fail-fast: Raise clear exceptions rather than returning partial data
    5. Availability checking: Providers report their availability status

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.base import (
    ...     EnrichmentProvider,
    ... )
    >>>
    >>> class MyProvider:
    ...     '''Custom enrichment provider.'''
    ...
    ...     @property
    ...     def name(self) -> str:
    ...         return "my_provider"
    ...
    ...     @property
    ...     def tier(self) -> str:
    ...         return "tier_2_model"
    ...
    ...     def is_available(self) -> bool:
    ...         return True  # Check model files, GPU, etc.
    ...
    ...     def supports(self, image_path: Path) -> bool:
    ...         return True  # Check if this image should be processed
    ...
    ...     def enrich(self, image_path: Path) -> EnrichmentData:
    ...         # Run inference and return enrichment
    ...         return EnrichmentData(...)
    ...
    ...     def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
    ...         # Batch inference for efficiency
    ...         return [self.enrich(p) for p in image_paths]
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...schemas.enrichment import EnrichmentData


@runtime_checkable
class EnrichmentProvider(Protocol):
    """Protocol for enrichment data providers.

    All enrichment providers must implement this protocol. Providers
    should be stateless and support batch inference for efficiency.

    Type Checking:
        Use @runtime_checkable to enable isinstance() checks:
        >>> isinstance(my_provider, EnrichmentProvider)  # Works at runtime
    """

    @property
    def name(self) -> str:
        """Provider name for logging and provenance.

        Returns:
            Unique identifier for this provider (e.g., "doclayout_yolo")

        Example:
            >>> provider.name
            "doclayout_yolo"
        """
        ...

    @property
    def tier(self) -> str:
        """Enrichment tier for this provider.

        Returns:
            EnrichmentTier value (tier_0_exact, tier_1_annotation,
            tier_2_model, tier_3_heuristic)

        Example:
            >>> provider.tier
            "tier_2_model"
        """
        ...

    def is_available(self) -> bool:
        """Check if this provider is available for use.

        Checks prerequisites like model files, GPU availability,
        and required dependencies.

        Returns:
            True if provider can be used, False otherwise

        Example:
            >>> provider.is_available()
            True  # Model found, GPU available
        """
        ...

    def supports(self, image_path: Path) -> bool:
        """Check if this provider should process the given image.

        Allows providers to opt-in or opt-out based on image properties,
        existing annotations, or other criteria.

        Args:
            image_path: Path to the image file

        Returns:
            True if this provider should process the image

        Example:
            >>> provider.supports(Path("document.jpg"))
            True  # This image needs layout detection
        """
        ...

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image.

        This is the primary enrichment method for single images.
        For batch processing, use enrich_batch() instead.

        Args:
            image_path: Path to the image file

        Returns:
            EnrichmentData with derived annotations

        Raises:
            InferenceError: If inference fails
            ProviderUnavailableError: If provider is not available

        Example:
            >>> enrichment = provider.enrich(Path("document.jpg"))
            >>> print(enrichment.layout_detections)
            [LayoutDetection(...), ...]
        """
        ...

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images in a batch.

        Batch processing can significantly improve performance by:
        - Amortizing model loading/initialization costs
        - Utilizing GPU batch inference capabilities
        - Reducing Python overhead

        The default implementation just calls enrich() for each image.
        Providers should override this for optimized batch processing.

        Args:
            image_paths: List of image file paths

        Returns:
            List of EnrichmentData in same order as image_paths

        Raises:
            InferenceError: If batch inference fails
            ProviderUnavailableError: If provider is not available

        Example:
            >>> paths = [Path("doc1.jpg"), Path("doc2.jpg")]
            >>> results = provider.enrich_batch(paths)
            >>> len(results)
            2
        """
        return [self.enrich(p) for p in image_paths]


@runtime_checkable
class QualityScoreProvider(Protocol):
    """Protocol for continuous quality score providers.

    Providers that predict continuous quality scores (0.0-1.0 or 1.0-5.0)
    should implement this protocol in addition to EnrichmentProvider.

    This protocol adds no additional methods but serves as a marker
    for type checking and documentation.

    Example:
        >>> class SigLIPProvider(EnrichmentProvider, QualityScoreProvider):
        ...     def enrich(self, image_path: Path) -> EnrichmentData:
        ...         # Predict quality score
        ...         score = self.model.predict(image_path)
        ...         return EnrichmentData(
        ...             llm_predicted_mos=score,
        ...             llm_prediction_confidence=0.95,
        ...             llm_model_name="siglip2-iqa",
        ...         )
    """


__all__ = [
    "EnrichmentProvider",
    "QualityScoreProvider",
]
