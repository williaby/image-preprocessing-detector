"""Simulated enrichment provider for GPU-less CI testing.

This module provides a SimulatedInferenceProvider that returns realistic
mock enrichment data without requiring actual GPU inference. This enables
E2E testing in CI environments without GPU access.

The provider generates deterministic, reproducible outputs based on:
- Image path/filename (for consistent test results)
- Configurable failure rates (for error testing)
- Realistic value distributions (for meaningful test coverage)

Usage:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.simulated import (
    ...     SimulatedInferenceProvider,
    ... )
    >>>
    >>> provider = SimulatedInferenceProvider(
    ...     failure_rate=0.0,  # No failures for normal tests
    ...     seed=42,  # Reproducible results
    ... )
    >>> assert provider.is_available()
    >>> result = provider.enrich(Path("test.png"))
    >>> print(result.quality_overall)
    0.85

For error testing:
    >>> # Inject 20% failure rate
    >>> provider = SimulatedInferenceProvider(failure_rate=0.2)
    >>> # Some calls will raise InferenceError
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "provider"
__l4_task__ = "iqa"
__l4_workstream__ = "WS3"
__l4_provides__ = "simulated_quality_labels"


import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from ...schemas.enrichment import EnrichmentData, LayoutDetection
from ..errors import InferenceError

if TYPE_CHECKING:
    pass  # No type-only imports needed yet; guard kept for future additions


class SimulatedInferenceProvider:
    """Simulated provider for GPU-less CI testing.

    Generates realistic mock enrichment data without GPU inference.
    Useful for:
    - E2E testing in CI (no GPU required)
    - Error injection testing
    - Performance benchmarking of pipeline logic
    - Unit testing of downstream consumers

    Args:
        failure_rate (float): Probability of simulated inference failure (0.0-1.0).
        seed (int): Random seed for reproducible outputs.
        simulate_latency (bool): Whether to add artificial latency.
        latency_ms (int): Latency to add in milliseconds (if enabled).

    Raises:
        ValueError: If failure_rate is not in [0.0, 1.0].
    """

    def __init__(
        self,
        failure_rate: float = 0.0,
        seed: int = 42,
        simulate_latency: bool = False,
        latency_ms: int = 10,
    ):
        if not 0.0 <= failure_rate <= 1.0:
            raise ValueError(f"failure_rate must be 0.0-1.0, got {failure_rate}")

        self._failure_rate = failure_rate
        self._seed = seed
        self._simulate_latency = simulate_latency
        self._latency_ms = latency_ms

        # Track call counts for deterministic failure injection
        self._call_count = 0

    @property
    def name(self) -> str:
        """Provider name for logging and provenance."""
        return "simulated_inference"

    @property
    def tier(self) -> str:
        """Enrichment tier - simulates tier_2_model providers."""
        return "tier_2_model"

    def is_available(self) -> bool:
        """Simulated provider is always available."""
        return True

    def supports(self, image_path: Path) -> bool:
        """Simulated provider supports all image formats."""
        # Support common image extensions
        supported_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".tif",
            ".bmp",
            ".webp",
        }
        return image_path.suffix.lower() in supported_extensions

    def _should_fail(self, image_path: Path) -> bool:
        """Determine if this call should fail based on failure rate.

        Uses deterministic hashing for reproducible behavior.
        """
        if self._failure_rate <= 0.0:
            return False
        if self._failure_rate >= 1.0:
            return True

        # Use hash of (path + call_count + seed) for determinism
        hash_input = f"{image_path.name}:{self._call_count}:{self._seed}"
        hash_value = int(
            hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:8], 16
        )
        threshold = int(self._failure_rate * 0xFFFFFFFF)

        return hash_value < threshold

    def _generate_deterministic_value(
        self,
        image_path: Path,
        field_name: str,
        min_val: float = 0.0,
        max_val: float = 1.0,
    ) -> float:
        """Generate a deterministic value based on image path and field.

        Args:
            image_path (Path): Path to image
            field_name (str): Name of the field being generated
            min_val (float): Minimum value
            max_val (float): Maximum value

        Returns:
            float: Deterministic float in [min_val, max_val]"""
        hash_input = f"{image_path.name}:{field_name}:{self._seed}"
        hash_value = int(
            hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:8], 16
        )
        normalized = hash_value / 0xFFFFFFFF  # 0.0-1.0
        return min_val + normalized * (max_val - min_val)

    def _generate_layout_detections(
        self,
        image_path: Path,
    ) -> list[LayoutDetection]:
        """Generate simulated layout detections.

        Based on filename patterns to provide meaningful test coverage.
        """
        detections = []
        filename = image_path.stem.lower()

        # Generate 1-3 detections based on path hash
        num_detections = 1 + int(
            self._generate_deterministic_value(image_path, "num_detections", 0, 2.99)
        )

        # Class names based on filename hints
        if "table" in filename:
            class_names = ["table", "text", "caption"]
        elif "form" in filename:
            class_names = ["text", "text", "figure"]
        elif "document" in filename:
            class_names = ["text", "title", "text"]
        else:
            class_names = ["text", "figure", "table"]

        for i in range(num_detections):
            # Generate deterministic bbox
            x1 = self._generate_deterministic_value(
                image_path, f"bbox_x1_{i}", 0.05, 0.3
            )
            y1 = self._generate_deterministic_value(
                image_path, f"bbox_y1_{i}", 0.05 + i * 0.25, 0.3 + i * 0.25
            )
            w = self._generate_deterministic_value(image_path, f"bbox_w_{i}", 0.3, 0.8)
            h = self._generate_deterministic_value(image_path, f"bbox_h_{i}", 0.1, 0.3)

            detections.append(
                LayoutDetection(
                    class_name=class_names[i % len(class_names)],
                    bbox=[x1, y1, x1 + w, y1 + h],
                    confidence=self._generate_deterministic_value(
                        image_path, f"conf_{i}", 0.75, 0.98
                    ),
                    source=self.name,
                )
            )

        return detections

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image with simulated data.

        Args:
            image_path (Path): Path to image file

        Returns:
            EnrichmentData: EnrichmentData with simulated values

        Raises:
            InferenceError: If simulated failure occurs
        """
        self._call_count += 1

        # Simulate latency if enabled
        if self._simulate_latency:
            import time

            time.sleep(self._latency_ms / 1000.0)

        # Check for simulated failure
        if self._should_fail(image_path):
            error_msg = (
                f"Simulated inference failure for {image_path.name} "
                f"(failure_rate={self._failure_rate})"
            )
            raise InferenceError(
                provider_name="SimulatedInferenceProvider",
                batch_size=1,
                cause=RuntimeError(error_msg),
            )

        # Generate deterministic enrichment data
        quality = self._generate_deterministic_value(image_path, "quality", 0.6, 0.95)
        llm_mos = self._generate_deterministic_value(image_path, "llm_mos", 2.5, 4.8)

        return EnrichmentData(
            # Quality scores
            quality_overall=quality,
            llm_predicted_mos=llm_mos,
            llm_predicted_normalized=llm_mos / 5.0,  # Normalize to 0-1
            llm_prediction_confidence=self._generate_deterministic_value(
                image_path, "llm_conf", 0.7, 0.95
            ),
            llm_model_name=self.name,
            # Layout detections
            layout_detections=[
                d.__dict__ for d in self._generate_layout_detections(image_path)
            ],
            # Content flags (deterministic based on filename)
            has_table="table" in image_path.stem.lower(),
            has_formula="formula" in image_path.stem.lower()
            or "math" in image_path.stem.lower(),
            has_handwriting="handwrit" in image_path.stem.lower()
            or "form" in image_path.stem.lower(),
            has_signature="sign" in image_path.stem.lower(),
            has_figure="figure" in image_path.stem.lower()
            or "image" in image_path.stem.lower(),
            content_flags_tier=self.tier,
            content_flags_source=self.name,
            # Structure analysis
            layout_type="single_column",
            text_density="high" if quality > 0.7 else "medium",
            # Resolution fields: simulated values
            resolution_dpi=300,
            resolution_category="high",
            # Domain fields: simulated document type
            domain_level1="DOC",  # Document
            domain_confidence=self._generate_deterministic_value(
                image_path, "domain_conf", 0.8, 0.95
            ),
        )

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images in batch.

        Args:
            image_paths (list[Path]): List of image paths

        Returns:
            list[EnrichmentData]: List of EnrichmentData in same order as inputs
        """
        return [self.enrich(p) for p in image_paths]


__all__ = ["SimulatedInferenceProvider"]
