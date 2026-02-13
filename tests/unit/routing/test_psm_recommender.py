# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for PSM Recommender.

Tests cover:
- Each routing rule individually
- Priority ordering (higher-priority rules override lower ones)
- PSM values always in valid range 0-13
- Edge cases (all defaults, all flags True)
"""

from __future__ import annotations

import pytest

from image_preprocessing_detector.routing.psm_recommender import (
    PSMInput,
    PSMRecommendation,
    PSMRecommender,
    recommend_psm,
)

# Valid Tesseract PSM range
_PSM_MIN = 0
_PSM_MAX = 13


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def recommender() -> PSMRecommender:
    """Return a fresh PSMRecommender instance."""
    return PSMRecommender()


# =============================================================================
# Rule 1: Low orientation confidence → PSM 1
# =============================================================================


class TestLowOrientationConfidence:
    """Rule 1: orientation_confidence < 0.5 → PSM 1."""

    def test_low_orientation_returns_psm_1(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(orientation_confidence=0.3)
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_zero_orientation_returns_psm_1(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(orientation_confidence=0.0)
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_boundary_below_threshold(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(orientation_confidence=0.49)
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_boundary_at_threshold_does_not_trigger(
        self, recommender: PSMRecommender
    ) -> None:
        """orientation_confidence == 0.5 should NOT trigger rule 1."""
        inp = PSMInput(orientation_confidence=0.5)
        rec = recommender.recommend(inp)
        assert rec.psm != 1

    def test_reason_mentions_orientation(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(orientation_confidence=0.2)
        rec = recommender.recommend(inp)
        assert "orientation" in rec.reason.lower()


# =============================================================================
# Rule 2: Sparse text with few elements → PSM 11
# =============================================================================


class TestSparseText:
    """Rule 2: is_sparse and element_count < 5 → PSM 11."""

    def test_sparse_few_elements_returns_psm_11(
        self, recommender: PSMRecommender
    ) -> None:
        inp = PSMInput(is_sparse=True, element_count=3)
        rec = recommender.recommend(inp)
        assert rec.psm == 11

    def test_sparse_zero_elements(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(is_sparse=True, element_count=0)
        rec = recommender.recommend(inp)
        assert rec.psm == 11

    def test_sparse_at_threshold_does_not_trigger(
        self, recommender: PSMRecommender
    ) -> None:
        """element_count == 5 should NOT trigger rule 2."""
        inp = PSMInput(is_sparse=True, element_count=5)
        rec = recommender.recommend(inp)
        assert rec.psm != 11

    def test_not_sparse_few_elements_does_not_trigger(
        self, recommender: PSMRecommender
    ) -> None:
        """Both conditions required: is_sparse AND element_count < 5."""
        inp = PSMInput(is_sparse=False, element_count=2)
        rec = recommender.recommend(inp)
        assert rec.psm != 11

    def test_reason_mentions_sparse(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(is_sparse=True, element_count=1)
        rec = recommender.recommend(inp)
        assert "sparse" in rec.reason.lower()


# =============================================================================
# Rule 3: Tables present → PSM 6
# =============================================================================


class TestHasTables:
    """Rule 3: has_tables → PSM 6."""

    def test_tables_returns_psm_6(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(has_tables=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 6

    def test_reason_mentions_tables(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(has_tables=True)
        rec = recommender.recommend(inp)
        assert "table" in rec.reason.lower()


# =============================================================================
# Rule 4: Single-column layout → PSM 6
# =============================================================================


class TestSingleColumn:
    """Rule 4: layout_type == 'single_column' → PSM 6."""

    def test_single_column_returns_psm_6(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(layout_type="single_column")
        rec = recommender.recommend(inp)
        assert rec.psm == 6

    def test_reason_mentions_single_column(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(layout_type="single_column")
        rec = recommender.recommend(inp)
        assert "single" in rec.reason.lower()


# =============================================================================
# Rule 5: Multi-column layout → PSM 3
# =============================================================================


class TestMultiColumn:
    """Rule 5: layout_type == 'multi_column' → PSM 3."""

    def test_multi_column_returns_psm_3(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(layout_type="multi_column")
        rec = recommender.recommend(inp)
        assert rec.psm == 3

    def test_reason_mentions_multi_column(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(layout_type="multi_column")
        rec = recommender.recommend(inp)
        assert "multi" in rec.reason.lower()


# =============================================================================
# Rule 6: Handwriting present → PSM 6
# =============================================================================


class TestHasHandwriting:
    """Rule 6: has_handwriting → PSM 6."""

    def test_handwriting_returns_psm_6(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(has_handwriting=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 6

    def test_reason_mentions_handwriting(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(has_handwriting=True)
        rec = recommender.recommend(inp)
        assert "handwriting" in rec.reason.lower()


# =============================================================================
# Rule 7: Default → PSM 3
# =============================================================================


class TestDefault:
    """Rule 7: No conditions matched → PSM 3."""

    def test_all_defaults_returns_psm_3(self, recommender: PSMRecommender) -> None:
        inp = PSMInput()
        rec = recommender.recommend(inp)
        assert rec.psm == 3

    def test_unknown_layout_type_returns_default(
        self, recommender: PSMRecommender
    ) -> None:
        inp = PSMInput(layout_type="figure_dominant")
        rec = recommender.recommend(inp)
        assert rec.psm == 3

    def test_none_layout_type_returns_default(
        self, recommender: PSMRecommender
    ) -> None:
        inp = PSMInput(layout_type=None)
        rec = recommender.recommend(inp)
        assert rec.psm == 3


# =============================================================================
# Priority ordering
# =============================================================================


class TestPriorityOrdering:
    """Higher-priority rules must override lower-priority ones."""

    def test_low_orientation_overrides_sparse(
        self, recommender: PSMRecommender
    ) -> None:
        """Rule 1 (orientation) beats rule 2 (sparse)."""
        inp = PSMInput(
            orientation_confidence=0.2,
            is_sparse=True,
            element_count=2,
        )
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_low_orientation_overrides_tables(
        self, recommender: PSMRecommender
    ) -> None:
        """Rule 1 (orientation) beats rule 3 (tables)."""
        inp = PSMInput(orientation_confidence=0.1, has_tables=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_low_orientation_overrides_handwriting(
        self, recommender: PSMRecommender
    ) -> None:
        """Rule 1 (orientation) beats rule 6 (handwriting)."""
        inp = PSMInput(orientation_confidence=0.3, has_handwriting=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_sparse_overrides_tables(self, recommender: PSMRecommender) -> None:
        """Rule 2 (sparse) beats rule 3 (tables)."""
        inp = PSMInput(is_sparse=True, element_count=2, has_tables=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 11

    def test_sparse_overrides_single_column(self, recommender: PSMRecommender) -> None:
        """Rule 2 (sparse) beats rule 4 (single_column)."""
        inp = PSMInput(is_sparse=True, element_count=1, layout_type="single_column")
        rec = recommender.recommend(inp)
        assert rec.psm == 11

    def test_tables_overrides_single_column(self, recommender: PSMRecommender) -> None:
        """Rule 3 (tables) beats rule 4 (single_column)."""
        inp = PSMInput(has_tables=True, layout_type="single_column")
        rec = recommender.recommend(inp)
        assert rec.psm == 6
        assert "table" in rec.reason.lower()

    def test_tables_overrides_handwriting(self, recommender: PSMRecommender) -> None:
        """Rule 3 (tables) beats rule 6 (handwriting)."""
        inp = PSMInput(has_tables=True, has_handwriting=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 6
        assert "table" in rec.reason.lower()

    def test_single_column_overrides_handwriting(
        self, recommender: PSMRecommender
    ) -> None:
        """Rule 4 (single_column) beats rule 6 (handwriting)."""
        inp = PSMInput(layout_type="single_column", has_handwriting=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 6
        assert "single" in rec.reason.lower()

    def test_multi_column_overrides_handwriting(
        self, recommender: PSMRecommender
    ) -> None:
        """Rule 5 (multi_column) beats rule 6 (handwriting)."""
        inp = PSMInput(layout_type="multi_column", has_handwriting=True)
        rec = recommender.recommend(inp)
        assert rec.psm == 3


# =============================================================================
# PSM value range validation
# =============================================================================


class TestPSMValueRange:
    """All returned PSM values must be in [0, 13]."""

    @pytest.mark.parametrize(
        "inp",
        [
            PSMInput(),
            PSMInput(orientation_confidence=0.0),
            PSMInput(is_sparse=True, element_count=0),
            PSMInput(has_tables=True),
            PSMInput(layout_type="single_column"),
            PSMInput(layout_type="multi_column"),
            PSMInput(has_handwriting=True),
            PSMInput(layout_type="mixed"),
        ],
        ids=[
            "default",
            "low_orientation",
            "sparse",
            "tables",
            "single_column",
            "multi_column",
            "handwriting",
            "mixed_layout",
        ],
    )
    def test_psm_in_valid_range(
        self, recommender: PSMRecommender, inp: PSMInput
    ) -> None:
        rec = recommender.recommend(inp)
        assert _PSM_MIN <= rec.psm <= _PSM_MAX

    @pytest.mark.parametrize(
        "inp",
        [
            PSMInput(),
            PSMInput(orientation_confidence=0.0),
            PSMInput(is_sparse=True, element_count=0),
            PSMInput(has_tables=True),
            PSMInput(layout_type="single_column"),
            PSMInput(layout_type="multi_column"),
            PSMInput(has_handwriting=True),
        ],
        ids=[
            "default",
            "low_orientation",
            "sparse",
            "tables",
            "single_column",
            "multi_column",
            "handwriting",
        ],
    )
    def test_confidence_in_valid_range(
        self, recommender: PSMRecommender, inp: PSMInput
    ) -> None:
        rec = recommender.recommend(inp)
        assert 0.0 <= rec.confidence <= 1.0


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_all_flags_true(self, recommender: PSMRecommender) -> None:
        """When everything is flagged, highest-priority rule wins (low orient)."""
        inp = PSMInput(
            layout_type="single_column",
            has_tables=True,
            is_sparse=True,
            has_handwriting=True,
            orientation_confidence=0.1,
            element_count=2,
        )
        rec = recommender.recommend(inp)
        assert rec.psm == 1

    def test_all_flags_true_good_orientation(self, recommender: PSMRecommender) -> None:
        """All flags true but good orientation → sparse wins (rule 2)."""
        inp = PSMInput(
            layout_type="single_column",
            has_tables=True,
            is_sparse=True,
            has_handwriting=True,
            orientation_confidence=0.9,
            element_count=2,
        )
        rec = recommender.recommend(inp)
        assert rec.psm == 11

    def test_all_flags_true_many_elements(self, recommender: PSMRecommender) -> None:
        """All flags true, good orient, many elements → tables wins (rule 3)."""
        inp = PSMInput(
            layout_type="single_column",
            has_tables=True,
            is_sparse=True,
            has_handwriting=True,
            orientation_confidence=0.9,
            element_count=20,
        )
        rec = recommender.recommend(inp)
        assert rec.psm == 6
        assert "table" in rec.reason.lower()

    def test_recommendation_is_frozen_dataclass(
        self, recommender: PSMRecommender
    ) -> None:
        """PSMRecommendation is immutable."""
        rec = recommender.recommend(PSMInput())
        with pytest.raises(AttributeError):
            rec.psm = 99  # type: ignore[misc]

    def test_input_is_frozen_dataclass(self) -> None:
        """PSMInput is immutable."""
        inp = PSMInput()
        with pytest.raises(AttributeError):
            inp.has_tables = True  # type: ignore[misc]


# =============================================================================
# Module-level convenience function
# =============================================================================


class TestConvenienceFunction:
    """Test the module-level recommend_psm() function."""

    def test_returns_recommendation(self) -> None:
        rec = recommend_psm(PSMInput())
        assert isinstance(rec, PSMRecommendation)
        assert rec.psm == 3

    def test_matches_class_method(self, recommender: PSMRecommender) -> None:
        inp = PSMInput(has_tables=True, orientation_confidence=0.9)
        assert recommend_psm(inp).psm == recommender.recommend(inp).psm

    def test_low_orientation_via_convenience(self) -> None:
        rec = recommend_psm(PSMInput(orientation_confidence=0.2))
        assert rec.psm == 1
