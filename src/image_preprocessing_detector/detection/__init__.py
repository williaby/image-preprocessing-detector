"""
Detection modules for image quality assessment and document analysis.

Phase 1: Text gate and classical IQA methods
Phase 2-3: ML-based detection (YOLOv8, PyTorch)
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
from image_preprocessing_detector.detection.text_gate import (
    TextDetectionResult,
    TextGate,
    detect_text,
)

__all__ = [
    # Text gate
    "TextGate",
    "TextDetectionResult",
    "detect_text",
    # Classical IQA
    "SkewDetector",
    "SkewDetectionResult",
    "BlurDetector",
    "BlurDetectionResult",
    "ContrastDetector",
    "ContrastDetectionResult",
    "Severity",
    "detect_skew",
    "detect_blur",
    "detect_contrast",
]
