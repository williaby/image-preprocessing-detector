---
schema_type: common
title: "Correction Pipeline"
description: "Guide to image correction operations and best practices"
tags: [guide, correction, image_processing, documentation]
status: published
owner: "cv-team"
authors:
  - name: "Byron Williams"
purpose: "Explain correction algorithms, guardrails, and best practices for image preprocessing."
---

The correction pipeline applies targeted fixes to detected quality issues using OpenCV-based algorithms with built-in guardrails to prevent over-correction.

## Overview

The correction pipeline provides four main operations:

1. **Deskew**: Correct rotation and alignment
2. **CLAHE**: Adaptive contrast enhancement
3. **Sharpening**: Reduce blur with unsharp mask
4. **Denoising**: Reduce noise while preserving detail

All corrections include **guardrails** to validate improvements and prevent degradation.

## Correction Workflow

```text
Detected Issues
      │
      ▼
┌──────────────┐
│  Prioritize  │  Critical → High → Medium
└──────┬───────┘
      │
      ▼
┌──────────────┐
│Apply Deskew  │  First: Geometric corrections
└──────┬───────┘
      │
      ▼
┌──────────────┐
│Apply CLAHE   │  Second: Contrast enhancement
└──────┬───────┘
      │
      ▼
┌──────────────┐
│  Sharpen     │  Third: Blur reduction
└──────┬───────┘
      │
      ▼
┌──────────────┐
│  Denoise     │  Last: Noise reduction
└──────┬───────┘
      │
      ▼
┌──────────────┐
│   Validate   │  Check improvements with guardrails
└──────┬───────┘
      │
      ▼
  Corrected Image
```text

## Deskew Correction

### Algorithm

**Method**: Affine rotation based on detected skew angle

**Steps**:

1. Detect skew angle using Hough transform
2. Compute rotation matrix
3. Apply affine transformation
4. Fill borders with white background

### Usage

```python
from image_preprocessing_detector.correction import apply_deskew

# Apply deskew
corrected, transform_info = apply_deskew(
    image,
    angle=-2.5,  # Detected skew angle
)

if transform_info["success"]:
    print(f"Deskewed by {angle}°")
```text

### Guardrails

**Angle Validation**:

- Rejects |angle| > 45° (likely detection error)
- Warns for |angle| > 10° (unusual skew)

**Border Check**:

- Validates no excessive black borders
- Ensures content preservation

**Quality Validation**:

- Compares before/after edge strength
- Rejects if content lost

### Parameters

- **angle**: Rotation angle in degrees (-45 to +45)

### Performance

- **Time**: ~200ms (CPU)
- **Memory**: 2× image size (temporary buffer)

## Contrast Enhancement

### Algorithm

**Method**: CLAHE (Contrast Limited Adaptive Histogram Equalization)

**Benefits**:

- Local contrast enhancement
- Prevents over-amplification
- Preserves details

### Usage

```python
from image_preprocessing_detector.correction import apply_contrast_enhancement

# Apply CLAHE
corrected, transform_info = apply_contrast_enhancement(
    image,
    clip_limit=2.0,        # Contrast limiting
    tile_grid_size=(8, 8),  # Grid size
)

if transform_info["success"]:
    print("Contrast enhanced")
```text

### Guardrails

**Clip Limit Bounds**:

- Range: 0.5 - 4.0
- Default: 2.0
- Higher = more contrast

**Histogram Validation**:

- Ensures improved distribution
- Checks for over-enhancement

**Content Preservation**:

- Validates perceptual quality
- Rejects if artifacts introduced

### Parameters

- **clip_limit**: Contrast limiting (1.0-4.0, default: 2.0)
- **tile_grid_size**: Grid size (default: (8, 8))

### Performance

- **Time**: ~100ms (CPU)
- **Memory**: Minimal overhead

## Sharpening

### Algorithm

**Method**: Unsharp Mask

**Steps**:

1. Apply Gaussian blur to create smoothed version
2. Subtract smoothed from original
3. Add weighted difference back to original

**Formula**: `sharp = original + amount × (original - blurred)`

### Usage

```python
from image_preprocessing_detector.correction import apply_sharpening

# Apply unsharp mask
corrected, transform_info = apply_sharpening(
    image,
    kernel_size=5,    # Gaussian kernel size
    sigma=1.0,        # Gaussian sigma
    amount=1.5,       # Sharpening strength
)

if transform_info["success"]:
    print("Image sharpened")
```text

### Guardrails

**Noise Amplification Check**:

- Monitors high-frequency content
- Prevents noise amplification

**Amount Limits**:

- Range: 0.5 - 3.0
- Default: 1.5
- Higher = stronger sharpening

**Edge Preservation**:

- Validates edge integrity
- Rejects if edges degraded

### Parameters

- **kernel_size**: Gaussian kernel (3, 5, 7)
- **sigma**: Gaussian sigma (0.5-2.0)
- **amount**: Sharpening strength (0.5-3.0)

### Performance

- **Time**: ~150ms (CPU)
- **Memory**: 2× image size

## Denoising

### Algorithm

**Method**: Non-Local Means Denoising

**Benefits**:

- Preserves edges and details
- Reduces various noise types
- Minimal artifacts

**Limitations**:

- Computationally expensive
- May over-smooth with high strength

### Usage

```python
from image_preprocessing_detector.correction import apply_denoising

# Apply denoising
corrected, transform_info = apply_denoising(
    image,
    h=10,              # Filter strength
    template_size=7,   # Template patch size
    search_size=21,    # Search window size
)

if transform_info["success"]:
    print("Noise reduced")
```text

### Guardrails

**Detail Preservation**:

- Checks for excessive smoothing
- Validates text readability

**Strength Limits**:

- Range: 3 - 15
- Default: 10
- Higher = stronger denoising

**Content Validation**:

- Ensures edges preserved
- Rejects if details lost

### Parameters

- **h**: Filter strength (3-15, default: 10)
- **template_size**: Patch size (5, 7, 9)
- **search_size**: Search window (15, 21, 27)

### Performance

- **Time**: ~500ms (CPU) - Most expensive
- **Memory**: High (search window buffering)

## Complete Pipeline Example

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
    apply_denoising,
)

def correct_document(image):
    """Apply full correction pipeline."""
    corrected = image.copy()
    transforms = []

    # 1. Deskew (geometric correction first)
    angle, conf = detect_skew(image)
    if abs(angle) > 0.5 and conf > 0.7:
        corrected, info = apply_deskew(corrected, angle)
        if info["success"]:
            transforms.append(info)

    # 2. Enhance contrast
    is_low, score = assess_contrast(corrected)
    if is_low:
        corrected, info = apply_contrast_enhancement(corrected)
        if info["success"]:
            transforms.append(info)

    # 3. Sharpen (if blurry)
    is_blurry, var = detect_blur(corrected)
    if is_blurry:
        corrected, info = apply_sharpening(corrected)
        if info["success"]:
            transforms.append(info)

    # 4. Denoise (optional, expensive)
    # Only if severe noise detected
    # corrected, info = apply_denoising(corrected)

    return corrected, transforms
```text

## Transform History Tracking

All corrections are tracked for audit trails:

```python
from image_preprocessing_detector.schema import DocumentMetadata

metadata = DocumentMetadata(
    source_file="document.pdf",
    num_pages=1,
    processing_version="0.1.0",
)

# Apply corrections
corrected, transforms = correct_document(image)

# Add to metadata
for transform in transforms:
    metadata.transform_history.append(transform)

# Export history
print(metadata.model_dump_json(indent=2))
```text

**Example Transform**:

```json
{
  "transform_type": "deskew",
  "parameters": {"angle": -2.5},
  "timestamp": "2025-11-08T12:00:00Z",
  "success": true
}
```text

## Best Practices

### 1. Sequential Order

**Always apply corrections in order**:

1. Deskew (geometric)
2. Contrast (intensity)
3. Sharpen (detail)
4. Denoise (noise)

**Why?** Each operation affects subsequent ones.

### 2. Validate Success

**Check transform_info before proceeding**:

```python
corrected, info = apply_deskew(image, angle)

if info["success"]:
    # Use corrected image
    pass
else:
    # Use original image
    print(f"Deskew failed: {info.get('error')}")
```text

### 3. Track History

**Maintain complete transform history**:

```python
# Add all transforms to metadata
for transform in transforms:
    metadata.transform_history.append(transform)

# Enable audit trail
metadata.to_json_file("output.json")
```text

### 4. Test Parameters

**Tune for your use case**:

```python
# Conservative sharpening
apply_sharpening(image, amount=1.0)

# Aggressive sharpening
apply_sharpening(image, amount=2.5)

# Test and compare results
```text

### 5. Use Dry Run

**Test detection without correction**:

```bash
poetry run imgprep process input.pdf --output result.json --dry-run
```text

## Performance Optimization

### Operation Costs

| Operation | Time (CPU) | GPU Benefit | Priority |
|-----------|-----------|-------------|----------|
| **Deskew** | ~200ms | Low | High |
| **CLAHE** | ~100ms | Low | Medium |
| **Sharpen** | ~150ms | Low | Medium |
| **Denoise** | ~500ms | **High** | Low |

### Recommendations

1. **Skip denoising** for clean images (expensive)
2. **Use batch processing** for multiple pages
3. **Consider GPU** for denoising (Phase 2+)
4. **Profile first** to identify bottlenecks

## Troubleshooting

### Over-Correction

**Symptom**: Artifacts, unnatural appearance

**Solution**: Reduce correction strength

```python
# Reduce sharpening amount
apply_sharpening(image, amount=1.0)  # Instead of 1.5

# Reduce CLAHE clip limit
apply_contrast_enhancement(image, clip_limit=1.5)  # Instead of 2.0
```text

### Under-Correction

**Symptom**: Issues still visible

**Solution**: Increase correction strength or adjust thresholds

```python
# Stronger sharpening
apply_sharpening(image, amount=2.0)

# Higher clip limit
apply_contrast_enhancement(image, clip_limit=3.0)
```text

### Guardrail Failures

**Symptom**: `transform_info["success"]` is False

**Solution**: Check error message and adjust parameters

```python
corrected, info = apply_deskew(image, angle)

if not info["success"]:
    print(f"Error: {info.get('error', 'Unknown')}")
    # Try alternative approach or skip correction
```text

## See Also

- [Detection API](../api/detection.md) - Quality issue detection
- [Correction API](../api/correction.md) - Correction functions
- [IQA Guide](iqa.md) - Quality assessment
- [System Overview](overview.md) - Architecture
