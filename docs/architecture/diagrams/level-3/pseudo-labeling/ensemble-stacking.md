---
owner: docs-team
purpose: Ensemble stacking module documentation for pseudo-labeling
schema_type: common
status: active
tags:
  - architecture
  - level-3
  - pseudo-labeling
  - ensemble
title: "Ensemble Stacking - 5-Model Architecture"
---

# Ensemble Stacking - 5-Model Architecture

**Parent**: [Level 3 Pseudo-Labeling Index](index.md)
**Primary Source**: `modal/generate_pseudo_labels.py` (1,042 LOC)

## Overview

The pseudo-labeling pipeline uses a 5-model ensemble split across two inference tracks to generate quality scores for unlabeled document images. The ensemble stacker combines predictions using variance-weighted voting with temperature-scaled calibration.

## Model Architecture

### Track A: Classical IQA Models

| Model | Purpose | Output Dimensions | Latency |
|-------|---------|-------------------|---------|
| MUSIQ | Sharpness, naturalness | 2 scores (0-1) | ~150ms |
| QualiCLIP | Color fidelity, aesthetics | 2 scores (0-1) | ~200ms |
| DocIQ-Replica | Document-specific overall quality | 1 score (0-1) | ~150ms |

Track A models run in parallel on Modal A10 GPU. Combined latency ~500ms per image (parallel execution).

### Track B: Vision-Language Models

| Model | Purpose | Output | Latency |
|-------|---------|--------|---------|
| Qwen3-VL-8B | Structured quality assessment | JSON with 6 quality dimensions | ~2s |
| InternVL3-8B | Document understanding + quality | JSON with 6 quality dimensions | ~2s |

Track B models produce structured JSON output that is parsed into normalized score vectors.

## Hierarchical Stacking Algorithm

### Step 1: Per-Dimension Variance Computation

For each quality dimension `d` (blur, noise, contrast, compression, skew, overall):

```
variance_d = var([model_1_score_d, model_2_score_d, ..., model_5_score_d])
weight_d_i = 1 / (variance_d_i + epsilon)  # epsilon = 1e-6
```

Models with lower variance (higher agreement) receive higher weight.

### Step 2: Weighted Voting

```
final_score_d = sum(weight_d_i * score_d_i) / sum(weight_d_i)
```

### Step 3: Outlier Detection

If any model's prediction deviates by more than 2 standard deviations from the ensemble mean for a given dimension, that model's weight is halved for that dimension.

## Temperature Scaling Calibration

After ensemble stacking, temperature scaling is applied to ensure calibrated confidence estimates:

```
calibrated_score = sigmoid(logit(raw_score) / T)
```

Where `T` is a learned temperature parameter per quality dimension.

### Calibration Validation

- **Metric**: Expected Calibration Error (ECE)
- **Threshold**: ECE < 0.1 (required for acceptance)
- **Bins**: 15 equal-width bins
- **Validation set**: 10% held-out from benchmark datasets

If ECE exceeds 0.1, temperature parameters are re-tuned using Platt scaling on the validation set.

## Confidence Filtering

### Agreement Score

```
agreement = 1 - (max_score - min_score) / (max_score + epsilon)
```

Where `max_score` and `min_score` are the highest and lowest predictions across all 5 models for a given sample.

### Routing Logic

| Agreement | Action | Destination |
|-----------|--------|-------------|
| > 0.8 | Accept | Pseudo-label parquet output |
| 0.5 - 0.8 | Flag | Included with low-confidence marker |
| < 0.5 | Reject | Dead-letter queue (manual review or discard) |

### Dead-Letter Queue

Low-agreement samples are written to a separate partition for:

1. Manual review by domain experts
2. Active learning candidate selection
3. Diagnostic analysis (which models disagree and why)

## Checkpoint Selection

After pseudo-labels are generated, model checkpoints are evaluated using:

```
checkpoint_score = 0.6 * SRCC + 0.3 * (1 - ECE) + 0.1 * coverage_ratio
```

The checkpoint with the highest score is registered in the model registry for downstream use by WS2 (training) and WS6 (arena validation).

## Source Files

| File | LOC | Role |
|------|-----|------|
| `modal/generate_pseudo_labels.py` | 1,042 | Ensemble orchestration, stacking, filtering |
| `modal/shared/metrics_utils.py` | 223 | PLCC, SRCC, ECE computation |
| `modal/teacher_inference.py` | 419 | VLM inference wrapper |

---

*Last Updated: February 2026*
