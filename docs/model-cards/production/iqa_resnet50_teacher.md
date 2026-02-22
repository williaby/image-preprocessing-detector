---
owner: docs-team
purpose: 'Documentation for Model Card: IQA ResNet-50 Teacher.'
schema_type: common
status: draft
tags:
- iqa
- production
title: 'Model Card: IQA ResNet-50 Teacher'
---

> ⚠️ **DEPRECATED** — This model (`iqa_resnet50_teacher_v1.0.0`) has been superseded by **SigLIP 2 NAFlex** as the multi-task teacher model (Phase 2+, Stream 4C). The ResNet-50 teacher was trained for Phase 3 and is no longer part of the active pipeline. See [`docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) for the current architecture.

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `iqa_resnet50_teacher_v1.0.0` |
| **Project** | Prepare-Doc |
| **Phase** | Phase 3 (Teacher-Student ML IQA) |
| **Status** | `trained` |
| **Priority** | P0 (Critical) |
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
| **Output Format** | 5-class multi-label scores [0,1] |
| **Export Formats** | PyTorch, ONNX, TorchScript |
| **ONNX Opset** | 17 |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Image Quality Assessment |
| **Role in Pipeline** | Teacher model for high-risk escalation |
| **Upstream Dependencies** | Text Gate, PDF Type Classifier, Classical IQA |
| **Downstream Consumers** | DQS Calculator, Routing Engine |

### Intended Use

- **Primary**: High-accuracy IQA inference for flagged documents (high uncertainty, discrepancy with student)
- **Secondary**: Knowledge distillation source for student model training
- **Out of Scope**: Real-time production inference (use student model instead)

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | OHR-Bench (100K images) |
| **Train/Val/Test Split** | 80/10/10 |
| **Epochs** | 50 |
| **Batch Size** | 128 |
| **Learning Rate** | 1e-4 with cosine decay |
| **Optimizer** | AdamW |
| **Loss Function** | BCE + Focal + Rank |
| **Augmentations** | Horizontal flip, rotation +/-5deg, color jitter |
| **GPU** | Modal A10 (24GB) |
| **Training Time** | ~4 hours |
| **Training Date** | 2025-01-15 |
| **Training Script** | `modal/train_phase2_iqa.py` |
| **Commit SHA** | See training logs |

---

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Validation Loss | 0.27 | < 0.30 | ✅ |
| mAP | >0.88 | > 0.88 | ✅ |
| Precision (macro) | >0.85 | > 0.80 | ✅ |
| Recall (macro) | >0.82 | > 0.80 | ✅ |

### 4.2 Per-Class Performance

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| Blur | 0.89 | 0.87 | 0.88 | ~2000 |
| Noise | 0.86 | 0.84 | 0.85 | ~1800 |
| Contrast | 0.90 | 0.88 | 0.89 | ~2200 |
| Skew | 0.92 | 0.90 | 0.91 | ~1500 |
| Overall | 0.88 | 0.85 | 0.86 | ~2500 |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| T4 GPU | 25ms | 35ms | 40 img/s | 2.1GB |
| A10 GPU | 18ms | 28ms | 55 img/s | 2.1GB |
| CPU (x86) | N/A | N/A | N/A | N/A |

**Note**: Teacher model is GPU-only for production use.

### 4.4 Cross-Dataset Validation

| Dataset | SRCC | PLCC | ECE | Notes |
|---------|------|------|-----|-------|
| OHR-Bench | 0.89 | 0.91 | 0.05 | Primary |
| DIQA-5000 | TBD | TBD | TBD | Planned validation |

---

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | Temperature scaling (T=1.2) |
| **ECE (Expected Calibration Error)** | 0.05 |
| **Uncertainty Output** | Softmax entropy per head |
| **Escalation Threshold** | N/A (this IS the escalation target) |

---

## 6. Limitations & Known Issues

### Limitations

- **GPU Required**: Too slow for CPU inference in production
- **Dataset Bias**: Trained on OHR-Bench; may not generalize to handwritten documents
- **Memory Footprint**: Requires 2.1GB GPU memory

### Known Failure Modes

- High false positive rate on heavily textured backgrounds
- Struggles with moire patterns from screen captures
- Underperforms on non-Latin script documents

### Bias & Fairness Considerations

- Dataset is ~85% English documents; non-Latin scripts underrepresented
- Scanned documents overrepresented vs. born-digital

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | ResNet-50 (ImageNet1K_V2) |
| **Parent Version** | N/A (first version) |
| **Derived Models** | `iqa_resnet18_student_v1.0.0` (distilled) |
| **Required Libraries** | PyTorch 2.0+, ONNX Runtime 1.15+ |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.pt` | PyTorch checkpoint | ~100MB | See GCS |
| `model.onnx` | ONNX export (opset 17) | ~98MB | See GCS |
| `model.torchscript` | TorchScript export | ~100MB | See GCS |
| `config.json` | Model configuration | <1KB | See GCS |

### Storage Locations

| Environment | Path |
|-------------|------|
| GCS | `gs://image_detection_b/models/iqa/resnet50_teacher_v1.0.0/` |
| Local | `models/iqa/resnet50_teacher_v1.0.0/` |

---

## 9. Deployment Configuration

```yaml
# Production deployment settings
model_id: iqa_resnet50_teacher_v1.0.0
device_priority:
  - local_gpu
  - modal_gpu
  - BLOCK  # Do not run on CPU
inference:
  batch_size: 8
  timeout_ms: 100
  warmup_iterations: 3
monitoring:
  prometheus_metrics: true
  log_level: INFO
escalation:
  trigger_conditions:
    - student_uncertainty > 0.7
    - student_classical_discrepancy > 0.3
    - high_risk_document: true
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-01-15 | Initial release | Prepare-Doc Team |

---

## 11. Citation

```bibtex
@misc{iqa_resnet50_teacher_v1.0.0,
  title={{IQA ResNet-50 Teacher: High-capacity IQA for document preprocessing}},
  author={{Prepare-Doc Team}},
  year={{2025}},
  note={{Internal model for document preprocessing pipeline}}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Prepare-Doc Core Team |
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
