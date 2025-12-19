# Model Card: Parasitic Element Classifier

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `classify_mobilenetv3_parasitic_v1.0.0` |
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
| **Architecture** | MobileNetV3-Small + Classification Head |
| **Parameters** | ~2.5M |
| **Precision** | FP32 (training), FP16/INT8 (inference) |
| **Input Size** | 224x224x3 |
| **Output Format** | 5-class multi-label sigmoid |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Parasitic element detection |
| **Role in Pipeline** | Page-level parasitic content detection |
| **Upstream Dependencies** | Ingestion pipeline |
| **Downstream Consumers** | Correction pipeline, OCR preprocessing |

### Intended Use

- **Primary**: Detect parasitic elements that may interfere with OCR
- **Secondary**: Flag documents needing preprocessing or manual review
- **Out of Scope**: Parasitic element removal (correction pipeline)

### Why MobileNetV3?

| Feature | Benefit |
|---------|---------|
| Lightweight (2.5M params) | Fast inference, low memory |
| Mobile-optimized | CPU-friendly |
| Multi-label support | Multiple parasitic types per image |

### Detection Categories

| Class | Description | Action |
|-------|-------------|--------|
| `watermark` | Visible watermarks, logos | Watermark removal or flagging |
| `stamp` | Rubber stamps, approval marks | Region exclusion |
| `redaction` | Black bars, whiteout | Skip redacted regions |
| `highlight` | Highlighting, underlining | Color filtering |
| `sticky_note` | Post-it notes, annotations | Region removal |

---

## 3. Training Details (Planned)

| Field | Planned Value |
|-------|---------------|
| **Dataset** | Custom parasitic elements dataset |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 30 |
| **Batch Size** | 128 |
| **Learning Rate** | 1e-3 with cosine annealing |
| **Optimizer** | Adam |
| **Loss Function** | BCE (multi-label) |
| **Augmentations** | Flip, rotation, color jitter, overlay |
| **GPU** | Modal T4 (16GB) |
| **Training Time** | ~1 hour (estimated) |
| **Training Script** | `modal/train_phase9_classifiers.py` (to be created) |

---

## 4. Performance Metrics (Targets)

### 4.1 Primary Benchmark

| Metric | Target | Notes |
|--------|--------|-------|
| mAP | > 0.85 | Multi-label |
| F1 (macro) | > 0.82 | Balanced across classes |
| Latency (GPU) | < 3ms | Lightweight model |
| Latency (CPU) | < 10ms | Mobile-optimized |

### 4.2 Per-Class Targets

| Class | Precision | Recall | Prevalence (Est.) |
|-------|-----------|--------|-------------------|
| watermark | > 0.90 | > 0.88 | ~15% |
| stamp | > 0.88 | > 0.85 | ~10% |
| redaction | > 0.92 | > 0.90 | ~5% |
| highlight | > 0.85 | > 0.82 | ~20% |
| sticky_note | > 0.80 | > 0.78 | ~5% |

---

## 5. Limitations & Known Issues (Anticipated)

### Expected Limitations

- May miss subtle watermarks (low opacity)
- Highlight detection depends on color contrast
- Sticky notes with similar color to document challenging

### Mitigation Strategies

- Multi-scale analysis for watermarks
- Color-space analysis for highlights
- Context-aware detection for sticky notes

---

## 6. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | MobileNetV3-Small (ImageNet1K_V2) |
| **Required Libraries** | PyTorch 2.0+, torchvision |

---

## 7. Files & Artifacts (Planned)

| File | Description | Size (Est.) |
|------|-------------|-------------|
| `model.pt` | PyTorch checkpoint | ~10MB |
| `model.onnx` | ONNX export | ~9MB |
| `model_int8.onnx` | INT8 quantized | ~3MB |

### Storage Locations (Planned)

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/classify/mobilenetv3_parasitic_v1.0.0/` |
| Local | `models/classify/mobilenetv3_parasitic_v1.0.0/` |

---

## 8. Implementation Checklist

- [ ] Collect parasitic elements dataset
- [ ] Label with multi-label annotations
- [ ] Create training script
- [ ] Train and validate model
- [ ] Export ONNX (FP16 + INT8)
- [ ] Update registry
- [ ] Complete model card

---

## 9. References

- [MobileNetV3 Paper](https://arxiv.org/abs/1905.02244)
- Detection Taxonomy: Parasitic elements category

---

## 10. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Status** | Planned - Phase 9 (Low Priority) |
