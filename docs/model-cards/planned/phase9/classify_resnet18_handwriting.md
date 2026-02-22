---
owner: docs-team
purpose: 'Documentation for Model Card: Handwriting Classifier.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: Handwriting Classifier'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_handwriting_v1.0.0` |
| **Project** | Prepare-Doc |
| **Phase** | Phase 9 (Element Classification) |
| **Status** | `planned` |
| **Priority** | P2 (Medium) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-18 + Classification Head |
| **Parameters** | ~11.7M |
| **Precision** | FP32 (training), FP16 (inference) |
| **Input Size** | 224x224x3 |
| **Output Format** | 4-class softmax |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Handwriting presence/type classification |
| **Role in Pipeline** | Page-level handwriting detection |
| **Upstream Dependencies** | Ingestion pipeline |
| **Downstream Consumers** | Routing Engine, OCR strategy selection |

### Intended Use

- **Primary**: Classify documents/regions by handwriting presence and type
- **Secondary**: Route to appropriate handwriting OCR engines
- **Out of Scope**: Handwriting recognition/transcription (downstream OCR)

### Classification Categories

| Class | Description | OCR Strategy |
|-------|-------------|--------------|
| `none` | No handwriting detected | Standard printed text OCR |
| `annotations` | Handwritten notes/marks on printed text | Hybrid OCR |
| `full_handwritten` | Entirely handwritten document | Handwriting-specialized OCR |
| `signatures` | Contains signatures only | Signature detection + skip |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Dataset** | IAM Handwriting + custom annotation dataset |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 40 |
| **Batch Size** | 64 |
| **Learning Rate** | 1e-3 with cosine annealing |
| **Optimizer** | AdamW |
| **Loss Function** | CrossEntropy with class weights |
| **Augmentations** | Rotation, scale, noise, blur |
| **GPU** | Modal T4 (16GB) |
| **Training Time** | ~3 hours (estimated) |
| **Training Script** | `modal/train_phase9_classifiers.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| Accuracy | > 94% | 4-class classification |
| F1 (macro) | > 0.92 | Balanced across classes |
| Latency (GPU) | < 5ms | Per image |
| Latency (CPU) | < 20ms | Per image |

### 4.2 Per-Class Targets

| Class | Precision | Recall | Support (Est.) |
|-------|-----------|--------|----------------|
| none | > 0.96 | > 0.95 | ~60% |
| annotations | > 0.90 | > 0.88 | ~20% |
| full_handwritten | > 0.94 | > 0.92 | ~10% |
| signatures | > 0.92 | > 0.90 | ~10% |

---

## 5. Limitations & Known Issues (Anticipated)

### Expected Limitations

- May struggle with stylized printed fonts that resemble handwriting
- Annotations detection sensitive to annotation density
- Non-Latin handwriting scripts underrepresented

### Mitigation Strategies

- Train on diverse handwriting styles
- Use multi-scale analysis for annotation detection
- Expand dataset with non-Latin scripts

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
| GCS | `gs://image_detection_b/models/classify/resnet18_handwriting_v1.0.0/` |
| Local | `models/classify/resnet18_handwriting_v1.0.0/` |

---

## 8. Implementation Checklist

- [ ] Collect handwriting classification dataset
- [ ] Define annotation guidelines
- [ ] Create training script
- [ ] Train and validate model
- [ ] Export ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 9. References

- [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database)
- Detection Taxonomy: Handwriting detection category

---

## 10. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Prepare-Doc Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - Phase 9 |
