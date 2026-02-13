# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for MetadataEnricher classification orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.labeling.domain.classifier import (
    MetadataEnricher,
    SampleInput,
    _fallback_result,
)
from image_preprocessing_detector.labeling.domain.config import (
    DomainPipelineConfig,
    EnrichmentResult,
)
from image_preprocessing_detector.labeling.domain.openrouter_client import (
    OpenRouterError,
)


def _make_result(
    domain: str = "SCI",
    confidence: float = 0.92,
    input_mode: str = "text",
) -> EnrichmentResult:
    """Create a test EnrichmentResult."""
    return EnrichmentResult(
        domain_level1=domain,
        domain_confidence=confidence,
        input_mode=input_mode,
        model_used="test-model",
    )


class TestSampleInput:
    """Tests for SampleInput dataclass."""

    def test_defaults(self) -> None:
        """Default values are correct."""
        sample = SampleInput(image_id="test-001")
        assert sample.text is None
        assert sample.image_path is None
        assert sample.text_source == "unknown"

    def test_with_text(self) -> None:
        """Text sample creation."""
        sample = SampleInput(
            image_id="test-001",
            text="Sample document",
            text_source="ground_truth",
        )
        assert sample.text == "Sample document"
        assert sample.text_source == "ground_truth"

    def test_with_image(self) -> None:
        """Image sample creation."""
        sample = SampleInput(
            image_id="test-001",
            image_path=Path("/tmp/test.png"),
        )
        assert sample.image_path == Path("/tmp/test.png")


class TestFallbackResult:
    """Tests for _fallback_result."""

    def test_text_fallback(self) -> None:
        """Text fallback returns UNK with zero confidence."""
        result = _fallback_result("text", "No text available")
        assert result.domain_level1 == "UNK"
        assert result.domain_confidence == 0.0
        assert result.input_mode == "text"
        assert "Fallback" in result.reasoning

    def test_vision_fallback(self) -> None:
        """Vision fallback returns UNK with zero confidence."""
        result = _fallback_result("vision", "API error")
        assert result.domain_level1 == "UNK"
        assert result.input_mode == "vision"
        assert result.model_used == "none"


class TestMetadataEnricher:
    """Tests for MetadataEnricher orchestrator."""

    def _make_enricher(self) -> MetadataEnricher:
        """Create enricher with mocked client."""
        config = DomainPipelineConfig(openrouter_api_key="test-key")
        enricher = MetadataEnricher(config)
        enricher._client = MagicMock()
        return enricher

    def test_text_routing(self) -> None:
        """Text input routes to text classification."""
        enricher = self._make_enricher()
        enricher._client.classify_text.return_value = _make_result("SCI", 0.95, "text")

        result = enricher.enrich_sample(text="Research paper about ML")
        assert result.domain_level1 == "SCI"
        assert result.domain_confidence == 0.95
        enricher._client.classify_text.assert_called_once()
        enricher._client.classify_image.assert_not_called()

    def test_image_routing(self) -> None:
        """Image-only input routes to vision classification."""
        enricher = self._make_enricher()
        enricher._client.classify_image.return_value = _make_result(
            "FIN", 0.88, "vision"
        )

        result = enricher.enrich_sample(image_path=Path("/tmp/test.png"))
        assert result.domain_level1 == "FIN"
        enricher._client.classify_image.assert_called_once()
        enricher._client.classify_text.assert_not_called()

    def test_no_input_raises(self) -> None:
        """Raises ValueError when neither text nor image provided."""
        enricher = self._make_enricher()
        with pytest.raises(ValueError, match="At least one"):
            enricher.enrich_sample()

    def test_empty_text_falls_back_to_image(self) -> None:
        """Empty text with image path falls back to vision."""
        enricher = self._make_enricher()
        enricher._client.classify_image.return_value = _make_result(
            "ADM", 0.80, "vision"
        )

        result = enricher.enrich_sample(text="   ", image_path=Path("/tmp/test.png"))
        assert result.domain_level1 == "ADM"
        enricher._client.classify_image.assert_called_once()

    def test_text_escalation_on_low_confidence(self) -> None:
        """Low confidence text result triggers escalation to secondary model."""
        enricher = self._make_enricher()

        primary_result = _make_result("SCI", 0.60, "text")
        secondary_result = _make_result("SCI", 0.90, "text")
        enricher._client.classify_text.side_effect = [
            primary_result,
            secondary_result,
        ]

        result = enricher.enrich_sample(text="Ambiguous document")
        assert result.domain_confidence == 0.90
        assert result.escalated is True
        assert enricher._client.classify_text.call_count == 2

    def test_text_no_escalation_on_high_confidence(self) -> None:
        """High confidence text result accepted without escalation."""
        enricher = self._make_enricher()
        enricher._client.classify_text.return_value = _make_result("FIN", 0.95, "text")

        result = enricher.enrich_sample(text="Financial statement Q4")
        assert result.domain_confidence == 0.95
        assert result.escalated is False
        assert enricher._client.classify_text.call_count == 1

    def test_text_escalation_keeps_primary_if_better(self) -> None:
        """Escalation keeps primary result when it has higher confidence."""
        enricher = self._make_enricher()

        primary_result = _make_result("SCI", 0.70, "text")
        secondary_result = _make_result("TEC", 0.50, "text")
        enricher._client.classify_text.side_effect = [
            primary_result,
            secondary_result,
        ]

        result = enricher.enrich_sample(text="Technical document")
        assert result.domain_level1 == "SCI"
        assert result.domain_confidence == 0.70
        assert result.escalated is True

    def test_secondary_text_failure_returns_primary(self) -> None:
        """Secondary model failure falls back to primary result."""
        enricher = self._make_enricher()

        primary_result = _make_result("MED", 0.60, "text")
        enricher._client.classify_text.side_effect = [
            primary_result,
            OpenRouterError("Secondary model error"),
        ]

        result = enricher.enrich_sample(text="Medical record")
        assert result.domain_level1 == "MED"
        assert result.escalated is True

    def test_primary_text_failure_returns_fallback(self) -> None:
        """Primary model failure returns fallback UNK result."""
        enricher = self._make_enricher()
        enricher._client.classify_text.side_effect = OpenRouterError("API down")

        result = enricher.enrich_sample(text="Document text")
        assert result.domain_level1 == "UNK"
        assert result.domain_confidence == 0.0

    def test_image_escalation_on_low_confidence(self) -> None:
        """Low confidence vision result triggers escalation."""
        enricher = self._make_enricher()

        primary_result = _make_result("UNK", 0.50, "vision")
        secondary_result = _make_result("EDU", 0.85, "vision")
        enricher._client.classify_image.side_effect = [
            primary_result,
            secondary_result,
        ]

        result = enricher.enrich_sample(image_path=Path("/tmp/test.png"))
        assert result.domain_level1 == "EDU"
        assert result.domain_confidence == 0.85
        assert result.escalated is True

    def test_get_stats_initial(self) -> None:
        """Initial stats are zeroed."""
        enricher = self._make_enricher()
        enricher._client.get_usage_stats.return_value = {
            "total_tokens": 0,
            "total_calls": 0,
        }

        stats = enricher.get_stats()
        assert stats["text_calls"] == 0
        assert stats["vision_calls"] == 0
        assert stats["escalations"] == 0
        assert stats["total_calls"] == 0

    def test_batch_processing(self) -> None:
        """Batch processes multiple samples."""
        enricher = self._make_enricher()
        enricher._config = DomainPipelineConfig(
            openrouter_api_key="test-key",
            rate_limit_delay=0.0,
        )
        enricher._client.classify_text.return_value = _make_result("SCI", 0.95, "text")

        samples = [
            SampleInput(image_id="s1", text="Paper 1"),
            SampleInput(image_id="s2", text="Paper 2"),
        ]
        results = enricher.enrich_batch(samples)
        assert len(results) == 2
        assert results[0][0] == "s1"
        assert results[1][0] == "s2"

    def test_batch_skip_ids(self) -> None:
        """Batch skips already-processed IDs."""
        enricher = self._make_enricher()
        enricher._config = DomainPipelineConfig(
            openrouter_api_key="test-key",
            rate_limit_delay=0.0,
        )
        enricher._client.classify_text.return_value = _make_result("SCI", 0.95, "text")

        samples = [
            SampleInput(image_id="s1", text="Paper 1"),
            SampleInput(image_id="s2", text="Paper 2"),
            SampleInput(image_id="s3", text="Paper 3"),
        ]
        results = enricher.enrich_batch(samples, skip_ids={"s1", "s3"})
        assert len(results) == 1
        assert results[0][0] == "s2"

    def test_batch_handles_errors(self) -> None:
        """Batch continues on individual sample errors."""
        enricher = self._make_enricher()
        enricher._config = DomainPipelineConfig(
            openrouter_api_key="test-key",
            rate_limit_delay=0.0,
        )
        enricher._client.classify_text.side_effect = [
            _make_result("SCI", 0.95, "text"),
            Exception("API error"),
            _make_result("FIN", 0.88, "text"),
        ]

        samples = [
            SampleInput(image_id="s1", text="Paper 1"),
            SampleInput(image_id="s2", text="Paper 2"),
            SampleInput(image_id="s3", text="Paper 3"),
        ]
        results = enricher.enrich_batch(samples)
        assert len(results) == 3
        # Second sample should have UNK fallback
        assert results[1][1].domain_level1 == "UNK"
