"""Image correction operations with guardrails.

Provides correction classes for detected image quality issues:
- DeskewCorrector: Rotation correction for skewed documents
- ContrastEnhancer: CLAHE-based contrast enhancement
- Sharpener: Unsharp mask for blur correction
- Denoiser: NLMeans noise reduction (Phase 4)
- BinarizationCorrector: Adaptive thresholding (Phase 4)
- IlluminationNormalizer: Morphological illumination normalization (Phase 4)
- BleedThroughSuppressor: Cross-channel bleed-through removal (Phase 4)

All correctors include guardrails to prevent quality degradation.
"""

from image_preprocessing_detector.correction.corrections import (
    # Core correction classes
    BinarizationCorrector,
    BleedThroughSuppressor,
    ContrastEnhancer,
    CorrectionResult,
    Denoiser,
    DeskewCorrector,
    IlluminationNormalizer,
    Sharpener,
    # Convenience functions
    correct_binarization,
    correct_skew,
    denoise_image,
    enhance_contrast,
    normalize_illumination,
    sharpen_image,
    suppress_bleed_through,
)

__all__ = [
    # Core classes
    "BinarizationCorrector",
    "BleedThroughSuppressor",
    "ContrastEnhancer",
    "CorrectionResult",
    "Denoiser",
    "DeskewCorrector",
    "IlluminationNormalizer",
    "Sharpener",
    # Convenience functions
    "correct_binarization",
    "correct_skew",
    "denoise_image",
    "enhance_contrast",
    "normalize_illumination",
    "sharpen_image",
    "suppress_bleed_through",
]
