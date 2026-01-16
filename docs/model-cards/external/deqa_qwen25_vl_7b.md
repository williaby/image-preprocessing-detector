---
owner: docs-team
purpose: 'Documentation for Model Card: DeQA-Doc Qwen2.5-VL-7B.'
schema_type: common
status: draft
tags:
- iqa
- vlm
- deqa_doc
- vquala_2025
- qwen
title: 'Model Card: DeQA-Doc Qwen2.5-VL-7B'
---

## Model Summary

> Qwen2.5-VL-7B is an alternative vision-language model used in the DeQA-Doc framework, offering native dynamic resolution support without requiring position embedding modifications. Part of the **VQualA 2025 DIQA Challenge Championship** ensemble, integrated via LLaMA-Factory framework.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `DeQA-Qwen2.5-VL-7B` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External VLM (DIQA Track A/B Candidate) |
| **Status** | `pretrained` (VQualA 2025 Champion Ensemble) |
| **Priority** | P1 (High - dynamic resolution VLM) |
| **Last Updated** | 2025-01-12 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | Qwen2.5-VL (ViT + Cross-Attention + Qwen2.5-7B LLM) |
| **Parameters** | ~7B |
| **Precision** | BF16 / FP16 |
| **Input Size** | **Dynamic** (original resolution preserved) |
| **Output Format** | Text-based quality scores (overall/sharpness/color) |
| **Output Type** | Regression (soft label distribution) |
| **Source** | [LLaMA-Factory Configuration](https://github.com/Junjie-Gao19/DeQA-Doc) |
| **License** | Apache 2.0 (Qwen2.5 base) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Document Image Quality Assessment with Native Resolution |
| **Role in Pipeline** | Alternative VLM for dynamic resolution documents |
| **Upstream Dependencies** | None (external pretrained) |
| **Downstream Consumers** | Ensemble fusion, pseudo-label generation |

### Key Advantage: Dynamic Resolution

Unlike mPLUG-Owl2 which requires position embedding removal for variable resolutions, Qwen2.5-VL **natively supports dynamic input resolutions**:

| Aspect | mPLUG-Owl2 | Qwen2.5-VL |
|--------|-----------|------------|
| Resolution Handling | Requires modification | Native support |
| Max Resolution | ~1536×1536 (modified) | Original document resolution |
| Architecture Change | Position embedding removal | None needed |
| Quality Impact | May lose positional information | Preserves spatial relationships |

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Base Model** | Qwen2.5-VL-7B-Instruct |
| **Training Framework** | LLaMA-Factory |
| **Config File** | `qwen2.5_vl_diqa_sft.yaml` |
| **Training Method** | Supervised Fine-Tuning (SFT) |
| **Epochs** | 3 |
| **Learning Rate** | 2e-5 |
| **Optimizer** | AdamW |
| **Hardware** | 8× NVIDIA A100 GPUs |

### LLaMA-Factory Integration

Training requires file exchanges within the LLaMA-Factory codebase:

```bash
# LLaMA-Factory training command
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 llamafactory-cli train \
    examples/qwen2.5_vl_diqa_sft.yaml
```

### Training Configuration (qwen2.5_vl_diqa_sft.yaml)

```yaml
# Key configuration parameters
model_name_or_path: Qwen/Qwen2.5-VL-7B-Instruct
stage: sft
do_train: true
finetuning_type: full  # or lora
dataset: diqa_5000
template: qwen2_vl
output_dir: saves/qwen2.5_vl_diqa
per_device_train_batch_size: 2
gradient_accumulation_steps: 8
learning_rate: 2.0e-5
num_train_epochs: 3.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true
```

---

## 4. Model Variants (Q0, Q1)

| Variant | Training | Resolution | Ensemble Role |
|---------|----------|------------|---------------|
| **Q0** | Full tuning | Original | Primary Qwen model |
| **Q1** | Full tuning (5-fold) | Original | 5-fold cross-validation ensemble |

### Ensemble Contribution

In the championship-winning ensemble (m0 + m1 + m3 + Q0 + Q1):

- **Q0**: Single Qwen2.5-VL model with full fine-tuning
- **Q1**: 5-fold ensemble of Qwen2.5-VL models for robustness
- **Combined**: Significant contribution to Final Score 0.9288

---

## 5. Performance Metrics

### VQualA 2025 Challenge Results (Ensemble Contribution)

| Configuration | Final Score | Notes |
|--------------|-------------|-------|
| Full ensemble (m0+m1+m3+Q0+Q1) | **0.9288** | Championship winning |
| Q0 + Q1 contribution | Significant | Dynamic resolution strength |

### Dimension Performance (Ensemble)

| Dimension | SRCC | Notes |
|-----------|------|-------|
| Overall | ~0.91+ | Ensemble performance |
| Sharpness | 0.9275 | Strong sharpness assessment |
| Color | 0.9198 | Strong color fidelity |

### Inference Performance

| Device | Latency | Memory |
|--------|---------|--------|
| A100 GPU | ~1500-2500 ms | ~16-20 GB |
| T4 GPU | Not recommended | - |

---

## 6. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | **Dynamic** (original document resolution) |
| **Color Space** | RGB |
| **Value Range** | Model-handled internally |
| **Max Resolution** | Limited by GPU memory |

### Dynamic Resolution Advantage

```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from PIL import Image

# Load model
model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2.5-VL-7B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

# Load document at ORIGINAL resolution (no resize needed!)
image = Image.open("document.png").convert("RGB")
# image.size could be (2480, 3508) - A4 at 300 DPI

# Process with dynamic resolution
inputs = processor(
    images=image,
    text=IQA_PROMPT,
    return_tensors="pt"
).to(model.device)

# Inference preserves original resolution information
with torch.inference_mode():
    outputs = model.generate(**inputs, max_new_tokens=64)
```

---

## 7. Architecture Comparison

### Qwen2.5-VL vs mPLUG-Owl2

| Component | mPLUG-Owl2 | Qwen2.5-VL |
|-----------|-----------|------------|
| Vision Encoder | CLIP ViT-L (fixed 448×448) | Dynamic ViT |
| Resolution Handling | Position embedding removal | Native dynamic |
| Visual Abstractor | Q-Former (6 layers) | Cross-attention |
| Language Model | LLaMA-2-7B | Qwen2.5-7B |
| Context Length | ~4K tokens | 32K+ tokens |

### Why Use Qwen2.5-VL?

1. **Native Dynamic Resolution**: No architecture modifications needed
2. **Longer Context**: Better for complex document analysis
3. **Newer Architecture**: Qwen2.5 improvements over LLaMA-2
4. **Better Instruction Following**: Improved SFT capabilities

---

## 8. Limitations & Known Issues

### Limitations

- **GPU Memory**: Requires A100-class GPU for full resolution
- **Inference Speed**: ~1.5-2.5s per image
- **Training Complexity**: Requires LLaMA-Factory setup

### Known Benefits

- **Resolution Preservation**: Better for high-resolution documents
- **Spatial Understanding**: Maintains positional relationships
- **Flexibility**: Handles variable document sizes naturally

---

## 9. Files & Artifacts

| File | Description | Location |
|------|-------------|----------|
| Base model | Qwen2.5-VL-7B-Instruct | HuggingFace |
| Fine-tuned weights | DIQA-specific | LLaMA-Factory output |
| Config | Training configuration | GitHub (DeQA-Doc) |

### Storage Locations

| Environment | Path |
|-------------|------|
| **HuggingFace** | `Qwen/Qwen2.5-VL-7B-Instruct` (base) |
| **GitHub** | `https://github.com/Junjie-Gao19/DeQA-Doc` |
| **LLaMA-Factory** | Required for training |

---

## 10. Citation

```bibtex
@inproceedings{gao2025deqa,
  title={DeQA-Doc: Adapting DeQA-Score to Document Image Quality Assessment},
  author={Gao, Junjie and others},
  booktitle={ICCV Workshops (VQualA 2025)},
  year={2025}
}

@article{qwen2vl,
  title={Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution},
  author={Qwen Team},
  year={2024}
}
```

---

## 11. Related Models

- [mPLUG-Owl2-7B](deqa_mplug_owl2_7b.md) - Alternative VLM (fixed resolution)
- [DIQA_model](diqa_model_dimension_specific.md) - Dimension specialists
- [DeQA-Mix](deqa_mix.md) - Mixed-dimension variant

---

## Production Readiness: External VLM (Dynamic resolution, native variable input, VQualA 2025 Champion ensemble component)
