"""Tests for generic field resolver framework."""

from __future__ import annotations

from scripts.audit.integration.resolvers import (
    SourcePriority,
    resolve_field,
    resolve_language,
)


class TestResolveField:
    """Tests for resolve_field function."""

    def test_returns_highest_priority_value(self) -> None:
        priorities = [
            SourcePriority("parser_gt", "lang", 0.95),
            SourcePriority("llm", "lang", 0.65),
        ]
        sources = {
            "parser_gt": {"lang": "en"},
            "llm": {"lang": "zh"},
        }
        result = resolve_field(priorities, sources)
        assert result.value == "en"
        assert result.confidence == 0.95
        assert result.source == "parser_gt"
        assert result.source_rank == 1

    def test_skips_none_source(self) -> None:
        priorities = [
            SourcePriority("parser_gt", "lang", 0.95),
            SourcePriority("llm", "lang", 0.65),
        ]
        sources = {
            "parser_gt": None,
            "llm": {"lang": "zh"},
        }
        result = resolve_field(priorities, sources)
        assert result.value == "zh"
        assert result.source == "llm"
        assert result.source_rank == 2

    def test_skips_empty_value(self) -> None:
        priorities = [
            SourcePriority("parser_gt", "lang", 0.95),
            SourcePriority("llm", "lang", 0.65),
        ]
        sources = {
            "parser_gt": {"lang": ""},
            "llm": {"lang": "zh"},
        }
        result = resolve_field(priorities, sources)
        assert result.value == "zh"

    def test_skips_values_in_skip_set(self) -> None:
        priorities = [
            SourcePriority("parser_gt", "lang", 0.95),
            SourcePriority("llm", "lang", 0.65),
        ]
        sources = {
            "parser_gt": {"lang": "und"},
            "llm": {"lang": "zh"},
        }
        result = resolve_field(priorities, sources, skip_values=frozenset({"und"}))
        assert result.value == "zh"

    def test_returns_default_when_no_match(self) -> None:
        priorities = [
            SourcePriority("parser_gt", "lang", 0.95),
        ]
        sources = {"parser_gt": None}
        result = resolve_field(
            priorities,
            sources,
            default_value="und",
            default_confidence=0.1,
            default_source="none",
        )
        assert result.value == "und"
        assert result.confidence == 0.1
        assert result.source == "none"

    def test_caps_confidence_at_max(self) -> None:
        priorities = [
            SourcePriority("openlid", "language", 0.65, max_confidence=0.70),
        ]
        sources = {
            "openlid": {"language": "en", "language_confidence": 0.95},
        }
        result = resolve_field(priorities, sources)
        assert result.confidence == 0.70

    def test_uses_source_confidence_when_available(self) -> None:
        priorities = [
            SourcePriority("openlid", "language", 0.65, max_confidence=1.0),
        ]
        sources = {
            "openlid": {"language": "en", "language_confidence": 0.82},
        }
        result = resolve_field(priorities, sources)
        assert result.confidence == 0.82

    def test_empty_priorities(self) -> None:
        result = resolve_field([], {}, default_value="fallback", default_confidence=0.0)
        assert result.value == "fallback"
        assert result.source_rank == 1

    def test_missing_source_in_dict(self) -> None:
        priorities = [
            SourcePriority("nonexistent", "lang", 0.95),
        ]
        sources = {"parser_gt": {"lang": "en"}}
        result = resolve_field(priorities, sources, default_value="und")
        assert result.value == "und"


class TestResolveLanguage:
    """Tests for resolve_language function."""

    def test_parser_gt_highest_priority(self) -> None:
        sources = {
            "parser_gt": {"language_code": "ja", "iso15924_script_code": "Jpan"},
            "llm": {"iso639_language": "en", "iso15924_script": "Latn"},
        }
        lang, script = resolve_language(sources)
        assert lang.value == "ja"
        assert lang.confidence == 0.95
        assert script.value == "Jpan"

    def test_llm_fallback(self) -> None:
        sources = {
            "parser_gt": None,
            "llm": {"iso639_language": "zh", "iso15924_script": "Hans"},
        }
        lang, script = resolve_language(sources)
        assert lang.value == "zh"
        assert script.value == "Hans"

    def test_openlid_fallback(self) -> None:
        sources = {
            "openlid": {"language": "ar", "script": "Arab"},
        }
        lang, script = resolve_language(sources)
        assert lang.value == "ar"
        assert script.value == "Arab"

    def test_default_when_no_sources(self) -> None:
        sources: dict = {}
        lang, script = resolve_language(sources)
        assert lang.value == "und"
        assert script.value == "Zyyy"

    def test_skips_und_language(self) -> None:
        sources = {
            "parser_gt": {"language_code": "und"},
            "llm": {"iso639_language": "en", "iso15924_script": "Latn"},
        }
        lang, script = resolve_language(sources)
        assert lang.value == "en"

    def test_script_defaults_to_zyyy(self) -> None:
        sources = {
            "llm": {"iso639_language": "en"},
        }
        lang, script = resolve_language(sources)
        assert lang.value == "en"
        assert script.value == "Zyyy"

    def test_custom_priorities(self) -> None:
        custom = [
            SourcePriority("custom_src", "lang", 0.99, 1.0),
        ]
        sources = {
            "custom_src": {"lang": "ko"},
        }
        lang, script = resolve_language(sources, priorities=custom)
        assert lang.value == "ko"
