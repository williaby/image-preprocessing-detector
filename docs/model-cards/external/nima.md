# Model Card: NIMA

## Model Summary

> NIMA (Neural Image Assessment) uses MobileNet backbone for aesthetic quality prediction. Shows **negative correlations** on documents (PLCC -0.12, SRCC -0.25), demonstrating fundamental domain mismatch between aesthetic scoring and document quality assessment.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-nima` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Evaluation) |
| **Status** | ❌ NOT RECOMMENDED |
| **Priority** | N/A (Evaluation Only) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | MobileNet + Aesthetic Score Distribution |
| **Parameters** | ~3.5M (MobileNet backbone) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Quality score distribution [1-10] |
| **Source** | PyIQA library (`pyiqa.create_metric('nima')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Aesthetic Image Quality Assessment |
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
| Overall | **-0.1232** | [-0.1853, -0.0590] | **-0.2484** | [-0.3057, -0.1898] |
| Sharpness | **-0.1232** | [-0.1853, -0.0590] | **-0.1283** | [-0.1923, -0.0610] |
| Color | **-0.2318** | [-0.2892, -0.1677] | **-0.2595** | [-0.3136, -0.1966] |

**Error Metrics (HIGH)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 1.0080 | 1.2030 |
| Sharpness | 0.9722 | 1.1629 |
| Color | 1.0293 | 1.2252 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 50 ms |
| Model Load Time | 3.0 s |

---

## 4. Limitations & Known Issues

### Critical Issues

1. **Negative Correlation**: SRCC -0.25 indicates model predictions are inversely correlated with document quality
2. **Aesthetic vs. Document Quality**: Trained for photography aesthetics, fundamentally different from document quality
3. **Not Suitable**: For any document IQA application

### Key Findings

- **Worst correlation** among efficient models (negative SRCC)
- Aesthetic quality scoring inversely predicts document quality
- Fast inference (50ms) but fundamentally unsuitable for task

---

## 5. Citation

```bibtex
@inproceedings{talebi2018nima,
  title={NIMA: Neural Image Assessment},
  author={Talebi, Hossein and Milanfar, Peyman},
  booktitle={IEEE TIP},
  year={2018}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (negative correlation - aesthetic/document domain mismatch)
