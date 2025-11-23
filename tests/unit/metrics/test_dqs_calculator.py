"""Unit tests for DQS Calculator (Milestone 8.1).

Tests for:
- DQSWeightConfig: Configurable weight dataclass
- DQSCalibrator: Weight calibration and optimization
- Enhanced calculate_degradation_score with configurable weights
- Enhanced normalize_classical_iqa with NoiseDetectionResult support
"""

import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    NoiseDetectionResult,
    Severity,
)
from image_preprocessing_detector.metrics.dqs_calculator import (
    CalibrationResult,
    CalibrationSample,
    DQSCalibrator,
    DQSWeightConfig,
    calculate_degradation_score,
    calculate_pre_ocr_risk,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
)
from image_preprocessing_detector.schema import (
    DQSMetadata,
    LayoutType,
    PageLayoutSummary,
    PDFType,
)


class TestDQSWeightConfig:
    """Test DQSWeightConfig dataclass."""

    def test_default_initialization(self) -> None:
        """Test default weight values."""
        config = DQSWeightConfig()

        assert config.blur_weight == 0.30
        assert config.noise_weight == 0.25
        assert config.contrast_weight == 0.20
        assert config.illumination_weight == 0.15
        assert config.artifacts_weight == 0.10
        assert config.ml_blend_ratio == 0.30

    def test_custom_initialization(self) -> None:
        """Test custom weight values."""
        config = DQSWeightConfig(
            blur_weight=0.40,
            noise_weight=0.30,
            contrast_weight=0.15,
            illumination_weight=0.10,
            artifacts_weight=0.05,
            ml_blend_ratio=0.50,
        )

        assert config.blur_weight == 0.40
        assert config.noise_weight == 0.30
        assert config.ml_blend_ratio == 0.50

    def test_validate_success(self) -> None:
        """Test validation passes for valid config."""
        config = DQSWeightConfig()
        config.validate()  # Should not raise

    def test_validate_negative_weight(self) -> None:
        """Test validation fails for negative weights."""
        config = DQSWeightConfig(blur_weight=-0.1)

        with pytest.raises(ValueError, match="blur_weight must be non-negative"):
            config.validate()

    def test_validate_invalid_ml_blend_ratio(self) -> None:
        """Test validation fails for out-of-range ml_blend_ratio."""
        config = DQSWeightConfig(ml_blend_ratio=1.5)

        with pytest.raises(ValueError, match="ml_blend_ratio must be in"):
            config.validate()

    def test_validate_invalid_structural_base_score(self) -> None:
        """Test validation fails for invalid structural base score."""
        config = DQSWeightConfig()
        config.structural_base_scores[LayoutType.COMPLEX] = 1.5

        with pytest.raises(ValueError, match="structural_base_scores"):
            config.validate()

    def test_validate_negative_structural_feature_weight(self) -> None:
        """Test validation fails for negative structural feature weight."""
        config = DQSWeightConfig()
        config.structural_feature_weights["has_tables"] = -0.1

        with pytest.raises(ValueError, match="structural_feature_weights"):
            config.validate()

    def test_get_normalized_degradation_weights(self) -> None:
        """Test weight normalization."""
        config = DQSWeightConfig(
            blur_weight=0.4,
            noise_weight=0.3,
            contrast_weight=0.2,
            illumination_weight=0.05,
            artifacts_weight=0.05,
        )

        weights = config.get_normalized_degradation_weights()

        assert abs(sum(weights.values()) - 1.0) < 1e-9
        assert weights["blur"] == 0.4
        assert weights["noise"] == 0.3

    def test_get_normalized_degradation_weights_all_zero(self) -> None:
        """Test weight normalization with all zeros falls back to equal weights."""
        config = DQSWeightConfig(
            blur_weight=0,
            noise_weight=0,
            contrast_weight=0,
            illumination_weight=0,
            artifacts_weight=0,
        )

        weights = config.get_normalized_degradation_weights()

        # Should fall back to equal weights
        assert all(w == 0.2 for w in weights.values())

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = DQSWeightConfig()
        data = config.to_dict()

        assert "degradation_weights" in data
        assert "ml_blend_ratio" in data
        assert "structural_base_scores" in data
        assert "structural_feature_weights" in data
        assert "risk_weights" in data

        assert data["degradation_weights"]["blur"] == 0.30
        assert data["ml_blend_ratio"] == 0.30

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "degradation_weights": {
                "blur": 0.40,
                "noise": 0.35,
            },
            "ml_blend_ratio": 0.50,
        }

        config = DQSWeightConfig.from_dict(data)

        assert config.blur_weight == 0.40
        assert config.noise_weight == 0.35
        assert config.ml_blend_ratio == 0.50
        # Unspecified values should remain default
        assert config.contrast_weight == 0.20

    def test_roundtrip_to_from_dict(self) -> None:
        """Test roundtrip conversion to/from dict."""
        original = DQSWeightConfig(
            blur_weight=0.35,
            noise_weight=0.28,
            ml_blend_ratio=0.45,
        )

        data = original.to_dict()
        restored = DQSWeightConfig.from_dict(data)

        assert restored.blur_weight == original.blur_weight
        assert restored.noise_weight == original.noise_weight
        assert restored.ml_blend_ratio == original.ml_blend_ratio


class TestCalibrationSample:
    """Test CalibrationSample dataclass."""

    def test_initialization(self) -> None:
        """Test sample creation."""
        sample = CalibrationSample(
            sample_id="test1",
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.9,
            illumination_score=0.85,
            artifacts_score=0.95,
            ground_truth_quality=0.82,
        )

        assert sample.sample_id == "test1"
        assert sample.blur_score == 0.8
        assert sample.ground_truth_quality == 0.82
        assert sample.metadata == {}

    def test_with_metadata(self) -> None:
        """Test sample with metadata."""
        sample = CalibrationSample(
            sample_id="test2",
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.9,
            illumination_score=0.85,
            artifacts_score=0.95,
            ground_truth_quality=0.82,
            metadata={"source": "benchmark", "annotator": "expert1"},
        )

        assert sample.metadata["source"] == "benchmark"


class TestDQSCalibrator:
    """Test DQSCalibrator class."""

    def _create_samples(self, n: int = 10) -> list[CalibrationSample]:
        """Create synthetic calibration samples."""
        import random

        random.seed(42)
        samples = []

        for i in range(n):
            blur = random.uniform(0.5, 1.0)
            noise = random.uniform(0.5, 1.0)
            contrast = random.uniform(0.5, 1.0)
            illumination = random.uniform(0.5, 1.0)
            artifacts = random.uniform(0.8, 1.0)

            # Ground truth is a weighted combination (simulating human perception)
            ground_truth = (
                0.35 * blur
                + 0.30 * noise
                + 0.20 * contrast
                + 0.10 * illumination
                + 0.05 * artifacts
            )

            samples.append(
                CalibrationSample(
                    sample_id=f"sample_{i}",
                    blur_score=blur,
                    noise_score=noise,
                    contrast_score=contrast,
                    illumination_score=illumination,
                    artifacts_score=artifacts,
                    ground_truth_quality=ground_truth,
                )
            )

        return samples

    def test_initialization(self) -> None:
        """Test calibrator initialization."""
        calibrator = DQSCalibrator()

        assert calibrator.initial_config is not None
        assert calibrator.learning_rate == 0.01
        assert calibrator.max_iterations == 1000

    def test_initialization_custom(self) -> None:
        """Test calibrator with custom config."""
        config = DQSWeightConfig(blur_weight=0.40)
        calibrator = DQSCalibrator(
            initial_config=config,
            learning_rate=0.02,
            max_iterations=500,
        )

        assert calibrator.initial_config.blur_weight == 0.40
        assert calibrator.learning_rate == 0.02
        assert calibrator.max_iterations == 500

    def test_calibrate_empty_samples_raises(self) -> None:
        """Test calibration fails with empty samples."""
        calibrator = DQSCalibrator()

        with pytest.raises(ValueError, match="Cannot calibrate with empty"):
            calibrator.calibrate([])

    def test_calibrate_returns_result(self) -> None:
        """Test calibration returns valid result."""
        calibrator = DQSCalibrator(max_iterations=100)
        samples = self._create_samples(20)

        result = calibrator.calibrate(samples)

        assert isinstance(result, CalibrationResult)
        assert isinstance(result.optimized_config, DQSWeightConfig)
        assert result.initial_mae >= 0
        assert result.final_mae >= 0
        assert result.final_mae <= result.initial_mae  # Should improve or stay same
        assert result.num_samples == 20
        assert result.convergence_iterations > 0

    def test_calibrate_improves_mae(self) -> None:
        """Test calibration improves MAE on synthetic data."""
        # Create samples where ground truth follows specific weights
        samples = self._create_samples(50)

        # Start with wrong initial weights
        initial_config = DQSWeightConfig(
            blur_weight=0.1,
            noise_weight=0.1,
            contrast_weight=0.4,
            illumination_weight=0.3,
            artifacts_weight=0.1,
        )

        calibrator = DQSCalibrator(
            initial_config=initial_config,
            learning_rate=0.02,
            max_iterations=500,
        )

        result = calibrator.calibrate(samples)

        # Should improve significantly since initial weights were wrong
        assert result.final_mae < result.initial_mae

    def test_evaluate(self) -> None:
        """Test evaluation metrics."""
        calibrator = DQSCalibrator()
        samples = self._create_samples(20)

        metrics = calibrator.evaluate(samples)

        assert "mae" in metrics
        assert "rmse" in metrics
        assert "r_squared" in metrics
        assert metrics["mae"] >= 0
        assert metrics["rmse"] >= 0
        assert -1 <= metrics["r_squared"] <= 1

    def test_evaluate_empty_samples(self) -> None:
        """Test evaluation with empty samples returns zeros."""
        calibrator = DQSCalibrator()

        metrics = calibrator.evaluate([])

        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["r_squared"] == 0.0


class TestCalculateDegradationScoreWithConfig:
    """Test calculate_degradation_score with configurable weights."""

    def test_default_config(self) -> None:
        """Test calculation with default config."""
        classical_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }

        score = calculate_degradation_score(classical_iqa)

        # Default weights: blur=0.3, noise=0.25, contrast=0.2, illum=0.15, art=0.1
        expected = 0.3 * 0.8 + 0.25 * 0.7 + 0.2 * 0.6 + 0.15 * 0.9 + 0.1 * 0.95
        assert abs(score - expected) < 1e-6

    def test_custom_config(self) -> None:
        """Test calculation with custom config."""
        classical_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }

        config = DQSWeightConfig(
            blur_weight=0.5,
            noise_weight=0.2,
            contrast_weight=0.1,
            illumination_weight=0.1,
            artifacts_weight=0.1,
        )

        score = calculate_degradation_score(classical_iqa, config=config)

        # Custom weights: blur=0.5, noise=0.2, contrast=0.1, illum=0.1, art=0.1
        expected = 0.5 * 0.8 + 0.2 * 0.7 + 0.1 * 0.6 + 0.1 * 0.9 + 0.1 * 0.95
        assert abs(score - expected) < 1e-6

    def test_ml_blend_ratio(self) -> None:
        """Test ML IQA blending with configurable ratio."""
        classical_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }
        ml_iqa = {"overall_quality": 0.9}

        # Default 30% ML
        score_default = calculate_degradation_score(classical_iqa, ml_iqa=ml_iqa)

        # Custom 50% ML
        config = DQSWeightConfig(ml_blend_ratio=0.50)
        score_custom = calculate_degradation_score(
            classical_iqa, ml_iqa=ml_iqa, config=config
        )

        # Score with 50% ML should be different from 30% ML
        assert score_default != score_custom


class TestNormalizeClassicalIQAWithNoiseResult:
    """Test normalize_classical_iqa with NoiseDetectionResult support."""

    def test_with_noise_result(self) -> None:
        """Test normalization with NoiseDetectionResult."""
        blur_result = BlurDetectionResult(
            score=300.0,
            blur_score=0.85,
            is_blurred=False,
            severity=Severity.LOW,
            confidence=0.9,
        )
        contrast_result = ContrastDetectionResult(
            score=0.75,
            is_low_contrast=False,
            severity=Severity.LOW,
            confidence=0.85,
        )
        noise_result = NoiseDetectionResult(
            noise_sigma=5.0,
            noise_score=0.83,  # 1 - 5/30
            is_noisy=False,
            severity=Severity.LOW,
            confidence=0.9,
        )

        iqa = normalize_classical_iqa(
            blur_result=blur_result,
            contrast_result=contrast_result,
            noise_result=noise_result,
        )

        assert abs(iqa["noise_score"] - 0.83) < 1e-6  # From noise_result
        assert iqa["contrast_score"] == 0.75

    def test_noise_result_takes_precedence(self) -> None:
        """Test NoiseDetectionResult takes precedence over noise_score."""
        noise_result = NoiseDetectionResult(
            noise_sigma=5.0,
            noise_score=0.83,
            is_noisy=False,
            severity=Severity.LOW,
            confidence=0.9,
        )

        iqa = normalize_classical_iqa(
            noise_result=noise_result,
            noise_score=0.5,  # Should be ignored
        )

        # noise_result should take precedence
        assert abs(iqa["noise_score"] - 0.83) < 1e-6

    def test_blur_score_field_used_if_available(self) -> None:
        """Test blur_score field is used if available on BlurDetectionResult."""
        # Create a result with blur_score field
        blur_result = BlurDetectionResult(
            score=300.0,
            blur_score=0.75,  # Normalized score
            is_blurred=False,
            severity=Severity.LOW,
            confidence=0.9,
        )

        iqa = normalize_classical_iqa(blur_result=blur_result)

        assert iqa["blur_score"] == 0.75  # Should use blur_score, not score/200

    def test_defaults_without_detectors(self) -> None:
        """Test default values when no detectors provided."""
        iqa = normalize_classical_iqa()

        assert iqa["blur_score"] == 0.8  # Default
        assert iqa["contrast_score"] == 0.7  # Default
        assert iqa["noise_score"] == 0.85  # Default
        assert iqa["illumination_score"] == 0.9  # Default
        assert iqa["artifacts_score"] == 0.95  # Default


class TestCalculateStructuralComplexityWithConfig:
    """Test calculate_structural_complexity_score with config."""

    def test_with_custom_base_scores(self) -> None:
        """Test calculation with custom base scores."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.MULTI_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.4,
        )

        config = DQSWeightConfig()
        config.structural_base_scores[LayoutType.MULTI_COLUMN] = 0.6

        score = calculate_structural_complexity_score(layout, config=config)

        assert abs(score - 0.6) < 1e-6

    def test_with_custom_feature_weights(self) -> None:
        """Test calculation with custom feature weights."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=True,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.3,
        )

        config = DQSWeightConfig()
        config.structural_feature_weights["has_tables"] = 0.30

        score = calculate_structural_complexity_score(layout, config=config)

        # single_column (0.1) + tables (0.30)
        assert abs(score - 0.4) < 1e-6


class TestCalculatePreOCRRiskWithConfig:
    """Test calculate_pre_ocr_risk with config."""

    def test_with_custom_risk_weights(self) -> None:
        """Test risk calculation with custom weights."""
        dqs = DQSMetadata(degradation_score=0.5, structural_complexity_score=0.5)

        config = DQSWeightConfig(
            risk_degradation_weight=0.50,
            risk_complexity_weight=0.50,
        )

        risk = calculate_pre_ocr_risk(dqs, None, [], config=config)

        # (1 - 0.5) * 0.5 + 0.5 * 0.5 = 0.25 + 0.25 = 0.5
        assert abs(risk - 0.5) < 1e-6

    def test_with_custom_pdf_type_penalties(self) -> None:
        """Test risk calculation with custom PDF type penalties."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        config = DQSWeightConfig(
            risk_degradation_weight=0.0,
            risk_complexity_weight=0.0,
            risk_pdf_type_penalty_image_only=0.5,
        )

        risk = calculate_pre_ocr_risk(dqs, PDFType.IMAGE_ONLY, [], config=config)

        assert abs(risk - 0.5) < 1e-6

    def test_with_custom_handwriting_penalty(self) -> None:
        """Test risk calculation with custom handwriting penalty."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=True,
            complexity_score=0.2,
        )

        config = DQSWeightConfig(
            risk_degradation_weight=0.0,
            risk_complexity_weight=0.0,
            risk_handwriting_penalty=0.25,
        )

        risk = calculate_pre_ocr_risk(dqs, None, [layout], config=config)

        assert abs(risk - 0.25) < 1e-6
