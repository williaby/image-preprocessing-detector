---
owner: docs-team
purpose: 'Documentation for Model Card: BRISQUE.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: BRISQUE'
---

## Model Summary

> BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator) is a classical NSS-based IQA method using spatial domain features with SVM regression. Shows near-zero correlations on documents (PLCC 0.09, SRCC -0.06) - **📊 REFERENCE BASELINE** for classical CV comparison.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-brisque` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Evaluation) |
| **Status** | 📊 REFERENCE BASELINE |
| **Priority** | N/A (Reference Only) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | NSS Features + SVM Regression (Classical CV) |
| **Parameters** | ~36 features (NOT a neural network) |
| **Precision** | FP32 |
| **Input Size** | Variable |
| **Output Format** | Quality score (lower = better) |
| **Source** | PyIQA library (`pyiqa.create_metric('brisque')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | NSS-based No-Reference IQA |
| **Role in Pipeline** | Reference baseline (classical CV comparison) |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | None (reference only) |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics (NEAR-ZERO)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | 0.0928 | [0.0248, 0.1577] | -0.0556 | [-0.1232, 0.0110] |
| Sharpness | 0.0928 | [0.0248, 0.1577] | 0.0329 | [-0.0327, 0.0981] |
| Color | 0.0220 | [-0.0478, 0.0889] | -0.0562 | [-0.1222, 0.0095] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.8080 | 0.9861 |
| Sharpness | 0.7904 | 0.9657 |
| Color | 0.7913 | 0.9629 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 20 ms |
| Model Load Time | 0.5 s |

---

## 4. Limitations & Known Issues

### Reference Baseline Context

- Classical NSS-based method (NOT a neural network)
- Demonstrates limitations of handcrafted features on documents
- Fast but near-random performance on document IQA

### Key Findings

- Near-zero correlation indicates random prediction quality
- NSS features designed for natural images, not documents
- Serves as baseline to demonstrate DL model improvements

---

## 5. Citation

```bibtex
@article{mittal2012brisque,
  title={No-Reference Image Quality Assessment in the Spatial Domain},
  author={Mittal, Anish and others},
  journal={IEEE TIP},
  year={2012}
}
```

---

## Production Readiness: 📊 REFERENCE BASELINE (classical CV comparison - near-zero correlation on documents)