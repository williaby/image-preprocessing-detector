"""Document Quality Score (DQS) calculation module.

Provides functions for calculating degradation scores and structural complexity
scores for routing decisions in the RAG pipeline.

Phase 4.10: Extended with configurable weights and new detector integration.
Milestone 8.1: DQS Weighting Optimization
- DQSWeightConfig: Configurable weight dataclass
- DQSCalibrator: Weight calibration and optimization framework
- CalibrationSample/CalibrationResult: Calibration data structures
- Extended IQA integration with illumination, JPEG blockiness, binarization, bleed-through detectors
"""

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
    # Phase 4.10: Extended DQS
    "DEFAULT_DQS_WEIGHTS",
    # Milestone 8.1: Calibration framework
    "CalibrationResult",
    "CalibrationSample",
    "DQSCalibrator",
    "DQSWeightConfig",
    "ExtendedIQAScores",
    # Core DQS functions
    "aggregate_dqs",
    "calculate_degradation_score",
    "calculate_dqs",
    "calculate_extended_degradation_score",
    "calculate_pre_ocr_risk",
    "calculate_structural_complexity_score",
    "normalize_classical_iqa",
    "normalize_extended_iqa",
]
