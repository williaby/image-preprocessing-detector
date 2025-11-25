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

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.blur.value == 0.25
        assert thresholds.contrast.value == 0.30
        assert thresholds.skew.value == 0.20
        assert thresholds.noise.value == 0.35
        assert thresholds.compression.value == 0.35
        assert thresholds.illumination.value == 0.30
        assert thresholds.aggregate_threshold == 0.25
        assert thresholds.min_heads_exceeded == 1

    def test_get_threshold_valid_head(self):
        """Test get_threshold() for valid head names."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_threshold("blur") == 0.25
        assert thresholds.get_threshold("contrast") == 0.30
        assert thresholds.get_threshold("skew") == 0.20
        assert thresholds.get_threshold("noise") == 0.35
        assert thresholds.get_threshold("compression") == 0.35
        assert thresholds.get_threshold("illumination") == 0.30

    def test_get_threshold_invalid_head(self):
        """Test get_threshold() fallback for invalid head name."""
        thresholds = DiscrepancyThresholds()

        # Should return default fallback of 0.30
        assert thresholds.get_threshold("nonexistent_head") == 0.30
        assert thresholds.get_threshold("invalid") == 0.30

    def test_get_threshold_non_threshold_config_attribute(self):
        """Test get_threshold() with non-ThresholdConfig attribute."""
        thresholds = DiscrepancyThresholds()

        # aggregate_threshold is a float, not ThresholdConfig
        assert thresholds.get_threshold("aggregate_threshold") == 0.30  # Fallback
        assert thresholds.get_threshold("min_heads_exceeded") == 0.30  # Fallback

    def test_get_weight_valid_head(self):
        """Test get_weight() for valid head names."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_weight("blur") == 1.2  # Higher weight
        assert thresholds.get_weight("contrast") == 1.0
        assert thresholds.get_weight("skew") == 0.8  # Lower weight
        assert thresholds.get_weight("noise") == 1.0
        assert thresholds.get_weight("compression") == 0.9
        assert thresholds.get_weight("illumination") == 1.0

    def test_get_weight_invalid_head(self):
        """Test get_weight() fallback for invalid head name."""
        thresholds = DiscrepancyThresholds()

        # Should return default fallback of 1.0
        assert thresholds.get_weight("nonexistent") == 1.0
        assert thresholds.get_weight("invalid_head") == 1.0

    def test_get_rationale_valid_head(self):
        """Test get_rationale() for valid head names."""
        thresholds = DiscrepancyThresholds()

        blur_rationale = thresholds.get_rationale("blur")
        assert "blur detection is critical" in blur_rationale.lower()

        contrast_rationale = thresholds.get_rationale("contrast")
        assert "moderate threshold" in contrast_rationale.lower()

    def test_get_rationale_invalid_head(self):
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

    def test_default_scores(self):
        """Test default score values are all 1.0 (good quality)."""
        scores = ClassicalScores()

        assert scores.blur_score == 1.0
        assert scores.contrast_score == 1.0
        assert scores.skew_score == 1.0
        assert scores.noise_score == 1.0
        assert scores.compression_score == 1.0
        assert scores.illumination_score == 1.0
        assert scores.binarization_score == 1.0
        assert scores.bleed_through_score == 1.0

    def test_custom_scores(self):
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

        assert scores.blur_score == 0.8
        assert scores.noise_score == 0.6
        assert scores.bleed_through_score == 0.5

    def test_to_dict(self):
        """Test to_dict() conversion."""
        scores = ClassicalScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
        )

        result = scores.to_dict()

        assert result["blur"] == 0.8
        assert result["contrast"] == 0.7
        assert result["skew"] == 0.9
        assert result["noise"] == 0.6
        assert result["compression"] == 1.0  # Default
        assert "illumination" in result


class TestMLScores:
    """Unit tests for MLScores dataclass."""

    def test_default_scores(self):
        """Test default ML score values."""
        scores = MLScores()

        assert scores.blur_score == 1.0
        assert scores.contrast_score == 1.0
        assert scores.skew_score == 1.0
        assert scores.noise_score == 1.0
        assert scores.compression_score == 1.0

    def test_to_dict(self):
        """Test to_dict() conversion."""
        scores = MLScores(
            blur_score=0.85,
            contrast_score=0.75,
            skew_score=0.95,
        )

        result = scores.to_dict()

        assert result["blur"] == 0.85
        assert result["contrast"] == 0.75
        assert result["skew"] == 0.95
        assert "noise" in result
        assert "compression" in result


class TestDiscrepancyAnalyzer:
    """Unit tests for DiscrepancyAnalyzer escalation logic."""

    def test_init_default_thresholds(self):
        """Test analyzer initialization with default thresholds."""
        analyzer = DiscrepancyAnalyzer()

        assert analyzer.thresholds is not None
        assert isinstance(analyzer.thresholds, DiscrepancyThresholds)

    def test_init_custom_thresholds(self):
        """Test analyzer initialization with custom thresholds."""
        custom_thresholds = DiscrepancyThresholds(
            blur=ThresholdConfig(value=0.15, rationale="Custom", weight=1.0),
            aggregate_threshold=0.20,
        )
        analyzer = DiscrepancyAnalyzer(thresholds=custom_thresholds)

        assert analyzer.thresholds.blur.value == 0.15
        assert analyzer.thresholds.aggregate_threshold == 0.20

    def test_analyze_no_discrepancy(self):
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
        assert result.max_discrepancy == 0.0
        assert result.weighted_mean_discrepancy == 0.0
        assert len(result.escalation_reasons) == 0

    def test_analyze_blur_exceeds_threshold(self):
        """Test analyze() when blur discrepancy exceeds threshold."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(blur_score=0.9)
        classical_scores = ClassicalScores(blur_score=0.6)  # Discrepancy = 0.3 > 0.25

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.should_escalate
        assert result.num_heads_exceeded >= 1
        assert result.per_head_exceeded["blur"]
        assert EscalationReason.BLUR_DISCREPANCY in result.escalation_reasons
        assert result.per_head_discrepancies["blur"] == pytest.approx(0.3)

    def test_analyze_multiple_heads_exceed(self):
        """Test analyze() when multiple heads exceed thresholds."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(
            blur_score=0.9,  # Discrepancy = 0.35 > 0.25
            contrast_score=0.8,  # Discrepancy = 0.4 > 0.30
            skew_score=0.9,  # Discrepancy = 0.3 > 0.20
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

    def test_analyze_aggregate_threshold_exceeded(self):
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
            blur_score=0.65,  # Discrepancy = 0.15 < 0.25 (blur threshold)
            contrast_score=0.6,  # Discrepancy = 0.15 < 0.30
            skew_score=0.7,  # Discrepancy = 0.15 < 0.20
            noise_score=0.55,  # Discrepancy = 0.15 < 0.35
            compression_score=0.65,  # Discrepancy = 0.15 < 0.35
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        # Should escalate due to aggregate threshold
        assert result.should_escalate
        assert EscalationReason.MULTIPLE_ISSUES in result.escalation_reasons

    def test_analyze_max_discrepancy_head(self):
        """Test analyze() correctly identifies head with max discrepancy."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(
            blur_score=0.9,
            contrast_score=0.95,  # Highest discrepancy
            skew_score=0.85,
        )
        classical_scores = ClassicalScores(
            blur_score=0.8,  # Discrepancy = 0.1
            contrast_score=0.5,  # Discrepancy = 0.45 (max)
            skew_score=0.75,  # Discrepancy = 0.1
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.max_discrepancy_head == "contrast"
        assert result.max_discrepancy == pytest.approx(0.45)

    def test_get_threshold_documentation(self):
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
        assert docs["blur"]["threshold"] == 0.25
        assert docs["blur"]["weight"] == 1.2
        assert isinstance(docs["blur"]["rationale"], str)


class TestHelperFunctions:
    """Unit tests for convenience helper functions."""

    def test_create_discrepancy_analyzer_default(self):
        """Test create_discrepancy_analyzer() with default values."""
        analyzer = create_discrepancy_analyzer()

        assert analyzer.thresholds.blur.value == 0.25
        assert analyzer.thresholds.contrast.value == 0.30
        assert analyzer.thresholds.skew.value == 0.20
        assert analyzer.thresholds.noise.value == 0.35
        assert analyzer.thresholds.compression.value == 0.35
        assert analyzer.thresholds.aggregate_threshold == 0.25

    def test_create_discrepancy_analyzer_custom(self):
        """Test create_discrepancy_analyzer() with custom thresholds."""
        analyzer = create_discrepancy_analyzer(
            blur_threshold=0.15,
            contrast_threshold=0.25,
            skew_threshold=0.10,
            noise_threshold=0.40,
            compression_threshold=0.30,
            aggregate_threshold=0.20,
        )

        assert analyzer.thresholds.blur.value == 0.15
        assert analyzer.thresholds.contrast.value == 0.25
        assert analyzer.thresholds.skew.value == 0.10
        assert analyzer.thresholds.noise.value == 0.40
        assert analyzer.thresholds.compression.value == 0.30
        assert analyzer.thresholds.aggregate_threshold == 0.20

    def test_create_discrepancy_analyzer_weights_preserved(self):
        """Test create_discrepancy_analyzer() preserves weight settings."""
        analyzer = create_discrepancy_analyzer(blur_threshold=0.15)

        # Weights should be set according to importance
        assert analyzer.thresholds.blur.weight == 1.2  # Higher (critical for OCR)
        assert analyzer.thresholds.contrast.weight == 1.0
        assert analyzer.thresholds.skew.weight == 0.8  # Lower (less critical)
