---
owner: docs-team
purpose: 'Documentation for Model Card: MANIQA-DIQA5000-Finetuned v1.0.0.'
schema_type: common
status: draft
tags:
- iqa
title: 'Model Card: MANIQA-DIQA5000-Finetuned v1.0.0'
---

**Model ID**: `MANIQA-DIQA5000-Finetuned-v1.0.0`
**Training Date**: 2025-12-19
**Model Type**: Document Image Quality Assessment (Multi-Task)
**Framework**: PyTorch 2.4.0, PyIQA 0.1.12
**Status**: ⚠️ **FAILED - Critical Performance Issue**

---

## Executive Summary

**CRITICAL FINDING**: This model exhibits a catastrophic failure where training validation performance (SRCC 0.83) completely fails to transfer to the test set (SRCC ~0.00). The model produces a **collapsed output distribution** in the range [1.2-2.0] instead of utilizing the full [1-5] scale, resulting in near-zero correlation with ground truth quality scores.

**Recommendation**: Do not use this model. Retrain with v2.0.0 addressing the identified issues.

---

## Model Architecture

### Base Model

- **Backbone**: MANIQA (Multi-dimension Attention Network for No-Reference IQA)
  - Pretrained on KonIQ-10k dataset
  - ViT encoder + Swin Transformer blocks + TABlocks
  - Feature dimension: 384
  - Input resolution: 224×224

### Custom Multi-Task Head

- **Shared Layers**:
  - Linear(384 → 384) + ReLU + Dropout(0.1)
  - Linear(384 → 192) + ReLU + Dropout(0.1)
- **Task-Specific Heads** (3 dimensions):
  - `overall_head`: Linear(192 → 1) + Sigmoid
  - `sharpness_head`: Linear(192 → 1) + Sigmoid
  - `color_head`: Linear(192 → 1) + Sigmoid
- **Output Range**: [0, 1] (sigmoid) → scaled to [1, 5] for evaluation
- **Total Parameters**: 326 keys, ~519 MB checkpoint

---

## Training Configuration

### Two-Phase Training Protocol

**Phase 1: Head Warmup** (Epochs 1-15)

- Frozen MANIQA backbone
- Learning rate: 1e-3
- Warmup: 3 epochs

**Phase 2: Full Fine-Tuning** (Epochs 16-50)

- Differential learning rates:
  - Backbone: 1e-6 (very conservative to preserve pretrained features)
  - Head: 1e-4
- Warmup: 2 epochs

### Optimization

- **Batch Size**: 4 (physical) × 8 (gradient accumulation) = 32 (effective)
- **Optimizer**: AdamW
- **Weight Decay**: 1e-4
- **Gradient Clipping**: Max norm 1.0
- **Mixed Precision**: FP16 (AMP) for memory efficiency

### Loss Function

Multi-task loss combining:

- **MSE Loss** (0.6 weight): L2 distance between predictions and ground truth
- **Rank Loss** (0.2 weight): Pairwise ranking consistency
- **Focal Loss** (0.2 weight): Focus on hard examples

**Dimension Weights**: [0.34, 0.33, 0.33] (overall, sharpness, color) - balanced generalist

---

## Training Dataset

**DIQA-5000** (Document Image Quality Assessment)

- **Total Samples**: 5000 document images
- **Train/Val/Test Split**: 3500 / 500 / 1000
- **Annotations**: 3 quality dimensions on 1-5 scale
  - Overall quality
  - Sharpness
  - Color fidelity
- **Resolution**: Variable (224×224 after preprocessing)
- **Source**: Mixed document types (invoices, receipts, forms, etc.)

---

## Training Results (Epoch 50)

### Validation Performance (500 samples)

| Dimension | SRCC | PLCC | ECE |
|-----------|------|------|-----|
| Overall | **0.8310** | 0.8721 | 0.0089 |
| Sharpness | **0.8345** | 0.8686 | 0.0175 |
| Color | **0.8216** | 0.8533 | 0.0103 |
| **Mean** | **0.8290** | - | 0.0122 |

**Train Loss**: 0.0067

These metrics suggest excellent performance on the validation set...

---

## Benchmark Results (CRITICAL FAILURE)

### Test Set Performance (1000 samples)

| Dimension | SRCC [95% CI] | PLCC [95% CI] | MAE | RMSE |
|-----------|---------------|---------------|-----|------|
| Overall | **-0.0089** [-0.0680, 0.0496] | -0.0226 [-0.0737, 0.0256] | 1.5334 | 1.6584 |
| Sharpness | **0.0009** [-0.0599, 0.0558] | 0.0159 [-0.0353, 0.0599] | 1.5596 | 1.6846 |
| Color | **0.0015** [-0.0617, 0.0565] | 0.0080 [-0.0464, 0.0556] | 1.5267 | 1.6500 |

**Interpretation**: Correlations indistinguishable from zero (random predictions).

### Inference Performance

- **Mean Inference**: 178ms/image (T4 GPU)
- **Model Load Time**: 45.1s
- **Success Rate**: 100.0% (1000/1000 samples)

---

## Root Cause Analysis

### Issue: Collapsed Output Distribution

**Findings from local inference testing:**

1. ✅ Model architecture is correct
2. ✅ All 326 checkpoint keys load without errors
3. ✅ Head weights (overall/sharpness/color) are present
4. ✅ Sigmoid outputs are in valid [0, 1] range
5. ⚠️ **CRITICAL**: Model predictions collapse to narrow range [1.2-2.0] instead of [1-5]

**Test Results:**

- Gray image (uniform quality): Overall=1.90, Sharpness=1.74, Color=2.04
- Random noise (poor quality): Overall=1.32, Sharpness=1.24, Color=1.44
- Expected range for diverse documents: 1.0-5.0 (full scale)
- Observed range: ~1.2-2.0 (25% of expected range)

### Hypotheses for Failure

1. **Overfitting to Validation Set**
   - Training SRCC 0.83 on 500 samples
   - Test SRCC 0.00 on 1000 samples
   - Suggests model memorized validation examples rather than learning generalizable quality features

2. **Collapsed Latent Space**
   - Sigmoid outputs cluster around 0.2-0.3 (before scaling)
   - Model learned to predict "moderate-low quality" for all inputs
   - Possible causes:
     - Loss function imbalance (MSE 0.6 may dominate, pulling predictions toward mean)
     - Insufficient backbone fine-tuning (LR 1e-6 too conservative)
     - Dropout 0.1 may be insufficient regularization

3. **Data Leakage or Distribution Shift**
   - Validation set may not represent test set distribution
   - Possible class imbalance between train/val/test splits

4. **Normalization Mismatch**
   - ImageNet normalization used: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
   - Document images may have different statistics
   - MANIQA pretrained on KonIQ-10k (natural scenes), not documents

---

## Recommended Fixes for v2.0.0

### High Priority

1. **Increase Backbone Learning Rate**
   - Current: 1e-6 (too conservative)
   - Proposed: 1e-5 to 1e-4
   - Rationale: Allow backbone to adapt to document-specific features

2. **Rebalance Loss Function**
   - Reduce MSE weight from 0.6 to 0.4
   - Increase Rank Loss weight from 0.2 to 0.3
   - Rationale: Emphasize relative ordering over absolute values

3. **Increase Regularization**
   - Increase head dropout from 0.1 to 0.3
   - Add L2 regularization on head weights
   - Rationale: Prevent overfitting to validation set

4. **Add Output Distribution Monitoring**
   - Log output histogram after each epoch
   - Add KL-divergence loss to match target distribution
   - Alert if sigmoid outputs cluster around single value

### Medium Priority

1. **Data Augmentation**
   - Add stronger augmentations: rotation, color jitter, blur
   - Mixup/CutMix for regularization
   - Rationale: Improve generalization

2. **Learning Rate Schedule**
   - Replace linear warmup with cosine annealing
   - Add learning rate restarts
   - Rationale: Escape local minima

3. **Validation Strategy**
   - K-fold cross-validation instead of single val split
   - Monitor test set metrics (read-only) to detect overfitting early
   - Rationale: Better estimate of generalization

### Low Priority

1. **Alternative Normalization**
   - Experiment with document-specific normalization statistics
   - Compute mean/std from DIQA-5000 training set
   - Rationale: Better match input distribution

2. **Longer Training**
   - Increase Phase 2 from 35 to 50 epochs
   - Add early stopping with patience=10
   - Rationale: Allow full convergence

3. **Ensemble Methods**
    - Train multiple models with different seeds
    - Average predictions
    - Rationale: Reduce variance

---

## Artifacts

### GCS Storage

**Location**: `gs://image_detection_b/models/diqa/track_a_iqa/maniqa/v1.0.0/`

- `model.pt` (519 MB) - PyTorch checkpoint with full state dict
- `config.json` - Training hyperparameters
- `metrics.json` - Final validation metrics

### Model Registry

**Status**: ❌ Not registered (failed model)

---

## Usage (NOT RECOMMENDED)

**WARNING**: This model should not be used in production due to failed test performance.

```python
import torch
import torch.nn as nn
import pyiqa
from einops import rearrange

class MANIQAMultiTask(nn.Module):
    # ... (see training code)

# Load model
model = MANIQAMultiTask()
checkpoint = torch.load("model.pt")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Inference
from torchvision import transforms
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

with torch.inference_mode():
    outputs = model(preprocess(image).unsqueeze(0))
    # outputs['overall'], outputs['sharpness'], outputs['color'] in [0, 1]
    # Scale to [1, 5]: output * 4.0 + 1.0
```

---

## Comparison with Baselines

| Model | SRCC Overall | SRCC Sharpness | SRCC Color | Inference (ms) |
|-------|-------------|----------------|-----------|----------------|
| **MANIQA Fine-tuned v1.0.0** | **-0.0089** | **0.0009** | **0.0015** | 178 |
| MANIQA Pretrained (PyIQA) | 0.5258 | 0.5592 | 0.5459 | ~150 |
| Random Baseline | ~0.00 | ~0.00 | ~0.00 | <1 |

**Finding**: Fine-tuning made the model WORSE than the pretrained baseline. This is a catastrophic regression.

---

## Ethical Considerations

This model should not be deployed due to:

1. **Zero predictive value**: Equivalent to random guessing
2. **Misleading outputs**: Produces seemingly valid [1-5] scores that don't correlate with quality
3. **Potential harm**: Could accept poor-quality documents or reject good ones randomly

---

## Conclusion

MANIQA-DIQA5000-Finetuned v1.0.0 represents a failed attempt at fine-tuning MANIQA for document quality assessment. While training validation metrics suggested strong performance (SRCC 0.83), this completely failed to generalize to the test set (SRCC ~0.00).

**Key Lessons**:

1. Validation metrics alone are insufficient - must monitor test set (read-only)
2. Output distribution collapse is a critical failure mode
3. Very low backbone learning rates (1e-6) may prevent adaptation
4. MSE-dominated loss functions may pull predictions toward mean

**Next Steps**: Implement recommended fixes in v2.0.0 training run.

---

**Model Card Version**: 1.0
**Last Updated**: 2025-12-19
**Contact**: Byron Williams <byronawilliams@gmail.com>
