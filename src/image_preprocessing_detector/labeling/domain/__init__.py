# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Domain classification and metadata enrichment via OpenRouter LLMs.

This package provides per-sample domain classification and multi-field
metadata enrichment using free and low-cost OpenRouter LLM models.

Modules:
    config: Pipeline configuration (model roster, thresholds, API settings)
    prompts: Prompt templates for text and vision classification
    openrouter_client: OpenRouter API client (OpenAI-compatible)
    classifier: Multi-field enrichment orchestrator with confidence escalation
"""

from image_preprocessing_detector.labeling.domain.classifier import (
    MetadataEnricher,
)
from image_preprocessing_detector.labeling.domain.config import (
    DomainModelConfig,
    DomainPipelineConfig,
    EnrichmentResult,
)

__all__ = [
    "DomainModelConfig",
    "DomainPipelineConfig",
    "EnrichmentResult",
    "MetadataEnricher",
]
