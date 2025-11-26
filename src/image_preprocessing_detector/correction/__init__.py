"""Image correction operations with guardrails.

Phase 1: Classical corrections (deskew, CLAHE, sharpening)
Phase 2-3: ML-based enhancements
Phase 8: Orientation correction (90°, 180°, 270° rotation)
"""

from image_preprocessing_detector.correction.corrections import (
    ContrastEnhancer,
    CorrectionResult,
    DeskewCorrector,
    OrientationCorrector,
    Sharpener,
    correct_orientation,
    correct_skew,
    enhance_contrast,
    sharpen_image,
)

__all__ = [
    "ContrastEnhancer",
    "CorrectionResult",
    "DeskewCorrector",
    "OrientationCorrector",
    "Sharpener",
    "correct_orientation",
    "correct_skew",
    "enhance_contrast",
    "sharpen_image",
]
