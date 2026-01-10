"""Document Quality Score (DQS) and calibration metrics module.

Provides functions for calculating degradation scores, structural complexity
scores for routing decisions, and model calibration metrics.

Phase 4.10: Extended with configurable weights and new detector integration.
Milestone 8.1: DQS Weighting Optimization
- DQSWeightConfig: Configurable weight dataclass
- DQSCalibrator: Weight calibration and optimization framework
- CalibrationSample/CalibrationResult: Calibration data structures
- Extended IQA integration with illumination, JPEG blockiness, binarization, bleed-through detectors

Phase 7: Model Calibration Metrics
- compute_ece: Expected Calibration Error
- compute_multiclass_ece: Per-class ECE for multi-label models
- compute_severity_metrics: Severity prediction metrics (MAE, correlation)
- CalibrationResult: Calibration evaluation results
"""

from image_preprocessing_detector.metrics.calibration import (
    CalibrationResult as ModelCalibrationResult,
)
from image_preprocessing_detector.metrics.calibration import (
    compute_ece,
    compute_multiclass_ece,
    compute_severity_metrics,
    generate_reliability_diagram_data,
)
from image_preprocessing_detector.metrics.dqs_calculator import (
    DEFAULT_DQS_WEIGHTS,
    CalibrationResult,
    CalibrationSample,
    DQSCalibrator,
    DQSWeightConfig,
    ExtendedIQAScores,
    aggregate_dqs,
    calculate_degradation_score,
    calculate_dqs,
    calculate_extended_degradation_score,
    calculate_pre_ocr_risk,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
    normalize_extended_iqa,
)

__all__ = [
    "DEFAULT_DQS_WEIGHTS",
    "CalibrationResult",
    "CalibrationSample",
    "DQSCalibrator",
    "DQSWeightConfig",
    "ExtendedIQAScores",
    "ModelCalibrationResult",
    "aggregate_dqs",
    "calculate_degradation_score",
    "calculate_dqs",
    "calculate_extended_degradation_score",
    "calculate_pre_ocr_risk",
    "calculate_structural_complexity_score",
    "compute_ece",
    "compute_multiclass_ece",
    "compute_severity_metrics",
    "generate_reliability_diagram_data",
    "normalize_classical_iqa",
    "normalize_extended_iqa",
]
