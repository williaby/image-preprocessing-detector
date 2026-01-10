# Complete Phase 7 Training History & Current State

**Date**: 2025-01-09
**Branch**: `feat/phase7-continuous-training`

---

## Timeline of Approaches (Chronological Evolution)

### Approach 1: V1 - 149K Augmentation-Based ❌ FAILED

**Date**: December 7-9, 2024
**Dataset**: 149K samples, augmentation-based labels

**Design**:

- 8 heads (blur, noise, skew, contrast, illumination, compression, binarization, bleed_through)
- Resolution: 224×224
- Loss: BCE+MSE (alpha=0.6, beta=0.4)
- Label semantics: 1=good, 0=bad
- Domain: 70% tables
- No training augmentation

**Fatal Flaws**:

- Label bug: blur/compression std=0.0 (constant values)
- Resolution too low for compression detection (224px)
- Domain imbalance (70% tables vs 20% production)
- BCE+MSE gradient conflicts
- No training augmentation (memorization)

**Status**: Dataset generated, label bug discovered December 11

---

### Approach 2: V2 - 149K Fixed Labels ❌ STILL FLAWED

**Date**: December 11-12, 2024
**Dataset**: iqa_phase7_165k_v2, iqa_phase7_165k_v3

**Design**:

- Fixed label bug (blur std=0.394 in v2, 0.307 in v3)
- Still 8 heads
- Still 224×224 resolution
- Still BCE+MSE loss
- Still 70% tables

**Improvements**:
✅ Label bug fixed

**Remaining Flaws**:

- Resolution still too low (384px needed minimum)
- Domain imbalance unchanged
- BCE+MSE still mathematically inconsistent
- No training augmentation
- Excessive size (149K vs 25K saturation)

**Status**: Dataset generated, training attempted December 12, stopped early

---

### Approach 3: V2 MVP - 25K Redesign ✅ DESIGNED (Not Implemented)

**Date**: December 14-15, 2024
**Documentation**: `PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md`

**Design**:

- **25K samples** (6x smaller, saturation point)
- **6 heads** (defer illumination/binarization/bleed_through to classical)
- **384×384 resolution**
- **Pure MSE loss** (no BCE)
- **0=perfect, 1=defect** semantics
- **Domain balanced**: 18% tables
- **Training augmentation**: RandomResizedCrop + ColorJitter
- **DIQA train only** (no data leakage)

**Multi-Model Consensus**: 5 frontier models, 8.8/10 confidence

**Status**: Fully specified, dataset generation never started

**Why Not Implemented**: Budget exhausted after discovering flaws, pivoted to Stage 2

---

### Approach 4: Stage 2 DocIQ-Replica with Layout Masks ✅ PARTIALLY COMPLETE

**Date**: December 18-21, 2024
**Branch**: `claude/add-labeling-workstreams` (different branch!)

**Architecture**: **DocIQ Paper-Aligned** (1600×1600 + Layout Fusion)

**Design**:

- **12,742 samples** (DIQA-5000 + SmartDoc-QA + SROIE + Tobacco-800 + FUNSD)
- **3 dimensions** (overall, sharpness, color) - NOT 8 heads
- **1600×1600 resolution** with 11-class layout masks
- **Layout Fusion Downsampler** (dual-path: visual + semantic)
- **Distribution prediction** (5-class soft labels: excellent/good/fair/poor/bad)
- **KL-divergence loss** (not MSE, not BCE+MSE)
- **DocIQ paper config**: 60 epochs, batch=20, LR=2e-4, step decay

**Two-Stage Training**:

- **Stage 1**: Train DocIQ-Replica on DIQA-5000 (5K with human MOS) ✅ COMPLETE
- **Stage 2**: Fine-tune on 12.7K multi-dataset ⚠️ PHASE 1 COMPLETE, PHASE 2 NOT STARTED

**Layout Masks**:

- Pre-generated for all 12,742 images
- 11 classes (DocLayNet): Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
- 1600×1600 resolution (50x larger than ImageNet standard)
- Stored as compressed NPZ (18GB vs 360GB raw)

**Stage 1 Results** (December 14-17):

- ✅ Models trained: `production_model_seed42.pt` (302MB), `student_model_seed42.pt` (133MB)
- ✅ Performance: ECE=0.028, Correlation=0.756
- ✅ Used to generate pseudo-labels for 13,890 images

**Stage 2 Phase 1 Results** (December 21):

- ✅ 15 epochs warmup training complete
- ✅ Val SRCC: 0.827, Val ECE: 0.037
- ❌ No checkpoints saved (vetoed due to output range <0.35)

**Stage 2 Phase 2** (December 21):

- ⚠️ Ready to launch: 45 epochs full fine-tuning
- 🛑 Budget exhausted before launch

**Purpose**: This is for **pseudo-labeling and benchmarking**, NOT Project A production IQA

**Key Difference from v2 MVP**:

- DocIQ outputs 3D (overall/sharpness/color)
- Project A needs 8D (blur/noise/skew/etc.)
- **Cannot use Stage 2 models directly in Project A pipeline**

---

## Current State (January 2025)

### What You Actually Have

#### Track 1: DocIQ-Replica (Stage 1-2) - For Pseudo-Labeling

**Branch**: `claude/add-labeling-workstreams`

**Complete**:

- ✅ Stage 1 models (trained on DIQA-5000, ECE=0.028)
- ✅ 12,742 layout masks (1600×1600, 11-class)
- ✅ Stage 2 Phase 1 training (15 epochs warmup)
- ✅ 12,742 DIQA-labeled images (10-bin distributions)

**Incomplete**:

- ⚠️ Stage 2 Phase 2 (45 epochs fine-tuning not started)

**Purpose**: Generate expert pseudo-labels for evaluation/benchmarking

#### Track 2: Project A Production Models - For RAG Pipeline

**Branch**: `feat/phase7-continuous-training` (current)

**Complete**:

- ✅ V1 dataset generated (149K, has label bugs)
- ✅ V2/V3 datasets (label bugs fixed but other design flaws remain)
- ✅ v2 MVP plan documented (25K, all flaws fixed)
- ✅ Training scripts exist (4 modal scripts)

**Incomplete**:

- ❌ v2 MVP dataset not generated
- ❌ No production IQA models trained
- ❌ 149K images don't have DIQA labels

**Purpose**: Train actual production 8-head IQA models for Project A

---

## The Fundamental Design Question

### What You Discovered (December 2024)

**Even 384×384 is too small** for document IQA!

From `diqa_research.md` (December 18, 2024):
> "DocIQ is designed to ingest images at 1600×1600 pixels. This resolution is approximately 50× larger than standard classification inputs. It ensures that the high-frequency components of text characters (strokes, serifs, diacritics) are preserved in the input tensor."

**Critical Insight**:

- 224×224: Compression 8×8 blocks → 1.8px (invisible)
- 384×384: Compression 8×8 blocks → 3.1px (barely visible)
- **1600×1600**: Compression 8×8 blocks → 12.8px (clearly visible!)

**This is why you implemented Stage 2 with 1600×1600 + layout masks!**

---

## The Two Separate Systems

### System A: DocIQ-Replica (Stage 2) - 1600×1600 + Layout Masks

**Purpose**: High-accuracy pseudo-labeling for benchmarking
**Architecture**: ResNet-50 + Layout Fusion Downsampler
**Input**: 1600×1600 RGB + 11-class layout mask
**Output**: 3 dimensions (overall, sharpness, color)
**Labels**: 5-class distributions (excellent/good/fair/poor/bad)
**Use Case**: Generate expert labels, evaluate models, benchmarking

**Status**: Stage 1 complete, Stage 2 Phase 2 ready

### System B: Project A Production IQA - Needs Design Decision

**Purpose**: Production quality assessment for RAG pipeline
**Architecture**: ResNet-50 → ResNet-18 (to be determined)
**Input**: ??? (224? 384? 1600? TBD)
**Output**: 8 heads OR 6 heads? (blur, noise, skew, contrast, compression, ± others)
**Labels**: Continuous [0-1] OR distributions?
**Use Case**: DQS calculation, OCR routing decisions

**Status**: Multiple partial datasets, no clear current approach

---

## The Critical Decision You Face

### Should Project A Use the DocIQ Approach?

**Option A: Full DocIQ Replication (1600×1600 + Layout Masks)**

**Pros**:

- ✅ Proven architecture (DocIQ paper, 0.90+ SRCC)
- ✅ Preserves compression features
- ✅ Layout-aware quality assessment
- ✅ Already implemented in Stage 2

**Cons**:

- ❌ 50x more expensive than 224px (memory, compute)
- ❌ Requires layout mask generation (adds latency)
- ❌ Outputs 3D not 8D (architecture mismatch)
- ❌ Batch size limited to 20 (vs 128)
- ❌ Slower inference (production impact)

**To Use This**:

1. Modify Stage 2 DocIQ to output 8 heads instead of 3
2. OR map 3D output to 8D continuous scores (lossy)
3. Generate layout masks for 25K training images
4. Train with 1600px input

**Option B: Simplified High-Res (No Layout Masks)**

**Pros**:

- ✅ Simpler architecture (standard ResNet)
- ✅ Faster inference (no mask generation)
- ✅ Direct 8-head output
- ✅ Can use existing v2 MVP plan (but increase resolution)

**Cons**:

- ⚠️ Not as accurate as full DocIQ
- ⚠️ Resolution still needs to be high (768px? 1024px?)

**Design**:

- 25K dataset per v2 MVP composition
- 768×768 or 1024×1024 resolution
- Standard ResNet-50 (no Layout Fusion)
- 8 heads (blur, noise, skew, contrast, compression, perspective, ±2 more)
- Pure MSE loss
- Training augmentation enabled

**Option C: Hybrid Approach**

**Pros**:

- ✅ Best of both worlds

**Design**:

- Generate layout masks ONCE during dataset prep
- Train at 1024×1024 with masks as additional input channels
- Lighter than full DocIQ (no Layout Fusion Downsampler)
- 8-head output for Project A needs

---

## What the Documentation Shows

### The Evolution of Thought (December 2024)

1. **Dec 7-9**: Generated V1 (149K, 224px, 8 heads) → label bug
2. **Dec 11-12**: Fixed labels (V2/V3) → still had design flaws
3. **Dec 14-15**: Comprehensive critique → v2 MVP plan (25K, 384px, 6 heads, MSE)
4. **Dec 14-17**: Implemented Stage 1 DocIQ (1600px, layout masks, 3D output) ✅
5. **Dec 18-21**: Worked on Stage 2 DocIQ fine-tuning (12.7K dataset)
6. **Dec 21**: Budget exhausted, both tracks stalled

### The Current Design Question

**Your December 18 research** (`diqa_research.md`) made it clear:

- 384×384 is still too small
- 1600×1600 + layout masks is the DocIQ standard
- This is what you implemented for Stage 2

**The Unanswered Question**:
Should Project A production models use the DocIQ approach (1600×1600 + masks)?

**Trade-offs**:

- **Accuracy**: DocIQ approach wins (proven 0.90+ SRCC)
- **Speed**: Simpler ResNet wins (no mask generation, smaller input)
- **Complexity**: Simpler ResNet wins (standard architecture)
- **Production**: Depends on latency budget (can you afford 1600px inference?)

---

## Where You Actually Stopped

**December 21, 2024**: Budget exhausted with THREE incomplete approaches:

1. **V3 (149K)**: Dataset exists but fundamentally flawed
2. **v2 MVP (25K)**: Fully specified but never implemented
3. **Stage 2 DocIQ (12.7K)**: Phase 1 complete, Phase 2 not started

**The Question**: Which approach to resume?

---

## Current Branch Status

### On `feat/phase7-continuous-training` (CURRENT)

**Have**:

- ✅ V1/V2/V3 datasets (149K) with various flaws
- ✅ v2 MVP plan (25K, 6 heads, 384px)
- ✅ Phase 7 training scripts (4 modal scripts for standard ResNet approach)
- ✅ Research showing 1600px needed
- ❌ No DocIQ Layout Fusion implementation
- ❌ No 1600px training scripts
- ❌ No layout masks for Phase 7 dataset

### On `claude/add-labeling-workstreams`

**Have**:

- ✅ DocIQ-Replica implementation (1600px + layout masks)
- ✅ Stage 1 trained models (ECE=0.028)
- ✅ 12,742 layout masks (1600×1600)
- ✅ Stage 2 training infrastructure
- ❌ 8-head output (only has 3-head)
- ❌ Not directly usable for Project A

---

## The Three Paths Forward

### Path A: Use Stage 2 DocIQ Architecture for Project A (1600px)

**What's Needed**:

1. **Modify DocIQ architecture** for 8-head output:

   ```python
   # Change from 3 heads (overall/sharpness/color)
   # To 8 heads (blur/noise/skew/contrast/compression/perspective/±2)
   ```

2. **Generate 25K dataset with layout masks**:
   - Select 25K images per v2 MVP composition
   - Generate 11-class layout masks (1600×1600)
   - Create DIQA labels using Stage 1 model

3. **Train modified DocIQ**:
   - Use Stage 2 training infrastructure
   - 1600×1600 input
   - Layout Fusion Downsampler
   - 8-head severity prediction

**Cost**: ~$20-30 (slower due to 1600px)
**Timeline**: 12-18 hours training + 4-6 hours dataset prep
**Result**: Highest accuracy, slower inference

### Path B: Simplified High-Res Without Layout Masks (768-1024px)

**What's Needed**:

1. **Generate 25K dataset per v2 MVP**:
   - 14 sources per v2 composition
   - 768×768 or 1024×1024 resolution
   - No layout masks required
   - Parameter-based labels (v2 formulas)

2. **Train standard ResNet**:
   - 8 heads (or 6 heads per v2 MVP)
   - Pure MSE loss
   - Training augmentation

**Cost**: ~$12-18 (faster than 1600px)
**Timeline**: 8-12 hours training + 3-4 hours dataset prep
**Result**: Good accuracy, faster inference

### Path C: Use Existing Stage 1 DocIQ for Pseudo-Labeling

**What's Needed**:

1. **Accept architecture mismatch**: 3D → 8D mapping
2. **Generate DIQA labels for 25K images**:
   - Use Stage 1 `student_model_seed42.pt`
   - Run inference to get overall/sharpness/color scores
   - Map to 8 heads somehow (unclear mapping)

**Cost**: ~$5-10 inference + $15-20 training
**Timeline**: 3-5 hours inference + 10-15 hours training
**Problem**: How to map 3D→8D? Unclear if feasible

---

## My Updated Recommendation

Based on discovering the 1600×1600 requirement and existing Stage 2 implementation:

### Recommended: Path A (DocIQ Architecture for Project A)

**Why**:

1. You already have the Stage 2 DocIQ infrastructure working
2. Research proves 1600×1600 is necessary for compression detection
3. Layout masks improve accuracy (DocIQ paper)
4. Can modify existing Stage 2 code for 8-head output

**Implementation Steps**:

1. **Merge branches** to get all code in one place
2. **Modify Stage 2 DocIQ** for 8-head output
3. **Select 25K base images** per v2 MVP composition
4. **Generate layout masks** for 25K images (reuse Stage 2 mask generator)
5. **Create labels** using modified parameter-based formulas
6. **Train modified DocIQ** on 25K + masks

**Estimated Cost**: $25-35 total
**Estimated Time**: 2-3 days (including dataset prep)

**Trade-off**: Slower inference but highest accuracy

---

## Summary

**The Real Situation**:

- You didn't just hit a budget limit
- You discovered 384px is still too small
- You researched and found DocIQ's 1600px + layout masks approach
- You implemented that for Stage 2 (different purpose)
- You never adapted it for Project A production models
- Both tracks stalled: Stage 2 at Phase 2 launch, Project A never started with correct design

**The Missing Piece**:
A Project A training implementation using:

- 1600×1600 resolution (or 768-1024px minimum)
- Layout masks (for best accuracy)
- 8-head output (Project A requirements)
- 25K balanced dataset (v2 MVP composition)

**Next Step**: Decide which path (A, B, or C) and implement the missing dataset generation + training scripts.

---

*This explains the entire confusing situation - you kept discovering fundamental flaws and pivoting to better designs, but ran out of budget before implementing the final correct approach.*
