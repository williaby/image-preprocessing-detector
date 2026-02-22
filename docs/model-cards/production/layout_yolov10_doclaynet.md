---
owner: docs-team
purpose: 'Documentation for Model Card: Layout YOLOv10 DocLayNet.'
schema_type: common
status: draft
tags:
- production
title: 'Model Card: Layout YOLOv10 DocLayNet'
---

> ⚠️ **DEPRECATED** — This model (`layout_yolov10_doclaynet_v1.0.0`) has been superseded by the Docling layout models: `docling-layout-egret-xlarge` (accuracy) and `docling-layout-heron` (speed). Retain for historical reference only.

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `layout_yolov10_doclaynet_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase 2 (Layout-Lite Detection) |
| **Status** | `pretrained` |
| **Priority** | P1 (High) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | YOLOv10-doc (document-optimized) |
| **Parameters** | ~8M (YOLOv10-S variant) |
| **Precision** | FP32 (original), FP16 (inference) |
| **Input Size** | 640x640x3 (resized with padding) |
| **Output Format** | Bounding boxes + class scores (COCO format) |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Coarse Layout Detection (Layout-Lite) |
| **Role in Pipeline** | Document element detection for structural complexity scoring |
| **Upstream Dependencies** | Text Gate (only runs if text detected) |
| **Downstream Consumers** | DQS Calculator, Routing Engine |

### Intended Use

- **Primary**: Detect 11 DocLayNet element classes for structural complexity scoring
- **Secondary**: Provide coarse page attributes (has_tables, has_figures, has_formulas)
- **Out of Scope**: Fine-grained table structure extraction (Project B), reading order prediction

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | DocLayNet (IBM, 80K+ documents) |
| **Train/Val/Test Split** | Pre-defined by DocLayNet |
| **Training** | **Pretrained** - no additional training required |
| **Original Authors** | Ultralytics / DocLayNet community |
| **Weights Source** | Hugging Face / Official release |

**Note**: This model uses pretrained weights from the DocLayNet-trained YOLOv10 variant. No additional training was performed.

---

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| mAP@0.5 | 0.72 | > 0.70 | ✅ |
| mAP@0.5:0.95 | 0.58 | > 0.55 | ✅ |
| FPS (T4 GPU) | 85+ | > 60 | ✅ |
| FPS (A10 GPU) | 120+ | > 80 | ✅ |

### 4.2 Per-Class Performance

| Class | AP@0.5 | AP@0.5:0.95 | Support |
|-------|--------|-------------|---------|
| Caption | 0.68 | 0.52 | ~5000 |
| Footnote | 0.65 | 0.48 | ~3000 |
| Formula | 0.71 | 0.55 | ~4000 |
| List-Item | 0.74 | 0.58 | ~8000 |
| Page-Footer | 0.82 | 0.68 | ~6000 |
| Page-Header | 0.80 | 0.65 | ~6000 |
| Picture | 0.75 | 0.60 | ~7000 |
| Section-Header | 0.78 | 0.62 | ~9000 |
| Table | 0.76 | 0.61 | ~5000 |
| Text | 0.85 | 0.72 | ~15000 |
| Title | 0.70 | 0.54 | ~4000 |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| T4 GPU | 12ms | 18ms | 85 img/s | 1.2GB |
| A10 GPU | 8ms | 14ms | 125 img/s | 1.2GB |
| CPU (x86) | 120ms | 180ms | 8 img/s | 0.8GB |

### 4.4 Cross-Dataset Validation

| Dataset | mAP@0.5 | Notes |
|---------|---------|-------|
| DocLayNet | 0.72 | Primary (pretrained) |
| PubLayNet | 0.68 | Cross-domain test |
| Custom samples | 0.70 | Internal validation |

---

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | None (detection confidence scores) |
| **Confidence Threshold** | 0.25 (default), 0.5 (high precision) |
| **NMS IoU Threshold** | 0.45 |
| **Uncertainty Output** | Detection confidence scores |

---

## 6. Limitations & Known Issues

### Limitations

- **Coarse Layout Only**: Designed for page-level element detection, not fine-grained structure
- **DocLayNet Bias**: Optimized for business/scientific documents; may underperform on other domains
- **No Reading Order**: Does not predict reading order (Project B responsibility)

### Known Failure Modes

- Struggles with heavily overlapping elements
- May miss small captions near figures
- Inconsistent on multi-column layouts with varying widths

### Bias & Fairness Considerations

- DocLayNet is predominantly English business/scientific documents
- Non-Latin scripts may have reduced detection accuracy
- Historical documents with unusual layouts underrepresented

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | YOLOv10-S (COCO pretrained) |
| **Fine-tuning Dataset** | DocLayNet |
| **Parent Version** | N/A (external pretrained) |
| **Derived Models** | None |
| **Required Libraries** | Ultralytics 8.0+, PyTorch 2.0+ |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.pt` | PyTorch checkpoint | ~16MB | See source |
| `model.onnx` | ONNX export (opset 17) | ~15MB | See GCS |
| `config.yaml` | Model configuration | <1KB | See GCS |

### Storage Locations

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/layout/yolov10_doclaynet_v1.0.0/` |
| Local | `models/layout/yolov10_doclaynet_v1.0.0/` |
| Source | Hugging Face / Ultralytics |

---

## 9. Deployment Configuration

```yaml
# Production deployment settings
model_id: layout_yolov10_doclaynet_v1.0.0
device_priority:
  - local_gpu
  - modal_gpu
  - cpu  # CPU fallback acceptable for batch processing
inference:
  batch_size: 4
  confidence_threshold: 0.25
  nms_iou_threshold: 0.45
  max_detections: 100
  timeout_ms: 50
monitoring:
  prometheus_metrics: true
  log_level: INFO
output:
  format: coco  # [x, y, width, height]
  include_scores: true
  include_class_names: true
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-01-10 | Initial integration from pretrained weights | Project A Team |

---

## 11. Citation

```bibtex
@article{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  author={Pfitzmann, Birgit and others},
  journal={arXiv preprint arXiv:2206.01062},
  year={2022}
}

@misc{yolov10,
  title={YOLOv10: Real-Time End-to-End Object Detection},
  author={Wang, Ao and others},
  year={2024}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Review Cadence** | Quarterly (P1 model) |

---

## Checklist

- [x] All required sections completed
- [x] Performance metrics meet targets
- [x] Inference latency validated
- [x] ONNX export tested
- [x] GCS backup completed
- [x] Registry updated
- [x] Limitations documented
