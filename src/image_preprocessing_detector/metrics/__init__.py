"""
Document Quality Score (DQS) calculation module.

Provides functions for calculating degradation scores and structural complexity
scores for routing decisions in the RAG pipeline.
"""

from image_preprocessing_detector.metrics.dqs_calculator import (
    aggregate_dqs,
    calculate_degradation_score,
    calculate_structural_complexity_score,
    normalize_classical_iqa,
)

__all__ = [
    "aggregate_dqs",
    "calculate_degradation_score",
    "calculate_structural_complexity_score",
    "normalize_classical_iqa",
]
