# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for domain classification config module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from image_preprocessing_detector.labeling.domain.config import (
    AVAILABLE_TEXT_MODELS,
    AVAILABLE_VISION_MODELS,
    VALID_CAPTURE_METHODS,
    VALID_DOMAIN_CODES,
    DomainModelConfig,
    DomainPipelineConfig,
    EnrichmentResult,
    get_default_config,
)


class TestDomainModelConfig:
    """Tests for DomainModelConfig dataclass."""

    def test_default_values(self) -> None:
        """Model config has sensible defaults."""
        config = DomainModelConfig(model_id="test/model:free", role="primary_text")
        assert config.max_tokens == 2000
        assert config.temperature == 0.0
        assert config.supports_vision is False

    def test_vision_model(self) -> None:
        """Vision model flag is correctly set."""
        config = DomainModelConfig(
            model_id="google/gemini-2.0-flash-001",
            role="primary_vision",
            supports_vision=True,
        )
        assert config.supports_vision is True

    def test_frozen(self) -> None:
        """Config is immutable."""
        config = DomainModelConfig(model_id="test/model:free", role="test")
        with pytest.raises(AttributeError):
            config.model_id = "changed"  # type: ignore[misc]


class TestDomainPipelineConfig:
    """Tests for DomainPipelineConfig."""

    def test_default_config(self) -> None:
        """Default config has expected model roster."""
        config = get_default_config()
        assert config.primary_text_model.model_id == "google/gemini-2.0-flash-001"
        assert (
            config.secondary_text_model.model_id == "google/gemini-2.0-flash-lite-001"
        )
        assert config.primary_vision_model.model_id == "google/gemini-2.0-flash-001"
        assert config.primary_vision_model.supports_vision is True

    def test_confidence_thresholds(self) -> None:
        """Default thresholds are within valid range."""
        config = get_default_config()
        assert 0.0 <= config.text_confidence_threshold <= 1.0
        assert 0.0 <= config.vision_confidence_threshold <= 1.0
        assert config.text_confidence_threshold == 0.85
        assert config.vision_confidence_threshold == 0.80

    def test_api_key_from_env(self) -> None:
        """API key resolved from environment variable."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"}):
            config = DomainPipelineConfig()
            assert config.get_api_key() == "test-key-123"

    def test_api_key_from_config(self) -> None:
        """API key from config takes precedence."""
        config = DomainPipelineConfig(openrouter_api_key="config-key")
        assert config.get_api_key() == "config-key"

    def test_api_key_missing_raises(self) -> None:
        """Missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENROUTER_API_KEY if set
            env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                config = DomainPipelineConfig()
                with pytest.raises(ValueError, match="OpenRouter API key"):
                    config.get_api_key()

    def test_rate_limit_delay(self) -> None:
        """Rate limit delay is configurable."""
        config = DomainPipelineConfig(rate_limit_delay=1.0)
        assert config.rate_limit_delay == 1.0


class TestEnrichmentResult:
    """Tests for EnrichmentResult dataclass."""

    def test_minimal_result(self) -> None:
        """Result with only required fields."""
        result = EnrichmentResult(domain_level1="SCI", domain_confidence=0.95)
        assert result.domain_level1 == "SCI"
        assert result.domain_confidence == 0.95
        assert result.iso639_language is None
        assert result.has_table is None
        assert result.input_mode == "text"
        assert result.escalated is False

    def test_full_result(self) -> None:
        """Result with all fields populated (vision mode)."""
        result = EnrichmentResult(
            domain_level1="FIN",
            domain_confidence=0.88,
            iso639_language="en",
            iso15924_script="Latn",
            content_type="financial_statement",
            capture_method="born_digital",
            has_table=True,
            has_formula=False,
            has_handwriting=False,
            has_signature=True,
            has_figure=True,
            orientation="portrait",
            reasoning="Annual report",
            model_used="google/gemini-2.0-flash-001",
            tokens_used=1200,
            input_mode="vision",
            escalated=False,
        )
        assert result.has_table is True
        assert result.has_signature is True
        assert result.input_mode == "vision"


class TestConstants:
    """Tests for module-level constants."""

    def test_domain_codes(self) -> None:
        """All 10 domain codes are present."""
        assert len(VALID_DOMAIN_CODES) == 10
        expected = {
            "TAX",
            "LEG",
            "FIN",
            "TEC",
            "SCI",
            "ADM",
            "MED",
            "EDU",
            "PER",
            "UNK",
        }
        assert expected == VALID_DOMAIN_CODES

    def test_capture_methods(self) -> None:
        """Capture methods match CaptureMethod enum."""
        assert "born_digital" in VALID_CAPTURE_METHODS
        assert "scanner_flatbed" in VALID_CAPTURE_METHODS
        assert "unknown" in VALID_CAPTURE_METHODS

    def test_available_text_models(self) -> None:
        """All 7 user-specified text models are listed."""
        assert len(AVAILABLE_TEXT_MODELS) == 7
        model_ids = {m.model_id for m in AVAILABLE_TEXT_MODELS}
        assert "deepseek/deepseek-r1-0528:free" in model_ids
        assert "meta-llama/llama-3.3-70b-instruct:free" in model_ids

    def test_available_vision_models(self) -> None:
        """Vision models are listed with supports_vision=True."""
        assert len(AVAILABLE_VISION_MODELS) >= 2
        for model in AVAILABLE_VISION_MODELS:
            assert model.supports_vision is True
