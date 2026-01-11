---
owner: docs-team
purpose: 'Documentation for Model Card: ResNet-34 ImageNet1K V2.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: ResNet-34 ImageNet1K V2'
---

## Model Summary

> ResNet-34 pretrained on ImageNet-1K using the improved V2 training recipe from torchvision. Evaluated on DIQA-5000 as an external baseline backbone for document image quality assessment. Shows near-zero correlations, confirming ImageNet features do not transfer effectively to document IQA without fine-tuning.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `ResNet34-ImageNet-IQA` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Dependency (Baseline Evaluation) |
| **Status** | `pretrained` |
| **Priority** | P3 (Evaluation/Research) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-34 (Deep Residual Network) |
| **Parameters** | 21,797,672 (~21.8M) |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Output Format** | 1000-class ImageNet classification logits |
| **Export Formats** | PyTorch (native via torchvision) |
| **Source** | `torchvision.models.resnet34(weights=ResNet34_Weights.IMAGENET1K_V1)` |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Baseline backbone evaluation for document IQA |
| **Role in Pipeline** | Transfer learning baseline (not production) |
| **Upstream Dependencies** | None (external pretrained model) |
| **Downstream Consumers** | None (evaluation only) |

### Intended Use

- **Primary**: Baseline comparison to quantify transfer learning gap
- **Secondary**: Architecture evaluation for IQA backbone selection
- **Out of Scope**: Production document quality assessment

---

## 3. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | `[N, 3, 224, 224]` (batch, channels, height, width) |
| **Color Space** | RGB |
| **Value Range** | [0, 1] after ToTensor() |
| **Channel Order** | CHW (PyTorch convention) |

### Normalization

```python
# Required preprocessing values (ImageNet statistics)
mean = [0.485, 0.456, 0.406]  # RGB channel means
std = [0.229, 0.224, 0.225]   # RGB channel stds
```

### Complete Transform Pipeline

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])
```

---

## 4. Performance Metrics

### 4.1 DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `ResNet34-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |
| **Official Tracking** | [diqa5000_benchmark_results.csv](../../benchmarks/diqa5000_benchmark_results.csv) |

**Correlation Metrics** (higher is better, range: -1 to +1):

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | -0.0602 | [-0.1216, 0.0078] | -0.0965 | [-0.1588, -0.0343] |
| Sharpness | 0.1053 | [0.0558, 0.1594] | 0.0722 | [0.0157, 0.1298] |
| Color | 0.1184 | [0.0595, 0.1740] | 0.1579 | [0.0996, 0.2157] |

**Error Metrics** (lower is better):

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4747 | 0.6356 |
| Sharpness | 0.5025 | 0.6832 |
| Color | 0.4879 | 0.5910 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 79 ms |
| Model Load Time | 4.0 s |

### Analysis

- **Overall**: Negative correlation (PLCC=-0.06, SRCC=-0.10) indicates predictions are inversely related to quality
- **Sharpness**: Weak positive correlation (PLCC=0.11) - marginally better than random
- **Color**: Weak positive correlation (PLCC=0.12) - slightly better than other dimensions
- **Conclusion**: ImageNet features do NOT transfer to document IQA without fine-tuning

---

## 5. Limitations & Known Issues

### Domain Mismatch

- **Critical**: ImageNet features (objects, textures) fundamentally misaligned with document quality
- **Evidence**: Near-zero/negative correlations across all dimensions
- **Impact**: Cannot be used for production document IQA

### Known Failure Modes

- Predictions move in opposite direction of true quality for overall dimension
- No awareness of document-specific degradations (text blur, scanning artifacts)
- Color statistics from natural images don't match document color spaces

---

## 6. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Original Paper** | "Deep Residual Learning for Image Recognition" (He et al., 2015) |
| **Pretrained Source** | torchvision 0.15+ (PyTorch ecosystem) |
| **Required Libraries** | PyTorch 2.0+, torchvision 0.15+ |

---

## 7. Citation

```bibtex
@inproceedings{he2016deep,
  title={Deep Residual Learning for Image Recognition},
  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  booktitle={CVPR},
  pages={770--778},
  year={2016}
}
```

---

## Production Readiness Checklist

- [x] Model Summary written
- [x] DIQA-5000 benchmark results recorded
- [x] Limitations documented
- [ ] ❌ Production deployment (NOT RECOMMENDED - baseline only)
