"""Document Quality Score (DQS) Calculator.

Calculates degradation and structural complexity scores for routing decisions
in the RAG pipeline (Project A → Project B handoff).

Phase 4.10: Updated with configurable weights and integration with new classical
IQA detectors (illumination, JPEG blockiness, binarization, bleed-through).

Milestone 8.1: DQS Weighting Optimization
- DQSWeightConfig: Configurable weight dataclass
- DQSCalibrator: Weight calibration and optimization framework
- Enhanced integration with blur and noise detection metrics
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityResult,
    BleedThroughResult,
    BlurDetectionResult,
    ContrastDetectionResult,
    IlluminationDetectionResult,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    SkewDetectionResult,
)
from image_preprocessing_detector.schema import (
    DQSMetadata,
    LayoutType,
    PageLayoutSummary,
    PDFType,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# =============================================================================
# Weight Configuration (Milestone 8.1.1)
# =============================================================================


@dataclass
class DQSWeightConfig:
    """Configurable weights for DQS calculation.

    All weights should be non-negative. Degradation weights are normalized
    to sum to 1.0 during calculation.

    Attributes:
        blur_weight: Weight for blur quality (default: 0.30)
        noise_weight: Weight for noise quality (default: 0.25)
        contrast_weight: Weight for contrast quality (default: 0.20)
        illumination_weight: Weight for illumination quality (default: 0.15)
        artifacts_weight: Weight for artifact presence (default: 0.10)
        ml_blend_ratio: Ratio for blending ML IQA with classical (default: 0.30)
        structural_base_scores: Base complexity scores by layout type
        structural_feature_weights: Weights for structural features

    Example:
        >>> config = DQSWeightConfig(blur_weight=0.35, noise_weight=0.30)
        >>> config.validate()
        >>> weights = config.get_normalized_degradation_weights()
    """

    # Degradation weights
    blur_weight: float = 0.30
    noise_weight: float = 0.25
    contrast_weight: float = 0.20
    illumination_weight: float = 0.15
    artifacts_weight: float = 0.10

    # ML IQA blending
    ml_blend_ratio: float = 0.30  # How much to weight ML vs classical (0-1)

    # Structural complexity base scores by layout type
    structural_base_scores: dict[LayoutType, float] = field(
        default_factory=lambda: {
            LayoutType.SINGLE_COLUMN: 0.1,
            LayoutType.MULTI_COLUMN: 0.4,
            LayoutType.THREE_COLUMN: 0.6,
            LayoutType.COMPLEX: 0.9,
            LayoutType.UNKNOWN: 0.5,
        }
    )

    # Structural feature weights
    structural_feature_weights: dict[str, float] = field(
        default_factory=lambda: {
            "has_tables": 0.20,
            "has_figures": 0.15,
            "has_dense_math": 0.15,
            "has_handwriting": 0.10,
        }
    )

    # Pre-OCR risk weights
    risk_degradation_weight: float = 0.40
    risk_complexity_weight: float = 0.30
    risk_pdf_type_penalty_image_only: float = 0.20
    risk_pdf_type_penalty_hybrid: float = 0.10
    risk_handwriting_penalty: float = 0.10

    def validate(self) -> None:
        """Validate weight configuration.

        Raises:
            ValueError: If any weights are invalid (negative or out of range)
        """
        # Validate degradation weights are non-negative
        degradation_weights = [
            ("blur_weight", self.blur_weight),
            ("noise_weight", self.noise_weight),
            ("contrast_weight", self.contrast_weight),
            ("illumination_weight", self.illumination_weight),
            ("artifacts_weight", self.artifacts_weight),
        ]

        for name, value in degradation_weights:
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")

        # Validate ML blend ratio
        if not 0.0 <= self.ml_blend_ratio <= 1.0:
            raise ValueError(
                f"ml_blend_ratio must be in [0, 1], got {self.ml_blend_ratio}"
            )

        # Validate risk weights
        risk_weights = [
            ("risk_degradation_weight", self.risk_degradation_weight),
            ("risk_complexity_weight", self.risk_complexity_weight),
            ("risk_pdf_type_penalty_image_only", self.risk_pdf_type_penalty_image_only),
            ("risk_pdf_type_penalty_hybrid", self.risk_pdf_type_penalty_hybrid),
            ("risk_handwriting_penalty", self.risk_handwriting_penalty),
        ]

        for name, value in risk_weights:
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")

        # Validate structural base scores
        for layout_type, score in self.structural_base_scores.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"structural_base_scores[{layout_type}] must be in [0, 1], "
                    f"got {score}"
                )

        # Validate structural feature weights
        for feature, weight in self.structural_feature_weights.items():
            if weight < 0:
                raise ValueError(
                    f"structural_feature_weights[{feature}] must be non-negative, "
                    f"got {weight}"
                )

        logger.debug("DQSWeightConfig validated successfully")

    def get_normalized_degradation_weights(self) -> dict[str, float]:
        """Get degradation weights normalized to sum to 1.0.

        Returns:
            Dictionary with normalized weights for each degradation metric
        """
        total = (
            self.blur_weight
            + self.noise_weight
            + self.contrast_weight
            + self.illumination_weight
            + self.artifacts_weight
        )

        if total == 0:
            # Fallback to equal weights if all are zero
            return {
                "blur": 0.20,
                "noise": 0.20,
                "contrast": 0.20,
                "illumination": 0.20,
                "artifacts": 0.20,
            }

        return {
            "blur": self.blur_weight / total,
            "noise": self.noise_weight / total,
            "contrast": self.contrast_weight / total,
            "illumination": self.illumination_weight / total,
            "artifacts": self.artifacts_weight / total,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "degradation_weights": {
                "blur": self.blur_weight,
                "noise": self.noise_weight,
                "contrast": self.contrast_weight,
                "illumination": self.illumination_weight,
                "artifacts": self.artifacts_weight,
            },
            "ml_blend_ratio": self.ml_blend_ratio,
            "structural_base_scores": {
                k.value: v for k, v in self.structural_base_scores.items()
            },
            "structural_feature_weights": self.structural_feature_weights,
            "risk_weights": {
                "degradation": self.risk_degradation_weight,
                "complexity": self.risk_complexity_weight,
                "pdf_type_penalty_image_only": self.risk_pdf_type_penalty_image_only,
                "pdf_type_penalty_hybrid": self.risk_pdf_type_penalty_hybrid,
                "handwriting_penalty": self.risk_handwriting_penalty,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DQSWeightConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary with weight configuration

        Returns:
            DQSWeightConfig instance
        """
        config = cls()

        if "degradation_weights" in data:
            dw = data["degradation_weights"]
            config.blur_weight = dw.get("blur", config.blur_weight)
            config.noise_weight = dw.get("noise", config.noise_weight)
            config.contrast_weight = dw.get("contrast", config.contrast_weight)
            config.illumination_weight = dw.get(
                "illumination", config.illumination_weight
            )
            config.artifacts_weight = dw.get("artifacts", config.artifacts_weight)

        if "ml_blend_ratio" in data:
            config.ml_blend_ratio = data["ml_blend_ratio"]

        if "structural_base_scores" in data:
            for k, v in data["structural_base_scores"].items():
                layout_type = LayoutType(k) if isinstance(k, str) else k
                config.structural_base_scores[layout_type] = v

        if "structural_feature_weights" in data:
            config.structural_feature_weights.update(data["structural_feature_weights"])

        if "risk_weights" in data:
            rw = data["risk_weights"]
            config.risk_degradation_weight = rw.get(
                "degradation", config.risk_degradation_weight
            )
            config.risk_complexity_weight = rw.get(
                "complexity", config.risk_complexity_weight
            )
            config.risk_pdf_type_penalty_image_only = rw.get(
                "pdf_type_penalty_image_only", config.risk_pdf_type_penalty_image_only
            )
            config.risk_pdf_type_penalty_hybrid = rw.get(
                "pdf_type_penalty_hybrid", config.risk_pdf_type_penalty_hybrid
            )
            config.risk_handwriting_penalty = rw.get(
                "handwriting_penalty", config.risk_handwriting_penalty
            )

        return config


@dataclass
class CalibrationSample:
    """A single calibration sample with IQA metrics and ground truth.

    Attributes:
        sample_id: Unique identifier for the sample
        blur_score: Normalized blur score (0-1, 1=sharp)
        noise_score: Normalized noise score (0-1, 1=clean)
        contrast_score: Normalized contrast score (0-1, 1=good)
        illumination_score: Normalized illumination score (0-1, 1=good)
        artifacts_score: Normalized artifacts score (0-1, 1=clean)
        ground_truth_quality: Human-labeled quality score (0-1)
        metadata: Optional additional metadata
    """

    sample_id: str
    blur_score: float
    noise_score: float
    contrast_score: float
    illumination_score: float
    artifacts_score: float
    ground_truth_quality: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationResult:
    """Result from DQS weight calibration.

    Attributes:
        optimized_config: The optimized weight configuration
        initial_mae: Mean Absolute Error before optimization
        final_mae: Mean Absolute Error after optimization
        improvement_pct: Percentage improvement in MAE
        num_samples: Number of samples used for calibration
        convergence_iterations: Number of iterations to converge
    """

    optimized_config: DQSWeightConfig
    initial_mae: float
    final_mae: float
    improvement_pct: float
    num_samples: int
    convergence_iterations: int


class DQSCalibrator:
    """Calibrator for optimizing DQS weights based on ground truth data.

    Uses gradient-free optimization to find weights that minimize the error
    between calculated DQS and human-labeled quality scores.

    Example:
        >>> calibrator = DQSCalibrator()
        >>> samples = [
        ...     CalibrationSample(
        ...         sample_id="doc1",
        ...         blur_score=0.8,
        ...         noise_score=0.7,
        ...         contrast_score=0.9,
        ...         illumination_score=0.85,
        ...         artifacts_score=0.95,
        ...         ground_truth_quality=0.82,
        ...     ),
        ...     # ... more samples
        ... ]
        >>> result = calibrator.calibrate(samples)
        >>> print(f"Improved MAE by {result.improvement_pct:.1f}%")
    """

    def __init__(
        self,
        initial_config: DQSWeightConfig | None = None,
        learning_rate: float = 0.01,
        max_iterations: int = 1000,
        convergence_threshold: float = 1e-6,
    ) -> None:
        """Initialize the calibrator.

        Args:
            initial_config: Starting weight configuration (uses defaults if None)
            learning_rate: Step size for weight updates
            max_iterations: Maximum optimization iterations
            convergence_threshold: Stop when improvement is below this threshold
        """
        self.initial_config = initial_config or DQSWeightConfig()
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

    def _calculate_score_with_weights(
        self,
        sample: CalibrationSample,
        weights: dict[str, float],
    ) -> float:
        """Calculate degradation score using given weights.

        Args:
            sample: Calibration sample with IQA metrics
            weights: Normalized weights for each metric

        Returns:
            Calculated quality score
        """
        return (
            weights["blur"] * sample.blur_score
            + weights["noise"] * sample.noise_score
            + weights["contrast"] * sample.contrast_score
            + weights["illumination"] * sample.illumination_score
            + weights["artifacts"] * sample.artifacts_score
        )

    def _calculate_mae(
        self,
        samples: list[CalibrationSample],
        config: DQSWeightConfig,
    ) -> float:
        """Calculate Mean Absolute Error for given configuration.

        Args:
            samples: List of calibration samples
            config: Weight configuration to evaluate

        Returns:
            Mean Absolute Error between predicted and ground truth
        """
        if not samples:
            return 0.0

        weights = config.get_normalized_degradation_weights()
        total_error = 0.0

        for sample in samples:
            predicted = self._calculate_score_with_weights(sample, weights)
            total_error += abs(predicted - sample.ground_truth_quality)

        return total_error / len(samples)

    def _copy_config(self, config: DQSWeightConfig) -> DQSWeightConfig:
        """Create a copy of a weight configuration."""
        return DQSWeightConfig(
            blur_weight=config.blur_weight,
            noise_weight=config.noise_weight,
            contrast_weight=config.contrast_weight,
            illumination_weight=config.illumination_weight,
            artifacts_weight=config.artifacts_weight,
        )

    def _try_weight_adjustment(
        self,
        samples: list[CalibrationSample],
        best_config: DQSWeightConfig,
        best_mae: float,
        weight_name: str,
        delta: float,
    ) -> tuple[DQSWeightConfig, float, bool]:
        """Try adjusting a single weight and return result if improved.

        Args:
            samples: Calibration samples
            best_config: Current best configuration
            best_mae: Current best MAE
            weight_name: Name of weight to adjust (without _weight suffix)
            delta: Amount to adjust (positive or negative)

        Returns:
            Tuple of (new_config, new_mae, improved)
        """
        test_config = self._copy_config(best_config)
        attr_name = f"{weight_name}_weight"
        current_value = getattr(test_config, attr_name)
        setattr(test_config, attr_name, max(0.0, current_value + delta))

        test_mae = self._calculate_mae(samples, test_config)
        if test_mae < best_mae:
            return test_config, test_mae, True
        return best_config, best_mae, False

    def calibrate(
        self,
        samples: list[CalibrationSample],
        verbose: bool = False,
    ) -> CalibrationResult:
        """Calibrate weights using coordinate descent optimization.

        Args:
            samples: List of calibration samples with ground truth
            verbose: Whether to log progress

        Returns:
            CalibrationResult with optimized configuration and metrics

        Raises:
            ValueError: If samples list is empty
        """
        if not samples:
            raise ValueError("Cannot calibrate with empty samples list")

        best_config = self._copy_config(self.initial_config)
        initial_mae = self._calculate_mae(samples, best_config)
        best_mae = initial_mae

        weight_names = ["blur", "noise", "contrast", "illumination", "artifacts"]
        iteration = 0

        for iteration in range(self.max_iterations):
            prev_mae = best_mae
            improved = False

            # Coordinate descent: optimize one weight at a time
            for weight_name in weight_names:
                # Try increasing the weight
                best_config, best_mae, inc_improved = self._try_weight_adjustment(
                    samples, best_config, best_mae, weight_name, self.learning_rate
                )
                if inc_improved:
                    improved = True
                    continue

                # Try decreasing the weight
                best_config, best_mae, dec_improved = self._try_weight_adjustment(
                    samples, best_config, best_mae, weight_name, -self.learning_rate
                )
                if dec_improved:
                    improved = True

            if verbose and iteration % 100 == 0:
                logger.info(
                    "Calibration progress",
                    iteration=iteration,
                    mae=best_mae,
                    improvement=initial_mae - best_mae,
                )

            # Check convergence
            if not improved or (prev_mae - best_mae) < self.convergence_threshold:
                break

        improvement_pct = (
            ((initial_mae - best_mae) / initial_mae * 100) if initial_mae > 0 else 0.0
        )

        logger.info(
            "Calibration complete",
            initial_mae=initial_mae,
            final_mae=best_mae,
            improvement_pct=improvement_pct,
            iterations=iteration + 1,
            num_samples=len(samples),
        )

        return CalibrationResult(
            optimized_config=best_config,
            initial_mae=initial_mae,
            final_mae=best_mae,
            improvement_pct=improvement_pct,
            num_samples=len(samples),
            convergence_iterations=iteration + 1,
        )

    def evaluate(
        self,
        samples: list[CalibrationSample],
        config: DQSWeightConfig | None = None,
    ) -> dict[str, float]:
        """Evaluate a configuration on calibration samples.

        Args:
            samples: List of calibration samples
            config: Configuration to evaluate (uses initial if None)

        Returns:
            Dictionary with evaluation metrics (MAE, RMSE, R²)
        """
        config = config or self.initial_config
        weights = config.get_normalized_degradation_weights()

        if not samples:
            return {"mae": 0.0, "rmse": 0.0, "r_squared": 0.0}

        predictions = []
        ground_truths = []

        for sample in samples:
            pred = self._calculate_score_with_weights(sample, weights)
            predictions.append(pred)
            ground_truths.append(sample.ground_truth_quality)

        predictions_arr = np.array(predictions)
        ground_truths_arr = np.array(ground_truths)

        # Mean Absolute Error
        mae = float(np.mean(np.abs(predictions_arr - ground_truths_arr)))

        # Root Mean Square Error
        rmse = float(np.sqrt(np.mean((predictions_arr - ground_truths_arr) ** 2)))

        # R² (coefficient of determination)
        ss_res = np.sum((ground_truths_arr - predictions_arr) ** 2)
        ss_tot = np.sum((ground_truths_arr - np.mean(ground_truths_arr)) ** 2)
        r_squared = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        return {
            "mae": mae,
            "rmse": rmse,
            "r_squared": r_squared,
        }


# Default global configuration (for backward compatibility)
_default_config = DQSWeightConfig()

# Legacy constants (deprecated, use DQSWeightConfig instead)
DEGRADATION_WEIGHTS = _default_config.get_normalized_degradation_weights()

# Layout type base complexity scores
LAYOUT_COMPLEXITY_BASE = _default_config.structural_base_scores

# Structural feature weights
STRUCTURAL_FEATURE_WEIGHTS = _default_config.structural_feature_weights


def calculate_degradation_score(
    classical_iqa: dict[str, Any],
    ml_iqa: dict[str, Any] | None = None,
    config: DQSWeightConfig | None = None,
) -> float:
    """Calculate degradation score from IQA metrics.

    Uses configurable weights (default: 0.3*blur + 0.25*noise + 0.2*contrast +
    0.15*illumination + 0.1*artifacts). All input metrics should be normalized
    to 0-1 range where 1=best quality.

    Args:
        classical_iqa: Classical IQA metrics dict with keys:
            - blur_score: Laplacian variance normalized (0-1, higher=sharper)
            - noise_score: Noise level normalized (0-1, higher=cleaner)
            - contrast_score: Contrast quality normalized (0-1, higher=better)
            - illumination_score: Illumination quality normalized (0-1, higher=better)
            - artifacts_score: Artifact presence normalized (0-1, higher=fewer artifacts)
        ml_iqa: Optional ML-based IQA metrics (Phase 2+). If provided, will be
            blended with classical metrics.
        config: Optional weight configuration. Uses defaults if not provided.

    Returns:
        Degradation score (0-1, where 0=worst degradation, 1=pristine quality)

    Raises:
        ValueError: If required metrics are missing or out of range

    Example:
        >>> classical_iqa = {
        ...     "blur_score": 0.8,
        ...     "noise_score": 0.7,
        ...     "contrast_score": 0.6,
        ...     "illumination_score": 0.9,
        ...     "artifacts_score": 0.95,
        ... }
        >>> score = calculate_degradation_score(classical_iqa)
        >>> assert 0.0 <= score <= 1.0
        >>> # With custom config
        >>> config = DQSWeightConfig(blur_weight=0.4, noise_weight=0.3)
        >>> score = calculate_degradation_score(classical_iqa, config=config)
    """
    # Use default config if not provided
    config = config or _default_config

    # Validate required metrics are present
    required_metrics = [
        "blur_score",
        "noise_score",
        "contrast_score",
        "illumination_score",
        "artifacts_score",
    ]

    for metric in required_metrics:
        if metric not in classical_iqa:
            raise ValueError(f"Missing required metric: {metric}")

        value = classical_iqa[metric]
        if not isinstance(value, int | float):
            raise TypeError(f"Metric {metric} must be numeric, got {type(value)}")

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Metric {metric} must be in range [0.0, 1.0], got {value}"
            )

    # Get normalized weights from config
    weights = config.get_normalized_degradation_weights()

    # Calculate weighted score
    degradation_score = (
        weights["blur"] * classical_iqa["blur_score"]
        + weights["noise"] * classical_iqa["noise_score"]
        + weights["contrast"] * classical_iqa["contrast_score"]
        + weights["illumination"] * classical_iqa["illumination_score"]
        + weights["artifacts"] * classical_iqa["artifacts_score"]
    )

    # If ML IQA is available (Phase 2+), blend with classical
    if ml_iqa is not None and "overall_quality" in ml_iqa:
        ml_quality = ml_iqa["overall_quality"]
        if not 0.0 <= ml_quality <= 1.0:
            logger.warning(
                "ML IQA quality score out of range, ignoring",
                ml_quality=ml_quality,
            )
        else:
            # Blend using configurable ratio
            classical_ratio = 1.0 - config.ml_blend_ratio
            degradation_score = (
                classical_ratio * degradation_score + config.ml_blend_ratio * ml_quality
            )
            logger.debug(
                "Blended classical and ML IQA scores",
                classical_ratio=classical_ratio,
                ml_ratio=config.ml_blend_ratio,
                ml_score=ml_quality,
                final_score=degradation_score,
            )

    # Ensure result is in valid range
    degradation_score = max(0.0, min(1.0, degradation_score))

    logger.debug(
        "Degradation score calculated",
        score=degradation_score,
        blur=classical_iqa["blur_score"],
        noise=classical_iqa["noise_score"],
        contrast=classical_iqa["contrast_score"],
        illumination=classical_iqa["illumination_score"],
        artifacts=classical_iqa["artifacts_score"],
        weights=weights,
    )

    return float(degradation_score)


def calculate_structural_complexity_score(
    layout_summary: PageLayoutSummary,
    config: DQSWeightConfig | None = None,
) -> float:
    """Calculate structural complexity score from layout metadata.

    Base score from layout_type (configurable):
    - single_column: 0.1
    - multi_column: 0.4
    - three_column: 0.6
    - complex: 0.9
    - unknown: 0.5

    Additional increments (configurable):
    - +0.2 if has_tables
    - +0.15 if has_figures
    - +0.15 if has_dense_math
    - +0.1 if has_handwriting

    Score is capped at 1.0.

    Args:
        layout_summary: PageLayoutSummary with layout type and feature flags
        config: Optional weight configuration. Uses defaults if not provided.

    Returns:
        Structural complexity score (0-1, where 0=simple, 1=very complex)

    Example:
        >>> from image_preprocessing_detector.schema import (
        ...     PageLayoutSummary,
        ...     LayoutType,
        ...     PageAttributes,
        ... )
        >>> layout = PageLayoutSummary(
        ...     page_index=0,
        ...     layout_type=LayoutType.MULTI_COLUMN,
        ...     has_tables=True,
        ...     has_figures=False,
        ...     has_dense_math=False,
        ...     has_handwriting=False,
        ...     page_attributes=PageAttributes(),
        ... )
        >>> score = calculate_structural_complexity_score(layout)
        >>> assert score == 0.4 + 0.2  # multi_column + has_tables
    """
    # Use default config if not provided
    config = config or _default_config

    # Start with base complexity from layout type
    complexity_score = config.structural_base_scores.get(
        layout_summary.layout_type, 0.5
    )

    logger.debug(
        "Base complexity from layout type",
        layout_type=layout_summary.layout_type.value,
        base_score=complexity_score,
    )

    feature_weights = config.structural_feature_weights

    # Add increments for structural features
    if layout_summary.has_tables:
        increment = feature_weights.get("has_tables", 0.20)
        complexity_score += increment
        logger.debug("Added tables complexity", increment=increment)

    if layout_summary.has_figures:
        increment = feature_weights.get("has_figures", 0.15)
        complexity_score += increment
        logger.debug("Added figures complexity", increment=increment)

    if layout_summary.has_dense_math:
        increment = feature_weights.get("has_dense_math", 0.15)
        complexity_score += increment
        logger.debug("Added dense math complexity", increment=increment)

    if layout_summary.has_handwriting:
        increment = feature_weights.get("has_handwriting", 0.10)
        complexity_score += increment
        logger.debug("Added handwriting complexity", increment=increment)

    # Cap at 1.0
    complexity_score = min(1.0, complexity_score)

    logger.debug(
        "Structural complexity score calculated",
        score=complexity_score,
        layout_type=layout_summary.layout_type.value,
        has_tables=layout_summary.has_tables,
        has_figures=layout_summary.has_figures,
        has_dense_math=layout_summary.has_dense_math,
        has_handwriting=layout_summary.has_handwriting,
    )

    return float(complexity_score)


def aggregate_dqs(
    page_dqs_list: list[DQSMetadata],
) -> DQSMetadata:
    """Aggregate page-level DQS scores to document-level.

    Aggregation strategy:
    - degradation_score: median (representative of typical page quality)
    - structural_complexity_score: max (worst page determines routing needs)

    Rationale: For routing decisions, we need to handle the most complex page
    and be aware of the typical quality level across all pages.

    Args:
        page_dqs_list: List of DQSMetadata instances, one per page

    Returns:
        Aggregated DQSMetadata for the entire document

    Raises:
        ValueError: If page_dqs_list is empty

    Example:
        >>> page_scores = [
        ...     DQSMetadata(degradation_score=0.8, structural_complexity_score=0.3),
        ...     DQSMetadata(degradation_score=0.7, structural_complexity_score=0.6),
        ...     DQSMetadata(degradation_score=0.9, structural_complexity_score=0.4),
        ... ]
        >>> doc_score = aggregate_dqs(page_scores)
        >>> assert doc_score.degradation_score == 0.8  # median
        >>> assert doc_score.structural_complexity_score == 0.6  # max
    """
    if not page_dqs_list:
        raise ValueError("Cannot aggregate empty page_dqs_list")

    # Extract scores into arrays
    degradation_scores = np.array([page.degradation_score for page in page_dqs_list])
    complexity_scores = np.array(
        [page.structural_complexity_score for page in page_dqs_list]
    )

    # Aggregate: median degradation, max complexity
    aggregated_degradation = float(np.median(degradation_scores))
    aggregated_complexity = float(np.max(complexity_scores))

    logger.info(
        "Aggregated document-level DQS",
        num_pages=len(page_dqs_list),
        degradation_median=aggregated_degradation,
        degradation_min=float(np.min(degradation_scores)),
        degradation_max=float(np.max(degradation_scores)),
        complexity_max=aggregated_complexity,
        complexity_min=float(np.min(complexity_scores)),
        complexity_median=float(np.median(complexity_scores)),
    )

    return DQSMetadata(
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )


def normalize_classical_iqa(
    blur_result: BlurDetectionResult | None = None,
    contrast_result: ContrastDetectionResult | None = None,
    _skew_result: SkewDetectionResult | None = None,
    noise_result: NoiseDetectionResult | None = None,
    noise_score: float | None = None,
    illumination_score: float | None = None,
    artifacts_score: float | None = None,
) -> dict[str, Any]:
    """Normalize classical IQA results into DQS-compatible format.

    Converts raw detector outputs into normalized 0-1 scores where 1=best quality.
    Uses sensible defaults for missing metrics.

    Args:
        blur_result: BlurDetectionResult from BlurDetector. If the result has a
            `blur_score` attribute (0-1 normalized), it will be used directly.
            Otherwise, the raw `score` (Laplacian variance) is normalized.
        contrast_result: ContrastDetectionResult from ContrastDetector
        _skew_result: SkewDetectionResult from SkewDetector (not directly used in DQS,
            but provided for completeness)
        noise_result: NoiseDetectionResult from NoiseDetector (Milestone 4.2).
            Takes precedence over noise_score if provided.
        noise_score: Pre-normalized noise score (0-1, 1=clean). Deprecated, use
            noise_result instead.
        illumination_score: Pre-normalized illumination score (0-1, 1=good)
        artifacts_score: Pre-normalized artifacts score (0-1, 1=clean)

    Returns:
        Dictionary with normalized IQA metrics ready for calculate_degradation_score()

    Example:
        >>> from image_preprocessing_detector.detection.iqa_classical import (
        ...     detect_blur,
        ...     detect_contrast,
        ...     detect_noise,
        ... )
        >>> import cv2
        >>> image = cv2.imread("document.jpg")
        >>> blur_result = detect_blur(image)
        >>> contrast_result = detect_contrast(image)
        >>> noise_result = detect_noise(image)
        >>> iqa = normalize_classical_iqa(
        ...     blur_result=blur_result,
        ...     contrast_result=contrast_result,
        ...     noise_result=noise_result,
        ... )
        >>> dqs = calculate_degradation_score(iqa)
    """
    # Normalize blur score
    if blur_result is not None:
        # Check if we have the new blur_score field (0-1 normalized)
        if hasattr(blur_result, "blur_score") and blur_result.blur_score is not None:
            blur_normalized = blur_result.blur_score
        else:
            # Fallback: normalize from raw Laplacian variance
            # Typical range: 0-1000+, good quality > 200
            raw_blur = blur_result.score
            blur_normalized = min(1.0, raw_blur / 200.0)
    else:
        blur_normalized = 0.8  # Default: assume reasonable quality

    # Normalize contrast score (already 0-1 from detector)
    contrast_normalized = (
        contrast_result.score if contrast_result is not None else 0.7
    )  # Default: assume moderate contrast

    # Normalize noise score (precedence: noise_result, then noise_score, then default)
    if noise_result is not None:
        # Use normalized noise_score from NoiseDetectionResult (1 = clean)
        noise_normalized = noise_result.noise_score
    elif noise_score is not None:
        noise_normalized = noise_score
    else:
        noise_normalized = 0.85  # Default: assume reasonably clean

    # Use provided normalized scores or defaults
    illumination_normalized = (
        illumination_score if illumination_score is not None else 0.9
    )
    artifacts_normalized = artifacts_score if artifacts_score is not None else 0.95

    logger.debug(
        "Normalized classical IQA metrics",
        blur=blur_normalized,
        contrast=contrast_normalized,
        noise=noise_normalized,
        illumination=illumination_normalized,
        artifacts=artifacts_normalized,
    )

    return {
        "blur_score": blur_normalized,
        "noise_score": noise_normalized,
        "contrast_score": contrast_normalized,
        "illumination_score": illumination_normalized,
        "artifacts_score": artifacts_normalized,
    }


def calculate_dqs(
    blur_scores: list[float],
    contrast_scores: list[float],
    noise_scores: list[float],
    _skew_angles: list[float],
    layout_complexities: list[float],
) -> DQSMetadata:
    """Calculate Document Quality Score from page-level metrics.

    Aggregates IQA metrics across all pages to produce document-level DQS.

    Args:
        blur_scores: List of blur scores per page (0-1, 1=sharp)
        contrast_scores: List of contrast scores per page (0-1, 1=good)
        noise_scores: List of noise scores per page (0-1, 1=clean)
        _skew_angles: List of skew angles per page (degrees, unused in current implementation)
        layout_complexities: List of layout complexity scores per page (0-1)

    Returns:
        DQSMetadata with aggregated degradation and complexity scores

    Example:
        >>> dqs = calculate_dqs(
        ...     blur_scores=[0.8, 0.7],
        ...     contrast_scores=[0.9, 0.85],
        ...     noise_scores=[0.75, 0.8],
        ...     _skew_angles=[1.0, 0.5],
        ...     layout_complexities=[0.3, 0.4],
        ... )
        >>> assert 0.0 <= dqs.degradation_score <= 1.0
    """
    import numpy as np

    # Aggregate degradation score: median of weighted IQA metrics
    num_pages = len(blur_scores)
    degradation_scores = []

    for i in range(num_pages):
        # Weight: 40% blur, 30% noise, 30% contrast
        page_degradation = (
            0.4 * blur_scores[i] + 0.3 * noise_scores[i] + 0.3 * contrast_scores[i]
        )
        degradation_scores.append(page_degradation)

    aggregated_degradation = float(np.median(degradation_scores))

    # Aggregate complexity: max complexity across all pages
    aggregated_complexity = float(np.max(layout_complexities))

    logger.debug(
        "Calculated DQS from page metrics",
        num_pages=num_pages,
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )

    return DQSMetadata(
        degradation_score=aggregated_degradation,
        structural_complexity_score=aggregated_complexity,
    )


def calculate_pre_ocr_risk(
    dqs: DQSMetadata,
    pdf_type: PDFType | None,
    page_layout_summary: list[PageLayoutSummary],
    config: DQSWeightConfig | None = None,
) -> float:
    """Calculate pre-OCR processing risk score.

    Risk score combines degradation quality, structural complexity, and document type
    to predict OCR difficulty (0=low risk, 1=high risk).

    Formula (configurable weights):
    - Base risk from degradation: (1 - degradation_score) * 0.4
    - Complexity contribution: complexity_score * 0.3
    - PDF type penalty: +0.2 for image_only, +0.1 for hybrid
    - Layout features: +0.1 if has_handwriting

    Args:
        dqs: Document Quality Score
        pdf_type: PDF classification (image_only/born_digital/hybrid)
        page_layout_summary: Per-page layout analysis
        config: Optional weight configuration. Uses defaults if not provided.

    Returns:
        Pre-OCR risk score (0-1, where 0=low risk, 1=high risk)

    Example:
        >>> dqs = DQSMetadata(degradation_score=0.7, structural_complexity_score=0.5)
        >>> risk = calculate_pre_ocr_risk(dqs, PDFType.HYBRID, [])
        >>> assert 0.0 <= risk <= 1.0
    """
    # Use default config if not provided
    config = config or _default_config

    # Base risk from degradation (inverse: low quality = high risk)
    degradation_risk = (1.0 - dqs.degradation_score) * config.risk_degradation_weight

    # Complexity contribution
    complexity_risk = dqs.structural_complexity_score * config.risk_complexity_weight

    # PDF type penalty
    pdf_type_penalty = 0.0
    if pdf_type == PDFType.IMAGE_ONLY:
        pdf_type_penalty = config.risk_pdf_type_penalty_image_only
    elif pdf_type == PDFType.HYBRID:
        pdf_type_penalty = config.risk_pdf_type_penalty_hybrid

    # Layout feature penalties
    has_handwriting = any(page.has_handwriting for page in page_layout_summary)
    handwriting_penalty = config.risk_handwriting_penalty if has_handwriting else 0.0

    # Aggregate risk
    total_risk = (
        degradation_risk + complexity_risk + pdf_type_penalty + handwriting_penalty
    )

    # Clamp to [0, 1]
    total_risk = max(0.0, min(1.0, total_risk))

    logger.debug(
        "Calculated pre-OCR risk",
        degradation_risk=degradation_risk,
        complexity_risk=complexity_risk,
        pdf_type_penalty=pdf_type_penalty,
        handwriting_penalty=handwriting_penalty,
        total_risk=total_risk,
    )

    return float(total_risk)


# =============================================================================
# Phase 4.10: Extended DQS with new classical IQA detectors
# =============================================================================


@dataclass
class ExtendedIQAScores:
    """Extended IQA scores from all classical detectors (Phase 4.10).

    All scores normalized to 0-1 where 1=best quality.

    Attributes:
        blur_score: Blur quality (from BlurDetector)
        noise_score: Noise quality (from NoiseDetector)
        contrast_score: Contrast quality (from ContrastDetector)
        illumination_score: Illumination quality (from IlluminationDetector)
        compression_score: Compression quality (from JPEGBlockinessDetector)
        binarization_score: Binarization quality (from BinarizationQualityDetector)
        bleed_through_score: Bleed-through quality (from BleedThroughDetector)
    """

    blur_score: float = 1.0
    noise_score: float = 1.0
    contrast_score: float = 1.0
    illumination_score: float = 1.0
    compression_score: float = 1.0
    binarization_score: float = 1.0
    bleed_through_score: float = 1.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "blur": self.blur_score,
            "noise": self.noise_score,
            "contrast": self.contrast_score,
            "illumination": self.illumination_score,
            "compression": self.compression_score,
            "binarization": self.binarization_score,
            "bleed_through": self.bleed_through_score,
        }


# Default weight configuration for extended IQA (Phase 4.10)
DEFAULT_DQS_WEIGHTS = DQSWeightConfig()

# Severity to quality score mapping
_SEVERITY_QUALITY_MAP: dict[str, float] = {
    "low": 0.85,
    "medium": 0.65,
    "high": 0.40,
    "critical": 0.15,
}


def _severity_to_quality(severity_value: str) -> float:
    """Convert severity level to quality score.

    Args:
        severity_value: Severity enum value string

    Returns:
        Quality score (0-1, higher is better)
    """
    return _SEVERITY_QUALITY_MAP.get(severity_value, 0.5)


def _normalize_blur_score(blur_result: BlurDetectionResult) -> float:
    """Normalize blur detection result to quality score."""
    if blur_result.is_blurred:
        return _severity_to_quality(blur_result.severity.value)
    return min(1.0, blur_result.score / 500.0)


def _normalize_noise_score(noise_result: NoiseDetectionResult) -> float:
    """Normalize noise detection result to quality score."""
    if noise_result.is_noisy:
        return _severity_to_quality(noise_result.severity.value)
    return noise_result.noise_score


def _normalize_contrast_score(contrast_result: ContrastDetectionResult) -> float:
    """Normalize contrast detection result to quality score."""
    if contrast_result.is_low_contrast:
        return _severity_to_quality(contrast_result.severity.value)
    return contrast_result.score


def _normalize_illumination_score(
    illumination_result: IlluminationDetectionResult,
) -> float:
    """Normalize illumination detection result to quality score."""
    if illumination_result.has_issues:
        return _severity_to_quality(illumination_result.severity.value)
    return illumination_result.uniformity


def _normalize_compression_score(compression_result: JPEGBlockinessResult) -> float:
    """Normalize compression detection result to quality score."""
    if compression_result.has_artifacts:
        return _severity_to_quality(compression_result.severity.value)
    return compression_result.compression_score


def normalize_extended_iqa(
    blur_result: BlurDetectionResult | None = None,
    noise_result: NoiseDetectionResult | None = None,
    contrast_result: ContrastDetectionResult | None = None,
    illumination_result: IlluminationDetectionResult | None = None,
    compression_result: JPEGBlockinessResult | None = None,
    binarization_result: BinarizationQualityResult | None = None,
    bleed_through_result: BleedThroughResult | None = None,
    _skew_result: SkewDetectionResult | None = None,  # Not used in DQS but accepted
) -> ExtendedIQAScores:
    """Normalize all classical detector outputs to ExtendedIQAScores.

    Phase 4.10: Integrates all Phase 4 classical IQA detectors into a
    unified score format for DQS calculation.

    Args:
        blur_result: BlurDetectionResult from BlurDetector
        noise_result: NoiseDetectionResult from NoiseDetector
        contrast_result: ContrastDetectionResult from ContrastDetector
        illumination_result: IlluminationDetectionResult from IlluminationDetector
        compression_result: JPEGBlockinessResult from JPEGBlockinessDetector
        binarization_result: BinarizationQualityResult from BinarizationQualityDetector
        bleed_through_result: BleedThroughResult from BleedThroughDetector
        skew_result: SkewDetectionResult (not used in DQS, but accepted for API completeness)

    Returns:
        ExtendedIQAScores with all normalized scores

    Example:
        >>> from image_preprocessing_detector.detection import (
        ...     detect_blur,
        ...     detect_noise,
        ...     detect_contrast,
        ... )
        >>> blur = detect_blur(image)
        >>> noise = detect_noise(image)
        >>> contrast = detect_contrast(image)
        >>> scores = normalize_extended_iqa(
        ...     blur_result=blur,
        ...     noise_result=noise,
        ...     contrast_result=contrast,
        ... )
        >>> dqs = calculate_extended_degradation_score(scores)
    """
    scores = ExtendedIQAScores()

    # Normalize each detector result using helpers
    if blur_result is not None:
        scores.blur_score = _normalize_blur_score(blur_result)

    if noise_result is not None:
        scores.noise_score = _normalize_noise_score(noise_result)

    if contrast_result is not None:
        scores.contrast_score = _normalize_contrast_score(contrast_result)

    if illumination_result is not None:
        scores.illumination_score = _normalize_illumination_score(illumination_result)

    if compression_result is not None:
        scores.compression_score = _normalize_compression_score(compression_result)

    if binarization_result is not None:
        scores.binarization_score = binarization_result.binarization_score

    if bleed_through_result is not None:
        if bleed_through_result.bleed_through_detected:
            scores.bleed_through_score = 1.0 - bleed_through_result.severity
        else:
            scores.bleed_through_score = 1.0

    return scores


def calculate_extended_degradation_score(
    iqa_scores: ExtendedIQAScores,
    weights: DQSWeightConfig | None = None,
    ml_iqa: dict[str, Any] | None = None,
) -> float:
    """Calculate degradation score using extended IQA metrics and configurable weights.

    Phase 4.10: Uses all Phase 4 classical IQA detectors with configurable weights.
    Note: This function uses a simplified 5-weight model (blur, noise, contrast,
    illumination, artifacts) where artifacts aggregate compression + binarization +
    bleed-through scores.

    Args:
        iqa_scores: ExtendedIQAScores with all normalized IQA metrics
        weights: DQSWeightConfig with calibrated weights (default: DEFAULT_DQS_WEIGHTS)
        ml_iqa: Optional ML-based IQA metrics. If provided, blends with classical.

    Returns:
        Degradation score (0-1, where 0=worst degradation, 1=pristine quality)

    Example:
        >>> scores = ExtendedIQAScores(
        ...     blur_score=0.8,
        ...     noise_score=0.7,
        ...     contrast_score=0.85,
        ...     illumination_score=0.9,
        ...     compression_score=0.95,
        ...     binarization_score=0.88,
        ...     bleed_through_score=1.0,
        ... )
        >>> dqs = calculate_extended_degradation_score(scores)
        >>> assert 0.0 <= dqs <= 1.0
    """
    if weights is None:
        weights = DEFAULT_DQS_WEIGHTS

    # Aggregate extended artifact metrics into single artifacts_score
    # Equal weight to each: compression, binarization, bleed-through
    artifacts_score = (
        iqa_scores.compression_score
        + iqa_scores.binarization_score
        + iqa_scores.bleed_through_score
    ) / 3.0

    # Use the standard 5-metric degradation calculation
    classical_iqa_dict = {
        "blur_score": iqa_scores.blur_score,
        "noise_score": iqa_scores.noise_score,
        "contrast_score": iqa_scores.contrast_score,
        "illumination_score": iqa_scores.illumination_score,
        "artifacts_score": artifacts_score,
    }

    # Reuse standard degradation score calculation
    degradation_score = calculate_degradation_score(
        classical_iqa=classical_iqa_dict,
        ml_iqa=ml_iqa,
        config=weights,
    )

    logger.debug(
        "Extended degradation score calculated",
        score=degradation_score,
        input_scores=iqa_scores.to_dict(),
        aggregated_artifacts=artifacts_score,
    )

    return float(degradation_score)
