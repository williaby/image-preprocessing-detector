---
schema_type: common
title: "Detection API"
description: "Image quality assessment and text detection algorithms"
tags: [api_reference, documentation, iqa, computer_vision]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the detection module for quality assessment and text detection."
---

The detection module provides algorithms for assessing image quality and detecting text presence in documents.

## Overview

The detection pipeline uses a **text detection gate** to route documents to specialized processing:

- **Text Gate**: Fast heuristics to detect text presence
- **Classical IQA**: Computer vision algorithms for quality assessment (blur, skew, contrast)
- **(Phase 2+)**: ML-based IQA and YOLOv8 layout detection

## Text Gate

::: image_preprocessing_detector.detection.text_gate
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Classical Image Quality Assessment

::: image_preprocessing_detector.detection.iqa_classical
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Usage Examples

### Text Detection

```python
from image_preprocessing_detector.detection.text_gate import detect_text
import cv2

# Load image
image = cv2.imread("document.jpg")

# Detect text - returns TextDetectionResult
result = detect_text(image)

if result.has_text:
    print(f"Text detected (confidence: {result.confidence:.2f})")
    # Route to text-based processing
else:
    print(f"No text detected (confidence: {result.confidence:.2f})")
    # Route to image-only processing
```

### Blur Detection

```python
from image_preprocessing_detector.detection import detect_blur

# Detect blur
is_blurry, variance = detect_blur(
    image,
    threshold=100.0,  # Laplacian variance threshold
)

if is_blurry:
    print(f"Image is blurry (variance: {variance:.2f})")
```

### Skew Detection

```python
from image_preprocessing_detector.detection import detect_skew

# Detect skew angle
angle, confidence = detect_skew(
    image,
    threshold=0.5,  # Minimum confidence
)

if abs(angle) > 0.5:  # More than 0.5 degrees
    print(f"Skew detected: {angle:.2f} degrees (confidence: {confidence:.2f})")
```

### Contrast Assessment

```python
from image_preprocessing_detector.detection import assess_contrast

# Assess contrast
is_low_contrast, score = assess_contrast(
    image,
    threshold=0.3,  # Normalized contrast threshold
)

if is_low_contrast:
    print(f"Low contrast detected (score: {score:.2f})")
```

### Complete Detection Pipeline

```python
from image_preprocessing_detector.detection import (
    detect_text_presence,
    detect_blur,
    detect_skew,
    assess_contrast,
)
from image_preprocessing_detector.schema import DetectedIssue

def detect_all_issues(image, thresholds=None):
    """Run all detection algorithms."""
    issues = []

    # Text detection
    has_text, text_conf = detect_text_presence(image)

    # Quality assessment
    is_blurry, blur_var = detect_blur(image)
    if is_blurry:
        issues.append(DetectedIssue(
            issue_type="blur",
            severity="high" if blur_var < 50 else "medium",
            confidence=0.9,
            metadata={"laplacian_variance": blur_var},
        ))

    # Skew detection
    angle, skew_conf = detect_skew(image)
    if abs(angle) > 0.5 and skew_conf > 0.7:
        issues.append(DetectedIssue(
            issue_type="skew",
            severity="high" if abs(angle) > 2.0 else "medium",
            confidence=skew_conf,
            metadata={"angle_degrees": angle},
        ))

    # Contrast assessment
    is_low, contrast_score = assess_contrast(image)
    if is_low:
        issues.append(DetectedIssue(
            issue_type="low_contrast",
            severity="medium",
            confidence=0.85,
            metadata={"contrast_score": contrast_score},
        ))

    return issues, has_text
```

## Algorithm Details

### Text Detection Gate

**Method**: Ensemble of fast heuristics
- Stroke width analysis
- Connected component analysis
- Edge density patterns

**Performance**: < 10ms per page

### Blur Detection

**Method**: Laplacian variance
- Computes variance of Laplacian filter
- Low variance indicates blur
- Threshold: 100.0 (default)

### Skew Detection

**Method**: Hough transform
- Detects dominant lines
- Estimates rotation angle
- Confidence based on line strength

### Contrast Assessment

**Method**: Histogram analysis
- Analyzes intensity distribution
- Computes normalized contrast score
- Threshold: 0.3 (default)

## Thresholds and Tuning

Default thresholds can be adjusted based on your use case:

```python
# Stricter blur detection (higher threshold)
is_blurry, var = detect_blur(image, threshold=150.0)

# More lenient skew detection (lower confidence)
angle, conf = detect_skew(image, threshold=0.3)

# Custom contrast threshold
is_low, score = assess_contrast(image, threshold=0.4)
```

## Performance

| Operation | Time (CPU) | Notes |
|-----------|-----------|-------|
| **Text Gate** | < 10ms | Fast ensemble heuristics |
| **Blur Detection** | ~50ms | Laplacian variance |
| **Skew Detection** | ~100ms | Hough transform |
| **Contrast** | ~20ms | Histogram analysis |

## See Also

- [Schema API](schema.md) - DetectedIssue model
- [Correction API](correction.md) - Applying fixes
- [User Guide: IQA](../guides/iqa.md) - Quality assessment overview
