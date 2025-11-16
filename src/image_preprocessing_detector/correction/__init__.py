"""Image correction operations with guardrails.

Phase 1: Classical corrections (deskew, CLAHE, sharpening)
Phase 2-3: ML-based enhancements
"""

from image_preprocessing_detector.correction.corrections import (
    ContrastEnhancer,
    CorrectionResult,
    DeskewCorrector,
    Sharpener,
    correct_skew,
    enhance_contrast,
    sharpen_image,
)

__all__ = [
    "ContrastEnhancer",
    "CorrectionResult",
    "DeskewCorrector",
    "Sharpener",
    "correct_skew",
    "enhance_contrast",
    "sharpen_image",
]
