---
owner: docs-team
purpose: 'Documentation for Model Card: QualiCLIP.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: QualiCLIP'
---

## Model Summary

> QualiCLIP is an opinion-unaware IQA method leveraging CLIP's vision-language pretraining with antonym prompts ("good photo"/"bad photo"). Evaluated on DIQA-5000, it shows moderate positive correlations (PLCC 0.22-0.31) - better than ImageNet-only backbones but requires fine-tuning for production document IQA.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-qualiclip` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Pretrained (DIQA Candidate) |
| **Status** | `pretrained` |
| **Priority** | P2 (DIQA Color Specialist Candidate) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | QualiCLIP (CLIP-based Opinion-Unaware IQA) |
| **Parameters** | ~150M (CLIP ViT-B/16 backbone) |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Key Innovation** | Vision-language quality assessment without human labels |
| **Source** | PyIQA library (`pyiqa.create_metric('qualiclip')`) |
| **License** | MIT |

### How It Works

- Uses CLIP's pretrained vision-language alignment
- Quality assessed via similarity to antonym prompts ("good photo" vs "bad photo")
- No human quality labels needed during training (opinion-unaware)

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | State-of-the-art no-reference IQA evaluation |
| **Role in Pipeline** | DIQA color specialist candidate |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | DIQA ensemble (planned) |

---

## 3. Preprocessing Requirements

### CLIP Normalization (Different from ImageNet!)

```python
mean = [0.48145466, 0.4578275, 0.40821073]  # CLIP RGB mean
std = [0.26862954, 0.26130258, 0.27577711]   # CLIP RGB std
```

---

## 4. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `PyIQA-qualiclip` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | **0.2216** | [0.1439, 0.2875] | 0.1038 | [0.0364, 0.1653] |
| Sharpness | **0.3070** | [0.2351, 0.3688] | **0.1963** | [0.1309, 0.2549] |
| Color | **0.2153** | [0.1371, 0.2806] | 0.1018 | [0.0341, 0.1599] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.6101 | 0.7564 |
| Sharpness | 0.5835 | 0.7283 |
| Color | 0.5915 | 0.7311 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 143 ms (higher due to CLIP) |
| Model Load Time | 17.2 s (large model) |

### Key Findings

- **Best sharpness** (PLCC=0.31) among opinion-unaware methods
- **Positive correlations** across all dimensions (unlike EfficientNet/Swin)
- **Still below production threshold** (target: PLCC >0.70)
- **High latency** due to CLIP dual-encoder architecture

---

## 5. Limitations & Known Issues

### Domain Gap

- **Photo quality prompts**: "good photo"/"bad photo" not optimized for documents
- **224×224 resolution**: May lose document-specific details
- **Generic quality**: Aesthetic quality ≠ document readability

### Production Blockers

- Insufficient correlation (PLCC=0.22 vs target >0.70)
- High latency (143ms vs target <100ms)
- Requires fine-tuning for document-specific quality

---

## 6. Recommended Next Steps

1. **Fine-tune on DIQA-5000** with document-specific prompts
2. **Focus on color dimension** (current weakness: SRCC=0.10)
3. **Optimize inference** via ONNX export or knowledge distillation

---

## 7. Citation

```bibtex
@inproceedings{wang2023qualiclip,
  title={Exploring CLIP for Assessing the Look and Feel of Images},
  author={Wang, Jianyi and Chan, Kelvin CK and Loy, Chen Change},
  booktitle={AAAI},
  year={2023}
}
```

---

## Production Readiness: ⚠️ REQUIRES FINE-TUNING (best baseline, but below threshold)