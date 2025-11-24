"""Detection modules for image quality assessment and document analysis.

Phase 1: Text gate and classical IQA methods
Phase 2-3: ML-based detection (DocLayout-YOLO, PyTorch)

Model configuration: configs/models/doclayout_yolo.yaml
"""

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    BlurDetector,
    ContrastDetectionResult,
    ContrastDetector,
    IlluminationDetectionResult,
    IlluminationDetector,
    IlluminationType,
    NoiseDetectionResult,
    NoiseDetector,
    NoiseType,
    Severity,
    SkewDetectionResult,
    SkewDetector,
    detect_blur,
    detect_contrast,
    detect_illumination,
    detect_noise,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)

__all__ = [
    # Classical IQA
    "BlurDetectionResult",
    "BlurDetector",
    "ContrastDetectionResult",
    "ContrastDetector",
    "IlluminationDetectionResult",
    "IlluminationDetector",
    "IlluminationType",
    "NoiseDetectionResult",
    "NoiseDetector",
    "NoiseType",
    "Severity",
    "SkewDetectionResult",
    "SkewDetector",
    # Text gate
    "TextDetectionResult",
    "TextGate",
    # Convenience functions
    "detect_blur",
    "detect_contrast",
    "detect_illumination",
    "detect_noise",
    "detect_skew",
    "detect_text",
]
