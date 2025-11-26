---
schema_type: common
title: "Model Cards"
description: "Detailed specifications for ML models in Project A"
tags:
  - reference
  - machine_learning
  - documentation
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document model architectures, training data, and performance metrics."
---

Detailed specifications for ML models used in Project A: Preprocessing & IQA.

## Overview

Project A uses a **teacher-student architecture** for learned IQA, combined with classical computer vision methods for deterministic quality assessment.

| Model | Architecture | Purpose | Production |
|-------|-------------|---------|------------|
| IQA Teacher | ResNet-50 | High-capacity training/validation | No |
| IQA Student | ResNet-18 | Fast production inference | Yes |
| Layout-Lite | DocLayout-YOLO | Coarse page classification | Yes |
| Classical CV | OpenCV | Deterministic IQA metrics | Yes |

---

## IQA Student Model (ResNet-18)

### Model Specification

| Property | Value |
|----------|-------|
| **Architecture** | ResNet-18 with multi-head output |
| **Input Size** | 224x224 RGB (normalized) |
| **Parameters** | ~11.7M |
| **Output Heads** | 4 (blur, noise, contrast, overall) |
| **Output Range** | 0-1 (quality scores) |
| **Format** | PyTorch (.pt), ONNX (.onnx), TorchScript |

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **mAP (IQA)** | 0.88+ | Multi-label on OHR-Bench |
| **Correlation (SSIM)** | 0.85+ | vs ground truth quality |
| **Inference Accuracy** | 94%+ | Binary quality classification |

### Latency Benchmarks

| Device | Latency (ms) | Throughput | Memory |
|--------|-------------|------------|--------|
| NVIDIA RTX 3080 | 8-12 | ~100 pages/sec | 0.5 GB |
| NVIDIA T4 | 15-25 | ~50 pages/sec | 0.5 GB |
| Intel i7-12700 (CPU) | 80-150 | ~8 pages/sec | 0.3 GB |
| AMD Ryzen 5800X (CPU) | 100-180 | ~6 pages/sec | 0.3 GB |
| Apple M2 (MPS) | 20-40 | ~30 pages/sec | 0.4 GB |

### Cost Analysis

| Deployment | Cost per 1M pages | Notes |
|------------|-------------------|-------|
| Local GPU | ~$0 | Amortized hardware |
| Local CPU | ~$0 | Slower but free |
| Modal T4 | ~$2-4 | $0.59/hr GPU |
| Modal A10 | ~$4-8 | $1.10/hr GPU |

### Usage

```python
from image_preprocessing_detector.detection.iqa_ml import IQAStudentModel

model = IQAStudentModel()
model.load("models/resnet18-iqa-v1.0.0.pt")

# Inference
scores = model.predict(image_array)  # Returns dict with quality scores
print(f"Blur: {scores['blur']:.2f}")
print(f"Overall: {scores['overall']:.2f}")
```text

---

## IQA Teacher Model (ResNet-50)

### Model Specification

| Property | Value |
|----------|-------|
| **Architecture** | ResNet-50 with multi-head output |
| **Input Size** | 224x224 RGB (normalized) |
| **Parameters** | ~25.6M |
| **Output Heads** | 4 (blur, noise, contrast, overall) |
| **Purpose** | Knowledge distillation, high-risk validation |

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **mAP (IQA)** | 0.92+ | Multi-label on OHR-Bench |
| **Correlation (SSIM)** | 0.90+ | vs ground truth quality |
| **Accuracy Uplift** | +3-5% | vs student on hard cases |

### Latency Benchmarks

| Device | Latency (ms) | Throughput | Memory |
|--------|-------------|------------|--------|
| NVIDIA RTX 3080 | 15-25 | ~50 pages/sec | 1.0 GB |
| NVIDIA T4 | 25-40 | ~30 pages/sec | 1.0 GB |
| Intel i7-12700 (CPU) | 300-500 | ~2 pages/sec | 0.6 GB |
| AMD Ryzen 5800X (CPU) | 400-600 | ~1.5 pages/sec | 0.6 GB |

### Gating Policy

The teacher model is **NOT used by default** in production. It is invoked only when:

1. **Explicit Request**: `enable_teacher=true` in API options
2. **High Uncertainty**: Student confidence < 0.7 on any quality dimension
3. **Discrepancy**: Student vs classical CV disagreement > 0.3
4. **High-Risk Document**: Complex layout or degraded quality signals

```python
# Gating logic pseudocode
def should_use_teacher(student_scores, classical_scores, options):
    if options.enable_teacher:
        return True
    if min(student_scores.values()) < UNCERTAINTY_THRESHOLD:  # 0.7
        return True
    if abs(student_scores['overall'] - classical_scores['overall']) > DISCREPANCY_THRESHOLD:  # 0.3
        return True
    return False
```text

### CPU Blocking Policy

**Teacher inference on CPU is BLOCKED by default** due to unacceptable latency (>500ms/page).

| Scenario | Allowed | Reason |
|----------|---------|--------|
| GPU available | Yes | Acceptable latency |
| CPU only, batch small | No | Blocked by default |
| CPU only, override | Yes | `IMGPREP_ALLOW_TEACHER_CPU=true` |
| Modal available | Yes | Falls back to Modal GPU |

**Override** (not recommended for production):

```bash
export IMGPREP_ALLOW_TEACHER_CPU=true
```text

### Cost Analysis

| Deployment | Cost per 1M pages | Notes |
|------------|-------------------|-------|
| Local GPU | ~$0 | Only for flagged pages |
| Modal T4 | ~$4-8 | ~5% of pages flagged |
| Modal A10 | ~$8-15 | Premium accuracy |

---

## Layout-Lite Model (DocLayout-YOLO)

### Model Specification

| Property | Value |
|----------|-------|
| **Architecture** | YOLOv10-based (DocLayout-YOLO) |
| **Input Size** | 1024x1024 |
| **Parameters** | ~8M |
| **Output Classes** | 6 coarse categories |

### Output Classes

| Class | Description | Use in Routing |
|-------|-------------|----------------|
| `dense_text` | Text-heavy pages | Fast OCR path |
| `multi_column` | Multi-column layout | Complex OCR path |
| `table_heavy` | Contains tables | Table extraction |
| `image_heavy` | Contains figures | Image extraction |
| `form_like` | Form/key-value structure | Form OCR path |
| `mixed` | Complex mixed content | Full analysis |

### Latency Benchmarks

| Device | Latency (ms) | Memory |
|--------|-------------|--------|
| NVIDIA RTX 3080 | 10-20 | 0.8 GB |
| NVIDIA T4 | 20-35 | 0.8 GB |
| CPU (i7-12700) | 150-250 | 0.4 GB |

### Structural Complexity Score

The layout-lite model outputs a **structural complexity score** (0-1):

```python
complexity = calculate_complexity(
    num_tables=layout.table_count,
    num_figures=layout.figure_count,
    column_count=layout.column_count,
    has_math=layout.has_dense_math,
    has_handwriting=layout.has_handwriting
)
```text

| Score Range | Interpretation | OCR Routing |
|-------------|----------------|-------------|
| 0.0 - 0.3 | Simple | `ocr_fast` |
| 0.3 - 0.6 | Moderate | `ocr_standard` |
| 0.6 - 0.8 | Complex | `ocr_advanced` |
| 0.8 - 1.0 | Very Complex | `ocr_advanced` + vision |

---

## Classical CV Metrics

### Blur Detection (Laplacian Variance)

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Laplacian Variance | `var(cv2.Laplacian(img, CV_64F))` | <100 = blurry |

**Calibration Notes**:

- Threshold calibrated on 10,000 document images
- False positive rate: <5% at threshold 100
- Consider document type: forms may have lower variance naturally

### Skew Detection (Hough Transform)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Skew Angle | Hough line detection | >2° triggers correction |

**Calibration Notes**:

- Correction applied only for angles 2-45°
- Angles >45° likely OCR will fail regardless
- Guardrail: undo if correction worsens metrics

### Contrast Score (Histogram Analysis)

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Histogram Spread | `percentile(95) - percentile(5)` | <50 = low contrast |

**Calibration Notes**:

- Normalized 0-255 grayscale histogram
- CLAHE applied if spread <50 and mode >200 (washed out)
- Do-no-harm: never darken already-dark images

### Noise Score (Connected Components)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Small Component Ratio | CC analysis on binary | >20% = noisy |

**Calibration Notes**:

- Components <10px considered noise candidates
- Threshold varies by DPI: adjust for 150 vs 300 DPI
- High ratio may also indicate halftone patterns

---

## Threshold Calibration

### IQA Quality Thresholds

| Quality Level | Overall Score | Action |
|---------------|---------------|--------|
| Excellent | >0.85 | No correction needed |
| Good | 0.70-0.85 | Minor corrections |
| Fair | 0.50-0.70 | Moderate corrections |
| Poor | 0.30-0.50 | Aggressive corrections |
| Very Poor | <0.30 | Flag for manual review |

### DQS (Document Quality Score) Calibration

```python
DQS = (
    0.6 * degradation_score +      # IQA-derived
    0.4 * structural_complexity    # Layout-derived
)
```text

| DQS Range | Interpretation | Pre-OCR Risk |
|-----------|----------------|--------------|
| 0.0 - 0.2 | High quality | Low |
| 0.2 - 0.4 | Good quality | Low-Medium |
| 0.4 - 0.6 | Moderate quality | Medium |
| 0.6 - 0.8 | Poor quality | High |
| 0.8 - 1.0 | Very poor quality | Very High |

### Routing Thresholds

| OCR Strategy | DQS Threshold | PDF Type | Complexity |
|--------------|---------------|----------|------------|
| `ocr_fast` | <0.3 | born_digital | <0.3 |
| `ocr_standard` | 0.3-0.5 | any | 0.3-0.6 |
| `ocr_advanced` | >0.5 | image_only | >0.6 |
| `vision_fallback` | >0.8 | any | any |

---

## Model Versioning

### Version Format

```text
{model_name}-v{major}.{minor}.{patch}

Examples:
- resnet18-iqa-v1.0.0
- resnet50-iqa-v1.0.0
- doclayout-yolo-v1.0.0
```text

### Model Registry

| Model | Current Version | Location |
|-------|-----------------|----------|
| IQA Student | v1.0.0 | `models/resnet18-iqa-v1.0.0.pt` |
| IQA Teacher | v1.0.0 | `models/resnet50-iqa-v1.0.0.pt` |
| Layout-Lite | v1.0.0 | `models/doclayout-yolo-v1.0.0.pt` |

### ONNX Export

All models are exported to ONNX for optimized inference:

```bash
# Export student model
python scripts/export_onnx.py \
  --model resnet18-iqa-v1.0.0.pt \
  --output models/onnx/resnet18-iqa-v1.0.0.onnx \
  --opset 17
```text

---

## Training Data

### IQA Models

| Dataset | Size | Use |
|---------|------|-----|
| OHR-Bench | 18 GB | Primary training |
| BRISQUE synthetic | 5 GB | Augmentation |
| Document degradation | 3 GB | Domain adaptation |

### Layout-Lite Model

| Dataset | Size | Use |
|---------|------|-----|
| DocStructBench | 10 GB | Pre-training |
| PubLayNet subset | 2 GB | Fine-tuning |
| Custom docs | 1 GB | Domain adaptation |

---

## Limitations

### IQA Models

1. **Domain Shift**: Trained primarily on Western documents; may underperform on non-Latin scripts
2. **Color Documents**: Grayscale-focused training; color quality assessment less reliable
3. **High-Resolution**: Downsampling to 224x224 loses fine detail

### Layout-Lite Model

1. **Coarse Only**: Not suitable for detailed element detection (use Project B)
2. **Novel Layouts**: May misclassify unusual document formats
3. **Handwriting**: Limited handwriting detection accuracy

### Classical CV

1. **Document-Specific**: Thresholds calibrated for office documents
2. **DPI Sensitive**: Metrics vary with input resolution
3. **Edge Cases**: Halftone, watermarks may trigger false positives
