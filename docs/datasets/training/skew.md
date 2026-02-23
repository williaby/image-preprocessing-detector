---
l4_category: training-dataset
l4_dataset: skew
l4_workstream: WS2
l4_source_datasets:
  - funsd
  - doclaynet
  - sroie
  - rvl-cdip
  - nist-sd2
  - nist-sd6
  - ohr-bench
  - iam
  - arabic-docs
  - tobacco800
  - smartdoc-qa
  - fintabnet
  - hiertext
l4_generation_script: scripts/generate_skew_dataset.py
l4_gcs_path: gs://image_detection_b/skew_training/
l4_image_count: 90412
l4_status: active
---

## skew

> **Quick Stats**: 90,412 images | 71K synthetic + 19K natural scans | 384×384 JPEG q90
>
> **Status**: ✅ Ready | **Created**: 2026-02-11

### Overview

Skew estimation training dataset for MobileNetV4-Conv-S Head 2. Combines synthetic document images
with classical-ensemble-labeled natural scans from 13 real-document source datasets.

**Purpose**: Train hybrid 42-bin classification + residual regression skew estimator.

**Design Reference**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

### Configuration

| Attribute | Value |
|-----------|-------|
| **Total Images** | 90,412 |
| **Synthetic** | 71,498 |
| **Natural Scans** | 18,914 (13 datasets, conf ≥ 0.7 filter) |
| **Image Size** | 384×384 JPEG quality 90 |
| **Skew Range** | ±45° (42 non-uniform bins) |
| **Split** | Train: 70,763 / Val: 9,025 / Test: 10,624 |
| **Local Path** | `E:\03_training_datasets\skew\` |
| **GCS Path** | `gs://image_detection_b/skew_training/` |
| **Head** | MobileNetV4-Conv-S H2 (orientation 4-class + 42-bin + residual regression) |

### Training Results

Best configuration: `conv_small @ 224px, 50 epochs`

| Config | Val MAE | Test MAE | SRCC | Orient Acc | CPU Inference |
|--------|---------|----------|------|------------|---------------|
| conv_small @ 224px, 50ep | **0.837°** | **0.956°** | **0.936** | 99.5% | 17.5ms |
| conv_small @ 320px, 10ep | 1.028° | 1.028° | -- | -- | 18.1ms |
| conv_small @ 384px, 10ep | 1.005° | 1.005° | -- | -- | 20.5ms |
| conv_medium @ 224px, 10ep | 1.017° | 1.017° | -- | -- | 40.1ms (ELIMINATED) |

**Run ID**: `20260212_155402` | **Checkpoint**: `best_model.pt` (epoch 47)

**Inference detail** (conv_small @ 224px):

- Mean: 17.5ms, p50: 17.4ms, p95: 18.8ms
- Within 0.5°: 70.8%
- Natural scan MAE: consistently ~0.9° across all configs (synthetic images drive overall MAE differences)

### Model Architecture

**Class**: `SkewEstimatorNet` -- MobileNetV4-Conv-S backbone + 3 heads:

| Head | Type | Classes / Range |
|------|------|-----------------|
| H1 (orientation) | 4-class classification | 0°, 90°, 180°, 270° |
| H2a (bins) | 42-class classification | Non-uniform bins spanning ±45° |
| H2b (residual) | Regression | Per-bin residual (half-width of each bin) |

**Critical**: `max_residual` is per-bin (matches each bin's half-width), NOT a global constant.
Global clamping causes systematic error at bin boundaries.

### Source Datasets (Natural Scans)

Natural scans drawn from the training splits of 13 source datasets:

| Dataset | Category | Approx Count |
|---------|----------|-------------|
| FUNSD | Forms | ~149 |
| DocLayNet | Mixed document | sampled |
| SROIE | Receipts | ~626 |
| RVL-CDIP | Scanned docs | sampled |
| NIST SD-2 | Tax forms | sampled |
| NIST SD-6 | Forms | sampled |
| OHR-Bench | Mixed | sampled |
| IAM | Handwriting | sampled |
| Arabic-docs | Arabic | sampled |
| Tobacco800 | Archival | sampled |
| SmartDoc-QA | Mobile capture | sampled |
| FinTabNet | Financial | sampled |
| HierText | Scene text | sampled |

**Labeling**: Classical ensemble (Hough transform + projection profiles + gradient methods).
Confidence filter: ≥0.7 required. Labels below threshold excluded from training.

### Label Schema

```json
{
  "image_path": "skew/train/img_00042.jpg",
  "skew_angle_degrees": -3.75,
  "orientation_class": 0,
  "bin_index": 18,
  "bin_residual": 0.25,
  "label_provenance": "classical_ensemble",
  "label_confidence": 0.85,
  "source_type": "natural_scan",
  "source_dataset": "DocLayNet",
  "split": "train"
}
```

**Synthetic label provenance**: `tier_0_exact` (skew angle is the generation parameter; confidence=1.0)

**Natural label provenance**: `classical_ensemble` (multi-method, conf ≥ 0.7)

### Directory Structure

```text
skew/
├── labels.json          (90,412 entries)
├── splits.jsonl         (SHA256-keyed split registry)
├── train/               (70,763 images)
├── val/                 (9,025 images)
└── test/                (10,624 images)
```

### Generation Scripts

| Script | Purpose |
|--------|---------|
| `generate_skew_dataset.py` | Generate synthetic skew images |
| `merge_skew_datasets.py` | Merge synthetic + natural scan subsets |
| `select_natural_scan_skew_subset.py` | Stratify and select natural scans |
| `label_skew_classical.py` | Classical ensemble angle labeling |

**Training script**: `modal/train_skew_estimator.py`

### QAT / Quantization Notes

- `model.train()` MUST be called BEFORE `prepare_qat()` (crashes with AssertionError otherwise)
- `prepare_qat()` adds `weight_fake_quant` / `activation_post_process` keys to state_dict
- For evaluation: create fresh `SkewEstimatorNet()` and load `best_model.pt` (pre-QAT) directly
- For resume: use `model.load_state_dict(ckpt, strict=False)` + try/except on optimizer/scheduler

### Next Steps

1. Dataset expansion: additional natural scans from synth-multiscript-v3 derived views
2. ONNX INT8 quantization for production deployment
3. Longer training run (75-100 epochs) to push val MAE below 0.80°
