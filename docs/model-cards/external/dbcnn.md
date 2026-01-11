---
owner: docs-team
purpose: 'Documentation for Model Card: DBCNN.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: DBCNN'
---

## Model Summary

> DBCNN (Deep Bilinear CNN) uses two parallel VGG-16 streams for synthetic and authentic distortion assessment. Shows moderate positive correlations (PLCC 0.29, SRCC 0.29) on documents with efficient 100ms inference - **✅ RECOMMENDED** as ensemble member.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-dbcnn` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | ✅ RECOMMENDED (ensemble member) |
| **Priority** | P2 (Medium - ensemble candidate) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | Deep Bilinear CNN (dual VGG-16 streams) |
| **Parameters** | ~30M (2× VGG-16 streams) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('dbcnn')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Dual-Stream Distortion Quality Assessment |
| **Role in Pipeline** | Ensemble member for quality scoring |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | DIQA ensemble |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.2880** | [0.2271, 0.3469] | **0.2880** | [0.2271, 0.3469] |
| Sharpness | **0.3568** | [0.2995, 0.4131] | **0.3737** | [0.3167, 0.4286] |
| Color | **0.2841** | [0.2241, 0.3413] | **0.3044** | [0.2447, 0.3581] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.5224 | 0.7105 |
| Sharpness | 0.5046 | 0.6925 |
| Color | 0.4943 | 0.6698 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 100 ms |
| Model Load Time | 5.0 s |

---

## 4. Limitations & Known Issues

### Production Path

- Correlation gap: PLCC 0.29 vs target >0.70 (0.41 points gap)
- Good for ensemble member role
- Efficient inference (100ms) suitable for production

### Key Findings

- **Dual-stream architecture** handles both synthetic and authentic distortions
- Sharpness dimension shows strongest correlation (0.37 SRCC)
- Consistent performance across dimensions
- 100ms latency enables real-time processing

---

## 5. Citation

```bibtex
@article{zhang2018dbcnn,
  title={Blind Image Quality Assessment Using A Deep Bilinear Convolutional Neural Network},
  author={Zhang, Weixia and others},
  journal={IEEE TCircuits},
  year={2018}
}
```

---

## Production Readiness: ✅ RECOMMENDED (ensemble member with efficient inference)
