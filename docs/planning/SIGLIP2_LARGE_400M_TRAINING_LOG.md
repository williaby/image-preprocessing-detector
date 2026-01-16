# SigLIP 2 Large (400M) Document IQA Training Log

> **Status**: Planning Phase
> **Created**: 2026-01-14
> **Target**: VQualA >= 0.92, SRCC >= 0.90
> **Dataset**: DIQA-5000 (Human MOS labels only)

---

## Executive Summary

This document tracks all training attempts, analysis, decisions, and results for the SigLIP 2 Large (400M) Document IQA model. The goal is to achieve VQualA >= 0.92 on DIQA-5000, surpassing the baseline 86M model's 0.886 result.

---

## 1. Background & Motivation

### 1.1 Previous Work: SigLIP 2 Base (86M)

**Training Completed**: 2026-01-14
**Model Card**: [siglip2_iqa_base_86m.md](../model-cards/siglip2_iqa_base_86m.md)

| Metric | Achieved | Target | Gap |
|--------|----------|--------|-----|
| VQualA | **0.886** | 0.92 | -3.4% |
| SRCC (overall) | **0.896** | 0.90 | ✅ Achieved |
| SRCC (sharpness) | **0.869** | 0.90 | -3.1% |
| SRCC (color) | **0.885** | 0.90 | -1.5% |

**Training Configuration**:

- Model: `google/siglip2-base-patch16-naflex`
- Epochs: ~25 (ended early due to lack of progress)
- Phase 1: 10 epochs head warmup (frozen backbone)
- Phase 2: 15 epochs full fine-tuning
- Scheduler: OneCycleLR
- Loss: GaussianNLLLoss + NormInNormLoss
- PCGrad: Disabled in Phase 2 due to OOM
- max_num_patches: 576
- GPU: A10 (24GB)

**Key Issues Identified**:

1. Early stopping triggered prematurely (~25 epochs)
2. OneCycleLR caused aggressive learning rate decay
3. PCGrad disabled in Phase 2 (OOM) - no gradient conflict mitigation
4. Sharpness SRCC (0.869) was the weakest dimension - may benefit from higher resolution

**Key Achievement**: The 86M model significantly outperforms all pretrained baselines:

- +32% VQualA over MANIQA (0.886 vs 0.563)
- +10% VQualA over DeQA-Doc-3Specialists (0.886 vs 0.786)

### 1.2 Why SigLIP 2 Large (400M)?

- **4.6× parameter scaling**: 400M vs 86M enables richer feature extraction
- **Better generalization**: Larger models transfer better to unseen document types
- **Industry evidence**: Research shows 0.92+ VQualA achievable with proper training
- **NaFlex architecture**: Native flexible resolution handles variable document sizes

---

## 2. Multi-Model Consensus Analysis

**Date**: 2026-01-14
**Models Consulted**: 5 frontier models with varying stances

| Model | Stance | Confidence | Key Recommendation |
|-------|--------|------------|-------------------|
| Gemini 2.5 Pro | For | 8/10 | CosineAnnealingLR, gradient accumulation, PCGrad |
| Gemini 3 Pro Preview | Neutral | 9/10 | Resolution (1296+ patches), ranking loss, LLRD |
| GPT-5.2 | Against | 7/10 | Fix NaFlex masking, exploit ori/res pairing |
| DeepSeek R1 | Neutral | 8/10 | 75 epochs, StepLR, multi-scale fusion |
| Grok 4 | For | 8/10 | Hybrid HyperIQA++ approach, ensemble fallback |

### 2.1 Resolution Analysis (Critical Finding)

**Source**: [siglip_research.md](../../tmp_cleanup/siglip_research.md) Section 4.2.1

The SigLIP 2 paper provides empirical data on resolution scaling (So400m NaFlex):

| Sequence Length | TextCaps R@1 | HierText R@1 | SciCap R@1 | Screen2Words R@1 |
|-----------------|--------------|--------------|------------|------------------|
| 64 patches | 5.6 | 10.3 | 11.8 | 12.1 |
| 256 patches | 9.2 | 15.7 | 29.8 | 17.5 |
| **576 patches** | 11.3 | **18.4** | 32.9 | 17.7 |
| 1024 patches | **11.7** | **18.4** | 32.6 | **17.8** |

**Key Insights**:

1. **Diminishing returns after 576 patches** - Performance plateaus; the gain from 576→1024 is minimal (~0.4 points)
2. **576 patches is the sweet spot** for most document tasks (HierText and Screen2Words plateau at 576)
3. **Higher resolution (1024) only helps for extremely dense documents** (full-page scans with small text)

**Updated Resolution Recommendation**: Target **576-784 patches** (not 1024-1296 as initially suggested by consensus). This balances:

- Memory efficiency (smaller batch size reduction)
- Training speed (fewer tokens per forward pass)
- Performance (captures most of the resolution benefit)

For dense documents requiring higher resolution, consider adaptive resolution during inference.

### 2.2 Unanimous Agreement (5/5 Models)

| Change | Current | Recommended | Rationale |
|--------|---------|-------------|-----------|
| LR Scheduler | OneCycleLR | CosineAnnealingLR or StepLR (γ=0.7) | OneCycleLR causes premature convergence |
| Gradient Accumulation | None | 4-8 steps | Required for 400M + high-res |
| Training Duration | 25 epochs | 60-80 epochs | Model needs more time |
| Resolution | 576 patches | **576-784 patches** | See Section 2.1 - diminishing returns above 576 |
| GPU | A10 (24GB) | A100 (40GB) | Memory requirements |
| Early Stopping | patience=10 | patience=15-20 | Prevent premature termination |

### 2.3 Strong Agreement (4-5/5 Models)

| Change | Implementation | Expected Impact |
|--------|---------------|-----------------|
| MarginRankingLoss | λ=0.3-0.5 alongside NormInNormLoss | Direct SRCC optimization |
| LLRD | 0.9 decay per layer | Prevents catastrophic forgetting |
| Attention Pooling | Learned token aggregation | Captures localized defects |
| Re-enable PCGrad | Phase 2 with accumulation | Multi-task conflict management |
| EMA/SWA | Last 10-20 epochs | 1-2% generalization boost |

### 2.4 Moderate Agreement (3/5 Models)

| Change | Implementation | Risk Level |
|--------|---------------|------------|
| Fix NaFlex masking | Pass pixel_attention_mask | Low |
| Exploit ori/res pairing | Pairwise ranking loss | Medium |
| KL divergence heads | Soft-label MOS modeling | Medium |
| Gradual unfreezing | 2-4 layers at a time | Low |
| Multi-scale fusion | From HyperIQA++ | High (complexity) |

### 2.5 Novel/Experimental Suggestions

| Source | Suggestion | Consideration |
|--------|------------|---------------|
| GPT-5.2 | Hybrid head (global + token-based) | Reduces task conflict |
| Grok 4 | Ensemble with DeQA-Doc | Fallback option |
| DeepSeek | 75 total epochs (15+60) | Conservative estimate |

---

## 3. Training Attempts

### 3.1 Attempt 1: [PLANNED]

**Date**: TBD
**Configuration**:

```python
# Planned configuration for first 400M attempt
config = {
    "model_name": "google/siglip2-so400m-patch16-naflex",  # So400m variant (400M)
    "max_num_patches": 784,  # Up from 576, but below 1024 (diminishing returns)
    "batch_size": 4,  # Larger batch possible with 784 patches
    "gradient_accumulation_steps": 4,  # Effective batch 16
    "total_epochs": 75,
    "phase1_epochs": 15,  # Warmup
    "phase2_epochs": 60,  # Fine-tuning
    "scheduler": "cosine",  # CosineAnnealingLR
    "learning_rate": 1e-4,
    "min_lr": 1e-6,
    "use_llrd": True,
    "llrd_decay": 0.9,
    "use_pcgrad": True,  # Re-enabled with accumulation
    "use_ranking_loss": True,
    "ranking_loss_weight": 0.3,
    "early_stopping_patience": 20,
    "gpu": "A100-40GB",
}
```

**Hypotheses to Test**:

1. CosineAnnealingLR prevents premature convergence
2. Higher resolution (1024 patches) improves sharpness SRCC
3. Ranking loss directly improves VQualA
4. LLRD preserves pretrained features better

**Results**: [PENDING]

---

## 4. Benchmark Context

### 4.1 DIQA-5000 Leaderboard (Current)

| Model | SRCC Overall | SRCC Sharpness | SRCC Color | VQualA |
|-------|--------------|----------------|------------|--------|
| **SigLIP 2 Base (86M)** | **0.896** | **0.869** | **0.885** | **0.886** |
| DeQA-Doc-3Specialists | 0.733 | 0.683 | 0.716 | 0.786 |
| DeQA-Score-Mix3-Prompted | 0.491 | 0.508 | 0.495 | 0.609 |
| MANIQA (pretrained) | 0.526 | 0.559 | 0.546 | 0.563 |
| PyIQA-liqe | 0.403 | 0.448 | 0.437 | 0.511 |
| PyIQA-hyperiqa | 0.236 | 0.303 | 0.239 | 0.327 |
| **SigLIP 2 Large (400M)** | TBD | TBD | TBD | TBD |

**Note**: SigLIP 2 Base (86M) is now the top performer on DIQA-5000, surpassing all pretrained and VLM-based models.

### 4.2 Target Performance

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| VQualA | 0.90 | 0.92 | 0.95 |
| SRCC Overall | 0.88 | 0.90 | 0.93 |
| SRCC Sharpness | 0.85 | 0.88 | 0.90 |
| SRCC Color | 0.85 | 0.88 | 0.90 |

---

## 5. Decision Log

### Decision 1: Use DIQA-5000 Human Labels Only

**Date**: 2026-01-14
**Decision**: Train on original DIQA-5000 human MOS labels, NOT Stage 2 pseudo-labels
**Rationale**:

- Stage 2 data has ~24% label noise from pseudo-labeling
- Human labels provide ground truth for IQA training
- Larger 400M model may generalize better than smaller model on clean data
**Alternatives Considered**:
- Use Stage 2 pseudo-labels (rejected - too noisy)
- Mix human + pseudo-labels (rejected - introduces bias)
- Rebuild Stage 2 with improved labeling (deferred)

### Decision 2: Target A100 GPU

**Date**: 2026-01-14
**Decision**: Use A100 (40GB) instead of A10 (24GB)
**Rationale**:

- 400M model + 1024 patches + gradient accumulation requires more VRAM
- A100 enables batch_size=2 with accumulation=8 (effective batch 16)
- Prevents OOM issues that plagued 86M training
**Alternatives Considered**:
- Continue with A10 (rejected - memory constraints)
- Use H100 (unnecessary - A100 sufficient)
- Multi-GPU training (deferred - adds complexity)

### Decision 3: Implement LLRD

**Date**: 2026-01-14
**Decision**: Use Layer-wise Learning Rate Decay (0.9 per layer) instead of flat 0.1× multiplier
**Rationale**:

- 400M model on 3.5k samples is prone to overfitting
- LLRD preserves pretrained features in early layers
- Industry standard for fine-tuning large VLMs
**Alternatives Considered**:
- Flat multiplier (current - insufficient for 400M scale)
- Freeze more layers (rejected - limits adaptation)
- Gradual unfreezing (may combine with LLRD)

---

## 6. Resource Estimates

| Resource | Specification | Cost Estimate |
|----------|--------------|---------------|
| GPU | A100 (40GB) | ~$2/hr on Modal |
| Training Time | ~36-48 hours | ~$72-96 |
| Storage | ~5GB model + checkpoints | Minimal |
| Inference | ~500ms/image | Production viable |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OOM during training | Medium | High | Gradient checkpointing, reduce batch |
| Overfitting on 3.5k samples | Medium | Medium | EMA/SWA, early stopping, augmentation |
| Not reaching 0.92 target | Medium | Medium | Ensemble fallback, architecture changes |
| Training instability | Low | Medium | Gradient clipping, warmup, stable scheduler |

---

## 8. Next Steps

1. [x] Create updated training script with consensus recommendations
2. [x] Implement LLRD, ranking loss, EMA (Tier 2)
3. [x] Implement gradient checkpointing and mixed precision (Tier 3)
4. [ ] Configure A100 GPU on Modal
5. [ ] Run first 400M training attempt
6. [ ] Benchmark and compare to 86M baseline
7. [ ] Iterate based on results

---

## 9. Training Script v2.0 Implementation

**Date**: 2026-01-14
**Script**: `modal/train_siglip2_iqa_v2.py`

### 9.1 Tier 1 Improvements (All Implemented)

| Improvement | v1.0 Value | v2.0 Value | Rationale |
|-------------|------------|------------|-----------|
| Scheduler | OneCycleLR | **CosineAnnealingLR** | Prevents premature convergence |
| Gradient Accumulation | None | **4-8 steps** | Enables larger effective batch |
| Total Epochs | 50 | **75** | Extended training for better convergence |
| Resolution | 576 patches | **784 patches** | Higher resolution (diminishing returns above) |
| Early Stopping | 15 epochs | **20 epochs** | More patience before stopping |

### 9.2 Tier 2 Improvements (All Implemented)

| Improvement | Implementation | Expected Impact |
|-------------|----------------|-----------------|
| LLRD | 0.9 decay per layer | Preserves pretrained features |
| MarginRankingLoss | λ=0.3 weight | Direct SRCC optimization |
| PCGrad Phase 2 | Re-enabled with accumulation | Multi-task conflict mitigation |
| EMA | 0.999 decay, starts epoch 55 | 1-2% generalization boost |

### 9.3 Tier 3 Improvements (All Implemented)

| Improvement | Implementation | Expected Impact |
|-------------|----------------|-----------------|
| Gradient Checkpointing | `model.backbone.gradient_checkpointing_enable()` | ~30% memory savings |
| Mixed Precision (BF16) | `torch.amp.autocast(device_type="cuda", dtype=bfloat16)` | 2x speed improvement |
| GradScaler (FP16 only) | `torch.amp.GradScaler("cuda")` | Prevents gradient underflow |

### 9.4 Usage Commands

```bash
# Quick test (2 epochs)
uv run modal run modal/train_siglip2_iqa_v2.py --test

# Train 86M model with all improvements
uv run modal run --detach modal/train_siglip2_iqa_v2.py

# Train 400M model
uv run modal run --detach modal/train_siglip2_iqa_v2.py --model so400m

# Custom configuration
uv run modal run --detach modal/train_siglip2_iqa_v2.py \
    --model so400m \
    --epochs 75 \
    --batch-size 4 \
    --accumulation 8 \
    --max-patches 784

# Monitor logs
modal app logs siglip2-iqa-training-v2 --follow
```

### 9.5 Key Architecture Changes

**LLRD Implementation**:

```python
# Layer groups from deepest (lowest LR) to shallowest (highest LR)
# Embeddings → Encoder Layers → Post LayerNorm → Heads
# Each layer gets llrd_decay^(layer_index) × base_lr
```

**MarginRankingLoss**:

```python
# Creates pairwise comparisons within batch
# Optimizes for correct relative ordering (direct SRCC alignment)
# Combined with GaussianNLLLoss: total_loss = gnll + λ × ranking_loss
```

**EMA**:

```python
# Shadow weights updated every gradient step after epoch 55
# shadow = (1 - decay) × current + decay × shadow
# Used for validation and final checkpoint
```

---

## Appendix A: Code References

- Training script v1: `modal/train_siglip2_iqa.py`
- **Training script v2**: `modal/train_siglip2_iqa_v2.py` (with Tier 1+2+3 improvements)
- HyperIQA++ reference: `modal/train_hyperiqa_plus_plus.py`
- Benchmark results: `docs/benchmarks/diqa5000_benchmark_results.csv`

## Appendix B: Research References

- SigLIP 2 Paper: Google Research (2024)
- NaFlex (Native Flexible Resolution): Google Research (2024)
- DeQA-Doc: VQualA 2025 Champion
- HyperIQA: CVPR 2020 IQA architecture
- PCGrad: NeurIPS 2020 multi-task learning

---

## Appendix C: Additional Research Findings (Tier 3 Analysis)

**Source**: `tmp_cleanup/siglip_training_research.md`

### C.1 Tier 3 Improvements

Based on detailed SigLIP 2 fine-tuning research, the following improvements have been analyzed:

| Improvement | Implementation | Risk | Expected Impact | Status |
|-------------|----------------|------|-----------------|--------|
| **Gradient Checkpointing** | `model.backbone.gradient_checkpointing_enable()` | Low | ~30% memory savings | ✅ **Implemented** |
| **Mixed Precision (BF16)** | `torch.amp.autocast(dtype=bfloat16)` | Low | 2x speed, same quality | ✅ **Implemented** |
| **Dynamic Loss Weighting** | Uncertainty-based or GradNorm | Medium | Better task balancing | Research needed |
| **Soft Label Distribution** | KL divergence with pseudo-variance | Medium | Captures MOS uncertainty | In DeQA-Doc |
| **Resolution Ensemble** | Multi-scale inference averaging | Low | +1-2% SRCC | Inference only |
| **Patch Packing** | Zero-padding elimination | Medium | GPU utilization | Complex |

**Tier 3 Implementation Details (v2.0)**:

- **Gradient Checkpointing**: Enabled by default (`--no-gradient-checkpointing` to disable)
  - Recomputes activations during backward pass instead of storing them
  - Reduces memory usage by ~30% at cost of ~20% training time
  - Critical for fitting 400M model + high resolution on A100

- **Mixed Precision (BF16/FP16)**: Enabled by default (`--no-mixed-precision` to disable, `--fp16` for FP16)
  - BF16 (default): Recommended for A100, no GradScaler needed
  - FP16 (fallback): Uses GradScaler to prevent gradient underflow on older GPUs
  - 2x speed improvement with minimal quality impact
  - Applied to forward pass, loss computation, and validation

### C.2 DeQA-Doc Soft Label Strategy

The research suggests treating quality prediction as **distribution learning** rather than point regression:

```python
# Current approach: Direct MOS regression
target = mos_score  # Single value

# DeQA-Doc approach: Soft probability distribution
# If variance unavailable, use pseudo-variance σ ≈ 0.2 × (max - min)
pseudo_sigma = 0.2 * (5.0 - 1.0)  # = 0.8 for 1-5 MOS scale
target_dist = gaussian_to_bins(mos_score, pseudo_sigma, bins=5)
# Loss: KL Divergence between predicted and target distributions
```

**Trade-off**: More complex loss function, but captures **uncertainty** in human MOS ratings.

### C.3 Resolution Ensemble (Inference Optimization)

The research suggests averaging predictions from multiple scales improves robustness:

```python
# Single-scale inference (current)
score = model.predict(image, max_patches=784)

# Resolution ensemble (proposed)
scores = [
    model.predict(image, max_patches=576),  # Lower res
    model.predict(image, max_patches=784),  # Standard
    model.predict(image, max_patches=1024), # Higher res
]
final_score = weighted_average(scores, weights=[0.2, 0.5, 0.3])
```

**Trade-off**: 3x inference cost, but provides multi-view consistency.

### C.4 Key Architectural Insights from Research

1. **LocCa Pre-training**: SigLIP 2 decoder-based pre-training forces spatial awareness - explains why NaFlex excels at localized quality defects

2. **Dense Feature Learning**: Self-distillation and masked prediction in SigLIP 2 pre-training creates robust local features for blur/sharpness detection

3. **So400m Sweet Spot**: 400M is optimal for document tasks - larger (1B) models show diminishing returns while adding latency

4. **Native Resolution Advantage**: Documents rely on high-frequency edges for text legibility - downscaling destroys features needed for blur/sharpness assessment

### C.5 Decision: Soft Labels vs Point Regression

**Status**: Under consideration for v3.0

**Arguments For Soft Labels**:

- Better captures inherent uncertainty in human MOS ratings
- KL Divergence provides richer gradient signal
- Aligns with DeQA-Doc championship approach

**Arguments Against**:

- More complex implementation
- May not be necessary if GaussianNLLLoss already models uncertainty
- Current approach (mu + sigma^2) already outputs uncertainty

**Recommendation**: Test soft labels on validation set before full training. If KL loss shows faster convergence or better SRCC, incorporate into v3.0.

---

*Last Updated: 2026-01-14 (v2.0 training script implemented, Tier 3 research analysis added)*
