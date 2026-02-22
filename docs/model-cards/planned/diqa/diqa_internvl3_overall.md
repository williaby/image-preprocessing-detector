---
owner: docs-team
purpose: 'Documentation for Model Card: DIQA InternVL3 Overall.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: DIQA InternVL3 Overall'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_internvl3_overall_v1.0.0` |
| **Project** | Prepare-Doc |
| **Phase** | DIQA (Pseudo-Labeling Ensemble) |
| **Status** | `planned` |
| **Priority** | P2 (Medium) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | InternVL3-1B (Vision-Language Model) |
| **Parameters** | ~1B |
| **Precision** | FP16 / INT4 (quantized) |
| **Input Size** | Variable (native resolution) |
| **Output Format** | Single overall quality score via structured prompting |
| **Export Formats** | PyTorch, vLLM-compatible |
| **ONNX Opset** | N/A (LLM inference) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Overall quality specialist (VLM) |
| **Role in Pipeline** | Track B specialist in DIQA ensemble |
| **Upstream Dependencies** | DIQA-5000 dataset |
| **Downstream Consumers** | DIQA Stacker Ensemble |

### Intended Use

- **Primary**: Overall quality dimension specialist for Track B
- **Secondary**: Holistic document quality assessment with natural language reasoning
- **Out of Scope**: Real-time production inference, dimension-specific assessment

### InternVL3 Advantages

| Feature | Benefit |
|---------|---------|
| Smaller than Qwen (1B vs 3B) | Faster inference |
| Strong document understanding | Good at overall assessment |
| Open-source | Full access to weights |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Base Weights** | InternVL3-1B (OpenGVLab) |
| **Fine-tune Method** | LoRA |
| **Fine-tune Dataset** | DIQA-5000 (overall dimension) |
| **Train/Val/Test Split** | 70/15/15 |
| **Epochs** | 15 |
| **Batch Size** | 16 |
| **Learning Rate** | 2e-5 |
| **Optimizer** | AdamW |
| **GPU** | Modal A10 (24GB) |
| **Training Time** | ~6 hours (estimated) |
| **Training Script** | `modal/train_diqa_internvl.py` (to be created) |

### Prompt Template

```text
Analyze this document image and provide an overall quality score from 0 to 100, where:
- 0-20: Very poor quality, nearly unusable
- 21-40: Poor quality, significant issues
- 41-60: Acceptable quality, some issues
- 61-80: Good quality, minor issues
- 81-100: Excellent quality, no significant issues

Consider: sharpness, contrast, brightness, color accuracy, and overall readability.

Respond with only the numeric score.
```

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (Overall) | > 0.84 | Specialist target |
| PLCC (Overall) | > 0.86 | Specialist target |
| Response Validity | > 99.5% | Valid numeric parsing |
| Latency (GPU) | < 800ms | A10 GPU |

### 4.2 Cross-Validation

| Validation Set | SRCC Target |
|----------------|-------------|
| DIQA-5000 Test | > 0.84 |
| KonIQ-10k | > 0.80 |
| SPAQ | > 0.78 |

---

## 5. Ensemble Role

### Track B Position

```text
Track B (VLM Models)
─────────────────────
    Qwen2.5-VL-3B (anchor)
        ↓
[InternVL3-1B] ← This model (specialist)
        ↓
    → Feed to Stacker
```

### Stacking Weight (Estimated)

- **Expected Weight**: 0.15-0.20 (overall specialist)
- **Rationale**: Focused on overall dimension, complements Qwen generalist

---

## 6. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Single-dimension output (overall only)
- Still slow compared to CNN models (~800ms)
- Less accurate than larger VLMs on nuanced quality aspects

### Mitigation Strategies

- Use only for overall dimension in ensemble
- Batch processing for efficiency
- Combine with Qwen for robust VLM signal

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | InternVL3-1B (OpenGVLab) |
| **Model Hub** | Hugging Face |
| **Required Libraries** | transformers, einops |

---

## 8. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `adapter_model.safetensors` | LoRA weights | ~30MB |
| `config.json` | Model configuration | <1KB |
| `prompt_template.txt` | Structured prompt | <1KB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/internvl3_overall_v1.0.0/` |
| Local | `models/diqa/internvl3_overall_v1.0.0/` |
| Base Model | Hugging Face Hub |

---

## 9. Implementation Checklist

- [ ] Set up InternVL3 inference pipeline
- [ ] Design overall quality prompt
- [ ] Create LoRA fine-tuning script
- [ ] Fine-tune on DIQA-5000
- [ ] Validate response parsing
- [ ] Benchmark latency
- [ ] Update registry
- [ ] Complete model card

---

## 10. References

- [InternVL Paper](https://arxiv.org/abs/2312.14238)
- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [OpenGVLab GitHub](https://github.com/OpenGVLab/InternVL)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Prepare-Doc Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - awaiting implementation |
