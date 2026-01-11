---
owner: docs-team
purpose: 'Documentation for Model Card: HyperIQA.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: HyperIQA'
---

## Model Summary

> HyperIQA uses a self-adaptive hyper-network for content-aware quality perception with ResNet-50 backbone. **BEST TIER 1 PERFORMER** with highest correlations (PLCC 0.33) among efficient models, making it the top candidate for fine-tuning.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-hyperiqa` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | ⭐ TOP TIER 1 CANDIDATE |
| **Priority** | P1 (High - best efficient model) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-50 + HyperNetwork (content-adaptive weights) |
| **Parameters** | ~25M (ResNet-50 base + hypernetwork) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-100] |
| **Source** | PyIQA library (`pyiqa.create_metric('hyperiqa')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Content-Aware Quality Assessment |
| **Role in Pipeline** | Top Tier 1 fine-tuning candidate |
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

**Correlation Metrics (BEST TIER 1)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.3271** ⭐ | [0.2622, 0.3903] | **0.2362** | [0.1717, 0.2978] |
| Sharpness | **0.3782** ⭐ | [0.3182, 0.4386] | **0.3034** | [0.2429, 0.3614] |
| Color | **0.3190** | [0.2589, 0.3808] | **0.2390** | [0.1749, 0.3004] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.6833 | 0.8652 |
| Sharpness | 0.6815 | 0.8605 |
| Color | 0.6393 | 0.8116 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 152 ms |
| Model Load Time | 6.0 s |

---

## 4. Limitations & Known Issues

### Production Path

- Correlation gap: PLCC 0.33 vs target >0.70 (0.37 points gap)
- Best among efficient models (Tier 1)
- Strong candidate for fine-tuning on DIQA-5000

### Key Findings

- **Best Tier 1 performer** - highest correlations among efficient models
- Self-adaptive hypernetwork enables content-aware quality perception
- Sharpness dimension shows strongest correlation (0.38 PLCC)
- 152ms latency acceptable for production

---

## 5. Citation

```bibtex
@inproceedings{su2020hyperiqa,
  title={Blindly Assess Image Quality in the Wild Guided by a Self-Adaptive Hyper Network},
  author={Su, Shaolin and others},
  booktitle={CVPR},
  year={2020}
}
```

---

## Production Readiness: ⭐ TOP TIER 1 CANDIDATE (best among efficient models, needs fine-tuning)
