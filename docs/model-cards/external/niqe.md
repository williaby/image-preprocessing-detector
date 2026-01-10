---
owner: docs-team
purpose: 'Documentation for Model Card: NIQE.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: NIQE'
---

## Model Summary

> NIQE (Natural Image Quality Evaluator) is a completely blind NSS-based IQA method using MVG (Multivariate Gaussian) modeling. Shows negative correlations on documents (PLCC -0.06, SRCC -0.21) - **📊 REFERENCE BASELINE** demonstrating NSS limitations.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-niqe` |
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
| **Architecture** | NSS Features + MVG Distance (Classical CV) |
| **Parameters** | ~0 learnable (handcrafted features) |
| **Precision** | FP32 |
| **Input Size** | Variable |
| **Output Format** | Quality score (lower = better) |
| **Source** | PyIQA library (`pyiqa.create_metric('niqe')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Completely Blind No-Reference IQA |
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

**Correlation Metrics (NEGATIVE)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **-0.0550** | [-0.1283, 0.0170] | **-0.2074** | [-0.2655, -0.1459] |
| Sharpness | **-0.0550** | [-0.1283, 0.0170] | **-0.1243** | [-0.1871, -0.0627] |
| Color | **-0.1311** | [-0.2079, -0.0577] | **-0.2068** | [-0.2669, -0.1444] |

**Error Metrics (HIGH)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 1.0121 | 1.2319 |
| Sharpness | 0.9984 | 1.2174 |
| Color | 0.9757 | 1.1834 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 30 ms |
| Model Load Time | 0.5 s |

---

## 4. Limitations & Known Issues

### Reference Baseline Context

- Completely blind IQA (no training data required)
- Models "pristine" natural image statistics
- Negative correlation shows documents violate natural image assumptions

### Key Findings

- Negative SRCC (-0.21) indicates inverse prediction on documents
- "Completely blind" approach fails when domain assumptions violated
- Documents differ fundamentally from natural image statistics

---

## 5. Citation

```bibtex
@article{mittal2013niqe,
  title={Making a "Completely Blind" Image Quality Analyzer},
  author={Mittal, Anish and others},
  journal={IEEE SPL},
  year={2013}
}
```

---

## Production Readiness: 📊 REFERENCE BASELINE (classical CV comparison - negative correlation on documents)