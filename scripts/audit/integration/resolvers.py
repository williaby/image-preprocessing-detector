"""Generic field resolver framework for integration scripts.

Provides a declarative priority-chain resolver that replaces per-script
resolve_language(), resolve_domain(), and resolve_capture_method()
functions. Each field resolution is driven by a priority list of
(source_name, field_key, confidence, max_confidence) tuples.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.audit.integration.mixins.confidence_tracking import ResolvedField


@dataclass(frozen=True)
class SourcePriority:
    """A single source in a field's priority chain.

    Attributes:
        source_name: Name of the enrichment source (e.g., "parser_gt").
        field_key: Key to look up in the source data dict.
        confidence: Default confidence when source provides a value.
        max_confidence: Maximum confidence to assign from this source.
    """

    source_name: str
    field_key: str
    confidence: float
    max_confidence: float = 1.0


def resolve_field(
    priorities: list[SourcePriority],
    sources: dict[str, dict[str, Any] | None],
    *,
    skip_values: frozenset[str] | None = None,
    default_value: Any = None,
    default_confidence: float = 0.1,
    default_source: str = "none",
) -> ResolvedField:
    """Resolve a field value from a priority chain of enrichment sources.

    Walks the priority list from highest to lowest priority. Returns
    the first non-null, non-skip value found, with its confidence
    capped at max_confidence.

    Args:
        priorities: Ordered list of SourcePriority entries (highest first).
        sources: Mapping of source_name to enrichment data dict (or None).
        skip_values: Values to treat as null (e.g., frozenset({"und", ""})).
        default_value: Fallback value if no source provides a valid value.
        default_confidence: Confidence for the default fallback.
        default_source: Source name for the default fallback.

    Returns:
        ResolvedField with the best available value, confidence, and source.
    """
    _skip = skip_values or frozenset()

    for rank, priority in enumerate(priorities, start=1):
        source_data = sources.get(priority.source_name)
        if source_data is None:
            continue

        value = source_data.get(priority.field_key)
        if value is None or value == "" or str(value) in _skip:
            continue

        # Use source-provided confidence if available, capped at max
        source_conf = source_data.get(f"{priority.field_key}_confidence")
        if source_conf is not None:
            confidence = min(float(source_conf), priority.max_confidence)
        else:
            confidence = priority.confidence

        return ResolvedField(
            value=value,
            confidence=confidence,
            source=priority.source_name,
            source_rank=rank,
        )

    return ResolvedField(
        value=default_value,
        confidence=default_confidence,
        source=default_source,
        source_rank=len(priorities) + 1,
    )


def resolve_language(
    sources: dict[str, dict[str, Any] | None],
    *,
    priorities: list[SourcePriority] | None = None,
) -> tuple[ResolvedField, ResolvedField]:
    """Resolve language and script fields from enrichment sources.

    Uses the standard 6-level priority chain unless custom priorities
    are provided.

    Args:
        sources: Mapping of source_name to enrichment data dict.
        priorities: Custom priority chain for language resolution.

    Returns:
        Tuple of (language_resolved, script_resolved).
    """
    default_priorities = [
        SourcePriority("parser_gt", "language_code", 0.95, 1.0),
        SourcePriority("train_gt", "iso639_language", 0.90, 0.95),
        SourcePriority("vlm", "iso639_language", 0.75, 0.80),
        SourcePriority("openlid", "language", 0.65, 0.70),
        SourcePriority("llm", "iso639_language", 0.65, 0.70),
        SourcePriority("dataset_doc", "iso639_language", 0.50, 1.0),
    ]
    lang_priorities = priorities or default_priorities

    lang_result = resolve_field(
        lang_priorities,
        sources,
        skip_values=frozenset({"und", ""}),
        default_value="und",
        default_confidence=0.1,
        default_source="none",
    )

    # Build script priorities matching the same sources
    script_key_map = {
        "parser_gt": "iso15924_script_code",
        "train_gt": "iso15924_script",
        "vlm": "iso15924_script",
        "openlid": "script",
        "llm": "iso15924_script",
        "dataset_doc": "iso15924_script",
    }

    # Try to get script from the same source that provided the language
    script_value = "Zyyy"
    if lang_result.source != "none":
        source_data = sources.get(lang_result.source)
        if source_data:
            script_key = script_key_map.get(lang_result.source, "iso15924_script")
            script_val = source_data.get(script_key)
            if script_val and script_val != "":
                script_value = script_val

    script_result = ResolvedField(
        value=script_value,
        confidence=lang_result.confidence,
        source=lang_result.source,
        source_rank=lang_result.source_rank,
    )

    return lang_result, script_result
