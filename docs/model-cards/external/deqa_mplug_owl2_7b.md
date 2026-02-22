---
owner: docs-team
purpose: 'Documentation for Model Card: DeQA-Doc mPLUG-Owl2-7B Base Model.'
schema_type: common
status: published
tags:
- iqa
- vlm
- deqa_doc
- vquala_2025
title: 'Model Card: DeQA-Doc mPLUG-Owl2-7B'
---

## Model Summary

> mPLUG-Owl2-7B is the base multimodal large language model (MLLM) for DeQA-Doc, the **VQualA 2025 DIQA Challenge Champion**. Uses CLIP ViT-L vision encoder, 6-layer Q-Former visual abstractor, and LLaMA-2-7B language decoder. Modified with absolute position embedding removal to handle variable document image resolutions.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `DeQA-mPLUG-Owl2-7B` |
| **Project** | Prepare-Doc |
| **Phase** | External VLM (DIQA Track A/B Candidate) |
| **Status** | `pretrained` (VQualA 2025 Champion) |
| **Priority** | P1 (High - competition winner) |
| **Last Updated** | 2026-01-16 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | CLIP ViT-L + Q-Former (6 layers) + LLaMA-2-7B |
| **Parameters** | ~7B (decoder) + ~427M (vision encoder) |
| **Precision** | BF16 / FP16 |
| **Input Size** | Variable (448×448 default, up to 1536×1536 with modification) |
| **Output Format** | Text-based quality scores (overall/sharpness/color) |
| **Output Type** | Regression (via soft label distribution) |
| **Source** | [GitHub - Junjie-Gao19/DeQA-Doc](https://github.com/Junjie-Gao19/DeQA-Doc) |
| **License** | Research (check original) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Document Image Quality Assessment via MLLM |
| **Role in Pipeline** | VLM-based IQA oracle / pseudo-label generator |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | Student model training, ensemble fusion |

### Intended Use

- **Primary**: Document image quality assessment with natural language scoring
- **Secondary**: Soft label generation for training traditional IQA models
- **Out of Scope**: Real-time production inference (high latency due to 7B parameters)

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Base Model** | mPLUG-Owl2-7B (HuggingFace) |
| **Training Method** | DeQA-Score soft label regression |
| **Epochs** | 3 |
| **Batch Size** | 64 (448×448), 8 (1024×1024), 2 (1536×1536) |
| **Learning Rate** | 2e-5 |
| **Optimizer** | AdamW |
| **Scheduler** | Cosine decay |
| **Hardware** | 8× NVIDIA A100 GPUs |
| **Loss Function** | Fidelity loss (soft label distribution) |
| **Reference Paper** | [arxiv:2507.12796](https://arxiv.org/abs/2507.12796) |

### Resolution Modification

The original mPLUG-Owl2 uses CLIP backbone with fixed 448×448 resolution via absolute position embeddings. DeQA-Doc removes these embeddings to enable flexible resolution processing:

- **Method**: Remove absolute position embeddings from CLIP encoder
- **Result**: Model can process document images at native resolution
- **Best Resolution**: 1024×1024 (Final Score 0.8989 vs 0.8849 at 448×448)

### Soft Label Construction

Standard IQA datasets provide only Mean Opinion Scores (MOS) without variance. DeQA-Doc constructs soft labels using:

1. **Pseudo Variance Method**: Assign fixed variance = 0.2 × (max - min) based on empirical statistics
2. **Linear Interpolation**: When score μ falls between adjacent levels cj and cj+1, distribute probability as: P(cj) = (cj+1 - μ) and P(cj+1) = (μ - cj)

---

## 4. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | Variable (up to 1536×1536 supported) |
| **Color Space** | RGB |
| **Value Range** | [0, 255] → normalized by vision encoder |
| **Channel Order** | HWC (PIL Image) |

### Preprocessing Pipeline

```python
from PIL import Image
from transformers import AutoProcessor

# Load processor (handles normalization internally)
processor = AutoProcessor.from_pretrained("MAGAer13/mplug-owl2-llama2-7b")

# Load and preprocess image
image = Image.open("document.png").convert("RGB")
# Resize to target resolution (1024×1024 recommended)
image = image.resize((1024, 1024))

# Process with model-specific preprocessing
inputs = processor(images=image, text=prompt, return_tensors="pt")
```

---

## 5. Performance Metrics

### VQualA 2025 Challenge Results

| Configuration | Final Score | Overall SRCC | Sharpness SRCC | Color SRCC |
|--------------|-------------|--------------|----------------|------------|
| m0 (Full tune, 1024×1024) | 0.8989 | N/R | N/R | N/R |
| m1 (LoRA, 1024×1024) | 0.9033 | N/R | N/R | N/R |
| m3 (KonIQ pretrain + LoRA) | N/R | N/R | N/R | N/R |

*N/R = Not reported individually; only Final Score available in published results.*

### Resolution Ablation

| Resolution | Final Score | Notes |
|------------|-------------|-------|
| 448×448 | 0.8849 | Default CLIP resolution |
| 1024×1024 | **0.8989** | Best single model |
| 1536×1536 | 0.8861 | Diminishing returns |

### Fine-tuning Method Comparison

| Method | Final Score | Notes |
|--------|-------------|-------|
| Full tuning | 0.8989 | All parameters updated |
| LoRA | **0.9033** | Parameter-efficient, better generalization |

### Inference Performance (Estimated)

| Device | Latency | Throughput | Memory |
|--------|---------|------------|--------|
| A100 GPU | ~2000-3000 ms | ~0.3-0.5 img/s | ~16-24 GB |
| T4 GPU | Not recommended | - | - |
| CPU | Not practical | - | - |

---

## 6. Limitations & Known Issues

### Limitations

- **High Latency**: 7B parameter model requires significant inference time
- **GPU Memory**: Requires A100 or similar high-memory GPU
- **Resolution Trade-off**: Higher resolution improves quality but increases compute
- **Text Output Parsing**: Quality scores extracted via regex from natural language

### Known Failure Modes

- May struggle with extremely degraded documents
- Performance varies by document type (born-digital vs scanned)
- Output parsing may fail on unexpected model responses

### Bias & Fairness Considerations

- Training data composition unknown (DIQA-5000 specific)
- May not generalize to non-document images
- Language bias from LLaMA-2 base model

---

## 7. Model Variants (m0, m1, m3)

| Variant | Training | Resolution | Pretrain | Final Score |
|---------|----------|------------|----------|-------------|
| **m0** | Full tuning | 1024×1024 | None | 0.8989 |
| **m1** | LoRA | 1024×1024 | None | 0.9033 |
| **m3** | LoRA | 1024×1024 | KonIQ-10k | N/R (ensemble component) |

### Ensemble Performance

The final DeQA-Doc ensemble (m0 + m1 + m3 + Q0 + Q1) achieves:

- **Final Score**: 0.9288 (Championship winning)
- **Overall**: Strong performance
- **Sharpness**: 0.9275
- **Color**: 0.9198

---

## 8. Files & Artifacts

| File | Description | Location |
|------|-------------|----------|
| Base weights | mPLUG-Owl2-7B initial | HuggingFace |
| Fine-tuned checkpoint | DIQA-specific | ModelScope (DIQA_model) |
| LoRA adapters | Parameter-efficient | DeQA-Doc GitHub |

### Storage Locations

| Environment | Path |
|-------------|------|
| **GitHub** | `https://github.com/Junjie-Gao19/DeQA-Doc` |
| **ModelScope** | DIQA_model (dimension-specific) |
| **HuggingFace** | `MAGAer13/mplug-owl2-llama2-7b` (base) |

---

## 9. Citation

```bibtex
@inproceedings{gao2025deqa,
  title={DeQA-Doc: Adapting DeQA-Score to Document Image Quality Assessment},
  author={Gao, Junjie and others},
  booktitle={ICCV Workshops (VQualA 2025)},
  year={2025}
}

@article{ye2023mplug,
  title={mPLUG-Owl2: Revolutionizing Multi-modal Large Language Model with Modality Collaboration},
  author={Ye, Qinghao and others},
  journal={arXiv preprint arXiv:2311.04257},
  year={2023}
}
```

---

## 10. Related Models

- [DeQA-Mix](deqa_mix.md) - Mixed-dimension training variant
- [DIQA_model](diqa_model_dimension_specific.md) - Dimension-specific specialists
- [Qwen2.5-VL-7B](deqa_qwen25_vl_7b.md) - Alternative VLM architecture

---

## Production Readiness: External VLM (High accuracy, requires A100 GPU, VQualA 2025 Champion)
