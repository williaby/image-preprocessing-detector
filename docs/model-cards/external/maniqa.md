---
owner: docs-team
purpose: 'Documentation for Model Card: MANIQA.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: MANIQA'
---

## Model Summary

> MANIQA (Multi-dimension Attention Network IQA) uses Vision Transformer with multi-dimension attention for comprehensive quality assessment. **🏆 BEST PERFORMER** with highest correlations (PLCC 0.56, SRCC 0.53) on DIQA-5000, but extremely high latency (1845ms) limits production use to teacher/oracle role.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-maniqa` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | 🏆 BEST PERFORMER (teacher/oracle role) |
| **Priority** | P0 (Critical - highest accuracy) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | Vision Transformer + Multi-Dimension Attention Network |
| **Parameters** | ~25M |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('maniqa')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Multi-Dimension Attention Quality Assessment |
| **Role in Pipeline** | Teacher/oracle model for difficult cases |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | Student model training, ensemble validation |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics (🏆 BEST OVERALL)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.5628** 🏆 | [0.5162, 0.6044] | **0.5258** 🏆 | [0.4772, 0.5672] |
| Sharpness | **0.5934** 🏆 | [0.5501, 0.6338] | **0.5592** 🏆 | [0.5089, 0.5976] |
| Color | **0.5694** 🏆 | [0.5267, 0.6100] | **0.5459** 🏆 | [0.5010, 0.5845] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.6861 | 0.8469 |
| Sharpness | 0.6881 | 0.8417 |
| Color | 0.6423 | 0.7942 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 1845 ms ⚠️ |
| Model Load Time | 12.6 s |

---

## 4. Limitations & Known Issues

### Production Constraints

- ⚠️ **Extremely High Latency**: 1845ms (1.8s) per image makes real-time use impractical
- Best suited as teacher/oracle model, not for default production inference
- Use for student training labels and validating difficult cases

### Key Findings

- **🏆 Best performer overall** - highest correlations across all dimensions
- Multi-dimension attention captures global quality features effectively
- All dimensions show strong positive correlations (>0.54 SRCC)
- Vision Transformer architecture provides robust quality assessment

---

## 5. Citation

```bibtex
@inproceedings{yang2022maniqa,
  title={MANIQA: Multi-dimension Attention Network for No-Reference Image Quality Assessment},
  author={Yang, Sidi and others},
  booktitle={CVPR Workshops},
  year={2022}
}
```

---

## Production Readiness: 🏆 BEST PERFORMER (highest accuracy, use as teacher/oracle due to high latency)