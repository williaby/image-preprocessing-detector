---
owner: docs-team
purpose: 'Documentation for Model Card: DeQA-Mix Mixed-Dimension Model.'
schema_type: common
status: published
tags:
- iqa
- vlm
- deqa_doc
- vquala_2025
- multi_task
title: 'Model Card: DeQA-Mix'
---

## Model Summary

> DeQA-Mix is a mixed-dimension variant of the DeQA-Doc framework that trains a single model to predict all three quality dimensions (overall, sharpness, color) simultaneously. Unlike DIQA_model which uses separate specialists, DeQA-Mix uses multi-task learning for efficient single-pass inference.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `DeQA-Mix` |
| **Project** | Prepare-Doc |
| **Phase** | External VLM (DIQA Track A Candidate) |
| **Status** | `pretrained` (VQualA 2025 Component) |
| **Priority** | P1 (High - efficient multi-task) |
| **Last Updated** | 2026-01-16 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | mPLUG-Owl2-7B with Multi-Task Head |
| **Parameters** | ~7B |
| **Precision** | BF16 / FP16 |
| **Input Size** | Variable (1024×1024 recommended) |
| **Output Format** | 3 quality scores (overall, sharpness, color) |
| **Output Type** | Multi-task regression |
| **Source** | [ModelScope - DeQA-Mix](https://modelscope.cn) |
| **License** | Research (check original) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Multi-Dimension Document Quality Assessment |
| **Role in Pipeline** | Efficient all-in-one IQA scoring |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | Ensemble fusion, production deployment |

### Intended Use

- **Primary**: Single-pass quality assessment across all dimensions
- **Secondary**: Efficient pseudo-label generation
- **Out of Scope**: Cases requiring maximum per-dimension accuracy

### Advantages Over Dimension-Specific Models

| Aspect | DeQA-Mix | DIQA_model (Separate) |
|--------|----------|----------------------|
| Inference Passes | 1 | 3 |
| Inference Time | ~2-3s | ~6-9s |
| GPU Memory | ~16-24 GB | ~16-24 GB (per model) |
| Cross-Dimension Learning | Yes | No |
| Per-Dimension Optimization | Less | More |

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Base Model** | mPLUG-Owl2-7B |
| **Training Method** | Multi-task DeQA-Score |
| **Epochs** | 3 |
| **Batch Size** | 8 (at 1024×1024) |
| **Learning Rate** | 2e-5 |
| **Optimizer** | AdamW |
| **Scheduler** | Cosine decay |
| **Loss Function** | Combined fidelity loss (weighted by dimension) |

### Multi-Task Training Approach

```python
# Mixed dimension loss combination
loss = (
    weight_overall * fidelity_loss(pred_overall, soft_label_overall) +
    weight_sharpness * fidelity_loss(pred_sharpness, soft_label_sharpness) +
    weight_color * fidelity_loss(pred_color, soft_label_color)
)

# Typical weights (balanced training)
weights = {
    "overall": 1.0,
    "sharpness": 1.0,
    "color": 1.0
}
```

### Shared Representations

Unlike separate specialists, DeQA-Mix learns shared visual representations that benefit all dimensions:

- **Shared Vision Encoder**: CLIP ViT-L processes image once
- **Shared Language Features**: LLaMA-2-7B encodes quality semantics jointly
- **Task-Specific Heads**: Final layers specialize for each dimension

---

## 4. Performance Metrics

### Expected Performance

| Dimension | Expected SRCC | Comparison to Specialists |
|-----------|---------------|--------------------------|
| Overall | ~0.82-0.88 | Slightly lower |
| Sharpness | ~0.82-0.90 | Slightly lower |
| Color | ~0.82-0.90 | Slightly lower |

**Trade-off**: ~5-10% lower per-dimension accuracy for 3× faster inference.

### Inference Performance

| Device | Latency (all dims) | Throughput | Memory |
|--------|-------------------|------------|--------|
| A100 GPU | ~2000-3000 ms | ~0.3-0.5 img/s | ~16-24 GB |
| T4 GPU | Not recommended | - | - |

---

## 5. Preprocessing Requirements

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

# Load mixed-dimension model (single model for all dimensions)
model = AutoModel.from_pretrained("DeQA-Mix")

# Process image
image = Image.open("document.png").convert("RGB").resize((1024, 1024))

# Get all dimension scores in single pass
scores = model.predict(image)
# scores = {"overall": 3.8, "sharpness": 4.1, "color": 3.9}

# Compute weighted final score
final_score = (
    0.5 * scores["overall"] +
    0.25 * scores["sharpness"] +
    0.25 * scores["color"]
)
```

---

## 6. Architecture Details

### Multi-Task Head Design

```text
                  ┌─────────────────┐
                  │  CLIP ViT-L     │
                  │  Vision Encoder │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │    Q-Former     │
                  │  (6 layers)     │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │   LLaMA-2-7B    │
                  │    Decoder      │
                  └────────┬────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
     │  Overall    ││  Sharpness  ││  Color      │
     │    Head     ││    Head     ││    Head     │
     └─────────────┘└─────────────┘└─────────────┘
```

### Output Format

```python
# Model output structure
{
    "overall": 3.8,      # [1, 5] scale
    "sharpness": 4.1,    # [1, 5] scale
    "color": 3.9,        # [1, 5] scale
    "confidence": {
        "overall": 0.85,
        "sharpness": 0.90,
        "color": 0.88
    }
}
```

---

## 7. Limitations & Known Issues

### Limitations

- **Accuracy Trade-off**: ~5-10% lower per-dimension accuracy vs specialists
- **Task Interference**: Multi-task learning may cause negative transfer
- **Fixed Weighting**: Dimension importance fixed at training time
- **GPU Requirements**: Still requires high-memory GPU (A100-class)

### When to Use DeQA-Mix vs DIQA_model

| Scenario | Recommended Model |
|----------|-------------------|
| Speed-critical applications | DeQA-Mix |
| Maximum per-dimension accuracy | DIQA_model (specialists) |
| Resource-constrained environments | DeQA-Mix |
| Research/benchmarking | DIQA_model |

---

## 8. Files & Artifacts

| File | Description | Location |
|------|-------------|----------|
| DeQA-Mix checkpoint | Multi-task model | ModelScope |
| Config | Model configuration | GitHub |

### Storage Locations

| Environment | Path |
|-------------|------|
| **ModelScope** | `DeQA-Mix` |
| **GitHub** | `https://github.com/Junjie-Gao19/DeQA-Doc` |

---

## 9. Citation

```bibtex
@inproceedings{gao2025deqa,
  title={DeQA-Doc: Adapting DeQA-Score to Document Image Quality Assessment},
  author={Gao, Junjie and others},
  booktitle={ICCV Workshops (VQualA 2025)},
  year={2025}
}
```

---

## 10. Related Models

- [mPLUG-Owl2-7B](deqa_mplug_owl2_7b.md) - Base architecture
- [DIQA_model](diqa_model_dimension_specific.md) - Dimension specialists
- [Qwen2.5-VL-7B](deqa_qwen25_vl_7b.md) - Alternative VLM

---

## Production Readiness: External VLM (Efficient multi-task, single-pass inference, 3× faster than specialists)
