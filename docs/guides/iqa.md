---
schema_type: common
title: "Image Quality Assessment"
description: "Comprehensive guide to image quality detection algorithms and methods"
tags: [guide, iqa, computer_vision, documentation]
status: published
owner: "cv-team"
authors:
  - name: "Byron Williams"
purpose: "Explain image quality assessment methods, algorithms, and best practices."
---

Image Quality Assessment (IQA) is the process of detecting and quantifying quality issues in images and documents. This guide covers the IQA algorithms used in the Image Preprocessing Detector.

## Overview

The system uses a **two-tier IQA approach**:

1. **Classical IQA**: Computer vision algorithms (Phase 1 - Current)
2. **ML-based IQA**: Deep learning models (Phase 2 - Planned)

## Classical IQA Methods

### 1. Blur Detection

**Method**: Laplacian Variance

**How it works**:

1. Apply Laplacian filter (edge detector)
2. Compute variance of filtered image
3. Low variance indicates blur

**Threshold**: 100.0 (default)

- Below threshold → Blurry
- Above threshold → Sharp

**Example**:

```python
from image_preprocessing_detector.detection import detect_blur

is_blurry, variance = detect_blur(image, threshold=100.0)

if is_blurry:
    print(f"Blurry image (variance: {variance:.2f})")
else:
    print(f"Sharp image (variance: {variance:.2f})")
```

**Performance**: ~50ms per image

**Strengths**:

- Fast and reliable
- No training required
- Works on grayscale

**Limitations**:

- Sensitive to noise
- Doesn't distinguish motion blur from defocus
- Global metric (doesn't detect local blur)

### 2. Skew Detection

**Method**: Hough Transform Line Detection

**How it works**:

1. Convert to grayscale and apply edge detection
2. Detect lines using Hough transform
3. Compute dominant angle
4. Estimate rotation needed

**Threshold**: 0.7 confidence (default)

**Example**:

```python
from image_preprocessing_detector.detection import detect_skew

angle, confidence = detect_skew(image, threshold=0.7)

if abs(angle) > 0.5 and confidence > 0.7:
    print(f"Skew detected: {angle:.2f}° (confidence: {confidence:.2f})")
```

**Performance**: ~100ms per image

**Strengths**:

- Accurate for text documents
- Provides confidence score
- Handles multi-line documents

**Limitations**:

- Requires structured content (lines of text)
- May fail on artistic layouts
- Computationally intensive

### 3. Contrast Assessment

**Method**: Histogram Analysis

**How it works**:

1. Convert to grayscale
2. Compute intensity histogram
3. Analyze distribution spread
4. Compute normalized contrast score

**Threshold**: 0.3 (default)

- Below threshold → Low contrast
- Above threshold → Normal/high contrast

**Example**:

```python
from image_preprocessing_detector.detection import assess_contrast

is_low, score = assess_contrast(image, threshold=0.3)

if is_low:
    print(f"Low contrast (score: {score:.2f})")
```

**Performance**: ~20ms per image

**Strengths**:

- Fast computation
- Intuitive metric
- Works on all image types

**Limitations**:

- Global metric (doesn't detect local contrast issues)
- Sensitive to image content
- May flag artistic low-contrast as issues

## Hybrid IQA Approach

**Problem**: Text documents contain embedded images (tables, figures) that need independent quality assessment.

**Solution**: Run IQA on each detected document element.

### Workflow

```text
1. Detect document layout (YOLOv8)
   └── Tables, images, figures, handwriting

2. For each detected element:
   ├── Extract bounding box region
   ├── Run classical IQA
   └── Store per-element quality issues

3. Generate hybrid metadata
   └── Page-level + per-element quality
```text

**Example**:

```python
from image_preprocessing_detector.schema import DocumentElement, DetectedIssue

element = DocumentElement(
    element_type="table",
    bbox=[100, 200, 800, 600],
    confidence=0.95,
    quality_issues=[
        DetectedIssue(
            issue_type="blur",
            severity="medium",
            confidence=0.85,
            location=[100, 200, 800, 600],
        )
    ],
)
```

**Benefits**:

- Accurate quality assessment for complex documents
- Identifies problematic regions
- Supports selective correction

**See**: [Architecture Correction](../../ARCHITECTURE_CORRECTION.md)

## ML-based IQA (Phase 2)

**Planned implementation** using deep learning models.

### Architecture

**Models**: MobileNetV3 or EfficientNet

**Task**: Multi-label classification

**Labels**:

- Blur (motion, defocus)
- Noise (gaussian, salt-pepper)
- Compression artifacts
- Low contrast
- Skew
- Low resolution

**Target Performance**: mAP > 0.88

### Training Data

**Datasets**:

- KADID-10k: Image quality assessment
- LIVE-IQA: Distortion types
- TID2013: Quality metrics
- Custom synthetic data

**Augmentation**:

- Albumentations pipeline
- Realistic degradation simulation

### Inference

**Optimization**: ONNX Runtime

**Latency Target**: < 50ms per image (GPU)

**Batch Processing**: 32 images per batch

## Quality Issue Types

### Blur

**Types**:

- Motion blur (camera shake)
- Defocus blur (out of focus)
- Gaussian blur (smoothing)

**Detection**: Laplacian variance

**Severity Levels**:

- High: variance < 50
- Medium: variance 50-100
- Low: variance 100-150

### Skew

**Definition**: Rotation angle from horizontal

**Detection**: Hough transform

**Severity Levels**:

- High: |angle| > 2.0°
- Medium: 0.5° < |angle| ≤ 2.0°
- Low: |angle| ≤ 0.5°

### Low Contrast

**Definition**: Poor intensity distribution

**Detection**: Histogram analysis

**Severity Levels**:

- High: score < 0.2
- Medium: 0.2 ≤ score < 0.3
- Low: 0.3 ≤ score < 0.5

### Noise

**Types** (Phase 2):

- Gaussian noise
- Salt-and-pepper noise
- Compression artifacts

**Detection**: ML-based (Phase 2)

## Best Practices

### 1. Threshold Tuning

Adjust thresholds based on your use case:

```bash
# Stricter blur detection (higher quality required)
poetry run imgprep process scan.pdf --output result.json \
  --blur-threshold 0.9

# More lenient for low-quality sources
poetry run imgprep process photo.jpg --output result.json \
  --blur-threshold 0.6
```

### 2. Dry Run Mode

Test detection without corrections:

```bash
poetry run imgprep process input.pdf --output result.json --dry-run
```

### 3. Validate Results

Check detected issues before applying corrections:

```python
from image_preprocessing_detector.schema import DocumentMetadata

metadata = DocumentMetadata.from_json_file("result.json")

for page in metadata.pages:
    print(f"Page {page.page_number}: {len(page.detected_issues)} issues")
    for issue in page.detected_issues:
        print(f"  - {issue.issue_type}: {issue.severity} (confidence: {issue.confidence})")
```

### 4. Selective Correction

Apply corrections only for specific issue types:

```python
# Only fix high-severity issues
high_severity = [
    issue for issue in page.detected_issues
    if issue.severity == "high"
]
```

## Performance Considerations

### Classical IQA Performance

| Algorithm | Time (CPU) | Memory |
|-----------|-----------|--------|
| **Blur Detection** | ~50ms | Low |
| **Skew Detection** | ~100ms | Low |
| **Contrast** | ~20ms | Low |
| **Total** | ~170ms | Low |

### ML IQA Performance (Phase 2)

| Configuration | Latency | Throughput |
|---------------|---------|------------|
| **CPU** | ~200ms | 5 img/sec |
| **GPU (T4)** | ~50ms | 20 img/sec |
| **GPU Batch** | ~30ms/img | 33 img/sec |

## Evaluation Metrics

### Detection Accuracy

**Metric**: Mean Average Precision (mAP)

**Target**: mAP > 0.88 (Phase 2)

**Datasets**: KADID-10k, LIVE-IQA

### Computational Efficiency

**Metric**: Latency and throughput

**Targets** (Phase 3):

- Latency < 150ms/page (GPU)
- Throughput > 6 pages/sec

## Troubleshooting

### False Positives

**Issue**: Clean images flagged as blurry

**Solution**: Lower threshold or tune for your content

```bash
poetry run imgprep process input.pdf --output result.json \
  --blur-threshold 0.7  # More lenient
```

### False Negatives

**Issue**: Poor quality images not detected

**Solution**: Raise threshold for stricter detection

```bash
poetry run imgprep process input.pdf --output result.json \
  --blur-threshold 0.9  # Stricter
```

### Performance Issues

**Issue**: Slow processing

**Solution**:

- Use dry-run mode for testing
- Process smaller batches
- Consider GPU acceleration (Phase 2+)

## See Also

- [Detection API](../api/detection.md) - IQA algorithms
- [Correction Guide](correction.md) - Fixing quality issues
- [System Overview](overview.md) - Architecture
