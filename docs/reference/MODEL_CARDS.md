---
schema_type: common
title: "Model Cards & Registry"
description: "Comprehensive model documentation, versioning, and inventory for all
  ML models in Project A"
tags:
- reference
- machine_learning
- documentation
- model_registry
- inventory
status: published
owner: core-maintainer
authors:
- name: "Byron Williams"
purpose: "Document model architectures, training data, performance metrics, and maintain
  complete model inventory."
---

## Comprehensive Model Documentation & Inventory

**Version:** 2.0.0
**Date:** December 2025
**Purpose:** Centralized model documentation, versioning, and inventory for all ML models in Project A

---

> **Individual Model Cards**: For detailed model cards, see the [docs/model-cards/](../model-cards/) directory:
>
> - [TEMPLATE.md](../model-cards/TEMPLATE.md) - Standard model card template
> - [REGISTRY.md](../model-cards/REGISTRY.md) - Complete model inventory with status tracking
> - [production/](../model-cards/production/) - Trained and deployed models
> - [classical/](../model-cards/classical/) - Rule-based detectors
> - [planned/](../model-cards/planned/) - Documented specifications for future models
>
> This document provides comprehensive reference material. Individual model cards provide focused documentation per model.

---

## Table of Contents

1. [Overview](#overview)
2. [Model Card Template](#model-card-template)
3. [Complete Model Inventory](#complete-model-inventory)
4. [Production Models](#production-models)
5. [Planned Models - DIQA Ensemble](#planned-models---diqa-ensemble)
6. [Planned Models - Phase 9 Classifiers](#planned-models---phase-9-classifiers)
7. [Classical Detectors](#classical-detectors)
8. [External/Pretrained Models](#externalpretrained-models)
9. [Model Registry Schema](#model-registry-schema)
10. [Storage & Versioning](#storage--versioning)
11. [Governance & Lifecycle](#governance--lifecycle)
12. [Threshold Calibration](#threshold-calibration)
13. [Limitations](#limitations)

---

## Overview

Project A uses a **teacher-student architecture** for learned IQA, combined with classical computer vision methods for deterministic quality assessment. This document provides:

- **Standardized model card template** for all models
- **Complete inventory** of all models (trained, pretrained, planned)
- **Registry schema** for version management
- **Governance policies** for model lifecycle

### Quick Reference

| Model | Architecture | Purpose | Status | Production |
|-------|-------------|---------|--------|------------|
| IQA Teacher | ResNet-50 | High-capacity training/validation | ✅ Trained | GPU-only |
| IQA Student | ResNet-18 | Fast production inference | ✅ Trained | Yes |
| Layout-Lite | DocLayout-YOLO | Coarse page classification | ✅ Pretrained | Yes |
| Classical CV | OpenCV | Deterministic IQA metrics | ✅ Complete | Yes |
| DIQA Ensemble | 5-model stack | Pseudo-labeling | ❌ Planned | No |
| Element Classifiers | ResNet-18/MobileNetV3 | Table/handwriting detection | ❌ Planned | No |

---

## Model Card Template

### Standard Model Card Format

Every trained model in Project A MUST have a `MODEL_CARD.md` following this template. This template extends Appendix C from the DIQA-5000 specification to cover all project models.

```markdown
# Model Card: {model_name}

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `{task}_{architecture}_{variant}_v{major}.{minor}.{patch}` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase X (Description) |
| **Status** | `trained` / `pretrained` / `planned` / `deprecated` |
| **Last Updated** | YYYY-MM-DD |

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | e.g., ResNet-50 + MultiTaskHead |
| **Parameters** | e.g., 25.6M |
| **Precision** | FP32 / FP16 / INT8 |
| **Input Size** | e.g., 384×384×3 |
| **Output Format** | e.g., 5-class multi-label scores |

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | e.g., Image Quality Assessment |
| **Role in Pipeline** | e.g., Teacher model for high-risk escalation |
| **Upstream Dependencies** | e.g., Text Gate, PDF Type Classifier |
| **Downstream Consumers** | e.g., DQS Calculator, Routing Engine |

### Intended Use
- **Primary**: [Main use case]
- **Secondary**: [Alternative applications]
- **Out of Scope**: [What this model should NOT be used for]

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | e.g., OHR-Bench (100K images) |
| **Train/Val/Test Split** | e.g., 80/10/10 |
| **Epochs** | e.g., 50 |
| **Batch Size** | e.g., 128 |
| **Learning Rate** | e.g., 1e-4 with cosine decay |
| **Optimizer** | e.g., AdamW |
| **Loss Function** | e.g., BCE + Focal + Rank |
| **Augmentations** | e.g., Horizontal flip, rotation ±5° |
| **GPU** | e.g., Modal A10 (24GB) |
| **Training Time** | e.g., 1.91 hours |
| **Training Date** | YYYY-MM-DD |
| **Training Script** | e.g., `modal/train_phase2_iqa.py` |
| **Commit SHA** | e.g., `abc123def456` |

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Validation Loss | 0.27 | < 0.30 | ✅ Pass |
| mAP | 0.88 | > 0.85 | ✅ Pass |
| Precision | 0.91 | > 0.85 | ✅ Pass |
| Recall | 0.85 | > 0.80 | ✅ Pass |

### 4.2 Per-Class Performance (if applicable)

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| blur | 0.92 | 0.88 | 0.90 | 5000 |
| noise | 0.89 | 0.84 | 0.86 | 4800 |
| skew | 0.94 | 0.91 | 0.92 | 5200 |
| ... | ... | ... | ... | ... |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| T4 GPU | 28ms | 35ms | 36 img/s | 1.2GB |
| A10 GPU | 18ms | 22ms | 56 img/s | 1.2GB |
| CPU (x86) | 95ms | 120ms | 10 img/s | 0.8GB |

### 4.4 Cross-Dataset Validation (for DIQA models)

| Dataset | SRCC | PLCC | ECE | Notes |
|---------|------|------|-----|-------|
| DIQA-5000 | 0.85 | 0.87 | 0.06 | Primary benchmark |
| DocVQA | 0.78 | 0.80 | 0.08 | OOD test |
| SmartDoc-QA | 0.82 | 0.84 | 0.07 | Real-world test |

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | e.g., Temperature scaling |
| **ECE (Expected Calibration Error)** | e.g., 0.06 |
| **Uncertainty Output** | e.g., Softmax entropy per head |
| **Escalation Threshold** | e.g., entropy > 0.7 → teacher |

## 6. Limitations & Known Issues

### Limitations
- [Limitation 1]: e.g., "Trained only on OHR-Bench; may not generalize to handwritten documents"
- [Limitation 2]: e.g., "Color dimension performance below target"

### Known Failure Modes
- [Mode 1]: e.g., "High false positive rate on heavily textured backgrounds"
- [Mode 2]: e.g., "Struggles with moiré patterns from screen captures"

### Bias & Fairness Considerations
- [Consideration 1]: e.g., "Dataset is 85% English documents; non-Latin scripts underrepresented"

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | e.g., ResNet-50 (ImageNet1K_V2) |
| **Parent Version** | e.g., N/A (first version) or `v1.0.0` |
| **Derived Models** | e.g., `iqa_resnet18_student_v1.0.0` (distilled) |
| **Required Libraries** | e.g., PyTorch 2.0+, ONNX Runtime 1.15+ |

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.pt` | PyTorch checkpoint | 98MB | `abc123...` |
| `model.onnx` | ONNX export (opset 17) | 97MB | `def456...` |
| `model.torchscript` | TorchScript export | 98MB | `ghi789...` |
| `config.json` | Model configuration | 2KB | `jkl012...` |

## 9. Deployment Configuration

    ```yaml
    # Production deployment settings
    device_priority:
      - local_gpu
      - modal_gpu
      - cpu  # or BLOCK for teacher
    inference:
      batch_size: 8
      timeout_ms: 100
      warmup_iterations: 3
    monitoring:
      prometheus_metrics: true
      log_level: INFO
    ```

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-12-15 | Initial release | Team |
| v1.1.0 | 2025-12-20 | Improved blur detection | Team |

## 11. Citation

    ```bibtex
    @misc{model_id,
      title={Model Name: Purpose},
      author={Project A Team},
      year={2025},
      note={Internal model for document preprocessing pipeline}
    }
    ```

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | [Team/Individual] |
| **Technical Contact** | [Email/Slack] |
| **Review Cadence** | Quarterly |
```

### Naming Convention

**Format:** `{task}_{architecture}_{variant}_v{major}.{minor}.{patch}`

| Component | Description | Examples |
|-----------|-------------|----------|
| `task` | Primary task identifier | `iqa`, `layout`, `textgate`, `dqs`, `diqa`, `classify` |
| `architecture` | Model architecture | `resnet50`, `resnet18`, `yolov10`, `musiq`, `qwen3vl` |
| `variant` | Specialization or role | `teacher`, `student`, `sharpness`, `color`, `generalist` |
| `version` | Semantic version | `v1.0.0`, `v1.2.3` |

**Examples:**

```text
iqa_resnet50_teacher_v1.0.0       # ML IQA teacher model
iqa_resnet18_student_v1.0.0       # ML IQA student (distilled)
layout_yolov10_doclaynet_v1.0.0   # Layout detection (pretrained)
diqa_musiq_sharpness_v1.0.0       # DIQA pseudo-labeling specialist
diqa_qwen3vl_generalist_v1.0.0    # DIQA VLM anchor
classify_resnet18_table_v1.0.0    # Table type classifier
```

---

## Complete Model Inventory

### Summary Table

| Model ID | Phase | Status | Architecture | Primary Task | Device |
|----------|-------|--------|--------------|--------------|--------|
| `iqa_resnet50_teacher_v1.0.0` | 3 | ✅ Trained | ResNet-50 + 5 heads | ML IQA (high-risk) | GPU |
| `iqa_resnet18_student_v1.0.0` | 3 | ✅ Trained | ResNet-18 + 5 heads | ML IQA (default) | GPU/CPU |
| `layout_yolov10_doclaynet_v1.0.0` | 2 | ✅ Pretrained | YOLOv10-doc | Element detection | GPU |
| `layout_yolov8_lite_v1.0.0` | 6 | ⚠️ Partial | YOLOv8 | Coarse regions | GPU |
| `diqa_resnet50_generalist_v1.0.0` | DIQA | ❌ Planned | ResNet-50 + Layout Fusion | DIQA anchor | A100 |
| `diqa_musiq_sharpness_v1.0.0` | DIQA | ❌ Planned | MUSIQ + MultiTask | Sharpness specialist | T4 |
| `diqa_qualiclip_color_v1.0.0` | DIQA | ❌ Planned | QualiCLIP + MultiTask | Color specialist | T4 |
| `diqa_qwen3vl_generalist_v1.0.0` | DIQA | ❌ Planned | Qwen3-VL-8B + LoRA | VLM anchor | A100 |
| `diqa_internvl3_overall_v1.0.0` | DIQA | ❌ Planned | InternVL3-8B + LoRA | Overall specialist | A100 |
| `diqa_stacker_ensemble_v1.0.0` | DIQA | ❌ Planned | HierarchicalStacker | Ensemble fusion | CPU |
| `classify_resnet18_table_v1.0.0` | 9 | ❌ Planned | ResNet-18 | Table type | GPU/CPU |
| `classify_resnet18_handwriting_v1.0.0` | 9 | ❌ Planned | ResNet-18 | Handwriting detection | GPU/CPU |
| `classical_iqa_ensemble_v1.0.0` | 1C | ✅ Complete | Rule-based (8 detectors) | Classical IQA | CPU |
| `textgate_heuristic_v1.0.0` | 1 | ✅ Complete | Ensemble heuristics | Text detection | CPU |
| `pdftype_classifier_v1.0.0` | 2 | ✅ Complete | Rule-based | PDF classification | CPU |

### Status Legend

| Status | Symbol | Description |
|--------|--------|-------------|
| Trained | ✅ | Model trained and validated |
| Pretrained | ✅ | Using pretrained weights (no custom training) |
| Complete | ✅ | Rule-based/classical detector implemented |
| Partial | ⚠️ | Framework ready, training incomplete |
| Planned | ❌ | Documented but not started |
| Deprecated | 🚫 | No longer supported |

### Model Count by Category

| Category | Count | Details |
|----------|-------|---------|
| **Deep Learning - Trained** | 2 | ResNet-50 teacher, ResNet-18 student |
| **Deep Learning - Pretrained** | 1 | DocLayout-YOLO |
| **Deep Learning - In Progress** | 1 | YOLOv8 layout-lite |
| **Deep Learning - Planned** | 8 | DIQA ensemble (6), Phase 9 classifiers (2) |
| **Classical Detectors** | 3 | IQA ensemble, text gate, PDF classifier |
| **Total** | 15 | 6 production-ready, 9 planned |

---

## Production Models

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
```

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
```

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
```

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
```

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

### Illumination Detection (9-Region Uniformity)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Uniformity Score | 9-region intensity analysis | <0.7 = non-uniform |

**Calibration Notes**:

- Divides image into 9 regions, compares mean intensities
- Detects vignetting via edge-to-center ratio
- Score range: 0.0-1.0 (higher = better uniformity)

### JPEG Blockiness (DCT Block Boundary)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Blockiness Score | DCT block boundary analysis | >0.3 = significant artifacts |

**Calibration Notes**:

- Analyzes 8x8 block boundary discontinuities
- Estimates original JPEG quality factor (1-100)
- Score range: 0.0-1.0 (higher = more blocky)

### Binarization Quality (Histogram Bimodality)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Binarization Quality | Histogram bimodality analysis | <0.5 = poor separation |

**Calibration Notes**:

- Measures separation between foreground/background peaks
- Useful for scanned documents with faded text
- Score range: 0.0-1.0 (higher = better text/background separation)

### Bleed-Through Detection (Verso Content)

| Metric | Method | Threshold |
|--------|--------|-----------|
| Bleed-Through Score | Verso content detection | >0.3 = bleed-through present |

**Calibration Notes**:

- Detects show-through from reverse side of scanned pages
- Common in thin paper and newspaper scans
- Score range: 0.0-1.0 (higher = more bleed-through)

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
```

| DQS Range | Interpretation | Pre-OCR Risk |
|-----------|----------------|--------------|
| 0.0 - 0.2 | High quality | Low |
| 0.2 - 0.4 | Good quality | Low-Medium |
| 0.4 - 0.6 | Moderate quality | Medium |
| 0.6 - 0.8 | Poor quality | High |
| 0.8 - 1.0 | Extremely poor quality | Critical |

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
```

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
```

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

---

## Planned Models - DIQA Ensemble

> **Reference**: See [DIQA-5000_Pseudo_Labels_v2.md](../planning/DIQA-5000_Pseudo_Labels_v2.md) for detailed specifications.

The DIQA pseudo-labeling system uses a **5-model ensemble** organized into two tracks for generating quality annotations on unlabeled document images.

### Track Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIQA PSEUDO-LABELING ENSEMBLE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TRACK A: IQA MODELS (CNN-based)         TRACK B: VLM MODELS           │
│  GPU: T4/A10G                            GPU: A100-80GB                 │
│  ┌───────────────────────────┐           ┌───────────────────────────┐  │
│  │ DocIQ-Replica (Anchor)    │           │ Qwen3-VL-8B (Anchor)      │  │
│  │ MUSIQ (Sharpness)         │           │ InternVL3-8B (Overall)    │  │
│  │ QualiCLIP (Color)         │           │                           │  │
│  └───────────────────────────┘           └───────────────────────────┘  │
│                │                                     │                  │
│                └─────────────────┬───────────────────┘                  │
│                                  ▼                                      │
│                    ┌─────────────────────────┐                          │
│                    │ HierarchicalStacker     │                          │
│                    │ + Temperature Scaling   │                          │
│                    └─────────────────────────┘                          │
│                                  ▼                                      │
│                    3 DIQA Scores + Uncertainties                        │
│                    (Overall, Sharpness, Color)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Track A: IQA Models

#### diqa_resnet50_generalist_v1.0.0 (DocIQ-Replica)

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_resnet50_generalist_v1.0.0` |
| **Status** | ❌ Requires Training |
| **Role** | Generalist Anchor (Track A) |
| **Architecture** | ResNet-50 + Layout Fusion Downsampler + MultiTaskHead |
| **Input Size** | 1600×1600 (paper-aligned) |
| **Layout Masks** | 11-class DocLayout-YOLO masks |
| **Parameters** | ~26M |
| **Precision** | FP32 |
| **GPU** | A100-80GB |
| **Training** | 60 epochs, equal loss weights [0.34, 0.33, 0.33] |
| **Target SRCC** | > 0.85 (all dimensions) |
| **Target ECE** | < 0.08 (mean) |

**Purpose**: Serves as the **generalist anchor** for Track A. Without IQA pretraining bias, it learns balanced representations across all three quality dimensions.

#### diqa_musiq_sharpness_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_musiq_sharpness_v1.0.0` |
| **Status** | ❌ Requires Fine-tuning |
| **Role** | Sharpness Specialist |
| **Architecture** | MUSIQ (ViT-B/16) + MultiTaskHead |
| **Base Model** | PyIQA MUSIQ (KonIQ-10k pretrained) |
| **Parameters** | ~27M |
| **Precision** | FP32 |
| **GPU** | T4/A10G |
| **Training** | 30 epochs, specialist weights [0.2, 0.6, 0.2] |
| **Target SRCC** | > 0.88 (sharpness dimension) |

**Purpose**: Leverages KonIQ-10k pretraining for blur/noise expertise.

#### diqa_qualiclip_color_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_qualiclip_color_v1.0.0` |
| **Status** | ❌ Requires Fine-tuning |
| **Role** | Color Specialist |
| **Architecture** | QualiCLIP (CLIP ViT-B/32) + MultiTaskHead |
| **Base Model** | PyIQA QualiCLIP |
| **Parameters** | ~150M |
| **Precision** | FP32 |
| **GPU** | T4/A10G |
| **Training** | 30 epochs, specialist weights [0.2, 0.2, 0.6] |
| **Target SRCC** | > 0.85 (color dimension) |

**Purpose**: CLIP pretraining provides strong color vocabulary and semantic understanding.

### Track B: VLM Models

#### diqa_qwen3vl_generalist_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_qwen3vl_generalist_v1.0.0` |
| **Status** | ❌ Requires Fine-tuning |
| **Role** | Generalist Anchor (Track B) |
| **Architecture** | Qwen3-VL-8B + LoRA |
| **HuggingFace** | `Qwen/Qwen3-VL-8B-Instruct` |
| **Parameters** | ~8B (LoRA: ~16M trainable) |
| **Precision** | FP16 |
| **GPU** | A100-80GB |
| **Training** | 3 epochs LoRA, equal weights [0.34, 0.33, 0.33] |
| **Target SRCC** | > 0.90 (all dimensions) |

**Purpose**: VLM anchor with semantic understanding for holistic quality assessment.

#### diqa_internvl3_overall_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_internvl3_overall_v1.0.0` |
| **Status** | ❌ Requires Fine-tuning |
| **Role** | Overall Specialist |
| **Architecture** | InternVL3-8B + LoRA |
| **HuggingFace** | `OpenGVLab/InternVL3-8B` |
| **Parameters** | ~8B (LoRA: ~16M trainable) |
| **Precision** | FP16 |
| **GPU** | A100-80GB |
| **Training** | 3 epochs LoRA, specialist weights [0.6, 0.2, 0.2] |
| **Target SRCC** | > 0.88 (overall dimension) |

**Purpose**: Overall specialist with holistic document understanding.

### Ensemble Stacker

#### diqa_stacker_ensemble_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_stacker_ensemble_v1.0.0` |
| **Status** | ❌ Requires Training |
| **Role** | Ensemble Fusion |
| **Architecture** | HierarchicalStacker + Temperature Scaling |
| **Parameters** | ~50K |
| **Device** | CPU |
| **Input** | 5 models × 3 dimensions predictions |
| **Output** | 3 fused scores + 3 uncertainties |

**Key Features**:

- Within-dimension variance as uncertainty signal (not cross-dimension divergence)
- Per-dimension learned weights
- Calibrated uncertainty via temperature scaling
- Target ECE < 0.08

### DIQA Ensemble Weights

```python
ENSEMBLE_WEIGHTS = {
    'overall': {
        'qwen3_vl_8b': 0.30,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA)
        'musiq': 0.10,           # Off-specialty
        'qualiclip': 0.10,       # Off-specialty
        'internvl3_8b': 0.30,    # Overall specialist
    },
    'sharpness': {
        'qwen3_vl_8b': 0.15,
        'dociq_replica': 0.20,
        'musiq': 0.35,           # Sharpness specialist
        'qualiclip': 0.10,
        'internvl3_8b': 0.20,
    },
    'color': {
        'qwen3_vl_8b': 0.20,
        'dociq_replica': 0.20,
        'musiq': 0.10,
        'qualiclip': 0.40,       # Color specialist
        'internvl3_8b': 0.10,
    },
}
```

---

## Planned Models - Phase 9 Classifiers

Phase 9 introduces specialized element classifiers for downstream processing decisions.

### classify_resnet18_table_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_table_v1.0.0` |
| **Status** | ❌ Planned |
| **Phase** | 9 |
| **Architecture** | ResNet-18 |
| **Purpose** | Table type classification |
| **Classes** | simple, complex, nested, multi-column |
| **Target Size** | < 25MB (ONNX) |
| **Device** | GPU/CPU |

### classify_resnet18_handwriting_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_handwriting_v1.0.0` |
| **Status** | ❌ Planned |
| **Phase** | 9 |
| **Architecture** | ResNet-18 |
| **Purpose** | Handwriting presence detection |
| **Classes** | none, partial, full |
| **Target Size** | < 25MB (ONNX) |
| **Device** | GPU/CPU |

### classify_resnet18_formula_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_formula_v1.0.0` |
| **Status** | ❌ Planned |
| **Phase** | 9 |
| **Architecture** | ResNet-18 |
| **Purpose** | Mathematical formula detection |
| **Classes** | none, simple, complex |
| **Target Size** | < 25MB (ONNX) |
| **Device** | GPU/CPU |

### classify_mobilenetv3_parasitic_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `classify_mobilenetv3_parasitic_v1.0.0` |
| **Status** | ❌ Planned |
| **Phase** | 9 |
| **Architecture** | MobileNetV3-Small |
| **Purpose** | Parasitic content classification |
| **Classes** | margin_notes, watermarks, artifacts |
| **Target Size** | < 15MB (ONNX) |
| **Device** | GPU/CPU |

---

## Classical Detectors

### classical_iqa_ensemble_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `classical_iqa_ensemble_v1.0.0` |
| **Status** | ✅ Complete |
| **Phase** | 1C |
| **Type** | Rule-based (no learnable parameters) |
| **Source** | `src/image_preprocessing_detector/detection/iqa_classical.py` |
| **Combined Latency** | < 25ms |
| **Tests** | 99 passing |

**Detectors (8 total)**:

| Detector | Method | Output |
|----------|--------|--------|
| Skew | Hough transform | angle_degrees, confidence |
| Blur | Laplacian variance | blur_score, confidence |
| Contrast | Histogram analysis | contrast_score, confidence |
| Noise | Wavelet-based DWT | noise_score, confidence |
| Illumination | 9-region uniformity | uniformity_score, confidence |
| JPEG Blockiness | DCT block boundary | blockiness_score, confidence |
| Binarization | Histogram bimodality | binarization_quality, confidence |
| Bleed-through | Verso content detection | bleedthrough_score, confidence |

### textgate_heuristic_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `textgate_heuristic_v1.0.0` |
| **Status** | ✅ Complete |
| **Phase** | 1 |
| **Type** | Rule-based ensemble |
| **Source** | `src/image_preprocessing_detector/detection/text_gate.py` |
| **Latency** | < 10ms |
| **Accuracy** | > 95% |

**Methods**: Stroke density, connected component analysis, edge density.

### pdftype_classifier_v1.0.0

| Field | Value |
|-------|-------|
| **Model ID** | `pdftype_classifier_v1.0.0` |
| **Status** | ✅ Complete |
| **Phase** | 2 |
| **Type** | Rule-based heuristics |
| **Source** | `src/image_preprocessing_detector/classification/pdf_type_classifier.py` |
| **Classes** | image_only, born_digital, hybrid |
| **Accuracy** | 100% (21/21 tests) |

---

## External/Pretrained Models

### Models Used Without Custom Training

| Model | Source | Purpose | License | Used In |
|-------|--------|---------|---------|---------|
| DocLayout-YOLO | HuggingFace | Layout detection | Apache 2.0 | layout_yolov10_doclaynet |
| MUSIQ (base) | PyIQA | IQA backbone | MIT | diqa_musiq_sharpness |
| QualiCLIP (base) | PyIQA | IQA backbone | MIT | diqa_qualiclip_color |
| ResNet-50 (ImageNet) | torchvision | Teacher backbone | BSD | iqa_resnet50_teacher |
| ResNet-18 (ImageNet) | torchvision | Student backbone | BSD | iqa_resnet18_student |
| Qwen3-VL-8B | HuggingFace | VLM backbone | Apache 2.0 | diqa_qwen3vl_generalist |
| InternVL3-8B | HuggingFace | VLM backbone | Apache 2.0 | diqa_internvl3_overall |

### PyIQA Model Registry

Models available via `pyiqa.create_metric()`:

| Model | Domain | Output | Notes |
|-------|--------|--------|-------|
| `musiq` | General IQA | MOS score | Multi-scale ViT |
| `qualiclip` | General IQA | Quality score | CLIP-based |
| `dbcnn` | General IQA | Quality score | Dual-branch CNN |
| `hyperiqa` | General IQA | Quality score | Hypernetwork |

---

## Model Registry Schema

### Python Schema

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class ModelRegistryEntry:
    """Schema for Project A model registry entries."""

    # Identity
    model_id: str                    # e.g., "iqa_resnet50_teacher_v1.0.0"
    task: str                        # e.g., "iqa", "layout", "diqa"
    architecture: str                # e.g., "resnet50", "yolov10"
    variant: str                     # e.g., "teacher", "student", "sharpness"
    version: str                     # Semantic version
    phase: str                       # Project phase
    status: Literal["trained", "pretrained", "planned", "deprecated"]
    created_at: datetime

    # Location
    gcs_path: str                    # gs://bucket/path/to/model/
    checkpoint_file: str             # model.pt or adapter_model.safetensors
    onnx_file: str | None            # Optional ONNX export
    torchscript_file: str | None     # Optional TorchScript export

    # Performance
    primary_metric_name: str         # e.g., "mAP", "SRCC", "val_loss"
    primary_metric_value: float
    secondary_metrics: dict[str, float]

    # Inference
    inference_latency_ms: float      # Mean latency on target device
    memory_mb: float                 # Peak VRAM/RAM usage
    supported_devices: list[str]     # ["gpu", "cpu", "modal"]

    # Lineage
    base_model: str                  # Parent model or pretrained source
    parent_version: str | None       # Previous version (if upgrade)
    derived_models: list[str]        # Models trained from this one
    training_commit: str             # Git commit SHA
    training_script: str             # Path to training script

    # Metadata
    owner: str                       # Team or individual
    description: str                 # Brief description
    tags: list[str]                  # Searchable tags
```

---

## Storage & Versioning

### GCS Storage Structure

```text
gs://image_detection_b/models/
├── phase2_iqa/                     # ResNet-50 teacher
│   ├── v1.0.0/
│   │   ├── resnet50_teacher.pt
│   │   ├── resnet50_teacher.onnx
│   │   ├── config.json
│   │   └── MODEL_CARD.md
│   └── v1.1.0/
├── phase2_student/                 # ResNet-18 student
│   └── v1.0.0/
├── doclayout_yolo/                 # Layout detection
│   └── doclaynet_pretrained/
├── diqa/                           # DIQA ensemble (planned)
│   ├── track_a_iqa/
│   │   ├── dociq_replica/
│   │   ├── musiq/
│   │   └── qualiclip/
│   ├── track_b_vlm/
│   │   ├── qwen3_vl_8b/
│   │   └── internvl3_8b/
│   └── stacker/
├── phase9_classifiers/             # Element classifiers (planned)
│   ├── table_type/
│   ├── handwriting/
│   └── formula/
└── registry/
    └── model_registry.json         # Central registry file
```

### Version Promotion Workflow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     Model Version Promotion                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. DEVELOPMENT (dev/)                                                  │
│     └─ Train model, save to gs://.../dev/{model}/                      │
│     └─ Run basic validation                                             │
│                                                                         │
│  2. STAGING (staging/)                                                  │
│     ├─ Run benchmark suite (OHR-Bench, DIQA-5000)                      │
│     ├─ Check performance thresholds                                     │
│     └─ If pass → promote to staging/                                    │
│                                                                         │
│  3. INTEGRATION TEST (staging/)                                         │
│     ├─ Run full pipeline integration tests                              │
│     └─ If pass → promote to prod/                                       │
│                                                                         │
│  4. PRODUCTION (prod/)                                                  │
│     ├─ Copy to versioned directory                                      │
│     ├─ Update MODEL_CARD.md                                             │
│     └─ Tag in model registry                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Governance & Lifecycle

### Model Review Cadence

| Model Type | Review Frequency | Trigger Events |
|------------|------------------|----------------|
| Production ML | Quarterly | Performance drift, new data |
| Pretrained | Annually | Upstream updates |
| Classical | As-needed | Bug reports |
| Planned | Per-phase | Phase start |

### Deprecation Policy

1. **Announcement**: 30 days notice before deprecation
2. **Migration Path**: Document replacement model and migration steps
3. **Sunset**: Remove from production after migration period
4. **Archive**: Keep in `deprecated/` folder for reference

### Model Card Requirements

| Requirement | New Models | Updates | Pretrained |
|-------------|------------|---------|------------|
| Full model card | ✅ Required | ✅ Required | ✅ Required |
| Performance metrics | ✅ Required | ✅ Required | ⚠️ Reference source |
| Training details | ✅ Required | ✅ Required | ❌ N/A |
| Lineage | ✅ Required | ✅ Required | ✅ Required |
| Limitations | ✅ Required | ✅ Required | ✅ Required |

### Pre-Production Checklist

Before promoting a model to production:

- [ ] MODEL_CARD.md complete and reviewed
- [ ] Performance metrics meet thresholds
- [ ] Inference latency within acceptable range
- [ ] Memory usage validated on target devices
- [ ] Integration tests pass
- [ ] ONNX export validated (if applicable)
- [ ] GCS backup complete
- [ ] Version tagged in registry
- [ ] Rollback plan documented

---

## Quick Reference Commands

```bash
# List all registered models
cat models/configs/model_manifest.json | jq '.models[].model_id'

# Check model performance
uv run python -c "from src.image_preprocessing_detector.models import get_model_info; print(get_model_info('student'))"

# Benchmark model latency
uv run python scripts/benchmark_model.py --model resnet18_student --device gpu

# Export to ONNX
uv run python scripts/export_onnx.py --model resnet50_teacher --opset 17

# Upload to GCS
gsutil -m cp -r models/iqa/v1.0.0/ gs://image_detection_b/models/phase2_iqa/v1.0.0/
```

---

## Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| PROJECT_PLAN.md | docs/planning/ | Phase breakdown and implementation |
| DIQA-5000_Pseudo_Labels_v2.md | docs/planning/ | DIQA ensemble specifications |
| MUSIQ_FINETUNING_PLAN.md | docs/planning/ | MUSIQ specialist training |
| doclayout_yolo.yaml | configs/models/ | DocLayout-YOLO configuration |
| model_optimizer.py | src/.../models/ | Model export utilities |

---

*Document Version 2.0.0 — December 2025*
*Project A: Preprocessing, IQA & Coarse Layout Gateway*
