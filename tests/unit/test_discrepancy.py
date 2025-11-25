"""Unit tests for discrepancy threshold tuning (Milestone 4.9)."""

import pytest

from image_preprocessing_detector.detection.discrepancy import (
    ClassicalScoreAdapter,
    ClassicalScores,
    DiscrepancyAnalyzer,
    DiscrepancyResult,
    DiscrepancyThresholds,
    EscalationReason,
    MLScores,
    ThresholdConfig,
    create_discrepancy_analyzer,
)
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    IlluminationDetectionResult,
    IlluminationType,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    Severity,
    SkewDetectionResult,
)


class TestThresholdConfig:
    """Test ThresholdConfig named tuple."""

    def test_threshold_config_creation(self) -> None:
        """Test creating a ThresholdConfig."""
        config = ThresholdConfig(
            value=0.25,
            rationale="Test rationale",
            weight=1.2,
        )
        assert config.value == pytest.approx(0.25)
        assert config.rationale == "Test rationale"
        assert config.weight == pytest.approx(1.2)

    def test_threshold_config_default_weight(self) -> None:
        """Test default weight value."""
        config = ThresholdConfig(value=0.3, rationale="Test")
        assert config.weight == pytest.approx(1.0)


class TestDiscrepancyThresholds:
    """Test DiscrepancyThresholds dataclass."""

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

    def test_get_threshold(self) -> None:
        """Test get_threshold method."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_threshold("blur") == pytest.approx(0.25)
        assert thresholds.get_threshold("contrast") == pytest.approx(0.30)
        assert thresholds.get_threshold("unknown") == pytest.approx(
            0.30
        )  # Default fallback

    def test_get_weight(self) -> None:
        """Test get_weight method."""
        thresholds = DiscrepancyThresholds()

        assert thresholds.get_weight("blur") == pytest.approx(1.2)  # Higher weight
        assert thresholds.get_weight("skew") == pytest.approx(0.8)  # Lower weight
        assert thresholds.get_weight("unknown") == pytest.approx(
            1.0
        )  # Default fallback

    def test_get_rationale(self) -> None:
        """Test get_rationale method."""
        thresholds = DiscrepancyThresholds()

        rationale = thresholds.get_rationale("blur")
        assert "blur" in rationale.lower() or "OCR" in rationale

        unknown_rationale = thresholds.get_rationale("unknown")
        assert "No specific rationale" in unknown_rationale

    def test_custom_thresholds(self) -> None:
        """Test custom threshold configuration."""
        custom_blur = ThresholdConfig(
            value=0.15,
            rationale="Custom blur threshold",
            weight=1.5,
        )
        thresholds = DiscrepancyThresholds(blur=custom_blur)

        assert thresholds.get_threshold("blur") == pytest.approx(0.15)
        assert thresholds.get_weight("blur") == pytest.approx(1.5)


class TestClassicalScores:
    """Test ClassicalScores dataclass."""

    def test_default_scores(self) -> None:
        """Test default scores are all 1.0 (good quality)."""
        scores = ClassicalScores()

        assert scores.blur_score == pytest.approx(1.0)
        assert scores.contrast_score == pytest.approx(1.0)
        assert scores.skew_score == pytest.approx(1.0)
        assert scores.noise_score == pytest.approx(1.0)
        assert scores.compression_score == pytest.approx(1.0)
        assert scores.illumination_score == pytest.approx(1.0)

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        scores = ClassicalScores(blur_score=0.5, contrast_score=0.8)
        d = scores.to_dict()

        assert d["blur"] == pytest.approx(0.5)
        assert d["contrast"] == pytest.approx(0.8)
        assert "skew" in d


class TestMLScores:
    """Test MLScores dataclass."""

    def test_default_scores(self) -> None:
        """Test default ML scores."""
        scores = MLScores()

        assert scores.blur_score == pytest.approx(1.0)
        assert scores.contrast_score == pytest.approx(1.0)

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        scores = MLScores(blur_score=0.9, noise_score=0.7)
        d = scores.to_dict()

        assert d["blur"] == pytest.approx(0.9)
        assert d["noise"] == pytest.approx(0.7)


class TestClassicalScoreAdapter:
    """Test ClassicalScoreAdapter class."""

    def test_convert_blur_blurry(self) -> None:
        """Test blur conversion for blurry image."""
        adapter = ClassicalScoreAdapter()
        result = BlurDetectionResult(
            is_blurred=True,
            score=50.0,
            blur_score=0.3,  # Low blur_score for blurry image
            severity=Severity.HIGH,
            confidence=0.9,
        )

        score = adapter.convert_blur(result)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low for HIGH severity

    def test_convert_blur_sharp(self) -> None:
        """Test blur conversion for sharp image."""
        adapter = ClassicalScoreAdapter()
        result = BlurDetectionResult(
            is_blurred=False,
            score=800.0,  # High Laplacian variance = sharp
            blur_score=0.9,  # High blur_score for sharp image
            severity=Severity.LOW,
            confidence=0.9,
        )

        score = adapter.convert_blur(result)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high for sharp image

    def test_convert_contrast_low(self) -> None:
        """Test contrast conversion for low contrast image."""
        adapter = ClassicalScoreAdapter()
        result = ContrastDetectionResult(
            is_low_contrast=True,
            score=0.3,
            severity=Severity.MEDIUM,
            confidence=0.85,
        )

        score = adapter.convert_contrast(result)
        assert 0.0 <= score <= 1.0
        assert score < 0.7  # Should be reduced for medium severity

    def test_convert_skew(self) -> None:
        """Test skew conversion."""
        adapter = ClassicalScoreAdapter(skew_max_angle=10.0)

        # No skew
        result = SkewDetectionResult(
            is_skewed=False,
            angle=0.5,
            severity=Severity.LOW,
            confidence=0.9,
            method="hough",
        )
        score = adapter.convert_skew(result)
        assert score > 0.9  # Should be high for small angle

        # High skew
        result = SkewDetectionResult(
            is_skewed=True,
            angle=8.0,
            severity=Severity.HIGH,
            confidence=0.9,
            method="hough",
        )
        score = adapter.convert_skew(result)
        assert score < 0.3  # Should be low for large angle

    def test_convert_noise_noisy(self) -> None:
        """Test noise conversion for noisy image."""
        adapter = ClassicalScoreAdapter()
        result = NoiseDetectionResult(
            is_noisy=True,
            noise_sigma=25.0,
            noise_score=0.3,  # Low score for noisy image
            severity=Severity.HIGH,
            confidence=0.88,
        )

        score = adapter.convert_noise(result)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low for high severity

    def test_convert_illumination(self) -> None:
        """Test illumination conversion."""
        adapter = ClassicalScoreAdapter()
        result = IlluminationDetectionResult(
            has_issues=True,
            score=0.5,
            issue_type=IlluminationType.UNEVEN,
            confidence=0.85,
            severity=Severity.MEDIUM,
            uniformity=0.6,
            vignetting_ratio=0.1,
            shadow_ratio=0.15,
            hotspot_ratio=0.05,
        )

        score = adapter.convert_illumination(result)
        assert 0.0 <= score <= 1.0

    def test_convert_compression(self) -> None:
        """Test compression artifact conversion."""
        adapter = ClassicalScoreAdapter()
        result = JPEGBlockinessResult(
            has_artifacts=True,
            blockiness_score=0.6,
            compression_score=0.4,
            estimated_quality=50,
            confidence=0.9,
            severity=Severity.MEDIUM,
            horizontal_blockiness=0.5,
            vertical_blockiness=0.5,
        )

        score = adapter.convert_compression(result)
        assert 0.0 <= score <= 1.0

    def test_convert_to_scores_partial(self) -> None:
        """Test converting only some detector results."""
        adapter = ClassicalScoreAdapter()
        blur_result = BlurDetectionResult(
            is_blurred=False,
            score=500.0,
            blur_score=0.8,
            severity=Severity.LOW,
            confidence=0.9,
        )

        scores = adapter.convert_to_scores(blur_result=blur_result)

        # Only blur should be converted, others should be default 1.0
        assert scores.blur_score < 1.0 or scores.blur_score == pytest.approx(0.5)
        assert scores.contrast_score == pytest.approx(1.0)


class TestDiscrepancyAnalyzer:
    """Test DiscrepancyAnalyzer class."""

    def test_init_default_thresholds(self) -> None:
        """Test initialization with default thresholds."""
        analyzer = DiscrepancyAnalyzer()
        assert analyzer.thresholds is not None
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.25)

    def test_init_custom_thresholds(self) -> None:
        """Test initialization with custom thresholds."""
        thresholds = DiscrepancyThresholds(aggregate_threshold=0.5)
        analyzer = DiscrepancyAnalyzer(thresholds=thresholds)
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.5)

    def test_analyze_no_discrepancy(self) -> None:
        """Test analysis when scores are similar."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(blur_score=0.85, contrast_score=0.80, skew_score=0.90)
        classical_scores = ClassicalScores(
            blur_score=0.87, contrast_score=0.82, skew_score=0.88
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert isinstance(result, DiscrepancyResult)
        assert not result.should_escalate
        assert len(result.escalation_reasons) == 0
        assert result.max_discrepancy < 0.2

    def test_analyze_blur_discrepancy(self) -> None:
        """Test analysis when blur scores differ significantly."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(blur_score=0.90, contrast_score=0.80)
        classical_scores = ClassicalScores(blur_score=0.50, contrast_score=0.78)

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.should_escalate
        assert result.per_head_discrepancies["blur"] >= pytest.approx(0.25)
        assert result.per_head_exceeded["blur"] is True
        assert EscalationReason.BLUR_DISCREPANCY in result.escalation_reasons

    def test_analyze_multiple_discrepancies(self) -> None:
        """Test analysis when multiple heads have discrepancies."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores(blur_score=0.90, contrast_score=0.90, skew_score=0.90)
        classical_scores = ClassicalScores(
            blur_score=0.50, contrast_score=0.50, skew_score=0.50
        )

        result = analyzer.analyze(ml_scores, classical_scores)

        assert result.should_escalate
        assert result.num_heads_exceeded >= 3
        # Multiple per-head reasons should be present
        assert len(result.escalation_reasons) >= 3

    def test_analyze_result_attributes(self) -> None:
        """Test that DiscrepancyResult has all expected attributes."""
        analyzer = DiscrepancyAnalyzer()
        ml_scores = MLScores()
        classical_scores = ClassicalScores()

        result = analyzer.analyze(ml_scores, classical_scores)

        assert hasattr(result, "per_head_discrepancies")
        assert hasattr(result, "per_head_exceeded")
        assert hasattr(result, "weighted_mean_discrepancy")
        assert hasattr(result, "max_discrepancy")
        assert hasattr(result, "max_discrepancy_head")
        assert hasattr(result, "num_heads_exceeded")
        assert hasattr(result, "should_escalate")
        assert hasattr(result, "escalation_reasons")

    def test_get_threshold_documentation(self) -> None:
        """Test threshold documentation retrieval."""
        analyzer = DiscrepancyAnalyzer()
        docs = analyzer.get_threshold_documentation()

        assert "blur" in docs
        assert "threshold" in docs["blur"]
        assert "weight" in docs["blur"]
        assert "rationale" in docs["blur"]
        assert "aggregate" in docs


class TestCreateDiscrepancyAnalyzer:
    """Test convenience function."""

    def test_create_with_defaults(self) -> None:
        """Test creating analyzer with default thresholds."""
        analyzer = create_discrepancy_analyzer()

        assert isinstance(analyzer, DiscrepancyAnalyzer)
        assert analyzer.thresholds.get_threshold("blur") == pytest.approx(0.25)

    def test_create_with_custom_values(self) -> None:
        """Test creating analyzer with custom thresholds."""
        analyzer = create_discrepancy_analyzer(
            blur_threshold=0.15,
            contrast_threshold=0.40,
            aggregate_threshold=0.30,
        )

        assert analyzer.thresholds.get_threshold("blur") == pytest.approx(0.15)
        assert analyzer.thresholds.get_threshold("contrast") == pytest.approx(0.40)
        assert analyzer.thresholds.aggregate_threshold == pytest.approx(0.30)


class TestEscalationReason:
    """Test EscalationReason enum."""

    def test_enum_values(self) -> None:
        """Test enum has expected values."""
        assert EscalationReason.HIGH_UNCERTAINTY.value == "high_uncertainty"
        assert EscalationReason.BLUR_DISCREPANCY.value == "blur_discrepancy"
        assert EscalationReason.MULTIPLE_ISSUES.value == "multiple_issues"

    def test_enum_creation_from_string(self) -> None:
        """Test creating enum from string."""
        reason = EscalationReason("blur_discrepancy")
        assert reason == EscalationReason.BLUR_DISCREPANCY


class TestIntegration:
    """Integration tests for the full discrepancy workflow."""

    def test_full_workflow(self) -> None:
        """Test complete workflow from detector results to escalation decision."""
        # Simulate classical detector results
        blur_result = BlurDetectionResult(
            is_blurred=False,
            score=600.0,
            blur_score=0.85,
            severity=Severity.LOW,
            confidence=0.9,
        )
        contrast_result = ContrastDetectionResult(
            is_low_contrast=False, score=0.85, severity=Severity.LOW, confidence=0.9
        )
        skew_result = SkewDetectionResult(
            is_skewed=False,
            angle=0.5,
            severity=Severity.LOW,
            confidence=0.95,
            method="hough",
        )

        # Convert to normalized scores
        adapter = ClassicalScoreAdapter()
        classical_scores = adapter.convert_to_scores(
            blur_result=blur_result,
            contrast_result=contrast_result,
            skew_result=skew_result,
        )

        # Simulate ML scores (slightly different)
        ml_scores = MLScores(
            blur_score=0.70,  # Some discrepancy
            contrast_score=0.85,
            skew_score=0.95,
        )

        # Analyze discrepancy
        analyzer = DiscrepancyAnalyzer()
        result = analyzer.analyze(ml_scores, classical_scores)

        # Verify result structure
        assert isinstance(result, DiscrepancyResult)
        assert 0.0 <= result.max_discrepancy <= 1.0
        assert result.max_discrepancy_head in [
            "blur",
            "contrast",
            "skew",
            "noise",
            "compression",
        ]

    def test_threshold_documentation_completeness(self) -> None:
        """Test that all heads have documentation."""
        analyzer = DiscrepancyAnalyzer()
        docs = analyzer.get_threshold_documentation()

        expected_heads = [
            "blur",
            "contrast",
            "skew",
            "noise",
            "compression",
            "illumination",
        ]
        for head in expected_heads:
            assert head in docs
            assert "threshold" in docs[head]
            assert isinstance(docs[head]["threshold"], float)
            assert "rationale" in docs[head]
            assert len(docs[head]["rationale"]) > 0  # type: ignore[arg-type]
