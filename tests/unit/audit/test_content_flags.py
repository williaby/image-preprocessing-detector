"""Tests for content flags derivation mixin."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.audit.integration.mixins.content_flags import (
    ContentFlags,
    ContentFlagsMixin,
)


@pytest.fixture
def mixin() -> ContentFlagsMixin:
    """Create a ContentFlagsMixin instance."""
    return ContentFlagsMixin()


class TestDeriveContentFlags:
    """Tests for derive_content_flags method."""

    def test_detects_all_content_types(
        self,
        mixin: ContentFlagsMixin,
        sample_layout_detections_standardized: list[dict[str, Any]],
    ) -> None:
        flags = mixin.derive_content_flags(sample_layout_detections_standardized)
        assert flags["has_table"] is True
        assert flags["has_figure"] is True

    def test_detects_formula_and_code(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        detections = [
            {"class_name": "Formula", "confidence": 0.9},
            {"class_name": "Code", "confidence": 0.85},
        ]
        flags = mixin.derive_content_flags(detections)
        assert flags["has_formula"] is True
        assert flags["has_code"] is True
        assert flags["has_table"] is False
        assert flags["has_figure"] is False

    def test_empty_detections(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        flags = mixin.derive_content_flags([])
        assert flags["has_table"] is False
        assert flags["has_formula"] is False
        assert flags["has_figure"] is False
        assert flags["has_code"] is False

    def test_case_insensitive(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        detections = [
            {"class_name": "table", "confidence": 0.9},
            {"class_name": "FORMULA", "confidence": 0.8},
        ]
        flags = mixin.derive_content_flags(detections)
        assert flags["has_table"] is True
        assert flags["has_formula"] is True

    def test_canonical_class_key(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        detections = [
            {"canonical_class": "Table", "class_name": "tbl", "confidence": 0.9}
        ]
        flags = mixin.derive_content_flags(detections)
        assert flags["has_table"] is True

    def test_custom_class_sets(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        detections = [{"class_name": "DIAGRAM", "confidence": 0.9}]
        flags = mixin.derive_content_flags(
            detections, figure_classes=frozenset({"DIAGRAM"})
        )
        assert flags["has_figure"] is True

    def test_isolate_formula_detected(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        detections = [{"class_name": "Isolate_Formula", "confidence": 0.8}]
        flags = mixin.derive_content_flags(detections)
        assert flags["has_formula"] is True


class TestApplyVLMContentFlagOverrides:
    """Tests for apply_vlm_content_flag_overrides method."""

    def test_vlm_overrides_false_positive_table(
        self,
        mixin: ContentFlagsMixin,
        vlm_table_true_positives: frozenset[str],
    ) -> None:
        layout_flags = {
            "has_table": True,
            "has_formula": False,
            "has_figure": False,
            "has_code": False,
        }
        result = mixin.apply_vlm_content_flag_overrides(
            "sample_999",
            layout_flags,
            vlm_table_tp=vlm_table_true_positives,
        )
        assert result.has_table is False

    def test_vlm_confirms_true_positive_table(
        self,
        mixin: ContentFlagsMixin,
        vlm_table_true_positives: frozenset[str],
    ) -> None:
        layout_flags = {
            "has_table": True,
            "has_formula": False,
            "has_figure": False,
            "has_code": False,
        }
        result = mixin.apply_vlm_content_flag_overrides(
            "sample_001",
            layout_flags,
            vlm_table_tp=vlm_table_true_positives,
        )
        assert result.has_table is True

    def test_synthetic_handwriting_always_false(
        self,
        mixin: ContentFlagsMixin,
        vlm_handwriting_true_positives: frozenset[str],
    ) -> None:
        layout_flags = {
            "has_table": False,
            "has_formula": False,
            "has_figure": False,
            "has_code": False,
        }
        result = mixin.apply_vlm_content_flag_overrides(
            "sample_010",
            layout_flags,
            is_synthetic=True,
            vlm_handwriting_tp=vlm_handwriting_true_positives,
        )
        assert result.has_handwriting is False

    def test_non_synthetic_handwriting_vlm_confirmed(
        self,
        mixin: ContentFlagsMixin,
        vlm_handwriting_true_positives: frozenset[str],
    ) -> None:
        layout_flags = {
            "has_table": False,
            "has_formula": False,
            "has_figure": False,
            "has_code": False,
        }
        result = mixin.apply_vlm_content_flag_overrides(
            "sample_010",
            layout_flags,
            is_synthetic=False,
            vlm_handwriting_tp=vlm_handwriting_true_positives,
        )
        assert result.has_handwriting is True

    def test_no_vlm_sets_uses_layout_flags(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        layout_flags = {
            "has_table": True,
            "has_formula": True,
            "has_figure": True,
            "has_code": True,
        }
        result = mixin.apply_vlm_content_flag_overrides(
            "sample_001",
            layout_flags,
        )
        assert result.has_table is True
        assert result.has_formula is True
        assert result.has_figure is True
        assert result.has_code is True

    def test_result_metadata(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        layout_flags = {
            "has_table": False,
            "has_formula": False,
            "has_figure": False,
            "has_code": False,
        }
        result = mixin.apply_vlm_content_flag_overrides("sample_001", layout_flags)
        assert result.confidence == 0.95
        assert "vlm_corrected" in result.source


class TestContentFlagsDataclass:
    """Tests for ContentFlags dataclass."""

    def test_to_dict(self) -> None:
        flags = ContentFlags(
            has_table=True,
            has_code=True,
            source="test_source",
            confidence=0.90,
        )
        result = flags.to_dict()
        assert result["has_table"] is True
        assert result["has_formula"] is False
        assert result["has_code"] is True
        assert result["content_flags_source"] == "test_source"
        assert result["content_flags_confidence"] == 0.90
        assert result["content_flags_tier"] == "tier_2_model"
        assert result["handwriting_present"] is False

    def test_default_values(self) -> None:
        flags = ContentFlags()
        assert flags.has_table is False
        assert flags.has_formula is False
        assert flags.has_figure is False
        assert flags.has_code is False
        assert flags.has_handwriting is False
        assert flags.has_signature is False


class TestApplySyntheticOverrides:
    """Tests for apply_synthetic_overrides method."""

    def test_overrides_handwriting(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        flags = ContentFlags(has_handwriting=True, has_table=True)
        result = mixin.apply_synthetic_overrides(flags)
        assert result.has_handwriting is False
        assert result.has_table is True

    def test_preserves_other_flags(
        self,
        mixin: ContentFlagsMixin,
    ) -> None:
        flags = ContentFlags(
            has_table=True,
            has_formula=True,
            has_figure=True,
            has_code=True,
            has_handwriting=True,
        )
        result = mixin.apply_synthetic_overrides(flags)
        assert result.has_table is True
        assert result.has_formula is True
        assert result.has_figure is True
        assert result.has_code is True
        assert result.has_handwriting is False
