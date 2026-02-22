---
owner: docs-team
purpose: 'Documentation for Model Card: DIQA Qwen2.5-VL Generalist.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: DIQA Qwen2.5-VL Generalist'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_qwen3vl_generalist_v1.0.0` |
| **Project** | Prepare-Doc |
| **Phase** | DIQA (Pseudo-Labeling Ensemble) |
| **Status** | `planned` |
| **Priority** | P1 (High) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | Qwen2.5-VL-3B (Vision-Language Model) |
| **Parameters** | ~3B |
| **Precision** | FP16 / INT4 (quantized) |
| **Input Size** | Variable (native resolution) |
| **Output Format** | 5-dimension quality scores via structured prompting |
| **Export Formats** | PyTorch, vLLM-compatible |
| **ONNX Opset** | N/A (LLM inference) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Generalist VLM IQA |
| **Role in Pipeline** | Track B anchor model in DIQA ensemble |
| **Upstream Dependencies** | DIQA-5000 dataset |
| **Downstream Consumers** | DIQA Stacker Ensemble |

### Intended Use

- **Primary**: Anchor model for Track B (VLM) in DIQA pseudo-labeling ensemble
- **Secondary**: Natural language quality descriptions
- **Out of Scope**: Real-time production inference (too slow)

### VLM Advantages

| Feature | Benefit |
|---------|---------|
| Multimodal understanding | Rich semantic quality assessment |
| Natural language output | Explainable quality scores |
| Zero-shot capability | Adapts to new quality dimensions |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Base Weights** | Qwen2.5-VL-3B (Hugging Face) |
| **Fine-tune Method** | LoRA / Prompt tuning |
| **Fine-tune Dataset** | DIQA-5000 (all dimensions) |
| **Train/Val/Test Split** | 70/15/15 |
| **Epochs** | 10 |
| **Batch Size** | 8 (gradient accumulation) |
| **Learning Rate** | 1e-5 |
| **Optimizer** | AdamW (8-bit) |
| **GPU** | Modal A100 (40GB) |
| **Training Time** | ~12 hours (estimated) |
| **Training Script** | `modal/train_diqa_qwen.py` (to be created) |

### Prompt Template

```text
You are a document image quality expert. Analyze this document image and rate the following quality dimensions on a scale of 0-100:

1. Sharpness: Focus quality and clarity
2. Contrast: Dynamic range and visibility
3. Brightness: Illumination quality
4. Color: Color accuracy and saturation
5. Overall: Holistic document quality

Respond in JSON format:
{"sharpness": <score>, "contrast": <score>, "brightness": <score>, "color": <score>, "overall": <score>}
```

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (Overall) | > 0.82 | VLM generalist |
| PLCC (Overall) | > 0.84 | VLM generalist |
| Response Validity | > 99% | Valid JSON parsing |
| Latency (GPU) | < 2000ms | A100 GPU |

### 4.2 Per-Dimension Targets

| Dimension | SRCC Target | PLCC Target |
|-----------|-------------|-------------|
| Sharpness | > 0.80 | > 0.82 |
| Contrast | > 0.78 | > 0.80 |
| Brightness | > 0.80 | > 0.82 |
| Color | > 0.76 | > 0.78 |
| Overall | > 0.82 | > 0.84 |

---

## 5. Ensemble Role

### Track B Position

```text
Track B (VLM Models)
─────────────────────
[Qwen2.5-VL-3B] ← This model (anchor)
        ↓
    InternVL3-1B (overall specialist)
        ↓
    → Feed to Stacker
```

### Stacking Weight (Estimated)

- **Expected Weight**: 0.20-0.30 (Track B anchor)
- **Rationale**: VLM provides diverse signal from IQA models

---

## 6. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Very slow inference (~2 seconds per image)
- High memory requirements (40GB+ GPU)
- Requires structured prompting for consistent outputs

### Mitigation Strategies

- Use only for offline pseudo-labeling, not production
- Batch processing with vLLM for efficiency
- Robust JSON parsing with fallbacks

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | Qwen2.5-VL-3B (Alibaba) |
| **Model Hub** | Hugging Face |
| **Required Libraries** | transformers, vLLM, bitsandbytes |

---

## 8. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `adapter_model.safetensors` | LoRA weights | ~50MB |
| `config.json` | Model configuration | <1KB |
| `prompt_template.txt` | Structured prompt | <1KB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/qwen3vl_generalist_v1.0.0/` |
| Local | `models/diqa/qwen3vl_generalist_v1.0.0/` |
| Base Model | Hugging Face Hub |

---

## 9. Implementation Checklist

- [ ] Set up Qwen2.5-VL inference pipeline
- [ ] Design structured prompting strategy
- [ ] Create LoRA fine-tuning script
- [ ] Fine-tune on DIQA-5000
- [ ] Validate response parsing
- [ ] Benchmark latency
- [ ] Update registry
- [ ] Complete model card

---

## 10. References

- [Qwen2.5-VL Paper](https://arxiv.org/abs/2409.12191)
- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [vLLM Documentation](https://docs.vllm.ai/)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Prepare-Doc Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - awaiting implementation |
