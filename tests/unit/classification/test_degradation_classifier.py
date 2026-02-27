"""Unit tests for degradation severity classifier."""

from __future__ import annotations

import pytest

from image_preprocessing_detector.classification.degradation_classifier import (
    DegradationClassification,
    DegradationInput,
    DegradationSeverityClassifier,
    classify_degradation_severity,
)


@pytest.fixture
def classifier() -> DegradationSeverityClassifier:
    """Return a fresh classifier instance."""
    return DegradationSeverityClassifier()


# ---------------------------------------------------------------------------
# Camera capture always complex
# ---------------------------------------------------------------------------


class TestCameraAlwaysComplex:
    """Camera capture methods must always yield 'complex'."""

    @pytest.mark.parametrize(
        "method",
        ["camera_professional", "camera_smartphone"],
    )
    def test_camera_capture_is_complex(
        self, classifier: DegradationSeverityClassifier, method: str
    ) -> None:
        """Any camera capture method produces 'complex' regardless of other signals."""
        inp = DegradationInput(capture_method=method)
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert any("Camera capture" in r for r in result.reasons)

    def test_camera_with_additional_indicators(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Camera + extra indicators still complex with higher confidence."""
        inp = DegradationInput(
            capture_method="camera_smartphone",
            dqs_score=0.3,
            has_shadows=True,
            has_warping=True,
        )
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert result.indicator_count == 3
        assert result.confidence > 0.90


# ---------------------------------------------------------------------------
# Indicator-based classification
# ---------------------------------------------------------------------------


class TestIndicatorClassification:
    """Severity classification based on indicator count."""

    def test_low_dqs_and_shadows_is_complex(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Two severe indicators (low DQS + shadows) produce 'complex'."""
        inp = DegradationInput(dqs_score=0.3, has_shadows=True)
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert result.indicator_count == 2

    def test_warping_and_handwriting_is_complex(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Two severe indicators (warping + handwriting) produce 'complex'."""
        inp = DegradationInput(has_warping=True, has_handwriting=True)
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert result.indicator_count == 2

    def test_single_indicator_is_simple(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """One indicator alone is not enough for 'complex'."""
        inp = DegradationInput(has_shadows=True)
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 1

    def test_all_four_indicators_is_complex(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """All four severe indicators produce 'complex' with high confidence."""
        inp = DegradationInput(
            dqs_score=0.2,
            has_shadows=True,
            has_warping=True,
            has_handwriting=True,
        )
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert result.indicator_count == 4
        assert result.confidence >= 0.85


# ---------------------------------------------------------------------------
# Clean / default document
# ---------------------------------------------------------------------------


class TestCleanDocument:
    """Documents with no degradation signals."""

    def test_clean_document_is_simple(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Document with all defaults yields 'simple'."""
        inp = DegradationInput()
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0
        assert result.confidence >= 0.90

    def test_clean_document_reason(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Clean document should report no significant indicators."""
        inp = DegradationInput()
        result = classifier.classify(inp)

        assert any("No significant" in r for r in result.reasons)

    def test_born_digital_high_dqs_is_simple(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Born-digital document with good quality is simple."""
        inp = DegradationInput(
            capture_method="born_digital",
            dqs_score=0.85,
        )
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0

    def test_scanner_no_issues_is_simple(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Flatbed scanner with no degradation is simple."""
        inp = DegradationInput(
            capture_method="scanner_flatbed",
            dqs_score=0.7,
        )
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_all_none_defaults(self, classifier: DegradationSeverityClassifier) -> None:
        """All-None / default input produces 'simple' with zero indicators."""
        inp = DegradationInput(
            capture_method=None,
            dqs_score=None,
            has_shadows=False,
            has_warping=False,
            has_handwriting=False,
            has_bleed_through=False,
        )
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0

    def test_dqs_exactly_at_threshold(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """DQS == 0.5 is NOT below threshold, so not counted as severe."""
        inp = DegradationInput(dqs_score=0.5)
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0

    def test_dqs_just_below_threshold(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """DQS just below 0.5 counts as a severe indicator."""
        inp = DegradationInput(dqs_score=0.499)
        result = classifier.classify(inp)

        assert result.indicator_count == 1
        # One indicator alone is still simple
        assert result.severity == "simple"

    def test_bleed_through_not_counted_as_severe(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Bleed-through is noted in reasons but not in indicator_count."""
        inp = DegradationInput(has_bleed_through=True)
        result = classifier.classify(inp)

        assert result.indicator_count == 0
        assert result.severity == "simple"
        assert any("Bleed-through" in r for r in result.reasons)

    def test_bleed_through_plus_one_indicator_still_simple(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Bleed-through + one severe indicator stays simple (count == 1)."""
        inp = DegradationInput(has_bleed_through=True, has_shadows=True)
        result = classifier.classify(inp)

        assert result.indicator_count == 1
        assert result.severity == "simple"

    def test_unknown_capture_method(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Unknown capture method does not trigger camera gate."""
        inp = DegradationInput(capture_method="unknown")
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert result.indicator_count == 0


# ---------------------------------------------------------------------------
# Confidence values
# ---------------------------------------------------------------------------


class TestConfidence:
    """Confidence should reflect decision clarity."""

    def test_camera_high_confidence(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Camera capture yields high confidence (deterministic gate)."""
        inp = DegradationInput(capture_method="camera_smartphone")
        result = classifier.classify(inp)

        assert result.confidence >= 0.90

    def test_clean_document_high_confidence(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """No indicators yields high confidence."""
        inp = DegradationInput()
        result = classifier.classify(inp)

        assert result.confidence >= 0.90

    def test_borderline_lower_confidence(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Exactly two indicators (borderline complex) yields lower confidence."""
        inp = DegradationInput(has_shadows=True, has_warping=True)
        result = classifier.classify(inp)

        assert result.severity == "complex"
        assert result.confidence < 0.85

    def test_many_indicators_high_confidence(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Three+ indicators yields high confidence for complex."""
        inp = DegradationInput(
            dqs_score=0.2,
            has_shadows=True,
            has_warping=True,
            has_handwriting=True,
        )
        result = classifier.classify(inp)

        assert result.confidence >= 0.85

    def test_single_indicator_moderate_confidence(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """One indicator: simple, but confidence is not maximal."""
        inp = DegradationInput(has_handwriting=True)
        result = classifier.classify(inp)

        assert result.severity == "simple"
        assert 0.70 <= result.confidence <= 0.90

    def test_confidence_always_in_range(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Confidence must be in [0.5, 1.0] for all combinations."""
        inputs = [
            DegradationInput(),
            DegradationInput(capture_method="camera_smartphone"),
            DegradationInput(
                dqs_score=0.1,
                has_shadows=True,
                has_warping=True,
                has_handwriting=True,
                has_bleed_through=True,
            ),
            DegradationInput(dqs_score=0.49, has_bleed_through=True),
        ]
        for inp in inputs:
            result = classifier.classify(inp)
            assert 0.5 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Module-level classify_degradation_severity wrapper."""

    def test_convenience_matches_class(self) -> None:
        """Convenience function produces identical results to class method."""
        inp = DegradationInput(
            capture_method="camera_professional",
            dqs_score=0.3,
            has_shadows=True,
        )
        class_result = DegradationSeverityClassifier().classify(inp)
        func_result = classify_degradation_severity(inp)

        assert class_result.severity == func_result.severity
        assert class_result.reasons == func_result.reasons
        assert class_result.indicator_count == func_result.indicator_count
        assert class_result.confidence == func_result.confidence

    def test_convenience_simple_case(self) -> None:
        """Convenience function works for simple classification."""
        result = classify_degradation_severity(DegradationInput())

        assert result.severity == "simple"


# ---------------------------------------------------------------------------
# Dataclass immutability
# ---------------------------------------------------------------------------


class TestDataclassImmutability:
    """Frozen dataclasses should reject mutation."""

    def test_input_is_frozen(self) -> None:
        """DegradationInput rejects attribute assignment."""
        inp = DegradationInput()
        with pytest.raises(AttributeError):
            inp.has_shadows = True  # type: ignore[misc]

    def test_classification_is_frozen(self) -> None:
        """DegradationClassification rejects attribute assignment."""
        result = DegradationClassification()
        with pytest.raises(AttributeError):
            result.severity = "complex"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Reason messages
# ---------------------------------------------------------------------------


class TestReasonMessages:
    """Human-readable reasons should be populated correctly."""

    def test_low_dqs_reason_includes_score(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """Low DQS reason includes the actual score value."""
        inp = DegradationInput(dqs_score=0.35)
        result = classifier.classify(inp)

        dqs_reasons = [r for r in result.reasons if "quality score" in r.lower()]
        assert len(dqs_reasons) == 1
        assert "0.35" in dqs_reasons[0]

    def test_multiple_reasons_accumulated(
        self, classifier: DegradationSeverityClassifier
    ) -> None:
        """All active signals produce their own reason string."""
        inp = DegradationInput(
            capture_method="camera_smartphone",
            dqs_score=0.2,
            has_shadows=True,
            has_warping=True,
            has_handwriting=True,
            has_bleed_through=True,
        )
        result = classifier.classify(inp)

        # Camera + 4 indicators + bleed-through = 6 reasons
        assert len(result.reasons) == 6
