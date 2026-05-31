"""Multi-field metadata enrichment orchestrator.

Coordinates domain classification and metadata extraction using tiered
confidence escalation across text and vision models.

Example:
    >>> from image_preprocessing_detector.labeling.domain.classifier import (
    ...     MetadataEnricher,
    ... )
    >>> from image_preprocessing_detector.labeling.domain.config import (
    ...     get_default_config,
    ... )
    >>> enricher = MetadataEnricher(get_default_config())
    >>> result = enricher.enrich_sample(text="Annual financial report...")
    >>> print(result.domain_level1, result.domain_confidence)
    FIN 0.92
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from image_preprocessing_detector.labeling.domain.config import (
    DomainPipelineConfig,
    EnrichmentResult,
)
from image_preprocessing_detector.labeling.domain.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
)

logger = structlog.get_logger(__name__)


@dataclass
class SampleInput:
    """Input for a single sample to enrich.

    Attributes:
        image_id (str): Unique identifier for the sample.
        text (str | None): Document text content (if available).
        image_path (Path | None): Path to document image (if available).
        text_source (str): How text was obtained ('ground_truth', 'extracted', 'ocr').
    """

    image_id: str
    text: str | None = None
    image_path: Path | None = None
    text_source: str = "unknown"


class MetadataEnricher:
    """Orchestrates multi-field metadata enrichment with confidence escalation.

    Uses a tiered approach:
    1. Samples with text -> text-only model (free)
    2. Low confidence text results -> escalate to secondary text model (free)
    3. Samples without text -> vision model (paid)
    4. Low confidence vision results -> escalate to secondary vision model (paid)

    Args:
        config (DomainPipelineConfig): Pipeline configuration with model roster and thresholds.
    """

    def __init__(self, config: DomainPipelineConfig) -> None:
        self._config = config
        self._client = OpenRouterClient(config)
        self._stats: dict[str, Any] = {
            "text_calls": 0,
            "vision_calls": 0,
            "escalations": 0,
            "errors": 0,
            "model_usage": {},
        }

    def enrich_sample(
        self,
        text: str | None = None,
        image_path: Path | None = None,
        text_source: str = "unknown",
    ) -> EnrichmentResult:
        """Enrich a single sample with domain and metadata.

        Routes to text or vision classification based on input availability,
        with confidence-based escalation to secondary models.

        Args:
            text (str | None): Document text (if available).
            image_path (Path | None): Path to document image (if available).
            text_source (str): How text was obtained.

        Returns:
            EnrichmentResult:             EnrichmentResult with extracted metadata fields.

        Raises:
            ValueError: If neither text nor image_path provided.
        """
        if text is None and image_path is None:
            msg = "At least one of text or image_path must be provided"
            raise ValueError(msg)

        if text is not None and text.strip():
            return self._enrich_from_text(text, text_source)
        if image_path is not None:
            return self._enrich_from_image(image_path)

        # No usable input
        return _fallback_result("text", "No text or image available")

    def enrich_batch(
        self,
        samples: list[SampleInput],
        skip_ids: set[str] | None = None,
    ) -> list[tuple[str, EnrichmentResult]]:
        """Enrich a batch of samples with progress tracking.

        Args:
            samples (list[SampleInput]): List of SampleInput objects.
            skip_ids (set[str] | None): Set of image_ids to skip (for resume support).

        Returns:
            list[tuple[str, EnrichmentResult]]:             List of (image_id, EnrichmentResult) tuples.
        """
        results: list[tuple[str, EnrichmentResult]] = []
        skip = skip_ids or set()

        for sample in samples:
            if sample.image_id in skip:
                continue

            try:
                result = self.enrich_sample(
                    text=sample.text,
                    image_path=sample.image_path,
                    text_source=sample.text_source,
                )
                results.append((sample.image_id, result))

            except Exception as exc:
                logger.warning(
                    "sample_enrichment_failed",
                    image_id=sample.image_id,
                    error=str(exc),
                )
                self._stats["errors"] += 1
                fallback = _fallback_result("text", f"Error: {exc}")
                results.append((sample.image_id, fallback))

            # Rate limiting between calls
            if self._config.rate_limit_delay > 0:
                time.sleep(self._config.rate_limit_delay)

        return results

    def _enrich_from_text(
        self,
        text: str,
        _text_source: str,
    ) -> EnrichmentResult:
        """Classify using text-only models with escalation.

        Args:
            text (str): Document text.
            _text_source (str): How text was obtained (reserved for future routing).

        Returns:
            EnrichmentResult:             EnrichmentResult from text classification.
        """
        primary = self._config.primary_text_model
        threshold = self._config.text_confidence_threshold

        try:
            result = self._client.classify_text(text, primary.model_id)
            self._track_model_usage(primary.model_id)
            self._stats["text_calls"] += 1

            if result.domain_confidence >= threshold:
                return result

            # Escalate to secondary model
            logger.info(
                "escalating_to_secondary_text",
                primary_confidence=result.domain_confidence,
                threshold=threshold,
            )
            secondary = self._config.secondary_text_model
            try:
                secondary_result = self._client.classify_text(text, secondary.model_id)
                self._track_model_usage(secondary.model_id)
                self._stats["text_calls"] += 1
                self._stats["escalations"] += 1

                # Take higher confidence result
                if secondary_result.domain_confidence > result.domain_confidence:
                    secondary_result.escalated = True
                    return secondary_result

                result.escalated = True
                return result  # noqa: TRY300

            except OpenRouterError as exc:
                logger.warning(
                    "secondary_text_model_failed",
                    error=str(exc),
                )
                result.escalated = True
                return result

        except OpenRouterError as exc:
            logger.warning(
                "primary_text_model_failed",
                error=str(exc),
            )
            self._stats["errors"] += 1
            return _fallback_result("text", f"API error: {exc}")

    def _enrich_from_image(self, image_path: Path) -> EnrichmentResult:
        """Classify using vision models with escalation.

        Args:
            image_path (Path): Path to document image.

        Returns:
            EnrichmentResult:             EnrichmentResult from vision classification.
        """
        primary = self._config.primary_vision_model
        threshold = self._config.vision_confidence_threshold

        try:
            result = self._client.classify_image(image_path, primary.model_id)
            self._track_model_usage(primary.model_id)
            self._stats["vision_calls"] += 1

            if result.domain_confidence >= threshold:
                return result

            # Escalate to secondary vision model
            logger.info(
                "escalating_to_secondary_vision",
                primary_confidence=result.domain_confidence,
                threshold=threshold,
            )
            secondary = self._config.secondary_vision_model
            try:
                secondary_result = self._client.classify_image(
                    image_path, secondary.model_id
                )
                self._track_model_usage(secondary.model_id)
                self._stats["vision_calls"] += 1
                self._stats["escalations"] += 1

                if secondary_result.domain_confidence > result.domain_confidence:
                    secondary_result.escalated = True
                    return secondary_result

                result.escalated = True
                return result  # noqa: TRY300

            except OpenRouterError as exc:
                logger.warning(
                    "secondary_vision_model_failed",
                    error=str(exc),
                )
                result.escalated = True
                return result

        except OpenRouterError as exc:
            logger.warning(
                "primary_vision_model_failed",
                error=str(exc),
            )
            self._stats["errors"] += 1
            return _fallback_result("vision", f"API error: {exc}")

    def _track_model_usage(self, model_id: str) -> None:
        """Track model call count.

        Args:
            model_id (str): Model identifier.
        """
        usage = self._stats["model_usage"]
        if model_id not in usage:
            usage[model_id] = {"calls": 0}
        usage[model_id]["calls"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get enrichment statistics.

        Returns:
            dict[str, Any]:             Dict with call counts, escalation rate, error count, model usage.
        """
        total = self._stats["text_calls"] + self._stats["vision_calls"]
        client_stats = self._client.get_usage_stats()

        return {
            **self._stats,
            "total_calls": total,
            "escalation_rate": (
                self._stats["escalations"] / total if total > 0 else 0.0
            ),
            "total_tokens": client_stats["total_tokens"],
        }


def _fallback_result(input_mode: str, reason: str) -> EnrichmentResult:
    """Create a fallback result when classification fails.

    Args:
        input_mode (str): Input type that was attempted.
        reason (str): Reason for fallback.

    Returns:
        EnrichmentResult:         EnrichmentResult with UNK domain and low confidence.
    """
    return EnrichmentResult(
        domain_level1="UNK",
        domain_confidence=0.0,
        reasoning=f"Fallback: {reason}",
        model_used="none",
        input_mode=input_mode,
    )
