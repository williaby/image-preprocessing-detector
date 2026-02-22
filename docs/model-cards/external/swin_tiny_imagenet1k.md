---
owner: docs-team
purpose: 'Documentation for Model Card: Swin-Tiny ImageNet1K.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: Swin-Tiny ImageNet1K'
---

## Model Summary

> Swin Transformer Tiny variant uses hierarchical shifted window attention for efficient vision processing. Evaluated on DIQA-5000, it shows near-zero overall correlation and **negative sharpness correlation**, demonstrating Vision Transformer ImageNet features don't transfer to document IQA.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `Swin-Tiny-ImageNet-IQA` |
| **Project** | Prepare-Doc |
| **Phase** | External Dependency (Baseline Evaluation) |
| **Status** | `pretrained` |
| **Priority** | P3 (Evaluation/Research) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | Swin Transformer Tiny |
| **Parameters** | ~28M |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Key Innovation** | Hierarchical shifted window self-attention |
| **Window Size** | 7×7 patches |
| **Source** | `torchvision.models.swin_t(weights=Swin_T_Weights.IMAGENET1K_V1)` |

### Architecture Features

- Hierarchical feature extraction (4 stages)
- Shifted window attention (compute efficient)
- Patch merging for multi-scale features
- Linear complexity vs quadratic for full attention

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Vision Transformer architecture evaluation |
| **Role in Pipeline** | Transfer learning baseline (not production) |
| **Finding** | ViT features do NOT transfer to document IQA |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `Swin-Tiny-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | 0.0474 | [-0.0083, 0.0994] | 0.0798 | [0.0176, 0.1379] |
| Sharpness | **-0.1270** | [-0.1777, -0.0712] | **-0.1385** | [-0.1939, -0.0763] |
| Color | 0.0311 | [-0.0247, 0.0856] | 0.0404 | [-0.0199, 0.0997] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4271 | 0.5805 |
| Sharpness | 0.4438 | 0.6196 |
| Color | 0.4213 | 0.5451 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 91 ms |
| Model Load Time | 4.0 s |

### Key Findings

- **Overall**: Near-zero correlation (PLCC=0.05) - essentially random predictions
- **Sharpness**: NEGATIVE correlation (PLCC=-0.13) - predicts opposite of ground truth
- **Color**: Near-zero (PLCC=0.03) - no predictive power
- **Conclusion**: Vision Transformers require domain-specific fine-tuning for IQA

---

## 4. Limitations & Known Issues

### Architecture Limitations for Document IQA

- **Window attention**: 7×7 windows may miss global degradations
- **Hierarchical design**: Optimized for object recognition, not quality assessment
- **Parameter overhead**: 28M params with no quality prediction benefit
- **Latency**: 91ms slower than comparable CNNs

### Known Failure Modes

- **Inverse sharpness**: Predicts sharp documents as blurry (SRCC=-0.14)
- **No color awareness**: Essentially random color quality prediction
- **Document blindness**: ImageNet object features irrelevant to document quality

---

## 5. Citation

```bibtex
@inproceedings{liu2021swin,
  title={Swin Transformer: Hierarchical Vision Transformer using Shifted Windows},
  author={Liu, Ze and Lin, Yutong and Cao, Yue and Hu, Han and Wei, Yixuan and Zhang, Zheng and Lin, Stephen and Guo, Baining},
  booktitle={ICCV},
  year={2021}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (negative sharpness correlation)
