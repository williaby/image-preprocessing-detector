"""Detection modules for image quality assessment and document analysis.

Phase 1: Text gate and classical IQA methods
Phase 2-3: ML-based detection (DocLayout-YOLO, PyTorch)
Phase 4.9: Discrepancy threshold tuning for ML-classical comparison

Model configuration: configs/models/doclayout_yolo.yaml
"""

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
from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityDetector,
    BinarizationQualityResult,
    BleedThroughDetector,
    BleedThroughResult,
    BlurDetectionResult,
    BlurDetector,
    ContrastDetectionResult,
    ContrastDetector,
    IlluminationDetectionResult,
    IlluminationDetector,
    IlluminationType,
    JPEGBlockinessDetector,
    JPEGBlockinessResult,
    NoiseDetectionResult,
    NoiseDetector,
    NoiseType,
    ProblemRegion,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    detect_binarization_quality,
    detect_bleed_through,
    detect_blur,
    detect_contrast,
    detect_illumination,
    detect_jpeg_blockiness,
    detect_noise,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)

__all__ = [
    # Discrepancy threshold tuning (Phase 4.9)
    "ClassicalScoreAdapter",
    "ClassicalScores",
    "DiscrepancyAnalyzer",
    "DiscrepancyResult",
    "DiscrepancyThresholds",
    "EscalationReason",
    "MLScores",
    "ThresholdConfig",
    "create_discrepancy_analyzer",
    # Classical IQA
    "BinarizationQualityDetector",
    "BinarizationQualityResult",
    "BleedThroughDetector",
    "BleedThroughResult",
    "BlurDetectionResult",
    "BlurDetector",
    "ContrastDetectionResult",
    "ContrastDetector",
    "IlluminationDetectionResult",
    "IlluminationDetector",
    "IlluminationType",
    "JPEGBlockinessDetector",
    "JPEGBlockinessResult",
    "NoiseDetectionResult",
    "NoiseDetector",
    "NoiseType",
    "ProblemRegion",
    "Severity",
    "SkewDetectionResult",
    "SkewDetector",
    # Text gate
    "TextDetectionResult",
    "TextGate",
    # Convenience functions
    "detect_binarization_quality",
    "detect_bleed_through",
    "detect_blur",
    "detect_contrast",
    "detect_illumination",
    "detect_jpeg_blockiness",
    "detect_noise",
    "detect_skew",
    "detect_text",
]
