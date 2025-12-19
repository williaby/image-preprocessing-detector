# Model Card: DIQA MUSIQ Sharpness

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_musiq_sharpness_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | DIQA (Pseudo-Labeling Ensemble) |
| **Status** | `trained` |
| **Priority** | P1 (High) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | MUSIQ (Multi-Scale Image Quality Transformer) + MultiTaskHead |
| **Parameters** | ~27.3M (backbone frozen, ~200K trainable) |
| **Precision** | FP32 (training), FP16 (inference) |
| **Input Size** | 512x512 (resized) |
| **Output Format** | 3 quality scores [0,1]: overall, sharpness, color |
| **Export Formats** | PyTorch (.pt) |
| **Training Script** | `modal/train_musiq_finetuning.py` |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Sharpness-specialized IQA for document images |
| **Role in Pipeline** | Track A specialist in DIQA ensemble |
| **Upstream Dependencies** | DIQA-5000 dataset |
| **Downstream Consumers** | DIQA Stacker Ensemble |

### Intended Use

- **Primary**: Sharpness dimension specialist for DIQA pseudo-labeling
- **Secondary**: Multi-task quality assessment (overall, color)
- **Specialist Focus**: 60% weight on sharpness during training

### MUSIQ Advantages

| Feature | Benefit |
|---------|---------|
| Multi-scale processing | Captures quality at different frequencies |
| ViT backbone | Strong feature extraction for quality perception |
| Pretrained on KonIQ-10k | Transfer learning from IQA datasets |

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Base Weights** | PyIQA MUSIQ (KonIQ-10k pretrained) |
| **Fine-tune Dataset** | DIQA-5000 (1000 test samples benchmarked) |
| **Training Approach** | Score-as-feature with MultiTaskHead |
| **Phase 1 Epochs** | 10 (backbone frozen) |
| **Phase 2 Epochs** | 20 (full fine-tune, not completed) |
| **Best Epoch** | 5 (Phase 1) |
| **Batch Size** | 8 |
| **Learning Rate** | 1e-3 (Phase 1 head warmup) |
| **Optimizer** | AdamW (weight_decay=0.0001) |
| **Loss Function** | MSE (0.6) + Rank (0.2) + Focal (0.2) |
| **Loss Weights** | overall=0.2, sharpness=0.6, color=0.2 |
| **GPU** | Modal A10G (24GB) |
| **Training Time** | ~30 minutes (Phase 1 only) |

### Architecture Details

```
Input Image → PyIQA MUSIQ (frozen) → MOS Score (0-100)
                                         ↓
                               score_encoder MLP
                                (1 → 64 → 256 → 384)
                                         ↓
                               MultiTaskHead
                              (384 → 256 → 3 outputs)
                                         ↓
                        {overall, sharpness, color} [0,1]
```

---

## 4. Performance Metrics

### 4.1 DIQA-5000 Test Set Benchmark (1000 samples)

| Metric | Overall | Sharpness | Color |
|--------|---------|-----------|-------|
| **PLCC** | 0.2531 [0.1775, 0.3171] | 0.3775 [0.3084, 0.4389] | 0.2393 [0.1625, 0.3056] |
| **SRCC** | 0.1158 [0.0472, 0.1797] | 0.2126 [0.1488, 0.2785] | 0.1118 [0.0457, 0.1758] |
| **MAE** | 0.4158 | 0.4121 | 0.4053 |
| **RMSE** | 0.5586 | 0.5708 | 0.5382 |

### 4.2 Inference Performance

| Metric | Value |
|--------|-------|
| **Mean Latency** | 273ms (T4 GPU) |
| **Model Load** | 15.3s |
| **Success Rate** | 100% (1000/1000) |

### 4.3 Comparison with Baselines

| Model | SRCC Sharpness | PLCC Sharpness | Type |
|-------|----------------|----------------|------|
| **MUSIQ Sharpness Specialist** | 0.2126 | 0.3775 | Fine-tuned |
| PyIQA MUSIQ (pretrained) | 0.2126 | 0.3074 | Pretrained |
| HyperIQA | 0.3034 | 0.3782 | Pretrained |
| TOPIQ-NR | 0.2274 | 0.3013 | Pretrained |
| CLIP-IQA | 0.2409 | 0.3159 | Pretrained |

### 4.4 Training Validation Metrics (Best Checkpoint)

| Metric | Value |
|--------|-------|
| **SRCC Overall** | 0.2641 |
| **SRCC Sharpness** | 0.3516 |
| **SRCC Color** | 0.2110 |
| **ECE Mean** | 0.0098 |
| **Train Loss** | 0.0295 |

---

## 5. Ensemble Role

### Track A Position

```text
Track A (IQA Models)
─────────────────────
    ResNet-50 Generalist (anchor)
        ↓
[MUSIQ Sharpness] ← This model (specialist)
        ↓
    QualiCLIP Color (specialist)
        ↓
    → Feed to Stacker
```

### Specialist Contribution

- **Sharpness Weight**: 60% in training loss
- **Multi-task Output**: Provides all 3 dimensions for ensemble
- **Calibration**: ECE < 0.01 indicates well-calibrated predictions

---

## 6. Limitations & Known Issues

### Current Limitations

- **Phase 1 Only**: Full fine-tuning (Phase 2) not completed
- **Modest SRCC**: 0.2126 on sharpness vs 0.3516 validation suggests overfit
- **High Latency**: 273ms per image due to MUSIQ backbone
- **Score-as-Feature**: Uses MUSIQ output score, not intermediate features

### Performance Gap Analysis

| Issue | Description | Impact |
|-------|-------------|--------|
| Val/Test Gap | SRCC drops from 0.35 (val) to 0.21 (test) | Generalization concern |
| vs HyperIQA | 0.2126 vs 0.3034 on sharpness | Not best-in-class |
| vs Pretrained | Similar to pretrained MUSIQ | Limited fine-tuning benefit |

### Recommendations

1. **Phase 2 Training**: Complete full fine-tuning with differential LRs
2. **Feature Extraction**: Consider using intermediate MUSIQ features
3. **Data Augmentation**: Apply document-specific augmentations
4. **Ensemble Strategy**: Combine with higher-performing HyperIQA

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | PyIQA MUSIQ (KonIQ-10k pretrained) |
| **Original Paper** | "MUSIQ: Multi-scale Image Quality Transformer" (ICCV 2021) |
| **Required Libraries** | PyTorch 2.0+, PyIQA 0.1.12+, structlog |

---

## 8. Files & Artifacts

| File | Description | Size |
|------|-------------|------|
| `model.pt` | PyTorch checkpoint (Phase 1, Epoch 5) | ~104MB |
| `config.json` | Training configuration | <1KB |
| `metrics.json` | Validation metrics | <1KB |

### Storage Locations

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/track_a_iqa/musiq/v1.0.0/` |
| Local | `models/diqa/track_a_iqa/musiq/v1.0.0/` |

---

## 9. Implementation Checklist

- [x] Obtain MUSIQ pretrained weights (PyIQA)
- [x] Create fine-tuning script (`modal/train_musiq_finetuning.py`)
- [x] Prepare DIQA-5000 labels
- [x] Fine-tune model (Phase 1 complete)
- [x] Validate on held-out test set
- [x] Benchmark on DIQA-5000 test
- [x] Upload to GCS
- [x] Update registry
- [x] Complete model card
- [ ] Phase 2 full fine-tuning
- [ ] ONNX export
- [ ] Integration into production pipeline

---

## 10. References

- [MUSIQ Paper](https://arxiv.org/abs/2108.05997)
- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [MUSIQ Fine-tuning Plan](../../../planning/MUSIQ_FINETUNING_PLAN.md)
- [KonIQ-10k Dataset](http://database.mmsp-kn.de/koniq-10k-database.html)
- [Benchmark Results](../../../benchmarks/diqa5000_benchmark_results.csv)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Trained (Phase 1) - Ready for ensemble evaluation |
