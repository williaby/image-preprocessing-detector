"""Discrepancy threshold tuning for student-classical IQA comparison.

This module implements milestone 4.9: Student vs classical discrepancy threshold tuning.

Key components:
- DiscrepancyThresholds: Per-head configurable thresholds with documented rationale
- ClassicalScoreAdapter: Converts classical detector outputs to normalized 0-1 scores
- EscalationRules: Comprehensive rules for teacher model escalation
- DiscrepancyAnalyzer: Main class for analyzing discrepancies and escalation decisions

Threshold Selection Rationale:
-----------------------------
The default thresholds are based on the following principles:

1. **Blur (0.25)**: Lower threshold because blur detection is critical for OCR quality.
   Laplacian variance is well-correlated with ML blur predictions, so smaller
   discrepancies are significant.

2. **Contrast (0.30)**: Moderate threshold. Histogram-based classical contrast
   and ML contrast may differ on textured images, allowing more tolerance.

3. **Skew (0.20)**: Lower threshold because skew angle estimation is precise
   with Hough transform. Large discrepancies indicate potential issues.

4. **Noise (0.35)**: Higher threshold. Wavelet-based noise estimation and ML
   noise detection use different methodologies, expecting some variance.

5. **Compression (0.35)**: Higher threshold. JPEG blockiness detection is
   sensitive to image characteristics and may differ from ML assessment.

6. **Illumination (0.30)**: Moderate threshold. Regional illumination analysis
   should correlate reasonably with ML predictions.

These thresholds should be refined through validation set calibration (Phase 10).
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, NamedTuple

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityResult,
    BleedThroughResult,
    BlurDetectionResult,
    ContrastDetectionResult,
    IlluminationDetectionResult,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    Severity,
    SkewDetectionResult,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class EscalationReason(StrEnum):
    """Reasons for escalating to teacher model."""

    HIGH_UNCERTAINTY = "high_uncertainty"
    LOW_CONFIDENCE = "low_confidence"
    BLUR_DISCREPANCY = "blur_discrepancy"
    CONTRAST_DISCREPANCY = "contrast_discrepancy"
    SKEW_DISCREPANCY = "skew_discrepancy"
    NOISE_DISCREPANCY = "noise_discrepancy"
    COMPRESSION_DISCREPANCY = "compression_discrepancy"
    ILLUMINATION_DISCREPANCY = "illumination_discrepancy"
    MULTIPLE_ISSUES = "multiple_issues"
    HIGH_RISK_DOCUMENT = "high_risk_document"


class ThresholdConfig(NamedTuple):
    """Configuration for a single discrepancy threshold.

    Attributes:
        value: Threshold value (0-1 scale)
        rationale: Documentation explaining why this threshold was chosen
        weight: Weight for aggregate discrepancy calculation (0-1)
    """

    value: float
    rationale: str
    weight: float = 1.0


@dataclass
class DiscrepancyThresholds:
    """Per-head configurable thresholds for discrepancy detection.

    Each threshold includes:
    - A numeric value (0-1 scale, where 1 = max discrepancy)
    - A documented rationale for the threshold selection
    - A weight for aggregate scoring

    Attributes:
        blur: Threshold for blur discrepancy (default: 0.25)
        contrast: Threshold for contrast discrepancy (default: 0.30)
        skew: Threshold for skew discrepancy (default: 0.20)
        noise: Threshold for noise discrepancy (default: 0.35)
        compression: Threshold for compression artifact discrepancy (default: 0.35)
        illumination: Threshold for illumination discrepancy (default: 0.30)
        aggregate_threshold: Threshold for weighted mean discrepancy (default: 0.25)
        min_heads_exceeded: Min number of heads exceeding threshold to escalate (default: 1)
    """

    blur: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.25,
            rationale=(
                "Lower threshold because blur detection is critical for OCR quality. "
                "Laplacian variance correlates well with ML blur predictions."
            ),
            weight=1.2,  # Higher weight - blur is critical for OCR
        )
    )
    contrast: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.30,
            rationale=(
                "Moderate threshold. Histogram-based classical contrast and ML "
                "contrast may differ on textured images."
            ),
            weight=1.0,
        )
    )
    skew: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.20,
            rationale=(
                "Lower threshold because Hough transform provides precise skew "
                "angle estimation. Large discrepancies indicate potential issues."
            ),
            weight=0.8,  # Lower weight - skew is less critical for IQA
        )
    )
    noise: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.35,
            rationale=(
                "Higher threshold. Wavelet-based noise estimation and ML noise "
                "detection use different methodologies."
            ),
            weight=1.0,
        )
    )
    compression: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.35,
            rationale=(
                "Higher threshold. JPEG blockiness detection is sensitive to "
                "image characteristics and may differ from ML assessment."
            ),
            weight=0.9,
        )
    )
    illumination: ThresholdConfig = field(
        default_factory=lambda: ThresholdConfig(
            value=0.30,
            rationale=(
                "Moderate threshold. Regional illumination analysis should "
                "correlate reasonably with ML predictions."
            ),
            weight=1.0,
        )
    )

    # Aggregate thresholds
    aggregate_threshold: float = 0.25
    min_heads_exceeded: int = 1

    def get_threshold(self, head_name: str) -> float:
        """Get threshold value for a specific head.

        Args:
            head_name: Name of the IQA head (blur, contrast, skew, etc.)

        Returns:
            Threshold value (0-1)
        """
        config = getattr(self, head_name, None)
        if config is None or not isinstance(config, ThresholdConfig):
            return 0.30  # Default fallback
        return float(config.value)

    def get_weight(self, head_name: str) -> float:
        """Get weight for a specific head.

        Args:
            head_name: Name of the IQA head

        Returns:
            Weight value (typically 0.5-1.5)
        """
        config = getattr(self, head_name, None)
        if config is None or not isinstance(config, ThresholdConfig):
            return 1.0  # Default fallback
        return float(config.weight)

    def get_rationale(self, head_name: str) -> str:
        """Get rationale for a specific head threshold.

        Args:
            head_name: Name of the IQA head

        Returns:
            Rationale string
        """
        config = getattr(self, head_name, None)
        if config is None or not isinstance(config, ThresholdConfig):
            return "No specific rationale documented."
        return str(config.rationale)


@dataclass
class ClassicalScores:
    """Normalized classical IQA scores (0-1 scale where 1=good quality).

    All scores are normalized to match the ML IQA output convention:
    - 0.0 = poor quality (blur, noise, artifacts present)
    - 1.0 = good quality (sharp, clean, no artifacts)

    Attributes:
        blur_score: Blur quality (1=sharp, 0=blurry)
        contrast_score: Contrast quality (1=good contrast, 0=low contrast)
        skew_score: Skew quality (1=straight, 0=highly skewed)
        noise_score: Noise quality (1=clean, 0=noisy)
        compression_score: Compression quality (1=clean, 0=artifacts)
        illumination_score: Illumination quality (1=uniform, 0=uneven)
        binarization_score: Binarization quality (1=good, 0=poor)
        bleed_through_score: Bleed-through quality (1=clean, 0=bleed-through)
    """

    blur_score: float = 1.0
    contrast_score: float = 1.0
    skew_score: float = 1.0
    noise_score: float = 1.0
    compression_score: float = 1.0
    illumination_score: float = 1.0
    binarization_score: float = 1.0
    bleed_through_score: float = 1.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "blur": self.blur_score,
            "contrast": self.contrast_score,
            "skew": self.skew_score,
            "noise": self.noise_score,
            "compression": self.compression_score,
            "illumination": self.illumination_score,
            "binarization": self.binarization_score,
            "bleed_through": self.bleed_through_score,
        }


class ClassicalScoreAdapter:
    """Converts classical detector outputs to normalized 0-1 scores.

    Normalization conventions:
    - All scores normalized to 0-1 where 1=good quality, 0=poor quality
    - Severity levels mapped to quality reduction factors
    - Boolean flags (is_blurred, is_skewed, etc.) used to invert quality

    Example:
        >>> adapter = ClassicalScoreAdapter()
        >>> blur_result = detect_blur(image)
        >>> contrast_result = detect_contrast(image)
        >>> classical_scores = adapter.convert_to_scores(
        ...     blur_result=blur_result,
        ...     contrast_result=contrast_result,
        ... )
    """

    # Severity to quality reduction mapping
    # Higher severity = lower quality score
    SEVERITY_FACTORS: ClassVar[dict[Severity, float]] = {
        Severity.LOW: 0.85,  # 15% quality reduction
        Severity.MEDIUM: 0.65,  # 35% quality reduction
        Severity.HIGH: 0.40,  # 60% quality reduction
        Severity.CRITICAL: 0.15,  # 85% quality reduction
    }

    def __init__(
        self,
        blur_score_scale: float = 1000.0,
        skew_max_angle: float = 10.0,
    ) -> None:
        """Initialize adapter.

        Args:
            blur_score_scale: Scale factor for normalizing Laplacian variance
            skew_max_angle: Maximum skew angle for normalization (degrees)
        """
        self.blur_score_scale = blur_score_scale
        self.skew_max_angle = skew_max_angle

    def _severity_to_quality(self, severity: Severity) -> float:
        """Convert severity level to quality score.

        Args:
            severity: Severity enum value

        Returns:
            Quality score (0-1)
        """
        return self.SEVERITY_FACTORS.get(severity, 1.0)

    def convert_blur(self, result: BlurDetectionResult) -> float:
        """Convert blur detection result to normalized score.

        Args:
            result: BlurDetectionResult from classical detector

        Returns:
            Normalized blur quality score (0=blurry, 1=sharp)
        """
        if result.is_blurred:
            # Use severity for quality estimation
            return self._severity_to_quality(result.severity)

        # Not blurred - calculate quality from Laplacian score
        # Higher Laplacian variance = sharper image
        # Typical range: 0-1000+, normalize to 0-1
        normalized = min(1.0, result.score / self.blur_score_scale)
        return float(np.clip(normalized, 0.0, 1.0))

    def convert_contrast(self, result: ContrastDetectionResult) -> float:
        """Convert contrast detection result to normalized score.

        Args:
            result: ContrastDetectionResult from classical detector

        Returns:
            Normalized contrast quality score (0=low contrast, 1=good contrast)
        """
        if result.is_low_contrast:
            return self._severity_to_quality(result.severity)

        # Use the contrast score directly (already 0-1 range)
        return float(np.clip(result.score, 0.0, 1.0))

    def convert_skew(self, result: SkewDetectionResult) -> float:
        """Convert skew detection result to normalized score.

        Args:
            result: SkewDetectionResult from classical detector

        Returns:
            Normalized skew quality score (0=highly skewed, 1=straight)
        """
        # Skew angle to quality: 0° = 1.0, max_angle = 0.0
        angle_abs = abs(result.angle)
        normalized = 1.0 - min(1.0, angle_abs / self.skew_max_angle)
        return float(np.clip(normalized, 0.0, 1.0))

    def convert_noise(self, result: NoiseDetectionResult) -> float:
        """Convert noise detection result to normalized score.

        Args:
            result: NoiseDetectionResult from classical detector

        Returns:
            Normalized noise quality score (0=noisy, 1=clean)
        """
        if result.is_noisy:
            return self._severity_to_quality(result.severity)

        # Invert noise score: higher noise score = lower quality
        # Noise score is typically 0-1 where higher = more noise
        return float(np.clip(1.0 - result.noise_score, 0.0, 1.0))

    def convert_illumination(self, result: IlluminationDetectionResult) -> float:
        """Convert illumination detection result to normalized score.

        Args:
            result: IlluminationDetectionResult from classical detector

        Returns:
            Normalized illumination quality score (0=uneven, 1=uniform)
        """
        if result.has_issues:
            return self._severity_to_quality(result.severity)

        # Use uniformity directly
        return float(np.clip(result.uniformity, 0.0, 1.0))

    def convert_compression(self, result: JPEGBlockinessResult) -> float:
        """Convert JPEG blockiness result to normalized score.

        Args:
            result: JPEGBlockinessResult from classical detector

        Returns:
            Normalized compression quality score (0=artifacts, 1=clean)
        """
        if result.has_artifacts:
            return self._severity_to_quality(result.severity)

        # Use compression score (higher = better quality)
        return float(np.clip(result.compression_score, 0.0, 1.0))

    def convert_binarization(self, result: BinarizationQualityResult) -> float:
        """Convert binarization quality result to normalized score.

        Args:
            result: BinarizationQualityResult from classical detector

        Returns:
            Normalized binarization quality score (0=poor, 1=good)
        """
        # Binarization score is already 0-1
        return float(np.clip(result.binarization_score, 0.0, 1.0))

    def convert_bleed_through(self, result: BleedThroughResult) -> float:
        """Convert bleed-through result to normalized score.

        Args:
            result: BleedThroughResult from classical detector

        Returns:
            Normalized bleed-through quality score (0=bleed-through, 1=clean)
        """
        if result.bleed_through_detected:
            # Invert severity: high severity = low quality
            return float(np.clip(1.0 - result.severity, 0.0, 1.0))

        # No bleed-through detected
        return 1.0

    def convert_to_scores(
        self,
        blur_result: BlurDetectionResult | None = None,
        contrast_result: ContrastDetectionResult | None = None,
        skew_result: SkewDetectionResult | None = None,
        noise_result: NoiseDetectionResult | None = None,
        illumination_result: IlluminationDetectionResult | None = None,
        compression_result: JPEGBlockinessResult | None = None,
        binarization_result: BinarizationQualityResult | None = None,
        bleed_through_result: BleedThroughResult | None = None,
    ) -> ClassicalScores:
        """Convert all classical detector outputs to normalized scores.

        Args:
            blur_result: BlurDetectionResult (optional)
            contrast_result: ContrastDetectionResult (optional)
            skew_result: SkewDetectionResult (optional)
            noise_result: NoiseDetectionResult (optional)
            illumination_result: IlluminationDetectionResult (optional)
            compression_result: JPEGBlockinessResult (optional)
            binarization_result: BinarizationQualityResult (optional)
            bleed_through_result: BleedThroughResult (optional)

        Returns:
            ClassicalScores with all normalized scores
        """
        scores = ClassicalScores()

        if blur_result is not None:
            scores.blur_score = self.convert_blur(blur_result)

        if contrast_result is not None:
            scores.contrast_score = self.convert_contrast(contrast_result)

        if skew_result is not None:
            scores.skew_score = self.convert_skew(skew_result)

        if noise_result is not None:
            scores.noise_score = self.convert_noise(noise_result)

        if illumination_result is not None:
            scores.illumination_score = self.convert_illumination(illumination_result)

        if compression_result is not None:
            scores.compression_score = self.convert_compression(compression_result)

        if binarization_result is not None:
            scores.binarization_score = self.convert_binarization(binarization_result)

        if bleed_through_result is not None:
            scores.bleed_through_score = self.convert_bleed_through(
                bleed_through_result
            )

        return scores


@dataclass
class DiscrepancyResult:
    """Result from discrepancy analysis.

    Attributes:
        per_head_discrepancies: Per-head discrepancy values (0-1)
        per_head_exceeded: Boolean flags for which heads exceeded threshold
        weighted_mean_discrepancy: Weighted mean of all discrepancies
        max_discrepancy: Maximum discrepancy across all heads
        max_discrepancy_head: Name of head with maximum discrepancy
        num_heads_exceeded: Number of heads exceeding their thresholds
        should_escalate: Whether to escalate to teacher model
        escalation_reasons: List of reasons for escalation
    """

    per_head_discrepancies: dict[str, float]
    per_head_exceeded: dict[str, bool]
    weighted_mean_discrepancy: float
    max_discrepancy: float
    max_discrepancy_head: str
    num_heads_exceeded: int
    should_escalate: bool
    escalation_reasons: list[EscalationReason]


@dataclass
class MLScores:
    """ML IQA scores for comparison (simplified interface).

    Attributes:
        blur_score: Blur quality (0=blurry, 1=sharp)
        contrast_score: Contrast quality (0=low, 1=good)
        skew_score: Skew quality (0=skewed, 1=straight)
        noise_score: Noise quality (0=noisy, 1=clean)
        compression_score: Compression quality (0=artifacts, 1=clean)
    """

    blur_score: float = 1.0
    contrast_score: float = 1.0
    skew_score: float = 1.0
    noise_score: float = 1.0
    compression_score: float = 1.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "blur": self.blur_score,
            "contrast": self.contrast_score,
            "skew": self.skew_score,
            "noise": self.noise_score,
            "compression": self.compression_score,
        }


def _calculate_head_discrepancy(
    head: str,
    ml_dict: dict[str, float],
    classical_dict: dict[str, float],
    thresholds: DiscrepancyThresholds,
) -> tuple[float, bool, float, float]:
    """Calculate discrepancy for a single head.

    Args:
        head: Head name (blur, contrast, etc.)
        ml_dict: ML scores dictionary
        classical_dict: Classical scores dictionary
        thresholds: Discrepancy thresholds configuration

    Returns:
        Tuple of (discrepancy, exceeded, weighted_discrepancy, weight)
    """
    ml_val = ml_dict.get(head, 1.0)
    classical_val = classical_dict.get(head, 1.0)

    discrepancy = abs(ml_val - classical_val)
    threshold = thresholds.get_threshold(head)
    exceeded = discrepancy >= threshold
    weight = thresholds.get_weight(head)
    weighted_discrepancy = discrepancy * weight

    return discrepancy, exceeded, weighted_discrepancy, weight


def _collect_escalation_reasons(
    per_head_exceeded: dict[str, bool],
    weighted_mean: float,
    thresholds: DiscrepancyThresholds,
) -> list[EscalationReason]:
    """Collect escalation reasons from discrepancy analysis.

    Args:
        per_head_exceeded: Per-head threshold exceeded flags
        weighted_mean: Weighted mean discrepancy
        thresholds: Discrepancy thresholds configuration

    Returns:
        List of escalation reasons
    """
    escalation_reasons: list[EscalationReason] = []

    # Rule 1: Any head exceeds threshold
    num_exceeded = sum(per_head_exceeded.values())
    if num_exceeded >= thresholds.min_heads_exceeded:
        for head, exceeded in per_head_exceeded.items():
            if exceeded:
                reason = EscalationReason(f"{head}_discrepancy")
                escalation_reasons.append(reason)

    # Rule 2: Weighted mean exceeds aggregate threshold
    if weighted_mean >= thresholds.aggregate_threshold:
        escalation_reasons.append(EscalationReason.MULTIPLE_ISSUES)

    return escalation_reasons


class DiscrepancyAnalyzer:
    """Analyzes discrepancies between ML student and classical IQA scores.

    Implements comprehensive escalation rules based on:
    1. Per-head discrepancy thresholds (configurable)
    2. Weighted aggregate discrepancy
    3. Number of heads exceeding thresholds

    Example:
        >>> analyzer = DiscrepancyAnalyzer()
        >>> result = analyzer.analyze(ml_scores, classical_scores)
        >>> if result.should_escalate:
        ...     print(f"Escalate: {result.escalation_reasons}")
    """

    def __init__(
        self,
        thresholds: DiscrepancyThresholds | None = None,
    ) -> None:
        """Initialize discrepancy analyzer.

        Args:
            thresholds: Custom thresholds (default: DiscrepancyThresholds())
        """
        self.thresholds = thresholds or DiscrepancyThresholds()

    def analyze(
        self,
        ml_scores: MLScores,
        classical_scores: ClassicalScores,
    ) -> DiscrepancyResult:
        """Analyze discrepancies between ML and classical scores.

        Args:
            ml_scores: ML IQA scores (from student model)
            classical_scores: Classical IQA scores (normalized)

        Returns:
            DiscrepancyResult with analysis details
        """
        ml_dict = ml_scores.to_dict()
        classical_dict = classical_scores.to_dict()
        compare_heads = ["blur", "contrast", "skew", "noise", "compression"]

        # Calculate per-head discrepancies using helper
        per_head_discrepancies: dict[str, float] = {}
        per_head_exceeded: dict[str, bool] = {}
        weighted_discrepancies: list[float] = []
        weights: list[float] = []

        for head in compare_heads:
            discrepancy, exceeded, weighted_disc, weight = _calculate_head_discrepancy(
                head, ml_dict, classical_dict, self.thresholds
            )
            per_head_discrepancies[head] = discrepancy
            per_head_exceeded[head] = exceeded
            weighted_discrepancies.append(weighted_disc)
            weights.append(weight)

        # Calculate aggregate metrics
        total_weight = sum(weights) if weights else 1.0
        weighted_mean = sum(weighted_discrepancies) / total_weight if weights else 0.0
        max_discrepancy = (
            max(per_head_discrepancies.values()) if per_head_discrepancies else 0.0
        )
        max_head = (
            max(per_head_discrepancies, key=lambda k: per_head_discrepancies[k])
            if per_head_discrepancies
            else ""
        )
        num_exceeded = sum(per_head_exceeded.values())

        # Collect escalation reasons using helper
        escalation_reasons = _collect_escalation_reasons(
            per_head_exceeded, weighted_mean, self.thresholds
        )
        should_escalate = len(escalation_reasons) > 0

        if should_escalate:
            logger.info(
                "Discrepancy escalation triggered",
                max_discrepancy=f"{max_discrepancy:.3f}",
                max_head=max_head,
                num_exceeded=num_exceeded,
                reasons=[r.value for r in escalation_reasons],
            )
        else:
            logger.debug(
                "No discrepancy escalation",
                max_discrepancy=f"{max_discrepancy:.3f}",
                weighted_mean=f"{weighted_mean:.3f}",
            )

        return DiscrepancyResult(
            per_head_discrepancies=per_head_discrepancies,
            per_head_exceeded=per_head_exceeded,
            weighted_mean_discrepancy=weighted_mean,
            max_discrepancy=max_discrepancy,
            max_discrepancy_head=max_head,
            num_heads_exceeded=num_exceeded,
            should_escalate=should_escalate,
            escalation_reasons=escalation_reasons,
        )

    def get_threshold_documentation(self) -> dict[str, dict[str, str | float | int]]:
        """Get documentation for all threshold settings.

        Returns:
            Dictionary with threshold values, rationales, and weights
        """
        heads = ["blur", "contrast", "skew", "noise", "compression", "illumination"]
        docs: dict[str, dict[str, str | float | int]] = {}

        for head in heads:
            docs[head] = {
                "threshold": self.thresholds.get_threshold(head),
                "weight": self.thresholds.get_weight(head),
                "rationale": self.thresholds.get_rationale(head),
            }

        docs["aggregate"] = {
            "threshold": self.thresholds.aggregate_threshold,
            "min_heads_exceeded": self.thresholds.min_heads_exceeded,
            "rationale": (
                "Aggregate threshold catches cases where multiple heads have "
                "moderate discrepancies that individually wouldn't trigger escalation."
            ),
        }

        return docs


# Convenience functions
def create_discrepancy_analyzer(
    blur_threshold: float = 0.25,
    contrast_threshold: float = 0.30,
    skew_threshold: float = 0.20,
    noise_threshold: float = 0.35,
    compression_threshold: float = 0.35,
    aggregate_threshold: float = 0.25,
) -> DiscrepancyAnalyzer:
    """Create a discrepancy analyzer with custom thresholds.

    Args:
        blur_threshold: Threshold for blur discrepancy
        contrast_threshold: Threshold for contrast discrepancy
        skew_threshold: Threshold for skew discrepancy
        noise_threshold: Threshold for noise discrepancy
        compression_threshold: Threshold for compression discrepancy
        aggregate_threshold: Threshold for weighted mean discrepancy

    Returns:
        Configured DiscrepancyAnalyzer
    """
    thresholds = DiscrepancyThresholds(
        blur=ThresholdConfig(
            value=blur_threshold,
            rationale="Custom blur threshold",
            weight=1.2,
        ),
        contrast=ThresholdConfig(
            value=contrast_threshold,
            rationale="Custom contrast threshold",
            weight=1.0,
        ),
        skew=ThresholdConfig(
            value=skew_threshold,
            rationale="Custom skew threshold",
            weight=0.8,
        ),
        noise=ThresholdConfig(
            value=noise_threshold,
            rationale="Custom noise threshold",
            weight=1.0,
        ),
        compression=ThresholdConfig(
            value=compression_threshold,
            rationale="Custom compression threshold",
            weight=0.9,
        ),
        aggregate_threshold=aggregate_threshold,
    )
    return DiscrepancyAnalyzer(thresholds)
