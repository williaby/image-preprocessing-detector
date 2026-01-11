---
owner: docs-team
purpose: 'Documentation for Model Card: IQA ResNet-18 Student.'
schema_type: common
status: draft
tags:
- iqa
- production
title: 'Model Card: IQA ResNet-18 Student'
---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `iqa_resnet18_student_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase 3 (Teacher-Student ML IQA) |
| **Status** | `trained` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-18 + MultiTaskHead |
| **Parameters** | ~11.7M |
| **Precision** | FP32 (training), FP16/INT8 (inference) |
| **Input Size** | 384x384x3 |
| **Output Format** | 5-class multi-label scores [0,1] |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Image Quality Assessment |
| **Role in Pipeline** | Default production IQA inference |
| **Upstream Dependencies** | Text Gate, PDF Type Classifier |
| **Downstream Consumers** | DQS Calculator, Routing Engine, Teacher (escalation) |

### Intended Use

- **Primary**: Fast, efficient IQA inference for all documents in production
- **Secondary**: First-pass quality gate before teacher escalation
- **Out of Scope**: High-stakes decisions without teacher verification

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | OHR-Bench (100K images) |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 30 |
| **Batch Size** | 256 |
| **Learning Rate** | 1e-3 with cosine decay |
| **Optimizer** | AdamW |
| **Loss Function** | BCE + Focal + Rank + Distillation Loss |
| **Distillation** | Soft labels from ResNet-50 teacher (T=4) |
| **Augmentations** | Horizontal flip, rotation +/-5deg, color jitter |
| **GPU** | Modal A10 (24GB) |
| **Training Time** | ~1.9 hours |
| **Training Date** | 2025-01-16 |
| **Training Script** | `modal/train_phase2_iqa.py` |
| **Commit SHA** | See training logs |

---

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Validation Loss | 0.14 | < 0.20 | ✅ |
| mAP | >0.85 | > 0.85 | ✅ |
| Precision (macro) | >0.83 | > 0.80 | ✅ |
| Recall (macro) | >0.80 | > 0.78 | ✅ |

### 4.2 Per-Class Performance

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Blur | 0.86 | 0.84 | 0.85 | ~2000 |
| Noise | 0.83 | 0.81 | 0.82 | ~1800 |
| Contrast | 0.87 | 0.85 | 0.86 | ~2200 |
| Skew | 0.89 | 0.87 | 0.88 | ~1500 |
| Overall | 0.85 | 0.82 | 0.83 | ~2500 |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| T4 GPU | 8ms | 12ms | 125 img/s | 0.9GB |
| A10 GPU | 6ms | 10ms | 165 img/s | 0.9GB |
| CPU (x86) | 45ms | 80ms | 22 img/s | 0.5GB |

**Note**: Meets production latency targets on both GPU and CPU.

### 4.4 Cross-Dataset Validation

| Dataset | SRCC | PLCC | ECE | Notes |
|---------|------|------|-----|-------|
| OHR-Bench | 0.86 | 0.88 | 0.06 | Primary |
| DIQA-5000 | TBD | TBD | TBD | Planned validation |

---

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | Temperature scaling (T=1.1) |
| **ECE (Expected Calibration Error)** | 0.06 |
| **Uncertainty Output** | Softmax entropy per head |
| **Escalation Threshold** | entropy > 0.7 → teacher |

---

## 6. Limitations & Known Issues

### Limitations

- **Slightly Lower Accuracy**: ~3% mAP gap vs teacher (acceptable trade-off)
- **Dataset Bias**: Trained on OHR-Bench; may not generalize to handwritten documents
- **Distillation Artifacts**: May inherit teacher's failure modes

### Known Failure Modes

- Moderate false positive rate on heavily textured backgrounds (better than teacher)
- Struggles with moire patterns from screen captures
- Underperforms on non-Latin script documents

### Bias & Fairness Considerations

- Dataset is ~85% English documents; non-Latin scripts underrepresented
- Scanned documents overrepresented vs. born-digital

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | ResNet-18 (ImageNet1K_V2) |
| **Teacher Model** | `iqa_resnet50_teacher_v1.0.0` |
| **Parent Version** | N/A (first version) |
| **Derived Models** | None |
| **Required Libraries** | PyTorch 2.0+, ONNX Runtime 1.15+ |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.pt` | PyTorch checkpoint | ~45MB | See GCS |
| `model.onnx` | ONNX export (opset 17) | ~44MB | See GCS |
| `model.torchscript` | TorchScript export | ~45MB | See GCS |
| `config.json` | Model configuration | <1KB | See GCS |

### Storage Locations

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/iqa/resnet18_student_v1.0.0/` |
| Local | `models/iqa/resnet18_student_v1.0.0/` |

---

## 9. Deployment Configuration

```yaml
# Production deployment settings
model_id: iqa_resnet18_student_v1.0.0
device_priority:
  - local_gpu
  - modal_gpu
  - cpu  # CPU fallback acceptable
inference:
  batch_size: 16
  timeout_ms: 50
  warmup_iterations: 3
monitoring:
  prometheus_metrics: true
  log_level: INFO
escalation:
  uncertainty_threshold: 0.7
  discrepancy_threshold: 0.3
  escalate_to: iqa_resnet50_teacher_v1.0.0
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-01-16 | Initial release (distilled from teacher) | Project A Team |

---

## 11. Citation

```bibtex
@misc{iqa_resnet18_student_v1.0.0,
  title={{IQA ResNet-18 Student: Fast production IQA via knowledge distillation}},
  author={{Project A Team}},
  year={{2025}},
  note={{Internal model for document preprocessing pipeline}}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Review Cadence** | Monthly (P0 model) |

---

## Checklist

- [x] All required sections completed
- [x] Performance metrics meet targets
- [x] Inference latency validated
- [x] ONNX export tested
- [x] GCS backup completed
- [x] Registry updated
- [x] Limitations documented
