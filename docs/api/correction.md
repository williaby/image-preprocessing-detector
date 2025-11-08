---
schema_type: common
title: "Correction API"
description: "OpenCV-based image corrections with guardrails"
tags: [api_reference, documentation, image_processing, correction]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the correction module for applying image preprocessing operations."
---

The correction module provides OpenCV-based algorithms for fixing detected quality issues with built-in guardrails to prevent over-correction.

## Overview

The correction pipeline applies targeted fixes based on detected issues:

- **Deskew**: Rotate images to correct skew
- **CLAHE**: Adaptive histogram equalization for contrast
- **Sharpening**: Unsharp mask for blur correction
- **Denoising**: Non-local means denoising

All corrections include **guardrails** to validate improvements and prevent degradation.

## Module Reference

::: image_preprocessing_detector.correction.corrections
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Usage Examples

### Deskew Correction

```python
from image_preprocessing_detector.correction import apply_deskew
import numpy as np

# Apply deskew
corrected_image, transform_info = apply_deskew(
    image,
    angle=-2.5,  # Detected skew angle
)

print(f"Transform: {transform_info}")
# {'transform_type': 'deskew', 'angle': -2.5, 'success': True}
```

### Contrast Enhancement

```python
from image_preprocessing_detector.correction import apply_contrast_enhancement

# Apply CLAHE
corrected_image, transform_info = apply_contrast_enhancement(
    image,
    clip_limit=2.0,      # CLAHE clip limit
    tile_grid_size=(8, 8),  # Grid size
)

if transform_info["success"]:
    print("Contrast enhanced successfully")
```

### Blur Correction

```python
from image_preprocessing_detector.correction import apply_sharpening

# Apply unsharp mask
corrected_image, transform_info = apply_sharpening(
    image,
    kernel_size=5,    # Gaussian kernel size
    sigma=1.0,        # Gaussian sigma
    amount=1.5,       # Sharpening amount
)
```

### Denoising

```python
from image_preprocessing_detector.correction import apply_denoising

# Apply non-local means denoising
corrected_image, transform_info = apply_denoising(
    image,
    h=10,              # Filter strength
    template_size=7,   # Template patch size
    search_size=21,    # Search window size
)
```

### Complete Correction Pipeline

```python
from image_preprocessing_detector.detection import (
    detect_blur,
    detect_skew,
    assess_contrast,
)
from image_preprocessing_detector.correction import (
    apply_deskew,
    apply_contrast_enhancement,
    apply_sharpening,
)
from image_preprocessing_detector.schema import TransformHistory

def correct_all_issues(image):
    """Apply all necessary corrections."""
    corrected = image.copy()
    transforms = []

    # Fix skew
    angle, conf = detect_skew(image)
    if abs(angle) > 0.5 and conf > 0.7:
        corrected, info = apply_deskew(corrected, angle)
        if info["success"]:
            transforms.append(info)

    # Enhance contrast
    is_low, score = assess_contrast(corrected)
    if is_low:
        corrected, info = apply_contrast_enhancement(corrected)
        if info["success"]:
            transforms.append(info)

    # Fix blur
    is_blurry, var = detect_blur(corrected)
    if is_blurry:
        corrected, info = apply_sharpening(corrected)
        if info["success"]:
            transforms.append(info)

    return corrected, transforms
```

## Guardrails

All correction functions include validation to ensure improvements:

### Deskew Guardrails

- **Angle limits**: Rejects angles > 45 degrees
- **Border validation**: Checks for excessive black borders
- **Content preservation**: Validates no significant content loss

### Contrast Guardrails

- **Histogram validation**: Ensures improved distribution
- **Clip limit bounds**: Prevents over-enhancement (0.5 - 4.0)
- **Content preservation**: Validates perceptual quality

### Sharpening Guardrails

- **Noise amplification check**: Monitors high-frequency content
- **Amount limits**: Prevents over-sharpening (0.5 - 3.0)
- **Edge preservation**: Validates edge integrity

### Denoising Guardrails

- **Detail preservation**: Checks for excessive smoothing
- **Strength limits**: Bounds filter strength (3 - 15)
- **Content validation**: Ensures text readability

## Transform History

All corrections are tracked for audit trails:

```python
from image_preprocessing_detector.schema import DocumentMetadata

metadata = DocumentMetadata(
    source_file="document.pdf",
    num_pages=1,
    processing_version="0.1.0",
)

# Apply corrections
corrected, transforms = correct_all_issues(image)

# Add to metadata
for transform in transforms:
    metadata.transform_history.append(transform)

# Export history
print(metadata.transform_history)
```

## Parameters and Tuning

### Deskew

- **angle**: Rotation angle in degrees (typically -45 to +45)

### CLAHE

- **clip_limit**: Contrast limiting (1.0-4.0, default: 2.0)
- **tile_grid_size**: Grid size (default: (8, 8))

### Sharpening

- **kernel_size**: Gaussian kernel size (3, 5, 7)
- **sigma**: Gaussian sigma (0.5-2.0)
- **amount**: Sharpening strength (0.5-3.0)

### Denoising

- **h**: Filter strength (3-15, default: 10)
- **template_size**: Patch size (5, 7, 9)
- **search_size**: Search window (15, 21, 27)

## Performance

| Operation | Time (CPU) | Notes |
|-----------|-----------|-------|
| **Deskew** | ~200ms | Affine transform |
| **CLAHE** | ~100ms | Adaptive equalization |
| **Sharpening** | ~150ms | Unsharp mask |
| **Denoising** | ~500ms | Non-local means (CPU-intensive) |

## Best Practices

1. **Validate First**: Always run detection before correction
2. **Check Success**: Verify `transform_info["success"]` before applying
3. **Track History**: Maintain transform history for audit trails
4. **Sequential Order**: Apply corrections in order: deskew → contrast → sharpen → denoise
5. **Test Thresholds**: Tune parameters for your specific use case

## See Also

- [Detection API](detection.md) - Quality issue detection
- [Schema API](schema.md) - TransformHistory model
- [User Guide: Correction](../guides/correction.md) - Correction pipeline overview
