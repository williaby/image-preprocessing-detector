# Training Optimization Plan: SigLIP 2 + MobileNetV4 Multi-Task Pipeline

> **Date**: 2026-02-09
> **Status**: Draft
> **Consensus Review**: 5-model consensus (Gemini 2.5 Pro, Gemini 3 Pro Preview, GPT-5.2, DeepSeek-R1, Grok 4)
> **Related Docs**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md), [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md)
> **Branch**: `feat/stream-1-schema-foundation`

---

## 1. Executive Summary

This document captures the training optimization strategy synthesized from a 5-model AI consensus review of the SigLIP 2 NAFlex + MobileNetV4-Conv-S multi-task pipeline. The plan addresses three dimensions:

1. **Dataset allocation optimization** via Integer Linear Programming (ILP)
2. **Multi-task training strategy** with gradient surgery and uncertainty weighting
3. **Iterative refinement** via active learning loops

A critical augmentation ordering bug was identified and fixed as part of this work: geometric transforms (skew, orientation) were being applied AFTER pixel degradation, creating unrealistic "rotated noise" artifacts.

---

## 2. Bug Fix: Augmentation Ordering (IMPLEMENTED)

**File**: `src/image_preprocessing_detector/synthetic/generator.py`

**Problem**: The `_apply_post_processing()` method applied geometric transforms (skew rotation, orientation rotation) AFTER the augmentation/degradation pipeline (Augraphy/Albumentations noise, blur, compression artifacts). This creates "rotated noise" artifacts that never occur in real documents -- real scanners physically rotate/skew the document first, then sensor noise is added.

**Root Cause**: The generation flow was:

1. Render clean document
2. Apply degradation (noise, blur, JPEG artifacts, aging)
3. `_apply_post_processing()` -- skew rotation, orientation rotation, color mode, char height

**Fix Applied**: Split `_apply_post_processing()` into two methods:

- `_apply_geometric_transforms(image)` -- skew + orientation, called on clean rendered image BEFORE augmentation
- `_apply_post_processing(sample)` -- color mode conversion + char height measurement, called AFTER augmentation

**Corrected Flow**:

1. Render clean document
2. **Apply geometric transforms** (skew, orientation) on clean image
3. Apply degradation (noise, blur, etc.) on geometrically-correct image
4. Apply post-processing (color mode, char height measurement)

**Files Changed**: `generator.py` -- methods `_apply_geometric_transforms` (new), `_apply_post_processing` (reduced), `_generate_single_sample`, `_generate_multi_script_sample`, `generate_multi_script_document`, `generate`

**Impact**: All 3 generation paths (single sample, internal multi-script, public multi-script) now apply geometry before augmentation. Noise patterns align with the document's geometric state, producing more realistic training data.

---

## 3. Optimization Strategy: Phased Approach

The consensus unanimously rejected MCTS as unsuitable for this problem (not sequential decision-making; hybrid action space; prohibitively expensive evaluation). Instead, the following phased approach was recommended:

### Phase 1: ILP for Sample Allocation (Week 1-2)

**Goal**: Optimally allocate samples from ~25 data sources across 10 training datasets subject to diversity constraints.

**Why ILP First**: The sample allocation problem is fundamentally a constrained integer optimization:

- Decision variables: `x[source][dataset]` = number of samples from source `s` assigned to dataset `d`
- Constraints: per-source caps (40% max), per-dataset size targets, minimum diversity thresholds per dimension
- Objective: maximize aggregate diversity coverage across all 14 dimensions

**Implementation**:

```python
# Solver: PuLP (Python LP/ILP library) or Google OR-Tools
# Variables: ~25 sources x 10 datasets = 250 integer variables
# Constraints: ~150 (diversity thresholds + source caps + dataset sizes)

from pulp import LpProblem, LpMaximize, LpVariable, LpInteger

prob = LpProblem("dataset_allocation", LpMaximize)

# Decision variables: samples from source s to dataset d
x = {
    (s, d): LpVariable(f"x_{s}_{d}", 0, source_sizes[s], cat=LpInteger)
    for s in sources for d in datasets
}

# Objective: maximize diversity coverage
prob += sum(
    diversity_score(s, d, dim) * x[s, d]
    for s in sources for d in datasets for dim in dimensions
)

# Constraints
for d in datasets:
    prob += sum(x[s, d] for s in sources) == dataset_targets[d]  # size target
    for s in sources:
        prob += x[s, d] <= 0.4 * dataset_targets[d]  # 40% cap per source
```

**Inputs Required**:

- Source dataset metadata (capture method, domain, script, resolution distributions) from Layer 2 enrichment
- Per-dimension diversity scoring function
- Dataset size targets from DATASET_DIVERSITY_REQUIREMENTS.md Section 1-10

**Output**: Allocation matrix specifying exactly how many samples from each source go to each training dataset.

**Validation**: Compare ILP allocation vs naive proportional allocation on diversity metrics.

### Phase 2: Active Learning Loop (Post First Training Run)

**Goal**: Identify systematic failure modes after initial training and generate targeted data to fill gaps.

**Workflow**:

```
Train initial model (SigLIP 2, 19 heads)
    |
    v
Evaluate on held-out validation set
    |
    v
Identify failure clusters:
    - Per-head error analysis (which heads underperform?)
    - Per-dimension stratification (which diversity dimensions have highest error?)
    - Per-source analysis (which data sources produce weakest samples?)
    |
    v
Generate/acquire targeted samples:
    - Synthetic: adjust generation params for failing cases
    - Real: prioritize annotation for underrepresented categories
    |
    v
Re-train with augmented dataset
    |
    v
Compare metrics, iterate
```

**Key Metrics for Failure Detection**:

- Per-head validation loss (6 IQA regression + 6 classification + 7 regression = 19 heads)
- Error stratified by: capture method, script family, resolution tier, document age, color mode
- Cross-head conflict analysis (does improving head A degrade head B?)

**Trigger for Active Learning**: Any head with validation loss >2x the median across heads, or any dimension with error >1.5x the dataset-wide average.

### Phase 3: Bayesian Optimization (If Plateau)

**Goal**: Fine-tune ~15 continuous hyperparameters in the synthetic generation pipeline if active learning plateaus.

**When to Trigger**: Training loss improvement <1% for 2 consecutive active learning cycles.

**Parameters to Optimize**:

| Parameter | Range | Type |
|-----------|-------|------|
| Skew angle max | [3, 15] degrees | Continuous |
| Noise sigma | [0.01, 0.1] | Continuous |
| JPEG quality min | [30, 80] | Integer |
| Blur kernel max | [3, 11] | Odd integer |
| Aging probability | [0.05, 0.30] | Continuous |
| Historical probability | [0.01, 0.10] | Continuous |
| Color mode weights (3) | Simplex | Continuous |
| Resolution tier weights (7) | Simplex | Continuous |
| Degradation profile weights (5) | Simplex | Continuous |

**Tool**: Optuna or BoTorch (Bayesian Optimization with Gaussian Process surrogate)

**Objective**: Weighted average of per-head validation metrics (weights from Kendall uncertainty, see Section 4).

### Phase 4: NSGA-II Multi-Objective (Deferred)

**Goal**: Explore Pareto front when training objectives genuinely conflict (e.g., improving script detection at cost of IQA regression).

**Status**: Deferred until empirical evidence shows irreconcilable head conflicts. NSGA-II is computationally expensive and only warranted when Phase 2-3 reveal persistent trade-offs.

**When to Trigger**: Active learning + BO cannot simultaneously improve 2+ conflicting heads above threshold.

---

## 4. Multi-Task Training Strategy

### 4.1 Loss Balancing: Kendall Uncertainty Weighting

For 19 heads with mixed loss types (regression L1/MSE + classification BCE/CE), use homoscedastic uncertainty weighting (Kendall et al., 2018):

```python
# Each task has a trainable log-sigma parameter
log_sigma = nn.Parameter(torch.zeros(19))  # one per head

# Combined loss
total_loss = 0
for i, (loss_i, is_regression) in enumerate(zip(task_losses, task_types)):
    if is_regression:
        # L = (1 / 2*sigma^2) * loss + log(sigma)
        total_loss += 0.5 * torch.exp(-2 * log_sigma[i]) * loss_i + log_sigma[i]
    else:
        # L = (1 / sigma^2) * loss + log(sigma)
        total_loss += torch.exp(-2 * log_sigma[i]) * loss_i + log_sigma[i]
```

**Why**: Automatically learns relative task weights during training. Tasks with higher inherent noise (uncertainty) get down-weighted, preventing noisy heads from dominating gradients.

### 4.2 Gradient Surgery: PCGrad

When gradients from different task heads point in conflicting directions, PCGrad (Yu et al., 2020) projects conflicting gradients to resolve interference:

```python
# PCGrad: for each pair of task gradients
# If g_i . g_j < 0 (conflicting):
#   g_i = g_i - (g_i . g_j / ||g_j||^2) * g_j
# This removes the conflicting component
```

**When to Apply**: Monitor gradient cosine similarity between head pairs. Apply PCGrad when >20% of head pairs show negative cosine similarity.

**Alternative**: GradNorm (Chen et al., 2018) for dynamic gradient magnitude balancing. Consider if PCGrad alone is insufficient.

### 4.3 Phased Head Training

Train heads in groups to establish a good shared backbone before fine-tuning all heads:

| Phase | Heads Active | Epochs | Rationale |
|-------|-------------|--------|-----------|
| Warmup | IQA (6 reg) + Script (1 cls) | 5 | Largest datasets, establish backbone features |
| Expand | + Orientation (1 cls) + Skew (1 reg) | 5 | Geometric understanding builds on visual features |
| Full | All 19 heads | 20-40 | All tasks jointly with Kendall weighting |
| Refine | All, lower LR | 5-10 | Fine-tune with reduced learning rate |

**Total**: ~35-60 epochs on SigLIP 2

### 4.4 Per-Task Data Sampling

Each training batch should be balanced across tasks using per-task sampling rates inversely proportional to dataset size:

```python
# Sampling rate: smaller datasets get higher sampling probability
# to ensure all heads see sufficient gradient signal
sampling_rate[task] = (1 / dataset_size[task]) / sum(1 / dataset_size[t] for t in tasks)
```

This ensures heads with smaller datasets (e.g., Code 10K, Shadow 15K) get adequate representation without requiring data duplication.

---

## 5. Dataset Generation Execution Order

Based on the ILP allocation strategy and training dependencies:

| Step | Dataset | Size | Source | Priority |
|------|---------|------|--------|----------|
| 1 | Orientation | 50K | Ready at `E:\03_training_datasets` | P0 (exists) |
| 2 | Synth-Multiscript | 250K | Generate on GCS via synth pipeline | P0 (in progress) |
| 3 | Skew | 40K | Derive from synth-multiscript base images | P1 |
| 4 | Resolution Quality | 30K | Derive from synth-multiscript + real docs at varied DPI | P1 |
| 5 | IQA (Phase 1) | 16K | OHR-Bench (8.5K) + DIQA-5000 (5.5K) + SmartDoc-QA + MIDV500 | P1 |
| 6 | IQA (Phase 2) | 100K | Synth-multiscript degradation views + real augmented | P2 |
| 7 | Handwriting | 60K | IAM + PUCIT-OHUL + Nepali + Tibetan + Muharaf | P2 |
| 8 | Capture Method | 50K | Pseudo-labels from metadata (born-digital/scanner/camera) | P2 |
| 9 | Shadow | 15K | Doc3D + RealDAE + synthetic | P3 |
| 10 | Warping | 20K | Doc3D + synthetic perspective transforms | P3 |
| 11 | Code Screenshots | 10K | Carbon/Playwright generation from open-source repos | P3 |

### Generation Cost Optimization

The "Adjust, Not Redesign" strategy from the Diversity Requirements Plan means:

1. **Generate synth-multiscript base images ONCE** (250K images)
2. **Derive multi-task views** from the same base images:
   - Script detection labels: inherent from generation
   - Skew labels: apply `_apply_geometric_transforms()` (now correctly ordered before augmentation)
   - Resolution labels: render at different DPI tiers, measure char height
   - IQA labels: apply augmentation pipeline, record degradation parameters
   - Orientation labels: apply rotation, record class
3. **Amortized cost**: One rendering pass produces data for 5+ tasks

---

## 6. MobileNetV4-Conv-S Training

The fast pre-correction model trains separately on a focused subset:

| Head | Dataset | Architecture |
|------|---------|-------------|
| Orientation (4-class) | Orientation 50K + synth-multiscript orientation views | Shared backbone -> FC -> Softmax |
| Skew (regression) | Skew 40K (from synth pipeline) | Shared backbone -> FC -> tanh * 10 |
| Resolution Quality (regression) | Resolution 30K (multi-DPI renders) | Shared backbone -> FC -> sigmoid |

**Training**: Standard transfer learning from ImageNet-pretrained MobileNetV4-Conv-S. ~10 epochs, SGD with cosine annealing.

**Distillation Path** (deferred): After SigLIP 2 is trained, its orientation/skew/resolution heads provide soft labels for improved MobileNetV4 training.

---

## 7. Verification and Quality Gates

### Pre-Training QA

From DATASET_DIVERSITY_REQUIREMENTS.md Section 12:

- [ ] Global split registry: no SHA256 collisions between train/val/test across datasets
- [ ] Per-dimension diversity coverage meets minimum thresholds (14 dimensions)
- [ ] Per-source contribution caps enforced (40% max per source per class)
- [ ] Cross-dimension interaction tests pass (e.g., script x resolution, capture x degradation)
- [ ] Label provenance weights applied (tier_0=1.0, tier_1=1.0, tier_2=0.8, tier_3=0.5)

### Training Monitoring

- Per-head validation loss tracked independently (19 time series)
- Gradient cosine similarity matrix between heads (detect conflicts)
- Kendall sigma values (detect tasks with high uncertainty)
- Per-dimension error stratification (catch diversity gaps)

### Red Flags During Training

| Signal | Action |
|--------|--------|
| Any head loss diverging | Reduce that head's learning rate; check data quality |
| >30% head pairs with negative gradient cosine | Enable PCGrad immediately |
| Kendall sigma >3.0 for any head | Investigate data quality for that task; possible label noise |
| Validation loss not improving for 5 epochs | Trigger Phase 3 (Bayesian Optimization) |
| Two heads consistently anti-correlated | Document as genuine trade-off; consider Phase 4 (NSGA-II) |

---

## 8. Production Safeguards

### Classical Fallback Table

If ML confidence is below threshold, fall back to classical methods:

| Task | ML Threshold | Classical Fallback |
|------|-------------|-------------------|
| Orientation | <0.85 confidence | Hough line analysis + text direction |
| Skew | predicted uncertainty >2.0 | Hough transform deskew |
| Resolution | <0.70 confidence | PyMuPDF DPI metadata + connected components |
| Script | <0.60 confidence | Unicode range analysis |
| IQA (blur) | <0.50 confidence | Laplacian variance |
| IQA (noise) | <0.50 confidence | Wiener filter estimation |
| Handwriting | <0.70 confidence | Stroke width transform heuristics |

### Confidence-Based Label Weighting (Training)

For mixed-provenance datasets:

```
training_weight = tier_base_weight * min(confidence, 1.0)
```

Where tier weights: `tier_0_exact=1.0`, `tier_1_annotation=1.0`, `tier_2_model=0.8`, `tier_3_heuristic=0.5`

---

## 9. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Camera capture IQA gap | High | Critical | Added SmartDoc-QA + MIDV500 to IQA dataset (583 -> 8,475 camera samples) |
| Script confusion (CJK) | Medium | High | HANS/HANT second-stage classifier; per-script test coverage |
| Synth-real domain gap | Medium | High | Active learning loop (Phase 2) identifies failing real-world cases |
| 19-head gradient conflict | Medium | Medium | PCGrad + Kendall uncertainty weighting + phased head training |
| Augmentation ordering artifacts | Fixed | High | Geometric transforms now applied before noise (this plan, Section 2) |
| ILP infeasibility | Low | Medium | Relax constraints iteratively; per-source caps are soft constraints |

---

## 10. Timeline and Dependencies

```
Week 1-2: ILP solver for sample allocation
    |-- Requires: Layer 2 metadata aggregates (20/51 datasets ready)
    |-- Output: Allocation matrix for 10 training datasets
    v
Week 3-4: Synth-multiscript generation (250K) with fixed augmentation ordering
    |-- Requires: Bug fix (done), generation infrastructure
    |-- Output: 250K base images + multi-task metadata
    v
Week 5-6: Derive task-specific datasets from base images
    |-- Skew (40K), Resolution (30K), IQA views (100K)
    |-- Requires: Allocation matrix from ILP
    v
Week 7-8: Assemble and validate all 10 training datasets
    |-- Requires: Real data sources (IAM, OHR-Bench, etc.)
    |-- Run pre-training QA (Section 7)
    v
Week 9-12: SigLIP 2 multi-task training (Phase 4.3 schedule)
    |-- Warmup -> Expand -> Full -> Refine
    v
Week 10-11 (parallel): MobileNetV4-Conv-S training
    |-- 3 heads, 10 epochs
    v
Week 13+: Active learning loop (Phase 2)
    |-- Evaluate, identify failures, augment, retrain
```

---

## 11. Consensus Model Contributions

| Model | Key Recommendation | Incorporated |
|-------|-------------------|-------------|
| Gemini 2.5 Pro (FOR, 9/10) | ILP -> BO -> NSGA-II ordering; validated all 3 recs | Yes (Section 3) |
| Gemini 3 Pro Preview (AGAINST, 9/10) | Augmentation ordering bug; over-engineering caution | Yes (Section 2, scope reduced) |
| GPT-5.2 (NEUTRAL) | Empty response | N/A |
| DeepSeek R1 (NEUTRAL, 8/10) | Script pseudo-labeling via Unicode; per-task random seeds | Yes (Section 4.4, 5) |
| Grok 4 (AGAINST, 8/10) | ILP first; active learning before BO; per-task randomization | Yes (Section 3 ordering) |

### Unanimous Consensus Points

1. **ILP before BO**: Start with discrete allocation, not continuous parameter tuning
2. **Active Learning before NSGA-II**: Real failure analysis more valuable than theoretical Pareto
3. **Augmentation ordering is critical**: Geometry before noise (now fixed)
4. **PCGrad + Kendall uncertainty**: Recommended combination for 19-head multi-task
5. **Phased head training**: Don't train all 19 heads from epoch 0

### Split Opinions (Resolved)

| Topic | For | Against | Resolution |
|-------|-----|---------|------------|
| BO timing | Gemini 2.5 Pro: early | Grok 4: only after AL plateau | After active learning (Phase 3) |
| NSGA-II utility | Gemini 2.5 Pro: useful | All others: premature | Deferred (Phase 4) |
| Scope of optimization | Gemini 2.5 Pro: full framework | Gemini 3 Pro: over-engineered | Reduced to actionable phases |
