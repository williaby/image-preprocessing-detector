---
owner: docs-team
purpose: 'Documentation for Model Card: DIQA_model Dimension-Specific Models.'
schema_type: common
status: published
tags:
- iqa
- vlm
- deqa_doc
- vquala_2025
- dimension_specific
title: 'Model Card: DIQA_model (Dimension-Specific)'
---

## Model Summary

> DIQA_model is a collection of dimension-specific quality assessment models from the DeQA-Doc framework. Three separate models are trained independently for overall quality, sharpness, and color fidelity dimensions. Based on mPLUG-Owl2-7B architecture with DeQA-Score soft label regression.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `DIQA_model` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External VLM (DIQA Track A Candidate) |
| **Status** | `pretrained` (VQualA 2025 Component) |
| **Priority** | P1 (High - dimension specialists) |
| **Last Updated** | 2026-01-16 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | mPLUG-Owl2-7B (CLIP ViT-L + Q-Former + LLaMA-2-7B) |
| **Parameters** | ~7B per model (3 models total) |
| **Precision** | BF16 / FP16 |
| **Input Size** | Variable (1024×1024 recommended) |
| **Output Format** | Single dimension quality score per model |
| **Output Type** | Regression (soft label distribution) |
| **Source** | [ModelScope - DIQA_model](https://modelscope.cn) |
| **License** | Research (check original) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Dimension-Specific Document Image Quality Assessment |
| **Role in Pipeline** | Specialized IQA scoring per quality dimension |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | Ensemble fusion, pseudo-label generation |

### Intended Use

- **Primary**: Per-dimension quality scoring (overall, sharpness, color)
- **Secondary**: Training labels for lightweight student models
- **Out of Scope**: Real-time inference (3 model passes required)

---

## 3. Model Variants

### DIQA_model consists of three independently trained specialists:

| Dimension | Purpose | Training Focus |
|-----------|---------|----------------|
| **Overall** | Global document quality | Combined degradation assessment |
| **Sharpness** | Blur/focus quality | Edge clarity, text readability |
| **Color** | Color fidelity | Color accuracy, saturation, balance |

### Training Strategy

Each model is trained separately on the same DIQA-5000 dataset but with different target labels:

```python
# Dimension-specific training targets
targets = {
    "overall": sample["mos_overall"],      # Overall quality score
    "sharpness": sample["mos_sharpness"],  # Sharpness score
    "color": sample["mos_color"]           # Color fidelity score
}
```

---

## 4. Training Details

| Field | Value |
|-------|-------|
| **Base Model** | mPLUG-Owl2-7B |
| **Training Method** | DeQA-Score (per-dimension) |
| **Epochs** | 3 per dimension |
| **Batch Size** | 8 (at 1024×1024) |
| **Learning Rate** | 2e-5 |
| **Optimizer** | AdamW |
| **Scheduler** | Cosine decay |
| **Loss Function** | Fidelity loss (soft labels) |

### Soft Label Construction

Same as base mPLUG-Owl2-7B model:
- **Pseudo Variance**: σ = 0.2 × (max - min) = 0.8 for [1, 5] score range
- **Linear Interpolation**: Distributes probability mass between adjacent quality levels

---

## 5. Performance Metrics

### Individual Dimension Performance

| Model | Target Dimension | Expected SRCC | Notes |
|-------|-----------------|---------------|-------|
| DIQA_overall | Overall | ~0.85-0.90 | General quality |
| DIQA_sharpness | Sharpness | ~0.85-0.93 | Best dimension |
| DIQA_color | Color | ~0.85-0.92 | Second best |

### Final Score Computation

DIQA-5000 challenge uses weighted combination:

```python
final_score = (
    0.5 * srcc_overall +
    0.25 * srcc_sharpness +
    0.25 * srcc_color
)
```

### Inference Performance (Per Model)

| Device | Latency | Memory |
|--------|---------|--------|
| A100 GPU | ~2000-3000 ms | ~16-24 GB |
| T4 GPU | Not recommended | - |

**Note**: Full 3-dimension assessment requires 3× inference time.

---

## 6. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | Variable (1024×1024 recommended) |
| **Color Space** | RGB |
| **Value Range** | Model-specific normalization |

### Usage Example

```python
from modelscope import AutoModel
from PIL import Image

# Load dimension-specific model
model_overall = AutoModel.from_pretrained("DIQA_model/overall")
model_sharpness = AutoModel.from_pretrained("DIQA_model/sharpness")
model_color = AutoModel.from_pretrained("DIQA_model/color")

# Process image
image = Image.open("document.png").convert("RGB").resize((1024, 1024))

# Get per-dimension scores
score_overall = model_overall.predict(image)
score_sharpness = model_sharpness.predict(image)
score_color = model_color.predict(image)

# Compute weighted final score
final_score = 0.5 * score_overall + 0.25 * score_sharpness + 0.25 * score_color
```

---

## 7. Limitations & Known Issues

### Limitations

- **3× Inference Cost**: Requires running 3 separate models for full assessment
- **GPU Memory**: Each model requires ~16-24 GB
- **No Cross-Dimension Learning**: Models don't share information between dimensions
- **Consistency**: Scores may not be perfectly aligned across dimensions

### Advantages vs Single Multi-Task Model

| Aspect | Dimension-Specific | Multi-Task (DeQA-Mix) |
|--------|-------------------|----------------------|
| Training | Simpler, focused | More complex |
| Inference | 3× slower | Single pass |
| Accuracy | Potentially higher per-dimension | Balanced across dimensions |
| Flexibility | Can update dimensions independently | All-or-nothing updates |

---

## 8. Ensemble Integration

DIQA_model can be combined with other models in the DeQA-Doc ensemble:

| Component | Role | Weight |
|-----------|------|--------|
| DIQA_model (overall) | Overall specialist | Variable |
| DIQA_model (sharpness) | Sharpness specialist | Variable |
| DIQA_model (color) | Color specialist | Variable |
| m0, m1, m3 | mPLUG-Owl2 variants | Variable |
| Q0, Q1 | Qwen2.5-VL variants | Variable |

---

## 9. Files & Artifacts

| File | Description | Location |
|------|-------------|----------|
| DIQA_overall | Overall quality model | ModelScope |
| DIQA_sharpness | Sharpness model | ModelScope |
| DIQA_color | Color fidelity model | ModelScope |

### Storage Locations

| Environment | Path |
|-------------|------|
| **ModelScope** | `DIQA_model/overall`, `DIQA_model/sharpness`, `DIQA_model/color` |
| **GitHub** | `https://github.com/Junjie-Gao19/DeQA-Doc` |

---

## 10. Citation

```bibtex
@inproceedings{gao2025deqa,
  title={DeQA-Doc: Adapting DeQA-Score to Document Image Quality Assessment},
  author={Gao, Junjie and others},
  booktitle={ICCV Workshops (VQualA 2025)},
  year={2025}
}
```

---

## 11. Related Models

- [mPLUG-Owl2-7B](deqa_mplug_owl2_7b.md) - Base architecture
- [DeQA-Mix](deqa_mix.md) - Mixed-dimension alternative
- [Qwen2.5-VL-7B](deqa_qwen25_vl_7b.md) - Alternative VLM

---

## Production Readiness: External VLM (Dimension specialists, 3× inference cost, high accuracy per dimension)
