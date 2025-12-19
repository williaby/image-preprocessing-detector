# Document Image Quality Assessment System

## Technical Implementation Handoff

**Version:** 1.1
**Date:** December 2025
**Target:** Production RAG Pipeline Document Preprocessing

---

## 1. Executive Summary

This document specifies the implementation of a Document Image Quality Assessment (IQA) system designed for production RAG pipelines. The system evaluates document images across three quality dimensions using a heterogeneous 5-model ensemble with multi-task training, specialist checkpoint selection, 8-bit quantization, and an uncertainty-aware hierarchical stacking architecture.

### Target Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| Expected Calibration Error (ECE) | < 0.08 | Critical |
| SRCC (vs human ratings) | > 0.92 | High |
| SRCC 95% CI Width | < 0.03 | High |
| Inference Latency (per image) | < 150ms | Medium |
| GPU Memory (inference) | < 8GB | Medium |

### Benchmark Metrics (DIQA5000)

For each quality dimension, track the following metrics:

| Metric | Description | Target |
|--------|-------------|--------|
| DIQA5000_SRCC | Spearman rank correlation | > 0.92 |
| DIQA5000_PLCC | Pearson linear correlation | > 0.90 |
| DIQA5000_SRCC_CI_Lower | 95% CI lower bound | Report |
| DIQA5000_SRCC_CI_Upper | 95% CI upper bound | Report |
| DIQA5000_ECE | Expected calibration error | < 0.08 |

**Note:** Confidence intervals should be computed via bootstrap resampling (1000 iterations) to ensure statistical validity of performance claims.

### Quality Dimensions

The system predicts scores (1-5 scale) for three quality dimensions with distinct perceptual mechanisms:

| Dimension | Primary Signals | Best Model Type |
|-----------|-----------------|-----------------|
| **Sharpness** | High-frequency content, edge gradients, blur kernels | CNNs with early-layer features (DocIQ, MUSIQ) |
| **Color Fidelity** | Color histograms, white balance, saturation | Models with color-aware pretraining (QualiCLIP) |
| **Overall** | Holistic assessment, readability, semantic quality | VLMs with semantic understanding (Qwen, DeepSeek) |

These dimensions aren't perfectly correlated—a document can be sharp but color-shifted, or have good color but be blurry. This is why specialized models outperform generalists that must compromise across all three.

---

## 2. Ensemble Architecture

### 2.1 Model Roster

The ensemble combines five models with complementary strengths: one large generalist anchor, two sharpness specialists, one color specialist, and one overall/readability specialist.

| Model | Role | Training Dimensions | Inference Output | Parameters |
|-------|------|---------------------|------------------|------------|
| **Qwen2.5-VL-72B** | Generalist Anchor | All 3 | All 3 | ~72B |
| **DocIQ** | Sharpness Specialist | All 3 | All 3 | ~25M |
| **MUSIQ** | Sharpness Specialist | All 3 | All 3 | ~27M |
| **QualiCLIP** | Color Specialist | All 3 | All 3 | ~150M |
| **DeepSeek-OCR** | Overall Specialist | All 3 | All 3 | ~1B |

### 2.2 Specialty Matrix

Each model is trained on all three dimensions but optimized for checkpoint selection on its specialty:

| Model | Overall | Sharpness | Color | Selection Criterion |
|-------|---------|-----------|-------|---------------------|
| Qwen2.5-VL-72B | Primary ★ | Primary ★ | Primary ★ | Mean ECE (all dims) |
| DocIQ | Secondary | **Primary ★** | Secondary | ECE_sharpness |
| MUSIQ | Secondary | **Primary ★** | Secondary | ECE_sharpness |
| QualiCLIP | Secondary | Secondary | **Primary ★** | ECE_color |
| DeepSeek-OCR | **Primary ★** | Secondary | Secondary | ECE_overall |

### 2.3 Why Specialization Works: Feature Representation

Different dimensions require different learned features, and specialists can optimize their feature hierarchy:

**Sharpness Detection Benefits From:**

- Preserving high-frequency information through the network
- Early layer features (edges, textures, gradients)
- Laplacian/gradient-like learned filters
- Blur kernel detection capabilities

**Color Fidelity Detection Benefits From:**

- Color histogram awareness
- White balance understanding
- Chromatic aberration detection
- Saturation/hue consistency measurement

**Overall Quality Detection Benefits From:**

- Semantic layout understanding
- Text readability assessment
- Document structure recognition
- Holistic degradation assessment

A generalist model must compromise between these competing feature requirements. Specialists can devote full representational capacity to their target dimension.

### 2.4 Why Every Model Predicts All Dimensions

Training specialists on all dimensions (not just their specialty) provides critical advantages:

1. **Multi-Task Regularization:** Training on all dimensions prevents overfitting to quirks of one dimension. Other dimensions act as implicit regularization.

2. **Correlated Supervision:** The dimensions aren't independent—a blurry document often has degraded overall quality. Multi-task learning exploits these correlations.

3. **Ensemble Flexibility:** Every model can contribute to every dimension with different weights. A sharpness specialist's color prediction still provides useful signal.

4. **Implicit Confidence Signals:** Off-specialty predictions correlate with model confidence—when a sharpness specialist's color and sharpness predictions diverge, it signals uncertainty.

### 2.5 Multi-Task Head Architecture

Each base model receives a shared multi-task prediction head:

```python
class MultiTaskHead(nn.Module):
    def __init__(self, in_features, hidden=256):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(in_features, hidden),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        self.heads = nn.ModuleDict({
            'overall': nn.Linear(hidden, 1),
            'sharpness': nn.Linear(hidden, 1),
            'color': nn.Linear(hidden, 1)
        })

    def forward(self, features):
        shared = self.shared(features)
        return {dim: head(shared).squeeze(-1) for dim, head in self.heads.items()}
```

---

## 3. Multi-Task Training with Specialist Selection

### 3.1 Core Training Strategy

```
Train on:  All 3 dimensions (shared backbone, 3 heads)
Select on: Specialty dimension ECE (with overall ECE as tiebreaker)
Output:    All 3 dimensions (but specialty is optimized)
```

### 3.2 Loss Weighting by Model

Training uses weighted multi-task loss where the specialty dimension receives higher weight:

| Model | Overall Weight | Sharpness Weight | Color Weight | Strategy |
|-------|----------------|------------------|--------------|----------|
| Qwen2.5-VL-72B | 0.34 | 0.33 | 0.33 | Equal (generalist) |
| DocIQ | 0.2 | **0.6** | 0.2 | Moderate specialist |
| MUSIQ | 0.2 | **0.6** | 0.2 | Moderate specialist |
| QualiCLIP | 0.2 | 0.2 | **0.6** | Moderate specialist |
| DeepSeek-OCR | **0.6** | 0.2 | 0.2 | Moderate specialist |

### 3.3 Specialist Trainer Implementation

```python
class SpecialistTrainer:
    def __init__(self, model, specialty='sharpness', specialty_weight=0.6):
        self.model = model
        self.specialty = specialty
        self.specialty_weight = specialty_weight

        # Weights for loss (specialty gets more)
        other_weight = (1 - specialty_weight) / 2
        self.loss_weights = {
            'overall': other_weight if specialty != 'overall' else specialty_weight,
            'sharpness': other_weight if specialty != 'sharpness' else specialty_weight,
            'color': other_weight if specialty != 'color' else specialty_weight,
        }

    def compute_loss(self, predictions, targets):
        total_loss = 0
        for dim in ['overall', 'sharpness', 'color']:
            dim_loss = self.dimension_loss(predictions[dim], targets[dim])
            total_loss += self.loss_weights[dim] * dim_loss
        return total_loss

    def dimension_loss(self, pred, target):
        """Combined MSE + rank loss + focal calibration for better ECE."""
        mse = F.mse_loss(pred, target)
        rank = self.differentiable_rank_loss(pred, target)

        # Focal calibration loss - penalizes confident wrong predictions more
        focal_ece = self.focal_calibration_loss(pred, target)

        # Specialists can weight calibration more heavily
        if self.specialty:
            return 0.6 * mse + 0.2 * rank + 0.2 * focal_ece
        else:
            return 0.7 * mse + 0.3 * rank

    def focal_calibration_loss(self, pred, target, gamma=2.0):
        """
        Focal loss variant for calibration - harder examples get more weight.
        Helps specialists achieve better ECE on their target dimension.
        """
        error = (pred - target).abs()
        confidence = 1.0 - error / 4.0  # Normalize to [0, 1] for 1-5 scale
        focal_weight = (1 - confidence) ** gamma
        return (focal_weight * error ** 2).mean()

    def select_best_checkpoint(self, checkpoints):
        # Sort by specialty ECE
        sorted_ckpts = sorted(checkpoints, key=lambda x: x[f'ece_{self.specialty}'])

        # Get candidates within threshold of best
        best_specialty_ece = sorted_ckpts[0][f'ece_{self.specialty}']
        candidates = [c for c in sorted_ckpts
                     if c[f'ece_{self.specialty}'] < best_specialty_ece + 0.01]

        # Tiebreak by mean ECE across all dimensions
        if len(candidates) > 1:
            return min(candidates, key=lambda x: x['ece_mean'])
        return candidates[0]
```

### 3.4 Checkpoint Selection Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│         CHECKPOINT SELECTION FOR SPECIALIST MODELS          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Is ECE_specialty within 0.01 of best?                     │
│       │                                                     │
│       ├── NO  → Select lowest ECE_specialty                │
│       │                                                     │
│       └── YES → Is ECE_mean within 0.005 of best?          │
│                     │                                       │
│                     ├── NO  → Select lowest ECE_mean       │
│                     │                                       │
│                     └── YES → Select highest SRCC_specialty│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Training Protocol

1. **Freeze backbone:** Load pretrained weights and freeze all backbone layers
2. **Train heads only:** Train multi-task heads for 10 epochs with lr=1e-3
3. **Unfreeze backbone:** Unfreeze backbone, continue with lr=1e-5 for 20 epochs
4. **Track all metrics:** Log ECE and SRCC for all three dimensions every epoch
5. **Save checkpoints:** Store model weights with full metric suite
6. **Select specialist checkpoint:** Use selection algorithm based on specialty ECE

### 3.6 Dynamic Loss Weighting (Advanced Option)

For improved feature learning, start with equal weights and gradually specialize:

```python
def get_loss_weights(epoch, total_epochs, specialty='sharpness'):
    # Start with equal weights, gradually increase specialty
    progress = epoch / total_epochs
    specialty_weight = 0.4 + 0.4 * progress  # 0.4 -> 0.8
    other_weight = (1 - specialty_weight) / 2

    weights = {'overall': other_weight, 'sharpness': other_weight, 'color': other_weight}
    weights[specialty] = specialty_weight
    return weights
```

### 3.7 Expected Training Outcomes

#### SRCC Improvement (Specialists vs Generalists)

| Approach | SRCC Sharpness | SRCC Color | SRCC Overall | Average |
|----------|----------------|------------|--------------|---------|
| 5 Generalists | 0.94 | 0.93 | 0.95 | 0.940 |
| **5 Multi-Task Specialists** | **0.96** | **0.95** | **0.96** | **0.957** |
| Improvement | +2% | +2% | +1% | +1.7% |

#### ECE Improvement (Specialists vs Generalists)

| Approach | ECE Sharpness | ECE Color | ECE Overall |
|----------|---------------|-----------|-------------|
| Generalists | 0.07 | 0.08 | 0.06 |
| **Specialists** | **0.04** | **0.05** | **0.05** |
| Improvement | -43% | -38% | -17% |

**Specialists should get you well under the ECE < 0.08 target across all dimensions.**

#### Multi-Task vs Pure Specialist Tradeoff

| Approach | Specialty ECE | Other Dims ECE | Flexibility |
|----------|---------------|----------------|-------------|
| Pure specialist (1 dim only) | 0.04 | N/A | Low |
| **Multi-task + specialist selection** | **0.045** | **0.06-0.07** | **High** |
| Generalist | 0.07 | 0.07 | Medium |

The ~0.005 ECE tradeoff on specialty is worth the flexibility gains: predictions on all dimensions, better generalization, and tiebreaker options.

---

## 4. 8-Bit Quantization Strategy

### 4.1 Quantization Methods by Model

| Model | Method | Calibration | Expected Degradation |
|-------|--------|-------------|---------------------|
| Qwen2.5-VL-72B | GPTQ / AWQ | 128 samples | < 1.5% SRCC |
| DocIQ | PTQ (torch.quantization) | 1000 doc images | < 0.5% SRCC |
| MUSIQ | PTQ (torch.quantization) | 1000 doc images | < 0.5% SRCC |
| QualiCLIP | PTQ (torch.quantization) | 1000 doc images | < 0.8% SRCC |
| DeepSeek-OCR | bitsandbytes LLM.int8() | Dynamic (per-token) | < 1.0% SRCC |

### 4.2 Implementation Steps

1. **Prepare calibration dataset:** Collect 1000 representative document images spanning all quality levels and document types
2. **Run calibration pass:** Forward pass through each model to collect activation statistics
3. **Apply quantization:** Convert weights and activations to INT8 with computed scale factors
4. **Validate quality:** Compare FP32 vs INT8 predictions on held-out validation set
5. **Export models:** Save quantized state dicts for production deployment

### 4.3 Memory Budget

| Model | FP32 Size | INT8 Size | Reduction |
|-------|-----------|-----------|-----------|
| Qwen2.5-VL-72B | ~144 GB | ~36 GB | 4× |
| DocIQ | ~100 MB | ~25 MB | 4× |
| MUSIQ | ~108 MB | ~27 MB | 4× |
| QualiCLIP | ~600 MB | ~150 MB | 4× |
| DeepSeek-OCR | ~4 GB | ~1.3 GB | ~3× |
| **Total** | **~149 GB** | **~37.5 GB** | **~4×** |

**Note:** Qwen2.5-VL-72B requires multi-GPU deployment or aggressive quantization (4-bit GPTQ) for single-GPU inference. Consider using Qwen2.5-VL-7B as an alternative for resource-constrained deployments.

### 4.4 Qwen2.5-VL Quantization Options

| Variant | VRAM Required | Quality Impact | Recommendation |
|---------|---------------|----------------|----------------|
| 72B FP16 | ~144 GB | Baseline | Multi-node only |
| 72B INT8 | ~72 GB | < 1% SRCC loss | A100 80GB cluster |
| 72B INT4 (GPTQ) | ~36 GB | < 2% SRCC loss | 2× A100 40GB |
| **7B INT8** | **~7 GB** | **< 3% vs 72B** | **Single GPU** |

---

## 5. Uncertainty-Aware Hierarchical Stacker

### 5.1 Architecture Overview

The stacking head combines predictions from all five models using a hierarchical architecture that leverages specialty knowledge and treats off-specialty predictions as uncertainty signals.

**Input:** 15 values (5 models × 3 dimensions)
**Output:** 3 calibrated scores + 3 uncertainty estimates

### 5.2 Stacker Implementation

```python
class HierarchicalStacker(nn.Module):
    """
    Uses specialist predictions as primary signal and
    off-specialty predictions as uncertainty indicators.
    """
    def __init__(self, n_models=5, hidden=32):
        super().__init__()

        # Which models specialize in which dimension (by index)
        # 0=Qwen, 1=DocIQ, 2=MUSIQ, 3=QualiCLIP, 4=DeepSeek
        self.specialties = {
            'overall': [0, 4],      # Qwen (generalist), DeepSeek-OCR
            'sharpness': [0, 1, 2], # Qwen (generalist), DocIQ, MUSIQ
            'color': [0, 3],        # Qwen (generalist), QualiCLIP
        }

        # Specialty encoder (high weight predictions)
        self.specialty_encoder = nn.Linear(3, hidden)  # max 3 specialists

        # Non-specialty encoder (uncertainty signals)
        self.uncertainty_encoder = nn.Linear(n_models * 2, hidden)

        # Fusion network
        self.fusion = nn.Sequential(
            nn.Linear(hidden * 2, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2)  # [prediction, log_variance]
        )

    def forward_dimension(self, all_preds, target_dim):
        """
        Process one dimension using specialists + uncertainty signals.

        Args:
            all_preds: [batch, n_models, 3] tensor
            target_dim: 'overall', 'sharpness', or 'color'
        """
        specialist_indices = self.specialties[target_dim]
        dim_idx = {'overall': 0, 'sharpness': 1, 'color': 2}[target_dim]

        # Primary signal: specialist predictions for this dimension
        specialty_preds = all_preds[:, specialist_indices, dim_idx]
        specialty_preds = F.pad(specialty_preds, (0, 3 - len(specialist_indices)))
        specialty_feat = self.specialty_encoder(specialty_preds)

        # Uncertainty signal: off-specialty predictions from all models
        other_dims = [d for d in [0, 1, 2] if d != dim_idx]
        uncertainty_signals = all_preds[:, :, other_dims].flatten(1)
        uncertainty_feat = self.uncertainty_encoder(uncertainty_signals)

        # Fuse specialty + uncertainty
        combined = torch.cat([specialty_feat, uncertainty_feat], dim=-1)
        output = self.fusion(combined)

        pred = output[:, 0]
        var = F.softplus(output[:, 1]) + 1e-6  # Ensure positive variance

        return pred, var

    def forward(self, all_preds):
        """
        Args:
            all_preds: [batch, n_models, 3] or dict of {dim: [batch, n_models]}
        """
        results = {}
        for dim in ['overall', 'sharpness', 'color']:
            pred, var = self.forward_dimension(all_preds, dim)
            results[dim] = {'pred': pred, 'var': var}
        return results
```

### 5.3 Key Insight: Off-Specialty as Confidence

The magic of multi-task specialists + stacking:

```
DocIQ (sharpness specialist) outputs:
  - sharpness: 4.2  (trust this)
  - color: 3.8      (uncertainty signal)
  - overall: 3.9    (uncertainty signal)

QualiCLIP (color specialist) outputs:
  - sharpness: 3.5  (uncertainty signal)
  - color: 4.1      (trust this)
  - overall: 3.7    (uncertainty signal)

Stacking head learns:
  "DocIQ's off-specialty predictions correlate with its confidence.
   When DocIQ_color ≈ DocIQ_sharpness, DocIQ is confident.
   When they diverge, DocIQ is uncertain about the image."
```

This information is **lost** with pure specialists that only predict one dimension.

### 5.4 Calibration Loss

The stacker is trained with a combined loss optimizing both accuracy and calibration:

```python
def stacker_loss(pred, target, pred_var):
    """
    Heteroscedastic loss with calibration regularization.
    """
    # Negative log-likelihood (encourages uncertainty matching)
    nll = 0.5 * (torch.log(pred_var) + (pred - target)**2 / pred_var)

    # Calibration: predicted std should match actual error
    pred_std = torch.sqrt(pred_var)
    actual_error = (pred - target).abs()
    calibration = F.mse_loss(pred_std, actual_error)

    return nll.mean() + 0.5 * calibration
```

### 5.5 Temperature Scaling

Post-training temperature scaling further improves ECE:

```python
class TemperatureScaler(nn.Module):
    """Per-dimension temperature scaling for final calibration."""
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(3))  # Per-dimension

    def forward(self, pred, var):
        # Scale variance by learned temperature
        return pred, var * self.temperature.unsqueeze(0)

# Optimize temperature on validation set
def calibrate_temperature(scaler, stacker, val_loader, epochs=20):
    optimizer = torch.optim.LBFGS([scaler.temperature], lr=0.01)

    for _ in range(epochs):
        def closure():
            optimizer.zero_grad()
            total_loss = 0
            for batch in val_loader:
                results = stacker(batch['model_preds'])
                for dim in ['overall', 'sharpness', 'color']:
                    pred, var = scaler(results[dim]['pred'], results[dim]['var'])
                    loss = stacker_loss(pred, batch['targets'][dim], var)
                    total_loss += loss
            total_loss.backward()
            return total_loss
        optimizer.step(closure)
```

### 5.6 Alternative: Dimension-Aware Stacker

For cases where cross-dimension attention is beneficial:

```python
class DimensionAwareStacker(nn.Module):
    """
    Process each dimension separately, then apply cross-dimension attention.
    """
    def __init__(self, n_models=5, hidden=32):
        super().__init__()

        # Per-dimension processing (sees all models for that dim)
        self.dim_encoders = nn.ModuleDict({
            'overall': nn.Linear(n_models, hidden),
            'sharpness': nn.Linear(n_models, hidden),
            'color': nn.Linear(n_models, hidden),
        })

        # Cross-dimension attention
        self.cross_attn = nn.MultiheadAttention(hidden, num_heads=4, batch_first=True)

        # Final prediction heads (output mean + variance)
        self.heads = nn.ModuleDict({
            'overall': nn.Linear(hidden, 2),
            'sharpness': nn.Linear(hidden, 2),
            'color': nn.Linear(hidden, 2),
        })

    def forward(self, all_preds):
        # all_preds: [batch, n_models, 3]

        # Encode each dimension
        dim_feats = []
        for i, dim in enumerate(['overall', 'sharpness', 'color']):
            feat = self.dim_encoders[dim](all_preds[:, :, i])  # [batch, hidden]
            dim_feats.append(feat)

        # Stack for attention: [batch, 3, hidden]
        dim_feats = torch.stack(dim_feats, dim=1)

        # Cross-dimension attention (dims attend to each other)
        attn_out, _ = self.cross_attn(dim_feats, dim_feats, dim_feats)

        # Final predictions
        results = {}
        for i, dim in enumerate(['overall', 'sharpness', 'color']):
            output = self.heads[dim](attn_out[:, i])
            results[dim] = {
                'pred': output[:, 0],
                'var': F.softplus(output[:, 1]) + 1e-6
            }
        return results
```

### 5.7 Stacker Selection Guide

| Scenario | Recommended Stacker | Rationale |
|----------|---------------------|-----------|
| Standard deployment | HierarchicalStacker | Best ECE, uses specialty knowledge |
| Highly correlated dimensions | DimensionAwareStacker | Cross-attention captures correlations |
| Minimal compute budget | Simple weighted average | Skip stacker, use fixed weights |
| Maximum flexibility | Both + ensemble | Train both, ensemble their outputs |

---

## 6. Ensemble Weighting

### 6.1 Per-Dimension Weight Matrix

Every model contributes to every dimension, but specialists receive higher weight on their specialty:

```python
ENSEMBLE_WEIGHTS = {
    'overall': {
        'qwen': 0.35,        # Generalist anchor
        'dociq': 0.10,       # Off-specialty
        'musiq': 0.10,       # Off-specialty
        'qualiclip': 0.10,   # Off-specialty
        'deepseek': 0.35,    # Overall specialist
    },
    'sharpness': {
        'qwen': 0.20,        # Generalist anchor
        'dociq': 0.30,       # Sharpness specialist
        'musiq': 0.30,       # Sharpness specialist
        'qualiclip': 0.10,   # Off-specialty
        'deepseek': 0.10,    # Off-specialty
    },
    'color': {
        'qwen': 0.30,        # Generalist anchor
        'dociq': 0.10,       # Off-specialty
        'musiq': 0.10,       # Off-specialty
        'qualiclip': 0.40,   # Color specialist
        'deepseek': 0.10,    # Off-specialty
    },
}
```

### 6.2 Learned vs Fixed Weights

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| Fixed weights | Simple, interpretable | May be suboptimal | Baseline, debugging |
| Learned stacker | Optimal combination | Requires training data | Production |
| Per-image adaptive | Handles distribution shift | Complex, slower | High-stakes applications |

---

## 7. Deployment Configuration

### 7.1 Inference Pipeline

1. **Load image:** Read document image, convert to RGB
2. **Preprocess:** Apply model-specific transforms (resize, normalize)
3. **Parallel inference:** Run all 5 models concurrently (or sequentially for memory)
4. **Collect predictions:** Gather [5 × 3] prediction matrix
5. **Stacker forward:** Pass through hierarchical stacker
6. **Temperature scale:** Apply learned temperature scaling
7. **Return:** Dict with scores and uncertainties for all dimensions

### 7.2 Output Format

```python
{
    'overall': {'score': 4.2, 'uncertainty': 0.15},
    'sharpness': {'score': 3.8, 'uncertainty': 0.22},
    'color': {'score': 4.5, 'uncertainty': 0.11},
    'metadata': {
        'model_predictions': {
            'qwen': {'overall': 4.1, 'sharpness': 3.9, 'color': 4.4},
            'dociq': {'overall': 4.0, 'sharpness': 3.7, 'color': 4.3},
            'musiq': {'overall': 4.2, 'sharpness': 3.8, 'color': 4.5},
            'qualiclip': {'overall': 4.3, 'sharpness': 3.6, 'color': 4.6},
            'deepseek': {'overall': 4.2, 'sharpness': 3.9, 'color': 4.4},
        },
        'inference_time_ms': 142
    }
}
```

### 7.3 Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU | 24GB VRAM (RTX 4090) | 80GB VRAM (A100) |
| CPU | 8 cores | 16 cores |
| RAM | 32 GB | 64 GB |
| Storage | 50 GB (models) | 100 GB (models + cache) |

**Note:** Requirements assume Qwen2.5-VL-7B variant. For 72B, multiply GPU VRAM by ~5× or use multi-GPU.

---

## 8. Validation & Testing

### 8.1 Test Datasets

- **Document-IQA benchmark:** Primary validation set with human annotations
- **Internal production sample:** 500 real documents from RAG pipeline
- **Synthetic degradation set:** Clean documents with controlled blur/noise/compression

### 8.2 Validation Checklist

- [ ] Per-dimension SRCC > 0.90 on DIQA5000 benchmark
- [ ] SRCC 95% confidence interval width < 0.03
- [ ] Overall ECE < 0.08 across all dimensions
- [ ] Inference latency < 150ms on target hardware
- [ ] Memory usage within budget during inference
- [ ] Uncertainty correlates with actual prediction error (r > 0.6)
- [ ] Quantized models within 1.5% SRCC of FP32 baselines
- [ ] Specialist checkpoints outperform generalist on specialty dimension
- [ ] Bootstrap CI validates statistical significance of improvements

### 8.3 Confidence Interval Computation

```python
def compute_srcc_with_ci(predictions, targets, n_bootstrap=1000, ci=0.95):
    """
    Compute SRCC with bootstrap confidence intervals.

    Returns:
        srcc: Point estimate
        ci_lower: Lower bound of CI
        ci_upper: Upper bound of CI
    """
    from scipy.stats import spearmanr
    import numpy as np

    # Point estimate
    srcc, _ = spearmanr(predictions, targets)

    # Bootstrap resampling
    n = len(predictions)
    bootstrap_srccs = []

    for _ in range(n_bootstrap):
        indices = np.random.choice(n, size=n, replace=True)
        boot_pred = predictions[indices]
        boot_target = targets[indices]
        boot_srcc, _ = spearmanr(boot_pred, boot_target)
        bootstrap_srccs.append(boot_srcc)

    # Compute percentile CI
    alpha = 1 - ci
    ci_lower = np.percentile(bootstrap_srccs, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_srccs, 100 * (1 - alpha / 2))

    return {
        'DIQA5000_SRCC': srcc,
        'DIQA5000_SRCC_CI_Lower': ci_lower,
        'DIQA5000_SRCC_CI_Upper': ci_upper,
        'DIQA5000_SRCC_CI_Width': ci_upper - ci_lower,
    }
```

### 8.4 Expected Performance

| Metric | Overall | Sharpness | Color |
|--------|---------|-----------|-------|
| SRCC | 0.94-0.96 | 0.92-0.94 | 0.91-0.93 |
| SRCC CI Lower (95%) | 0.93-0.95 | 0.91-0.93 | 0.90-0.92 |
| SRCC CI Upper (95%) | 0.95-0.97 | 0.93-0.95 | 0.92-0.94 |
| PLCC | 0.93-0.95 | 0.91-0.93 | 0.90-0.92 |
| ECE | 0.04-0.06 | 0.04-0.06 | 0.05-0.07 |

### 8.5 Per-Model Performance Targets

| Model | Specialty SRCC | Specialty ECE | Notes |
|-------|----------------|---------------|-------|
| Qwen2.5-VL | > 0.93 (all dims) | < 0.07 (all) | Anchor/generalist |
| DocIQ | > 0.94 (sharpness) | < 0.05 (sharpness) | Sharpness specialist |
| MUSIQ | > 0.94 (sharpness) | < 0.05 (sharpness) | Sharpness specialist |
| QualiCLIP | > 0.93 (color) | < 0.05 (color) | Color specialist |
| DeepSeek-OCR | > 0.94 (overall) | < 0.05 (overall) | Overall specialist |

---

## Appendix A: Complete Model Configuration

```python
MODEL_CONFIG = {
    'qwen': {
        'name': 'Qwen2.5-VL-72B',
        'hf_path': 'Qwen/Qwen2.5-VL-72B-Instruct',
        'role': 'generalist_anchor',
        'input_size': 'dynamic',
        'quantization': 'gptq_int4',  # Or int8 for multi-GPU
        'specialty': None,  # Generalist
        'loss_weights': {'overall': 0.34, 'sharpness': 0.33, 'color': 0.33},
        'checkpoint_selection': 'ece_mean',
    },
    'dociq': {
        'name': 'DocIQ',
        'backbone': 'resnet50',
        'role': 'sharpness_specialist',
        'input_size': 384,
        'quantization': 'ptq_int8',
        'specialty': 'sharpness',
        'loss_weights': {'overall': 0.2, 'sharpness': 0.6, 'color': 0.2},
        'checkpoint_selection': 'ece_sharpness',
    },
    'musiq': {
        'name': 'MUSIQ',
        'backbone': 'vit_b_16',
        'role': 'sharpness_specialist',
        'input_size': 'variable',
        'quantization': 'ptq_int8',
        'specialty': 'sharpness',
        'loss_weights': {'overall': 0.2, 'sharpness': 0.6, 'color': 0.2},
        'checkpoint_selection': 'ece_sharpness',
    },
    'qualiclip': {
        'name': 'QualiCLIP',
        'backbone': 'clip_vit_b_32',
        'role': 'color_specialist',
        'input_size': 224,
        'quantization': 'ptq_int8',
        'specialty': 'color',
        'loss_weights': {'overall': 0.2, 'sharpness': 0.2, 'color': 0.6},
        'checkpoint_selection': 'ece_color',
    },
    'deepseek': {
        'name': 'DeepSeek-OCR',
        'hf_path': 'deepseek-ai/deepseek-vl-1b',
        'role': 'overall_specialist',
        'input_size': 1024,
        'quantization': 'llm_int8',
        'specialty': 'overall',
        'loss_weights': {'overall': 0.6, 'sharpness': 0.2, 'color': 0.2},
        'checkpoint_selection': 'ece_overall',
    },
}
```

## Appendix B: Stacker Training Configuration

```python
STACKER_CONFIG = {
    'architecture': 'HierarchicalStacker',
    'hidden_dim': 32,
    'n_models': 5,
    'n_dimensions': 3,

    # Training
    'learning_rate': 1e-3,
    'weight_decay': 1e-4,
    'epochs': 100,
    'batch_size': 256,
    'calibration_weight': 0.5,
    'early_stopping_patience': 10,

    # Temperature scaling
    'temp_scaling_epochs': 20,
    'temp_scaling_lr': 0.01,

    # Specialist indices (model order: qwen, dociq, musiq, qualiclip, deepseek)
    'specialties': {
        'overall': [0, 4],
        'sharpness': [0, 1, 2],
        'color': [0, 3],
    },
}
```

## Appendix C: Checkpoint Logging Schema

```python
CHECKPOINT_SCHEMA = {
    'epoch': int,
    'model_name': str,
    'weights_path': str,

    # Per-dimension SRCC with confidence intervals
    'srcc_overall': float,
    'srcc_overall_ci_lower': float,
    'srcc_overall_ci_upper': float,
    'srcc_sharpness': float,
    'srcc_sharpness_ci_lower': float,
    'srcc_sharpness_ci_upper': float,
    'srcc_color': float,
    'srcc_color_ci_lower': float,
    'srcc_color_ci_upper': float,
    'srcc_mean': float,

    # Per-dimension PLCC
    'plcc_overall': float,
    'plcc_sharpness': float,
    'plcc_color': float,

    # Per-dimension ECE (critical for selection)
    'ece_overall': float,
    'ece_sharpness': float,
    'ece_color': float,
    'ece_mean': float,

    # Training metadata
    'loss_weights': dict,
    'learning_rate': float,
    'timestamp': str,
}

# Full DIQA5000 benchmark result format
BENCHMARK_RESULT_SCHEMA = {
    'model_name': str,
    'dimension': str,  # 'overall', 'sharpness', 'color'
    'DIQA5000_SRCC': float,
    'DIQA5000_PLCC': float,
    'DIQA5000_SRCC_CI_Lower': float,
    'DIQA5000_SRCC_CI_Upper': float,
    'DIQA5000_ECE': float,
    'n_samples': int,
    'timestamp': str,
}
```

---

*Document Version 1.1 — December 2025*
