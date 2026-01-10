# Model Card: PaQ-2-PiQ

## Model Summary

> PaQ-2-PiQ (Patches to Pictures) uses ResNet-18 for patch-based quality aggregation. Shows near-zero/negative correlations on documents (PLCC -0.02, SRCC -0.20), demonstrating that patch-level natural image quality doesn't transfer to documents.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-paq2piq` |
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
| **Architecture** | ResNet-18 + Patch Aggregation |
| **Parameters** | ~11M (ResNet-18 backbone) |
| **Precision** | FP32 |
| **Input Size** | Variable (patch-based) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('paq2piq')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Patch-based Picture Quality Assessment |
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

**Correlation Metrics (CRITICAL: Near-zero/negative)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **-0.0206** | [-0.0880, 0.0468] | **-0.1953** | [-0.2565, -0.1304] |
| Sharpness | **-0.0206** | [-0.0880, 0.0468] | **-0.0853** | [-0.1486, -0.0180] |
| Color | **-0.1466** | [-0.2123, -0.0840] | **-0.2275** | [-0.2894, -0.1641] |

**Error Metrics (HIGH)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.7905 | 1.0019 |
| Sharpness | 0.7776 | 0.9943 |
| Color | 0.7385 | 0.9468 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 80 ms |
| Model Load Time | 4.0 s |

---

## 4. Limitations & Known Issues

### Critical Issues

1. **Near-Zero/Negative Correlation**: PLCC -0.02 (random), SRCC -0.20 (inversely correlated)
2. **Domain Mismatch**: Patch-based natural image quality doesn't apply to documents
3. **Not Suitable**: For any document IQA application

### Key Findings

- Patch-level aggregation fails on document images
- Color dimension shows strongest negative correlation (-0.23 SRCC)
- Fast inference (80ms) but fundamentally unsuitable for task

---

## 5. Citation

```bibtex
@inproceedings{ying2020paq2piq,
  title={From Patches to Pictures (PaQ-2-PiQ): Mapping the Perceptual Space of Picture Quality},
  author={Ying, Zhenqiang and others},
  booktitle={CVPR},
  year={2020}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (near-zero/negative correlation - domain mismatch)
