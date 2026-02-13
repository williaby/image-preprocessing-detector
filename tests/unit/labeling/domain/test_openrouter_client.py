# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for OpenRouter API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from image_preprocessing_detector.labeling.domain.config import (
    DomainPipelineConfig,
    EnrichmentResult,
)
from image_preprocessing_detector.labeling.domain.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
    _clamp_confidence,
    _extract_json,
    _parse_text_response,
    _parse_vision_response,
    _safe_bool,
    _safe_str,
)


class TestExtractJson:
    """Tests for _extract_json helper."""

    def test_clean_json(self) -> None:
        """Parses clean JSON directly."""
        result = _extract_json('{"domain": "SCI", "domain_confidence": 0.95}')
        assert result["domain"] == "SCI"
        assert result["domain_confidence"] == pytest.approx(0.95)

    def test_json_in_markdown_code_block(self) -> None:
        """Extracts JSON from markdown code blocks."""
        text = '```json\n{"domain": "FIN", "domain_confidence": 0.88}\n```'
        result = _extract_json(text)
        assert result["domain"] == "FIN"

    def test_json_with_surrounding_text(self) -> None:
        """Extracts JSON from text with surrounding content."""
        text = 'Here is the result: {"domain": "LEG", "domain_confidence": 0.90}'
        result = _extract_json(text)
        assert result["domain"] == "LEG"

    def test_invalid_json_raises(self) -> None:
        """Raises OpenRouterError for unparseable content."""
        with pytest.raises(OpenRouterError, match="Could not extract valid JSON"):
            _extract_json("This is not JSON at all")

    def test_whitespace_handling(self) -> None:
        """Handles leading/trailing whitespace."""
        result = _extract_json('  \n {"domain": "TAX"} \n  ')
        assert result["domain"] == "TAX"

    def test_code_block_without_json_label(self) -> None:
        """Extracts from code block without json label."""
        text = '```\n{"domain": "MED", "domain_confidence": 0.75}\n```'
        result = _extract_json(text)
        assert result["domain"] == "MED"


class TestParseTextResponse:
    """Tests for _parse_text_response."""

    def test_valid_response(self) -> None:
        """Parses a complete valid text response."""
        raw: dict[str, Any] = {
            "domain": "SCI",
            "domain_confidence": 0.92,
            "iso639_language": "en",
            "iso15924_script": "Latn",
            "content_type": "scientific_paper",
            "reasoning": "Contains abstract and citations",
        }
        result = _parse_text_response(raw, "deepseek/deepseek-r1-0528:free")
        assert result.domain_level1 == "SCI"
        assert result.domain_confidence == pytest.approx(0.92)
        assert result.iso639_language == "en"
        assert result.iso15924_script == "Latn"
        assert result.input_mode == "text"
        assert result.model_used == "deepseek/deepseek-r1-0528:free"

    def test_invalid_domain_defaults_to_unk(self) -> None:
        """Invalid domain code defaults to UNK."""
        raw: dict[str, Any] = {"domain": "INVALID", "domain_confidence": 0.9}
        result = _parse_text_response(raw, "test-model")
        assert result.domain_level1 == "UNK"

    def test_missing_domain_defaults_to_unk(self) -> None:
        """Missing domain field defaults to UNK."""
        raw: dict[str, Any] = {"domain_confidence": 0.5}
        result = _parse_text_response(raw, "test-model")
        assert result.domain_level1 == "UNK"

    def test_confidence_clamped(self) -> None:
        """Confidence values clamped to [0, 1]."""
        raw: dict[str, Any] = {"domain": "FIN", "domain_confidence": 1.5}
        result = _parse_text_response(raw, "test-model")
        assert result.domain_confidence == pytest.approx(1.0)

    def test_domain_case_insensitive(self) -> None:
        """Domain codes are uppercased."""
        raw: dict[str, Any] = {"domain": "fin", "domain_confidence": 0.8}
        result = _parse_text_response(raw, "test-model")
        assert result.domain_level1 == "FIN"


class TestParseVisionResponse:
    """Tests for _parse_vision_response."""

    def test_full_vision_response(self) -> None:
        """Parses a complete vision response with all fields."""
        raw: dict[str, Any] = {
            "domain": "FIN",
            "domain_confidence": 0.88,
            "iso639_language": "en",
            "iso15924_script": "Latn",
            "content_type": "financial_statement",
            "capture_method": "born_digital",
            "has_table": True,
            "has_formula": False,
            "has_handwriting": False,
            "has_signature": True,
            "has_figure": True,
            "orientation": "portrait",
            "reasoning": "Annual report",
        }
        result = _parse_vision_response(raw, "google/gemini-2.0-flash-001")
        assert result.domain_level1 == "FIN"
        assert result.capture_method == "born_digital"
        assert result.has_table is True
        assert result.has_signature is True
        assert result.orientation == "portrait"
        assert result.input_mode == "vision"

    def test_invalid_capture_method_defaults(self) -> None:
        """Invalid capture method defaults to 'unknown'."""
        raw: dict[str, Any] = {
            "domain": "SCI",
            "domain_confidence": 0.9,
            "capture_method": "magic_scanner",
        }
        result = _parse_vision_response(raw, "test-model")
        assert result.capture_method == "unknown"

    def test_invalid_orientation_defaults_to_none(self) -> None:
        """Invalid orientation defaults to None."""
        raw: dict[str, Any] = {
            "domain": "SCI",
            "domain_confidence": 0.9,
            "orientation": "diagonal",
        }
        result = _parse_vision_response(raw, "test-model")
        assert result.orientation is None

    def test_valid_orientation_values(self) -> None:
        """Both portrait and landscape are valid."""
        for orient in ("portrait", "landscape"):
            raw: dict[str, Any] = {
                "domain": "ADM",
                "domain_confidence": 0.85,
                "orientation": orient,
            }
            result = _parse_vision_response(raw, "test-model")
            assert result.orientation == orient


class TestClampConfidence:
    """Tests for _clamp_confidence."""

    def test_normal_value(self) -> None:
        """Normal values pass through."""
        assert _clamp_confidence(0.85) == pytest.approx(0.85)

    def test_above_one(self) -> None:
        """Values above 1.0 clamped to 1.0."""
        assert _clamp_confidence(1.5) == pytest.approx(1.0)

    def test_below_zero(self) -> None:
        """Values below 0.0 clamped to 0.0."""
        assert _clamp_confidence(-0.5) == pytest.approx(0.0)

    def test_non_numeric_defaults(self) -> None:
        """Non-numeric values default to 0.5."""
        assert _clamp_confidence("not a number") == pytest.approx(0.5)
        assert _clamp_confidence(None) == pytest.approx(0.5)

    def test_string_number(self) -> None:
        """String numbers are converted."""
        assert _clamp_confidence("0.75") == pytest.approx(0.75)


class TestSafeStr:
    """Tests for _safe_str."""

    def test_normal_string(self) -> None:
        """Normal strings returned as-is."""
        assert _safe_str("hello") == "hello"

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert _safe_str(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert _safe_str("") is None

    def test_whitespace_only_returns_none(self) -> None:
        """Whitespace-only string returns None."""
        assert _safe_str("   ") is None

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace stripped."""
        assert _safe_str("  hello  ") == "hello"


class TestSafeBool:
    """Tests for _safe_bool."""

    def test_true_bool(self) -> None:
        """True bool returns True."""
        assert _safe_bool(True) is True

    def test_false_bool(self) -> None:
        """False bool returns False."""
        assert _safe_bool(False) is False

    def test_none_returns_none(self) -> None:
        """None returns None."""
        assert _safe_bool(None) is None

    def test_string_true_variants(self) -> None:
        """String 'true', '1', 'yes' return True."""
        assert _safe_bool("true") is True
        assert _safe_bool("True") is True
        assert _safe_bool("1") is True
        assert _safe_bool("yes") is True

    def test_string_false_variants(self) -> None:
        """Other strings return False."""
        assert _safe_bool("false") is False
        assert _safe_bool("no") is False
        assert _safe_bool("0") is False


class TestOpenRouterClient:
    """Tests for OpenRouterClient (mocked API)."""

    def test_classify_text_success(self) -> None:
        """Successful text classification returns EnrichmentResult."""
        config = DomainPipelineConfig(openrouter_api_key="test-key")
        client = OpenRouterClient(config)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"domain": "SCI", "domain_confidence": 0.92, '
                    '"iso639_language": "en", "iso15924_script": "Latn", '
                    '"content_type": "paper", "reasoning": "test"}'
                )
            )
        ]
        mock_response.usage = MagicMock(total_tokens=150)

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        client._client = mock_openai_client

        result = client.classify_text("Sample text", "deepseek/deepseek-r1-0528:free")
        assert isinstance(result, EnrichmentResult)
        assert result.domain_level1 == "SCI"
        assert result.domain_confidence == pytest.approx(0.92)
        assert result.input_mode == "text"

    def test_retry_on_failure(self) -> None:
        """Client retries on API failure."""
        config = DomainPipelineConfig(
            openrouter_api_key="test-key",
            max_retries=2,
            retry_base_delay=0.01,
        )
        client = OpenRouterClient(config)

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        client._client = mock_openai_client

        with pytest.raises(OpenRouterError, match="All 2 retries failed"):
            client.classify_text("text", "test-model")

        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_ensure_client_missing_openai(self) -> None:
        """Raises OpenRouterError when openai not installed."""
        config = DomainPipelineConfig(openrouter_api_key="test-key")
        client = OpenRouterClient(config)

        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(OpenRouterError, match="openai library required"):
                client._ensure_client()

    def test_usage_stats(self) -> None:
        """Usage stats track tokens and calls."""
        config = DomainPipelineConfig(openrouter_api_key="test-key")
        client = OpenRouterClient(config)
        stats = client.get_usage_stats()
        assert stats["total_tokens"] == 0
        assert stats["total_calls"] == 0
