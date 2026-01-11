---
owner: docs-team
purpose: 'Documentation for Model Card: Formula Classifier.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: Formula Classifier'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_formula_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase 9 (Element Classification) |
| **Status** | `planned` |
| **Priority** | P3 (Low) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-18 + Classification Head |
| **Parameters** | ~11.7M |
| **Precision** | FP32 (training), FP16 (inference) |
| **Input Size** | 224x224x3 (cropped formula region) |
| **Output Format** | 4-class softmax |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Formula type classification |
| **Role in Pipeline** | Post-detection classifier for formula elements |
| **Upstream Dependencies** | Layout-Lite (YOLOv10) formula detections |
| **Downstream Consumers** | Routing Engine, Project B (formula extraction) |

### Intended Use

- **Primary**: Classify detected formula regions by type
- **Secondary**: Route to appropriate formula recognition engines
- **Out of Scope**: Formula detection (use YOLOv10), formula recognition/LaTeX conversion

### Classification Categories

| Class | Description | Processing Strategy |
|-------|-------------|---------------------|
| `inline_math` | Inline mathematical expressions | MathML extraction |
| `display_math` | Display/block equations | LaTeX conversion |
| `chemical` | Chemical formulas and reactions | ChemDraw-style parsing |
| `none` | Non-formula content (false positive) | Skip formula processing |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Dataset** | Im2Latex + ChemDraw + scientific papers |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 25 |
| **Batch Size** | 64 |
| **Learning Rate** | 1e-3 with step decay |
| **Optimizer** | Adam |
| **Loss Function** | CrossEntropy |
| **Augmentations** | Scale, rotation, noise |
| **GPU** | Modal T4 (16GB) |
| **Training Time** | ~1.5 hours (estimated) |
| **Training Script** | `modal/train_phase9_classifiers.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| Accuracy | > 90% | 4-class classification |
| F1 (macro) | > 0.88 | Balanced across classes |
| Latency (GPU) | < 5ms | Per formula crop |
| Latency (CPU) | < 20ms | Per formula crop |

### 4.2 Per-Class Targets

| Class | Precision | Recall | Support (Est.) |
|-------|-----------|--------|----------------|
| inline_math | > 0.92 | > 0.90 | ~40% |
| display_math | > 0.94 | > 0.92 | ~35% |
| chemical | > 0.88 | > 0.85 | ~15% |
| none | > 0.85 | > 0.88 | ~10% |

---

## 5. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Chemical formula detection may be challenging
- Handwritten formulas not well supported
- Complex multi-line equations may be split incorrectly

### Mitigation Strategies

- Train on diverse formula styles
- Use confidence thresholds for uncertain cases
- Consider separate chemical formula classifier if needed

---

## 6. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | ResNet-18 (ImageNet1K_V2) |
| **Required Libraries** | PyTorch 2.0+, torchvision |

---

## 7. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `model.pt` | PyTorch checkpoint | ~45MB |
| `model.onnx` | ONNX export | ~44MB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/classify/resnet18_formula_v1.0.0/` |
| Local | `models/classify/resnet18_formula_v1.0.0/` |

---

## 8. Implementation Checklist

- [ ] Collect formula classification dataset
- [ ] Label formula types
- [ ] Create training script
- [ ] Train and validate model
- [ ] Export ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 9. References

- [Im2Latex Dataset](https://zenodo.org/record/56198)
- [Layout-Lite Model Card](../../production/layout_yolov10_doclaynet.md)
- Detection Taxonomy: Formula detection category

---

## 10. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - Phase 9 (Low Priority) |
