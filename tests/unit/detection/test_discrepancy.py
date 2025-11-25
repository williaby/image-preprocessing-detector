"""Unit tests for discrepancy analysis module (discrepancy.py).

Tests threshold configuration, discrepancy analysis logic, and helper functions.

Coverage targets:
- DiscrepancyThresholds configuration and accessor methods
- DiscrepancyAnalyzer escalation decision logic
- ClassicalScores and MLScores data models
- Helper functions and edge cases
"""

import pytest

from image_preprocessing_detector.detection.discrepancy import (
    ClassicalScores,
    DiscrepancyAnalyzer,
    DiscrepancyThresholds,
    EscalationReason,
    MLScores,
    ThresholdConfig,
    create_discrepancy_analyzer,
)


class TestDiscrepancyThresholds:
    """Unit tests for DiscrepancyThresholds configuration."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.blur.value == pytest.approx(0.25)
        assert thresholds.contrast.value == pytest.approx(0.30)
        assert thresholds.skew.value == pytest.approx(0.20)
        assert thresholds.noise.value == pytest.approx(0.35)
        assert thresholds.compression.value == pytest.approx(0.35)
        assert thresholds.illumination.value == pytest.approx(0.30)
        assert thresholds.aggregate_threshold == pytest.approx(0.25)
        assert thresholds.min_heads_exceeded == 1

    def test_get_threshold_valid_head(self) -> None:
        """Test get_threshold() for valid head names."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_threshold("blur") == pytest.approx(0.25)
        assert thresholds.get_threshold("contrast") == pytest.approx(0.30)
        assert thresholds.get_threshold("skew") == pytest.approx(0.20)
        assert thresholds.get_threshold("noise") == pytest.approx(0.35)
        assert thresholds.get_threshold("compression") == pytest.approx(0.35)
        assert thresholds.get_threshold("illumination") == pytest.approx(0.30)

    def test_get_threshold_invalid_head(self) -> None:
        """Test get_threshold() fallback for invalid head name."""
        thresholds = DiscrepancyThresholds()

        # Should return default fallback of 0.30
        assert thresholds.get_threshold("nonexistent_head") == pytest.approx(0.30)
        assert thresholds.get_threshold("invalid") == pytest.approx(0.30)

    def test_get_threshold_non_threshold_config_attribute(self) -> None:
        """Test get_threshold() with non-ThresholdConfig attribute."""
        thresholds = DiscrepancyThresholds()

        # aggregate_threshold is a float, not ThresholdConfig
        assert thresholds.get_threshold("aggregate_threshold") == pytest.approx(
            0.30
        )  # Fallback
        assert thresholds.get_threshold("min_heads_exceeded") == pytest.approx(
            0.30
        )  # Fallback

    def test_get_weight_valid_head(self) -> None:
        """Test get_weight() for valid head names."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_weight("blur") == pytest.approx(1.2)  # Higher weight
        assert thresholds.get_weight("contrast") == pytest.approx(1.0)
        assert thresholds.get_weight("skew") == pytest.approx(0.8)  # Lower weight
        assert thresholds.get_weight("noise") == pytest.approx(1.0)
        assert thresholds.get_weight("compression") == pytest.approx(0.9)
        assert thresholds.get_weight("illumination") == pytest.approx(1.0)

    def test_get_weight_invalid_head(self) -> None:
        """Test get_weight() fallback for invalid head name."""
        thresholds = DiscrepancyThresholds()

        # Should return default fallback of 1.0
        assert thresholds.get_weight("nonexistent") == pytest.approx(1.0)
        assert thresholds.get_weight("invalid_head") == pytest.approx(1.0)

    def test_get_rationale_valid_head(self) -> None:
        """Test get_rationale() for valid head names."""
        thresholds = DiscrepancyThresholds()

        blur_rationale = thresholds.get_rationale("blur")
        assert "blur detection is critical" in blur_rationale.lower()

        contrast_rationale = thresholds.get_rationale("contrast")
        assert "moderate threshold" in contrast_rationale.lower()

    def test_get_rationale_invalid_head(self) -> None:
        """Test get_rationale() fallback for invalid head name."""
        thresholds = DiscrepancyThresholds()

        # Should return default message
        assert (
            thresholds.get_rationale("nonexistent")
            == "No specific rationale documented."
        )
        assert (
            thresholds.get_rationale("invalid") == "No specific rationale documented."
        )


class TestClassicalScores:
    """Unit tests for ClassicalScores dataclass."""

    def test_default_scores(self) -> None:
        """Test default score values are all 1.0 (good quality)."""
        scores = ClassicalScores()

        assert scores.blur_score == pytest.approx(1.0)
        assert scores.contrast_score == pytest.approx(1.0)
        assert scores.skew_score == pytest.approx(1.0)
        assert scores.noise_score == pytest.approx(1.0)
        assert scores.compression_score == pytest.approx(1.0)
        assert scores.illumination_score == pytest.approx(1.0)
        assert scores.binarization_score == pytest.approx(1.0)
        assert scores.bleed_through_score == pytest.approx(1.0)

    def test_custom_scores(self) -> None:
        """Test creating ClassicalScores with custom values."""
        scores = ClassicalScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
            compression_score=0.75,
            illumination_score=0.85,
            binarization_score=0.95,
            bleed_through_score=0.5,
        )

        assert scores.blur_score == pytest.approx(0.8)
        assert scores.noise_score == pytest.approx(0.6)
        assert scores.bleed_through_score == pytest.approx(0.5)

    def test_to_dict(self) -> None:
        """Test to_dict() conversion."""
        scores = ClassicalScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
        )

        result = scores.to_dict()

        assert result["blur"] == pytest.approx(0.8)
        assert result["contrast"] == pytest.approx(0.7)
        assert result["skew"] == pytest.approx(0.9)
        assert result["noise"] == pytest.approx(0.6)
        assert result["compression"] == pytest.approx(1.0)  # Default
        assert "illumination" in result


class TestMLScores:
    """Unit tests for MLScores dataclass."""

    def test_default_scores(self) -> None:
        """Test default ML score values."""
        scores = MLScores()

        assert scores.blur_score == pytest.approx(1.0)
        assert scores.contrast_score == pytest.approx(1.0)
        assert scores.skew_score == pytest.approx(1.0)
        assert scores.noise_score == pytest.approx(1.0)
        assert scores.compression_score == pytest.approx(1.0)

    def test_to_dict(self) -> None:
        """Test to_dict() conversion."""
        scores = MLScores(
            blur_score=0.85,
            contrast_score=0.75,
            skew_score=0.95,
        )

        result = scores.to_dict()

        assert result["blur"] == pytest.approx(0.85)
        assert result["contrast"] == pytest.approx(0.75)
        assert result["skew"] == pytest.approx(0.95)
        assert "noise" in result
        assert "compression" in result


class TestDiscrepancyAnalyzer:
    """Unit tests for DiscrepancyAnalyzer escalation logic."""

    def test_init_default_thresholds(self) -> None:
        """Test analyzer initialization with default thresholds."""
        analyzer = DiscrepancyAnalyzer()

        assert analyzer.thresholds is not None
        assert isinstance(analyzer.thresholds, DiscrepancyThresholds)

    def test_init_custom_thresholds(self) -> None:
        """Test analyzer initialization with custom thresholds."""
        custom_thresholds = DiscrepancyThresholds(
            blur=ThresholdConfig(value=0.15, rationale="Custom", weight=1.0),
            aggregate_threshold=0.20,
        )
        analyzer = DiscrepancyAnalyzer(thresholds=custom_thresholds)

        assert analyzer.thresholds.blur.value == pytest.approx(0.15)
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.20)

    def test_analyze_no_discrepancy(self) -> None:
        """Test analyze() when scores are identical (no discrepancy)."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
            compression_score=0.85,
        )
        classical_scores = ClassicalScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
            compression_score=0.85,
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert not result.should_escalate
        assert result.num_heads_exceeded == 0
        assert result.max_discrepancy == pytest.approx(0.0)
        assert result.weighted_mean_discrepancy == pytest.approx(0.0)
        assert len(result.escalation_reasons) == 0

    def test_analyze_blur_exceeds_threshold(self) -> None:
        """Test analyze() when blur discrepancy exceeds threshold."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(blur_score=0.9)
        classical_scores = ClassicalScores(blur_score=0.6)  # creates high discrepancy

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.should_escalate
        assert result.num_heads_exceeded >= 1
        assert result.per_head_exceeded["blur"]
        assert EscalationReason.BLUR_DISCREPANCY in result.escalation_reasons
        assert result.per_head_discrepancies["blur"] == pytest.approx(0.3)

    def test_analyze_multiple_heads_exceed(self) -> None:
        """Test analyze() when multiple heads exceed thresholds."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(
            blur_score=0.9,  # exceeds blur threshold
            contrast_score=0.8,  # exceeds contrast threshold
            skew_score=0.9,  # exceeds skew threshold
        )
        classical_scores = ClassicalScores(
            blur_score=0.55,
            contrast_score=0.4,
            skew_score=0.6,
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.should_escalate
        assert result.num_heads_exceeded >= 2
        assert result.per_head_exceeded["blur"]
        assert result.per_head_exceeded["contrast"]
        assert result.per_head_exceeded["skew"]
        assert len(result.escalation_reasons) >= 3

    def test_analyze_aggregate_threshold_exceeded(self) -> None:
        """Test analyze() when weighted mean exceeds aggregate threshold."""
        # Create analyzer with low aggregate threshold
        thresholds = DiscrepancyThresholds(
            aggregate_threshold=0.15,  # Lower than default
        )
        analyzer = DiscrepancyAnalyzer(thresholds=thresholds)

        # Small discrepancies on all heads that don't individually exceed thresholds
        # but weighted mean is high
        ml_scores = MLScores(
            blur_score=0.8,
            contrast_score=0.75,
            skew_score=0.85,
            noise_score=0.7,
            compression_score=0.8,
        )
        classical_scores = ClassicalScores(
            blur_score=0.65,  # below individual blur threshold
            contrast_score=0.6,  # below individual contrast threshold
            skew_score=0.7,  # below individual skew threshold
            noise_score=0.55,  # below individual noise threshold
            compression_score=0.65,  # below individual compression threshold
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        # Should escalate due to aggregate threshold
        assert result.should_escalate
        assert EscalationReason.MULTIPLE_ISSUES in result.escalation_reasons

    def test_analyze_max_discrepancy_head(self) -> None:
        """Test analyze() correctly identifies head with max discrepancy."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(
            blur_score=0.9,
            contrast_score=0.95,  # Highest discrepancy
            skew_score=0.85,
        )
        classical_scores = ClassicalScores(
            blur_score=0.8,  # small discrepancy
            contrast_score=0.5,  # largest discrepancy
            skew_score=0.75,  # small discrepancy
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.max_discrepancy_head == "contrast"
        assert result.max_discrepancy == pytest.approx(0.45)

    def test_get_threshold_documentation(self) -> None:
        """Test get_threshold_documentation() returns complete docs."""
        analyzer = DiscrepancyAnalyzer()

        docs = analyzer.get_threshold_documentation()

        # Should have entries for all heads
        assert "blur" in docs
        assert "contrast" in docs
        assert "skew" in docs
        assert "noise" in docs
        assert "compression" in docs
        assert "illumination" in docs
        assert "aggregate" in docs

        # Check structure
        assert "threshold" in docs["blur"]
        assert "weight" in docs["blur"]
        assert "rationale" in docs["blur"]

        # Verify values
        assert docs["blur"]["threshold"] == pytest.approx(0.25)
        assert docs["blur"]["weight"] == pytest.approx(1.2)
        assert isinstance(docs["blur"]["rationale"], str)


class TestHelperFunctions:
    """Unit tests for convenience helper functions."""

    def test_create_discrepancy_analyzer_default(self) -> None:
        """Test create_discrepancy_analyzer() with default values."""
        analyzer = create_discrepancy_analyzer()

        assert analyzer.thresholds.blur.value == pytest.approx(0.25)
        assert analyzer.thresholds.contrast.value == pytest.approx(0.30)
        assert analyzer.thresholds.skew.value == pytest.approx(0.20)
        assert analyzer.thresholds.noise.value == pytest.approx(0.35)
        assert analyzer.thresholds.compression.value == pytest.approx(0.35)
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.25)

    def test_create_discrepancy_analyzer_custom(self) -> None:
        """Test create_discrepancy_analyzer() with custom thresholds."""
        analyzer = create_discrepancy_analyzer(
            blur_threshold=0.15,
            contrast_threshold=0.25,
            skew_threshold=0.10,
            noise_threshold=0.40,
            compression_threshold=0.30,
            aggregate_threshold=0.20,
        )

        assert analyzer.thresholds.blur.value == pytest.approx(0.15)
        assert analyzer.thresholds.contrast.value == pytest.approx(0.25)
        assert analyzer.thresholds.skew.value == pytest.approx(0.10)
        assert analyzer.thresholds.noise.value == pytest.approx(0.40)
        assert analyzer.thresholds.compression.value == pytest.approx(0.30)
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.20)

    def test_create_discrepancy_analyzer_weights_preserved(self) -> None:
        """Test create_discrepancy_analyzer() preserves weight settings."""
        analyzer = create_discrepancy_analyzer(blur_threshold=0.15)

        # Weights should be set according to importance
        assert analyzer.thresholds.blur.weight == pytest.approx(
            1.2
        )  # Higher (critical for OCR)
        assert analyzer.thresholds.contrast.weight == pytest.approx(1.0)
        assert analyzer.thresholds.skew.weight == pytest.approx(
            0.8
        )  # Lower (less critical)
