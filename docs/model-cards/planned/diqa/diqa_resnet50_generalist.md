# Model Card: DIQA ResNet-50 Generalist

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_resnet50_generalist_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | DIQA (Pseudo-Labeling Ensemble) |
| **Status** | `planned` |
| **Priority** | P1 (High) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-50 + MultiTaskHead |
| **Parameters** | ~25.6M |
| **Precision** | FP32 (training), FP16 (inference) |
| **Input Size** | 384x384x3 |
| **Output Format** | 5-dimension quality scores [0,1] |
| **Export Formats** | PyTorch, ONNX |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Generalist IQA for DIQA pseudo-labeling |
| **Role in Pipeline** | Track A anchor model in DIQA ensemble |
| **Upstream Dependencies** | DIQA-5000 dataset |
| **Downstream Consumers** | DIQA Stacker Ensemble |

### Intended Use

- **Primary**: Anchor model for Track A (IQA) in DIQA pseudo-labeling ensemble
- **Secondary**: Baseline quality assessment across all dimensions
- **Out of Scope**: Production inference (use IQA Student instead)

### DIQA Quality Dimensions

| Dimension | Description |
|-----------|-------------|
| Sharpness | Focus quality, motion blur, resolution adequacy |
| Contrast | Dynamic range, visibility of details |
| Brightness | Illumination quality, under/over exposure |
| Color | Color accuracy, saturation, white balance |
| Overall | Holistic document quality score |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Dataset** | DIQA-5000 (5000 document images) |
| **Train/Val/Test Split** | 70/15/15 |
| **Epochs** | 100 |
| **Batch Size** | 64 |
| **Learning Rate** | 1e-4 with cosine annealing |
| **Optimizer** | AdamW |
| **Loss Function** | MSE + Rank + Correlation |
| **Augmentations** | Geometric, photometric, quality-aware |
| **GPU** | Modal A10 (24GB) |
| **Training Time** | ~6 hours (estimated) |
| **Training Script** | `modal/train_diqa_resnet.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (Overall) | > 0.85 | Spearman correlation |
| PLCC (Overall) | > 0.87 | Pearson correlation |
| ECE | < 0.08 | Calibration error |
| Latency (GPU) | < 30ms | T4/A10 GPU |

### 4.2 Per-Dimension Targets

| Dimension | SRCC Target | PLCC Target |
|-----------|-------------|-------------|
| Sharpness | > 0.83 | > 0.85 |
| Contrast | > 0.82 | > 0.84 |
| Brightness | > 0.84 | > 0.86 |
| Color | > 0.80 | > 0.82 |
| Overall | > 0.85 | > 0.87 |

---

## 5. Ensemble Role

### Track A Position

```text
Track A (IQA Models)
─────────────────────
[ResNet-50 Generalist] ← This model (anchor)
        ↓
    MUSIQ Sharpness (specialist)
        ↓
    QualiCLIP Color (specialist)
        ↓
    → Feed to Stacker
```

### Stacking Weight (Estimated)

- **Expected Weight**: 0.35-0.45 (highest in Track A)
- **Rationale**: Generalist provides balanced signal across all dimensions

---

## 6. Limitations & Known Issues (Anticipated)

### Expected Limitations

- May be outperformed by specialists on individual dimensions
- Larger than specialists, higher inference cost
- Requires GPU for reasonable latency

### Mitigation Strategies

- Combine with specialists via stacking ensemble
- Use only for pseudo-labeling, not production inference

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | ResNet-50 (ImageNet1K_V2) |
| **Related Models** | `iqa_resnet50_teacher_v1.0.0` (architecture reference) |
| **Required Libraries** | PyTorch 2.0+, timm |

---

## 8. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `model.pt` | PyTorch checkpoint | ~100MB |
| `model.onnx` | ONNX export | ~98MB |
| `config.json` | Model configuration | <1KB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/resnet50_generalist_v1.0.0/` |
| Local | `models/diqa/resnet50_generalist_v1.0.0/` |

---

## 9. Implementation Checklist

- [ ] Create training script
- [ ] Prepare DIQA-5000 dataset
- [ ] Define augmentation pipeline
- [ ] Train model
- [ ] Validate performance targets
- [ ] Export ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 10. References

- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [IQA Teacher Model Card](../../production/iqa_resnet50_teacher.md)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - awaiting implementation |
