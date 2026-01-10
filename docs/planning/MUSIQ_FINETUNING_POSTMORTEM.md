---
owner: docs-team
purpose: Documentation for MUSIQ Fine-Tuning Postmortem.
schema_type: common
status: draft
tags:
- planning
title: MUSIQ Fine-Tuning Postmortem
---

**Status**: TABLED - Pivoting to alternative approach
**Date**: 2025-12-18
**Duration**: ~6 hours of iteration

## Summary

Attempted to fine-tune PyIQA's MUSIQ model as a "Sharpness Specialist" for the DIQA-5000 pseudo-labeling ensemble (Sub-Track A1 from DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1). After multiple iterations addressing various technical challenges, the approach proved infeasible due to fundamental memory constraints with MUSIQ's multi-scale architecture.

## What Was Built

### Infrastructure (Working)

1. **Training Configuration** (`configs/musiq_finetuning.yaml`)
   - Two-phase training protocol (Phase 1: head warmup, Phase 2: full fine-tune)
   - Loss weights for sharpness specialist: [0.2, 0.6, 0.2] for [overall, sharpness, color]
   - Gradient accumulation support
   - Checkpoint selection with SRCC + ECE scoring

2. **MUSIQ Wrapper** (`src/.../labeling/finetuning/musiq_wrapper.py`)
   - `MUSIQBackbone`: Wraps PyIQA MUSIQ, uses score output as feature
   - `MultiTaskHead`: 3-output regression head (overall, sharpness, color)
   - `MUSIQMultiTask`: Combined model with freeze/unfreeze support
   - Score encoder: 1→64→256→384 dim MLP to map MUSIQ score to feature space

3. **Dataset** (`src/.../labeling/finetuning/musiq_dataset.py`)
   - `DIQA5000TrainingDataset`: PyTorch Dataset wrapper
   - Albumentations-based transforms for Phase 1/2
   - Proper [0, 1] normalization for PyIQA

4. **Loss Functions** (`src/.../labeling/finetuning/musiq_loss.py`)
   - `MUSIQSpecialistLoss`: Combined MSE + Rank + Focal calibration
   - Dimension-weighted loss with sharpness emphasis

5. **Modal Training Script** (`modal/train_musiq_finetuning.py`)
   - GCS dataset download and extraction
   - Two-phase training loop with gradient accumulation
   - Checkpoint saving to GCS
   - Validation metrics (SRCC, ECE)

6. **Unit Tests** - 120+ tests passing for all MUSIQ components

### DIQA-5000 Dataset

- Uploaded to GCS: `gs://image_detection_b/datasets/diqa-5000/`
- Size: 5.05 GB, 5000 document images
- Splits: 3500 train / 500 val / 1000 test

## Issues Encountered & Solutions Attempted

### 1. Image Size Mismatch (SOLVED)

**Error**: `RuntimeError: stack expects each tensor to be equal size`
**Solution**: Added `alb.Resize(height=224, width=224)` in transforms

### 2. OOM on T4 GPU (PARTIALLY SOLVED)

**Error**: `Runner killed (SIGKILL), exit code: 137`
**Solution**: Reduced batch size 32→16→8, added gradient accumulation (4 steps)

### 3. Input Normalization (SOLVED)

**Error**: `AssertionError: Input must be normalized to [0, 1]`
**Solution**: Removed ImageNet normalization, kept images in [0, 1] range

### 4. MUSIQ Training Mode Issue (SOLVED)

**Error**: `RuntimeError: shape '[-1, 3, 32, 32]' is invalid for input of size`
**Cause**: MUSIQ's `forward()` skips `get_multiscale_patches` in training mode
**Solution**: Force eval mode when calling MUSIQ backbone:

```python
self._musiq_model.eval()
with torch.no_grad():
    scores = self._musiq_model(x)
```

### 5. Phase 2 OOM (UNSOLVED - FUNDAMENTAL LIMITATION)

**Error**: OOM when unfreezing backbone for full fine-tuning
**Cause**: 27.3M trainable parameters require too much memory for:

- Gradient storage
- Optimizer states (AdamW momentum + variance)
- MUSIQ's multi-scale patch extraction
**Attempted Solutions**:
- Upgraded T4 (16GB) → A10G (24GB VRAM)
- Increased system RAM to 64GB
- Reduced batch size to 8 with 4x gradient accumulation
**Result**: Still OOM at epoch 16 of Phase 2

## Training Results Achieved

### Phase 1 (Head-Only Training) - COMPLETED

- 10 epochs with frozen backbone
- Trainable parameters: 99,331 (score encoder + multi-task head)
- Final metrics:
  - Loss: 0.0293
  - SRCC_sharpness: 0.3516
  - ECE: 0.0182
- Checkpoint saved: `checkpoint_phase1_epoch10.pt`

### Phase 2 (Full Fine-Tuning) - FAILED

- Crashed at epoch 16 due to OOM
- 27,340,612 trainable parameters exceeded A10G memory

## Root Cause Analysis

MUSIQ's architecture is fundamentally memory-intensive:

1. **Multi-scale patch extraction**: Processes images at multiple resolutions (224, 384) simultaneously
2. **Hash-based spatial encoding**: Additional memory for positional information
3. **ViT backbone**: Large transformer with attention mechanisms

The `get_multiscale_patches` preprocessing creates a tensor of shape:
`[batch, num_crops, seq_len, patch_dim + spatial_dim + scale_dim]`

This expands significantly with larger images or higher resolutions, making full fine-tuning impractical on commodity GPUs.

## Recommendations for Alternative Approaches

### Option 1: CLIP-based IQA (Recommended)

- Use CLIP's frozen image encoder
- Add lightweight regression head
- Much smaller memory footprint
- Good zero-shot quality understanding

### Option 2: ResNet/EfficientNet with Custom Head

- Use pretrained ImageNet features
- Add DIQA-specific regression head
- Well-understood training dynamics
- Proven approach for IQA tasks

### Option 3: DocIQ Replica (Per DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3)

- LayoutFusionDownsampler with DocLayout-YOLO
- Fuses RGB with 11-class layout masks
- 1600×1600 → 400×400 downsampling
- Already partially implemented in `layout_fusion.py`

### Option 4: Lighter IQA Models

- NIMA (Neural Image Assessment) - simpler architecture
- HyperIQA - efficient hypernetwork design
- DBCNN - lightweight dual-branch CNN

## Files to Keep

These files represent working infrastructure that can be reused:

- `configs/musiq_finetuning.yaml` - Training config structure
- `src/.../labeling/finetuning/musiq_loss.py` - Loss functions (model-agnostic)
- `src/.../labeling/finetuning/musiq_config.py` - Config class structure
- `src/.../labeling/finetuning/musiq_dataset.py` - Dataset wrapper
- `modal/train_musiq_finetuning.py` - Modal training scaffold

## Files Specific to MUSIQ (May Remove Later)

- `src/.../labeling/finetuning/musiq_wrapper.py` - MUSIQ-specific wrapper
- `tests/unit/labeling/finetuning/test_musiq_wrapper.py` - MUSIQ tests

## Lessons Learned

1. **Pre-flight memory estimation**: Should have calculated memory requirements before training
2. **Model architecture matters**: Transformer-based IQA models may not be suitable for fine-tuning on commodity GPUs
3. **Score-as-feature approach**: Using pretrained model scores as features (rather than intermediate activations) can work but limits learning capacity
4. **Multi-scale architectures**: Inherently memory-hungry, consider single-scale alternatives
5. **Modal GPU tiers**: A10G (24GB) is insufficient for fine-tuning large vision transformers; may need A100 (40GB+) or gradient checkpointing

## Next Steps

1. Archive this work on current branch
2. Evaluate alternative model architectures (CLIP, ResNet, DocIQ Replica)
3. Prototype simpler approach with lower memory footprint
4. Consider the LayoutFusionDownsampler approach from Section 4.4A3