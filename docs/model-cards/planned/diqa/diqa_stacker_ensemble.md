---
owner: docs-team
purpose: 'Documentation for Model Card: DIQA Stacker Ensemble.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: DIQA Stacker Ensemble'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_stacker_ensemble_v1.0.0` |
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
| **Architecture** | Gradient Boosting Meta-Learner |
| **Parameters** | ~10K (lightweight) |
| **Precision** | FP32 |
| **Input Size** | Feature vector from ensemble |
| **Output Format** | 5-dimension final pseudo-labels [0,1] |
| **Export Formats** | Pickle, ONNX, joblib |
| **ONNX Opset** | 12 (simple ops) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Ensemble fusion for pseudo-labeling |
| **Role in Pipeline** | Final aggregation layer in DIQA ensemble |
| **Upstream Dependencies** | All Track A + Track B models |
| **Downstream Consumers** | DIQA-5000 pseudo-label generation |

### Intended Use

- **Primary**: Fuse predictions from 5 ensemble models into final pseudo-labels
- **Secondary**: Learn optimal weighting across models and dimensions
- **Out of Scope**: Direct image processing (works on model predictions only)

### Stacking Architecture

```text
Input Features (per image):
─────────────────────────────
Track A:
  - ResNet-50 Generalist: [sharpness, contrast, brightness, color, overall]
  - MUSIQ Sharpness: [sharpness]
  - QualiCLIP Color: [color]

Track B:
  - Qwen2.5-VL: [sharpness, contrast, brightness, color, overall]
  - InternVL3: [overall]

Total: 13 input features
─────────────────────────────
        ↓
[Gradient Boosting Stacker]
        ↓
Final Output: [sharpness, contrast, brightness, color, overall]
```

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Algorithm** | XGBoost / LightGBM |
| **Training Data** | Human-labeled subset of DIQA-5000 (~500 images) |
| **Validation** | 5-fold cross-validation |
| **Features** | 13 model predictions + confidence scores |
| **Targets** | 5 quality dimensions |
| **Hyperparameters** | Grid search optimization |
| **Training Time** | < 5 minutes (CPU) |
| **Training Script** | `scripts/train_diqa_stacker.py` (to be created) |

### Feature Engineering

| Feature Type | Count | Description |
|--------------|-------|-------------|
| Raw predictions | 13 | Direct model outputs |
| Confidence scores | 5 | Per-model uncertainty |
| Agreement metrics | 5 | Cross-model correlation |
| **Total** | 23 | Input feature dimension |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (Overall) | > 0.90 | Ensemble target |
| PLCC (Overall) | > 0.92 | Ensemble target |
| Improvement over best single | > 3% | Ensemble benefit |
| Latency | < 1ms | Lightweight model |

### 4.2 Per-Dimension Targets

| Dimension | SRCC Target | Best Single Model |
|-----------|-------------|-------------------|
| Sharpness | > 0.90 | MUSIQ (0.88) |
| Contrast | > 0.86 | ResNet-50 (0.82) |
| Brightness | > 0.88 | ResNet-50 (0.84) |
| Color | > 0.85 | QualiCLIP (0.82) |
| Overall | > 0.90 | InternVL3 (0.84) |

---

## 5. Ensemble Design

### Stacking Strategy

| Strategy | Description |
|----------|-------------|
| **Level 0** | Base model predictions (5 models) |
| **Level 1** | Gradient boosting meta-learner |
| **Output** | Final pseudo-labels with calibrated uncertainty |

### Expected Model Weights (Estimated)

| Model | Est. Weight | Rationale |
|-------|-------------|-----------|
| ResNet-50 Generalist | 0.25 | Strong baseline across dimensions |
| MUSIQ Sharpness | 0.20 | Best for sharpness |
| QualiCLIP Color | 0.10 | Specialist for color |
| Qwen2.5-VL | 0.25 | Diverse VLM signal |
| InternVL3 | 0.20 | Strong overall assessment |

---

## 6. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Dependent on quality of base model predictions
- Requires all 5 base models to run (latency accumulates)
- Human-labeled training subset may have annotation noise

### Mitigation Strategies

- Use high-quality human labels for stacker training
- Implement model caching for base predictions
- Cross-validation to detect overfitting

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Algorithm** | XGBoost 2.0+ or LightGBM 4.0+ |
| **Base Models** | 5 DIQA ensemble models |
| **Required Libraries** | xgboost/lightgbm, scikit-learn, numpy |

### Model Dependencies

| Dependency | Model ID |
|------------|----------|
| Track A Anchor | `diqa_resnet50_generalist_v1.0.0` |
| Track A Specialist | `diqa_musiq_sharpness_v1.0.0` |
| Track A Specialist | `diqa_qualiclip_color_v1.0.0` |
| Track B Anchor | `diqa_qwen3vl_generalist_v1.0.0` |
| Track B Specialist | `diqa_internvl3_overall_v1.0.0` |

---

## 8. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `stacker.pkl` | Trained model (pickle) | <1MB |
| `stacker.onnx` | ONNX export | <500KB |
| `feature_config.json` | Feature definitions | <1KB |
| `calibration.json` | Output calibration params | <1KB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/diqa/stacker_ensemble_v1.0.0/` |
| Local | `models/diqa/stacker_ensemble_v1.0.0/` |

---

## 9. Implementation Checklist

- [ ] Implement base model inference pipeline
- [ ] Collect human annotations (~500 images)
- [ ] Design feature engineering pipeline
- [ ] Train and validate stacker
- [ ] Calibrate output uncertainty
- [ ] Export to ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 10. References

- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [DIQA-5000 Specification](../../../planning/DIQA-5000_Pseudo_Labels_v2.md)
- [Stacking Ensembles Paper](https://arxiv.org/abs/1704.00109)

---

## 11. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - awaiting base model implementation |
