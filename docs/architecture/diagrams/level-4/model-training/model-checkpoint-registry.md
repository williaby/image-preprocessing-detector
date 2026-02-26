---
l4_category: model-checkpoint
l4_generated: manual
owner: docs-team
tags:
- architecture
title: 'Level 4: Model Checkpoint Registry'
---

# Model Checkpoint Registry

This registry is **manually maintained** as training runs complete. It catalogs
trained model checkpoints with run IDs, evaluation metrics, and GCS storage paths.

## MobileNetV4 Checkpoints

### Skew Estimator (conv_small)

| Run ID | Epoch | Architecture | Resolution | Val MAE | Test MAE | SRCC | CPU Latency | GCS Path | Status |
|--------|-------|-------------|-----------|---------|----------|------|-------------|----------|--------|
| `20260212_155402` | 47 | conv_small | 224px | 0.837° | 0.956° | 0.936 | 17.5ms | `gs://image_detection_b/skew_checkpoints/20260212_155402/best_model.pt` | ✅ Best |

**Notes**:

- orient_acc=99.5%, within 0.5°: 70.8%
- Ablation winner over conv_small@320 (marginal MAE gain vs +3% CPU) and conv_medium@224 (ELIMINATED — too close to SigLIP 50ms budget)

---

## SigLIP 2 Checkpoints

*Training pending — no checkpoints yet.*

| Run ID | Epoch | Architecture | Val Loss | Heads | GCS Path | Status |
|--------|-------|-------------|---------|-------|----------|--------|
| *(pending)* | | | | | | |

---

## Retired Checkpoints

### ResNet IQA (Phase 3 — Teacher-Student)

These checkpoints are from the Phase 3 ResNet teacher-student system. They are superseded
by the SigLIP 2 multi-task pipeline but retained for reference.

| Model | Epochs | Val Loss | Notes |
|-------|--------|---------|-------|
| ResNet-50 (teacher) | 50 | 0.27 | ONNX + TorchScript exported |
| ResNet-18 (student) | 30 | 0.14 | Production default for Phase 3 |

---

## Column Definitions

| Column | Definition |
|--------|-----------|
| Run ID | Timestamp-based ID from training script (`YYYYMMDD_HHMMSS`) |
| Epoch | Best checkpoint epoch (by val loss/MAE) |
| Val MAE | Validation mean absolute error (regression heads) |
| Test MAE | Test set MAE at run completion |
| SRCC | Spearman rank correlation coefficient |
| CPU Latency | Mean inference latency on CPU (no GPU) |
| GCS Path | Full GCS URI to checkpoint file |
| Status | Active (in production), Best (best run), Retired, Candidate |
