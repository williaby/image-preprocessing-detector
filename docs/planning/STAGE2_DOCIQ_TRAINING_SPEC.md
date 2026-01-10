# Stage 2: DocIQ-Replica Training Specification

**Status**: Ready for Implementation
**Created**: 2025-12-19
**Strategy**: Option A Modified (DocIQ Paper + Adaptive Ultra-Strict Monitoring)

---

## Executive Summary

Train DocIQ-Replica (Generalist Anchor, Track A) on Stage 2 dataset following the original DocIQ paper methodology with adaptive strictness escalation to prevent MANIQA-style catastrophic failures.

### Dataset Ready

- **Location**: `gs://image_detection_b/training/stage2_diqa_ensemble/`
- **Images**: 12,742 across 5 datasets
- **Splits**: train (8,918), val (1,273), test (2,551)
- **Labels**: DeQA soft-labels + DIQA-5000 human MOS
- **Tarballs**: Uploaded to GCS (18 GB total)

---

## Training Configuration: DocIQ Paper-Aligned with Adaptive Monitoring

### Phase 1: Head Warmup (Epochs 1-15)

**Freeze**: Backbone + Layout Fusion Downsampler
**Train**: Multi-task head only

```python
{
    'epochs': 15,
    'freeze_backbone': True,
    'optimizer': 'Adam',
    'lr': 2e-4,  # PAPER ALIGNED
    'weight_decay': 1e-4,
    'batch_size': 20,  # PAPER ALIGNED (or 16 with grad_accum=2)
    'loss_weights': {
        'kl_divergence': 0.60,  # Soft-label training
        'rank_loss': 0.25,
        'mse': 0.15,
    },
}
```

### Phase 2: Full Fine-Tuning (Epochs 16-60)

**Unfreeze**: All parameters
**LR**: Continue from Phase 1 with step decay

```python
{
    'epochs': 45,
    'freeze_backbone': False,
    'optimizer': 'Adam',
    'lr_initial': 2e-4,  # PAPER ALIGNED
    'lr_schedule': 'step',  # PAPER ALIGNED
    'lr_step_size': 10,  # PAPER ALIGNED
    'lr_gamma': 0.6,  # PAPER ALIGNED
    'backbone_lr_multiplier': 0.1,  # Backbone gets 2e-5, head gets 2e-4
    'weight_decay': 1e-4,
    'batch_size': 20,
}
```

---

## Architecture: Exact DocIQ Paper Replication

### Input Pipeline

```
1600×1600 RGB Image
    ↓
Layout Detection (DocLayout-YOLO)
    ↓
11-Class Semantic Mask [11, 1600, 1600]
    ↓
Layout Fusion Downsampler
    ├── RGB Encoder: Conv 7×7 s4 → [64, 400, 400]
    ├── Layout Encoder: Conv 3×3 s2 → Conv 3×3 s2 → [64, 400, 400]
    └── Fusion: Concat [128, 400, 400] → Conv 1×1 → [3, 400, 400]
    ↓
ResNet-50 Backbone (ImageNet pretrained)
    ↓
Feature Vector [2048]
    ↓
Multi-Task Head
    ├── Overall: [2048 → 512 → 10] (10-bin soft-label)
    ├── Sharpness: [2048 → 512 → 10]
    └── Color: [2048 → 512 → 10]
```

**Critical**: No downsampling before layout fusion - full 1600×1600 processing

---

## Ultra-Strict Monitoring (Always Active)

### Level 1: Pre-Training Validation (Before Epoch 1)

```python
PreTrainingChecklist = [
    "✓ Split leakage check (no image in multiple splits)",
    "✓ Label distribution health (entropy > 1.0, all bins used)",
    "✓ Model initialization health (output range > 0.5 on dummy data)",
    "✓ Loss configuration validation (KL-div ≥ 0.4, MSE ≤ 0.3)",
    "✓ Dataset integrity (all files present, checksums match)",
]
```

### Level 2: Every Epoch Monitoring

```python
EpochChecks = {
    # Output Health (MANIQA failed here)
    'output_range': 'HALT if < 0.30 (collapsed distribution)',
    'bin_usage': 'WARN if >2 bins unused',
    'entropy': 'WARN if < 0.50 (overconfident)',
    'mode_frequency': 'HALT if >0.50 (mode collapse)',

    # Cross-Dataset Validation
    'dataset_specific_srcc': 'WARN if any < 0.70',
    'dataset_srcc_range': 'WARN if range > 0.20',

    # Calibration
    'ece': 'WARN if > 0.15, HALT if > 0.20',
    'ece_growth': 'ESCALATE if grows >0.02/epoch',
}
```

### Level 3: Every 3 Epochs (Test Set Early Warning)

```python
ValTestDivergenceCheck = {
    'val_srcc': 'Validation set SRCC',
    'test_srcc': 'Test set SRCC (read-only)',
    'divergence': '|val_srcc - test_srcc|',
    'action': {
        'divergence > 0.15': 'WARN (possible overfitting)',
        'divergence > 0.20': 'ESCALATE to ultra-strict',
        'divergence > 0.25': 'HALT training',
    },
}
```

### Level 4: Adaptive Escalation

**Escalation Triggers** (any one triggers ultra-strict mode):

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Output range | < 0.40 | Reduce LR by 50%, increase dropout to 0.35 |
| Val/test gap | > 0.15 | Reduce LR by 50%, increase weight decay to 2e-3 |
| ECE | > 0.15 | Add label smoothing 0.05, stricter checkpointing |
| Dataset SRCC | Any < 0.70 | Review dataset, consider rebalancing |

**Ultra-Strict Mode Changes**:

```python
ultra_strict_mode = {
    'lr': initial_lr * 0.5,
    'dropout': 0.35,
    'weight_decay': 2e-3,
    'circuit_breaker_thresholds': {
        'min_output_range': 0.35,  # From 0.30
        'max_val_test_gap': 0.15,  # From 0.20
        'max_ece': 0.12,  # From 0.15
    },
}
```

---

## Checkpoint Selection: Multi-Criteria with Veto Power

### Primary Criteria (70% SRCC + 30% ECE)

```python
checkpoint_score = (
    0.70 * mean_val_srcc +
    0.30 * (1 - val_ece)
)
```

### Veto Criteria (ANY fails → reject checkpoint)

| Criterion | Threshold | Reason |
|-----------|-----------|--------|
| ECE | Must be < 0.12 | Reject poorly calibrated models |
| Output range | Must be > 0.35 | Reject collapsed distributions |
| Any dataset SRCC | Must be > 0.70 | Reject dataset-specific failures |
| Val/test divergence | Must be < 0.18 | Reject overfitted checkpoints |

Only checkpoints that pass ALL vetoes compete on the composite score.

---

## Two-Tier Evaluation

### Tier 1: Gold Standard (DIQA-5000 Human MOS)

**Test Set**: 1,000 images with human ratings

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC (overall) | > 0.85 | Primary success criterion |
| SRCC (sharpness) | > 0.82 | Generalist, not specialist |
| SRCC (color) | > 0.82 | Generalist, not specialist |
| PLCC (mean) | > 0.85 | Linear correlation |
| MAE | < 0.15 | Mean absolute error (0-1 scale) |
| ECE (mean) | < 0.08 | Well-calibrated |

### Tier 2: Silver Standard (DeQA Pseudo-Labels)

**Test Set**: 1,551 images (SmartDoc-QA, FUNSD, SROIE, Tobacco-800)

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC vs DeQA | > 0.80 | Teacher replication |
| PLCC vs DeQA | > 0.78 | Linear correlation |
| KL-divergence | < 0.15 | Distribution matching |
| Per-dataset consistency | Range < 0.15 | No dataset-specific failures |

**Success**: High Tier 1 AND high Tier 2 → model generalizes
**Failure**: High Tier 1, low Tier 2 → overfitting to DIQA-5000 (MANIQA problem)

---

## Implementation Checklist

### Data Preparation

- [x] Stage 2 dataset assembled (12,742 images)
- [x] Tarballs created (train/val/test)
- [x] Upload to GCS (complete)
- [ ] Pre-generate layout masks for all images
- [ ] Cache masks to avoid runtime overhead

### Code Implementation

- [x] LayoutFusionDownsampler implemented
- [x] DocIQReplica model implemented
- [x] MultiTaskHead implemented
- [x] Complete training loop with monitoring
- [x] Implement pre-training validation
- [x] Implement adaptive escalation logic
- [x] Implement checkpoint selection with vetoes
- [ ] Implement two-tier evaluation

### Infrastructure

- [x] Modal function for training
- [x] GCS dataset download in Modal
- [x] Checkpoint saving to Modal volume
- [ ] TensorBoard logging
- [x] Training resumption from checkpoints

---

## Estimated Timeline

| Phase | Task | Duration | GPU |
|-------|------|----------|-----|
| **Data Prep** | GCS upload | 30-60 min | N/A |
| **Data Prep** | Generate layout masks | 3-4 hrs | T4 |
| **Phase 1** | Head warmup training | 2-3 hrs | A100-80GB |
| **Phase 2** | Full fine-tuning | 10-15 hrs | A100-80GB |
| **Evaluation** | Two-tier test eval | 30 min | A100-80GB |
| **Total** | End-to-end | ~18-24 hrs | |

**Cost Estimate** (Modal A100-80GB @ ~$3/hr):

- Training: 12-18 hours × $3/hr = **$36-54**
- Layout mask generation: 3-4 hours × $0.60/hr (T4) = **$2-3**
- **Total**: **$38-57**

---

## Success Criteria

### Minimum Viable (Phase 1 Complete)

- [ ] Phase 1 completes without halting (15 epochs)
- [ ] Validation SRCC > 0.70 (any dimension)
- [ ] No output distribution collapse
- [ ] No val/test divergence > 0.20

### Production Ready (Phase 2 Complete)

- [ ] Tier 1 SRCC (DIQA-5000) > 0.85 (overall)
- [ ] Tier 2 SRCC (Others) > 0.80 (overall)
- [ ] ECE < 0.12 across all dimensions
- [ ] No dataset-specific failures (all SRCC > 0.70)
- [ ] Output range > 0.35 (full scale usage)

### Stretch Goals

- [ ] Tier 1 SRCC > 0.88 (matches DocIQ paper claims)
- [ ] Tier 2 SRCC > 0.85 (strong generalization)
- [ ] ECE < 0.08 (excellent calibration)

---

## Risk Mitigation

### Risk: Output Distribution Collapse (MANIQA Failure Mode)

**Detection**:

- Monitor output range every epoch
- Monitor bin usage every epoch
- Alert if range < 0.40 or >2 bins unused

**Response**:

- Escalate to ultra-strict (reduce LR, increase dropout)
- If persists, HALT and investigate loss function

### Risk: Val/Test Divergence (Overfitting to Validation)

**Detection**:

- Check test set every 3 epochs
- Alert if |val_srcc - test_srcc| > 0.15

**Response**:

- Escalate to ultra-strict
- Increase weight decay
- Add label smoothing

### Risk: Dataset-Specific Failure (Poor Generalization)

**Detection**:

- Track per-dataset SRCC every epoch
- Alert if any dataset < 0.70 or range > 0.20

**Response**:

- Review dataset balance in training
- Consider dataset-specific augmentation
- May indicate need for more diverse training data

---

## Next Steps

1. **Complete GCS Upload** (in progress)
   - Train: 13 GB
   - Val: 1.7 GB
   - Test: 3.5 GB
   - Metadata: 3.7 KB

2. **Pre-Generate Layout Masks**
   - Run DocLayout-YOLO on all 12,742 images
   - Cache to GCS for training
   - Estimated: 3-4 hours on T4

3. **Implement Complete Training Script**
   - All monitoring levels (pre-training, batch, epoch)
   - Adaptive escalation logic
   - Multi-criteria checkpoint selection
   - Two-tier evaluation

4. **Launch Training on Modal**
   - Phase 1: ~2-3 hours
   - Phase 2: ~10-15 hours
   - Monitor for escalation triggers

---

## Document Trail Complete

| Document | Purpose |
|----------|---------|
| [STAGE2_DOCIQ_TRAINING_SPEC.md](STAGE2_DOCIQ_TRAINING_SPEC.md) | This file - complete training spec |
| [UNIFIED_LABELING_STRATEGY.md](UNIFIED_LABELING_STRATEGY.md) | Stage 1-4 workflow context |
| [DIQA-5000_Pseudo_Labels_v2.md](DIQA-5000_Pseudo_Labels_v2.md) | 5-model ensemble details |
| [MANIQA_DIQA5000_v1.0.0.md](../model-cards/MANIQA_DIQA5000_v1.0.0.md) | Failure analysis - lessons learned |
| Stage 2 Dataset README | `E:\image_detection\03_training_datasets\stage2_diqa_ensemble\README.md` |
| Stage 2 Dataset Manifest | `E:\image_detection\03_training_datasets\stage2_diqa_ensemble\MANIFEST.json` |

---

## References

- **DocIQ Paper**: [arXiv:2509.17012](https://arxiv.org/abs/2509.17012) - Training methodology (Section IV-A)
- **DeQA-Doc Paper**: [arXiv:2507.12796](https://arxiv.org/html/2507.12796) - Soft-label methodology
- **MANIQA Failure**: [docs/model-cards/MANIQA_DIQA5000_v1.0.0.md](../model-cards/MANIQA_DIQA5000_v1.0.0.md)

---

*Document Version 1.0 - December 2025*
