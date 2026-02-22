---
owner: docs-team
purpose: 'Documentation for Model Card: ARNIQA.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: ARNIQA'
---

## Model Summary

> ARNIQA (Adversarial-based Representation learning for No-Reference IQA) uses ResNet-50 backbone with adversarial training to learn distortion manifolds. Shows **negative correlation** on documents (-0.12 SRCC), demonstrating fundamental domain mismatch between natural image IQA and document quality assessment.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-arniqa` |
| **Project** | Prepare-Doc |
| **Phase** | External Pretrained (DIQA Evaluation) |
| **Status** | ❌ NOT RECOMMENDED |
| **Priority** | N/A (Evaluation Only) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-50 with Adversarial Training |
| **Parameters** | ~25.6M |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('arniqa')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | No-Reference Image Quality Assessment |
| **Role in Pipeline** | Evaluation baseline (NOT for production) |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | None (excluded from ensemble) |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics (CRITICAL: Negative correlations)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **-0.0512** | [-0.1161, 0.0112] | **-0.1202** | [-0.1813, -0.0576] |
| Sharpness | 0.0351 | [-0.0260, 0.0952] | -0.0233 | [-0.0845, 0.0429] |
| Color | -0.0575 | [-0.1181, 0.0041] | **-0.1241** | [-0.1841, -0.0623] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.7393 | 0.9031 |
| Sharpness | 0.7136 | 0.8804 |
| Color | 0.7178 | 0.8759 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 111 ms |
| Model Load Time | 4.5 s |

---

## 4. Limitations & Known Issues

### Critical Issues

1. **Negative Correlation**: SRCC -0.12 indicates model predictions are inversely correlated with document quality
2. **Domain Mismatch**: Trained on natural images, adversarial training doesn't transfer to documents
3. **Not Suitable**: For any document IQA application

### Key Findings

- Worst performing model among all evaluated (negative correlations)
- Demonstrates importance of domain-specific training
- Adversarial learning approach fails on document domain

---

## 5. Citation

```bibtex
@inproceedings{agnolucci2024arniqa,
  title={ARNIQA: Learning Distortion Manifold for Image Quality Assessment},
  author={Agnolucci, Lorenzo and others},
  booktitle={WACV},
  year={2024}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (negative correlation - domain mismatch)
