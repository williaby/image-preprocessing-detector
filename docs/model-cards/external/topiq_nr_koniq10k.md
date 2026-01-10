---
owner: docs-team
purpose: 'Documentation for Model Card: TOPIQ-NR (KonIQ-10k).'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: TOPIQ-NR (KonIQ-10k)'
---

## Model Summary

> TOPIQ-NR uses Cross-scale Feature Attention Network (CFANet) for state-of-the-art no-reference IQA. Pretrained on KonIQ-10k, it shows the **highest correlations among tested pretrained IQA models** on DIQA-5000 (PLCC=0.24 overall, 0.30 sharpness). Strong candidate for DIQA ensemble.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-topiq_nr` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Ensemble Candidate) |
| **Status** | `pretrained` |
| **Priority** | P1 (High - Best Performing Baseline) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | TOPIQ-NR (CFANet - Cross-scale Feature Attention Network) |
| **Parameters** | ~25M (estimated) |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Pretraining** | KonIQ-10k (10,073 images with authentic distortions) |
| **Source** | PyIQA library (`pyiqa.create_metric('topiq_nr')`) |
| **License** | MIT |

### Key Innovation

- **Cross-scale features**: Multi-resolution quality assessment
- **Attention mechanism**: Focuses on quality-relevant regions
- **Top-down approach**: Semantics guide distortion analysis
- **KonIQ-10k training**: Authentic social media distortions

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | State-of-the-art no-reference IQA |
| **Role in Pipeline** | Primary DIQA ensemble candidate |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | DIQA stacker ensemble |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-topiq_nr` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics** (⭐ BEST AMONG PRETRAINED MODELS):

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.2425** ⭐ | [0.1671, 0.3079] | **0.1761** ⭐ | [0.1138, 0.2327] |
| Sharpness | **0.3013** ⭐ | [0.2280, 0.3653] | **0.2274** ⭐ | [0.1625, 0.2842] |
| Color | **0.2236** | [0.1505, 0.2892] | **0.1604** | [0.0996, 0.2170] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.8003 | 1.0146 |
| Sharpness | 0.8048 | 1.0088 |
| Color | 0.7519 | 0.9612 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 123 ms |
| Model Load Time | 5.3 s |

### Key Findings

- **Highest overall PLCC** (0.24) among all tested pretrained IQA models
- **Best sharpness correlation** (PLCC=0.30, SRCC=0.23)
- **Consistent positive correlations** across all dimensions
- **High MAE** (~0.8) indicates scale calibration needed

---

## 4. Limitations & Known Issues

### Scale Calibration Required

- **Issue**: MAE ~0.8 on 0-5 DIQA scale (16% error rate)
- **Cause**: Model outputs 0-100 scores vs DIQA 0-5 MOS
- **Solution**: Linear rescaling: `diqa_score = (topiq_score / 100) * 5`

### Domain Gap

- **Training**: Natural images (social media photos)
- **Evaluation**: Document images (scans, PDFs)
- **Impact**: Moderate correlations suggest domain adaptation needed

---

## 5. Recommended Integration

```python
import pyiqa

# Load TOPIQ-NR
model = pyiqa.create_metric('topiq_nr', device='cuda')

# Inference with scale calibration
raw_score = model(image_tensor).item()  # 0-100 scale
diqa_calibrated = (raw_score / 100.0) * 5.0  # 0-5 scale
```

---

## 6. Citation

```bibtex
@article{chen2023topiq,
  title={TOPIQ: A Top-down Approach from Semantics to Distortions for Image Quality Assessment},
  author={Chen, Chaofeng and Mo, Jiadi and Hou, Jingwen and Wu, Haoning and Liao, Liang and Sun, Wenxiu and Yan, Qiong and Lin, Weisi},
  journal={IEEE Transactions on Image Processing},
  year={2023}
}
```

---

## Production Readiness: ⚠️ BEST CANDIDATE (requires scale calibration + ensemble integration)