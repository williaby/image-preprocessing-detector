---
owner: docs-team
purpose: 'Documentation for Model Card: EfficientNet-B4 ImageNet1K.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: EfficientNet-B4 ImageNet1K'
---

## Model Summary

> EfficientNet-B4 uses compound scaling (depth, width, resolution) for efficient CNN design. Evaluated on DIQA-5000, it shows **consistently negative correlations** across all quality dimensions, making it unsuitable for document IQA even as a baseline.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `EfficientNet-B4-ImageNet-IQA` |
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
| **Architecture** | EfficientNet-B4 (Compound Scaled CNN) |
| **Parameters** | ~19M |
| **Precision** | FP32 |
| **Input Size** | 380x380x3 (RGB) |
| **Key Innovation** | Compound scaling of depth, width, resolution |
| **Source** | `timm.create_model('efficientnet_b4', pretrained=True)` |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Compound-scaled architecture evaluation |
| **Role in Pipeline** | Transfer learning baseline (not production) |
| **Finding** | **Negative correlations** - inverse relationship with document quality |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `EfficientNet-B4-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics** (⚠️ ALL NEGATIVE):

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **-0.1222** | [-0.1854, -0.0537] | **-0.0767** | [-0.1383, -0.0120] |
| Sharpness | **-0.2561** | [-0.3141, -0.2022] | **-0.2104** | [-0.2714, -0.1498] |
| Color | **-0.1295** | [-0.1817, -0.0740] | **-0.1530** | [-0.2105, -0.0924] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4269 | 0.5817 |
| Sharpness | 0.4275 | 0.6005 |
| Color | 0.4081 | 0.5418 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 112 ms (higher than ResNets) |
| Model Load Time | 3.1 s |

### Critical Finding

- **ALL dimensions show NEGATIVE correlations** - model predicts opposite of ground truth
- **Sharpness worst** (PLCC=-0.26) - severe inverse relationship
- **Higher latency** than ResNets despite fewer parameters
- **NOT SUITABLE** for document IQA in any capacity

---

## 4. Limitations & Known Issues

### Critical Failure

- **Inverse predictions**: Model assigns higher scores to lower-quality documents
- **Architecture mismatch**: Compound scaling optimized for natural image classification
- **Cannot be salvaged**: Fine-tuning may not overcome fundamental inverse correlation

### Why EfficientNet Failed

1. Squeeze-and-Excitation blocks learn texture features inversely correlated with document quality
2. Compound scaling amplifies domain mismatch
3. 380×380 input resolution increases compute without benefit for documents

---

## 5. Citation

```bibtex
@inproceedings{tan2019efficientnet,
  title={EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks},
  author={Tan, Mingxing and Le, Quoc},
  booktitle={ICML},
  year={2019}
}
```

---

## Production Readiness: ❌ UNSUITABLE (negative correlations)