---
owner: docs-team
purpose: 'Documentation for Model Card: CLIP-IQA.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: CLIP-IQA'
---

## Model Summary

> CLIP-IQA leverages CLIP's vision-language pretraining for quality assessment through quality-aware contrastive learning. Shows moderate positive correlations (PLCC 0.24-0.32) on documents - better than ImageNet-only backbones but requires fine-tuning for production document IQA.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-clipiqa` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | ⚠️ REQUIRES FINE-TUNING |
| **Priority** | P2 (Fine-tuning candidate) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | CLIP ViT-B/32 with Quality-Aware Contrastive Head |
| **Parameters** | ~151M (CLIP ViT-B/32 backbone) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('clipiqa')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Vision-Language Quality Assessment |
| **Role in Pipeline** | Candidate for fine-tuning |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | DIQA ensemble (after fine-tuning) |

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
| Overall | **0.2397** | [0.1768, 0.3021] | 0.1596 | [0.1041, 0.2182] |
| Sharpness | **0.3159** | [0.2553, 0.3754] | **0.2409** | [0.1835, 0.2982] |
| Color | 0.2202 | [0.1560, 0.2841] | 0.1461 | [0.0876, 0.2079] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.6848 | 0.8507 |
| Sharpness | 0.6619 | 0.8251 |
| Color | 0.6639 | 0.8267 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 116 ms |
| Model Load Time | 7.1 s |

---

## 4. Limitations & Known Issues

### Production Blockers

- Correlation below target (PLCC=0.24 vs target >0.70)
- Latency acceptable (116ms)
- Requires fine-tuning on DIQA-5000 for production use

### Key Findings

- Positive correlations across all dimensions (good baseline)
- Best sharpness detection (PLCC=0.32) among CLIP-based methods
- CLIP features show transfer potential for document IQA

---

## 5. Citation

```bibtex
@inproceedings{wang2023clipiqa,
  title={Exploring CLIP for Assessing the Look and Feel of Images},
  author={Wang, Jianyi and Chan, Kelvin CK and Loy, Chen Change},
  booktitle={AAAI},
  year={2023}
}
```

---

## Production Readiness: ⚠️ REQUIRES FINE-TUNING (positive correlations, below target)
