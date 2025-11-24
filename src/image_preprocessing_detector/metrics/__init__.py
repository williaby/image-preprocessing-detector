"""Document Quality Score (DQS) calculation module.

Provides functions for calculating degradation scores and structural complexity
scores for routing decisions in the RAG pipeline.

Milestone 8.1: DQS Weighting Optimization
- DQSWeightConfig: Configurable weight dataclass
- DQSCalibrator: Weight calibration and optimization framework
- CalibrationSample/CalibrationResult: Calibration data structures
"""

from image_preprocessing_detector.metrics.dqs_calculator import (
    CalibrationResult,
    CalibrationSample,
    DQSCalibrator,
    DQSWeightConfig,
    aggregate_dqs,
    calculate_degradation_score,
    calculate_dqs,
    calculate_pre_ocr_risk,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
)

__all__ = [
    "CalibrationResult",
    "CalibrationSample",
    "DQSCalibrator",
    "DQSWeightConfig",
    "aggregate_dqs",
    "calculate_degradation_score",
    "calculate_dqs",
    "calculate_pre_ocr_risk",
    "calculate_structural_complexity_score",
    "normalize_classical_iqa",
]
