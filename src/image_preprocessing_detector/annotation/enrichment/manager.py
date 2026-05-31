"""Enrichment manager for orchestrating multiple providers.

This module provides the EnrichmentManager class that coordinates multiple
enrichment providers, handles provider failures gracefully, and integrates
with validation from schemas/validators.py.

Classes:
    EnrichmentManager: Orchestrates multiple enrichment providers

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.manager import (
    ...     EnrichmentManager,
    ... )
    >>> from image_preprocessing_detector.annotation.enrichment.providers.yolo import (
    ...     YOLOProvider,
    ... )
    >>>
    >>> # Create providers
    >>> yolo = YOLOProvider(model_path="checkpoints/yolo.pt")
    >>>
    >>> # Create manager
    >>> manager = EnrichmentManager(providers=[yolo])
    >>>
    >>> # Enrich images
    >>> paths = [Path("doc1.jpg"), Path("doc2.jpg")]
    >>> results = manager.enrich_batch(paths)
    >>> for result in results:
    ...     if result.errors:
    ...         print(f"Errors: {result.errors}")
    ...     else:
    ...         print(f"Success: {len(result.data.layout_detections)} detections")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import EnrichmentError

if TYPE_CHECKING:
    from ..schemas.enrichment import EnrichmentData
    from .providers.base import EnrichmentProvider

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of enrichment with optional errors.

    Attributes:
        data: Enriched data (may be partial on error)
        errors: List of error messages encountered
        warnings: List of non-fatal warning messages
        providers_used: Names of providers that processed this image
    """

    data: EnrichmentData
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether enrichment completed without errors."""
        return len(self.errors) == 0


class EnrichmentManager:
    """Manage multiple enrichment providers with validation.

    Coordinates multiple enrichment providers, routing images to appropriate
    providers based on availability and configuration. Handles provider failures
    gracefully and provides comprehensive error tracking.

    Features:
        - Tier-ordered provider execution (lower tier = higher priority)
        - Provider fallback chain on failures
        - Runtime validation using schema validators
        - Dead-letter queue for failed samples
        - Retry logic for transient failures

    Attributes:
        providers: List of enrichment providers
        validate: Whether to validate enrichment results
        max_retries: Maximum retry attempts for transient failures
    """

    def __init__(
        self,
        providers: list[EnrichmentProvider],
        validate: bool = True,
        max_retries: int = 2,
    ):
        """Initialize EnrichmentManager.

        Args:
            providers (list[EnrichmentProvider]): List of enrichment providers to use
            validate (bool): Whether to validate enrichment results (default: True)
            max_retries (int): Maximum retry attempts for transient failures"""
        self.providers = providers
        self.validate = validate
        self.max_retries = max_retries

        # Tier priority mapping (lower tier = higher priority)
        self._tier_priority = {
            "tier_0_exact": 0,
            "tier_1_annotation": 1,
            "tier_2_model": 2,
            "tier_3_heuristic": 3,
        }

        # Dead-letter queue for failed samples
        self._dead_letter: list[tuple[Path, Exception]] = []

        logger.info(f"EnrichmentManager initialized with {len(providers)} providers")

    def enrich(self, image_path: Path) -> EnrichmentResult:
        """Enrich a single image.

        Args:
            image_path (Path): Path to image file

        Returns:
            EnrichmentResult: EnrichmentResult with data and any errors"""
        return self.enrich_batch([image_path])[0]

    def enrich_batch(
        self,
        image_paths: list[Path],
        existing: list[EnrichmentData | None] | None = None,
    ) -> list[EnrichmentResult]:
        """Apply all applicable providers in tier order.

        Processes images through available providers in tier priority order:
        1. Tier 0 (exact) - highest confidence
        2. Tier 1 (annotation-derived)
        3. Tier 2 (model inference)
        4. Tier 3 (heuristics) - lowest confidence

        Args:
            image_paths (list[Path]): Paths to images to enrich
            existing (list[EnrichmentData | None] | None): Optional existing enrichment data to augment

        Returns:
            list[EnrichmentResult]: List of EnrichmentResult with data and any errors"""
        from ..schemas.enrichment import EnrichmentData

        if not image_paths:
            return []

        # Initialize results with existing data or empty
        if existing is None:
            existing = [None] * len(image_paths)

        results = [EnrichmentResult(data=e or EnrichmentData()) for e in existing]

        # Get available providers sorted by tier priority
        available_providers = self._get_sorted_providers()

        if not available_providers:
            logger.warning("No enrichment providers available")
            for result in results:
                result.warnings.append("No enrichment providers available")
            return results

        # Apply each provider
        for provider in available_providers:
            logger.debug(f"Applying provider: {provider.name} (tier: {provider.tier})")

            # Find images that this provider should process
            applicable_indices = [
                i for i, path in enumerate(image_paths) if provider.supports(path)
            ]

            if not applicable_indices:
                logger.debug(f"Provider {provider.name} has no applicable images")
                continue

            # Extract batch for this provider
            batch_paths = [image_paths[i] for i in applicable_indices]
            batch_existing = [results[i].data for i in applicable_indices]

            # Process with retry logic
            enriched = self._process_with_retry(
                provider, batch_paths, batch_existing, applicable_indices, results
            )

            # Update results
            if enriched is not None:
                for idx, enrichment in zip(applicable_indices, enriched, strict=True):
                    results[idx].data = enrichment
                    results[idx].providers_used.append(provider.name)

        # Validate results if enabled
        if self.validate:
            self._validate_results(results)

        return results

    def _get_sorted_providers(self) -> list[EnrichmentProvider]:
        """Get available providers sorted by tier priority.

        Returns:
            list[EnrichmentProvider]: List of available providers in priority order"""
        available = [p for p in self.providers if p.is_available()]

        # Sort by tier (lower tier number = higher priority)
        sorted_providers = sorted(
            available, key=lambda p: self._tier_priority.get(p.tier, 99)
        )

        logger.debug(
            f"Available providers: {[p.name for p in sorted_providers]} "
            f"(out of {len(self.providers)} total)"
        )

        return sorted_providers

    def _process_with_retry(
        self,
        provider: EnrichmentProvider,
        batch_paths: list[Path],
        _batch_existing: list[EnrichmentData],
        indices: list[int],
        results: list[EnrichmentResult],
    ) -> list[EnrichmentData] | None:
        """Process batch with retry logic for transient failures.

        Args:
            provider (EnrichmentProvider): Provider to use
            batch_paths (list[Path]): Image paths to process
            _batch_existing (list[EnrichmentData]): Existing enrichment data (reserved for incremental enrichment)
            indices (list[int]): Indices in original results list
            results (list[EnrichmentResult]): Results list to update on error

        Returns:
            list[EnrichmentData] | None: List of enriched data, or None on failure"""
        for attempt in range(self.max_retries + 1):
            try:
                enriched = provider.enrich_batch(batch_paths)
            except EnrichmentError as e:
                # Structured enrichment error - log and track
                logger.warning(
                    f"Provider {provider.name} failed (attempt {attempt + 1}): {e}"
                )

                # Add to dead letter queue
                for _idx, path in zip(indices, batch_paths, strict=True):
                    self._dead_letter.append((path, e))

                # Update result errors
                for idx in indices:
                    results[idx].errors.append(f"{provider.name}: {e}")

                # Retry on transient errors
                if attempt < self.max_retries and self._is_transient(e):
                    logger.info(f"Retrying provider {provider.name}...")
                    continue
                return None

            except Exception as e:
                # Unexpected error - log and fail
                logger.error(
                    f"Provider {provider.name} failed unexpectedly: {e}", exc_info=True
                )

                for _idx, path in zip(indices, batch_paths, strict=True):
                    self._dead_letter.append((path, e))
                    results[indices[batch_paths.index(path)]].errors.append(
                        f"{provider.name}: Unexpected error: {e}"
                    )

                return None

            else:
                if attempt > 0:
                    logger.info(
                        f"Provider {provider.name} succeeded on retry {attempt}"
                    )
                return enriched

        return None

    def _is_transient(self, error: Exception) -> bool:
        """Check if error is transient and worth retrying.

        Args:
            error (Exception): Exception to check

        Returns:
            bool: True if error might be transient"""
        # Check for CUDA OOM or other transient GPU errors
        error_msg = str(error).lower()
        transient_indicators = [
            "out of memory",
            "cuda error",
            "timeout",
            "connection",
        ]

        return any(indicator in error_msg for indicator in transient_indicators)

    def _validate_results(self, results: list[EnrichmentResult]) -> None:
        """Validate enrichment results using schema validators.

        Args:
            results (list[EnrichmentResult]): List of results to validate"""
        from ..schemas.validators import validate_enrichment_data

        for i, result in enumerate(results):
            try:
                # Convert EnrichmentData to dict for validation
                data_dict = self._enrichment_to_dict(result.data)

                # Validate using schema validators
                validation_result = validate_enrichment_data(data_dict)

                if not validation_result.valid:
                    result.errors.extend(validation_result.errors)
                    logger.warning(
                        f"Validation failed for result {i}: {validation_result.errors}"
                    )

                if validation_result.warnings:
                    result.warnings.extend(validation_result.warnings)

            except Exception as e:
                error_msg = f"Validation error: {e}"
                result.errors.append(error_msg)
                logger.error(f"Validation error for result {i}: {e}", exc_info=True)

    def _enrichment_to_dict(self, data: EnrichmentData) -> dict:
        """Convert EnrichmentData to dictionary for validation.

        Args:
            data (EnrichmentData): EnrichmentData instance

        Returns:
            dict: Dictionary representation"""
        from dataclasses import asdict

        return asdict(data)

    def get_dead_letter_queue(self) -> list[tuple[Path, Exception]]:
        """Get samples that failed enrichment.

        Returns:
            list[tuple[Path, Exception]]: List of (image_path, exception) tuples"""
        return list(self._dead_letter)

    def clear_dead_letter_queue(self) -> None:
        """Clear the dead-letter queue."""
        self._dead_letter.clear()
        logger.debug("Dead-letter queue cleared")

    def get_stats(self) -> dict:
        """Get enrichment statistics.

        Returns:
            dict: Dictionary with processing statistics"""
        available_count = len([p for p in self.providers if p.is_available()])

        return {
            "total_providers": len(self.providers),
            "available_providers": available_count,
            "dead_letter_count": len(self._dead_letter),
            "validation_enabled": self.validate,
            "max_retries": self.max_retries,
        }


__all__ = ["EnrichmentManager", "EnrichmentResult"]
