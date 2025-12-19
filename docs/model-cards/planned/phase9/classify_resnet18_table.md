# Model Card: Table Type Classifier

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `classify_resnet18_table_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
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
| **Input Size** | 224x224x3 (cropped table region) |
| **Output Format** | 4-class softmax |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Table type classification |
| **Role in Pipeline** | Post-detection classifier for table elements |
| **Upstream Dependencies** | Layout-Lite (YOLOv10) table detections |
| **Downstream Consumers** | Routing Engine, Project B (table structure) |

### Intended Use

- **Primary**: Classify detected table regions into complexity categories
- **Secondary**: Inform OCR strategy for table extraction
- **Out of Scope**: Table detection (use YOLOv10), table structure extraction (Project B)

### Classification Categories

| Class | Description | OCR Strategy |
|-------|-------------|--------------|
| `simple` | Grid tables with clear borders | Standard table OCR |
| `complex` | Multi-level headers, merged cells | Advanced table OCR |
| `nested` | Tables within tables | Recursive extraction |
| `borderless` | No visible borders/lines | Structure inference |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Dataset** | PubTables-1M (table crops) + DocLayNet tables |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 30 |
| **Batch Size** | 64 |
| **Learning Rate** | 1e-3 with step decay |
| **Optimizer** | Adam |
| **Loss Function** | CrossEntropy |
| **Augmentations** | Flip, rotation, scale, color jitter |
| **GPU** | Modal T4 (16GB) |
| **Training Time** | ~2 hours (estimated) |
| **Training Script** | `modal/train_phase9_classifiers.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| Accuracy | > 92% | 4-class classification |
| F1 (macro) | > 0.90 | Balanced across classes |
| Latency (GPU) | < 5ms | Per table crop |
| Latency (CPU) | < 20ms | Per table crop |

### 4.2 Per-Class Targets

| Class | Precision | Recall | Support (Est.) |
|-------|-----------|--------|----------------|
| simple | > 0.95 | > 0.94 | ~40% |
| complex | > 0.90 | > 0.88 | ~30% |
| nested | > 0.85 | > 0.82 | ~15% |
| borderless | > 0.88 | > 0.86 | ~15% |

---

## 5. Limitations & Known Issues (Anticipated)

### Expected Limitations

- Requires pre-detection by YOLOv10
- May struggle with partially visible tables
- Borderless detection challenging for unusual layouts

### Mitigation Strategies

- Use confidence thresholds for uncertain cases
- Ensemble with rule-based features if needed

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
| GCS | `gs://image_detection_b/models/classify/resnet18_table_v1.0.0/` |
| Local | `models/classify/resnet18_table_v1.0.0/` |

---

## 8. Implementation Checklist

- [ ] Prepare table crop dataset
- [ ] Label table types (simple/complex/nested/borderless)
- [ ] Create training script
- [ ] Train and validate model
- [ ] Export ONNX
- [ ] Update registry
- [ ] Complete model card

---

## 9. References

- [PubTables-1M Paper](https://arxiv.org/abs/2110.00061)
- [Layout-Lite Model Card](../../production/layout_yolov10_doclaynet.md)

---

## 10. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - Phase 9 |
