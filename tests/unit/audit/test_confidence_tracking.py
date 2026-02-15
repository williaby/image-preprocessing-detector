"""Tests for confidence tracking mixin."""

from __future__ import annotations

import pytest

from scripts.audit.integration.mixins.confidence_tracking import (
    ConfidenceTrackingMixin,
    FieldConfidenceRecord,
    ResolvedField,
)


@pytest.fixture
def mixin() -> ConfidenceTrackingMixin:
    """Create a ConfidenceTrackingMixin instance."""
    return ConfidenceTrackingMixin()


class TestResolvedField:
    """Tests for ResolvedField dataclass."""

    def test_create_resolved_field(self) -> None:
        rf = ResolvedField(value="en", confidence=0.95, source="parser_gt")
        assert rf.value == "en"
        assert rf.confidence == 0.95
        assert rf.source == "parser_gt"
        assert rf.source_rank == 1

    def test_custom_source_rank(self) -> None:
        rf = ResolvedField(
            value="zh", confidence=0.65, source="llm_vision", source_rank=5
        )
        assert rf.source_rank == 5

    def test_immutability(self) -> None:
        rf = ResolvedField(value="en", confidence=0.95, source="parser_gt")
        with pytest.raises(AttributeError):
            rf.value = "zh"  # type: ignore[misc]


class TestFieldConfidenceRecord:
    """Tests for FieldConfidenceRecord."""

    def test_track_field(self) -> None:
        record = FieldConfidenceRecord()
        resolved = ResolvedField(value="en", confidence=0.95, source="parser_gt")
        record.track("iso639_language", resolved)
        assert record.get_confidence("iso639_language") == 0.95
        assert record.get_source("iso639_language") == "parser_gt"

    def test_get_confidence_untracked(self) -> None:
        record = FieldConfidenceRecord()
        assert record.get_confidence("nonexistent") == 0.0

    def test_get_source_untracked(self) -> None:
        record = FieldConfidenceRecord()
        assert record.get_source("nonexistent") == "none"

    def test_get_min_confidence(self) -> None:
        record = FieldConfidenceRecord()
        record.track("lang", ResolvedField("en", 0.95, "parser_gt"))
        record.track("domain", ResolvedField("SCI", 0.65, "llm_vision"))
        record.track("capture", ResolvedField("scanner", 1.0, "doc"))
        min_conf, min_field = record.get_min_confidence()
        assert min_conf == 0.65
        assert min_field == "domain"

    def test_get_min_confidence_empty(self) -> None:
        record = FieldConfidenceRecord()
        min_conf, min_field = record.get_min_confidence()
        assert min_conf == 0.0
        assert min_field == "none"

    def test_to_dict(self) -> None:
        record = FieldConfidenceRecord()
        record.track("lang", ResolvedField("en", 0.95, "parser_gt", source_rank=1))
        record.track("domain", ResolvedField("SCI", 0.65, "llm_vision", source_rank=3))
        result = record.to_dict()
        assert "lang" in result
        assert result["lang"]["value"] == "en"
        assert result["lang"]["confidence"] == 0.95
        assert result["lang"]["source"] == "parser_gt"
        assert result["lang"]["source_rank"] == 1
        assert result["domain"]["source_rank"] == 3

    def test_overwrite_field(self) -> None:
        record = FieldConfidenceRecord()
        record.track("lang", ResolvedField("en", 0.5, "llm"))
        record.track("lang", ResolvedField("zh", 0.9, "parser_gt"))
        assert record.get_confidence("lang") == 0.9
        assert record.fields["lang"].value == "zh"


class TestConfidenceTrackingMixin:
    """Tests for ConfidenceTrackingMixin."""

    def test_create_confidence_record(
        self,
        mixin: ConfidenceTrackingMixin,
    ) -> None:
        record = mixin.create_confidence_record()
        assert isinstance(record, FieldConfidenceRecord)
        assert len(record.fields) == 0

    def test_track_field(
        self,
        mixin: ConfidenceTrackingMixin,
    ) -> None:
        record = mixin.create_confidence_record()
        mixin.track_field(record, "language", "en", 0.95, "parser_gt")
        assert record.get_confidence("language") == 0.95
        assert record.get_source("language") == "parser_gt"

    def test_track_field_with_rank(
        self,
        mixin: ConfidenceTrackingMixin,
    ) -> None:
        record = mixin.create_confidence_record()
        mixin.track_field(record, "domain", "SCI", 0.65, "llm_vision", source_rank=4)
        result = record.to_dict()
        assert result["domain"]["source_rank"] == 4

    def test_get_confidence_summary(
        self,
        mixin: ConfidenceTrackingMixin,
    ) -> None:
        record = mixin.create_confidence_record()
        mixin.track_field(record, "language", "en", 0.95, "parser_gt")
        mixin.track_field(record, "domain", "SCI", 0.65, "llm_vision")
        mixin.track_field(record, "capture", "scanner", 1.0, "doc")

        summary = mixin.get_confidence_summary(record)
        assert summary["min_confidence"] == 0.65
        assert summary["min_confidence_field"] == "domain"
        assert summary["tracked_field_count"] == 3
        assert "fields" in summary
        assert len(summary["fields"]) == 3

    def test_get_confidence_summary_empty(
        self,
        mixin: ConfidenceTrackingMixin,
    ) -> None:
        record = mixin.create_confidence_record()
        summary = mixin.get_confidence_summary(record)
        assert summary["min_confidence"] == 0.0
        assert summary["tracked_field_count"] == 0
