# DeQA-Doc Analysis: Implications for DIQA-5000 Pseudo-Labeling System

**Date:** December 2025
**Status:** Strategic Analysis Document
**Context:** Evaluating the VQualA 2025 DIQA Challenge winning approach (DeQA-Doc) against our current multi-specialist ensemble design
**Prior Research:** [tmp_cleanup/diqa_research.md](../../tmp_cleanup/diqa_research.md) - Comprehensive DocIQ/DIQA-5000 technical analysis

---

## Executive Summary

**DeQA-Doc** ([arXiv:2507.12796](https://arxiv.org/abs/2507.12796)) won the VQualA 2025 DIQA Challenge with a **0.929 final score** (7.3% improvement over the best baseline RichIQA at 0.866). The approach fundamentally differs from our current design by treating quality assessment as **distribution regression** rather than point regression.

### Key Recommendation

**Do NOT abandon the multi-specialist ensemble architecture. Instead, integrate DeQA-Doc's soft-label training methodology into your existing framework.**

This hybrid approach combines:

- **Our architectural advantage**: Diverse model ensemble with CNN + VLM specialists
- **DeQA-Doc's training advantage**: Soft-label distribution regression with KL-divergence loss

---

## Critical Context from Prior Research

The [diqa_research.md](../../tmp_cleanup/diqa_research.md) document provides essential context that validates and extends this analysis:

### The Original DocIQ Architecture (Our Foundation)

The original DocIQ paper (arXiv:2509.17012) established the CNN baseline we're building upon:

| Component | Specification | Our Implementation |
|-----------|--------------|-------------------|
| **Backbone** | ResNet-50 (ImageNet pretrained) | ✅ DocIQ-Replica uses same |
| **Input Resolution** | 1600×1600 | ✅ Implemented |
| **Layout Fusion** | Dual-path with semantic masks | ✅ LayoutFusionDownsampler |
| **Output** | Score distributions (not scalars) | ⚠️ Currently regression |
| **Training** | 60 epochs, Adam, step-decay LR | ✅ Planned |
| **OCR Correlation** | SRCC 0.9086 with Character Accuracy | Target metric |

**Key Insight**: DocIQ already used **score distribution prediction** with KL-divergence—this is not new to DeQA-Doc. The difference is DeQA-Doc applies it to MLLMs rather than CNNs.

### The "Missing Variance" Problem

The prior research identifies a critical issue:

> "While DocIQ authors had access to the full score distributions (internal data), the public dataset only provided the Mean Opinion Score (MOS)."

This explains why DeQA-Doc developed **pseudo-variance soft labeling**—they had to reconstruct the distribution information that was stripped from the public DIQA-5000 release. Our system must also address this.

### The CV vs VL Paradigm Dichotomy

The research establishes a clear trade-off:

| Paradigm | Representative | Accuracy | Inference Cost | Layout Awareness |
|----------|---------------|----------|----------------|------------------|
| **CV (CNN)** | DocIQ | ~0.90 | Low (ResNet) | Explicit (masks) |
| **VL (MLLM)** | DeQA-Doc | 0.929 | High (7B+ params) | Implicit (learned) |

**Our hybrid approach bridges both paradigms** by keeping CNN specialists (efficient, explicit layout) while upgrading the training methodology (soft labels, KL-div).

### OCR Correlation Validation

The prior research confirms that **DocIQ score correlates with OCR accuracy** (SRCC 0.9086), not just perceptual quality. This validates our entire approach—we're building a functional metric, not just an aesthetic one.

### What We Were Missing (Now Clear)

Our original DIQA-5000_Pseudo_Labels_v2.md plan used **regression heads with MSE loss**. The prior research reveals this was a deviation from the original DocIQ methodology:

| Aspect | Original DocIQ | Our Current Plan | Corrected Plan |
|--------|---------------|------------------|----------------|
| **Output** | Distribution over 5 bins | Single scalar | Distribution over N bins |
| **Loss** | KL-Divergence | MSE + Rank + Focal ECE | KL-Divergence |
| **Labels** | Full rater distributions | MOS only | Reconstructed soft labels |

**The soft-label approach is not a DeQA-Doc innovation—it's returning to what DocIQ always intended.** DeQA-Doc simply showed it works even better on MLLMs and provided the pseudo-variance workaround for the public dataset.

---

## Technical Analysis

### DeQA-Doc Core Innovation

DeQA-Doc's key insight is that **quality scores are inherently probabilistic**, not deterministic:

```
Traditional Approach:          DeQA-Doc Approach:
─────────────────────         ──────────────────────
Image → Model → Score 4.2     Image → Model → Distribution
                               [excellent: 0.05, good: 0.60, fair: 0.30, poor: 0.05, bad: 0.0]
                               Expected Value: 4.2
                               Uncertainty: Built-in from distribution variance
```

#### Soft Label Construction

For a continuous MOS score μ with standard deviation σ:

```python
# Discretize into 5 quality bins: [excellent, good, fair, poor, bad] → [5, 4, 3, 2, 1]
# Two methods when variance is unavailable:

# Method 1: Pseudo Variance (recommended)
# σ_pseudo = 0.2 × (max_score - min_score)
# For 1-5 scale: σ_pseudo = 0.2 × 4 = 0.8

# Method 2: Linear Interpolation
# For μ=3.7, distribute between "fair"(3) and "good"(4):
# P(good) = 0.7, P(fair) = 0.3
```

#### Training Loss

```python
# Standard regression (our current approach)
loss = MSE(predicted_score, target_score)

# DeQA-Doc approach
loss = KL_Divergence(predicted_distribution, soft_label_distribution)
```

### Comparative Analysis

| Aspect | Our Current Approach | DeQA-Doc |
|--------|---------------------|----------|
| **Architecture** | 5-model ensemble (3 CNN + 2 VLM) | Single MLLM (5-fold CV) |
| **Output** | Point estimates + computed uncertainty | Probability distribution |
| **Loss** | MSE + Rank + Focal ECE | KL-Divergence |
| **Specialization** | Explicit (weighted loss) | None (generalist only) |
| **Layout Awareness** | DocIQ-Replica with semantic masks | None (pixel-only) |
| **Ensemble Diversity** | High (different architectures) | Low (same model, different folds) |
| **Challenge Score** | Unknown (not yet trained) | **0.929** (champion) |

---

## What DeQA-Doc Gets Right

### 1. Soft Labels Model Human Rating Ambiguity

Quality assessment is subjective. A score of 78 vs 79 is not meaningfully different. MSE loss forces false precision:

```
MSE: Penalizes prediction=79 when target=78 (even though both are "good")
KL-div: Matches distribution shapes, tolerating score ambiguity within quality bins
```

### 2. Richer Gradient Signal

KL-divergence provides gradients that capture distribution shape, not just point error:

```python
# MSE gradient: ∂L/∂θ ∝ (pred - target)
# KL-div gradient: ∂L/∂θ ∝ (P_pred / P_target - 1) across all bins
```

### 3. Built-in Uncertainty Quantification

The predicted distribution's variance is a natural uncertainty metric:

```python
# Current approach: Need separate uncertainty estimation
uncertainty = within_dimension_variance(model_predictions)

# DeQA approach: Uncertainty from distribution
uncertainty = variance(predicted_distribution)
```

### 4. Resolution Flexibility

DeQA-Doc handles high-resolution documents (1024×1024) by removing absolute position embeddings from the vision encoder.

---

## What Our Approach Gets Right (Don't Abandon)

### 1. Architectural Diversity

Our ensemble combines fundamentally different inductive biases:

| Model | Architecture | Inductive Bias |
|-------|-------------|----------------|
| MUSIQ | ViT-B/16 | Multi-scale texture analysis |
| QualiCLIP | CLIP ViT-B/32 | Vision-language semantic alignment |
| DocIQ-Replica | ResNet-50 + Layout Fusion | Document structure awareness |
| Qwen3-VL-8B | LLM + Vision | Semantic reasoning |
| InternVL3-8B | LLM + Vision | Cross-modal understanding |

DeQA-Doc's 5-fold ensemble is just 5 copies of the same model—**far less diverse**.

### 2. Explicit Specialization

Our specialist weighting creates domain experts:

```python
# MUSIQ Sharpness Specialist
loss_weights = [0.2, 0.6, 0.2]  # overall, sharpness, color

# QualiCLIP Color Specialist
loss_weights = [0.2, 0.2, 0.6]

# Generalist Anchors
loss_weights = [0.34, 0.33, 0.33]
```

DeQA-Doc has no specialization mechanism—all dimensions weighted equally.

### 3. Layout Fusion Downsampler

**This is NOT made obsolete by DeQA-Doc.** They are orthogonal:

- **Layout Fusion**: Input representation (semantic document structure)
- **Soft Labels**: Output representation (probabilistic quality)

Our DocIQ-Replica has explicit awareness of document regions (tables, headers, text). MLLMs process pixels without this structural prior.

### 4. Track Separation (Cost Efficiency)

Our two-track architecture optimizes compute:

| Track | GPU | Batch | Latency | Cost/Hour |
|-------|-----|-------|---------|-----------|
| Track A (CNNs) | T4/A10G | 32-64 | <50ms/img | ~$0.40-1.00 |
| Track B (VLMs) | A100-80GB | 1-4 | 200-400ms/img | ~$4.50 |

DeQA-Doc requires A100 for everything.

---

## The Hybrid Strategy: Integrating DeQA-Doc into Our System

### Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID DeQA-SPECIALIST ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Continuous Score (e.g., 3.7/5.0)                                       │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │          SOFT LABEL GENERATOR (NEW)                      │            │
│  │  Convert to distribution: [0.0, 0.1, 0.6, 0.3, 0.0]     │            │
│  └─────────────────────────────────────────────────────────┘            │
│         │                                                                │
│         ▼                                                                │
│  ┌───────────────────┐  ┌───────────────────┐                           │
│  │   Track A (CNN)   │  │   Track B (VLM)   │                           │
│  ├───────────────────┤  ├───────────────────┤                           │
│  │ DocIQ-Replica     │  │ Qwen3-VL-8B       │                           │
│  │ (w/ Layout Fusion)│  │                   │                           │
│  │ MUSIQ             │  │ InternVL3-8B      │                           │
│  │ QualiCLIP         │  │                   │                           │
│  └─────────┬─────────┘  └─────────┬─────────┘                           │
│            │                       │                                     │
│            ▼                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │         MODIFIED MULTI-TASK DISTRIBUTION HEAD            │            │
│  │  Output: N_BINS probabilities per dimension              │            │
│  │  Loss: KL-Divergence (weighted for specialists)          │            │
│  └─────────────────────────────────────────────────────────┘            │
│            │                                                             │
│            ▼                                                             │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │         UPGRADED HIERARCHICAL STACKER                    │            │
│  │  Input: 5 distributions × 3 dimensions × N_BINS          │            │
│  │  Output: Fused distribution + calibrated uncertainty     │            │
│  └─────────────────────────────────────────────────────────┘            │
│            │                                                             │
│            ▼                                                             │
│  Final Score = Expected Value of Fused Distribution                     │
│  Final Uncertainty = Variance of Fused Distribution                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow-by-Workflow Impact Assessment

### Workflow 1: DocIQ-Replica Training

**Current Design:**

- ResNet-50 + Layout Fusion Downsampler (1600×1600 → 400×400)
- MSE + Rank + Focal ECE loss
- 60 epochs (15 frozen + 45 full fine-tune)

**Recommended Changes:**

| Component | Current | Recommended |
|-----------|---------|-------------|
| Output Layer | `nn.Linear(hidden, 1)` × 3 | `nn.Linear(hidden, N_BINS)` × 3 |
| Activation | None (regression) | `nn.LogSoftmax(dim=-1)` |
| Loss | `MSE + Rank + Focal_ECE` | `KLDivLoss(reduction='batchmean')` |
| Target | Scalar 1-5 | Soft label vector [N_BINS] |

**Assessment:**

- Current approach: **Suboptimal** (not broken)
- Change complexity: **Low-Medium**
- Risk: Learning rate may need re-tuning
- Layout Fusion: **Keep unchanged** (orthogonal to loss function)

### Workflow 2: MUSIQ Fine-tuning

**Current Design:**

- PyIQA MUSIQ backbone → score encoder → MultiTaskHead
- Uses MUSIQ MOS score as feature (workaround for complex internals)
- Weighted loss [0.2, 0.6, 0.2] for sharpness specialization

**Recommended Changes:**

| Component | Current | Recommended |
|-----------|---------|-------------|
| MUSIQBackbone | Keep (pragmatic workaround) | Keep |
| MultiTaskHead output | `nn.Linear(256, 1)` × 3 | `nn.Linear(256, N_BINS)` × 3 |
| Loss | `MSE` | `KLDivLoss` with weights [0.2, 0.6, 0.2] |

**Assessment:**

- Current approach: **Suboptimal** (wrapper is pragmatic, not ideal)
- The wrapper architecture (using MUSIQ score as feature) is not the main problem
- The regression head is the issue—**fix the head, not the backbone**
- Change complexity: **Low**

### Workflow 3: QualiCLIP Fine-tuning

**Current Design:** Similar to MUSIQ

**Recommended Changes:** Same as MUSIQ workflow

**Assessment:**

- Apply identical changes to output heads and loss
- Maintain specialist weighting [0.2, 0.2, 0.6] for color

### Workflow 4: VLM Fine-tuning (Qwen3-VL-8B, InternVL3-8B)

**Current Design:**

- LoRA fine-tuning
- JSON output parsing for 3 scores
- Text generation for quality assessment

**Recommended Changes:**

| Component | Current | Recommended |
|-----------|---------|-------------|
| Output Format | JSON: `{"overall": 4.2, ...}` | Level tokens: `[level_8]` |
| Loss | Cross-entropy on full sequence | KL-div on level token logits only |
| Inference | Parse JSON string | Softmax over level token logits |

**Assessment:**

- Current approach: **Suboptimal and brittle** (JSON parsing errors, indirect task)
- Change complexity: **High** (requires loss masking, tokenizer changes)
- This is the highest-impact but highest-effort change
- **Consider phasing this change**: Start with CNN models, VLM later

### Workflow 5: HierarchicalStacker

**Current Design:**

- Input: 5 point estimates + within-dimension variances per dimension
- Output: Fused prediction + uncertainty

**Recommended Changes:**

| Component | Current | Recommended |
|-----------|---------|-------------|
| Input | `[5 × 3 scores] + [5 × 3 variances]` | `[5 × 3 × N_BINS distributions]` |
| Architecture | MLP with variance encoding | Distribution fusion network |
| Uncertainty | Computed from model disagreement | Intrinsic from fused distribution |

**New Stacker Architecture:**

```python
class DistributionStacker(nn.Module):
    """Fuses probability distributions from ensemble models."""

    def __init__(self, n_models: int = 5, n_dims: int = 3, n_bins: int = 10):
        super().__init__()
        # Input: concatenated distributions [batch, n_models * n_dims * n_bins]
        input_size = n_models * n_dims * n_bins

        self.encoder = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
        )

        # Per-dimension output heads producing fused distributions
        self.dim_heads = nn.ModuleDict({
            'overall': nn.Linear(128, n_bins),
            'sharpness': nn.Linear(128, n_bins),
            'color': nn.Linear(128, n_bins),
        })

    def forward(self, model_distributions: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        Args:
            model_distributions: [batch, n_models * n_dims * n_bins]

        Returns:
            Dict with fused distributions for each dimension.
            Use softmax + expected value for final scores.
        """
        encoded = self.encoder(model_distributions)
        return {
            dim: F.softmax(head(encoded), dim=-1)
            for dim, head in self.dim_heads.items()
        }
```

**Assessment:**

- Current approach: **Suboptimal** (loses information by collapsing to point estimates)
- Full distributions provide much richer fusion signal
- Change complexity: **Medium**

---

## Implementation Plan

### Phase 1: Foundation (Recommended First)

1. **Implement `SoftLabelGenerator`**
   - Convert continuous scores to Gaussian-discretized soft labels
   - Support pseudo-variance and linear interpolation methods
   - Unit tests for edge cases (scores at bin boundaries)

2. **Implement `MultiTaskDistributionHead`**
   - Replace regression heads with N_BINS classification
   - LogSoftmax activation
   - Compatible with existing backbone wrappers

### Phase 2: CNN Models (Lower Risk)

1. **Upgrade DocIQ-Replica**
   - Swap heads and loss function
   - Validate training convergence
   - Compare SRCC/PLCC with regression baseline

2. **Upgrade MUSIQ and QualiCLIP**
   - Apply same changes
   - Maintain specialist loss weighting

### Phase 3: Stacker (Depends on Phase 2)

1. **Implement `DistributionStacker`**
   - New architecture for distribution fusion
   - Train on Phase 2 model outputs

### Phase 4: VLM Models (Highest Complexity)

1. **Upgrade Qwen3-VL-8B and InternVL3-8B**
   - Add level tokens to tokenizer
   - Implement loss masking
   - Modify inference pipeline

### Phase 5: Validation

1. **End-to-end benchmark on DIQA-5000**
   - Compare hybrid system vs original regression system
   - Ablation studies on each component

---

## Validated Training Parameters (From Prior Research)

The prior research provides exact hyperparameters from the original DocIQ paper that should guide our implementation:

| Hyperparameter | DocIQ Value | Rationale |
|----------------|-------------|-----------|
| **Optimizer** | Adam | Adaptive learning rate for high-dimensional image data |
| **Initial LR** | 2×10⁻⁴ | Conservative for fine-tuning pretrained backbone |
| **LR Schedule** | Step decay | Decay every 10 epochs by factor 0.6 |
| **Total Epochs** | 60 | Convergence without overfitting on 5,000 images |
| **Batch Size** | 20 | Memory-constrained by 1600×1600 inputs |
| **Hardware** | NVIDIA A10 | High-memory for large input tensors |
| **Data Split** | 80/20 train/test | 4,000 training, 1,000 validation |

### Training Schedule Detail

```text
Epoch 1-10:   LR = 2.0×10⁻⁴
Epoch 11-20:  LR = 1.2×10⁻⁴  (×0.6)
Epoch 21-30:  LR = 7.2×10⁻⁵  (×0.6)
Epoch 31-40:  LR = 4.3×10⁻⁵  (×0.6)
Epoch 41-50:  LR = 2.6×10⁻⁵  (×0.6)
Epoch 51-60:  LR = 1.6×10⁻⁵  (×0.6)
```

These parameters should be used as the baseline for our DocIQ-Replica training, with adjustments for the soft-label KL-divergence loss.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hyperparameter re-tuning needed | High | Medium | Start with DeQA-Doc's settings |
| VLM tokenizer modification breaks model | Medium | High | Test on small subset first |
| Soft labels don't improve CNNs | Low | Medium | Keep regression fallback |
| Increased training complexity | High | Low | Good documentation, modular design |
| Distribution stacker overfits | Medium | Medium | Start with simple weighted average |

---

## Conclusion

**DeQA-Doc represents a significant advancement in the training methodology for IQA, not the architecture.** The key insight—treating quality as a probability distribution—should be integrated into our existing multi-specialist ensemble.

### What to Keep

- 5-model diverse ensemble architecture
- Specialist loss weighting
- Layout Fusion Downsampler for DocIQ-Replica
- Two-track (CNN/VLM) cost optimization

### What to Change

- Replace regression heads with distribution classification heads
- Replace MSE loss with KL-divergence loss
- Update soft label construction in data pipeline
- Upgrade stacker to fuse distributions

### Expected Outcome

A hybrid system that combines our architectural diversity advantage with DeQA-Doc's superior training methodology, potentially exceeding the 0.929 challenge benchmark.

---

## References

1. **DeQA-Doc Paper**: [arXiv:2507.12796](https://arxiv.org/abs/2507.12796)
2. **DeQA-Score Paper**: [arXiv:2501.11561](https://arxiv.org/abs/2501.11561) (CVPR 2025)
3. **VQualA 2025 Challenge**: [ICCVW 2025 Proceedings](https://openaccess.thecvf.com/content/ICCV2025W/VQualA/papers/Huang_VQualA_2025_Document_Image_Quality_Assessment_Challenge_ICCVW_2025_paper.pdf)
4. **DeQA-Doc Repository**: [GitHub](https://github.com/Junjie-Gao19/DeQA-Doc)
5. **DeQA-Score Repository**: [GitHub](https://github.com/zhiyuanyou/DeQA-Score)
6. **Our Pseudo-Labeling Spec**: [DIQA-5000_Pseudo_Labels_v2.md](./DIQA-5000_Pseudo_Labels_v2.md)

---

*Document Version 1.0 — December 2025*
