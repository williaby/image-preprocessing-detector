---
owner: docs-team
purpose: 'Documentation for Model Card: DIQA QualiCLIP Color.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: DIQA QualiCLIP Color'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_qualiclip_color_v1.0.0` |
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
| **Architecture** | QualiCLIP (CLIP-based IQA) |
| **Parameters** | ~150M (CLIP backbone) |
| **Precision** | FP32 (training), FP16 (inference) |
| **Input Size** | 224x224x3 (CLIP standard) |
| **Output Format** | Single color quality score [0,1] |
| **Export Formats** | PyTorch, ONNX |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Color quality specialist |
| **Role in Pipeline** | Track A specialist in DIQA ensemble |
| **Upstream Dependencies** | DIQA-5000 dataset |
| **Downstream Consumers** | DIQA Stacker Ensemble |

### Intended Use

- **Primary**: Color dimension specialist for DIQA pseudo-labeling
- **Secondary**: Color accuracy, saturation, white balance assessment
- **Out of Scope**: Other quality dimensions (sharpness, overall)

### QualiCLIP Advantages

| Feature | Benefit |
|---------|---------|
| CLIP backbone | Rich semantic understanding |
| Zero-shot capability | Can generalize to unseen quality prompts |
| Vision-language alignment | Color description in natural language |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Base Weights** | QualiCLIP pretrained |
| **Fine-tune Dataset** | DIQA-5000 (color dimension) |
| **Train/Val/Test Split** | 70/15/15 |
| **Epochs** | 30 |
| **Batch Size** | 32 |
| **Learning Rate** | 1e-5 with warmup |
| **Optimizer** | AdamW |
| **Loss Function** | MSE + Contrastive |
| **GPU** | Modal A10 (24GB) |
| **Training Time** | ~3 hours (estimated) |
| **Training Script** | `modal/train_diqa_qualiclip.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (Color) | > 0.82 | Specialist target |
| PLCC (Color) | > 0.84 | Specialist target |
| ECE | < 0.08 | Calibration error |
| Latency (GPU) | < 35ms | CLIP inference |

### 4.2 Color Quality Aspects

| Aspect | Description | Target SRCC |
|--------|-------------|-------------|
| Saturation | Color vividness | > 0.80 |
| White Balance | Color temperature | > 0.78 |
| Color Accuracy | True-to-original | > 0.82 |

---

## 5. Ensemble Role

### Track A Position

```text
Track A (IQA Models)
─────────────────────
    ResNet-50 Generalist (anchor)
        ↓
    MUSIQ Sharpness (specialist)
        ↓
[QualiCLIP Color] ← This model (specialist)
        ↓
    → Feed to Stacker
```

### Stacking Weight (Estimated)

- **Expected Weight**: 0.15-0.25 (color dimension)
- **Rationale**: Specialist for color, lower weight than sharpness

---

## 6. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Single-dimension output (color only)
- CLIP backbone is large (150M parameters)
- Less effective on grayscale documents

### Mitigation Strategies

- Use only for color dimension in ensemble
- Skip for documents detected as grayscale
- Consider distillation for production if needed

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | QualiCLIP (CLIP ViT-B/16) |
| **Original Paper** | "QualiCLIP: Contrastive Learning for CLIP-based Image Quality Assessment" |
| **Required Libraries** | PyTorch 2.0+, transformers, open_clip |

---

## 8. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `model.pt` | PyTorch checkpoint | ~600MB |
| `model.onnx` | ONNX export | ~580MB |
| `config.json` | Model configuration | <1KB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/qualiclip_color_v1.0.0/` |
| Local | `models/diqa/qualiclip_color_v1.0.0/` |

---

## 9. Implementation Checklist

- [ ] Obtain QualiCLIP pretrained weights
- [ ] Create fine-tuning script
- [ ] Prepare DIQA-5000 color labels
- [ ] Fine-tune model
- [ ] Validate specialist performance
- [ ] Export ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 10. References

- [QualiCLIP Paper](https://arxiv.org/abs/2311.13090)
- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [CLIP Paper](https://arxiv.org/abs/2103.00020)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Prepare-Doc Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - awaiting implementation |
