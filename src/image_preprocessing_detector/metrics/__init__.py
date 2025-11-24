"""Document Quality Score (DQS) calculation module.

Provides functions for calculating degradation scores and structural complexity
scores for routing decisions in the RAG pipeline.

Phase 4.10: Extended with configurable weights and new detector integration.
"""

from image_preprocessing_detector.metrics.dqs_calculator import (
    DEFAULT_DQS_WEIGHTS,
    DQSWeightConfig,
    ExtendedIQAScores,
    aggregate_dqs,
    calculate_degradation_score,
    calculate_extended_degradation_score,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
    normalize_extended_iqa,
)

__all__ = [
    # Phase 4.10: Extended DQS
    "DEFAULT_DQS_WEIGHTS",
    "DQSWeightConfig",
    "ExtendedIQAScores",
    "calculate_extended_degradation_score",
    "normalize_extended_iqa",
    # Legacy DQS functions
    "aggregate_dqs",
    "calculate_degradation_score",
    "calculate_structural_complexity_score",
    "normalize_classical_iqa",
]
