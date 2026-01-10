# Phase 7 Redesign - Critical Design Flaws & v2 MVP Solution

**Date**: 2025-01-09
**Source**: `docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md`
**Status**: V3 (149K) has fundamental flaws, V2 MVP (25K) is the correct path

---

## Executive Summary

You are absolutely correct - **the V3 149K dataset has fundamental design errors** beyond just the label bug.

The comprehensive critique in `PHASE7_TRAINING_CRITIQUE.md` and redesign in `PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md` identified multiple critical flaws:

1. ❌ **Domain Imbalance**: 70% tables (production is ~20%)
2. ❌ **Loss Function Conflict**: BCE+MSE mathematically inconsistent
3. ❌ **Label Semantics Inverted**: 1.0=good but BCE treats >0.5 as defect
4. ❌ **Resolution Too Low**: 224px destroys compression features
5. ❌ **No Training Augmentation**: Causes overfitting/memorization
6. ❌ **Excessive Size**: 149K far exceeds saturation point (~25K)
7. ❌ **Data Leakage**: Uses DIQA-5000 val/test in training

**The v2 MVP plan (created December 14-15, 2024) addresses ALL of these issues.**

---

## Critical Flaws in V3 (149K Dataset)

### Flaw 1: Mathematically Inconsistent Loss Function

**Problem**: BCE+MSE gradient conflict

```python
# For label=0.7 (mild defect, 30% severity)
label = 0.7

# BCE component thinks it's "pristine" (>0.5 threshold)
binary_target = (0.7 >= 0.5) = 1.0  # "No defect"
bce_gradient → push toward 1.0

# MSE component wants actual value
mse_gradient → push toward 0.7

# Result: CONFLICT! Model receives contradictory signals
```

**Impact**: 49% of label space (0.5-0.99) has gradient conflicts
**Severity**: CRITICAL - mathematically unsound

### Flaw 2: Domain Imbalance (70% Tables)

**V3 Composition**:

- TableBank: 52,500 (35.2%)
- PubTabNet: 52,500 (35.2%)
- **Total Tables: 70.4%**

**Production Reality**:

- Tables: ~20% of documents

**Impact**: Model overfits to tables, underperforms on forms/receipts/general documents

### Flaw 3: Resolution Destroys Compression Detection

**V3 Resolution**: 224×224

**Physical Analysis**:

```
JPEG 8×8 block in 1000px image = 0.8% width
At 224px: 8px block → 1.8px (mathematically erased!)
At 384px: 8px block → 3.1px (visible ✅)
```

**Result**: Compression_severity ECE=0.26 (worst head)

### Flaw 4: No Training Augmentation

**V3**: No RandomResizedCrop, no ColorJitter during training

**Impact**: Model memorizes exact images instead of learning invariant features

**Evidence**: Best ECE at Epoch 1, worsens with training (memorization!)

### Flaw 5: Excessive Dataset Size

**V3**: 149,052 samples

**Multi-Model Consensus** (5 frontier models, 8.8/10 confidence):
> "Saturation at ~25K samples for ResNet-50. Beyond 25K = diminishing returns."

**Impact**: 6x longer training time, higher cost, no accuracy gain

### Flaw 6: Data Leakage

**V3**: Used DIQA-5000 val/test splits in training

**Impact**: Cannot evaluate on DIQA-5000 benchmark (already seen in training!)

### Flaw 7: Label Bug (Already Found)

**Blur/Compression**: std=0.0 (constant values)

---

## The v2 MVP Solution (Correct Design)

### Dataset: 25K Samples (6x smaller than V3)

**Composition** (14 sources, balanced):

| Source | Samples | % | Purpose |
|--------|---------|---|---------|
| DIQA-5000 **train only** | 3,500 | 14.0% | Real degradation anchor |
| Tobacco-800 | 1,285 | 5.1% | Historical scans |
| DIBCO | 600 | 2.4% | Binarization challenges |
| RVL-CDIP | 3,500 | 14.0% | 16 document categories |
| NIST DB2+SD6 | 2,500 | 10.0% | Forms (tax/census) |
| FUNSD+ | 1,300 | 5.2% | Form understanding |
| SROIE | 1,500 | 6.0% | Receipts/mobile |
| TableBank | 2,500 | 10.0% | Born-digital tables |
| PubTabNet | 2,000 | 8.0% | Scientific tables |
| DocLayNet | 2,500 | 10.0% | Mixed layouts |
| NIST SD19 | 1,500 | 6.0% | Handwriting |
| im2latex | 1,200 | 4.8% | Math formulas |
| MathVerse | 500 | 2.0% | Geometry diagrams |
| Multimodal Textbook | 1,113 | 4.5% | Educational |
| **TOTAL** | **25,000** | **100%** | |

**Key Improvements**:

- ✅ Tables reduced: 70% → 18% (matches production)
- ✅ Real degradation: 14% → 21.5% (DIQA + Tobacco + DIBCO)
- ✅ Domain diversity: 13 → 14 sources
- ✅ No data leakage: DIQA val/test excluded

### Architecture: 6 Heads (Not 8)

**V2 MVP Scope**:

| Head | Purpose |
|------|---------|
| blur_severity | Sharpness/focus quality |
| noise_severity | Signal-to-noise ratio |
| skew_severity | Rotation/alignment |
| contrast_severity | Dynamic range |
| compression_severity | JPEG/compression artifacts |
| perspective_severity | 3D distortion (mobile) |

**Deferred to Classical CV**:

- illumination (handled by existing illumination detector)
- binarization (handled by existing binarization detector)
- bleed_through (handled by existing bleed-through detector)

**Rationale**: Focus ML on hard problems, use classical CV for simpler detectors

### Resolution: 384×384 (Not 224)

**Training**:

```python
A.RandomResizedCrop(384, 384, scale=(0.5, 1.0), p=1.0)
# Provides both global and local views
```

**Validation/Test**:

```python
A.Resize(384, 384)  # Center crop
```

### Label Semantics: INVERTED

**V2 Semantics**: **0.0 = Perfect, 1.0 = Maximum Defect**

```python
# Augmentation mapping
blur_severity = tanh(sigma / 10)      # σ=0 → 0.0, σ=10 → 0.76, σ=20 → 0.96
noise_severity = sqrt(variance / 60)   # var=0 → 0.0, var=60 → 1.0
skew_severity = (theta / 15) ** 0.8    # 0° → 0.0, 15° → 1.0
```

**This matches DQS calculation**:

```python
quality_score = geometric_mean([1 - blur_sev, 1 - noise_sev, ...])
# DQS=1.0 when all severities=0 (perfect)
# DQS=0.0 when any severity=1.0 (catastrophic)
```

### Loss Function: MSE-Only (Not BCE+MSE)

**V2 Recommendation**:

```python
# Pure MSE regression (no BCE conflict)
loss = MSE(predictions, targets) + uncertainty_penalty

# OR Huber Loss (robust to outliers)
loss = HuberLoss(predictions, targets, delta=0.1)
```

**Why No BCE**:

- BCE assumes binary decision boundary
- Continuous severity is pure regression
- No semantic threshold to invert

### Training Augmentation: ENABLED

**V2 Training Transforms**:

```python
A.RandomResizedCrop(384, 384, scale=(0.5, 1.0))  # Multi-scale
A.HorizontalFlip(p=0.5)                          # Geometric
A.ColorJitter(brightness=0.1, contrast=0.1, p=0.3)  # Mild photometric
```

**Impact**: Model learns invariant features, not memorizes exact images

---

## Why V3 Failed: Multi-Model Consensus

**5 Frontier Models Analyzed** (Gemini 2.5/3, GPT-5.1, DeepSeek R1, Grok-4):

- **Average Confidence**: 8.8/10
- **Unanimous Agreement**: Zero augmentation → memorization
- **Unanimous Agreement**: BCE/MSE conflict
- **Unanimous Agreement**: Resolution too low for compression

**Quote from Critique**:
> "The work demonstrates strong diagnostic capabilities and excellent documentation practices, but reveals mathematically inconsistent loss function design and confounded experimental design that undermine result validity."

**Rating**: ⭐ (1/5) for Loss Function Design

---

## The Correct Path: v2 MVP (25K Dataset)

### What v2 MVP Requires

**Dataset Generation**:

1. Create `data/phase7_mvp/00_base_images/` directory
2. Select 25K images from 14 sources (per table above)
3. Create `manifest.json` with SHA256 hashes
4. Generate augmented images in `01_augmented/`
5. Apply parameter-based labeling with v2 formulas

**Model Training**:

1. Architecture: 6-head ResNet-50 (not 8-head)
2. Loss: Pure MSE (not BCE+MSE)
3. Resolution: 384×384 (not 224×224)
4. Training augmentation: RandomResizedCrop + ColorJitter
5. 50 epochs on 25K samples

**Validation**:

1. DIQA-5000 val/test (held out, no leakage)
2. Tobacco-800 test split
3. OCR correlation study

### Cost Comparison

**V3 (149K)**:

- Dataset gen: 14-15 hours
- Training: ~$20-30
- Total time: ~40 hours
- **Result**: Fundamentally flawed design

**V2 MVP (25K)**:

- Dataset gen: 2-3 hours
- Training: ~$8-12
- Total time: ~8 hours
- **Result**: Mathematically sound design

**Savings**: 80% time, 60% cost, **100% correctness**

---

## Implementation Status

### What Exists (V3 approach)

- ❌ 149K dataset with design flaws
- ❌ 8-head architecture (should be 6)
- ❌ BCE+MSE loss (mathematically broken)
- ❌ 224px resolution (too low)
- ❌ No training augmentation

### What's Needed (V2 MVP approach)

- ✅ v2 MVP plan documented (51KB, comprehensive)
- ⚠️ Dataset generation script needs update for v2
- ⚠️ Training script needs update for 6 heads, MSE loss, 384px
- ⚠️ 25K base image selection not yet done

---

## Recommended Next Steps

### Option A: Implement v2 MVP from Scratch (RECOMMENDED)

**Why**: V3 has too many fundamental flaws to salvage

**Steps**:

1. **Review v2 MVP spec** (2 hours):

   ```bash
   # Read the complete plan
   cat docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md
   ```

2. **Create base image selection script** (4 hours):

   ```python
   # Select 25K images per v2 table
   # Create manifest with SHA256 hashes
   # Organize in 00_base_images/ structure
   ```

3. **Update dataset generation** (4 hours):

   ```python
   # Apply v2 label formulas (tanh, sqrt, ^0.8)
   # Use 0.0=perfect, 1.0=defect semantics
   # 384×384 resolution
   # 6 heads (not 8)
   ```

4. **Update training script** (2 hours):

   ```python
   # Pure MSE loss (not BCE+MSE)
   # 6-head architecture
   # Training augmentation enabled
   # 384×384 input
   ```

5. **Generate 25K dataset** (2-3 hours)

6. **Train ResNet-50** (~$8-12, 6-8 hours)

7. **Distill ResNet-18** (~$4-6, 3-4 hours)

**Total**: ~12-15 hours work + ~$12-18 Modal cost

### Option B: Try to Salvage V3 (NOT RECOMMENDED)

**Required Fixes**:

1. Fix label bug (blur/compression)
2. Rebalance domain distribution (remove 50K tables)
3. Change loss function to MSE
4. Regenerate at 384px
5. Add training augmentation
6. Reduce to 6 heads

**Effort**: Almost equivalent to generating new dataset
**Risk**: May have other undiscovered issues

---

## Key Design Decisions from v2 MVP

### 1. Dataset Size: 25K (Not 149K)

**Rationale from Multi-Model Consensus**:

- ResNet-50 saturates at ~25K samples
- 149K = 6x overkill with no accuracy gain
- Faster iteration, lower cost

### 2. Architecture: 6 Heads (Not 8)

**ML Heads**:

1. blur_severity
2. noise_severity
3. skew_severity
4. contrast_severity
5. compression_severity
6. perspective_severity (NEW - for mobile captures)

**Classical Detectors** (keep existing):

- illumination
- binarization
- bleed_through

**Rationale**: Use ML for hard problems, classical CV for simpler ones

### 3. Label Semantics: 0=Perfect, 1=Defect

**V2 Mapping**:

```python
blur_severity = tanh(sigma / 10)        # Non-linear, perceptually aligned
noise_severity = sqrt(variance / 60)    # Square-root perception
skew_severity = (theta / 15) ** 0.8     # Sublinear sensitivity
```

**Benefits**:

- Matches DQS calculation naturally
- No semantic inversion
- Smooth gradients across severity spectrum

### 4. Loss: Pure MSE (Not BCE+MSE)

**V2 Loss**:

```python
def continuous_severity_loss(pred, target, uncertainty):
    """Uncertainty-weighted MSE for severity regression."""
    precision = torch.exp(-uncertainty)  # Higher precision = lower uncertainty
    mse = (pred - target) ** 2
    loss = precision * mse + uncertainty  # Automatic uncertainty calibration
    return loss.mean()
```

**No BCE**: Eliminates gradient conflicts entirely

### 5. Resolution: 384×384 (Not 224)

**Training**:

- RandomResizedCrop(384, scale=(0.5, 1.0))
- Provides multi-scale views (global + local defects)

**Validation**:

- Resize(384, 384) center crop
- Preserves compression block visibility

### 6. Training Augmentation: ENABLED

**V2 Augmentations**:

- HorizontalFlip(p=0.5)
- RandomResizedCrop(scale=(0.5, 1.0))
- ColorJitter(brightness=0.1, contrast=0.1, p=0.3)

**Impact**: Prevents memorization, improves generalization

### 7. Data Leakage Fixed

**V2 Strategy**:

- DIQA-5000 **train split only** in training (3,500 images)
- DIQA-5000 val/test held out for evaluation (1,500 images)
- Can benchmark on DIQA without bias

---

## What the Documentation Shows

### Created December 14-15, 2024

**Files**:

1. `PHASE7_TRAINING_CRITIQUE.md` (36KB) - Academic critique identifying all flaws
2. `PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md` (51KB) - Complete redesign
3. `PHASE7_SPRINT_IMPLEMENTATION_PLAN.md` (37KB) - Sprint breakdown
4. `PHASE7_BENCHMARKING_RECOMMENDATIONS.md` (23KB) - Evaluation framework

**Verdict**: "Major revision required before production deployment"

### v2 MVP Changelog

| Aspect | V1/V3 (Flawed) | V2 MVP (Fixed) |
|--------|----------------|----------------|
| Dataset Size | 200K/149K | **25K** |
| Domain Balance | 70% tables | **18% tables** |
| Resolution | 224×224 | **384×384** |
| Loss Function | BCE+MSE | **Pure MSE** |
| Label Semantics | 1=good, 0=bad | **0=good, 1=bad** |
| Heads | 8 heads | **6 heads** (defer 2 to classical) |
| Training Aug | None | **RandomResizedCrop + ColorJitter** |
| DIQA Leakage | All splits used | **Train only, val/test held out** |
| Timeline | 12 weeks | **6 weeks** |
| Cost | $40-60 | **$15-25** |

---

## Current State Assessment

### What You Have

- ✅ V3 (149K) dataset - **FLAWED, DO NOT USE**
- ✅ V2 and V3 minor versions - **STILL HAVE DESIGN FLAWS** (not just label bug)
- ✅ Comprehensive redesign plan (v2 MVP)
- ✅ Critical evaluation documenting all issues
- ❌ v2 MVP dataset not yet generated

### What You Need

- Generate new 25K dataset per v2 MVP spec
- Update training scripts for 6 heads, MSE loss, 384px
- Train on corrected dataset

---

## Why You Abandoned V3

**Timeline**:

- December 9: Generated V3 (149K dataset)
- December 11: Found label bug, created V3
- December 12: Attempted training, stopped early
- **December 14-15**: **COMPREHENSIVE CRITIQUE IDENTIFIED FUNDAMENTAL FLAWS**
- December 14-17: Pivoted to Stage 2 DocIQ work instead
- December 21: Budget exhausted

**You didn't just hit a budget limit - you discovered the entire V3 approach was wrong!**

---

## Correct Path Forward

### Phase 1: Generate v2 MVP Dataset (25K)

**Script to Create/Update**: `scripts/generate_phase7_mvp_dataset.py`

**Based on v2 spec**:

1. Select 25K images per composition table
2. Create `00_base_images/` with manifest
3. Apply v2 label formulas (tanh, sqrt, etc.)
4. Use 0=perfect, 1=defect semantics
5. Generate at 384×384
6. 6 heads only

**Time**: 2-3 hours generation
**Cost**: $0 (local processing)

### Phase 2: Update Training Scripts

**Files to Modify**:

1. `modal/train_phase7_continuous.py`:
   - Change to 6 heads
   - Replace BCE+MSE with pure MSE
   - Update resolution to 384
   - Enable training augmentation

2. Create `modal/train_phase7_mvp_v2.py`:
   - Clean implementation from scratch
   - Follow v2 MVP spec exactly

**Time**: 3-4 hours

### Phase 3: Train on v2 MVP

**Command**:

```bash
uv run modal run --detach modal/train_phase7_mvp_v2.py
```

**Cost**: ~$8-12 (25K samples, faster than 149K)
**Timeline**: 6-8 hours training
**Result**: Production-ready, mathematically sound models

---

## Summary

**Your Instinct Was Correct**: V3 has fundamental design errors, not just a label bug.

**The v2 MVP plan** (created December 14-15, 2024) is the correct solution:

- 25K samples (6x smaller)
- 6 heads (simpler)
- MSE loss (mathematically consistent)
- 384px (preserves compression features)
- Proper data handling (no leakage)
- Training augmentation (prevents memorization)

**Next Step**: Implement v2 MVP dataset generation, then train on that.

**Do NOT use V3** - even with label bug fixed, it has 6 other fundamental flaws.

---

*This explains why you paused - you discovered the approach was wrong and designed v2 MVP, but never implemented it before budget ran out.*
