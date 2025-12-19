# Model Card: LIQE

## Model Summary

> LIQE (Learnable Image Quality Evaluator) uses CLIP backbone with quality-aware text prompts for opinion-unaware assessment. **⭐⭐ HIGHLY RECOMMENDED** - second best performer with excellent correlations (PLCC 0.51, SRCC 0.40) and best MAE/RMSE metrics.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-liqe` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | ⭐⭐ HIGHLY RECOMMENDED |
| **Priority** | P1 (High - second best performer) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | CLIP ViT-B/16 + Quality-Aware Text Encoder |
| **Parameters** | ~150M (CLIP ViT-B/16 backbone) |
| **Precision** | FP32 |
| **Input Size** | 224×224×3 (RGB) |
| **Output Format** | Single quality score [0-1] |
| **Source** | PyIQA library (`pyiqa.create_metric('liqe')`) |
| **License** | MIT |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | CLIP-based Quality Assessment with Text Prompts |
| **Role in Pipeline** | Top candidate for fine-tuning, ensemble leader |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | DIQA ensemble (primary) |

---

## 3. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics (⭐⭐ SECOND BEST)**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.5107** ⭐⭐ | [0.4628, 0.5547] | **0.4031** ⭐⭐ | [0.3455, 0.4586] |
| Sharpness | **0.5267** ⭐⭐ | [0.4784, 0.5698] | **0.4478** ⭐⭐ | [0.3915, 0.4991] |
| Color | **0.5058** ⭐⭐ | [0.4556, 0.5520] | **0.4365** ⭐⭐ | [0.3815, 0.4894] |

**Error Metrics (BEST)**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | **0.5107** 🏆 | **0.6461** 🏆 |
| Sharpness | **0.4958** 🏆 | **0.6238** 🏆 |
| Color | 0.5240 | 0.6560 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 150 ms |
| Model Load Time | 10.0 s |

---

## 4. Limitations & Known Issues

### Production Path

- Second best correlations after MANIQA (PLCC 0.51 vs 0.56)
- Best MAE/RMSE error metrics among all models
- 150ms latency is production-acceptable

### Key Findings

- **Second best performer** - excellent balance of accuracy and speed
- **Best error metrics** - lowest MAE/RMSE across all models
- CLIP-based architecture provides robust quality perception
- All dimensions show strong positive correlations (>0.40 SRCC)

---

## 5. Citation

```bibtex
@inproceedings{zhang2023liqe,
  title={Blind Image Quality Assessment via Vision-Language Correspondence: A Multitask Learning Perspective},
  author={Zhang, Weixia and others},
  booktitle={CVPR},
  year={2023}
}
```

---

## Production Readiness: ⭐⭐ HIGHLY RECOMMENDED (second best performer, best error metrics)
