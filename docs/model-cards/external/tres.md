---
owner: docs-team
purpose: 'Documentation for Model Card: TReS.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: TReS'
---

## Model Summary

> TReS (Transformer for Relative Quality Assessment) uses Vision Transformer with relative ranking loss. Shows weak positive correlations (PLCC 0.12, SRCC 0.06) with extremely high latency (700ms) - **❌ NOT RECOMMENDED** for document IQA.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-tres` |
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
| **Architecture** | Vision Transformer + Relative Ranking |
| **Parameters** | ~85M (ViT backbone) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('tres')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Transformer-based Relative Quality Ranking |
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

**Correlation Metrics (WEAK)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | 0.1206 | [0.0520, 0.1838] | 0.0588 | [-0.0048, 0.1178] |
| Sharpness | 0.1713 | [0.1017, 0.2370] | 0.1015 | [0.0382, 0.1643] |
| Color | 0.1062 | [0.0373, 0.1689] | 0.0431 | [-0.0221, 0.1031] |

**Error Metrics (HIGH)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.8946 | 1.1054 |
| Sharpness | 0.9016 | 1.1073 |
| Color | 0.8406 | 1.0436 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 700 ms ⚠️ |
| Model Load Time | 8.9 s |

---

## 4. Limitations & Known Issues

### Critical Issues

1. **Weak Correlation**: PLCC 0.12 and SRCC 0.06 indicate minimal predictive value
2. **High Latency**: 700ms inference time without accuracy benefit
3. **Domain Mismatch**: Trained on natural images, poor transfer to documents

### Key Findings

- Near-random performance on document quality assessment
- High latency (700ms) without corresponding accuracy gain
- Relative ranking approach doesn't transfer well to documents

---

## 5. Citation

```bibtex
@inproceedings{golestaneh2022tres,
  title={No-Reference Image Quality Assessment via Transformers, Relative Ranking, and Self-Consistency},
  author={Golestaneh, S. Alireza and others},
  booktitle={WACV},
  year={2022}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (weak correlation, high latency)
