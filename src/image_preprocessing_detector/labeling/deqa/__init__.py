"""DeQA-Doc multi-mode labeling infrastructure.

This module provides a reusable infrastructure for generating document IQA
pseudo-labels using DeQA-Doc models with support for multiple inference modes
and datasets.

Inference Modes:
    - specialist: 3 dimension-specific CNN models (overall, sharpness, color)
    - ensemble: 5 VLM models (full VQualA 2025 champion configuration)
    - vl: Single configurable VL model (fastest, most flexible)

Example:
    >>> from image_preprocessing_detector.labeling.deqa import (
    ...     DeQAConfig,
    ...     create_inference_engine,
    ... )
    >>> config = DeQAConfig(mode="specialist")
    >>> engine = create_inference_engine(config)
    >>> engine.load_models()
    >>> scores = engine.predict(image)
"""

from image_preprocessing_detector.labeling.deqa.analysis import (
    ComparisonMetrics,
    LabelAnalysis,
    VQualAScore,
    analyze_label_set,
    compare_label_sets,
    compare_to_ground_truth,
    compute_vquala_score,
    generate_comparison_report,
    load_labels,
)
from image_preprocessing_detector.labeling.deqa.base import (
    CheckpointManager,
    DeQAInference,
    DeQAScore,
    LabelResult,
)
from image_preprocessing_detector.labeling.deqa.config import (
    DATASET_CONFIGS,
    MODEL_REGISTRY,
    QUALITY_LEVELS,
    QUALITY_SCORES,
    DeQAConfig,
    InferenceMode,
    ModelConfig,
    ModelSource,
    QualityDimension,
)

__all__ = [
    "DATASET_CONFIGS",
    "MODEL_REGISTRY",
    "QUALITY_LEVELS",
    "QUALITY_SCORES",
    "CheckpointManager",
    "ComparisonMetrics",
    "DeQAConfig",
    "DeQAInference",
    "DeQAScore",
    "InferenceMode",
    "LabelAnalysis",
    "LabelResult",
    "ModelConfig",
    "ModelSource",
    "QualityDimension",
    "VQualAScore",
    "analyze_label_set",
    "compare_label_sets",
    "compare_to_ground_truth",
    "compute_vquala_score",
    "create_inference_engine",
    "generate_comparison_report",
    "load_labels",
]


def create_inference_engine(config: DeQAConfig) -> DeQAInference:
    """Create an inference engine for the specified mode.

    Args:
        config: Configuration specifying inference mode and parameters.

    Returns:
        DeQAInference subclass instance for the specified mode.

    Raises:
        ValueError: If an unknown inference mode is specified.

    Note:
        SPECIALIST and SPECIALIST_TRUE both use SpecialistInference.
        ENSEMBLE and ENSEMBLE_TRUE both use EnsembleInference.
        The TRUE variants indicate the full model configuration is used.
    """
    # Specialist modes (dimension-specific CNN models)
    if config.mode in (InferenceMode.SPECIALIST, InferenceMode.SPECIALIST_TRUE):
        from image_preprocessing_detector.labeling.deqa.specialist import (
            SpecialistInference,
        )

        return SpecialistInference(config)

    # Ensemble modes (multiple VLM models)
    if config.mode in (InferenceMode.ENSEMBLE, InferenceMode.ENSEMBLE_TRUE):
        from image_preprocessing_detector.labeling.deqa.ensemble import (
            EnsembleInference,
        )

        return EnsembleInference(config)

    # Single VL model mode
    if config.mode == InferenceMode.VL:
        from image_preprocessing_detector.labeling.deqa.vl_single import (
            VLSingleInference,
        )

        return VLSingleInference(config)

    msg = f"Unknown inference mode: {config.mode}"
    raise ValueError(msg)
