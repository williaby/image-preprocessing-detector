"""Tests for reliability summary mixin."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.audit.integration.mixins.reliability_summary import (
    ReliabilitySummaryMixin,
    _classify_confidence,
)


@pytest.fixture
def mixin() -> ReliabilitySummaryMixin:
    """Create a ReliabilitySummaryMixin instance."""
    return ReliabilitySummaryMixin()


class TestClassifyConfidence:
    """Tests for _classify_confidence helper."""

    def test_hard_label(self) -> None:
        assert _classify_confidence(0.95) == "hard_label"
        assert _classify_confidence(0.90) == "hard_label"

    def test_soft_label(self) -> None:
        assert _classify_confidence(0.85) == "soft_label"
        assert _classify_confidence(0.70) == "soft_label"

    def test_active_learning(self) -> None:
        assert _classify_confidence(0.65) == "active_learning"
        assert _classify_confidence(0.50) == "active_learning"

    def test_unreliable(self) -> None:
        assert _classify_confidence(0.49) == "unreliable"
        assert _classify_confidence(0.0) == "unreliable"

    def test_boundary_values(self) -> None:
        assert _classify_confidence(0.9) == "hard_label"
        assert _classify_confidence(0.7) == "soft_label"
        assert _classify_confidence(0.5) == "active_learning"


class TestComputeReliabilitySummary:
    """Tests for compute_reliability_summary method."""

    def test_mixed_confidence_levels(
        self,
        mixin: ReliabilitySummaryMixin,
        sample_enrichment_data: dict[str, Any],
    ) -> None:
        result = mixin.compute_reliability_summary(sample_enrichment_data)
        assert result["assessed_field_count"] == 5
        assert result["min_confidence"] == 0.72
        assert result["min_confidence_field"] == "domain"
        assert result["min_confidence_category"] == "soft_label"
        assert "computed_at" in result

    def test_field_counts(
        self,
        mixin: ReliabilitySummaryMixin,
        sample_enrichment_data: dict[str, Any],
    ) -> None:
        result = mixin.compute_reliability_summary(sample_enrichment_data)
        # capture=0.95 (hard), domain=0.72 (soft), lang=0.88 (soft),
        # layout=0.85 (soft), content=0.90 (hard)
        assert result["hard_field_count"] == 2
        assert result["soft_field_count"] == 3

    def test_low_confidence_data(
        self,
        mixin: ReliabilitySummaryMixin,
        sample_enrichment_data_low_confidence: dict[str, Any],
    ) -> None:
        result = mixin.compute_reliability_summary(
            sample_enrichment_data_low_confidence
        )
        assert result["min_confidence"] == 0.0
        assert result["min_confidence_field"] == "layout_detections"
        assert result["min_confidence_category"] == "unreliable"

    def test_all_hard_labels(
        self,
        mixin: ReliabilitySummaryMixin,
    ) -> None:
        data = {
            "capture_confidence": 1.0,
            "domain_confidence": 0.95,
            "language_confidence": 0.92,
            "layout_confidence": 0.90,
            "content_flags_confidence": 0.98,
        }
        result = mixin.compute_reliability_summary(data)
        assert result["hard_field_count"] == 5
        assert result["soft_field_count"] == 0

    def test_none_confidence_treated_as_zero(
        self,
        mixin: ReliabilitySummaryMixin,
    ) -> None:
        data = {
            "capture_confidence": None,
            "domain_confidence": 0.8,
            "language_confidence": 0.9,
            "layout_confidence": 0.85,
            "content_flags_confidence": 0.95,
        }
        result = mixin.compute_reliability_summary(data)
        assert result["min_confidence"] == 0.0
        assert result["min_confidence_field"] == "capture_method"
        assert result["min_confidence_category"] == "unreliable"

    def test_missing_confidence_treated_as_zero(
        self,
        mixin: ReliabilitySummaryMixin,
    ) -> None:
        data: dict[str, Any] = {}
        result = mixin.compute_reliability_summary(data)
        assert result["min_confidence"] == 0.0
        assert result["assessed_field_count"] == 5

    def test_custom_field_defs(
        self,
        mixin: ReliabilitySummaryMixin,
    ) -> None:
        custom_defs = [
            ("custom_field", "custom_confidence"),
        ]
        data = {"custom_confidence": 0.88}
        result = mixin.compute_reliability_summary(data, field_defs=custom_defs)
        assert result["assessed_field_count"] == 1
        assert result["min_confidence_field"] == "custom_field"

    def test_field_summary_structure(
        self,
        mixin: ReliabilitySummaryMixin,
        sample_enrichment_data: dict[str, Any],
    ) -> None:
        result = mixin.compute_reliability_summary(sample_enrichment_data)
        summary = result["field_summary"]
        assert len(summary) == 5
        for field in summary:
            assert "field" in field
            assert "confidence" in field
            assert "category" in field
            assert "is_soft_label" in field

    def test_confidence_rounding(
        self,
        mixin: ReliabilitySummaryMixin,
    ) -> None:
        data = {
            "capture_confidence": 0.123456789,
            "domain_confidence": 0.9,
            "language_confidence": 0.9,
            "layout_confidence": 0.9,
            "content_flags_confidence": 0.9,
        }
        result = mixin.compute_reliability_summary(data)
        capture_field = next(
            f for f in result["field_summary"] if f["field"] == "capture_method"
        )
        assert capture_field["confidence"] == 0.1235
