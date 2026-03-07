"""Detection modules for image quality assessment and document analysis.

Phase 1: Text gate and classical IQA methods
Phase 2-3: ML-based IQA (teacher-student ResNet)
Phase 4: Classical IQA detectors (blur, noise, skew, contrast, illumination,
         JPEG blockiness, binarization, bleed-through)
Phase 4.9: Discrepancy threshold tuning for ML-classical comparison
Phase 6: Layout-lite detection (DocLayout-YOLO + heuristics)
Phase 8: Orientation detection (0°, 90°, 180°, 270°)
Phase 10: OOD detection and cross-model agreement

DocLayout-YOLO is a YOLOv10-based model specifically optimized for document
layout detection. Pre-trained models are available (no training required).

Model configuration: configs/models/doclayout_yolo.yaml
"""

# Deskew pipeline (ML-first with classical fallback)
# Stream 2: Heuristic detectors
from image_preprocessing_detector.detection.blank_page_detector import (
    BlankPageDetector,
    BlankPageResult,
    detect_blank_page,
)
from image_preprocessing_detector.detection.code_detector import (
    CodeDetectionResult,
    CodeDetector,
    detect_code,
)

# OOD detection and cross-model agreement (Phase 10)
from image_preprocessing_detector.detection.cross_model_calibration import (
    CategoryDistribution,
    CrossModelCalibrator,
)
from image_preprocessing_detector.detection.cross_model_validator import (
    CrossModelValidator,
    ReliabilityResult,
    ValidatorConfig,
    ValidatorScore,
    reliability_result_to_dict,
)
from image_preprocessing_detector.detection.deskew_pipeline import (
    DeskewConfig,
    DeskewPipeline,
    DeskewResult,
)
from image_preprocessing_detector.detection.discrepancy import (
    ClassicalScoreAdapter,
    ClassicalScores,
    DiscrepancyAnalyzer,
    DiscrepancyResult,
    DiscrepancyThresholds,
    EscalationReason,
    MLScores,
    ThresholdConfig,
    create_discrepancy_analyzer,
)
from image_preprocessing_detector.detection.handwriting_detector import (
    HandwritingDetectionResult,
    HandwritingDetector,
    detect_handwriting,
)
from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityDetector,
    BinarizationQualityResult,
    BleedThroughDetector,
    BleedThroughResult,
    BlurDetectionResult,
    BlurDetector,
    BlurMetrics,
    ContrastDetectionResult,
    ContrastDetector,
    IlluminationDetectionResult,
    IlluminationDetector,
    IlluminationType,
    JPEGBlockinessDetector,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    NoiseDetector,
    NoiseMetrics,
    NoiseType,
    ProblemRegion,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    compute_laplacian_variance,
    detect_binarization_quality,
    detect_bleed_through,
    detect_blur,
    detect_contrast,
    detect_illumination,
    detect_jpeg_blockiness,
    detect_noise,
    detect_skew,
    estimate_noise_mad,
    normalize_blur_score,
    normalize_noise_score,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    DiscrepancyMetrics,
    EscalationDecision,
    MLIQADetector,
    MLIQAScores,
    ModelType,
    UncertaintyMetrics,
    discrepancy_metrics_to_dict,
    ml_iqa_scores_to_dict,
    teacher_iqa_to_dict,
    uncertainty_metrics_to_dict,
)
from image_preprocessing_detector.detection.ood_detector import (
    EmbeddingOODDetector,
    OODResult,
)
from image_preprocessing_detector.detection.orientation_detector import (
    OrientationConfig,
    OrientationDetector,
    OrientationVote,
    correct_orientation,
    detect_orientation,
)
from image_preprocessing_detector.detection.script_detector import (
    ScriptDetectorHeuristic,
    detect_script_heuristic,
)
from image_preprocessing_detector.detection.shadow_detector import (
    ShadowDetectionResult,
    ShadowDetector,
    detect_shadows,
)
from image_preprocessing_detector.detection.table_complexity import (
    TableComplexityAnalyzer,
    analyze_table_complexity,
)
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)
from image_preprocessing_detector.detection.warping_detector import (
    WarpingDetectionResult,
    WarpingDetector,
    detect_warping_distortion,
)

# DocLayout-YOLO detector (Phase 6)
# Import with try/except to allow graceful degradation when ML deps unavailable
try:
    from image_preprocessing_detector.detection.doclayout_yolo import (
        DetectedElement,
        DocLayoutClass,
        DocLayoutYOLODetector,
        LayoutDetectionResult,
        detect_layout,
        get_doclayout_yolo_model_info,
        is_doclayout_yolo_available,
    )

    _has_doclayout_yolo = True
except ImportError:
    _has_doclayout_yolo = False

__all__ = [
    # Classical IQA
    "BinarizationQualityDetector",
    # Deskew pipeline
    "DeskewConfig",
    "DeskewPipeline",
    "DeskewResult",
    "BinarizationQualityResult",
    "BleedThroughDetector",
    "BleedThroughResult",
    "BlurDetectionResult",
    "BlurDetector",
    "BlurMetrics",
    "ClassicalIQAScores",
    # Discrepancy threshold tuning (Phase 4.9)
    "ClassicalScoreAdapter",
    "ClassicalScores",
    "ContrastDetectionResult",
    "ContrastDetector",
    "Device",
    "DiscrepancyAnalyzer",
    "DiscrepancyMetrics",
    "DiscrepancyResult",
    "DiscrepancyThresholds",
    "EscalationDecision",
    "EscalationReason",
    "IlluminationDetectionResult",
    "IlluminationDetector",
    "IlluminationType",
    "JPEGBlockinessDetector",
    "JPEGBlockinessResult",
    "MLIQADetector",
    "MLIQAScores",
    "MLScores",
    "ModelType",
    "NoiseDetectionResult",
    "NoiseDetector",
    "NoiseMetrics",
    "NoiseType",
    # Orientation detection (Phase 8)
    "OrientationConfig",
    "OrientationDetector",
    "OrientationVote",
    "ProblemRegion",
    "Severity",
    "SkewDetectionResult",
    "SkewDetector",
    "TextDetectionResult",
    "TextGate",
    "ThresholdConfig",
    "UncertaintyMetrics",
    "compute_laplacian_variance",
    "create_discrepancy_analyzer",
    "detect_binarization_quality",
    "detect_bleed_through",
    "detect_blur",
    "detect_contrast",
    "detect_illumination",
    "detect_jpeg_blockiness",
    "detect_noise",
    "detect_orientation",
    "detect_skew",
    "detect_text",
    "correct_orientation",
    "discrepancy_metrics_to_dict",
    "estimate_noise_mad",
    "ml_iqa_scores_to_dict",
    "normalize_blur_score",
    "normalize_noise_score",
    "teacher_iqa_to_dict",
    "uncertainty_metrics_to_dict",
    # Warping detection (Stream 2)
    "WarpingDetectionResult",
    "WarpingDetector",
    "detect_warping_distortion",
    # Stream 2: Heuristic detectors
    "BlankPageDetector",
    "BlankPageResult",
    "detect_blank_page",
    "CodeDetectionResult",
    "CodeDetector",
    "detect_code",
    "HandwritingDetectionResult",
    "HandwritingDetector",
    "detect_handwriting",
    "ScriptDetectorHeuristic",
    "detect_script_heuristic",
    "ShadowDetectionResult",
    "ShadowDetector",
    "detect_shadows",
    "TableComplexityAnalyzer",
    "analyze_table_complexity",
    # OOD detection and cross-model agreement (Phase 10)
    "CategoryDistribution",
    "CrossModelCalibrator",
    "CrossModelValidator",
    "EmbeddingOODDetector",
    "OODResult",
    "ReliabilityResult",
    "ValidatorConfig",
    "ValidatorScore",
    "reliability_result_to_dict",
]

# Add DocLayout-YOLO exports if available
if _has_doclayout_yolo:
    __all__.extend(
        [
            # DocLayout-YOLO (Phase 6)
            "DetectedElement",
            "DocLayoutClass",
            "DocLayoutYOLODetector",
            "LayoutDetectionResult",
            "detect_layout",
            "get_doclayout_yolo_model_info",
            "is_doclayout_yolo_available",
        ]
    )
