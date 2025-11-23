"""Detection modules for image quality assessment and document analysis.

Phase 1: Text gate and classical IQA methods
Phase 2-3: ML-based IQA (teacher-student ResNet)
Phase 6: Layout-lite detection (YOLOv8-nano)
"""

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    BlurDetector,
    ContrastDetectionResult,
    ContrastDetector,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    detect_blur,
    detect_contrast,
    detect_skew,
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
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)

__all__ = [
    "BlurDetectionResult",
    "BlurDetector",
    "ClassicalIQAScores",
    "ContrastDetectionResult",
    "ContrastDetector",
    "Device",
    "DiscrepancyMetrics",
    "EscalationDecision",
    "MLIQADetector",
    "MLIQAScores",
    "ModelType",
    "Severity",
    "SkewDetectionResult",
    "SkewDetector",
    "TextDetectionResult",
    "TextGate",
    "UncertaintyMetrics",
    "detect_blur",
    "detect_contrast",
    "detect_skew",
    "detect_text",
    "discrepancy_metrics_to_dict",
    "ml_iqa_scores_to_dict",
    "teacher_iqa_to_dict",
    "uncertainty_metrics_to_dict",
]
