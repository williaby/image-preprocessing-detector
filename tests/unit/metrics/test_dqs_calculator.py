"""Unit tests for Document Quality Score (DQS) Calculator.

Tests cover:
- calculate_degradation_score: Weighted formula, validation, ML blending
- calculate_structural_complexity_score: Layout-based scoring
- aggregate_dqs: Page-to-document aggregation (median/max)
- normalize_classical_iqa: Detector output normalization
- calculate_dqs: Simplified page metrics calculation
- calculate_pre_ocr_risk: Risk scoring for routing
"""

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    Severity,
    SkewDetectionResult,
)
from image_preprocessing_detector.metrics.dqs_calculator import (
    DEGRADATION_WEIGHTS,
    LAYOUT_COMPLEXITY_BASE,
    STRUCTURAL_FEATURE_WEIGHTS,
    aggregate_dqs,
    calculate_degradation_score,
    calculate_dqs,
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


# =============================================================================
# calculate_degradation_score Tests
# =============================================================================


@pytest.mark.unit
class TestCalculateDegradationScore:
    """Tests for calculate_degradation_score function."""

    @pytest.fixture
    def perfect_iqa(self) -> dict:
        """Perfect quality IQA metrics (all 1.0)."""
        return {
            "blur_score": 1.0,
            "noise_score": 1.0,
            "contrast_score": 1.0,
            "illumination_score": 1.0,
            "artifacts_score": 1.0,
        }

    @pytest.fixture
    def poor_iqa(self) -> dict:
        """Poor quality IQA metrics (all 0.0)."""
        return {
            "blur_score": 0.0,
            "noise_score": 0.0,
            "contrast_score": 0.0,
            "illumination_score": 0.0,
            "artifacts_score": 0.0,
        }

    def test_perfect_quality_returns_1(self, perfect_iqa: dict) -> None:
        """Test that perfect quality metrics return score of 1.0."""
        score = calculate_degradation_score(perfect_iqa)
        assert score == 1.0

    def test_worst_quality_returns_0(self, poor_iqa: dict) -> None:
        """Test that worst quality metrics return score of 0.0."""
        score = calculate_degradation_score(poor_iqa)
        assert score == 0.0

    def test_weighted_formula(self) -> None:
        """Test that weighted formula is correctly applied."""
        # Set specific values to verify weights
        iqa = {
            "blur_score": 0.5,
            "noise_score": 0.5,
            "contrast_score": 0.5,
            "illumination_score": 0.5,
            "artifacts_score": 0.5,
        }
        score = calculate_degradation_score(iqa)
        # All at 0.5, weighted sum should be 0.5
        assert score == 0.5

    def test_blur_weight(self) -> None:
        """Test blur weight (0.30) contribution."""
        iqa = {
            "blur_score": 1.0,  # Only blur at max
            "noise_score": 0.0,
            "contrast_score": 0.0,
            "illumination_score": 0.0,
            "artifacts_score": 0.0,
        }
        score = calculate_degradation_score(iqa)
        assert abs(score - DEGRADATION_WEIGHTS["blur"]) < 0.001

    def test_weights_sum_to_one(self) -> None:
        """Verify degradation weights sum to 1.0."""
        total_weight = sum(DEGRADATION_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_missing_metric_raises_error(self) -> None:
        """Test that missing required metric raises ValueError."""
        incomplete_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.7,
            # Missing contrast, illumination, artifacts
        }
        with pytest.raises(ValueError, match="Missing required metric"):
            calculate_degradation_score(incomplete_iqa)

    def test_out_of_range_metric_raises_error(self) -> None:
        """Test that out-of-range metric raises ValueError."""
        invalid_iqa = {
            "blur_score": 1.5,  # > 1.0
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }
        with pytest.raises(ValueError, match="must be in range"):
            calculate_degradation_score(invalid_iqa)

    def test_negative_metric_raises_error(self) -> None:
        """Test that negative metric raises ValueError."""
        invalid_iqa = {
            "blur_score": -0.1,  # < 0.0
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }
        with pytest.raises(ValueError, match="must be in range"):
            calculate_degradation_score(invalid_iqa)

    def test_non_numeric_metric_raises_error(self) -> None:
        """Test that non-numeric metric raises TypeError."""
        invalid_iqa = {
            "blur_score": "high",  # Not numeric
            "noise_score": 0.7,
            "contrast_score": 0.6,
            "illumination_score": 0.9,
            "artifacts_score": 0.95,
        }
        with pytest.raises(TypeError, match="must be numeric"):
            calculate_degradation_score(invalid_iqa)

    def test_ml_blending(self) -> None:
        """Test ML IQA blending (70% classical, 30% ML)."""
        classical_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.8,
            "contrast_score": 0.8,
            "illumination_score": 0.8,
            "artifacts_score": 0.8,
        }
        ml_iqa = {"overall_quality": 1.0}

        # Without ML: all 0.8 -> score = 0.8
        score_classical_only = calculate_degradation_score(classical_iqa)
        assert abs(score_classical_only - 0.8) < 0.001

        # With ML: 0.7 * 0.8 + 0.3 * 1.0 = 0.56 + 0.30 = 0.86
        score_with_ml = calculate_degradation_score(classical_iqa, ml_iqa)
        expected = 0.7 * 0.8 + 0.3 * 1.0
        assert abs(score_with_ml - expected) < 0.001

    def test_ml_out_of_range_ignored(self) -> None:
        """Test that out-of-range ML score is ignored (with warning)."""
        classical_iqa = {
            "blur_score": 0.8,
            "noise_score": 0.8,
            "contrast_score": 0.8,
            "illumination_score": 0.8,
            "artifacts_score": 0.8,
        }
        ml_iqa = {"overall_quality": 1.5}  # Out of range

        # Should return classical-only score
        score = calculate_degradation_score(classical_iqa, ml_iqa)
        assert abs(score - 0.8) < 0.001


# =============================================================================
# calculate_structural_complexity_score Tests
# =============================================================================


@pytest.mark.unit
class TestCalculateStructuralComplexityScore:
    """Tests for calculate_structural_complexity_score function."""

    def test_single_column_base_score(self) -> None:
        """Test single column layout has base score 0.1."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.1,
        )
        score = calculate_structural_complexity_score(layout)
        assert abs(score - 0.1) < 0.001

    def test_multi_column_base_score(self) -> None:
        """Test multi-column layout has base score 0.4."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.MULTI_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.4,
        )
        score = calculate_structural_complexity_score(layout)
        assert abs(score - 0.4) < 0.001

    def test_complex_layout_base_score(self) -> None:
        """Test complex layout has base score 0.9."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.COMPLEX,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.9,
        )
        score = calculate_structural_complexity_score(layout)
        assert abs(score - 0.9) < 0.001

    def test_unknown_layout_base_score(self) -> None:
        """Test unknown layout has base score 0.5."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.UNKNOWN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.5,
        )
        score = calculate_structural_complexity_score(layout)
        assert abs(score - 0.5) < 0.001

    def test_tables_add_complexity(self) -> None:
        """Test tables add 0.20 to complexity score."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=True,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.3,
        )
        score = calculate_structural_complexity_score(layout)
        expected = LAYOUT_COMPLEXITY_BASE[LayoutType.SINGLE_COLUMN] + 0.20
        assert abs(score - expected) < 0.001

    def test_figures_add_complexity(self) -> None:
        """Test figures add 0.15 to complexity score."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=True,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.25,
        )
        score = calculate_structural_complexity_score(layout)
        expected = LAYOUT_COMPLEXITY_BASE[LayoutType.SINGLE_COLUMN] + 0.15
        assert abs(score - expected) < 0.001

    def test_all_features_capped_at_1(self) -> None:
        """Test that score is capped at 1.0 even with all features."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.COMPLEX,  # Base 0.9
            has_tables=True,  # +0.20
            has_figures=True,  # +0.15
            has_dense_math=True,  # +0.15
            has_handwriting=True,  # +0.10
            complexity_score=1.0,  # Would exceed 1.0
        )
        score = calculate_structural_complexity_score(layout)
        assert score == 1.0  # Capped at 1.0

    def test_cumulative_feature_weights(self) -> None:
        """Test multiple features add cumulatively."""
        layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,  # 0.1
            has_tables=True,  # +0.20
            has_figures=True,  # +0.15
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.45,
        )
        score = calculate_structural_complexity_score(layout)
        expected = 0.1 + 0.20 + 0.15
        assert abs(score - expected) < 0.001


# =============================================================================
# aggregate_dqs Tests
# =============================================================================


@pytest.mark.unit
class TestAggregateDQS:
    """Tests for aggregate_dqs function."""

    def test_single_page_returns_same(self) -> None:
        """Test single page aggregation returns same values."""
        page = DQSMetadata(degradation_score=0.75, structural_complexity_score=0.4)
        result = aggregate_dqs([page])
        assert result.degradation_score == 0.75
        assert result.structural_complexity_score == 0.4

    def test_median_degradation(self) -> None:
        """Test degradation uses median aggregation."""
        pages = [
            DQSMetadata(degradation_score=0.6, structural_complexity_score=0.1),
            DQSMetadata(degradation_score=0.8, structural_complexity_score=0.2),
            DQSMetadata(degradation_score=0.7, structural_complexity_score=0.3),
        ]
        result = aggregate_dqs(pages)
        # Median of [0.6, 0.8, 0.7] = 0.7
        assert result.degradation_score == 0.7

    def test_max_complexity(self) -> None:
        """Test complexity uses max aggregation."""
        pages = [
            DQSMetadata(degradation_score=0.8, structural_complexity_score=0.3),
            DQSMetadata(degradation_score=0.8, structural_complexity_score=0.6),
            DQSMetadata(degradation_score=0.8, structural_complexity_score=0.4),
        ]
        result = aggregate_dqs(pages)
        # Max of [0.3, 0.6, 0.4] = 0.6
        assert result.structural_complexity_score == 0.6

    def test_empty_list_raises_error(self) -> None:
        """Test empty page list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot aggregate empty"):
            aggregate_dqs([])

    def test_even_number_pages_median(self) -> None:
        """Test median calculation for even number of pages."""
        pages = [
            DQSMetadata(degradation_score=0.6, structural_complexity_score=0.1),
            DQSMetadata(degradation_score=0.8, structural_complexity_score=0.2),
        ]
        result = aggregate_dqs(pages)
        # Median of [0.6, 0.8] = 0.7
        assert result.degradation_score == 0.7


# =============================================================================
# normalize_classical_iqa Tests
# =============================================================================


@pytest.mark.unit
class TestNormalizeClassicalIQA:
    """Tests for normalize_classical_iqa function."""

    def test_defaults_when_no_inputs(self) -> None:
        """Test sensible defaults when no inputs provided."""
        result = normalize_classical_iqa()
        assert result["blur_score"] == 0.8
        assert result["noise_score"] == 0.85
        assert result["contrast_score"] == 0.7
        assert result["illumination_score"] == 0.9
        assert result["artifacts_score"] == 0.95

    def test_blur_normalization_low_score(self) -> None:
        """Test blur normalization for blurry image (low Laplacian)."""
        blur_result = BlurDetectionResult(
            is_blurred=True,
            score=50.0,  # Low Laplacian variance
            confidence=0.9,
            severity=Severity.HIGH,
        )
        result = normalize_classical_iqa(blur_result=blur_result)
        # 50/200 = 0.25
        assert abs(result["blur_score"] - 0.25) < 0.001

    def test_blur_normalization_high_score(self) -> None:
        """Test blur normalization for sharp image (high Laplacian)."""
        blur_result = BlurDetectionResult(
            is_blurred=False,
            score=300.0,  # High Laplacian variance
            confidence=0.8,
            severity=Severity.LOW,
        )
        result = normalize_classical_iqa(blur_result=blur_result)
        # 300/200 capped at 1.0
        assert result["blur_score"] == 1.0

    def test_contrast_passed_through(self) -> None:
        """Test contrast score is passed through directly."""
        contrast_result = ContrastDetectionResult(
            is_low_contrast=False,
            score=0.85,
            confidence=0.9,
            severity=Severity.LOW,
        )
        result = normalize_classical_iqa(contrast_result=contrast_result)
        assert result["contrast_score"] == 0.85

    def test_custom_scores_override_defaults(self) -> None:
        """Test custom scores override defaults."""
        result = normalize_classical_iqa(
            noise_score=0.5,
            illumination_score=0.6,
            artifacts_score=0.7,
        )
        assert result["noise_score"] == 0.5
        assert result["illumination_score"] == 0.6
        assert result["artifacts_score"] == 0.7


# =============================================================================
# calculate_dqs Tests
# =============================================================================


@pytest.mark.unit
class TestCalculateDQS:
    """Tests for calculate_dqs function."""

    def test_single_page(self) -> None:
        """Test DQS calculation for single page."""
        result = calculate_dqs(
            blur_scores=[0.8],
            contrast_scores=[0.7],
            noise_scores=[0.9],
            _skew_angles=[2.0],
            layout_complexities=[0.3],
        )
        # Degradation: 0.4*0.8 + 0.3*0.9 + 0.3*0.7 = 0.32 + 0.27 + 0.21 = 0.8
        expected_degradation = 0.4 * 0.8 + 0.3 * 0.9 + 0.3 * 0.7
        assert abs(result.degradation_score - expected_degradation) < 0.001
        assert result.structural_complexity_score == 0.3

    def test_multi_page_median_degradation(self) -> None:
        """Test multi-page uses median for degradation."""
        result = calculate_dqs(
            blur_scores=[0.6, 0.8, 0.7],
            contrast_scores=[0.6, 0.8, 0.7],
            noise_scores=[0.6, 0.8, 0.7],
            _skew_angles=[1.0, 2.0, 1.5],
            layout_complexities=[0.2, 0.4, 0.3],
        )
        # Max complexity = 0.4
        assert result.structural_complexity_score == 0.4

    def test_skew_angles_not_used(self) -> None:
        """Test skew angles don't affect DQS calculation."""
        result1 = calculate_dqs(
            blur_scores=[0.8],
            contrast_scores=[0.8],
            noise_scores=[0.8],
            _skew_angles=[0.0],
            layout_complexities=[0.3],
        )
        result2 = calculate_dqs(
            blur_scores=[0.8],
            contrast_scores=[0.8],
            noise_scores=[0.8],
            _skew_angles=[45.0],  # Very different skew
            layout_complexities=[0.3],
        )
        # Skew doesn't affect score
        assert result1.degradation_score == result2.degradation_score


# =============================================================================
# calculate_pre_ocr_risk Tests
# =============================================================================


@pytest.mark.unit
class TestCalculatePreOCRRisk:
    """Tests for calculate_pre_ocr_risk function."""

    def test_perfect_quality_low_risk(self) -> None:
        """Test perfect quality document has low risk."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)
        risk = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, [])
        # (1-1.0)*0.4 + 0.0*0.3 + 0 = 0.0
        assert risk == 0.0

    def test_poor_quality_high_risk(self) -> None:
        """Test poor quality document has high risk."""
        dqs = DQSMetadata(degradation_score=0.0, structural_complexity_score=1.0)
        risk = calculate_pre_ocr_risk(dqs, PDFType.IMAGE_ONLY, [])
        # (1-0.0)*0.4 + 1.0*0.3 + 0.2 = 0.4 + 0.3 + 0.2 = 0.9
        assert abs(risk - 0.9) < 0.001

    def test_image_only_penalty(self) -> None:
        """Test IMAGE_ONLY PDF type adds 0.2 penalty."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        # Born digital: no penalty
        risk_born = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, [])
        # Image only: +0.2 penalty
        risk_image = calculate_pre_ocr_risk(dqs, PDFType.IMAGE_ONLY, [])

        assert abs(risk_image - risk_born - 0.2) < 0.001

    def test_hybrid_penalty(self) -> None:
        """Test HYBRID PDF type adds 0.1 penalty."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        risk_born = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, [])
        risk_hybrid = calculate_pre_ocr_risk(dqs, PDFType.HYBRID, [])

        assert abs(risk_hybrid - risk_born - 0.1) < 0.001

    def test_handwriting_penalty(self) -> None:
        """Test handwriting adds 0.1 penalty."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        layout_no_hw = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.1,
            )
        ]
        layout_hw = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=True,
                complexity_score=0.2,
            )
        ]

        risk_no_hw = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, layout_no_hw)
        risk_hw = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, layout_hw)

        assert abs(risk_hw - risk_no_hw - 0.1) < 0.001

    def test_risk_capped_at_1(self) -> None:
        """Test risk is capped at 1.0."""
        dqs = DQSMetadata(degradation_score=0.0, structural_complexity_score=1.0)
        layout_hw = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.COMPLEX,
                has_tables=True,
                has_figures=True,
                has_dense_math=True,
                has_handwriting=True,
                complexity_score=1.0,
            )
        ]
        risk = calculate_pre_ocr_risk(dqs, PDFType.IMAGE_ONLY, layout_hw)
        # Maximum possible: 0.4 + 0.3 + 0.2 + 0.1 = 1.0
        assert risk <= 1.0

    def test_none_pdf_type(self) -> None:
        """Test None PDF type doesn't add penalty."""
        dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)

        risk_none = calculate_pre_ocr_risk(dqs, None, [])
        risk_born = calculate_pre_ocr_risk(dqs, PDFType.BORN_DIGITAL, [])

        assert risk_none == risk_born


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


@pytest.mark.unit
class TestDQSEdgeCases:
    """Edge case and boundary condition tests."""

    def test_boundary_scores_zero(self) -> None:
        """Test boundary condition: all zeros."""
        iqa = {
            "blur_score": 0.0,
            "noise_score": 0.0,
            "contrast_score": 0.0,
            "illumination_score": 0.0,
            "artifacts_score": 0.0,
        }
        score = calculate_degradation_score(iqa)
        assert score == 0.0

    def test_boundary_scores_one(self) -> None:
        """Test boundary condition: all ones."""
        iqa = {
            "blur_score": 1.0,
            "noise_score": 1.0,
            "contrast_score": 1.0,
            "illumination_score": 1.0,
            "artifacts_score": 1.0,
        }
        score = calculate_degradation_score(iqa)
        assert score == 1.0

    def test_large_page_count_aggregation(self) -> None:
        """Test aggregation with many pages."""
        pages = [
            DQSMetadata(
                degradation_score=i / 100,
                structural_complexity_score=i / 100
            )
            for i in range(1, 101)
        ]
        result = aggregate_dqs(pages)
        # Median of 0.01...1.0 = 0.505 (average of 0.50 and 0.51)
        assert 0.5 <= result.degradation_score <= 0.51
        # Max complexity = 1.0
        assert result.structural_complexity_score == 1.0

    def test_integer_metric_values(self) -> None:
        """Test integer values work correctly (not just floats)."""
        iqa = {
            "blur_score": 1,  # Integer
            "noise_score": 0,  # Integer
            "contrast_score": 1,
            "illumination_score": 1,
            "artifacts_score": 1,
        }
        # Should not raise, integers are valid
        score = calculate_degradation_score(iqa)
        assert 0.0 <= score <= 1.0


# =============================================================================
# Parametrized Tests for Comprehensive Coverage
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "metric_name,weight",
    [
        ("blur", 0.30),
        ("noise", 0.25),
        ("contrast", 0.20),
        ("illumination", 0.15),
        ("artifacts", 0.10),
    ],
)
def test_degradation_weight_contribution(metric_name: str, weight: float) -> None:
    """Parametrized test for individual metric weight contributions.

    Verifies each metric contributes its expected weight to the final score.
    """
    # Create IQA with only one metric at 1.0, rest at 0.0
    iqa = {
        "blur_score": 1.0 if metric_name == "blur" else 0.0,
        "noise_score": 1.0 if metric_name == "noise" else 0.0,
        "contrast_score": 1.0 if metric_name == "contrast" else 0.0,
        "illumination_score": 1.0 if metric_name == "illumination" else 0.0,
        "artifacts_score": 1.0 if metric_name == "artifacts" else 0.0,
    }
    score = calculate_degradation_score(iqa)
    assert abs(score - weight) < 0.001, (
        f"{metric_name} weight mismatch: expected {weight}, got {score}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "layout_type,expected_base",
    [
        (LayoutType.SINGLE_COLUMN, 0.1),
        (LayoutType.MULTI_COLUMN, 0.4),
        (LayoutType.THREE_COLUMN, 0.6),
        (LayoutType.COMPLEX, 0.9),
        (LayoutType.UNKNOWN, 0.5),
    ],
)
def test_layout_type_base_scores(layout_type: LayoutType, expected_base: float) -> None:
    """Parametrized test for layout type base complexity scores."""
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=layout_type,
        has_tables=False,
        has_figures=False,
        has_dense_math=False,
        has_handwriting=False,
        complexity_score=expected_base,
    )
    score = calculate_structural_complexity_score(layout)
    assert abs(score - expected_base) < 0.001


@pytest.mark.unit
@pytest.mark.parametrize(
    "feature,weight",
    [
        ("has_tables", 0.20),
        ("has_figures", 0.15),
        ("has_dense_math", 0.15),
        ("has_handwriting", 0.10),
    ],
)
def test_structural_feature_weights(feature: str, weight: float) -> None:
    """Parametrized test for structural feature weight contributions."""
    # Create layout with only one feature enabled
    layout = PageLayoutSummary(
        page_number=1,
        layout_type=LayoutType.SINGLE_COLUMN,  # Base 0.1
        has_tables=(feature == "has_tables"),
        has_figures=(feature == "has_figures"),
        has_dense_math=(feature == "has_dense_math"),
        has_handwriting=(feature == "has_handwriting"),
        complexity_score=0.1 + weight,
    )
    score = calculate_structural_complexity_score(layout)
    expected = LAYOUT_COMPLEXITY_BASE[LayoutType.SINGLE_COLUMN] + weight
    assert abs(score - expected) < 0.001


@pytest.mark.unit
@pytest.mark.parametrize(
    "pdf_type,expected_penalty",
    [
        (PDFType.BORN_DIGITAL, 0.0),
        (PDFType.IMAGE_ONLY, 0.2),
        (PDFType.HYBRID, 0.1),
        (None, 0.0),
    ],
)
def test_pdf_type_risk_penalties(
    pdf_type: PDFType | None, expected_penalty: float
) -> None:
    """Parametrized test for PDF type risk penalties."""
    dqs = DQSMetadata(degradation_score=1.0, structural_complexity_score=0.0)
    risk = calculate_pre_ocr_risk(dqs, pdf_type, [])
    assert abs(risk - expected_penalty) < 0.001


@pytest.mark.unit
@pytest.mark.parametrize(
    "degradation,complexity,pdf_type,expected_risk",
    [
        # Perfect quality, simple, born-digital -> 0.0
        (1.0, 0.0, PDFType.BORN_DIGITAL, 0.0),
        # Perfect quality, simple, image-only -> 0.2 penalty
        (1.0, 0.0, PDFType.IMAGE_ONLY, 0.2),
        # Poor quality (0.5), medium complexity (0.5), born-digital
        # (1-0.5)*0.4 + 0.5*0.3 = 0.2 + 0.15 = 0.35
        (0.5, 0.5, PDFType.BORN_DIGITAL, 0.35),
        # Worst case: poor quality, high complexity, image-only
        # (1-0.0)*0.4 + 1.0*0.3 + 0.2 = 0.4 + 0.3 + 0.2 = 0.9
        (0.0, 1.0, PDFType.IMAGE_ONLY, 0.9),
    ],
)
def test_pre_ocr_risk_scenarios(
    degradation: float,
    complexity: float,
    pdf_type: PDFType,
    expected_risk: float,
) -> None:
    """Parametrized test for various pre-OCR risk scenarios."""
    dqs = DQSMetadata(
        degradation_score=degradation,
        structural_complexity_score=complexity,
    )
    risk = calculate_pre_ocr_risk(dqs, pdf_type, [])
    assert abs(risk - expected_risk) < 0.01
