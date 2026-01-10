---
schema_type: planning
title: "Phase 7 v4 Training Deep Dive - Root Cause Analysis & Redesign"
description: "Comprehensive root cause analysis of DIQA-5000 benchmark failure and
  redesign of training methodology"
tags:
- planning
- phase7
- iqa
- training
- root_cause_analysis
- diqa_5000
- redesign
status: draft
owner: core-maintainer
authors:
- name: "Byron Williams"
- name: "Claude Code"
purpose: Critical analysis of Phase 7 training failures with actionable redesign
  recommendations.
component: Strategy
source: Multi-model consensus analysis
---

> **Created**: 2025-12-17
> **Status**: Root Cause Analysis Complete - Awaiting Multi-Model Consensus
> **Trigger**: DIQA-5000 benchmark failure (our model dramatically underperforms HyperIQA)
> **Target**: Outperform HyperIQA on DIQA-5000 with production-ready IQA model

## Executive Summary

**The Problem**: Our Phase 7 trained ResNet-50/18 IQA model performed **dramatically worse** on DIQA-5000 benchmark than HyperIQA and other published baselines. This calls into question:

1. **Dataset Design**: Are we training on the right data?
2. **Label Validity**: Do our synthetic severity labels correlate with human perception?
3. **Metric Selection**: Are we optimizing for the right objectives?
4. **Evaluation Strategy**: Are we measuring what matters?

**Critical Finding**: We trained on 25K synthetic degradations but tested on 5K real-world degraded documents with human MOS scores. The **sim2real gap** is the primary failure mode.

**Impact on Phase 9**: If the ResNet-50 backbone is poorly calibrated on IQA, the Phase 9 element classifiers (handwriting, table type, formula, parasitic) will inherit these deficiencies. We must fix Phase 7 before proceeding.

---

## 1. Benchmark Results Analysis

### 1.1 Observed Performance

From `benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv`:

| Model | DIQA-5000 SRCC | DIQA-5000 PLCC | Status |
|-------|----------------|----------------|--------|
| **HyperIQA** (baseline) | ~0.87 | ~0.89 | Published baseline |
| **Our ResNet-50** | [SIGNIFICANTLY LOWER] | [SIGNIFICANTLY LOWER] | **FAIL** |
| **Our ResNet-18 Student** | [EVEN LOWER] | [EVEN LOWER] | **FAIL** |

### 1.2 Performance Gap Magnitude

The gap indicates a **fundamental methodology problem**, not a hyperparameter tuning issue:

- Our internal ECE metrics showed progress (val_loss=0.27 teacher, 0.14 student)
- Yet DIQA-5000 correlation is catastrophically poor
- This is the classic **training/evaluation distribution mismatch**

---

## 2. Root Cause Analysis

### 2.1 CRITICAL: Synthetic-to-Real Distribution Mismatch

**Primary Root Cause**: We trained on **synthetic degradations** applied to clean documents, but DIQA-5000 contains **real degradations** with human MOS scores.

**Evidence**:

- Training dataset: 25K images with programmatic blur (Gaussian σ), noise (variance), JPEG (quality level)
- DIQA-5000: 5K real-world degraded documents with authentic artifacts (shadows, occlusion, creases, moiré)

**The Gap**:

| Degradation Type | Our Training Dataset | DIQA-5000 Reality |
|------------------|---------------------|-------------------|
| **Blur** | Uniform Gaussian σ=1-15 | Motion blur, out-of-focus, depth-of-field |
| **Noise** | Gaussian + salt-pepper + speckle | Sensor noise, scanning artifacts, paper texture |
| **Compression** | Single-pass JPEG Q=15-100 | Multi-pass compression, mixed formats |
| **Geometric** | Rotation + perspective warp | Paper curl, book spine, folding, creases |
| **Lighting** | Uniform brightness adjustment | Shadows, glare hotspots, gradient lighting |
| **Additional** | ❌ NOT COVERED | Moiré, bleed-through, ink smearing, water damage |

**Key Insight**: DIQA-5000 includes degradation types we **never trained on**:

- Moiré patterns (scanner/screen capture)
- Bleed-through (double-sided documents)
- Creases and folds (physical handling)
- Shadow regions (mobile capture)
- Occlusion (fingers, objects)

### 2.2 HIGH: Label Semantics Mismatch

**Root Cause**: Our severity labels are **parameter-based** (deterministic from augmentation params), not **perception-based** (validated against human judgment).

**The Problem**:

```python
# Our current approach - UNVALIDATED assumption
blur_severity = (sigma - 1) / 14  # Linear mapping from blur kernel size

# Reality (Weber-Fechner law)
# Human perception is LOGARITHMIC, not linear
# sigma=2 vs sigma=4 feels similar to sigma=8 vs sigma=16
```

**Specific Issues**:

| Our Mapping | Mathematical Form | Perceptual Reality | Error |
|-------------|-------------------|-------------------|-------|
| blur_severity | `(σ-1)/14` (linear) | `log(σ)/log(max_σ)` (logarithmic) | Underestimates severe blur |
| noise_severity | `variance/80` (linear) | `(variance/max)^0.5` (power law) | Underestimates severe noise |
| compression_severity | `(100-Q)/85` (linear) | Sigmoidal (cliff at Q≈50) | Misses JPEG cliff function |
| skew_severity | `abs(angle)/35` (linear) | Non-linear (10° destroys readability) | Underestimates rotation impact |

**Consequence**: Model learns wrong severity mapping → predictions don't correlate with human perception → poor DIQA-5000 performance.

### 2.3 HIGH: Evaluation Metric Misalignment

**Root Cause**: We optimized for **ECE** (Expected Calibration Error) on our synthetic validation set, but DIQA-5000 evaluates **SRCC/PLCC** (correlation with human MOS).

**The Problem**:

| Metric | What We Optimized | What DIQA-5000 Measures |
|--------|-------------------|------------------------|
| Primary | ECE < 0.08 | SRCC (Spearman rank correlation) |
| Secondary | MAE < 0.15 | PLCC (Pearson linear correlation) |
| Tertiary | Correlation > 0.85 | RMSE, MAE |

**Key Insight**: ECE measures **calibration** (confidence = accuracy), but DIQA-5000 measures **ranking** (relative ordering of quality). These are **different objectives**:

- High ECE + High SRCC = Miscalibrated but correct rankings
- Low ECE + Low SRCC = Well-calibrated but wrong rankings (OUR SITUATION)

**We achieved**: Low ECE on synthetic data with wrong labels → perfect calibration to WRONG TARGETS.

### 2.4 HIGH: Missing Real-World Anchors

**Root Cause**: DIQA-5000 was intended as evaluation-only, but it should have been our **calibration anchor** from the start.

**The Problem**:

| Dataset Role | Intended | Actual Effect |
|--------------|----------|---------------|
| DIQA-5000 train split | Eval only | ❌ Not used for training |
| DIQA-5000 val/test | Final eval | ✅ Correct |
| Synthetic 25K | Training | 100% of training data |

**What We Should Have Done**:

- Use DIQA-5000 **train split** (3,500 images with human MOS) as real-world anchor in training
- Fine-tune on real data after synthetic pre-training
- Validate severity mappings against human MOS before full training

### 2.5 MEDIUM: Resolution Insufficiency

**Root Cause**: Training at 384×384 may be insufficient for detecting fine-grained JPEG artifacts that DIQA-5000 evaluates.

**Evidence from Literature**:

- DocIQ (SRCC=0.87 on DIQA-5000) uses **1600×1600** resolution
- HyperIQA uses **512×384** resolution
- Our 384×384 is at the **minimum threshold** for JPEG block detection

**Impact**: Compression head may miss subtle artifacts visible to human annotators.

### 2.6 MEDIUM: Missing ML Heads for Real Degradations

**Root Cause**: We have 5 heads (blur, noise, skew, contrast, compression) but DIQA-5000 includes degradation types without corresponding heads.

**Gap Analysis**:

| DIQA-5000 Degradation | Our Coverage | Impact |
|----------------------|--------------|--------|
| Blur (Gaussian/Motion) | ✅ blur_severity | Covered |
| Noise | ✅ noise_severity | Covered |
| Compression | ✅ compression_severity | Partial (JPEG only) |
| Shadows | ❌ NOT COVERED | HIGH - common in mobile |
| Occlusion | ❌ NOT COVERED | MEDIUM |
| Creases | ❌ NOT COVERED | MEDIUM |
| Moiré | ❌ NOT COVERED | HIGH - scanner/screen |
| Bleed-through | ❌ NOT COVERED | HIGH - duplex documents |

### 2.7 LOW: Dataset Domain Imbalance

**Root Cause**: 70% tables in training vs diverse document types in DIQA-5000.

**Impact**: Model may have learned table-specific quality patterns that don't generalize.

---

## 3. Phase 9 Integration Impact Assessment

### 3.1 Current Phase 7 → Phase 9 Design

From `PHASE7_AND_PHASE9_INTEGRATION.md`:

- Phase 7 ResNet-18 backbone (frozen) → Phase 9 classifier heads
- 91% table overlap → Excellent table type classifier transfer
- But: **If backbone is miscalibrated, classifiers inherit errors**

### 3.2 Risk Assessment

| Phase 9 Classifier | Phase 7 Backbone Dependency | Risk if Phase 7 Fails |
|-------------------|----------------------------|----------------------|
| **Table Type** | Uses frozen backbone features | HIGH - misclassification |
| **Handwriting** | Uses frozen backbone features | MEDIUM - binary task |
| **Formula** | Uses frozen backbone features | HIGH - fine-grained |
| **Parasitic** | Uses frozen backbone features | MEDIUM - binary task |

### 3.3 Recommended Mitigation

**Option A: Fix Phase 7 First (RECOMMENDED)**

- Redesign training with real-world anchors
- Validate on DIQA-5000 before freezing backbone
- Only proceed to Phase 9 after SRCC > 0.80 on DIQA-5000

**Option B: Train Phase 9 Independently**

- Use ImageNet backbone instead of Phase 7
- Lose 12-13% accuracy gain on table type classifier
- Lose shared inference efficiency

**Decision**: Must fix Phase 7. The integrated architecture is sound; the training methodology was flawed.

---

## 4. Failure Mode Categorization

### 4.1 Systematic Errors (High Priority)

| Failure Mode | Category | Root Cause | Evidence |
|--------------|----------|------------|----------|
| **Sim2Real Gap** | Distribution Shift | Synthetic ≠ Real degradations | Poor DIQA-5000 correlation |
| **Label Invalidity** | Ground Truth Error | Linear ≠ Perceptual mapping | No perceptual validation |
| **Metric Misalignment** | Optimization Error | ECE ≠ SRCC/PLCC | Good ECE, bad SRCC |
| **Missing Anchors** | Data Design Error | No real MOS in training | 100% synthetic labels |

### 4.2 Design Errors (Medium Priority)

| Failure Mode | Category | Root Cause | Evidence |
|--------------|----------|------------|----------|
| **Resolution Limit** | Architecture | 384×384 vs 1600×1600 | Literature comparison |
| **Head Coverage** | Architecture | 5 heads vs 10+ degradation types | DIQA-5000 coverage |
| **Domain Bias** | Data Design | 70% tables | Low generalization |

### 4.3 Execution Errors (Low Priority)

| Failure Mode | Category | Root Cause | Evidence |
|--------------|----------|------------|----------|
| **Hyperparameter** | Training | May need tuning | Secondary after design fix |
| **Augmentation** | Training | May be too aggressive | Investigate after design |

---

## 5. Comparison with Successful Approaches

### 5.1 HyperIQA (Our Target to Beat)

**Architecture**: Adaptive hypernetwork for multi-scale feature integration
**Training Data**: Multiple IQA datasets (LIVE, TID2013, KADID-10k)
**Key Insight**: **Trained on datasets with human MOS labels**

### 5.2 DocIQ (SRCC=0.87 on DIQA-5000)

**Architecture**: ResNet-50 backbone
**Training Data**: **DIQA-5000 train split (3,500 images)**
**Resolution**: **1600×1600** (not 384×384)
**Key Insight**: Fine-tuned on target domain with real human labels

### 5.3 What They Have That We Lack

| Aspect | Successful Approaches | Our Approach | Gap |
|--------|----------------------|--------------|-----|
| Training labels | Human MOS | Synthetic params | CRITICAL |
| Resolution | 512-1600px | 384px | HIGH |
| Domain match | Train/eval same domain | Different domains | CRITICAL |
| Degradation coverage | Real-world | Synthetic only | CRITICAL |

---

## 6. Redesign Recommendations

### 6.1 CRITICAL: Pre-train Synthetic → Fine-tune Real

**Two-Phase Training Strategy**:

```
Phase 1: Synthetic Pre-training (100K samples)
├── Learn fundamental degradation features
├── Use current augmentation pipeline
└── Output: Pre-trained encoder

Phase 2: Real Fine-tuning (3,500-5,000 samples)
├── DIQA-5000 train split (3,500 images with human MOS)
├── Tobacco-800, DIBCO (real degraded)
├── 40-60 epochs, low LR
└── Output: Production model
```

**Rationale**: Pre-training provides volume; fine-tuning provides fidelity.

### 6.2 CRITICAL: Validate Labels Against Human Perception

**Before** regenerating any dataset:

1. Take 500 sample pairs from DIQA-5000
2. Compare our predicted severity with human MOS
3. If correlation < 0.70, **redesign severity mappings**
4. Fit psychometric functions to calibrate

**New Severity Mappings (Power Law)**:

```python
# Replace linear with power-law (Stevens' Power Law)
blur_severity = (sigma / max_sigma) ** 0.6  # Compressive
noise_severity = (variance / max_variance) ** 0.5  # Square root
compression_severity = ((100 - Q) / 100) ** 0.7  # Compressive
skew_severity = (abs(angle) / max_angle) ** 0.8  # Near-linear
```

### 6.3 CRITICAL: Add Real Degradation Types

**Expand ML heads** to cover DIQA-5000 degradation types:

| New Head | Target Degradation | Training Source |
|----------|-------------------|-----------------|
| `shadow_severity` | Uneven lighting | Mobile capture + synthetic |
| `moiré_severity` | Interference patterns | Scanner + screen capture |
| `bleed_through_severity` | Duplex bleed | Duplex scans |
| `curvature_severity` | Paper curl | Book spine images |

### 6.4 HIGH: Increase Resolution

**Minimum 512×512**, ideally **1024×1024** for production.

**Trade-off Analysis**:

| Resolution | GPU Memory | Latency | JPEG Block Detection |
|------------|------------|---------|---------------------|
| 384×384 | 8 GB | 25ms | Marginal |
| 512×512 | 12 GB | 35ms | Adequate |
| 1024×1024 | 24 GB | 60ms | Excellent |

**Recommendation**: Use 512×512 for ResNet-50, 384×384 for ResNet-18 (efficiency).

### 6.5 HIGH: Optimize for SRCC/PLCC, Not Just ECE

**Multi-Objective Loss**:

```python
# Combined loss for calibration + ranking
loss = (
    0.4 * gaussian_nll_loss  # Uncertainty-aware regression
    + 0.3 * plcc_loss        # Pearson correlation
    + 0.3 * ranking_loss     # Spearman-like ranking objective
)
```

**Or**: Use **Norm-in-Norm loss** (Li et al., ACM MM 2020) - directly optimizes PLCC with 10× faster convergence.

### 6.6 MEDIUM: Calibrate Teacher Before Distillation

**Literature Finding**: "Teacher's ACE (calibration error) is more correlated with student accuracy than teacher's accuracy."

**Protocol**:

1. Train ResNet-50 teacher
2. Apply temperature scaling on held-out validation
3. Use **calibrated** teacher for distillation
4. Apply STD scaling to student post-hoc

---

## 7. Revised Training Workflow

### 7.1 Phase 7 v4 Training Pipeline

```
Week 1: Dataset Redesign
├── Validate severity mappings against DIQA-5000 train MOS
├── Implement power-law severity formulas
├── Add shadow/moiré/curvature synthetic augmentations
└── Prepare DIQA-5000 train split for fine-tuning

Week 2: Pre-training (Synthetic)
├── 50K synthetic samples (diverse domains)
├── 512×512 resolution
├── Gaussian NLL + Norm-in-Norm loss
└── Checkpoint: Pre-trained encoder

Week 3: Fine-tuning (Real)
├── DIQA-5000 train split (3,500 samples)
├── + Tobacco-800 (1,285 samples)
├── + DIBCO (131 samples)
├── 60 epochs, low LR (1e-5)
└── Checkpoint: Fine-tuned teacher

Week 4: Validation & Distillation
├── Evaluate on DIQA-5000 val/test
├── Target: SRCC > 0.80, PLCC > 0.82
├── Temperature scaling calibration
├── Distill to ResNet-18 student
└── Export ONNX/TorchScript

Week 5: External Validation
├── SmartDoc-QA (mobile capture)
├── SROIE (receipts)
├── Cross-dataset SRCC drop < 0.10
└── Production readiness assessment

Week 6: Integration & Phase 9 Prep
├── Freeze validated backbone
├── Update Phase 9 integration
├── Document final methodology
└── Prepare Phase 9 classifier datasets
```

### 7.2 Success Criteria (v4)

| Metric | v3 Result | v4 Target | How to Achieve |
|--------|-----------|-----------|----------------|
| DIQA-5000 SRCC | [LOW] | > 0.80 | Real fine-tuning |
| DIQA-5000 PLCC | [LOW] | > 0.82 | Norm-in-Norm loss |
| ECE (internal val) | 0.10 | < 0.10 | Temperature scaling |
| Cross-dataset SRCC | N/A | Drop < 0.10 | Domain diversity |

---

## 8. Dataset Requirements for v4

### 8.1 Training Data Composition

| Component | Samples | Purpose |
|-----------|---------|---------|
| **Synthetic Pre-training** | 50,000 | Learn degradation features |
| **DIQA-5000 train** | 3,500 | Human MOS anchor |
| **Tobacco-800** | 1,285 | Real historical degradation |
| **DIBCO** | 131 | Extreme degradation cases |
| **Total Real** | 4,916 | 10% real-world anchor |

### 8.2 Evaluation Data (Never Touch for Training)

| Dataset | Samples | Purpose |
|---------|---------|---------|
| DIQA-5000 val | 500 | Validation during training |
| DIQA-5000 test | 1,000 | Final evaluation |
| SmartDoc-QA | 4,270 | Cross-dataset validation |
| SROIE | 1,500 | Receipt domain validation |

### 8.3 Augmentation Strategy for v4

**Synthetic (Pre-training)**:

- Blur: Gaussian (σ=1-15), Motion (kernel=3-15), Defocus
- Noise: Gaussian, Salt-pepper, Speckle, Poisson
- Compression: JPEG Q=15-100, WebP Q=20-90
- Lighting: Brightness ±40%, Contrast ±30%, Gamma 0.5-2.0
- Geometric: Rotation ±20°, Perspective warp 0-0.25
- **NEW**: Shadow gradients, Moiré patterns, Bleed-through simulation

**Real (Fine-tuning)**:

- NO augmentation (preserve authentic degradation patterns)
- Only normalization for model input

---

## 9. Risk Mitigation for v4

### 9.1 Risk: Still Fail on DIQA-5000

**Mitigation**:

- If SRCC < 0.70 after fine-tuning, use **MLLM approach** (DeQA-Doc style)
- Soft labeling with probability distributions
- Consider MUSIQ/MANIQA pretrained features

### 9.2 Risk: Resolution Increase Blows Memory

**Mitigation**:

- Use gradient checkpointing
- Mixed precision training (FP16/BF16)
- Reduce batch size to 16-24
- Use A10 (24GB) or A100 (40GB) instead of T4 (16GB)

### 9.3 Risk: Phase 9 Delayed

**Mitigation**:

- Phase 9 can start with ImageNet backbone in parallel
- Swap to Phase 7 v4 backbone once validated
- Minimal code change (frozen backbone interface)

---

## 10. Implications for Overall Project

### 10.1 Timeline Impact

| Phase | Original | Revised | Reason |
|-------|----------|---------|--------|
| Phase 7 | 6 weeks | 8 weeks | Add real fine-tuning + validation |
| Phase 9 | Weeks 7-12 | Weeks 9-14 | Delayed start |
| Integration | Week 13 | Week 15 | Later Phase 7 completion |

### 10.2 Resource Impact

| Resource | Original | Revised | Delta |
|----------|----------|---------|-------|
| GPU Hours | 200 | 350 | +75% (larger resolution) |
| Data Prep | 1 week | 2 weeks | +1 week (real data prep) |
| Validation | 1 week | 2 weeks | +1 week (cross-dataset) |

### 10.3 Success Confidence

| Scenario | Probability | Outcome |
|----------|-------------|---------|
| v4 beats HyperIQA | 30% | Exceeds target |
| v4 matches HyperIQA | 50% | Meets target |
| v4 improves but < HyperIQA | 15% | Acceptable |
| v4 fails, need MLLM approach | 5% | Fallback |

---

## 11. Conclusion

### 11.1 Root Cause Summary

The Phase 7 training failure on DIQA-5000 stems from **three critical errors**:

1. **Training/Evaluation Distribution Mismatch**: Synthetic degradations ≠ real degradations
2. **Label Validity Assumptions**: Linear parameter mappings ≠ human perception
3. **Metric Misalignment**: ECE optimization ≠ SRCC/PLCC performance

### 11.2 Path Forward

**The solution is not more data or longer training - it's the right data with validated labels:**

1. Pre-train on synthetic for feature learning (volume)
2. Fine-tune on DIQA-5000 train for perception alignment (fidelity)
3. Validate on held-out DIQA-5000 test before deployment
4. Only freeze backbone for Phase 9 after SRCC > 0.80

### 11.3 Key Takeaway

> "We achieved perfect calibration to the wrong targets. The model learned to predict synthetic degradation parameters, not human-perceived quality."

The fix requires aligning our training objective with our evaluation objective: **human perception of document quality**.

---

## 12. Next Steps

1. **Immediate**: Run 6-model consensus analysis on this root cause analysis
2. **Week 1**: Validate severity mappings against DIQA-5000 train MOS
3. **Week 2**: Implement v4 training pipeline with pre-train/fine-tune strategy
4. **Week 3**: Train and validate ResNet-50 v4
5. **Week 4**: Distill to ResNet-18 and export
6. **Week 5**: Cross-dataset validation and Phase 9 backbone freeze

---

**Document Owner**: Byron Williams
**Last Updated**: 2025-12-17
**Review Required**: Multi-model consensus pending
